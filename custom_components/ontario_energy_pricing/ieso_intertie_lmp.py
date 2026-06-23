"""IESO Intertie LMP Client.

Provides real-time interchange LMP prices at interties from IESO.
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


IESO_INTERTIE_LMP_URL: Final = (
    "https://reports-public.ieso.ca/public/RealTimeIntertieLMP/"
    "PUB_RealTimeIntertieLMP.xml"
)


@dataclass(frozen=True, slots=True)
class IESOIntertieLMP:
    """LMP at a specific intertie point for a specific interval."""

    intertie_point: str  # e.g., "EC.MARITIMES_NYSI:LMP"
    delivery_date: str
    delivery_hour: int
    interval: int  # 1-12
    lmp_mwh: float  # $/MWh
    flag: str


@dataclass(frozen=True, slots=True)
class IESOIntertieLMPData:
    """Complete intertie LMP data."""

    delivery_date: str
    delivery_hour: int
    created_at: datetime
    lmp_data: list[IESOIntertieLMP] = field(default_factory=list)

    def get_lmp_by_intertie(self, intertie_point: str) -> list[IESOIntertieLMP]:
        """Get LMP data for a specific intertie point."""
        return [
            l
            for l in self.lmp_data
            if l.intertie_point.upper() == intertie_point.upper()
        ]

    def get_latest_lmp_by_intertie(self, intertie_point: str) -> IESOIntertieLMP | None:
        """Get the most recent LMP for a specific intertie point."""
        intertie_data = self.get_lmp_by_intertie(intertie_point)
        if not intertie_data:
            return None
        return max(intertie_data, key=lambda x: x.interval)

    def get_intertie_points(self) -> list[str]:
        """Get list of intertie points available."""
        return list({l.intertie_point for l in self.lmp_data})

    def get_current_interval_lmp(self, intertie_point: str) -> float | None:
        """Get the current interval LMP for a specific intertie point."""
        latest = self.get_latest_lmp_by_intertie(intertie_point)
        if latest:
            return latest.lmp_mwh
        return None


class IESOIntertieLMPClient:
    """Client for fetching IESO Intertie LMP data."""

    def __init__(self, session: aiohttp.ClientSession, timeout: int = 30) -> None:
        """Initialize the client."""
        self._session = session
        self._timeout = aiohttp.ClientTimeout(total=timeout)

    async def fetch(self) -> IESOIntertieLMPData:
        """Fetch and parse intertie LMP data."""
        try:
            async with self._session.get(
                IESO_INTERTIE_LMP_URL, timeout=self._timeout
            ) as resp:
                resp.raise_for_status()
                content = await resp.text()
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise IESOPredispatchError(
                f"Failed to fetch intertie LMP data: {err}"
            ) from err

        return self._parse_xml(content)

    def _parse_xml(self, xml_content: str) -> IESOIntertieLMPData:
        """Parse intertie LMP XML."""
        try:
            root = ET.fromstring(xml_content)
        except ET.ParseError as err:
            raise IESOPredispatchError(f"Invalid XML: {err}") from err

        ns = {"ieso": IESO_LMP_NAMESPACE}

        # Parse metadata
        created_at_elem = root.find(".//ieso:CreatedAt", ns)
        delivery_date_elem = root.find(".//ieso:DeliveryDate", ns)
        delivery_hour_elem = root.find(".//ieso:DeliveryHour", ns)

        if not all(
            elem is not None and elem.text
            for elem in [created_at_elem, delivery_date_elem, delivery_hour_elem]
        ):
            raise IESOPredispatchError("Required XML elements not found")

        assert created_at_elem is not None and created_at_elem.text
        assert delivery_date_elem is not None and delivery_date_elem.text
        assert delivery_hour_elem is not None and delivery_hour_elem.text

        created_at = datetime.fromisoformat(created_at_elem.text)
        delivery_date = delivery_date_elem.text.strip()
        delivery_hour = int(delivery_hour_elem.text)

        lmp_data: list[IESOIntertieLMP] = []

        # Parse IntertieLMPrice elements
        for intertie_lmp_price in root.findall(".//ieso:IntertieLMPrice", ns):
            intertie_name_elem = intertie_lmp_price.find("ieso:IntertiePLName", ns)
            if intertie_name_elem is None or intertie_name_elem.text is None:
                continue
            intertie_point = intertie_name_elem.text.strip()

            # Parse Components - we want the "Intertie LMP" component
            for components in intertie_lmp_price.findall("ieso:Components", ns):
                lmp_component_elem = components.find("ieso:LMPComponent", ns)
                if lmp_component_elem is None or lmp_component_elem.text is None:
                    continue
                if lmp_component_elem.text.strip() != "Intertie LMP":
                    continue

                # Parse IntervalLMP elements
                for interval_lmp in components.findall("ieso:IntervalLMP", ns):
                    interval_elem = interval_lmp.find("ieso:Interval", ns)
                    lmp_elem = interval_lmp.find("ieso:LMP", ns)
                    flag_elem = interval_lmp.find("ieso:Flag", ns)

                    if interval_elem is None or interval_elem.text is None:
                        continue
                    if lmp_elem is None or lmp_elem.text is None or lmp_elem.text.strip() == "":
                        continue

                    try:
                        interval = int(interval_elem.text)
                        lmp_mwh = float(lmp_elem.text)
                        flag = flag_elem.text.strip() if flag_elem is not None and flag_elem.text else ""
                    except (ValueError, TypeError):
                        continue

                    if 1 <= interval <= 12:
                        lmp_data.append(
                            IESOIntertieLMP(
                                intertie_point=intertie_point,
                                delivery_date=delivery_date,
                                delivery_hour=delivery_hour,
                                interval=interval,
                                lmp_mwh=lmp_mwh,
                                flag=flag,
                            )
                        )

        return IESOIntertieLMPData(
            delivery_date=delivery_date,
            delivery_hour=delivery_hour,
            created_at=created_at,
            lmp_data=lmp_data,
        )