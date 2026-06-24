"""Tests for component lifecycle."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from custom_components.ontario_energy_pricing import (
    async_setup_entry,
    async_unload_entry,
)
from custom_components.ontario_energy_pricing.const import DOMAIN
from custom_components.ontario_energy_pricing.coordinator import (
    OntarioEnergyPricingCoordinator,
)


@pytest.mark.asyncio
async def test_async_setup_entry_success(mock_hass, mock_config_entry) -> None:
    """Test successful setup of config entry."""
    mock_hass.data = {}
    mock_hass.config_entries.async_forward_entry_setups = AsyncMock(return_value=None)

    with patch.object(
        OntarioEnergyPricingCoordinator,
        "async_config_entry_first_refresh",
        new_callable=AsyncMock,
    ) as mock_refresh:
        mock_refresh.return_value = None
        result = await async_setup_entry(mock_hass, mock_config_entry)

        assert result is True
        assert hasattr(mock_config_entry, "runtime_data")
        assert isinstance(
            mock_config_entry.runtime_data, OntarioEnergyPricingCoordinator
        )
        mock_refresh.assert_called_once()
        mock_hass.config_entries.async_forward_entry_setups.assert_called_once()


@pytest.mark.asyncio
async def test_async_setup_entry_stores_data(mock_hass, mock_config_entry) -> None:
    """Test that setup stores entry data correctly."""
    mock_hass.data = {}
    mock_hass.config_entries.async_forward_entry_setups = AsyncMock(return_value=None)

    with patch.object(
        OntarioEnergyPricingCoordinator,
        "async_config_entry_first_refresh",
        new_callable=AsyncMock,
    ):
        await async_setup_entry(mock_hass, mock_config_entry)

        assert hasattr(mock_config_entry, "runtime_data")
        coordinator = mock_config_entry.runtime_data
        assert isinstance(coordinator, OntarioEnergyPricingCoordinator)
        # In c8c3d2f, admin_fee is stored as _admin_fee and not exposed as property


@pytest.mark.asyncio
async def test_async_setup_entry_no_api_key(mock_hass, mock_config_entry) -> None:
    """Test setup without API key (new simplified architecture)."""
    mock_hass.data = {}
    mock_hass.config_entries.async_forward_entry_setups = AsyncMock(return_value=None)
    # Ensure no api_key in config
    mock_config_entry.data.pop("api_key", None)

    with patch.object(
        OntarioEnergyPricingCoordinator,
        "async_config_entry_first_refresh",
        new_callable=AsyncMock,
    ):
        result = await async_setup_entry(mock_hass, mock_config_entry)

        assert result is True


@pytest.mark.asyncio
async def test_async_unload_entry_success(mock_hass, mock_config_entry) -> None:
    """Test successful unload of config entry."""
    mock_hass.data = {DOMAIN: {mock_config_entry.entry_id: {}}}

    with patch.object(
        mock_hass.config_entries, "async_unload_platforms", new_callable=AsyncMock
    ) as mock_unload:
        mock_unload.return_value = True
        result = await async_unload_entry(mock_hass, mock_config_entry)

        assert result is True
        mock_unload.assert_called_once_with(
            mock_config_entry, ["sensor", "binary_sensor"]
        )