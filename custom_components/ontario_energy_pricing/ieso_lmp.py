"""IESO Real-Time Ontario Zonal Price XML client."""

from __future__ import annotations

import asyncio
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Final

import aiohttp  # type: ignore[import]

from .const import LOGGER
from .const import IESO_DEFAULT_TIMEOUT

# IESO Ontario Zonal Price URL
IESO_LMP_URL: Final = "https://reports-public.ieso.ca/public/RealtimeOntarioZonalPrice/PUB_RealtimeOntarioZonalPrice.xml"
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

    @property
    def time_range(self) -> str:
        """Return the time range for this interval."""
        hour_start = (self.interval - 1) * 5
        hour_end = self.interval * 5
        return f"{hour_start:02d}-{hour_end:02d} min"


@dataclass(frozen=True, slots=True)
class IESOLMPData:
    """IESO Ontario Zonal Pricing data for a delivery hour."""

    delivery_date: str  # YYYY-MM-DD
    delivery_hour: int  # 0-23
    created_at: datetime
    intervals: list[IESOZonalPrice] = field(default_factory=list)
    hour_average_mwh: float = 0.0
    hour_average_kwh: float = 0.0

    @property
    def latest_interval(self) -> IESOZonalPrice | None:
        """Get the most recent complete interval."""
        if not self.intervals:
            return None
        return max(self.intervals, key=lambda x: x.interval)

    @property
    def current_lmp_kwh(self) -> float:
        """Current LMP in ¢/kWh (latest interval or hour average)."""
        latest = self.latest_interval
        if latest:
            return latest.lmp_kwh
        return self.hour_average_kwh

    @property
    def effective_time(self) -> datetime:
        """The effective time of the current price."""
        now = datetime.now(tz=timezone.utc)
        latest = self.latest_interval
        if latest:
            # Calculate the actual start time
            base_time = datetime.strptime(
                f"{self.delivery_date} {self.delivery_hour:02d}:00", "%Y-%m-%d %H:%M"
            ).replace(tzinfo=timezone.utc)
            minutes_offset = (latest.interval - 1) * 5
            return base_time + timedelta(minutes=minutes_offset)
        return now

    def calculate_total_rate(self, global_adjustment: float, admin_fee: float) -> float:
        """Calculate total rate including GA and admin fee.

        All inputs should be in ¢/kWh.
        Returns total rate in ¢/kWh.
        """
        return self.current_lmp_kwh + global_adjustment + admin_fee


class IESOLMPClient:
    """Client for IESO Real-Time Ontario Zonal Price XML feed."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        """Initialize the IESO LMP client."""
        self._session = session
        self._url = IESO_LMP_URL

    async def async_get_current_lmp(self) -> IESOLMPData:
        """Fetch current Ontario Zonal LMP data."""
        try:
            async with asyncio.timeout(IESO_DEFAULT_TIMEOUT):
                async with self._session.get(self._url) as response:
                    response.raise_for_status()
                    xml_text = await response.text()
        except aiohttp.ClientError as err:
            raise IESOLMPError(f"Failed to fetch IESO LMP XML: {err}") from err
        except TimeoutError as err:
            raise IESOLMPError("IESO LMP request timeout") from err

        return self._parse_lmp_xml(xml_text)

    def _parse_lmp_xml(self, xml_text: str) -> IESOLMPData:
        """Parse IESO Real-Time Ontario Zonal Price XML."""
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as err:
            raise IESOLMPError(
                f"Invalid XML: {err}",
                xml_snippet=xml_text[:500],
            ) from err

        ns = {"ieso": IESO_LMP_NS}

        # Extract metadata
        created_at_elem = root.find(".//ieso:CreatedAt", ns)
        if created_at_elem is None:
            created_at_elem = root.find(".//CreatedAt")

        delivery_date_elem = root.find(".//ieso:DeliveryDate", ns)
        if delivery_date_elem is None:
            delivery_date_elem = root.find(".//DeliveryDate")

        delivery_hour_elem = root.find(".//ieso:DeliveryHour", ns)
        if delivery_hour_elem is None:
            delivery_hour_elem = root.find(".//DeliveryHour")

        # Validate required elements
        for name, elem in [
            ("CreatedAt", created_at_elem),
            ("DeliveryDate", delivery_date_elem),
            ("DeliveryHour", delivery_hour_elem),
        ]:
            if elem is None or not elem.text:
                raise IESOLMPError(
                    f"{name} element not found",
                    xml_snippet=xml_text[:500],
                )

        created_at = datetime.fromisoformat(created_at_elem.text)
        delivery_date = delivery_date_elem.text.strip()
        delivery_hour = int(delivery_hour_elem.text)

        # Parse interval data
        intervals: list[IESOZonalPrice] = []
        zonal_prices = root.findall(".//ieso:ZonalPrice", ns) or root.findall(
            ".//ZonalPrice"
        )

        for price in zonal_prices:
            interval_elem = price.find("ieso:Interval", ns) or price.find("Interval")
            lmp_elem = price.find("ieso:LmpCap", ns) or price.find("LmpCap")
            flag_elem = price.find("ieso:Flag", ns) or price.find("Flag")

            # Skip empty intervals (not yet populated)
            if (
                interval_elem is None
                or not interval_elem.text
                or lmp_elem is None
                or not lmp_elem.text
                or not lmp_elem.text.strip()
            ):
                continue

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
                        lmp_kwh=lmp_mwh / 10,  # Convert $/MWh to ¢/kWh
                        flag=flag,
                    )
                )
            except (ValueError, TypeError) as err:
                LOGGER.warning("Skipping invalid LMP interval: %s", err)

        # Parse hour average
        avg_elem = root.find(".//ieso:AveragePrice/ieso:LmpCap", ns) or root.find(
            ".//AveragePrice/LmpCap"
        )
        hour_average_mwh = 0.0
        if avg_elem is not None and avg_elem.text:
            try:
                hour_average_mwh = float(avg_elem.text)
            except ValueError:
                LOGGER.warning("Could not parse hour average LMP")

        # Sort intervals by number
        intervals.sort(key=lambda x: x.interval)

        LOGGER.debug(
            "Parsed IESO LMP: date=%s, hour=%s, intervals=%d, avg=%.2f",
            delivery_date,
            delivery_hour,
            len(intervals),
            hour_average_mwh,
        )

        return IESOLMPData(
            delivery_date=delivery_date,
            delivery_hour=delivery_hour,
            created_at=created_at,
            intervals=intervals,
            hour_average_mwh=hour_average_mwh,
            hour_average_kwh=hour_average_mwh / 10,  # Convert to ¢/kWh
        )
