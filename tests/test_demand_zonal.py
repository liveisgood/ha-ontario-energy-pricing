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

# Real IESO format: 3 metadata lines, then header, then data rows
SAMPLE_CSV = """Ontario Real-Time 5 Minute Zonal Demand Report
 CREATED AT 2026/06/14 08:30:00 
FOR 2026
Date,Hour,Interval,Ontario Demand,NORTHWEST,NORTHEAST,OTTAWA,EAST,TORONTO,ESSA,BRUCE,SOUTHWEST,NIAGARA,WEST,Zones Total,DIFF
2026-06-14,1,1,     1386,       57,      123,      89,      93,     471,     103,       8,     254,      49,     159,    1407,      21
2026-06-14,1,2,     1385,       57,      123,      89,      92,     469,     103,       8,     253,      48,     160,    1403,      17
2026-06-14,1,3,     1392,       57,      122,      88,      91,     468,     103,       8,     251,      48,     160,    1396,       4
2026-06-14,1,4,     1384,       58,      121,      88,      90,     466,     102,       8,     249,      48,     159,    1388,       4
2026-06-14,1,5,     1384,       58,      124,      87,      90,     465,     102,       8,     253,      47,     159,    1393,       9
2026-06-14,1,6,     1379,       57,      125,      87,      89,     464,     102,       8,     252,      47,     162,    1394,      14
"""

EMPTY_CSV = """Ontario Real-Time 5 Minute Zonal Demand Report
 CREATED AT 2026/06/14 08:30:00 
FOR 2026
Date,Hour,Interval,Ontario Demand,NORTHWEST,NORTHEAST,OTTAWA,EAST,TORONTO,ESSA,BRUCE,SOUTHWEST,NIAGARA,WEST,Zones Total,DIFF
"""


def test_parse_demand_zonal_csv():
    """Test parsing of demand zonal CSV."""
    client = IESODemandZonalClient(MagicMock())
    data = client._parse_csv(SAMPLE_CSV)

    # 6 data rows x 10 zones = 60 entries
    assert len(data.demand_data) == 60

    # Check first Toronto entry (row 1, hour=1, interval=1, Toronto=471)
    toronto_entries = data.get_demand_by_zone("TORONTO")
    assert len(toronto_entries) == 6
    # First entry: hour 1, interval 1 -> timestamp at 00:00
    first = toronto_entries[0]
    assert first.demand_mw == 471.0

    # Check first Ottawa entry (row 1, hour=1, interval=1, OTTAWA=89)
    ottawa_entries = data.get_demand_by_zone("OTTAWA")
    assert len(ottawa_entries) == 6
    assert ottawa_entries[0].demand_mw == 89.0

    # Check zones available
    zones = data.get_zones()
    expected_zones = {"NORTHWEST", "NORTHEAST", "OTTAWA", "EAST", "TORONTO",
                      "ESSA", "BRUCE", "SOUTHWEST", "NIAGARA", "WEST"}
    assert set(zones) == expected_zones


def test_get_demand_by_zone():
    """Test getting demand data by zone."""
    client = IESODemandZonalClient(MagicMock())
    data = client._parse_csv(SAMPLE_CSV)

    toronto_data = data.get_demand_by_zone("TORONTO")
    assert len(toronto_data) == 6  # 6 intervals

    # Check timestamps are in order
    for i in range(len(toronto_data) - 1):
        assert toronto_data[i].timestamp <= toronto_data[i + 1].timestamp


def test_get_latest_demand_by_zone():
    """Test getting the most recent demand data by zone."""
    client = IESODemandZonalClient(MagicMock())
    data = client._parse_csv(SAMPLE_CSV)

    latest_toronto = data.get_latest_demand_by_zone("TORONTO")
    assert latest_toronto is not None
    assert latest_toronto.zone == "TORONTO"
    assert latest_toronto.demand_mw == 464.0  # Last row, Toronto column

    latest_ottawa = data.get_latest_demand_by_zone("OTTAWA")
    assert latest_ottawa is not None
    assert latest_ottawa.zone == "OTTAWA"
    assert latest_ottawa.demand_mw == 87.0  # Last row, Ottawa column


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
