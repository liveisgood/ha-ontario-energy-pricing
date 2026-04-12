# Ontario Energy Pricing

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz/)
[![ha_version](https://img.shields.io/badge/Home%20Assistant-2024.1%2B-blue.svg)](https://www.home-assistant.io/)

Track real-time Ontario electricity rates in Home Assistant.

## Features

- **Current LMP** - Locational Marginal Price from [GridStatus.io](https://gridstatus.io) (real-time, hourly updates)
- **24-Hour Average LMP** - Daily average computed from 30-minute interval data
- **Global Adjustment** - Monthly rate component from [IESO](https://ieso.ca)
- **Total Rate** - Combined calculation (LMP + GA + Admin Fee)
- **Automatic Zone Discovery** - Finds your electricity zone from location input

> **Note:** This integration uses [LMP (Locational Marginal Pricing)](https://www.ieso.ca/power-market/market-renewal) which replaced the retired HOEP on May 1, 2025 under Ontario's Market Renewal Program.

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
4. Enter your **[GridStatus API key](https://gridstatus.io/)**
5. Enter your **location** (e.g., "Oakville, ON" or "Toronto")
6. Select your **electricity zone** (or use "ONTARIO" for province-wide average)
7. Enter your **admin fee** from your electricity retailer ($/kWh)

## Sensors

The integration creates the following entities:

| Entity | Description | Unit | Update Frequency |
|--------|-------------|------|------------------|
| `sensor.ontario_energy_pricing_current_lmp` | Current Locational Marginal Price | CAD/kWh | Hourly |
| `sensor.ontario_energy_pricing_lmp_24h_average` | 24-hour rolling average | CAD/kWh | Daily at midnight |
| `sensor.ontario_energy_pricing_global_adjustment` | Global Adjustment rate | CAD/kWh | Monthly (IESO publication) |
| `sensor.ontario_energy_pricing_total_rate` | Total combined rate | CAD/kWh | Hourly (follows LMP) |

### Total Rate Calculation

```
Total Rate = Current LMP + Global Adjustment + Admin Fee
```

**Example:**
- Current LMP: $0.08/kWh
- Global Adjustment: $0.05/kWh  
- Admin Fee: $0.02/kWh
- **Total Rate: $0.15/kWh**

## Automation Examples

### High Rate Alert

Send a notification when electricity price exceeds $0.15/kWh:

```yaml
automation:
  - alias: "High electricity rate alert"
    trigger:
      - platform: numeric_state
        entity_id: sensor.ontario_energy_pricing_total_rate
        above: 0.15
    action:
      - service: notify.notify
        data:
          message: "⚡ Electricity rate is now ${{ trigger.to_state.state }}/kWh! Consider delaying high-power usage."
```

### Run Dishwasher During Low Rates

Start the dishwasher only when the rate drops below $0.06/kWh:

```yaml
automation:
  - alias: "Run dishwasher when rates are low"
    trigger:
      - platform: numeric_state
        entity_id: sensor.ontario_energy_pricing_total_rate
        below: 0.06
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

Useful for testing or forcing an immediate update outside of the normal schedule.

## Screenshots

<!-- TODO: Add screenshots of:
- Configuration flow
- Dashboard card with 4 sensors
- History graph showing rate changes
-->

## Troubleshooting

### "Sensor unavailable"
- Verify your **GridStatus API key** is valid at [gridstatus.io](https://gridstatus.io)
- Check that your **location** was recognized and a zone was selected
- Check **Home Assistant logs** for API errors

### "Global Adjustment sensor showing 'unknown'"
- IESO Global Adjustment XML is published monthly; during the first week of a new month, data may be temporarily unavailable
- The integration retains the previous month's value for up to 7 days

### Rate seems incorrect
- Verify your **Admin Fee** matches your electricity bill
- Check that the correct **Zone** is selected for your location

## Data Sources

- **LMP Data:** [GridStatus.io API](https://gridstatus.io) (requires free API key)
- **Global Adjustment:** [IESO Public Reports](http://reports.ieso.ca/public/GlobalAdjustment/)

## Configuration Options

After initial setup, you can reconfigure:
- **Admin Fee** - Update your retailer fee anytime
- **Zone** - Change electricity zone if you move

Go to **Settings** → **Devices & Services** → **Ontario Energy Pricing** → **Configure**.

## Support

- [Home Assistant Community Forum](link) (coming soon)
- [Issues](https://github.com/lobstah/ha-ontario-energy-pricing/issues)

## Credits

- Data provided by [GridStatus.io](https://gridstatus.io) and [IESO](https://ieso.ca)
- Built with ❤️ for Ontario homeowners

## License

MIT License - see [LICENSE](LICENSE) file
