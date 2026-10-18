import sys
from decimal import Decimal

import pytest

from computer_inventory.main import main


@pytest.mark.parametrize(
    "flag,expected",
    [("--demo", "92700.00"), ("--analytics", "92700.00"), ("--oop-demo", "40000")],
)
def test_cli_modes(monkeypatch, capsys, flag, expected):
    monkeypatch.setattr(sys, "argv", ["inventory-service", flag])
    main()
    assert expected in capsys.readouterr().out


def test_stream_cli(monkeypatch, tmp_path, capsys):
    from computer_inventory.streaming import generate_csv

    path = tmp_path / "input.csv"
    generate_csv(path, 3)
    monkeypatch.setattr(sys, "argv", ["inventory-service", "--stream", str(path)])
    main()
    assert "3" in capsys.readouterr().out


def test_cli_import_failure(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys, "argv", ["inventory-service", "--import-config", "missing.yaml"]
    )
    with pytest.raises(SystemExit) as error:
        main()
    assert error.value.code == 1
    assert "Помилка імпорту" in capsys.readouterr().out


def test_rounding_consistency(engine, device_factory):
    from sqlalchemy.orm import Session

    from computer_inventory.database import DeviceRepository
    from computer_inventory.streaming import aggregate

    items = [device_factory("A", "0.00"), device_factory("B", "0.01")]
    assert aggregate(iter(items)).average == Decimal("0.01")
    with Session(engine) as session:
        repo = DeviceRepository(session)
        for item in items:
            repo.add(item)
        assert repo.statistics()["average"] == "0.01"
