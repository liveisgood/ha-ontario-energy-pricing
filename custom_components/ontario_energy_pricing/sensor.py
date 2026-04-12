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
    ATTR_PREVIOUS_RATE,
    ATTR_TIMESTAMP,
    ATTR_TRADE_MONTH,
    ATTR_ZONE,
    CURRENCY_CAD,
    DOMAIN,
    SENSOR_GLOBAL_ADJUSTMENT,
    SENSOR_LMP_24H_AVG,
    SENSOR_LMP_CURRENT,
    SENSOR_TOTAL_RATE,
    UNIT_KWH,
)
from .coordinator import (
    GlobalAdjustmentCoordinator,
    LMP24hAverageCoordinator,
    LMPCoordinator,
)

if TYPE_CHECKING:
    pass  # type: ignore


def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntryType,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Ontario Energy Pricing sensors from a config entry."""
    entry_data = hass.data[DOMAIN][config_entry.entry_id]
    api_key = entry_data["api_key"]
    zone = entry_data["zone"]
    admin_fee = entry_data["admin_fee"]

    # Create coordinators
    lmp_coordinator = LMPCoordinator(hass, api_key, zone)
    lmp_24h_coordinator = LMP24hAverageCoordinator(hass, api_key, zone)
    ga_coordinator = GlobalAdjustmentCoordinator(hass)

    # Store coordinators for service access
    hass.data[DOMAIN][config_entry.entry_id]["coordinators"] = [
        lmp_coordinator,
        lmp_24h_coordinator,
        ga_coordinator,
    ]

    # Create sensors
    entities: list[SensorEntity] = [
        OntarioLMPCurrentPriceSensor(lmp_coordinator),
        OntarioLMP24hAverageSensor(lmp_24h_coordinator),
        OntarioGlobalAdjustmentSensor(ga_coordinator),
        OntarioTotalRateSensor(lmp_coordinator, ga_coordinator, admin_fee),
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
        coordinator: LMPCoordinator
        | LMP24hAverageCoordinator
        | GlobalAdjustmentCoordinator,
        translation_key: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_translation_key = translation_key
        self._attr_unique_id = f"{DOMAIN}_{translation_key}"


class OntarioLMPCurrentPriceSensor(OntarioEnergyPricingSensor):
    """Sensor for current LMP price."""

    _attr_icon = "mdi:lightning-bolt"

    def __init__(self, coordinator: LMPCoordinator) -> None:
        """Initialize the current LMP sensor."""
        super().__init__(coordinator, SENSOR_LMP_CURRENT)
        self._lmp_coordinator = coordinator

    @property
    def native_value(self) -> float | None:
        """Return the current LMP price."""
        if self.coordinator.data:
            return self.coordinator.data.price
        return None

    @property
    def extra_state_attributes(self) -> dict[str, str | float | None]:
        """Return sensor attributes."""
        attrs: dict[str, str | float | None] = {}
        if self.coordinator.data:
            attrs[ATTR_TIMESTAMP] = (
                self.coordinator.data.interval_start.isoformat()
                if self.coordinator.data.interval_start
                else None
            )
            attrs[ATTR_ZONE] = self.coordinator.data.zone
            attrs[ATTR_PREVIOUS_RATE] = self._lmp_coordinator.previous_price
        return attrs


class OntarioLMP24hAverageSensor(OntarioEnergyPricingSensor):
    """Sensor for 24-hour LMP average."""

    _attr_icon = "mdi:chart-line"

    def __init__(self, coordinator: LMP24hAverageCoordinator) -> None:
        """Initialize the 24h average sensor."""
        super().__init__(coordinator, SENSOR_LMP_24H_AVG)

    @property
    def native_value(self) -> float | None:
        """Return the 24-hour average LMP price."""
        if isinstance(self.coordinator, LMP24hAverageCoordinator):
            return self.coordinator.get_24h_average()
        return None

    @property
    def extra_state_attributes(self) -> dict[str, str | None]:
        """Return sensor attributes."""
        attrs: dict[str, str | None] = {}
        if self.coordinator.data:
            attrs[ATTR_TIMESTAMP] = (
                self.coordinator.data.end_time.isoformat()
                if self.coordinator.data.end_time
                else None
            )
        return attrs


class OntarioGlobalAdjustmentSensor(OntarioEnergyPricingSensor):
    """Sensor for Global Adjustment rate."""

    _attr_icon = "mdi:cash"

    def __init__(self, coordinator: GlobalAdjustmentCoordinator) -> None:
        """Initialize the GA sensor."""
        super().__init__(coordinator, SENSOR_GLOBAL_ADJUSTMENT)

    @property
    def native_value(self) -> float | None:
        """Return the Global Adjustment rate."""
        if isinstance(self.coordinator, GlobalAdjustmentCoordinator):
            return self.coordinator.current_rate
        return None

    @property
    def extra_state_attributes(self) -> dict[str, str | None]:
        """Return sensor attributes."""
        attrs: dict[str, str | None] = {}
        if isinstance(self.coordinator, GlobalAdjustmentCoordinator):
            attrs[ATTR_TRADE_MONTH] = self.coordinator.trade_month
        return attrs


class OntarioTotalRateSensor(OntarioEnergyPricingSensor):
    """Sensor for total rate (LMP + GA + Admin Fee)."""

    _attr_icon = "mdi:scale-balance"

    def __init__(
        self,
        lmp_coordinator: LMPCoordinator,
        ga_coordinator: GlobalAdjustmentCoordinator,
        admin_fee: float,
    ) -> None:
        """Initialize the total rate sensor."""
        super().__init__(lmp_coordinator, SENSOR_TOTAL_RATE)
        self._ga_coordinator = ga_coordinator
        self._admin_fee = admin_fee

    @property
    def native_value(self) -> float | None:
        """Calculate total rate from LMP + GA + Admin Fee."""
        lmp_price = None
        if self.coordinator.data:
            lmp_price = self.coordinator.data.price
        ga_rate = None
        if self._ga_coordinator.data:
            ga_rate = self._ga_coordinator.data.rate
        if lmp_price is not None and ga_rate is not None:
            return lmp_price + ga_rate + self._admin_fee
        return None

    @property
    def extra_state_attributes(self) -> dict[str, float | None]:
        """Return sensor attributes with component values."""
        lmp_price = None
        if self.coordinator.data:
            lmp_price = self.coordinator.data.price
        ga_rate = None
        if self._ga_coordinator.data:
            ga_rate = self._ga_coordinator.data.rate
        return {
            "lmp_rate": lmp_price,
            "ga_rate": ga_rate,
            "admin_fee": self._admin_fee,
        }
