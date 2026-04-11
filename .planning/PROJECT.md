# Ontario Energy Pricing HACS Integration

## What This Is

A Home Assistant custom integration (HACS-compatible) that provides three sensors tracking electricity pricing components for Oakville, Ontario:

1. **Hourly Ontario Energy Price (HOEP)** - Real-time wholesale market price from gridstatus.io, updated hourly with timestamp and previous rate attributes
2. **Global Adjustment (GA)** - Weekly-published rate component from IESO, updated weekly
3. **Administrative Fee** - User-configured static fee from their energy contract

The integration exposes these as Home Assistant sensors that can be used in automations, dashboards, and energy monitoring.

## Core Value

Users can see their real-time electricity rates in Home Assistant and make informed decisions about energy usage based on current pricing.

## Requirements

### Validated
(None yet - ship to validate)

### Active
- [ ] Retrieve HOEP rate from gridstatus.io API for Ontario (south/central zone covering Oakville)
- [ ] Retrieve Global Adjustment from authoritative IESO source
- [ ] Config flow for API key and admin fee amount
- [ ] Three sensors exposed: HOEP, Global Adjustment, Admin Fee
- [ ] HOEP sensor includes attributes: timestamp and previous hour's rate
- [ ] Hourly refresh for HOEP sensor
- [ ] Weekly refresh for Global Adjustment sensor
- [ ] Static admin fee sensor (no polling needed)
- [ ] HACS-compatible structure (hacs.json, manifest.json, etc.)
- [ ] Custom repository installable via HACS

### Out of Scope
- Multiple zone support (only Ontario/south zone) -超出当前需求
- Historical data storage - Home Assistant handles this
- Rate prediction/forecasting - too complex for v1
- Energy bill calculation - just expose the rates
- OAuth integration - gridstatus uses simple API key
- Multi-language support - English only for now
- Public HACS default repository submission - personal use only
## Context

This integration is designed for personal use in Oakville, Ontario where the user has a contract with an energy supplier that includes:
- Real-time HOEP-based pricing
- Global Adjustment passthrough
- Fixed administrative fee

**Key technical considerations:**
- gridstatus.io provides a Python client library but raw REST API may be preferred for Home Assistant integration
- IESO Global Adjustment is typically published on the IESO website or via their market data APIs
- Home Assistant integrations use `async` patterns and should not block the event loop
- HACS requires specific repository structure (custom_components/ folder, hacs.json, etc.)

**Data sources to research:**
- gridstatus.io API documentation and authentication
- IESO Global Adjustment publication schedule and access method
- Home Assistant's recommended patterns for REST API polling

## Constraints

- **Tech stack:** Python (Home Assistant custom integration), possibly homeassistant-aiohttp for HTTP requests
- **Runtime:** Must work within Home Assistant's async ecosystem
- **Data:** Requires valid gridstatus.io API key
- **Polling:** HOEP hourly (or slightly more frequent), GA weekly
- **Compatibility:** Home Assistant Core 2024.x+, HACS
- **Development:** Will use local devcontainer or HA development environment

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| HACS custom repository vs default | Only for personal use, not submitting to HACS default repo | - Pending |
| REST API vs Python client | Home Assistant integrations typically use direct HTTP to avoid extra deps | - Pending |
| IESO GA source | Need to determine: IESO website scraping vs API vs RSS feed | - Pending |
| Three sensors vs one compound sensor | Separates concerns, different update frequencies | - Pending |

---

*Last updated: 2025-04-11 after initialization*
