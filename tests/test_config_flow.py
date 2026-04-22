"""Tests for configuration flow."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from custom_components.ontario_energy_pricing.config_flow import (
    CONF_ADMIN_FEE,
    CONF_LOCATION,
    OntarioEnergyPricingConfigFlow,
)
from custom_components.ontario_energy_pricing.const import DOMAIN


@pytest.fixture
def mock_flow(mock_hass) -> OntarioEnergyPricingConfigFlow:
    """Create a mock config flow instance."""
    flow = OntarioEnergyPricingConfigFlow()
    flow.hass = mock_hass
    flow._admin_fee = 0.0
    flow._location = None
    return flow


@pytest.mark.asyncio
async def test_config_flow_user_step(mock_flow) -> None:
    """Test that user step shows input form."""
    result = await mock_flow.async_step_user(user_input=None)
    assert result["type"] == "form"
    assert result["step_id"] == "user"


@pytest.mark.asyncio
async def test_config_flow_valid_input(mock_flow) -> None:
    """Test valid user input stores data and creates entry."""
    user_input = {
        CONF_ADMIN_FEE: 1.45,
        CONF_LOCATION: "Oakville, ON",
    }

    result = await mock_flow.async_step_user(user_input=user_input)

    assert result["type"] == "create_entry"
    assert result["data"][CONF_ADMIN_FEE] == 1.45
    assert result["data"][CONF_LOCATION] == "Oakville, ON"


@pytest.mark.asyncio
async def test_config_flow_no_api_key_required(mock_flow) -> None:
    """Test that config flow works without API key (IESO direct)."""
    user_input = {
        CONF_ADMIN_FEE: 2.0,
        CONF_LOCATION: "Toronto",
    }

    result = await mock_flow.async_step_user(user_input=user_input)

    assert result["type"] == "create_entry"
    # Should only have admin_fee and location
    assert "admin_fee" in result["data"]
    assert "location" in result["data"]
    assert "api_key" not in result["data"]  # Not needed for IESO direct


@pytest.mark.asyncio
async def test_config_flow_zero_admin_fee(mock_flow) -> None:
    """Test config flow accepts zero admin fee."""
    user_input = {
        CONF_ADMIN_FEE: 0.0,
        CONF_LOCATION: "Ottawa",
    }

    result = await mock_flow.async_step_user(user_input=user_input)

    assert result["type"] == "create_entry"
    assert result["data"][CONF_ADMIN_FEE] == 0.0


@pytest.mark.asyncio
async def test_config_flow_already_configured(mock_hass, mock_config_entry) -> None:
    """Test that config flow aborts if already configured."""
    flow = OntarioEnergyPricingConfigFlow()
    flow.hass = mock_hass
    flow.hass.data = {DOMAIN: {mock_config_entry.entry_id: {}}}

    # Mock _async_current_entries to return existing entry
    flow._async_current_entries = MagicMock(return_value=[mock_config_entry])

    result = await flow.async_step_user(user_input=None)

    assert result["type"] == "abort"


@pytest.mark.asyncio
async def test_config_entry_structure(mock_flow) -> None:
    """Test that created config entry has required data fields."""
    user_input = {
        CONF_ADMIN_FEE: 1.45,
        CONF_LOCATION: "Oakville, ON",
    }

    result = await mock_flow.async_step_user(user_input=user_input)

    assert result["type"] == "create_entry"
    data = result["data"]

    # Required fields
    assert CONF_ADMIN_FEE in data
    assert CONF_LOCATION in data

    # Should NOT have GridStatus-specific fields
    assert "api_key" not in data
    assert "zone" not in data


@pytest.mark.asyncio
async def test_options_flow_init(mock_hass, mock_config_entry) -> None:
    """Test options flow initialization."""
    from custom_components.ontario_energy_pricing.config_flow import (
        OntarioEnergyPricingOptionsFlow,
    )

    options_flow = OntarioEnergyPricingOptionsFlow(mock_config_entry)

    result = await options_flow.async_step_init(user_input=None)

    assert result["type"] == "form"
    assert result["step_id"] == "init"


@pytest.mark.asyncio
async def test_options_flow_update_admin_fee(mock_hass, mock_config_entry) -> None:
    """Test updating admin fee in options flow."""
    from custom_components.ontario_energy_pricing.config_flow import (
        OntarioEnergyPricingOptionsFlow,
    )

    options_flow = OntarioEnergyPricingOptionsFlow(mock_config_entry)

    user_input = {
        CONF_ADMIN_FEE: 2.50,
    }

    result = await options_flow.async_step_init(user_input=user_input)

    assert result["type"] == "create_entry"
    assert result["data"][CONF_ADMIN_FEE] == 2.50
