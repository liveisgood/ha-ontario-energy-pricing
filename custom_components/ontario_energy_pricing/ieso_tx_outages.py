"""IESO Transmission Outages Client.

Provides real-time and planned transmission outages from IESO.
"""

from __future__ import annotations

import asyncio
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime
from typing import Final

import aiohttp

from .const import IESO_LMP_NAMESPACE
from .exceptions import IESOPredispatchError


IESO_TX_OUTAGES_URL: Final = (
    "https://reports-public.ieso.ca/public/TxOutagesTodayAll/"
    "PUB_TxOutagesTodayAll.xml"
)


@dataclass(frozen=True, slots=True)
class IESOTxOutage:
    """Single transmission outage."""

    equipment_name: str
    equipment_type: str
    zone: str
    start_date: str
    start_time: str
    end_date: str
    end_time: str
    status: str
    reason: str
    capacity_mw: float


@dataclass(frozen=True, slots=True)
class IESOTxOutagesData:
    """Complete transmission outages data."""

    delivery_date: str
    created_at: datetime
    outages: list[IESOTxOutage] = field(default_factory=list)

    def get_outages_by_zone(self, zone: str) -> list[IESOTxOutage]:
        """Get outages affecting a specific zone."""
        return [o for o in self.outages if o.zone.upper() == zone.upper()]

    def get_active_outages(self) -> list[IESOTxOutage]:
        """Get outages that are currently active.

        A transmission outage is considered active if it has status 'IMPL'
        (implemented/in progress) per the IESO feed.
        """
        return [o for o in self.outages if o.status in ("IMPL", "ACTIVE", "IN_PROGRESS")]

    def get_total_capacity_impact(self, zone: str | None = None) -> float:
        """Get total capacity impact in MW, optionally filtered by zone."""
        if zone:
            outages = [o for o in self.outages if o.zone.upper() == zone.upper()]
        else:
            outages = self.outages
        return sum(o.capacity_mw for o in outages)


class IESOTxOutagesClient:
    """Client for fetching IESO Transmission Outages data."""

    def __init__(self, session: aiohttp.ClientSession, timeout: int = 30) -> None:
        """Initialize the client."""
        self._session = session
        self._timeout = aiohttp.ClientTimeout(total=timeout)

    async def fetch(self) -> IESOTxOutagesData:
        """Fetch and parse transmission outages data."""
        try:
            async with self._session.get(
                IESO_TX_OUTAGES_URL, timeout=self._timeout
            ) as resp:
                resp.raise_for_status()
                content = await resp.text()
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise IESOPredispatchError(f"Failed to fetch tx outages: {err}") from err

        return self._parse_xml(content)

    def _parse_xml(self, xml_content: str) -> IESOTxOutagesData:
        """Parse transmission outages XML.

        Real IESO format:
        <Document>
          <DocHeader><CreatedAt>...</CreatedAt></DocHeader>
          <DocBody>
            <OutageRangeStart>...</OutageRangeStart>
            <OutageRangeEnd>...</OutageRangeEnd>
            <OutageRequest>
              <OutageID>...</OutageID>
              <PlannedStart>...</PlannedStart>
              <PlannedEnd>...</PlannedEnd>
              <Priority>...</Priority>
              <EquipmentRequested>
                <EquipmentName>...</EquipmentName>
                <EquipmentType>...</EquipmentType>
                <EquipmentVoltage>...</EquipmentVoltage>
              </EquipmentRequested>
              <OutageRequestStatus>...</OutageRequestStatus>
            </OutageRequest>
          </DocBody>
        </Document>
        """
        try:
            root = ET.fromstring(xml_content)
        except ET.ParseError as err:
            raise IESOPredispatchError(f"Invalid XML: {err}") from err

        ns = {"ieso": IESO_LMP_NAMESPACE}

        created_at_elem = root.find(".//ieso:CreatedAt", ns)
        if created_at_elem is None or not created_at_elem.text:
            raise IESOPredispatchError("Required XML elements not found")

        created_at = datetime.fromisoformat(created_at_elem.text)
        delivery_date = created_at.strftime("%Y-%m-%d")

        outages: list[IESOTxOutage] = []

        for request_elem in root.findall(".//ieso:OutageRequest", ns):
            outage_id_elem = request_elem.find("ieso:OutageID", ns)
            planned_start_elem = request_elem.find("ieso:PlannedStart", ns)
            planned_end_elem = request_elem.find("ieso:PlannedEnd", ns)
            status_elem = request_elem.find("ieso:OutageRequestStatus", ns)

            if status_elem is None or not status_elem.text:
                continue

            # Get first equipment name/type (an outage can have multiple equipment entries)
            equip_elem = request_elem.find("ieso:EquipmentRequested", ns)
            equipment_name = "Unknown"
            equipment_type = "Unknown"
            if equip_elem is not None:
                name_elem = equip_elem.find("ieso:EquipmentName", ns)
                type_elem = equip_elem.find("ieso:EquipmentType", ns)
                if name_elem is not None and name_elem.text is not None:
                    equipment_name = name_elem.text.strip()
                if type_elem is not None and type_elem.text is not None:
                    equipment_type = type_elem.text.strip()

            # Derive start/end dates and times from PlannedStart/PlannedEnd
            start_date = ""
            start_time = ""
            end_date = ""
            end_time = ""
            if planned_start_elem is not None and planned_start_elem.text is not None:
                try:
                    dt = datetime.fromisoformat(planned_start_elem.text)
                    start_date = dt.strftime("%Y-%m-%d")
                    start_time = dt.strftime("%H:%M:%S")
                except (ValueError, TypeError):
                    pass
            if planned_end_elem is not None and planned_end_elem.text is not None:
                try:
                    dt = datetime.fromisoformat(planned_end_elem.text)
                    end_date = dt.strftime("%Y-%m-%d")
                    end_time = dt.strftime("%H:%M:%S")
                except (ValueError, TypeError):
                    pass

            # Determine zone from equipment name (e.g., "FORT WILLIAM" -> "NORTHWEST")
            # Fallback to "UNKNOWN" since IESO feed doesn't include zone info directly
            zone = self._derive_zone_from_equipment(equipment_name)

            # Determine outage reason from priority
            priority_elem = request_elem.find("ieso:Priority", ns)
            reason = priority_elem.text.strip() if priority_elem is not None and priority_elem.text is not None else "Scheduled"

            outages.append(
                IESOTxOutage(
                    equipment_name=equipment_name,
                    equipment_type=equipment_type,
                    zone=zone,
                    start_date=start_date,
                    start_time=start_time,
                    end_date=end_date,
                    end_time=end_time,
                    status=status_elem.text.strip(),
                    reason=reason,
                    capacity_mw=0.0,  # IESO feed doesn't include MW capacity directly
                )
            )

        return IESOTxOutagesData(
            delivery_date=delivery_date,
            created_at=created_at,
            outages=outages,
        )

    def _derive_zone_from_equipment(self, equipment_name: str) -> str:
        """Derive IESO zone from equipment name using known station prefixes."""
        # Map common station/area prefixes to IESO zones
        known_prefixes = {
            "BAIN": "EAST", "BLDG": "TORONTO", "BROOK": "EAST",
            "BRUCE": "BRUCE", "BUR": "TORONTO", "CH": "NIAGARA",
            "CHAPAIS": "NORTHEAST", "CHE": "NIAGARA", "CL": "OTTAWA",
            "CLAR": "EAST", "CON": "SOUTHWEST", "DAR": "TORONTO",
            "DAWN": "SOUTHWEST", "DOW": "EAST", "ELG": "SOUTHWEST",
            "ELL": "NORTHEAST", "ERS": "NORTHEAST", "FORT": "NORTHWEST",
            "FORT FRANCES": "NORTHWEST", "FORT WILLIAM": "NORTHWEST",
            "GARD": "ESSA", "GORE": "SOUTHWEST", "GRE": "NIAGARA",
            "GREEN": "EAST", "GRIFFIN": "TORONTO", "GRIM": "NIAGARA",
            "HALD": "NIAGARA", "HAN": "SOUTHWEST", "HER": "TORONTO",
            "HIGH": "TORONTO", "HIG": "TORONTO", "HOLT": "NORTHEAST",
            "HURLE": "NORTHWEST", "HURON": "WEST", "KAP": "NORTHEAST",
            "KIR": "NORTHEAST", "KORTR": "NORTHEAST", "LAKE": "TORONTO",
            "LAM": "SOUTHWEST", "LEA": "EAST", "LONG": "SOUTHWEST",
            "LONDON": "SOUTHWEST", "MAG": "NORTHEAST", "MAJESTIC": "EAST",
            "MAN": "TORONTO", "MAR": "TORONTO", "MEAF": "WEST",
            "MER": "TORONTO", "MID": "ESSA", "MISS": "TORONTO",
            "MIL": "TORONTO", "MTN": "EAST", "NAG": "NIAGARA",
            "NANT": "SOUTHWEST", "NEW": "TORONTO", "NIAG": "NIAGARA",
            "NIP": "NORTHEAST", "NOR": "ESSA", "NORFOLK": "SOUTHWEST",
            "NORTH": "NORTHEAST", "OAK": "TORONTO", "OAKV": "TORONTO",
            "ORI": "ESSA", "OSHA": "TORONTO", "OTTA": "OTTAWA",
            "OWER": "WEST", "PARK": "TORONTO", "PAUGAN": "NORTHEAST",
            "PEL": "NIAGARA", "PER": "ESSA", "PERR": "NORTHEAST",
            "PETA": "TORONTO", "PICK": "TORONTO", "PIN": "ESSA",
            "PINE": "NORTHEAST", "PINO": "NORTHEAST", "PINY": "NORTHEAST",
            "PLA": "OTTAWA", "POC": "NORTHEAST", "POR": "OTTAWA",
            "PORT": "OTTAWA", "RAIN": "NORTHEAST", "RAM": "TORONTO",
            "RAN": "NORTHEAST", "RED": "NORTHWEST", "RID": "EAST",
            "RIVER": "NORTHEAST", "RYE": "OTTAWA", "SAP": "NORTHEAST",
            "SAU": "NORTHEAST", "SCAR": "TORONTO", "SHAN": "NORTHEAST",
            "SIE": "TORONTO", "SMOK": "NORTHEAST", "SPRING": "SOUTHWEST",
            "STAD": "NIAGARA", "SUDB": "NORTHEAST", "TER": "ESSA",
            "THOR": "NIAGARA", "THUN": "NORTHWEST", "THUNDER": "NORTHWEST",
            "TIL": "SOUTHWEST", "TOR": "TORONTO", "TRAF": "TORONTO",
            "TRAFAL": "TORONTO", "TRAIL": "NORTHEAST", "TWE": "NORTHEAST",
            "UHT": "NORTHEAST", "UPPER": "NORTHEAST", "VIA": "ESSA",
            "WASA": "ESSA", "WATER": "SOUTHWEST", "WAWA": "NORTHEAST",
            "WEST": "SOUTHWEST", "WESTW": "NIAGARA", "WHIT": "TORONTO",
            "WIND": "SOUTHWEST", "WINS": "SOUTHWEST", "WOOD": "SOUTHWEST",
            "ZONE": "EAST",
        }
        name_upper = equipment_name.upper().strip()
        for prefix, zone in known_prefixes.items():
            if name_upper.startswith(prefix):
                return zone
        return "UNKNOWN"

    async def _fetch_xml(self) -> str:
        """Fetch XML content."""
        async with self._session.get(
            IESO_TX_OUTAGES_URL, timeout=self._timeout
        ) as resp:
            resp.raise_for_status()
            return await resp.text()
