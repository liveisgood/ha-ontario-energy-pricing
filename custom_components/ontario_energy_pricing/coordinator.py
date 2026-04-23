"""DataUpdateCoordinators for Ontario Energy Pricing."""

from __future__ import annotations

import asyncio
import traceback
from dataclasses import dataclass, field
from datetime import timedelta
from typing import TYPE_CHECKING, Any

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

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
        LOGGER.debug(
            "[COORDINATOR] __init__ called: admin_fee=%s, update_interval=%s",
            admin_fee,
            UPDATE_INTERVAL_LMP,
        )
        super().__init__(
            hass=hass,
            logger=LOGGER,
            name=f"{DOMAIN}_unified",
            update_interval=timedelta(seconds=UPDATE_INTERVAL_LMP),
        )
        LOGGER.debug("[COORDINATOR] super().__init__ completed successfully")

    async def _async_setup(self) -> None:
        """Set up clients after Home Assistant is ready."""
        LOGGER.debug("[COORDINATOR] _async_setup: creating aiohttp client session...")
        try:
            from homeassistant.helpers.aiohttp_client import async_get_clientsession

            session = async_get_clientsession(self.hass)
            LOGGER.debug(
                "[COORDINATOR] _async_setup: got client session: %s",
                type(session).__name__,
            )
        except Exception as err:
            LOGGER.error(
                "[COORDINATOR] _async_setup FAILED to get client session: %s\n%s",
                err,
                traceback.format_exc(),
            )
            raise

        try:
            self._lmp_client = IESOLMPClient(session)
            self._ga_client = IESOGlobalAdjustmentClient(session)
            LOGGER.debug(
                "[COORDINATOR] _async_setup: clients created: lmp=%s, ga=%s",
                type(self._lmp_client).__name__,
                type(self._ga_client).__name__,
            )
        except Exception as err:
            LOGGER.error(
                "[COORDINATOR] _async_setup FAILED to create clients: %s\n%s",
                err,
                traceback.format_exc(),
            )
            raise

    async def _async_update_data(self) -> OntarioEnergyPricingData:
        """Fetch all pricing data from IESO."""
        LOGGER.debug("[COORDINATOR] _async_update_data called")

        if self._lmp_client is None or self._ga_client is None:
            LOGGER.debug("[COORDINATOR] Clients not initialized, calling _async_setup")
            await self._async_setup()
            assert self._lmp_client is not None
            assert self._ga_client is not None

        try:
            LOGGER.debug("[COORDINATOR] Fetching LMP data from IESO...")
            lmp_task = self._lmp_client.async_get_current_lmp()

            LOGGER.debug("[COORDINATOR] Fetching GA data from IESO...")
            ga_task = self._ga_client.async_get_current_rate()

            LOGGER.debug("[COORDINATOR] Awaiting both fetches (asyncio.gather)...")
            lmp_data, ga_data = await asyncio.gather(lmp_task, ga_task)

            LOGGER.debug(
                "[COORDINATOR] Fetch successful: lmp_date=%s, lmp_hour=%s, lmp_intervals=%d, ga_rate=%s, ga_month=%s",
                lmp_data.delivery_date,
                lmp_data.delivery_hour,
                len(lmp_data.intervals),
                ga_data.rate,
                ga_data.trade_month,
            )
        except IESOXMLParseError as err:
            LOGGER.error(
                "[COORDINATOR] IESOXMLParseError during fetch: %s\n%s",
                err,
                traceback.format_exc(),
            )
            raise
        except Exception as err:
            LOGGER.error(
                "[COORDINATOR] UNEXPECTED error during fetch: %s (type=%s)\n%s",
                err,
                type(err).__name__,
                traceback.format_exc(),
            )
            raise

        try:
            result = OntarioEnergyPricingData(
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
            LOGGER.debug(
                "[COORDINATOR] Data assembled: lmp_kwh=%s, ga=%s, admin_fee=%s, total=%s, intervals=%d",
                result.current_lmp_kwh,
                result.global_adjustment,
                result.admin_fee,
                result.total_rate,
                len(result.intervals),
            )
            return result
        except Exception as err:
            LOGGER.error(
                "[COORDINATOR] FAILED to assemble OntarioEnergyPricingData: %s\n%s",
                err,
                traceback.format_exc(),
            )
            raise
