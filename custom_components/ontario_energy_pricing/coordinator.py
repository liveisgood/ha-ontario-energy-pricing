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
from .ieso_ga import IESOGlobalAdjustmentClient
from .ieso_lmp import IESOLMPClient
from .ieso_predispatch import (
    IESOForecastData,
    IESOPredispatchClient,
    IESOPredispatchError,
)
from .ieso_vg_forecast import IESOVGforecastClient
from .ieso_gen_output import IESOGenOutputClient
from .ieso_reserves import IESOReservePricesClient
from .ieso_shadow_prices import IESOShadowPricesClient
from .ieso_tx_outages import IESOTxOutagesClient
from .ieso_demand_zonal import IESODemandZonalClient
from .ieso_intertie_lmp import IESOIntertieLMPClient
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
    # New: Shadow prices
    shadow_prices: dict[str, Any] | None = None
    # New: Tx outages
    tx_outages: dict[str, Any] | None = None
    # New: Demand zonal
    demand_zonal: dict[str, Any] | None = None
    # New: Intertie LMP
    intertie_lmp: dict[str, Any] | None = None

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
        self._reserve_client: IESOReservePricesClient | None = None
        self._shadow_prices_client: IESOShadowPricesClient | None = None
        self._tx_outages_client: IESOTxOutagesClient | None = None
        self._demand_zonal_client: IESODemandZonalClient | None = None
        self._intertie_lmp_client: IESOIntertieLMPClient | None = None
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
        location = self.config_entry.options.get(
            CONF_LOCATION
        ) or self.config_entry.data.get(CONF_LOCATION)
        self._lmp_client = IESOLMPClient(session, location=location)
        self._ga_client = IESOGlobalAdjustmentClient(session)
        self._predisp_client = IESOPredispatchClient(session)
        self._vg_client = IESOVGforecastClient(session)
        self._gen_client = IESOGenOutputClient(session)
        self._reserve_client = IESOReservePricesClient(session)
        self._shadow_prices_client = IESOShadowPricesClient(session)
        self._tx_outages_client = IESOTxOutagesClient(session)
        self._demand_zonal_client = IESODemandZonalClient(session)
        self._intertie_lmp_client = IESOIntertieLMPClient(session)

    async def _async_update_data(self) -> OntarioEnergyPricingData:
        """Fetch all pricing data from IESO."""
        assert self._lmp_client is not None
        assert self._ga_client is not None
        assert self._predisp_client is not None
        assert self._vg_client is not None
        assert self._gen_client is not None
        assert self._reserve_client is not None
        assert self._shadow_prices_client is not None
        assert self._tx_outages_client is not None
        assert self._demand_zonal_client is not None
        assert self._intertie_lmp_client is not None
        # Fetch required data (LMP and GA) - if either fails, we cannot proceed
        try:
            lmp_data = await self._lmp_client.async_get_current_lmp()
            ga_data = await self._ga_client.async_get_current_rate()
        except Exception as err:
            raise UpdateFailed(f"Error fetching required IESO data: {err}") from err

        try:
            # Update rolling price history for grid stress detection
            self.recent_prices.append(lmp_data.current_lmp_kwh)
            # Fetch forecast, VG, fuel mix, reserve, shadow prices, tx outages, demand zonal, and intertie LMP data in parallel, but allow failures
            optional_results = await asyncio.gather(
                self._predisp_client.async_get_predispatch(),
                self._predisp_client.async_get_day_ahead(),
                self._vg_client.fetch(),
                self._gen_client.fetch(),
                self._reserve_client.fetch(),
                self._shadow_prices_client.fetch(),
                self._tx_outages_client.fetch(),
                self._demand_zonal_client.fetch(),
                self._intertie_lmp_client.fetch(),
                return_exceptions=True,
            )
            (
                forecast_today_result,
                forecast_tomorrow_result,
                vg_result,
                gen_result,
                reserve_result,
                shadow_prices_result,
                tx_outages_result,
                demand_zonal_result,
                intertie_lmp_result,
            ) = optional_results
            forecast_today = None
            forecast_tomorrow = None
            vg_forecast = None
            fuel_mix = None
            shadow_prices = None
            tx_outages = None
            demand_zonal = None
            intertie_lmp = None
            # Process forecast today (optional)
            if not isinstance(forecast_today_result, Exception):
                forecast_today = forecast_today_result
                if isinstance(forecast_today_result, IESOPredispatchError):
                    LOGGER.warning(
                        "Failed to fetch IESO predispatch forecast: %s",
                        forecast_today_result,
                    )
            # Process forecast tomorrow (optional)
            if not isinstance(forecast_tomorrow_result, Exception):
                forecast_tomorrow = forecast_tomorrow_result
                if isinstance(forecast_tomorrow_result, IESOPredispatchError):
                    LOGGER.warning(
                        "Failed to fetch IESO day-ahead forecast: %s",
                        forecast_tomorrow_result,
                    )
            # Process VG forecast (optional)
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
                if isinstance(vg_result, IESOPredispatchError):
                    LOGGER.warning("Failed to fetch IESO VG forecast: %s", vg_result)
            # Process fuel mix (optional)
            if not isinstance(gen_result, Exception):
                ieso_gen = gen_result
                current_hour = ieso_gen.current_hour_output()
                if current_hour:
                    # Use the data date from IESO (midnight of that day) as timestamp
                    fuel_mix_timestamp = datetime.combine(
                        ieso_gen.date, datetime.min.time()
                    )
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
                if isinstance(gen_result, IESOPredispatchError):
                    LOGGER.warning(
                        "Failed to fetch IESO generator output: %s", gen_result
                    )
            # Process reserve prices (optional)
            if not isinstance(reserve_result, Exception):
                reserve_data = reserve_result
                # Store reserve data directly - it's already in the right format from the client
                reserve_prices = reserve_data
                # Note: We're not converting to a specific model here since the client returns
                # a structured dict that can be used directly by binary sensors
                # If we need a specific model later, we can add it
            # Process shadow prices (optional)
            if not isinstance(shadow_prices_result, Exception):
                shadow_prices = shadow_prices_result
            # Process tx outages (optional)
            if not isinstance(tx_outages_result, Exception):
                tx_outages = tx_outages_result
            # Process demand zonal (optional)
            if not isinstance(demand_zonal_result, Exception):
                demand_zonal = demand_zonal_result
            # Process intertie LMP (optional)
            if not isinstance(intertie_lmp_result, Exception):
                intertie_lmp = intertie_lmp_result
            # Return the compiled data
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
                shadow_prices=shadow_prices,
                tx_outages=tx_outages,
                demand_zonal=demand_zonal,
                intertie_lmp=intertie_lmp,
            )
        except Exception as err:
            raise UpdateFailed(f"Error processing IESO data: {err}") from err
