"""Constants for the Ontario Energy Pricing integration."""

from __future__ import annotations

import logging
from typing import Final

DOMAIN: Final = "ontario_energy_pricing"
LOGGER = logging.getLogger(__name__)

# IESO LMP (Real-Time Ontario Zonal Price) Configuration
IESO_LMP_URL: Final = (
    "https://reports-public.ieso.ca/public/RealtimeOntarioZonalPrice/"
    "PUB_RealtimeOntarioZonalPrice.xml"
)
IESO_LMP_NAMESPACE: Final = "http://www.ieso.ca/schema"

# IESO Global Adjustment Configuration
IESO_GA_URL: Final = (
    "https://reports-public.ieso.ca/public/GlobalAdjustment/PUB_GlobalAdjustment.xml"
)
IESO_GA_NAMESPACE: Final = "http://www.ieso.ca/schema"
IESO_DEFAULT_TIMEOUT: Final = 30  # seconds

# Update Intervals (seconds)
UPDATE_INTERVAL_LMP: Final = 270  # 4 minutes 30 seconds

# Default Values
DEFAULT_ADMIN_FEE: Final = 0.0

# Configuration Keys
CONF_ADMIN_FEE: Final = "admin_fee"
CONF_LOCATION: Final = "location"
CONF_WINDOW_HOURS: Final = "window_hours"
CONF_CHEAPEST_WINDOWS: Final = "cheapest_windows"

# Outage Risk Sensor Thresholds
CONF_OUTAGE_CAPACITY_THRESHOLD: Final = "outage_capacity_threshold"
DEFAULT_OUTAGE_CAPACITY_THRESHOLD: Final = 500.0  # MW
MIN_OUTAGE_CAPACITY_THRESHOLD: Final = 0.0
MAX_OUTAGE_CAPACITY_THRESHOLD: Final = 2000.0

CONF_OUTAGE_COUNT_THRESHOLD: Final = "outage_count_threshold"
DEFAULT_OUTAGE_COUNT_THRESHOLD: Final = 5  # count
MIN_OUTAGE_COUNT_THRESHOLD: Final = 0
MAX_OUTAGE_COUNT_THRESHOLD: Final = 50

# Congestion Pricing Sensor Thresholds
CONF_SHADOW_PRICE_AVERAGE_THRESHOLD: Final = "shadow_price_average_threshold"
DEFAULT_SHADOW_PRICE_AVERAGE_THRESHOLD: Final = 10.0  # $/MWh
MIN_SHADOW_PRICE_AVERAGE_THRESHOLD: Final = 0.0
MAX_SHADOW_PRICE_AVERAGE_THRESHOLD: Final = 100.0

CONF_SHADOW_PRICE_MAX_THRESHOLD: Final = "shadow_price_max_threshold"
DEFAULT_SHADOW_PRICE_MAX_THRESHOLD: Final = 20.0  # $/MWh
MIN_SHADOW_PRICE_MAX_THRESHOLD: Final = 0.0
MAX_SHADOW_PRICE_MAX_THRESHOLD: Final = 100.0

CONF_BINDING_CONSTRAINTS_THRESHOLD: Final = "binding_constraints_threshold"
DEFAULT_BINDING_CONSTRAINTS_THRESHOLD: Final = 3  # count
MIN_BINDING_CONSTRAINTS_THRESHOLD: Final = 0
MAX_BINDING_CONSTRAINTS_THRESHOLD: Final = 20

# Intertie Arbitrage Sensor Thresholds
CONF_ARBITRAGE_SPREAD_THRESHOLD: Final = "arbitrage_spread_threshold"
DEFAULT_ARBITRAGE_SPREAD_THRESHOLD: Final = 15.0  # $/MWh
MIN_ARBITRAGE_SPREAD_THRESHOLD: Final = 0.0
MAX_ARBITRAGE_SPREAD_THRESHOLD: Final = 100.0

# Demand Anomaly Sensor Thresholds
CONF_DEMAND_ANOMALY_THRESHOLD_PERCENT: Final = "demand_anomaly_threshold_percent"
DEFAULT_DEMAND_ANOMALY_THRESHOLD_PERCENT: Final = 20.0  # %
MIN_DEMAND_ANOMALY_THRESHOLD_PERCENT: Final = 0.0
MAX_DEMAND_ANOMALY_THRESHOLD_PERCENT: Final = 100.0

CONF_DEMAND_HISTORY_SIZE: Final = "demand_history_size"
DEFAULT_DEMAND_HISTORY_SIZE: Final = 27  # intervals (~2 hours at 5-min intervals)
MIN_DEMAND_HISTORY_SIZE: Final = 5
MAX_DEMAND_HISTORY_SIZE: Final = 100

# Entity IDs
SENSOR_CURRENT_LMP: Final = "current_lmp"
SENSOR_HOUR_AVG_LMP: Final = "hour_average_lmp"
SENSOR_GLOBAL_ADJUSTMENT: Final = "global_adjustment"
SENSOR_TOTAL_RATE: Final = "total_rate"

# Cheapest window defaults
DEFAULT_WINDOW_HOURS: Final = 3
MIN_WINDOW_HOURS: Final = 1
MAX_WINDOW_HOURS: Final = 24

# IESO Zone Mapping - Map Ontario locations to IESO zones
# Zones from: RealtimeZonalEnergyPrices feed
IESO_ZONES: Final = [
    "EAST",
    "ESSA",
    "NIAGARA",
    "NORTHEAST",
    "NORTHWEST",
    "OTTAWA",
    "SOUTHWEST",
    "TORONTO",
    "WEST",
]

# Location to zone mapping (simplified - city -> zone)
# For more precise mapping, would need postal code / address lookup
LOCATION_TO_ZONE: Final = {
    # TORONTO zone
    "toronto": "TORONTO",
    "oakville": "TORONTO",
    "mississauga": "TORONTO",
    "brampton": "TORONTO",
    "markham": "TORONTO",
    "vaughan": "TORONTO",
    "richmond hill": "TORONTO",
    "ajax": "TORONTO",
    "pickering": "TORONTO",
    "whitby": "TORONTO",
    "oshawa": "TORONTO",
    "burlington": "TORONTO",
    "hamilton": "TORONTO",
    "caledon": "TORONTO",
    "king": "TORONTO",
    "aurora": "TORONTO",
    "newmarket": "TORONTO",
    "east guilimbury": "TORONTO",
    "georgina": "TORONTO",
    # OTTAWA zone
    "ottawa": "OTTAWA",
    "kanata": "OTTAWA",
    "orleans": "OTTAWA",
    "nepean": "OTTAWA",
    "barrhaven": "OTTAWA",
    "stittsville": "OTTAWA",
    # NIAGARA zone
    "niagara falls": "NIAGARA",
    "st. catharines": "NIAGARA",
    "welland": "NIAGARA",
    "fort erie": "NIAGARA",
    "niagara-on-the-lake": "NIAGARA",
    "grimsby": "NIAGARA",
    # SOUTHWEST zone
    "london": "SOUTHWEST",
    "kitchener": "SOUTHWEST",
    "waterloo": "SOUTHWEST",
    "cambridge": "SOUTHWEST",
    "guelph": "SOUTHWEST",
    "windsor": "SOUTHWEST",
    "sarnia": "SOUTHWEST",
    "stratford": "SOUTHWEST",
    "woodstock": "SOUTHWEST",
    "chatham": "SOUTHWEST",
    "leamington": "SOUTHWEST",
    # EAST zone
    "kingston": "EAST",
    "belleville": "EAST",
    "peterborough": "EAST",
    "cobourg": "EAST",
    "port hope": "EAST",
    "brockville": "EAST",
    "cornwall": "EAST",
    # ESSA zone
    "barrie": "ESSA",
    "orillia": "ESSA",
    "midland": "ESSA",
    "collingwood": "ESSA",
    "wasaga beach": "ESSA",
    "innisfil": "ESSA",
    # NORTHEAST zone
    "sudbury": "NORTHEAST",
    "north bay": "NORTHEAST",
    "timmins": "NORTHEAST",
    "sault ste. marie": "NORTHEAST",
    # NORTHWEST zone
    "thunder bay": "NORTHWEST",
    "kenora": "NORTHWEST",
    "dryden": "NORTHWEST",
    # WEST zone
    "owen sound": "WEST",
    "blue mountains": "WEST",
    "meaford": "WEST",
}

# Sorted unique location names for dropdown
LOCATION_OPTIONS: Final = sorted(LOCATION_TO_ZONE.keys())


def get_zone_from_location(location: str) -> str:
    """
    Map a location string to an IESO zone.

    Args:
        location: User-provided location (e.g., "Oakville, Ontario")

    Returns:
        IESO zone name (e.g., "TORONTO"), defaults to "TORONTO" if unknown
    """
    if not location:
        return "TORONTO"

    # Normalize: lowercase, remove "ontario" and "on" as whole words only
    normalized = location.lower()
    # Remove "ontario" as whole word
    normalized = " ".join(w for w in normalized.split() if w not in {"ontario", "on"})
    normalized = normalized.strip()

    # Try exact match first
    if normalized in LOCATION_TO_ZONE:
        return LOCATION_TO_ZONE[normalized]

    # Try partial match (e.g., "oakville, ontario" -> "oakville")
    for city, zone in LOCATION_TO_ZONE.items():
        if city in normalized:
            return zone

    # Default to Toronto (most populous)
    LOGGER.warning("Unknown location '%s', defaulting to TORONTO zone", location)
    return "TORONTO"
