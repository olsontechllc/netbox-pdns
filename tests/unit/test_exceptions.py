"""Tests for custom exceptions."""

from netbox_pdns.exceptions import (
    ConfigurationError,
    MQTTConnectionError,
    MQTTMessageError,
    NetboxAPIError,
    NetboxPDNSError,
    PowerDNSAPIError,
    ValidationError,
    ZoneNotFoundError,
    ZoneSyncError,
)


class TestNetboxPDNSError:
    """Test the base exception class."""

    def test_base_exception(self) -> None:
        """Test base exception creation."""
        error = NetboxPDNSError("Test error")
        assert str(error) == "Test error"
        assert isinstance(error, Exception)


class TestConfigurationError:
    """Test configuration errors."""

    def test_configuration_error(self) -> None:
        """Test configuration error creation."""
        error = ConfigurationError("Invalid config")
        assert str(error) == "Invalid config"
        assert isinstance(error, NetboxPDNSError)


class TestAPIErrors:
    """Test API-related errors."""

    def test_netbox_api_error_without_status(self) -> None:
        """Test Netbox API error without status code."""
        error = NetboxAPIError("Connection failed")
        assert str(error) == "Connection failed"
        assert error.status_code is None
        assert isinstance(error, NetboxPDNSError)

    def test_netbox_api_error_with_status(self) -> None:
        """Test Netbox API error with status code."""
        error = NetboxAPIError("Not found", 404)
        assert str(error) == "Not found"
        assert error.status_code == 404

    def test_powerdns_api_error_without_status(self) -> None:
        """Test PowerDNS API error without status code."""
        error = PowerDNSAPIError("Connection failed")
        assert str(error) == "Connection failed"
        assert error.status_code is None
        assert isinstance(error, NetboxPDNSError)

    def test_powerdns_api_error_with_status(self) -> None:
        """Test PowerDNS API error with status code."""
        error = PowerDNSAPIError("Unauthorized", 401)
        assert str(error) == "Unauthorized"
        assert error.status_code == 401


class TestZoneErrors:
    """Test zone-related errors."""

    def test_zone_not_found_error(self) -> None:
        """Test zone not found error."""
        error = ZoneNotFoundError("example.com")
        assert str(error) == "Zone not found: example.com"
        assert error.zone_name == "example.com"
        assert isinstance(error, NetboxPDNSError)

    def test_zone_sync_error(self) -> None:
        """Test zone sync error."""
        error = ZoneSyncError("example.com", "Serial mismatch")
        assert str(error) == "Error syncing zone example.com: Serial mismatch"
        assert error.zone_name == "example.com"
        assert isinstance(error, NetboxPDNSError)


class TestMQTTErrors:
    """Test MQTT-related errors."""

    def test_mqtt_connection_error(self) -> None:
        """Test MQTT connection error."""
        error = MQTTConnectionError("Broker unreachable")
        assert str(error) == "Broker unreachable"
        assert isinstance(error, NetboxPDNSError)

    def test_mqtt_message_error(self) -> None:
        """Test MQTT message error."""
        error = MQTTMessageError("Invalid message format")
        assert str(error) == "Invalid message format"
        assert isinstance(error, NetboxPDNSError)


class TestValidationError:
    """Test validation errors."""

    def test_validation_error(self) -> None:
        """Test validation error."""
        error = ValidationError("Invalid DNS name")
        assert str(error) == "Invalid DNS name"
        assert isinstance(error, NetboxPDNSError)