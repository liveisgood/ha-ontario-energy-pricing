"""Tests for data update coordinators."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from homeassistant.helpers.update_coordinator import UpdateFailed
from custom_components.ontario_energy_pricing.const import UPDATE_INTERVAL_LMP, UPDATE_INTERVAL_GA, UPDATE_INTERVAL_24H_AVG
from custom_components.ontario_energy_pricing.coordinator import LMPCoordinator, LMP24hAverageCoordinator, GlobalAdjustmentCoordinator
from custom_components.ontario_energy_pricing.exceptions import GridStatusAuthError, GridStatusAPIError, GridStatusConnectionError, IESOXMLParseError
from custom_components.ontario_energy_pricing.models import LMPCurrentPrice, LMPHistoricalData, GlobalAdjustment


@pytest.mark.asyncio
async def test_lmp_coordinator_update_success(mock_hass, sample_lmp_price) -> None:
    """Test LMPCoordinator successfully fetches data."""
    with patch("custom_components.ontario_energy_pricing.coordinator.async_get_clientsession"):
        with patch("custom_components.ontario_energy_pricing.coordinator.GridStatusClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.async_get_current_lmp = AsyncMock(return_value=sample_lmp_price)
            mock_client_class.return_value = mock_client
            coordinator = LMPCoordinator(hass=mock_hass, api_key="test_key", zone="OAKVILLE")
            result = await coordinator._async_update_data()
    assert isinstance(result, LMPCurrentPrice)
    assert result.price == 0.0895


@pytest.mark.asyncio
async def test_lmp_coordinator_update_failure(mock_hass) -> None:
    """Test LMPCoordinator raises UpdateFailed on API error."""
    with patch("custom_components.ontario_energy_pricing.coordinator.async_get_clientsession"):
        with patch("custom_components.ontario_energy_pricing.coordinator.GridStatusClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.async_get_current_lmp = AsyncMock(side_effect=GridStatusAPIError("API error"))
            mock_client_class.return_value = mock_client
            coordinator = LMPCoordinator(hass=mock_hass, api_key="test_key", zone="OAKVILLE")
            with pytest.raises(UpdateFailed) as exc_info:
                await coordinator._async_update_data()
    assert "API error" in str(exc_info.value)


@pytest.mark.asyncio
async def test_lmp_coordinator_auth_error(mock_hass) -> None:
    """Test LMPCoordinator raises UpdateFailed on auth error."""
    with patch("custom_components.ontario_energy_pricing.coordinator.async_get_clientsession"):
        with patch("custom_components.ontario_energy_pricing.coordinator.GridStatusClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.async_get_current_lmp = AsyncMock(side_effect=GridStatusAuthError("Invalid key"))
            mock_client_class.return_value = mock_client
            coordinator = LMPCoordinator(hass=mock_hass, api_key="bad_key", zone="OAKVILLE")
            with pytest.raises(UpdateFailed) as exc_info:
                await coordinator._async_update_data()
    assert "Authentication" in str(exc_info.value)


@pytest.mark.asyncio
async def test_lmp_coordinator_update_interval(mock_hass) -> None:
    """Test LMPCoordinator has correct update interval."""
    with patch("custom_components.ontario_energy_pricing.coordinator.async_get_clientsession"):
        with patch("custom_components.ontario_energy_pricing.coordinator.GridStatusClient"):
            coordinator = LMPCoordinator(hass=mock_hass, api_key="test_key", zone="OAKVILLE")
    assert coordinator.update_interval.total_seconds() == UPDATE_INTERVAL_LMP


@pytest.mark.asyncio
async def test_lmp_24h_coordinator_update_success(mock_hass, sample_lmp_history) -> None:
    """Test LMP24hAverageCoordinator successfully fetches data."""
    with patch("custom_components.ontario_energy_pricing.coordinator.async_get_clientsession"):
        with patch("custom_components.ontario_energy_pricing.coordinator.GridStatusClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.async_get_24h_history = AsyncMock(return_value=sample_lmp_history)
            mock_client_class.return_value = mock_client
            coordinator = LMP24hAverageCoordinator(hass=mock_hass, api_key="test_key", zone="OAKVILLE")
            result = await coordinator._async_update_data()
    assert isinstance(result, LMPHistoricalData)


@pytest.mark.asyncio
async def test_ga_coordinator_update_success(mock_hass, sample_global_adjustment) -> None:
    """Test GlobalAdjustmentCoordinator successfully fetches data."""
    with patch("custom_components.ontario_energy_pricing.coordinator.async_get_clientsession"):
        with patch("custom_components.ontario_energy_pricing.coordinator.IESOGlobalAdjustmentClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.async_get_current_rate = AsyncMock(return_value=sample_global_adjustment)
            mock_client_class.return_value = mock_client
            coordinator = GlobalAdjustmentCoordinator(hass=mock_hass)
            result = await coordinator._async_update_data()
    assert isinstance(result, GlobalAdjustment)
    assert result.rate == 0.0485
