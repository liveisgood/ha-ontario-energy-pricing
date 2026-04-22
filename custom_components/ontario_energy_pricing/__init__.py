"""Ontario Energy Pricing integration for Home Assistant.

Provides sensors for Ontario electricity pricing components:
- Current LMP (Locational Marginal Price)
- Hour Average LMP
- Global Adjustment
- Total Rate (LMP + GA + Admin Fee)
"""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall

from .const import DOMAIN, LOGGER
from .coordinator import OntarioEnergyPricingCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Set up Ontario Energy Pricing from a config entry."""
    LOGGER.debug("Setting up entry: %s", entry.entry_id)

    # Create unified coordinator
    admin_fee = entry.data.get("admin_fee", 0.0)
    coordinator = OntarioEnergyPricingCoordinator(hass, admin_fee)

    # Store coordinator in runtime_data (modern pattern)
    entry.runtime_data = coordinator

    # Do first refresh to get initial data
    await coordinator.async_config_entry_first_refresh()

    # Forward to sensor platform
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register refresh service
    async def async_refresh_service(call: ServiceCall) -> None:
        """Handle refresh service call."""
        LOGGER.debug("Refresh service called")
        await entry.runtime_data.async_refresh()

    service_remove = hass.services.async_register(
        DOMAIN, "refresh", async_refresh_service
    )
    entry.async_on_unload(service_remove)

    LOGGER.debug("Setup complete for entry: %s", entry.entry_id)
    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Unload a config entry."""
    LOGGER.debug("Unloading entry: %s", entry.entry_id)
    # Unload platforms
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def config_entry_update_listener(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)
