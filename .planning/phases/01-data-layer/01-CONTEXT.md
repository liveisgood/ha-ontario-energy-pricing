# Phase 1: Data Layer - Context

**Gathered:** 2026-04-11  
**Status:** Ready for planning  
**Home Assistant Version Target:** 2026.4.x (current stable)

---

## Phase Boundary

Implement the underlying data infrastructure for the Ontario Energy Pricing integration:
- GridStatus API client with proper async HTTP handling
- IESO Global Adjustment XML parser
- Data models with full type hints for all API responses
- 5-minute to 30-minute aggregation logic
- Zone discovery for location-based LMP lookup

**Scope:** Data layer only - no sensors, no coordinators, no config flow. Just the API clients and data models that Phase 2 will consume.

---

## Implementation Decisions

### D-01: Python Version and Type System
**Decision:** Target Python 3.14.2+ (required for Home Assistant 2026.4.x)

**Implications:**
- Use modern Python syntax (PEP 695 type parameter syntax, pattern matching where appropriate)
- Enable strict mypy checking (`--strict` flag required for Gold quality scale)
- All functions must have complete type annotations
- No implicit `Any` types allowed

### D-02: API Client Architecture
**Decision:** Class-based async API client using Home Assistant's injected `aiohttp.ClientSession`

**Pattern:**
```python
class GridStatusClient:
    def __init__(self, api_key: str, session: ClientSession) -> None:
        self._api_key = api_key
        self._session = session
```

**Why:**
- Home Assistant 2026.x **requires** `async_get_clientsession(hass)` for all HTTP
- Connection pooling, SSL handling, timeouts managed by HA core
- This is a **platinum quality scale requirement**
- Makes testing easier (can inject mock session)

### D-03: Error Handling Strategy
**Decision:** Use HA's `UpdateFailed` and specific exceptions

**Exception Hierarchy:**
- `GridStatusAuthError` (ConfigEntryAuthFailed) - 401 responses
- `GridStatusAPIError` (UpdateFailed) - 5xx responses
- `IESOXMLParseError` (UpdateFailed) - XML parsing failures
- `ZoneNotFoundError` - No matching zone for location

**Why:**
- HA 2026 coordinators expect specific exception types
- Proper error types enable automatic retry/backoff
- Config flow can distinguish auth errors vs connectivity errors

### D-04: Data Models
**Decision:** Python dataclasses with `__future__` annotations

**Pattern:**
```python
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime

@dataclass(frozen=True, slots=True)
class LMPCurrentPrice:
    price: float  # $/kWh
    timestamp: datetime  # TZ-aware
    zone: str
    previous_price: float | None = None
```

**Why:**
- `frozen=True` - immutable data (safe for coordinator caching)
- `slots=True` - memory efficient (Python 3.10+)
- Full type annotations required for mypy strict mode
- No Pydantic - avoid extra dependencies (core HA doesn't use Pydantic)

### D-05: Data Aggregation Approach
**Decision:** On-demand aggregation, no raw data storage

**Process:**
1. Query 24h of 5-minute LMP data from GridStatus
2. Group into 30-minute buckets (6 x 5-min points per bucket)
3. Calculate average for each 30-min bucket
4. Return 48 x 30-min averages
5. Discard raw 5-min data

**Why:**
- Memory efficient (don't store 288 raw points)
- HA DataUpdateCoordinator handles caching anyway
- Simple to compute: `statistics.mean(prices)` for each bucket
- Previous hour cached via coordinator's `last_update_success_time`

### D-06: Zone Discovery
**Decision:** Query all zones from API, then fuzzy string match

**Algorithm:**
1. Query GridStatus for all available zones (sample API call)
2. User enters location string (e.g., "Oakville, ON")
3. Case-insensitive search: zone contains location or vice versa
4. If no match, fallback to "ONTARIO" (province-wide)
5. Store selected zone in config entry

**Why:**
- No hardcoded zone mappings needed (maintenance burden)
- Self-documenting: user sees available zones if query fails
- Works with IESO's nodal zones regardless of post-Market Renewal changes

### D-07: Testing Strategy
**Decision:** pytest-homeassistant-custom-component + snapshot testing

**Stack:**
- `pytest-homeassistant-custom-component` (community standard)
- `pytest-asyncio` mode="auto"
- `pytest-snapshot` / `syrupy` for API response snapshots
- `aioresponses` or `aresponses` for mocking aiohttp
- `mypy --strict` in CI (required for Gold quality scale)
- `ruff check --select I` for import sorting

**Why:**
- HA core = 90%+ coverage expectation
- Snapshot testing catches API schema changes
- pytest-homeassistant-custom-component provides HA fixtures
- 2026.x integrations must pass mypy strict to reach Gold

### D-08: XML Parsing
**Decision:** `xml.etree.ElementTree` with defensive parsing

**Pattern:**
```python
import xml.etree.ElementTree as ET

def parse_ga_xml(xml_text: str) -> GlobalAdjustment:
    try:
        root = ET.fromstring(xml_text)
        # Defensive: check elements exist before accessing
        trade_month = root.findtext('.//{http://www.ieso.ca/schema}TradeMonth')
        if trade_month is None:
            raise IESOXMLParseError("TradeMonth not found")
        ...
    except ET.ParseError as err:
        raise IESOXMLParseError(f"Invalid XML: {err}") from err
```

**Why:**
- Standard library (no extra deps like lxml)
- Namespace handling required for IESO schema
- Defensive parsing: validate before accessing (handles format changes)

---

## Canonical References

**Downstream agents MUST read these before implementing:**

### Home Assistant 2026.x Development
- `https://developers.home-assistant.io/docs/integration_fetching_data/` - Coordinator patterns, `_async_setup` method
- `https://developers.home-assistant.io/docs/config_entries_config_flow_handler/` - Config flow requirements
- `https://developers.home-assistant.io/docs/core/integration-quality-scale/` - Gold/Platinum quality scale requirements
- `https://github.com/home-assistant/developers.home-assistant/pull/2208` - Inject websession requirement (2024.8+)

### GridStatus API
- `https://docs.gridstatus.io/data-guides/market-guides/independent-electricity-system-operator-ieso` - IESO LMP documentation
- `https://www.gridstatus.io/datasets/ieso_lmp_real_time_5_min_all` - Dataset schema

### IESO Data
- `http://reports.ieso.ca/public/GlobalAdjustment/PUB_GlobalAdjustment.xml` - GA XML endpoint
- `http://reports.ieso.ca/public/GlobalAdjustment/GlobalAdjustment.xsd` - XML schema (if available)

---

## Existing Code Insights

### Reusable Assets (in HA Core)
- `homeassistant.helpers.update_coordinator.DataUpdateCoordinator` - Use for Phase 2
- `homeassistant.helpers.aiohttp_client.async_get_clientsession` - REQUIRED for HTTP
- `homeassistant.exceptions.ConfigEntryAuthFailed` - For auth errors
- `homeassistant.exceptions.UpdateFailed` - For data fetch errors

### Established Patterns
- All HA integrations use `from __future__ import annotations`
- Config entries stored via `async_create_entry`/`async_update_entry`
- Domain constant: `DOMAIN = "ontario_energy_pricing"`
- Logger: `_LOGGER = logging.getLogger(__name__)`

### Integration Points
- Phase 1 outputs: `GridStatusClient`, `IESOGlobalAdjustment`, data models
- Phase 2 consumes: these classes in coordinators
- HACS: `custom_components/ontario_energy_pricing/` folder structure

---

## Specific Ideas

- "I want this to be HACS-ready from day one - quality over speed"
- "If it can reach Gold quality scale, that's the target"
- "Python 3.14.2+ only - don't support old versions"
- Use `async_get_clientsession(hass)` always - this is non-negotiable for HA 2026.x

---

## Deferred Ideas

None - Phase 1 discussion stayed within scope.

---

*Phase: 01-data-layer*  
*Context gathered: 2026-04-11*  
*HA Target: 2026.4.x*
