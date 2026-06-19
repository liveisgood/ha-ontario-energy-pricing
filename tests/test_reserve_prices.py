"""Tests for Reserve Prices client - IESO RealtimeORLMP."""

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

from custom_components.ontario_energy_pricing.ieso_reserves import (
    IESOReservePricesClient,
)

SAMPLE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<Document docID="RealtimeORLMP" xmlns="http://www.ieso.ca/schema">
<DocHeader>
<DocTitle>Real-Time Operating Reserve LMP Report</DocTitle>
<CreatedAt>2026-06-14T08:01:25</CreatedAt>
</DocHeader>
<DocBody>
<DELIVERYDATE>2026-06-14</DELIVERYDATE>
<HourlyPrice>
<MarketName>ORLMP</MarketName>
<Region>TORONTO</Region>
<DeliveryHour>1</DeliveryHour>
<Interval>1</Interval>
<Type>10MinSync</Type>
<Price>5.25</Price>
</HourlyPrice>
<HourlyPrice>
<MarketName>ORLMP</MarketName>
<Region>TORONTO</Region>
<DeliveryHour>1</DeliveryHour>
<Interval>2</Interval>
<Type>10MinSync</Type>
<Price>5.30</Price>
</HourlyPrice>
<HourlyPrice>
<MarketName>ORLMP</MarketName>
<Region>TORONTO</Region>
<DeliveryHour>1</DeliveryHour>
<Interval>1</Interval>
<Type>10MinNonSync</Type>
<Price>4.80</Price>
</HourlyPrice>
<HourlyPrice>
<MarketName>ORLMP</MarketName>
<Region>TORONTO</Region>
<DeliveryHour>1</DeliveryHour>
<Interval>1</Interval>
<Type>30Min</Type>
<Price>3.75</Price>
</HourlyPrice>
<HourlyPrice>
<MarketName>ORLMP</MarketName>
<Region>OTTAWA</Region>
<DeliveryHour>1</DeliveryHour>
<Interval>1</Interval>
<Type>10MinSync</Type>
<Price>5.10</Price>
</HourlyPrice>
</DocBody>
</Document>
"""

EMPTY_XML = """<?xml version="1.0" encoding="UTF-8"?>
<Document docID="RealtimeORLMP" xmlns="http://www.ieso.ca/schema">
<DocHeader>
<DocTitle>Real-Time Operating Reserve LMP Report</DocTitle>
<CreatedAt>2026-06-14T08:01:25</CreatedAt>
</DocHeader>
<DocBody>
<DELIVERYDATE>2026-06-14</DELIVERYDATE>
</DocBody>
</Document>
"""


def test_parse_reserve_prices_xml():
    """Test parsing of reserve prices XML."""
    client = IESOReservePricesClient(MagicMock())
    data = client._parse_xml(SAMPLE_XML)

    assert data.delivery_date == "2026-06-14"
    assert data.created_at.hour == 8
    assert data.created_at.minute == 1
    assert data.created_at.second == 25

    # Check that we have regions
    assert "TORONTO" in data.region_prices
    assert "OTTAWA" in data.region_prices

    # Check TORONTO region
    toronto = data.region_prices["TORONTO"]
    assert "10MinSync" in toronto.reserve_types
    assert "10MinNonSync" in toronto.reserve_types
    assert "30Min" in toronto.reserve_types

    # Check 10MinSync for hour 1
    sync_10min = toronto.reserve_types["10MinSync"]
    assert 1 in sync_10min.hourly_prices
    hour_1_prices = sync_10min.hourly_prices[1]
    assert len(hour_1_prices) == 2  # Two intervals
    assert hour_1_prices[1] == 5.25  # Interval 1
    assert hour_1_prices[2] == 5.30  # Interval 2

    # Check 10MinNonSync for hour 1
    nonsync_10min = toronto.reserve_types["10MinNonSync"]
    assert 1 in nonsync_10min.hourly_prices
    hour_1_nonsync = nonsync_10min.hourly_prices[1]
    assert len(hour_1_nonsync) == 1  # One interval
    assert hour_1_nonsync[1] == 4.80  # Interval 1

    # Check 30Min for hour 1
    thirty_min = toronto.reserve_types["30Min"]
    assert 1 in thirty_min.hourly_prices
    hour_1_thirty = thirty_min.hourly_prices[1]
    assert len(hour_1_thirty) == 1  # One interval
    assert hour_1_thirty[1] == 3.75  # Interval 1

    # Check OTTAWA region
    ottawa = data.region_prices["OTTAWA"]
    assert "10MinSync" in ottawa.reserve_types
    sync_10min_ottawa = ottawa.reserve_types["10MinSync"]
    assert 1 in sync_10min_ottawa.hourly_prices
    hour_1_ottawa = sync_10min_ottawa.hourly_prices[1]
    assert len(hour_1_ottawa) == 1  # One interval
    assert hour_1_ottawa[1] == 5.10  # Interval 1


def test_reserve_price_by_region_and_type():
    """Test getting reserve price by region, type, hour, and interval."""
    client = IESOReservePricesClient(MagicMock())
    data = client._parse_xml(SAMPLE_XML)

    # Test existing values
    price = data.get_reserve_price("TORONTO", "10MinSync", 1, 1)
    assert price == 5.25

    price = data.get_reserve_price("TORONTO", "10MinSync", 1, 2)
    assert price == 5.30

    price = data.get_reserve_price("TORONTO", "10MinNonSync", 1, 1)
    assert price == 4.80

    price = data.get_reserve_price("TORONTO", "30Min", 1, 1)
    assert price == 3.75

    # Test non-existent values return None
    assert (
        data.get_reserve_price("TORONTO", "10MinSync", 2, 1) is None
    )  # Hour 2 doesn't exist
    assert (
        data.get_reserve_price("TORONTO", "10MinSync", 1, 3) is None
    )  # Interval 3 doesn't exist for this hour
    assert (
        data.get_reserve_price("MONTREAL", "10MinSync", 1, 1) is None
    )  # Region doesn't exist
    assert (
        data.get_reserve_price("TORONTO", "5MinSync", 1, 1) is None
    )  # Type doesn't exist


def test_empty_reserve_prices():
    """Test parsing of empty reserve prices XML."""
    client = IESOReservePricesClient(MagicMock())
    data = client._parse_xml(EMPTY_XML)

    assert data.delivery_date == "2026-06-14"
    assert data.created_at.hour == 8
    assert len(data.region_prices) == 0


def test_regions_method():
    """Test getting list of regions."""
    client = IESOReservePricesClient(MagicMock())
    data = client._parse_xml(SAMPLE_XML)

    regions = data.get_regions()
    assert set(regions) == {"TORONTO", "OTTAWA"}


def test_reserve_types_method():
    """Test getting list of reserve types for a region."""
    client = IESOReservePricesClient(MagicMock())
    data = client._parse_xml(SAMPLE_XML)

    toronto_types = data.get_reserve_types("TORONTO")
    assert set(toronto_types) == {"10MinSync", "10MinNonSync", "30Min"}

    ottawa_types = data.get_reserve_types("OTTAWA")
    assert set(ottawa_types) == {"10MinSync"}

    # Non-existent region
    assert data.get_reserve_types("MONTREAL") == []


def test_hourly_prices_method():
    """Test getting hourly prices for a region and reserve type."""
    client = IESOReservePricesClient(MagicMock())
    data = client._parse_xml(SAMPLE_XML)

    # Test TORONTO 10MinSync
    hourly = data.get_hourly_prices("TORONTO", "10MinSync")
    assert hourly == {1: {1: 5.25, 2: 5.30}}

    # Test TORONTO 10MinNonSync
    hourly = data.get_hourly_prices("TORONTO", "10MinNonSync")
    assert hourly == {1: {1: 4.80}}

    # Test non-existent combination
    assert data.get_hourly_prices("TORONTO", "NonExistent") == {}
    assert data.get_hourly_prices("NonExistent", "10MinSync") == {}


if __name__ == "__main__":
    test_parse_reserve_prices_xml()
    test_reserve_price_by_region_and_type()
    test_empty_reserve_prices()
    test_regions_method()
    test_reserve_types_method()
    test_hourly_prices_method()
    print("✅ All Reserve Prices tests passed!")
