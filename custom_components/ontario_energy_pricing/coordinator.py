"""DataUpdateCoordinators for Ontario Energy Pricing."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import timedelta
from typing import TYPE_CHECKING, Any

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

from .const import DOMAIN, LOGGER, UPDATE_INTERVAL_LMP
from .exceptions import IESOLMPError, IESOXMLParseError
from .ieso_ga import IESOGlobalAdjustmentClient
from .ieso_lmp import IESOLMPClient


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

    @property
    def total_rate(self) -> float:
        """Total rate in ¢/kWh."""
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
        self._lmp_client = IESOLMPClient(session)
        self._ga_client = IESOGlobalAdjustmentClient(session)

    async def _async_update_data(self) -> OntarioEnergyPricingData:
        """Fetch all pricing data from IESO."""
        assert self._lmp_client is not None
        assert self._ga_client is not None

        try:
            lmp_data, ga_data = await asyncio.gather(
                self._lmp_client.async_get_current_lmp(),
                self._ga_client.async_get_current_rate(),
            )
        except (IESOXMLParseError, IESOLMPError) as err:
            raise UpdateFailed(f"Error fetching IESO data: {err}") from err
        except Exception as err:
            raise UpdateFailed(f"Unexpected error fetching IESO data: {err}") from err

        try:
            return OntarioEnergyPricingData(
                current_lmp_kwh=lmp_data.current_lmp_kwh,
                hour_average_lmp_kwh=lmp_data.hour_average_kwh,
                current_lmp_mwh=lmp_data.latest_interval.lmp_mwh
                if lmp_data.latest_interval
                else 0.0,
                delivery_hour=lmp_data.delivery_hour,
                delivery_date=lmp_data.delivery_date,
                global_adjustment=ga_data.rate
                / 10,  # IESO GA is in $/MWh, convert to ¢/kWh
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
            )
        except Exception as err:
            raise UpdateFailed(f"Error processing IESO data: {err}") from err
