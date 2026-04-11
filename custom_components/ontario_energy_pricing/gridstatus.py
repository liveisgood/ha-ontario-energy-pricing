"""GridStatus API client for Ontario LMP data."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any, Final

import aiohttp  # type: ignore[import]

from .const import (
    GRIDSTATUS_API_BASE_URL,
    GRIDSTATUS_DATASET_LMP,
    GRIDSTATUS_DEFAULT_TIMEOUT,
    LOGGER,
)
from .exceptions import (
    GridStatusAPIError,
    GridStatusAuthError,
    GridStatusConnectionError,
)
from .models import LMPCurrentPrice, LMPDataPoint, LMPHistoricalData


class GridStatusClient:
    """Client for GridStatus.io IESO LMP API."""

    _DATASET: Final = GRIDSTATUS_DATASET_LMP

    def __init__(
        self,
        api_key: str,
        session: aiohttp.ClientSession,
    ) -> None:
        """Initialize the GridStatus client."""
        self._api_key = api_key
        self._session = session
        self._base_url = GRIDSTATUS_API_BASE_URL

    async def async_get_current_lmp(
        self,
        zone: str,
    ) -> LMPCurrentPrice:
        """Get current LMP for a zone."""
        now = datetime.now(timezone.utc)
        start = now - timedelta(hours=2)
        end = now

        history = await self._fetch_lmp_data(zone, start, end, limit=2)

        if not history.data_points:
            raise GridStatusAPIError(f"No LMP data returned for zone {zone}")

        current = history.data_points[-1]
        previous = (
            history.data_points[-2].price if len(history.data_points) > 1 else None
        )

        return LMPCurrentPrice(
            price=current.price,
            timestamp=current.timestamp,
            zone=zone,
            previous_price=previous,
        )

    async def async_get_24h_history(
        self,
        zone: str,
    ) -> LMPHistoricalData:
        """Get 24 hours of LMP history."""
        now = datetime.now(timezone.utc)
        start = now - timedelta(hours=24)
        end = now

        return await self._fetch_lmp_data(zone, start, end, limit=300)

    async def async_get_available_zones(self) -> list[str]:
        """Get list of available zones from API."""
        params = {
            "limit": 100,
            "select": "location",
        }

        data = await self._make_request("/query", params)

        if not isinstance(data, list):
            raise GridStatusAPIError("Unexpected response format")

        zones = {row["location"] for row in data if row.get("location")}
        return sorted(zones)

    async def _fetch_lmp_data(
        self,
        zone: str,
        start: datetime,
        end: datetime,
        limit: int = 300,
    ) -> LMPHistoricalData:
        """Fetch LMP data from GridStatus API."""
        params: dict[str, Any] = {
            "filter_column": "location",
            "filter_value": zone,
            "start": start.isoformat(),
            "end": end.isoformat(),
            "limit": limit,
            "timezone": "US/Eastern",
        }

        data = await self._make_request("/query", params)

        if not isinstance(data, list):
            raise GridStatusAPIError("Unexpected response format")

        data_points: list[LMPDataPoint] = []
        for row in data:
            try:
                ts_str = row.get("interval_start_local") or row.get(
                    "interval_start_utc"
                )
                price = float(row.get("lmp", row.get("price", 0)))

                if ts_str:
                    ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                    data_points.append(LMPDataPoint(timestamp=ts, price=price))
            except (ValueError, TypeError) as err:
                LOGGER.warning("Skipping invalid row: %s", err)

        return LMPHistoricalData(data_points=data_points, zone=zone)

    async def _make_request(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
    ) -> Any:
        """Make authenticated request to GridStatus API."""
        url = f"{self._base_url}/datasets/{self._DATASET}{endpoint}"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Accept": "application/json",
        }

        try:
            async with asyncio.timeout(GRIDSTATUS_DEFAULT_TIMEOUT):
                async with self._session.get(
                    url,
                    headers=headers,
                    params=params,
                ) as response:
                    if response.status == 401:
                        raise GridStatusAuthError("Invalid GridStatus API key")
                    elif response.status >= 500:
                        raise GridStatusAPIError(
                            f"GridStatus API error: {response.status}",
                            status_code=response.status,
                        )
                    response.raise_for_status()
                    return await response.json()

        except aiohttp.ClientResponseError as err:
            raise GridStatusAPIError(
                f"GridStatus API request failed: {err.message}",
                status_code=err.status,
            ) from err
        except aiohttp.ClientConnectorError as err:
            raise GridStatusConnectionError(
                f"Cannot connect to GridStatus: {err}"
            ) from err
        except TimeoutError as err:
            raise GridStatusConnectionError("GridStatus API timeout") from err
