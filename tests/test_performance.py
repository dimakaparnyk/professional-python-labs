from decimal import Decimal
import pytest
from computer_inventory.performance import (
    CachedInventory, numeric_statistics, numpy_statistics,
    parallel_statistics, synchronized_count, import_files,
)


@pytest.mark.parametrize("values", [[], [1], [1, 2, 3, 4], [100, 200, 500]])
def test_optimized_equivalence(values):
    expected = numeric_statistics(values)
    assert numpy_statistics(values) == expected
    assert parallel_statistics(values, 2) == expected


def test_process_equivalence():
    assert parallel_statistics(list(range(100)), 2, True) == numeric_statistics(list(range(100)))


def test_cache_invalidation(devices):
    cache = CachedInventory()
    for device in devices:
        cache.add(device)
    first = cache.statistics("Dell")
    assert cache.statistics("Dell") == first
    assert cache.cache_info().hits == 1
    cache.change_cost("INV-002", Decimal(1))
    assert cache.statistics("Dell")["total"] != first["total"]
    cache.delete("INV-002")
    assert cache.statistics("Dell")["count"] == 1
    cache.add(devices[1])
    assert cache.statistics("Dell")["count"] == 2
    with pytest.raises(ValueError):
        cache.add(devices[1])
    result = cache.statistics("Dell")
    result["count"] = 999
    assert cache.statistics("Dell")["count"] == 2


def test_lock_and_errors():
    assert synchronized_count(4, 100) == 400
    with pytest.raises(ValueError):
        parallel_statistics([1], 0)
    with pytest.raises(ValueError):
        numpy_statistics([2**62])


def test_parallel_file_import(tmp_path):
    from computer_inventory.streaming import generate_csv
    path = tmp_path / "input.csv"
    generate_csv(path, 10)
    assert import_files([path, path], 2) == 20
