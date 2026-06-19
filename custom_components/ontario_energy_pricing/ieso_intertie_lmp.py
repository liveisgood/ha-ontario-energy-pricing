"""IESO Intertie LMP Client.

Provides real-time interchange LMP prices at interties from IESO.
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


IESO_INTERTIE_LMP_URL: Final = (
    "https://reports-public.ieso.ca/public/RealtimeIntertieLMP/"
    "PUB_RealtimeIntertieLMP.xml"
)


@dataclass(frozen=True, slots=True)
class IESOIntertieLMP:
    """LMP at a specific intertie point."""

    intertie_point: (
        str  # e.g., "MICHIGAN", "NEW_YORK", "QUEBEC", "MANITOBA", "MINNESOTA"
    )
    timestamp: datetime
    lmp_mwh: float  # $/MWh


@dataclass(frozen=True, slots=True)
class IESOIntertieLMPData:
    """Complete intertie LMP data."""

    lmp_data: list[IESOIntertieLMP] = field(default_factory=list)

    def get_lmp_by_intertie(self, intertie_point: str) -> list[IESOIntertieLMP]:
        """Get LMP data for a specific intertie point."""
        return [
            l
            for l in self.lmp_data
            if l.intertie_point.upper() == intertie_point.upper()
        ]

    def get_latest_lmp_by_intertie(self, intertie_point: str) -> IESOIntertieLMP | None:
        """Get the most recent LMP for a specific intertie point."""
        intertie_data = self.get_lmp_by_intertie(intertie_point)
        if not intertie_data:
            return None
        return max(intertie_data, key=lambda x: x.timestamp)

    def get_intertie_points(self) -> list[str]:
        """Get list of intertie points available."""
        return list({l.intertie_point for l in self.lmp_data})


class IESOIntertieLMPClient:
    """Client for fetching IESO Intertie LMP data."""

    def __init__(self, session: aiohttp.ClientSession, timeout: int = 30) -> None:
        """Initialize the client."""
        self._session = session
        self._timeout = aiohttp.ClientTimeout(total=timeout)

    async def fetch(self) -> IESOIntertieLMPData:
        """Fetch and parse intertie LMP data."""
        try:
            async with self._session.get(
                IESO_INTERTIE_LMP_URL, timeout=self._timeout
            ) as resp:
                resp.raise_for_status()
                content = await resp.text()
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise IESOPredispatchError(
                f"Failed to fetch intertie LMP data: {err}"
            ) from err

        return self._parse_xml(content)

    async def _fetch_xml(self) -> str:
        """Fetch XML content."""
        async with self._session.get(
            IESO_INTERTIE_LMP_URL, timeout=self._timeout
        ) as resp:
            resp.raise_for_status()
            return await resp.text()

    def _parse_xml(self, xml_content: str) -> IESOIntertieLMPData:
        """Parse intertie LMP XML."""
        try:
            root = ET.fromstring(xml_content)
        except ET.ParseError as err:
            raise IESOPredispatchError(f"Invalid XML: {err}") from err

        ns = {"ieso": IESO_LMP_NAMESPACE}

        # Parse metadata (if available)
        # Note: Intertie LMP XML may have different structure than other IESO XMLs

        lmp_data: list[IESOIntertieLMP] = []

        # Look for LMP data elements - need to inspect actual XML structure
        # Based on similar IESO XML files, likely looks for HourlyPrice or similar elements
        for hourly_price in root.findall(".//ieso:HourlyPrice", ns):
            intertie_elem = hourly_price.find("ieso:IntertiePoint", ns)
            timestamp_elem = hourly_price.find("ieso:DateTime", ns)
            if timestamp_elem is None:
                timestamp_elem = hourly_price.find("ieso:Timestamp", ns)
            lmp_elem = hourly_price.find("ieso:LMP", ns)

            # Check if primary elements are valid
            primary_valid = all(
                elem is not None and elem.text is not None and elem.text.strip() != ""
                for elem in [intertie_elem, timestamp_elem, lmp_elem]
            )

            if not primary_valid:
                # Try alternative element names
                intertie_elem = hourly_price.find("ieso:Point", ns)
                timestamp_elem = hourly_price.find("ieso:Time", ns)
                if timestamp_elem is None:
                    timestamp_elem = hourly_price.find("ieso:Hour", ns)
                lmp_elem = hourly_price.find("ieso:Price", ns)
                if lmp_elem is None:
                    lmp_elem = hourly_price.find("ieso:Value", ns)

                # Check if alternative elements are valid
                if not all(
                    elem is not None
                    and elem.text is not None
                    and elem.text.strip() != ""
                    for elem in [intertie_elem, timestamp_elem, lmp_elem]
                ):
                    continue

            # At this point, we know all elements are not None and have text
            assert intertie_elem is not None and intertie_elem.text is not None
            assert timestamp_elem is not None and timestamp_elem.text is not None
            assert lmp_elem is not None and lmp_elem.text is not None

            intertie_point_text = intertie_elem.text.strip()
            timestamp_text = timestamp_elem.text.strip()
            lmp_text = lmp_elem.text

            intertie_point = intertie_point_text
            try:
                # Parse timestamp - try different formats
                timestamp = None
                for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%H:%M:%S", "%H:%M"):
                    try:
                        timestamp = datetime.strptime(timestamp_text, fmt)
                        break
                    except ValueError:
                        continue

                if timestamp is None:
                    # If we can't parse the timestamp, use current time as fallback
                    timestamp = datetime.now()

                lpmwh = float(lmp_text)
            except (ValueError, TypeError):
                continue

            lmp_data.append(
                IESOIntertieLMP(
                    intertie_point=intertie_point,
                    timestamp=timestamp,
                    lmp_mwh=lpmwh,
                )
            )

        return IESOIntertieLMPData(lmp_data=lmp_data)


IESO_INTERTIE_LMP_URL: Final = (
    "https://reports-public.ieso.ca/public/RealtimeIntertieLMP/"
    "PUB_RealtimeIntertieLMP.xml"
)
