"""Data models for the Ontario Energy Pricing integration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class GlobalAdjustment:
    """Global Adjustment rate from IESO."""

    rate: float  # $ (not ¢) - straight from XML
    trade_month: str  # YYYY-MM
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

    rate: float  # ¢/kWh

    def __post_init__(self) -> None:
        """Validate the admin fee."""
        if self.rate < 0:
            raise ValueError(f"Admin fee cannot be negative: {self.rate}")
