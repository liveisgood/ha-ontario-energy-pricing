"""Tests for Intertie LMP client - IESO RealtimeIntertieLMP."""

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

from custom_components.ontario_energy_pricing.ieso_intertie_lmp import (
    IESOIntertieLMPClient,
)

SAMPLE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<Document docID="RealtimeIntertieLMP" xmlns="http://www.ieso.ca/schema">
<DocHeader>
<DocTitle>Real-Time Intertie LMP Report</DocTitle>
<CreatedAt>2026-06-14T08:01:25</CreatedAt>
</DocHeader>
<DocBody>
<DELIVERYDATE>2026-06-14</DELIVERYDATE>
<HourlyPrice>
<IntertiePoint>MICHIGAN</IntertiePoint>
<DateTime>2026-06-14 08:00:00</DateTime>
<LMP>25.50</LMP>
</HourlyPrice>
<HourlyPrice>
<IntertiePoint>MICHIGAN</IntertiePoint>
<DateTime>2026-06-14 08:05:00</DateTime>
<LMP>26.00</LMP>
</HourlyPrice>
<HourlyPrice>
<IntertiePoint>NEW_YORK</IntertiePoint>
<DateTime>2026-06-14 08:00:00</DateTime>
<LMP>24.75</LMP>
</HourlyPrice>
<HourlyPrice>
<IntertiePoint>QUEBEC</IntertiePoint>
<DateTime>2026-06-14 08:00:00</DateTime>
<LMP>23.20</LMP>
</HourlyPrice>
</DocBody>
</Document>
"""

EMPTY_XML = """<?xml version="1.0" encoding="UTF-8"?>
<Document docID="RealtimeIntertieLMP" xmlns="http://www.ieso.ca/schema">
<DocHeader>
<DocTitle>Real-Time Intertie LMP Report</DocTitle>
<CreatedAt>2026-06-14T08:01:25</CreatedAt>
</DocHeader>
<DocBody>
<DELIVERYDATE>2026-06-14</DELIVERYDATE>
</DocBody>
</Document>
"""


def test_parse_intertie_lmp_xml():
    """Test parsing of intertie LMP XML."""
    client = IESOIntertieLMPClient(MagicMock())
    data = client._parse_xml(SAMPLE_XML)
    
    assert len(data.lmp_data) == 4
    
    # Check Michigan 08:00 entry
    michigan_0800 = next((l for l in data.lmp_data 
                          if l.intertie_point == "MICHIGAN" and l.timestamp.hour == 8 and l.timestamp.minute == 0), None)
    assert michigan_0800 is not None
    assert michigan_0800.lmp_mwh == 25.50
    
    # Check Michigan 08:05 entry
    michigan_0805 = next((l for l in data.lmp_data 
                          if l.intertie_point == "MICHIGAN" and l.timestamp.hour == 8 and l.timestamp.minute == 5), None)
    assert michigan_0805 is not None
    assert michigan_0805.lmp_mwh == 26.00
    
    # Check New York entry
    newyork_0800 = next((l for l in data.lmp_data 
                         if l.intertie_point == "NEW_YORK" and l.timestamp.hour == 8 and l.timestamp.minute == 0), None)
    assert newyork_0800 is not None
    assert newyork_0800.lmp_mwh == 24.75
    
    # Check Quebec entry
    quebec_0800 = next((l for l in data.lmp_data 
                        if l.intertie_point == "QUEBEC" and l.timestamp.hour == 8 and l.timestamp.minute == 0), None)
    assert quebec_0800 is not None
    assert quebec_0800.lmp_mwh == 23.20
    
    # Check that we have the right intertie points
    points = data.get_intertie_points()
    assert set(points) == {"MICHIGAN", "NEW_YORK", "QUEBEC"}


def test_get_lmp_by_intertie():
    """Test getting LMP data by intertie point."""
    client = IESOIntertieLMPClient(MagicMock())
    data = client._parse_xml(SAMPLE_XML)
    
    michigan_data = data.get_lmp_by_intertie("MICHIGAN")
    assert len(michigan_data) == 2  # Two time points for Michigan
    
    newyork_data = data.get_lmp_by_intertie("NEW_YORK")
    assert len(newyork_data) == 1  # One time point for New York
    
    quebec_data = data.get_lmp_by_intertie("QUEBEC")
    assert len(quebec_data) == 1  # One time point for Quebec
    
    # Check that data is sorted by time (should be in order from XML)
    assert michigan_data[0].timestamp < michigan_data[1].timestamp


def test_get_latest_lmp_by_intertie():
    """Test getting the most recent LMP by intertie point."""
    client = IESOIntertieLMPClient(MagicMock())
    data = client._parse_xml(SAMPLE_XML)
    
    latest_michigan = data.get_latest_lmp_by_intertie("MICHIGAN")
    assert latest_michigan is not None
    assert latest_michigan.intertie_point == "MICHIGAN"
    assert latest_michigan.timestamp.hour == 8
    assert latest_michigan.timestamp.minute == 5  # Latest timestamp
    assert latest_michigan.lmp_mwh == 26.00  # Latest value
    
    latest_newyork = data.get_latest_lmp_by_intertie("NEW_YORK")
    assert latest_newyork is not None
    assert latest_newyork.intertie_point == "NEW_YORK"
    assert latest_newyork.timestamp.hour == 8
    assert latest_newyork.timestamp.minute == 0  # Only timestamp
    assert latest_newyork.lmp_mwh == 24.75  # Only value
    
    latest_quebec = data.get_latest_lmp_by_intertie("QUEBEC")
    assert latest_quebec is not None
    assert latest_quebec.intertie_point == "QUEBEC"
    assert latest_quebec.timestamp.hour == 8
    assert latest_quebec.timestamp.minute == 0  # Only timestamp
    assert latest_quebec.lmp_mwh == 23.20  # Only value


def test_empty_intertie_lmp():
    """Test parsing of empty intertie LMP XML."""
    client = IESOIntertieLMPClient(MagicMock())
    data = client._parse_xml(EMPTY_XML)
    
    assert len(data.lmp_data) == 0
    assert data.get_intertie_points() == []


def test_get_latest_lmp_by_intertie_empty():
    """Test getting latest LMP from empty data returns None."""
    client = IESOIntertieLMPClient(MagicMock())
    data = client._parse_xml(EMPTY_XML)
    
    result = data.get_latest_lmp_by_intertie("MICHIGAN")
    assert result is None


if __name__ == "__main__":
    test_parse_intertie_lmp_xml()
    test_get_lmp_by_intertie()
    test_get_latest_lmp_by_intertie()
    test_empty_intertie_lmp()
    test_get_latest_lmp_by_intertie_empty()
    print("✅ All Intertie LMP tests passed!")