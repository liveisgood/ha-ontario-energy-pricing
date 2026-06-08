"""Config flow for Ontario Energy Pricing integration."""

from __future__ import annotations

import traceback
from typing import Any, Final

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_ADMIN_FEE,
    CONF_CHEAPEST_WINDOWS,
    CONF_LOCATION,
    CONF_WINDOW_HOURS,
    DEFAULT_WINDOW_HOURS,
    DOMAIN,
    LOGGER,
    MAX_WINDOW_HOURS,
    MIN_WINDOW_HOURS,
)

STEP_USER_DATA_SCHEMA: Final = vol.Schema(
    {
        vol.Required(CONF_LOCATION): str,
        vol.Required(CONF_ADMIN_FEE, default=0.0): vol.All(
            vol.Coerce(float), vol.Range(min=0)
        ),
    }
)

RECONFIGURE_SCHEMA: Final = vol.Schema(
    {
        vol.Required(CONF_ADMIN_FEE): vol.All(vol.Coerce(float), vol.Range(min=0)),
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
        self._windows: list[dict[str, Any]] = []

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

            # Store user input, proceed to window setup
            LOGGER.debug(
                "[CONFIG_FLOW] User completed basic setup: admin_fee=%s, location=%s",
                self._admin_fee,
                self._location,
            )
            return await self.async_step_setup_windows()

        LOGGER.debug(
            "[CONFIG_FLOW] Showing user form (no input yet), schema=%s",
            STEP_USER_DATA_SCHEMA,
        )
        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_setup_windows(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 2: Setup cheapest-hours binary sensors (optional)."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # If user clicked "add", go to add step
            if user_input.get("add_window"):
                return await self.async_step_add_window()

            # If user selected a window to remove, go to remove step
            if user_input.get("remove_window"):
                self._remove_target = user_input["remove_window"]
                return await self.async_step_remove_window()

            # User is done - create entry with options
            new_options = {
                CONF_ADMIN_FEE: self._admin_fee,
                CONF_LOCATION: self._location,
                CONF_CHEAPEST_WINDOWS: self._windows,
            }

            LOGGER.debug("[CONFIG_FLOW] Creating entry with options: %s", new_options)
            try:
                result = self.async_create_entry(
                    title=f"Ontario Energy Pricing - {self._location}",
                    data=new_options,
                )
                LOGGER.debug(
                    "[CONFIG_FLOW] Entry created successfully: version=%s, entry_id=%s",
                    result.get("version"),
                    result.get("entry_id"),
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
                    step_id="setup_windows",
                    data_schema=self._setup_windows_schema(),
                    errors=errors,
                )

        # Show setup windows form
        return self.async_show_form(
            step_id="setup_windows",
            data_schema=self._setup_windows_schema(),
            description_placeholders={
                "existing_windows": self._get_windows_description()
            },
        )

    def _setup_windows_schema(self) -> vol.Schema:
        """Generate schema for the setup windows step."""
        schema_dict: dict[object, object] = {
            vol.Optional("add_window", default=False): bool,
        }

        if self._windows:
            # Build remove dropdown from existing windows
            remove_options = {"": "(none)"}
            remove_options.update({w["name"]: w["name"] for w in self._windows})
            schema_dict[vol.Optional("remove_window", default="")] = vol.In(
                remove_options
            )

        return vol.Schema(schema_dict)

    def _get_windows_description(self) -> str:
        """Get description showing existing windows."""
        if not self._windows:
            return (
                "No cheapest-hours sensors configured yet. "
                "Check 'Add cheapest window' to create one."
            )

        window_list = "\n".join(
            f"  - {w['name']}: {w[CONF_WINDOW_HOURS]} cheapest hours"
            for w in self._windows
        )
        return (
            "Existing cheapest-hours sensors:\n"
            f"{window_list}\n\n"
            "Check 'Add cheapest window' to create a new sensor, "
            "or select one to remove."
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle reconfiguration of the integration."""
        LOGGER.debug(
            "[CONFIG_FLOW] async_step_reconfigure called, user_input=%s",
            user_input,
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
                vol.Required(CONF_ADMIN_FEE, default=current_fee): vol.All(
                    vol.Coerce(float), vol.Range(min=0)
                ),
                vol.Required(CONF_LOCATION, default=current_location): str,
            }
        )
        return self.async_show_form(step_id="reconfigure", data_schema=schema)


class OntarioEnergyPricingOptionsFlow(OptionsFlow):
    """Handle options flow for Ontario Energy Pricing.

    Step 1 (init): Admin fee setting
    Step 2 (add_window): Add a new cheapest-hours binary sensor
    Step 3 (manage_windows): Review/remove existing cheapest-hours sensors
    """

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry
        # Work with a mutable copy of the cheapest windows list
        self._windows: list[dict[str, Any]] = list(
            config_entry.options.get(CONF_CHEAPEST_WINDOWS, [])
        )

        LOGGER.debug(
            "[OPTIONS_FLOW] Initialized, entry_id=%s, data=%s",
            config_entry.entry_id,
            config_entry.data,
        )

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 1: Manage admin fee and choose action."""
        LOGGER.debug("[OPTIONS_FLOW] async_step_init called, user_input=%s", user_input)

        if user_input is not None:
            # Save admin fee, then check actions
            new_options = {
                CONF_ADMIN_FEE: user_input[CONF_ADMIN_FEE],
                CONF_CHEAPEST_WINDOWS: self._windows,
            }

            # If user clicked "add", go to add step
            if user_input.get("add_window"):
                return await self.async_step_add_window()

            # If user selected a window to remove, go to remove step
            if user_input.get("remove_window"):
                self._remove_target = user_input["remove_window"]
                return await self.async_step_remove_window()

            LOGGER.debug(
                "[OPTIONS_FLOW] Creating options entry with data=%s", new_options
            )
            try:
                result = self.async_create_entry(title="", data=new_options)
                LOGGER.debug("[OPTIONS_FLOW] Options entry created: %s", result)
                return result
            except Exception as err:
                LOGGER.error(
                    "[OPTIONS_FLOW] FAILED to create options entry: %s\n%s",
                    err,
                    traceback.format_exc(),
                )
                raise

        current_fee = self.config_entry.options.get(
            CONF_ADMIN_FEE,
            self.config_entry.data.get(CONF_ADMIN_FEE, 0.0),
        )

        # Build description showing existing windows
        if self._windows:
            window_list = "\n".join(
                f"  - {w['name']}: {w[CONF_WINDOW_HOURS]} cheapest hours"
                for w in self._windows
            )
            desc = (
                "Adjust your energy pricing settings.\n\n"
                "Existing cheapest-hours sensors:\n"
                f"{window_list}\n\n"
                "Check 'Add cheapest window' to create a new sensor, "
                "or select one to remove."
            )
        else:
            desc = (
                "Adjust your energy pricing settings.\n\n"
                "No cheapest-hours sensors configured yet. "
                "Check 'Add cheapest window' to create one."
            )

        # Build remove dropdown from existing windows
        remove_options = {"": "(none)"}
        remove_options.update({w["name"]: w["name"] for w in self._windows})

        schema_dict: dict[object, object] = {
            vol.Required(
                CONF_ADMIN_FEE,
                default=float(current_fee),
            ): vol.All(vol.Coerce(float), vol.Range(min=0)),
            vol.Optional("add_window", default=False): bool,
        }

        if self._windows:
            schema_dict[vol.Optional("remove_window", default="")] = vol.In(
                remove_options
            )

        schema = vol.Schema(schema_dict)

        return self.async_show_form(
            step_id="init",
            data_schema=schema,
            description_placeholders={"existing_windows": desc},
        )

    async def async_step_add_window(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 2: Add a new cheapest-hours binary sensor."""
        errors: dict[str, str] = {}

        if user_input is not None:
            window_name = user_input.get("name", "").strip()
            window_hours = user_input.get(CONF_WINDOW_HOURS, DEFAULT_WINDOW_HOURS)

            # Validate name is not empty and not a duplicate
            if not window_name:
                errors["name"] = "name_required"
            elif any(w.get("name") == window_name for w in self._windows):
                errors["name"] = "name_duplicate"
            else:
                self._windows.append(
                    {"name": window_name, CONF_WINDOW_HOURS: window_hours}
                )
                LOGGER.debug(
                    "[OPTIONS_FLOW] Added window: name=%s, hours=%s",
                    window_name,
                    window_hours,
                )
                # Go back to init to save or add more
                return await self.async_step_init()

        schema = vol.Schema(
            {
                vol.Required("name"): str,
                vol.Required(
                    CONF_WINDOW_HOURS,
                    default=DEFAULT_WINDOW_HOURS,
                ): vol.All(
                    vol.Coerce(int),
                    vol.Range(min=MIN_WINDOW_HOURS, max=MAX_WINDOW_HOURS),
                ),
            }
        )

        return self.async_show_form(
            step_id="add_window",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_remove_window(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 3: Confirm removal of a cheapest-hours sensor."""
        target = getattr(self, "_remove_target", "")

        if user_input is not None and user_input.get("confirm_remove"):
            # Remove the window
            self._windows = [w for w in self._windows if w.get("name") != target]
            LOGGER.debug("[OPTIONS_FLOW] Removed window: %s", target)
            return await self.async_step_init()

        return self.async_show_form(
            step_id="remove_window",
            data_schema=vol.Schema(
                {vol.Required("confirm_remove", default=True): bool}
            ),
            description_placeholders={"name": target},
        )
