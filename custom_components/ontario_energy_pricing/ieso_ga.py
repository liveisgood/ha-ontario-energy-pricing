"""IESO Global Adjustment XML client."""

from __future__ import annotations

import asyncio
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    import aiohttp

from .const import LOGGER
from .exceptions import IESOXMLParseError
from .models import GlobalAdjustment

IESO_GA_URL: Final = (
    "https://reports-public.ieso.ca/public/GlobalAdjustment/PUB_GlobalAdjustment.xml"
)
IESO_GA_NAMESPACE: Final = "http://www.ieso.ca/schema"
IESO_DEFAULT_TIMEOUT: Final = 30


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
        rate_elem = root.find(".//ieso:FirstEstimateRate", ns)

        if not all(
            elem is not None and elem.text for elem in [trade_month_elem, rate_elem]
        ):
            raise IESOXMLParseError("Required GA elements not found")

        assert trade_month_elem is not None and trade_month_elem.text
        assert rate_elem is not None and rate_elem.text

        trade_month = trade_month_elem.text.strip()
        rate = float(rate_elem.text.strip())

        LOGGER.debug("Parsed IESO GA: rate=%s, month=%s", rate, trade_month)

        return GlobalAdjustment(
            rate=rate,
            trade_month=trade_month,
            last_updated=datetime.now(timezone.utc),
        )
