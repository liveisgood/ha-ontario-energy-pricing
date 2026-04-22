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

# Unit of Measurement
CURRENCY_CAD: Final = "CAD"
UNIT_KWH: Final = "/kWh"

# Configuration Keys
CONF_ADMIN_FEE: Final = "admin_fee"
CONF_LOCATION: Final = "location"

# Entity IDs
SENSOR_CURRENT_LMP: Final = "current_lmp"
SENSOR_HOUR_AVG_LMP: Final = "hour_average_lmp"
SENSOR_GLOBAL_ADJUSTMENT: Final = "global_adjustment"
SENSOR_TOTAL_RATE: Final = "total_rate"
