"""Test fixtures for Ontario Energy Pricing integration."""
from __future__ import annotations

from collections.abc import Generator
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pytest import FixtureRequest

# Home Assistant imports
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

# Integration imports
from custom_components.ontario_energy_pricing.const import DOMAIN
from custom_components.ontario_energy_pricing.models import (
    GlobalAdjustment,
    LMPCurrentPrice,
    LMPDataPoint,
    LMPHistoricalData,
)

# Test constants
TEST_API_KEY = "test_api_key_12345"
TEST_ZONE = "OAKVILLE"
TEST_LOCATION = "Oakville, ON"
TEST_ADMIN_FEE = 0.025  # $/kWh


@pytest.fixture
def mock_hass(event_loop) -> Generator[MagicMock, None, None]:
    """Create a mock HomeAssistant instance."""
    hass = MagicMock(spec=HomeAssistant)
    hass.data = {}
    hass.config = MagicMock()
    hass.config.time_zone = "America/Toronto"
    hass.async_add_executor_job = AsyncMock()
    hass.async_create_task = AsyncMock()
    yield hass


@pytest.fixture
def mock_config_entry() -> ConfigEntry:
    """Create a mock ConfigEntry with test data."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry_id"
    entry.data = {
        "api_key": TEST_API_KEY,
        "zone": TEST_ZONE,
        "admin_fee": TEST_ADMIN_FEE,
        "location": TEST_LOCATION,
    }
    entry.options = {}
    entry.title = "Test Ontario Energy Pricing"
    return entry


@pytest.fixture
def mock_entry_data() -> dict[str, Any]:
    """Return mock entry data dict."""
    return {
        "api_key": TEST_API_KEY,
        "zone": TEST_ZONE,
        "admin_fee": TEST_ADMIN_FEE,
        "location": TEST_LOCATION,
    }


@pytest.fixture
def sample_lmp_price() -> LMPCurrentPrice:
    """Create a sample LMPCurrentPrice instance."""
    return LMPCurrentPrice(
        price=0.0895,  # $/kWh
        timestamp=datetime(2026, 4, 12, 14, 30, tzinfo=timezone.utc),
        zone=TEST_ZONE,
        previous_price=0.0872,
    )


@pytest.fixture
def sample_lmp_history() -> LMPHistoricalData:
    """Create a sample LMPHistoricalData instance with 24h of data."""
    base_time = datetime(2026, 4, 11, 0, 0, tzinfo=timezone.utc)
    data_points = []

    # Create 288 5-minute intervals (24 hours)
    for i in range(288):
        timestamp = base_time.replace(minute=i * 5)
        # Simulate daily cycle: higher during day, lower at night
        hour = timestamp.hour
        if 9 <= hour <= 17:  # Peak hours
            price = 0.12 + (i % 10) / 1000  # ~0.12-0.13 $/kWh
        elif 7 <= hour <= 22:  # Shoulder hours
            price = 0.08 + (i % 10) / 1000  # ~0.08-0.09 $/kWh
        else:  # Off-peak
            price = 0.04 + (i % 5) / 1000  # ~0.04-0.05 $/kWh

        data_points.append(LMPDataPoint(timestamp=timestamp, price=price))

    return LMPHistoricalData(data_points=data_points, zone=TEST_ZONE)


@pytest.fixture
def sample_global_adjustment() -> GlobalAdjustment:
    """Create a sample GlobalAdjustment instance."""
    return GlobalAdjustment(
        rate=0.0485,  # $/kWh
        trade_month="2026-04",
        last_updated=datetime(2026, 4, 1, 0, 0, tzinfo=timezone.utc),
    )


@pytest.fixture
def mock_gridstatus_client(sample_lmp_price: LMPCurrentPrice, sample_lmp_history: LMPHistoricalData) -> Generator[AsyncMock, None, None]:
    """Create a mock GridStatusClient."""
    client = AsyncMock()
    client.async_get_current_lmp = AsyncMock(return_value=sample_lmp_price)
    client.async_get_24h_history = AsyncMock(return_value=sample_lmp_history)
    client.async_get_available_zones = AsyncMock(return_value=[
        "OAKVILLE",
        "TORONTO",
        "OTTAWA",
        "ONTARIO",
    ])

    with patch(
        "custom_components.ontario_energy_pricing.coordinator.GridStatusClient",
        return_value=client,
    ):
        with patch(
            "custom_components.ontario_energy_pricing.config_flow.GridStatusClient",
            return_value=client,
        ):
            yield client


@pytest.fixture
def mock_ieso_client(sample_global_adjustment: GlobalAdjustment) -> Generator[AsyncMock, None, None]:
    """Create a mock IESOGlobalAdjustmentClient."""
    client = AsyncMock()
    client.async_get_current_rate = AsyncMock(return_value=sample_global_adjustment)

    with patch(
        "custom_components.ontario_energy_pricing.coordinator.IESOGlobalAdjustmentClient",
        return_value=client,
    ):
        yield client


@pytest.fixture
def mock_async_get_clientsession() -> Generator[MagicMock, None, None]:
    """Mock async_get_clientsession to return a mock session."""
    mock_session = AsyncMock()

    with patch(
        "custom_components.ontario_energy_pricing.coordinator.async_get_clientsession",
        return_value=mock_session,
    ) as mock:
        yield mock


@pytest.fixture
def mock_async_get_clientsession_config_flow() -> Generator[MagicMock, None, None]:
    """Mock async_get_clientsession in config_flow module."""
    mock_session = AsyncMock()

    with patch(
        "custom_components.ontario_energy_pricing.config_flow.async_get_clientsession",
        return_value=mock_session,
    ) as mock:
        yield mock


@pytest.fixture
def mock_coordinators(
    sample_lmp_price: LMPCurrentPrice,
    sample_lmp_history: LMPHistoricalData,
    sample_global_adjustment: GlobalAdjustment,
) -> Generator[MagicMock, None, None]:
    """Create mock coordinators for sensor tests."""
    lmp_coordinator = MagicMock()
    lmp_coordinator.data = sample_lmp_price
    lmp_coordinator.previous_price = 0.0872

    lmp_24h_coordinator = MagicMock()
    lmp_24h_coordinator.data = sample_lmp_history

    ga_coordinator = MagicMock()
    ga_coordinator.data = sample_global_adjustment
    ga_coordinator.current_rate = sample_global_adjustment.rate
    ga_coordinator.trade_month = sample_global_adjustment.trade_month

    yield {
        "lmp": lmp_coordinator,
        "lmp_24h": lmp_24h_coordinator,
        "ga": ga_coordinator,
    }
