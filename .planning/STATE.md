---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
current_phase: "01 of 1 (ieso-direct-refactor) 🔄"
status: executing
stopped_at: "Architecture Pivot: Refactoring to IESO Direct"
last_updated: "2026-04-12T19:00:00Z"
progress:
  total_phases: 4
  completed_phases: 3
previous_architecture:
  complete: true
  tag: "pre-ieso-direct-arch"
  data_source: "gridstatus-api"
refactor:
  status: "in_progress"
  reason: "IESO direct XML provides real-time data without API key"
  estimated_effort: "2-3 hours"
  actual_progress: "~70%"
---

# State: Ontario Energy Pricing HACS Integration

## 🔄 ARCHITECTURE PIVOT IN PROGRESS

**Current Status:** Refactoring from GridStatus API → IESO Direct XML  
**Reason:** Discovery that IESO provides real-time 5-min LMP data via public XML  
**Tag:** `pre-ieso-direct-arch` preserves old implementation  
**Progress:** ~70% complete

---

## Why The Pivot?

| Aspect | GridStatus API | IESO Direct XML |
|--------|---------------|-----------------|
| **Authentication** | API key required | ✅ None (public) |
| **Data freshness** | 11+ months old | ✅ Real-time 5-min |
| **Reliability** | External dependency | ✅ Direct from source |
| **Complexity** | Complex query params | ✅ Simple HTTP GET |

---

## ✅ COMPLETED REFACTOR WORK

### Files Updated (2026-04-12)

1. **NEW: `ieso_lmp.py`** - Real-time LMP client using IESO direct XML
   - Fetches `PUB_RealtimeOntarioZonalPrice.xml`
   - Parses 5-minute intervals
   - Converts $/MWh → ¢/kWh
   - Returns `IESOLMPData` with intervals and hour average

2. **NEW: `ieso_ga.py`** - Renamed from `ieso.py`
   - Global Adjustment client (unchanged)

3. **UPDATED: `coordinator.py`** - Unified coordinator
   - Single coordinator for LMP + GA
   - 4.5-minute update interval
   - Simplified data model

4. **UPDATED: `config_flow.py`** - Removed API key and zone selection
   - Simplified to location + admin fee only
   - No API key required!

5. **UPDATED: `sensor.py`** - Simplified sensors
   - Current LMP (latest interval)
   - Hour Average LMP
   - Global Adjustment
   - Total Rate

6. **UPDATED: `const.py`** - Updated intervals and URLs

7. **UPDATED: `__init__.py`** - Unified coordinator setup

8. **UPDATED: `exceptions.py`** - Removed GridStatus exceptions

9. **UPDATED: `models.py`** - Simplified models

10. **UPDATED: `translations/en.json`** - Removed API key references

11. **DELETED: `gridstatus.py`** - No longer needed

---

## 📋 REMAINING WORK

- [ ] Update manifest.json (check dependencies)
- [ ] Create new test suite
- [ ] Update README.md
- [ ] Update HACS.json
- [ ] Verify hacs.json and services.yaml
- [ ] Final integration test

---

## New Architecture

### Data Sources
- **LMP (Real-time):** `https://reports-public.ieso.ca/public/RealtimeOntarioZonalPrice/PUB_RealtimeOntarioZonalPrice.xml`
- **GA (Weekly):** `http://reports.ieso.ca/public/GlobalAdjustment/PUB_GlobalAdjustment.xml`

### Update Intervals
- **LMP:** 4.5 minutes (was 1 hour) - Prices change every 5 minutes
- **GA:** Weekly (unchanged) - Settled monthly

### Unit Conversion
- IESO returns: **$51.98/MWh** (current example)
- Convert to: **5.20 ¢/kWh** (divide by 10)
- Your rate: **~12.65 ¢/kWh** (LMP + GA + Admin Fee)

---

## Test Results

**Latest IESO Direct Test (2026-04-12 14:00 EST):**
```
Delivery Date: 2026-04-12
Delivery Hour: 14:00
Hour Average LMP: 51.98 $/MWh (5.20 ¢/kWh)
Valid Intervals: 10 of 12
GA Rate: 0.0600 $/kWh (6.00 ¢/kWh)

YOUR TOTAL RATE:
  Admin Fee: 1.45 ¢/kWh
  LMP (avg): 5.20 ¢/kWh
  GA: +6.00 ¢/kWh
  TOTAL: 12.65 ¢/kWh ($0.1265/kWh)
```

---

## Key Changes

| Before | After |
|--------|-------|
| GridStatus API key required | ✅ No API key |
| Zone selection needed | ✅ Ontario-wide zonal price |
| 3-step config flow | ✅ 1-step simple config |
| Multiple coordinators | ✅ Single unified coordinator |
| Hourly updates | ✅ 4.5-minute updates |
| Historic data (11mo old) | ✅ Real-time current data |

---

## Related Memory Cards
- [[ieso-direct-lmp-discovery]] - Full technical details
- [[ontario-energy-pricing-domain]] - May need update

---

*Pivot started: 2026-04-12 after GridStatus returned 11-month-old data*  
*Committed to: Simpler, faster, no API key approach*  
*Status: ~70% complete, core refactor done*
