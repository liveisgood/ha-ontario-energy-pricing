"""IESO Real-Time Ontario Zonal Price XML client."""

from __future__ import annotations

import asyncio
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    import aiohttp

from .const import IESO_DEFAULT_TIMEOUT, LOGGER

# IESO Ontario Zonal Price URL
IESO_LMP_URL: Final = (
    "https://reports-public.ieso.ca/public/RealtimeOntarioZonalPrice/"
    "PUB_RealtimeOntarioZonalPrice.xml"
)
IESO_LMP_NS: Final = "http://www.ieso.ca/schema"


class IESOLMPError(Exception):
    """Error parsing or fetching IESO LMP data."""

    def __init__(self, message: str, xml_snippet: str | None = None) -> None:
        """Initialize the error."""
        super().__init__(message)
        self.xml_snippet = xml_snippet


@dataclass(frozen=True, slots=True)
class IESOZonalPrice:
    """A single 5-minute interval price."""

    interval: int  # 1-12
    lmp_mwh: float  # $/MWh
    lmp_kwh: float  # ¢/kWh (lmp_mwh / 10)
    flag: str  # Dispatch status


@dataclass(frozen=True, slots=True)
class IESOLMPData:
    """IESO Ontario Zonal Pricing data."""

    delivery_date: str
    delivery_hour: int
    created_at: datetime
    intervals: list[IESOZonalPrice] = field(default_factory=list)
    hour_average_mwh: float = 0.0
    hour_average_kwh: float = 0.0

    @property
    def latest_interval(self) -> IESOZonalPrice | None:
        """Get most recent interval."""
        if not self.intervals:
            return None
        return max(self.intervals, key=lambda x: x.interval)

    @property
    def current_lmp_kwh(self) -> float:
        """Current LMP in ¢/kWh."""
        latest = self.latest_interval
        if latest:
            return latest.lmp_kwh
        return self.hour_average_kwh


class IESOLMPClient:
    """Client for IESO LMP XML."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        """Initialize client."""
        self._session = session

    async def async_get_current_lmp(self) -> IESOLMPData:
        """Fetch current LMP data."""
        try:
            async with asyncio.timeout(IESO_DEFAULT_TIMEOUT):
                async with self._session.get(IESO_LMP_URL) as response:
                    response.raise_for_status()
                    xml_text = await response.text()
        except Exception as err:
            raise IESOLMPError(f"Failed to fetch IESO LMP: {err}") from err

        return self._parse_lmp_xml(xml_text)

    def _parse_lmp_xml(self, xml_text: str) -> IESOLMPData:
        """Parse IESO LMP XML."""
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as err:
            raise IESOLMPError(f"Invalid XML: {err}") from err

        ns = {"ieso": IESO_LMP_NS}

        # Extract metadata
        created_at_elem = root.find(".//ieso:CreatedAt", ns)
        delivery_date_elem = root.find(".//ieso:DeliveryDate", ns)
        delivery_hour_elem = root.find(".//ieso:DeliveryHour", ns)

        if not all(
            elem is not None and elem.text
            for elem in [created_at_elem, delivery_date_elem, delivery_hour_elem]
        ):
            raise IESOLMPError("Required XML elements not found")

        assert created_at_elem is not None and created_at_elem.text
        assert delivery_date_elem is not None and delivery_date_elem.text
        assert delivery_hour_elem is not None and delivery_hour_elem.text

        created_at = datetime.fromisoformat(created_at_elem.text)
        delivery_date = delivery_date_elem.text.strip()
        delivery_hour = int(delivery_hour_elem.text)

        intervals: list[IESOZonalPrice] = []
        zonal_prices = root.findall(".//ieso:ZonalPrice", ns)

        for price in zonal_prices:
            interval_elem = price.find("ieso:Interval", ns)
            lmp_elem = price.find("ieso:LmpCap", ns)
            flag_elem = price.find("ieso:Flag", ns)

            if not all(
                elem is not None and elem.text and elem.text.strip()
                for elem in [interval_elem, lmp_elem]
            ):
                continue

            assert interval_elem is not None and interval_elem.text
            assert lmp_elem is not None and lmp_elem.text

            try:
                interval_num = int(interval_elem.text)
                lmp_mwh = float(lmp_elem.text)
                flag = (
                    flag_elem.text if flag_elem is not None and flag_elem.text else ""
                )

                intervals.append(
                    IESOZonalPrice(
                        interval=interval_num,
                        lmp_mwh=lmp_mwh,
                        lmp_kwh=lmp_mwh / 10,
                        flag=flag,
                    )
                )
            except (ValueError, TypeError):
                continue

        intervals.sort(key=lambda x: x.interval)

        LOGGER.debug(
            "Parsed IESO LMP: date=%s, hour=%s, intervals=%d",
            delivery_date,
            delivery_hour,
            len(intervals),
        )

        return IESOLMPData(
            delivery_date=delivery_date,
            delivery_hour=delivery_hour,
            created_at=created_at,
            intervals=intervals,
        )
