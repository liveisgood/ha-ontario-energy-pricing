"""IESO Generator Output by Fuel Type (Real-time) Client."""

from __future__ import annotations

import asyncio
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime
from typing import Final

import aiohttp

from .const import IESO_LMP_NAMESPACE
from .exceptions import IESOPredispatchError


IESO_GEN_OUTPUT_URL: Final = (
    "https://reports-public.ieso.ca/public/GenOutputbyFuelHourly/PUB_GenOutputbyFuelHourly.xml"
)


@dataclass
class FuelOutput:
    """Output for a single fuel type."""

    fuel_type: str
    mw: float
    quality: int  # 0 = good, -1 = estimated


@dataclass
class HourlyFuelOutput:
    """All fuel outputs for a single hour."""

    hour: int  # 1-24
    fuels: dict[str, FuelOutput] = field(default_factory=dict)

    def get_fuel(self, fuel_type: str) -> FuelOutput | None:
        """Get output for a specific fuel type."""
        return self.fuels.get(fuel_type.upper())

    def total_mw(self) -> float:
        """Total generation across all fuels (MW)."""
        return sum(f.mw for f in self.fuels.values())

    def renewable_mw(self) -> float:
        """Renewable generation (nuclear + hydro + wind + solar + biofuel)."""
        renewable_types = {"NUCLEAR", "HYDRO", "WIND", "SOLAR", "BIOFUEL"}
        return sum(f.mw for ft, f in self.fuels.items() if ft in renewable_types)

    def thermal_mw(self) -> float:
        """Thermal generation (gas + other)."""
        thermal_types = {"GAS", "OTHER"}
        return sum(f.mw for ft, f in self.fuels.items() if ft in thermal_types)

    def renewable_percentage(self) -> float:
        """Percentage of generation from renewable/zero-carbon sources."""
        total = self.total_mw()
        if total == 0:
            return 0.0
        return (self.renewable_mw() / total) * 100

    def carbon_intensity_gco2_per_kwh(self) -> float:
        """
        Estimate grid carbon intensity in gCO2/kWh.

        Rough emission factors (gCO2/kWh):
        - Nuclear: 12
        - Hydro: 24
        - Wind: 11
        - Solar: 41
        - Biofuel: 230 (considered carbon-neutral but has emissions)
        - Gas: 400
        - Other: 500 (conservative estimate)
        """
        emission_factors = {
            "NUCLEAR": 12,
            "HYDRO": 24,
            "WIND": 11,
            "SOLAR": 41,
            "BIOFUEL": 230,
            "GAS": 400,
            "OTHER": 500,
        }

        total_mwh = self.total_mw()  # MW for 1 hour = MWh
        if total_mwh == 0:
            return 0.0

        total_gco2 = sum(
            f.mw * emission_factors.get(ft, 500) for ft, f in self.fuels.items()
        )
        return total_gco2 / total_mwh


@dataclass
class IESOGenOutputData:
    """Complete generator output data for the current day."""

    date: datetime
    hours: dict[int, HourlyFuelOutput] = field(default_factory=dict)

    def get_hour(self, hour: int) -> HourlyFuelOutput | None:
        """Get fuel output for a specific hour (1-24)."""
        return self.hours.get(hour)

    def current_hour_output(self) -> HourlyFuelOutput | None:
        """Get output for the current hour."""
        current_hour = datetime.now().hour
        # IESO hours are 1-24, Python hours are 0-23
        ieso_hour = current_hour if current_hour > 0 else 24
        return self.get_hour(ieso_hour)


class IESOGenOutputClient:
    """Client for fetching IESO Generator Output by Fuel Type."""

    def __init__(self, session: aiohttp.ClientSession, timeout: int = 30) -> None:
        """Initialize the client."""
        self._session = session
        self._timeout = aiohttp.ClientTimeout(total=timeout)

    async def fetch(self) -> IESOGenOutputData:
        """Fetch and parse generator output data."""
        try:
            async with self._session.get(
                IESO_GEN_OUTPUT_URL, timeout=self._timeout
            ) as resp:
                resp.raise_for_status()
                content = await resp.text()
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise IESOPredispatchError(f"Failed to fetch gen output: {err}") from err

        return self._parse_xml(content)

    def _parse_xml(self, xml_content: str) -> IESOGenOutputData:
        """Parse generator output XML."""
        try:
            root = ET.fromstring(xml_content)
            ns = {"ns": IESO_LMP_NAMESPACE}

            # Parse date
            date_elem = root.find(".//ns:DeliveryYear", ns)
            if date_elem is None or date_elem.text is None:
                raise IESOPredispatchError("Missing DeliveryYear in gen output")

            # Find the latest DailyData
            daily_data_elements = root.findall(".//ns:DailyData", ns)
            if not daily_data_elements:
                raise IESOPredispatchError("No DailyData found in gen output")

            # Use the last (most recent) day
            latest_day = daily_data_elements[-1]

            date_str = latest_day.find("ns:Day", ns)
            if date_str is None or date_str.text is None:
                raise IESOPredispatchError("Missing Day in gen output")
            try:
                date = datetime.fromisoformat(date_str.text)
            except ValueError as err:
                raise IESOPredispatchError(f"Invalid date format: {err}") from err

            data = IESOGenOutputData(date=date)

            # Parse hourly data
            for hourly in latest_day.findall("ns:HourlyData", ns):
                hour_elem = hourly.find("ns:Hour", ns)
                if hour_elem is None or hour_elem.text is None:
                    continue
                try:
                    hour = int(hour_elem.text)
                except ValueError:
                    continue

                if not 1 <= hour <= 24:
                    continue

                hourly_output = HourlyFuelOutput(hour=hour)

                for fuel_total in hourly.findall("ns:FuelTotal", ns):
                    fuel_elem = fuel_total.find("ns:Fuel", ns)
                    energy_elem = fuel_total.find("ns:EnergyValue", ns)
                    if fuel_elem is None or energy_elem is None:
                        continue

                    fuel_type = fuel_elem.text.strip().upper() if fuel_elem.text else ""
                    if not fuel_type:
                        continue

                    output_elem = energy_elem.find("ns:Output", ns)
                    quality_elem = energy_elem.find("ns:OutputQuality", ns)

                    try:
                        mw = float(output_elem.text) if output_elem.text else 0.0
                        quality = int(quality_elem.text) if quality_elem.text else 0
                    except (ValueError, TypeError):
                        continue

                    hourly_output.fuels[fuel_type] = FuelOutput(
                        fuel_type=fuel_type, mw=mw, quality=quality
                    )

                data.hours[hour] = hourly_output

            return data

        except ET.ParseError as err:
            raise IESOPredispatchError(f"Failed to parse gen output XML: {err}") from err
        except Exception as err:
            raise IESOPredispatchError(f"Unexpected error parsing gen output: {err}") from err