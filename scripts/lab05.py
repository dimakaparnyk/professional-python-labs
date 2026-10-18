"""Run strict/tolerant and atomic-output experiments."""
from dataclasses import asdict, replace
import csv
import json
from pathlib import Path
import sys

from computer_inventory.fileio import (
    FileConfig, ImportStats, RecordValidationError, atomic_text,
    configure_logging, export_json, import_csv, load_config, run_import,
)


def main() -> None:
    output = Path(sys.argv[1]).resolve()
    output.mkdir(parents=True, exist_ok=True)
    configure_logging(output / "errors.log")
    source = output / "mixed.csv"
    with source.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["inventory_number", "type", "manufacturer", "model", "value"])
        for i in range(1010):
            writer.writerow([str(i), "Computer", "Dell", "Model", "bad" if i % 101 == 100 else "100"])
    rows = []
    for tolerant in (False, True):
        target = output / f"export-{tolerant}.json"
        target.write_text('["previous valid output"]', encoding="utf-8")
        config = FileConfig(source, target, skip_invalid=tolerant)
        stats = ImportStats()
        try:
            export_json(import_csv(config, stats), target, stats)
            status = "success"
        except RecordValidationError as error:
            status = type(error).__name__ + " caused by " + type(error.__cause__).__name__
        rows.append({"mode": "tolerant" if tolerant else "strict", **asdict(stats), "status": status})
        assert not list(output.glob("*.tmp"))
        if not tolerant:
            assert target.read_text(encoding="utf-8") == '["previous valid output"]'
    target = output / "atomic.txt"
    target.write_text("original", encoding="utf-8")
    try:
        with atomic_text(target) as stream:
            stream.write("incomplete")
            raise RuntimeError("simulated interruption")
    except RuntimeError:
        assert target.read_text(encoding="utf-8") == "original"
        assert not list(output.glob("*.tmp"))
    print(json.dumps(rows, indent=2))
    print("Atomic export: previous output preserved; temporary file removed")
    (output / "results05.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
