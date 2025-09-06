"""Redesigned MQTT Integration Tests - End-to-End Focus

These tests focus on the public API and end-to-end behavior rather than
internal implementation details. Internal handler logic is covered by unit tests.
"""

from collections.abc import Generator
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from netbox_pdns import create_app
from netbox_pdns.models import Settings


class TestMQTTIntegrationEndToEnd:
    """End-to-end integration tests for MQTT functionality with FastAPI app."""

    @pytest.fixture
    def mqtt_disabled_config(self) -> Settings:
        """Configuration with MQTT disabled for safe testing."""
        return Settings(
            api_key="test_api_key",
            nb_url="https://netbox.example.com",
            nb_token="test_nb_token",
            nb_ns_id=1,
            pdns_url="https://pdns.example.com",
            pdns_token="test_pdns_token",
            mqtt_enabled=False,  # Disabled for safe testing
        )

    @pytest.fixture
    def mqtt_enabled_config(self) -> Settings:
        """Configuration with MQTT enabled for testing enabled state."""
        return Settings(
            api_key="test_api_key",
            nb_url="https://netbox.example.com",
            nb_token="test_nb_token",
            nb_ns_id=1,
            pdns_url="https://pdns.example.com",
            pdns_token="test_pdns_token",
            mqtt_enabled=True,
            mqtt_broker_url="mqtt://test-broker:1883",
            mqtt_client_id="test-client",
            mqtt_topic_prefix="test/zones",
            mqtt_qos=1,
        )

    @pytest.fixture
    def mock_netbox_api(self) -> Generator[Mock, None, None]:
        """Mock the NetboxPDNS API layer to avoid external dependencies."""
        with patch("netbox_pdns.NetboxPDNS") as mock_class:
            mock_instance = Mock()
            mock_class.return_value = mock_instance
            mock_instance.full_sync.return_value = {"result": "success"}
            yield mock_instance

    def test_mqtt_status_endpoint_disabled(self, mock_netbox_api: Mock) -> None:
        """Test MQTT status endpoint when MQTT is disabled."""
        # Configure with MQTT disabled
        mock_netbox_api.config = Settings(
            api_key="test_api_key",
            nb_url="https://netbox.example.com",
            nb_token="test_nb_token",
            nb_ns_id=1,
            pdns_url="https://pdns.example.com",
            pdns_token="test_pdns_token",
            mqtt_enabled=False,
        )

        with patch("apscheduler.schedulers.background.BackgroundScheduler"):
            with patch("netbox_pdns.mqtt_service.MQTTService") as mqtt_mock:
                mqtt_instance = Mock()
                mqtt_mock.return_value = mqtt_instance

                app = create_app()
                client = TestClient(app)

                response = client.get("/mqtt/status")

                assert response.status_code == 200
                data = response.json()

                # Test the response structure
                assert "enabled" in data
                assert "connected" in data
                assert "broker_url" in data
                assert "client_id" in data
                assert "topic_prefix" in data
                assert "qos" in data

                # MQTT should be disabled
                assert data["enabled"] is False

    def test_mqtt_status_endpoint_enabled_structure(self, mock_netbox_api: Mock) -> None:
        """Test MQTT status endpoint returns correct structure when enabled."""
        # Configure with MQTT enabled (but mocked to avoid actual connection)
        mock_netbox_api.config = Settings(
            api_key="test_api_key",
            nb_url="https://netbox.example.com",
            nb_token="test_nb_token",
            nb_ns_id=1,
            pdns_url="https://pdns.example.com",
            pdns_token="test_pdns_token",
            mqtt_enabled=True,
            mqtt_broker_url="mqtt://test-broker:1883",
            mqtt_client_id="test-client-id",
            mqtt_topic_prefix="test/zones",
            mqtt_qos=2,
        )

        with patch("apscheduler.schedulers.background.BackgroundScheduler"):
            with patch("netbox_pdns.mqtt_service.MQTTService") as mqtt_mock:
                mqtt_instance = Mock()
                mqtt_mock.return_value = mqtt_instance

                # Mock the status response
                mqtt_instance.get_status.return_value = {
                    "enabled": True,
                    "connected": False,  # Not actually connected in test
                    "broker_url": "mqtt://test-broker:1883",
                    "client_id": "test-client-id",
                    "topic_prefix": "test/zones",
                    "qos": 2,
                }

                app = create_app()
                client = TestClient(app)

                response = client.get("/mqtt/status")

                assert response.status_code == 200
                data = response.json()

                # Verify the response contains expected configuration
                assert data["enabled"] is True
                assert data["broker_url"] == "mqtt://test-broker:1883"
                assert data["client_id"] == "test-client-id"
                assert data["topic_prefix"] == "test/zones"
                assert data["qos"] == 2

    def test_app_startup_mqtt_disabled(self, mock_netbox_api: Mock) -> None:
        """Test app startup behavior when MQTT is disabled."""
        mock_netbox_api.config = Settings(
            api_key="test_api_key",
            nb_url="https://netbox.example.com",
            nb_token="test_nb_token",
            nb_ns_id=1,
            pdns_url="https://pdns.example.com",
            pdns_token="test_pdns_token",
            mqtt_enabled=False,
        )

        with patch("apscheduler.schedulers.background.BackgroundScheduler"):
            with patch("netbox_pdns.mqtt_service.MQTTService") as mqtt_mock:
                mqtt_instance = Mock()
                mqtt_mock.return_value = mqtt_instance

                # Create and start app
                with TestClient(create_app()) as client:
                    # Verify basic functionality works
                    response = client.get("/health")
                    assert response.status_code == 200
                    assert response.json() == {"status": "Healthy"}

                # With MQTT disabled, start should not be called
                mqtt_instance.start.assert_not_called()

    def test_app_startup_mqtt_enabled_observable_behavior(self, mock_netbox_api: Mock) -> None:
        """Test observable behavior when MQTT is enabled (focus on what we can see)."""
        mock_netbox_api.config = Settings(
            api_key="test_api_key",
            nb_url="https://netbox.example.com",
            nb_token="test_nb_token",
            nb_ns_id=1,
            pdns_url="https://pdns.example.com",
            pdns_token="test_pdns_token",
            mqtt_enabled=True,
            mqtt_broker_url="mqtt://localhost:1883",
            mqtt_client_id="integration-test-client",
            mqtt_topic_prefix="integration/test",
            mqtt_qos=1,
        )

        with patch("apscheduler.schedulers.background.BackgroundScheduler"):
            with patch("netbox_pdns.MQTTService") as mqtt_mock:
                mqtt_instance = Mock()
                mqtt_mock.return_value = mqtt_instance

                # Mock all methods to prevent real network activity
                from unittest.mock import AsyncMock

                mqtt_instance.wait_for_connection = AsyncMock(return_value=False)
                mqtt_instance.start = Mock(return_value=None)  # Don't actually call start
                mqtt_instance.stop = Mock(return_value=None)
                mqtt_instance.get_status = Mock(
                    return_value={
                        "enabled": True,
                        "connected": False,
                        "broker_url": "mqtt://localhost:1883",
                        "client_id": "integration-test-client",
                        "topic_prefix": "integration/test",
                        "qos": 1,
                    }
                )

                # The key test: app should start successfully even if MQTT is disabled/mocked
                with TestClient(create_app()) as client:
                    # Test that core endpoints work
                    response = client.get("/health")
                    assert response.status_code == 200
                    assert response.json() == {"status": "Healthy"}

                    # MQTT status endpoint should still work
                    response = client.get("/mqtt/status")
                    assert response.status_code == 200

                # MQTT service creation should have been attempted
                mqtt_mock.assert_called_once()

    def test_api_endpoints_work_regardless_of_mqtt_config(self, mock_netbox_api: Mock) -> None:
        """Test that core API endpoints work regardless of MQTT configuration."""
        # Test with MQTT disabled
        mock_netbox_api.config = Settings(
            api_key="test_api_key",
            nb_url="https://netbox.example.com",
            nb_token="test_nb_token",
            nb_ns_id=1,
            pdns_url="https://pdns.example.com",
            pdns_token="test_pdns_token",
            mqtt_enabled=False,
        )

        with patch("apscheduler.schedulers.background.BackgroundScheduler"):
            with patch("netbox_pdns.mqtt_service.MQTTService") as mqtt_mock:
                mqtt_instance = Mock()
                mqtt_mock.return_value = mqtt_instance

                app = create_app()
                client = TestClient(app)

                # Test core endpoints
                response = client.get("/health")
                assert response.status_code == 200

                # Test MQTT status endpoint works even with MQTT disabled
                response = client.get("/mqtt/status")
                assert response.status_code == 200

    def test_configuration_validation_integration(self) -> None:
        """Test that invalid configurations are caught during app creation."""
        # This is more of a unit test but validates end-to-end integration

        with patch("netbox_pdns.NetboxPDNS") as mock_netbox:
            # Mock NetboxPDNS to use invalid config
            mock_instance = Mock()
            mock_netbox.return_value = mock_instance

            # Test invalid MQTT broker URL
            # Should raise ValidationError during Settings creation
            with pytest.raises(Exception):  # noqa: B017
                Settings(
                    api_key="test_api_key",
                    nb_url="https://netbox.example.com",
                    nb_token="test_nb_token",
                    nb_ns_id=1,
                    pdns_url="https://pdns.example.com",
                    pdns_token="test_pdns_token",
                    mqtt_enabled=True,
                    mqtt_broker_url="invalid-url-format",  # This should fail validation
                )

    def test_mqtt_status_endpoint_authentication(self) -> None:
        """Test that MQTT status endpoint doesn't require API key (monitoring endpoint)."""
        with patch("netbox_pdns.NetboxPDNS") as mock_netbox:
            mock_instance = Mock()
            mock_netbox.return_value = mock_instance
            mock_instance.config = Settings(
                api_key="secret_key",
                nb_url="https://netbox.example.com",
                nb_token="test_nb_token",
                nb_ns_id=1,
                pdns_url="https://pdns.example.com",
                pdns_token="test_pdns_token",
                mqtt_enabled=False,
            )

            with patch("apscheduler.schedulers.background.BackgroundScheduler"):
                with patch("netbox_pdns.mqtt_service.MQTTService") as mqtt_mock:
                    mqtt_instance = Mock()
                    mqtt_mock.return_value = mqtt_instance

                    app = create_app()
                    client = TestClient(app)

                    # MQTT status should work without API key (monitoring endpoint)
                    response = client.get("/mqtt/status")
                    assert response.status_code == 200

                    # But other endpoints should still require API key
                    response = client.get("/sync")
                    assert response.status_code == 401  # Unauthorized
