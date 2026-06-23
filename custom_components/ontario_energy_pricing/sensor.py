"""Sensor platform for Ontario Energy Pricing."""
from __future__ import annotations

import traceback
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, LOGGER
from .coordinator import OntarioEnergyPricingCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Ontario Energy Pricing sensors from a config entry."""
    LOGGER.debug(
        "[SENSOR] async_setup_entry called: entry_id=%s, data=%s",
        entry.entry_id,
        entry.data,
    )
    try:
        coordinator: OntarioEnergyPricingCoordinator = entry.runtime_data
        LOGGER.debug(
            "[SENSOR] Got coordinator from runtime_data: type=%s, last_success=%s",
            type(coordinator).__name__,
            coordinator.last_update_success,
        )
    except Exception as err:
        LOGGER.error(
            "[SENSOR] FAILED to get coordinator from runtime_data: %s\n%s",
            err,
            traceback.format_exc(),
        )
        return

    try:
        entities: list[OntarioEnergyPricingSensor] = [
            OntarioCurrentLMPSensor(coordinator),
            OntarioHourAverageLMPSensor(coordinator),
            OntarioGlobalAdjustmentSensor(coordinator),
            OntarioTotalRateSensor(coordinator),
        ]
        LOGGER.debug(
            "[SENSOR] Created %d entities: %s",
            len(entities),
            [type(e).__name__ for e in entities],
        )
    except Exception as err:
        LOGGER.error(
            "[SENSOR] FAILED to create entity instances: %s\n%s",
            err,
            traceback.format_exc(),
        )
        return

    try:
        async_add_entities(entities)
        LOGGER.debug("[SENSOR] async_add_entities called successfully")
    except Exception as err:
        LOGGER.error(
            "[SENSOR] FAILED in async_add_entities: %s\n%s",
            err,
            traceback.format_exc(),
        )


class OntarioEnergyPricingSensor(CoordinatorEntity):
    """Base class for Ontario Energy Pricing sensors."""

    _attr_has_entity_name = True
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "¢/kWh"
    _attr_device_class = SensorDeviceClass.MONETARY

    def __init__(
        self,
        coordinator: OntarioEnergyPricingCoordinator,
        translation_key: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_translation_key = translation_key
        self._attr_unique_id = f"{DOMAIN}_{translation_key}"
        LOGGER.debug(
            "[SENSOR] Initialized %s: unique_id=%s, translation_key=%s",
            type(self).__name__,
            self._attr_unique_id,
            translation_key,
        )


class OntarioCurrentLMPSensor(OntarioEnergyPricingSensor):
    """Sensor for current LMP price (latest 5-min interval)."""

    _attr_icon = "mdi:lightning-bolt"

    def __init__(self, coordinator: OntarioEnergyPricingCoordinator) -> None:
        """Initialize the current LMP sensor."""
        super().__init__(coordinator, "current_lmp")

    @property
    def native_value(self) -> float | None:
        """Return the current LMP price in ¢/kWh."""
        if self.coordinator.data:
            return self.coordinator.data.current_lmp_kwh

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return sensor attributes."""
        if not self.coordinator.data:
            return {}
        return {
            "lmp_mwh": self.coordinator.data.current_lmp_mwh,
            "delivery_hour": self.coordinator.data.delivery_hour,
            "delivery_date": self.coordinator.data.delivery_date,
            "trade_month": self.coordinator.data.trade_month,
        }


class OntarioHourAverageLMPSensor(OntarioEnergyPricingSensor):
    """Sensor for hourly average LMP."""

    _attr_icon = "mdi:chart-line"

    def __init__(self, coordinator: OntarioEnergyPricingCoordinator) -> None:
        """Initialize the hour average LMP sensor."""
        super().__init__(coordinator, "hour_average_lmp")

    @property
    def native_value(self) -> float | None:
        """Return the hour average LMP price in ¢/kWh."""
        if self.coordinator.data:
            return self.coordinator.data.hour_average_lmp_kwh


class OntarioGlobalAdjustmentSensor(OntarioEnergyPricingSensor):
    """Sensor for Global Adjustment rate."""

    _attr_icon = "mdi:cash"

    def __init__(self, coordinator: OntarioEnergyPricingCoordinator) -> None:
        """Initialize the GA sensor."""
        super().__init__(coordinator, "global_adjustment")

    @property
    def native_value(self) -> float | None:
        """Return the Global Adjustment rate in ¢/kWh."""
        if self.coordinator.data:
            return self.coordinator.data.global_adjustment

    @property
    def extra_state_attributes(self) -> dict[str, str | None]:
        """Return sensor attributes."""
        if not self.coordinator.data:
            return {}
        return {"trade_month": self.coordinator.data.trade_month}


class OntarioTotalRateSensor(OntarioEnergyPricingSensor):
    """Sensor for total rate (LMP + GA + Admin Fee)."""

    _attr_icon = "mdi:scale-balance"

    def __init__(self, coordinator: OntarioEnergyPricingCoordinator) -> None:
        """Initialize the total rate sensor."""
        super().__init__(coordinator, "total_rate")

    @property
    def native_value(self) -> float | None:
        """Calculate total rate from LMP + GA + Admin Fee."""
        if self.coordinator.data:
            return self.coordinator.data.total_rate

    @property
    def extra_state_attributes(self) -> dict[str, float]:
        """Return sensor attributes with component values."""
        if not self.coordinator.data:
            return {}
        return {
            "lmp_rate": self.coordinator.data.current_lmp_kwh,
            "ga_rate": self.coordinator.data.global_adjustment,
            "admin_fee": self.coordinator.data.admin_fee,
        }