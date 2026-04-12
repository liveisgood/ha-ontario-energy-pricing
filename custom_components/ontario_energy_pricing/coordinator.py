"""DataUpdateCoordinators for Ontario Energy Pricing."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

from homeassistant.core import HomeAssistant  # type: ignore
from homeassistant.helpers.aiohttp_client import async_get_clientsession  # type: ignore
from homeassistant.helpers.update_coordinator import (  # type: ignore
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.util import dt as dt_util  # type: ignore

from .const import (
    DOMAIN,
    LOGGER,
    UPDATE_INTERVAL_LMP,
    UPDATE_INTERVAL_GA,
    UPDATE_INTERVAL_24H_AVG,
)
from .exceptions import (
    GridStatusAPIError,
    GridStatusAuthError,
    GridStatusConnectionError,
    IESOXMLParseError,
)
from .gridstatus import GridStatusClient
from .ieso import IESOGlobalAdjustmentClient
from .models import GlobalAdjustment, LMPCurrentPrice, LMPHistoricalData

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant  # type: ignore


class OntarioEnergyPricingDataUpdateCoordinator(DataUpdateCoordinator):
    """Base coordinator for Ontario Energy Pricing."""

    def __init__(
        self,
        hass: HomeAssistant,
        name: str,
        update_interval: timedelta | None = None,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass=hass,
            logger=LOGGER,
            name=name,
            update_interval=update_interval,
        )


class LMPCoordinator(OntarioEnergyPricingDataUpdateCoordinator):
    """Coordinator for current LMP data."""

    def __init__(
        self,
        hass: HomeAssistant,
        api_key: str,
        zone: str,
    ) -> None:
        """Initialize the LMP coordinator."""
        self._zone = zone
        self._previous_price: float | None = None
        session = async_get_clientsession(hass)
        self._client = GridStatusClient(api_key=api_key, session=session)
        super().__init__(
            hass=hass,
            name=f"{DOMAIN}_lmp_{zone}",
            update_interval=timedelta(seconds=UPDATE_INTERVAL_LMP),
        )

    async def _async_update_data(self) -> LMPCurrentPrice:
        """Fetch current LMP data from GridStatus."""
        try:
            data = await self._client.async_get_current_lmp(zone=self._zone)
            # Store previous price before updating
            if data.price is not None:
                self._previous_price = data.price
            return data
        except GridStatusAuthError as err:
            # Auth errors - don't retry, fail immediately
            LOGGER.error("Authentication failed for LMP fetch: %s", err)
            raise UpdateFailed(f"Authentication failed: {err}") from err
        except (GridStatusAPIError, GridStatusConnectionError) as err:
            # Transient errors - coordinator will retry automatically
            LOGGER.warning("LMP fetch failed, will retry: %s", err)
            raise UpdateFailed(f"Failed to fetch LMP data: {err}") from err
        except Exception as err:
            # Unexpected errors - coordinator will retry
            LOGGER.exception("Unexpected error during LMP fetch: %s", err)
            raise UpdateFailed(f"Unexpected error: {err}") from err

    @property
    def previous_price(self) -> float | None:
        """Return the previous price (from last successful update)."""
        return self._previous_price


class LMP24hAverageCoordinator(OntarioEnergyPricingDataUpdateCoordinator):
    """Coordinator for 24-hour LMP average."""

    def __init__(
        self,
        hass: HomeAssistant,
        api_key: str,
        zone: str,
    ) -> None:
        """Initialize the 24h average coordinator."""
        self._zone = zone
        session = async_get_clientsession(hass)
        self._client = GridStatusClient(api_key=api_key, session=session)
        super().__init__(
            hass=hass,
            name=f"{DOMAIN}_lmp_24h_{zone}",
            update_interval=timedelta(seconds=UPDATE_INTERVAL_24H_AVG),
        )

    async def _async_update_data(self) -> LMPHistoricalData:
        """Fetch 24h LMP data and aggregate to 30-min averages."""
        try:
            data = await self._client.async_get_24h_history(zone=self._zone)
            return data
        except GridStatusAuthError as err:
            LOGGER.error("Authentication failed for 24h LMP fetch: %s", err)
            raise UpdateFailed(f"Authentication failed: {err}") from err
        except (GridStatusAPIError, GridStatusConnectionError) as err:
            LOGGER.warning("24h LMP fetch failed, will retry: %s", err)
            raise UpdateFailed(f"Failed to fetch 24h LMP data: {err}") from err
        except Exception as err:
            LOGGER.exception("Unexpected error during 24h LMP fetch: %s", err)
            raise UpdateFailed(f"Unexpected error: {err}") from err

    def get_24h_average(self) -> float | None:
        """Calculate and return the 24-hour average price."""
        if not self.data:
            return None
        return self.data.aggregate_to_30min()


class GlobalAdjustmentCoordinator(OntarioEnergyPricingDataUpdateCoordinator):
    """Coordinator for Global Adjustment data."""

    def __init__(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Initialize the GA coordinator."""
        self._current_trade_month: str | None = None
        self._last_valid_rate: float | None = None
        self._last_valid_date: dt_util.datetime | None = None
        session = async_get_clientsession(hass)
        self._client = IESOGlobalAdjustmentClient(session=session)
        super().__init__(
            hass=hass,
            name=f"{DOMAIN}_ga",
            update_interval=timedelta(seconds=UPDATE_INTERVAL_GA),
        )

    async def _async_update_data(self) -> GlobalAdjustment:
        """Fetch Global Adjustment data from IESO."""
        try:
            data = await self._client.async_get_current_rate()

            # Check if trade_month changed (weekly check)
            if (
                self._current_trade_month
                and data.trade_month == self._current_trade_month
            ):
                LOGGER.debug(
                    "Trade month unchanged (%s), keeping current data",
                    data.trade_month,
                )
                # Return cached data
                if self.data:
                    return self.data

            # Update trade month and store valid rate with timestamp
            self._current_trade_month = data.trade_month
            self._last_valid_rate = data.rate
            self._last_valid_date = dt_util.utcnow()
            return data

        except IESOXMLParseError as err:
            # Parse errors - check staleness
            LOGGER.warning("GA XML parse failed: %s", err)

            if self._last_valid_date is not None:
                age = dt_util.utcnow() - self._last_valid_date
                if age > timedelta(days=7):
                    # Data is stale (> 7 days), mark unavailable
                    LOGGER.error("GA data is stale (> 7 days), marking unavailable")
                    self._last_valid_rate = None
                    self._last_valid_date = None
                    raise UpdateFailed(f"GA data stale: {err}") from err

            # Return cached value (or None if never successfully fetched)
            LOGGER.debug("Returning cached GA rate: %s", self._last_valid_rate)
            if self._last_valid_rate is not None:
                # Create a GlobalAdjustment with cached rate
                return GlobalAdjustment(
                    trade_month=self._current_trade_month or "unknown",
                    rate=self._last_valid_rate,
                    last_updated=self._last_valid_date or dt_util.utcnow(),
                )
            return self.data  # Fallback to last known data

        except Exception as err:
            LOGGER.exception("Unexpected error during GA fetch: %s", err)
            raise UpdateFailed(f"Failed to fetch GA: {err}") from err

    @property
    def current_rate(self) -> float | None:
        """Return the current GA rate."""
        if self.data:
            return self.data.rate
        return None

    @property
    def trade_month(self) -> str | None:
        """Return the current trade month."""
        if self.data:
            return self.data.trade_month
        return None
