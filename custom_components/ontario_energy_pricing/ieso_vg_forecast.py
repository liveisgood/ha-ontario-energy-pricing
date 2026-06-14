"""IESO Variable Generation (Solar/Wind) Forecast Client."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime

import aiohttp
from dateutil import parser as date_parser

from .exceptions import IESOPredispatchError


# VG Forecast URL
IESO_VG_FORECAST_URL: str = (
    "https://reports-public.ieso.ca/public/VGForecastSummary/PUB_VGForecastSummary.xml"
)
IESO_VG_NAMESPACE: str = "http://www.ieso.ca/schema"


@dataclass
class VGForecastHour:
    """Single hour forecast for a fuel type in a zone."""

    hour: int  # 1-24
    mw_output: float


@dataclass
class VGForecastDay:
    """One day's forecast for a fuel type in a zone."""

    date: datetime
    hours: dict[int, float] = field(default_factory=dict)  # hour -> MW

    def get_hour(self, hour: int) -> float | None:
        """Get MW output for a specific hour (1-24)."""
        return self.hours.get(hour)


@dataclass
class VGFuelForecast:
    """Forecast for one fuel type across zones."""

    fuel_type: str  # "Solar" or "Wind"
    zones: dict[str, list[VGForecastDay]] = field(default_factory=dict)  # zone -> [days]

    def get_zone_forecast(self, zone: str) -> list[VGForecastDay] | None:
        """Get forecast days for a specific zone."""
        return self.zones.get(zone)

    def get_total_mw(self, date: datetime, hour: int) -> float:
        """Get total MW across all zones for a specific date/hour."""
        total = 0.0
        for zone_days in self.zones.values():
            for day in zone_days:
                if day.date.date() == date.date():
                    mw = day.get_hour(hour)
                    if mw is not None:
                        total += mw
        return total


@dataclass
class IESOVGforecastData:
    """Complete VG Forecast data."""

    forecast_timestamp: datetime
    solar: VGFuelForecast
    wind: VGFuelForecast

    def get_solar_total_mw(self, date: datetime, hour: int) -> float:
        """Get total solar forecast MW for Ontario."""
        return self.solar.get_total_mw(date, hour)

    def get_wind_total_mw(self, date: datetime, hour: int) -> float:
        """Get total wind forecast MW for Ontario."""
        return self.wind.get_total_mw(date, hour)

    def get_total_vg_mw(self, date: datetime, hour: int) -> float:
        """Total variable generation (solar + wind) forecast MW."""
        return self.get_solar_total_mw(date, hour) + self.get_wind_total_mw(date, hour)

    def is_high_vg_hour(self, date: datetime, hour: int, threshold_mw: float = 1000.0) -> bool:
        """Check if hour has high variable generation (likely low/negative prices)."""
        return self.get_total_vg_mw(date, hour) >= threshold_mw

    def get_negative_price_probability(self, date: datetime, hour: int) -> float:
        """
        Estimate probability of negative prices based on VG forecast.

        Heuristic: High solar+wind + shoulder hours (low demand) = higher probability.
        This is a simple model - could be enhanced with historical correlation.
        """
        vg_mw = self.get_total_vg_mw(date, hour)

        # Base probability from VG level
        if vg_mw >= 3000:
            base_prob = 0.7
        elif vg_mw >= 2000:
            base_prob = 0.4
        elif vg_mw >= 1000:
            base_prob = 0.15
        else:
            base_prob = 0.02

        # Adjust for hour (shoulder hours more likely negative)
        if 2 <= hour <= 5:  # Overnight minimum demand
            base_prob *= 1.5
        elif 10 <= hour <= 16:  # Solar peak hours
            base_prob *= 1.3

        return min(base_prob, 0.95)


class IESOVGforecastClient:
    """Client for fetching IESO Variable Generation Forecast data."""

    def __init__(self, session: aiohttp.ClientSession, timeout: int = 30) -> None:
        """Initialize the client."""
        self._session = session
        self._timeout = aiohttp.ClientTimeout(total=timeout)

    async def fetch(self) -> IESOVGforecastData:
        """Fetch and parse VG forecast data."""
        try:
            async with self._session.get(IESO_VG_FORECAST_URL, timeout=self._timeout) as resp:
                resp.raise_for_status()
                content = await resp.text()
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise IESOPredispatchError(f"Failed to fetch VG forecast: {err}") from err

        return self._parse_xml(content)

    def _parse_xml(self, xml_content: str) -> IESOVGforecastData:
        """Parse VG forecast XML."""
        import xml.etree.ElementTree as ET

        try:
            root = ET.fromstring(xml_content)
            ns = {"ns": IESO_VG_NAMESPACE}

            # Parse forecast timestamp
            timestamp_elem = root.find(".//ns:ForecastTimeStamp", ns)
            if timestamp_elem is None or timestamp_elem.text is None:
                raise IESOPredispatchError("Missing ForecastTimeStamp in VG forecast")
            forecast_timestamp = date_parser.parse(timestamp_elem.text)

            # Initialize fuel forecasts
            solar_forecast = VGFuelForecast(fuel_type="Solar")
            wind_forecast = VGFuelForecast(fuel_type="Wind")

            # Parse organization data (fuel types)
            for org_data in root.findall(".//ns:OrganizationData", ns):
                fuel_elem = org_data.find("ns:FuelData", ns)
                if fuel_elem is None:
                    continue

                fuel_type_elem = fuel_elem.find("ns:FuelType", ns)
                if fuel_type_elem is None or fuel_type_elem.text is None:
                    continue
                fuel_type = fuel_type_elem.text.strip()

                # Select the right forecast object
                if fuel_type == "Solar":
                    fuel_forecast = solar_forecast
                elif fuel_type == "Wind":
                    fuel_forecast = wind_forecast
                else:
                    continue

                # Parse resources (zones)
                for resource in fuel_elem.findall("ns:ResourceData", ns):
                    zone_elem = resource.find("ns:ZoneName", ns)
                    if zone_elem is None or zone_elem.text is None:
                        continue
                    zone = zone_elem.text.strip()

                    # Parse energy forecasts (days)
                    zone_days: list[VGForecastDay] = []
                    for energy_fcst in resource.findall("ns:EnergyForecast", ns):
                        date_elem = energy_fcst.find("ns:ForecastDate", ns)
                        if date_elem is None or date_elem.text is None:
                            continue
                        try:
                            fcst_date = date_parser.parse(date_elem.text).replace(tzinfo=None)
                        except ValueError:
                            continue

                        day = VGForecastDay(date=fcst_date)

                        # Parse hourly intervals
                        for interval in energy_fcst.findall("ns:ForecastInterval", ns):
                            hour_elem = interval.find("ns:ForecastHour", ns)
                            mw_elem = interval.find("ns:MWOutput", ns)
                            if hour_elem is None or mw_elem is None:
                                continue
                            try:
                                hour = int(hour_elem.text)
                                mw = float(mw_elem.text)
                                if 1 <= hour <= 24:
                                    day.hours[hour] = mw
                            except (ValueError, TypeError):
                                continue

                        zone_days.append(day)

                    if zone_days:
                        fuel_forecast.zones[zone] = zone_days

            return IESOVGforecastData(
                forecast_timestamp=forecast_timestamp,
                solar=solar_forecast,
                wind=wind_forecast,
            )

        except ET.ParseError as err:
            raise IESOPredispatchError(f"Failed to parse VG forecast XML: {err}") from err
        except Exception as err:
            raise IESOPredispatchError(f"Unexpected error parsing VG forecast: {err}") from err