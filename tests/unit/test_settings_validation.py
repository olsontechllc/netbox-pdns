"""Tests for Settings model validation."""
import pytest

from netbox_pdns.exceptions import ConfigurationError, ValidationError
from netbox_pdns.models import Settings


class TestSettingsValidation:
    """Test Settings model validation."""

    def test_valid_settings(self) -> None:
        """Test creation of valid settings."""
        settings = Settings(
            api_key="test-api-key",
            nb_url="https://netbox.example.com",
            nb_token="nb-token",
            nb_ns_id=1,
            pdns_url="https://pdns.example.com:8081",
            pdns_token="pdns-token",
        )
        
        assert settings.api_key == "test-api-key"
        assert settings.nb_url == "https://netbox.example.com"
        assert settings.pdns_url == "https://pdns.example.com:8081"

    def test_log_level_validation(self) -> None:
        """Test log level validation."""
        # Valid log levels should work
        for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            settings = Settings(
                api_key="test-api-key",
                nb_url="https://netbox.example.com",
                nb_token="nb-token", 
                nb_ns_id=1,
                pdns_url="https://pdns.example.com",
                pdns_token="pdns-token",
                log_level=level
            )
            assert settings.log_level == level

        # Case insensitive
        settings = Settings(
            api_key="test-api-key",
            nb_url="https://netbox.example.com",
            nb_token="nb-token",
            nb_ns_id=1,
            pdns_url="https://pdns.example.com",
            pdns_token="pdns-token",
            log_level="info"
        )
        assert settings.log_level == "INFO"

        # Invalid log level should raise ValidationError
        with pytest.raises(ValidationError, match="Invalid log level"):
            Settings(
                api_key="test-api-key",
                nb_url="https://netbox.example.com",
                nb_token="nb-token",
                nb_ns_id=1,
                pdns_url="https://pdns.example.com",
                pdns_token="pdns-token",
                log_level="INVALID"
            )

    def test_url_validation(self) -> None:
        """Test URL validation for Netbox and PowerDNS URLs."""
        base_settings = {
            "api_key": "test-api-key",
            "nb_token": "nb-token",
            "nb_ns_id": 1,
            "pdns_token": "pdns-token",
        }

        # Valid URLs should work
        settings = Settings(
            **base_settings,
            nb_url="https://netbox.example.com",
            pdns_url="http://pdns.example.com:8081"
        )
        assert settings.nb_url == "https://netbox.example.com"
        assert settings.pdns_url == "http://pdns.example.com:8081"

        # URLs with trailing slashes should be cleaned
        settings = Settings(
            **base_settings,
            nb_url="https://netbox.example.com/",
            pdns_url="https://pdns.example.com/"
        )
        assert settings.nb_url == "https://netbox.example.com"
        assert settings.pdns_url == "https://pdns.example.com"

        # Empty URLs should raise ValidationError
        with pytest.raises(ValidationError, match="Netbox URL cannot be empty"):
            Settings(**base_settings, nb_url="", pdns_url="https://pdns.example.com")

        with pytest.raises(ValidationError, match="PowerDNS URL cannot be empty"):
            Settings(**base_settings, nb_url="https://netbox.example.com", pdns_url="")

        # Invalid URL formats should raise ValidationError
        with pytest.raises(ValidationError, match="Invalid Netbox URL format"):
            Settings(**base_settings, nb_url="not-a-url", pdns_url="https://pdns.example.com")

        with pytest.raises(ValidationError, match="Invalid PowerDNS URL format"):
            Settings(**base_settings, nb_url="https://netbox.example.com", pdns_url="not-a-url")

        # Invalid schemes should raise ValidationError
        with pytest.raises(ValidationError, match="Netbox URL must use http or https scheme"):
            Settings(**base_settings, nb_url="ftp://netbox.example.com", pdns_url="https://pdns.example.com")

        with pytest.raises(ValidationError, match="PowerDNS URL must use http or https scheme"):
            Settings(**base_settings, nb_url="https://netbox.example.com", pdns_url="ftp://pdns.example.com")

    def test_nameserver_id_validation(self) -> None:
        """Test nameserver ID validation."""
        # Valid positive integer should work
        settings = Settings(
            api_key="test-api-key",
            nb_url="https://netbox.example.com",
            nb_token="nb-token",
            nb_ns_id=5,
            pdns_url="https://pdns.example.com",
            pdns_token="pdns-token",
        )
        assert settings.nb_ns_id == 5

        # Zero or negative should raise ValidationError
        with pytest.raises(ValueError):
            Settings(
                api_key="test-api-key",
                nb_url="https://netbox.example.com",
                nb_token="nb-token",
                nb_ns_id=0,
                pdns_url="https://pdns.example.com",
                pdns_token="pdns-token",
            )

    def test_crontab_validation(self) -> None:
        """Test crontab format validation."""
        base_settings = {
            "api_key": "test-api-key",
            "nb_url": "https://netbox.example.com",
            "nb_token": "nb-token",
            "nb_ns_id": 1,
            "pdns_url": "https://pdns.example.com",
            "pdns_token": "pdns-token",
        }

        # Valid crontab expressions should work
        valid_crontabs = [
            "* * * * *",
            "0 0 * * *",
            "*/15 * * * *",
            "0 9-17 * * 1-5",
        ]
        
        for crontab in valid_crontabs:
            settings = Settings(**base_settings, sync_crontab=crontab)
            assert settings.sync_crontab == crontab

        # Empty crontab should raise ValidationError
        with pytest.raises(ValidationError, match="Crontab expression cannot be empty"):
            Settings(**base_settings, sync_crontab="")

        # Invalid format (wrong number of parts) should raise ValidationError
        with pytest.raises(ValidationError, match="Invalid crontab format"):
            Settings(**base_settings, sync_crontab="* * *")  # Only 3 parts instead of 5

    def test_mqtt_broker_url_validation(self) -> None:
        """Test MQTT broker URL validation."""
        base_settings = {
            "api_key": "test-api-key",
            "nb_url": "https://netbox.example.com",
            "nb_token": "nb-token",
            "nb_ns_id": 1,
            "pdns_url": "https://pdns.example.com",
            "pdns_token": "pdns-token",
        }

        # Valid MQTT URLs should work
        settings = Settings(**base_settings, mqtt_broker_url="mqtt://localhost:1883")
        assert settings.mqtt_broker_url == "mqtt://localhost:1883"

        settings = Settings(**base_settings, mqtt_broker_url="mqtts://broker:8883")
        assert settings.mqtt_broker_url == "mqtts://broker:8883"

        # Empty URL should raise ValidationError
        with pytest.raises(ValidationError, match="MQTT broker URL cannot be empty"):
            Settings(**base_settings, mqtt_broker_url="")

        # Invalid format should raise ValidationError
        with pytest.raises(ValidationError, match="Invalid MQTT broker URL format"):
            Settings(**base_settings, mqtt_broker_url="not-a-url")

        # Invalid scheme should raise ValidationError
        with pytest.raises(ValidationError, match="MQTT broker URL must use mqtt or mqtts scheme"):
            Settings(**base_settings, mqtt_broker_url="http://broker:1883")

    def test_mqtt_client_id_validation(self) -> None:
        """Test MQTT client ID validation."""
        base_settings = {
            "api_key": "test-api-key",
            "nb_url": "https://netbox.example.com",
            "nb_token": "nb-token",
            "nb_ns_id": 1,
            "pdns_url": "https://pdns.example.com",
            "pdns_token": "pdns-token",
        }

        # Valid client IDs should work
        valid_ids = ["netbox-pdns", "client-123", "test_client", "a1b2c3"]
        for client_id in valid_ids:
            settings = Settings(**base_settings, mqtt_client_id=client_id)
            assert settings.mqtt_client_id == client_id

        # Empty client ID should raise ValidationError
        with pytest.raises(ValueError):  # Pydantic min_length validation
            Settings(**base_settings, mqtt_client_id="")

        # Client ID too long should raise ValidationError
        with pytest.raises(ValueError):  # Pydantic max_length validation
            Settings(**base_settings, mqtt_client_id="a" * 30)

        # Invalid characters should raise ValidationError
        with pytest.raises(ValidationError, match="MQTT client ID can only contain"):
            Settings(**base_settings, mqtt_client_id="client@invalid")

    def test_mqtt_topic_prefix_validation(self) -> None:
        """Test MQTT topic prefix validation."""
        base_settings = {
            "api_key": "test-api-key",
            "nb_url": "https://netbox.example.com",
            "nb_token": "nb-token",
            "nb_ns_id": 1,
            "pdns_url": "https://pdns.example.com",
            "pdns_token": "pdns-token",
        }

        # Valid topic prefixes should work
        valid_prefixes = ["dns/zones", "netbox-dns", "test_topic", "a/b/c"]
        for prefix in valid_prefixes:
            settings = Settings(**base_settings, mqtt_topic_prefix=prefix)
            # Leading/trailing slashes should be stripped
            expected = prefix.strip('/')
            assert settings.mqtt_topic_prefix == expected

        # Empty prefix should raise ValidationError
        with pytest.raises(ValueError):  # Pydantic min_length validation
            Settings(**base_settings, mqtt_topic_prefix="")

        # Invalid characters should raise ValidationError
        with pytest.raises(ValidationError, match="MQTT topic prefix can only contain"):
            Settings(**base_settings, mqtt_topic_prefix="invalid@topic")

    def test_mqtt_auth_validation(self) -> None:
        """Test MQTT authentication validation."""
        base_settings = {
            "api_key": "test-api-key",
            "nb_url": "https://netbox.example.com",
            "nb_token": "nb-token",
            "nb_ns_id": 1,
            "pdns_url": "https://pdns.example.com",
            "pdns_token": "pdns-token",
            "mqtt_enabled": True,
        }

        # Both username and password provided should work
        settings = Settings(
            **base_settings,
            mqtt_username="user",
            mqtt_password="pass"
        )
        assert settings.mqtt_username == "user"
        assert settings.mqtt_password == "pass"

        # Neither username nor password provided should work
        settings = Settings(**base_settings)
        assert settings.mqtt_username is None
        assert settings.mqtt_password is None

        # Only username provided should raise ConfigurationError
        with pytest.raises(ConfigurationError, match="Both mqtt_username and mqtt_password"):
            Settings(**base_settings, mqtt_username="user")

        # Only password provided should raise ConfigurationError
        with pytest.raises(ConfigurationError, match="Both mqtt_username and mqtt_password"):
            Settings(**base_settings, mqtt_password="pass")

        # Empty strings should be treated as None
        settings = Settings(
            **base_settings,
            mqtt_username="",
            mqtt_password=""
        )
        # The validation should pass since both are empty