"""IESO Demand Zonal Client.

Provides real-time demand data by zone from IESO.
Real feed format: CSV with columns Date,Hour,Interval,Ontario Demand,NORTHWEST,NORTHEAST,...
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

# Known IESO zones from the CSV column headers
IESO_ZONE_COLUMNS: Final = [
    "NORTHWEST",
    "NORTHEAST",
    "OTTAWA",
    "EAST",
    "TORONTO",
    "ESSA",
    "BRUCE",
    "SOUTHWEST",
    "NIAGARA",
    "WEST",
]


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

    def _parse_csv(self, csv_content: str) -> IESODemandZonalData:
        """Parse demand zonal CSV.

        Real IESO format (first 4 lines are header):
          Line 0: "Ontario Real-Time 5 Minute Zonal Demand Report"
          Line 1: " CREATED AT YYYY/MM/DD HH:MM:SS "
          Line 2: "FOR YYYY"
          Line 3: "Date,Hour,Interval,Ontario Demand,NORTHWEST,NORTHEAST,..."
          Line 4+: data rows
        """
        demand_data: list[IESODemandZoneData] = []

        lines = csv_content.strip().split('\n')
        if len(lines) < 5:  # Need at least 4 header lines + 1 data row
            return IESODemandZonalData(demand_data=demand_data)

        # Line 3 is the CSV column header
        header_line = lines[3].strip().replace('\r', '')
        columns = [c.strip() for c in header_line.split(',')]

        # Find which column indices correspond to zone columns
        zone_column_indices: dict[str, int] = {}
        for idx, col in enumerate(columns):
            col_upper = col.upper()
            if col_upper in [z.upper() for z in IESO_ZONE_COLUMNS]:
                zone_column_indices[col_upper] = idx

        if not zone_column_indices:
            # Fallback: try to find zone columns dynamically
            # Known zones are columns 4-13 (0-indexed), but headers may vary
            known_zones = [z.upper() for z in IESO_ZONE_COLUMNS]
            for idx, col in enumerate(columns):
                if col.upper() in known_zones:
                    zone_column_indices[col.upper()] = idx

        if not zone_column_indices:
            return IESODemandZonalData(demand_data=demand_data)

        # Parse data rows (start from line 4)
        for line in lines[4:]:
            line = line.strip().replace('\r', '')
            if not line:
                continue

            parts = [p.strip() for p in line.split(',')]
            if len(parts) <= max(zone_column_indices.values()):
                continue

            # Parse date, hour, interval
            date_str = parts[0]  # "YYYY-MM-DD"
            try:
                hour = int(parts[1])
                interval = int(parts[2])
            except (ValueError, IndexError):
                continue

            # Build timestamp: IESO hour 1 = 00:00-01:00
            # Use the start of the interval as the timestamp
            try:
                base_date = datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                continue

            # IESO hours are 1-24, subtract 1 to get 0-23
            minutes = (hour - 1) * 60 + (interval - 1) * 5
            from datetime import timedelta
            timestamp = base_date + timedelta(minutes=minutes)

            # Extract demand for each zone
            for zone_name_upper, col_idx in zone_column_indices.items():
                try:
                    demand_str = parts[col_idx].strip()
                    if not demand_str:
                        continue
                    demand_mw = float(demand_str)
                except (ValueError, IndexError):
                    continue

                demand_data.append(
                    IESODemandZoneData(
                        zone=zone_name_upper,
                        timestamp=timestamp,
                        demand_mw=demand_mw,
                    )
                )

        return IESODemandZonalData(demand_data=demand_data)
