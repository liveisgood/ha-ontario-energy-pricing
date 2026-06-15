# Ontario Energy Pricing

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz/)
[![ha_version](https://img.shields.io/badge/Home%20Assistant-2024.1%2B-blue.svg)](https://www.home-assistant.io/)

Track real-time Ontario electricity rates in Home Assistant with smart scheduling for pool pumps, EV chargers, and HVAC. Fetches data directly from IESO (Independent Electricity System Operator) public feeds.

## ✨ Features

- **No API Key Required** - Uses public IESO data feeds
- **Zone-Aware LMP** - Maps your location to IESO zone (Oakville → TORONTO, London → SOUTHWEST, etc.)
- **Location Dropdown** - Select from 65 Ontario cities in config flow
- **Real-Time Updates** - LMP updates every 5 minutes
- **Smart Scheduling** - Binary sensors for cheapest hours, price thresholds, negative prices
- **Renewable Intelligence** - Solar/wind forecasts, fuel mix, carbon intensity
- **Automation Ready** - Binary sensors for pool pump, EV charger, AC, load shedding

> **Note:** This integration uses [LMP (Locational Marginal Pricing)](https://www.ieso.ca/power-market/market-renewal) which replaced the retired HOEP on May 1, 2025 under Ontario's Market Renewal Program.

---

## 🚀 Quick Start

### HACS (Recommended)

1. Open HACS → Integrations → ⋮ (menu) → Custom repositories
2. Add repository URL: `https://github.com/liveisgood/ha-ontario-energy-pricing`
3. Category: Integration
4. Install "Ontario Energy Pricing"
5. Restart Home Assistant

### Manual

1. Copy `custom_components/ontario_energy_pricing/` to your `config/custom_components/`
2. Restart Home Assistant

### Configuration

1. **Settings** → **Devices & Services** → **+ Add Integration**
3. Search "**Ontario Energy Pricing**"
4. **Select your location** from dropdown (65 Ontario cities mapped to IESO zones)
5. Enter **admin fee** from your retailer bill (¢/kWh, e.g., `1.45`)

---

## 📊 Sensors & Binary Sensors

### Price Sensors (¢/kWh)

| Entity | Description | Update |
|--------|-------------|--------|
| `sensor.ontario_energy_pricing_current_lmp` | Current 5-min LMP (your zone) | ~4.5 min |
| `sensor.ontario_energy_pricing_hour_average_lmp` | Hourly average LMP | ~4.5 min |
| `sensor.ontario_energy_pricing_global_adjustment` | Monthly GA rate | On change |
| `sensor.ontario_energy_pricing_total_rate` | **LMP + GA + Admin Fee** | ~4.5 min |

### Binary Sensors (Automation Triggers)

| Entity | Triggers ON When | Use Case |
|--------|------------------|----------|
| `binary_sensor.ontario_energy_pricing_cheapest_<name>` | Current hour in your cheapest N forecast hours | Pool pump, EV charger, AC pre-cool |
| `binary_sensor.ontario_energy_pricing_price_below_pool_pump` | Price < **5¢/kWh** | Run pool pump |
| `binary_sensor.ontario_energy_pricing_price_below_ac_precool` | Price < **10¢/kWh** | AC pre-cool allowed |
| `binary_sensor.ontario_energy_pricing_price_above_ac_setback` | Price > **20¢/kWh** | AC setback / let temp rise |
| `binary_sensor.ontario_energy_pricing_price_above_shed_all` | Price > **30¢/kWh** | Shed all discretionary loads |
| `binary_sensor.ontario_energy_pricing_price_negative` | **Price < 0¢/kWh** (get paid!) | Run everything, charge battery |
| `binary_sensor.ontario_energy_pricing_grid_stressed` | High gas + low renewable = sustained high prices | Avoid starting loads |

### Smart Forecast & Grid Sensors

| Entity | Description |
|--------|-------------|
| `sensor.ontario_energy_pricing_solar_forecast_mw` | Next 24h solar forecast (MW) |
| `sensor.ontario_energy_pricing_wind_forecast_mw` | Next 24h wind forecast (MW) |
| `sensor.ontario_energy_pricing_negative_price_probability` | Probability of negative prices |
| `sensor.ontario_energy_pricing_nuclear_mw` / `hydro_mw` / `wind_mw` / `solar_mw` / `gas_mw` | Real-time fuel mix (MW) |
| `sensor.ontario_energy_pricing_carbon_intensity` | Grid gCO₂/kWh (real-time) |
| `sensor.ontario_energy_pricing_renewable_percentage` | % zero-carbon generation |

---

## 💡 Automation Examples

### Pool Pump - Run During Cheapest Hours
```yaml
automation:
  - alias: "Pool Pump - Optimal Schedule"
    trigger:
      - platform: state
        entity_id: binary_sensor.ontario_energy_pricing_cheapest_pool_pump
        to: "on"
      - platform: state
        entity_id: binary_sensor.ontario_energy_pricing_price_negative
        to: "on"
    condition:
      - condition: or
        conditions:
          - condition: state
            entity_id: binary_sensor.ontario_energy_pricing_cheapest_pool_pump
            state: "on"
          - condition: state
            entity_id: binary_sensor.ontario_energy_pricing_price_negative
            state: "on"
      - condition: state
        entity_id: binary_sensor.ontario_energy_pricing_price_above_shed_all
        state: "off"
    action:
      - service: switch.turn_on
        target: entity_id: switch.pool_pump
```

### Pool Pump - Stop When Expensive
```yaml
automation:
  - alias: "Pool Pump - Avoid Peak Rates"
    trigger:
      - platform: state
        entity_id: binary_sensor.ontario_energy_pricing_price_above_shed_all
        to: "on"
      - platform: state
        entity_id: binary_sensor.ontario_energy_pricing_grid_stressed
        to: "on"
    action:
      - service: switch.turn_off
        target: entity_id: switch.pool_pump
```

### EV Charger - Charge When Cheap
```yaml
automation:
  - alias: "EV Charger - Smart Charging"
    trigger:
      - platform: state
        entity_id: binary_sensor.ontario_energy_pricing_price_below_pool_pump
        to: "on"
    condition:
      - condition: state
        entity_id: binary_sensor.ev_needs_charge
        state: "on"
    action:
      - service: switch.turn_on
        target: entity_id: switch.ev_charger
```

### AC Pre-cool Before Peak
```yaml
automation:
  - alias: "AC - Pre-cool Before Peak"
    trigger:
      - platform: state
        entity_id: binary_sensor.ontario_energy_pricing_price_below_ac_precool
        to: "on"
    condition:
      - condition: time
        after: "12:00"
        before: "18:00"
    action:
      - service: climate.set_temperature
        target: entity_id: climate.main_floor
        data:
          temperature: 20  # Overcool by 2°C
```

### AC Setback During Peak
```yaml
automation:
  - alias: "AC - Setback During Expensive Hours"
    trigger:
      - platform: state
        entity_id: binary_sensor.ontario_energy_pricing_price_above_ac_setback
        to: "on"
    action:
      - service: climate.set_temperature
        target: entity_id: climate.main_floor
        data:
          temperature: 24  # Let temp drift up
```

### Negative Price = Get Paid to Consume
```yaml
automation:
  - alias: "Negative Price - Run Everything"
    trigger:
      - platform: state
        entity_id: binary_sensor.ontario_energy_pricing_price_negative
        to: "on"
    action:
      - service: switch.turn_on
        target:
          - switch.pool_pump
          - switch.ev_charger
          - switch.water_heater
          - switch.battery_charge
```

---

## ⚙️ Configuration Options

After setup, go to **Settings → Devices & Services → Ontario Energy Pricing → Configure**:

- **Admin Fee** - Update retailer fee (¢/kWh)
- **Add Cheapest Window** - Create binary sensor for pool pump (16h), EV (8h), AC (4h), etc.
- **Remove Window** - Delete a sensor

Each "cheapest window" sensor:
- Turns ON during the N cheapest forecast hours (non-contiguous)
- Named: `Cheapest N Hours (Pool Pump)` → entity `binary_sensor.ontario_energy_pricing_cheapest_pool_pump`

---

## 🔌 Service

### Manual Refresh
```yaml
service: ontario_energy_pricing.refresh
```

---

## 🔬 Data Sources (All Public, No Auth)

| Feed | Purpose | URL |
|------|---------|-----|
| Realtime Zonal LMP | Your zone's 5-min LMP | `RealtimeZonalEnergyPrices` |
| Global Adjustment | Monthly GA rate | `GlobalAdjustment` |
| Predispatch | Today's 24h forecast | `PredispHourlyOntarioZonalPrice` |
| Day-Ahead | Tomorrow's 24h forecast | `DAHourlyOntarioZonalPrice` |
| VG Forecast | Solar/wind forecast | `VGForecastSummary` |
| Gen Output | Real-time fuel mix | `GenOutputbyFuelHourly` |

All published by [IESO](https://ieso.ca) - no API keys, no registration.

---

## 🗺️ Zone Mapping (Automatic)

Your selected city → IESO zone:
- **TORONTO**: Oakville, Toronto, Mississauga, Brampton, Hamilton, Burlington, etc.
- **SOUTHWEST**: London, Kitchener, Waterloo, Windsor, Guelph, etc.
- **OTTAWA**: Ottawa, Kanata, Orleans, Nepean, etc.
- **NIAGARA**: Niagara Falls, St. Catharines, Welland, etc.
- **EAST**: Kingston, Belleville, Peterborough, Cornwall
- **ESSA**: Barrie, Orillia, Collingwood, Midland
- **NORTHEAST**: Sudbury, North Bay, Timmins, Sault Ste. Marie
- **NORTHWEST**: Thunder Bay, Kenora, Dryden
- **WEST**: Owen Sound, Blue Mountains, Meaford

Unknown locations default to TORONTO with a warning.

---

## 🔧 Troubleshooting

| Issue | Solution |
|-------|----------|
| Sensors "unavailable" | Check HA logs for IESO network errors; feeds update every 5 min |
| GA "unknown" | IESO publishes monthly; retains previous month up to 7 days |
| Rate seems wrong | Verify admin fee matches your bill; compare LMP at [IESO Market Data](https://www.ieso.ca/market-data) |
| Binary sensor never ON | Check forecast availability in sensor attributes; forecast may not be published yet |

---

## 📦 Installation Files

```
custom_components/ontario_energy_pricing/
├── __init__.py          # Integration entry point
├── config_flow.py       # Setup + options flow (location dropdown, cheapest windows)
├── const.py             # Constants, zone mapping, location options
├── coordinator.py       # Data coordinator (LMP, GA, forecast, VG, fuel mix)
├── sensor.py            # 4 price sensors
├── binary_sensor.py     # 7+ binary sensors (cheapest, thresholds, grid)
├── ieso_lmp.py          # Zone-aware LMP client
├── ieso_ga.py           # Global Adjustment client
├── ieso_predispatch.py  # Forecast client
├── ieso_vg_forecast.py  # Solar/wind forecast client
├── ieso_gen_output.py   # Fuel mix client
├── models.py            # Data models (VG forecast, fuel mix, thresholds)
├── exceptions.py        # Custom exceptions
├── strings.json         # UI strings
├── translations/en.json # English translations
├── manifest.json        # HA manifest
├── services.yaml        # Refresh service
└── diagnostics.py       # HA diagnostics support
```

---

## 🧪 Testing

```bash
# Run unit tests
python3 tests/test_const.py    # Location → zone mapping (7 tests)
python3 tests/test_models.py   # Data models (8 tests)
```

Tests cover:
- Location normalization (Toronto/London/Hamilton bug regression)
- Zone mapping for 65 Ontario cities
- VG forecast probability calculations
- Fuel mix carbon intensity
- Price threshold logic

---

## 🤝 Contributing

1. Fork the repo
2. Create feature branch
3. Add tests for new logic
4. Ensure `python3 -m py_compile` and tests pass
5. Submit PR

---

## 📜 License

MIT License - see [LICENSE](LICENSE)

---

## 🙏 Credits

- Data provided by [IESO](https://ieso.ca)
- Built for Ontario homeowners wanting smarter energy costs