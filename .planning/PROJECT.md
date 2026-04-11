# Ontario Energy Pricing HACS Integration

## What This Is

A Home Assistant custom integration (HACS-compatible) that provides sensors tracking electricity pricing components for Oakville, Ontario (L6L 2S7):

1. **Current LMP Price** - Real-time Locational Marginal Price from gridstatus.io (replaced retired HOEP), updated hourly with timestamp and previous rate attributes
2. **24-Hour Average LMP** - Daily average price computed from 30-minute intervals, refreshed at midnight
3. **Global Adjustment (GA)** - Monthly rate component from IESO public XML
4. **Total Rate** - Combined LMP + GA + Admin Fee (for easy automation use)

The integration exposes these as Home Assistant sensors that can be used in automations, dashboards, and energy monitoring. Location is configurable during setup (e.g., "Oakville, ON").

**Note:** HOEP was retired on May 1, 2025. This integration uses LMP (Locational Marginal Pricing) which replaced HOEP under IESO's Market Renewal Program.

## Core Value

Users can see their real-time electricity rates in Home Assistant and make informed decisions about energy usage based on current pricing.

## Requirements

### Validated
- ✓ **Data Layer (Phase 1)** - API clients, data models, exceptions (2026-04-11)

### Active
- [ ] Retrieve LMP rate from gridstatus.io API for user-configured location
- [ ] Compute 24-hour rolling average from 30-minute interval data
- [ ] Retrieve Global Adjustment from IESO public XML (published monthly)
- [ ] Config flow for API key and admin fee amount (fee added to current rate)
- [ ] Four sensors exposed: Current LMP, 24h Average LMP, Global Adjustment, Total Rate
- [ ] LMP sensor includes attributes: timestamp and previous hour's rate
- [ ] Hourly refresh for current LMP sensor
- [ ] Daily refresh (midnight) for 24h average sensor
- [ ] Monthly refresh for Global Adjustment sensor
- [ ] Static admin fee added to Total Rate calculation
- [ ] HACS-compatible structure (hacs.json, manifest.json, etc.)
- [ ] Custom repository installable via HACS

### Out of Scope
- Multiple location support (only L6L zone) -超出当前需求
- Historical data storage - Home Assistant handles this
- Rate prediction/forecasting - too complex for v1
- Energy bill calculation - just expose the rates
- OAuth integration - gridstatus uses simple API key
- Multi-language support - English only for now
- Public HACS default repository submission - personal use only
- Component breakdown (energy/congestion/loss) - future enhancement

## Context

This integration is designed for personal use in Ontario where users have contracts with energy suppliers that include real-time LMP-based pricing, Global Adjustment passthrough, and administrative fees.

**Location Configuration:**
- User configures their city/location during setup (e.g., "Oakville, ON")
- Integration queries GridStatus API to find nearest/appropriate IESO zone
- Stores selected zone in config for all future queries
- Falls back to ONTARIO-wide average if specific zone unavailable

**Key technical considerations:**
- gridstatus.io provides a Python client library but raw REST API may be preferred for Home Assistant integration
- IESO Global Adjustment is published monthly via public XML at reports.ieso.ca
- Home Assistant integrations use `async` patterns and should not block the event loop
- HACS requires specific repository structure (custom_components/ folder, hacs.json, etc.)

## Constraints

- **Tech stack:** Python (Home Assistant custom integration), possibly homeassistant-aiohttp for HTTP requests
- **Runtime:** Must work within Home Assistant's async ecosystem
- **Data:** Requires valid gridstatus.io API key
- **Polling:** LMP hourly, 24h average daily at midnight, GA monthly
- **Compatibility:** Home Assistant Core 2024.x+, HACS
- **Development:** Will use local devcontainer or HA development environment

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| HACS custom repository vs default | Only for personal use, not submitting to HACS default repo | - Pending |
| REST API vs Python client | Home Assistant integrations typically use direct HTTP to avoid extra deps | - Pending |
| IESO GA source | IESO public XML at reports.ieso.ca/public/GlobalAdjustment/ | - Pending |
| Ontario zone mapping | Configurable location with zone discovery during setup | - Pending |
| 24h average aggregation | GridStatus provides 5-min data, aggregate to 30-min intervals then daily average | - Pending |

---

*Last updated: 2025-04-11 after requirements clarification*
