from decimal import Decimal

import pytest

from computer_inventory.domain import InMemoryRepository
from computer_inventory.main import create_demo_devices
from computer_inventory.models import Device


@pytest.fixture
def devices():
    return create_demo_devices()


@pytest.fixture
def repository():
    return InMemoryRepository[Device]()


@pytest.fixture
def csv_path(tmp_path):
    path = tmp_path / "inventory.csv"
    path.write_text(
        "inventory_number,type,manufacturer,model,value\nA,Computer,Dell,Latitude,100.50\nB,Printer,HP,LaserJet,200\n",
        encoding="utf-8",
    )
    yield path
    assert path.exists()


@pytest.fixture
def device_factory():
    def factory(number="X", cost="100"):
        return Device(number, "Computer", "Dell", "Latitude", Decimal(cost))

    return factory


@pytest.fixture
def engine(tmp_path):
    from computer_inventory.database import make_engine

    result = make_engine("sqlite:///" + (tmp_path / "test.db").as_posix())
    yield result
    result.dispose()
