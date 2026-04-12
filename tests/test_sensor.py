"""Tests for sensor entities."""

from __future__ import annotations


from custom_components.ontario_energy_pricing.const import (
    ATTR_PREVIOUS_RATE,
    ATTR_TIMESTAMP,
    ATTR_TRADE_MONTH,
    ATTR_ZONE,
)
from custom_components.ontario_energy_pricing.sensor import (
    OntarioGlobalAdjustmentSensor,
    OntarioLMP24hAverageSensor,
    OntarioLMPCurrentPriceSensor,
    OntarioTotalRateSensor,
)


class TestCurrentLMPSensor:
    """Tests for current LMP sensor."""

    def test_sensor_state(self, mock_coordinators) -> None:
        """Test sensor returns current LMP price."""
        sensor = OntarioLMPCurrentPriceSensor(mock_coordinators["lmp"])
        assert sensor.native_value == 0.0895

    def test_sensor_attributes(self, mock_coordinators) -> None:
        """Test sensor includes required attributes."""
        sensor = OntarioLMPCurrentPriceSensor(mock_coordinators["lmp"])
        attrs = sensor.extra_state_attributes
        assert ATTR_TIMESTAMP in attrs
        assert ATTR_ZONE in attrs
        assert attrs[ATTR_ZONE] == "OAKVILLE"
        assert ATTR_PREVIOUS_RATE in attrs

    def test_sensor_device_class(self, mock_coordinators) -> None:
        """Test sensor has MONETARY device class."""
        sensor = OntarioLMPCurrentPriceSensor(mock_coordinators["lmp"])
        assert "monetary" in str(sensor.device_class).lower()

    def test_sensor_unique_id(self, mock_coordinators) -> None:
        """Test sensor has correct unique_id."""
        sensor = OntarioLMPCurrentPriceSensor(mock_coordinators["lmp"])
        assert "current_lmp" in sensor.unique_id


class Test24hAverageSensor:
    """Tests for 24h average sensor."""

    def test_sensor_attributes(self, mock_coordinators) -> None:
        """Test sensor includes timestamp attribute."""
        sensor = OntarioLMP24hAverageSensor(mock_coordinators["lmp_24h"])
        attrs = sensor.extra_state_attributes
        assert ATTR_TIMESTAMP in attrs

    def test_sensor_device_class(self, mock_coordinators) -> None:
        """Test sensor has MONETARY device class."""
        sensor = OntarioLMP24hAverageSensor(mock_coordinators["lmp_24h"])
        assert "monetary" in str(sensor.device_class).lower()


class TestGlobalAdjustmentSensor:
    """Tests for GA sensor."""

    def test_sensor_state(self, mock_coordinators) -> None:
        """Test sensor returns GA rate."""
        sensor = OntarioGlobalAdjustmentSensor(mock_coordinators["ga"])
        assert sensor.native_value == 0.0485

    def test_sensor_attributes(self, mock_coordinators) -> None:
        """Test sensor includes trade_month attribute."""
        sensor = OntarioGlobalAdjustmentSensor(mock_coordinators["ga"])
        attrs = sensor.extra_state_attributes
        assert ATTR_TRADE_MONTH in attrs
        assert attrs[ATTR_TRADE_MONTH] == "2026-04"


class TestTotalRateSensor:
    """Tests for total rate sensor."""

    def test_sensor_calculation(self, mock_coordinators) -> None:
        """Test sensor calculates LMP + GA + Admin Fee."""
        sensor = OntarioTotalRateSensor(
            mock_coordinators["lmp"],
            mock_coordinators["ga"],
            0.025,
        )
        expected = 0.0895 + 0.0485 + 0.025
        assert abs(sensor.native_value - expected) < 0.001

    def test_sensor_missing_lmp(self, mock_coordinators) -> None:
        """Test sensor returns None when LMP missing."""
        mock_coordinators["lmp"].data = None
        sensor = OntarioTotalRateSensor(
            mock_coordinators["lmp"],
            mock_coordinators["ga"],
            0.025,
        )
        assert sensor.native_value is None

    def test_sensor_attributes(self, mock_coordinators) -> None:
        """Test sensor attributes show component values."""
        sensor = OntarioTotalRateSensor(
            mock_coordinators["lmp"],
            mock_coordinators["ga"],
            0.025,
        )
        attrs = sensor.extra_state_attributes
        assert attrs.get("lmp_rate") == 0.0895
        assert attrs.get("ga_rate") == 0.0485
        assert attrs.get("admin_fee") == 0.025
