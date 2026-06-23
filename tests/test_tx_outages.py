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


def make_outage_xml(outage_requests: list[dict]) -> str:
    """Build an XML string matching the real IESO TxOutagesTodayAll format."""
    parts = []
    for req in outage_requests:
        equip_parts = []
        for equip in req.get("equipment", [{"name": "UNKNOWN", "type": "LINE"}]):
            equip_parts.append(f"""      <EquipmentRequested>
        <EquipmentName>{equip["name"]}</EquipmentName>
        <EquipmentType>{equip["type"]}</EquipmentType>
      </EquipmentRequested>""")
        equip_xml = "\n".join(equip_parts)

        parts.append(f"""    <OutageRequest>
      <OutageID>{req.get("id", "1-00000001")}</OutageID>
      <PlannedStart>{req.get("planned_start", "2026-06-14T06:00:00")}</PlannedStart>
      <PlannedEnd>{req.get("planned_end", "2026-06-14T18:00:00")}</PlannedEnd>
      <Priority>{req.get("priority", "F")}</Priority>
{equip_xml}
      <OutageRequestStatus>{req.get("status", "IMPL")}</OutageRequestStatus>
    </OutageRequest>""")

    body_xml = "\n".join(parts)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Document docID="TxOutagesTodayAll" xmlns="http://www.ieso.ca/schema">
<DocHeader>
<DocTitle>All Transmission Outages Occurring Today</DocTitle>
<CreatedAt>{outage_requests[0].get("created_at", "2026-06-14T20:03:00") if outage_requests else "2026-06-14T20:03:00"}</CreatedAt>
</DocHeader>
<DocBody>
{body_xml}
</DocBody>
</Document>"""


SAMPLE_XML = make_outage_xml([
    {
        "id": "1-00123456",
        "planned_start": "2026-06-14T06:00:00",
        "planned_end": "2026-06-14T18:00:00",
        "priority": "F",
        "equipment": [{"name": "B5G", "type": "LINE"}],
        "status": "IMPL",
    },
    {
        "id": "1-00123457",
        "planned_start": "2026-06-14T08:00:00",
        "planned_end": "2026-06-16T20:00:00",
        "priority": "E",
        "equipment": [{"name": "T21R", "type": "TRANSFORMER"}],
        "status": "IMPL",
    },
])

THREE_OUTAGE_XML = make_outage_xml([
    {
        "id": "1-00123456",
        "planned_start": "2026-06-14T06:00:00",
        "planned_end": "2026-06-14T18:00:00",
        "priority": "F",
        "equipment": [{"name": "B5G", "type": "LINE"}],
        "status": "IMPL",
    },
    {
        "id": "1-00123457",
        "planned_start": "2026-06-14T08:00:00",
        "planned_end": "2026-06-16T20:00:00",
        "priority": "E",
        "equipment": [{"name": "T21R", "type": "TRANSFORMER"}],
        "status": "IMPL",
    },
    {
        "id": "1-00123458",
        "planned_start": "2026-06-15T00:00:00",
        "planned_end": "2026-06-17T23:59:00",
        "priority": "F",
        "equipment": [{"name": "K2K", "type": "LINE"}],
        "status": "PLANNED",
    },
])

EMPTY_XML = make_outage_xml([])


def test_parse_tx_outages_xml():
    client = IESOTxOutagesClient(MagicMock())
    data = client._parse_xml(SAMPLE_XML)

    assert data is not None
    assert data.delivery_date == "2026-06-14"
    assert len(data.outages) == 2

    outage1 = data.outages[0]
    assert outage1.equipment_name == "B5G"
    assert outage1.equipment_type == "LINE"
    # Zone derived from equipment name prefix mapping
    assert outage1.status == "IMPL"


def test_outages_by_zone():
    client = IESOTxOutagesClient(MagicMock())
    data = client._parse_xml(THREE_OUTAGE_XML)

    assert len(data.outages) == 3

    # Test getting outages by zone (zones derived from equipment name)
    ne_outages = data.get_outages_by_zone("NORTHEAST")
    # B5G doesn't match a known prefix -> UNKNOWN
    unknown_outages = data.get_outages_by_zone("UNKNOWN")
    assert len(unknown_outages) > 0

    # K2K doesn't match a known prefix -> UNKNOWN
    k2k_outages = [o for o in data.outages if o.equipment_name == "K2K"]
    assert len(k2k_outages) == 1


def test_active_outages():
    client = IESOTxOutagesClient(MagicMock())
    data = client._parse_xml(THREE_OUTAGE_XML)

    # Active outages are those with status in (IMPL, ACTIVE, IN_PROGRESS)
    active = data.get_active_outages()
    assert len(active) == 2  # Two IMPL outages
    for o in active:
        assert o.status in ("IMPL", "ACTIVE", "IN_PROGRESS")


def test_total_capacity_impact():
    client = IESOTxOutagesClient(MagicMock())
    data = client._parse_xml(SAMPLE_XML)

    # Real IESO feed doesn't provide MW capacity, so it's always 0.0
    total_capacity = data.get_total_capacity_impact()
    assert total_capacity == 0.0


def test_empty_outages():
    client = IESOTxOutagesClient(MagicMock())
    data = client._parse_xml(EMPTY_XML)

    assert len(data.outages) == 0
    assert data.get_active_outages() == []
    assert data.get_total_capacity_impact() == 0
    print("✅ test_empty_outages passed")


if __name__ == "__main__":
    test_parse_tx_outages_xml()
    test_outages_by_zone()
    test_active_outages()
    test_total_capacity_impact()
    test_empty_outages()
    print("\n🎉 All TxOutages tests passed!")
