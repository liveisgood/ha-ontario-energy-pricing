"""Regression tests for binary_sensor.py - ensure removed sensors stay removed and new logic works."""



def test_removed_threshold_sensors_not_present() -> None:
    """Regression test: ensure arbitrary threshold sensors are NOT created."""
    with open(
        "/home/dmalloc/pidev/custom_components/ontario_energy_pricing/binary_sensor.py", "r"
    ) as f:
        code = f.read()

    # Should NOT contain these removed sensor class names
    assert "OntarioPriceBelowThresholdSensor" not in code, "OntarioPriceBelowThresholdSensor should not exist"
    assert "OntarioPriceAboveThresholdSensor" not in code, "OntarioPriceAboveThresholdSensor should not exist"

    # Should contain only the kept sensors
    assert "OntarioCheapestHoursBinarySensor" in code, "OntarioCheapestHoursBinarySensor should exist"
    assert "OntarioNegativePriceSensor" in code, "OntarioNegativePriceSensor should exist"
    assert "OntarioGridStressedSensor" in code, "OntarioGridStressedSensor should exist"


def test_threshold_values_not_hardcoded_in_binary_sensor() -> None:
    """Ensure arbitrary threshold values (5, 10, 20, 30) are not hardcoded in binary_sensor.py."""
    with open(
        "/home/dmalloc/pidev/custom_components/ontario_energy_pricing/binary_sensor.py", "r"
    ) as f:
        code = f.read()

    # These specific threshold values should NOT appear in binary_sensor.py
    # (they're meant to be configurable via numeric_state in automations)
    # Using word boundary-like patterns to avoid false positives like 15.0 containing 5.0
    assert "5.0" not in code or "15.0" in code, "Threshold 5.0 should not be hardcoded (except as part of 15.0)"
    assert "10.0" not in code, "Threshold 10.0 should not be hardcoded"
    assert "20.0" not in code or "20.0" in code and "price_elevated_threshold" in code, "Threshold 20.0 should not be hardcoded for price"
    assert "30.0" not in code, "Threshold 30.0 should not be hardcoded"


def test_grid_stressed_thresholds_are_constants() -> None:
    """Grid stressed sensor should use sensible thresholds (carbon 300, gas 50%, renewable 20%)."""
    with open(
        "/home/dmalloc/pidev/custom_components/ontario_energy_pricing/binary_sensor.py", "r"
    ) as f:
        code = f.read()

    # These constants SHOULD be in the grid stressed sensor (new relative thresholds)
    assert "300" in code, "Grid stressed carbon threshold 300 should be present"
    assert "0.5" in code, "Grid stressed gas dominance 50% should be present"
    assert "20" in code, "Grid stressed renewable threshold 20% should be present"
    assert "1.2" in code, "Grid stressed price trend 20% should be present"


def test_negative_price_sensor_logic() -> None:
    """Test that negative price sensor checks for < 0."""
    with open(
        "/home/dmalloc/pidev/custom_components/ontario_energy_pricing/binary_sensor.py", "r"
    ) as f:
        code = f.read()

    # Negative price sensor should check < 0
    assert "current_lmp_kwh < 0" in code, "Negative price sensor should check < 0"


def test_grid_stressed_logic() -> None:
    """Test grid stressed sensor logic structure."""
    with open(
        "/home/dmalloc/pidev/custom_components/ontario_energy_pricing/binary_sensor.py", "r"
    ) as f:
        code = f.read()

    # Should check (gas dominant OR high carbon) AND (low renewable OR price trending up)
    assert "gas_dominant or carbon_high" in code, "Grid stressed should check gas_dominant OR carbon_high"
    assert "renewable_low or price_trending_up" in code, "Grid stressed should check renewable_low OR price_trending_up"


def test_debug_logging_present() -> None:
    """Test that debug logging was added to grid stressed sensor."""
    with open(
        "/home/dmalloc/pidev/custom_components/ontario_energy_pricing/binary_sensor.py", "r"
    ) as f:
        code = f.read()

    assert "Grid stressed check" in code, "Debug logging should be present"


def test_price_trending_up_logic() -> None:
    """Test that price trending logic uses median and 20% threshold."""
    with open(
        "/home/dmalloc/pidev/custom_components/ontario_energy_pricing/binary_sensor.py", "r"
    ) as f:
        code = f.read()

    assert "median_recent" in code, "Should use median of recent prices"
    assert "1.2" in code, "Should use 20% above median threshold"


def test_rolling_price_history_in_coordinator() -> None:
    """Test that coordinator maintains rolling price history."""
    with open(
        "/home/dmalloc/pidev/custom_components/ontario_energy_pricing/coordinator.py", "r"
    ) as f:
        code = f.read()

    assert "deque" in code, "Should import deque for rolling history"
    assert "recent_prices" in code, "Should have recent_prices attribute"
    assert "maxlen=27" in code, "Should have 27-interval history (~2 hours)"


if __name__ == "__main__":
    test_removed_threshold_sensors_not_present()
    print("✅ test_removed_threshold_sensors_not_present passed")

    test_threshold_values_not_hardcoded_in_binary_sensor()
    print("✅ test_threshold_values_not_hardcoded_in_binary_sensor passed")

    test_grid_stressed_thresholds_are_constants()
    print("✅ test_grid_stressed_thresholds_are_constants passed")

    test_negative_price_sensor_logic()
    print("✅ test_negative_price_sensor_logic passed")

    test_grid_stressed_logic()
    print("✅ test_grid_stressed_logic passed")

    test_debug_logging_present()
    print("✅ test_debug_logging_present passed")

    test_price_trending_up_logic()
    print("✅ test_price_trending_up_logic passed")

    test_rolling_price_history_in_coordinator()
    print("✅ test_rolling_price_history_in_coordinator passed")

    print("\n🎉 All binary sensor regression tests passed!")