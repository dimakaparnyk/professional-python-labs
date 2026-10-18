"""Lab 2: structured data, functional decomposition and decorators."""

from collections import Counter, defaultdict, deque
from collections.abc import Callable, Iterable
from decimal import Decimal
from functools import wraps
from time import perf_counter
from typing import ParamSpec, TypeVar

from computer_inventory.models import Device
from computer_inventory.services import average_cost, most_expensive, total_cost

P = ParamSpec("P")
R = TypeVar("R")
history: deque[tuple[str, float]] = deque(maxlen=10)


def timed(label: str) -> Callable[[Callable[P, R]], Callable[P, R]]:
    def decorate(function: Callable[P, R]) -> Callable[P, R]:
        @wraps(function)
        def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
            start = perf_counter()
            try:
                return function(*args, **kwargs)
            finally:
                history.append((label, perf_counter() - start))

        return wrapped

    return decorate


def make_cost_filter(minimum: Decimal) -> Callable[[Device], bool]:
    """The returned closure remembers the minimum cost."""
    return lambda device: device.cost >= minimum


def select(devices: Iterable[Device], **criteria: str) -> list[Device]:
    allowed = {"device_type", "manufacturer", "inventory_number", "model"}
    if not criteria.keys() <= allowed:
        raise ValueError("Unknown search field")
    return [
        d
        for d in devices
        if all(
            str(getattr(d, key)).casefold() == value.strip().casefold()
            for key, value in criteria.items()
        )
    ]


def merge(*groups: Iterable[Device]) -> list[Device]:
    return [device for group in groups for device in group]


def unique_manufacturers(devices: Iterable[Device]) -> set[str]:
    return {d.manufacturer for d in devices}


def build_index(devices: Iterable[Device]) -> dict[str, Device]:
    items = list(devices)
    index = {d.inventory_number.casefold(): d for d in items}
    if len(items) != len(index):
        raise ValueError("Duplicate inventory number")
    return index


def group_by(
    devices: Iterable[Device], field: str = "manufacturer"
) -> dict[str, list[Device]]:
    if field not in {"manufacturer", "device_type"}:
        raise ValueError("Unsupported grouping field")
    groups: defaultdict[str, list[Device]] = defaultdict(list)
    for device in devices:
        groups[str(getattr(device, field))].append(device)
    return dict(groups)


def count_types(devices: Iterable[Device]) -> Counter[str]:
    return Counter(d.device_type for d in devices)


@timed("summary")
def summarize(devices: Iterable[Device]) -> dict[str, object]:
    items = list(devices)
    best = most_expensive(items)
    return {
        "count": len(items),
        "total": str(total_cost(items)),
        "average": str(average_cost(items)),
        "most_expensive": best.inventory_number if best else None,
        "manufacturers": sorted(unique_manufacturers(items)),
        "types": dict(count_types(items)),
    }
