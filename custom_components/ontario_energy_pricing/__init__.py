"""Ontario Energy Pricing integration for Home Assistant.

Provides sensors for Ontario electricity pricing components:
- Current LMP (Locational Marginal Price)
- 24-hour average LMP
- Global Adjustment
- Total Rate (LMP + GA + Admin Fee)
"""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry  # type: ignore
from homeassistant.const import Platform  # type: ignore
from homeassistant.core import HomeAssistant, ServiceCall  # type: ignore

from .const import DOMAIN, LOGGER

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Ontario Energy Pricing from a config entry."""
    LOGGER.debug("Setting up entry: %s", entry.entry_id)

    # Store entry data for coordinators
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "api_key": entry.data["api_key"],
        "admin_fee": entry.data.get("admin_fee", 0.0),
        "location": entry.data["location"],
        "zone": entry.data.get("zone", "ONTARIO"),
        "coordinators": [],  # Will be populated by sensor platform
    }

    # Forward to sensor platform
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register refresh service
    async def async_refresh_service(call: ServiceCall) -> None:
        """Handle refresh service call."""
        LOGGER.debug("Refresh service called")
        entry_data = hass.data[DOMAIN][entry.entry_id]
        coordinators = entry_data.get("coordinators", [])
        LOGGER.debug("Refreshing %d coordinators", len(coordinators))
        for coordinator in coordinators:
            await coordinator.async_refresh()

    hass.services.async_register(DOMAIN, "refresh", async_refresh_service)

    LOGGER.debug("Setup complete for entry: %s", entry.entry_id)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    LOGGER.debug("Unloading entry: %s", entry.entry_id)

    # Remove refresh service
    hass.services.async_remove(DOMAIN, "refresh")

    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def config_entry_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
