from unittest.mock import Mock, patch

import dns.name
import pytest

from netbox_pdns.api import NetboxPDNS
from netbox_pdns.models import Settings


# Integration tests with real responses but mocked API clients
@pytest.fixture
def real_settings() -> Settings:
    """Use test environment settings"""
    return Settings(
        api_key="test_api_key",
        nb_url="https://netbox.example.com",
        nb_token="netbox_token",
        nb_ns_id=1,
        pdns_url="https://pdns.example.com",
        pdns_token="pdns_token",
        log_level="DEBUG",
    )


@pytest.fixture
def mock_nb_zones() -> list:
    """Mock response for Netbox zones"""

    class MockZone:
        def __init__(self, id: int, name: str, soa_serial: int) -> None:
            self.id = id
            self.name = name
            self.soa_serial = soa_serial
            self.default_ttl = 3600

    return [MockZone(1, "example.com", 2023010101), MockZone(2, "new.com", 2023010102)]


@pytest.fixture
def mock_nb_records() -> dict:
    """Mock response for Netbox records"""

    class MockRecord:
        def __init__(
            self,
            id: int,
            zone_id: int,
            fqdn: str,
            type: str,
            value: str,
            ttl: None = None,
        ):
            self.id = id
            self.zone_id = zone_id
            self.fqdn = fqdn
            self.type = type
            self.value = value
            self.ttl = ttl

    return {
        1: [
            MockRecord(
                1,
                1,
                "example.com",
                "SOA",
                "ns1.example.com. admin.example.com. 2023010101 3600 900 1209600 86400",
            ),
            MockRecord(2, 1, "example.com", "NS", "ns1.example.com"),
            MockRecord(3, 1, "www.example.com", "A", "192.0.2.1"),
            MockRecord(4, 1, "www.example.com", "A", "192.0.2.2"),
        ],
        2: [
            MockRecord(
                5,
                2,
                "new.com",
                "SOA",
                "ns1.example.com. admin.new.com. 2023010102 3600 900 1209600 86400",
            ),
            MockRecord(6, 2, "new.com", "NS", "ns1.example.com"),
            MockRecord(7, 2, "www.new.com", "A", "192.0.2.3"),
        ],
    }


@pytest.fixture
def mock_pdns_zones() -> list:
    """Mock response for PowerDNS zones"""

    class MockZone:
        def __init__(self, id: str, name: str, serial: int, rrsets: list) -> None:
            self.id = id
            self.name = name
            self.serial = serial
            self.rrsets = rrsets

    class MockRRSet:
        def __init__(self, name: str, type: str, ttl: int, records: list) -> None:
            self.name = name
            self.type = type
            self.ttl = ttl
            self.records = records

    class MockRecord:
        def __init__(self, content: str) -> None:
            self.content = content

    # Create RRsets for example.com
    example_rrsets = [
        MockRRSet(
            "example.com",
            "SOA",
            3600,
            [MockRecord("ns1.example.com. admin.example.com. 2023010101 3600 900 1209600 86400")],
        ),
        MockRRSet("example.com", "NS", 3600, [MockRecord("ns1.example.com")]),
        MockRRSet(
            "www.example.com",
            "A",
            3600,
            [MockRecord("192.0.2.1"), MockRecord("192.0.2.2")],
        ),
    ]

    # Create zones
    return [
        MockZone("example.com", "example.com.", 2023010101, example_rrsets),
        MockZone("old.com", "old.com.", 2023010100, []),
    ]


@pytest.fixture
def integration_api(
    real_settings: Settings,
    mock_nb_zones: Mock,
    mock_nb_records: Mock,
    mock_pdns_zones: Mock,
) -> NetboxPDNS:
    """Set up a NetboxPDNS instance with mocked API but real behavior"""
    with patch("netbox_pdns.api.Settings", return_value=real_settings):
        # Mock Netbox API responses
        with patch("pynetbox.api") as mock_nb_api:
            mock_nb = mock_nb_api.return_value

            # Mock the plugins structure
            mock_nb.plugins = type(
                "obj",
                (object,),
                {
                    "netbox_dns": type(
                        "obj",
                        (object,),
                        {
                            "zones": type(
                                "obj",
                                (object,),
                                {
                                    "filter": lambda nameserver_id: [
                                        z
                                        for z in mock_nb_zones
                                        if nameserver_id == real_settings.nb_ns_id
                                    ],
                                    "get": lambda id: next(
                                        (z for z in mock_nb_zones if z.id == id), None
                                    ),
                                },
                            ),
                            "records": type(
                                "obj",
                                (object,),
                                {"filter": lambda zone_id: mock_nb_records.get(zone_id, [])},
                            ),
                        },
                    )
                },
            )

            # Mock PowerDNS API responses
            with patch("pdns_auth_client.ApiClient"):
                with patch("pdns_auth_client.ZonesApi") as mock_zones_api_class:
                    mock_zones_api = mock_zones_api_class.return_value

                    # Mock zone operations
                    mock_zones_api.list_zones = lambda server_id: mock_pdns_zones
                    mock_zones_api.list_zone = lambda server_id, zone_id: next(
                        (z for z in mock_pdns_zones if z.id == zone_id), None
                    )

                    # Mock actual API calls with traceable mocks
                    mock_zones_api.create_zone = Mock()
                    mock_zones_api.delete_zone = Mock()
                    mock_zones_api.patch_zone = Mock()

                    instance = NetboxPDNS()
                    return instance


def test_integration_full_sync(integration_api: Mock) -> None:
    """Test a full synchronization between Netbox and PowerDNS"""
    result = integration_api.full_sync()

    # Check that sync results in success
    assert result == {"result": "success"}

    # Verify that new.com was created in PowerDNS
    integration_api.zones_api.create_zone.assert_called_once()
    zone_name = integration_api.zones_api.create_zone.call_args[0][1].name
    assert zone_name == "new.com."

    # Verify that old.com was deleted from PowerDNS
    integration_api.zones_api.delete_zone.assert_called_once()
    zone_name = integration_api.zones_api.delete_zone.call_args[0][1]
    assert zone_name == "old.com."

    # example.com should be synchronized, but since the serial numbers match,
    # no patch should be performed
    integration_api.zones_api.patch_zone.assert_not_called()


def test_integration_create_zone(integration_api: Mock, mock_nb_zones: Mock) -> None:
    """Test creating a zone in PowerDNS from Netbox data"""
    # Get a zone from our mock data
    nb_zone = mock_nb_zones[1]  # new.com

    # Create the zone in PowerDNS
    integration_api.create_zone(nb_zone)

    # Verify the create_zone call
    integration_api.zones_api.create_zone.assert_called_once()

    # Verify the zone name in the call
    created_zone = integration_api.zones_api.create_zone.call_args[0][1]
    assert created_zone.name == "new.com."
    assert created_zone.serial == 2023010102

    # Verify RRsets are included
    assert len(created_zone.rrsets) > 0


def test_integration_sync_zone_with_changes(
    integration_api: Mock, mock_nb_zones: Mock, mock_pdns_zones: Mock
) -> None:
    """Test syncing a zone when the serial numbers don't match"""
    # Get a zone from our mock data
    nb_zone = mock_nb_zones[0]  # example.com
    pdns_zone = mock_pdns_zones[0]  # example.com

    # Modify the serial to trigger synchronization
    pdns_zone.serial = 2023010100  # Different from nb_zone.soa_serial

    # Sync the zone
    integration_api.sync_zone(nb_zone, pdns_zone)

    # Verify the patch_zone call
    integration_api.zones_api.patch_zone.assert_called_once()

    # Verify the zone details in the call
    patch_zone = integration_api.zones_api.patch_zone.call_args[0][2]
    assert patch_zone.name == "example.com."
    assert patch_zone.serial == 2023010101


def test_integration_delete_zone(integration_api: Mock) -> None:
    """Test deleting a zone from PowerDNS"""
    # Create a DNS name to delete
    zone_name = dns.name.from_text("old.com")

    # Delete the zone
    integration_api.delete_zone(zone_name)

    # Verify the delete_zone call
    integration_api.zones_api.delete_zone.assert_called_once_with(
        integration_api.config.pdns_server_id, "old.com."
    )
