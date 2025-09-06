import os
from collections.abc import Generator
from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def mock_env_file() -> Generator[None, None, None]:
    """
    Create a mock environment for all tests.
    This prevents tests from reading real .env files or environment variables.
    """
    # Mock environment variables for testing
    env_vars = {
        "NETBOX_PDNS_API_KEY": "test_api_key",
        "NETBOX_PDNS_NB_URL": "https://netbox.example.com",
        "NETBOX_PDNS_NB_TOKEN": "netbox_token",
        "NETBOX_PDNS_NB_NS_ID": "1",
        "NETBOX_PDNS_PDNS_URL": "https://pdns.example.com",
        "NETBOX_PDNS_PDNS_TOKEN": "pdns_token",
    }

    with patch.dict(os.environ, env_vars, clear=True):
        yield
