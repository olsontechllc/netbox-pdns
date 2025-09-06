#!/usr/bin/env python3
import argparse

import uvicorn

from netbox_pdns import create_app
from netbox_pdns.models import Settings


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Netbox PowerDNS Connector")
    parser.add_argument(
        "--host", type=str, default="127.0.0.1", help="Host address to bind to (default: 127.0.0.1)"
    )
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on (default: 8000)")
    return parser.parse_args()


def main() -> None:
    """
    Main entry point for the netbox-pdns connector.
    Starts the FastAPI application with uvicorn.
    """
    # Parse command line arguments
    args = parse_args()

    # Load settings
    settings = Settings()

    # Start the FastAPI application
    app = create_app()

    # Configure and run uvicorn server
    uvicorn.run(app, host=args.host, port=args.port, log_level=settings.log_level.lower())
