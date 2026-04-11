"""IESO Global Adjustment XML client."""

from __future__ import annotations

import asyncio
import xml.etree.ElementTree as ET
from datetime import date, datetime, timezone

import aiohttp  # type: ignore[import]

from .const import IESO_DEFAULT_TIMEOUT, IESO_GA_NAMESPACE, IESO_GA_URL, LOGGER
from .exceptions import IESOXMLParseError
from .models import GlobalAdjustment


class IESOGlobalAdjustmentClient:
    """Client for IESO Global Adjustment XML feed."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        """Initialize the IESO client."""
        self._session = session

    async def async_get_current_rate(self) -> GlobalAdjustment:
        """Get current Global Adjustment rate from IESO."""
        try:
            async with asyncio.timeout(IESO_DEFAULT_TIMEOUT):
                async with self._session.get(IESO_GA_URL) as response:
                    response.raise_for_status()
                    xml_text = await response.text()
        except aiohttp.ClientError as err:
            raise IESOXMLParseError(f"Failed to fetch IESO XML: {err}") from err

        return self._parse_ga_xml(xml_text)

    async def async_get_historical_rates(
        self,
        year: int,
        month: int,
    ) -> GlobalAdjustment:
        """Get historical Global Adjustment rate."""
        url = (
            f"http://reports.ieso.ca/public/GlobalAdjustment/"
            f"PUB_GlobalAdjustment_{year}{month:02d}.xml"
        )

        LOGGER.debug("Fetching historical IESO GA from %s", url)

        try:
            async with asyncio.timeout(IESO_DEFAULT_TIMEOUT):
                async with self._session.get(url) as response:
                    if response.status == 404:
                        raise IESOXMLParseError(
                            f"Historical GA not found for {year}-{month:02d}"
                        )
                    response.raise_for_status()
                    xml_text = await response.text()
        except aiohttp.ClientError as err:
            raise IESOXMLParseError(
                f"Failed to fetch historical IESO XML: {err}"
            ) from err

        return self._parse_ga_xml(xml_text)

    def _parse_ga_xml(self, xml_text: str) -> GlobalAdjustment:
        """Parse IESO Global Adjustment XML."""
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as err:
            raise IESOXMLParseError(
                f"Invalid XML: {err}",
                xml_snippet=xml_text[:500],
            ) from err

        # Extract TradeMonth with namespace
        ns = {"ieso": IESO_GA_NAMESPACE}
        trade_month_elem = root.find(".//ieso:TradeMonth", ns)
        if trade_month_elem is None:
            trade_month_elem = root.find(".//TradeMonth")

        if trade_month_elem is None or not trade_month_elem.text:
            raise IESOXMLParseError(
                "TradeMonth element not found",
                xml_snippet=xml_text[:500],
            )

        trade_month = trade_month_elem.text.strip()

        # Extract FirstEstimateRate with namespace
        rate_elem = root.find(".//ieso:FirstEstimateRate", ns)
        if rate_elem is None:
            rate_elem = root.find(".//FirstEstimateRate")

        if rate_elem is None or not rate_elem.text:
            raise IESOXMLParseError(
                "FirstEstimateRate element not found",
                xml_snippet=xml_text[:500],
            )

        try:
            rate = float(rate_elem.text.strip())
        except ValueError as err:
            raise IESOXMLParseError(
                f"Invalid rate value: {rate_elem.text}",
                xml_snippet=rate_elem.text,
            ) from err

        LOGGER.debug(
            "Parsed IESO GA: rate=%s, trade_month=%s",
            rate,
            trade_month,
        )

        return GlobalAdjustment(
            rate=rate,
            trade_month=trade_month,
            last_updated=datetime.now(timezone.utc),
        )

    async def async_get_rates_for_current_month(self) -> GlobalAdjustment:
        """Get rate for the current month."""
        today = date.today()
        try:
            return await self.async_get_historical_rates(today.year, today.month)
        except IESOXMLParseError:
            LOGGER.debug("Falling back to current GA XML")
            return await self.async_get_current_rate()
