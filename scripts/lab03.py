"""Eager/lazy measurements; never invent benchmark results."""
import argparse
from contextlib import closing
from dataclasses import asdict
import json
from pathlib import Path
from time import perf_counter
import tracemalloc

from computer_inventory.streaming import aggregate, generate_csv, pipeline, batches


def measure(path: Path, eager: bool) -> dict[str, float]:
    tracemalloc.start()
    start = perf_counter()
    if eager:
        items = list(pipeline(path))
        first = perf_counter() - start
        result = aggregate(items)
    else:
        with closing(pipeline(path)) as items:
            next(items, None)
            first = perf_counter() - start
        result = aggregate(pipeline(path))
    elapsed = perf_counter() - start
    peak = tracemalloc.get_traced_memory()[1] / 1024**2
    tracemalloc.stop()
    return {"elapsed_s": elapsed, "peak_MiB": peak,
            "first_s": first, "count": result.count, "total": str(result.total)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    results = []
    for size in (10000, 100000, 500000):
        path = args.output / f"inventory-{size}.csv"
        generate_csv(path, size)
        eager = measure(path, True)
        lazy = measure(path, False)
        assert eager["total"] == lazy["total"]
        assert eager["count"] == lazy["count"] == size
        results.append({"records": size, "eager": eager, "lazy": lazy})
        print(json.dumps(results[-1]), flush=True)
    early_path = args.output / "inventory-1000000.csv"
    generate_csv(early_path, 1000000)
    start = perf_counter()
    with closing(pipeline(early_path)) as stream:
        first = next(d for d in stream if d.manufacturer == "Dell")
    lazy_time = perf_counter() - start
    start = perf_counter()
    matches = [d for d in pipeline(early_path) if d.manufacturer == "Dell"]
    eager_time = perf_counter() - start
    assert first == matches[0]
    early = {"records": 1000000, "lazy_s": lazy_time, "eager_s": eager_time,
             "first_id": first.inventory_number}
    print(json.dumps({"early_termination": early}), flush=True)
    (args.output / "results03.json").write_text(
        json.dumps({"measurements": results, "early": early}, indent=2), encoding="utf-8")
    assert sum(len(b) for b in batches(pipeline(args.output / "inventory-10000.csv"), 333)) == 10000


if __name__ == "__main__":
    main()
