"""Business logic independent from console input/output."""

from decimal import ROUND_HALF_UP, Decimal

from computer_inventory.models import Device

CENT = Decimal("0.01")


def add_device(devices: list[Device], device: Device) -> None:
    """Add an item, rejecting duplicate inventory numbers."""
    if any(
        d.inventory_number.casefold() == device.inventory_number.casefold()
        for d in devices
    ):
        raise ValueError("Пристрій із цим інвентарним номером уже існує.")
    devices.append(device)


def search_devices(devices: list[Device], query: str) -> list[Device]:
    """Search a substring in all four text fields, ignoring letter case."""
    query = query.strip().casefold()
    if not query:
        return []
    return [
        d
        for d in devices
        if any(
            query in value.casefold()
            for value in (
                d.inventory_number,
                d.device_type,
                d.manufacturer,
                d.model,
            )
        )
    ]


def filter_by_manufacturer(
    devices: list[Device],
    manufacturer: str,
) -> list[Device]:
    """Match a full manufacturer name, ignoring case and outer whitespace."""
    name = manufacturer.strip().casefold()
    return [d for d in devices if d.manufacturer.casefold() == name]


def total_cost(devices: list[Device]) -> Decimal:
    """Sum costs exactly, including an empty inventory."""
    return sum((d.cost for d in devices), Decimal("0.00"))


def average_cost(devices: list[Device]) -> Decimal:
    """Return a mean rounded to cents; empty inventory has mean zero."""
    if not devices:
        return Decimal("0.00")
    return (total_cost(devices) / len(devices)).quantize(
        CENT,
        rounding=ROUND_HALF_UP,
    )


def most_expensive(devices: list[Device]) -> Device | None:
    """Return the first maximal item, or None for an empty inventory."""
    return max(devices, key=lambda d: d.cost, default=None)


def sort_by_cost(devices: list[Device]) -> list[Device]:
    """Return a new ascending list without modifying the original."""
    return sorted(devices, key=lambda d: d.cost)
