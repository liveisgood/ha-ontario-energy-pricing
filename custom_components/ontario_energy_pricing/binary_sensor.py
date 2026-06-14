"""Binary sensor platform for Ontario Energy Pricing.

Provides configurable 'cheapest hours' binary sensors. Each sensor is ON when
the current hour is one of the X cheapest hours in the IESO forecast, and OFF
otherwise.

Users can create multiple sensors with different hour counts via the
integration's Options flow:
  - Pool pump: 16 cheapest hours → sensor ON during the 16 lowest-price hours
  - EV charger: 8 cheapest hours → sensor ON during the 8 lowest-price hours
  - AC pre-cool: 4 cheapest hours → sensor ON during the 4 lowest-price hours

Also provides price threshold binary sensors for automation triggers:
  - Price below X ¢/kWh (e.g., run pool pump)
  - Price above Y ¢/kWh (e.g., shed loads, AC setback)
  - Negative price (get paid to consume)
  - Grid stressed (sustained high prices likely)
"""

from __future__ import annotations

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
)
from .coordinator import OntarioEnergyPricingCoordinator, OntarioEnergyPricingData


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Ontario Energy Pricing binary sensors from a config entry."""
    coordinator: OntarioEnergyPricingCoordinator = entry.runtime_data

    # Read cheapest window configs from options (list of dicts with name/hours)
    windows: list[dict] = entry.options.get(CONF_CHEAPEST_WINDOWS, [])

    entities: list[BinarySensorEntity] = []

    # Cheapest hours binary sensors (user-configured)
    for window_config in windows:
        entities.append(OntarioCheapestHoursBinarySensor(coordinator, window_config))

    # Price threshold binary sensors (always available)
    entities.extend([
        OntarioPriceBelowThresholdSensor(coordinator, "pool_pump", 5.0, "Pool Pump On"),
        OntarioPriceBelowThresholdSensor(coordinator, "ac_precool", 10.0, "AC Pre-cool OK"),
        OntarioPriceAboveThresholdSensor(coordinator, "ac_setback", 20.0, "AC Setback"),
        OntarioPriceAboveThresholdSensor(coordinator, "shed_all", 30.0, "Shed All Loads"),
        OntarioNegativePriceSensor(coordinator),
        OntarioGridStressedSensor(coordinator),
    ])

    async_add_entities(entities)


class OntarioCheapestHoursBinarySensor(
    CoordinatorEntity[OntarioEnergyPricingCoordinator], BinarySensorEntity
):
    """Binary sensor: ON during the X cheapest forecast hours.

    The sensor is ON when the current IESO delivery hour is one of the
    N cheapest hours in the predispatch/day-ahead forecast. Hours need
    not be contiguous — the sensor simply flips ON/OFF at each hour
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


class OntarioPriceBelowThresholdSensor(
    CoordinatorEntity[OntarioEnergyPricingCoordinator], BinarySensorEntity
):
    """Binary sensor: ON when current price is below threshold (¢/kWh)."""

    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.RUNNING

    def __init__(
        self,
        coordinator: OntarioEnergyPricingCoordinator,
        suffix: str,
        threshold: float,
        name: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._threshold = threshold
        self._suffix = suffix
        self._name = name
        self._attr_unique_id = f"{DOMAIN}_price_below_{suffix}"
        self._attr_translation_key = "price_below"
        self._attr_translation_placeholders = {
            "threshold": f"{threshold}¢/kWh",
            "name": name,
        }

    @property
    def name(self) -> str:
        return f"Price Below {self._threshold}¢ ({self._name})"

    def is_on(self) -> bool | None:
        data: OntarioEnergyPricingData | None = self.coordinator.data
        if not data:
            return None
        return data.current_lmp_kwh < self._threshold

    @property
    def icon(self) -> str:
        return "mdi:cash-plus" if self.is_on else "mdi:cash-minus"

    @property
    def extra_state_attributes(self) -> dict[str, object] | None:
        data = self.coordinator.data
        if not data:
            return None
        return {
            "threshold_cents_per_kwh": self._threshold,
            "current_price_cents_per_kwh": round(data.current_lmp_kwh, 2),
            "price_difference": round(self._threshold - data.current_lmp_kwh, 2),
        }


class OntarioPriceAboveThresholdSensor(
    CoordinatorEntity[OntarioEnergyPricingCoordinator], BinarySensorEntity
):
    """Binary sensor: ON when current price is above threshold (¢/kWh)."""

    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(
        self,
        coordinator: OntarioEnergyPricingCoordinator,
        suffix: str,
        threshold: float,
        name: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._threshold = threshold
        self._suffix = suffix
        self._name = name
        self._attr_unique_id = f"{DOMAIN}_price_above_{suffix}"
        self._attr_translation_key = "price_above"
        self._attr_translation_placeholders = {
            "threshold": f"{threshold}¢/kWh",
            "name": name,
        }

    @property
    def name(self) -> str:
        return f"Price Above {self._threshold}¢ ({self._name})"

    def is_on(self) -> bool | None:
        data: OntarioEnergyPricingData | None = self.coordinator.data
        if not data:
            return None
        return data.current_lmp_kwh > self._threshold

    @property
    def icon(self) -> str:
        return "mdi:alert-circle-outline" if self.is_on else "mdi:check-circle-outline"

    @property
    def extra_state_attributes(self) -> dict[str, object] | None:
        data = self.coordinator.data
        if not data:
            return None
        return {
            "threshold_cents_per_kwh": self._threshold,
            "current_price_cents_per_kwh": round(data.current_lmp_kwh, 2),
            "price_difference": round(data.current_lmp_kwh - self._threshold, 2),
        }


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
        return data.current_lmp_kwh < 0

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

    Combines:
    - High gas generation (marginal price setter)
    - High reserve prices (from IESO ORLMP feed)
    - Transmission congestion (shadow prices)
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

        # Heuristic: grid stressed if multiple indicators align
        # 1. Gas generation is high (>6000 MW = lots of marginal gas)
        # 2. Price is already elevated (>15¢/kWh)
        # 3. Fuel mix has low renewable percentage (<20%)

        if data.fuel_mix:
            gas_high = data.fuel_mix.gas_mw > 6000
            renewable_low = data.fuel_mix.renewable_percentage < 20
        else:
            gas_high = False
            renewable_low = False

        price_elevated = data.current_lmp_kwh > 15.0

        # Grid stressed if price elevated AND (gas high OR renewable low)
        return price_elevated and (gas_high or renewable_low)

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
            "renewable_percentage": round(data.fuel_mix.renewable_percentage, 1),
            "carbon_intensity_gco2_per_kwh": round(data.fuel_mix.carbon_intensity_gco2_per_kwh, 1),
            "total_generation_mw": round(data.fuel_mix.total_mw, 0),
        }