"""Diagnostics support for Ontario Energy Pricing."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Final

from homeassistant.helpers.diagnostics import async_redact_data

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

    from .coordinator import OntarioEnergyPricingCoordinator

# Redact user's location for privacy
TO_REDACT: Final = {"location"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator: OntarioEnergyPricingCoordinator = entry.runtime_data

    diagnostics: dict[str, Any] = {
        "entry": {
            "entry_id": entry.entry_id,
            "domain": entry.domain,
            "title": entry.title,
            "version": entry.version,
            "data": async_redact_data(dict(entry.data), TO_REDACT),
        },
        "coordinator": {
            "last_update_success": coordinator.last_update_success,
            "update_interval": str(coordinator.update_interval),
        },
    }

    if coordinator.data:
        data = coordinator.data
        diagnostics["data"] = {
            "current_lmp_kwh": data.current_lmp_kwh,
            "hour_average_lmp_kwh": data.hour_average_lmp_kwh,
            "global_adjustment": data.global_adjustment,
            "total_rate": data.total_rate,
            "admin_fee": data.admin_fee,
            "delivery_date": data.delivery_date,
            "delivery_hour": data.delivery_hour,
            "trade_month": data.trade_month,
            "interval_count": len(data.intervals),
        }
    else:
        diagnostics["data"] = None

    return diagnostics
