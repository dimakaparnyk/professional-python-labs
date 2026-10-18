"""Deliberately defective examples are isolated from the production test suite."""

import importlib.util
import json
import random
import sys
import tempfile
from decimal import Decimal
from pathlib import Path
from unittest.mock import Mock

import coverage

from computer_inventory.domain import (
    InMemoryRepository,
    MaintenanceService,
    StandardMaintenance,
)
from computer_inventory.models import Device


def main() -> None:
    output = Path(sys.argv[1]).resolve()
    output.mkdir(parents=True, exist_ok=True)

    def wrong_total(values):
        return sum(values) + 1

    weak_passed = True
    wrong_total([1, 2, 3])
    try:
        assert wrong_total([1, 2, 3]) == 6
        strong_detected = False
    except AssertionError:
        strong_detected = True
    source = output / "branch_sample.py"
    source.write_text(
        'def classify(value):\n    if value >= 100:\n        return "high"\n    return "low"\n',
        encoding="utf-8",
    )
    branch = []
    for cases in ([100], [100, 0]):
        cov = coverage.Coverage(branch=True, data_file=None, include=[str(source)])
        cov.start()
        spec = importlib.util.spec_from_file_location("branch_sample", source)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        for value in cases:
            module.classify(value)
        cov.stop()
        report = output / f"coverage-{len(cases)}.json"
        cov.json_report(outfile=str(report))
        branch.append(json.loads(report.read_text(encoding="utf-8"))["totals"])
    rng = random.Random(42)
    flaky_pass = 0
    for _ in range(20):
        try:
            assert rng.randint(1, 2) == 1
            flaky_pass += 1
        except AssertionError:
            pass
    fixed_pass = sum(random.Random(42).randint(1, 2) == 1 for _ in range(20))
    device = Device("A", "Computer", "Dell", "Model", Decimal(100))
    mock = Mock()
    mock.get.return_value = device
    fake = InMemoryRepository[Device]()
    fake.add(device)
    assert MaintenanceService(mock, StandardMaintenance()).schedule(
        "A"
    ) == MaintenanceService(fake, StandardMaintenance()).schedule("A")
    temporary_paths = []
    for _ in range(2):
        with tempfile.TemporaryDirectory(dir=output) as directory:
            path = Path(directory) / "output.txt"
            assert not path.exists()
            path.write_text("isolated", encoding="utf-8")
            temporary_paths.append(str(path))
    assert temporary_paths[0] != temporary_paths[1]
    assert not any(Path(p).exists() for p in temporary_paths)
    result = {
        "weak_passed_without_result_check": weak_passed,
        "strong_assertion_detected_defect": strong_detected,
        "branch_before": branch[0],
        "branch_after": branch[1],
        "random_sequence_passed": flaky_pass,
        "random_sequence_failed": 20 - flaky_pass,
        "seeded_test_passed": fixed_pass,
        "mock_fake_equivalent": True,
        "filesystem_isolated": True,
    }
    (output / "results06.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
