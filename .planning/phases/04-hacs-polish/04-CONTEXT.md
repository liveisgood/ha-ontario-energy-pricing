# Phase 4: HACS & Polish - Context
**Gathered:** 2026-04-12
**Status:** Ready for planning

---

## Phase Boundary
Package the Ontario Energy Pricing integration for HACS custom repository installation. Create comprehensive documentation and metadata required for HACS distribution, including repository-level files and polished presentation.

**Scope:**
- hacs.json at repository root
- Comprehensive README.md with installation, configuration, and usage docs
- services.yaml for manual refresh service
- Updated manifest.json with entity icons
- Version 1.0.0 release preparation

---

## Implementation Decisions

### D-01: README Scope
**Decision:** Comprehensive documentation covering all aspects of the integration

**Sections to include:**
1. **Header** - Project title, badges (HACS, HA version), short description
2. **Features** - What the integration provides (4 sensors, real-time pricing, etc.)
3. **Installation** - HACS custom repo add → install → restart HA
4. **Configuration** - Step-by-step config flow walkthrough with screenshots
5. **Sensors** - Table of 4 sensors with descriptions, units, update intervals
6. **Pricing Formula** - Total Rate = LMP + GA + Admin Fee
7. **Automation Examples** - 2-3 common automations:
   - "Notify when rate exceeds threshold"
   - "Run dishwasher when rate is low"
8. **Troubleshooting** - Common issues and solutions
9. **Screenshots** - Dashboard card examples

**Why:** Good HACS integrations stand out with complete docs; reduces support questions.

### D-02: Service Calls
**Decision:** Add manual refresh service for power users

**Implementation:**
- File: `custom_components/ontario_energy_pricing/services.yaml`
- Service: `ontario_energy_pricing.refresh`
- Description: "Manually refresh all sensor data"
- Fields: none (refreshes all coordinators)

**Integration:** Register service in `__init__.py` `async_setup_entry` via `hass.services.async_register`

**Why:** Nice UX for testing/debugging; discoverable in Developer Tools → Services.

### D-03: Sensor Icons
**Decision:** Add entity icons to manifest.json for visual polish

**Icon mappings:**
| Sensor | Icon |
|--------|------|
| `current_lmp` | `mdi:lightning-bolt` |
| `lmp_24h_average` | `mdi:chart-line` |
| `global_adjustment` | `mdi:cash` |
| `total_rate` | `mdi:scale-balance` |

**Implementation:** Add `icons` field to `manifest.json` following HA pattern.

**Why:** Visual polish helps users identify entities quickly in UI.

### D-04: Version/Release
**Decision:** Semantic versioning starting at 1.0.0

**Version strategy:**
- Current: `1.0.0` (complete, tested integration)
- Patch: `1.0.1` for bug fixes
- Minor: `1.1.0` for new features
- Major: `2.0.0` for breaking changes

**Release process:**
1. Update `manifest.json` version
2. Tag release on GitHub: `v1.0.0`
3. HACS will pick up the release

**Why:** Standard semver is expected by HACS users; signals stable, production-ready integration.

---

## Canonical References

### HACS Requirements
- `https://hacs.xyz/docs/publish/integration/` - HACS integration requirements
- `https://hacs.xyz/docs/publish/start/` - Publishing to HACS

### Home Assistant Manifest
- `https://developers.home-assistant.io/docs/creating_integration_manifest/` - manifest.json spec
- `https://developers.home-assistant.io/docs/dev_101_services/` - services.yaml

### Phase 3 Code (to document)
- `custom_components/ontario_energy_pricing/__init__.py` - for service registration
- `custom_components/ontario_energy_pricing/manifest.json` - for icon updates
- `custom_components/ontario_energy_pricing/sensor.py` - sensor details for README

---

## Existing Code Insights

### Reusable Assets
- `manifest.json` - exists, needs icon additions
- `translations/en.json` - complete, can reference for README
- Four sensors already implemented - document their behavior

### Established Patterns
- Semantic versioning used in manifest.json (currently "1.0.0")
- Service registration pattern in HA: `hass.services.async_register(DOMAIN, "refresh", handler)`
- Icon format: `"icons": [{"icon": "mdi:lightning-bolt", "entity_id": "sensor.ontario_energy_pricing_current_lmp"}]`

### Integration Points
- Services register in `async_setup_entry`
- Services unregister in `async_unload_entry`
- hacs.json references manifest.json location

---

## Specific Ideas
- Screenshot: Config flow step 1 (API key entry)
- Screenshot: Sensor card showing all 4 values
- Automation example: "If current_lmp > 0.15, send notification"
- Troubleshooting: "Sensor unavailable - check API key validity"
- Badge: HACS Custom status badge in README

---

## Deferred Ideas
- **Changelog** - Add CHANGELOG.md for release notes (nice but not required)
- **Multi-language docs** - English only for v1 (out of scope)
- **Advanced automations** - Rate prediction scripts (complex, future phase)

---

*Phase: 04-hacs-polish*
*Context gathered: 2026-04-12*
