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
        """Get outages that are currently active (IN_PROGRESS)."""
        return [o for o in self.outages if o.status == "IN_PROGRESS"]

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

    async def _fetch_xml(self) -> str:
        """Fetch XML content."""
        async with self._session.get(
            IESO_TX_OUTAGES_URL, timeout=self._timeout
        ) as resp:
            resp.raise_for_status()
            return await resp.text()

    def _parse_xml(self, xml_content: str) -> IESOTxOutagesData:
        """Parse transmission outages XML."""
        try:
            root = ET.fromstring(xml_content)
        except ET.ParseError as err:
            raise IESOPredispatchError(f"Invalid XML: {err}") from err

        ns = {"ieso": IESO_LMP_NAMESPACE}

        created_at_elem = root.find(".//ieso:CreatedAt", ns)
        delivery_date_elem = root.find(".//ieso:DELIVERYDATE", ns)

        if not all(
            elem is not None and elem.text
            for elem in [created_at_elem, delivery_date_elem]
        ):
            raise IESOPredispatchError("Required XML elements not found")

        assert created_at_elem is not None and created_at_elem.text
        assert delivery_date_elem is not None and delivery_date_elem.text

        created_at = datetime.fromisoformat(created_at_elem.text)
        delivery_date = delivery_date_elem.text.strip()

        outages: list[IESOTxOutage] = []

        for outage_elem in root.findall(".//ieso:Outage", ns):
            equipment_name_elem = outage_elem.find("ieso:EquipmentName", ns)
            equipment_type_elem = outage_elem.find("ieso:EquipmentType", ns)
            zone_elem = outage_elem.find("ieso:Zone", ns)
            start_date_elem = outage_elem.find("ieso:StartDate", ns)
            start_time_elem = outage_elem.find("ieso:StartTime", ns)
            end_date_elem = outage_elem.find("ieso:EndDate", ns)
            end_time_elem = outage_elem.find("ieso:EndTime", ns)
            status_elem = outage_elem.find("ieso:Status", ns)
            reason_elem = outage_elem.find("ieso:Reason", ns)
            capacity_elem = outage_elem.find("ieso:CapacityMW", ns)

            if not all(
                elem is not None and elem.text
                for elem in [
                    equipment_name_elem,
                    equipment_type_elem,
                    zone_elem,
                    start_date_elem,
                    start_time_elem,
                    end_date_elem,
                    end_time_elem,
                    status_elem,
                    reason_elem,
                    capacity_elem,
                ]
            ):
                continue

            assert equipment_name_elem is not None and equipment_name_elem.text
            assert equipment_type_elem is not None and equipment_type_elem.text
            assert zone_elem is not None and zone_elem.text
            assert start_date_elem is not None and start_date_elem.text
            assert start_time_elem is not None and start_time_elem.text
            assert end_date_elem is not None and end_date_elem.text
            assert end_time_elem is not None and end_time_elem.text
            assert status_elem is not None and status_elem.text
            assert reason_elem is not None and reason_elem.text
            assert capacity_elem is not None and capacity_elem.text

            try:
                capacity_mw = float(capacity_elem.text)
            except (ValueError, TypeError):
                capacity_mw = 0.0

            outages.append(
                IESOTxOutage(
                    equipment_name=equipment_name_elem.text.strip(),
                    equipment_type=equipment_type_elem.text.strip(),
                    zone=zone_elem.text.strip(),
                    start_date=start_date_elem.text.strip(),
                    start_time=start_time_elem.text.strip(),
                    end_date=end_date_elem.text.strip(),
                    end_time=end_time_elem.text.strip(),
                    status=status_elem.text.strip(),
                    reason=reason_elem.text.strip(),
                    capacity_mw=capacity_mw,
                )
            )

        return IESOTxOutagesData(
            delivery_date=delivery_date,
            created_at=created_at,
            outages=outages,
        )


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
        """Get outages that are currently active (IN_PROGRESS)."""
        return [o for o in self.outages if o.status == "IN_PROGRESS"]

    def get_total_capacity_impact(self, zone: str | None = None) -> float:
        """Get total capacity impact in MW, optionally filtered by zone."""
        if zone:
            outages = [o for o in self.outages if o.zone.upper() == zone.upper()]
        else:
            outages = self.outages
        return sum(o.capacity_mw for o in outages)


# Constants already defined above
# IESO_TX_OUTAGES_URL already defined above