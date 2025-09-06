"""Unit tests for non-blocking startup behavior.

These tests verify that the application starts up properly without blocking
the event loop and that status endpoints work correctly.
"""

import time
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi.testclient import TestClient


class TestStartupBehavior:
    """Unit tests for startup behavior."""

    @pytest.fixture
    def mock_netbox_pdns(self) -> Mock:
        """Mock NetboxPDNS instance for testing."""
        mock_api = Mock()
        mock_api.config = Mock()
        mock_api.config.mqtt_enabled = False
        mock_api.config.sync_crontab = "0 */6 * * *"
        mock_api.logger = Mock()
        mock_api._operation_lock_with_logging = Mock()
        mock_api.full_sync = Mock(return_value={"result": "success"})
        return mock_api

    @pytest.fixture
    def mock_mqtt_service(self) -> Mock:
        """Mock MQTT service for testing."""
        mock_service = Mock()
        mock_service.get_status = Mock(return_value={"enabled": False})
        return mock_service

    @patch("netbox_pdns.NetboxPDNS")
    @patch("netbox_pdns.MQTTService")
    @patch("netbox_pdns.BackgroundScheduler")
    def test_app_starts_without_blocking(
        self,
        mock_scheduler_class: Mock,
        mock_mqtt_service_class: Mock,
        mock_netbox_pdns_class: Mock,
    ) -> None:
        """Test that the app starts without blocking on full_sync."""
        # Setup mocks
        mock_api = Mock()
        mock_api.config.mqtt_enabled = False
        mock_api.config.sync_crontab = "0 */6 * * *"
        mock_api.logger = Mock()
        mock_api._operation_lock_with_logging = Mock()
        mock_api.full_sync = Mock()
        mock_netbox_pdns_class.return_value = mock_api

        mock_scheduler = Mock()
        mock_scheduler.running = True
        mock_scheduler.get_jobs = Mock(return_value=[])
        mock_scheduler_class.return_value = mock_scheduler

        mock_mqtt_service = Mock()
        mock_mqtt_service.get_status = Mock(return_value={"enabled": False})
        mock_mqtt_service_class.return_value = mock_mqtt_service

        # Import and create app after mocking
        from netbox_pdns import create_app

        app = create_app()

        # Create test client and measure startup time
        start_time = time.time()
        client = TestClient(app)
        startup_time = time.time() - start_time

        # Startup should be very fast (not blocked by full_sync)
        assert startup_time < 1.0, f"Startup took {startup_time:.3f}s, expected < 1.0s"

        # full_sync should not have been called during synchronous startup
        # It should be called in the background thread
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "Healthy"

    @patch("netbox_pdns.NetboxPDNS")
    @patch("netbox_pdns.MQTTService")
    @patch("netbox_pdns.BackgroundScheduler")
    def test_detailed_status_endpoint(
        self,
        mock_scheduler_class: Mock,
        mock_mqtt_service_class: Mock,
        mock_netbox_pdns_class: Mock,
    ) -> None:
        """Test the detailed status endpoint returns correct information."""
        # Setup mocks
        mock_api = Mock()
        mock_api.config.mqtt_enabled = False
        mock_api.config.sync_crontab = "0 */6 * * *"
        mock_api.logger = Mock()
        mock_api._operation_lock_with_logging = Mock()
        mock_netbox_pdns_class.return_value = mock_api

        mock_scheduler = Mock()
        mock_scheduler.running = True
        mock_scheduler.get_jobs = Mock(return_value=["job1", "job2"])
        mock_scheduler_class.return_value = mock_scheduler

        mock_mqtt_service = Mock()
        mock_mqtt_service.get_status = Mock(return_value={"enabled": False, "connected": False})
        mock_mqtt_service_class.return_value = mock_mqtt_service

        # Import and create app after mocking
        from netbox_pdns import create_app

        app = create_app()
        client = TestClient(app)

        # Test status endpoint
        response = client.get("/status")
        assert response.status_code == 200

        status_data = response.json()

        # Check required fields
        assert "status" in status_data
        assert "uptime_seconds" in status_data
        assert "initial_sync" in status_data
        assert "scheduler" in status_data
        assert "mqtt" in status_data

        # Check initial sync structure
        sync_info = status_data["initial_sync"]
        assert "started" in sync_info
        assert "completed" in sync_info
        assert "error" in sync_info

        # Check scheduler info
        scheduler_info = status_data["scheduler"]
        assert scheduler_info["running"] is True
        assert scheduler_info["jobs_count"] == 2

        # Check MQTT info when disabled
        mqtt_info = status_data["mqtt"]
        assert mqtt_info["enabled"] is False

    @patch("netbox_pdns.NetboxPDNS")
    @patch("netbox_pdns.MQTTService")
    @patch("netbox_pdns.BackgroundScheduler")
    def test_status_initial_state(
        self,
        mock_scheduler_class: Mock,
        mock_mqtt_service_class: Mock,
        mock_netbox_pdns_class: Mock,
    ) -> None:
        """Test that status endpoint shows correct initial state."""
        # Setup mocks
        mock_api = Mock()
        mock_api.config.mqtt_enabled = False
        mock_api.config.sync_crontab = "0 */6 * * *"
        mock_api.logger = Mock()
        mock_api._operation_lock_with_logging = Mock()
        mock_api.full_sync = Mock(return_value={"result": "success"})
        mock_netbox_pdns_class.return_value = mock_api

        mock_scheduler = Mock()
        mock_scheduler.running = True
        mock_scheduler.get_jobs = Mock(return_value=[])
        mock_scheduler_class.return_value = mock_scheduler

        mock_mqtt_service = Mock()
        mock_mqtt_service.get_status = Mock(return_value={"enabled": False})
        mock_mqtt_service_class.return_value = mock_mqtt_service

        # Import and create app after mocking
        from netbox_pdns import create_app

        app = create_app()
        client = TestClient(app)

        response = client.get("/status")
        assert response.status_code == 200

        status_data = response.json()
        sync_info = status_data["initial_sync"]

        # Initially, sync should not be started yet or just started
        assert isinstance(sync_info["started"], bool)
        assert isinstance(sync_info["completed"], bool)
        assert sync_info["error"] is None  # No error initially

    @patch("netbox_pdns.NetboxPDNS")
    @patch("netbox_pdns.MQTTService")
    @patch("netbox_pdns.BackgroundScheduler")
    def test_status_with_mqtt_enabled(
        self,
        mock_scheduler_class: Mock,
        mock_mqtt_service_class: Mock,
        mock_netbox_pdns_class: Mock,
    ) -> None:
        """Test status endpoint with MQTT enabled."""
        # Setup mocks
        mock_api = Mock()
        mock_api.config.mqtt_enabled = True
        mock_api.config.sync_crontab = "0 */6 * * *"
        mock_api.logger = Mock()
        mock_api._operation_lock_with_logging = Mock()
        mock_netbox_pdns_class.return_value = mock_api

        mock_scheduler = Mock()
        mock_scheduler.running = True
        mock_scheduler.get_jobs = Mock(return_value=[])
        mock_scheduler_class.return_value = mock_scheduler

        mock_mqtt_service = Mock()
        mock_mqtt_service.start = Mock()
        mock_mqtt_service.wait_for_connection = AsyncMock(return_value=True)
        mock_mqtt_service.get_status = Mock(
            return_value={"enabled": True, "connected": True, "broker_url": "mqtt://localhost:1883"}
        )
        mock_mqtt_service_class.return_value = mock_mqtt_service

        # Import and create app after mocking
        from netbox_pdns import create_app

        app = create_app()
        client = TestClient(app)

        response = client.get("/status")
        assert response.status_code == 200

        status_data = response.json()
        mqtt_info = status_data["mqtt"]

        assert mqtt_info["enabled"] is True
        assert mqtt_info["connected"] is True
        assert "broker_url" in mqtt_info
