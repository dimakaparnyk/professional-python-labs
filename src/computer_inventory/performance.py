"""Lab 9: comparable implementations and invalidated statistics cache."""

from collections.abc import Iterable
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from dataclasses import replace
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from threading import Lock, Thread
from typing import Any

import numpy as np

from computer_inventory.analytics import summarize
from computer_inventory.models import Device
from computer_inventory.streaming import aggregate, pipeline


def numeric_statistics(values: list[int]) -> tuple[int, int, int, int]:
    if not values:
        return 0, 0, 0, 0
    return len(values), sum(values), sum(v * v for v in values), max(values)


def combine(parts: Iterable[tuple[int, int, int, int]]) -> tuple[int, int, int, int]:
    rows = list(parts)
    return (
        sum(p[0] for p in rows),
        sum(p[1] for p in rows),
        sum(p[2] for p in rows),
        max((p[3] for p in rows), default=0),
    )


def parallel_statistics(
    values: list[int], workers: int, processes: bool = False
) -> tuple[int, int, int, int]:
    if workers < 1:
        raise ValueError("Workers must be positive")
    size = max(1, (len(values) + workers - 1) // workers)
    chunks = [values[i : i + size] for i in range(0, len(values), size)]
    executor = ProcessPoolExecutor if processes else ThreadPoolExecutor
    with executor(max_workers=workers) as pool:
        return combine(pool.map(numeric_statistics, chunks))


def numpy_statistics(values: list[int]) -> tuple[int, int, int, int]:
    if not values:
        return 0, 0, 0, 0
    # Check bounds before using int64 so vectorization cannot silently overflow.
    bound = max(abs(min(values)), abs(max(values)))
    if bound * bound * len(values) > np.iinfo(np.int64).max:
        raise ValueError("Input exceeds safe int64 range")
    array = np.asarray(values, dtype=np.int64)
    return (
        len(values),
        int(array.sum()),
        int(np.square(array).sum()),
        int(array.max(axis=0)),
    )


def import_files(paths: list[Path], workers: int = 4) -> int:
    def count_file(path: Path) -> int:
        return aggregate(pipeline(path)).count

    with ThreadPoolExecutor(max_workers=workers) as pool:
        return sum(pool.map(count_file, paths))


def synchronized_count(workers: int = 4, increments: int = 1000) -> int:
    lock = Lock()
    total = 0

    def worker() -> None:
        nonlocal total
        for _ in range(increments):
            with lock:
                total += 1

    threads = [Thread(target=worker) for _ in range(workers)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    return total


class CachedInventory:
    def __init__(self) -> None:
        self._items: dict[str, Device] = {}
        self._cached = lru_cache(maxsize=128)(self._calculate)

    def _calculate(self, manufacturer: str, device_type: str) -> dict[str, Any]:
        return summarize(
            d
            for d in self._items.values()
            if (not manufacturer or d.manufacturer.casefold() == manufacturer)
            and (not device_type or d.device_type.casefold() == device_type)
        )

    def add(self, device: Device) -> None:
        key = device.inventory_number.casefold()
        if key in self._items:
            raise ValueError("Duplicate inventory number")
        self._items[key] = device
        self._cached.cache_clear()

    def delete(self, inventory_number: str) -> None:
        del self._items[inventory_number.casefold()]
        self._cached.cache_clear()

    def change_cost(self, inventory_number: str, cost: Decimal) -> None:
        key = inventory_number.casefold()
        self._items[key] = replace(self._items[key], cost=cost)
        self._cached.cache_clear()

    def statistics(
        self, manufacturer: str = "", device_type: str = ""
    ) -> dict[str, Any]:
        result = self._cached(
            manufacturer.strip().casefold(), device_type.strip().casefold()
        )
        # Do not let callers mutate the cached dictionary or nested values.
        import copy

        return copy.deepcopy(result)

    def cache_info(self) -> Any:
        return self._cached.cache_info()
