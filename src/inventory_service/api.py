"""Uvicorn application factory configured through the environment."""

import logging

from fastapi import FastAPI

from computer_inventory.api import create_app as create_inventory_app
from inventory_service.config import Settings


def create_app() -> FastAPI:
    settings = Settings.from_env()
    logging.basicConfig(
        level=settings.log_level, format="%(levelname)s %(name)s %(message)s"
    )
    return create_inventory_app(settings.database_url)
