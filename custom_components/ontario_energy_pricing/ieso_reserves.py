"""IESO Operating Reserve Prices Client.

Provides real-time operating reserve LMP prices from IESO.
CSV format from RealtimeORLMP feed.
"""

from __future__ import annotations

import asyncio
import csv
import io
from dataclasses import dataclass, field
from datetime import datetime
from typing import Final

import aiohttp

from .const import IESO_LMP_NAMESPACE
from .exceptions import IESOPredispatchError


IESO_RESERVE_PRICES_URL: Final = (
    "https://reports-public.ieso.ca/public/RealtimeORLMP/PUB_RealtimeORLMP.csv"
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

        return self._parse_csv(content)

    def _parse_csv(self, csv_content: str) -> IESOReservePriceData:
        """Parse reserve prices CSV."""
        # Parse the header line to get created_at
        lines = csv_content.strip().split("\n")
        if not lines:
            raise IESOPredispatchError("Empty CSV content")

        # First line: "CREATED AT 2026/06/22 19:07:27 FOR 2026/06/22"
        header_line = lines[0].strip()
        created_at = datetime.now()
        delivery_date = datetime.now().strftime("%Y-%m-%d")

        if header_line.startswith("CREATED AT"):
            # Parse: CREATED AT 2026/06/22 19:07:27 FOR 2026/06/22
            parts = header_line.split()
            if len(parts) >= 5:
                try:
                    created_at_str = f"{parts[2]} {parts[3]}"
                    created_at = datetime.strptime(created_at_str, "%Y/%m/%d %H:%M:%S")
                    delivery_date = parts[5] if len(parts) > 5 else created_at.strftime("%Y-%m-%d")
                except (ValueError, IndexError):
                    pass

        # Parse CSV data (skip header line)
        reader = csv.DictReader(io.StringIO("\n".join(lines[1:])))
        region_prices: dict[str, IESORegionReservePrice] = {}

        for row in reader:
            try:
                delivery_hour = int(row["Delivery Hour"])
                interval = int(row["Interval"])
                region = row["Pricing Location"].strip()

                # Parse reserve prices: 10S, 10N, 30R
                # Columns: LMP 10S, Congestion Price 10S, LMP 10N, Congestion Price 10N, LMP 30R, Congestion Price 30R
                reserve_prices = {
                    "10S": float(row["LMP 10S"]) if row["LMP 10S"] else 0.0,
                    "10N": float(row["LMP 10N"]) if row["LMP 10N"] else 0.0,
                    "30R": float(row["LMP 30R"]) if row["LMP 30R"] else 0.0,
                }

                # Validate ranges
                if not 1 <= delivery_hour <= 24:
                    continue
                if not 1 <= interval <= 12:
                    continue

                # Get or create region data
                if region not in region_prices:
                    region_prices[region] = IESORegionReservePrice(region=region)

                region_data = region_prices[region]

                # Add each reserve type
                for reserve_type, price in reserve_prices.items():
                    if reserve_type not in region_data.reserve_types:
                        region_data.reserve_types[reserve_type] = IESOReserveTypePrices(
                            reserve_type=reserve_type
                        )

                    reserve_type_data = region_data.reserve_types[reserve_type]

                    # Initialize hour dict if needed
                    if delivery_hour not in reserve_type_data.hourly_prices:
                        reserve_type_data.hourly_prices[delivery_hour] = {}

                    # Set the price
                    reserve_type_data.hourly_prices[delivery_hour][interval] = price

            except (ValueError, TypeError, KeyError):
                continue

        return IESOReservePriceData(
            delivery_date=delivery_date,
            created_at=created_at,
            region_prices=region_prices,
        )