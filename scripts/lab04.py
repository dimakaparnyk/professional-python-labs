"""Object model demo for inventory variant 13."""

from decimal import Decimal

from computer_inventory.domain import (
    Computer,
    InMemoryRepository,
    InventoryRegistry,
    MaintenanceService,
    Printer,
    StandardMaintenance,
)
from computer_inventory.models import Device


def main() -> None:
    repository: InMemoryRepository[Device] = InMemoryRepository()
    registry = InventoryRegistry(repository)
    registry.register(
        Computer("C-1", "Computer", "Dell", "Latitude", Decimal("40000"), 16)
    )
    registry.register(Printer("P-1", "Printer", "HP", "LaserJet", Decimal("8000")))
    service = MaintenanceService(repository, StandardMaintenance())
    print(
        "Devices:",
        len(registry),
        "Total:",
        registry.total,
        "Average:",
        registry.average,
    )
    print("Computer maintenance:", service.schedule("C-1"), "days")
    print("Printer maintenance:", service.schedule("P-1"), "days")
    print("Contains C-1:", "C-1" in registry)
    print("Best:", registry.best())
    print("Dell:", registry.by_manufacturer("Dell"))


if __name__ == "__main__":
    main()
