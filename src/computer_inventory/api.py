"""Lab 8: persistent REST API; use create_app for isolated tests."""
from collections.abc import Iterator
from contextlib import asynccontextmanager
from decimal import Decimal
import os
from typing import Annotated, Any

from fastapi import Depends, FastAPI, HTTPException, Query, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from computer_inventory.database import (
    DeviceRepository, DeviceRow, ManufacturerRepository, ManufacturerRow, make_engine,
)
from computer_inventory.models import Device


class DeviceCreate(BaseModel):
    inventory_number: str = Field(min_length=1, max_length=100)
    type: str = Field(min_length=1, max_length=100)
    manufacturer: str = Field(min_length=1, max_length=100)
    model: str = Field(min_length=1, max_length=200)
    value: Decimal = Field(ge=0, le=1000000000000, decimal_places=2)
    location: str | None = Field(default=None, max_length=200)

    @field_validator("inventory_number", "type", "manufacturer", "model")
    @classmethod
    def nonempty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Field cannot be blank")
        return value.strip()


class DevicePatch(BaseModel):
    value: Decimal = Field(ge=0, le=1000000000000, decimal_places=2)


class DeviceView(BaseModel):
    id: int
    inventory_number: str
    type: str
    manufacturer: str
    manufacturer_id: int
    model: str
    value: str
    location: str | None


class ManufacturerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)

    @field_validator("name")
    @classmethod
    def nonempty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Manufacturer cannot be blank")
        return value.strip()


class ManufacturerView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str


def view(row: DeviceRow) -> DeviceView:
    return DeviceView(id=row.id, inventory_number=row.inventory_number,
                      type=row.type, manufacturer=row.manufacturer.name,
                      manufacturer_id=row.manufacturer_id, model=row.model,
                      value=f"{Decimal(row.value_cents)/100:.2f}", location=row.location)


def create_app(database_url: str | None = None) -> FastAPI:
    url = database_url or os.getenv("DATABASE_URL", "sqlite:///inventory.db")
    engine = make_engine(url)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        yield
        engine.dispose()

    app = FastAPI(title="Inventory Service", version="1.0.0", lifespan=lifespan)
    app.state.engine = engine

    def session_dependency() -> Iterator[Session]:
        with Session(engine) as session:
            yield session

    Database = Annotated[Session, Depends(session_dependency)]

    @app.get("/health")
    def health(database: Database) -> dict[str, str]:
        database.execute(select(1))
        return {"status": "ok"}

    @app.get("/statistics")
    @app.get("/devices/statistics")
    def statistics(database: Database) -> dict[str, Any]:
        return DeviceRepository(database).statistics()

    @app.get("/devices", response_model=list[DeviceView])
    def list_devices(database: Database, manufacturer: str | None = None,
                     inventory_number: str | None = None,
                     offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100)) -> list[DeviceView]:
        repository = DeviceRepository(database)
        rows = repository.all(manufacturer)
        if inventory_number:
            rows = [row for row in rows if row.inventory_number.casefold() == inventory_number.strip().casefold()]
        return [view(row) for row in rows[offset:offset + limit]]

    @app.post("/devices", status_code=201, response_model=DeviceView)
    def add_device(payload: DeviceCreate, database: Database) -> DeviceView:
        device = Device(payload.inventory_number, payload.type, payload.manufacturer,
                        payload.model, payload.value)
        try:
            row = DeviceRepository(database).add(device, payload.location)
            result = view(row)
            database.commit()
            return result
        except IntegrityError as error:
            database.rollback()
            raise HTTPException(409, "Inventory number already exists") from error

    @app.get("/devices/{device_id}", response_model=DeviceView)
    def get_device(device_id: int, database: Database) -> DeviceView:
        row = DeviceRepository(database).get(device_id)
        if row is None:
            raise HTTPException(404, "Device not found")
        return view(row)

    @app.patch("/devices/{device_id}", response_model=DeviceView)
    def update_device(device_id: int, payload: DevicePatch, database: Database) -> DeviceView:
        try:
            row = DeviceRepository(database).change_cost(device_id, payload.value)
            result = view(row)
            database.commit()
            return result
        except LookupError as error:
            raise HTTPException(404, "Device not found") from error

    @app.delete("/devices/{device_id}", status_code=204)
    def delete_device(device_id: int, database: Database) -> Response:
        try:
            DeviceRepository(database).delete(device_id)
            database.commit()
            return Response(status_code=204)
        except LookupError as error:
            raise HTTPException(404, "Device not found") from error

    @app.get("/manufacturers", response_model=list[ManufacturerView])
    def manufacturers(database: Database) -> list[ManufacturerRow]:
        return ManufacturerRepository(database).all()

    @app.post("/manufacturers", status_code=201, response_model=ManufacturerView)
    def add_manufacturer(payload: ManufacturerCreate, database: Database) -> ManufacturerRow:
        try:
            row = ManufacturerRepository(database).add(payload.name)
            database.commit()
            database.refresh(row)
            return row
        except IntegrityError as error:
            database.rollback()
            raise HTTPException(409, "Manufacturer already exists") from error

    @app.get("/manufacturers/{manufacturer_id}/devices", response_model=list[DeviceView])
    def manufacturer_devices(manufacturer_id: int, database: Database) -> list[DeviceView]:
        row = database.get(ManufacturerRow, manufacturer_id)
        if row is None:
            raise HTTPException(404, "Manufacturer not found")
        return [view(device) for device in DeviceRepository(database).all(row.name)]

    return app
