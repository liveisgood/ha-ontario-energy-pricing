"""Ontario Energy Pricing integration for Home Assistant.

Provides sensors for Ontario electricity pricing components:
- Current LMP (Locational Marginal Price)
- Hour Average LMP
- Global Adjustment
- Total Rate (LMP + GA + Admin Fee)
"""

from __future__ import annotations

import traceback

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall

from .const import DOMAIN, LOGGER
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
    LOGGER.debug(
        "[INIT] HA version: %s",
        getattr(hass.config, "version", "N/A"),
    )

    # Create unified coordinator
    admin_fee = entry.data.get("admin_fee", 0.0)
    LOGGER.debug(
        "[INIT] Creating coordinator with admin_fee=%s (type=%s)",
        admin_fee,
        type(admin_fee).__name__,
    )
    try:
        coordinator = OntarioEnergyPricingCoordinator(hass, admin_fee)
        LOGGER.debug("[INIT] Coordinator created successfully")
    except Exception as err:
        LOGGER.error(
            "[INIT] FAILED to create coordinator: %s\n%s",
            err,
            traceback.format_exc(),
        )
        return False

    # Store coordinator in runtime_data (modern pattern)
    entry.runtime_data = coordinator
    LOGGER.debug("[INIT] Coordinator stored in entry.runtime_data")

    # Do first refresh to get initial data
    LOGGER.debug("[INIT] Starting async_config_entry_first_refresh...")
    try:
        await coordinator.async_config_entry_first_refresh()
        LOGGER.debug(
            "[INIT] First refresh complete: success=%s, data=%s",
            coordinator.last_update_success,
            coordinator.data,
        )
    except Exception as err:
        LOGGER.error(
            "[INIT] FAILED first refresh: %s\n%s",
            err,
            traceback.format_exc(),
        )
        # Don't return False here - HA allows setup to succeed even if first refresh fails
        LOGGER.debug("[INIT] Continuing setup despite first refresh failure")

    # Forward to sensor platform
    LOGGER.debug("[INIT] Forwarding entry to platforms: %s", PLATFORMS)
    try:
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
        LOGGER.debug("[INIT] Platform forwarding complete")
    except Exception as err:
        LOGGER.error(
            "[INIT] FAILED to forward platforms: %s\n%s",
            err,
            traceback.format_exc(),
        )
        return False

    # Register options update listener so changes reload the integration
    entry.async_on_unload(entry.add_update_listener(config_entry_update_listener))

    LOGGER.debug("[INIT] Setup complete for entry: %s", entry.entry_id)
    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: OntarioEnergyPricingConfigEntry,
) -> bool:
    """Unload a config entry."""
    LOGGER.debug("[INIT] Unloading entry: %s", entry.entry_id)
    # Unload platforms
    try:
        result = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
        LOGGER.debug("[INIT] Unload platforms result: %s", result)
        return result
    except Exception as err:
        LOGGER.error(
            "[INIT] FAILED to unload platforms: %s\n%s",
            err,
            traceback.format_exc(),
        )
        return False


async def config_entry_update_listener(
    hass: HomeAssistant,
    entry: OntarioEnergyPricingConfigEntry,
) -> None:
    """Handle options update."""
    LOGGER.debug(
        "[INIT] config_entry_update_listener called for entry=%s, new_options=%s",
        entry.entry_id,
        entry.options,
    )
    await hass.config_entries.async_reload(entry.entry_id)
