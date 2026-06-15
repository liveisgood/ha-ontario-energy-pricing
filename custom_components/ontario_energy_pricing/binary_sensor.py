"""Binary sensor platform for Ontario Energy Pricing.

Provides configurable 'cheapest hours' binary sensors. Each sensor is ON when
the current hour is one of the X cheapest hours in the IESO forecast, and OFF
otherwise.

Users can create multiple sensors with different hour counts via the
integration's Options flow:
  - Pool pump: 16 cheapest hours -> sensor ON during the 16 lowest-price hours
  - EV charger: 8 cheapest hours -> sensor ON during the 8 lowest-price hours
  - AC pre-cool: 4 cheapest hours -> sensor ON during the 4 lowest-price hours

Also provides special binary sensors:
  - Negative price (get paid to consume)
  - Grid stressed (sustained high prices likely)
"""

from __future__ import annotations

from collections import deque

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_CHEAPEST_WINDOWS,
    CONF_WINDOW_HOURS,
    DEFAULT_WINDOW_HOURS,
    DOMAIN,
    LOGGER,
)
from .coordinator import OntarioEnergyPricingCoordinator, OntarioEnergyPricingData


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Ontario Energy Pricing binary sensors from a config entry."""
    coordinator: OntarioEnergyPricingCoordinator = entry.runtime_data

    # Initialize rolling price history for grid stress detection
    if not hasattr(coordinator, "recent_prices"):
        coordinator.recent_prices = deque(maxlen=27)  # ~2 hours at 4.5 min intervals

    # Read cheapest window configs from options (list of dicts with name/hours)
    windows: list[dict] = entry.options.get(CONF_CHEAPEST_WINDOWS, [])

    entities: list[BinarySensorEntity] = []

    # Cheapest hours binary sensors (user-configured)
    for window_config in windows:
        entities.append(OntarioCheapestHoursBinarySensor(coordinator, window_config))

    # Special binary sensors (always available)
    entities.extend(
        [
            OntarioNegativePriceSensor(coordinator),
            OntarioGridStressedSensor(coordinator),
        ]
    )

    async_add_entities(entities)


class OntarioCheapestHoursBinarySensor(
    CoordinatorEntity[OntarioEnergyPricingCoordinator], BinarySensorEntity
):
    """Binary sensor: ON during the X cheapest forecast hours.

    The sensor is ON when the current IESO delivery hour is one of the
    N cheapest hours in the predispatch/day-ahead forecast. Hours need
    not be contiguous -- the sensor simply flips ON/OFF at each hour
    boundary depending on whether that hour made the cheap list.
    """

    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.RUNNING

    def __init__(
        self,
        coordinator: OntarioEnergyPricingCoordinator,
        window_config: dict,
    ) -> None:
        """Initialize the binary sensor.

        Args:
            coordinator: The data update coordinator.
            window_config: Dict with 'name' and 'window_hours' keys.
        """
        super().__init__(coordinator)
        self._window_hours: int = window_config.get(
            CONF_WINDOW_HOURS, DEFAULT_WINDOW_HOURS
        )
        self._window_name: str = window_config.get(
            "name", f"cheapest_{self._window_hours}h"
        )
        self._attr_unique_id = f"{DOMAIN}_cheapest_{self._window_name}"
        self._attr_translation_key = "cheapest_hours"
        self._attr_translation_placeholders = {
            "name": self._window_name,
            "hours": str(self._window_hours),
        }

    @property
    def name(self) -> str:
        """Return the friendly name."""
        return f"Cheapest {self._window_hours}h ({self._window_name})"

    def is_on(self) -> bool | None:
        """Return True if currently in one of the cheapest forecast hours."""
        data: OntarioEnergyPricingData | None = self.coordinator.data
        if not data:
            return None

        current_hour = data.delivery_hour  # IESO convention 1-24

        # Try today's forecast first
        if data.forecast_today is not None:
            return data.forecast_today.is_in_cheapest_hours(
                current_hour, self._window_hours
            )

        # Fall back to tomorrow's forecast
        if data.forecast_tomorrow is not None:
            return data.forecast_tomorrow.is_in_cheapest_hours(
                current_hour, self._window_hours
            )

        return None

    @property
    def extra_state_attributes(self) -> dict[str, object] | None:
        """Return forecast details as attributes for automation debugging."""
        data: OntarioEnergyPricingData | None = self.coordinator.data
        if not data:
            return None

        forecast = data.forecast_today or data.forecast_tomorrow
        if forecast is None:
            return {"forecast_available": False}

        cheapest = forecast.cheapest_hours(self._window_hours)

        # Build hourly price list sorted by hour
        hourly_prices = {
            f"hour_{h.hour:02d}": h.zonal_price_kwh for h in forecast.hours
        }

        # Calculate average price of the cheapest hours
        cheapest_hour_data = [h for h in forecast.hours if h.hour in cheapest]
        avg_cheapest = (
            round(
                sum(h.zonal_price_kwh for h in cheapest_hour_data)
                / len(cheapest_hour_data),
                4,
            )
            if cheapest_hour_data
            else None
        )

        return {
            "forecast_available": True,
            "forecast_date": forecast.delivery_date,
            "window_hours": self._window_hours,
            "cheapest_hours": sorted(cheapest),
            "avg_cheapest_price_cents": avg_cheapest,
            "current_delivery_hour": data.delivery_hour,
            "forecast_min_price": forecast.min_price_hour.zonal_price_kwh
            if forecast.min_price_hour
            else None,
            "forecast_max_price": forecast.max_price_hour.zonal_price_kwh
            if forecast.max_price_hour
            else None,
            "forecast_avg_price": round(forecast.average_price_kwh, 4),
            **hourly_prices,
        }

    @property
    def icon(self) -> str:
        """Return icon based on state."""
        return "mdi:power-plug-outline" if self.is_on else "mdi:power-plug-off-outline"


class OntarioNegativePriceSensor(
    CoordinatorEntity[OntarioEnergyPricingCoordinator], BinarySensorEntity
):
    """Binary sensor: ON when current LMP price is negative."""

    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.RUNNING

    def __init__(self, coordinator: OntarioEnergyPricingCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_price_negative"
        self._attr_translation_key = "price_negative"

    @property
    def name(self) -> str:
        return "Negative Price (Get Paid)"

    def is_on(self) -> bool | None:
        data: OntarioEnergyPricingData | None = self.coordinator.data
        if not data:
            return None
        result = data.current_lmp_kwh < 0
        LOGGER.debug(
            "Negative price check: current=%.2f -> %s",
            data.current_lmp_kwh,
            result,
        )
        return result

    @property
    def icon(self) -> str:
        return "mdi:cash-multiple" if self.is_on else "mdi:cash-off"

    @property
    def extra_state_attributes(self) -> dict[str, object] | None:
        data = self.coordinator.data
        if not data:
            return None
        return {
            "current_price_cents_per_kwh": round(data.current_lmp_kwh, 2),
        }


class OntarioGridStressedSensor(
    CoordinatorEntity[OntarioEnergyPricingCoordinator], BinarySensorEntity
):
    """Binary sensor: ON when grid stress indicators suggest sustained high prices.

    Uses RELATIVE signals (no fixed thresholds) that work year-round:
    - Gas is the marginal price setter (>50% of total = gas-dominated pricing)
    - Low renewables (<20%) = less zero-carbon competition for gas
    - Price trending up vs recent history (rolling percentile)
    - High carbon intensity (>300 gCO2/kWh = gas-heavy grid)
    """

    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, coordinator: OntarioEnergyPricingCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_grid_stressed"
        self._attr_translation_key = "grid_stressed"

    @property
    def name(self) -> str:
        return "Grid Stressed (High Prices Likely)"

    def is_on(self) -> bool | None:
        data: OntarioEnergyPricingData | None = self.coordinator.data
        if not data:
            return None

        if not data.fuel_mix:
            return None

        # Signal 1: Gas is dominant marginal setter (>50% of generation)
        gas_dominant = data.fuel_mix.gas_mw > (data.fuel_mix.total_mw * 0.5)

        # Signal 2: Low renewable competition for gas (<20% zero-carbon)
        renewable_low = data.fuel_mix.renewable_percentage < 20

        # Signal 3: High carbon intensity (>300 gCO2/kWh = gas-heavy)
        carbon_high = data.fuel_mix.carbon_intensity_gco2_per_kwh > 300

        # Signal 4: Price trending up vs recent history (coordinator rolling avg)
        price_trending_up = self._is_price_trending_up(data)

        # Grid stressed if: (gas dominant OR high carbon) AND (low renewable OR price trending up)
        is_stressed = (gas_dominant or carbon_high) and (
            renewable_low or price_trending_up
        )

        # Debug logging
        LOGGER.debug(
            "Grid stressed check: price=%.2fc gas=%.0fMW (%.1f%%) dominant=%s "
            "renewable=%.1f%% low=%s carbon=%.0f high=%s trending=%s -> stressed=%s",
            data.current_lmp_kwh,
            data.fuel_mix.gas_mw,
            (data.fuel_mix.gas_mw / data.fuel_mix.total_mw * 100)
            if data.fuel_mix.total_mw > 0
            else 0,
            gas_dominant,
            data.fuel_mix.renewable_percentage,
            renewable_low,
            data.fuel_mix.carbon_intensity_gco2_per_kwh,
            carbon_high,
            price_trending_up,
            is_stressed,
        )

        return is_stressed

    def _is_price_trending_up(self, data: OntarioEnergyPricingData) -> bool:
        """Check if price is trending up vs recent coordinator history."""
        # Use coordinator's rolling price history (last ~2 hours = ~27 intervals)
        recent_prices = getattr(self.coordinator, "recent_prices", None)
        if not recent_prices or len(recent_prices) < 10:
            return False

        # Compare current price to median of recent
        median_recent = sorted(recent_prices)[len(recent_prices) // 2]
        return data.current_lmp_kwh > median_recent * 1.2  # 20% above median

    @property
    def icon(self) -> str:
        return "mdi:flash-alert" if self.is_on else "mdi:flash-off"

    @property
    def extra_state_attributes(self) -> dict[str, object] | None:
        data = self.coordinator.data
        if not data or not data.fuel_mix:
            return None
        return {
            "current_price_cents_per_kwh": round(data.current_lmp_kwh, 2),
            "gas_generation_mw": round(data.fuel_mix.gas_mw, 0),
            "gas_percentage": round(
                data.fuel_mix.gas_mw / data.fuel_mix.total_mw * 100, 1
            )
            if data.fuel_mix.total_mw > 0
            else 0,
            "renewable_percentage": round(data.fuel_mix.renewable_percentage, 1),
            "carbon_intensity_gco2_per_kwh": round(
                data.fuel_mix.carbon_intensity_gco2_per_kwh, 1
            ),
            "total_generation_mw": round(data.fuel_mix.total_mw, 0),
            "gas_dominant": data.fuel_mix.gas_mw > (data.fuel_mix.total_mw * 0.5)
            if data.fuel_mix.total_mw > 0
            else False,
            "carbon_high": data.fuel_mix.carbon_intensity_gco2_per_kwh > 300,
            "renewable_low": data.fuel_mix.renewable_percentage < 20,
            "price_trending_up": self._is_price_trending_up(data) if data else False,
        }
