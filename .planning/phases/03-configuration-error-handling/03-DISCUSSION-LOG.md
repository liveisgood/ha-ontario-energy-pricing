# Phase 3: Configuration & Error Handling - Discussion Log
> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md - this log preserves the alternatives considered.

**Date:** 2026-04-12
**Phase:** 03-configuration-error-handling
**Areas discussed:** Reconfiguration/Options Flow, Single Config Entry Enforcement, Coordinator Retry Strategy, GA XML Parse Errors, Network Recovery

---

## Reconfiguration/Options Flow

| Option | Description | Selected |
|--------|-------------|----------|
| Full Options Flow | Allow editing admin_fee and zone via Configure button; API key read-only | ✓ |
| Admin Fee Only | Only allow editing admin_fee; zone and API key locked | |
| No Reconfiguration | Delete and recreate config entry to change settings | |

**User's choice:** Full Options Flow - "Yes, they should be able to reconfigure this using the provided, standard HASS UI elements and best practices. The API key does remain the same it can only be changed with a full new setup. So option 1 is the one that makes most sense."

**Notes:** User acknowledged this follows standard HA patterns and users expect this flexibility.

---

## Single Config Entry Enforcement

| Option | Description | Selected |
|--------|-------------|----------|
| Block with friendly message | Check existing entries, show generic error | |
| Show existing config details | Block but show location/zone of existing config | ✓ |
| Silent ignore | Don't show Add button if config exists (HA UI handles) | |
| Allow multiple with warning | Technically allow but warn it's redundant | |

**User's choice:** Option 2 - "Option 2 is sensible"

**Notes:** User valued seeing context (location/zone) to help decide if reconfiguration is really needed.

---

## Coordinator Retry Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Exponential backoff | Retry after 5s, 15s, 45s; max 3 retries | ✓ |
| Fixed interval | Retry every 60 seconds, max 3 | |
| Immediate retry for specific | Only retry on transient errors (503) | |
| Wait for next poll | No retries, just mark unavailable | |

**User's choice:** Option 1 - "Option 1 of course"

**Notes:** GridStatus API is reliable; exponential backoff handles transient hiccups without hammering API.

---

## GA XML Parse Errors

| Option | Description | Selected |
|--------|-------------|----------|
| Retain indefinitely | Keep showing last GA value until next month | |
| Retain for 1 week | After 7 days of failures, mark unavailable | ✓ |
| Mark unavailable immediately | Any parse failure = unavailable | |
| Show last value with warning | Always retain but add stale attribute | |

**User's choice:** Option 2 - "Option 2 is acceptable"

**Notes:** Balances tolerance for IESO delays with catching real failures.

---

## Network Recovery

| Option | Description | Selected |
|--------|-------------|----------|
| Wait for next poll | Standard HA behavior | ✓ |
| Immediate retry on resume | Detect network restoration, trigger refresh | |
| Backoff with recovery | Retry every 5 min during outage | |
| Distinguish error types | Different behavior per error type | |

**User's choice:** Option 1

**Notes:** Standard HA behavior is sufficient; simpler code, less complexity.

---

## the agent's Discretion
- Exact error message wording for translations
- Debug logging level for retries
- Whether to cache available_zones in hass.data

---

## Deferred Ideas
- Config migration strategy (for v2 data structure changes)
- Re-authentication flow (not needed for GridStatus)
- Service calls for manual refresh (HA handles automatically)

---

*Discussion complete - ready for planning*
