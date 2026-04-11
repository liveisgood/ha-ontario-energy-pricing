# Roadmap: Ontario Energy Pricing HACS Integration

**Project:** Ontario Energy Pricing HACS Integration  
**Created:** 2025-04-11  
**Phases:** 4 | **Requirements:** 29

---

## Phase Overview

| # | Phase | Requirements | Status |
|---|-------|--------------|--------|
| 1 | Data Layer | DATA-01 to DATA-07 | ○ Not Started |
| 2 | Core Entities | SENS-01 to SENS-06, CONF-01, CONF-02, CONF-05, CONF-06, SCH-01 to SCH-04, LOC-01 to LOC-04 | ○ Not Started |
| 3 | Configuration | CONF-03, CONF-04, ERR-01 to ERR-04 | ○ Not Started |
| 4 | HACS & Polish | HACS-01 to HACS-04 | ○ Not Started |

---

## Phase 1: Data Layer

**Goal:** Implement API clients and data retrieval/aggregation logic

**Requirements:**
- DATA-01: GridStatus API client for LMP data
- DATA-02: Zone-specific data filtering
- DATA-03: 24-hour LMP history retrieval
- DATA-04: Aggregate 5-min data to 30-min averages
- DATA-05: IESO Global Adjustment XML retrieval
- DATA-06: GA XML parsing
- DATA-07: Previous hour LMP caching

**Success Criteria:**
1. `GridStatusClient` class can authenticate and fetch LMP data
2. `IESOGlobalAdjustment` class can fetch and parse GA XML
3. 5-min data aggregation produces 48 x 30-min averages for 24h
4. All data models properly typed and validated

**Entry Criteria:** None (first phase)

**Files to Create:**
- `custom_components/ontario_energy_pricing/const.py` - Constants
- `custom_components/ontario_energy_pricing/gridstatus.py` - GridStatus API client
- `custom_components/ontario_energy_pricing/ieso.py` - IESO GA client
- `custom_components/ontario_energy_pricing/models.py` - Data models (LMPPrice, GlobalAdjustment, etc.)

---

## Phase 2: Core Entities

**Goal:** Implement sensors and data coordinators

**Requirements:**
- SENS-01 to SENS-06: Four sensors with proper attributes
- CONF-01, CONF-02, CONF-05, CONF-06: Config flow setup
- SCH-01 to SCH-04: Scheduled updates
- LOC-01 to LOC-04: Zone discovery and location handling

**Success Criteria:**
1. LMPCoordinator fetches data hourly and stores previous hour
2. LMP24hAverageCoordinator computes daily average at midnight
3. GlobalAdjustmentCoordinator checks for updates
4. Four sensors exposed with correct device classes
5. Config flow accepts API key, admin fee, and location
6. Zone discovery queries API during setup

**Entry Criteria:** Phase 1 complete, data models working

**Files to Create:**
- `custom_components/ontario_energy_pricing/__init__.py` - Component init
- `custom_components/ontario_energy_pricing/coordinator.py` - Data coordinators
- `custom_components/ontario_energy_pricing/sensor.py` - Sensor entities
- `custom_components/ontario_energy_pricing/config_flow.py` - Config flow (UI)
- `custom_components/ontario_energy_pricing/entity.py` - Base entity class (if needed)

---

## Phase 3: Configuration & Error Handling

**Goal:** Robust config management and error handling

**Requirements:**
- CONF-03: Config persistence
- CONF-04: Single config entry enforcement
- ERR-01 to ERR-04: Error handling

**Success Criteria:**
1. Config entries survive restart
2. API key validation during config flow (test API call)
3. Network errors handled gracefully with retry logic
4. XML parse errors handled, previous value retained
5. Sensors become unavailable on data fetch failure

**Entry Criteria:** Phase 2 complete, sensors functioning

**Files Modified:**
- `custom_components/ontario_energy_pricing/config_flow.py` - Add validation
- `custom_components/ontario_energy_pricing/coordinator.py` - Add error handling

---

## Phase 4: HACS & Polish

**Goal:** Package for HACS installation

**Requirements:**
- HACS-01 to HACS-04: HACS compatibility

**Success Criteria:**
1. manifest.json valid with config_flow
2. hacs.json at repo root
3. README.md with installation instructions
4. Integration installable via HACS custom repository
5. Sensors display with proper icons and units in HA

**Entry Criteria:** Phase 3 complete, integration working

**Files to Create:**
- `custom_components/ontario_energy_pricing/manifest.json`
- `custom_components/ontario_energy_pricing/hacs.json` (at repo root)
- `custom_components/ontario_energy_pricing/services.yaml` (optional)
- `custom_components/ontario_energy_pricing/translations/en.json`
- `README.md`

**Deliverables:**
- Working HACS custom integration
- Git repository ready for HACS

---

## Dependency Graph

```
Phase 1 (Data Layer)
  │
  ├──► const.py
  ├──► models.py
  ├──► gridstatus.py
  └──► ieso.py
       │
       ▼
Phase 2 (Core Entities)
       │
       ├──► __init__.py
       ├──► coordinator.py (depends on gridstatus.py, ieso.py)
       ├──► config_flow.py (depends on gridstatus.py for zone discovery)
       └──► sensor.py (depends on coordinator.py)
            │
            ▼
Phase 3 (Error Handling)
            │
            └──► Enhance config_flow.py and coordinator.py
                 │
                 ▼
Phase 4 (HACS)
                 │
                 ├──► manifest.json
                 ├──► hacs.json
                 └──► README.md
```

---

## Key Design Decisions

| Decision | Rationale | Phase |
|----------|-----------|-------|
| Three coordinators vs one | Different update frequencies (hourly, daily, monthly) | Phase 2 |
| Location config + zone discovery | User-friendly while supporting accurate nodal pricing | Phase 2 |
| Separate GA XML fetching | Free, no auth, simple structure | Phase 1 |
| Total Rate sensor | Convenience for automations (single value) | Phase 2 |
| Store zone in config entry | Avoid re-querying zone on every update | Phase 2 |

---

## Risk Mitigation

| Risk | Phase | Mitigation |
|------|-------|------------|
| IESO zone matching unclear | Phase 2 | Test zone discovery with API; fallback to ONTARIO |
| GridStatus API rate limits | Phase 1-2 | Cache data; respect update intervals |
| XML format changes | Phase 1-3 | Defensive parsing; log full XML on error |
| Timezone bugs | Phase 2 | Always use US/Eastern for IESO; proper TZ-aware datetime |

---

## Milestones

| Milestone | Definition | Estimated |
|-----------|------------|-----------|
| **Core Data Working** | Can fetch LMP and GA from APIs | Phase 1 |
| **Sensors Active** | All three sensors visible in HA | Phase 2 |
| **Config Working** | Config flow creates entry successfully | Phase 2 |
| **HACS Ready** | Installable via HACS custom repository | Phase 4 |

---

## Phase Transitions

### Phase 1 → Phase 2
- [ ] GridStatusClient authenticates and returns data
- [ ] IESO client fetches and parses GA XML
- [ ] 24h aggregation produces correct averages
- [ ] Unit tests pass

### Phase 2 → Phase 3
- [ ] Sensors display in HA UI
- [ ] Config flow creates config entry
- [ ] Hourly updates working
- [ ] 24h average computes at midnight

### Phase 3 → Phase 4
- [ ] Error handling verified (disconnect network, simulate 401, etc.)
- [ ] Config restart persistence verified
- [ ] All sensors survive HA restart

---

*Generated: 2025-04-11*
*Last updated: 2025-04-11*
