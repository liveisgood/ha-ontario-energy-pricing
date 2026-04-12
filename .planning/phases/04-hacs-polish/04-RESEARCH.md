# Phase 4: HACS & Polish - Technical Research
**Researched:** 2026-04-12
**Status:** Ready for planning

---

## Research Scope

Investigate Home Assistant and HACS packaging requirements:
1. hacs.json structure and requirements
2. manifest.json icon configuration
3. services.yaml specification
4. README best practices for HA custom integrations
5. HACS publication and release tagging

---

## 1. hacs.json Structure

### Required Fields
```json
{
  "name": "Ontario Energy Pricing",
  "content_in_root": false,
  "filename": "ontario_energy_pricing.zip",
  "country": ["CA"],
  "homeassistant": "2024.1.0",
  "render_readme": true,
  "iot_class": "cloud_polling"
}
```

### Field Descriptions

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Display name in HACS store |
| `content_in_root` | No | If true, integration files are at repo root |
| `filename` | No | For zip releases (not typically used) |
| `country` | No | ISO country codes for region filtering |
| `homeassistant` | Yes | Minimum HA version required |
| `render_readme` | No | If true, render README.md in HACS |
| `iot_class` | Yes | Classification (cloud_polling typical) |

**Location:** Repository root (`hacs.json`, not in `custom_components/`)

**Source:** https://hacs.xyz/docs/publish/integration/#hacsjson

---

## 2. Manifest Icons

### Icon Format in manifest.json
```json
{
  "domain": "ontario_energy_pricing",
  "name": "Ontario Energy Pricing",
  "icons": {
    "current_lmp": "mdi:lightning-bolt",
    "lmp_24h_average": "mdi:chart-line",
    "global_adjustment": "mdi:cash",
    "total_rate": "mdi:scale-balance"
  }
}
```

### Icon Path Strategy
**Per HA docs**, icons go in manifest.json `"icons"` object, OR in entity platform code:

**Option 1: manifest.json (preferred for static icons)**
```json
"icons": {
  "current_lmp": "mdi:lightning-bolt"
}
```

**Option 2: Entity property**
```python
@property
def icon(self) -> str | None:
    return "mdi:lightning-bolt"
```

**Current HA recommendation**: Use entity `icon` property for dynamic icons. For static icons that don't change, manifest.json is simpler.

### Common Pricing Icons
| Purpose | MDI Icon |
|---------|----------|
| Energy/Electricity | `mdi:lightning-bolt` |
| Money/Pricing | `mdi:cash` or `mdi:currency-usd` |
| Rate/Total | `mdi:scale-balance` |
| Chart/Average | `mdi:chart-line` |
| Timer/Interval | `mdi:clock-outline` |

**Source:** https://pictogrammers.com/library/mdi/ (searchable)

---

## 3. Services.yaml

### Service Definition Format

```yaml
# Location: custom_components/ontario_energy_pricing/services.yaml
# See: https://developers.home-assistant.io/docs/dev_101_services/

refresh:
  name: Refresh
  description: Manually refresh all sensor data from APIs
  fields: {}  # No parameters

custom_update:
  name: Custom Update
  description: Update with custom parameters
  target:
    entity:
      integration: ontario_energy_pricing
      domain: sensor
  fields:
    force:
      name: Force
      description: Force update even if not due
      default: false
      selector:
        boolean: {}
```

### Service Registration Pattern

```python
# In __init__.py async_setup_entry
hass.services.async_register(
    DOMAIN,
    "refresh",
    handle_refresh_service,
    schema=vol.Schema({}),  # Empty for no parameters
)
```

### Service Unregistration

```python
# In __init__.py async_unload_entry
hass.services.async_remove(DOMAIN, "refresh")
```

### Service Types
For this integration, a simple service without parameters is appropriate:

| Service | Parameters | Returns |
|---------|------------|---------|
| `refresh` | None | None (updates all coordinators) |

---

## 4. README Best Practices for HACS

### Structure Template

```markdown
# Ontario Energy Pricing [![hacs_badge](URL)](URL) [![ha_version](URL)]()

Track real-time electricity rates in Home Assistant for Ontario, Canada.

## Features

- Current LMP (Locational Marginal Price)
- 24-hour average LMP
- Global Adjustment rate
- Total Rate (LMP + GA + Admin Fee)

## Installation

### HACS (Recommended)
1. Add this repository as a custom repository in HACS
2. Search for "Ontario Energy Pricing"
3. Install
4. Restart Home Assistant

### Manual
1. Copy `custom_components/ontario_energy_pricing/` to your config
2. Restart Home Assistant

## Configuration

1. Go to Settings → Devices & Services
2. Click "Add Integration"
3. Search for "Ontario Energy Pricing"
4. Enter GridStatus API key and your location

## Sensors

| Sensor | Description | Unit | Update Frequency |
|--------|-------------|------|------------------|
| sensor.ontario_energy_pricing_current_lmp | Current LMP | CAD/kWh | Hourly |
| ... | | | |

## Pricing Formula

```
Total Rate = LMP + Global Adjustment + Admin Fee
```

## Automation Examples

### Example 1: High Rate Alert
```yaml
automation:
  - alias: "High electricity rate alert"
    trigger:
      - platform: numeric_state
        entity_id: sensor.ontario_energy_pricing_total_rate
        above: 0.15
    action:
      - service: notify.notify
        data:
          message: "Electricity rate is ${{ trigger.to_state.state }}/kWh!"
```

## Screenshots

[Include 2-3 screenshots]

## Troubleshooting

### Sensor unavailable
- Check GridStatus API key validity
- Verify zone selection in configuration

---

## Credits
- Data from [GridStatus.io](https://gridstatus.io) and [IESO](https://ieso.ca)
```

### Badge URLs

| Badge | Markdown |
|-------|----------|
| HACS Custom | `[![hacs_custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz/)` |
| HA Version | `[![ha_version](https://img.shields.io/badge/Home%20Assistant-2024.1.0-blue.svg)](https://www.home-assistant.io/)` |

---

## 5. HACS Publication Process

### Release Tagging

1. Update `manifest.json` version
2. Commit changes
3. Create GitHub release with tag `v1.0.0`
4. HACS detects new release within ~15 minutes

### Release Checklist

- [ ] `hacs.json` at repo root
- [ ] `manifest.json` with version
- [ ] `custom_components/ontario_energy_pricing/` structure
- [ ] GitHub release tagged
- [ ] README.md with installation instructions

### Version Sync

**Important:** HACS uses the tag version, NOT the manifest.json version directly. Best practice: keep them in sync.

| File | Version Location | Example |
|------|------------------|---------|
| manifest.json | `"version": "1.0.0"` | `"1.0.0"` |
| Git tag | Tag name | `v1.0.0` |
| hacs.json | Not required | - |

---

## Key Implementation Notes

### Icon Implementation
- Entity `icon` property is the modern HA pattern
- `hass_icon` in manifest.json is legacy (2024+)
- Recommended: implement in sensor.py, not manifest.json

### Service Registration
- Register in `async_setup_entry`
- Unregister in `async_unload_entry`
- `services.yaml` is auto-loaded, no explicit read needed

### README Maintenance
- Keep screenshots current with actual UI
- Update automation examples to match syntax
- Include attribution (GridStatus, IESO)

---

## References

1. https://hacs.xyz/docs/publish/integration/ - HACS publishing
2. https://developers.home-assistant.io/docs/dev_101_services/ - Services
3. https://developers.home-assistant.io/docs/creating_integration_manifest/ - Manifest
4. https://pictogrammers.com/library/mdi/ - Material Design Icons

---

*Phase: 04-hacs-polish*
*Research: 2026-04-12*
