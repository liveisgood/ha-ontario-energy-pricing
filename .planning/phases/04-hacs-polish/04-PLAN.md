# Phase 4: HACS & Polish - Plan 01

---
frontmatter:
  wave: 1
  depends_on: ["03-configuration-error-handling"]
  files_modified:
    - hacs.json
    - README.md
    - custom_components/ontario_energy_pricing/services.yaml
    - custom_components/ontario_energy_pricing/manifest.json
    - custom_components/ontario_energy_pricing/sensor.py
    - custom_components/ontario_energy_pricing/__init__.py
  autonomous: true
  requirements_addressed: ["HACS-01", "HACS-02", "HACS-03", "HACS-04"]
---

## Objective
Package the Ontario Energy Pricing integration for HACS custom repository installation by creating required metadata files, comprehensive documentation, and service definition.

---

## Task 1: Create hacs.json

<read_first>
- https://hacs.xyz/docs/publish/integration/ (HACS requirements)
- custom_components/ontario_energy_pricing/manifest.json (for iot_class, version)
- .planning/phases/04-hacs-polish/04-RESEARCH.md (hacs.json format)
</read_first>

<action>
Create hacs.json at repository root:

1. Create file hacs.json with:
   ```json
   {
     "name": "Ontario Energy Pricing",
     "content_in_root": false,
     "homeassistant": "2024.1.0",
     "render_readme": true,
     "iot_class": "cloud_polling",
     "country": ["CA"]
   }
   ```

2. Verify hacs.json is valid JSON

3. File location: repository root (same level as custom_components/)
</action>

<acceptance_criteria>
- hacs.json exists at repository root
- Contains required fields: "name", "homeassistant"
- Contains recommended fields: "content_in_root", "render_readme", "iot_class"
- Valid JSON (no syntax errors)
</acceptance_criteria>

---

## Task 2: Create Comprehensive README.md

<read_first>
- custom_components/ontario_energy_pricing/manifest.json (integration info)
- custom_components/ontario_energy_pricing/const.py (sensor IDs)
- .planning/phases/04-hacs-polish/04-CONTEXT.md (D-01 README sections)
- .planning/phases/04-hacs-polish/04-RESEARCH.md (README template)
</read_first>

<action>
Create README.md at repository root with the following sections:

1. **Header**:
   ```markdown
   # Ontario Energy Pricing
   [![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz/)
   [![ha_version](https://img.shields.io/badge/Home%20Assistant-2024.1%2B-blue.svg)](https://www.home-assistant.io/)

   Track real-time Ontario electricity rates in Home Assistant.
   ```

2. **Features** paragraph:
   - Current LMP (Locational Marginal Price) from GridStatus.io
   - 24-hour average LMP
   - Global Adjustment rate from IESO
   - Total Rate calculation (LMP + GA + Admin Fee)
   - Automatic zone discovery based on location

3. **Installation section**:
   - HACS: Add custom repository → Install → Restart
   - Manual: Copy custom_components/ → Restart

4. **Configuration section**:
   - Settings → Devices & Services → Add Integration
   - Enter GridStatus API key
   - Enter location (e.g., "Oakville, ON")
   - Select zone (or ONTARIO for province-wide)
   - Enter admin fee ($/kWh)

5. **Sensors table**:
   | Entity | Description | Unit | Update |
   |--------|-------------|------|--------|
   | sensor.ontario_energy_pricing_current_lmp | Current LMP | CAD/kWh | Hourly |
   | sensor.ontario_energy_pricing_lmp_24h_average | 24h Average | CAD/kWh | Daily |
   | sensor.ontario_energy_pricing_global_adjustment | Global Adj | CAD/kWh | Monthly |
   | sensor.ontario_energy_pricing_total_rate | Total Rate | CAD/kWh | Hourly |

6. **Pricing Formula**:
   ```
   Total Rate = Current LMP + Global Adjustment + Admin Fee
   ```

7. **Automation Examples** (2 YAML examples):
   - High rate alert (> $0.15/kWh)
   - Run device when rate is low (< $0.06/kWh)

8. **Troubleshooting**:
   - "Sensor unavailable": Check API key, verify zone selection
   - "No data": Check GridStatus API status, verify IESO XML availability

9. **Credits**:
   - Data from [GridStatus.io](https://gridstatus.io)
   - Global Adjustment from [IESO](https://ieso.ca)

10. **Links**:
    - [HACS](https://hacs.xyz/)
    - [GridStatus API](https://gridstatus.io)
</action>

<acceptance_criteria>
- README.md exists at repository root
- Contains header with badges (HACS, HA version)
- Contains Installation section with HACS and Manual steps
- Contains Configuration section with step-by-step guide
- Contains Sensors table with all 4 sensors
- Contains Pricing Formula
- Contains at least 2 Automation Examples with YAML code blocks
- Contains Troubleshooting section
- Markdown is valid (headers, tables, code blocks formatted correctly)
</acceptance_criteria>

---

## Task 3: Create services.yaml

<read_first>
- custom_components/ontario_energy_pricing/__init__.py (will register service)
- .planning/phases/04-hacs-polish/04-RESEARCH.md (services.yaml format)
- https://developers.home-assistant.io/docs/dev_101_services/ (reference)
</read_first>

<action>
Create services.yaml at custom_components/ontario_energy_pricing/services.yaml:

1. Create file content:
   ```yaml
   refresh:
     name: Refresh
     description: Manually refresh all sensor data from APIs
     fields: {}
   ```

2. File location: custom_components/ontario_energy_pricing/services.yaml

Note: HA auto-loads this file on startup. No explicit import needed.
</action>

<acceptance_criteria>
- services.yaml exists at custom_components/ontario_energy_pricing/services.yaml
- Contains refresh service definition
- Service has name, description, and empty fields
- File is valid YAML
</acceptance_criteria>

---

## Task 4: Register Refresh Service in __init__.py

<read_first>
- custom_components/ontario_energy_pricing/__init__.py (current lifecycle handlers)
- custom_components/ontario_energy_pricing/const.py (DOMAIN constant)
- .planning/phases/04-hacs-polish/04-RESEARCH.md (service registration pattern)
</read_first>

<action>
Add service registration and unregistration to __init__.py:

1. Import UpdateFailed at top:
   ```python
   from homeassistant.exceptions import HomeAssistantError
   ```

2. In async_setup_entry, after sensor platform setup:
   ```python
   # Register refresh service
   async def handle_refresh_service(call):
       """Handle refresh service call."""
       coordinators = hass.data[DOMAIN][entry.entry_id].get("coordinators", [])
       for coordinator in coordinators:
           await coordinator.async_refresh()
   
   hass.services.async_register(
       DOMAIN,
       "refresh",
       handle_refresh_service,
   )
   
   # Store service handle for cleanup
   hass.data[DOMAIN][entry.entry_id]["service_handle"] = handle_refresh_service
   ```

3. In async_unload_entry:
   ```python
   # Remove refresh service
   hass.services.async_remove(DOMAIN, "refresh")
   ```

Note: Requires coordinators to be stored in hass.data for access.
</action>

<acceptance_criteria>
- async_setup_entry registers service using hass.services.async_register
- Service name is "refresh" in DOMAIN namespace
- Service handler calls async_refresh on all coordinators
- async_unload_entry removes service using hass.services.async_remove
- Service is accessible in Developer Tools → Services
</acceptance_criteria>

---

## Task 5: Add Entity Icons to Sensors

<read_first>
- custom_components/ontario_energy_pricing/sensor.py (current sensor entities)
- .planning/phases/04-hacs-polish/04-RESEARCH.md (icon patterns)
- https://pictogrammers.com/library/mdi/ (icon reference)
</read_first>

<action>
Add icon property to each sensor class in sensor.py:

1. In LMPCurrentPriceSensor class, add:
   ```python
   @property
   def icon(self) -> str | None:
       """Return the icon."""
       return "mdi:lightning-bolt"
   ```

2. In LMP24hAverageSensor class, add:
   ```python
   @property   def icon(self) -> str | None:
       """Return the icon."""
       return "mdi:chart-line"
   ```

3. In GlobalAdjustmentSensor class, add:
   ```python
   @property
   def icon(self) -> str | None:
       """Return the icon."""
       return "mdi:cash"
   ```

4. In TotalRateSensor class, add:
   ```python
   @property
   def icon(self) -> str | None:
       """Return the icon."""
       return "mdi:scale-balance"
   ```

Note: Using entity property (modern HA pattern) vs manifest.json icons.
</action>

<acceptance_criteria>
- All 4 sensor classes have icon() property returning MDI icon strings
- Current LMP: mdi:lightning-bolt
- 24h Average: mdi:chart-line
- Global Adjustment: mdi:cash
- Total Rate: mdi:scale-balance
- Icons appear in entity registry and dashboard entities
</acceptance_criteria>

---

## Task 6: Update manifest.json with Additional Metadata

<read_first>
- custom_components/ontario_energy_pricing/manifest.json (current)
- https://developers.home-assistant.io/docs/creating_integration_manifest/
</read_first>

<action>
Update manifest.json with best-practice fields:

1. Ensure current manifest.json has:
   ```json
   {
     "domain": "ontario_energy_pricing",
     "name": "Ontario Energy Pricing",
     "codeowners": [],
     "config_flow": true,
     "dependencies": [],
     "documentation": "https://github.com/lobstah/ha-ontario-energy-pricing",
     "iot_class": "cloud_polling",
     "requirements": [
       "aiohttp>=3.9.0",
       "voluptuous>=0.13.0"
     ],
     "version": "1.0.0"
   }
   ```

2. Verify fields:
   - version: "1.0.0" (for release)
   - iot_class: "cloud_polling" (correct)
   - config_flow: true (already set)

3. If missing, add documentation URL pointing to repo

Note: manifest.json was already created in Phase 2. This is verification/updates only.
</action>

<acceptance_criteria>
- manifest.json exists at custom_components/ontario_energy_pricing/manifest.json
- Contains "name": "Ontario Energy Pricing"
- Contains "domain": "ontario_energy_pricing"
- Contains "config_flow": true
- Contains "iot_class": "cloud_polling"
- Contains valid semver "version" (e.g., "1.0.0")
- Contains "requirements" with aiohttp and voluptuous
- Valid JSON syntax
</acceptance_criteria>

---

## Verification Criteria

After executing all tasks:

1. **HACS Metadata**
   - hacs.json at repo root with name, homeassistant, iot_class
   - Valid JSON structure
   - render_readme: true enabled

2. **Documentation**
   - README.md with badges, installation, configuration, sensors table
   - Automation examples with YAML
   - Troubleshooting section
   - Original sensors documented accurately

3. **Service**
   - services.yaml exists and valid
   - Service registered in __init__.py
   - Service unregistered in async_unload_entry
   - "ontario_energy_pricing.refresh" appears in Developer Tools

4. **Icons**
   - All 4 sensors have icon property
   - Icons match: lightning-bolt, chart-line, cash, scale-balance
   - Icons display in entity registry

5. **Manifest**
   - Version set to "1.0.0"
   - All required fields present
   - Valid JSON

6. **Integration Test**
   - Files can be copied/installed via HACS
   - No import errors on startup
   - Service callable via Developer Tools

---

## must_haves (Goal-Backward Verification)

The following capabilities MUST be present to consider Phase 4 complete:

- [ ] hacs.json at repo root enables HACS custom repository
- [ ] Comprehensive README.md with installation instructions
- [ ] services.yaml defines refresh service
- [ ] Service registered and callable in Developer Tools
- [ ] All 4 sensors have custom icons (MDI)
- [ ] manifest.json has correct version (1.0.0)
- [ ] Badges in README for HACS and HA version
- [ ] Automation examples in README
- [ ] Pricing formula documented
- [ ] Troubleshooting section covers common issues

---

*Plan: 04-PLAN.md*
*Target Phase: 04-hacs-polish*
*Requirements: HACS-01, HACS-02, HACS-03, HACS-04*
*Technical: https://hacs.xyz/docs/publish/integration/*
