"""Constants for the Ontario Energy Pricing integration."""

from __future__ import annotations

import logging
from typing import Final

DOMAIN: Final = "ontario_energy_pricing"

LOGGER = logging.getLogger(__package__)

# IESO LMP (Real-Time Ontario Zonal Price) Configuration
IESO_LMP_URL: Final = "https://reports-public.ieso.ca/public/RealtimeOntarioZonalPrice/PUB_RealtimeOntarioZonalPrice.xml"
IESO_LMP_NAMESPACE: Final = "http://www.ieso.ca/schema"

# IESO Global Adjustment Configuration
IESO_GA_URL: Final = (
    "http://reports.ieso.ca/public/GlobalAdjustment/PUB_GlobalAdjustment.xml"
)
IESO_GA_HISTORICAL_URL_TEMPLATE: Final = "http://reports.ieso.ca/public/GlobalAdjustment/PUB_GlobalAdjustment_{year}{month:02d}.xml"
IESO_GA_NAMESPACE: Final = "http://www.ieso.ca/schema"
IESO_DEFAULT_TIMEOUT: Final = 30  # seconds

# Update Intervals (seconds)
# LMP updates every 5 minutes, we fetch every 4 minutes 30 seconds to be safe
UPDATE_INTERVAL_LMP: Final = 270  # 4 minutes 30 seconds
UPDATE_INTERVAL_GA: Final = 604800  # 1 week (check for new month)
UPDATE_INTERVAL_TOTAL_RATE: Final = 270  # 4 minutes 30 seconds (depends on LMP)

# Default Values
DEFAULT_ZONE: Final = "ONTARIO"
DEFAULT_ADMIN_FEE: Final = 0.0  # $/kWh

# Unit of Measurement
CURRENCY_CAD: Final = "CAD"
UNIT_KWH: Final = "/kWh"

# Sensor Attributes
ATTR_PREVIOUS_RATE: Final = "previous_rate"
ATTR_TIMESTAMP: Final = "timestamp"
ATTR_ZONE: Final = "zone"
ATTR_TRADE_MONTH: Final = "trade_month"
ATTR_LAST_UPDATED: Final = "last_updated"

# Configuration Keys
CONF_API_KEY: Final = "api_key"
CONF_ADMIN_FEE: Final = "admin_fee"
CONF_LOCATION: Final = "location"
CONF_ZONE: Final = "zone"

# Entity IDs
SENSOR_LMP_CURRENT: Final = "current_lmp"
SENSOR_LMP_24H_AVG: Final = "lmp_24h_average"
SENSOR_GLOBAL_ADJUSTMENT: Final = "global_adjustment"
SENSOR_TOTAL_RATE: Final = "total_rate"
