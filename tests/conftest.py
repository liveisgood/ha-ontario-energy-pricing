"""Test fixtures for Ontario Energy Pricing integration."""

from __future__ import annotations

from collections.abc import Generator
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Home Assistant imports
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

# Integration imports
from custom_components.ontario_energy_pricing.coordinator import (
    OntarioEnergyPricingData,
)
from custom_components.ontario_energy_pricing.ieso_ga import GlobalAdjustment

# Test constants
TEST_LOCATION = "Oakville, ON"
TEST_ADMIN_FEE = 1.45  # ¢/kWh


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
        "admin_fee": TEST_ADMIN_FEE,
        "location": TEST_LOCATION,
    }


@pytest.fixture
def sample_ieso_lmp_data() -> dict[str, Any]:
    """Create sample IESO LMP XML data."""
    return {
        "delivery_date": "2026-04-12",
        "delivery_hour": 14,
        "created_at": datetime(2026, 4, 12, 13, 22, 48, tzinfo=timezone.utc),
        "hour_average_mwh": 53.88,
        "hour_average_kwh": 5.388,
        "current_lmp_kwh": 5.241,  # Latest interval
        "intervals": [
            {
                "interval": 1,
                "lmp_mwh": 56.55,
                "lmp_kwh": 5.655,
                "flag": "DSO-RD",
            },
            {
                "interval": 2,
                "lmp_mwh": 52.41,
                "lmp_kwh": 5.241,
                "flag": "DSO-RD",
            },
            {
                "interval": 3,
                "lmp_mwh": 51.23,
                "lmp_kwh": 5.123,
                "flag": "DSO-RD",
            },
        ],
    }


@pytest.fixture
def sample_ieso_xml() -> str:
    """Sample IESO LMP XML response."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="http://www.ieso.ca/schema">
  <DocHeader>
    <DocTitle>Real-Time 5-min Ontario Zonal Energy Price Report</DocTitle>
    <CreatedAt>2026-04-12T13:22:48</CreatedAt>
  </DocHeader>
  <DocBody>
    <DeliveryDate>2026-04-12</DeliveryDate>
    <DeliveryHour>14</DeliveryHour>
    <ZonalPrice>
      <Interval>1</Interval>
      <LmpCap>56.55</LmpCap>
      <Flag>DSO-RD</Flag>
    </ZonalPrice>
    <ZonalPrice>
      <Interval>2</Interval>
      <LmpCap>52.41</LmpCap>
      <Flag>DSO-RD</Flag>
    </ZonalPrice>
    <ZonalPrice>
      <Interval>3</Interval>
      <LmpCap>51.23</LmpCap>
      <Flag>DSO-RD</Flag>
    </ZonalPrice>
    <AveragePrice>
      <LmpCap>53.88</LmpCap>
    </AveragePrice>
  </DocBody>
</Document>"""


@pytest.fixture
def sample_ieso_ga_xml() -> str:
    """Sample IESO GA XML response."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="http://www.ieso.ca/schema">
  <PublishInfo>
    <PublishDateTime>2026-04-01T00:00:00</PublishDateTime>
  </PublishInfo>
  <GlobalAdjustment>
    <TradeMonth>2026-04</TradeMonth>
    <FirstEstimateRate>0.06</FirstEstimateRate>
  </GlobalAdjustment>
</Document>"""


@pytest.fixture
def sample_global_adjustment() -> GlobalAdjustment:
    """Create a sample GlobalAdjustment instance."""
    return GlobalAdjustment(
        rate=0.06,  # $/kWh
        trade_month="2026-04",
        last_updated=datetime(2026, 4, 1, 0, 0, tzinfo=timezone.utc),
    )


@pytest.fixture
def sample_coordinator_data(
    sample_ieso_lmp_data: dict[str, Any],
    sample_global_adjustment: GlobalAdjustment,
) -> OntarioEnergyPricingData:
    """Create sample unified coordinator data."""
    return OntarioEnergyPricingData(
        current_lmp_kwh=sample_ieso_lmp_data["current_lmp_kwh"],
        hour_average_lmp_kwh=sample_ieso_lmp_data["hour_average_kwh"],
        current_lmp_mwh=sample_ieso_lmp_data["hour_average_mwh"],
        delivery_hour=sample_ieso_lmp_data["delivery_hour"],
        delivery_date=sample_ieso_lmp_data["delivery_date"],
        global_adjustment=sample_global_adjustment.rate * 100,  # Convert to cents
        trade_month=sample_global_adjustment.trade_month,
        admin_fee=TEST_ADMIN_FEE,
        intervals=sample_ieso_lmp_data["intervals"],
    )


@pytest.fixture
def mock_ieso_lmp_client(
    sample_ieso_lmp_data: dict[str, Any],
) -> Generator[AsyncMock, None, None]:
    """Create a mock IESOLMPClient."""
    from custom_components.ontario_energy_pricing.ieso_lmp import (
        IESOLMPClient,
        IESOLMPData,
        IESOZonalPrice,
    )

    mock_data = MagicMock(spec=IESOLMPData)
    mock_data.delivery_date = sample_ieso_lmp_data["delivery_date"]
    mock_data.delivery_hour = sample_ieso_lmp_data["delivery_hour"]
    mock_data.created_at = sample_ieso_lmp_data["created_at"]
    mock_data.hour_average_mwh = sample_ieso_lmp_data["hour_average_mwh"]
    mock_data.hour_average_kwh = sample_ieso_lmp_data["hour_average_kwh"]
    mock_data.current_lmp_kwh = sample_ieso_lmp_data["current_lmp_kwh"]
    mock_data.intervals = [
        MagicMock(
            spec=IESOZonalPrice,
            interval=i["interval"],
            lmp_mwh=i["lmp_mwh"],
            lmp_kwh=i["lmp_kwh"],
            flag=i["flag"],
        )
        for i in sample_ieso_lmp_data["intervals"]
    ]

    mock_client = AsyncMock(spec=IESOLMPClient)
    mock_client.async_get_current_lmp = AsyncMock(return_value=mock_data)

    with patch(
        "custom_components.ontario_energy_pricing.ieso_lmp.IESOLMPClient",
        return_value=mock_client,
    ):
        yield mock_client


@pytest.fixture
def mock_ieso_ga_client(
    sample_global_adjustment: GlobalAdjustment,
) -> Generator[AsyncMock, None, None]:
    """Create a mock IESOGlobalAdjustmentClient."""
    from custom_components.ontario_energy_pricing.ieso_ga import (
        IESOGlobalAdjustmentClient,
    )

    mock_client = AsyncMock(spec=IESOGlobalAdjustmentClient)
    mock_client.async_get_current_rate = AsyncMock(
        return_value=sample_global_adjustment
    )

    with patch(
        "custom_components.ontario_energy_pricing.ieso_ga.IESOGlobalAdjustmentClient",
        return_value=mock_client,
    ):
        yield mock_client


@pytest.fixture
def mock_coordinator(
    sample_coordinator_data: OntarioEnergyPricingData,
) -> Generator[MagicMock, None, None]:
    """Create a mock unified coordinator."""
    from custom_components.ontario_energy_pricing.coordinator import (
        OntarioEnergyPricingCoordinator,
    )

    mock = MagicMock(spec=OntarioEnergyPricingCoordinator)
    mock.data = sample_coordinator_data
    mock.last_update_success = True
    yield mock


@pytest.fixture
def mock_async_get_clientsession() -> Generator[MagicMock, None, None]:
    """Mock async_get_clientsession to return a mock session."""
    mock_session = AsyncMock()
    with patch(
        "custom_components.ontario_energy_pricing.coordinator.async_get_clientsession",
        return_value=mock_session,
    ) as mock:
        yield mock
