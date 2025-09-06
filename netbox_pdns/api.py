import logging
import random
import sys
import threading
import time
from collections.abc import Callable, Generator
from contextlib import contextmanager
from typing import Any, TypeVar

import dns.name
import pdns_auth_client
import pynetbox

from .exceptions import (
    NetboxAPIError,
    PowerDNSAPIError,
    ZoneNotFoundError,
    ZoneSyncError,
)
from .models import Settings

T = TypeVar("T")


class NetboxPDNS:
    def __init__(self) -> None:
        self.config = Settings()
        self.nb = self.setup_netbox()
        self.pdns = self.setup_pdns()
        self.zones_api = pdns_auth_client.ZonesApi(self.pdns)
        self.logger = self.setup_logging()
        # Thread lock to prevent concurrent operations
        self._operation_lock = threading.Lock()
        self.logger.info(f"Netbox PowerDNS Connector intialized id: {id(self)}")

    @contextmanager
    def _operation_lock_with_logging(self, operation_name: str) -> Generator[None, None, None]:
        """Context manager for operation lock with debug logging and timing"""
        self.logger.debug(f"Attempting to acquire lock for operation: {operation_name}")
        start_time = time.time()

        # Try to acquire lock with timeout to detect contention
        acquired = self._operation_lock.acquire(timeout=30.0)
        if not acquired:
            self.logger.warning(f"Failed to acquire lock for {operation_name} within 30 seconds")
            raise TimeoutError(f"Lock timeout for operation: {operation_name}")

        acquire_time = time.time() - start_time
        if acquire_time > 1.0:  # Log if we waited more than 1 second
            self.logger.warning(
                f"Lock acquired for {operation_name} after {acquire_time:.2f}s wait"
            )
        else:
            self.logger.debug(f"Lock acquired for {operation_name} (waited {acquire_time:.3f}s)")

        try:
            yield
        finally:
            self._operation_lock.release()
            total_time = time.time() - start_time
            self.logger.debug(
                f"Lock released for {operation_name} (total operation time: {total_time:.3f}s)"
            )

    def retry_with_backoff(
        self,
        func: Callable[..., T],
        *args: Any,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        backoff_factor: float = 2.0,
        jitter: bool = True,
        **kwargs: Any,
    ) -> T:
        """Execute function with exponential backoff retry logic"""
        last_exception = None

        for attempt in range(max_attempts):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e

                if attempt == max_attempts - 1:  # Last attempt
                    self.logger.error(
                        f"Function {func.__name__} failed after {max_attempts} attempts: {e}"
                    )
                    raise e

                # Calculate delay with exponential backoff
                delay = min(base_delay * (backoff_factor**attempt), max_delay)

                # Add jitter to prevent thundering herd
                if jitter:
                    delay = delay * (0.5 + random.random() * 0.5)  # noqa: S311

                self.logger.warning(
                    f"Function {func.__name__} failed (attempt {attempt + 1}/{max_attempts}): {e}. "
                    f"Retrying in {delay:.2f}s"
                )
                time.sleep(delay)

        # This should never be reached, but just in case
        raise last_exception or Exception("Retry failed")

    def setup_logging(self) -> logging.Logger:
        log_level = self.config.log_level
        log_level = getattr(logging, log_level.upper())

        # Create a logger
        logger = logging.getLogger("netbox_pdns")
        logger.setLevel(log_level)

        # Create a stream handler that outputs to stdout
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(log_level)

        # Create a formatter and add it to the handler
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)

        # Add the handler to the logger
        logger.addHandler(handler)

        return logger

    def setup_netbox(self) -> pynetbox.api:
        return pynetbox.api(self.config.nb_url, token=self.config.nb_token)

    def setup_pdns(self) -> pdns_auth_client.ApiClient:
        configuration = pdns_auth_client.Configuration(host=self.config.pdns_url)
        configuration.api_key["APIKeyHeader"] = self.config.pdns_token
        return pdns_auth_client.ApiClient(configuration)

    def get_nb_zone(self, zone_id: int) -> pynetbox.core.response.Record:
        """Get a Netbox zone by ID.

        Args:
            zone_id: The Netbox zone ID

        Returns:
            The zone record

        Raises:
            NetboxAPIError: If there's an error communicating with Netbox
            ZoneNotFoundError: If the zone is not found
        """
        if zone_id <= 0:
            raise ValueError("Zone ID must be positive")

        try:
            zone = self.nb.plugins.netbox_dns.zones.get(id=zone_id)
            if zone is None:
                raise ZoneNotFoundError(f"Zone ID {zone_id}")
            return zone
        except ZoneNotFoundError:
            raise
        except Exception as e:
            raise NetboxAPIError(f"Failed to fetch zone ID {zone_id} from Netbox: {e}") from e

    def get_nb_zone_by_name(self, zone_name: str) -> pynetbox.core.response.Record | None:
        """Get a Netbox zone by name.

        Args:
            zone_name: The DNS zone name to look up

        Returns:
            The zone record if found, None otherwise

        Raises:
            NetboxAPIError: If there's an error communicating with Netbox
        """
        if not zone_name or not zone_name.strip():
            return None

        try:
            zones = self.nb.plugins.netbox_dns.zones.filter(name=zone_name.strip())
            # RecordSet is an iterator, get the first item by iterating
            for zone in zones:
                return zone
            return None
        except Exception as e:
            raise NetboxAPIError(f"Failed to fetch zone {zone_name} from Netbox: {e}") from e

    def get_pdns_zone(self, zone_id: str) -> pdns_auth_client.Zone:
        """Get a PowerDNS zone by ID.

        Args:
            zone_id: The PowerDNS zone ID (usually the zone name)

        Returns:
            The zone record

        Raises:
            PowerDNSAPIError: If there's an error communicating with PowerDNS
            ZoneNotFoundError: If the zone is not found
        """
        if not zone_id or not zone_id.strip():
            raise ValueError("Zone ID cannot be empty")

        def _get_pdns_zone() -> pdns_auth_client.Zone:
            zone = self.zones_api.list_zone(self.config.pdns_server_id, zone_id.strip())
            if zone is None:
                raise ZoneNotFoundError(zone_id)
            return zone

        try:
            return self.retry_with_backoff(_get_pdns_zone)
        except ZoneNotFoundError:
            raise
        except Exception as e:
            raise PowerDNSAPIError(f"Failed to fetch zone {zone_id} from PowerDNS: {e}") from e

    def get_nb_rrsets(self, zone_id: int) -> dict:
        """Get Netbox records for a zone, grouped by FQDN and record type.

        Args:
            zone_id: The Netbox zone ID

        Returns:
            Dictionary mapping (fqdn, record_type) tuples to lists of records

        Raises:
            NetboxAPIError: If there's an error communicating with Netbox
        """
        if zone_id <= 0:
            raise ValueError("Zone ID must be positive")

        try:
            nb_records = self.nb.plugins.netbox_dns.records.filter(zone_id=zone_id)
            nb_rrsets: dict = {}
            for record in nb_records:
                key = (record.fqdn, record.type)
                if key not in nb_rrsets:
                    nb_rrsets[key] = []
                nb_rrsets[key].append(record)
            return nb_rrsets
        except Exception as e:
            raise NetboxAPIError(f"Failed to fetch records for zone ID {zone_id}: {e}") from e

    def _mk_pdns_rrsets(
        self,
        nb_zone: pynetbox.core.response.Record,
        nb_rrsets: dict,
        nb_rrsets_deleted: set | None = None,
        nb_rrsets_replace: set | None = None,
    ) -> list:
        if nb_rrsets_deleted is None:
            nb_rrsets_deleted = set()
        if nb_rrsets_replace is None:
            nb_rrsets_replace = set()
        pdns_rrsets = []
        for nb_rrset in nb_rrsets_deleted:
            self.logger.info(f"Deleting RRSet {nb_rrset}")
            pdns_rrset = pdns_auth_client.RRSet(
                changetype="DELETE", name=nb_rrset[0], type=nb_rrset[1], records=[]
            )
            pdns_rrsets.append(pdns_rrset)
        for nb_rrset in nb_rrsets_replace:
            self.logger.info(f"Replacing RRSet {nb_rrset}")
            nb_record_ttl = nb_rrsets[nb_rrset][0].ttl
            pdns_rrset = pdns_auth_client.RRSet(
                changetype="REPLACE",
                name=nb_rrset[0],
                type=nb_rrset[1],
                ttl=nb_record_ttl if nb_record_ttl is not None else nb_zone.default_ttl,
                records=[pdns_auth_client.Record(content=r.value) for r in nb_rrsets[nb_rrset]],
            )
            pdns_rrsets.append(pdns_rrset)
        return pdns_rrsets

    def full_sync(self) -> dict[str, str]:
        with self._operation_lock_with_logging("full_sync"):
            self.logger.info("Synchronizing all zones from Netbox")

            pdns_zones_list = self.zones_api.list_zones(self.config.pdns_server_id)
            pdns_zones = {
                dns.name.from_text(z.name if z.name is not None else ""): z for z in pdns_zones_list
            }
            self.logger.debug(f"pdns_zones = {pdns_zones}")

            nb_zones = self.nb.plugins.netbox_dns.zones.filter(nameserver_id=self.config.nb_ns_id)
            nb_zones = {dns.name.from_text(z.name): z for z in nb_zones}
            self.logger.debug(f"nb_zones = {nb_zones}")

            pdns_zone_set = set(pdns_zones.keys())
            nb_zone_set = set(nb_zones.keys())

            self.logger.debug(f"pdns_zone_set = {pdns_zone_set}")
            self.logger.debug(f"nb_zone_set = {nb_zone_set}")

            sync_zones = pdns_zone_set & nb_zone_set
            self.logger.debug(f"sync_zones = {sync_zones}")
            for zone in sync_zones:
                self.sync_zone(nb_zones[zone], pdns_zones[zone])

            nb_created = nb_zone_set - pdns_zone_set
            self.logger.debug(f"nb_created = {nb_created}")
            for zone in nb_created:
                self.create_zone(nb_zones[zone])

            nb_deleted = pdns_zone_set - nb_zone_set
            self.logger.debug(f"nb_deleted = {nb_deleted}")
            for zone in nb_deleted:
                self.delete_zone(zone)

            return {"result": "success"}

    def create_zone(self, nb_zone: pynetbox.core.response.Record) -> None:
        self.logger.info(f"Creating zone {nb_zone.name}")

        # Retrieve RRSets from Netbox
        nb_rrsets = self.get_nb_rrsets(nb_zone.id)
        self.logger.debug(f"nb_rrsets = {nb_rrsets}")

        # Make PowerDNS RRSets from Netbox RRSets
        pdns_rrsets = self._mk_pdns_rrsets(
            nb_zone, nb_rrsets, nb_rrsets_replace=set(nb_rrsets.keys())
        )
        self.logger.debug(f"pdns_rrsets = {pdns_rrsets}")

        # Build Zone struct to create on PowerDNS server
        pdns_zone = pdns_auth_client.Zone(
            name=dns.name.from_text(nb_zone.name).to_text(),
            serial=nb_zone.soa_serial,
            rrsets=pdns_rrsets,
            soa_edit_api="",
            kind="Native",
        )

        def _create_pdns_zone() -> None:
            self.zones_api.create_zone(self.config.pdns_server_id, pdns_zone)

        try:
            self.retry_with_backoff(_create_pdns_zone)
        except Exception as e:
            error_msg = f"Failed to create zone {nb_zone.name} in PowerDNS: {e}"
            # Check if it's a 409 Conflict (zone already exists)
            if "409" in str(e) and "Conflict" in str(e):
                self.logger.warning(
                    f"Zone {nb_zone.name} already exists in PowerDNS, skipping creation"
                )
                return
            else:
                self.logger.error(error_msg)
                raise PowerDNSAPIError(error_msg) from e

    def delete_zone(self, zone: dns.name.Name) -> None:
        self.logger.info(f"Deleting zone {zone.to_text()}")

        def _delete_pdns_zone() -> None:
            self.zones_api.delete_zone(self.config.pdns_server_id, zone.to_text())

        try:
            self.retry_with_backoff(_delete_pdns_zone)
        except Exception as e:
            error_msg = f"Failed to delete zone {zone.to_text()} from PowerDNS: {e}"
            self.logger.error(error_msg)
            raise PowerDNSAPIError(error_msg) from e

    def sync_zone(
        self, nb_zone: pynetbox.core.response.Record, pdns_zone: pdns_auth_client.Zone
    ) -> None:
        # Skip synchronizing the zone when the serials from both APIs match
        if nb_zone.soa_serial == pdns_zone.serial:
            self.logger.info(
                f"Skipping synchronization of zone {nb_zone.name} because serial numbers match"
            )
            return

        self.logger.info(f"Synchronizing zone {nb_zone.name}")

        # Retrieve RRSets from Netbox
        nb_rrsets = self.get_nb_rrsets(nb_zone.id)
        self.logger.debug(f"nb_rrsets = {nb_rrsets}")

        # Retrieve RRSets from PowerDNS Server
        pdns_rrsets_list = self.zones_api.list_zone(
            self.config.pdns_server_id, pdns_zone.id if pdns_zone.id is not None else ""
        ).rrsets
        pdns_rrsets_list = [] if pdns_rrsets_list is None else pdns_rrsets_list
        pdns_rrsets = {(r.name, r.type): r for r in pdns_rrsets_list}
        self.logger.debug(f"pdns_rrsets = {pdns_rrsets}")

        # Create sets from each RRSet collection
        nb_rrsets_set = set(nb_rrsets.keys())
        pdns_rrsets_set = set(pdns_rrsets.keys())
        self.logger.debug(f"nb_rrsets_set = {nb_rrsets_set}")
        self.logger.debug(f"pdns_rrsets_set = {pdns_rrsets_set}")

        # Determine the RRSets that need to be replaced and deleted
        nb_rrsets_deleted = pdns_rrsets_set - nb_rrsets_set
        nb_rrsets_replace = nb_rrsets_set - nb_rrsets_deleted
        self.logger.debug(f"nb_rrsets_deleted = {nb_rrsets_deleted}")
        self.logger.debug(f"nb_rrsets_replace = {nb_rrsets_replace}")

        # Create RRSet patch to apply to zone
        pdns_rrset_patch = self._mk_pdns_rrsets(
            nb_zone, nb_rrsets, nb_rrsets_deleted, nb_rrsets_replace
        )
        self.logger.debug(f"pdns_rrset_patch = {pdns_rrset_patch}")

        # Build Zone struct to patch PowerDNS server
        pdns_zone_updated = pdns_auth_client.Zone(
            name=pdns_zone.name, serial=nb_zone.soa_serial, rrsets=pdns_rrset_patch
        )

        def _patch_pdns_zone() -> None:
            self.zones_api.patch_zone(
                self.config.pdns_server_id,
                pdns_zone.id if pdns_zone.id is not None else "",
                pdns_zone_updated,
            )

        try:
            self.retry_with_backoff(_patch_pdns_zone)
        except Exception as e:
            error_msg = f"Failed to patch zone {pdns_zone.name} in PowerDNS: {e}"
            self.logger.error(error_msg)
            raise ZoneSyncError(pdns_zone.name or "unknown", str(e)) from e
