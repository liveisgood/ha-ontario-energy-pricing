"""Tests for Demand Zonal client - IESO RealtimeDemandZonal."""

import sys
from unittest.mock import MagicMock

# Mock Home Assistant modules
sys.modules["homeassistant"] = MagicMock()
sys.modules["homeassistant.exceptions"] = MagicMock()
sys.modules["homeassistant.exceptions"].HomeAssistantError = Exception
sys.modules["homeassistant.const"] = MagicMock()
sys.modules["homeassistant.const"].Platform = MagicMock()
sys.modules["homeassistant.config_entries"] = MagicMock()
sys.modules["homeassistant.core"] = MagicMock()
sys.modules["homeassistant.helpers"] = MagicMock()
sys.modules["homeassistant.helpers.aiohttp_client"] = MagicMock()
sys.modules["homeassistant.helpers.update_coordinator"] = MagicMock()
sys.modules["homeassistant.helpers.entity_platform"] = MagicMock()
sys.modules["homeassistant.config_entries"] = MagicMock()
sys.modules["homeassistant.components"] = MagicMock()
sys.modules["homeassistant.components.binary_sensor"] = MagicMock()
sys.modules["homeassistant.components.sensor"] = MagicMock()
sys.modules["voluptuous"] = MagicMock()

sys.path.insert(0, "/home/dmalloc/pidev")

from custom_components.ontario_energy_pricing.ieso_demand_zonal import (
    IESODemandZonalClient,
)

SAMPLE_CSV = """Date Time,Zone,Demand (MW)
2026-06-14 08:00:00,TORONTO,18500
2026-06-14 08:00:00,OTTAWA,2100
2026-06-14 08:05:00,TORONTO,18600
2026-06-14 08:05:00,OTTAWA,2150
2026-06-14 08:10:00,TORONTO,18700
2026-06-14 08:10:00,OTTAWA,2200
"""

EMPTY_CSV = """Date Time,Zone,Demand (MW)
"""


def test_parse_demand_zonal_csv():
    """Test parsing of demand zonal CSV."""
    client = IESODemandZonalClient(MagicMock())
    data = client._parse_csv(SAMPLE_CSV)

    assert len(data.demand_data) == 6

    # Check first Toronto entry
    toronto_0800 = next(
        (
            d
            for d in data.demand_data
            if d.zone == "TORONTO" and d.timestamp.hour == 8 and d.timestamp.minute == 0
        ),
        None,
    )
    assert toronto_0800 is not None
    assert toronto_0800.demand_mw == 18500.0

    # Check first Ottawa entry
    ottawa_0800 = next(
        (
            d
            for d in data.demand_data
            if d.zone == "OTTAWA" and d.timestamp.hour == 8 and d.timestamp.minute == 0
        ),
        None,
    )
    assert ottawa_0800 is not None
    assert ottawa_0800.demand_mw == 2100.0

    # Check that we have the right zones
    zones = data.get_zones()
    assert set(zones) == {"TORONTO", "OTTAWA"}


def test_get_demand_by_zone():
    """Test getting demand data by zone."""
    client = IESODemandZonalClient(MagicMock())
    data = client._parse_csv(SAMPLE_CSV)

    toronto_data = data.get_demand_by_zone("TORONTO")
    assert len(toronto_data) == 3  # Three 5-minute intervals for Toronto

    ottawa_data = data.get_demand_by_zone("OTTAWA")
    assert len(ottawa_data) == 3  # Three 5-minute intervals for Ottawa

    # Check that data is sorted by time (should be in order from CSV)
    assert (
        toronto_data[0].timestamp
        < toronto_data[1].timestamp
        < toronto_data[2].timestamp
    )
    assert (
        ottawa_data[0].timestamp < ottawa_data[1].timestamp < ottawa_data[2].timestamp
    )


def test_get_latest_demand_by_zone():
    """Test getting the most recent demand data by zone."""
    client = IESODemandZonalClient(MagicMock())
    data = client._parse_csv(SAMPLE_CSV)

    latest_toronto = data.get_latest_demand_by_zone("TORONTO")
    assert latest_toronto is not None
    assert latest_toronto.zone == "TORONTO"
    assert latest_toronto.timestamp.hour == 8
    assert latest_toronto.timestamp.minute == 10  # Latest timestamp
    assert latest_toronto.demand_mw == 18700.0  # Highest value in sample

    latest_ottawa = data.get_latest_demand_by_zone("OTTAWA")
    assert latest_ottawa is not None
    assert latest_ottawa.zone == "OTTAWA"
    assert latest_ottawa.timestamp.hour == 8
    assert latest_ottawa.timestamp.minute == 10  # Latest timestamp
    assert latest_ottawa.demand_mw == 2200.0  # Highest value in sample


def test_empty_demand_zonal():
    """Test parsing of empty demand zonal CSV."""
    client = IESODemandZonalClient(MagicMock())
    data = client._parse_csv(EMPTY_CSV)

    assert len(data.demand_data) == 0
    assert data.get_zones() == []


def test_get_latest_demand_by_zone_empty():
    """Test getting latest demand from empty data returns None."""
    client = IESODemandZonalClient(MagicMock())
    data = client._parse_csv(EMPTY_CSV)

    result = data.get_latest_demand_by_zone("TORONTO")
    assert result is None


if __name__ == "__main__":
    test_parse_demand_zonal_csv()
    test_get_demand_by_zone()
    test_get_latest_demand_by_zone()
    test_empty_demand_zonal()
    test_get_latest_demand_by_zone_empty()
    print("✅ All Demand Zonal tests passed!")
