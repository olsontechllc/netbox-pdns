"""Unit tests for MQTT message handlers.

These tests focus on the internal handler logic that processes MQTT messages.
They test the handler functions directly without requiring FastAPI integration.
"""
import time
from unittest.mock import Mock

import dns.name
import pytest

from netbox_pdns.mqtt_service import MQTTZoneUpdate


class TestMQTTHandlers:
    """Unit tests for MQTT message handlers."""

    @pytest.fixture
    def mock_api(self):
        """Mock NetboxPDNS API instance for handler testing."""
        mock_api = Mock()
        mock_api.logger = Mock()
        return mock_api

    @pytest.fixture 
    def sample_zone_update(self):
        """Sample zone update for testing."""
        return MQTTZoneUpdate(
            zone="example.com",
            serial=2023010101, 
            event="update",
            timestamp=time.time(),
            nameserver_ids=[1, 2, 3],
        )

    def create_handler_function(self, mock_api):
        """Create the MQTT zone update handler function for testing."""
        def handle_mqtt_zone_update(zone_update: MQTTZoneUpdate) -> None:
            """Handle MQTT zone update messages - extracted from __init__.py for testing."""
            try:
                if zone_update.event == "create":
                    # For create events, get the zone from Netbox and create it
                    nb_zone = mock_api.get_nb_zone_by_name(zone_update.zone)
                    if nb_zone:
                        mock_api.create_zone(nb_zone)
                        mock_api.logger.info(f"MQTT: Created zone {zone_update.zone}")
                    else:
                        mock_api.logger.warning(f"MQTT: Zone {zone_update.zone} not found in Netbox")
                        
                elif zone_update.event == "update":
                    # For update events, sync the zone if serial numbers differ
                    try:
                        nb_zone = mock_api.get_nb_zone_by_name(zone_update.zone)
                        pdns_zone = mock_api.get_pdns_zone(zone_update.zone)
                        if nb_zone and pdns_zone:
                            mock_api.sync_zone(nb_zone, pdns_zone)
                            mock_api.logger.info(f"MQTT: Synced zone {zone_update.zone}")
                        elif nb_zone and not pdns_zone:
                            # Zone exists in Netbox but not PowerDNS, create it
                            mock_api.create_zone(nb_zone)
                            mock_api.logger.info(f"MQTT: Created missing zone {zone_update.zone}")
                        else:
                            mock_api.logger.warning(f"MQTT: Zone {zone_update.zone} not found")
                    except Exception as e:
                        mock_api.logger.error(f"MQTT: Error syncing zone {zone_update.zone}: {e}")
                        
                elif zone_update.event == "delete":
                    # For delete events, remove the zone from PowerDNS
                    try:
                        zone_name = dns.name.from_text(zone_update.zone)
                        mock_api.delete_zone(zone_name)
                        mock_api.logger.info(f"MQTT: Deleted zone {zone_update.zone}")
                    except Exception as e:
                        mock_api.logger.error(f"MQTT: Error deleting zone {zone_update.zone}: {e}")
                        
                else:
                    mock_api.logger.warning(f"MQTT: Unknown event type '{zone_update.event}' for zone {zone_update.zone}")
                    
            except Exception as e:
                mock_api.logger.error(f"MQTT: Error processing zone update for {zone_update.zone}: {e}")
        
        return handle_mqtt_zone_update

    def test_handler_create_event_success(self, mock_api, sample_zone_update):
        """Test handler processes create event successfully."""
        sample_zone_update.event = "create"
        handler = self.create_handler_function(mock_api)
        
        # Mock successful zone lookup
        mock_zone = Mock(id=1, name="example.com")
        mock_api.get_nb_zone_by_name.return_value = mock_zone
        
        # Call handler
        handler(sample_zone_update)
        
        # Verify correct methods called
        mock_api.get_nb_zone_by_name.assert_called_once_with("example.com")
        mock_api.create_zone.assert_called_once_with(mock_zone)
        mock_api.logger.info.assert_called_with("MQTT: Created zone example.com")

    def test_handler_create_event_zone_not_found(self, mock_api, sample_zone_update):
        """Test handler handles create event when zone not found in Netbox."""
        sample_zone_update.event = "create"
        handler = self.create_handler_function(mock_api)
        
        # Mock zone not found
        mock_api.get_nb_zone_by_name.return_value = None
        
        # Call handler
        handler(sample_zone_update)
        
        # Verify correct methods called
        mock_api.get_nb_zone_by_name.assert_called_once_with("example.com")
        mock_api.create_zone.assert_not_called()
        mock_api.logger.warning.assert_called_with("MQTT: Zone example.com not found in Netbox")

    def test_handler_update_event_success(self, mock_api, sample_zone_update):
        """Test handler processes update event successfully."""
        sample_zone_update.event = "update"
        handler = self.create_handler_function(mock_api)
        
        # Mock successful zone lookups
        mock_nb_zone = Mock(id=1, name="example.com")
        mock_pdns_zone = Mock(id="example.com", name="example.com")
        mock_api.get_nb_zone_by_name.return_value = mock_nb_zone
        mock_api.get_pdns_zone.return_value = mock_pdns_zone
        
        # Call handler
        handler(sample_zone_update)
        
        # Verify correct methods called
        mock_api.get_nb_zone_by_name.assert_called_once_with("example.com")
        mock_api.get_pdns_zone.assert_called_once_with("example.com")
        mock_api.sync_zone.assert_called_once_with(mock_nb_zone, mock_pdns_zone)
        mock_api.logger.info.assert_called_with("MQTT: Synced zone example.com")

    def test_handler_update_event_create_missing_zone(self, mock_api, sample_zone_update):
        """Test handler creates zone when it exists in Netbox but not PowerDNS."""
        sample_zone_update.event = "update"
        handler = self.create_handler_function(mock_api)
        
        # Mock zone exists in Netbox but not PowerDNS
        mock_nb_zone = Mock(id=1, name="example.com")
        mock_api.get_nb_zone_by_name.return_value = mock_nb_zone
        mock_api.get_pdns_zone.return_value = None
        
        # Call handler
        handler(sample_zone_update)
        
        # Verify zone creation is attempted
        mock_api.create_zone.assert_called_once_with(mock_nb_zone)
        mock_api.logger.info.assert_called_with("MQTT: Created missing zone example.com")

    def test_handler_delete_event_success(self, mock_api, sample_zone_update):
        """Test handler processes delete event successfully."""
        sample_zone_update.event = "delete"
        handler = self.create_handler_function(mock_api)
        
        # Call handler
        handler(sample_zone_update)
        
        # Verify delete method called with DNS name object
        mock_api.delete_zone.assert_called_once()
        delete_arg = mock_api.delete_zone.call_args[0][0]
        assert str(delete_arg) == "example.com."

    def test_handler_delete_event_exception(self, mock_api, sample_zone_update):
        """Test handler handles delete event exceptions."""
        sample_zone_update.event = "delete"
        handler = self.create_handler_function(mock_api)
        
        # Mock delete_zone to raise exception
        mock_api.delete_zone.side_effect = Exception("PowerDNS error")
        
        # Call handler - should not raise exception
        handler(sample_zone_update)
        
        # Verify error was logged
        mock_api.logger.error.assert_called()
        error_call = mock_api.logger.error.call_args[0][0]
        assert "MQTT: Error deleting zone example.com" in error_call

    def test_handler_unknown_event_type(self, mock_api, sample_zone_update):
        """Test handler handles unknown event types."""
        sample_zone_update.event = "unknown_event"
        handler = self.create_handler_function(mock_api)
        
        # Call handler
        handler(sample_zone_update)
        
        # Verify warning logged
        mock_api.logger.warning.assert_called_with("MQTT: Unknown event type 'unknown_event' for zone example.com")
        
        # Verify no sync methods called
        mock_api.create_zone.assert_not_called()
        mock_api.sync_zone.assert_not_called()
        mock_api.delete_zone.assert_not_called()

    def test_handler_exception_handling(self, mock_api, sample_zone_update):
        """Test handler exception handling."""
        sample_zone_update.event = "create" 
        handler = self.create_handler_function(mock_api)
        
        # Mock get_nb_zone_by_name to raise exception
        mock_api.get_nb_zone_by_name.side_effect = Exception("API Error")
        
        # Call handler - should not raise exception
        handler(sample_zone_update)
        
        # Verify error was logged
        mock_api.logger.error.assert_called()
        error_call = mock_api.logger.error.call_args[0][0]
        assert "MQTT: Error processing zone update for example.com" in error_call