"""Tests for component lifecycle."""

from __future__ import annotations

from unittest.mock import patch
import pytest

from custom_components.ontario_energy_pricing import (
    async_setup_entry,
    async_unload_entry,
    async_reload_entry,
)
from custom_components.ontario_energy_pricing.const import DOMAIN


@pytest.mark.asyncio
async def test_async_setup_entry_success(mock_hass, mock_config_entry) -> None:
    """Test successful setup of config entry."""
    mock_hass.data = {}
    with patch(
        "custom_components.ontario_energy_pricing.async_forward_entry_setups",
        return_value=None,
    ):
        result = await async_setup_entry(mock_hass, mock_config_entry)
    assert result is True
    assert DOMAIN in mock_hass.data
    assert mock_config_entry.entry_id in mock_hass.data[DOMAIN]


@pytest.mark.asyncio
async def test_async_setup_entry_stores_data(mock_hass, mock_config_entry) -> None:
    """Test that setup stores entry data correctly."""
    mock_hass.data = {}
    with patch(
        "custom_components.ontario_energy_pricing.async_forward_entry_setups",
        return_value=None,
    ):
        await async_setup_entry(mock_hass, mock_config_entry)
    stored_data = mock_hass.data[DOMAIN][mock_config_entry.entry_id]
    assert "api_key" in stored_data
    assert "zone" in stored_data
    assert "admin_fee" in stored_data
    assert "location" in stored_data


@pytest.mark.asyncio
async def test_async_unload_entry_success(mock_hass, mock_config_entry) -> None:
    """Test successful unload of config entry."""
    mock_hass.data = {DOMAIN: {mock_config_entry.entry_id: {}}}
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
