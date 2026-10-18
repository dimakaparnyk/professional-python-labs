"""Ukrainian console interface and reproducible demonstration."""

import argparse
from decimal import Decimal, InvalidOperation

from computer_inventory.models import Device
from computer_inventory.services import (
    add_device, average_cost, filter_by_manufacturer, most_expensive,
    search_devices, sort_by_cost, total_cost,
)


CURRENCY = "грн"
MAX_COST = Decimal("1000000000000")


def create_demo_devices() -> list[Device]:
    return [
        Device("INV-001", "Ноутбук", "Lenovo", "ThinkPad E14",
               Decimal("32000")),
        Device("INV-002", "Монітор", "Dell", "P2422H", Decimal("8500")),
        Device("INV-003", "Ноутбук", "Dell", "Latitude 5440",
               Decimal("45000")),
        Device("INV-004", "Принтер", "HP", "LaserJet M110w", Decimal("7200")),
    ]


def print_devices(devices: list[Device]) -> None:
    if not devices:
        print("Пристроїв не знайдено.")
        return
    for d in devices:
        print(f"{d.inventory_number} | {d.device_type} | {d.manufacturer} | "
              f"{d.model} | {d.cost:.2f} {CURRENCY}")


def print_statistics(devices: list[Device]) -> None:
    print(f"Кількість пристроїв: {len(devices)}")
    print(f"Загальна вартість: {total_cost(devices):.2f} {CURRENCY}")
    print(f"Середня вартість: {average_cost(devices):.2f} {CURRENCY}")
    best = most_expensive(devices)
    print("Найдорожчий пристрій:")
    print_devices([best] if best else [])


def read_text(prompt: str) -> str:
    while True:
        value = input(prompt).strip()
        if value:
            return value
        print("Помилка: введіть непорожнє значення.")


def read_cost() -> Decimal:
    while True:
        try:
            text = input("Вартість (грн): ").strip().replace(",", ".")
            value = Decimal(text)
            if (not value.is_finite() or not 0 <= value <= MAX_COST):
                raise ValueError
            if value != value.quantize(Decimal("0.01")):
                raise ValueError
            return value
        except (InvalidOperation, ValueError):
            print("Помилка: число від 0 до 1000000000000, "
                  "до 2 знаків після коми.")


def read_device() -> Device:
    return Device(
        read_text("Інвентарний номер: "), read_text("Тип: "),
        read_text("Виробник: "), read_text("Модель: "), read_cost(),
    )


def run_demo() -> None:
    devices = create_demo_devices()
    print("ОБЛІК КОМП’ЮТЕРНОЇ ТЕХНІКИ — ВАРІАНТ 13")
    print("Усі пристрої:")
    print_devices(devices)
    print("\nПошук: INV-002")
    print_devices(search_devices(devices, "INV-002"))
    print("\nВиробник: Dell")
    print_devices(filter_by_manufacturer(devices, "Dell"))
    print("\nСтатистика:")
    print_statistics(devices)


def run_menu() -> None:
    devices: list[Device] = []
    print("Облік комп’ютерної техніки. Варіант 13.")
    print("Дані зберігаються в пам’яті до завершення програми.")
    while True:
        print("\n1 — Додати  2 — Список  3 — Пошук  4 — Виробник")
        print("5 — Статистика  6 — За вартістю  0 — Вихід")
        command = input("Команда: ").strip()
        if command == "0":
            print("Роботу завершено.")
            return
        if command == "1":
            try:
                add_device(devices, read_device())
                print("Пристрій додано.")
            except ValueError as error:
                print(f"Помилка: {error}")
        elif command == "2":
            print_devices(devices)
        elif command == "3":
            print_devices(search_devices(devices, read_text("Пошук: ")))
        elif command == "4":
            manufacturer = read_text("Виробник: ")
            print_devices(filter_by_manufacturer(devices, manufacturer))
        elif command == "5":
            print_statistics(devices)
        elif command == "6":
            print_devices(sort_by_cost(devices))
        else:
            print("Невідома команда.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Облік комп’ютерної техніки")
    parser.add_argument(
        "--demo", action="store_true", help="Демонстрація варіанта 13",
    )
    args = parser.parse_args()
    try:
        if args.demo:
            run_demo()
        else:
            run_menu()
    except (EOFError, KeyboardInterrupt):
        print("\nРоботу завершено.")


if __name__ == "__main__":
    main()
