#!/usr/bin/env python3
"""Watchdog: start emergency hotspot after 60s without network."""

from __future__ import annotations

import logging
import sys
import time

from app.network.nm_client import NetworkManagerClient

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

WAIT_SECONDS = 60
POLL_INTERVAL = 5


def main() -> int:
    nm = NetworkManagerClient()
    elapsed = 0
    while elapsed < WAIT_SECONDS:
        if nm.any_connected():
            logger.info("Network connected — hotspot not needed")
            return 0
        time.sleep(POLL_INTERVAL)
        elapsed += POLL_INTERVAL

    if nm.any_connected():
        return 0

    logger.warning("No connection after %ds — starting hotspot", WAIT_SECONDS)
    if nm.create_hotspot():
        logger.info("Hotspot RadioPi-Setup is active")
        return 0
    logger.error("Failed to start hotspot")
    return 1


if __name__ == "__main__":
    sys.exit(main())
