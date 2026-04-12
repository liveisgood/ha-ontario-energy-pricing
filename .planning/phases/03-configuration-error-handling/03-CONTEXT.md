# Phase 3: Configuration & Error Handling - Context
**Gathered:** 2026-04-12
**Status:** Ready for planning

---

## Phase Boundary
Implement robust config management and comprehensive error handling for the Ontario Energy Pricing integration. This phase ensures the integration survives restarts, handles edge cases gracefully, and provides clear feedback to users on configuration and runtime issues.

**Scope:**
- Options flow for reconfiguring admin_fee and zone
- Single config entry enforcement
- Config entry persistence verification
- Comprehensive error handling (ERR-01 to ERR-04)
- Coordinator retry strategies
- Recovery mechanisms

---

## Implementation Decisions

### D-01: Options Flow Design
**Decision:** Implement OptionsFlow for post-setup configuration changes

**Editable Fields:**
- `admin_fee` - Allow users to adjust their retailer admin fee anytime
- `zone` - Allow users to change location zone if they move or want different coverage

**Read-Only Fields:**
- `api_key` - Requires full re-setup for security/privacy reasons
- `location` - Tied to zone selection; zone change covers location updates

**UI Flow:**
- HA's "Configure" button on integration card
- Single form with current values pre-filled
- Zone dropdown populated from cached available_zones (or re-fetch if needed)
- Validation: admin_fee must be non-negative float

**Why:** Standard HA pattern; users expect to adjust fees without re-entering API key.

### D-02: Single Config Entry Enforcement
**Decision:** Block second config entry with context

**Behavior:**
- Check `hass.config_entries.async_entries(DOMAIN)` in `async_step_user`
- If entries exist: show abort with `user-friendly message + existing location/zone`
- Do not proceed to config form if already configured

**Abort Message:**
"Ontario Energy Pricing is already configured for {location} ({zone}). Remove the existing configuration to add a new one."

**Why:** Integration manages one location per HA instance; multiple entries would create duplicate sensors.

### D-03: Coordinator Retry Strategy (ERR-02)
**Decision:** Exponential backoff for LMP fetch failures

**Pattern:**
```python
# DataUpdateCoordinator handles retries automatically
# update_interval is 1 hour (3600s)
# On failure: retry at 5s, 15s, 45s (exponential)
# After 3 failures: sensor becomes unavailable
# On next poll: attempt fresh fetch
```

**GridStatus Specific:**
- Retry on: `GridStatusConnectionError`, `TimeoutError`, `aiohttp.ClientError`
- Fail fast on: `GridStatusAuthError` (401/403 - key is bad, no retry helps)

**Why:** Transient network/API hiccups resolve quickly; exponential avoids hammering API.

### D-04: GA XML Parse Error Handling (ERR-03)
**Decision:** Retain previous value for 1 week, then mark unavailable

**Pattern:**
```python
# GlobalAdjustmentCoordinator tracks:
- self._last_valid_rate: float | None
- self._last_valid_date: datetime | None

# On parse error:
- Log error
- Return last_valid_rate (coordinator keeps it)
- Sensor shows last known value

# Check staleness:
- If now - last_valid_date > 7 days:
  - Set self._last_valid_rate = None
  - Coordinator raises UpdateFailed
  - Sensor becomes unavailable
```

**Why:** IESO XML is monthly; 1 week tolerance allows for IESO publication delays without stale data.

### D-05: Network Unavailable Handling (ERR-04)
**Decision:** Standard HA behavior - wait for next scheduled poll

**Pattern:**
- Coordinator raises ` UpdateFailed` on network error
- HA marks entities unavailable
- No special recovery detection
- Next scheduled poll (hourly for LMP) attempts fresh connection

**Why:** HA's built-in behavior is sufficient; simpler code, less complexity, reliable.

### D-06: Config Entry Persistence Verification
**Decision:** Verify config survives restart

**Verification Method:**
- Config stored in `.storage/core.config_entries` (HA handles this)
- Integration reloads on HA restart via `async_setup_entry`
- `async_unload_entry` saves state properly
- `async_reload_entry` handles reconfiguration

**Test:** Restart HA after setup, verify sensors appear with correct values.

### D-07: API Key Validation (ERR-01)
**Decision:** Validate during config flow with test endpoint

**Already Implemented in Phase 2:**
- `async_step_api_test` validates key with GridStatus API
- Shows "invalid_auth" error if 401/403 returned
- Prevents saving invalid config

**This Phase:** Ensure error messages are user-friendly with actionable guidance.

---

## Canonical References

### Home Assistant Development
- `https://developers.home-assistant.io/docs/config_entries_options_flow_handler/` - Options flow implementation
- `https://developers.home-assistant.io/docs/integration_fetching_data/` - Coordinator retry patterns
- `https://developers.home-assistant.io/docs/integration_setup_error_handling/` - Error handling best practices

### Phase 2 Code (to extend)
- `custom_components/ontario_energy_pricing/config_flow.py` - Config flow base
- `custom_components/ontario_energy_pricing/coordinator.py` - Coordinators to enhance
- `custom_components/ontario_energy_pricing/const.py` - Constants for new features

### Error Handling Requirements
- ERR-01: API key invalid validation in config flow
- ERR-02: LMP fetch failure with retry
- ERR-03: GA XML parse error with 1-week retention
- ERR-04: Network unavailable with poll recovery

---

## Existing Code Insights

### Reusable Assets
- `OntarioEnergyPricingConfigFlow` class - Extend with `async_step_init` for OptionsFlow
- `LMPCoordinator` - Already raises UpdateFailed, configure retry behavior
- `GlobalAdjustmentCoordinator` - Add `_last_valid_rate` tracking
- `const.py` - Add CONF_ZONE to editable options

### Established Patterns
- Three-step config flow - Follow same pattern for options flow
- `from __future__ import annotations` - Continue strict typing
- `LOGGER = logging.getLogger(__name__)` - Use for error logging

### Integration Points
- `hass.config_entries` - Access existing entries for single-entry check
- `config_entries.OptionsFlow` - Base class for options flow
- `coordinator.DataUpdateCoordinator` - Configure retry intervals

---

## Specific Ideas
- Options flow should show current zone name, not just zone code
- Consider caching available_zones in hass.data to avoid re-fetching
- Single config entry check should happen before any form shows (abort early)
- GA retention: store last_valid_date in coordinator, not just value
- Add debug logging for retry attempts in coordinators

---

## Deferred Ideas
- **Config migration** - If we change data structure in v2, add migration in `async_migrate_entry`
- **Re-authentication flow** - If API key expires (not applicable to GridStatus), implement reauth
- **Service calls for manual refresh** - `sensor.refresh` service (HA handles this automatically, not needed)

---

*Phase: 03-configuration-error-handling*
*Context gathered: 2026-04-12*
*HA Target: 2026.4.x*
