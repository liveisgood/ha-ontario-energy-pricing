"""Unit tests for models.py - VGForecastData, FuelMixData, PriceThresholds."""

import logging
from datetime import datetime

logging.basicConfig(level=logging.WARNING)

# Load models module
with open('/home/dmalloc/pidev/custom_components/ontario_energy_pricing/models.py', 'r') as f:
    code = f.read()

namespace = {'logging': logging}
exec(code, namespace)

VGForecastData = namespace['VGForecastData']
FuelMixData = namespace['FuelMixData']
PriceThresholds = namespace['PriceThresholds']


def test_vg_forecast_total_vg_mw():
    """Test total VG MW calculation."""
    now = datetime.now()
    solar = {12: 500.0, 13: 800.0, 14: 1000.0}
    wind = {12: 300.0, 13: 400.0, 14: 600.0}

    vg = VGForecastData(
        forecast_timestamp=now,
        solar_forecast_mw=solar,
        wind_forecast_mw=wind,
    )

    assert vg.total_vg_mw(12) == 800.0
    assert vg.total_vg_mw(13) == 1200.0
    assert vg.total_vg_mw(14) == 1600.0
    assert vg.total_vg_mw(15) == 0.0  # not in forecast


def test_vg_forecast_high_vg_hour():
    """Test high VG hour detection."""
    now = datetime.now()
    vg = VGForecastData(
        forecast_timestamp=now,
        solar_forecast_mw={12: 1500.0},
        wind_forecast_mw={12: 1500.0},  # Total 3000 MW
    )

    assert vg.is_high_vg_hour(12, threshold_mw=1000.0) is True
    assert vg.is_high_vg_hour(12, threshold_mw=3000.0) is True
    assert vg.is_high_vg_hour(12, threshold_mw=3001.0) is False
    assert vg.is_high_vg_hour(13) is False


def test_vg_forecast_negative_price_probability():
    """Test negative price probability heuristic."""
    now = datetime.now()

    # Very high VG (3000+ MW) - high probability
    vg_high = VGForecastData(
        forecast_timestamp=now,
        solar_forecast_mw={12: 2000.0},
        wind_forecast_mw={12: 1500.0},  # 3500 total
    )
    assert vg_high.negative_price_probability(12) >= 0.7

    # High VG (2000+ MW) - medium probability (base 0.4 * 1.3 solar peak = 0.52)
    vg_med = VGForecastData(
        forecast_timestamp=now,
        solar_forecast_mw={12: 1000.0},
        wind_forecast_mw={12: 1200.0},  # 2200 total
    )
    prob = vg_med.negative_price_probability(12)
    assert 0.3 <= prob <= 0.6  # 0.4 * 1.3 = 0.52

    # Medium VG (1000+ MW) - low probability
    vg_low = VGForecastData(
        forecast_timestamp=now,
        solar_forecast_mw={12: 600.0},
        wind_forecast_mw={12: 500.0},  # 1100 total
    )
    assert vg_low.negative_price_probability(12) <= 0.2

    # Low VG - very low probability
    vg_very_low = VGForecastData(
        forecast_timestamp=now,
        solar_forecast_mw={12: 100.0},
        wind_forecast_mw={12: 200.0},  # 300 total
    )
    assert vg_very_low.negative_price_probability(12) <= 0.05

    # Probability capped at 0.95
    vg_extreme = VGForecastData(
        forecast_timestamp=now,
        solar_forecast_mw={2: 5000.0},
        wind_forecast_mw={2: 5000.0},  # 10000 total
    )
    assert vg_extreme.negative_price_probability(2) <= 0.95

    # Overnight hours (2-5) get 1.5x multiplier
    vg_overnight = VGForecastData(
        forecast_timestamp=now,
        solar_forecast_mw={3: 1000.0},
        wind_forecast_mw={3: 1000.0},
    )
    day_prob = vg_overnight.negative_price_probability(12)
    night_prob = vg_overnight.negative_price_probability(3)
    assert night_prob > day_prob

    # Solar peak hours (10-16) get 1.3x multiplier
    vg_solar = VGForecastData(
        forecast_timestamp=now,
        solar_forecast_mw={14: 1000.0},
        wind_forecast_mw={14: 1000.0},
    )
    solar_peak_prob = vg_solar.negative_price_probability(14)
    off_peak_prob = vg_solar.negative_price_probability(8)
    assert solar_peak_prob > off_peak_prob


def test_fuel_mix_totals():
    """Test fuel mix total calculations."""
    mix = FuelMixData(
        timestamp=datetime.now(),
        nuclear_mw=9000.0,
        hydro_mw=3000.0,
        wind_mw=2000.0,
        solar_mw=500.0,
        gas_mw=4000.0,
        biofuel_mw=100.0,
        other_mw=50.0,
    )

    assert mix.total_mw == 18650.0
    assert mix.renewable_mw == 14600.0  # nuclear + hydro + wind + solar + biofuel
    assert mix.thermal_mw == 4050.0  # gas + other
    assert abs(mix.renewable_percentage - (14600 / 18650 * 100)) < 0.01


def test_fuel_mix_carbon_intensity():
    """Test carbon intensity calculation."""
    # Pure nuclear - very low carbon
    nuclear_only = FuelMixData(
        timestamp=datetime.now(),
        nuclear_mw=10000.0,
    )
    assert nuclear_only.carbon_intensity_gco2_per_kwh == 12.0

    # Pure gas - high carbon
    gas_only = FuelMixData(
        timestamp=datetime.now(),
        gas_mw=5000.0,
    )
    assert gas_only.carbon_intensity_gco2_per_kwh == 400.0

    # Mixed - weighted average
    mixed = FuelMixData(
        timestamp=datetime.now(),
        nuclear_mw=5000.0,  # 12 gCO2
        gas_mw=5000.0,      # 400 gCO2
    )
    # (5000*12 + 5000*400) / 10000 = 206 gCO2/kWh
    assert abs(mixed.carbon_intensity_gco2_per_kwh - 206.0) < 0.01


def test_fuel_mix_zero_generation():
    """Test edge case with zero generation."""
    empty = FuelMixData(timestamp=datetime.now())
    assert empty.total_mw == 0.0
    assert empty.renewable_mw == 0.0
    assert empty.thermal_mw == 0.0
    assert empty.renewable_percentage == 0.0
    assert empty.carbon_intensity_gco2_per_kwh == 0.0


def test_price_thresholds_defaults():
    """Test PriceThresholds default values."""
    pt = PriceThresholds()
    assert pt.pool_pump_on_below == 5.0
    assert pt.ac_precool_below == 10.0
    assert pt.ac_setback_above == 20.0
    assert pt.shed_all_above == 30.0


def test_price_thresholds_custom():
    """Test PriceThresholds with custom values."""
    pt = PriceThresholds(
        pool_pump_on_below=3.0,
        ac_precool_below=8.0,
        ac_setback_above=25.0,
        shed_all_above=40.0,
    )
    assert pt.pool_pump_on_below == 3.0
    assert pt.ac_precool_below == 8.0
    assert pt.ac_setback_above == 25.0
    assert pt.shed_all_above == 40.0


if __name__ == "__main__":
    test_vg_forecast_total_vg_mw()
    print("✅ test_vg_forecast_total_vg_mw passed")

    test_vg_forecast_high_vg_hour()
    print("✅ test_vg_forecast_high_vg_hour passed")

    test_vg_forecast_negative_price_probability()
    print("✅ test_vg_forecast_negative_price_probability passed")

    test_fuel_mix_totals()
    print("✅ test_fuel_mix_totals passed")

    test_fuel_mix_carbon_intensity()
    print("✅ test_fuel_mix_carbon_intensity passed")

    test_fuel_mix_zero_generation()
    print("✅ test_fuel_mix_zero_generation passed")

    test_price_thresholds_defaults()
    print("✅ test_price_thresholds_defaults passed")

    test_price_thresholds_custom()
    print("✅ test_price_thresholds_custom passed")

    print("\n🎉 All model tests passed!")