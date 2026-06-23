"""IESO Real-Time Zonal Energy Price XML client."""

from __future__ import annotations

import asyncio
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime
from typing import Final

import aiohttp

from .const import (
    IESO_DEFAULT_TIMEOUT,
    IESO_LMP_NAMESPACE,
    LOGGER,
    get_zone_from_location,
)
from .exceptions import IESOLMPError


# Correct zonal feed with per-zone prices
IESO_ZONAL_LMP_URL: Final = (
    "https://reports-public.ieso.ca/public/RealtimeZonalEnergyPrices/"
    "PUB_RealtimeZonalEnergyPrices.xml"
)


@dataclass(frozen=True, slots=True)
class IESOZonalPrice:
    """A single 5-minute interval price for a specific zone."""

    interval: int  # 1-12
    lmp_mwh: float  # $/MWh
    lmp_kwh: float  # ¢/kWh ($/MWh × 100¢/$ ÷ 1000kWh/MWh = $/MWh ÷ 10)
    flag: str  # Dispatch status

    @property
    def time_range(self) -> str:
        """Get time range string for this interval (e.g., '00-05 min')."""
        start_min = (self.interval - 1) * 5
        end_min = self.interval * 5
        return f"{start_min:02d}-{end_min:02d} min"


@dataclass(frozen=True, slots=True)
class IESOLMPData:
    """IESO Ontario Zonal Pricing data for a specific zone."""

    zone: str
    delivery_date: str
    delivery_hour: int
    created_at: datetime
    intervals: list[IESOZonalPrice] = field(default_factory=list)

    @property
    def hour_average_mwh(self) -> float:
        """Average LMP across all available intervals in $/MWh."""
        if not self.intervals:
            return 0.0
        return sum(i.lmp_mwh for i in self.intervals) / len(self.intervals)

    @property
    def hour_average_kwh(self) -> float:
        """Average LMP across all available intervals in ¢/kWh."""
        # $/MWh × 100¢/$ ÷ 1000kWh/MWh = $/MWh ÷ 10
        return self.hour_average_mwh / 10

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
    """Client for IESO Zonal LMP XML."""

    def __init__(
        self, session: aiohttp.ClientSession, location: str | None = None
    ) -> None:
        """Initialize client with optional location for zone selection."""
        self._session = session
        self._zone = get_zone_from_location(location) if location else "TORONTO"
        LOGGER.info("IESO LMP client initialized for zone: %s", self._zone)

    async def async_get_current_lmp(self) -> IESOLMPData:
        """Fetch current LMP data for the configured zone."""
        try:
            async with asyncio.timeout(IESO_DEFAULT_TIMEOUT):
                async with self._session.get(IESO_ZONAL_LMP_URL) as response:
                    response.raise_for_status()
                    xml_text = await response.text()
        except Exception as err:
            raise IESOLMPError(f"Failed to fetch IESO LMP: {err}") from err

        return self._parse_lmp_xml(xml_text)

    def _parse_lmp_xml(self, xml_text: str) -> IESOLMPData:
        """Parse IESO Zonal LMP XML for the configured zone."""
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as err:
            raise IESOLMPError(f"Invalid XML: {err}") from err

        ns = {"ieso": IESO_LMP_NAMESPACE}

        # Extract metadata
        created_at_elem = root.find(".//ieso:CreatedAt", ns)
        delivery_date_elem = root.find(".//ieso:DELIVERYDATE", ns)
        delivery_hour_elem = root.find(".//ieso:DELIVERYHOUR", ns)

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

        # Find the zone we want (format: "ZONENAME:HUB")
        target_zone_name = f"{self._zone}:HUB"

        # Search through TransactionZone elements
        for transaction_zone in root.findall(".//ieso:TransactionZone", ns):
            zone_name_elem = transaction_zone.find("ieso:ZoneName", ns)
            if zone_name_elem is None or zone_name_elem.text is None:
                continue

            if zone_name_elem.text.strip() != target_zone_name:
                continue

            # Found our zone - parse intervals
            for interval_price in transaction_zone.findall("ieso:IntervalPrice", ns):
                interval_elem = interval_price.find("ieso:Interval", ns)
                lmp_elem = interval_price.find("ieso:ZonalPrice", ns)
                flag_elem = interval_price.find("ieso:FlagNo", ns)

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
                        flag_elem.text
                        if flag_elem is not None and flag_elem.text
                        else ""
                    )

                    intervals.append(
                        IESOZonalPrice(
                            interval=interval_num,
                            lmp_mwh=lmp_mwh,
                            lmp_kwh=lmp_mwh / 10,  # $/MWh × 100¢/$ ÷ 1000kWh/MWh
                            flag=flag,
                        )
                    )
                except (ValueError, TypeError):
                    continue

            # Sort intervals by interval number
            intervals.sort(key=lambda x: x.interval)

            LOGGER.debug(
                "Parsed IESO LMP for zone %s: date=%s, hour=%s, intervals=%d",
                self._zone,
                delivery_date,
                delivery_hour,
                len(intervals),
            )

            return IESOLMPData(
                zone=self._zone,
                delivery_date=delivery_date,
                delivery_hour=delivery_hour,
                created_at=created_at,
                intervals=intervals,
            )

        # Zone not found
        raise IESOLMPError(
            f"Zone {target_zone_name} not found in IESO zonal price data"
        )