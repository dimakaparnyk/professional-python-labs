"""Domain model and validation."""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Device:
    """An inventory item; cost is a non-negative amount in UAH."""

    inventory_number: str
    device_type: str
    manufacturer: str
    model: str
    cost: Decimal

    def __post_init__(self) -> None:
        for field in (
            "inventory_number", "device_type", "manufacturer", "model",
        ):
            value = getattr(self, field).strip()
            if not value:
                raise ValueError("Текстові поля не можуть бути порожніми.")
            object.__setattr__(self, field, value)
        if (not self.cost.is_finite()
                or not 0 <= self.cost <= Decimal("1000000000000")):
            raise ValueError(
                "Вартість має бути числом від 0 до 1000000000000."
            )
        if self.cost != self.cost.quantize(Decimal("0.01")):
            raise ValueError("Допускається не більше двох знаків після коми.")
