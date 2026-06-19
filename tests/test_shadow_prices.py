"""Tests for Shadow Prices client - congestion costs from IESO."""

import sys
from unittest.mock import MagicMock

# Mock Home Assistant modules BEFORE importing

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

# NOW import the test modules
import sys

sys.path.insert(0, "/home/dmalloc/pidev")

import logging
from unittest.mock import MagicMock

logging.basicConfig(level=logging.WARNING)

# NOW import the shadow prices module
from custom_components.ontario_energy_pricing.ieso_shadow_prices import (
    IESOShadowPricesClient,
)

logging.basicConfig(level=logging.WARNING)


# Sample XML fixtures
SAMPLE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<Document docID="RealtimeConstrShadowPrices" xmlns="http://www.ieso.ca/schema">
<DocHeader>
<DocTitle>Real-Time Constraints Shadow Prices Report</DocTitle>
<CreatedAt>2026-06-14T08:01:25</CreatedAt>
</DocHeader>
<DocBody>
<DELIVERYDATE>2026-06-08</DELIVERYDATE>
<HourlyPrice>
<ConstraintName>BASE CASE 0 NW.O.T21_R.V12N_D</ConstraintName>
<DeliveryHour>24</DeliveryHour>
<IntervalShadowPrices>
<Interval>1</Interval>
<ShadowPrice>-1.08</ShadowPrice>
<Interval>2</Interval>
<ShadowPrice>-5.77</ShadowPrice>
<Interval>3</Interval>
<ShadowPrice>-5.82</ShadowPrice>
<Interval>4</Interval>
<ShadowPrice>-8.38</ShadowPrice>
<Interval>5</Interval>
<ShadowPrice>-8.37</ShadowPrice>
<Interval>6</Interval>
<ShadowPrice>-8.36</ShadowPrice>
<Interval>7</Interval>
<ShadowPrice>-8.35</ShadowPrice>
<Interval>8</Interval>
<ShadowPrice>-8.36</ShadowPrice>
<Interval>9</Interval>
<ShadowPrice>-5.76</ShadowPrice>
<Interval>10</Interval>
<ShadowPrice>-8.2</ShadowPrice>
<Interval>11</Interval>
<ShadowPrice>-8.19</ShadowPrice>
<Interval>12</Interval>
<ShadowPrice>0</ShadowPrice>
</IntervalShadowPrices>
</HourlyPrice>
<HourlyPrice>
<ConstraintName>BASE CASE 0 NW.O.T21_R.V12N_D</ConstraintName>
<DeliveryHour>23</DeliveryHour>
<IntervalShadowPrices>
<Interval>1</Interval>
<ShadowPrice>0</ShadowPrice>
<Interval>2</Interval>
<ShadowPrice>0</ShadowPrice>
<Interval>3</Interval>
<ShadowPrice>15.5</ShadowPrice>
<Interval>4</Interval>
<ShadowPrice>25.0</ShadowPrice>
</IntervalShadowPrices>
</HourlyPrice>
</DocBody>
</Document>"""

MULTI_CONSTRAINT_XML = """<?xml version="1.0" encoding="UTF-8"?>
<Document docID="RealtimeConstrShadowPrices" xmlns="http://www.ieso.ca/schema">
<DocHeader><CreatedAt>2026-06-14T08:01:25</CreatedAt></DocHeader>
<DocBody>
<DELIVERYDATE>2026-06-08</DELIVERYDATE>
<HourlyPrice>
<ConstraintName>NORTHWEST_IMPORT_LIMIT</ConstraintName>
<DeliveryHour>15</DeliveryHour>
<IntervalShadowPrices>
<Interval>1</Interval><ShadowPrice>25.5</ShadowPrice>
<Interval>2</Interval><ShadowPrice>30.0</ShadowPrice>
</IntervalShadowPrices>
</HourlyPrice>
<HourlyPrice>
<ConstraintName>SOUTHWEST_EXPORT_LIMIT</ConstraintName>
<DeliveryHour>15</DeliveryHour>
<IntervalShadowPrices>
<Interval>1</Interval><ShadowPrice>0</ShadowPrice>
<Interval>2</Interval><ShadowPrice>0</ShadowPrice>
</IntervalShadowPrices>
</HourlyPrice>
</DocBody></Document>"""

MULTI_CONSTRAINT_MAX_XML = """<?xml version="1.0" encoding="UTF-8"?>
<Document docID="RealtimeConstrShadowPrices" xmlns="http://www.ieso.ca/schema">
<DocHeader><CreatedAt>2026-06-14T08:01:25</CreatedAt></DocHeader>
<DocBody>
<DELIVERYDATE>2026-06-08</DELIVERYDATE>
<HourlyPrice>
<ConstraintName>CONSTRAINT_A</ConstraintName>
<DeliveryHour>15</DeliveryHour>
<IntervalShadowPrices>
<Interval>1</Interval><ShadowPrice>10.0</ShadowPrice>
</IntervalShadowPrices>
</HourlyPrice>
<HourlyPrice>
<ConstraintName>CONSTRAINT_B</ConstraintName>
<DeliveryHour>15</DeliveryHour>
<IntervalShadowPrices>
<Interval>1</Interval><ShadowPrice>50.0</ShadowPrice>
</IntervalShadowPrices>
</HourlyPrice>
</DocBody></Document>"""

CURRENT_HOUR_XML = """<?xml version="1.0" encoding="UTF-8"?>
<Document docID="RealtimeConstrShadowPrices" xmlns="http://www.ieso.ca/schema">
<DocHeader><CreatedAt>2026-06-14T15:30:00</CreatedAt></DocHeader>
<DocBody>
<DELIVERYDATE>2026-06-14</DELIVERYDATE>
<HourlyPrice>
<ConstraintName>TEST_CONSTRAINT</ConstraintName>
<DeliveryHour>16</DeliveryHour>
<IntervalShadowPrices>
<Interval>1</Interval><ShadowPrice>25.0</ShadowPrice>
<Interval>2</Interval><ShadowPrice>30.0</ShadowPrice>
</IntervalShadowPrices>
</HourlyPrice>
</DocBody></Document>"""

NEGATIVE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<Document docID="RealtimeConstrShadowPrices" xmlns="http://www.ieso.ca/schema">
<DocHeader><CreatedAt>2026-06-14T08:01:25</CreatedAt></DocHeader>
<DocBody>
<DELIVERYDATE>2026-06-08</DELIVERYDATE>
<HourlyPrice>
<ConstraintName>TEST_CONSTRAINT</ConstraintName>
<DeliveryHour>24</DeliveryHour>
<IntervalShadowPrices>
<Interval>1</Interval><ShadowPrice>-1.08</ShadowPrice>
<Interval>2</Interval><ShadowPrice>-5.77</ShadowPrice>
<Interval>3</Interval><ShadowPrice>0</ShadowPrice>
</IntervalShadowPrices>
</HourlyPrice>
</DocBody></Document>"""

EMPTY_XML = """<?xml version="1.0" encoding="UTF-8"?>
<Document docID="RealtimeConstrShadowPrices" xmlns="http://www.ieso.ca/schema">
<DocHeader><CreatedAt>2026-06-14T08:01:25</CreatedAt></DocHeader>
<DocBody>
<DELIVERYDATE>2026-06-08</DELIVERYDATE>
<HourlyPrice>
<ConstraintName>EMPTY_CONSTRAINT</ConstraintName>
<DeliveryHour>15</DeliveryHour>
<IntervalShadowPrices>
<Interval>1</Interval><ShadowPrice></ShadowPrice>
<Interval>2</Interval><ShadowPrice></ShadowPrice>
</IntervalShadowPrices>
</HourlyPrice>
</DocBody></Document>"""


@pytest.fixture
def client():
    """Create a client with mocked session."""
    return IESOShadowPricesClient(MagicMock())


# --- Parsing Tests ---


def test_parse_shadow_prices_xml(client):
    """Test parsing shadow prices XML with multiple constraints."""
    data = client._parse_xml(SAMPLE_XML)

    assert data is not None
    assert data.delivery_date == "2026-06-08"
    assert len(data.constraints) >= 1

    constraint = data.constraints["BASE CASE 0 NW.O.T21_R.V12N_D"]
    assert constraint is not None
    assert len(constraint.hourly_prices) >= 1

    hour_24 = constraint.hourly_prices.get(24)
    assert hour_24 is not None
    assert len(hour_24.intervals) == 12

    assert hour_24.intervals.get(4) == -8.38
    assert hour_24.intervals.get(12) == 0


def test_shadow_price_zone_specific():
    """Test getting shadow prices for specific zones."""
    client = IESOShadowPricesClient(MagicMock())
    data = client._parse_xml(MULTI_CONSTRAINT_XML)

    assert "NORTHWEST_IMPORT_LIMIT" in data.constraints
    assert "SOUTHWEST_EXPORT_LIMIT" in data.constraints

    nw_constraint = data.constraints["NORTHWEST_IMPORT_LIMIT"]
    hour_15 = nw_constraint.hourly_prices.get(15)
    assert hour_15 is not None
    assert hour_15.intervals.get(1) == 25.5
    assert hour_15.intervals.get(2) == 30.0

    sw_constraint = data.constraints["SOUTHWEST_EXPORT_LIMIT"]
    hour_15_sw = sw_constraint.hourly_prices.get(15)
    assert hour_15_sw is not None
    assert hour_15_sw.intervals.get(1) == 0


def test_get_max_shadow_price():
    """Test getting maximum shadow price across all constraints."""
    client = IESOShadowPricesClient(MagicMock())
    data = client._parse_xml("""<?xml version="1.0" encoding="UTF-8"?>
<Document docID="RealtimeConstrShadowPrices" xmlns="http://www.ieso.ca/schema">
<DocHeader><CreatedAt>2026-06-14T08:01:25</CreatedAt></DocHeader>
<DocBody>
<DELIVERYDATE>2026-06-08</DELIVERYDATE>
<HourlyPrice>
<ConstraintName>CONSTRAINT_A</ConstraintName>
<DeliveryHour>15</DeliveryHour>
<IntervalShadowPrices>
<Interval>1</Interval><ShadowPrice>10.0</ShadowPrice>
</IntervalShadowPrices>
</HourlyPrice>
<HourlyPrice>
<ConstraintName>CONSTRAINT_B</ConstraintName>
<DeliveryHour>15</DeliveryHour>
<IntervalShadowPrices>
<Interval>1</Interval><ShadowPrice>50.0</ShadowPrice>
</IntervalShadowPrices>
</HourlyPrice>
</DocBody></Document>""")

    max_price = data.get_max_shadow_price(15)
    assert max_price == 50.0


def test_shadow_price_current_hour():
    """Test getting shadow price for a specific delivery hour."""
    client = IESOShadowPricesClient(MagicMock())
    data = client._parse_xml("""<?xml version="1.0" encoding="UTF-8"?>
<Document docID="RealtimeConstrShadowPrices" xmlns="http://www.ieso.ca/schema">
<DocHeader><CreatedAt>2026-06-14T15:30:00</CreatedAt></DocHeader>
<DocBody>
<DELIVERYDATE>2026-06-14</DELIVERYDATE>
<HourlyPrice>
<ConstraintName>TEST_CONSTRAINT</ConstraintName>
<DeliveryHour>16</DeliveryHour>
<IntervalShadowPrices>
<Interval>1</Interval><ShadowPrice>25.0</ShadowPrice>
<Interval>2</Interval><ShadowPrice>30.0</ShadowPrice>
</IntervalShadowPrices>
</HourlyPrice>
</DocBody></Document>""")

    # Test getting shadow price for hour 16
    current_hour_price = data.get_max_shadow_price(16)
    assert current_hour_price == 30.0  # Last interval of current hour

    print("✅ test_shadow_price_current_hour passed")


def test_negative_shadow_prices():
    """Test handling of negative shadow prices (counter-flow relief)."""
    client = IESOShadowPricesClient(MagicMock())
    data = client._parse_xml("""<?xml version="1.0" encoding="UTF-8"?>
<Document docID="RealtimeConstrShadowPrices" xmlns="http://www.ieso.ca/schema">
<DocHeader><CreatedAt>2026-06-14T08:01:25</CreatedAt></DocHeader>
<DocBody>
<DELIVERYDATE>2026-06-08</DELIVERYDATE>
<HourlyPrice>
<ConstraintName>TEST_CONSTRAINT</ConstraintName>
<DeliveryHour>24</DeliveryHour>
<IntervalShadowPrices>
<Interval>1</Interval><ShadowPrice>-1.08</ShadowPrice>
<Interval>2</Interval><ShadowPrice>-5.77</ShadowPrice>
<Interval>3</Interval><ShadowPrice>0</ShadowPrice>
</IntervalShadowPrices>
</HourlyPrice>
</DocBody></Document>""")

    constraint = data.constraints.get("TEST_CONSTRAINT")
    hour_24 = constraint.hourly_prices.get(24)

    assert hour_24.intervals.get(1) == -1.08
    assert hour_24.intervals.get(2) == -5.77
    assert hour_24.intervals.get(3) == 0

    print("✅ test_negative_shadow_prices passed")


def test_empty_shadow_prices():
    """Test handling of empty/missing shadow prices."""
    client = IESOShadowPricesClient(MagicMock())
    data = client._parse_xml("""<?xml version="1.0" encoding="UTF-8"?>
<Document docID="RealtimeConstrShadowPrices" xmlns="http://www.ieso.ca/schema">
<DocHeader><CreatedAt>2026-06-14T08:01:25</CreatedAt></DocHeader>
<DocBody>
<DELIVERYDATE>2026-06-08</DELIVERYDATE>
<HourlyPrice>
<ConstraintName>EMPTY_CONSTRAINT</ConstraintName>
<DeliveryHour>15</DeliveryHour>
<IntervalShadowPrices>
<Interval>1</Interval><ShadowPrice></ShadowPrice>
<Interval>2</Interval><ShadowPrice></ShadowPrice>
</IntervalShadowPrices>
</HourlyPrice>
</DocBody></Document>""")

    constraint = data.constraints.get("EMPTY_CONSTRAINT")
    hour_15 = constraint.hourly_prices.get(15)

    # Empty values should be treated as 0 or None
    assert hour_15.intervals.get(1) in (0, None)
    assert hour_15.intervals.get(2) in (0, None)

    print("✅ test_empty_shadow_prices passed")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
