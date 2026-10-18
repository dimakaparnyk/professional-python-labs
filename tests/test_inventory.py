"""Functional and boundary checks using only the standard library."""

import unittest
from decimal import Decimal
from io import StringIO
from unittest.mock import patch

from computer_inventory.main import create_demo_devices, read_cost, run_menu
from computer_inventory.models import Device
from computer_inventory.services import (
    add_device,
    average_cost,
    filter_by_manufacturer,
    most_expensive,
    search_devices,
    sort_by_cost,
    total_cost,
)


class InventoryTests(unittest.TestCase):
    def setUp(self):
        self.devices = create_demo_devices()

    def test_totals(self):
        self.assertEqual(total_cost(self.devices), Decimal("92700"))
        self.assertEqual(average_cost(self.devices), Decimal("23175.00"))

    def test_search_all_fields(self):
        for query, count in [
            ("inv-002", 1),
            ("ноутбук", 2),
            ("dElL", 2),
            ("latitude", 1),
            ("missing", 0),
        ]:
            with self.subTest(query=query):
                self.assertEqual(len(search_devices(self.devices, query)), count)
        self.assertEqual(search_devices(self.devices, "  "), [])

    def test_filter_exact_case_insensitive(self):
        self.assertEqual(len(filter_by_manufacturer(self.devices, " dELL ")), 2)
        self.assertEqual(filter_by_manufacturer(self.devices, "De"), [])

    def test_max_and_sort(self):
        self.assertEqual(most_expensive(self.devices).inventory_number, "INV-003")
        ordered = sort_by_cost(self.devices)
        self.assertEqual(ordered[0].inventory_number, "INV-004")
        self.assertEqual(self.devices[0].inventory_number, "INV-001")

    def test_empty_inventory(self):
        self.assertEqual(total_cost([]), Decimal("0.00"))
        self.assertEqual(average_cost([]), Decimal("0.00"))
        self.assertIsNone(most_expensive([]))
        self.assertEqual(search_devices([], "Dell"), [])

    def test_add_and_duplicate(self):
        d = Device(" inv-005 ", "ПК", "HP", "ProDesk", Decimal("20000"))
        add_device(self.devices, d)
        self.assertEqual(len(self.devices), 5)
        with self.assertRaises(ValueError):
            add_device(self.devices, Device("INV-005", "ПК", "HP", "X", Decimal(1)))

    def test_invalid_model(self):
        for value in ["-1", "NaN", "Infinity", "1.001"]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                Device("X", "ПК", "HP", "A", Decimal(value))
        with self.assertRaises(ValueError):
            Device("  ", "ПК", "HP", "A", Decimal(0))

    def test_exact_money_and_rounding(self):
        values = [
            Device(str(i), "ПК", "HP", "A", Decimal(c))
            for i, c in enumerate(["0.10", "0.20", "0.20"])
        ]
        self.assertEqual(total_cost(values), Decimal("0.50"))
        self.assertEqual(average_cost(values), Decimal("0.17"))

    @patch("sys.stdout", new_callable=StringIO)
    def test_cost_input_validation(self, output):
        with patch(
            "builtins.input", side_effect=["NaN", "-1", "1.001", "abc", "12,50"]
        ):
            self.assertEqual(read_cost(), Decimal("12.50"))
        self.assertEqual(output.getvalue().count("Помилка:"), 4)

    @patch("sys.stdout", new_callable=StringIO)
    def test_menu_add_search_and_exit(self, output):
        values = [
            "1",
            "A-1",
            "Ноутбук",
            "Dell",
            "Test",
            "100,50",
            "3",
            "A-1",
            "5",
            "wrong",
            "0",
        ]
        with patch("builtins.input", side_effect=values):
            run_menu()
        text = output.getvalue()
        self.assertIn("Пристрій додано.", text)
        self.assertIn("100.50", text)
        self.assertIn("Невідома команда.", text)
        self.assertIn("Роботу завершено.", text)


if __name__ == "__main__":
    unittest.main()
