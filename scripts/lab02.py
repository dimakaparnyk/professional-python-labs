"""Reproducible list versus dictionary experiment."""

import json
from decimal import Decimal
from statistics import median
from timeit import repeat

from computer_inventory.analytics import (
    build_index,
    count_types,
    group_by,
    make_cost_filter,
    merge,
    select,
    summarize,
)
from computer_inventory.main import create_demo_devices
from computer_inventory.models import Device


def main() -> None:
    demo = create_demo_devices()
    print(json.dumps(summarize(demo), ensure_ascii=False, indent=2))
    print("Dell:", [d.inventory_number for d in select(demo, manufacturer="Dell")])
    print("Groups:", {k: len(v) for k, v in group_by(demo).items()})
    print("Counter:", count_types(demo))
    print(
        "Closure:",
        [d.inventory_number for d in filter(make_cost_filter(Decimal(30000)), demo)],
    )
    assert len(merge(demo[:2], demo[2:])) == 4
    rows = []
    for n in (1000, 10000, 100000):
        items = [
            Device(str(i), "Computer", "Dell", "Model", Decimal(i)) for i in range(n)
        ]
        target = str(n - 1)
        start = median(repeat(lambda: build_index(items), number=1, repeat=5))
        index = build_index(items)

        def linear():
            return next((d for d in items if d.inventory_number == target), None)

        def lookup():
            return index.get(target)

        assert linear() == lookup()
        rows.append(
            {
                "records": n,
                "list_seconds": median(repeat(linear, number=50, repeat=5)) / 50,
                "dict_seconds": median(repeat(lookup, number=50000, repeat=5)) / 50000,
                "build_seconds": start,
            }
        )
    print(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()
