import asyncio
from dataclasses import replace
from decimal import Decimal
from io import StringIO
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest

from computer_inventory.analytics import (
    build_index, count_types, group_by, history, make_cost_filter, merge,
    select, summarize, unique_manufacturers,
)
from computer_inventory.domain import (
    Computer, Printer, InventoryRegistry, MaintenanceService,
    StandardMaintenance, Money, Manufacturer, from_payload, load_remote,
)
from computer_inventory.fileio import (
    ConfigurationError, FileConfig, ImportExportError, ImportStats,
    RecordValidationError, atomic_text, export_json, import_csv,
    load_config, run_import, validate_record,
)
from computer_inventory.models import Device
from computer_inventory.streaming import (
    InventoryNumbers, aggregate, batches, clean_rows, generate_csv,
    multi_file, pipeline, filter_devices, transform,
)


@pytest.mark.parametrize("value", ["-0.01", "NaN", "Infinity", "1.001", "1000000000001"])
def test_invalid_cost(value, device_factory):
    with pytest.raises(ValueError):
        device_factory(cost=value)


@pytest.mark.parametrize("value", ["0", "0.01", "1000000000000"])
def test_valid_cost_boundary(value, device_factory):
    assert device_factory(cost=value).cost == Decimal(value)


def test_money_addition():
    assert (Money(Decimal("0.1")) + Money(Decimal("0.2"))).amount == Decimal("0.3")
    assert str(Money(Decimal(10))) == "10.00 UAH"


def test_invalid_money():
    with pytest.raises(ValueError):
        Money(Decimal(-1))
    with pytest.raises(ValueError):
        Money(Decimal(1), "USD")


def test_immutable(device_factory):
    from dataclasses import FrozenInstanceError
    with pytest.raises(FrozenInstanceError):
        device_factory().cost = Decimal(4)


def test_computer_printer(device_factory):
    base = device_factory()
    fields = (base.inventory_number, base.device_type, base.manufacturer, base.model, base.cost)
    assert Computer(*fields, 16).ram_gb == 16
    assert Printer(*fields).color is False
    with pytest.raises(ValueError):
        Computer(*fields, 0)


def test_manufacturer():
    with pytest.raises(ValueError):
        Manufacturer(" ")


def test_repository_and_registry(repository, device_factory):
    registry = InventoryRegistry(repository)
    device = device_factory()
    registry.register(device)
    assert len(registry) == 1 and "X" in registry
    assert list(registry) == [device] and registry["X"] == device
    assert registry.best() == device
    assert registry.total.amount == registry.average.amount == Decimal(100)
    assert registry.by_manufacturer("dell") == [device]
    assert len(registry.manufacturers) == 1
    with pytest.raises(ValueError):
        registry.register(device)
    with pytest.raises(KeyError):
        registry["missing"]


def test_empty_registry(repository):
    registry = InventoryRegistry(repository)
    assert not registry and registry.best() is None
    assert registry.total.amount == Decimal(0)


def test_maintenance_mock(device_factory):
    repository = Mock()
    policy = Mock(spec=StandardMaintenance)
    repository.get.return_value = device_factory()
    policy.interval_days.return_value = 180
    service = MaintenanceService(repository, policy)
    assert service.schedule("X") == 180
    repository.get.assert_called_once_with("X")
    policy.interval_days.assert_called_once_with(repository.get.return_value)
    repository.get.side_effect = RuntimeError("database unavailable")
    policy.reset_mock()
    with pytest.raises(RuntimeError):
        service.schedule("X")
    policy.interval_days.assert_not_called()


def test_missing_maintenance():
    repository = Mock()
    repository.get.return_value = None
    policy = Mock()
    with pytest.raises(LookupError):
        MaintenanceService(repository, policy).schedule("X")
    policy.interval_days.assert_not_called()


def test_async_provider(devices):
    provider = Mock()
    provider.fetch = AsyncMock(return_value=devices)
    assert asyncio.run(load_remote(provider)) == devices
    provider.fetch.assert_awaited_once()
    provider.fetch.side_effect = TimeoutError("timeout")
    with pytest.raises(TimeoutError):
        asyncio.run(load_remote(provider))


def test_payload():
    device = from_payload({"inventory_number": "A", "device_type": "Computer",
                           "manufacturer": "Dell", "model": "X", "cost": "10.10"})
    assert float(device.cost) == pytest.approx(10.10)


def test_analytics(devices):
    assert unique_manufacturers(devices) == {"Dell", "HP", "Lenovo"}
    assert len(group_by(devices)["Dell"]) == 2
    assert count_types(devices)["Ноутбук"] == 2
    assert len(merge(devices[:1], devices[1:])) == 4
    assert len(select(devices, manufacturer="Dell")) == 2
    assert len(list(filter(make_cost_filter(Decimal(30000)), devices))) == 2
    assert summarize(devices)["total"] == "92700.00"
    assert history[-1][0] == "summary"
    assert build_index(devices)["inv-001"] == devices[0]


def test_analytics_errors(devices):
    with pytest.raises(ValueError):
        build_index([devices[0], devices[0]])
    with pytest.raises(ValueError):
        select(devices, missing="X")
    with pytest.raises(ValueError):
        group_by(devices, "model")
    assert summarize([])["most_expensive"] is None


def test_streaming_iterator():
    numbers = InventoryNumbers()
    assert iter(numbers) is numbers
    assert next(numbers) == "INV-0000001"
    assert next(numbers) == "INV-0000002"


def test_streaming_pipeline(tmp_path):
    path = tmp_path / "input.csv"
    generate_csv(path, 100)
    result = aggregate(pipeline(path))
    assert result.count == 100 and result.total > 0
    assert result.average > 0 and sum(result.types.values()) == 100
    assert len(list(pipeline(path, "Dell", "Computer"))) == 17
    assert sum(len(batch) for batch in batches(pipeline(path), 13)) == 100
    assert len(list(multi_file([path, path]))) == 200
    assert aggregate([]).average == Decimal(0)
    with pytest.raises(ValueError):
        list(batches([], 0))


def test_clean_malformed():
    with pytest.raises(ValueError):
        list(clean_rows([{"cost": None}]))


def test_configuration(tmp_path, csv_path, monkeypatch):
    config = tmp_path / "config.yaml"
    config.write_text(f"input: {csv_path.name}\noutput: out.json\nallowed_manufacturers: [Dell, HP]\nskip_invalid: true\n", encoding="utf-8")
    assert load_config(config).skip_invalid is True
    result = run_import(config)
    assert result.exported == 2
    assert (tmp_path / "out.json").exists()


@pytest.mark.parametrize("body", ["[broken", "[]", "input: x", "input: x\noutput: y\nskip_invalid: yesplease", "input: missing.csv\noutput: y", "input: a\noutput: b\nallowed_types: Computer"])
def test_invalid_configuration(tmp_path, body):
    path = tmp_path / "bad.yaml"
    path.write_text(body, encoding="utf-8")
    with pytest.raises(ConfigurationError) as error:
        load_config(path)
    assert error.value.__cause__ is not None


def test_missing_configuration(tmp_path):
    with pytest.raises(ConfigurationError):
        load_config(tmp_path / "missing.yaml")


def test_import_export_integration(csv_path, tmp_path):
    import json
    config = FileConfig(csv_path, tmp_path / "out.json")
    stats = ImportStats()
    export_json(import_csv(config, stats), config.output, stats)
    data = json.loads(config.output.read_text(encoding="utf-8"))
    assert len(data) == stats.valid == stats.exported == 2
    assert data[0]["value"] == "100.50"


def test_tolerant_integration(csv_path, tmp_path):
    with csv_path.open("a", encoding="utf-8") as stream:
        stream.write("C,Computer,Dell,X,-1\n")
        stream.write("A,Computer,Dell,X,100\n")
    config = FileConfig(csv_path, tmp_path / "out.json", skip_invalid=True)
    stats = ImportStats()
    assert len(list(import_csv(config, stats))) == 2
    assert (stats.processed, stats.valid, stats.invalid) == (4, 2, 2)


def test_atomic_failure_integration(csv_path, tmp_path):
    with csv_path.open("a", encoding="utf-8") as stream:
        stream.write("C,Computer,Dell,X,wrong\n")
    config = FileConfig(csv_path, tmp_path / "out.json")
    config.output.write_text("original", encoding="utf-8")
    with pytest.raises(RecordValidationError) as error:
        export_json(import_csv(config, ImportStats()), config.output, ImportStats())
    assert error.value.__cause__ is not None
    assert config.output.read_text(encoding="utf-8") == "original"
    assert not list(tmp_path.glob("*.tmp"))


def test_export_os_failure(tmp_path, monkeypatch):
    from computer_inventory import fileio
    def fail(*args, **kwargs):
        raise OSError("simulated disk failure")
    monkeypatch.setattr(fileio.os, "replace", fail)
    with pytest.raises(ImportExportError):
        export_json(iter([]), tmp_path / "out.json", ImportStats())
    assert not list(tmp_path.glob("*.tmp"))


def test_input_os_failure(tmp_path):
    with pytest.raises(ImportExportError):
        list(import_csv(FileConfig(tmp_path / "missing.csv", tmp_path / "out"), ImportStats()))


def test_missing_header(tmp_path):
    path = tmp_path / "bad.csv"
    path.write_text("name,value\nX,10\n", encoding="utf-8")
    with pytest.raises(ImportExportError):
        list(import_csv(FileConfig(path, tmp_path / "out"), ImportStats()))


@pytest.mark.parametrize("field,value", [("type", "Bad"), ("manufacturer", "Bad"), ("status", "Bad"), ("inventory_number", " ")])
def test_record_policy(field, value, tmp_path):
    row = {"inventory_number": "A", "type": "Computer", "manufacturer": "Dell",
           "model": "X", "value": "100", "status": "active"}
    row[field] = value
    config = FileConfig(tmp_path / "in", tmp_path / "out", ("Computer",), ("Dell",))
    with pytest.raises(RecordValidationError):
        validate_record(row, config)
