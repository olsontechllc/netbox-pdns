import os
from typing import TypedDict
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from netbox_pdns.models import NetboxWebhook, Settings


class SettingsParams(TypedDict):
    api_key: str
    nb_url: str
    nb_token: str
    nb_ns_id: int
    pdns_url: str
    pdns_token: str


class WebhookParams(TypedDict, total=False):
    id: int
    name: str
    serial: int


def test_settings_required_fields() -> None:
    """Test that required fields are properly enforced"""
    # Missing required fields should raise ValidationError
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValidationError):
            Settings()

    # Minimal valid configuration
    valid_settings: SettingsParams = {
        "api_key": "test_api_key",
        "nb_url": "https://netbox.example.com",
        "nb_token": "netbox_token",
        "nb_ns_id": 1,
        "pdns_url": "https://pdns.example.com",
        "pdns_token": "pdns_token",
    }

    # This should not raise an exception
    settings = Settings(**valid_settings)
    assert settings.api_key == "test_api_key"
    assert settings.nb_ns_id == 1


def test_settings_default_values() -> None:
    """Test that default values are properly set"""
    minimal_settings: SettingsParams = {
        "api_key": "test_api_key",
        "nb_url": "https://netbox.example.com",
        "nb_token": "netbox_token",
        "nb_ns_id": 1,
        "pdns_url": "https://pdns.example.com",
        "pdns_token": "pdns_token",
    }

    settings = Settings(**minimal_settings)
    assert settings.sync_crontab == "* * * * *"
    assert settings.log_level == "INFO"
    assert settings.pdns_server_id == "localhost"


def test_netbox_webhook_model() -> None:
    """Test the NetboxWebhook model validation"""
    # Valid webhook data
    webhook_data: WebhookParams = {
        "id": 123,
        "name": "example.com",
        "serial": 2023010101,
    }

    webhook = NetboxWebhook(**webhook_data)
    assert webhook.id == 123
    assert webhook.name == "example.com"
    assert webhook.serial == 2023010101

    # Serial is optional
    webhook_data_no_serial: WebhookParams = {"id": 123, "name": "example.com"}

    webhook = NetboxWebhook(**webhook_data_no_serial)
    assert webhook.serial is None
