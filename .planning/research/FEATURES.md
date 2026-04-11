# Features Research: Ontario Energy Pricing HACS Integration

**Research Date:** 2025-04-11
**Researcher:** Claude Code

---

## Table Stakes (Must Have)

These are the core features expected in any energy pricing integration:

### T1: Electricity Price Sensor
- [x] **T1.1** Current LMP price as sensor state (CAD/kWh)
- [x] **T1.2** Timestamp attribute showing when price is from
- [x] **T1.3** Previous hour price attribute
- [x] **T1.4** Hourly updates (or near-real-time configuration option)

### T2: Global Adjustment Sensor
- [x] **T2.1** Current GA rate as sensor state (CAD/kWh)
- [x] **T2.2** Weekly updates (or configurable check frequency)
- [x] **T2.3** Month/year attribution (so user knows which period it applies to)

### T3: Configuration
- [x] **T3.1** API key input (GridStatus)
- [x] **T3.2** Admin fee input (static)
- [x] **T3.3** Config entry created and reloadable

---

## Differentiators (Below Standard but Useful)

### D1: Price Breakdown Sensor
Expose the LMP components as separate attributes or sensors:
- Energy component
- Congestion component
- Loss component

### D2: Rate Tier Display
Show if current price is:
- On-peak
- Mid-peak
- Off-peak
(Note: This requires knowledge of Ontario's TOU periods)

### D3: Total Rate Sensor
Combined sensor showing: LMP + GA + Admin Fee + other components

### D4: Historical Comparison
- Today's average vs yesterday
- Price trend indicator

### D5: Next Period Preview
Show next hour's projected price (if available in LMP day-ahead data)

---

## Anti-Features (Explicitly Out of Scope)

These are common energy integration features that we'll deliberately exclude:

### A1: Bill Calculation
- Why: Too variable (delivery charges, regulatory, HST)
- Scope: Just expose wholesale + GA + admin

### A2: Usage Tracking
- Why: HA Energy dashboard handles this
- Scope: Focus on price data only

### A3: Real-Time Demand/Fuel Mix
- Why: User only asked for pricing
- Scope: Stick to requested sensors

### A4: Multiple Locations/Zones
- Why: User specific to Oakville
- Scope: Just Ontario-wide or Oakville zone

### A5: Notification/Alert System
- Why: Can be done via HA automations
- Scope: Data provision only

---

## Feature Complexity Assessment

| Feature | Effort | Notes |
|---------|--------|-------|
| Basic LMP sensor | Low | Simple API poll |
| Basic GA sensor | Low | Parse XML, check weekly |
| Admin fee sensor | Very Low | Config value |
| Price attributes | Low | Just extra API fields |
| Config flow | Medium | HA UI boilerplate |
| LMP components | Low | API provides these |
| TOU tier detection | Medium | Requires business logic |
| Total rate calc | Low | Simple math |
| Historical average | High | Requires data storage |
| Day-ahead preview | Medium | Different API dataset |

---

## Recommended v1 Scope

Focus on Core + Differentiator D1:

**Sensor 1: `sensor.ontario_lmp_price`**
- State: Current $/kWh
- Attributes:
  - `timestamp`: ISO8601 of interval start
  - `previous_rate`: Previous hour price
  - `zone`: "ONTARIO" or zone name

**Sensor 2: `sensor.ontario_global_adjustment`**
- State: Current GA rate $/kWh
- Attributes:
  - `trade_month`: e.g., "2026-04"
  - `last_updated`: When XML was checked

**Sensor 3: `sensor.ontario_admin_fee`**
- State: Admin fee $/kWh (or $/month - clarify with user)
- No attributes needed (static)

**Config Flow:**
- API key (password field)
- Admin fee (number, default 0)

---

## Future v2 Considerations

- LMP component breakdown (energy/congestion/loss)
- Day-ahead pricing sensor
- Demand response event detection
- Energy dashboard compatibility

---

*Generated: 2025-04-11*
