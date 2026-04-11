# Pitfalls Research: Ontario Energy Pricing HACS Integration

**Research Date:** 2025-04-11
**Researcher:** Claude Code

---

## 1. Data Source Pitfalls

### P1.1: HOEP Retirement Confusion

**Risk:** High  
**Phase:** Development  
**Issue:** User requested HOEP, but it was retired May 1, 2025

**Symptoms:**
- Finding `ieso_hoep_real_time_hourly` dataset retired
- Confusion about what data to use
- Possible mismatch with user's expectations

**Prevention:**
- Use `ieso_lmp_real_time_5_min_all` (LMP) instead
- Explain to user: LMP is the new HOEP (Ontario-wide zonal prices)
- Document the transition in README

**Detection:**
- GridStatus shows "Retired" status for HOEP dataset
- Documentation mentions Market Renewal

**Recovery:**
- Already using correct replacement dataset
- No action needed beyond documentation

---

### P1.2: Global Adjustment Parse Errors

**Risk:** Medium  
**Phase:** Development  
**Issue:** IESO XML structure changes or unexpected format

**Symptoms:**
- XML parsing errors
- Missing FirstEstimateRate element
- Encoding issues (UTF-8 BOM)

**Prevention:**
- Use defensive XML parsing (try/except)
- Validate element existence before access
- Log full XML on parse error for debugging

**Detection:**
- Coordinator update fails with ParseError
- Sensor becomes unavailable

**Recovery:**
- Keep previous value on parse failure
- Mark sensor as unavailable vs unknown
- Retry on next update cycle

---

### P1.3: LMP Zone Filtering

**Risk:** Medium  
**Phase:** Development  
**Issue:** Need to filter LMP data for correct zone

**Symptoms:**
- Getting multiple prices (node-level data)
- Unclear which represents "Oakville"

**Prevention:**
- Filter for zone = "ONTARIO" or zone containing user's zone
- Inspect actual API responses during dev
- Allow zone override in config if needed

**Detection:**
- Price volatility (node-level prices vary significantly)
- Too many data points per interval

**Recovery:**
- Default to ONTARIO-wide average
- Add configuration option for zone selection

---

### P1.4: Timezone Handling

**Risk:** High  
**Phase:** Development  
**Issue:** Multiple timezone conversions (UTC, Eastern, Local)

**Symptoms:**
- Wrong hour displayed
- Prices not updating at expected times
- "Current" hour not actually current

**Prevention:**
- Always use timezone-aware datetime
- Query GridStatus with US/Eastern
- Store timestamps as ISO8601 with TZ info
- Use HA's dt_util.now() for local time comparisons

**Detection:**
- Sensor timestamp shows +5 hour offset
- Price not updating at top of hour

**Recovery:**
- Verify all datetime imports use proper TZ handling
- Log entry/exit points with TZ info for debugging

---

## 2. Home Assistant Pitfalls

### P2.1: Async Pattern Violations

**Risk:** High  
**Phase:** Development  
**Issue:** Blocking calls in async code

**Symptoms:**
- Home Assistant event loop blocked
- Warnings in logs about blocking I/O
- Integration marked as slow

**Prevention:**
- Always use `aiohttp` for HTTP (not requests)
- Use `asyncio` versions of I/O operations
- Mark XML parsing as executor job if synchronous

**Code Review:**
```python
# BAD - blocks event loop
async def update(self):
    import requests
    requests.get(url)  # BLOCKING
    
# GOOD - async
async def update(self):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            # non-blocking
```

**Detection:**
- HA logs warnings about blocking calls
- Timeout errors in other integrations

**Recovery:**
- Move blocking code to executor: `await hass.async_add_executor_job(func)`

---

### P2.2: Coordinator Update Failures

**Risk:** High  
**Phase:** All phases  
**Issue:** API unavailable or rate limited

**Symptoms:**
- All sensors become unavailable
- No retries despite temporary failure
- User confusion about why sensors are down

**Prevention:**
- Use HA's DataUpdateCoordinator (handles retries automatically)
- Set `update_interval` appropriately
- Implement exponential backoff for API failures
- Log errors at appropriate levels

**Detection:**
- Coordinator shows failed updates in logs
- Sensors show "unavailable" state longer than expected

**Recovery:**
- Coordinator already handles this, but verify:
- `UpdateFailed` exception raised (not generic Exception)
- Coordinator uses default retry logic

---

### P2.3: Config Flow Validation Failures

**Risk:** Medium  
**Phase:** User onboarding  
**Issue:** API key appears valid but later fails

**Symptoms:**
- Config flow succeeds during setup
- Sensors never get data
- Silent failures after setup

**Prevention:**
- Actually call GridStatus during config flow to validate key
- Test with a small data window (not full query)
- Handle rate limit responses (429 status)

**Code Example:**
```python
async def async_step_user(self, user_input):
    # Validate API key before creating entry
    try:
        await validate_api_key(user_input[CONF_API_KEY])
    except InvalidAuth:
        return self.async_show_form(errors={"base": "invalid_auth"})
    except CannotConnect:
        return self.async_show_form(errors={"base": "cannot_connect"})
    
    return self.async_create_entry(...)
```

**Detection:**
- Sensors show "Unknown" not "Unavailable"
- No data ever despite "success" in config

**Recovery:**
- Clear config entry, re-add
- Better: implement reconfig flow (v2 feature)

---

### P2.4: Entity Naming Convention

**Risk:** Low  
**Phase:** Development  
**Issue:** Sensor entity IDs don't follow HA conventions

**Symptoms:**
- Entity IDs like `sensor.ontario_lmp`
- User can't tell which sensor is which
- Translations missing

**Prevention:**
- Follow HA naming patterns: `domain_sensor_name`
- Use `has_translation` in manifest
- Provide proper `translation_key`

**Recommended IDs:**
```python
ontario_lmp_price -> sensor.ontario_energy_pricing_lmp_price
ontario_global_adjustment -> sensor.ontario_energy_pricing_global_adjustment
ontario_admin_fee -> sensor.ontario_energy_pricing_admin_fee
```

**Detection:**
- Code review
- HA developer tools entity registry

---

## 3. HACS Pitfalls

### P3.1: Repository Structure

**Risk:** Medium  
**Phase:** Publishing  
**Issue:** HACS doesn't recognize the integration

**Symptoms:**
- HACS shows "Not loaded" in UI
- No errors but integration not available
- Can't install via HACS

**Prevention:**
- Follow HACS structure exactly:
  ```
  repo-root/
  ├── custom_components/
  │   └── ontario_energy_pricing/
  │       ├── manifest.json (must exist)
  │       └── __init__.py
  ├── hacs.json
  └── README.md
  ```
- hacs.json must be valid JSON

**Detection:**
- HACS validation fails
- Custom repository adds but doesn't show integration

**Recovery:**
- Check manifest.json version present
- Verify file paths are correct
- Check hacs.json syntax

---

### P3.2: Version Management

**Risk:** Low  
**Phase:** Maintenance  
**Issue:** HACS shows update available when there isn't

**Symptoms:**
- Constant update notifications
- Version mismatch between manifest and git tags

**Prevention:**
- Use proper semantic versioning in manifest.json
- Tag releases matching manifest version
- Keep versions in sync

**Recovery:**
- Update manifest.json version
- Create git tag matching version

---

## 4. Testing Pitfalls

### P4.1: No Network Access in Tests

**Risk:** Medium  
**Phase:** Development  
**Issue:** pytest-homeassistant-custom-component environment has no internet

**Symptoms:**
- Tests fail with timeout
- Can't test actual API calls

**Prevention:**
- Mock GridStatus API responses
- Mock IESO XML responses
- Test with fixture files

**Code Example:**
```python
@pytest.fixture
def