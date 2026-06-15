"""IESO Real-Time Constraints Shadow Prices Client.

Provides real-time congestion shadow prices from IESO.
Shadow price = cost of transmission congestion ($/MWh).
High shadow price = constraint binding = grid congestion.
"""

from __future__ import annotations

import asyncio
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime
from typing import Final

import aiohttp

from .const import IESO_LMP_NAMESPACE
from .exceptions import IESOPredispatchError


IESO_SHADOW_PRICES_URL: Final = (
    "https://reports-public.ieso.ca/public/RealtimeConstrShadowPrices/"
    "PUB_RealtimeConstrShadowPrices.xml"
)


@dataclass(frozen=True, slots=True)
class IESOShadowPriceInterval:
    """Single 5-minute interval shadow price."""

    interval: int  # 1-12
    shadow_price: float  # $/MWh


@dataclass(frozen=True, slots=True)
class IESOHourlyShadowPrice:
    """Hourly shadow prices for a constraint (12 intervals)."""

    hour: int  # 1-24
    intervals: dict[int, float] = field(default_factory=dict)

    def get_interval(self, interval: int) -> float | None:
        """Get shadow price for a specific 5-min interval."""
        return self.intervals.get(interval)

    def max_price(self) -> float:
        """Maximum shadow price in the hour."""
        if not self.intervals:
            return 0.0
        return max(self.intervals.values())

    def avg_price(self) -> float:
        """Average shadow price in the hour."""
        if not self.intervals:
            return 0.0
        return sum(self.intervals.values()) / len(self.intervals)


@dataclass(frozen=True, slots=True)
class IESOConstraintShadowPrice:
    """Shadow prices for a specific transmission constraint."""

    constraint_name: str
    hourly_prices: dict[int, "IESOHourlyShadowPrice"] = field(default_factory=dict)

    def get_hour(self, hour: int) -> "IESOHourlyShadowPrice | None":
        """Get shadow prices for a specific hour."""
        return self.hourly_prices.get(hour)


@dataclass(frozen=True, slots=True)
class IESOShadowPricesData:
    """Complete shadow prices data for all constraints."""

    delivery_date: str
    created_at: datetime
    constraints: dict[str, IESOConstraintShadowPrice] = field(default_factory=dict)

    def get_constraint(
        self, constraint_name: str
    ) -> "IESOConstraintShadowPrice | None":
        """Get shadow prices for a specific constraint."""
        return self.constraints.get(constraint_name)

    def get_max_shadow_price(self, hour: int) -> float:
        """Get maximum shadow price across all constraints for a specific hour."""
        max_price = 0.0
        for constraint in self.constraints.values():
            hour_data = constraint.get_hour(hour)
            if hour_data:
                max_price = max(max_price, hour_data.max_price())
        return max_price

    def get_current_hour_shadow_price(self) -> float:
        """Get max shadow price for the current hour (approximate)."""
        current_hour = datetime.now().hour
        # IESO hours are 1-24
        ieso_hour = current_hour if current_hour > 0 else 24
        return self.get_max_shadow_price(ieso_hour)


class IESOShadowPricesClient:
    """Client for fetching IESO Real-Time Constraints Shadow Prices."""

    def __init__(self, session: aiohttp.ClientSession, timeout: int = 30) -> None:
        """Initialize the client."""
        self._session = session
        self._timeout = aiohttp.ClientTimeout(total=timeout)

    async def fetch(self) -> IESOShadowPricesData:
        """Fetch and parse shadow prices data."""
        try:
            async with self._session.get(
                IESO_SHADOW_PRICES_URL, timeout=self._timeout
            ) as resp:
                resp.raise_for_status()
                content = await resp.text()
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise IESOPredispatchError(f"Failed to fetch shadow prices: {err}") from err

        return self._parse_xml(content)

    async def _fetch_xml(self) -> str:
        """Fetch XML content."""
        async with self._session.get(
            IESO_SHADOW_PRICES_URL, timeout=self._timeout
        ) as resp:
            resp.raise_for_status()
            return await resp.text()

    def _parse_xml(self, xml_content: str) -> IESOShadowPricesData:
        """Parse shadow prices XML."""
        try:
            root = ET.fromstring(xml_content)
        except ET.ParseError as err:
            raise IESOPredispatchError(f"Invalid XML: {err}") from err

        ns = {"ieso": IESO_LMP_NAMESPACE}

        # Parse metadata
        created_at_elem = root.find(".//ieso:CreatedAt", ns)
        delivery_date_elem = root.find(".//ieso:DELIVERYDATE", ns)

        if not all(
            elem is not None and elem.text
            for elem in [created_at_elem, delivery_date_elem]
        ):
            raise IESOPredispatchError("Required XML elements not found")

        assert created_at_elem is not None and created_at_elem.text
        assert delivery_date_elem is not None and delivery_date_elem.text

        created_at = datetime.fromisoformat(created_at_elem.text)
        delivery_date = delivery_date_elem.text.strip()

        constraints: dict[str, IESOConstraintShadowPrice] = {}

        # Parse HourlyPrice elements
        for hourly_price in root.findall(".//ieso:HourlyPrice", ns):
            constraint_elem = hourly_price.find("ieso:ConstraintName", ns)
            hour_elem = hourly_price.find("ieso:DeliveryHour", ns)

            if constraint_elem is None or constraint_elem.text is None:
                continue
            if hour_elem is None or hour_elem.text is None:
                continue

            constraint_name = constraint_elem.text.strip()
            try:
                hour = int(hour_elem.text)
            except ValueError:
                continue

            if not 1 <= hour <= 24:
                continue

            # Get or create constraint
            if constraint_name not in constraints:
                constraints[constraint_name] = IESOConstraintShadowPrice(
                    constraint_name=constraint_name
                )

            constraint = constraints[constraint_name]

            # Get or create hour
            if hour not in constraint.hourly_prices:
                constraint.hourly_prices[hour] = IESOHourlyShadowPrice(hour=hour)

            hour_data = constraint.hourly_prices[hour]

            # Parse intervals - they are siblings under IntervalShadowPrices
            interval_shadow_prices = hourly_price.find("ieso:IntervalShadowPrices", ns)
            if interval_shadow_prices is not None:
                # Get all Interval and ShadowPrice elements as siblings
                intervals_elem = interval_shadow_prices.findall("ieso:Interval", ns)
                prices_elem = interval_shadow_prices.findall("ieso:ShadowPrice", ns)

                # Pair them up (they should be in order)
                for interval_elem, price_elem in zip(intervals_elem, prices_elem):
                    if interval_elem is None or interval_elem.text is None:
                        continue
                    if price_elem is None or price_elem.text is None:
                        continue

                    try:
                        interval = int(interval_elem.text)
                        price = float(price_elem.text) if price_elem.text else 0.0
                    except (ValueError, TypeError):
                        continue

                    if 1 <= interval <= 12:
                        hour_data.intervals[interval] = price

        return IESOShadowPricesData(
            delivery_date=delivery_date_elem.text.strip()
            if delivery_date_elem is not None and delivery_date_elem.text
            else "",
            created_at=datetime.fromisoformat(created_at_elem.text)
            if created_at_elem is not None and created_at_elem.text
            else datetime.now(),
            constraints=constraints,
        )
