# Phase 3: Configuration & Error Handling - Technical Research
**Researched:** 2026-04-12
**Status:** Ready for planning

---

## Research Scope

Investigate Home Assistant patterns for:
1. OptionsFlow implementation for post-setup configuration
2. DataUpdateCoordinator retry and error handling
3. Single config entry enforcement
4. Error handling in config flow and coordinators

---

## 1. OptionsFlow Implementation

### Pattern Overview
OptionsFlow allows users to reconfigure integration settings after initial setup via the "Configure" button on the integration card.

### Key Components

**Flow Registration:**
```python
@config_entries.HANDLERS.register(DOMAIN)
class OntarioEnergyPricingConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle initial config and options."""
    
    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return OntarioEnergyPricingOptionsFlow(config_entry)
```

**OptionsFlow Class:**
```python
class OntarioEnergyPricingOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow."""
    
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry
        self.options = dict(config_entry.options)
        
    async def async_step_init(self, user_input=None):
        """Manage options."""
        if user_input is not None:
            # Update options and reload entry
            return self.async_create_entry(title="", data=user_input)
            
        # Build schema with current values
        schema = vol.Schema({
            vol.Required("admin_fee", 
                default=self.config_entry.data.get("admin_fee", 0.0)
            ): vol.Coerce(float),
        })
        
        return self.async_show_form(
            step_id="init",
            data_schema=schema
        )
```

**Important Notes:**
- Options are stored separately from `config_entry.data` in `config_entry.options`
- Changing options triggers `async_reload` of the entry
- Entry reinitialization calls `async_unload_entry` then `async_setup_entry`
- Coordinator receives new config data on reload

**Data Structure:**
```python
# config_entry.data (immutable after creation)
{
    "api_key": "gs_...",
    "location": "Oakville, ON",
    "zone": "OAKVILLE",
    "zone_from_lookup": True
}

# config_entry.options (mutable via OptionsFlow)
{
    "admin_fee": 0.02
}
```

**Source:** Home Assistant Core examples, https://developers.home-assistant.io/docs/config_entries_config_flow_handler/

---

## 2. DataUpdateCoordinator Retry Strategy

### Coordinator Behavior
DataUpdateCoordinator handles automatic retries with exponential backoff.

**Retry Configuration:**
```python
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

coordinator = DataUpdateCoordinator(
    hass,
    LOGGER,
    name="lmp_current",
    update_method=self._async_update_data,
    update_interval=timedelta(hours=1),
    request_refresh_debouncer=None,  # Disable debouncing for testing
)
```

**Request Deboundcer (built-in retry):**
The coordinator has a debouncer that will:
- Queue refresh requests
- Wait ~10 seconds between attempts
- Retry on failure automatically

**Custom Retry Pattern:**
```python
async def _async_update_data(self):
    """Fetch data with exponential backoff."""
    errors = 0
    max_retries = 3
    base_delay = 5  # seconds
    
    while errors < max_retries:
        try:
            return await self.api.get_data()
        except GridStatusAuthError as err:
            # Auth errors - don't retry
            raise UpdateFailed(f"Authentication failed: {err}") from err
        except GridStatusAPIError as err:
            # API errors - retry with backoff
            errors += 1
            if errors >= max_retries:
                raise UpdateFailed(f"API error after {max_retries} retries: {err}") from err
            delay = base_delay * (3 ** (errors - 1))  # 5s, 15s, 45s
            LOGGER.debug("Retry %d/%d in %ds", errors, max_retries, delay)
            await asyncio.sleep(delay)
```

**Retry Without Sleep (coordinator handles it):**
```python
async def _async_update_data(self):
    """Just raise UpdateFailed - coordinator retries."""
    try:
        return await self.api.get_data()
    except GridStatusAuthError as err:
        raise UpdateFailed(f"Auth failed: {err}") from err
    except Exception as err:
        # Coordinator will retry with debouncer
        raise UpdateFailed(f"Fetch failed: {err}") from err
```

**Decision:** Use coordinator's built-in retry (via debouncer) with exponential backoff. No custom sleep needed.

---

## 3. Single Config Entry Enforcement

### Pattern: Abort Flow
```python
@config_entries.HANDLERS.register(DOMAIN)
class OntarioEnergyPricingConfigFlow(ConfigFlow, domain=DOMAIN):
    """Config flow for single entry."""

    async def async_step_user(self, user_input=None):
        """Handle user step."""
        # Check if already configured
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        
        # Or manual check:
        if self._async_current_entries():
            existing = self._async_current_entries()[0]
            return self.async_abort(
                reason="already_configured",
                description_placeholders={
                    "location": existing.data.get("location", "Unknown"),
                    "zone": existing.data.get("zone", "Unknown")
                }
            )
        # ... continue config flow
```

**Method Options:**

| Method | When to Use |
|--------|-------------|
| `self._abort_if_unique_id_configured()` | Simple case - just block |
| `self._async_current_entries()` | Need context to show user |
| `self._async_current_entry()` | Only one entry allowed |

**Translation Strings:**
```json
{
  "config": {
    "abort": {
      "already_configured": "Ontario Energy Pricing is already configured for {location} ({zone}). Remove the existing configuration to add a new one."
    }
  }
}
```

**Recommended:** `self._async_current_entries()` to fetch existing config for context message.

---

## 4. Error Handling in Config Flow

### Validation Patterns

**HTTP Error Mapping:**
```python
async def async_step_api_test(self, user_input=None):
    """Test API connection."""
    errors = {}
    
    try:
        await client.async_get_data()
    except GridStatusAuthError:
        errors["base"] = "invalid_auth"
    except GridStatusConnectionError:
        errors["base"] = "cannot_connect"
    except Exception:  # pylint: disable=broad-except
        errors["base"] = "unknown"
    else:
        return self.async_create_entry(...)
        
    return self.async_show_form(
        step_id="api_test",
        errors=errors
    )
```

**Error Types:**

| Error | UI Key | Translation Key |
|-------|--------|-----------------|
| 401 Unauthorized | `errors["base"] = "invalid_auth"` | `config.error.invalid_auth` |
| 403 Forbidden | `errors["base"] = "invalid_auth"` | `config.error.invalid_auth` |
| Connection refused | `errors["base"] = "cannot_connect"` | `config.error.cannot_connect` |
| Timeout | `errors["base"] = "cannot_connect"` | `config.error.cannot_connect` |
| Other | `errors["base"] = "unknown"` | `config.error.unknown` |

---

## 5. Global Adjustment State Retention

### Stateful Coordinator Pattern
For data that should persist across update failures:

```python