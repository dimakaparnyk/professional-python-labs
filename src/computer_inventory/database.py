"""Lab 7: SQLite, versioned schema and SQLAlchemy repositories."""

import sqlite3
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Integer,
    String,
    create_engine,
    event,
    func,
    select,
)
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship

from computer_inventory.models import Device

SCHEMA_V1 = """
CREATE TABLE IF NOT EXISTS manufacturers (
 id INTEGER PRIMARY KEY, name TEXT COLLATE NOCASE NOT NULL UNIQUE);
CREATE TABLE IF NOT EXISTS devices (
 id INTEGER PRIMARY KEY,
 inventory_number TEXT COLLATE NOCASE NOT NULL UNIQUE,
 type TEXT NOT NULL, model TEXT NOT NULL,
 value_cents INTEGER NOT NULL CHECK(value_cents >= 0),
 manufacturer_id INTEGER NOT NULL REFERENCES manufacturers(id));
"""


class Base(DeclarativeBase):
    pass


class ManufacturerRow(Base):
    __tablename__ = "manufacturers"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(collation="NOCASE"), unique=True)
    devices: Mapped[list["DeviceRow"]] = relationship(back_populates="manufacturer")


class DeviceRow(Base):
    __tablename__ = "devices"
    __table_args__ = (CheckConstraint("value_cents >= 0"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    inventory_number: Mapped[str] = mapped_column(
        String(collation="NOCASE"), unique=True
    )
    type: Mapped[str] = mapped_column(String)
    model: Mapped[str] = mapped_column(String)
    value_cents: Mapped[int] = mapped_column(Integer)
    manufacturer_id: Mapped[int] = mapped_column(ForeignKey("manufacturers.id"))
    manufacturer: Mapped[ManufacturerRow] = relationship(back_populates="devices")
    location: Mapped[str | None] = mapped_column(String, nullable=True)


def migrate(connection: sqlite3.Connection) -> None:
    """Upgrade v0 -> v1 -> v2 once; user_version records the schema version."""
    version = connection.execute("PRAGMA user_version").fetchone()[0]
    if version > 2:
        raise ValueError("Database schema is newer than this application")
    with connection:
        if version < 1:
            connection.executescript(SCHEMA_V1)
            connection.execute("PRAGMA user_version=1")
        if version < 2:
            connection.execute("ALTER TABLE devices ADD COLUMN location TEXT")
            connection.execute("PRAGMA user_version=2")


def make_engine(url: str) -> Engine:
    engine = create_engine(url, connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection: Any, record: Any) -> None:
        connection.execute("PRAGMA foreign_keys=ON")

    raw = engine.raw_connection()
    try:
        connection = raw.driver_connection
        assert isinstance(connection, sqlite3.Connection)
        migrate(connection)
    finally:
        raw.close()
    return engine


class ManufacturerRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, name: str) -> ManufacturerRow:
        if not name.strip():
            raise ValueError("Manufacturer cannot be empty")
        row = ManufacturerRow(name=name.strip())
        self.session.add(row)
        self.session.flush()
        return row

    def get_or_create(self, name: str) -> ManufacturerRow:
        row = self.session.scalar(
            select(ManufacturerRow).where(
                func.lower(ManufacturerRow.name) == name.strip().lower()
            )
        )
        return row if row is not None else self.add(name)

    def all(self) -> list[ManufacturerRow]:
        return list(
            self.session.scalars(select(ManufacturerRow).order_by(ManufacturerRow.id))
        )


class DeviceRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, device: Device, location: str | None = None) -> DeviceRow:
        manufacturer = ManufacturerRepository(self.session).get_or_create(
            device.manufacturer
        )
        row = DeviceRow(
            inventory_number=device.inventory_number,
            type=device.device_type,
            model=device.model,
            value_cents=int(device.cost * 100),
            manufacturer_id=manufacturer.id,
            location=location,
        )
        self.session.add(row)
        self.session.flush()
        return row

    def get(self, device_id: int) -> DeviceRow | None:
        return self.session.get(DeviceRow, device_id)

    def find(self, inventory_number: str) -> DeviceRow | None:
        return self.session.scalar(
            select(DeviceRow).where(
                DeviceRow.inventory_number == inventory_number.strip()
            )
        )

    def all(self, manufacturer: str | None = None) -> list[DeviceRow]:
        statement = select(DeviceRow).join(DeviceRow.manufacturer)
        if manufacturer:
            statement = statement.where(
                func.lower(ManufacturerRow.name) == manufacturer.strip().lower()
            )
        return list(self.session.scalars(statement.order_by(DeviceRow.id)))

    def change_cost(self, device_id: int, cost: Decimal) -> DeviceRow:
        row = self.get(device_id)
        if row is None:
            raise LookupError(device_id)
        # Reuse the domain validation, including cents and upper bound.
        Device(row.inventory_number, row.type, row.manufacturer.name, row.model, cost)
        row.value_cents = int(cost * 100)
        self.session.flush()
        return row

    def delete(self, device_id: int) -> None:
        row = self.get(device_id)
        if row is None:
            raise LookupError(device_id)
        self.session.delete(row)
        self.session.flush()

    def statistics(self) -> dict[str, Any]:
        count, total = self.session.execute(
            select(
                func.count(DeviceRow.id),
                func.coalesce(func.sum(DeviceRow.value_cents), 0),
            )
        ).one()
        best = self.session.scalar(
            select(DeviceRow)
            .order_by(DeviceRow.value_cents.desc(), DeviceRow.id)
            .limit(1)
        )
        return {
            "count": count,
            "total": f"{Decimal(total) / 100:.2f}",
            "average": str(
                (Decimal(total) / 100 / count).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
            )
            if count
            else "0.00",
            "most_expensive_id": best.id if best else None,
        }


def register_batch(session: Session, devices: list[Device]) -> None:
    """Caller provides a fresh session; all inserts commit or all roll back."""
    with session.begin():
        repository = DeviceRepository(session)
        for device in devices:
            repository.add(device)


def dbapi_search(
    path: Path, inventory_number: str, manufacturer: str = ""
) -> list[tuple[Any, ...]]:
    with sqlite3.connect(path) as connection:
        return connection.execute(
            "SELECT d.inventory_number, m.name, d.value_cents FROM devices d "
            "JOIN manufacturers m ON m.id=d.manufacturer_id "
            "WHERE d.inventory_number = ? COLLATE NOCASE "
            "AND (? = '' OR m.name = ? COLLATE NOCASE)",
            (inventory_number, manufacturer, manufacturer),
        ).fetchall()
