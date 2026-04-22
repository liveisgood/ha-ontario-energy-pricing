"""DataUpdateCoordinators for Ontario Energy Pricing."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import timedelta
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN, LOGGER, UPDATE_INTERVAL_LMP
from .exceptions import IESOXMLParseError
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
            update_interval=timedelta(seconds=UPDATE_INTERVAL_LMP),
        )

    async def _async_setup(self) -> None:
        """Set up clients after Home Assistant is ready."""
        from homeassistant.helpers.aiohttp_client import async_get_clientsession

        session = async_get_clientsession(self.hass)
        self._lmp_client = IESOLMPClient(session)
        self._ga_client = IESOGlobalAdjustmentClient(session)

    async def _async_update_data(self) -> OntarioEnergyPricingData:
        """Fetch all pricing data from IESO."""
        if self._lmp_client is None or self._ga_client is None:
            await self._async_setup()

        assert self._lmp_client is not None
        assert self._ga_client is not None

        try:
            lmp_task = self._lmp_client.async_get_current_lmp()
            ga_task = self._ga_client.async_get_current_rate()
            lmp_data, ga_data = await asyncio.gather(lmp_task, ga_task)
        except IESOXMLParseError as err:
            self.logger.error("Failed to fetch IESO data: %s", err)
            raise

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
