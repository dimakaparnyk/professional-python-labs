from decimal import Decimal
from pathlib import Path
import sqlite3
import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from computer_inventory.database import (
    make_engine, migrate, ManufacturerRepository, DeviceRepository,
    DeviceRow, register_batch, dbapi_search,
)


@pytest.fixture
def engine(tmp_path):
    engine = make_engine("sqlite:///" + (tmp_path / "test.db").as_posix())
    yield engine
    engine.dispose()


def test_crud_filter_aggregates(engine, devices):
    with Session(engine) as session, session.begin():
        repo = DeviceRepository(session)
        rows = [repo.add(d) for d in devices]
        assert repo.get(rows[0].id).model == devices[0].model
        assert repo.find("inv-001").id == rows[0].id
        assert len(repo.all("Dell")) == 2
        assert repo.statistics()["total"] == "92700.00"
        assert repo.statistics()["average"] == "23175.00"
        repo.change_cost(rows[0].id, Decimal("10000"))
        assert repo.get(rows[0].id).value_cents == 1000000
        repo.delete(rows[-1].id)
        assert len(repo.all()) == 3
        assert len(ManufacturerRepository(session).all()) == 3


def test_unique_batch_rollback(engine, devices):
    with Session(engine) as session:
        with pytest.raises(IntegrityError):
            register_batch(session, [devices[0], devices[0]])
    with Session(engine) as session:
        assert DeviceRepository(session).all() == []
        assert ManufacturerRepository(session).all() == []


def test_persistent_commit_dbapi(engine, devices):
    with Session(engine) as session:
        register_batch(session, devices)
    path = Path(engine.url.database)
    assert dbapi_search(path, "INV-002", "Dell")[0][2] == 850000
    assert dbapi_search(path, "x' OR 1=1 --") == []


def test_migration_and_foreign_key(engine):
    with engine.connect() as connection:
        assert connection.exec_driver_sql("PRAGMA user_version").scalar() == 2
        assert "location" in [row[1] for row in connection.exec_driver_sql("PRAGMA table_info(devices)")]
        assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar() == 1
    with Session(engine) as session:
        with pytest.raises(IntegrityError):
            session.execute(text("INSERT INTO devices(inventory_number,type,model,value_cents,manufacturer_id) VALUES ('A','PC','M',0,999)"))
        session.rollback()


def test_empty_and_missing(engine):
    with Session(engine) as session:
        repo = DeviceRepository(session)
        assert repo.statistics() == {"count": 0, "total": "0.00", "average": "0.00", "most_expensive_id": None}
        with pytest.raises(LookupError):
            repo.delete(999)
        with pytest.raises(LookupError):
            repo.change_cost(999, Decimal(1))
