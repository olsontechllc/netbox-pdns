import logging
import sys
from collections.abc import Generator
from typing import Any
from unittest.mock import MagicMock, Mock, call, patch

import dns.name
import pytest

from netbox_pdns.api import NetboxPDNS
from netbox_pdns.exceptions import PowerDNSAPIError, ZoneSyncError
from netbox_pdns.models import Settings


# Create fixtures to mock external dependencies
@pytest.fixture
def mock_settings() -> Settings:
    return Settings(
        api_key="test_api_key",
        nb_url="https://netbox.example.com",
        nb_token="netbox_token",
        nb_ns_id=1,
        pdns_url="https://pdns.example.com",
        pdns_token="pdns_token",
    )


@pytest.fixture
def mock_pynetbox() -> Generator[Mock, None, None]:
    with patch("pynetbox.api") as mock_api:
        mock_nb = Mock()
        mock_api.return_value = mock_nb

        # Mock the plugins structure
        mock_nb.plugins = Mock()
        mock_nb.plugins.netbox_dns = Mock()
        mock_nb.plugins.netbox_dns.zones = Mock()
        mock_nb.plugins.netbox_dns.records = Mock()

        yield mock_nb


@pytest.fixture
def mock_pdns_client() -> Generator[Mock, None, None]:
    with patch("pdns_auth_client.ApiClient") as mock_api_client:
        mock_client = Mock()
        mock_api_client.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_zones_api() -> Generator[Mock, None, None]:
    with patch("pdns_auth_client.ZonesApi") as mock_zones_api:
        mock_api = Mock()
        mock_zones_api.return_value = mock_api
        yield mock_api


@pytest.fixture
def netbox_pdns_instance(
    mock_settings: Settings,
    mock_pynetbox: Mock,
    mock_pdns_client: Mock,
    mock_zones_api: Mock,
) -> NetboxPDNS:
    with patch("netbox_pdns.api.Settings", return_value=mock_settings):
        with patch("netbox_pdns.api.NetboxPDNS.setup_logging") as mock_logging:
            mock_logging.return_value = Mock()
            instance = NetboxPDNS()
            return instance


def test_init(netbox_pdns_instance: Mock) -> None:
    """Test initialization of NetboxPDNS class"""
    assert netbox_pdns_instance is not None
    assert netbox_pdns_instance.config is not None
    assert netbox_pdns_instance.nb is not None
    assert netbox_pdns_instance.pdns is not None
    assert netbox_pdns_instance.zones_api is not None
    assert netbox_pdns_instance.logger is not None


def test_setup_logging(netbox_pdns_instance: Mock) -> None:
    """Test setup_logging method properly configures logging"""
    # Reset the logger to ensure we test the actual setup
    with patch("logging.getLogger") as mock_get_logger:
        with patch("logging.StreamHandler") as mock_stream_handler:
            with patch("logging.Formatter") as mock_formatter:
                # Setup mock objects
                mock_logger = Mock()
                mock_get_logger.return_value = mock_logger

                mock_handler = Mock()
                mock_stream_handler.return_value = mock_handler

                mock_format = Mock()
                mock_formatter.return_value = mock_format

                # Test with different log levels
                test_config = Mock(log_level="INFO")

                # Replace instance config with our test config
                original_config = netbox_pdns_instance.config
                netbox_pdns_instance.config = test_config

                # Call setup_logging
                result = netbox_pdns_instance.setup_logging()

                # Restore original config
                netbox_pdns_instance.config = original_config

                # Verify logger was created with correct name
                mock_get_logger.assert_called_once_with("netbox_pdns")

                # Verify logger level was set
                mock_logger.setLevel.assert_called_once_with(logging.INFO)

                # Verify handler was created and configured
                mock_stream_handler.assert_called_once_with(sys.stdout)
                mock_handler.setLevel.assert_called_once_with(logging.INFO)

                # Verify formatter was created with correct format
                mock_formatter.assert_called_once()
                mock_handler.setFormatter.assert_called_once_with(mock_format)

                # Verify handler was added to logger
                mock_logger.addHandler.assert_called_once_with(mock_handler)

                # Verify result
                assert result == mock_logger


def test_setup_netbox(netbox_pdns_instance: Mock) -> None:
    """Test setup_netbox method properly configures and returns pynetbox API client"""
    with patch("pynetbox.api") as mock_api:
        mock_nb = Mock()
        mock_api.return_value = mock_nb

        # Reset existing netbox client to ensure we test the method
        original_nb = netbox_pdns_instance.nb
        netbox_pdns_instance.nb = None

        # Call setup_netbox
        result = netbox_pdns_instance.setup_netbox()

        # Restore original nb
        netbox_pdns_instance.nb = original_nb

        # Verify pynetbox.api was called with correct params
        mock_api.assert_called_once_with(
            netbox_pdns_instance.config.nb_url,
            token=netbox_pdns_instance.config.nb_token,
        )

        # Verify result
        assert result == mock_nb


def test_setup_pdns(netbox_pdns_instance: Mock) -> None:
    """Test setup_pdns method properly configures and returns PowerDNS API client"""
    with patch("pdns_auth_client.Configuration") as mock_config_class:
        with patch("pdns_auth_client.ApiClient") as mock_api_client_class:
            # Setup mocks
            mock_config = Mock()
            mock_config.api_key = {}
            mock_config_class.return_value = mock_config

            mock_api_client = Mock()
            mock_api_client_class.return_value = mock_api_client

            # Reset existing pdns client to ensure we test the method
            original_pdns = netbox_pdns_instance.pdns
            netbox_pdns_instance.pdns = None

            # Call setup_pdns
            result = netbox_pdns_instance.setup_pdns()

            # Restore original pdns
            netbox_pdns_instance.pdns = original_pdns

            # Verify Configuration was created with correct params
            mock_config_class.assert_called_once_with(host=netbox_pdns_instance.config.pdns_url)

            # Verify API key was set
            assert mock_config.api_key["APIKeyHeader"] == netbox_pdns_instance.config.pdns_token

            # Verify ApiClient was created with config
            mock_api_client_class.assert_called_once_with(mock_config)

            # Verify result
            assert result == mock_api_client


def test_get_nb_zone(netbox_pdns_instance: Mock) -> None:
    """Test getting a zone from Netbox"""
    mock_zone = Mock()
    netbox_pdns_instance.nb.plugins.netbox_dns.zones.get.return_value = mock_zone

    zone = netbox_pdns_instance.get_nb_zone(1)

    netbox_pdns_instance.nb.plugins.netbox_dns.zones.get.assert_called_once_with(id=1)
    assert zone == mock_zone


def test_get_pdns_zone(netbox_pdns_instance: Mock) -> None:
    """Test getting a zone from PowerDNS"""
    mock_zone = Mock()
    netbox_pdns_instance.zones_api.list_zone.return_value = mock_zone

    zone = netbox_pdns_instance.get_pdns_zone("example.com")

    netbox_pdns_instance.zones_api.list_zone.assert_called_once_with(
        netbox_pdns_instance.config.pdns_server_id, "example.com"
    )
    assert zone == mock_zone


def test_get_nb_rrsets(netbox_pdns_instance: Mock) -> None:
    """Comprehensive test for get_nb_rrsets method"""
    # Create various types of mock records
    mock_records = [
        # Multiple A records for same FQDN
        Mock(fqdn="www.example.com", type="A", value="192.0.2.1"),
        Mock(fqdn="www.example.com", type="A", value="192.0.2.2"),
        # A single AAAA record
        Mock(fqdn="www.example.com", type="AAAA", value="2001:db8::1"),
        # MX record
        Mock(fqdn="example.com", type="MX", value="10 mail.example.com"),
        # TXT record
        Mock(fqdn="example.com", type="TXT", value="v=spf1 -all"),
        # CNAME record
        Mock(fqdn="alias.example.com", type="CNAME", value="www.example.com"),
        # SRV record
        Mock(fqdn="_sip._tcp.example.com", type="SRV", value="0 5 5060 sip.example.com"),
    ]

    netbox_pdns_instance.nb.plugins.netbox_dns.records.filter.return_value = mock_records

    # Call get_nb_rrsets
    rrsets = netbox_pdns_instance.get_nb_rrsets(1)

    # Verify filter was called with correct zone_id
    netbox_pdns_instance.nb.plugins.netbox_dns.records.filter.assert_called_once_with(zone_id=1)

    # Verify rrsets dictionary structure
    assert len(rrsets) == 6  # 6 unique FQDN+type combinations

    # Check specific record groups
    assert len(rrsets[("www.example.com", "A")]) == 2
    assert len(rrsets[("www.example.com", "AAAA")]) == 1
    assert len(rrsets[("example.com", "MX")]) == 1
    assert len(rrsets[("example.com", "TXT")]) == 1
    assert len(rrsets[("alias.example.com", "CNAME")]) == 1
    assert len(rrsets[("_sip._tcp.example.com", "SRV")]) == 1

    # Check actual record objects in the sets
    assert mock_records[0] in rrsets[("www.example.com", "A")]
    assert mock_records[1] in rrsets[("www.example.com", "A")]
    assert mock_records[2] in rrsets[("www.example.com", "AAAA")]


def test_get_nb_rrsets_empty(netbox_pdns_instance: Mock) -> None:
    """Test get_nb_rrsets with no records"""
    netbox_pdns_instance.nb.plugins.netbox_dns.records.filter.return_value = []

    # Call get_nb_rrsets
    rrsets = netbox_pdns_instance.get_nb_rrsets(1)

    # Verify filter was called
    netbox_pdns_instance.nb.plugins.netbox_dns.records.filter.assert_called_once_with(zone_id=1)

    # Verify empty dictionary returned
    assert len(rrsets) == 0
    assert isinstance(rrsets, dict)


def test_mk_pdns_rrsets(netbox_pdns_instance: Mock) -> None:
    """Test the _mk_pdns_rrsets method that creates PowerDNS RRSet objects"""
    # Create mock zone with default TTL
    mock_nb_zone = Mock(default_ttl=3600)

    # Create mock Netbox records with different TTL scenarios
    mock_record1 = Mock(ttl=7200, value="192.0.2.1")
    mock_record2 = Mock(ttl=None, value="192.0.2.2")  # Test None TTL (should use default)
    mock_record3 = Mock(ttl=900, value="10 mail.example.com")

    # Create test data
    nb_rrsets = {
        ("www.example.com", "A"): [mock_record1],
        ("api.example.com", "A"): [mock_record2],
        ("mail.example.com", "MX"): [mock_record3],
    }
    nb_rrsets_deleted = {("old.example.com", "CNAME"), ("unused.example.com", "TXT")}
    nb_rrsets_replace = {
        ("www.example.com", "A"),
        ("api.example.com", "A"),
        ("mail.example.com", "MX"),
    }

    # Use real RRSet and Record classes with mocked pdns_auth_client module
    with patch("pdns_auth_client.RRSet") as mock_rrset_class:
        with patch("pdns_auth_client.Record") as mock_record_class:
            # Call the method
            result = netbox_pdns_instance._mk_pdns_rrsets(
                mock_nb_zone, nb_rrsets, nb_rrsets_deleted, nb_rrsets_replace
            )

            # Verify the results
            assert len(result) == 5  # 2 deletes + 3 replaces

            # Validate DELETE operations were called with correct params
            delete_calls = [
                call(
                    changetype="DELETE",
                    name="old.example.com",
                    type="CNAME",
                    records=[],
                ),
                call(
                    changetype="DELETE",
                    name="unused.example.com",
                    type="TXT",
                    records=[],
                ),
            ]

            # Check that the appropriate RRSet calls were made for DELETE operations
            for delete_call in delete_calls:
                assert delete_call in mock_rrset_class.call_args_list

            # Verify REPLACE operations - extract calls for each record type
            www_call = call(
                changetype="REPLACE",
                name="www.example.com",
                type="A",
                ttl=7200,  # Record's TTL
                records=[mock_record_class.return_value],
            )

            api_call = call(
                changetype="REPLACE",
                name="api.example.com",
                type="A",
                ttl=3600,  # Zone's default TTL
                records=[mock_record_class.return_value],
            )

            mail_call = call(
                changetype="REPLACE",
                name="mail.example.com",
                type="MX",
                ttl=900,  # Record's TTL
                records=[mock_record_class.return_value],
            )

            # Verify all expected calls were made
            assert www_call in mock_rrset_class.call_args_list
            assert api_call in mock_rrset_class.call_args_list
            assert mail_call in mock_rrset_class.call_args_list

            # Verify Record constructor calls for content values
            record_calls = [
                call(content="192.0.2.1"),
                call(content="192.0.2.2"),
                call(content="10 mail.example.com"),
            ]

            for record_call in record_calls:
                assert record_call in mock_record_class.call_args_list

            # Verify logging calls - should log deletes and replaces
            log_calls = [
                call(f"Deleting RRSet {('old.example.com', 'CNAME')}"),
                call(f"Deleting RRSet {('unused.example.com', 'TXT')}"),
                call(f"Replacing RRSet {('www.example.com', 'A')}"),
                call(f"Replacing RRSet {('api.example.com', 'A')}"),
                call(f"Replacing RRSet {('mail.example.com', 'MX')}"),
            ]

            for log_call in log_calls:
                assert log_call in netbox_pdns_instance.logger.info.call_args_list


def test_mk_pdns_rrsets_empty(netbox_pdns_instance: Mock) -> None:
    """Test the _mk_pdns_rrsets method with empty inputs"""
    # Create empty nb_rrsets dict
    empty_nb_rrsets: dict[Any, Any] = {}

    # Create mock Netbox zone with default TTL
    mock_nb_zone = Mock(default_ttl=3600)

    result = netbox_pdns_instance._mk_pdns_rrsets(mock_nb_zone, empty_nb_rrsets, None, None)

    assert len(result) == 0
    assert isinstance(result, list)


def test_create_zone(netbox_pdns_instance: Mock) -> None:
    """Test creating a zone in PowerDNS"""
    # Create mock zone
    mock_nb_zone = MagicMock()
    mock_nb_zone.id = 1
    mock_nb_zone.name = "example.com"
    mock_nb_zone.soa_serial = 12345
    mock_nb_zone.default_ttl = 3600

    # Mock get_nb_rrsets to return some records
    with patch.object(netbox_pdns_instance, "get_nb_rrsets") as mock_get_nb_rrsets:
        mock_get_nb_rrsets.return_value = {
            ("www.example.com", "A"): [
                Mock(fqdn="www.example.com", type="A", ttl=3600, value="192.0.2.1")
            ],
            ("mail.example.com", "MX"): [
                Mock(
                    fqdn="mail.example.com",
                    type="MX",
                    ttl=None,
                    value="10 mail.example.com",
                )
            ],
        }

        # Mock _mk_pdns_rrsets
        with patch.object(netbox_pdns_instance, "_mk_pdns_rrsets") as mock_mk_rrsets:
            mock_rrsets = [
                Mock(name="www.example.com", type="A"),
                Mock(name="mail.example.com", type="MX"),
            ]
            mock_mk_rrsets.return_value = mock_rrsets

            # Mock pdns_auth_client Zone class
            with patch("pdns_auth_client.Zone") as mock_zone_class:
                mock_zone = Mock()
                mock_zone_class.return_value = mock_zone

                # Call create_zone
                netbox_pdns_instance.create_zone(mock_nb_zone)

                # Verify the calls
                mock_get_nb_rrsets.assert_called_once_with(1)
                mock_mk_rrsets.assert_called_once_with(
                    mock_nb_zone,
                    mock_get_nb_rrsets.return_value,
                    nb_rrsets_replace=set(mock_get_nb_rrsets.return_value.keys()),
                )

                # Verify Zone creation
                mock_zone_class.assert_called_once()
                zone_args = mock_zone_class.call_args[1]
                assert zone_args["name"] == dns.name.from_text("example.com").to_text()
                assert zone_args["serial"] == 12345
                assert zone_args["rrsets"] == mock_rrsets
                assert zone_args["soa_edit_api"] == ""
                assert zone_args["kind"] == "Native"

                # Verify create_zone API call
                netbox_pdns_instance.zones_api.create_zone.assert_called_once_with(
                    netbox_pdns_instance.config.pdns_server_id, mock_zone
                )

                # Verify logging
                netbox_pdns_instance.logger.info.assert_called_with(
                    f"Creating zone {mock_nb_zone.name}"
                )
                netbox_pdns_instance.logger.error.assert_not_called()


def test_create_zone_exception_handling(netbox_pdns_instance: Mock) -> None:
    """Test that create_zone properly handles exceptions from the PowerDNS API"""
    # Create mock zone
    mock_nb_zone = MagicMock()
    mock_nb_zone.id = 1
    mock_nb_zone.name = "example.com"
    mock_nb_zone.soa_serial = 12345

    # Mock get_nb_rrsets to return minimal data
    with patch.object(netbox_pdns_instance, "get_nb_rrsets") as mock_get_nb_rrsets:
        mock_get_nb_rrsets.return_value = {
            ("www.example.com", "A"): [Mock(ttl=3600, value="192.0.2.1")]
        }

        # Mock _mk_pdns_rrsets
        with patch.object(netbox_pdns_instance, "_mk_pdns_rrsets") as mock_mk_rrsets:
            mock_mk_rrsets.return_value = [Mock()]

            # Mock Zone constructor
            with patch("pdns_auth_client.Zone") as mock_zone_class:
                mock_zone = Mock()
                mock_zone_class.return_value = mock_zone

                # Make create_zone raise an exception
                test_exception = Exception("Test API exception")
                netbox_pdns_instance.zones_api.create_zone.side_effect = test_exception

                # Call create_zone, should raise PowerDNSAPIError
                with pytest.raises(PowerDNSAPIError):
                    netbox_pdns_instance.create_zone(mock_nb_zone)

                # Verify the exception was logged (retry mechanism logs first,
                # then original error handling)
                assert netbox_pdns_instance.logger.error.call_count == 2

                # Check retry mechanism error
                retry_error = netbox_pdns_instance.logger.error.call_args_list[0][0][0]
                assert "failed after 3 attempts" in retry_error

                # Check original error handling
                original_error = netbox_pdns_instance.logger.error.call_args_list[1][0][0]
                assert "Failed to create zone example.com in PowerDNS" in original_error
                assert "Test API exception" in original_error


def test_create_zone_empty_rrsets(netbox_pdns_instance: Mock) -> None:
    """Test create_zone behavior with empty RRsets"""
    # Create mock zone
    mock_nb_zone = MagicMock()
    mock_nb_zone.id = 1
    mock_nb_zone.name = "empty.com"
    mock_nb_zone.soa_serial = 12345
    mock_nb_zone.default_ttl = 3600

    # Mock get_nb_rrsets to return empty dict
    with patch.object(netbox_pdns_instance, "get_nb_rrsets") as mock_get_nb_rrsets:
        mock_get_nb_rrsets.return_value = {}

        # Mock _mk_pdns_rrsets to return empty list
        with patch.object(netbox_pdns_instance, "_mk_pdns_rrsets") as mock_mk_rrsets:
            mock_mk_rrsets.return_value = []

            # Mock Zone constructor
            with patch("pdns_auth_client.Zone") as mock_zone_class:
                mock_zone = Mock()
                mock_zone_class.return_value = mock_zone

                # Call create_zone
                netbox_pdns_instance.create_zone(mock_nb_zone)

                # Verify Zone creation with empty RRsets
                mock_zone_class.assert_called_once()
                zone_args = mock_zone_class.call_args[1]
                assert zone_args["rrsets"] == []

                # Verify create_zone API call still happens
                netbox_pdns_instance.zones_api.create_zone.assert_called_once()


def test_delete_zone(netbox_pdns_instance: Mock) -> None:
    """Test deleting a zone in PowerDNS"""
    # Create a zone name using dns.name
    zone_name = dns.name.from_text("example.com")

    # Call delete_zone
    netbox_pdns_instance.delete_zone(zone_name)

    # Verify logging
    netbox_pdns_instance.logger.info.assert_called_with(f"Deleting zone {zone_name.to_text()}")

    # Verify delete_zone API call
    netbox_pdns_instance.zones_api.delete_zone.assert_called_once_with(
        netbox_pdns_instance.config.pdns_server_id, zone_name.to_text()
    )

    # Verify no errors were logged
    netbox_pdns_instance.logger.error.assert_not_called()


def test_delete_zone_exception_handling(netbox_pdns_instance: Mock) -> None:
    """Test that delete_zone properly handles exceptions from the PowerDNS API"""
    # Create a zone name using dns.name
    zone_name = dns.name.from_text("non-existent.com")

    # Make delete_zone raise an exception
    test_exception = Exception("Zone not found")
    netbox_pdns_instance.zones_api.delete_zone.side_effect = test_exception

    # Call delete_zone, should raise PowerDNSAPIError
    with pytest.raises(PowerDNSAPIError):
        netbox_pdns_instance.delete_zone(zone_name)

    # Verify the exception was logged (retry mechanism + original error handling)
    assert netbox_pdns_instance.logger.error.call_count == 2
    error_message = netbox_pdns_instance.logger.error.call_args[0][0]
    assert "Failed to delete zone non-existent.com. from PowerDNS" in error_message
    assert "Zone not found" in error_message


def test_sync_zone_matching_serials(netbox_pdns_instance: Mock) -> None:
    """Test sync_zone when serial numbers match - should skip synchronization"""
    # Create mock zones with matching serials
    mock_nb_zone = MagicMock()
    mock_nb_zone.name = "example.com"
    mock_nb_zone.soa_serial = 12345

    mock_pdns_zone = Mock(serial=12345)

    # Mock get_nb_rrsets, list_zone, and patch_zone
    with patch.object(netbox_pdns_instance, "get_nb_rrsets") as mock_get_nb_rrsets:
        with patch.object(netbox_pdns_instance.zones_api, "list_zone") as mock_list_zone:
            with patch.object(netbox_pdns_instance.zones_api, "patch_zone") as mock_patch_zone:
                # Call sync_zone
                netbox_pdns_instance.sync_zone(mock_nb_zone, mock_pdns_zone)

                # Verify that the logger was called
                netbox_pdns_instance.logger.info.assert_called_with(
                    "Skipping synchronization of zone example.com because serial numbers match"
                )

                # Verify no other operations occurred
                mock_get_nb_rrsets.assert_not_called()
                mock_list_zone.assert_not_called()
                mock_patch_zone.assert_not_called()


def test_sync_zone_different_serials(netbox_pdns_instance: Mock) -> None:
    """Test sync_zone when serial numbers differ - should perform synchronization"""
    # Create mock zones with different serials
    mock_nb_zone = MagicMock()
    mock_nb_zone.id = 1
    mock_nb_zone.name = "example.com"
    mock_nb_zone.soa_serial = 12346
    mock_nb_zone.default_ttl = 3600

    mock_pdns_zone = MagicMock()
    mock_pdns_zone.id = "example.com"
    mock_pdns_zone.name = "example.com"
    mock_pdns_zone.serial = 12345  # Different from nb_zone

    # Mock get_nb_rrsets to return some records
    with patch.object(netbox_pdns_instance, "get_nb_rrsets") as mock_get_nb_rrsets:
        mock_get_nb_rrsets.return_value = {
            ("www.example.com", "A"): [
                Mock(fqdn="www.example.com", type="A", ttl=3600, value="192.0.2.1")
            ],
            ("mail.example.com", "MX"): [
                Mock(
                    fqdn="mail.example.com",
                    type="MX",
                    ttl=None,
                    value="10 mail.example.com",
                )
            ],
        }

        # Mock PowerDNS zone list_zone to return RRsets
        mock_pdns_rrset1 = MagicMock()
        mock_pdns_rrset1.name = "www.example.com"
        mock_pdns_rrset1.type = "A"
        mock_pdns_rrset2 = MagicMock()  # This one should be deleted
        mock_pdns_rrset2.name = "old.example.com"
        mock_pdns_rrset2.type = "CNAME"
        mock_pdns_rrsets = Mock(rrsets=[mock_pdns_rrset1, mock_pdns_rrset2])
        netbox_pdns_instance.zones_api.list_zone.return_value = mock_pdns_rrsets

        # Mock pdns_auth_client RRSet and Record classes
        with patch("pdns_auth_client.RRSet") as mock_rrset_class:
            with patch("pdns_auth_client.Record") as mock_record_class:
                # Configure mocks to return objects with provided kwargs
                mock_record_class.side_effect = lambda **kwargs: Mock(**kwargs)
                mock_rrset_class.side_effect = lambda **kwargs: Mock(**kwargs)

                # Set up our zone patch object to be returned for assertions
                mock_zone_patch = Mock()
                mock_rrset_class.side_effect = lambda **kwargs: Mock(**kwargs)

                # Mock Zone constructor
                with patch("pdns_auth_client.Zone") as mock_zone_class:
                    mock_zone_class.return_value = mock_zone_patch

                    # Call sync_zone
                    netbox_pdns_instance.sync_zone(mock_nb_zone, mock_pdns_zone)

                    # Verify API calls
                    netbox_pdns_instance.get_nb_rrsets.assert_called_once_with(1)
                    netbox_pdns_instance.zones_api.list_zone.assert_called_once_with(
                        netbox_pdns_instance.config.pdns_server_id, "example.com"
                    )

                    # Verify Zone creation for the patch
                    mock_zone_class.assert_called_once()
                    zone_args = mock_zone_class.call_args[1]
                    assert zone_args["name"] == "example.com"
                    assert zone_args["serial"] == 12346  # Updated to Netbox serial

                    # Verify the patch_zone call
                    netbox_pdns_instance.zones_api.patch_zone.assert_called_once_with(
                        netbox_pdns_instance.config.pdns_server_id,
                        "example.com",
                        mock_zone_patch,
                    )

                    # Verify RRSet creation calls - should have DELETE for old.example.com
                    # and REPLACE for www.example.com and mail.example.com
                    assert mock_rrset_class.call_count >= 3

                    # Check for a DELETE call for old.example.com
                    delete_call = call(
                        changetype="DELETE",
                        name="old.example.com",
                        type="CNAME",
                        records=[],
                    )
                    assert delete_call in mock_rrset_class.call_args_list


def test_sync_zone_exception_handling(netbox_pdns_instance: Mock) -> None:
    """Test that sync_zone properly handles exceptions from the PowerDNS API"""
    # Create mock zones
    mock_nb_zone = MagicMock()
    mock_nb_zone.id = 1
    mock_nb_zone.name = "example.com"
    mock_nb_zone.soa_serial = 12346

    mock_pdns_zone = MagicMock()
    mock_pdns_zone.id = "example.com"
    mock_pdns_zone.name = "example.com"
    mock_pdns_zone.serial = 12345

    # Mock get_nb_rrsets to return minimal data
    with patch.object(netbox_pdns_instance, "get_nb_rrsets") as mock_get_nb_rrsets:
        mock_get_nb_rrsets.return_value = {
            ("www.example.com", "A"): [Mock(ttl=3600, value="192.0.2.1")]
        }

        # Mock PowerDNS list_zone to return minimal RRsets
        mock_pdns_rrset = MagicMock()
        mock_pdns_rrset.name = "www.example.com"
        mock_pdns_rrset.type = "A"
        mock_pdns_rrsets = Mock(rrsets=[mock_pdns_rrset])
        netbox_pdns_instance.zones_api.list_zone.return_value = mock_pdns_rrsets

        # Make patch_zone raise an exception
        test_exception = Exception("Test API exception")
        netbox_pdns_instance.zones_api.patch_zone.side_effect = test_exception

        # Call sync_zone, should raise ZoneSyncError
        with pytest.raises(ZoneSyncError):
            netbox_pdns_instance.sync_zone(mock_nb_zone, mock_pdns_zone)

        # Verify the exception was logged (retry mechanism + original error handling)
        assert netbox_pdns_instance.logger.error.call_count == 2
        error_message = netbox_pdns_instance.logger.error.call_args[0][0]
        assert "Failed to patch zone example.com in PowerDNS" in error_message
        assert "Test API exception" in error_message


def test_sync_zone_empty_rrsets(netbox_pdns_instance: Mock) -> None:
    """Test sync_zone behavior with empty RRsets"""
    # Create mock zones
    mock_nb_zone = MagicMock()
    mock_nb_zone.id = 1
    mock_nb_zone.name = "empty.com"
    mock_nb_zone.soa_serial = 12346
    mock_nb_zone.default_ttl = 3600

    mock_pdns_zone = MagicMock()
    mock_pdns_zone.id = "empty.com"
    mock_pdns_zone.name = "empty.com"
    mock_pdns_zone.serial = 12345

    # Mock get_nb_rrsets to return empty dict
    with patch.object(netbox_pdns_instance, "get_nb_rrsets") as mock_get_nb_rrsets:
        mock_get_nb_rrsets.return_value = {}

        # Mock PowerDNS list_zone to return some RRsets that should be deleted
        mock_pdns_rrset1 = MagicMock()
        mock_pdns_rrset1.name = "www.empty.com"
        mock_pdns_rrset1.type = "A"
        mock_pdns_rrset2 = MagicMock()
        mock_pdns_rrset2.name = "mail.empty.com"
        mock_pdns_rrset2.type = "MX"
        mock_pdns_rrsets = Mock(rrsets=[mock_pdns_rrset1, mock_pdns_rrset2])
        netbox_pdns_instance.zones_api.list_zone.return_value = mock_pdns_rrsets

        # Call sync_zone
        with patch("pdns_auth_client.RRSet") as mock_rrset_class:
            with patch("pdns_auth_client.Zone") as mock_zone_class:
                netbox_pdns_instance.sync_zone(mock_nb_zone, mock_pdns_zone)

                # Verify that both RRsets from PowerDNS were marked for deletion
                assert mock_rrset_class.call_count == 2
                delete_calls = [
                    call(changetype="DELETE", name="www.empty.com", type="A", records=[]),
                    call(
                        changetype="DELETE",
                        name="mail.empty.com",
                        type="MX",
                        records=[],
                    ),
                ]

                for delete_call in delete_calls:
                    assert delete_call in mock_rrset_class.call_args_list

                # Verify the Zone was created with the DELETE RRsets
                mock_zone_class.assert_called_once()
                netbox_pdns_instance.zones_api.patch_zone.assert_called_once()


def test_full_sync(netbox_pdns_instance: Mock) -> None:
    """Comprehensive test for full_sync method"""
    # Mock the zones returned from PowerDNS
    pdns_zone1 = MagicMock()
    pdns_zone1.name = "existing.com."  # Note: PDNS may return names with trailing dots
    pdns_zone1.id = "existing.com"

    pdns_zone2 = MagicMock()
    pdns_zone2.name = "to-be-deleted.com."
    pdns_zone2.id = "to-be-deleted.com"

    pdns_zone3 = MagicMock()
    pdns_zone3.name = "sync-needed.com."
    pdns_zone3.id = "sync-needed.com"
    pdns_zone3.serial = 1001

    netbox_pdns_instance.zones_api.list_zones.return_value = [
        pdns_zone1,
        pdns_zone2,
        pdns_zone3,
    ]

    # Mock the zones returned from Netbox
    nb_zone1 = MagicMock()
    nb_zone1.name = "existing.com"
    nb_zone1.soa_serial = 1000

    nb_zone2 = MagicMock()
    nb_zone2.name = "to-be-created.com"

    nb_zone3 = MagicMock()
    nb_zone3.name = "sync-needed.com"
    nb_zone3.soa_serial = 1002  # Different from pdns_zone3.serial -> needs sync

    netbox_pdns_instance.nb.plugins.netbox_dns.zones.filter.return_value = [
        nb_zone1,
        nb_zone2,
        nb_zone3,
    ]

    # Mock sync_zone, create_zone, and delete_zone methods
    with patch.object(netbox_pdns_instance, "sync_zone") as mock_sync:
        with patch.object(netbox_pdns_instance, "create_zone") as mock_create:
            with patch.object(netbox_pdns_instance, "delete_zone") as mock_delete:
                # Call full_sync
                result = netbox_pdns_instance.full_sync()

                # Verify API calls were made
                netbox_pdns_instance.zones_api.list_zones.assert_called_once_with(
                    netbox_pdns_instance.config.pdns_server_id
                )

                netbox_pdns_instance.nb.plugins.netbox_dns.zones.filter.assert_called_once_with(
                    nameserver_id=netbox_pdns_instance.config.nb_ns_id
                )

                # Verify logging
                netbox_pdns_instance.logger.info.assert_called_with(
                    "Synchronizing all zones from Netbox"
                )

                # Verify sync_zone calls
                # We expect 2 sync calls - for existing.com and sync-needed.com
                assert mock_sync.call_count == 2
                sync_calls = [call(nb_zone1, pdns_zone1), call(nb_zone3, pdns_zone3)]
                mock_sync.assert_has_calls(sync_calls, any_order=True)

                # Verify create_zone calls
                mock_create.assert_called_once_with(nb_zone2)

                # Verify delete_zone calls - should be called with dns.name.Name object
                assert mock_delete.call_count == 1
                # Extract the argument from the call and check it's a dns.name.Name object
                delete_arg = mock_delete.call_args[0][0]
                assert isinstance(delete_arg, dns.name.Name)
                assert delete_arg.to_text() == "to-be-deleted.com."

                # Verify result
                assert result == {"result": "success"}


def test_full_sync_empty_zones(netbox_pdns_instance: Mock) -> None:
    """Test full_sync when no zones exist in either system"""
    # Mock empty zone lists
    netbox_pdns_instance.zones_api.list_zones.return_value = []
    netbox_pdns_instance.nb.plugins.netbox_dns.zones.filter.return_value = []

    # Mock sync_zone, create_zone, and delete_zone methods
    with patch.object(netbox_pdns_instance, "sync_zone") as mock_sync:
        with patch.object(netbox_pdns_instance, "create_zone") as mock_create:
            with patch.object(netbox_pdns_instance, "delete_zone") as mock_delete:
                # Call full_sync
                result = netbox_pdns_instance.full_sync()

                # Verify none of the methods were called
                mock_sync.assert_not_called()
                mock_create.assert_not_called()
                mock_delete.assert_not_called()

                # Verify result
                assert result == {"result": "success"}
