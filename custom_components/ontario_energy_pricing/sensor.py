"""Sensor platform for Ontario Energy Pricing."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.sensor import (  # type: ignore
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.core import HomeAssistant  # type: ignore
from homeassistant.helpers.entity_platform import AddEntitiesCallback  # type: ignore
from homeassistant.helpers.typing import ConfigEntryType  # type: ignore
from homeassistant.helpers.update_coordinator import CoordinatorEntity  # type: ignore

from .const import (
    CURRENCY_CAD,
    DOMAIN,
    UNIT_KWH,
)
from .coordinator import OntarioEnergyPricingCoordinator

if TYPE_CHECKING:
    pass  # type: ignore


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntryType,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Ontario Energy Pricing sensors from a config entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]

    entities: list[SensorEntity] = [
        OntarioCurrentLMPSensor(coordinator),
        OntarioHourAverageLMPSensor(coordinator),
        OntarioGlobalAdjustmentSensor(coordinator),
        OntarioTotalRateSensor(coordinator),
    ]
    async_add_entities(entities)


class OntarioEnergyPricingSensor(CoordinatorEntity, SensorEntity):
    """Base class for Ontario Energy Pricing sensors."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = f"{CURRENCY_CAD}{UNIT_KWH}"

    def __init__(
        self,
        coordinator: OntarioEnergyPricingCoordinator,
        translation_key: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_translation_key = translation_key
        self._attr_unique_id = f"{DOMAIN}_{translation_key}"


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
        return None

    @property
    def extra_state_attributes(self) -> dict[str, float | str | None]:
        """Return sensor attributes."""
        attrs: dict[str, float | str | None] = {}
        if self.coordinator.data:
            attrs["lmp_mwh"] = self.coordinator.data.current_lmp_mwh
            attrs["delivery_hour"] = self.coordinator.data.delivery_hour
            attrs["delivery_date"] = self.coordinator.data.delivery_date
            attrs["trade_month"] = self.coordinator.data.trade_month
        return attrs


class OntarioHourAverageLMPSensor(OntarioEnergyPricingSensor):
    """Sensor for hourly average LMP."""

    _attr_icon = "mdi:chart-line"

    def __init__(self, coordinator: OntarioEnergyPricingCoordinator) -> None:
        """Initialize the hour average LMP sensor."""
        super().__init__(coordinator, "hour_average_lmp")

    @property
    def native_value(self) -> float | None:
        """Return the current LMP price in ¢/kWh."""
        if self.coordinator.data:
            return self.coordinator.data.hour_average_lmp_kwh
        return None


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
        return None

    @property
    def extra_state_attributes(self) -> dict[str, str | None]:
        """Return sensor attributes."""
        attrs: dict[str, str | None] = {}
        if self.coordinator.data:
            attrs["trade_month"] = self.coordinator.data.trade_month
        return attrs


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
        return None

    @property
    def extra_state_attributes(self) -> dict[str, float | None]:
        """Return sensor attributes with component values."""
        if self.coordinator.data:
            return {
                "lmp_rate": self.coordinator.data.current_lmp_kwh,
                "ga_rate": self.coordinator.data.global_adjustment,
                "admin_fee": self.coordinator.data.admin_fee,
            }
        return {}
