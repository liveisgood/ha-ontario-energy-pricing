"""IESO Global Adjustment XML client."""

from __future__ import annotations

import asyncio
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Final

import aiohttp

from .const import IESO_DEFAULT_TIMEOUT, LOGGER
from .exceptions import IESOXMLParseError
from .models import GlobalAdjustment

IESO_GA_URL: Final = (
    "https://reports-public.ieso.ca/public/GlobalAdjustment/PUB_GlobalAdjustment.xml"
)
IESO_GA_NAMESPACE: Final = "http://www.ieso.ca/schema"


class IESOGlobalAdjustmentClient:
    """Client for IESO Global Adjustment XML."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        """Initialize the IESO GA client."""
        self._session: aiohttp.ClientSession = session

    async def async_get_current_rate(self) -> GlobalAdjustment:
        """Get current Global Adjustment rate from IESO."""
        try:
            async with asyncio.timeout(IESO_DEFAULT_TIMEOUT):
                async with self._session.get(IESO_GA_URL) as response:
                    response.raise_for_status()
                    xml_text = await response.text()
        except Exception as err:
            raise IESOXMLParseError(f"Failed to fetch IESO GA: {err}") from err

        return self._parse_ga_xml(xml_text)

    def _parse_ga_xml(self, xml_text: str) -> GlobalAdjustment:
        """Parse IESO Global Adjustment XML."""
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as err:
            raise IESOXMLParseError(f"Invalid XML: {err}") from err

        ns = {"ieso": IESO_GA_NAMESPACE}

        trade_month_elem = root.find(".//ieso:TradeMonth", ns)
        # Real feed has FirstEstimateRate under GAValues wrapper
        rate_elem = root.find(".//ieso:GAValues/ieso:FirstEstimateRate", ns)
        if rate_elem is None:
            # Fallback to direct location for compatibility
            rate_elem = root.find(".//ieso:FirstEstimateRate", ns)

        if trade_month_elem is None or not trade_month_elem.text:
            raise IESOXMLParseError("Missing required GA element: TradeMonth")

        if rate_elem is None or not rate_elem.text:
            raise IESOXMLParseError("Missing required GA element: FirstEstimateRate")

        trade_month = trade_month_elem.text.strip()
        try:
            # IESO GA feed provides rate in $/MWh, convert to $/kWh
            rate_mwh = float(rate_elem.text.strip())
            rate = rate_mwh / 1000.0
        except ValueError as err:
            raise IESOXMLParseError(f"Invalid rate value: {err}") from err

        LOGGER.debug(
            "Parsed IESO GA: rate=%s $/kWh (%s $/MWh), month=%s",
            rate,
            rate_mwh,
            trade_month,
        )

        return GlobalAdjustment(
            rate=rate,
            trade_month=trade_month,
            last_updated=datetime.now(timezone.utc),
        )