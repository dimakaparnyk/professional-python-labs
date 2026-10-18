import json
import tracemalloc
from decimal import Decimal
from pathlib import Path
from time import perf_counter

from computer_inventory.fileio import FileConfig, ImportStats, import_csv

out = []
for size in (10000, 100000, 500000):
    path = Path("work/datasets") / f"inventory-{size}.csv"
    for eager in (True, False):
        stats = ImportStats()
        cfg = FileConfig(path, Path("work/unused.json"))
        tracemalloc.start()
        start = perf_counter()
        items = list(import_csv(cfg, stats)) if eager else import_csv(cfg, stats)
        total = sum((d.cost for d in items), Decimal(0))
        elapsed = perf_counter() - start
        peak = tracemalloc.get_traced_memory()[1] / 1024**2
        tracemalloc.stop()
        row = {
            "records": size,
            "mode": "eager" if eager else "streaming",
            "seconds": elapsed,
            "peak_MiB": peak,
            "valid": stats.valid,
            "total": str(total),
        }
        out.append(row)
        print(json.dumps(row), flush=True)
Path("work/io-experiment/stream-results.json").write_text(
    json.dumps(out, indent=2), encoding="utf-8"
)
