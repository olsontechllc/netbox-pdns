import asyncio
import json
import time
from unittest.mock import Mock, patch

import pytest
from pydantic import ValidationError as PydanticValidationError

from netbox_pdns.exceptions import MQTTConnectionError, ValidationError
from netbox_pdns.models import Settings
from netbox_pdns.mqtt_service import MQTTService, MQTTZoneUpdate


class TestMQTTZoneUpdate:
    """Test the MQTTZoneUpdate model"""

    def test_valid_zone_update(self) -> None:
        """Test creating a valid zone update"""
        timestamp = time.time()
        update = MQTTZoneUpdate(
            zone="example.com",
            serial=2023010101,
            event="update",
            timestamp=timestamp,
            nameserver_ids=[1, 2, 3],
        )
        assert update.zone == "example.com"
        assert update.serial == 2023010101
        assert update.event == "update"
        assert update.nameserver_ids == [1, 2, 3]

    def test_zone_update_without_nameserver_ids(self) -> None:
        """Test zone update without nameserver IDs (optional field)"""
        timestamp = time.time()
        update = MQTTZoneUpdate(
            zone="example.com",
            serial=2023010101,
            event="create",
            timestamp=timestamp,
        )
        assert update.nameserver_ids is None

    def test_invalid_zone_update_missing_required_field(self) -> None:
        """Test zone update with missing required field"""
        timestamp = time.time()
        
        with pytest.raises(PydanticValidationError):
            # Missing 'event' field should raise validation error
            MQTTZoneUpdate(
                zone="example.com",
                serial=2023010101,
                timestamp=timestamp,
            )  # type: ignore[call-arg]

    def test_validate_zone_name(self) -> None:
        """Test zone name validation"""
        update = MQTTZoneUpdate(zone="example.com", serial=1, event="create", timestamp=time.time())

        # Valid zone name should not raise
        update.validate_zone_name()

        # Invalid zone name should raise ValueError
        update.zone = ""
        with pytest.raises(ValidationError, match="Invalid DNS zone name"):
            update.validate_zone_name()


class TestMQTTService:
    """Test the MQTTService class"""

    @pytest.fixture
    def mqtt_settings(self) -> Settings:
        """Create MQTT-enabled settings for testing"""
        return Settings(
            api_key="test_key",
            nb_url="https://netbox.example.com",
            nb_token="nb_token",
            nb_ns_id=1,
            pdns_url="https://pdns.example.com",
            pdns_token="pdns_token",
            mqtt_enabled=True,
            mqtt_broker_url="mqtt://localhost:1883",
            mqtt_client_id="test-client",
            mqtt_topic_prefix="test/zones",
            mqtt_qos=1,
        )

    @pytest.fixture
    def disabled_mqtt_settings(self) -> Settings:
        """Create MQTT-disabled settings for testing"""
        return Settings(
            api_key="test_key",
            nb_url="https://netbox.example.com",
            nb_token="nb_token",
            nb_ns_id=1,
            pdns_url="https://pdns.example.com",
            pdns_token="pdns_token",
            mqtt_enabled=False,
        )

    @pytest.fixture
    def mock_zone_handler(self) -> Mock:
        """Create a mock zone handler function"""
        return Mock()

    def test_init(self, mqtt_settings: Settings, mock_zone_handler: Mock) -> None:
        """Test MQTT service initialization"""
        service = MQTTService(mqtt_settings, mock_zone_handler)

        assert service.config == mqtt_settings
        assert service.zone_handler == mock_zone_handler
        assert service.client is None
        assert service.connected is False
        assert service.reconnect_delay == mqtt_settings.mqtt_reconnect_delay

    def test_parse_broker_url_mqtt(self, mqtt_settings: Settings, mock_zone_handler: Mock) -> None:
        """Test parsing MQTT broker URL"""
        service = MQTTService(mqtt_settings, mock_zone_handler)

        host, port, use_tls = service._parse_broker_url()
        assert host == "localhost"
        assert port == 1883
        assert use_tls is False

    def test_parse_broker_url_mqtts(self, mqtt_settings: Settings, mock_zone_handler: Mock) -> None:
        """Test parsing MQTTS broker URL"""
        mqtt_settings.mqtt_broker_url = "mqtts://secure.broker:8883"
        service = MQTTService(mqtt_settings, mock_zone_handler)

        host, port, use_tls = service._parse_broker_url()
        assert host == "secure.broker"
        assert port == 8883
        assert use_tls is True

    def test_parse_broker_url_invalid_scheme(
        self, mqtt_settings: Settings, mock_zone_handler: Mock
    ) -> None:
        """Test parsing invalid broker URL scheme"""
        mqtt_settings.mqtt_broker_url = "http://invalid.broker"
        service = MQTTService(mqtt_settings, mock_zone_handler)

        with pytest.raises(MQTTConnectionError, match="Unsupported MQTT scheme"):
            service._parse_broker_url()

    def test_start_disabled(
        self, disabled_mqtt_settings: Settings, mock_zone_handler: Mock
    ) -> None:
        """Test starting MQTT service when disabled"""
        service = MQTTService(disabled_mqtt_settings, mock_zone_handler)

        with patch("paho.mqtt.client.Client") as mock_client_class:
            service.start()

            # Should not create MQTT client when disabled
            mock_client_class.assert_not_called()
            assert service.client is None

    @patch("paho.mqtt.client.Client")
    def test_start_enabled(
        self, mock_client_class: Mock, mqtt_settings: Settings, mock_zone_handler: Mock
    ) -> None:
        """Test starting MQTT service when enabled"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        service = MQTTService(mqtt_settings, mock_zone_handler)
        service.start()

        # Verify client creation and configuration
        mock_client_class.assert_called_once()
        assert service.client == mock_client

        # Verify callbacks are set
        assert mock_client.on_connect is not None
        assert mock_client.on_disconnect is not None
        assert mock_client.on_message is not None
        assert mock_client.on_subscribe is not None
        assert mock_client.on_log is not None

        # Verify connection attempt
        mock_client.connect.assert_called_once_with("localhost", 1883, keepalive=60)
        mock_client.loop_start.assert_called_once()

    @patch("paho.mqtt.client.Client")
    def test_start_with_auth(
        self, mock_client_class: Mock, mqtt_settings: Settings, mock_zone_handler: Mock
    ) -> None:
        """Test starting MQTT service with authentication"""
        mqtt_settings.mqtt_username = "testuser"
        mqtt_settings.mqtt_password = "testpass"  # noqa: S105

        mock_client = Mock()
        mock_client_class.return_value = mock_client

        service = MQTTService(mqtt_settings, mock_zone_handler)
        service.start()

        # Verify authentication is configured
        mock_client.username_pw_set.assert_called_once_with("testuser", "testpass")

    @patch("paho.mqtt.client.Client")
    def test_start_with_tls(
        self, mock_client_class: Mock, mqtt_settings: Settings, mock_zone_handler: Mock
    ) -> None:
        """Test starting MQTT service with TLS"""
        mqtt_settings.mqtt_broker_url = "mqtts://secure.broker:8883"

        mock_client = Mock()
        mock_client_class.return_value = mock_client

        service = MQTTService(mqtt_settings, mock_zone_handler)
        service.start()

        # Verify TLS is configured
        mock_client.tls_set.assert_called_once()
        mock_client.connect.assert_called_once_with("secure.broker", 8883, keepalive=60)

    def test_stop(self, mqtt_settings: Settings, mock_zone_handler: Mock) -> None:
        """Test stopping MQTT service"""
        service = MQTTService(mqtt_settings, mock_zone_handler)
        mock_client = Mock()
        service.client = mock_client
        service.connected = True

        service.stop()

        mock_client.loop_stop.assert_called_once()
        mock_client.disconnect.assert_called_once()
        assert service.client is None
        assert service.connected is False

    def test_stop_no_client(self, mqtt_settings: Settings, mock_zone_handler: Mock) -> None:
        """Test stopping MQTT service with no client"""
        service = MQTTService(mqtt_settings, mock_zone_handler)
        service.client = None

        # Should not raise exception
        service.stop()

    def test_is_connected(self, mqtt_settings: Settings, mock_zone_handler: Mock) -> None:
        """Test connection status check"""
        service = MQTTService(mqtt_settings, mock_zone_handler)

        assert service.is_connected() is False

        service.connected = True
        assert service.is_connected() is True

    @pytest.mark.asyncio
    async def test_wait_for_connection_disabled(
        self, disabled_mqtt_settings: Settings, mock_zone_handler: Mock
    ) -> None:
        """Test waiting for connection when MQTT is disabled"""
        service = MQTTService(disabled_mqtt_settings, mock_zone_handler)

        # Should return True immediately when disabled
        result = await service.wait_for_connection()
        assert result is True

    @pytest.mark.asyncio
    async def test_wait_for_connection_success(
        self, mqtt_settings: Settings, mock_zone_handler: Mock
    ) -> None:
        """Test waiting for connection success"""
        service = MQTTService(mqtt_settings, mock_zone_handler)

        # Simulate connection after short delay
        async def connect_after_delay() -> None:
            await asyncio.sleep(0.1)
            service.connected = True

        asyncio.create_task(connect_after_delay())

        result = await service.wait_for_connection(connection_timeout=1.0)
        assert result is True

    @pytest.mark.asyncio
    async def test_wait_for_connection_timeout(
        self, mqtt_settings: Settings, mock_zone_handler: Mock
    ) -> None:
        """Test waiting for connection timeout"""
        service = MQTTService(mqtt_settings, mock_zone_handler)
        # Don't set connected = True

        result = await service.wait_for_connection(connection_timeout=0.1)
        assert result is False

    def test_get_status(self, mqtt_settings: Settings, mock_zone_handler: Mock) -> None:
        """Test getting service status"""
        service = MQTTService(mqtt_settings, mock_zone_handler)
        service.connected = True

        status = service.get_status()

        expected = {
            "enabled": True,
            "connected": True,
            "broker_url": "mqtt://localhost:1883",
            "client_id": "test-client",
            "topic_prefix": "test/zones",
            "qos": 1,
        }
        assert status == expected

    def test_on_connect_success(self, mqtt_settings: Settings, mock_zone_handler: Mock) -> None:
        """Test successful MQTT connection callback"""
        service = MQTTService(mqtt_settings, mock_zone_handler)
        mock_client = Mock()

        service._on_connect(mock_client, None, {}, 0)

        assert service.connected is True
        mock_client.subscribe.assert_called_once_with("test/zones/+/+", qos=1)

    def test_on_connect_failure(self, mqtt_settings: Settings, mock_zone_handler: Mock) -> None:
        """Test failed MQTT connection callback"""
        service = MQTTService(mqtt_settings, mock_zone_handler)
        mock_client = Mock()

        service._on_connect(mock_client, None, {}, 4)  # Bad username/password

        assert service.connected is False
        mock_client.subscribe.assert_not_called()

    def test_on_disconnect(self, mqtt_settings: Settings, mock_zone_handler: Mock) -> None:
        """Test MQTT disconnection callback"""
        service = MQTTService(mqtt_settings, mock_zone_handler)
        service.connected = True

        service._on_disconnect(Mock(), None, 0)  # Clean disconnect
        assert service.connected is False

    def test_on_message_valid(self, mqtt_settings: Settings, mock_zone_handler: Mock) -> None:
        """Test processing valid MQTT message"""
        service = MQTTService(mqtt_settings, mock_zone_handler)

        # Create mock message
        mock_message = Mock()
        mock_message.topic = "test/zones/example.com/update"
        mock_message.payload.decode.return_value = json.dumps(
            {
                "zone": "example.com",
                "serial": 2023010101,
                "event": "update",
                "timestamp": time.time(),
                "nameserver_ids": [1, 2],
            }
        )

        service._on_message(Mock(), None, mock_message)

        # Verify handler was called
        mock_zone_handler.assert_called_once()
        called_update = mock_zone_handler.call_args[0][0]
        assert isinstance(called_update, MQTTZoneUpdate)
        assert called_update.zone == "example.com"
        assert called_update.event == "update"

    def test_on_message_invalid_topic(
        self, mqtt_settings: Settings, mock_zone_handler: Mock
    ) -> None:
        """Test processing message with invalid topic"""
        service = MQTTService(mqtt_settings, mock_zone_handler)

        # Create mock message with invalid topic
        mock_message = Mock()
        mock_message.topic = "invalid/topic"

        service._on_message(Mock(), None, mock_message)

        # Handler should not be called
        mock_zone_handler.assert_not_called()

    def test_on_message_invalid_json(
        self, mqtt_settings: Settings, mock_zone_handler: Mock
    ) -> None:
        """Test processing message with invalid JSON"""
        service = MQTTService(mqtt_settings, mock_zone_handler)

        # Create mock message with invalid JSON
        mock_message = Mock()
        mock_message.topic = "test/zones/example.com/update"
        mock_message.payload.decode.return_value = "invalid json"

        service._on_message(Mock(), None, mock_message)

        # Handler should not be called
        mock_zone_handler.assert_not_called()

    def test_on_message_invalid_zone_update(
        self, mqtt_settings: Settings, mock_zone_handler: Mock
    ) -> None:
        """Test processing message with invalid zone update format"""
        service = MQTTService(mqtt_settings, mock_zone_handler)

        # Create mock message with missing required fields
        mock_message = Mock()
        mock_message.topic = "test/zones/example.com/update"
        mock_message.payload.decode.return_value = json.dumps(
            {
                "zone": "example.com",
                # Missing 'serial', 'event', 'timestamp'
            }
        )

        service._on_message(Mock(), None, mock_message)

        # Handler should not be called
        mock_zone_handler.assert_not_called()

    def test_on_message_zone_name_mismatch(
        self, mqtt_settings: Settings, mock_zone_handler: Mock
    ) -> None:
        """Test processing message with zone name mismatch"""
        service = MQTTService(mqtt_settings, mock_zone_handler)

        # Create mock message with mismatched zone names
        mock_message = Mock()
        mock_message.topic = "test/zones/example.com/update"
        mock_message.payload.decode.return_value = json.dumps(
            {
                "zone": "different.com",  # Different from topic
                "serial": 2023010101,
                "event": "update",
                "timestamp": time.time(),
            }
        )

        service._on_message(Mock(), None, mock_message)

        # Handler should not be called
        mock_zone_handler.assert_not_called()

    def test_on_message_old_message(self, mqtt_settings: Settings, mock_zone_handler: Mock) -> None:
        """Test processing old message (should be ignored)"""
        service = MQTTService(mqtt_settings, mock_zone_handler)

        # Create mock message with old timestamp (older than 5 minutes)
        mock_message = Mock()
        mock_message.topic = "test/zones/example.com/update"
        mock_message.payload.decode.return_value = json.dumps(
            {
                "zone": "example.com",
                "serial": 2023010101,
                "event": "update",
                "timestamp": time.time() - 400,  # 400 seconds ago
            }
        )

        service._on_message(Mock(), None, mock_message)

        # Handler should not be called for old messages
        mock_zone_handler.assert_not_called()
