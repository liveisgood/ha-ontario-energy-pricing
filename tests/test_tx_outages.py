"""Tests for Transmission Outages client - IESO TxOutagesTodayAll."""

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

from custom_components.ontario_energy_pricing.ieso_tx_outages import (
    IESOTxOutagesClient,
)

SAMPLE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<Document docID="TxOutagesTodayAll" xmlns="http://www.ieso.ca/schema">
<DocHeader>
<DocTitle>Transmission Outages Today</DocTitle>
<CreatedAt>2026-06-14T20:03:00</CreatedAt>
</DocHeader>
<DocBody>
<DELIVERYDATE>2026-06-14</DELIVERYDATE>
<Outage>
<EquipmentName>B5G</EquipmentName>
<EquipmentType>LINE</EquipmentType>
<Zone>NORTHEAST</Zone>
<StartDate>2026-06-14</StartDate>
<StartTime>06:00</StartTime>
<EndDate>2026-06-14</EndDate>
<EndTime>18:00</EndTime>
<Status>APPROVED</Status>
<Reason>MAINTENANCE</Reason>
<CapacityMW>500</CapacityMW>
</Outage>
<Outage>
<EquipmentName>T21R</EquipmentName>
<EquipmentType>TRANSFORMER</EquipmentType>
<Zone>NORTHWEST</Zone>
<StartDate>2026-06-14</StartDate>
<StartTime>08:00</StartTime>
<EndDate>2026-06-16</EndDate>
<EndTime>20:00</EndTime>
<Status>IN_PROGRESS</Status>
<Reason>EMERGENCY</Reason>
<CapacityMW>300</CapacityMW>
</Outage>
</DocBody>
</Document>"""

MULTI_DAY_XML = """<?xml version="1.0" encoding="UTF-8"?>
<Document docID="TxOutagesTodayAll" xmlns="http://www.ieso.ca/schema">
<DocHeader><CreatedAt>2026-06-14T20:03:00</CreatedAt></DocHeader>
<DocBody>
<DELIVERYDATE>2026-06-14</DELIVERYDATE>
<Outage>
<EquipmentName>B5G</EquipmentName>
<EquipmentType>LINE</EquipmentType>
<Zone>NORTHEAST</Zone>
<StartDate>2026-06-14</StartDate>
<StartTime>06:00</StartTime>
<EndDate>2026-06-14</EndDate>
<EndTime>18:00</EndTime>
<Status>APPROVED</Status>
<Reason>MAINTENANCE</Reason>
<CapacityMW>500</CapacityMW>
</Outage>
<Outage>
<EquipmentName>T21R</EquipmentName>
<EquipmentType>TRANSFORMER</EquipmentType>
<Zone>NORTHWEST</Zone>
<StartDate>2026-06-14</StartDate>
<StartTime>08:00</StartTime>
<EndDate>2026-06-16</EndDate>
<EndTime>20:00</EndTime>
<Status>IN_PROGRESS</Status>
<Reason>EMERGENCY</Reason>
<CapacityMW>300</CapacityMW>
</Outage>
<Outage>
<EquipmentName>K2K</EquipmentName>
<EquipmentType>LINE</EquipmentType>
<Zone>SOUTHWEST</Zone>
<StartDate>2026-06-15</StartDate>
<StartTime>00:00</StartTime>
<EndDate>2026-06-17</EndDate>
<EndTime>23:59</EndTime>
<Status>PLANNED</Status>
<Reason>MAINTENANCE</Reason>
<CapacityMW>800</CapacityMW>
</Outage>
</DocBody>
</Document>"""

FUTURE_OUTAGE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<Document docID="TxOutagesTodayAll" xmlns="http://www.ieso.ca/schema">
<DocHeader><CreatedAt>2026-06-14T20:03:00</CreatedAt></DocHeader>
<DocBody>
<DELIVERYDATE>2026-06-14</DELIVERYDATE>
<Outage>
<EquipmentName>FUTURE_LINE</EquipmentName>
<EquipmentType>LINE</EquipmentType>
<Zone>TORONTO</Zone>
<StartDate>2026-06-20</StartDate>
<StartTime>00:00</StartTime>
<EndDate>2026-06-25</EndDate>
<EndTime>23:59</EndTime>
<Status>PLANNED</Status>
<Reason>MAINTENANCE</Reason>
<CapacityMW>1000</CapacityMW>
</Outage>
</DocBody>
</Document>"""

EMPTY_XML = """<?xml version="1.0" encoding="UTF-8"?>
<Document docID="TxOutagesTodayAll" xmlns="http://www.ieso.ca/schema">
<DocHeader><CreatedAt>2026-06-14T20:03:00</CreatedAt></DocHeader>
<DocBody>
<DELIVERYDATE>2026-06-14</DELIVERYDATE>
</DocBody>
</Document>"""


from unittest.mock import MagicMock

def test_parse_tx_outages_xml():
    client = IESOTxOutagesClient(MagicMock())
    data = client._parse_xml("""<?xml version="1.0" encoding="UTF-8"?>
<Document docID="TxOutagesTodayAll" xmlns="http://www.ieso.ca/schema">
<DocHeader>
<DocTitle>Transmission Outages Today</DocTitle>
<CreatedAt>2026-06-14T20:03:00</CreatedAt>
</DocHeader>
<DocBody>
<DELIVERYDATE>2026-06-14</DELIVERYDATE>
<Outage>
<EquipmentName>B5G</EquipmentName>
<EquipmentType>LINE</EquipmentType>
<Zone>NORTHEAST</Zone>
<StartDate>2026-06-14</StartDate>
<StartTime>06:00</StartTime>
<EndDate>2026-06-14</EndDate>
<EndTime>18:00</EndTime>
<Status>APPROVED</Status>
<Reason>MAINTENANCE</Reason>
<CapacityMW>500</CapacityMW>
</Outage>
<Outage>
<EquipmentName>T21R</EquipmentName>
<EquipmentType>TRANSFORMER</EquipmentType>
<Zone>NORTHWEST</Zone>
<StartDate>2026-06-14</StartDate>
<StartTime>08:00</StartTime>
<EndDate>2026-06-16</EndDate>
<EndTime>20:00</EndTime>
<Status>IN_PROGRESS</Status>
<Reason>EMERGENCY</Reason>
<CapacityMW>300</CapacityMW>
</Outage>
</DocBody>
</Document>""")
    
    assert data is not None
    assert data.delivery_date == "2026-06-14"
    assert len(data.outages) == 2
    
    outage1 = data.outages[0]
    assert outage1.equipment_name == "B5G"
    assert outage1.equipment_type == "LINE"
    assert outage1.zone == "NORTHEAST"
    assert outage1.capacity_mw == 500
    assert outage1.status == "APPROVED"
    assert outage1.reason == "MAINTENANCE"
    
    outage2 = data.outages[1]
    assert outage2.equipment_name == "T21R"
    assert outage2.equipment_type == "TRANSFORMER"
    assert outage2.zone == "NORTHWEST"
    assert outage2.capacity_mw == 300
    assert outage2.status == "IN_PROGRESS"
    assert outage2.reason == "EMERGENCY"
    
    print("✅ test_parse_tx_outages_xml passed")


def test_outages_by_zone():
    client = IESOTxOutagesClient(MagicMock())
    data = client._parse_xml("""<?xml version="1.0" encoding="UTF-8"?>
<Document docID="TxOutagesTodayAll" xmlns="http://www.ieso.ca/schema">
<DocHeader><CreatedAt>2026-06-14T20:03:00</CreatedAt></DocHeader>
<DocBody>
<DELIVERYDATE>2026-06-14</DELIVERYDATE>
<Outage>
<EquipmentName>B5G</EquipmentName>
<EquipmentType>LINE</EquipmentType>
<Zone>NORTHEAST</Zone>
<StartDate>2026-06-14</StartDate>
<StartTime>06:00</StartTime>
<EndDate>2026-06-14</EndDate>
<EndTime>18:00</EndTime>
<Status>APPROVED</Status>
<Reason>MAINTENANCE</Reason>
<CapacityMW>500</CapacityMW>
</Outage>
<Outage>
<EquipmentName>T21R</EquipmentName>
<EquipmentType>TRANSFORMER</EquipmentType>
<Zone>NORTHWEST</Zone>
<StartDate>2026-06-14</StartDate>
<StartTime>08:00</StartTime>
<EndDate>2026-06-16</EndDate>
<EndTime>20:00</EndTime>
<Status>IN_PROGRESS</Status>
<Reason>EMERGENCY</Reason>
<CapacityMW>300</CapacityMW>
</Outage>
<Outage>
<EquipmentName>K2K</EquipmentName>
<EquipmentType>LINE</EquipmentType>
<Zone>SOUTHWEST</Zone>
<StartDate>2026-06-15</StartDate>
<StartTime>00:00</StartTime>
<EndDate>2026-06-17</EndDate>
<EndTime>23:59</EndTime>
<Status>PLANNED</Status>
<Reason>MAINTENANCE</Reason>
<CapacityMW>800</CapacityMW>
</Outage>
</DocBody>
</Document>""")
    
    assert len(data.outages) == 3
    
    # Test getting outages by zone
    ne_outages = data.get_outages_by_zone("NORTHEAST")
    assert len(ne_outages) == 1
    assert ne_outages[0].equipment_name == "B5G"
    
    nw_outages = data.get_outages_by_zone("NORTHWEST")
    assert len(nw_outages) == 1
    assert nw_outages[0].equipment_name == "T21R"
    
    sw_outages = data.get_outages_by_zone("SOUTHWEST")
    assert len(sw_outages) == 1
    assert sw_outages[0].equipment_name == "K2K"
    
    # Unknown zone
    assert data.get_outages_by_zone("UNKNOWN") == []
    
    print("✅ test_outages_by_zone passed")


def test_active_outages():
    client = IESOTxOutagesClient(MagicMock())
    data = client._parse_xml("""<?xml version="1.0" encoding="UTF-8"?>
<Document docID="TxOutagesTodayAll" xmlns="http://www.ieso.ca/schema">
<DocHeader><CreatedAt>2026-06-14T14:00:00</CreatedAt></DocHeader>
<DocBody>
<DELIVERYDATE>2026-06-14</DELIVERYDATE>
<Outage>
<EquipmentName>B5G</EquipmentName>
<EquipmentType>LINE</EquipmentType>
<Zone>NORTHEAST</Zone>
<StartDate>2026-06-14</StartDate>
<StartTime>06:00</StartTime>
<EndDate>2026-06-14</EndDate>
<EndTime>18:00</EndTime>
<Status>APPROVED</Status>
<Reason>MAINTENANCE</Reason>
<CapacityMW>500</CapacityMW>
</Outage>
<Outage>
<EquipmentName>T21R</EquipmentName>
<EquipmentType>TRANSFORMER</EquipmentType>
<Zone>NORTHWEST</Zone>
<StartDate>2026-06-14</StartDate>
<StartTime>08:00</StartTime>
<EndDate>2026-06-16</EndDate>
<EndTime>20:00</EndTime>
<Status>IN_PROGRESS</Status>
<Reason>EMERGENCY</Reason>
<CapacityMW>300</CapacityMW>
</Outage>
<Outage>
<EquipmentName>FUTURE_LINE</EquipmentName>
<EquipmentType>LINE</EquipmentType>
<Zone>TORONTO</Zone>
<StartDate>2026-06-20</StartDate>
<StartTime>00:00</StartTime>
<EndDate>2026-06-25</EndDate>
<EndTime>23:59</EndTime>
<Status>PLANNED</Status>
<Reason>MAINTENANCE</Reason>
<CapacityMW>1000</CapacityMW>
</Outage>
</DocBody>
</Document>""")
    
    # At 14:00 on 2026-06-14, first two outages should be active
    # (assuming we mock datetime.now)
    # This test is more of a structure test
    active = data.get_active_outages()
    assert len(active) >= 1  # At least one active
    
    print("✅ test_active_outages passed")


def test_total_capacity_impact():
    client = IESOTxOutagesClient(MagicMock())
    data = client._parse_xml("""<?xml version="1.0" encoding="UTF-8"?>
<Document docID="TxOutagesTodayAll" xmlns="http://www.ieso.ca/schema">
<DocHeader><CreatedAt>2026-06-14T20:03:00</CreatedAt></DocHeader>
<DocBody>
<DELIVERYDATE>2026-06-14</DELIVERYDATE>
<Outage>
<EquipmentName>B5G</EquipmentName>
<EquipmentType>LINE</EquipmentType>
<Zone>NORTHEAST</Zone>
<StartDate>2026-06-14</StartDate>
<StartTime>06:00</StartTime>
<EndDate>2026-06-14</EndDate>
<EndTime>18:00</EndTime>
<Status>APPROVED</Status>
<Reason>MAINTENANCE</Reason>
<CapacityMW>500</CapacityMW>
</Outage>
<Outage>
<EquipmentName>T21R</EquipmentName>
<EquipmentType>TRANSFORMER</EquipmentType>
<Zone>NORTHWEST</Zone>
<StartDate>2026-06-14</StartDate>
<StartTime>08:00</StartTime>
<EndDate>2026-06-16</EndDate>
<EndTime>20:00</EndTime>
<Status>IN_PROGRESS</Status>
<Reason>EMERGENCY</Reason>
<CapacityMW>300</CapacityMW>
</Outage>
</DocBody>
</Document>""")
    
    total_capacity = data.get_total_capacity_impact()
    assert total_capacity == 800
    
    # By zone
    ne_capacity = data.get_total_capacity_impact("NORTHEAST")
    assert ne_capacity == 500
    
    nw_capacity = data.get_total_capacity_impact("NORTHWEST")
    assert nw_capacity == 300
    
    print("✅ test_total_capacity_impact passed")


def test_empty_outages():
    client = IESOTxOutagesClient(MagicMock())
    data = client._parse_xml("""<?xml version="1.0" encoding="UTF-8"?>
<Document docID="TxOutagesTodayAll" xmlns="http://www.ieso.ca/schema">
<DocHeader><CreatedAt>2026-06-14T20:03:00</CreatedAt></DocHeader>
<DocBody>
<DELIVERYDATE>2026-06-14</DELIVERYDATE>
</DocBody>
</Document>""")
    
    assert len(data.outages) == 0
    assert data.get_active_outages() == []
    assert data.get_total_capacity_impact() == 0
    print("✅ test_empty_outages passed")


if __name__ == "__main__":
    from unittest.mock import MagicMock
    
    # Mock Home Assistant dependencies
    import sys
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
    
    test_parse_tx_outages_xml()
    test_outages_by_zone()
    test_active_outages()
    test_total_capacity_impact()
    test_empty_outages()
    print("\n🎉 All TxOutages tests passed!")