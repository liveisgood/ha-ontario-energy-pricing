"""Data models for the Ontario Energy Pricing integration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from statistics import mean
from typing import Final

from .const import DEFAULT_ZONE


@dataclass(frozen=True, slots=True)
class LMPDataPoint:
    """A single LMP data point at a specific time."""

    timestamp: datetime
    price: float

    def __post_init__(self) -> None:
        """Validate the data point."""
        if self.price < 0:
            raise ValueError(f"Price cannot be negative: {self.price}")
        if self.timestamp.tzinfo is None:
            raise ValueError("Timestamp must be timezone-aware")


@dataclass(frozen=True, slots=True)
class LMPCurrentPrice:
    """Current LMP price with metadata."""

    price: float
    timestamp: datetime
    zone: str
    previous_price: float | None = None

    def __post_init__(self) -> None:
        """Validate the current price."""
        if self.price < 0:
            raise ValueError(f"Price cannot be negative: {self.price}")
        if self.timestamp.tzinfo is None:
            raise ValueError("Timestamp must be timezone-aware")
        if self.previous_price is not None and self.previous_price < 0:
            raise ValueError(
                f"Previous price cannot be negative: {self.previous_price}"
            )


@dataclass(frozen=True, slots=True)
class LMPHistoricalData:
    """Historical LMP data for a 24-hour period."""

    data_points: list[LMPDataPoint]
    zone: str = DEFAULT_ZONE

    _MINUTES_PER_INTERVAL: Final = 30
    _INTERVALS_PER_DAY: Final = 48

    def __post_init__(self) -> None:
        """Validate the historical data."""
        object.__setattr__(
            self,
            "data_points",
            sorted(self.data_points, key=lambda x: x.timestamp),
        )

    def aggregate_to_30min(self) -> list[tuple[datetime, float]]:
        """Aggregate 5-minute data points into 30-minute averages."""
        if not self.data_points:
            return []

        buckets: dict[datetime, list[float]] = {}

        for point in self.data_points:
            minutes_since_hour = point.timestamp.minute % self._MINUTES_PER_INTERVAL
            bucket_start = point.timestamp - timedelta(minutes=minutes_since_hour)
            bucket_start = bucket_start.replace(second=0, microsecond=0)

            if bucket_start not in buckets:
                buckets[bucket_start] = []
            buckets[bucket_start].append(point.price)

        intervals = []
        for bucket_start in sorted(buckets.keys()):
            prices = buckets[bucket_start]
            if prices:
                avg_price = mean(prices)
                intervals.append((bucket_start, avg_price))

        return intervals

    def calculate_24h_average(self) -> float:
        """Calculate the average price over the entire 24-hour period."""
        if not self.data_points:
            raise ValueError("No data points available")
        return mean(p.price for p in self.data_points)


@dataclass(frozen=True, slots=True)
class GlobalAdjustment:
    """Global Adjustment rate from IESO."""

    rate: float
    trade_month: str
    last_updated: datetime

    def __post_init__(self) -> None:
        """Validate the global adjustment data."""
        if self.rate < 0:
            raise ValueError(f"Rate cannot be negative: {self.rate}")
        if self.last_updated.tzinfo is None:
            raise ValueError("last_updated must be timezone-aware")

        # Validate trade_month format (YYYY-MM)
        try:
            year, month = self.trade_month.split("-")
            if len(year) != 4 or len(month) != 2:
                raise ValueError("Invalid format")
            int(year)
            int(month)
        except ValueError as err:
            raise ValueError(
                f"Invalid trade_month format: {self.trade_month}. "
                f"Expected YYYY-MM, e.g., 2026-04"
            ) from err


@dataclass(frozen=True, slots=True)
class AdminFeeConfig:
    """Administrative fee configuration."""

    rate: float

    def __post_init__(self) -> None:
        """Validate the admin fee."""
        if self.rate < 0:
            raise ValueError(f"Admin fee cannot be negative: {self.rate}")
