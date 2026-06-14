"""Data models for the Ontario Energy Pricing integration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class GlobalAdjustment:
    """Global Adjustment rate from IESO."""

    rate: float  # $/MWh - straight from IESO XML (FirstEstimateRate)
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
        except ValueError as err:
            raise ValueError(
                f"Invalid trade_month format: {self.trade_month}. "
                f"Expected YYYY-MM, e.g., 2026-04"
            ) from err


@dataclass(frozen=True, slots=True)
class AdminFeeConfig:
    """Administrative fee config."""

    rate: float  # ¢/kWh

    def __post_init__(self) -> None:
        """Validate the admin fee."""
        if self.rate < 0:
            raise ValueError(f"Admin fee cannot be negative: {self.rate}")


@dataclass(frozen=True, slots=True)
class VGForecastData:
    """Variable Generation (Solar/Wind) forecast data."""

    forecast_timestamp: datetime
    solar_forecast_mw: dict[int, float]  # hour (1-24) -> MW
    wind_forecast_mw: dict[int, float]  # hour (1-24) -> MW

    def total_vg_mw(self, hour: int) -> float:
        """Total VG forecast for a specific hour."""
        return self.solar_forecast_mw.get(hour, 0.0) + self.wind_forecast_mw.get(
            hour, 0.0
        )

    def is_high_vg_hour(self, hour: int, threshold_mw: float = 1000.0) -> bool:
        """Check if hour has high variable generation."""
        return self.total_vg_mw(hour) >= threshold_mw

    def negative_price_probability(self, hour: int) -> float:
        """
        Estimate probability of negative prices based on VG forecast.

        Heuristic based on VG level and time of day.
        """
        vg_mw = self.total_vg_mw(hour)

        if vg_mw >= 3000:
            base_prob = 0.7
        elif vg_mw >= 2000:
            base_prob = 0.4
        elif vg_mw >= 1000:
            base_prob = 0.15
        else:
            base_prob = 0.02

        # Adjust for hour (shoulder hours more likely negative)
        if 2 <= hour <= 5:  # Overnight minimum demand
            base_prob *= 1.5
        elif 10 <= hour <= 16:  # Solar peak hours
            base_prob *= 1.3

        return min(base_prob, 0.95)


@dataclass(frozen=True, slots=True)
class FuelMixData:
    """Real-time generator output by fuel type."""

    timestamp: datetime
    nuclear_mw: float = 0.0
    hydro_mw: float = 0.0
    wind_mw: float = 0.0
    solar_mw: float = 0.0
    gas_mw: float = 0.0
    biofuel_mw: float = 0.0
    other_mw: float = 0.0

    @property
    def total_mw(self) -> float:
        """Total generation (MW)."""
        return (
            self.nuclear_mw
            + self.hydro_mw
            + self.wind_mw
            + self.solar_mw
            + self.gas_mw
            + self.biofuel_mw
            + self.other_mw
        )

    @property
    def renewable_mw(self) -> float:
        """Zero-carbon generation (MW)."""
        return (
            self.nuclear_mw
            + self.hydro_mw
            + self.wind_mw
            + self.solar_mw
            + self.biofuel_mw
        )

    @property
    def thermal_mw(self) -> float:
        """Thermal generation (MW)."""
        return self.gas_mw + self.other_mw

    @property
    def renewable_percentage(self) -> float:
        """Percentage from zero-carbon sources."""
        if self.total_mw == 0:
            return 0.0
        return (self.renewable_mw / self.total_mw) * 100

    @property
    def carbon_intensity_gco2_per_kwh(self) -> float:
        """Estimated grid carbon intensity (gCO2/kWh)."""
        emission_factors = {
            "nuclear": 12,
            "hydro": 24,
            "wind": 11,
            "solar": 41,
            "biofuel": 230,
            "gas": 400,
            "other": 500,
        }
        if self.total_mw == 0:
            return 0.0
        total_gco2 = (
            self.nuclear_mw * emission_factors["nuclear"]
            + self.hydro_mw * emission_factors["hydro"]
            + self.wind_mw * emission_factors["wind"]
            + self.solar_mw * emission_factors["solar"]
            + self.biofuel_mw * emission_factors["biofuel"]
            + self.gas_mw * emission_factors["gas"]
            + self.other_mw * emission_factors["other"]
        )
        return total_gco2 / self.total_mw


@dataclass(frozen=True, slots=True)
class PriceThresholds:
    """Configurable price thresholds for automation triggers."""

    pool_pump_on_below: float = 5.0  # ¢/kWh - turn pool pump ON below this
    ac_precool_below: float = 10.0  # ¢/kWh - allow AC pre-cool below this
    ac_setback_above: float = 20.0  # ¢/kWh - setback AC above this
    shed_all_above: float = 30.0  # ¢/kWh - shed all discretionary loads above this
