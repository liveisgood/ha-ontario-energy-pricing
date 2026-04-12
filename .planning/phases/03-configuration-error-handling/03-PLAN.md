# Phase 3: Configuration & Error Handling - Plan 01

---
frontmatter:
  wave: 1
  depends_on: ["02-core-entities"]
  files_modified:
    - custom_components/ontario_energy_pricing/config_flow.py
    - custom_components/ontario_energy_pricing/translations/en.json
    - custom_components/ontario_energy_pricing/const.py
    - custom_components/ontario_energy_pricing/coordinator.py
  autonomous: true
  requirements_addressed: ["CONF-03", "CONF-04", "ERR-01", "ERR-02", "ERR-03", "ERR-04"]
---

## Objective
Implement robust config management and comprehensive error handling, including OptionsFlow for post-setup configuration, single config entry enforcement, and proper error recovery mechanisms.

---

## Task 1: Create Options Flow Handler

<read_first>
- custom_components/ontario_energy_pricing/config_flow.py (current implementation)
- custom_components/ontario_energy_pricing/const.py (for CONF_ constants)
- custom_components/ontario_energy_pricing/translations/en.json (for UI strings)
- https://developers.home-assistant.io/docs/config_entries_options_flow_handler/ (reference)
</read_first>

<action>
Add OptionsFlow class and registration to config_flow.py:

1. Add `@staticmethod @callback async_get_options_flow` to `OntarioEnergyPricingConfigFlow` class that returns `OntarioEnergyPricingOptionsFlow(config_entry)`

2. Create new class `OntarioEnergyPricingOptionsFlow(config_entries.OptionsFlow)` after the ConfigFlow class with:
   - `__init__(self, config_entry)` that stores `self.config_entry = config_entry`
   - `async def async_step_init(self, user_input=None)` that:
     - If `user_input is not None`: return `self.async_create_entry(title="", data=user_input)`
     - Build `vol.Schema` with:
       - `vol.Required(CONF_ADMIN_FEE, default=self.config_entry.data.get(CONF_ADMIN_FEE, 0.0)): vol.Coerce(float)`
       - `vol.Required(CONF_ZONE, default=self.config_entry.data.get(CONF_ZONE, "ONTARIO")): str`
       - Note: CONF_ZONE should show dropdown with cached zone options or allow manual text entry
     - Return `self.async_show_form(step_id="init", data_schema=schema)`

3. In const.py, add `CONF_ZONE = "zone"` import if not present

4. Ensure `OntarioEnergyPricingOptionsFlow` class is exported from config_flow.py (no special export needed, HA uses async_get_options_flow)
</action>

<acceptance_criteria>
- config_flow.py contains `OntarioEnergyPricingOptionsFlow` class
- `OntarioEnergyPricingConfigFlow.async_get_options_flow` returns OptionsFlow instance
- `async_step_init` in OptionsFlow creates form with admin_fee and zone fields
- `vol.Schema` uses CONF_ADMIN_FEE and CONF_ZONE with correct defaults from config_entry.data
- Form submission calls `async_create_entry` with empty title and user_input data
</acceptance_criteria>

---

## Task 2: Update Translations for Options Flow

<read_first>
- custom_components/ontario_energy_pricing/translations/en.json (current translations)
</read_first>

<action>
Add translations for OptionsFlow UI in translations/en.json:

1. Under `"config"` section, ensure `"abort"` has entry:
   - `"already_configured": "Ontario Energy Pricing is already configured for {location} ({zone}). Remove the existing configuration to add a new one."`

2. Add new `"options"` section at root level with:
   ```json
   "options": {
     "step": {
       "init": {
         "title": "Configure Ontario Energy Pricing",
         "description": "Adjust your energy pricing settings",
         "data": {
           "admin_fee": "Admin Fee ($/kWh)",
           "zone": "Zone"
         }
       }
     }
   }
   ```
</action>

<acceptance_criteria>
- translations/en.json contains `"options"` section at root
- `"options.step.init"` has `title`, `description`, and `data` keys
- `"data.admin_fee"` translation exists
- `"data.zone"` translation exists
- `"config.abort.already_configured"` translation exists with `{location}` and `{zone}` placeholders
</acceptance_criteria>

---

## Task 3: Implement Single Config Entry Enforcement

<read_first>
- custom_components/ontario_energy_pricing/config_flow.py (async_step_user)
- custom_components/ontario_energy_pricing/const.py (DOMAIN constant)
</read_first>

<action>
Add single config entry enforcement to async_step_user in config_flow.py:

1. At start of `async_step_user`, before any processing:
   ```python
   # Check if already configured
   entries = self._async_current_entries()
   if entries:
       existing = entries[0]
       return self.async_abort(
           reason="already_configured",
           description_placeholders={
               "location": existing.data.get(CONF_LOCATION, "Unknown"),
               "zone": existing.data.get(CONF_ZONE, "Unknown")
           }
       )
   ```

2. Ensure `CONF_LOCATION` is imported from const.py

3. The following code should remain unchanged (API key entry, validation, zone selection)
</action>

<acceptance_criteria>
- `async_step_user` calls `self._async_current_entries()` at start
- If entries exist, returns `self.async_abort(reason="already_configured", ...)`
- `description_placeholders` includes `"location"` and `"zone"` from existing entry
- User cannot proceed to config form if entry already exists
</acceptance_criteria>

---

## Task 4: Configure Coordinator Retry Strategy

<read_first>
- custom_components/ontario_energy_pricing/coordinator.py (LMPCoordinator)
- custom_components/ontario_energy_pricing/exceptions.py (error types)
</read_first>

<action>
Update LMPCoordinator._async_update_data to implement proper error handling with retry:

1. In LMPCoordinator._async_update_data, structure error handling as:
   ```python
   try:
       return await self.client.get_current_lmp(self.zone)
   except GridStatusAuthError as err:
       # Auth errors - don't retry, mark unavailable immediately
       LOGGER.error("Authentication failed for LMP fetch: %s", err)
       raise UpdateFailed(f"Authentication failed: {err}") from err
   except (GridStatusConnectionError, GridStatusAPIError) as err:
       # Transient errors - coordinator will retry automatically
       LOGGER.warning("LMP fetch failed, will retry: %s", err)
       raise UpdateFailed(f"Failed to fetch LMP data: {err}") from err
   except Exception as err:
       # Unexpected errors - coordinator will retry
       LOGGER.exception("Unexpected error during LMP fetch: %s", err)
       raise UpdateFailed(f"Unexpected error: {err}") from err
   ```

2. Ensure LOGGER is configured with appropriate log level (DEBUG for retry attempts, WARNING for failures)

3. Update DataUpdateCoordinator initialization to set appropriate update_interval (already set to 1 hour in Phase 2)

Note: Home Assistant's DataUpdateCoordinator automatically retries failed updates with exponential backoff through its internal request debouncer. No custom sleep/retry logic needed.
</action>

<acceptance_criteria>
- LMPCoordinator._async_update_data has specific handling for GridStatusAuthError (fails fast)
- GridStatusConnectionError and GridStatusAPIError raise UpdateFailed (triggers coordinator retry)
- Generic Exception also raises UpdateFailed
- LOGGER.error used for auth failures, LOGGER.warning for transient failures
- No custom asyncio.sleep or retry loop in _async_update_data (rely on HA's built-in retry)
</acceptance_criteria>

---

## Task 5: Implement GA XML Parse Error Handling with State Retention

<read_first>
- custom_components/ontario_energy_pricing/coordinator.py (GlobalAdjustmentCoordinator)
- custom_components/ontario_energy_pricing/exceptions.py
</read_first>

<action>
Enhance GlobalAdjustmentCoordinator to retain previous values during parse errors:

1. Add instance variables in `__init__`:
   ```python
   self._last_valid_rate: float | None = None
   self._last_valid_date: datetime | None = None
   ```

2. Update GlobalAdjustmentCoordinator._async_update_data:
   ```python
   try:
       rate = await self.client.get_monthly_rate()
       self._last_valid_rate = rate
       self._last_valid_date = dt_util.utcnow()
       return rate
   except (IESOXMLParseError, IESOConnectionError) as err:
       # Parse/connection errors - check staleness
       LOGGER.warning("GA XML parse failed: %s", err)
       
       # Check if data is stale (> 7 days)
       if (self._last_valid_date is not None and 
           (dt_util.utcnow() - self._last_valid_date) > timedelta(days=7)):
           LOGGER.error("GA data is stale (> 7 days), marking unavailable")
           self._last_valid_rate = None
           self._last_valid_date = None
           raise UpdateFailed(f"GA data stale: {err}") from err
       
       # Return cached value
       LOGGER.debug("Returning cached GA rate: %s", self._last_valid_rate)
       return self._last_valid_rate
   except Exception as err:
       LOGGER.exception("Unexpected error during GA fetch: %s", err)
       raise UpdateFailed(f"Failed to fetch GA: {err}") from err
   ```

3. Import required modules:
   - `from homeassistant.util import dt as dt_util`
   - `from datetime import timedelta`
</action>

<acceptance_criteria>
- GlobalAdjustmentCoordinator.__init__ defines `self._last_valid_rate` and `self._last_valid_date`
- _async_update_data stores valid rate/date in instance variables on success
- On parse error, checks staleness: `(now - _last_valid_date) > timedelta(days=7)`
- If data is stale, sets `_last_valid_rate = None` and raises UpdateFailed
- If data is not stale, returns cached `_last_valid_rate`
</acceptance_criteria>

---

## Task 6: Verify Config Entry Persistence

<read_first>
- custom_components/ontario_energy_pricing/__init__.py (entry lifecycle)
</read_first>

<action>
Ensure config entry persistence across restarts:

1. In __init__.py async_setup_entry, verify entry.data contains all required fields
2. In __init__.py async_unload_entry, ensure proper cleanup
3. HA automatically handles persistence - no explicit code needed
4. For verification: Restart HA, sensors should appear with same configuration
</action>

<acceptance_criteria>
- async_setup_entry accepts ConfigEntry and uses entry.data for initialization
- async_unload_entry properly unloads platforms
- Entry creation stores all required fields
- No errors on HA restart after configuration
</acceptance_criteria>

---

## must_haves

The following capabilities MUST be present to consider Phase 3 complete:

- [ ] Users can reconfigure admin_fee via Configure button
- [ ] Users can reconfigure zone via Configure button
- [ ] Only one config entry allowed - duplicates blocked with context
- [ ] LMP coordinator handles transient errors with HA retry
- [ ] LMP coordinator fails fast on auth errors
- [ ] GA coordinator retains value during parse errors
- [ ] GA becomes unavailable after 7 days of parse failures
- [ ] All settings survive HA restart
- [ ] Error translations present in en.json
- [ ] Options translations present in en.json

---

*Plan: 03-PLAN.md*
*Target Phase: 03-configuration-error-handling*
