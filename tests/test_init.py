"""Tests for component lifecycle."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from custom_components.ontario_energy_pricing import (
    async_reload_entry,
    async_setup_entry,
    async_unload_entry,
)
from custom_components.ontario_energy_pricing.const import DOMAIN


@pytest.mark.asyncio
async def test_async_setup_entry_success(mock_hass, mock_config_entry) -> None:
    """Test successful setup of config entry."""
    mock_hass.data = {}

    with patch(
        "custom_components.ontario_energy_pricing.async_forward_entry_setups",
        return_value=None,
    ) as mock_forward:
        with patch(
            "custom_components.ontario_energy_pricing.OntarioEnergyPricingCoordinator.async_config_entry_first_refresh",
            return_value=None,
        ) as mock_refresh:
            result = await async_setup_entry(mock_hass, mock_config_entry)

            assert result is True
            assert DOMAIN in mock_hass.data
            assert mock_config_entry.entry_id in mock_hass.data[DOMAIN]
            mock_forward.assert_called_once()


@pytest.mark.asyncio
async def test_async_setup_entry_stores_data(mock_hass, mock_config_entry) -> None:
    """Test that setup stores entry data correctly."""
    mock_hass.data = {}

    with patch(
        "custom_components.ontario_energy_pricing.async_forward_entry_setups",
        return_value=None,
    ):
        with patch(
            "custom_components.ontario_energy_pricing.OntarioEnergyPricingCoordinator.async_config_entry_first_refresh",
            return_value=None,
        ):
            await async_setup_entry(mock_hass, mock_config_entry)

            stored_data = mock_hass.data[DOMAIN][mock_config_entry.entry_id]
            assert "admin_fee" in stored_data
            assert "location" in stored_data
            assert "coordinator" in stored_data


@pytest.mark.asyncio
async def test_async_setup_entry_no_api_key(mock_hass, mock_config_entry) -> None:
    """Test setup without API key (new simplified architecture)."""
    mock_hass.data = {}
    # Ensure no api_key in config
    mock_config_entry.data.pop("api_key", None)

    with patch(
        "custom_components.ontario_energy_pricing.async_forward_entry_setups",
        return_value=None,
    ):
        with patch(
            "custom_components.ontario_energy_pricing.OntarioEnergyPricingCoordinator.async_config_entry_first_refresh",
            return_value=None,
        ):
            result = await async_setup_entry(mock_hass, mock_config_entry)

            assert result is True


@pytest.mark.asyncio
async def test_async_unload_entry_success(mock_hass, mock_config_entry) -> None:
    """Test successful unload of config entry."""
    mock_hass.data = {DOMAIN: {mock_config_entry.entry_id: {}}}
    mock_hass.services = MagicMock()
    mock_hass.services.async_remove = MagicMock()

    with patch(
        "custom_components.ontario_energy_pricing.async_unload_platforms",
        return_value=True,
    ):
        result = await async_unload_entry(mock_hass, mock_config_entry)

        assert result is True
        assert mock_config_entry.entry_id not in mock_hass.data[DOMAIN]


@pytest.mark.asyncio
async def test_async_reload_entry(mock_hass, mock_config_entry) -> None:
    """Test reload calls unload then setup."""
    with patch(
        "custom_components.ontario_energy_pricing.async_unload_entry"
    ) as mock_unload:
        with patch(
            "custom_components.ontario_energy_pricing.async_setup_entry",
            return_value=True,
        ) as mock_setup:
            await async_reload_entry(mock_hass, mock_config_entry)

            mock_unload.assert_called_once_with(mock_hass, mock_config_entry)
            mock_setup.assert_called_once_with(mock_hass, mock_config_entry)
