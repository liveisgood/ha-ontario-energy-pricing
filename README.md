# Ontario Energy Pricing

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz/)
[![ha_version](https://img.shields.io/badge/Home%20Assistant-2024.1%2B-blue.svg)](https://www.home-assistant.io/)

Track real-time Ontario electricity rates in Home Assistant. Fetches data directly from IESO (Independent Electricity System Operator) public feeds.

## Features

- ✓ **No API Key Required** - Uses public IESO data feeds
- ✓ **Real-Time Updates** - LMP updates every 5 minutes
- ✓ **Current LMP** - Locational Marginal Price from [IESO](https://ieso.ca) (real-time)
- ✓ **Hour Average LMP** - Hourly average of 5-minute intervals
- ✓ **Global Adjustment** - Monthly rate component from IESO
- ✓ **Total Rate** - Combined calculation (LMP + GA + Admin Fee)

> **Note:** This integration uses [LMP (Locational Marginal Pricing)](https://www.ieso.ca/power-market/market-renewal) which replaced the retired HOEP on May 1, 2025 under Ontario's Market Renewal Program.

## How It Works

The integration fetches live electricity pricing data directly from IESO:

1. **LMP** - Real-time 5-minute Ontario zonal price from IESO's public XML feed
2. **Global Adjustment** - Monthly rate from IESO's GA publication
3. **Calculates** your total rate: LMP + GA + Admin Fee

All data is fetched directly from IESO - no third-party APIs, no authentication required.

## Installation

### HACS (Recommended)

1. Open HACS → Integrations → ⋮ (menu) → Custom repositories
2. Add repository URL: `https://github.com/lobstah/ha-ontario-energy-pricing`
3. Category: Integration
4. Install "Ontario Energy Pricing"
5. Restart Home Assistant

### Manual

1. Copy the `custom_components/ontario_energy_pricing/` folder to your Home Assistant `config/custom_components/` directory
2. Restart Home Assistant

## Configuration

1. Go to **Settings** → **Devices & Services**
2. Click **+ Add Integration**
3. Search for "**Ontario Energy Pricing**"
4. Enter your **location** (e.g., "Oakville, ON" or "Toronto")
5. Enter your **admin fee** from your electricity retailer (¢/kWh, e.g., 1.45 for 1.45¢/kWh)

**That's it!** No API key, no zone selection - the integration fetches the Ontario zonal price automatically.

## Sensors

The integration creates the following entities:

| Entity | Description | Unit | Update Frequency |
|--------|-------------|------|------------------|
| `sensor.ontario_energy_pricing_current_lmp` | Current LMP (latest interval) | ¢/kWh | ~4.5 minutes |
| `sensor.ontario_energy_pricing_hour_average_lmp` | Hour average LMP | ¢/kWh | ~4.5 minutes |
| `sensor.ontario_energy_pricing_global_adjustment` | Global Adjustment rate | c/kWh | Weekly (check for new month) |
| `sensor.ontario_energy_pricing_total_rate` | Total combined rate | c/kWh | ~4.5 minutes |

### Total Rate Calculation

```
Total Rate (¢/kWh) = Current LMP + Global Adjustment + Admin Fee
```

**Example:**
- Current LMP: 5.20 ¢/kWh
- Global Adjustment: 6.00 ¢/kWh
- Admin Fee: 1.45 ¢/kWh
- **Total Rate: 12.65 ¢/kWh ($0.1265/kWh)**

## Automation Examples

### High Rate Alert

Send a notification when electricity price exceeds 15¢/kWh:

```yaml
automation:
  - alias: "High electricity rate alert"
    trigger:
      - platform: numeric_state
        entity_id: sensor.ontario_energy_pricing_total_rate
        above: 15
    action:
      - service: notify.notify
        data:
          message: "⚡ Electricity rate is now {{ trigger.to_state.state }}¢/kWh! Consider delaying high-power usage."
```

### Run Dishwasher During Low Rates

Start the dishwasher only when the rate drops below 8¢/kWh:

```yaml
automation:
  - alias: "Run dishwasher when rates are low"
    trigger:
      - platform: numeric_state
        entity_id: sensor.ontario_energy_pricing_total_rate
        below: 8
    condition:
      - condition: state
        entity_id: binary_sensor.dishwasher_needs_run
        state: "on"
    action:
      - service: switch.turn_on
        target:
          entity_id: switch.dishwasher
      - service: notify.notify
        data:
          message: "🍽️ Dishwasher started - low electricity rate!"
```

## Service

### Refresh

Manually refresh all sensor data:

**Service:** `ontario_energy_pricing.refresh`

**Parameters:** None

**Example:**

```yaml
service: ontario_energy_pricing.refresh
```

## Data Sources

- **LMP Data:** [IESO Real-Time Ontario Zonal Price](https://reports-public.ieso.ca/public/RealtimeOntarioZonalPrice/) (public XML feed)
- **Global Adjustment:** [IESO Global Adjustment](http://reports.ieso.ca/public/GlobalAdjustment/)

Both feeds are published by IESO and are freely available without authentication.

## Configuration Options

After initial setup, you can reconfigure:

- **Admin Fee** - Update your retailer fee anytime

Go to **Settings** → **Devices & Services** → **Ontario Energy Pricing** → **Configure**.

## Troubleshooting

### "Sensor unavailable"

- Check that your Home Assistant can reach IESO servers
- Check **Home Assistant logs** for network errors
- IESO feeds update every 5 minutes; temporary network issues will recover

### "Global Adjustment sensor showing 'unknown'"

- IESO Global Adjustment XML is published monthly; during the first week of a new month, data may be temporarily unavailable
- The integration retains the previous month's value for up to 7 days

### Rate seems incorrect

- Verify your **Admin Fee** matches your electricity bill
- Compare LMP values with [IESO's Market Data](https://www.ieso.ca/market-data)

## Support

- [Issues](https://github.com/lobstah/ha-ontario-energy-pricing/issues)

## Credits

- Data provided by [IESO](https://ieso.ca) 
- Built with ❤️ for Ontario homeowners

## License

MIT License - see [LICENSE](LICENSE) file
