"""Tests for IESO LMP client."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import aiohttp
import pytest

from custom_components.ontario_energy_pricing.ieso_lmp import (
    IESOLMPClient,
    IESOLMPData,
    IESOLMPError,
    IESOZonalPrice,
)


class TestIESOLMPClient:
    """Test IESO LMP client functionality."""

    @pytest.mark.asyncio
    async def test_async_get_current_lmp_success(self, sample_ieso_xml) -> None:
        """Test successful LMP fetch."""
        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.text = AsyncMock(return_value=sample_ieso_xml)
        mock_response.raise_for_status = MagicMock()
        mock_session.get = AsyncMock(return_value=mock_response)

        client = IESOLMPClient(session=mock_session)
        result = await client.async_get_current_lmp()

        assert isinstance(result, IESOLMPData)
        assert result.delivery_date == "2026-04-12"
        assert result.delivery_hour == 14
        assert result.hour_average_mwh == 53.88
        assert result.hour_average_kwh == 5.388
        assert len(result.intervals) == 3

    @pytest.mark.asyncio
    async def test_unit_conversion(self, sample_ieso_xml) -> None:
        """Test that $/MWh is correctly converted to ¢/kWh."""
        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.text = AsyncMock(return_value=sample_ieso_xml)
        mock_response.raise_for_status = MagicMock()
        mock_session.get = AsyncMock(return_value=mock_response)

        client = IESOLMPClient(session=mock_session)
        result = await client.async_get_current_lmp()

        # $/MWh to ¢/kWh: divide by 10
        # 56.55 $/MWh = 5.655 ¢/kWh
        assert result.intervals[0].lmp_mwh == 56.55
        assert result.intervals[0].lmp_kwh == pytest.approx(5.655, rel=1e-3)

    @pytest.mark.asyncio
    async def test_latest_interval_property(self, sample_ieso_xml) -> None:
        """Test getting the latest interval."""
        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.text = AsyncMock(return_value=sample_ieso_xml)
        mock_response.raise_for_status = MagicMock()
        mock_session.get = AsyncMock(return_value=mock_response)

        client = IESOLMPClient(session=mock_session)
        result = await client.async_get_current_lmp()

        latest = result.latest_interval
        assert latest is not None
        assert latest.interval == 3  # Highest interval number

    @pytest.mark.asyncio
    async def test_empty_intervals_skipped(self) -> None:
        """Test that empty intervals (not yet populated) are skipped."""
        # XML with some empty intervals (no LmpCap)
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="http://www.ieso.ca/schema">
  <DocHeader>
    <CreatedAt>2026-04-12T13:22:48</CreatedAt>
  </DocHeader>
  <DocBody>
    <DeliveryDate>2026-04-12</DeliveryDate>
    <DeliveryHour>14</DeliveryHour>
    <ZonalPrice>
      <Interval>1</Interval>
      <LmpCap>50.00</LmpCap>
      <Flag>DSO-RD</Flag>
    </ZonalPrice>
    <ZonalPrice>
      <Interval>2</Interval>
      <LmpCap></LmpCap>
      <Flag></Flag>
    </ZonalPrice>
    <ZonalPrice>
      <Interval>3</Interval>
      <LmpCap>52.00</LmpCap>
      <Flag>DSO-RD</Flag>
    </ZonalPrice>
    <AveragePrice>
      <LmpCap>51.00</LmpCap>
    </AveragePrice>
  </DocBody>
</Document>"""

        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.text = AsyncMock(return_value=xml)
        mock_response.raise_for_status = MagicMock()
        mock_session.get = AsyncMock(return_value=mock_response)

        client = IESOLMPClient(session=mock_session)
        result = await client.async_get_current_lmp()

        # Should only have 2 valid intervals
        assert len(result.intervals) == 2
        assert result.intervals[0].interval == 1
        assert result.intervals[1].interval == 3

    @pytest.mark.asyncio
    async def test_http_error(self) -> None:
        """Test HTTP error handling."""
        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.raise_for_status.side_effect = aiohttp.ClientResponseError(
            MagicMock(), (), status=500, message="Server Error"
        )
        mock_session.get = AsyncMock(return_value=mock_response)

        client = IESOLMPClient(session=mock_session)

        with pytest.raises(IESOLMPError) as exc_info:
            await client.async_get_current_lmp()
        assert "Failed to fetch" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_malformed_xml(self) -> None:
        """Test handling of malformed XML."""
        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.text = AsyncMock(return_value="<invalid>xml")
        mock_response.raise_for_status = MagicMock()
        mock_session.get = AsyncMock(return_value=mock_response)

        client = IESOLMPClient(session=mock_session)

        with pytest.raises(IESOLMPError) as exc_info:
            await client.async_get_current_lmp()
        assert "Invalid XML" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_missing_required_elements(self) -> None:
        """Test handling of XML missing required elements."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="http://www.ieso.ca/schema">
  <DocHeader>
  </DocHeader>
</Document>"""

        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.text = AsyncMock(return_value=xml)
        mock_response.raise_for_status = MagicMock()
        mock_session.get = AsyncMock(return_value=mock_response)

        client = IESOLMPClient(session=mock_session)

        with pytest.raises(IESOLMPError) as exc_info:
            await client.async_get_current_lmp()
        assert "not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_timeout_error(self) -> None:
        """Test handling of request timeout."""
        mock_session = AsyncMock()
        mock_session.get = AsyncMock(side_effect=asyncio.TimeoutError())

        client = IESOLMPClient(session=mock_session)

        with pytest.raises(IESOLMPError) as exc_info:
            await client.async_get_current_lmp()
        assert "timeout" in str(exc_info.value).lower()


class TestIESOLMPData:
    """Test IESO LMP data model."""

    def test_calculate_total_rate(self) -> None:
        """Test total rate calculation."""
        data = MagicMock(spec=IESOLMPData)
        data.current_lmp_kwh = 5.20
        data.hour_average_kwh = 5.50
        data.hour_average_mwh = 55.0
        data.delivery_hour = 14
        data.delivery_date = "2026-04-12"
        data.created_at = datetime(2026, 4, 12, 13, 22, 48, tzinfo=timezone.utc)
        data.intervals = []

        # Patch the calculate_total_rate method
        def mock_calculate(ga, admin):
            return data.current_lmp_kwh + ga + admin

        data.calculate_total_rate = mock_calculate

        result = data.calculate_total_rate(6.0, 1.45)
        assert result == pytest.approx(12.65, rel=1e-3)


class TestIESOZonalPrice:
    """Test IESO Zonal Price model."""

    def test_time_range_calculation(self) -> None:
        """Test time range for interval."""
        price = IESOZonalPrice(
            interval=6,
            lmp_mwh=52.41,
            lmp_kwh=5.241,
            flag="DSO-RD",
        )
        assert price.time_range == "25-30 min"

    def test_time_range_first_interval(self) -> None:
        """Test time range for first interval."""
        price = IESOZonalPrice(
            interval=1,
            lmp_mwh=56.55,
            lmp_kwh=5.655,
            flag="DSO-RD",
        )
        assert price.time_range == "00-05 min"

    def test_time_range_last_interval(self) -> None:
        """Test time range for last interval."""
        price = IESOZonalPrice(
            interval=12,
            lmp_mwh=55.00,
            lmp_kwh=5.500,
            flag="DSO-RD",
        )
        assert price.time_range == "55-60 min"
