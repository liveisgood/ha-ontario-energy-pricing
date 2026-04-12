# Phase 4: HACS & Polish - Discussion Log
> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md - this log preserves the alternatives considered.

**Date:** 2026-04-12
**Phase:** 04-hacs-polish
**Areas discussed:** README Scope, Service Calls, Sensor Icons, Version/Release

---

## README Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Minimal | Installation only, link to wiki | |
| Standard HACS | Installation + basic config + sensor list | |
| Comprehensive | Installation + config + sensors + troubleshooting + automation examples + screenshots | ✓ |
| Full docs site | README as overview, separate docs site | |

**User's choice:** Option 3 - "Option 3 please"

**Notes:** User values complete documentation for HACS; wants to stand out from minimal integrations.

---

## Service Calls

| Option | Description | Selected |
|--------|-------------|----------|
| Add manual refresh service | `ontario_energy_pricing.refresh` service for power users | ✓ |
| Use HA built-in | Rely on `homeassistant.update_entity` | |
| Both | Custom service + built-in works | |

**User's choice:** Option 1 - "Option 1"

**Notes:** Good UX for testing and debugging; will be discoverable in Developer Tools.

---

## Sensor Icons

| Option | Description | Selected |
|--------|-------------|----------|
| Add to manifest.json | Centralized icon mappings | ✓ |
| Use HA defaults | No custom icons, use MONETARY defaults | |
| Icons per sensor | Define in sensor.py entity definitions | |

**User's choice:** Option 1 - "Option 1"

**Notes:** Icons to use: lightning-bolt (LMP), chart-line (24h avg), cash (GA), scale-balance (Total).

---

## Version/Release

| Option | Description | Selected |
|--------|-------------|----------|
| Semver 1.0.0 | First stable release, follow semver | ✓ |
| Start at 0.1.0 | Beta/early release versioning | |
| Calendar versioning | Date-based versions | |
| Git commit hash | No tags, use latest commit | |

**User's choice:** Option 1 - "Option 1"

**Notes:** Integration is complete and tested; 1.0.0 signals production-ready.

---

## the agent's Discretion
- Specific screenshot content and layout
- Exact troubleshooting FAQ items
- Automation example complexity

---

## Deferred Ideas
- CHANGELOG.md (nice but not required)
- Multi-language documentation (out of scope for v1)
- Rate prediction scripts (future enhancement)

---

*Discussion complete - ready for planning*
