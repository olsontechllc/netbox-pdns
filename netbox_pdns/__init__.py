import hashlib
import hmac
import json
import secrets
import threading
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

import dns.name
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import Depends, FastAPI, HTTPException, Request, Security
from fastapi.security import APIKeyHeader
from pydantic import ValidationError
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from starlette.status import HTTP_401_UNAUTHORIZED

from .api import NetboxPDNS
from .models import NetboxWebhook
from .mqtt_service import MQTTService, MQTTZoneUpdate


def create_app() -> FastAPI:
    api = NetboxPDNS()
    scheduler = BackgroundScheduler()
    trigger = CronTrigger.from_crontab(api.config.sync_crontab)
    scheduler.add_job(api.full_sync, trigger)
    scheduler.start()
    
    # Application state tracking
    app_state: dict[str, Any] = {
        "initial_sync_complete": False,
        "initial_sync_started": False,
        "initial_sync_error": None,
        "startup_time": time.time()
    }
    
    # Shared zone operation handlers (used by both MQTT and webhooks)
    def handle_zone_create(zone_name: str, source: str = "MQTT") -> None:
        """Handle zone creation"""
        with api._operation_lock_with_logging(f"{source.lower()}_zone_create"):
            nb_zone = api.get_nb_zone_by_name(zone_name)
            if nb_zone:
                api.create_zone(nb_zone)
                api.logger.info(f"{source}: Created zone {zone_name}")
            else:
                api.logger.warning(f"{source}: Zone {zone_name} not found in Netbox")

    def handle_zone_update(zone_name: str, source: str = "MQTT") -> None:
        """Handle zone update/sync"""
        with api._operation_lock_with_logging(f"{source.lower()}_zone_update"):
            nb_zone = api.get_nb_zone_by_name(zone_name)
            pdns_zone = api.get_pdns_zone(zone_name)
            if nb_zone and pdns_zone:
                api.sync_zone(nb_zone, pdns_zone)
                api.logger.info(f"{source}: Synced zone {zone_name}")
            elif nb_zone and not pdns_zone:
                # Zone exists in Netbox but not PowerDNS, create it
                api.create_zone(nb_zone)
                api.logger.info(f"{source}: Created missing zone {zone_name}")
            else:
                api.logger.warning(f"{source}: Zone {zone_name} not found for update")

    def handle_zone_delete(zone_name: str, source: str = "MQTT") -> None:
        """Handle zone deletion"""
        with api._operation_lock_with_logging(f"{source.lower()}_zone_delete"):
            zone_dns_name = dns.name.from_text(zone_name)
            api.delete_zone(zone_dns_name)
            api.logger.info(f"{source}: Deleted zone {zone_name}")

    def run_initial_sync_background() -> None:
        """Run initial sync in background thread"""
        try:
            app_state["initial_sync_started"] = True
            api.logger.info("Starting initial sync in background")
            api.full_sync()
            app_state["initial_sync_complete"] = True
            app_state["initial_sync_error"] = None
            api.logger.info("Initial sync completed successfully")
        except Exception as e:
            error_msg = str(e)
            app_state["initial_sync_error"] = error_msg
            api.logger.error(f"Initial sync failed: {e}", exc_info=True)

    # MQTT zone update handler  
    def handle_mqtt_zone_update(zone_update: MQTTZoneUpdate) -> None:
        """Handle MQTT zone update messages"""
        try:
            api.logger.info(f"MQTT: Received {zone_update.event} event for zone {zone_update.zone}")
            
            if zone_update.event == "create":
                handle_zone_create(zone_update.zone, "MQTT")
            elif zone_update.event == "update":
                handle_zone_update(zone_update.zone, "MQTT")
            elif zone_update.event == "delete":
                handle_zone_delete(zone_update.zone, "MQTT")
            else:
                api.logger.warning(
                    f"MQTT: Unknown event type '{zone_update.event}' for zone {zone_update.zone}"
                )
                
        except Exception as e:
            api.logger.error(
                f"MQTT: Error processing {zone_update.event} event for zone {zone_update.zone}: {e}"
            )
    
    # Initialize MQTT service
    mqtt_service = MQTTService(api.config, handle_mqtt_zone_update)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        # Start MQTT service
        if api.config.mqtt_enabled:
            api.logger.info("Starting MQTT service")
            mqtt_service.start()
            # Wait for MQTT connection (with timeout)
            connected = await mqtt_service.wait_for_connection(timeout=10.0)
            if connected:
                api.logger.info("MQTT service connected successfully")
            else:
                api.logger.warning("MQTT service failed to connect within timeout")
        
        # Start initial sync in background thread (non-blocking)
        sync_thread = threading.Thread(target=run_initial_sync_background, daemon=True)
        sync_thread.start()
        api.logger.info("Initial sync started in background")
        
        yield
        
        # Shutdown services
        scheduler.shutdown()
        if api.config.mqtt_enabled:
            api.logger.info("Stopping MQTT service")
            mqtt_service.stop()

    def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
        """Verify HMAC webhook signature"""
        if not signature or not secret:
            return False
        try:
            # Remove 'sha256=' prefix if present
            if signature.startswith('sha256='):
                signature = signature[7:]
            expected_signature = hmac.new(
                secret.encode(), 
                payload, 
                hashlib.sha256
            ).hexdigest()
            return secrets.compare_digest(expected_signature, signature)
        except Exception:
            return False

    api_key_header = APIKeyHeader(name="x-netbox-pdns-api-key", auto_error=False)

    async def get_api_key(api_key_header: str = Security(api_key_header)) -> str:
        if api_key_header and secrets.compare_digest(api_key_header, api.config.api_key):
            return api_key_header
        else:
            raise HTTPException(
                status_code=HTTP_401_UNAUTHORIZED, detail="Could not validate API key"
            )

    async def verify_webhook_and_parse(request: Request) -> tuple[NetboxWebhook, str]:
        """Verify webhook authentication and parse data in one step"""
        # First verify API key
        api_key_value = request.headers.get("x-netbox-pdns-api-key")
        if not api_key_value or not secrets.compare_digest(api_key_value, api.config.api_key):
            raise HTTPException(
                status_code=HTTP_401_UNAUTHORIZED, detail="Could not validate API key"
            )
        
        # Get raw body for both signature verification and parsing
        body = await request.body()
        
        # If webhook secret is configured, verify HMAC signature
        if api.config.webhook_secret:
            signature = (
                request.headers.get("x-hub-signature-256") or 
                request.headers.get("x-signature-256")
            )
            if not signature:
                raise HTTPException(
                    status_code=HTTP_401_UNAUTHORIZED, 
                    detail="HMAC signature required when webhook secret is configured"
                )
            
            if not verify_webhook_signature(body, signature, api.config.webhook_secret):
                raise HTTPException(
                    status_code=HTTP_401_UNAUTHORIZED, 
                    detail="Invalid webhook signature"
                )
        
        # Parse JSON body into NetboxWebhook model
        try:
            data_dict = json.loads(body.decode('utf-8'))
            webhook_data = NetboxWebhook(**data_dict)
            return webhook_data, api_key_value
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=400, detail="Invalid JSON in request body") from e
        except ValidationError as e:
            raise HTTPException(status_code=400, detail=f"Invalid webhook data: {e}") from e
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error parsing webhook data: {e}") from e

    # Initialize rate limiter
    limiter = Limiter(key_func=get_remote_address)
    
    app = FastAPI(lifespan=lifespan)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

    @app.get("/health")
    @limiter.limit("100/minute")  # Allow generous rate for health checks
    async def health_check(request: Request) -> dict[str, Any]:
        """Basic health check endpoint"""
        return {"status": "Healthy"}
    
    @app.get("/status") 
    @limiter.limit("30/minute")  # Reasonable rate for monitoring
    async def detailed_status(request: Request) -> dict[str, Any]:
        """Detailed application status including sync state"""
        startup_time = app_state["startup_time"]
        uptime = time.time() - (startup_time if isinstance(startup_time, int | float) else 0)
        
        status_info = {
            "status": "Healthy",
            "uptime_seconds": round(uptime, 2),
            "initial_sync": {
                "started": app_state["initial_sync_started"],
                "completed": app_state["initial_sync_complete"],
                "error": app_state["initial_sync_error"]
            },
            "scheduler": {
                "running": scheduler.running,
                "jobs_count": len(scheduler.get_jobs())
            },
            "mqtt": mqtt_service.get_status() if api.config.mqtt_enabled else {"enabled": False}
        }
        
        # Determine overall health
        if app_state["initial_sync_error"]:
            status_info["status"] = "Degraded"
        elif not app_state["initial_sync_complete"] and uptime > 300:  # 5 minutes
            status_info["status"] = "Warning"
            
        return status_info

    @app.get("/mqtt/status")
    @limiter.limit("30/minute")  # Reasonable rate for monitoring
    async def mqtt_status(request: Request) -> dict[str, Any]:
        return mqtt_service.get_status()

    @app.get("/sync")
    @limiter.limit("5/minute")  # Strict limit for manual sync operations
    def sync(request: Request, api_key: str = Depends(get_api_key)) -> dict[str, str]:
        return api.full_sync()

    @app.post("/zones/create")
    @limiter.limit("20/minute")  # Reasonable rate for webhook operations
    async def create_zone_webhook(request: Request) -> None:
        data, api_key = await verify_webhook_and_parse(request)
        api.logger.info(f"Received Netbox create webhook {data}")
        api.create_zone(api.get_nb_zone(data.id))

    @app.delete("/zones/delete")
    @limiter.limit("20/minute")  # Reasonable rate for webhook operations
    async def delete_zone_webhook(request: Request) -> None:
        data, api_key = await verify_webhook_and_parse(request)
        api.logger.info(f"Received Netbox delete webhook {data}")
        api.delete_zone(dns.name.from_text(data.name))

    @app.post("/zones/update")
    @limiter.limit("20/minute")  # Reasonable rate for webhook operations
    async def update_zone_webhook(request: Request) -> None:
        data, api_key = await verify_webhook_and_parse(request)
        api.logger.info(f"Received Netbox update webhook {data}")
        api.sync_zone(api.get_nb_zone(data.id), api.get_pdns_zone(data.name))

    return app
