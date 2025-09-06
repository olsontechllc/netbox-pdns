import asyncio
import json
import logging
import time
from collections.abc import Callable
from typing import Any
from urllib.parse import urlparse

import dns.name
import paho.mqtt.client as mqtt
from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError

from .exceptions import MQTTConnectionError, ValidationError
from .models import Settings


class MQTTZoneUpdate(BaseModel):
    """Model for MQTT zone update messages"""

    zone: str
    serial: int
    event: str
    timestamp: float
    nameserver_ids: list[int] | None = None

    def validate_zone_name(self) -> None:
        """Validate that the zone name is a valid DNS name"""
        if not self.zone or not self.zone.strip():
            raise ValidationError(f"Invalid DNS zone name '{self.zone}': empty zone name")
        try:
            dns.name.from_text(self.zone)
        except Exception as e:
            raise ValidationError(f"Invalid DNS zone name '{self.zone}': {e}") from e


class MQTTService:
    """MQTT service for receiving zone update notifications"""

    def __init__(self, config: Settings, zone_handler: Callable[[MQTTZoneUpdate], None]) -> None:
        self.config = config
        self.zone_handler = zone_handler
        self.logger = logging.getLogger("netbox_pdns.mqtt")
        self.client: mqtt.Client | None = None
        self.connected = False
        self.reconnect_delay = config.mqtt_reconnect_delay
        self.max_reconnect_delay = 300
        self._shutdown_event = asyncio.Event()

    def _parse_broker_url(self) -> tuple[str, int, bool]:
        """Parse MQTT broker URL and return host, port, and TLS flag"""
        parsed = urlparse(self.config.mqtt_broker_url)
        
        if parsed.scheme == "mqtt":
            port = parsed.port or 1883
            use_tls = False
        elif parsed.scheme == "mqtts":
            port = parsed.port or 8883
            use_tls = True
        else:
            raise MQTTConnectionError(f"Unsupported MQTT scheme: {parsed.scheme}")
        
        return parsed.hostname or "localhost", port, use_tls

    def _on_connect(self, client: mqtt.Client, userdata: Any, flags: dict, rc: int, properties: Any = None) -> None:
        """Callback for when the client connects to the MQTT broker"""
        if rc == 0:
            self.connected = True
            self.reconnect_delay = self.config.mqtt_reconnect_delay  # Reset delay on successful connection
            self.logger.info(f"Connected to MQTT broker at {self.config.mqtt_broker_url}")
            
            # Subscribe to zone update topics
            topic = f"{self.config.mqtt_topic_prefix}/+/+"
            client.subscribe(topic, qos=self.config.mqtt_qos)
            self.logger.info(f"Subscribed to MQTT topic: {topic}")
        else:
            self.connected = False
            error_messages = {
                1: "Connection refused - incorrect protocol version",
                2: "Connection refused - invalid client identifier",
                3: "Connection refused - server unavailable",
                4: "Connection refused - bad username or password",
                5: "Connection refused - not authorised"
            }
            error_msg = error_messages.get(rc, f"Connection refused - unknown error ({rc})")
            self.logger.error(f"Failed to connect to MQTT broker: {error_msg}")

    def _on_disconnect(self, client: mqtt.Client, userdata: Any, rc: int, properties: Any = None) -> None:
        """Callback for when the client disconnects from the MQTT broker"""
        self.connected = False
        if rc == 0:
            self.logger.info("Disconnected from MQTT broker")
        else:
            self.logger.warning(f"Unexpected disconnection from MQTT broker (code: {rc})")

    def _on_message(self, client: mqtt.Client, userdata: Any, message: mqtt.MQTTMessage) -> None:
        """Callback for when a message is received from the MQTT broker"""
        try:
            # Parse topic to extract zone name and event
            topic_parts = message.topic.split("/")
            if len(topic_parts) < 3:
                self.logger.warning(f"Invalid topic format: {message.topic}")
                return
            
            expected_prefix_parts = self.config.mqtt_topic_prefix.split("/")
            if len(topic_parts) < len(expected_prefix_parts) + 2:
                self.logger.warning(f"Topic doesn't match expected format: {message.topic}")
                return
            
            # Extract zone name and event from topic
            zone_name = topic_parts[len(expected_prefix_parts)]
            event_type = topic_parts[len(expected_prefix_parts) + 1]
            
            # Parse message payload
            try:
                payload = json.loads(message.payload.decode('utf-8'))
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse JSON payload: {e}")
                return
            
            # Validate message format
            try:
                zone_update = MQTTZoneUpdate(**payload)
                zone_update.validate_zone_name()
            except PydanticValidationError as e:
                self.logger.error(f"Invalid zone update message format: {e}")
                return
            except ValidationError as e:
                self.logger.error(f"Zone validation error: {e}")
                return
            
            # Verify zone name consistency
            if zone_update.zone != zone_name:
                self.logger.warning(
                    f"Zone name mismatch: topic={zone_name}, payload={zone_update.zone}"
                )
                return
            
            # Verify event type consistency
            if zone_update.event != event_type:
                self.logger.warning(
                    f"Event type mismatch: topic={event_type}, payload={zone_update.event}"
                )
                return
            
            # Check message age (ignore messages older than 5 minutes)
            message_age = time.time() - zone_update.timestamp
            if message_age > 300:
                self.logger.warning(
                    f"Ignoring old message for {zone_name} (age: {message_age:.1f}s)"
                )
                return
            
            self.logger.info(
                f"Processing MQTT zone update: {zone_name} ({event_type}, serial: {zone_update.serial})"
            )
            
            # Call the zone handler
            self.zone_handler(zone_update)
            
        except Exception as e:
            self.logger.error(f"Error processing MQTT message: {e}", exc_info=True)

    def _on_subscribe(self, client: mqtt.Client, userdata: Any, mid: int, granted_qos: list, properties: Any = None) -> None:
        """Callback for when a subscription is confirmed"""
        self.logger.debug(f"Subscription confirmed (mid: {mid}, qos: {granted_qos})")

    def _on_log(self, client: mqtt.Client, userdata: Any, level: int, buf: str) -> None:
        """Callback for MQTT client logging"""
        if level == mqtt.MQTT_LOG_DEBUG:
            self.logger.debug(f"MQTT: {buf}")
        elif level == mqtt.MQTT_LOG_INFO:
            self.logger.info(f"MQTT: {buf}")
        elif level == mqtt.MQTT_LOG_WARNING:
            self.logger.warning(f"MQTT: {buf}")
        elif level == mqtt.MQTT_LOG_ERR:
            self.logger.error(f"MQTT: {buf}")

    def start(self) -> None:
        """Start the MQTT client and connect to broker"""
        if not self.config.mqtt_enabled:
            self.logger.info("MQTT is disabled, skipping connection")
            return
        
        try:
            # Create MQTT client
            self.client = mqtt.Client(
                callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
                client_id=self.config.mqtt_client_id,
                protocol=mqtt.MQTTv5
            )
            
            # Set callbacks
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            self.client.on_message = self._on_message
            self.client.on_subscribe = self._on_subscribe
            self.client.on_log = self._on_log
            
            # Configure authentication if provided
            if self.config.mqtt_username and self.config.mqtt_password:
                self.client.username_pw_set(
                    self.config.mqtt_username, 
                    self.config.mqtt_password
                )
                self.logger.info("MQTT authentication configured")
            
            # Parse broker URL
            host, port, use_tls = self._parse_broker_url()
            
            # Configure TLS if needed
            if use_tls:
                self.client.tls_set()
                self.logger.info("MQTT TLS enabled")
            
            # Connect to broker
            self.logger.info(f"Connecting to MQTT broker: {host}:{port}")
            self.client.connect(host, port, keepalive=self.config.mqtt_keepalive)
            
            # Start the client loop in a separate thread
            self.client.loop_start()
            
        except Exception as e:
            error_msg = f"Failed to start MQTT client: {e}"
            self.logger.error(error_msg, exc_info=True)
            raise MQTTConnectionError(error_msg) from e

    def stop(self) -> None:
        """Stop the MQTT client and disconnect from broker"""
        self._shutdown_event.set()
        
        if self.client:
            self.logger.info("Stopping MQTT client")
            self.client.loop_stop()
            if self.connected:
                self.client.disconnect()
            self.connected = False
            self.client = None

    def is_connected(self) -> bool:
        """Check if the MQTT client is connected"""
        return self.connected

    async def wait_for_connection(self, timeout: float = 10.0) -> bool:
        """Wait for MQTT connection to be established"""
        if not self.config.mqtt_enabled:
            return True
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.connected:
                return True
            await asyncio.sleep(0.1)
        
        return False

    def get_status(self) -> dict[str, Any]:
        """Get MQTT service status information"""
        return {
            "enabled": self.config.mqtt_enabled,
            "connected": self.connected,
            "broker_url": self.config.mqtt_broker_url,
            "client_id": self.config.mqtt_client_id,
            "topic_prefix": self.config.mqtt_topic_prefix,
            "qos": self.config.mqtt_qos,
        }