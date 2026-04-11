# Phase 2: Core Entities - Plan 02

**Plan:** 02 - Coordinators, Sensors, and Config Flow
**Wave:** 1
**Type:** Infrastructure
**Created:** 2026-04-11
**Phase:** 02-core-entities

---

## Objective

Create data coordinators, sensor entities, and config flow for the Ontario Energy Pricing integration.

---

## Phase Requirements Addressed

- SENS-01 to SENS-06 - Four sensors with attributes
- CONF-01, CONF-02, CONF-05, CONF-06 - Config flow with zone discovery
- SCH-01 to SCH-04 - Scheduled updates
- LOC-01 to LOC-04 - Zone discovery and location handling

---

## Task 1: Update Component __init__.py

Update `__init__.py` for component setup.

<action>
1. Add `async_setup_entry(hass, entry)` function
2. Add `async_unload_entry(hass, entry)` function
3. Add `async_reload_entry(hass, entry)` function
</action>

<acceptance_criteria>
- `__init__.py` defines async_setup_entry, async_unload_entry, async_reload_entry
- Each function has type annotations
- `hass.data[DOMAIN][entry.entry_id]` populated
</acceptance_criteria>

---

## Task 2: Create Data Coordinators

Create `coordinator.py` with three DataUpdateCoordinators.

<action>
1. Create `OntarioEnergyPricingDataUpdateCoordinator` base class
2. Create `LMPCoordinator` - hourly updates, returns LMPCurrentPrice
3. Create `LMP24hAverageCoordinator` - daily updates, returns average
4. Create `GlobalAdjustmentCoordinator` - weekly updates, returns GlobalAdjustment
</action>

<acceptance_criteria>
- coordinator.py exists with four coordinator classes
- Each has proper update_interval
- async_update_data() returns correct model types
- Exceptions wrapped in UpdateFailed
</acceptance_criteria>

---

## Task 3: Create Sensor Entities

Create `sensor.py` with four sensors.

<action>
1. Create `async_setup_entry()` platform setup
2. Create `OntarioEnergyPricingSensor` base sensor class
3. Create four sensor classes with proper attributes
4. Link each sensor to respective coordinator
</action>

<acceptance_criteria>
- sensor.py exists with five sensor classes
- Base class has `has_entity_name = True`
- Each sensor has `native_value` returning float
- `_attr_device_class = SensorDeviceClass.MONETARY`
</acceptance_criteria>

---

## Task 4: Create Config Flow

Create `config_flow.py` for user configuration.

<action>
1. Create ConfigFlow class with domain
2. Add async_step_user for API key input
3. Add async_step_api_test for validation
4. Add async_step_zone_select for zone selection
</action>

<acceptance_criteria>
- config_flow.py exists
- Three async_step methods
- API validation during flow
- Zone discovery implemented
</acceptance_criteria>

---

## Task 5: Create Manifest

Create `manifest.json` for integration metadata.

<action>
Create manifest.json with domain, name, version, config_flow, requirements.
</action>

<acceptance_criteria>
- manifest.json exists with valid JSON
- config_flow: true
- domain matches const.py
</acceptance_criteria>

---

## Task 6: Create Translations

Create `translations/en.json` for UI strings.

<action>
1. Create translations directory
2. Create en.json with strings for config flow steps
3. Add error messages and sensor names
4. Add title for integration
</action>

<acceptance_criteria>
- translations/en.json exists
- Contains config flow strings
- Contains sensor names
- Valid JSON structure
</acceptance_criteria>

---

## Success Criteria

- All coordinators return data correctly
- Sensors display in HA with proper values
- Config flow allows setup with zone discovery
- Integration loads without errors

---

*Phase: 02-core-entities*
*Plan: 02*
