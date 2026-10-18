"""Profile the same exact-number lookup before and after indexing."""

import cProfile
import io
import json
import pstats
import sys
from decimal import Decimal
from pathlib import Path
from time import perf_counter

from computer_inventory.analytics import build_index
from computer_inventory.models import Device


def main() -> None:
    output = Path(sys.argv[1])
    output.mkdir(parents=True, exist_ok=True)
    items = [
        Device(str(i), "Computer", "Dell", "Model", Decimal(100)) for i in range(100000)
    ]
    queries = [str(99999 - i) for i in range(200)]

    def linear():
        return [
            next((d for d in items if d.inventory_number.casefold() == query), None)
            for query in queries
        ]

    started = perf_counter()
    index = build_index(items)
    build_s = perf_counter() - started

    def indexed():
        return [index.get(query) for query in queries]

    rows = []
    expected = linear()
    for name, call in [("linear", linear), ("indexed", indexed)]:
        started = perf_counter()
        result = call()
        elapsed = perf_counter() - started
        assert result == expected
        profile = cProfile.Profile()
        profile.runcall(call)
        buffer = io.StringIO()
        pstats.Stats(profile, stream=buffer).sort_stats("cumulative").print_stats(10)
        (output / (name + "-profile.txt")).write_text(
            buffer.getvalue(), encoding="utf-8"
        )
        rows.append(
            {
                "method": name,
                "seconds": elapsed,
                "queries": len(queries),
                "records": len(items),
            }
        )
    result = {
        "measurements": rows,
        "index_build_s": build_s,
        "lookup_speedup": rows[0]["seconds"] / rows[1]["seconds"],
        "speedup_including_build": rows[0]["seconds"] / (rows[1]["seconds"] + build_s),
    }
    print(json.dumps(result, indent=2))
    (output / "target-optimization.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
