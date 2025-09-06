"""Custom exceptions for netbox-pdns."""


class NetboxPDNSError(Exception):
    """Base exception for all netbox-pdns errors."""

    pass


class ConfigurationError(NetboxPDNSError):
    """Raised when there's an issue with configuration."""

    pass


class NetboxAPIError(NetboxPDNSError):
    """Raised when there's an error communicating with Netbox API."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class PowerDNSAPIError(NetboxPDNSError):
    """Raised when there's an error communicating with PowerDNS API."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class ZoneNotFoundError(NetboxPDNSError):
    """Raised when a requested zone is not found."""

    def __init__(self, zone_name: str) -> None:
        super().__init__(f"Zone not found: {zone_name}")
        self.zone_name = zone_name


class ZoneSyncError(NetboxPDNSError):
    """Raised when there's an error during zone synchronization."""

    def __init__(self, zone_name: str, message: str) -> None:
        super().__init__(f"Error syncing zone {zone_name}: {message}")
        self.zone_name = zone_name


class MQTTConnectionError(NetboxPDNSError):
    """Raised when there's an error connecting to MQTT broker."""

    pass


class MQTTMessageError(NetboxPDNSError):
    """Raised when there's an error processing MQTT messages."""

    pass


class ValidationError(NetboxPDNSError):
    """Raised when data validation fails."""

    pass