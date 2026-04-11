# Phase 1: Data Layer - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.  
> Decisions are captured in CONTEXT.md - this log preserves the alternatives considered.

**Date:** 2026-04-11  
**Phase:** 01-data-layer  
**Areas discussed:** API Client Architecture, Data Models, Data Aggregation, Zone Discovery, Testing Strategy, Error Handling

---

## Discussion Summary

### Context
User specified:
- HACS/HASS best practices required (for possible community sharing)
- Automated testing essential for code quality
- Must be compatible with Home Assistant 2026.x
- Current date is April 2026, targeting HA 2026.4.x

### Key Decision
Research revealed HA 2026.x requires **Python 3.14.2+** - this drove several technical decisions.

---

## API Client Architecture

| Option | Description | Selected |
|--------|-------------|----------|
| **Injected ClientSession** | Use `async_get_clientsession(hass)` per HA best practices | ✓ |
| Standalone AsyncHTTP | Create own aiohttp session | |
| Requests (blocking) | Use requests library | |

**Research finding:** Injected web session is **platinum quality scale requirement** in HA 2026.x

**User's choice:** "Make sure you use the latest from HASS, we must be compatible with the latest release of 2026"

**Notes:**
- Confirmed `async_get_clientsession(hass)` is the only acceptable pattern
- Connection pooling and SSL handling managed by HA core
- Makes testing easier (can mock the session)

---

## Data Models

| Option | Description | Selected |
|--------|-------------|----------|
| **Dataclasses** | Python @dataclass with frozen=True, slots=True | ✓ |
| Pydantic | Pydantic models with validation | |
| TypedDict | Dictionary-based typing | |

**Notes:**
- No Pydantic - avoid extra dependencies (core HA doesn't use Pydantic)
- `frozen=True` for immutability (coordinator-safe)
- `slots=True` for memory efficiency
- Full type annotations required for mypy strict

---

## Data Aggregation

| Option | Description | Selected |
|--------|-------------|----------|
| **On-demand** | Query 24h, aggregate to 30-min, discard raw | ✓ |
| Cached Raw | Store 5-min points, compute on request | |
| Pre-computed | GridStatus provides averages directly | X - not available |

**Notes:**
- Memory efficient (don't store 288 raw points)
- HA DataUpdateCoordinator provides caching anyway
- Simple: statistics.mean() per 30-min bucket

---

## Zone Discovery

| Option | Description | Selected |
|--------|-------------|----------|
| **API Query + Fuzzy Match** | Get all zones from API, match user location | ✓ |
| Hardcoded Mapping | Maintain dict of city→zone mappings | |
| User Selection | Present list, user manually selects | |

**Notes:**
- No maintenance burden (no hardcoded mappings)
- Self-documenting (user sees available zones)
- IESO nodal zones changed with Market Renewal (May 2025)

---

## Testing Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| **pytest-homeassistant-custom-component** | Community standard + snapshots | ✓ |
| pytest-asyncio only | Basic async testing | |
| HA Core test style | Copy HA's complex test setup | |

**Required stack:**
- pytest-homeassistant-custom-component
- pytest-asyncio (mode="auto")
- syrupy/pytest-snapshot for API response snapshots
- aioresponses for aiohttp mocking
- mypy --strict (Gold quality requirement)

---

## Error Handling

| Exception Type | Use Case |
|----------------|----------|
| ConfigEntryAuthFailed | GridStatus 401 responses |
| UpdateFailed | All API errors (5xx, parse errors, network) |
| ZoneNotFoundError | No matching zone for location |

**Notes:**
- HA 2026 coordinators expect specific exception types
- Enables automatic retry/backoff
- Config flow distinguishes auth vs connectivity errors

---

## Dependencies

**Explicitly NOT using:**
- Pydantic (extra dependency, HA doesn't use)
- lxml for XML (use stdlib ElementTree)
- Any HTTP library except aiohttp via HA's session
- Additional JSON parsers (use stdlib json)

**Home Assistant 2026.x Built-ins:**
- aiohttp 3.13.3+
- voluptuous (config validation)
- orjson (JSON - faster but stdlib json acceptable)

---

## the agent's Discretion

**None** - All major decisions were user-specified via "use HASS best practices"

---

## Deferred Ideas

**None** - Discussion stayed within Phase 1 scope

---

*Discussion logged: 2026-04-11*
