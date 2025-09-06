import json
from collections.abc import Generator
from unittest.mock import Mock, patch

import dns.name
import pytest
from fastapi.testclient import TestClient

from netbox_pdns import create_app
from netbox_pdns.models import Settings


@pytest.fixture
def mock_netbox_pdns() -> Generator[Mock, None, None]:
    with patch("netbox_pdns.NetboxPDNS") as mock_class:
        mock_instance = Mock()
        mock_class.return_value = mock_instance

        # Provide real Settings object to prevent URL parsing issues
        mock_instance.config = Settings(
            api_key="test_api_key",
            nb_url="https://netbox.example.com",
            nb_token="test_nb_token",
            nb_ns_id=1,
            pdns_url="https://pdns.example.com",
            pdns_token="test_pdns_token",
            sync_crontab="*/15 * * * *",
            mqtt_enabled=False,  # Disable MQTT to avoid connection attempts
        )

        # Mock methods
        mock_instance.full_sync.return_value = {"result": "success"}

        yield mock_instance


@pytest.fixture
def client(mock_netbox_pdns: Mock) -> TestClient:
    with patch("apscheduler.schedulers.background.BackgroundScheduler") as mock_scheduler:
        mock_scheduler_instance = Mock()
        mock_scheduler.return_value = mock_scheduler_instance

        # Mock MQTT service to prevent connection attempts
        with patch("netbox_pdns.mqtt_service.MQTTService") as mqtt_mock:
            mqtt_instance = Mock()
            mqtt_mock.return_value = mqtt_instance

            app = create_app()
            return TestClient(app)


def test_lifespan(client: TestClient, mock_netbox_pdns: Mock) -> None:
    with client:
        mock_netbox_pdns.full_sync.assert_called_once()


def test_health_check(client: TestClient) -> None:
    """Test the health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "Healthy"}


def test_sync_unauthorized(client: TestClient) -> None:
    """Test accessing sync endpoint without API key"""
    response = client.get("/sync")
    assert response.status_code == 401


def test_sync_authorized(client: TestClient, mock_netbox_pdns: Mock) -> None:
    """Test accessing sync endpoint with valid API key"""
    response = client.get("/sync", headers={"x-netbox-pdns-api-key": "test_api_key"})
    assert response.status_code == 200
    assert response.json() == {"result": "success"}
    mock_netbox_pdns.full_sync.assert_called_once()


def test_zones_create(client: TestClient, mock_netbox_pdns: Mock) -> None:
    """Test creating a zone via webhook"""
    webhook_data = {"id": 123, "name": "example.com", "serial": 2023010101}

    # Mock get_nb_zone to return a Mock zone
    mock_zone = Mock()
    mock_netbox_pdns.get_nb_zone.return_value = mock_zone

    response = client.post(
        "/zones/create",
        json=webhook_data,
        headers={"x-netbox-pdns-api-key": "test_api_key"},
    )

    assert response.status_code == 200
    mock_netbox_pdns.get_nb_zone.assert_called_once_with(123)
    mock_netbox_pdns.create_zone.assert_called_once_with(mock_zone)


def test_zones_delete(client: TestClient, mock_netbox_pdns: Mock) -> None:
    """Test deleting a zone via webhook"""
    webhook_data = {"id": 123, "name": "example.com"}

    response = client.request(
        method="DELETE",
        url="/zones/delete",
        content=json.dumps(webhook_data),
        headers={"x-netbox-pdns-api-key": "test_api_key"},
    )

    assert response.status_code == 200
    # Check that delete_zone was called with a DNS name
    mock_netbox_pdns.delete_zone.assert_called_once()
    called_arg = mock_netbox_pdns.delete_zone.call_args[0][0]
    assert isinstance(called_arg, dns.name.Name)
    assert called_arg.to_text() == "example.com."


def test_zones_update(client: TestClient, mock_netbox_pdns: Mock) -> None:
    """Test updating a zone via webhook"""
    webhook_data = {"id": 123, "name": "example.com"}

    # Mock get_nb_zone and get_pdns_zone to return Mock objects
    mock_nb_zone = Mock()
    mock_pdns_zone = Mock()
    mock_netbox_pdns.get_nb_zone.return_value = mock_nb_zone
    mock_netbox_pdns.get_pdns_zone.return_value = mock_pdns_zone

    response = client.post(
        "/zones/update",
        json=webhook_data,
        headers={"x-netbox-pdns-api-key": "test_api_key"},
    )

    assert response.status_code == 200
    mock_netbox_pdns.get_nb_zone.assert_called_once_with(123)
    mock_netbox_pdns.get_pdns_zone.assert_called_once_with("example.com")
    mock_netbox_pdns.sync_zone.assert_called_once_with(mock_nb_zone, mock_pdns_zone)
