"""Ontario Energy Pricing integration for Home Assistant.

Provides sensors for Ontario electricity pricing components:
- Current LMP (Locational Marginal Price)
- Hour Average LMP
- Global Adjustment
- Total Rate (LMP + GA + Admin Fee)
"""

from __future__ import annotations

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall

from .const import CONF_ADMIN_FEE, DOMAIN, LOGGER
from .coordinator import OntarioEnergyPricingCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR]

# Modern type alias for config entry with runtime_data type
OntarioEnergyPricingConfigEntry = ConfigEntry[OntarioEnergyPricingCoordinator]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Ontario Energy Pricing domain.

    Services are registered here per HA best practices:
    https://developers.home-assistant.io/docs/dev_101_services/
    """
    LOGGER.debug("[INIT] async_setup called")

    async def async_refresh_service(call: ServiceCall) -> None:
        """Handle refresh service call."""
        LOGGER.debug("[INIT] Refresh service called")
        # Find the first config entry and refresh its coordinator
        entries = hass.config_entries.async_entries(DOMAIN)
        if entries:
            entry: OntarioEnergyPricingConfigEntry = entries[0]
            if hasattr(entry, "runtime_data") and entry.runtime_data:
                await entry.runtime_data.async_request_refresh()

    hass.services.async_register(
        DOMAIN,
        "refresh",
        async_refresh_service,
        schema=vol.Schema({}),
    )

    return True


async def async_setup_entry(
    hass: HomeAssistant,
    entry: OntarioEnergyPricingConfigEntry,
) -> bool:
    """Set up Ontario Energy Pricing from a config entry."""
    LOGGER.debug(
        "[INIT] async_setup_entry called: entry_id=%s, data=%s, options=%s, version=%s",
        entry.entry_id,
        entry.data,
        entry.options,
        entry.version,
    )

    # Read admin_fee from options (set by options flow) with fallback to data
    admin_fee = entry.options.get(
        CONF_ADMIN_FEE, entry.data.get(CONF_ADMIN_FEE, 0.0)
    )
    LOGGER.debug("[INIT] Creating coordinator with admin_fee=%s", admin_fee)

    coordinator = OntarioEnergyPricingCoordinator(hass, entry, admin_fee)

    # Store coordinator in runtime_data (modern pattern)
    entry.runtime_data = coordinator

    # Do first refresh - let HA handle ConfigEntryNotReady automatically
    # if the refresh fails, HA will retry setup later
    await coordinator.async_config_entry_first_refresh()

    # Forward to sensor platform
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register options update listener so changes reload the integration
    entry.async_on_unload(entry.add_update_listener(config_entry_update_listener))

    LOGGER.debug("[INIT] Setup complete for entry: %s", entry.entry_id)
    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: OntarioEnergyPricingConfigEntry,
) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def config_entry_update_listener(
    hass: HomeAssistant,
    entry: OntarioEnergyPricingConfigEntry,
) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)
