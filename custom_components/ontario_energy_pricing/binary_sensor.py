"""Binary sensor platform for Ontario Energy Pricing."""
from __future__ import annotations

import logging
from collections import deque
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    CONF_CHEAPEST_WINDOWS,
    DEFAULT_OUTAGE_CAPACITY_THRESHOLD,
    DEFAULT_OUTAGE_COUNT_THRESHOLD,
    DEFAULT_SHADOW_PRICE_AVERAGE_THRESHOLD,
    DEFAULT_SHADOW_PRICE_MAX_THRESHOLD,
    DEFAULT_BINDING_CONSTRAINTS_THRESHOLD,
    DEFAULT_ARBITRAGE_SPREAD_THRESHOLD,
    DEFAULT_DEMAND_ANOMALY_THRESHOLD_PERCENT,
    DEFAULT_DEMAND_HISTORY_SIZE,
)
from .coordinator import (
    OntarioEnergyPricingData,
    OntarioEnergyPricingCoordinator,
)

LOGGER = logging.getLogger(__name__)


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
            OntarioOutageRiskBinarySensor(coordinator),
            OntarioCongestionPricingBinarySensor(coordinator),
            OntarioIntertieArbitrageBinarySensor(coordinator),
            OntarioDemandAnomalyBinarySensor(coordinator),
        ]
    )

    async_add_entities(entities)


class OntarioCheapestHoursBinarySensor(
    CoordinatorEntity[OntarioEnergyPricingCoordinator], BinarySensorEntity
):
    """Binary sensor: ON when current hour is in cheapest window."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:timer-outline"

    def __init__(
        self,
        coordinator: OntarioEnergyPricingCoordinator,
        window_config: dict[str, Any],
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._window_config = window_config
        self._attr_unique_id = f"{DOMAIN}_cheapest_hours_{window_config['name']}"
        self._attr_translation_key = "cheapest_hours"
        self._attr_translation_placeholders = {"name": window_config["name"]}

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return f"Cheapest Hours: {self._window_config['name']}"

    @property
    def is_on(self) -> bool | None:
        """Return True if current hour is in cheapest window."""
        from datetime import datetime

        data: OntarioEnergyPricingData | None = self.coordinator.data
        if not data or not data.forecast_today:
            return None

        current_hour = datetime.now().hour + 1  # IESO hour 1=00:00-01:00
        num_hours = self._window_config.get("window_hours", 16)
        return data.forecast_today.is_in_cheapest_hours(current_hour, num_hours)

    @property
    def extra_state_attributes(self) -> dict[str, object] | None:
        """Return entity specific state attributes."""
        from datetime import datetime

        data: OntarioEnergyPricingData | None = self.coordinator.data
        if not data or not data.forecast_today:
            return None
        num_hours = self._window_config.get("window_hours", 16)
        current_hour = datetime.now().hour + 1  # IESO hour convention
        cheapest = data.forecast_today.cheapest_hours(num_hours)
        return {
            "cheapest_hours": sorted(cheapest),
            "num_cheapest_hours": num_hours,
            "current_hour": current_hour,
            "forecast_price_cents_per_kwh": round(
                data.forecast_today.average_price_kwh, 2
            ),
        }


class OntarioNegativePriceSensor(
    CoordinatorEntity[OntarioEnergyPricingCoordinator], BinarySensorEntity
):
    """Binary sensor: ON when LMP price is negative."""

    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, coordinator: OntarioEnergyPricingCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_negative_price"
        self._attr_translation_key = "negative_price"

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return "Negative Price"

    @property
    def is_on(self) -> bool | None:
        """Return True if LMP price is negative."""
        data: OntarioEnergyPricingData | None = self.coordinator.data
        if not data:
            return None
        return data.current_lmp_kwh < 0

    @property
    def icon(self) -> str:
        """Return the icon of the sensor."""
        return "mdi:flash-alert" if self.is_on else "mdi:flash-off"

    @property
    def extra_state_attributes(self) -> dict[str, object] | None:
        """Return entity specific state attributes."""
        data: OntarioEnergyPricingData | None = self.coordinator.data
        if not data:
            return None
        return {
            "current_price_cents_per_kwh": round(data.current_lmp_kwh, 2),
            "current_price_dollars_per_mwh": round(data.current_lmp_mwh, 2),
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
    - High outage capacity impact (>500 MW)
    - High shadow prices (>10 $/MWh average)
    - High demand anomaly (>20% above recent median)
    - High intertie spread (>15 $/MWh max spread)
    """

    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, coordinator: OntarioEnergyPricingCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_grid_stressed"
        self._attr_translation_key = "grid_stressed"

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return "Grid Stressed (High Prices Likely)"

    def is_on(self) -> bool | None:
        """Return True if grid is stressed."""
        data: OntarioEnergyPricingData | None = self.coordinator.data
        if not data:
            return None

        # Signal 1: Gas is dominant marginal setter (>50% of generation)
        gas_dominant = (
            data.fuel_mix
            and data.fuel_mix.gas_mw > (data.fuel_mix.total_mw * 0.5)
            if data.fuel_mix and data.fuel_mix.total_mw > 0
            else False
        )

        # Signal 2: Low renewable competition for gas (<20% zero-carbon)
        renewable_low = (
            data.fuel_mix
            and data.fuel_mix.renewable_percentage < 20
            if data.fuel_mix
            else False
        )

        # Signal 3: High carbon intensity (>300 gCO2/kWh = gas-heavy)
        carbon_high = (
            data.fuel_mix
            and data.fuel_mix.carbon_intensity_gco2_per_kwh > 300
            if data.fuel_mix
            else False
        )

        # Signal 4: Price trending up vs recent history (coordinator rolling avg)
        price_trending_up = self._is_price_trending_up(data)

        # Signal 5: High outage capacity impact (>500 MW)
        outage_capacity_high = False
        if data.tx_outages:
            total_capacity = data.tx_outages.get_total_capacity_impact()
            outage_capacity_high = total_capacity > DEFAULT_OUTAGE_CAPACITY_THRESHOLD

        # Signal 6: High shadow prices (>10 $/MWh average)
        shadow_price_high = False
        if data.shadow_prices:
            # Calculate average shadow price across all constraints and intervals
            total_price = 0.0
            count = 0
            for constraint in data.shadow_prices.constraints.values():
                for hour_data in constraint.hourly_prices.values():
                    for price in hour_data.intervals.values():
                        total_price += price
                        count += 1
            avg_shadow_price = total_price / count if count > 0 else 0.0
            shadow_price_high = avg_shadow_price > DEFAULT_SHADOW_PRICE_AVERAGE_THRESHOLD

        # Signal 7: High demand anomaly (>20% above recent median)
        demand_anomaly_high = False
        if data.demand_zonal:
            total_demand = sum(
                zone_data.demand_mw
                for zone_data in data.demand_zonal.demand_data
            )
            # We would need historical data to compute anomaly, but we don't have it here.
            # For now, we'll skip this signal and rely on the dedicated Demand Anomaly sensor.
            pass

        # Signal 8: High intertie spread (>15 $/MWh max spread)
        intertie_spread_high = False
        if data.intertie_lmp:
            lmp_values = [
                lmp.lmp_mwh
                for lmp in data.intertie_lmp.lmp_data
                if lmp.lmp_mwh is not None
            ]
            if lmp_values:
                max_spread = max(lmp_values) - min(lmp_values)
                intertie_spread_high = max_spread > DEFAULT_ARBITRAGE_SPREAD_THRESHOLD

        # Grid stressed if: (gas dominant OR high carbon) AND (low renewable OR price trending up)
        # OR any of the new stress signals are high
        original_condition = (gas_dominant or carbon_high) and (
            renewable_low or price_trending_up
        )
        new_condition = outage_capacity_high or shadow_price_high or intertie_spread_high

        is_stressed = original_condition or new_condition

        # Debug logging
        LOGGER.debug(
            "Grid stressed check: price=%.2fc gas=%.0fMW (%.1f%%) dominant=%s "
            "renewable=%.1f%% low=%s carbon=%.0f high=%s trending=%s "
            "outage_cap=%.1fMW high=%s shadow_price=%.2f avg high=%s "
            "intertie_spread=%.2f high=%s -> stressed=%s",
            data.current_lmp_kwh if data else 0,
            data.fuel_mix.gas_mw if data.fuel_mix else 0,
            (data.fuel_mix.gas_mw / data.fuel_mix.total_mw * 100)
            if data.fuel_mix and data.fuel_mix.total_mw > 0
            else 0,
            gas_dominant,
            data.fuel_mix.renewable_percentage if data.fuel_mix else 0,
            renewable_low,
            data.fuel_mix.carbon_intensity_gco2_per_kwh if data.fuel_mix else 0,
            carbon_high,
            price_trending_up,
            data.tx_outages.get_total_capacity_impact() if data.tx_outages else 0,
            outage_capacity_high,
            shadow_price_high if 'shadow_price_high' in locals() else 0,
            shadow_price_high if 'shadow_price_high' in locals() else False,
            (max(lmp_values) - min(lmp_values)) if data.intertie_lmp and [lmp.lmp_mwh for lmp in data.intertie_lmp.lmp_data if lmp.lmp_mwh is not None] else 0,
            intertie_spread_high,
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
        """Return the icon of the sensor."""
        return "mdi:flash-alert" if self.is_on else "mdi:flash-off"

    @property
    def extra_state_attributes(self) -> dict[str, object] | None:
        """Return entity specific state attributes."""
        data = self.coordinator.data
        if not data:
            return None
        attrs = {
            "current_price_cents_per_kwh": round(data.current_lmp_kwh, 2),
            "gas_generation_mw": round(
                data.fuel_mix.gas_mw, 0
            ) if data.fuel_mix else 0,
            "gas_percentage": round(
                data.fuel_mix.gas_mw / data.fuel_mix.total_mw * 100, 1
            )
            if data.fuel_mix and data.fuel_mix.total_mw > 0
            else 0,
            "renewable_percentage": round(
                data.fuel_mix.renewable_percentage, 1
            )
            if data.fuel_mix
            else 0,
            "carbon_intensity_gco2_per_kwh": round(
                data.fuel_mix.carbon_intensity_gco2_per_kwh, 1
            )
            if data.fuel_mix
            else 0,
            "total_generation_mw": round(
                data.fuel_mix.total_mw, 0
            )
            if data.fuel_mix
            else 0,
            "gas_dominant": data.fuel_mix.gas_mw > (data.fuel_mix.total_mw * 0.5)
            if data.fuel_mix and data.fuel_mix.total_mw > 0
            else False,
            "carbon_high": data.fuel_mix.carbon_intensity_gco2_per_kwh > 300
            if data.fuel_mix
            else False,
            "renewable_low": data.fuel_mix.renewable_percentage < 20
            if data.fuel_mix
            else False,
            "price_trending_up": self._is_price_trending_up(data) if data else False,
        }
        # Add outage attributes if available
        if data.tx_outages:
            attrs.update(
                {
                    "tx_outage_total_capacity_mw": round(
                        data.tx_outages.get_total_capacity_impact(), 1
                    ),
                    "tx_outage_active_count": len(
                        data.tx_outages.get_active_outages()
                    ),
                    "tx_outage_total_count": len(data.tx_outages.outages),
                }
            )
        # Add shadow prices attributes if available
        if data.shadow_prices:
            # Calculate average shadow price across all constraints and intervals
            total_price = 0.0
            count = 0
            max_price = 0.0
            binding_constraints = 0
            for constraint in data.shadow_prices.constraints.values():
                for hour_data in constraint.hourly_prices.values():
                    for price in hour_data.intervals.values():
                        total_price += price
                        count += 1
                        if price > 0:
                            binding_constraints += 1
                        if price > max_price:
                            max_price = price
            avg_shadow_price = total_price / count if count > 0 else 0.0
            attrs.update(
                {
                    "shadow_price_avg": round(avg_shadow_price, 2),
                    "shadow_price_max": round(max_price, 2),
                    "shadow_price_binding_constraints": binding_constraints,
                }
            )
        # Add intertie LMP attributes if available
        if data.intertie_lmp:
            lmp_values = [
                lmp.lmp_mwh
                for lmp in data.intertie_lmp.lmp_data
                if lmp.lmp_mwh is not None
            ]
            if lmp_values:
                attrs.update(
                    {
                        "intertie_lmp_max": round(max(lmp_values), 2),
                        "intertie_lmp_min": round(min(lmp_values), 2),
                        "intertie_lmp_spread": round(
                            max(lmp_values) - min(lmp_values), 2
                        ),
                        "intertie_points": list(
                            data.intertie_lmp.get_intertie_points()
                        ),
                    }
                )
        return attrs


class OntarioOutageRiskBinarySensor(
    CoordinatorEntity[OntarioEnergyPricingCoordinator], BinarySensorEntity
):
    """Binary sensor: ON when transmission outage risk is high."""

    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, coordinator: OntarioEnergyPricingCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_outage_risk"
        self._attr_translation_key = "outage_risk"

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return "Transmission Outage Risk"

    @property
    def is_on(self) -> bool | None:
        """Return True if outage risk is high."""
        data: OntarioEnergyPricingData | None = self.coordinator.data
        if not data or not data.tx_outages:
            return None

        total_capacity = data.tx_outages.get_total_capacity_impact()
        active_outages = data.tx_outages.get_active_outages()
        outage_count = len(active_outages)

        is_high = (
            total_capacity > DEFAULT_OUTAGE_CAPACITY_THRESHOLD
            or outage_count > DEFAULT_OUTAGE_COUNT_THRESHOLD
        )

        return is_high

    @property
    def icon(self) -> str:
        """Return the icon of the sensor."""
        return "mdi:transmission-tower-alert" if self.is_on else "mdi:transmission-tower"

    @property
    def extra_state_attributes(self) -> dict[str, object] | None:
        """Return entity specific state attributes."""
        data: OntarioEnergyPricingData | None = self.coordinator.data
        if not data or not data.tx_outages:
            return None
        total_capacity = data.tx_outages.get_total_capacity_impact()
        active_outages = data.tx_outages.get_active_outages()
        outages_by_zone = {}
        for outage in data.tx_outages.outages:
            zone = outage.zone
            outages_by_zone[zone] = outages_by_zone.get(zone, 0) + 1
        return {
            "total_capacity_mw": round(total_capacity, 1),
            "active_outage_count": len(active_outages),
            "total_outage_count": len(data.tx_outages.outages),
            "outages_by_zone": outages_by_zone,
            "largest_outage_mw": round(
                max((o.capacity_mw for o in data.tx_outages.outages), default=0.0), 1
            ),
        }


class OntarioCongestionPricingBinarySensor(
    CoordinatorEntity[OntarioEnergyPricingCoordinator], BinarySensorEntity
):
    """Binary sensor: ON when congestion pricing is high (indicating transmission constraints)."""

    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, coordinator: OntarioEnergyPricingCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_congestion_pricing"
        self._attr_translation_key = "congestion_pricing"

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return "Congestion Pricing"

    @property
    def is_on(self) -> bool | None:
        """Return True if congestion pricing is high."""
        data: OntarioEnergyPricingData | None = self.coordinator.data
        if not data or not data.shadow_prices:
            return None

        # Calculate average shadow price, max shadow price, and binding constraints count
        total_price = 0.0
        count = 0
        max_price = 0.0
        binding_constraints = 0
        for constraint in data.shadow_prices.constraints.values():
            for hour_data in constraint.hourly_prices.values():
                for price in hour_data.intervals.values():
                    total_price += price
                    count += 1
                    if price > 0:
                        binding_constraints += 1
                    if price > max_price:
                        max_price = price
        avg_shadow_price = total_price / count if count > 0 else 0.0

        is_high = (
            avg_shadow_price > DEFAULT_SHADOW_PRICE_AVERAGE_THRESHOLD
            or max_price > DEFAULT_SHADOW_PRICE_MAX_THRESHOLD
            or binding_constraints > DEFAULT_BINDING_CONSTRAINTS_THRESHOLD
        )

        return is_high

    @property
    def icon(self) -> str:
        """Return the icon of the sensor."""
        return "mdi:alert-circle-outline" if self.is_on else "mdi:alert-circle"

    @property
    def extra_state_attributes(self) -> dict[str, object] | None:
        """Return entity specific state attributes."""
        data: OntarioEnergyPricingData | None = self.coordinator.data
        if not data or not data.shadow_prices:
            return None
        # Calculate average shadow price, max shadow price, and binding constraints count
        total_price = 0.0
        count = 0
        max_price = 0.0
        binding_constraints = 0
        constraint_details = []
        for constraint_name, constraint in data.shadow_prices.constraints.items():
            constraint_max = 0.0
            constraint_count = 0
            constraint_total = 0.0
            for hour_data in constraint.hourly_prices.values():
                for price in hour_data.intervals.values():
                    constraint_total += price
                    constraint_count += 1
                    if price > 0:
                        binding_constraints += 1
                    if price > constraint_max:
                        constraint_max = price
                    if price > max_price:
                        max_price = price
            constraint_avg = constraint_total / constraint_count if constraint_count > 0 else 0.0
            constraint_details.append(
                {
                    "constraint": constraint_name,
                    "avg_price": round(constraint_avg, 2),
                    "max_price": round(constraint_max, 2),
                }
            )
        # Sort constraint details by max price descending
        constraint_details.sort(key=lambda x: x["max_price"], reverse=True)
        avg_shadow_price = total_price / count if count > 0 else 0.0
        return {
            "shadow_price_avg": round(avg_shadow_price, 2),
            "shadow_price_max": round(max_price, 2),
            "shadow_price_binding_constraints": binding_constraints,
            "top_constraints": constraint_details[:5],  # Top 5 constraints by max price
        }


class OntarioIntertieArbitrageBinarySensor(
    CoordinatorEntity[OntarioEnergyPricingCoordinator], BinarySensorEntity
):
    """Binary sensor: ON when intertie arbitrage opportunity exists."""

    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, coordinator: OntarioEnergyPricingCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_intertie_arbitrage"
        self._attr_translation_key = "intertie_arbitrage"

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return "Intertie Arbitrage Opportunity"

    @property
    def is_on(self) -> bool | None:
        """Return True if intertie arbitrage opportunity exists."""
        data: OntarioEnergyPricingData | None = self.coordinator.data
        if not data or not data.intertie_lmp:
            return None

        lmp_values = [
            lmp.lmp_mwh
            for lmp in data.intertie_lmp.lmp_data
            if lmp.lmp_mwh is not None
        ]
        if not lmp_values or len(lmp_values) < 2:
            return False

        max_spread = max(lmp_values) - min(lmp_values)
        return max_spread > DEFAULT_ARBITRAGE_SPREAD_THRESHOLD

    @property
    def icon(self) -> str:
        """Return the icon of the sensor."""
        return "mdi:swap-horizontal" if self.is_on else "mdi:swap-horizontal-variant"

    @property
    def extra_state_attributes(self) -> dict[str, object] | None:
        """Return entity specific state attributes."""
        data: OntarioEnergyPricingData | None = self.coordinator.data
        if not data or not data.intertie_lmp:
            return None
        lmp_values = [
            lmp.lmp_mwh
            for lmp in data.intertie_lmp.lmp_data
            if lmp.lmp_mwh is not None
        ]
        if not lmp_values:
            return None
        # Get latest LMP for each intertie point (use interval as recency proxy)
        latest_by_point: dict[str, tuple[int, float]] = {}
        for lmp in data.intertie_lmp.lmp_data:
            point = lmp.intertie_point.upper()
            sort_key = lmp.delivery_hour * 12 + lmp.interval
            if point not in latest_by_point or sort_key > latest_by_point[point][0]:
                latest_by_point[point] = (sort_key, lmp.lmp_mwh)
        # Create a dict of latest prices
        latest_prices = {
            point: price for point, (_, price) in latest_by_point.items()
        }
        return {
            "intertie_lmp_max": round(max(lmp_values), 2),
            "intertie_lmp_min": round(min(lmp_values), 2),
            "intertie_lmp_spread": round(max(lmp_values) - min(lmp_values), 2),
            "intertie_points": list(latest_prices.keys()),
            "latest_prices": {
                point: round(price, 2) for point, price in latest_prices.items()
            },
        }


class OntarioDemandAnomalyBinarySensor(
    CoordinatorEntity[OntarioEnergyPricingCoordinator], BinarySensorEntity
):
    """Binary sensor: ON when demand anomaly is detected (unexpected high demand)."""

    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, coordinator: OntarioEnergyPricingCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_demand_anomaly"
        self._attr_translation_key = "demand_anomaly"
        # Initialize rolling demand history
        self._recent_total_demand: deque[float] = deque(maxlen=DEFAULT_DEMAND_HISTORY_SIZE)

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return "Demand Anomaly"

    @property
    def is_on(self) -> bool | None:
        """Return True if demand anomaly is detected."""
        data: OntarioEnergyPricingData | None = self.coordinator.data
        if not data or not data.demand_zonal:
            return None

        # Calculate total demand across all zones
        total_demand = sum(
            zone_data.demand_mw
            for zone_data in data.demand_zonal.demand_data
        )

        # Add current demand to history (but we will check against previous values)
        # We need at least some history to compute a meaningful median
        if len(self._recent_total_demand) < 5:
            # Not enough history yet, add current value and return False
            self._recent_total_demand.append(total_demand)
            return False

        # Compute median of previous values (excluding current)
        sorted_previous = sorted(self._recent_total_demand)
        median_previous = sorted_previous[len(sorted_previous) // 2]

        # Check if current demand is above threshold percent of median
        is_anomaly = (
            total_demand
            > median_previous * (1 + DEFAULT_DEMAND_ANOMALY_THRESHOLD_PERCENT / 100.0)
        )

        # Add current demand to history for next check
        self._recent_total_demand.append(total_demand)

        return is_anomaly

    @property
    def icon(self) -> str:
        """Return the icon of the sensor."""
        return "mdi:chart-line-variant" if self.is_on else "mdi:chart-line"

    @property
    def extra_state_attributes(self) -> dict[str, object] | None:
        """Return entity specific state attributes."""
        data: OntarioEnergyPricingData | None = self.coordinator.data
        if not data or not data.demand_zonal:
            return None
        total_demand = sum(
            zone_data.demand_mw
            for zone_data in data.demand_zonal.demand_data
        )
        # Compute median of recent history (including current if we have added it)
        # We'll compute median of the history deque
        history_list = list(self._recent_total_demand)
        if not history_list:
            median_demand = 0.0
        else:
            sorted_history = sorted(history_list)
            median_demand = sorted_history[len(history_list) // 2]
        return {
            "total_demand_mw": round(total_demand, 1),
            "recent_median_demand_mw": round(median_demand, 1),
            "demand_anomaly_threshold_percent": DEFAULT_DEMAND_ANOMALY_THRESHOLD_PERCENT,
            "zones": list(data.demand_zonal.get_zones()),
            "demand_by_zone": {
                zone.zone: round(zone.demand_mw, 1)
                for zone in data.demand_zonal.demand_data
            },
        }