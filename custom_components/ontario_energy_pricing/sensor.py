"""Sensor platform for Ontario Energy Pricing."""
from __future__ import annotations

import traceback
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
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
        entities: list[SensorEntity] = [
            # Core pricing sensors
            OntarioCurrentLMPSensor(coordinator),
            OntarioHourAverageLMPSensor(coordinator),
            OntarioGlobalAdjustmentSensor(coordinator),
            OntarioTotalRateSensor(coordinator),
            # Fuel mix sensors
            OntarioFuelMixNuclearSensor(coordinator),
            OntarioFuelMixHydroSensor(coordinator),
            OntarioFuelMixWindSensor(coordinator),
            OntarioFuelMixSolarSensor(coordinator),
            OntarioFuelMixGasSensor(coordinator),
            OntarioFuelMixBiofuelSensor(coordinator),
            OntarioFuelMixOtherSensor(coordinator),
            OntarioFuelMixTotalSensor(coordinator),
            OntarioFuelMixRenewablePercentSensor(coordinator),
            OntarioFuelMixCarbonIntensitySensor(coordinator),
            # Shadow prices sensors
            OntarioShadowPriceMaxSensor(coordinator),
            OntarioShadowPriceBindingConstraintsSensor(coordinator),
            # Intertie LMP sensors
            OntarioIntertieLMPMichiganSensor(coordinator),
            OntarioIntertieLMPNewYorkSensor(coordinator),
            OntarioIntertieLMPQuebecSensor(coordinator),
            OntarioIntertieLMPManitobaSensor(coordinator),
            OntarioIntertieLMPMinnesotaSensor(coordinator),
            # Reserve prices sensor
            OntarioReservePrice10SSensor(coordinator),
            OntarioReservePrice10NSensor(coordinator),
            OntarioReservePrice30RSensor(coordinator),
            # Tx outages sensors
            OntarioTxOutagesCountSensor(coordinator),
            OntarioTxOutagesCapacityImpactSensor(coordinator),
            # Demand zonal sensors
            OntarioDemandZonalTotalSensor(coordinator),
            OntarioDemandZonalTorontoSensor(coordinator),
            OntarioDemandZonalOttawaSensor(coordinator),
            # VG forecast sensors
            OntarioVGForecastSolarSensor(coordinator),
            OntarioVGForecastWindSensor(coordinator),
            OntarioVGForecastTotalSensor(coordinator),
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


# =============================================================================
# Core Pricing Sensors
# =============================================================================

class OntarioCurrentLMPSensor(OntarioEnergyPricingSensor):
    """Sensor for current LMP price (latest 5-min interval)."""

    _attr_icon = "mdi:lightning-bolt"
    _attr_native_unit_of_measurement = "¢/kWh"
    _attr_device_class = SensorDeviceClass.MONETARY

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
    _attr_native_unit_of_measurement = "¢/kWh"
    _attr_device_class = SensorDeviceClass.MONETARY

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
    _attr_native_unit_of_measurement = "¢/kWh"
    _attr_device_class = SensorDeviceClass.MONETARY

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
    _attr_native_unit_of_measurement = "¢/kWh"
    _attr_device_class = SensorDeviceClass.MONETARY

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


# =============================================================================
# Fuel Mix Sensors
# =============================================================================

class OntarioFuelMixBaseSensor(OntarioEnergyPricingSensor):
    """Base class for fuel mix sensors."""

    _attr_native_unit_of_measurement = "MW"
    _attr_icon = "mdi:power-plant"

    def _get_fuel_mix(self) -> Any:
        """Get fuel mix data from coordinator."""
        if self.coordinator.data:
            return self.coordinator.data.fuel_mix
        return None


class OntarioFuelMixNuclearSensor(OntarioFuelMixBaseSensor):
    """Sensor for nuclear generation output."""

    _attr_icon = "mdi:atom-variant"

    def __init__(self, coordinator: OntarioEnergyPricingCoordinator) -> None:
        super().__init__(coordinator, "fuel_mix_nuclear")

    @property
    def native_value(self) -> float | None:
        fuel_mix = self._get_fuel_mix()
        if fuel_mix:
            return fuel_mix.nuclear_mw
        return None


class OntarioFuelMixHydroSensor(OntarioFuelMixBaseSensor):
    """Sensor for hydro generation output."""

    _attr_icon = "mdi:waves"

    def __init__(self, coordinator: OntarioEnergyPricingCoordinator) -> None:
        super().__init__(coordinator, "fuel_mix_hydro")

    @property
    def native_value(self) -> float | None:
        fuel_mix = self._get_fuel_mix()
        if fuel_mix:
            return fuel_mix.hydro_mw
        return None


class OntarioFuelMixWindSensor(OntarioFuelMixBaseSensor):
    """Sensor for wind generation output."""

    _attr_icon = "mdi:weather-windy"

    def __init__(self, coordinator: OntarioEnergyPricingCoordinator) -> None:
        super().__init__(coordinator, "fuel_mix_wind")

    @property
    def native_value(self) -> float | None:
        fuel_mix = self._get_fuel_mix()
        if fuel_mix:
            return fuel_mix.wind_mw
        return None


class OntarioFuelMixSolarSensor(OntarioFuelMixBaseSensor):
    """Sensor for solar generation output."""

    _attr_icon = "mdi:white-balance-sunny"

    def __init__(self, coordinator: OntarioEnergyPricingCoordinator) -> None:
        super().__init__(coordinator, "fuel_mix_solar")

    @property
    def native_value(self) -> float | None:
        fuel_mix = self._get_fuel_mix()
        if fuel_mix:
            return fuel_mix.solar_mw
        return None


class OntarioFuelMixGasSensor(OntarioFuelMixBaseSensor):
    """Sensor for gas generation output."""

    _attr_icon = "mdi:fire"

    def __init__(self, coordinator: OntarioEnergyPricingCoordinator) -> None:
        super().__init__(coordinator, "fuel_mix_gas")

    @property
    def native_value(self) -> float | None:
        fuel_mix = self._get_fuel_mix()
        if fuel_mix:
            return fuel_mix.gas_mw
        return None


class OntarioFuelMixBiofuelSensor(OntarioFuelMixBaseSensor):
    """Sensor for biofuel generation output."""

    _attr_icon = "mdi:leaf"

    def __init__(self, coordinator: OntarioEnergyPricingCoordinator) -> None:
        super().__init__(coordinator, "fuel_mix_biofuel")

    @property
    def native_value(self) -> float | None:
        fuel_mix = self._get_fuel_mix()
        if fuel_mix:
            return fuel_mix.biofuel_mw
        return None


class OntarioFuelMixOtherSensor(OntarioFuelMixBaseSensor):
    """Sensor for other generation output."""

    def __init__(self, coordinator: OntarioEnergyPricingCoordinator) -> None:
        super().__init__(coordinator, "fuel_mix_other")

    @property
    def native_value(self) -> float | None:
        fuel_mix = self._get_fuel_mix()
        if fuel_mix:
            return fuel_mix.other_mw
        return None


class OntarioFuelMixTotalSensor(OntarioFuelMixBaseSensor):
    """Sensor for total generation output."""

    _attr_icon = "mdi:gauge"

    def __init__(self, coordinator: OntarioEnergyPricingCoordinator) -> None:
        super().__init__(coordinator, "fuel_mix_total")

    @property
    def native_value(self) -> float | None:
        fuel_mix = self._get_fuel_mix()
        if fuel_mix:
            return fuel_mix.total_mw
        return None


class OntarioFuelMixRenewablePercentSensor(OntarioEnergyPricingSensor):
    """Sensor for renewable generation percentage."""

    _attr_icon = "mdi:leaf"
    _attr_native_unit_of_measurement = "%"

    def __init__(self, coordinator: OntarioEnergyPricingCoordinator) -> None:
        super().__init__(coordinator, "fuel_mix_renewable_percent")

    @property
    def native_value(self) -> float | None:
        fuel_mix = self._get_fuel_mix()
        if fuel_mix:
            return round(fuel_mix.renewable_percentage, 1)
        return None

    def _get_fuel_mix(self) -> Any:
        if self.coordinator.data:
            return self.coordinator.data.fuel_mix
        return None


class OntarioFuelMixCarbonIntensitySensor(OntarioEnergyPricingSensor):
    """Sensor for grid carbon intensity."""

    _attr_icon = "mdi:molecule-co2"
    _attr_native_unit_of_measurement = "gCO₂/kWh"

    def __init__(self, coordinator: OntarioEnergyPricingCoordinator) -> None:
        super().__init__(coordinator, "fuel_mix_carbon_intensity")

    @property
    def native_value(self) -> float | None:
        fuel_mix = self._get_fuel_mix()
        if fuel_mix:
            return round(fuel_mix.carbon_intensity_gco2_per_kwh, 1)
        return None

    def _get_fuel_mix(self) -> Any:
        if self.coordinator.data:
            return self.coordinator.data.fuel_mix
        return None


# =============================================================================
# Shadow Prices Sensors
# =============================================================================

class OntarioShadowPriceBaseSensor(OntarioEnergyPricingSensor):
    """Base class for shadow prices sensors."""

    _attr_native_unit_of_measurement = "$/MWh"
    _attr_icon = "mdi:transmission-tower"

    def _get_shadow_prices(self) -> Any:
        """Get shadow prices data from coordinator."""
        if self.coordinator.data:
            return self.coordinator.data.shadow_prices
        return None


class OntarioShadowPriceMaxSensor(OntarioShadowPriceBaseSensor):
    """Sensor for maximum shadow price (congestion cost)."""

    def __init__(self, coordinator: OntarioEnergyPricingCoordinator) -> None:
        super().__init__(coordinator, "shadow_price_max")

    @property
    def native_value(self) -> float | None:
        shadow_prices = self._get_shadow_prices()
        if shadow_prices:
            # Get current hour (IESO hours are 1-24)
            from datetime import datetime
            current_hour = datetime.now().hour
            ieso_hour = current_hour if current_hour > 0 else 24
            return round(shadow_prices.get_max_shadow_price(ieso_hour), 2)
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        shadow_prices = self._get_shadow_prices()
        if not shadow_prices:
            return {}
        return {
            "constraints_count": len(shadow_prices.constraints),
            "constraint_names": list(shadow_prices.constraints.keys()),
        }


class OntarioShadowPriceBindingConstraintsSensor(OntarioShadowPriceBaseSensor):
    """Sensor for count of binding constraints (shadow price > 0)."""

    _attr_native_unit_of_measurement = "count"
    _attr_icon = "mdi:alert-circle"

    def __init__(self, coordinator: OntarioEnergyPricingCoordinator) -> None:
        super().__init__(coordinator, "shadow_price_binding_constraints")

    @property
    def native_value(self) -> int | None:
        shadow_prices = self._get_shadow_prices()
        if not shadow_prices:
            return None
        from datetime import datetime
        current_hour = datetime.now().hour
        ieso_hour = current_hour if current_hour > 0 else 24
        count = 0
        for constraint in shadow_prices.constraints.values():
            hour_data = constraint.get_hour(ieso_hour)
            if hour_data and hour_data.max_price() > 0:
                count += 1
        return count


# =============================================================================
# Intertie LMP Sensors
# =============================================================================

class OntarioIntertieLMPBaseSensor(OntarioEnergyPricingSensor):
    """Base class for intertie LMP sensors."""

    _attr_native_unit_of_measurement = "$/MWh"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_icon = "mdi:transmission-tower-export"

    def __init__(
        self,
        coordinator: OntarioEnergyPricingCoordinator,
        translation_key: str,
        intertie_point: str,
    ) -> None:
        super().__init__(coordinator, translation_key)
        self._intertie_point = intertie_point

    def _get_intertie_lmp(self) -> Any:
        if self.coordinator.data:
            return self.coordinator.data.intertie_lmp
        return None

    @property
    def native_value(self) -> float | None:
        intertie_lmp = self._get_intertie_lmp()
        if intertie_lmp:
            return intertie_lmp.get_current_interval_lmp(self._intertie_point)
        return None


class OntarioIntertieLMPMichiganSensor(OntarioIntertieLMPBaseSensor):
    """Sensor for Michigan intertie LMP."""

    def __init__(self, coordinator: OntarioEnergyPricingCoordinator) -> None:
        super().__init__(coordinator, "intertie_lmp_michigan", "MICHIGAN")


class OntarioIntertieLMPNewYorkSensor(OntarioIntertieLMPBaseSensor):
    """Sensor for New York intertie LMP."""

    def __init__(self, coordinator: OntarioEnergyPricingCoordinator) -> None:
        super().__init__(coordinator, "intertie_lmp_new_york", "NEW_YORK")


class OntarioIntertieLMPQuebecSensor(OntarioIntertieLMPBaseSensor):
    """Sensor for Quebec intertie LMP."""

    def __init__(self, coordinator: OntarioEnergyPricingCoordinator) -> None:
        super().__init__(coordinator, "intertie_lmp_quebec", "QUEBEC")


class OntarioIntertieLMPManitobaSensor(OntarioIntertieLMPBaseSensor):
    """Sensor for Manitoba intertie LMP."""

    def __init__(self, coordinator: OntarioEnergyPricingCoordinator) -> None:
        super().__init__(coordinator, "intertie_lmp_manitoba", "MANITOBA")


class OntarioIntertieLMPMinnesotaSensor(OntarioIntertieLMPBaseSensor):
    """Sensor for Minnesota intertie LMP."""

    def __init__(self, coordinator: OntarioEnergyPricingCoordinator) -> None:
        super().__init__(coordinator, "intertie_lmp_minnesota", "MINNESOTA")


# =============================================================================
# Reserve Prices Sensors
# =============================================================================

class OntarioReservePriceBaseSensor(OntarioEnergyPricingSensor):
    """Base class for reserve price sensors."""

    _attr_native_unit_of_measurement = "$/MWh"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_icon = "mdi:battery-heart"

    def __init__(
        self,
        coordinator: OntarioEnergyPricingCoordinator,
        translation_key: str,
        reserve_type: str,
    ) -> None:
        super().__init__(coordinator, translation_key)
        self._reserve_type = reserve_type

    def _get_reserve_prices(self) -> Any:
        if self.coordinator.data:
            return self.coordinator.data.reserve_prices
        return None

    @property
    def native_value(self) -> float | None:
        reserve_prices = self._get_reserve_prices()
        if not reserve_prices:
            return None
        # Get the first region's price for this reserve type (ONTARIO region typically)
        regions = reserve_prices.get_regions()
        for region in regions:
            price = reserve_prices.get_reserve_price(region, self._reserve_type, 1, 1)
            if price is not None:
                return price
        return None


class OntarioReservePrice10SSensor(OntarioReservePriceBaseSensor):
    """Sensor for 10-minute spinning reserve price."""

    def __init__(self, coordinator: OntarioEnergyPricingCoordinator) -> None:
        super().__init__(coordinator, "reserve_price_10s", "10S")


class OntarioReservePrice10NSensor(OntarioReservePriceBaseSensor):
    """Sensor for 10-minute non-spinning reserve price."""

    def __init__(self, coordinator: OntarioEnergyPricingCoordinator) -> None:
        super().__init__(coordinator, "reserve_price_10n", "10N")


class OntarioReservePrice30RSensor(OntarioReservePriceBaseSensor):
    """Sensor for 30-minute reserve price."""

    def __init__(self, coordinator: OntarioEnergyPricingCoordinator) -> None:
        super().__init__(coordinator, "reserve_price_30r", "30R")


# =============================================================================
# Tx Outages Sensors
# =============================================================================

class OntarioTxOutagesBaseSensor(OntarioEnergyPricingSensor):
    """Base class for transmission outages sensors."""

    def _get_tx_outages(self) -> Any:
        if self.coordinator.data:
            return self.coordinator.data.tx_outages
        return None


class OntarioTxOutagesCountSensor(OntarioTxOutagesBaseSensor):
    """Sensor for active transmission outages count."""

    _attr_icon = "mdi:alert-circle"
    _attr_native_unit_of_measurement = "count"

    def __init__(self, coordinator: OntarioEnergyPricingCoordinator) -> None:
        super().__init__(coordinator, "tx_outages_count")

    @property
    def native_value(self) -> int | None:
        tx_outages = self._get_tx_outages()
        if tx_outages:
            return len(tx_outages.get_active_outages())
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        tx_outages = self._get_tx_outages()
        if not tx_outages:
            return {}
        active = tx_outages.get_active_outages()
        return {
            "total_outages": len(tx_outages.outages) if hasattr(tx_outages, 'outages') else 0,
            "active_outages": len(active),
            "zones_affected": list(set(o.zone for o in active if hasattr(o, 'zone') and o.zone)),
        }


class OntarioTxOutagesCapacityImpactSensor(OntarioTxOutagesBaseSensor):
    """Sensor for total capacity impact of outages."""

    _attr_icon = "mdi:flash"
    _attr_native_unit_of_measurement = "MW"

    def __init__(self, coordinator: OntarioEnergyPricingCoordinator) -> None:
        super().__init__(coordinator, "tx_outages_capacity_impact")

    @property
    def native_value(self) -> float | None:
        tx_outages = self._get_tx_outages()
        if tx_outages:
            return round(tx_outages.get_total_capacity_impact(), 1)
        return None


# =============================================================================
# Demand Zonal Sensors
# =============================================================================

class OntarioDemandZonalBaseSensor(OntarioEnergyPricingSensor):
    """Base class for demand zonal sensors."""

    _attr_native_unit_of_measurement = "MW"
    _attr_icon = "mdi:home-lightning-bolt"

    def __init__(
        self,
        coordinator: OntarioEnergyPricingCoordinator,
        translation_key: str,
        zone: str,
    ) -> None:
        super().__init__(coordinator, translation_key)
        self._zone = zone

    def _get_demand_zonal(self) -> Any:
        if self.coordinator.data:
            return self.coordinator.data.demand_zonal
        return None

    @property
    def native_value(self) -> float | None:
        demand_zonal = self._get_demand_zonal()
        if demand_zonal:
            latest = demand_zonal.get_latest_demand_by_zone(self._zone)
            if latest:
                return latest.demand_mw
        return None


class OntarioDemandZonalTotalSensor(OntarioEnergyPricingSensor):
    """Sensor for total Ontario demand."""

    _attr_native_unit_of_measurement = "MW"
    _attr_icon = "mdi:home-lightning-bolt"

    def __init__(self, coordinator: OntarioEnergyPricingCoordinator) -> None:
        super().__init__(coordinator, "demand_zonal_total")

    def _get_demand_zonal(self) -> Any:
        if self.coordinator.data:
            return self.coordinator.data.demand_zonal
        return None

    @property
    def native_value(self) -> float | None:
        demand_zonal = self._get_demand_zonal()
        if demand_zonal:
            latest = demand_zonal.get_latest_demand_by_zone("ONTARIO")
            if latest:
                return latest.demand_mw
            # Sum all zones
            zones = ["NORTHWEST", "NORTHEAST", "OTTAWA", "EAST", "TORONTO", "ESSA", "BRUCE", "SOUTHWEST", "NIAGARA", "WEST"]
            total = 0.0
            for zone in zones:
                val = demand_zonal.get_latest_demand_by_zone(zone)
                if val:
                    total += val.demand_mw
            return total if total > 0 else None
        return None


class OntarioDemandZonalTorontoSensor(OntarioDemandZonalBaseSensor):
    """Sensor for Toronto zone demand."""

    def __init__(self, coordinator: OntarioEnergyPricingCoordinator) -> None:
        super().__init__(coordinator, "demand_zonal_toronto", "TORONTO")


class OntarioDemandZonalOttawaSensor(OntarioDemandZonalBaseSensor):
    """Sensor for Ottawa zone demand."""

    def __init__(self, coordinator: OntarioEnergyPricingCoordinator) -> None:
        super().__init__(coordinator, "demand_zonal_ottawa", "OTTAWA")


# =============================================================================
# VG Forecast Sensors
# =============================================================================

class OntarioVGForecastBaseSensor(OntarioEnergyPricingSensor):
    """Base class for VG forecast sensors."""

    _attr_native_unit_of_measurement = "MW"
    _attr_icon = "mdi:chart-line"

    def __init__(
        self,
        coordinator: OntarioEnergyPricingCoordinator,
        translation_key: str,
        fuel_type: str,  # "solar" or "wind"
    ) -> None:
        super().__init__(coordinator, translation_key)
        self._fuel_type = fuel_type

    def _get_vg_forecast(self) -> Any:
        if self.coordinator.data:
            return self.coordinator.data.vg_forecast
        return None

    @property
    def native_value(self) -> float | None:
        vg_forecast = self._get_vg_forecast()
        if not vg_forecast:
            return None
        from datetime import datetime
        current_hour = datetime.now().hour
        ieso_hour = current_hour if current_hour > 0 else 24
        if self._fuel_type == "solar":
            return vg_forecast.solar_forecast_mw.get(ieso_hour, 0.0)
        elif self._fuel_type == "wind":
            return vg_forecast.wind_forecast_mw.get(ieso_hour, 0.0)
        return None


class OntarioVGForecastSolarSensor(OntarioVGForecastBaseSensor):
    """Sensor for solar forecast."""

    _attr_icon = "mdi:white-balance-sunny"

    def __init__(self, coordinator: OntarioEnergyPricingCoordinator) -> None:
        super().__init__(coordinator, "vg_forecast_solar", "solar")


class OntarioVGForecastWindSensor(OntarioVGForecastBaseSensor):
    """Sensor for wind forecast."""

    _attr_icon = "mdi:weather-windy"

    def __init__(self, coordinator: OntarioEnergyPricingCoordinator) -> None:
        super().__init__(coordinator, "vg_forecast_wind", "wind")


class OntarioVGForecastTotalSensor(OntarioEnergyPricingSensor):
    """Sensor for total VG (solar + wind) forecast."""

    _attr_native_unit_of_measurement = "MW"
    _attr_icon = "mdi:chart-line"

    def __init__(self, coordinator: OntarioEnergyPricingCoordinator) -> None:
        super().__init__(coordinator, "vg_forecast_total")

    def _get_vg_forecast(self) -> Any:
        if self.coordinator.data:
            return self.coordinator.data.vg_forecast
        return None

    @property
    def native_value(self) -> float | None:
        vg_forecast = self._get_vg_forecast()
        if not vg_forecast:
            return None
        from datetime import datetime
        current_hour = datetime.now().hour
        ieso_hour = current_hour if current_hour > 0 else 24
        solar = vg_forecast.solar_forecast_mw.get(ieso_hour, 0.0)
        wind = vg_forecast.wind_forecast_mw.get(ieso_hour, 0.0)
        return solar + wind