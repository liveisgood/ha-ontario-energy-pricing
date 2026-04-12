# Phase 2: Core Entities - Validation Plan

**Phase:** 02-core-entities  
**Plan:** Validation/Test Implementation  
**Wave:** 2 (Validation)  
**Created:** 2026-04-12  
**Agent:** gsd-nyquist-auditor  

---

## Objectives

Create comprehensive pytest-based test suite for Phase 2 Core Entities:
1. Test all 4 sensor entities with mocked coordinators
2. Test 3 data coordinators with mocked API clients
3. Test config flow with mocked API responses
4. Test component lifecycle (setup/unload/reload)
5. Achieve >80% code coverage on coordinator.py and sensor.py

---

## Requirements to Validate

| Req ID | Requirement | Target File | Priority |
|--------|-------------|-------------|----------|
| SENS-01 | Current LMP sensor exposes timestamp | test_sensor.py | High |
| SENS-02 | 24h Average LMP sensor | test_sensor.py | High |
| SENS-03 | Global Adjustment sensor | test_sensor.py | High |
| SENS-04 | Total Rate sensor combines values | test_sensor.py | High |
| SENS-05 | Sensor attributes (timestamp, previous_rate) | test_sensor.py | High |
| SENS-06 | Device class MONETARY | test_sensor.py | Medium |
| CONF-01 | Config flow entry point exists | test_config_flow.py | High |
| CONF-02 | API key input form validates | test_config_flow.py | High |
| CONF-05 | Zone selection step works | test_config_flow.py | Medium |
| CONF-06 | Config entry created successfully | test_config_flow.py | High |
| SCH-01 | Hourly LMP coordinator updates | test_coordinator.py | High |
| SCH-02 | Daily 24h average coordinator | test_coordinator.py | High |
| SCH-03 | Monthly GA coordinator | test_coordinator.py | Medium |
| SCH-04 | Entry unload/reload functions | test_init.py | Medium |
| LOC-01 | Location input accepted | test_config_flow.py | Medium |
| LOC-02 | Zone discovery API called | test_config_flow.py | Medium |
| LOC-03 | Zone matching logic | test_config_flow.py | Medium |
| LOC-04 | Zone persisted in config entry | test_config_flow.py | Medium |

---

## Test Infrastructure

### Framework Setup
```
tests/
├── conftest.py           # Shared fixtures
├── test_init.py          # Component lifecycle
├── test_coordinator.py   # Data coordinators
├── test_sensor.py        # Sensor entities
└── test_config_flow.py   # Configuration flow
```

### Key Fixtures (conftest.py)

1. **MockHA Fixtures**
   - `mock_hass` - Mock HomeAssistant instance
   - `mock_config_entry` - ConfigEntry with test data
   - `mock_entry_data` - Entry data dict

2. **Mock API Clients**
   - `mock_gridstatus_client` - AsyncMock for GridStatusClient
   - `mock_ieso_client` - AsyncMock for IESOGlobalAdjustment

3. **Mock Data Models**
   - `sample_lmp_price` - LMPCurrentPrice fixture
   - `sample_lmp_history` - LMPHistoricalData fixture
   - `sample_ga` - GlobalAdjustment fixture

4. **Coordinator Fixtures**
   - `lmp_coordinator` - LMPCoordinator with mocked client
   - `lmp_24h_coordinator` - LMP24hAverageCoordinator
   - `ga_coordinator` - GlobalAdjustmentCoordinator

### Dependencies (conftest.py or pytest.ini)

```python
# Requirements for testing:
pytest>=7.0.0
pytest-asyncio>=0.21.0
pytest-aiohttp>=1.0.4
pytest-homeassistant-custom-component>=0.13.0
aioresponses>=0.7.4
```

---

## Test Tasks

### Task 1: Test Infrastructure Setup

**File:** `tests/conftest.py`

<action>
1. Create tests/ directory at project root
2. Create conftest.py with Home Assistant test fixtures
3. Add mock_hass fixture with required hass.data setup
4. Add mock_config_entry fixture with complete entry data
5. Create GridStatusClient mock with async methods
6. Create IESO client mock with async_fetch_global_adjustment
</action>

<acceptance_criteria>
- conftest.py loads without errors
- mock_hass provides valid HomeAssistant-like object
- mock_config_entry contains all required keys: api_key, zone, admin_fee
- Mock clients have proper async return values
</acceptance_criteria>

---

### Task 2: Component Lifecycle Tests

**File:** `tests/test_init.py`

<action>
1. Test async_setup_entry success path
2. Test async_setup_entry failure (bad API key)
3. Test async_unload_entry removes data from hass.data
4. Test async_reload_entry re-initializes
5. Test setup stores coordinators in hass.data[DOMAIN][entry_id]
</action>

<acceptance_criteria>
- setup_entry returns True on success
- unload_entry returns True and cleans up hass.data
- reload_entry calls unload then setup
- Proper error handling for coordinator init failures
</acceptance_criteria>

**Requirements:** SCH-04 (Entry unload/reload)

---

### Task 3: Data Coordinator Tests

**File:** `tests/test_coordinator.py`

<action>
1. **LMPCoordinator tests:**
   - test_lmp_coordinator_update_success - Returns LMPCurrentPrice
   - test_lmp_coordinator_update_failure - Raises UpdateFailed on API error
   - test_lmp_coordinator_update_interval - Verify 1 hour interval

2. **LMP24hAverageCoordinator tests:**
   - test_lmp_24h_update_success - Computes average from history
   - test_lmp_24h_empty_history - Handles empty history gracefully
   - test_lmp_24h_update_interval - Verify 24 hour interval

3. **GlobalAdjustmentCoordinator tests:**
   - test_ga_coordinator_update_success - Returns GlobalAdjustment
   - test_ga_coordinator_xml_parse_error - Handles XML errors
   - test_ga_coordinator_update_interval - Verify 1 week interval

4. **Error handling tests:**
   - test_coordinator_auth_error - GridStatusAuthError handling
   - test_coordinator_connection_error - ConnectionError handling
   - test_coordinator_retry_behavior - Verify retry logic
</action>

<acceptance_criteria>
- Each coordinator returns correct model type
- UpdateFailed raised on API errors
- Sensors become unavailable when UpdateFailed raised
- Update intervals match specification (1h, 24h, 1w)
- Exceptions properly chained with `from err`
</acceptance_criteria>

**Requirements:** SCH-01, SCH-02, SCH-03, ERR-01, ERR-02

---

### Task 4: Sensor Entity Tests

**File:** `tests/test_sensor.py`

<action>
1. **Current LMP Sensor:**
   - test_current_lmp_sensor_state - Returns price value
   - test_current_lmp_sensor_attributes - Has timestamp, zone, previous_rate
   - test_current_lmp_sensor_device_class - MONETARY
   - test_current_lmp_sensor_unavailable - None when coordinator fails

2. **24h Average Sensor:**
   - test_lmp_24h_sensor_state - Returns average value
   - test_lmp_24h_sensor_attributes - Has timestamp
   - test_lmp_24h_sensor_unavailable - None when no history

3. **Global Adjustment Sensor:**
   - test_ga_sensor_state - Returns GA rate
   - test_ga_sensor_attributes - Has trade_month
   - test_ga_sensor_device_class - MONETARY
   - test_ga_sensor_unavailable - None when coordinator fails

4. **Total Rate Sensor:**
   - test_total_rate_calculation - LMP + GA + admin_fee
   - test_total_rate_missing_lmp - Handles missing LMP
   - test_total_rate_missing_ga - Handles missing GA
   - test_total_rate_attributes - Shows component breakdown

5. **Platform setup test:**
   - test_async_setup_entry_sensors - Creates all 4 sensors
</action>

<acceptance_criteria>
- All 4 sensors have correct entity IDs
- native_value returns float or None (not string)
- Attributes match specification from SUMMARY.md
- Device class MONETARY set on all monetary sensors
- Total Rate correctly sums LMP + GA + admin_fee
- Sensors become unavailable (state None) on coordinator failure
</acceptance_criteria>

**Requirements:** SENS-01 to SENS-06

---

### Task 5: Config Flow Tests

**File:** `tests/test_config_flow.py`

<action>
1. **User step tests:**
   - test_config_flow_user_step_form - Shows input form
   - test_config_flow_user_step_valid - Validates user input
   - test_config_flow_invalid_api_key - Shows error on empty key
   - test_config_flow_invalid_admin_fee - Shows error on negative fee

2. **API test step tests:**
   - test_config