"""Config flow for Ontario Energy Pricing integration."""

from __future__ import annotations

from typing import Any, Final

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import CONF_ADMIN_FEE, CONF_LOCATION


def _validate_non_negative_float(value: float | int | str) -> float:
    """Validate that value is a non-negative float."""
    try:
        val = float(value)
        if val < 0:
            raise vol.Invalid("Value must be non-negative")
        return val
    except (ValueError, TypeError) as err:
        raise vol.Invalid(f"Invalid value: {err}")


STEP_USER_DATA_SCHEMA: Final = vol.Schema(
    {
        vol.Required(CONF_LOCATION): str,
        vol.Required(CONF_ADMIN_FEE, default=0.0): _validate_non_negative_float,
    }
)


class OntarioEnergyPricingConfigFlow(ConfigFlow):
    """Handle a config flow for Ontario Energy Pricing."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._admin_fee: float = 0.0
        self._location: str | None = None

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> OntarioEnergyPricingOptionsFlow:
        """Get the options flow for this handler."""
        return OntarioEnergyPricingOptionsFlow(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        # Check if already configured
        entries = self._async_current_entries()
        if entries:
            existing = entries[0]
            return self.async_abort(
                reason="already_configured",
                description_placeholders={
                    "location": existing.data.get(CONF_LOCATION, "Unknown")
                },
            )

        errors: dict[str, str] = {}

        if user_input is not None:
            self._admin_fee = user_input[CONF_ADMIN_FEE]
            self._location = user_input[CONF_LOCATION]
            # Create entry - no API key or zone needed!
            data = {
                CONF_ADMIN_FEE: self._admin_fee,
                CONF_LOCATION: self._location,
            }
            return self.async_create_entry(
                title=f"Ontario Energy Pricing - {self._location}",
                data=data,
            )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )


class OntarioEnergyPricingOptionsFlow(OptionsFlow):
    """Handle options flow for Ontario Energy Pricing."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_ADMIN_FEE,
                    default=self.config_entry.data.get(CONF_ADMIN_FEE, 0.0),
                ): vol.Coerce(float),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
