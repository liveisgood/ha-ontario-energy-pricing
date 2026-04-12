"""Tests for configuration flow."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from custom_components.ontario_energy_pricing.config_flow import (
    CONF_ADMIN_FEE,
    CONF_API_KEY,
    CONF_LOCATION,
    CONF_ZONE,
    OntarioEnergyPricingConfigFlow,
)
from custom_components.ontario_energy_pricing.const import DOMAIN
from custom_components.ontario_energy_pricing.exceptions import (
    GridStatusAuthError,
    GridStatusConnectionError,
)


@pytest.fixture
def mock_flow(mock_hass) -> OntarioEnergyPricingConfigFlow:
    """Create a mock config flow instance."""
    flow = OntarioEnergyPricingConfigFlow()
    flow.hass = mock_hass
    flow._api_key = None
    flow._admin_fee = 0.0
    flow._location = None
    flow._available_zones = []
    return flow


@pytest.mark.asyncio
async def test_config_flow_user_step(mock_flow) -> None:
    """Test that user step shows input form."""
    result = await mock_flow.async_step_user(user_input=None)
    assert result["type"] == "form"
    assert result["step_id"] == "user"


@pytest.mark.asyncio
async def test_config_flow_valid_input(mock_flow) -> None:
    """Test valid user input stores data."""
    user_input = {
        CONF_API_KEY: "test_api_key",
        CONF_ADMIN_FEE: 0.025,
        CONF_LOCATION: "Oakville",
    }
    with patch.object(mock_flow, "async_step_api_test"):
        await mock_flow.async_step_user(user_input=user_input)
    assert mock_flow._api_key == "test_api_key"
    assert mock_flow._admin_fee == 0.025
    assert mock_flow._location == "Oakville"


@pytest.mark.asyncio
async def test_config_flow_api_test_success(mock_flow) -> None:
    """Test successful API test creates entry."""
    mock_flow._api_key = "test_key"
    mock_flow._admin_fee = 0.025
    mock_flow._location = "Oakville"
    with patch("custom_components.ontario_energy_pricing.config_flow.async_get_clientsession"):
        with patch("custom_components.ontario_energy_pricing.config_flow.GridStatusClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.async_get_available_zones = AsyncMock(
                return_value=["OAKVILLE", "TORONTO", "ONTARIO"],
            )
            mock_client_class.return_value = mock_client
            result = await mock_flow.async_step_api_test(user_input=None)
    assert result["type"] == "create_entry"
    assert result["data"][CONF_ZONE] == "OAKVILLE"


@pytest.mark.asyncio
async def test_config_flow_auth_error(mock_flow) -> None:
    """Test API test shows error on auth failure."""
    mock_flow._api_key = "bad_key"
    mock_flow._admin_fee = 0.025
    mock_flow._location = "Oakville"
    with patch("custom_components.ontario_energy_pricing.config_flow.async_get_clientsession"):
        with patch("custom_components.ontario_energy_pricing.config_flow.GridStatusClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.async_get_available_zones = AsyncMock(
                side_effect=GridStatusAuthError("Invalid key"),
            )
            mock_client_class.return_value = mock_client
            result = await mock_flow.async_step_api_test(user_input=None)
    assert result["type"] == "form"
    assert result["step_id"] == "api_test"


@pytest.mark.asyncio
async def test_zone_matching_exact(mock_flow) -> None:
    """Test exact zone matching."""
    mock_flow._location = "Oakville"
    zones = ["OAKVILLE", "TORONTO", "OTTAWA"]
    matched = mock_flow._match_zone_to_location(zones)
    assert matched == "OAKVILLE"


@pytest.mark.asyncio
async def test_zone_matching_substring(mock_flow) -> None:
    """Test substring zone matching."""
    mock_flow._location = "oakville"
    zones = ["OAKVILLE_ZONE", "TORONTO", "ONTARIO"]
    matched = mock_flow._match_zone_to_location(zones)
    assert matched == "OAKVILLE_ZONE"


@pytest.mark.asyncio
async def test_config_entry_structure(mock_flow) -> None:
    """Test that created config entry has required data."""
    mock_flow._api_key = "test_key"
    mock_flow._admin_fee = 0.025
    mock_flow._location = "Oakville"
    with patch("custom_components.ontario_energy_pricing.config_flow.async_get_clientsession"):
        with patch("custom_components.ontario_energy_pricing.config_flow.GridStatusClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.async_get_available_zones = AsyncMock(
                return_value=["OAKVILLE", "ONTARIO"],
            )
            mock_client_class.return_value = mock_client
            result = await mock_flow.async_step_api_test(user_input=None)
    assert result["type"] == "create_entry"
    data = result["data"]
    assert CONF_API_KEY in data
    assert CONF_ADMIN_FEE in data
    assert CONF_LOCATION in data
    assert CONF_ZONE in data
