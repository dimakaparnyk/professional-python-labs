"""Five repeated measurements per method, size and worker count."""

import cProfile
import csv
import io
import json
import os
import platform
import pstats
import shutil
import sys
import tracemalloc
from decimal import Decimal
from pathlib import Path
from statistics import mean
from time import perf_counter

from computer_inventory.analytics import group_by, summarize
from computer_inventory.models import Device
from computer_inventory.performance import (
    CachedInventory,
    import_files,
    numeric_statistics,
    numpy_statistics,
    parallel_statistics,
    synchronized_count,
)
from computer_inventory.services import filter_by_manufacturer, search_devices


def main() -> None:
    output = Path(sys.argv[1]).resolve()
    output.mkdir(parents=True, exist_ok=True)
    rows = []
    for size in (10000, 100000, 1000000):
        values = [1000 + i % 90000 for i in range(size)]
        expected = numeric_statistics(values)
        methods = [
            ("Sequential", 1, lambda: numeric_statistics(values)),
            ("NumPy", 1, lambda: numpy_statistics(values)),
        ]
        for workers in (1, 2, 4, 8):
            methods.append(
                ("Threads", workers, lambda w=workers: parallel_statistics(values, w))
            )
            methods.append(
                (
                    "Processes",
                    workers,
                    lambda w=workers: parallel_statistics(values, w, True),
                )
            )
        baseline = 0.0
        for method, workers, call in methods:
            times = []
            for _ in range(5):
                start = perf_counter()
                result = call()
                times.append(perf_counter() - start)
                assert result == expected
            if method == "Sequential":
                baseline = mean(times)
            row = {
                "records": size,
                "method": method,
                "workers": workers,
                **{f"run_{i + 1}": t for i, t in enumerate(times)},
                "mean_s": mean(times),
                "speedup": baseline / mean(times),
            }
            rows.append(row)
            print(json.dumps(row), flush=True)
        tracemalloc.start()
        numeric_statistics(values)
        peak_python = tracemalloc.get_traced_memory()[1]
        tracemalloc.stop()
        tracemalloc.start()
        numpy_statistics(values)
        peak_numpy = tracemalloc.get_traced_memory()[1]
        tracemalloc.stop()
        print(
            json.dumps(
                {
                    "records": size,
                    "python_peak_bytes": peak_python,
                    "numpy_peak_bytes": peak_numpy,
                }
            ),
            flush=True,
        )
    with (output / "benchmark.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    items = [
        Device(
            str(i),
            "Computer",
            ("Dell", "HP")[i % 2],
            "Model",
            Decimal(1000 + i % 90000),
        )
        for i in range(100000)
    ]

    def workload():
        search_devices(items, "99999")
        filter_by_manufacturer(items, "Dell")
        group_by(items, "device_type")
        summarize(items)

    profile = cProfile.Profile()
    profile.runcall(workload)
    buffer = io.StringIO()
    pstats.Stats(profile, stream=buffer).sort_stats("cumulative").print_stats(20)
    (output / "profile.txt").write_text(buffer.getvalue(), encoding="utf-8")
    cached = CachedInventory()
    for item in items:
        cached.add(item)
    start = perf_counter()
    cold = cached.statistics("Dell")
    cold_s = perf_counter() - start
    start = perf_counter()
    warm = cached.statistics("Dell")
    warm_s = perf_counter() - start
    assert cold == warm
    cached.change_cost("0", Decimal(1))
    assert cached.statistics("Dell")["total"] != cold["total"]
    cached.delete("0")
    cached.add(Device("new", "Computer", "Dell", "Model", Decimal(10)))
    print(
        json.dumps(
            {
                "cache_cold_s": cold_s,
                "cache_warm_s": warm_s,
                "cache_speedup": cold_s / warm_s,
                "cache_info": str(cached.cache_info()),
                "synchronized_count": synchronized_count(),
                "python": platform.python_version(),
                "cpu_count": os.cpu_count(),
            }
        ),
        flush=True,
    )
    paths = sorted((output.parent / "datasets").glob("inventory-10000.csv"))
    if paths:
        start = perf_counter()
        copies = [output / f"import-{i}.csv" for i in range(4)]
        for destination in copies:
            shutil.copyfile(paths[0], destination)
        count = import_files(copies, 4)
        print(
            json.dumps(
                {"threaded_import_count": count, "seconds": perf_counter() - start}
            ),
            flush=True,
        )
    (output / "results09.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
