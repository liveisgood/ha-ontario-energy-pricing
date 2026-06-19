"""IESO Operating Reserve Prices Client.

Provides real-time operating reserve LMP prices from IESO.
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


IESO_RESERVE_PRICES_URL: Final = (
    "https://reports-public.ieso.ca/public/RealtimeORLMP/PUB_RealtimeORLMP.xml"
)


@dataclass(frozen=True, slots=True)
class IESOReserveTypePrices:
    """Reserve prices for a specific reserve type."""

    reserve_type: str
    hourly_prices: dict[int, dict[int, float]] = field(default_factory=dict)
    # Structure: hourly_prices[hour][interval] = price

    def get_reserve_price(self, hour: int, interval: int) -> float | None:
        """Get reserve price for specific hour and interval."""
        if hour not in self.hourly_prices:
            return None
        if interval not in self.hourly_prices[hour]:
            return None
        return self.hourly_prices[hour][interval]


@dataclass(frozen=True, slots=True)
class IESORegionReservePrice:
    """Reserve prices for a specific region."""

    region: str
    reserve_types: dict[str, IESOReserveTypePrices] = field(default_factory=dict)
    # Structure: reserve_types[reserve_type].hourly_prices[hour][interval] = price

    def get_reserve_price(
        self, reserve_type: str, hour: int, interval: int
    ) -> float | None:
        """Get reserve price for specific reserve type, hour, and interval."""
        if reserve_type not in self.reserve_types:
            return None
        return self.reserve_types[reserve_type].get_reserve_price(hour, interval)

    def get_hourly_prices(self, reserve_type: str) -> dict[int, dict[int, float]]:
        """Get all hourly prices for a reserve type."""
        if reserve_type not in self.reserve_types:
            return {}
        return self.reserve_types[reserve_type].hourly_prices.copy()

    def get_reserve_types(self) -> list[str]:
        """Get list of reserve types available for this region."""
        return list(self.reserve_types.keys())


@dataclass(frozen=True, slots=True)
class IESOReservePriceData:
    """Complete reserve prices data for all regions."""

    delivery_date: str
    created_at: datetime
    region_prices: dict[str, IESORegionReservePrice] = field(default_factory=dict)

    def get_region_prices(self, region: str) -> IESORegionReservePrice | None:
        """Get reserve prices for a specific region."""
        return self.region_prices.get(region)

    def get_reserve_price(
        self, region: str, reserve_type: str, hour: int, interval: int
    ) -> float | None:
        """Get reserve price for specific region, reserve type, hour, and interval."""
        region_data = self.get_region_prices(region)
        if region_data is None:
            return None
        return region_data.get_reserve_price(reserve_type, hour, interval)

    def get_regions(self) -> list[str]:
        """Get list of regions available."""
        return list(self.region_prices.keys())

    def get_reserve_types(self, region: str) -> list[str]:
        """Get list of reserve types available for a region."""
        region_data = self.get_region_prices(region)
        if region_data is None:
            return []
        return region_data.get_reserve_types()

    def get_hourly_prices(
        self, region: str, reserve_type: str
    ) -> dict[int, dict[int, float]]:
        """Get hourly prices for a region and reserve type."""
        region_data = self.get_region_prices(region)
        if region_data is None:
            return {}
        return region_data.get_hourly_prices(reserve_type)


class IESOReservePricesClient:
    """Client for fetching IESO Operating Reserve Prices data."""

    def __init__(self, session: aiohttp.ClientSession, timeout: int = 30) -> None:
        """Initialize the client."""
        self._session = session
        self._timeout = aiohttp.ClientTimeout(total=timeout)

    async def fetch(self) -> IESOReservePriceData:
        """Fetch and parse reserve prices data."""
        try:
            async with self._session.get(
                IESO_RESERVE_PRICES_URL, timeout=self._timeout
            ) as resp:
                resp.raise_for_status()
                content = await resp.text()
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise IESOPredispatchError(
                f"Failed to fetch reserve prices: {err}"
            ) from err

        return self._parse_xml(content)

    async def _fetch_xml(self) -> str:
        """Fetch XML content."""
        async with self._session.get(
            IESO_RESERVE_PRICES_URL, timeout=self._timeout
        ) as resp:
            resp.raise_for_status()
            return await resp.text()

    def _parse_xml(self, xml_content: str) -> IESOReservePriceData:
        """Parse reserve prices XML."""
        try:
            root = ET.fromstring(xml_content)
        except ET.ParseError as err:
            raise IESOPredispatchError(f"Invalid XML: {err}") from err

        ns = {"ieso": IESO_LMP_NAMESPACE}

        # Parse metadata
        created_at_elem = root.find(".//ieso:CreatedAt", ns)
        delivery_date_elem = root.find(".//ieso:DELIVERYDATE", ns)

        if not all(
            elem is not None and elem.text is not None and elem.text.strip() != ""
            for elem in [created_at_elem, delivery_date_elem]
        ):
            raise IESOPredispatchError("Required XML elements not found")

        assert created_at_elem is not None and created_at_elem.text
        assert delivery_date_elem is not None and delivery_date_elem.text

        created_at = datetime.fromisoformat(created_at_elem.text)
        delivery_date = delivery_date_elem.text.strip()

        # Parse HourlyPrice elements
        region_prices: dict[str, IESORegionReservePrice] = {}

        for hourly_price in root.findall(".//ieso:HourlyPrice", ns):
            region_elem = hourly_price.find("ieso:Region", ns)
            hour_elem = hourly_price.find("ieso:DeliveryHour", ns)
            interval_elem = hourly_price.find("ieso:Interval", ns)
            type_elem = hourly_price.find("ieso:Type", ns)
            price_elem = hourly_price.find("ieso:Price", ns)
            market_elem = hourly_price.find("ieso:MarketName", ns)

            # Validate required elements and extract text
            if not all(
                elem is not None and elem.text is not None and elem.text.strip() != ""
                for elem in [
                    region_elem,
                    hour_elem,
                    interval_elem,
                    type_elem,
                    price_elem,
                ]
            ):
                continue

            region = region_elem.text.strip()
            try:
                hour = int(hour_elem.text)
                interval = int(interval_elem.text)
                price = float(price_elem.text)
            except (ValueError, TypeError):
                continue

            # Validate ranges
            if not 1 <= hour <= 24:
                continue
            if not 1 <= interval <= 12:  # 5-minute intervals in an hour
                continue

            reserve_type = type_elem.text.strip()

            # Get or create region data
            if region not in region_prices:
                region_prices[region] = IESORegionReservePrice(region=region)

            region_data = region_prices[region]

            # Get or create reserve type data
            if reserve_type not in region_data.reserve_types:
                region_data.reserve_types[reserve_type] = IESOReserveTypePrices(
                    reserve_type=reserve_type
                )

            reserve_type_data = region_data.reserve_types[reserve_type]

            # Initialize hour dict if needed
            if hour not in reserve_type_data.hourly_prices:
                reserve_type_data.hourly_prices[hour] = {}

            # Set the price
            reserve_type_data.hourly_prices[hour][interval] = price

        return IESOReservePriceData(
            delivery_date=delivery_date,
            created_at=created_at,
            region_prices=region_prices,
        )


IESO_RESERVE_PRICES_URL: Final = (
    "https://reports-public.ieso.ca/public/RealtimeORLMP/PUB_RealtimeORLMP.xml"
)
