"""Lab 3: lazy CSV pipeline with constant-size aggregation."""

import csv
from collections import Counter
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from itertools import chain, count, islice
from pathlib import Path

from computer_inventory.models import Device


class InventoryNumbers(Iterator[str]):
    def __init__(self, prefix: str = "INV") -> None:
        self.prefix = prefix
        self._numbers = count(1)

    def __iter__(self) -> "InventoryNumbers":
        return self

    def __next__(self) -> str:
        return f"{self.prefix}-{next(self._numbers):07d}"


def read_rows(path: Path) -> Iterator[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        yield from csv.DictReader(stream)


def clean_rows(rows: Iterable[dict[str, str]]) -> Iterator[dict[str, str]]:
    for row in rows:
        if None in row or any(value is None for value in row.values()):
            raise ValueError("Malformed CSV row")
        yield {key.strip(): value.strip() for key, value in row.items()}


def parse_rows(rows: Iterable[dict[str, str]]) -> Iterator[Device]:
    for row in rows:
        yield Device(
            row["inventory_number"],
            row["type"],
            row["manufacturer"],
            row["model"],
            Decimal(row["cost"]),
        )


def filter_devices(
    devices: Iterable[Device], manufacturer: str = "", device_type: str = ""
) -> Iterator[Device]:
    for device in devices:
        if manufacturer and device.manufacturer.casefold() != manufacturer.casefold():
            continue
        if device_type and device.device_type.casefold() != device_type.casefold():
            continue
        yield device


def transform(devices: Iterable[Device]) -> Iterator[Device]:
    """Normalize outer whitespace through the validated immutable model."""
    for device in devices:
        yield Device(
            device.inventory_number,
            device.device_type,
            device.manufacturer,
            device.model,
            device.cost,
        )


def pipeline(
    path: Path, manufacturer: str = "", device_type: str = ""
) -> Iterator[Device]:
    yield from transform(
        filter_devices(
            parse_rows(clean_rows(read_rows(path))), manufacturer, device_type
        )
    )


def multi_file(paths: Iterable[Path]) -> Iterator[Device]:
    yield from chain.from_iterable(pipeline(path) for path in paths)


def batches(items: Iterable[Device], size: int = 1000) -> Iterator[tuple[Device, ...]]:
    if size < 1:
        raise ValueError("Batch size must be positive")
    iterator = iter(items)
    while batch := tuple(islice(iterator, size)):
        yield batch


@dataclass
class StreamSummary:
    count: int = 0
    total: Decimal = Decimal("0.00")
    most_expensive: Device | None = None
    types: Counter[str] = field(default_factory=Counter)
    manufacturers: Counter[str] = field(default_factory=Counter)

    @property
    def average(self) -> Decimal:
        return (
            (self.total / self.count).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            if self.count
            else Decimal("0.00")
        )


def aggregate(devices: Iterable[Device]) -> StreamSummary:
    result = StreamSummary()
    for device in devices:
        result.count += 1
        result.total += device.cost
        result.types[device.device_type] += 1
        result.manufacturers[device.manufacturer] += 1
        if result.most_expensive is None or device.cost > result.most_expensive.cost:
            result.most_expensive = device
    return result


def generate_csv(path: Path, size: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    numbers = InventoryNumbers()
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["inventory_number", "type", "manufacturer", "model", "cost"])
        for i in range(size):
            writer.writerow(
                [
                    next(numbers),
                    ("Computer", "Printer")[i % 2],
                    ("Dell", "HP", "Lenovo")[i % 3],
                    f"Model-{i % 20}",
                    f"{1000 + i % 90000}.25",
                ]
            )
