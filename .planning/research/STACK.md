# Stack Research: Ontario Energy Pricing HACS Integration

**Research Date:** 2025-04-11
**Researcher:** Claude Code

---

## Overview

Home Assistant custom integration that exposes Ontario electricity pricing data through three sensors:
1. **Current Electricity Price** (LMP from IESO, post-HOEP retirement)
2. **Global Adjustment** (from IESO public XML)
3. **Administrative Fee** (user-configured static value)

---

## 1. Data Source Stack

### Electricity Pricing Data (Formerly HOEP)

**Finding:** IESO retired HOEP on May 1, 2025 as part of Market Renewal.

**Current Source:** GridStatus.io API
- **Dataset:** `ieso_lmp_real_time_5_min_all`
- **Description:** Real-time 5-minute LMP data for all Ontario nodes/zones
- **Authentication:** Bearer token (API key)
- **Update Frequency:** 5 minutes (will poll hourly for sensor)
- **Cost:** Free tier available

**API Details:**
```
Endpoint: https://api.gridstatus.io/v1/datasets/ieso_lmp_real_time_5_min_all/query
Auth: Authorization: Bearer <API_KEY>
Query params: start, end, timezone, limit
```

**Response:** JSON with fields:
- `interval_start_local` / `interval_end_local` - timestamps
- `location` - zone/node name
- `lmp` - locational marginal price
- Various LMP components (energy, congestion, loss)

**For Oakville:** Filter by zone (likely "ONTARIO" or distribution zone)

### Global Adjustment Data

**Source:** IESO Public Reports
**URL:** `http://reports.ieso.ca/public/GlobalAdjustment/PUB_GlobalAdjustment.xml`
**Format:** XML
**Update Frequency:** Monthly (new file published ~15th of month for next month)

**XML Structure:**
```xml
<Document>
  <DocBody>
    <TradeMonth>2026-04</TradeMonth>
    <GAValues>
      <FirstEstimateRate>0.06</FirstEstimateRate>
    </GAValues>
  </DocBody>
</Document>
```

**Notes:**
- Rate in $/kWh (0.06 = 6 cents/kWh)
- "First Estimate" - may be revised later
- Monthly file naming: `PUB_GlobalAdjustment_YYYYMM.xml`

### Administrative Fee

**Source:** User configuration (no external API)
- Fixed value entered during config flow
- Persists across restarts
- No polling needed (truly static)

---

## 2. Home Assistant Integration Stack

### Core Framework
- **Platform:** Python 3.12+
- **Framework:** Home Assistant Core API
- **Pattern:** Integration/Platform pattern with Config Flow

### Required Components

| Component | Purpose | File |
|-----------|---------|------|
| `manifest.json` | Integration metadata | Required |
| `__init__.py` | Component initialization | Required |
| `config_flow.py` | Configuration UI | Required for config entries |
| `sensor.py` | Sensor platform | Required |
| `coordinator.py` | Data update coordination | Recommended |

### Manifest Requirements
```json
{
  "domain": "ontario_energy_pricing",
  "name": "Ontario Energy Pricing",
  "version": "1.0.0",
  "codeowners": ["@dmalloc"],
  "config_flow": true,
  "dependencies": [],
  "documentation": "https://github.com/dmalloc/ontario-energy-pricing",
  "integration_type": "service",
  "iot_class": "cloud_polling",
  "requirements": []
}
```

### HACS Requirements

**Repository Structure:**
```
repo-root/
├── custom_components/
│   └── ontario_energy_pricing/
│       ├── __init__.py
│       ├── manifest.json
│       ├── config_flow.py
│       ├── sensor.py
│       └── coordinator.py
├── hacs.json
├── README.md
└── LICENSE
```

**hacs.json:**
```json
{
  "name": "Ontario Energy Pricing",
  "hacs": "1.6.0",
  "render_readme": true
}
```

---

## 3. Python Dependencies

### Core Dependencies (Home Assistant provides)
- `aiohttp` - HTTP async client (provided by HA core)
- `voluptuous` - Config validation (provided by HA core)

### Integration-Specific
- None required for external APIs (using direct HTTP with aiohttp)
- Standard library: `xml.etree.ElementTree` for parsing IESO XML

### Development Dependencies
- `pytest-homeassistant-custom-component` - Testing (optional)

---

## 4. Architecture Patterns

### DataUpdateCoordinator Pattern
**Recommendation:** Use HA's `DataUpdateCoordinator` for both pricing sensors

**Benefits:**
- Coordinated polling across entities
- Automatic retry logic
- Throttling/backoff
- Shared update logic

**Implementation:**
- Create `OntarioPricingCoordinator` for LMP data (hourly updates)
- Create `GlobalAdjustmentCoordinator` for GA data (weekly updates)
- Each coordinator polls its own source at appropriate frequency

### Config Flow Pattern
**Required for user input:**
- GridStatus API key (text input, password mask)
- Administrative fee (number input, CAD)
- Optional: Zone override (default to Ontario-wide)

---

## 5. Decisions Summary

| Decision | Choice | Rationale |
|----------|--------|-----------|
| LMP vs HOEP | LMP via `ieso_lmp_real_time_5_min_all` | HOEP retired May 2025 |
| GA Source | IESO Public XML | Free, no auth, machine-readable |
| HA Pattern | Config Flow + Coordinator | Standard for cloud-polling integrations |
| HTTP Client | aiohttp (HA bundled) | No extra dependencies |
| XML Parser | xml.etree.ElementTree | Standard library |
| HACS Support | Yes | User requested custom repo install |
| Update Frequency | Hourly (LMP), Weekly (GA) | As specified by user |

---

## References

1. GridStatus IESO Documentation: https://docs.gridstatus.io/data-guides/market-guides/independent-electricity-system-operator-ieso
2. IESO Global Adjustment Reports: http://reports.ieso.ca/public/GlobalAdjustment/
3. IESO Market Renewal Info: https://ieso.ca/Market-Renewal
4. HA Integration Development: https://developers.home-assistant.io/docs/creating_integration_file_structure
5. HACS Integration Requirements: https://hacs.xyz/docs/publish/integration

---

*Generated: 2025-04-11*
