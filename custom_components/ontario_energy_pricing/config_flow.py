"""Config flow for Ontario Energy Pricing integration."""
from __future__ import annotations

from typing import Any, TYPE_CHECKING

import voluptuous as vol  # type: ignore
from homeassistant.config_entries import ConfigFlow, config_entries  # type: ignore
from homeassistant.const import CONF_API_KEY  # type: ignore
from homeassistant.core import HomeAssistant, callback  # type: ignore
from homeassistant.data_entry_flow import FlowResult  # type: ignore
from homeassistant.helpers.aiohttp_client import async_get_clientsession  # type: ignore

from .const import (
    CONF_ADMIN_FEE,
    CONF_LOCATION,
    CONF_ZONE,
    DOMAIN,
    LOGGER,
)
from .exceptions import GridStatusAuthError, GridStatusConnectionError
from .gridstatus import GridStatusClient

if TYPE_CHECKING:
    pass


def _validate_positive_float(value: float | int | str) -> float:
    """Validate that value is a positive float."""
    try:
        val = float(value)
        if val < 0:
            raise vol.Invalid("Value must be non-negative")
        return val
    except (ValueError, TypeError) as err:
        raise vol.Invalid(f"Invalid value: {err}")


STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_KEY): str,
        vol.Required(CONF_ADMIN_FEE, default=0.0): _validate_positive_float,
        vol.Required(CONF_LOCATION): str,
    }
)


class OntarioEnergyPricingConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Ontario Energy Pricing."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._api_key: str | None = None
        self._admin_fee: float = 0.0
        self._location: str | None = None
        self._available_zones: list[str] = []

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
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
                    "location": existing.data.get(CONF_LOCATION, "Unknown"),
                    "zone": existing.data.get(CONF_ZONE, "Unknown")
                }
            )

        errors: dict[str, str] = {}
        if user_input is not None:
            self._api_key = user_input[CONF_API_KEY]
            self._admin_fee = user_input[CONF_ADMIN_FEE]
            self._location = user_input[CONF_LOCATION]

            # Proceed to API validation
            return await self.async_step_api_test()

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_api_test(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Test API connection and discover zones."""
        errors: dict[str, str] = {}
        error_detail: str = ""

        if self._api_key is None:
            return await self.async_step_user()

        # Test API connection and get available zones
        hass: HomeAssistant = self.hass
        session = async_get_clientsession(hass)
        client = GridStatusClient(api_key=self._api_key, session=session)

        try:
            LOGGER.debug("Testing API connection with provided key")
            # Try to get available zones to validate API and get zone list
            self._available_zones = await client.async_get_available_zones()
            LOGGER.debug("Found %d available zones", len(self._available_zones))

            # If zones found, try to match location
            matched_zone = self._match_zone_to_location(self._available_zones)
            if matched_zone:
                # Store matched zone and skip to completion
                data = {
                    CONF_API_KEY: self._api_key,
                    CONF_ADMIN_FEE: self._admin_fee,
                    CONF_LOCATION: self._location,
                    CONF_ZONE: matched_zone,
                }
                return self.async_create_entry(
                    title=f"Ontario Energy Pricing - {self._location}",
                    data=data,
                )

            # No good match, show zone selection
            return await self.async_step_zone_select()

        except GridStatusAuthError:
            LOGGER.error("API authentication failed")
            errors["base"] = "invalid_auth"
        except GridStatusConnectionError:
            LOGGER.error("Failed to connect to GridStatus API")
            errors["base"] = "cannot_connect"
        except Exception as err:
            LOGGER.exception("Unexpected error during API test: %s", err)
            errors["base"] = "unknown"
            error_detail = str(err)

        return self.async_show_form(
            step_id="api_test",
            errors=errors,
            description_placeholders={"error_detail": error_detail},
        )

    def _match_zone_to_location(self, zones: list[str]) -> str | None:
        """Try to match user's location to available zones.

        Uses simple string matching - first zone containing location substring.
        Falls back to "ONTARIO" if no match found.
        """
        if not self._location or not zones:
            return None

        location_lower = self._location.lower()

        # Try exact match first
        for zone in zones:
            if location_lower == zone.lower():
                return zone

        # Try substring match
        for zone in zones:
            if location_lower in zone.lower() or zone.lower() in location_lower:
                return zone

        # No match found
        return None

    async def async_step_zone_select(
        self, user_input: dict[str, str] | None = None
    ) -> FlowResult:
        """Handle zone selection."""
        errors: dict[str, str] = {}

        # Build zone options with "ONTARIO" as fallback
        zone_options = {
            "ONTARIO": "ONTARIO (province-wide average)",
        }
        for zone in self._available_zones:
            zone_options[zone] = zone

        if user_input is not None:
            selected_zone = user_input.get(CONF_ZONE, "ONTARIO")
            data = {
                CONF_API_KEY: self._api_key,
                CONF_ADMIN_FEE: self._admin_fee,
                CONF_LOCATION: self._location,
                CONF_ZONE: selected_zone,
            }
            return self.async_create_entry(
                title=f"Ontario Energy Pricing - {self._location}",
                data=data,
            )

        # Try to pre-select best match
        default_zone = self._match_zone_to_location(self._available_zones) or "ONTARIO"
        schema = vol.Schema(
            {
                vol.Required(CONF_ZONE, default=default_zone): vol.In(zone_options),
            }
        )

        return self.async_show_form(
            step_id="zone_select",
            data_schema=schema,
            errors=errors,
        )


class OntarioEnergyPricingOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Ontario Energy Pricing."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # Build form with current values
        schema = vol.Schema({
            vol.Required(
                CONF_ADMIN_FEE,
                default=self.config_entry.data.get(CONF_ADMIN_FEE, 0.0)
            ): vol.Coerce(float),
            vol.Required(
                CONF_ZONE,
                default=self.config_entry.data.get(CONF_ZONE, "ONTARIO")
            ): str,
        })

        return self.async_show_form(
            step_id="init",
            data_schema=schema,
        )
