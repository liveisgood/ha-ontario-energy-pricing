"""DataUpdateCoordinators for Ontario Energy Pricing."""

from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

from .const import CONF_LOCATION, DOMAIN, LOGGER, UPDATE_INTERVAL_LMP
from .exceptions import IESOLMPError, IESOXMLParseError
from .ieso_ga import IESOGlobalAdjustmentClient
from .ieso_lmp import IESOLMPClient
from .ieso_predispatch import (
    IESOForecastData,
    IESOPredispatchClient,
    IESOPredispatchError,
)
from .ieso_vg_forecast import IESOVGforecastClient
from .ieso_gen_output import IESOGenOutputClient
from .models import VGForecastData, FuelMixData


@dataclass(frozen=True)
class OntarioEnergyPricingData:
    """Unified energy pricing data from IESO."""

    current_lmp_kwh: float
    hour_average_lmp_kwh: float
    current_lmp_mwh: float
    delivery_hour: int
    delivery_date: str
    global_adjustment: float
    trade_month: str
    admin_fee: float
    intervals: list[dict[str, Any]] = field(default_factory=list)
    forecast_today: IESOForecastData | None = None
    forecast_tomorrow: IESOForecastData | None = None
    # New: VG forecast and fuel mix
    vg_forecast: VGForecastData | None = None
    fuel_mix: FuelMixData | None = None

    @property
    def total_rate(self) -> float:
        """Total rate in c/kWh."""
        return self.current_lmp_kwh + self.global_adjustment + self.admin_fee


class OntarioEnergyPricingCoordinator(DataUpdateCoordinator):
    """Unified coordinator for Ontario Energy Pricing data."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        admin_fee: float,
    ) -> None:
        """Initialize the coordinator."""
        self._admin_fee = admin_fee
        self._lmp_client: IESOLMPClient | None = None
        self._ga_client: IESOGlobalAdjustmentClient | None = None
        self._predisp_client: IESOPredispatchClient | None = None
        self._vg_client: IESOVGforecastClient | None = None
        self._gen_client: IESOGenOutputClient | None = None
        # Rolling price history for grid stress detection (~2 hours at 4.5 min intervals)
        self.recent_prices: deque[float] = deque(maxlen=27)
        super().__init__(
            hass=hass,
            logger=LOGGER,
            name=f"{DOMAIN}_unified",
            config_entry=entry,
            update_interval=timedelta(seconds=UPDATE_INTERVAL_LMP),
            always_update=False,
        )

    async def _async_setup(self) -> None:
        """Set up clients after Home Assistant is ready.

        This is called automatically during async_config_entry_first_refresh.
        """
        from homeassistant.helpers.aiohttp_client import async_get_clientsession

        session = async_get_clientsession(self.hass)
        location = self.config_entry.options.get(CONF_LOCATION) or self.config_entry.data.get(CONF_LOCATION)
        self._lmp_client = IESOLMPClient(session, location=location)
        self._ga_client = IESOGlobalAdjustmentClient(session)
        self._predisp_client = IESOPredispatchClient(session)
        self._vg_client = IESOVGforecastClient(session)
        self._gen_client = IESOGenOutputClient(session)

    async def _async_update_data(self) -> OntarioEnergyPricingData:
        """Fetch all pricing data from IESO."""
        assert self._lmp_client is not None
        assert self._ga_client is not None
        assert self._predisp_client is not None
        assert self._vg_client is not None
        assert self._gen_client is not None

        # Fetch required data (LMP and GA) in parallel
        required_results = await asyncio.gather(
            self._lmp_client.async_get_current_lmp(),
            self._ga_client.async_get_current_rate(),
            return_exceptions=True,
        )
        lmp_result, ga_result = required_results

        # Check if LMP or GA failed
        if isinstance(lmp_result, Exception):
            if isinstance(lmp_result, (IESOXMLParseError, IESOLMPError)):
                raise UpdateFailed(f"Error fetching IESO LMP data: {lmp_result}") from lmp_result
            else:
                raise UpdateFailed(f"Unexpected error fetching IESO LMP data: {lmp_result}") from lmp_result
        if isinstance(ga_result, Exception):
            if isinstance(ga_result, (IESOXMLParseError, IESOLMPError)):
                raise UpdateFailed(f"Error fetching IESO GA data: {ga_result}") from ga_result
            else:
                raise UpdateFailed(f"Unexpected error fetching IESO GA data: {ga_result}") from ga_result

        lmp_data = lmp_result
        ga_data = ga_result

        # Update rolling price history for grid stress detection
        self.recent_prices.append(lmp_data.current_lmp_kwh)

        # Fetch forecast, VG, and fuel mix data in parallel, but allow failures
        optional_results = await asyncio.gather(
            self._predisp_client.async_get_predispatch(),
            self._predisp_client.async_get_day_ahead(),
            self._vg_client.fetch(),
            self._gen_client.fetch(),
            return_exceptions=True,
        )
        forecast_today_result, forecast_tomorrow_result, vg_result, gen_result = optional_results

        forecast_today = None
        forecast_tomorrow = None
        vg_forecast = None
        fuel_mix = None

        if not isinstance(forecast_today_result, Exception):
            forecast_today = forecast_today_result
        else:
            if isinstance(forecast_today_result, IESOPredispatchError):
                LOGGER.warning("Failed to fetch IESO predispatch forecast: %s", forecast_today_result)
            else:
                LOGGER.warning("Unexpected error fetching IESO predispatch forecast: %s", forecast_today_result)

        if not isinstance(forecast_tomorrow_result, Exception):
            forecast_tomorrow = forecast_tomorrow_result
        else:
            if isinstance(forecast_tomorrow_result, IESOPredispatchError):
                LOGGER.warning("Failed to fetch IESO day-ahead forecast: %s", forecast_tomorrow_result)
            else:
                LOGGER.warning("Unexpected error fetching IESO day-ahead forecast: %s", forecast_tomorrow_result)

        if not isinstance(vg_result, Exception):
            ieso_vg = vg_result
            # Convert to our model - use today's forecast from the VG data
            forecast_ts = ieso_vg.forecast_timestamp
            today = forecast_ts.date()
            solar_today = {
                h: ieso_vg.get_solar_total_mw(
                    datetime.combine(today, datetime.min.time()), h
                )
                for h in range(1, 25)
            }
            wind_today = {
                h: ieso_vg.get_wind_total_mw(
                    datetime.combine(today, datetime.min.time()), h
                )
                for h in range(1, 25)
            }
            vg_forecast = VGForecastData(
                forecast_timestamp=ieso_vg.forecast_timestamp,
                solar_forecast_mw=solar_today,
                wind_forecast_mw=wind_today,
            )
        else:
            if isinstance(vg_result, IESOPredispatchError):
                LOGGER.warning("Failed to fetch IESO VG forecast: %s", vg_result)
            else:
                LOGGER.warning("Unexpected error fetching IESO VG forecast: %s", vg_result)

        if not isinstance(gen_result, Exception):
            ieso_gen = gen_result
            current_hour = ieso_gen.current_hour_output()
            if current_hour:
                # Use the data date from IESO (midnight of that day) as timestamp
                fuel_mix_timestamp = datetime.combine(ieso_gen.date, datetime.min.time())
                fuel_mix = FuelMixData(
                    timestamp=fuel_mix_timestamp,
                    nuclear_mw=current_hour.get_fuel("NUCLEAR").mw
                    if current_hour.get_fuel("NUCLEAR")
                    else 0.0,
                    hydro_mw=current_hour.get_fuel("HYDRO").mw
                    if current_hour.get_fuel("HYDRO")
                    else 0.0,
                    wind_mw=current_hour.get_fuel("WIND").mw
                    if current_hour.get_fuel("WIND")
                    else 0.0,
                    solar_mw=current_hour.get_fuel("SOLAR").mw
                    if current_hour.get_fuel("SOLAR")
                    else 0.0,
                    gas_mw=current_hour.get_fuel("GAS").mw
                    if current_hour.get_fuel("GAS")
                    else 0.0,
                    biofuel_mw=current_hour.get_fuel("BIOFUEL").mw
                    if current_hour.get_fuel("BIOFUEL")
                    else 0.0,
                    other_mw=current_hour.get_fuel("OTHER").mw
                    if current_hour.get_fuel("OTHER")
                    else 0.0,
                )
        else:
            if isinstance(gen_result, IESOPredispatchError):
                LOGGER.warning("Failed to fetch IESO generator output: %s", gen_result)
            else:
                LOGGER.warning("Unexpected error fetching IESO generator output: %s", gen_result)

        try:
            return OntarioEnergyPricingData(
                current_lmp_kwh=lmp_data.current_lmp_kwh,
                hour_average_lmp_kwh=lmp_data.hour_average_kwh,
                current_lmp_mwh=(
                    lmp_data.latest_interval.lmp_mwh
                    if lmp_data.latest_interval
                    else 0.0
                ),
                delivery_hour=lmp_data.delivery_hour,
                delivery_date=lmp_data.delivery_date,
                # $/MWh x 100c/$ / 1000kWh/MWh = $/MWh / 10
                global_adjustment=ga_data.rate / 10,
                trade_month=ga_data.trade_month,
                admin_fee=self._admin_fee,
                intervals=[
                    {
                        "interval": i.interval,
                        "lmp_kwh": i.lmp_kwh,
                        "lmp_mwh": i.lmp_mwh,
                        "flag": i.flag,
                    }
                    for i in lmp_data.intervals
                ],
                forecast_today=forecast_today,
                forecast_tomorrow=forecast_tomorrow,
                vg_forecast=vg_forecast,
                fuel_mix=fuel_mix,
            )
        except Exception as err:
            raise UpdateFailed(f"Error processing IESO data: {err}") from err