"""IESO Predispatch and Day-Ahead Ontario Zonal Price XML client.

Provides forecast hourly prices from:
- Predispatch: today's 24 hourly predicted prices (updated hourly)
- Day-Ahead: tomorrow's 24 hourly predicted prices (published around noon)

Both feeds use the same XML namespace as the real-time LMP feed.
Both report prices in $/MWh.
Conversion to c/kWh: $/MWh x 100c/$ / 1000kWh/MWh = $/MWh / 10
"""

from __future__ import annotations

import asyncio
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime
from typing import Final

import aiohttp

from .const import IESO_DEFAULT_TIMEOUT, IESO_LMP_NAMESPACE, LOGGER

IESO_PREDISP_URL: Final = (
    "https://reports-public.ieso.ca/public/PredispHourlyOntarioZonalPrice/"
    "PUB_PredispHourlyOntarioZonalPrice.xml"
)

IESO_DA_URL: Final = (
    "https://reports-public.ieso.ca/public/DAHourlyOntarioZonalPrice/"
    "PUB_DAHourlyOntarioZonalPrice.xml"
)


class IESOPredispatchError(Exception):
    """Error fetching or parsing IESO predispatch data."""


@dataclass(frozen=True, slots=True)
class IESOForecastHour:
    """A single hourly forecast price."""

    hour: int  # 1-24
    zonal_price_mwh: float  # $/MWh
    zonal_price_kwh: float  # c/kWh ($/MWh x 100c/$ / 1000kWh/MWh = $/MWh / 10)
    loss_price_mwh: float  # $/MWh (marginal loss component)
    congestion_price_mwh: float  # $/MWh (congestion component)
    flag: str  # Dispatch status flag (may be empty)


@dataclass(frozen=True)
class IESOForecastData:
    """IESO forecast pricing data for a delivery date."""

    delivery_date: str  # YYYY-MM-DD
    created_at: datetime
    hours: list[IESOForecastHour] = field(default_factory=list)

    @property
    def average_price_mwh(self) -> float:
        """Average zonal price across all hours in $/MWh."""
        if not self.hours:
            return 0.0
        return sum(h.zonal_price_mwh for h in self.hours) / len(self.hours)

    @property
    def average_price_kwh(self) -> float:
        """Average zonal price in c/kWh ($/MWh / 10)."""
        return self.average_price_mwh / 10

    @property
    def min_price_hour(self) -> IESOForecastHour | None:
        """Hour with the lowest forecast price."""
        if not self.hours:
            return None
        return min(self.hours, key=lambda h: h.zonal_price_mwh)

    @property
    def max_price_hour(self) -> IESOForecastHour | None:
        """Hour with the highest forecast price."""
        if not self.hours:
            return None
        return max(self.hours, key=lambda h: h.zonal_price_mwh)

    def cheapest_hours(self, num_hours: int) -> set[int]:
        """Return the set of hour numbers (1-24) that are the X cheapest.

        Hours are NOT required to be contiguous — the sensor simply turns ON
        during whichever hours have the lowest forecast prices.

        Args:
            num_hours: How many of the cheapest hours to select (1-24).

        Returns:
            Set of hour numbers (1-24) with the lowest prices.
        """
        if num_hours < 1 or not self.hours:
            return set()
        sorted_hours = sorted(self.hours, key=lambda h: h.zonal_price_mwh)
        return {h.hour for h in sorted_hours[:num_hours]}

    def is_in_cheapest_hours(self, current_hour: int, num_hours: int) -> bool:
        """Check if the current hour is one of the X cheapest.

        Args:
            current_hour: Current hour (1-24, IESO convention where 1=00:00-01:00).
            num_hours: How many cheapest hours to consider.
        """
        return current_hour in self.cheapest_hours(num_hours)



class IESOPredispatchClient:
    """Client for IESO Predispatch and Day-Ahead XML feeds."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        """Initialize client."""
        self._session = session

    async def async_get_predispatch(self) -> IESOForecastData:
        """Fetch today's predispatch forecast (24 hourly prices)."""
        xml_text = await self._fetch_xml(IESO_PREDISP_URL)
        return self._parse_forecast_xml(xml_text, "predispatch")

    async def async_get_day_ahead(self) -> IESOForecastData | None:
        """Fetch tomorrow's day-ahead forecast.

        Returns None if the day-ahead report is not yet available
        (typically published around noon for the next day).
        """
        try:
            xml_text = await self._fetch_xml(IESO_DA_URL)
            return self._parse_forecast_xml(xml_text, "day-ahead")
        except IESOPredispatchError:
            LOGGER.debug("Day-ahead report not yet available")
            return None

    async def _fetch_xml(self, url: str) -> str:
        """Fetch XML from IESO."""
        try:
            async with asyncio.timeout(IESO_DEFAULT_TIMEOUT):
                async with self._session.get(url) as response:
                    response.raise_for_status()
                    return await response.text()
        except Exception as err:
            raise IESOPredispatchError(f"Failed to fetch IESO forecast: {err}") from err

    def _parse_forecast_xml(self, xml_text: str, feed_name: str) -> IESOForecastData:
        """Parse IESO Predispatch/Day-Ahead XML.

        Both feeds share the same structure:
          <HourlyPriceComponents>
            <PricingHour>1</PricingHour>
            <ZonalPrice>31.58</ZonalPrice>
            <LossPriceCapped>0.08</LossPriceCapped>
            <CongestionPriceCapped>-0.29</CongestionPriceCapped>
            <Flag>DSO-RD</Flag>  (optional)
          </HourlyPriceComponents>
        """
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as err:
            raise IESOPredispatchError(f"Invalid XML from {feed_name}: {err}") from err

        ns = {"ieso": IESO_LMP_NAMESPACE}

        created_at_elem = root.find(".//ieso:CreatedAt", ns)
        delivery_date_elem = root.find(".//ieso:DeliveryDate", ns)

        if not all(
            elem is not None and elem.text
            for elem in [created_at_elem, delivery_date_elem]
        ):
            raise IESOPredispatchError(
                f"Required header elements missing from {feed_name}"
            )

        assert created_at_elem is not None and created_at_elem.text
        assert delivery_date_elem is not None and delivery_date_elem.text

        created_at = datetime.fromisoformat(created_at_elem.text)
        delivery_date = delivery_date_elem.text.strip()

        hours: list[IESOForecastHour] = []
        for component in root.findall(".//ieso:HourlyPriceComponents", ns):
            hour_elem = component.find("ieso:PricingHour", ns)
            zonal_elem = component.find("ieso:ZonalPrice", ns)
            loss_elem = component.find("ieso:LossPriceCapped", ns)
            congestion_elem = component.find("ieso:CongestionPriceCapped", ns)
            flag_elem = component.find("ieso:Flag", ns)

            if not all(
                elem is not None and elem.text and elem.text.strip()
                for elem in [hour_elem, zonal_elem]
            ):
                continue

            assert hour_elem is not None and hour_elem.text
            assert zonal_elem is not None and zonal_elem.text

            try:
                zonal_mwh = float(zonal_elem.text)
                hours.append(
                    IESOForecastHour(
                        hour=int(hour_elem.text),
                        zonal_price_mwh=zonal_mwh,
                        zonal_price_kwh=round(zonal_mwh / 10, 4),
                        loss_price_mwh=(
                            float(loss_elem.text)
                            if loss_elem is not None and loss_elem.text
                            else 0.0
                        ),
                        congestion_price_mwh=(
                            float(congestion_elem.text)
                            if congestion_elem is not None and congestion_elem.text
                            else 0.0
                        ),
                        flag=(
                            flag_elem.text.strip()
                            if flag_elem is not None and flag_elem.text
                            else ""
                        ),
                    )
                )
            except (ValueError, TypeError):
                continue

        hours.sort(key=lambda h: h.hour)

        LOGGER.debug(
            "Parsed IESO %s: date=%s, hours=%d",
            feed_name,
            delivery_date,
            len(hours),
        )

        return IESOForecastData(
            delivery_date=delivery_date,
            created_at=created_at,
            hours=hours,
        )
