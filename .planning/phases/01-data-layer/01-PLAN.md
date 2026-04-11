# Phase 1: Data Layer - Plan 01

**Plan:** 01 - Data Models and API Clients  
**Wave:** 1  
**Type:** Infrastructure  
**Created:** 2026-04-11  
**Phase:** 01-data-layer

---

## Objective

Create the GridStatus API client, IESO XML parser, and data models for the Ontario Energy Pricing integration. These are the foundational components that Phase 2 (coordinators) will consume.

---

## Phase Requirements Addressed

- **DATA-01** - GridStatus API client for LMP data
- **DATA-02** - Zone-specific data filtering (via zone parameter)
- **DATA-03** - 24-hour LMP history retrieval
- **DATA-04** - Aggregate 5-min data to 30-min averages
- **DATA-05** - IESO Global Adjustment XML retrieval
- **DATA-06** - GA XML parsing
- **DATA-07** - Previous hour LMP caching (data structure supports this)

---

## Files to Create/Modify

### New Files
- `custom_components/ontario_energy_pricing/__init__.py` (empty, just module marker)
- `custom_components/ontario_energy_pricing/const.py` - Domain constants
- `custom_components/ontario_energy_pricing/exceptions.py` - Custom exceptions
- `custom_components/ontario_energy_pricing/models.py` - Data models
- `custom_components/ontario_energy_pricing/gridstatus.py` - GridStatus API client
- `custom_components/ontario_energy_pricing/ieso.py` - IESO XML client
- `tests/__init__.py` - Test module marker
- `tests/conftest.py` - Pytest fixtures
- `tests/test_models.py` - Model tests
- `tests/test_gridstatus.py` - API client tests
- `tests/test_ieso.py` - XML parser tests

---

## Tasks

### Task 1: Create Project Structure

<read_first>
- `.planning/phases/01-data-layer/01-CONTEXT.md` - Implementation decisions
- `.planning/PROJECT.md` - Project overview
</read_first>

<action>
Create the directory structure for the custom component:

1. Create directories:
   - `custom_components/ontario_energy_pricing/`
   - `tests/`

2. Create empty `__init__.py` files in both directories

3. Create `const.py` with:
   - `DOMAIN = "ontario_energy_pricing"`
   - `LOGGER` constant
   - GridStatus API base URL
   - IESO GA URL
   - Default timeouts
</action>

<acceptance_criteria>
- `custom_components/ontario_energy_pricing/__init__.py` exists and is importable
- `custom_components/ontario_energy_pricing/const.py` contains DOMAIN, LOGGER, and URLs
- `tests/__init__.py` exists
</acceptance_criteria>

---

### Task 2: Define Custom Exceptions

<read_first>
- `custom_components/ontario_energy_pricing/const.py` - Domain constant for logger
- `.planning/phases/01-data-layer/01-CONTEXT.md` - Error handling strategy
</read_first>

<action>
Create `custom_components/ontario_energy_pricing/exceptions.py` with:

1. Base exception class inheriting from `HomeAssistantError`
2. Specific exceptions:
   - `GridStatusAuthError` - 401 responses, authentication failure
   - `GridStatusAPIError` - 5xx responses, API errors
   - `IESOXMLParseError` - XML parsing failures
   - `ZoneNotFoundError` - No matching zone for location
   - `GridStatusConnectionError` - Network/connectivity errors

All exceptions should:
- Accept message parameter
- Accept translation_key for translations
- Accept translation_placeholders dict
</action>

<acceptance_criteria>
- `custom_components/ontario_energy_pricing/exceptions.py` exists
- All exception classes defined with proper inheritance
- Each exception accepts message, translation_key, translation_placeholders
</acceptance_criteria>

---

### Task 3: Create Data Models

<read_first>
- `.planning/phases/01-data-layer/01-CONTEXT.md` - Model decisions (frozen dataclasses)
- `.planning/REQUIREMENTS.md` - DATA-01 to DATA-07 requirements
</read_first>

<action>
Create `custom_components/ontario_energy_pricing/models.py` with frozen dataclasses:

1. `@dataclass(frozen=True, slots=True)` for memory efficiency
   - `LMPCurrentPrice`: price (float), timestamp (datetime), zone (str), previous_price (float | None)
   - `LMPHistoricalData`: list of LMPDataPoint, zone (str)
   - `LMPDataPoint`: timestamp (datetime), price (float)
   - `GlobalAdjustment`: rate (float), trade_month (str), last_updated (datetime)
   - `AdminFeeConfig`: rate (float)

2. All datetime fields must be timezone-aware (US/Eastern for IESO data)

3. Include type annotations everywhere - Python 3.14+ compatible

4. Add `__str__` methods for debugging

5. Include 24h aggregation method on LMPHistoricalData
</action>

<acceptance_criteria>
- `custom_components/ontario_energy_pricing/models.py` exists
- All dataclasses use `@dataclass(frozen=True, slots=True)`
- All fields have type annotations
- `LMPCurrentPrice`, `LMPHistoricalData`, `LMPDataPoint`, `GlobalAdjustment` defined
- `aggregate_to_30min()` method exists on LMPHistoricalData
- All datetime fields are timezone-aware
</acceptance_criteria>

---

### Task 4: Implement GridStatus API Client

<read_first>
- `custom_components/ontario_energy_pricing/models.py` - Data models to return
- `custom_components/ontario_energy_pricing/exceptions.py` - Exceptions to raise
- `custom_components/ontario_energy_pricing/const.py` - API URLs
- `.planning/phases/01-data-layer/01-CONTEXT.md` - D-02 (API client architecture)
</read_first>

<action>
Create `custom_components/ontario_energy_pricing/gridstatus.py`:

1. Class `GridStatusClient`:
   - `__init__(self, api_key: str, session: ClientSession) -> None`
   - `api_key`: GridStatus API key
   - `session`: aiohttp ClientSession (injected from HA)

2. Method `async_get_current_lmp(self, zone: str) -> LMPCurrentPrice`:
   - Query GridStatus API for current hour
   - Filter by zone parameter
   - Return LMPCurrentPrice

3. Method `async_get_24h_history(self, zone: str) -> LMPHistoricalData`:
   - Query past 24 hours of 5-minute data
   - Return LMPHistoricalData with all data points

4. Method `async_get_available_zones(self) -> list[str]`:
   - Query API to get unique zone names
   - Used for zone discovery

5. Proper error handling:
   - 401 -> GridStatusAuthError
   - 5xx -> GridStatusAPIError
   - Network -> GridStatusConnectionError
   - JSON parse errors -> wrapped exceptions

6. API endpoint: `https://api.gridstatus.io/v1/datasets/ieso_lmp_real_time_5_min_all/query`
</action>

<acceptance_criteria>
- `custom_components/ontario_energy_pricing/gridstatus.py` exists
- `GridStatusClient` class with `__init__`, `async_get_current_lmp`, `async_get_24h_history`, `async_get_available_zones`
- `ClientSession` is required parameter (no default session creation)
- GridStatus API base URL defined in const.py
- Proper exception types raised for each error case
- All methods have complete type annotations
</acceptance_criteria>

---

### Task 5: Implement IESO XML Client

<read_first>
- `custom_components/ontario_energy_pricing/models.py` - GlobalAdjustment model
- `custom_components/ontario_energy_pricing/exceptions.py` - IESOXMLParseError
- `custom_components/ontario_energy_pricing/const.py` - IESO GA URL
- `.planning/phases/01-data-layer/01-CONTEXT.md` - D-08 (XML parsing)
</read_first>

<action>
Create `custom_components/ontario_energy_pricing/ieso.py`:

1. Class `IESOGlobalAdjustmentClient`:
   - `__init__(self, session: ClientSession) -> None`
   - Optional: can also use regular aiohttp without injection (IESO is simple XML)

2. Method `async_get_current_rate(self) -> GlobalAdjustment`:
   - Fetch from `http://reports.ieso.ca/public/GlobalAdjustment/PUB_GlobalAdjustment.xml`
   - Parse XML with ElementTree
   - Extract TradeMonth and FirstEstimateRate
   - Return GlobalAdjustment model

3. Method `async_get_historical_rates(self, months: int = 3) -> list[GlobalAdjustment]`:
   - Fetch historical XML files (PUB_GlobalAdjustment_YYYYMM.xml)
   - Return list of GlobalAdjustment

4. Defensive XML parsing:
   - Check element exists before accessing
   -