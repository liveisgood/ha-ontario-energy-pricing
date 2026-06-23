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


class TestIESOZonalPrice:
    """Tests for IESOZonalPrice dataclass."""

    def test_time_range_calculation(self) -> None:
        """Test time range for interval."""
        price = IESOZonalPrice(
            interval=11,
            lmp_mwh=56.55,
            lmp_kwh=5.655,
            flag="DSO-RD",
        )
        assert price.time_range == "50-55 min"

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


class TestIESOLMPData:
    """Tests for IESOLMPData dataclass."""

    def test_calculate_total_rate(self) -> None:
        """Test total rate calculation."""
        intervals = [
            IESOZonalPrice(interval=1, lmp_mwh=50.0, lmp_kwh=5.0, flag=""),
            IESOZonalPrice(interval=2, lmp_mwh=60.0, lmp_kwh=6.0, flag=""),
        ]
        data = IESOLMPData(
            zone="TORONTO",
            delivery_date="2026-04-12",
            delivery_hour=14,
            created_at=datetime(2026, 4, 12, 13, 22, 48, tzinfo=timezone.utc),
            intervals=intervals,
        )

        # Average of 50 and 60 = 55 $/MWh = 5.5 ¢/kWh
        assert data.hour_average_mwh == 55.0
        assert data.hour_average_kwh() == 5.5


class TestIESOLMPClient:
    """Test IESO LMP client functionality."""

    @pytest.fixture
    def sample_ieso_xml(self) -> str:
        """Sample IESO LMP XML response (matches real RealtimeZonalEnergyPrices feed)."""
        return """<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="http://www.ieso.ca/schema">
  <DocHeader>
    <DocTitle>Realtime 5-min Virtual Zonal Energy Prices Report</DocTitle>
    <DocRevision>1</DocRevision>
    <DocConfidentiality>
      <DocConfClass>PUB</DocConfClass>
    </DocConfidentiality>
    <CreatedAt>2026-04-12T13:22:48</CreatedAt>
  </DocHeader>
  <DocBody>
    <DELIVERYDATE>2026-04-12</DELIVERYDATE>
    <DELIVERYHOUR>14</DELIVERYHOUR>
    <ZonalPrices>
      <TransactionZone>
        <ZoneName>TORONTO:HUB</ZoneName>
        <IntervalPrice>
          <Interval>1</Interval>
          <ZonalPrice>56.55</ZonalPrice>
          <EnergyLossPrice>0.0</EnergyLossPrice>
          <EnergyCongPrice>0.0</EnergyCongPrice>
          <FlagNo>0</FlagNo>
        </IntervalPrice>
        <IntervalPrice>
          <Interval>2</Interval>
          <ZonalPrice>52.41</ZonalPrice>
          <EnergyLossPrice>0.0</EnergyLossPrice>
          <EnergyCongPrice>0.0</EnergyCongPrice>
          <FlagNo>0</FlagNo>
        </IntervalPrice>
        <IntervalPrice>
          <Interval>3</Interval>
          <ZonalPrice>51.23</ZonalPrice>
          <EnergyLossPrice>0.0</EnergyLossPrice>
          <EnergyCongPrice>0.0</EnergyCongPrice>
          <FlagNo>0</FlagNo>
        </IntervalPrice>
      </TransactionZone>
    </ZonalPrices>
  </DocBody>
</Document>"""

    @pytest.mark.asyncio
    async def test_async_get_current_lmp_success(self, sample_ieso_xml) -> None:
        """Test successful LMP fetch."""
        mock_session = AsyncMock()

        # Create a proper async context manager mock
        mock_response = AsyncMock()
        mock_response.text = AsyncMock(return_value=sample_ieso_xml)
        mock_response.raise_for_status = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        mock_session.get = MagicMock(return_value=mock_response)

        client = IESOLMPClient(session=mock_session)
        result = await client.async_get_current_lmp()

        assert isinstance(result, IESOLMPData)
        assert result.delivery_date == "2026-04-12"
        assert result.delivery_hour == 14
        assert result.hour_average_mwh == 53.39666666666667  # (56.55+52.41+51.23)/3
        assert result.hour_average_kwh() == 5.339666666666667
        assert len(result.intervals) == 3

    @pytest.mark.asyncio
    async def test_unit_conversion(self, sample_ieso_xml) -> None:
        """Test that $/MWh is correctly converted to ¢/kWh."""
        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.text = AsyncMock(return_value=sample_ieso_xml)
        mock_response.raise_for_status = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        mock_session.get = MagicMock(return_value=mock_response)

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
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        mock_session.get = MagicMock(return_value=mock_response)

        client = IESOLMPClient(session=mock_session)
        result = await client.async_get_current_lmp()

        latest = result.latest_interval
        assert latest is not None
        assert latest.interval == 3  # Highest interval number

    @pytest.mark.asyncio
    async def test_empty_intervals_skipped(self) -> None:
        """Test that empty intervals (not yet populated) are skipped."""
        # XML with some empty intervals (no ZonalPrice text)
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="http://www.ieso.ca/schema">
  <DocHeader>
    <CreatedAt>2026-04-12T13:22:48</CreatedAt>
  </DocHeader>
  <DocBody>
    <DELIVERYDATE>2026-04-12</DELIVERYDATE>
    <DELIVERYHOUR>14</DELIVERYHOUR>
    <ZonalPrices>
      <TransactionZone>
        <ZoneName>TORONTO:HUB</ZoneName>
        <IntervalPrice>
          <Interval>1</Interval>
          <ZonalPrice>50.00</ZonalPrice>
          <EnergyLossPrice>0.0</EnergyLossPrice>
          <EnergyCongPrice>0.0</EnergyCongPrice>
          <FlagNo>0</FlagNo>
        </IntervalPrice>
        <IntervalPrice>
          <Interval>2</Interval>
          <ZonalPrice></ZonalPrice>
          <EnergyLossPrice></EnergyLossPrice>
          <EnergyCongPrice></EnergyCongPrice>
          <FlagNo></FlagNo>
        </IntervalPrice>
        <IntervalPrice>
          <Interval>3</Interval>
          <ZonalPrice>52.00</ZonalPrice>
          <EnergyLossPrice>0.0</EnergyLossPrice>
          <EnergyCongPrice>0.0</EnergyCongPrice>
          <FlagNo>0</FlagNo>
        </IntervalPrice>
      </TransactionZone>
    </ZonalPrices>
  </DocBody>
</Document>"""

        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.text = AsyncMock(return_value=xml)
        mock_response.raise_for_status = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        mock_session.get = MagicMock(return_value=mock_response)

        client = IESOLMPClient(session=mock_session)
        result = await client.async_get_current_lmp()

        # Should only have 2 intervals (interval 2 was empty)
        assert len(result.intervals) == 2
        assert result.intervals[0].interval == 1
        assert result.intervals[1].interval == 3

    @pytest.mark.asyncio
    async def test_http_error(self) -> None:
        """Test handling of HTTP errors."""
        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock(side_effect=aiohttp.ClientError("404 Not Found"))
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        mock_session.get = MagicMock(return_value=mock_response)

        client = IESOLMPClient(session=mock_session)

        with pytest.raises(IESOLMPError) as exc_info:
            await client.async_get_current_lmp()
        assert "Failed to fetch IESO LMP" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_malformed_xml(self) -> None:
        """Test handling of malformed XML."""
        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.text = AsyncMock(return_value="<invalid>xml")
        mock_response.raise_for_status = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        mock_session.get = MagicMock(return_value=mock_response)

        client = IESOLMPClient(session=mock_session)

        with pytest.raises(IESOLMPError) as exc_info:
            await client.async_get_current_lmp()
        assert "Invalid XML" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_missing_required_elements(self) -> None:
        """Test handling of missing required XML elements."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="http://www.ieso.ca/schema">
  <DocHeader>
    <CreatedAt>2026-04-12T13:22:48</CreatedAt>
  </DocHeader>
  <DocBody>
    <!-- Missing DELIVERYDATE and DELIVERYHOUR -->
  </DocBody>
</Document>"""

        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.text = AsyncMock(return_value=xml)
        mock_response.raise_for_status = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        mock_session.get = MagicMock(return_value=mock_response)

        client = IESOLMPClient(session=mock_session)

        with pytest.raises(IESOLMPError) as exc_info:
            await client.async_get_current_lmp()
        assert "not found" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_timeout_error(self) -> None:
        """Test handling of request timeout."""
        mock_session = AsyncMock()
        # Simulate timeout in the async context manager
        async def mock_get(*args, **kwargs):
            raise asyncio.TimeoutError()
        mock_session.get = mock_get

        client = IESOLMPClient(session=mock_session)

        with pytest.raises(IESOLMPError) as exc_info:
            await client.async_get_current_lmp()
        # The error should mention timeout or the original exception
        assert "timeout" in str(exc_info.value).lower() or exc_info.value.__cause__ is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])