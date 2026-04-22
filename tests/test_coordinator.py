"""Tests for data update coordinators."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.ontario_energy_pricing.const import (
    UPDATE_INTERVAL_LMP,
)
from custom_components.ontario_energy_pricing.coordinator import (
    OntarioEnergyPricingCoordinator,
    OntarioEnergyPricingData,
)
from custom_components.ontario_energy_pricing.exceptions import (
    IESOLMPError,
    IESOXMLParseError,
)


@pytest.mark.asyncio
async def test_coordinator_update_success(mock_hass, sample_coordinator_data) -> None:
    """Test unified coordinator successfully fetches LMP and GA data."""
    with patch(
        "custom_components.ontario_energy_pricing.coordinator.async_get_clientsession"
    ):
        with patch(
            "custom_components.ontario_energy_pricing.coordinator.IESOLMPClient"
        ) as mock_lmp_class:
            with patch(
                "custom_components.ontario_energy_pricing.coordinator.IESOGlobalAdjustmentClient"
            ) as mock_ga_class:
                # Setup mocks
                mock_lmp = MagicMock()
                mock_lmp.async_get_current_lmp = AsyncMock(
                    return_value=MagicMock(
                        current_lmp_kwh=sample_coordinator_data.current_lmp_kwh,
                        hour_average_kwh=sample_coordinator_data.hour_average_lmp_kwh,
                        hour_average_mwh=sample_coordinator_data.current_lmp_mwh,
                        delivery_hour=sample_coordinator_data.delivery_hour,
                        delivery_date=sample_coordinator_data.delivery_date,
                        intervals=[
                            MagicMock(
                                interval=i["interval"],
                                lmp_kwh=i["lmp_kwh"],
                                lmp_mwh=i["lmp_mwh"],
                                flag=i["flag"],
                            )
                            for i in sample_coordinator_data.intervals
                        ],
                    )
                )
                mock_lmp_class.return_value = mock_lmp

                mock_ga = MagicMock()
                mock_ga.async_get_current_rate = AsyncMock(
                    return_value=MagicMock(
                        rate=sample_coordinator_data.global_adjustment / 100,
                        trade_month=sample_coordinator_data.trade_month,
                    )
                )
                mock_ga_class.return_value = mock_ga

                coordinator = OntarioEnergyPricingCoordinator(
                    hass=mock_hass, admin_fee=1.45
                )
                result = await coordinator._async_update_data()

                assert isinstance(result, OntarioEnergyPricingData)
                assert result.current_lmp_kwh == sample_coordinator_data.current_lmp_kwh
                assert (
                    result.global_adjustment
                    == sample_coordinator_data.global_adjustment
                )


@pytest.mark.asyncio
async def test_coordinator_lmp_failure(mock_hass) -> None:
    """Test coordinator raises UpdateFailed on LMP error."""
    with patch(
        "custom_components.ontario_energy_pricing.coordinator.async_get_clientsession"
    ):
        with patch(
            "custom_components.ontario_energy_pricing.coordinator.IESOLMPClient"
        ) as mock_lmp_class:
            mock_lmp = MagicMock()
            mock_lmp.async_get_current_lmp = AsyncMock(
                side_effect=IESOLMPError("Failed to fetch LMP")
            )
            mock_lmp_class.return_value = mock_lmp

            coordinator = OntarioEnergyPricingCoordinator(
                hass=mock_hass, admin_fee=1.45
            )

            with pytest.raises(UpdateFailed) as exc_info:
                await coordinator._async_update_data()
            assert "LMP" in str(exc_info.value)


@pytest.mark.asyncio
async def test_coordinator_ga_failure(mock_hass) -> None:
    """Test coordinator raises UpdateFailed on GA error."""
    with patch(
        "custom_components.ontario_energy_pricing.coordinator.async_get_clientsession"
    ):
        with patch(
            "custom_components.ontario_energy_pricing.coordinator.IESOLMPClient"
        ) as mock_lmp_class:
            mock_lmp = MagicMock()
            mock_lmp.async_get_current_lmp = AsyncMock(return_value=MagicMock())
            mock_lmp_class.return_value = mock_lmp

            with patch(
                "custom_components.ontario_energy_pricing.coordinator.IESOGlobalAdjustmentClient"
            ) as mock_ga_class:
                mock_ga = MagicMock()
                mock_ga.async_get_current_rate = AsyncMock(
                    side_effect=IESOXMLParseError("Invalid GA XML")
                )
                mock_ga_class.return_value = mock_ga

                coordinator = OntarioEnergyPricingCoordinator(
                    hass=mock_hass, admin_fee=1.45
                )

                with pytest.raises(UpdateFailed) as exc_info:
                    await coordinator._async_update_data()
                assert "GA" in str(exc_info.value) or "IESO" in str(exc_info.value)


@pytest.mark.asyncio
async def test_coordinator_update_interval(mock_hass) -> None:
    """Test coordinator has correct update interval."""
    with patch(
        "custom_components.ontario_energy_pricing.coordinator.async_get_clientsession"
    ):
        coordinator = OntarioEnergyPricingCoordinator(hass=mock_hass, admin_fee=1.45)
        assert coordinator.update_interval.total_seconds() == UPDATE_INTERVAL_LMP


@pytest.mark.asyncio
async def test_coordinator_calculated_rates(mock_hass, sample_coordinator_data) -> None:
    """Test coordinator calculates total rates correctly."""
    with patch(
        "custom_components.ontario_energy_pricing.coordinator.async_get_clientsession"
    ):
        with patch(
            "custom_components.ontario_energy_pricing.coordinator.IESOLMPClient"
        ) as mock_lmp_class:
            with patch(
                "custom_components.ontario_energy_pricing.coordinator.IESOGlobalAdjustmentClient"
            ) as mock_ga_class:
                # Setup mocks with known data
                mock_lmp = MagicMock()
                mock_lmp.async_get_current_lmp = AsyncMock(
                    return_value=MagicMock(
                        current_lmp_kwh=5.0,
                        hour_average_kwh=5.5,
                        hour_average_mwh=55.0,
                        delivery_hour=14,
                        delivery_date="2026-04-12",
                        intervals=[],
                    )
                )
                mock_lmp_class.return_value = mock_lmp

                mock_ga = MagicMock()
                mock_ga.async_get_current_rate = AsyncMock(
                    return_value=MagicMock(rate=0.06, trade_month="2026-04")
                )
                mock_ga_class.return_value = mock_ga

                coordinator = OntarioEnergyPricingCoordinator(
                    hass=mock_hass, admin_fee=1.45
                )
                result = await coordinator._async_update_data()

                # Check calculations
                assert result.current_lmp_kwh == 5.0
                assert result.global_adjustment == 6.0  # 0.06 * 100
                assert result.admin_fee == 1.45
                assert result.total_rate == 12.45  # 5.0 + 6.0 + 1.45
