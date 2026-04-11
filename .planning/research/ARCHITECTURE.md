# Architecture Research: Ontario Energy Pricing HACS Integration

**Research Date:** 2025-04-11
**Researcher:** Claude Code

---

## 1. High-Level Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Home Assistant Core                       │
│  ┌───────────────────────────────────────────────────────┐  │
│  │         Ontario Energy Pricing Integration             │  │
│  │                                                        │  │
│  │   ┌──────────────────────────────────────────────┐    │  │
│  │   │          config_flow.py (Config Flow)         │    │  │
│  │   │   - API key validation                        │    │  │
│  │   │   - Admin fee input                           │    │  │
│  │   └──────────────────────────────────────────────┘    │  │
│  │                                                        │  │
│  │   ┌──────────────────────────────────────────────┐    │  │
│  │   │            coordinator.py                      │    │  │
│  │   │                                              │    │  │
│  │   │  ┌───────────────────────────────┐          │    │  │
│  │   │  │ LMP Coordinator (Hourly)     │          │    │  │
│  │   │  │ - Polls GridStatus API       │          │    │  │
│  │   │  │ - Caches last hour price     │          │    │  │
│  │   │  └───────────────────────────────┘          │    │  │
│  │   │                                              │    │  │
│  │   │  ┌───────────────────────────────┐          │    │  │
│  │   │  │ GA Coordinator (Weekly)      │          │    │  │
│  │   │  │ - Polls IESO XML             │          │    │  │
│  │   │  │ - Checks once per week       │          │    │  │
│  │   │  └───────────────────────────────┘          │    │  │
│  │   │                                              │    │  │
│  │   │  ┌───────────────────────────────┐          │    │  │
│  │   │  │ Admin Fee (Static)             │          │    │  │
│  │   │  │ - Reads from config entry    │          │    │  │
│  │   │  │ - No polling needed          │          │    │  │
│  │   │  └───────────────────────────────┘          │    │  │
│  │   └──────────────────────────────────────────────┘    │  │
│  │                                                        │  │
│  │   ┌──────────────────────────────────────────────┐    │  │
│  │   │           sensor.py (Platform)             │    │  │
│  │   │   - OntariolmpPriceSensor                   │    │  │
│  │   │   - OntarioGlobalAdjustmentSensor           │    │  │
│  │   │   - OntarioAdminFeeSensor                   │    │  │
│  │   └──────────────────────────────────────────────┘    │  │
│  │                                                        │  │
│  │   ┌──────────────────────────────────────────────┐    │  │
│  │   │           __init__.py (Component)          │    │  │
│  │   │   - async_setup_entry                      │    │  │
│  │   │   - Forward to sensor platform             │    │  │
│  │   └──────────────────────────────────────────────┘    │  │
│  └────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ HTTPS
                              ▼
┌─────────────────┐    ╔═══════════════╗    ┌─────────────────────┐
│   GridStatus    │◄──►║  Some public  ║◄──►│   IESO Public       │
│     API         │    ╚═══════════════╝    │   XML Reports       │
└─────────────────┘                         └─────────────────────┘
   api.gridstatus.io                            reports.ieso.ca
```

---

## 2. Class Structure

### Data Models

```python
@dataclass
class LMPCurrentPrice:
    """LMP price data for current hour."""
    price: float              # $/kWh
    timestamp: datetime       # Interval start time (TZ-aware)
    previous_price: float     # Previous hour $/kWh
    zone: str                 # e.g., "ONTARIO"

@dataclass
class GlobalAdjustmentRate:
    """Global Adjustment data from IESO XML."""
    rate: float               # $/kWh
    trade_month: str          # "YYYY-MM"
    last_updated: datetime    # When we last checked the XML

@dataclass
class AdminFeeConfig:
    """User-configured admin fee."""
    rate: float               # $/kWh (or $/month if fee is monthly)
```

### Coordinator Classes

```python
class LMPCoordinator(DataUpdateCoordinator):
    """Coordinator for LMP price updates."""
    
    def __init__(self, hass, api_key, zone="ONTARIO"):
        self._api_key = api_key
        self._zone = zone
        super().__init__(
            hass,
            LOGGER,
            name="LMP Coordinator",
            update_interval=timedelta(hours=1),
        )
    
    async def _async_update_data(self) -> LMPCurrentPrice:
        # Fetch from GridStatus API
        # Filter for zone
        # Return structured data

class GlobalAdjustmentCoordinator(DataUpdateCoordinator):
    """Coordinator for GA updates."""
    
    def __init__(self, hass):
        super().__init__(
            hass,
            LOGGER,
            name="GA Coordinator",
            update_interval=timedelta(weeks=1),
        )
    
    async def _async_update_data(self) -> GlobalAdjustmentRate:
        # Fetch IESO XML
        # Parse with ElementTree
        # Return structured data
```

### Sensor Classes

```python
class OntariolmpPriceSensor(CoordinatorEntity):
    """Sensor for current LMP price."""
    
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = "/kWh"
    _attr_state_class = SensorStateClass.MEASUREMENT
    
    @property
    def native_value(self):
        return self.coordinator.data.price
    
    @property
    def extra_state_attributes(self):
        return {
            "timestamp": self.coordinator.data.timestamp.isoformat(),
            "previous_rate": self.coordinator.data.previous_price,
            "zone": self.coordinator.data.zone,
        }

class OntarioGlobalAdjustmentSensor(CoordinatorEntity):
    """Sensor for Global Adjustment."""
    
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = "/kWh"
    _attr_state_class = SensorStateClass.MEASUREMENT

class OntarioAdminFeeSensor(SensorEntity):
    """Static sensor for admin fee (no coordinator)."""
    
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = "/kWh"
    _attr_state_class = SensorStateClass.MEASUREMENT
```

---

## 3. Data Flow

### Setup Flow
```
User initiates config flow
    │
    ▼
Enter API key + Admin fee
    │
    ▼
Validate API key (test call to GridStatus)
    │
    ▼
Create config entry
    │
    ▼
Setup entry called
    │
    ├──► Create LMPCoordinator
    │    ├──► Initial fetch (current hour)
    │    └──► Cache result
    │
    ├──► Create GlobalAdjustmentCoordinator
    │    ├──► Initial fetch (XML)
    │    └──► Cache result
    │
    └──► Forward to sensor platform
              ├──► Create LMP Sensor
              ├──► Create GA Sensor
              └──► Create Admin Fee Sensor
```

### Update Flow (LMP)
```
Hourly timer fires
    │
    ▼
Coordinator._async_update_data()
    │
    ├──► HTTP GET to api.gridstatus.io/v1/datasets/ieso_lmp_real_time_5_min_all
    │    Query: start=current_hour, end=current_hour, timezone=US/Eastern
    │
    ▼
Parse JSON response
    │
    ├─► Filter for zone (e.g., "ONTARIO")
    ├─► Check if current interval
    ├─► Cache previous hour price
    └─► Store new price
    │
    ▼
Update sensor state
    │
    ▼
Notify Home Assistant
```

### Update Flow (GA)
```
Weekly timer fires (or manual check)
    │
    ▼
Coordinator._async_update_data()
    │
    ├──► HTTP GET to reports.ies