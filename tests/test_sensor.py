"""Tests for sensor entities."""

from __future__ import annotations



from custom_components.ontario_energy_pricing.sensor import (
    OntarioCurrentLMPSensor,
    OntarioGlobalAdjustmentSensor,
    OntarioHourAverageLMPSensor,
    OntarioTotalRateSensor,
)


class TestCurrentLMPSensor:
    """Tests for current LMP sensor."""

    def test_sensor_state(self, mock_coordinator) -> None:
        """Test sensor returns current LMP price."""
        sensor = OntarioCurrentLMPSensor(mock_coordinator)
        assert sensor.native_value == 5.241

    def test_sensor_unit(self, mock_coordinator) -> None:
        """Test sensor has MONETARY device class."""
        sensor = OntarioCurrentLMPSensor(mock_coordinator)
        assert "monetary" in str(sensor.device_class).lower()

    def test_sensor_attributes(self, mock_coordinator) -> None:
        """Test sensor includes required attributes."""
        sensor = OntarioCurrentLMPSensor(mock_coordinator)
        attrs = sensor.extra_state_attributes

        assert "lmp_mwh" in attrs
        assert attrs["lmp_mwh"] == 53.88
        assert attrs["delivery_hour"] == 14
        assert attrs["delivery_date"] == "2026-04-12"
        assert attrs["trade_month"] == "2026-04"

    def test_sensor_unique_id(self, mock_coordinator) -> None:
        """Test sensor has correct unique_id."""
        sensor = OntarioCurrentLMPSensor(mock_coordinator)
        assert "current_lmp" in sensor.unique_id

    def test_sensor_icon(self, mock_coordinator) -> None:
        """Test sensor has correct icon."""
        sensor = OntarioCurrentLMPSensor(mock_coordinator)
        assert sensor._attr_icon == "mdi:lightning-bolt"


class TestHourAverageLMPSensor:
    """Tests for hour average LMP sensor."""

    def test_sensor_state(self, mock_coordinator) -> None:
        """Test sensor returns hour average LMP."""
        sensor = OntarioHourAverageLMPSensor(mock_coordinator)
        assert sensor.native_value == 5.388

    def test_sensor_device_class(self, mock_coordinator) -> None:
        """Test sensor has MONETARY device class."""
        sensor = OntarioHourAverageLMPSensor(mock_coordinator)
        assert "monetary" in str(sensor.device_class).lower()

    def test_sensor_icon(self, mock_coordinator) -> None:
        """Test sensor has correct icon."""
        sensor = OntarioHourAverageLMPSensor(mock_coordinator)
        assert sensor._attr_icon == "mdi:chart-line"


class TestGlobalAdjustmentSensor:
    """Tests for GA sensor."""

    def test_sensor_state(self, mock_coordinator) -> None:
        """Test sensor returns GA rate in cents."""
        sensor = OntarioGlobalAdjustmentSensor(mock_coordinator)
        # GA rate is 0.06 $/kWh * 100 = 6.0 ¢/kWh
        assert sensor.native_value == 6.0

    def test_sensor_attributes(self, mock_coordinator) -> None:
        """Test sensor includes trade_month attribute."""
        sensor = OntarioGlobalAdjustmentSensor(mock_coordinator)
        attrs = sensor.extra_state_attributes

        assert attrs.get("trade_month") == "2026-04"

    def test_sensor_icon(self, mock_coordinator) -> None:
        """Test sensor has correct icon."""
        sensor = OntarioGlobalAdjustmentSensor(mock_coordinator)
        assert sensor._attr_icon == "mdi:cash"


class TestTotalRateSensor:
    """Tests for total rate sensor."""

    def test_sensor_calculation(self, mock_coordinator) -> None:
        """Test sensor calculates LMP + GA + Admin Fee correctly."""
        sensor = OntarioTotalRateSensor(mock_coordinator)

        # 5.241 + 6.0 + 1.45 = 12.691
        expected = 5.241 + 6.0 + 1.45
        assert abs(sensor.native_value - expected) < 0.001

    def test_sensor_attributes(self, mock_coordinator) -> None:
        """Test sensor attributes show component values."""
        sensor = OntarioTotalRateSensor(mock_coordinator)
        attrs = sensor.extra_state_attributes

        assert attrs.get("lmp_rate") == 5.241
        assert attrs.get("ga_rate") == 6.0
        assert attrs.get("admin_fee") == 1.45

    def test_sensor_missing_data(self, mock_coordinator) -> None:
        """Test sensor returns None when coordinator data is missing."""
        mock_coordinator.data = None
        sensor = OntarioTotalRateSensor(mock_coordinator)
        assert sensor.native_value is None

    def test_sensor_empty_attributes(self, mock_coordinator) -> None:
        """Test sensor returns empty attributes when data is missing."""
        mock_coordinator.data = None
        sensor = OntarioTotalRateSensor(mock_coordinator)
        attrs = sensor.extra_state_attributes
        assert attrs == {}

    def test_sensor_icon(self, mock_coordinator) -> None:
        """Test sensor has correct icon."""
        sensor = OntarioTotalRateSensor(mock_coordinator)
        assert sensor._attr_icon == "mdi:scale-balance"


class TestSensorUnitConversion:
    """Tests for unit conversion verification."""

    def test_lmp_cents_per_kwh(self, mock_coordinator) -> None:
        """Verify LMP is in cents per kWh."""
        sensor = OntarioCurrentLMPSensor(mock_coordinator)
        # 53.88 $/MWh / 10 = 5.388 ¢/kWh
        assert 0 < sensor.native_value < 50  # Reasonable cents range

    def test_ga_cents_per_kwh(self, mock_coordinator) -> None:
        """Verify GA is converted to cents per kWh."""
        sensor = OntarioGlobalAdjustmentSensor(mock_coordinator)
        # 0.06 $/kWh * 100 = 6.0 ¢/kWh
        assert 0 < sensor.native_value < 20  # Reasonable GA range
