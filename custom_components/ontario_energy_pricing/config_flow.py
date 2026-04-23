"""Config flow for Ontario Energy Pricing integration."""

from __future__ import annotations

import traceback
from typing import Any, Final

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import CONF_ADMIN_FEE, CONF_LOCATION, DOMAIN, LOGGER


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

RECONFIGURE_SCHEMA: Final = vol.Schema(
    {
        vol.Required(CONF_ADMIN_FEE): _validate_non_negative_float,
        vol.Required(CONF_LOCATION): str,
    }
)


class OntarioEnergyPricingConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Ontario Energy Pricing."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._admin_fee: float = 0.0
        self._location: str | None = None
        LOGGER.debug(
            "[CONFIG_FLOW] __init__ called, flow_id=%s",
            getattr(self, "flow_id", "N/A"),
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> OntarioEnergyPricingOptionsFlow:
        """Get the options flow for this handler."""
        LOGGER.debug(
            "[CONFIG_FLOW] async_get_options_flow called for entry=%s",
            config_entry.entry_id,
        )
        return OntarioEnergyPricingOptionsFlow(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        LOGGER.debug("[CONFIG_FLOW] async_step_user called, user_input=%s", user_input)

        # Set unique ID to prevent duplicate entries
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        errors: dict[str, str] = {}

        if user_input is not None:
            LOGGER.debug(
                "[CONFIG_FLOW] Processing user_input: raw=%s, keys=%s",
                user_input,
                list(user_input.keys()),
            )
            try:
                self._admin_fee = user_input[CONF_ADMIN_FEE]
                self._location = user_input[CONF_LOCATION]
                LOGGER.debug(
                    "[CONFIG_FLOW] Parsed values: admin_fee=%s (type=%s), location=%s (type=%s)",
                    self._admin_fee,
                    type(self._admin_fee).__name__,
                    self._location,
                    type(self._location).__name__,
                )
            except (KeyError, vol.Invalid) as err:
                LOGGER.error(
                    "[CONFIG_FLOW] FAILED to parse user_input: %s\n%s",
                    err,
                    traceback.format_exc(),
                )
                errors["base"] = "unknown"
                return self.async_show_form(
                    step_id="user",
                    data_schema=STEP_USER_DATA_SCHEMA,
                    errors=errors,
                )

            # Create entry - no API key or zone needed!
            data = {
                CONF_ADMIN_FEE: self._admin_fee,
                CONF_LOCATION: self._location,
            }
            LOGGER.debug(
                "[CONFIG_FLOW] Creating entry: title='Ontario Energy Pricing - %s', data=%s",
                self._location,
                data,
            )
            try:
                result = self.async_create_entry(
                    title=f"Ontario Energy Pricing - {self._location}",
                    data=data,
                )
                LOGGER.debug(
                    "[CONFIG_FLOW] Entry created successfully: version=%s, entry_id=%s, result_keys=%s",
                    result.get("version"),
                    result.get("entry_id"),
                    list(result.keys())
                    if isinstance(result, dict)
                    else type(result).__name__,
                )
                return result
            except Exception as err:
                LOGGER.error(
                    "[CONFIG_FLOW] FAILED to create entry: %s\n%s",
                    err,
                    traceback.format_exc(),
                )
                errors["base"] = "unknown"
                return self.async_show_form(
                    step_id="user",
                    data_schema=STEP_USER_DATA_SCHEMA,
                    errors=errors,
                )

        LOGGER.debug(
            "[CONFIG_FLOW] Showing user form (no input yet), schema=%s",
            STEP_USER_DATA_SCHEMA,
        )
        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle reconfiguration of the integration."""
        LOGGER.debug(
            "[CONFIG_FLOW] async_step_reconfigure called, user_input=%s", user_input
        )
        entry = self._get_reconfigure_entry()

        if user_input is not None:
            LOGGER.debug(
                "[CONFIG_FLOW] Reconfigure: processing user_input=%s", user_input
            )
            try:
                admin_fee = user_input[CONF_ADMIN_FEE]
                location = user_input[CONF_LOCATION]
                LOGGER.debug(
                    "[CONFIG_FLOW] Reconfigure: admin_fee=%s, location=%s",
                    admin_fee,
                    location,
                )
            except KeyError as err:
                LOGGER.error(
                    "[CONFIG_FLOW] Reconfigure FAILED to parse input: %s\n%s",
                    err,
                    traceback.format_exc(),
                )
                errors = {"base": "unknown"}
                return self.async_show_form(
                    step_id="reconfigure",
                    data_schema=RECONFIGURE_SCHEMA,
                    errors=errors,
                )

            return self.async_update_reload_and_abort(
                entry,
                data_updates={
                    CONF_ADMIN_FEE: admin_fee,
                    CONF_LOCATION: location,
                },
            )

        # Pre-fill with current values
        current_fee = entry.data.get(CONF_ADMIN_FEE, 0.0)
        current_location = entry.data.get(CONF_LOCATION, "")
        LOGGER.debug(
            "[CONFIG_FLOW] Reconfigure: showing form, current fee=%s, location=%s",
            current_fee,
            current_location,
        )
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_ADMIN_FEE, default=current_fee
                ): _validate_non_negative_float,
                vol.Required(CONF_LOCATION, default=current_location): str,
            }
        )
        return self.async_show_form(step_id="reconfigure", data_schema=schema)


class OntarioEnergyPricingOptionsFlow(OptionsFlow):
    """Handle options flow for Ontario Energy Pricing."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry
        LOGGER.debug(
            "[OPTIONS_FLOW] Initialized, entry_id=%s, data=%s",
            config_entry.entry_id,
            config_entry.data,
        )

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage options."""
        LOGGER.debug("[OPTIONS_FLOW] async_step_init called, user_input=%s", user_input)
        if user_input is not None:
            LOGGER.debug(
                "[OPTIONS_FLOW] Creating options entry with data=%s", user_input
            )
            try:
                result = self.async_create_entry(title="", data=user_input)
                LOGGER.debug("[OPTIONS_FLOW] Options entry created: %s", result)
                return result
            except Exception as err:
                LOGGER.error(
                    "[OPTIONS_FLOW] FAILED to create options entry: %s\n%s",
                    err,
                    traceback.format_exc(),
                )
                raise

        current_fee = self.config_entry.data.get(CONF_ADMIN_FEE, 0.0)
        LOGGER.debug(
            "[OPTIONS_FLOW] Showing options form, current admin_fee=%s (type=%s)",
            current_fee,
            type(current_fee).__name__,
        )
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_ADMIN_FEE,
                    default=current_fee,
                ): vol.Coerce(float),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
