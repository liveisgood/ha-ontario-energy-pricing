"""DataUpdateCoordinators for Ontario Energy Pricing."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import timedelta
from typing import TYPE_CHECKING

from homeassistant.core import HomeAssistant  # type: ignore
from homeassistant.helpers.aiohttp_client import async_get_clientsession  # type: ignore
from homeassistant.helpers.update_coordinator import (  # type: ignore
    DataUpdateCoordinator,
)

from .const import DOMAIN, LOGGER, UPDATE_INTERVAL_LMP
from .ieso_ga import IESOGlobalAdjustmentClient
from .ieso_lmp import IESOLMPClient

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant  # type: ignore


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
    intervals: list[dict] = field(default_factory=list)

    @property
    def total_rate(self) -> float:
        """Total rate in ¢/kWh."""
        return self.current_lmp_kwh + self.global_adjustment + self.admin_fee

    @property
    def total_rate_hour_avg(self) -> float:
        """Total rate using hour average LMP in ¢/kWh."""
        return self.hour_average_lmp_kwh + self.global_adjustment + self.admin_fee


class OntarioEnergyPricingCoordinator(DataUpdateCoordinator):
    """Unified coordinator for all Ontario Energy Pricing data."""

    def __init__(
        self,
        hass: HomeAssistant,
        admin_fee: float,
    ) -> None:
        """Initialize the unified coordinator."""
        self._admin_fee = admin_fee
        self._lmp_client: IESOLMPClient | None = None
        self._ga_client: IESOGlobalAdjustmentClient | None = None

        super().__init__(
            hass=hass,
            logger=LOGGER,
            name=f"{DOMAIN}_unified",
            update_interval=timedelta(seconds=UPDATE_INTERVAL_LMP),
        )

    async def _async_setup(self) -> None:
        """Set up clients after Home Assistant is ready."""
        session = async_get_clientsession(self.hass)
        self._lmp_client = IESOLMPClient(session=session)
        self._ga_client = IESOGlobalAdjustmentClient(session=session)

    async def _async_update_data(self) -> OntarioEnergyPricingData:
        """Fetch all pricing data from IESO."""
        if self._lmp_client is None or self._ga_client is None:
            await self._async_setup()

        assert self._lmp_client is not None
        assert self._ga_client is not None

        lmp_task = self._lmp_client.async_get_current_lmp()
        ga_task = self._ga_client.async_get_current_rate()

        lmp_data, ga_data = await asyncio.gather(lmp_task, ga_task)

        return OntarioEnergyPricingData(
            current_lmp_kwh=lmp_data.current_lmp_kwh,
            hour_average_lmp_kwh=lmp_data.hour_average_kwh,
            current_lmp_mwh=lmp_data.hour_average_mwh,
            delivery_hour=lmp_data.delivery_hour,
            delivery_date=lmp_data.delivery_date,
            global_adjustment=ga_data.rate * 100,
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
