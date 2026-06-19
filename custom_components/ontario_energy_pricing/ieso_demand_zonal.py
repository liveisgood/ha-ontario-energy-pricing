"""IESO Demand Zonal Client.

Provides real-time demand data by zone from IESO.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Final

import aiohttp

from .exceptions import IESOPredispatchError


IESO_DEMAND_ZONAL_URL: Final = (
    "https://reports-public.ieso.ca/public/RealtimeDemandZonal/"
    "PUB_RealtimeDemandZonal.csv"
)


@dataclass(frozen=True, slots=True)
class IESODemandZoneData:
    """Demand data for a specific zone."""

    zone: str
    timestamp: datetime
    demand_mw: float


@dataclass(frozen=True, slots=True)
class IESODemandZonalData:
    """Complete demand zonal data."""

    demand_data: list[IESODemandZoneData] = field(default_factory=list)

    def get_demand_by_zone(self, zone: str) -> list[IESODemandZoneData]:
        """Get demand data for a specific zone."""
        return [d for d in self.demand_data if d.zone.upper() == zone.upper()]

    def get_latest_demand_by_zone(self, zone: str) -> IESODemandZoneData | None:
        """Get the most recent demand data for a specific zone."""
        zone_data = self.get_demand_by_zone(zone)
        if not zone_data:
            return None
        return max(zone_data, key=lambda x: x.timestamp)

    def get_zones(self) -> list[str]:
        """Get list of zones available."""
        return list({d.zone for d in self.demand_data})


class IESODemandZonalClient:
    """Client for fetching IESO Demand Zonal data."""

    def __init__(self, session: aiohttp.ClientSession, timeout: int = 30) -> None:
        """Initialize the client."""
        self._session = session
        self._timeout = aiohttp.ClientTimeout(total=timeout)

    async def fetch(self) -> IESODemandZonalData:
        """Fetch and parse demand zonal data."""
        try:
            async with self._session.get(
                IESO_DEMAND_ZONAL_URL, timeout=self._timeout
            ) as resp:
                resp.raise_for_status()
                content = await resp.text()
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise IESOPredispatchError(f"Failed to fetch demand zonal data: {err}") from err

        return self._parse_csv(content)

    async def _fetch_csv(self) -> str:
        """Fetch CSV content."""
        async with self._session.get(
            IESO_DEMAND_ZONAL_URL, timeout=self._timeout
        ) as resp:
            resp.raise_for_status()
            return await resp.text()

    def _parse_csv(self, csv_content: str) -> IESODemandZonalData:
        """Parse demand zonal CSV."""
        demand_data: list[IESODemandZoneData] = []

        # Parse CSV
        lines = csv_content.strip().split('\n')
        if len(lines) < 2:  # Need at least header and one data row
            return IESODemandZonalData(demand_data=demand_data)

        # Parse header
        header = lines[0].strip()
        expected_columns = ['Date Time', 'Zone', 'Demand (MW)']
        # Note: Being lenient with header validation since IESO format may vary

        # Parse data rows
        for line in lines[1:]:  # Skip header
            line = line.strip()
            if not line:
                continue

            try:
                parts = [part.strip() for part in line.split(',')]
                if len(parts) < 3:
                    continue

                # Parse timestamp (format: "YYYY-MM-DD HH:MM:SS")
                # Handle different possible column arrangements
                if len(parts) == 3:
                    # Format: Date Time, Zone, Demand (MW)
                    timestamp_str = parts[0]
                    zone = parts[1]
                    demand_str = parts[2]
                elif len(parts) >= 4:
                    # Format: Date, Time, Zone, Demand (MW) or similar
                    timestamp_str = f"{parts[0]} {parts[1]}"
                    zone = parts[2]
                    demand_str = parts[3]
                else:
                    continue

                # Parse timestamp
                # Try common IESO timestamp formats
                timestamp = None
                for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y/%m/%d %H:%M:%S"):
                    try:
                        timestamp = datetime.strptime(timestamp_str, fmt)
                        break
                    except ValueError:
                        continue

                if timestamp is None:
                    # If we can't parse the timestamp, skip this row
                    continue

                # Parse zone
                zone = zone.strip()

                # Parse demand
                try:
                    demand_mw = float(demand_str)
                except (ValueError, TypeError):
                    continue

                demand_data.append(
                    IESODemandZoneData(
                        zone=zone,
                        timestamp=timestamp,
                        demand_mw=demand_mw,
                    )
                )
            except (ValueError, IndexError):
                # Skip malformed rows
                continue

        return IESODemandZonalData(demand_data=demand_data)