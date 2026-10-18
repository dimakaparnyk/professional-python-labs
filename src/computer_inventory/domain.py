"""Lab 4: typed object model, composition, generics and dependency injection."""

from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Generic, Protocol, TypedDict, TypeVar

from computer_inventory.models import Device
from computer_inventory.services import (
    average_cost,
    filter_by_manufacturer,
    most_expensive,
    total_cost,
)


@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str = "UAH"

    def __post_init__(self) -> None:
        if not self.amount.is_finite() or self.amount < 0:
            raise ValueError("Invalid money amount")
        if self.currency != "UAH":
            raise ValueError("Only UAH is supported")

    def __add__(self, other: "Money") -> "Money":
        return Money(self.amount + other.amount, self.currency)

    def __str__(self) -> str:
        return f"{self.amount:.2f} {self.currency}"


@dataclass(frozen=True)
class Manufacturer:
    name: str

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Empty manufacturer")


@dataclass(frozen=True)
class Computer(Device):
    ram_gb: int = 8

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.ram_gb < 1:
            raise ValueError("RAM must be positive")


@dataclass(frozen=True)
class Printer(Device):
    color: bool = False


T = TypeVar("T", bound=Device)


class InventoryRepository(Protocol[T]):
    def add(self, item: T) -> None: ...
    def get(self, inventory_number: str) -> T | None: ...
    def all(self) -> list[T]: ...


class InMemoryRepository(Generic[T]):
    def __init__(self) -> None:
        self._items: dict[str, T] = {}

    def add(self, item: T) -> None:
        key = item.inventory_number.casefold()
        if key in self._items:
            raise ValueError("Duplicate inventory number")
        self._items[key] = item

    def get(self, inventory_number: str) -> T | None:
        return self._items.get(inventory_number.strip().casefold())

    def all(self) -> list[T]:
        return list(self._items.values())


class MaintenancePolicy(ABC):
    @abstractmethod
    def interval_days(self, device: Device) -> int:
        """Return the recommended maintenance interval."""


class StandardMaintenance(MaintenancePolicy):
    def interval_days(self, device: Device) -> int:
        return 90 if isinstance(device, Printer) else 180


class MaintenanceService:
    def __init__(
        self, repository: InventoryRepository[Device], policy: MaintenancePolicy
    ) -> None:
        self.repository = repository
        self.policy = policy

    def schedule(self, inventory_number: str) -> int:
        device = self.repository.get(inventory_number)
        if device is None:
            raise LookupError(inventory_number)
        return self.policy.interval_days(device)


@dataclass
class InventoryRegistry:
    repository: InventoryRepository[Device]
    manufacturers: list[Manufacturer] = field(default_factory=list)

    def register(self, device: Device) -> None:
        self.repository.add(device)
        manufacturer = Manufacturer(device.manufacturer)
        if manufacturer not in self.manufacturers:
            self.manufacturers.append(manufacturer)

    @property
    def total(self) -> Money:
        return Money(total_cost(self.repository.all()))

    @property
    def average(self) -> Money:
        return Money(average_cost(self.repository.all()))

    def best(self) -> Device | None:
        return most_expensive(self.repository.all())

    def by_manufacturer(self, name: str) -> list[Device]:
        return filter_by_manufacturer(self.repository.all(), name)

    def __len__(self) -> int:
        return len(self.repository.all())

    def __iter__(self) -> Iterator[Device]:
        return iter(self.repository.all())

    def __contains__(self, inventory_number: str) -> bool:
        return self.repository.get(inventory_number) is not None

    def __getitem__(self, inventory_number: str) -> Device:
        device = self.repository.get(inventory_number)
        if device is None:
            raise KeyError(inventory_number)
        return device


class DevicePayload(TypedDict):
    inventory_number: str
    device_type: str
    manufacturer: str
    model: str
    cost: str


def from_payload(payload: DevicePayload) -> Device:
    return Device(
        payload["inventory_number"],
        payload["device_type"],
        payload["manufacturer"],
        payload["model"],
        Decimal(payload["cost"]),
    )


class AsyncInventoryProvider(Protocol):
    async def fetch(self) -> list[Device]: ...


async def load_remote(provider: AsyncInventoryProvider) -> list[Device]:
    return await provider.fetch()
