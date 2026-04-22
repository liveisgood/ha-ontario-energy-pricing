"""Tests for IESO Global Adjustment client."""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import aiohttp
import pytest

from custom_components.ontario_energy_pricing.exceptions import IESOXMLParseError
from custom_components.ontario_energy_pricing.ieso_ga import (
    IESOGlobalAdjustmentClient,
)
from custom_components.ontario_energy_pricing.models import GlobalAdjustment


class TestIESOGlobalAdjustmentClient:
    """Test IESO Global Adjustment client."""

    @pytest.mark.asyncio
    async def test_async_get_current_rate_success(self, sample_ieso_ga_xml) -> None:
        """Test successful GA fetch."""
        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.text = AsyncMock(return_value=sample_ieso_ga_xml)
        mock_response.raise_for_status = MagicMock()
        mock_session.get = AsyncMock(return_value=mock_response)

        client = IESOGlobalAdjustmentClient(session=mock_session)
        result = await client.async_get_current_rate()

        assert isinstance(result, GlobalAdjustment)
        assert result.rate == 0.06
        assert result.trade_month == "2026-04"

    @pytest.mark.asyncio
    async def test_rate_conversion_to_cents(self, sample_ieso_ga_xml) -> None:
        """Test that rate is in $/kWh (to be converted to cents)."""
        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.text = AsyncMock(return_value=sample_ieso_ga_xml)
        mock_response.raise_for_status = MagicMock()
        mock_session.get = AsyncMock(return_value=mock_response)

        client = IESOGlobalAdjustmentClient(session=mock_session)
        result = await client.async_get_current_rate()

        # Rate should be in $/kWh from XML
        assert result.rate == 0.06  # $/kWh
        # In coordinator, this will be multiplied by 100 to get cents

    @pytest.mark.asyncio
    async def test_async_get_historical_rate(self) -> None:
        """Test fetching historical GA rate."""
        historical_xml = """<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="http://www.ieso.ca/schema">
  <PublishInfo>
    <PublishDateTime>2026-03-01T00:00:00</PublishDateTime>
  </PublishInfo>
  <GlobalAdjustment>
    <TradeMonth>2026-03</TradeMonth>
    <FirstEstimateRate>0.055</FirstEstimateRate>
  </GlobalAdjustment>
</Document>"""

        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.text = AsyncMock(return_value=historical_xml)
        mock_response.raise_for_status = MagicMock()
        mock_response.status = 200
        mock_session.get = AsyncMock(return_value=mock_response)

        client = IESOGlobalAdjustmentClient(session=mock_session)
        result = await client.async_get_historical_rates(2026, 3)

        assert result.rate == 0.055
        assert result.trade_month == "2026-03"

    @pytest.mark.asyncio
    async def test_historical_not_found(self) -> None:
        """Test 404 error for historical data."""
        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status = 404
        mock_response.raise_for_status.side_effect = (
            aiohttp.ClientResponseError(
                MagicMock(), (), status=404, message="Not Found"
            )
        )
        mock_session.get = AsyncMock(return_value=mock_response)

        client = IESOGlobalAdjustmentClient(session=mock_session)

        with pytest.raises(IESOXMLParseError) as exc_info:
            await client.async_get_historical_rates(2026, 1)
        assert "not found" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_invalid_xml(self) -> None:
        """Test handling of invalid XML."""
        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.text = AsyncMock(return_value="<invalid>")
        mock_response.raise_for_status = MagicMock()
        mock_session.get = AsyncMock(return_value=mock_response)

        client = IESOGlobalAdjustmentClient(session=mock_session)

        with pytest.raises(IESOXMLParseError) as exc_info:
            await client.async_get_current_rate()
        assert "Invalid XML" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_missing_trade_month(self) -> None:
        """Test XML missing TradeMonth element."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="http://www.ieso.ca/schema">
  <GlobalAdjustment>
    <FirstEstimateRate>0.06</FirstEstimateRate>
  </GlobalAdjustment>
</Document>"""

        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.text = AsyncMock(return_value=xml)
        mock_response.raise_for_status = MagicMock()
        mock_session.get = AsyncMock(return_value=mock_response)

        client = IESOGlobalAdjustmentClient(session=mock_session)

        with pytest.raises(IESOXMLParseError) as exc_info:
            await client.async_get_current_rate()
        assert "TradeMonth" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_missing_rate(self) -> None:
        """Test XML missing FirstEstimateRate element."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="http://www.ieso.ca/schema">
  <GlobalAdjustment>
    <TradeMonth>2026-04</TradeMonth>
  </GlobalAdjustment>
</Document>"""

        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.text = AsyncMock(return_value=xml)
        mock_response.raise_for_status = MagicMock()
        mock_session.get = AsyncMock(return_value=mock_response)

        client = IESOGlobalAdjustmentClient(session=mock_session)

        with pytest.raises(IESOXMLParseError) as exc_info:
            await client.async_get_current_rate()
        assert "FirstEstimateRate" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_invalid_rate_value(self) -> None:
        """Test XML with invalid rate value."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="http://www.ieso.ca/schema">
  <GlobalAdjustment>
    <TradeMonth>2026-04</TradeMonth>
    <FirstEstimateRate>invalid</FirstEstimateRate>
  </GlobalAdjustment>
</Document>"""

        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.text = AsyncMock(return_value=xml)
        mock_response.raise_for_status = MagicMock()
        mock_session.get = AsyncMock(return_value=mock_response)

        client = IESOGlobalAdjustmentClient(session=mock_session)

        with pytest.raises(IESOXMLParseError) as exc_info:
            await client.async_get_current_rate()
        assert "Invalid rate" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_current_month_fallback(self, sample_ieso_ga_xml) -> None:
        """Test fallback to current rate when historical fails."""
        mock_session = AsyncMock()

        # Historical request fails
        historical_response = AsyncMock()
        historical_response.status = 404
        historical_response.raise_for_status.side_effect = (
            aiohttp.ClientResponseError(
                MagicMock(), (), status=404, message="Not Found"
            )
        )

        # Current request succeeds
        current_response = AsyncMock()
        current_response.text = AsyncMock(return_value=sample_ieso_ga_xml)
        current_response.raise_for_status = MagicMock()

        mock_session.get = AsyncMock(side_effect=[
            historical_response,
            current_response,
        ])

        client = IESOGlobalAdjustmentClient(session=mock_session)
        result = await client.async_get_rates_for_current_month()

        assert result.rate ==        assert result.rate == 0.06

    @pytest.mark.asyncio
    async def test_xml_snippet_in_error(self) -> None:
        """Test that XML snippet is included in parse errors."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="http://www.ieso.ca/schema">
  <Invalid>
</Document>"""

        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.text = AsyncMock(return_value=xml)
        mock_response.raise_for_status = MagicMock()
        mock_session.get = AsyncMock(return_value=mock_response)

        client = IESOGlobalAdjustmentClient(session=mock_session)

        try:
            await client.async_get_current_rate()
            assert False, "Should have raised IESOXMLParseError"
        except IESOXMLParseError as e:
            # XML snippet should be in error
            assert e.xml_snippet is not None
