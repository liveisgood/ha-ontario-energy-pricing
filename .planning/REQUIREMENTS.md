# Requirements: Ontario Energy Pricing HACS Integration

**Defined:** 2025-04-11
**Core Value:** Users can see real-time Ontario electricity rates (LMP) and make informed energy usage decisions

---

## v1 Requirements

### Data Retrieval

| ID | Requirement | Acceptance Criteria | Priority |
|----|-------------|---------------------|----------|
| **DATA-01** | Retrieve current LMP from GridStatus API | HTTP GET with API key returns valid JSON; parse interval_start_local and lmp fields | Must |
| **DATA-02** | Filter LMP data for configured location | Query returns data for zone determined during config based on user's city/location; fallback to ONTARIO-wide if specific zone unavailable | Must |
| **DATA-03** | Retrieve 24 hours of LMP history | Query returns past 24 hours of 5-minute interval data from GridStatus | Must |
| **DATA-04** | Aggregate 5-min data to 30-minute averages | Group 6 x 5-min prices into 30-min average; result is 48 data points per day | Must |
| **DATA-05** | Retrieve Global Adjustment from IESO | HTTP GET to reports.ieso.ca/public/GlobalAdjustment/PUB_GlobalAdjustment.xml returns valid XML with FirstEstimateRate | Must |
| **DATA-06** | Parse GA XML response | Successfully extract TradeMonth and FirstEstimateRate from XML | Must |
| **DATA-07** | Cache previous hour LMP | Store previous hour's rate for attribute reference | Must |

### Sensors

| ID | Requirement | Acceptance Criteria | Priority |
|----|-------------|---------------------|----------|
| **SENS-01** | Current LMP price sensor | Entity `sensor.ontario_energy_pricing_current_lmp`; state shows current $/kWh; device_class: monetary; unit: CAD/kWh | Must |
| **SENS-02** | LMP attributes | timestamp (ISO8601), previous_rate ($/kWh), zone (string) | Must |
| **SENS-03** | 24-hour average LMP sensor | Entity `sensor.ontario_energy_pricing_lmp_24h_average`; state shows average of last 24h; unit: CAD/kWh | Must |
| **SENS-04** | Global Adjustment sensor | Entity `sensor.ontario_energy_pricing_global_adjustment`; state shows GA rate; unit: CAD/kWh | Must |
| **SENS-05** | GA attributes | trade_month (YYYY-MM), last_updated (timestamp) | Should |
| **SENS-06** | Total Rate sensor | Entity `sensor.ontario_energy_pricing_total_rate`; state = LMP + GA + admin_fee; unit: CAD/kWh | Should |

### Configuration

| ID | Requirement | Acceptance Criteria | Priority |
|----|-------------|---------------------|----------|
| **CONF-01** | Config flow with API key | UI prompts for GridStatus API key; masked input; validation test endpoint before save | Must |
| **CONF-02** | Config flow with admin fee | UI prompts for admin fee in cents/kWh or $/kWh; numeric validation | Must |
| **CONF-05** | Config flow with location | UI prompts for city/location (e.g., "Oakville, ON"); used to determine appropriate IESO zone/node | Must |
| **CONF-03** | Config entry persistence | Settings survive restart; editable via UI | Must |
| **CONF-04** | Single config entry | Integration only allows one configuration | Must |
| **CONF-06** | Location zone resolution | On setup, query GridStatus API to find nearest/appropriate zone for configured location; store zone in config entry | Must |

### Update Intervals

| ID | Requirement | Acceptance Criteria | Priority |
|----|-------------|---------------------|----------|
| **SCH-01** | Current LMP hourly | Coordinator polls every 60 minutes; logs timestamp of last update | Must |
| **SCH-02** | 24h average daily at midnight | Coordinator updates once daily at 00:00 local time | Must |
| **SCH-03** | Global Adjustment monthly | Coordinator checks weekly but only updates when XML TradeMonth changes | Must |
| **SCH-04** | Admin fee on reload | Total Rate recalculated when admin fee changes in config | Must |

### HACS Integration

| ID | Requirement | Acceptance Criteria | Priority |
|----|-------------|---------------------|----------|
| **HACS-01** | manifest.json | Valid JSON with domain, name, version, codeowners, config_flow=true | Must |
| **HACS-02** | hacs.json | Valid JSON at repo root with name and render_readme | Must |
| **HACS-03** | Custom component structure | Files in `custom_components/ontario_energy_pricing/` | Must |
| **HACS-04** | Installable via HACS | Add custom repository URL; shows integration; installs successfully | Must |

### Location & Zone

| ID | Requirement | Acceptance Criteria | Priority |
|----|-------------|---------------------|----------|
| **LOC-01** | Location input validation | Config flow accepts city/location string; validates non-empty | Must |
| **LOC-02** | Zone discovery | During setup, query GridStatus API for available zones/nodes; find closest match to configured location | Must |
| **LOC-03** | Zone fallback | If no specific zone match found, default to "ONTARIO" (province-wide average) | Should |
| **LOC-04** | Zone stored in config | Selected zone name stored in config entry; used for all future API queries | Must |

### Error Handling

| ID | Requirement | Acceptance Criteria | Priority |
|----|-------------|---------------------|----------|
| **ERR-01** | API key invalid | Config flow shows error when GridStatus returns 401 | Must |
| **ERR-02** | LMP fetch failure | Sensor becomes unavailable; coordinator retries with backoff | Must |
| **ERR-03** | GA XML parse error | Keep previous value; mark unavailable on persistent failure | Should |
| **ERR-04** | Network unavailable | Sensors become unavailable; recovery on next successful poll | Must |

---

## v2 Requirements (Deferred)

### Advanced Features

| ID | Requirement | Notes |
|----|-------------|-------|
| **V2-01** | LMP component breakdown | energy, congestion, loss as separate sensors |
| **V2-02** | Day-ahead pricing | Separate sensor for DAM LMP |
| **V2-03** | Price threshold alerts | Binary sensor for high/low price alerts |
| **V2-04** | Energy dashboard integration | Compatible with HA Energy feature |
| **V2-05** | Multiple location support | Configurable zone/node selection |

---

## Out of Scope

| Feature | Reason |
|---------|--------|
| Historical data queries beyond 24h | Home Assistant handles long-term storage |
| Bill calculation | Too variable (delivery, HST, other charges) |
| TOU period detection | No longer relevant with LMP |
| Real-time 5-min updates | User requested hourly, not sub-hourly |
| Mobile app | HACS is for HA, not standalone |
| Email/webhook notifications | Use HA automation engine |

---

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| DATA-01 | Phase 1 | Pending |
| DATA-02 | Phase 1 | Pending |
| DATA-03 | Phase 1 | Pending |
| DATA-04 | Phase 1 | Pending |
| DATA-05 | Phase 1 | Pending |
| DATA-06 | Phase 1 | Pending |
| DATA-07 | Phase 1 | Pending |
| SENS-01 | Phase 2 | Pending |
| SENS-02 | Phase 2 | Pending |
| SENS-03 | Phase 2 | Pending |
| SENS-04 | Phase 2 | Pending |
| SENS-05 | Phase 2 | Pending |
| SENS-06 | Phase 2 | Pending |
| CONF-01 | Phase 2 | Pending |
| CONF-02 | Phase 2 | Pending |
| CONF-03 | Phase 3 | Pending |
| CONF-04 | Phase 3 | Pending |
| CONF-05 | Phase 2 | Pending |
| CONF-06 | Phase 2 | Pending |
| SCH-01 | Phase 2 | Pending |
| SCH-02 | Phase 2 | Pending |
| SCH-03 | Phase 2 | Pending |
| SCH-04 | Phase 2 | Pending |
| HACS-01 | Phase 4 | Pending |
| HACS-02 | Phase 4 | Pending |
| HACS-03 | Phase 4 | Pending |
| HACS-04 | Phase 4 | Pending |
| LOC-01 | Phase 2 | Pending |
| LOC-02 | Phase 2 | Pending |
| LOC-03 | Phase 2 | Pending |
| LOC-04 | Phase 2 | Pending |
| ERR-01 | Phase 3 | Pending |
| ERR-02 | Phase 3 | Pending |
| ERR-03 | Phase 3 | Pending |
| ERR-04 | Phase 3 | Pending |

**Coverage:**
- v1 requirements: 29 total
- Mapped to phases: 29
- Unmapped: 0 ✓

---

*Requirements defined: 2025-04-11*
*Last updated: 2025-04-11 after scope clarification (24h average sensor)*
