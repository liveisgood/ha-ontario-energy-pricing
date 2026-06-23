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
- **Grid Intelligence** - Outage risk, congestion pricing, intertie arbitrage, demand anomaly sensors

> **Note:** This integration uses [LMP (Locational Marginal Pricing)](https://www.ieso.ca/power-market/market-renewal) which replaced the retired HOEP on May 1, 2025 under Ontario's Market Renewal Program.

## 🚀 Quick Start

### HACS (Recommended)
1. Open HACS → Integrations → ⋮ (menu) → Custom repositories
2. Add repo URL: `https://github.com/liveisgood/ha-ontario-energy-pricing`
3. Category: Integration
4. Install "Ontario Energy Pricing"
5. Restart Home Assistant

### Manual
1. Copy `custom_components/ontario_energy_pricing/` to your `config/custom_components/`
2. Restart Home Assistant

### Configure
1. **Settings** → **Devices & Services** → **+ Add Integration**
2. Search "**Ontario Energy Pricing**"
3. **Select your location** from dropdown (65 Ontario cities mapped to IESO zones)
4. Enter **admin fee** from your retailer bill (¢/kWh, e.g., `1.45`)

## 📊 Sensors & Binary Sensors (35 Total)

### Core Price Sensors (¢/kWh)
| Entity | Description | Update |
|--------|-------------|--------|
| `sensor.ontario_energy_pricing_current_lmp` | Current 5-min LMP (your zone) | ~4.5 min |
| `sensor.ontario_energy_pricing_hour_average_lmp` | Hourly average LMP | ~4.5 min |
| `sensor.ontario_energy_pricing_global_adjustment` | Monthly GA rate | On change |
| `sensor.ontario_energy_pricing_total_rate` | **LMP + GA + Admin Fee** | ~4.5 min |

### Fuel Mix Sensors (Real-time Generation)
| Entity | Description | Unit |
|--------|-------------|------|
| `sensor.ontario_energy_pricing_fuel_mix_nuclear` | Nuclear generation | MW |
| `sensor.ontario_energy_pricing_fuel_mix_hydro` | Hydro generation | MW |
| `sensor.ontario_energy_pricing_fuel_mix_wind` | Wind generation | MW |
| `sensor.ontario_energy_pricing_fuel_mix_solar` | Solar generation | MW |
| `sensor.ontario_energy_pricing_fuel_mix_gas` | Gas generation | MW |
| `sensor.ontario_energy_pricing_fuel_mix_biofuel` | Biofuel generation | MW |
| `sensor.ontario_energy_pricing_fuel_mix_other` | Other generation | MW |
| `sensor.ontario_energy_pricing_fuel_mix_total` | Total generation | MW |
| `sensor.ontario_energy_pricing_fuel_mix_renewable_percent` | Renewable % | % |
| `sensor.ontario_energy_pricing_fuel_mix_carbon_intensity` | Grid carbon intensity | gCO₂/kWh |

### Shadow Prices (Congestion Costs)
| Entity | Description | Unit |
|--------|-------------|------|
| `sensor.ontario_energy_pricing_shadow_price_max` | Max shadow price (current hour) | $/MWh |
| `sensor.ontario_energy_pricing_shadow_price_binding_constraints` | Count of binding constraints | count |

### Intertie LMPs (Interchange Prices)
| Entity | Description | Unit |
|--------|-------------|------|
| `sensor.ontario_energy_pricing_intertie_lmp_michigan` | Michigan intertie LMP | $/MWh |
| `sensor.ontario_energy_pricing_intertie_lmp_new_york` | New York intertie LMP | $/MWh |
| `sensor.ontario_energy_pricing_intertie_lmp_quebec` | Quebec intertie LMP | $/MWh |
| `sensor.ontario_energy_pricing_intertie_lmp_manitoba` | Manitoba intertie LMP | $/MWh |
| `sensor.ontario_energy_pricing_intertie_lmp_minnesota` | Minnesota intertie LMP | $/MWh |

### Reserve Prices (Operating Reserves)
| Entity | Description | Unit |
|--------|-------------|------|
| `sensor.ontario_energy_pricing_reserve_price_10s` | 10-min spinning reserve | $/MWh |
| `sensor.ontario_energy_pricing_reserve_price_10n` | 10-min non-spinning reserve | $/MWh |
| `sensor.ontario_energy_pricing_reserve_price_30r` | 30-min operating reserve | $/MWh |

### Transmission Outages
| Entity | Description | Unit |
|--------|-------------|------|
| `sensor.ontario_energy_pricing_tx_outages_count` | Active outages count | count |
| `sensor.ontario_energy_pricing_tx_outages_capacity_impact` | Total capacity impact | MW |

### Demand Zonal
| Entity | Description | Unit |
|--------|-------------|------|
| `sensor.ontario_energy_pricing_demand_zonal_total` | Total Ontario demand | MW |
| `sensor.ontario_energy_pricing_demand_zonal_toronto` | Toronto zone demand | MW |
| `sensor.ontario_energy_pricing_demand_zonal_ottawa` | Ottawa zone demand | MW |

### VG Forecast (Variable Generation)
| Entity | Description | Unit |
|--------|-------------|------|
| `sensor.ontario_energy_pricing_vg_forecast_solar` | Solar forecast (current hour) | MW |
| `sensor.ontario_energy_pricing_vg_forecast_wind` | Wind forecast (current hour) | MW |
| `sensor.ontario_energy_pricing_vg_forecast_total` | Total VG forecast | MW |

### Binary Sensors (Automation Triggers)
| Entity | Triggers ON When | Use Case |
|--------|------------------|----------|
| `binary_sensor.ontario_energy_pricing_cheapest_<name>` | Current hour in your cheapest N forecast hours | Pool pump, EV charger, AC pre-cool |
| `binary_sensor.ontario_energy_pricing_price_negative` | **Price < 0¢/kWh** (get paid!) | Run everything, charge battery |
| `binary_sensor.ontario_energy_pricing_grid_stressed` | High gas + low renewable = sustained high prices | Avoid starting loads |
| `binary_sensor.ontario_energy_pricing_outage_risk` | High transmission outage capacity or count | Delay non-critical loads |
| `binary_sensor.ontario_energy_pricing_congestion` | High shadow prices = transmission constraints | Shift flexible loads |
| `binary_sensor.ontario_energy_pricing_intertie_arbitrage` | Large price spread between interties | Export/import power opportunities |
| `binary_sensor.ontario_energy_pricing_demand_anomaly` | Unexpected demand surge | Pre-cool/pre-heat before peak |

> **Note:** For price thresholds (e.g., "run pool when < 5¢"), use `sensor.ontario_energy_pricing_total_rate` with `numeric_state` triggers in your automations — no dedicated sensors needed.

## 🔥 Fuel Mix Dashboard (ApexCharts)

Create a beautiful real-time fuel mix chart using the ApexCharts card:

```yaml
type: custom:apexcharts-card
header:
  show: true
  title: "Ontario Grid Fuel Mix (Real-time)"
  show_states: true
  colorize_states: true
  - entity: sensor.ontario_energy_pricing_fuel_mix_nuclear
    name: Nuclear
    type: area
    color: "#1f77b4"
  - entity: sensor.ontario_energy_pricing_fuel_mix_hydro
    name: Hydro
    color: "#2ca02c"
  - entity: sensor.ontario_energy_pricing_fuel_mix_wind
    name: Wind
    color: "#8c564b"
  - entity: sensor.ontario_energy_pricing_fuel_mix_solar
    name: Solar
    color: "#ff7f0e"
  - entity: sensor.ontario_energy_pricing_fuel_mix_gas
    name: Gas
    color: "#d62728"
  - entity: sensor.ontario_energy_pricing_fuel_mix_biofuel
    name: Biofuel
    color: "#9467bd"
group_by: stack
start: day
```

**Carbon Intensity Gauge:**
```yaml
type: custom:apexcharts-card
header:
  show: true
  title: "Grid Carbon Intensity"
  show_states: true
  - entity: sensor.ontario_energy_pricing_fuel_mix_carbon_intensity
    name: gCO₂/kWh
    type: radialBar
    color: "#d62728"
      val: true
      name: true
```

**Renewable Percentage:**
```yaml
type: custom:apexcharts-card
header:
  show: true
  title: "Renewable Energy %"
  show_states: true
  - entity: sensor.ontario_energy_pricing_fuel_mix_renewable_percent
    name: Renewable %
    type: radialBar
    color: "#2ca02c"
```

## 💡 Automation Examples

### Pool Pump - Run During Cheapest Hours
```yaml
- alias: "Pool Pump - Optimal Schedule"
  trigger:
    - platform: state
      entity_id: binary_sensor.ontario_energy_pricing_cheapest_pool_pump
      to: "on"
    - platform: state
      entity_id: binary_sensor.ontario_energy_pricing_price_negative
      to: "on"
  condition: or
    - condition: state
      entity_id: binary_sensor.ontario_energy_pricing_cheapest_pool_pump
      state: "on"
    - condition: state
      entity_id: binary_sensor.ontario_energy_pricing_price_negative
      state: "on"
    - condition: numeric_state
      entity_id: sensor.ontario_energy_pricing_total_rate
      below: 30
  action:
    - service: switch.turn_on
      target: entity_id: switch.pool_pump
```

### Pool Pump - Stop When Expensive
```yaml
- alias: "Pool Pump - Avoid Peak Rates"
  trigger:
    - platform: numeric_state
      entity_id: sensor.ontario_energy_pricing_total_rate
      above: 30
  action:
    - service: switch.turn_off
      target: entity_id: switch.pool_pump
```

### EV Charger - Charge When Cheap
```yaml
- alias: "EV Charger - Smart Charging"
  trigger:
    - platform: numeric_state
      entity_id: sensor.ontario_energy_pricing_total_rate
      below: 5
    - condition: state
      entity_id: binary_sensor.ev_needs_charge
      state: "on"
  action:
    - service: switch.turn_on
      target: entity_id: switch.ev_charger
```

### AC Pre-cool Before Peak
```yaml
- alias: "AC - Pre-cool Before Peak"
  trigger:
    - platform: numeric_state
      entity_id: sensor.ontario_energy_pricing_total_rate
      below: 10
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
- alias: "AC - Setback During Expensive Hours"
  trigger:
    - platform: numeric_state
      entity_id: sensor.ontario_energy_pricing_total_rate
      above: 20
  action:
    - service: climate.set_temperature
      target: entity_id: climate.main_floor
      data:
        temperature: 24  # Let temp drift up
```

### Negative Price = Get Paid to Consume
```yaml
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

### Outage Risk - Delay Non-Essential Loads
```yaml
- alias: "Delay Loads During High Outage Risk"
  trigger:
    - platform: state
      entity_id: binary_sensor.ontario_energy_pricing_outage_risk
      to: "on"
  action:
    - service: input_boolean.turn_on
      target: entity_id: input_boolean.outage_risk_mode
    - wait_for_trigger:
        - platform: state
          entity_id: binary_sensor.ontario_energy_pricing_outage_risk
          to: "off"
        timeout: "06:00:00"
      then:
        - service: input_boolean.turn_off
          target: entity_id: input_boolean.outage_risk_mode
```

### Congestion Pricing - Shift Flexible Loads
```yaml
- alias: "Shift Load During Congestion Pricing"
  trigger:
    - platform: state
      entity_id: binary_sensor.ontario_energy_pricing_congestion
      to: "on"
  action:
    - service: climate.set_temperature
      data:
        temperature: "{{ (states('input_heater_temp') | float) - 2 }}"
      target:
        entity_id: climate.main_heater
    - wait_for_trigger:
        - platform: state
          entity_id: binary_sensor.ontario_energy_pricing_congestion
          to: "off"
        timeout: "04:00:00"
      then:
        - service: climate.set_temperature
          data:
            temperature: "{{ states('input_heater_temp') | float }}"
          target:
            entity_id: climate.main_heater
```

### Intertie Arbitrage - Export Power When Profitable
```yaml
- alias: "Export Power During Intertie Arbitrage"
  trigger:
    - platform: state
      entity_id: binary_sensor.ontario_energy_pricing_intertie_arbitrage
      to: "on"
  action:
    - service: switch.turn_on
      target: entity_id: switch.battery_export_mode
    - wait_for_trigger:
        - platform: state
          entity_id: binary_sensor.ontario_energy_pricing_intertie_arbitrage
          to: "off"
        timeout: "03:00:00"
      then:
        - service: switch.turn_off
          target: entity_id: switch.battery_export_mode
```

### Demand Anomaly - Pre-cool Before Unexpected Demand Surge
```yaml
- alias: "Pre-cool Before Demand Anomaly"
  trigger:
    - platform: state
      entity_id: binary_sensor.ontario_energy_pricing_demand_anomaly
      to: "on"
  action:
    - service: climate.set_temperature
      target:
        entity_id: climate.main_floor
        temperature: 18  # Pre-cool by 4°C
    - delay: "01:00:00"
    - action:
        - service: climate.set_temperature
          target:
            entity_id: climate.main_floor
            temperature: 22  # Return to normal
```

## ⚙️ Config Options

After setup, go to **Settings → Devices & Services → Ontario Energy Pricing → Configure**:
- **Admin Fee** - Update retailer fee (¢/kWh)
- **Add Cheapest Window** - Create binary sensor for pool pump (16h), EV (8h), AC (4h), etc.
- **Remove Window** - Delete a sensor

Each "cheapest window" sensor:
- Turns ON during the N cheapest forecast hours (non-contiguous)
- Named: `Cheapest N Hours (Pool Pump)` → entity `binary_sensor.ontario_energy_pricing_cheapest_pool_pump`

## 🔌 Service

### Manual Refresh
```yaml
service: ontario_energy_pricing.refresh
```

## 🔬 Data Sources (All Public, No Auth)

| Feed | Purpose | IESO Feed |
|------|---------|-----------|
| Realtime Zonal LMP | Your zone's 5-min LMP | `RealtimeZonalEnergyPrices` |
| Global Adjustment | Monthly GA rate | `GlobalAdjustment` |
| Predispatch | Today's 24h forecast | `PredispHourlyOntarioZonalPrice` |
| Day-Ahead | Tomorrow's 24h forecast | `DAHourlyOntarioZonalPrice` |
| VG Forecast | Solar/wind forecast | `VGForecastSummary` |
| Gen Output | Real-time fuel mix | `GenOutputbyFuelHourly` |
| Shadow Prices | Transmission constraint shadow prices | `RealtimeConstrShadowPrices` |
| Tx Outages | Today's transmission outages | `TxOutagesTodayAll` |
| Demand Zonal | 5-min demand by zone | `RealtimeDemandZonal` |
| Intertie LMP | Real-time interchange LMP prices | `RealtimeIntertieLMP` |
| Reserve Prices | Operating reserve LMP prices | `RealtimeORLMP` |

All published by [IESO](https://ieso.ca) - no API keys, no registration.

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

## 🔧 Troubleshooting

| Issue | Solution |
|-------|----------|
| Sensors "unavailable" | Check HA logs for IESO network errors; feeds update every 5 min |
| GA "unknown" | IESO publishes monthly; retains prev month up to 7 days |
| Rate seems wrong | Verify admin fee matches your bill; compare LMP at [IESO Market Data](https://www.ieso.ca/market-data) |
| Binary sensor never ON | Check forecast availability in sensor attributes; forecast may not be published yet |

## 📦 Installation Files

```
custom_components/ontario_energy_pricing/
├── __init__.py              # Integration entry point
├── config_flow.py           # Setup + options flow (location dropdown, cheapest windows)
├── const.py                 # Constants, zone mapping, location options
├── coordinator.py           # Data coordinator (all IESO feeds)
├── sensor.py                # 35 sensors (4 core + 31 new)
├── binary_sensor.py         # 7 binary sensors
├── ieso_lmp.py              # Zone-aware LMP client
├── ieso_ga.py               # Global Adjustment client
├── ieso_predispatch.py      # Forecast client
├── ieso_vg_forecast.py      # Solar/wind forecast client
├── ieso_gen_output.py       # Fuel mix client
├── ieso_shadow_prices.py    # Shadow prices client
├── ieso_tx_outages.py       # Tx outages client
├── ieso_demand_zonal.py     # Demand zonal client
├── ieso_intertie_lmp.py     # Intertie LMP client
├── ieso_reserves.py         # Reserve prices client
├── models.py                # Data models (VG forecast, fuel mix, thresholds)
├── exceptions.py            # Custom exceptions
├── strings.json             # UI strings
├── translations/en.json     # English translations
├── manifest.json            # HA manifest
├── services.yaml            # Refresh service
└── diagnostics.py           # HA diagnostics support
```

## 🧪 Testing

```bash
# Run unit tests
python3 -m pytest tests/test_sensor.py tests/test_ieso_lmp.py tests/test_binary_sensors.py tests/test_shadow_prices.py tests/test_tx_outages.py tests/test_demand_zonal.py tests/test_models.py tests/test_const.py -v
```

Tests cover (76 tests passing):
- Location normalization (Toronto/London/Hamilton bug regression)
- Zone mapping for 65 Ontario cities
- VG forecast probability calculations
- Fuel mix carbon intensity
- Price threshold logic
- Binary sensor logic for all sensor types
- New client parsing and data structures

## 🤝 Contributing

1. Fork the repo
2. Create feature branch
3. Add tests for new logic
4. Ensure `python3 -m pytest` passes
5. Submit PR

## 📜 License

MIT License - see [LICENSE]

## 🙏 Credits

- Data provided by [IESO](https://ieso.ca)
- Built for Ontario homeowners wanting smarter energy costs