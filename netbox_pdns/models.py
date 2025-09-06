import re
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from .exceptions import ConfigurationError, ValidationError


class Settings(BaseSettings):
    """
    In order to operate, the connector needs to be configured with the required variables.

    At a minimum, you will require:
      - URL of a Netbox installation with the Netbox DNS plugin installed
      - API Key for Netbox, with permissions specified in the documentation
      - URL of a PowerDNS authoritative server API
      - API Key for the PowerDNS Authoritative Server API
      - The ID number in Netbox of the Nameserver object associated with this instance
      - An API Key string must be configured to authenticate Netbox web hooks

    The connector is not designed to operate on PowerDNS servers with existing records. It should
    co-exist with other domains that are not also managed in Netbox, but any records that are not
    in Netbox will be removed from the PowerDNS server for all domains that exist in Netbox.
    """

    model_config = SettingsConfigDict(env_prefix="NETBOX_PDNS_", title="Netbox PowerDNS Connector")
    api_key: str = Field(
        default=...,
        description="The secret API key used to authenticate webhook requests from Netbox",
    )
    webhook_secret: str | None = Field(
        default=None, 
        description="Secret for HMAC webhook signature verification. If not set, only API key auth is used."
    )
    sync_crontab: str = Field(
        default="* * * * *",
        description="A string in crontab format that schedules a periodic full synchronization",
    )
    
    @field_validator("sync_crontab")
    @classmethod
    def validate_sync_crontab(cls, v: str) -> str:
        """Validate crontab format (basic validation)."""
        if not v or not v.strip():
            raise ValidationError("Crontab expression cannot be empty")
        
        # Basic crontab validation - should have 5 parts
        parts = v.strip().split()
        if len(parts) != 5:
            raise ValidationError(
                f"Invalid crontab format: {v}. Expected 5 parts (minute hour day month weekday)"
            )
        
        return v.strip()
    log_level: str = Field(default="INFO", description="Sets the log level of the console")
    
    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate that log level is supported."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in valid_levels:
            raise ValidationError(f"Invalid log level '{v}'. Must be one of: {', '.join(valid_levels)}")
        return v.upper()
    nb_url: str = Field(
        default=...,
        description="URL of a Netbox installation running the Netbox DNS plugin",
    )
    
    @field_validator("nb_url")
    @classmethod
    def validate_nb_url(cls, v: str) -> str:
        """Validate Netbox URL format."""
        if not v or not v.strip():
            raise ValidationError("Netbox URL cannot be empty")
        
        parsed = urlparse(v.strip())
        if not parsed.scheme or not parsed.netloc:
            raise ValidationError(f"Invalid Netbox URL format: {v}")
        if parsed.scheme not in {"http", "https"}:
            raise ValidationError(f"Netbox URL must use http or https scheme, got: {parsed.scheme}")
        
        return v.strip().rstrip('/')
    nb_token: str = Field(default=..., description="API token for the Netbox server")
    nb_ns_id: int = Field(
        default=...,
        ge=1,
        description="ID number in Netbox of the Nameserver object associated with this instance",
    )
    pdns_url: str = Field(default=..., description="URL of the PowerDNS Authoritative Server API")
    
    @field_validator("pdns_url")
    @classmethod
    def validate_pdns_url(cls, v: str) -> str:
        """Validate PowerDNS URL format."""
        if not v or not v.strip():
            raise ValidationError("PowerDNS URL cannot be empty")
        
        parsed = urlparse(v.strip())
        if not parsed.scheme or not parsed.netloc:
            raise ValidationError(f"Invalid PowerDNS URL format: {v}")
        if parsed.scheme not in {"http", "https"}:
            raise ValidationError(f"PowerDNS URL must use http or https scheme, got: {parsed.scheme}")
        
        return v.strip().rstrip('/')
    pdns_token: str = Field(
        default=..., description="API token for the PowerDNS Authoritative Server API"
    )
    pdns_server_id: str = Field(
        default="localhost",
        description="The server identifier used when constructing PowerDNS API requests",
    )
    mqtt_enabled: bool = Field(
        default=False,
        description="Enable MQTT subscription for zone update notifications",
    )
    mqtt_broker_url: str = Field(
        default="mqtt://localhost:1883",
        description="MQTT broker URL (e.g., mqtt://localhost:1883 or mqtts://broker:8883)",
    )
    
    @field_validator("mqtt_broker_url")
    @classmethod
    def validate_mqtt_broker_url(cls, v: str) -> str:
        """Validate MQTT broker URL format."""
        if not v or not v.strip():
            raise ValidationError("MQTT broker URL cannot be empty")
        
        parsed = urlparse(v.strip())
        if not parsed.scheme or not parsed.netloc:
            raise ValidationError(f"Invalid MQTT broker URL format: {v}")
        if parsed.scheme not in {"mqtt", "mqtts"}:
            raise ValidationError(f"MQTT broker URL must use mqtt or mqtts scheme, got: {parsed.scheme}")
        
        return v.strip()
    mqtt_client_id: str = Field(
        default="netbox-pdns",
        min_length=1,
        max_length=23,  # MQTT client ID length limit
        description="Unique client ID for this MQTT connector instance",
    )
    
    @field_validator("mqtt_client_id")
    @classmethod
    def validate_mqtt_client_id(cls, v: str) -> str:
        """Validate MQTT client ID format."""
        if not v or not v.strip():
            raise ValidationError("MQTT client ID cannot be empty")
        
        # Check for valid characters (alphanumeric, dash, underscore)
        if not re.match(r'^[a-zA-Z0-9_-]+$', v.strip()):
            raise ValidationError("MQTT client ID can only contain alphanumeric characters, dashes, and underscores")
        
        return v.strip()
    mqtt_topic_prefix: str = Field(
        default="dns/zones",
        min_length=1,
        description="Topic prefix for DNS zone update messages",
    )
    
    @field_validator("mqtt_topic_prefix")
    @classmethod
    def validate_mqtt_topic_prefix(cls, v: str) -> str:
        """Validate MQTT topic prefix format."""
        if not v or not v.strip():
            raise ValidationError("MQTT topic prefix cannot be empty")
        
        # Remove leading/trailing slashes and validate characters
        cleaned = v.strip().strip('/')
        if not re.match(r'^[a-zA-Z0-9_/-]+$', cleaned):
            raise ValidationError("MQTT topic prefix can only contain alphanumeric characters, dashes, underscores, and forward slashes")
        
        return cleaned
    mqtt_qos: int = Field(
        default=1,
        ge=0,
        le=2,
        description="MQTT Quality of Service level (0, 1, or 2)",
    )
    mqtt_username: str | None = Field(
        default=None,
        description="MQTT broker username for authentication",
    )
    mqtt_password: str | None = Field(
        default=None,
        description="MQTT broker password for authentication",
    )
    mqtt_keepalive: int = Field(
        default=60,
        ge=10,
        le=3600,
        description="MQTT keepalive interval in seconds",
    )
    mqtt_reconnect_delay: int = Field(
        default=5,
        ge=1,
        le=300,
        description="Initial delay between MQTT reconnection attempts in seconds",
    )
    
    @model_validator(mode='after')
    def validate_mqtt_auth(self) -> 'Settings':
        """Validate MQTT authentication configuration."""
        # If one auth field is provided, both should be provided
        if self.mqtt_enabled:
            has_username = self.mqtt_username is not None and bool(self.mqtt_username.strip() if self.mqtt_username else False)
            has_password = self.mqtt_password is not None and bool(self.mqtt_password.strip() if self.mqtt_password else False)
            
            if has_username != has_password:
                raise ConfigurationError(
                    "Both mqtt_username and mqtt_password must be provided together, or both omitted"
                )
        
        return self


class NetboxWebhook(BaseModel):
    id: int
    name: str
    serial: int | None = None
