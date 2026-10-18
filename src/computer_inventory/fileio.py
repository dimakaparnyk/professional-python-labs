"""Lab 5: validated streaming input and transactional file output."""

import csv
import json
import logging
import os
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import TextIO

import yaml

from computer_inventory.models import Device

logger = logging.getLogger(__name__)


class InventoryError(Exception):
    """Base application error."""


class ConfigurationError(InventoryError):
    """Invalid or inaccessible YAML configuration."""


class RecordValidationError(InventoryError):
    """Invalid equipment record."""


class ImportExportError(InventoryError):
    """Input or output operation failed."""


@dataclass(frozen=True)
class FileConfig:
    input: Path
    output: Path
    allowed_types: tuple[str, ...] = ()
    allowed_manufacturers: tuple[str, ...] = ()
    allowed_statuses: tuple[str, ...] = ("active", "maintenance", "retired")
    skip_invalid: bool = False


@dataclass
class ImportStats:
    processed: int = 0
    valid: int = 0
    invalid: int = 0
    exported: int = 0


def configure_logging(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        path, maxBytes=1000000, backupCount=2, encoding="utf-8"
    )
    handler.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def load_config(path: Path) -> FileConfig:
    try:
        with path.open(encoding="utf-8") as source:
            data = yaml.safe_load(source)
        if not isinstance(data, dict):
            raise ValueError("Configuration must be a mapping")
        for key in ("input", "output"):
            if not isinstance(data.get(key), str) or not data[key].strip():
                raise ValueError(f"Missing or invalid {key}")
        for key in ("allowed_types", "allowed_manufacturers", "allowed_statuses"):
            values = data.get(key, [])
            if not isinstance(values, list) or any(
                not isinstance(x, str) or not x.strip() for x in values
            ):
                raise ValueError(f"Invalid {key}")
        skip = data.get("skip_invalid", False)
        if not isinstance(skip, bool):
            raise ValueError("skip_invalid must be boolean")
        base = path.resolve().parent
        result = FileConfig(
            base / data["input"],
            base / data["output"],
            tuple(data.get("allowed_types", [])),
            tuple(data.get("allowed_manufacturers", [])),
            tuple(data.get("allowed_statuses", ["active", "maintenance", "retired"])),
            skip,
        )
        if not result.input.is_file():
            raise ValueError("Input file does not exist")
        return result
    except (OSError, yaml.YAMLError, ValueError) as error:
        raise ConfigurationError(f"Cannot load configuration: {path}") from error


def validate_record(row: dict[str, str], config: FileConfig) -> Device:
    try:
        if None in row or any(v is None for v in row.values()):
            raise ValueError("Malformed CSV record")
        cost = row.get("value", row.get("cost", ""))
        device = Device(
            row["inventory_number"],
            row["type"],
            row["manufacturer"],
            row["model"],
            Decimal(cost),
        )
        if config.allowed_types and device.device_type not in config.allowed_types:
            raise ValueError("Device type is not allowed")
        if (
            config.allowed_manufacturers
            and device.manufacturer not in config.allowed_manufacturers
        ):
            raise ValueError("Manufacturer is not allowed")
        status = row.get("status", "active")
        if status not in config.allowed_statuses:
            raise ValueError("Status is not allowed")
        return device
    except (KeyError, ValueError, InvalidOperation) as error:
        raise RecordValidationError("Invalid inventory record") from error


def import_csv(config: FileConfig, stats: ImportStats) -> Iterator[Device]:
    seen: set[str] = set()
    try:
        with config.input.open(encoding="utf-8-sig", newline="") as source:
            reader = csv.DictReader(source)
            required = {"inventory_number", "type", "manufacturer", "model"}
            if not required <= set(reader.fieldnames or []) or not (
                {"cost", "value"} & set(reader.fieldnames or [])
            ):
                raise ImportExportError("Required CSV columns are missing")
            for line, row in enumerate(reader, 2):
                stats.processed += 1
                try:
                    device = validate_record(row, config)
                    key = device.inventory_number.casefold()
                    if key in seen:
                        raise RecordValidationError("Duplicate inventory number")
                    seen.add(key)
                except RecordValidationError:
                    stats.invalid += 1
                    logger.exception("Invalid record at line %d", line)
                    if not config.skip_invalid:
                        raise
                    continue
                stats.valid += 1
                yield device
    except (OSError, csv.Error) as error:
        raise ImportExportError("CSV input failed") from error


@contextmanager
def atomic_text(path: Path) -> Iterator[TextIO]:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as target:
            yield target
            target.flush()
            os.fsync(target.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def device_json(device: Device) -> dict[str, str]:
    return {
        "inventory_number": device.inventory_number,
        "type": device.device_type,
        "manufacturer": device.manufacturer,
        "model": device.model,
        "value": f"{device.cost:.2f}",
    }


def export_json(devices: Iterator[Device], path: Path, stats: ImportStats) -> None:
    exported = 0
    try:
        with atomic_text(path) as target:
            target.write("[\n")
            for device in devices:
                if exported:
                    target.write(",\n")
                json.dump(device_json(device), target, ensure_ascii=False)
                exported += 1
            target.write("\n]\n")
        stats.exported = exported
        logger.info("Exported %d devices", exported)
    except OSError as error:
        logger.exception("Output failed")
        raise ImportExportError("JSON output failed") from error


def run_import(config_path: Path, stats: ImportStats | None = None) -> ImportStats:
    config = load_config(config_path)
    result = stats if stats is not None else ImportStats()
    export_json(import_csv(config, result), config.output, result)
    return result
