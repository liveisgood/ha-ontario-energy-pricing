# Phase 2: Core Entities - Context

**Gathered:** 2026-04-11
**Status:** Ready for planning
**Home Assistant Version Target:** 2026.4.x

---

## Phase Boundary

Implement data coordinators, sensor entities, and config flow for the Ontario Energy Pricing integration. This phase builds on the Phase 1 data layer to expose sensors in Home Assistant and provide a configuration UI.

**Scope:**
- Three DataUpdateCoordinators (hourly LMP, daily 24h average, weekly GA)
- Four SensorEntities with proper device classes
- ConfigFlow for user setup with zone discovery
- Entity ID mapping and translation keys

----

## Implementation Decisions

### D-01: Coordinator Architecture
**Decision:** Three separate coordinators with different update intervals

**Pattern:**
- `LMPCoordinator` - Hourly updates, `update_interval=timedelta(hours=1)`
- `LMP24hAverageCoordinator` - Daily at midnight using `async_track_time_change`
- `GlobalAdjustmentCoordinator` - Weekly checks, only updates when trade_month changes

**Rationale:**
- Each data source has different update frequency
- Matches HA's DataUpdateCoordinator pattern
- Easier to debug and test independently
- Respects API update schedules

### D-02: Config Flow Design
**Decision:** Three-step config flow with validation

**Steps:**
1. **User Data** - API key, admin fee, location text input
2. **API Validation** - Test GridStatus auth, discover zones
3. **Zone Selection** - Present discovered zones, user selects or use ONTARIO fallback

**Why:**
- Validates credentials before saving
- Shows available zones to user
- Stores zone in config (no re-querying)
- Friendly error messages on validation failure

### D-03: Sensor Implementation
**Decision:** Extend `CoordinatorEntity` mixin for all sensors

**Four Sensors:**
| Sensor | Device Class | Unit | State Class |
|--------|--------------|------|-------------|
| `current_lmp` | MONETARY | CAD/kWh | MEASUREMENT |
| `lmp_24h` | MONETARY | CAD/kWh | MEASUREMENT |
| `global_adjustment` | MONETARY | CAD/kWh | MEASUREMENT |
| `total_rate` | MONETARY | CAD/kWh | MEASUREMENT |

**Attributes:**
- `current_lmp`: `timestamp`, `previous_rate`, `zone`
- `lmp_24h`: `timestamp` (aggregation date)
- `global_adjustment`: `trade_month`
- `total_rate`: `lmp_rate`, `ga_rate`, `admin_fee` (components)

### D-04: Update Scheduling
**Decision:** Coordinator-level scheduling using HA helpers

**Pattern:**
```python
# Hourly LMP - update_interval
data_update_coordinator.DataUpdateCoordinator(
    update_interval=timedelta(hours=1)
)

# Daily 24h average - track midnight
async_track_time_pattern(hass, coordinator.async_refresh, hour=0, minute=0)

# Weekly GA check - asyncio.sleep + compare trade_month
```

**Why:**
- Efficient (no redundant polling)
- Exact timing for requirements
- User sees accurate `last_updated`
- Follows HA patterns

### D-05: Zone Discovery
**Decision:** API query during config, store result

**Flow:**
1. User enters location string
2. Query GridStatus for available zones
3. Fuzzy match location against zone names
4. Present best match(es) to user
5. Store selected zone in config entry

**Why:**
- No hardcoded zone mappings
- Self-documenting
- Handles IESO nodal zone changes
- User can override

### D-06: Config Entry Structure
**Decision:** Dict-based config entry

**Keys:**
- `api_key` - GridStatus API key
- `admin_fee` - Fixed admin fee ($/kWh)
- `location` - User's location string
- `zone` - Selected IESO zone
- `zone_from_lookup` - Boolean (discovery vs manual)

**Why:**
- HA standard pattern
- Easy to migrate
- Clear semantics

### D-07: Error Handling in Coordinators
**Decision:** Raise `UpdateFailed`, let sensor become unavailable

**Pattern:**
```python
async def _async_update_data(self):
    try:
        return await self.api.get_data()
    except GridStatusAuthError as err:
        raise UpdateFailed(f"Authentication failed: {err}") from err
    except GridStatusAPIError as err:
        raise UpdateFailed(f"API error: {err}") from err
```

**Why:**
- HA handles unavailable state automatically
- Coordinator retry logic handles transient failures
- Clear error messages in logs

### D-08: Translations and Entity IDs
**Decision:** Translation keys for friendly names

**Pattern:**
- Translation keys in `translations/en.json`
- Entity IDs: `sensor.{DOMAIN}_{sensor_name}`
- `has_entity_name=True` on sensor entities
- `translation_key` on entities

**Why:**
- HACS requirement
- User can rename if needed
- Proper HA internationalization

---

## Canonical References

### Home Assistant Development
- `https://developers.home-assistant.io/docs/integration_fetching_data/` - Coordinator patterns
- `https://developers.home-assistant.io/docs/config_entries_config_flow_handler/` - Config flow
- `https://developers.home-assistant.io/docs/core/entity/sensor/` - Sensor entities

### Phase 1 Code (consumed by this phase)
- `custom_components/ontario_energy_pricing/models.py` - Data models
- `custom_components/ontario_energy_pricing/gridstatus.py` - API client
- `custom_components/ontario_energy_pricing/ieso.py` - XML client
- `custom_components/ontario_energy_pricing/exceptions.py` - Error types

---

## Existing Code Insights

### Reusable Assets (from Phase 1)
- `GridStatusClient` - Injected in coordinator init
- `IESOGlobalAdjustmentClient` - Injected in GA coordinator
- Data models - Returned by coordinators
- Custom exceptions - Caught and wrapped

### Established Patterns
- `from __future__ import annotations`
- Full type annotations (mypy strict)
- Frozen dataclasses
- Injected `aiohttp.ClientSession`

### Integration Points
- `hass.config_entries.async_setup_entry` - Entry setup
- `hass.helpers.update_coordinator.DataUpdateCoordinator` - Base class
- `hass.components.sensor.SensorEntity` - Base sensor
- `hass.helpers.entity_platform.AddEntitiesCallback` - Platform setup

---

## Specific Ideas

- Auto-discover zone matching user's city name
- Allow user to manually enter zone if auto-match fails
- Show approximate cost per kWh in sensor name
- Include "last updated" in sensor attributes
- Validate API key during config flow with a test request
- Fallback to ONTARIO-wide if zone discovery fails

---

## Deferred Ideas

**None** - Phase 2 discussion stayed within scope.

Configuration validation (ERR-01 to ERR-04) and error handling refinement moved to Phase 3.

---

*Phase: 02-core-entities*
*Context gathered: 2026-04-11*
*HA Target: 2026.4.x*
