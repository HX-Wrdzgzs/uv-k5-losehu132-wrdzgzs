#!/usr/bin/env python3
"""Run static safety checks before firmware or EEPROM operations.

This tool never opens a serial port and never writes a device.  Hardware
identity and EEPROM capacity require the separate read-only device probe.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from .write_eeprom_repeaters import validate_database
except ImportError:  # pragma: no cover - direct script execution
    from write_eeprom_repeaters import validate_database


FLASH_BYTES = 60 * 1024
PACKED_LIMIT = 64 * 1024


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--firmware", type=Path, required=True)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--json", action="store_true", dest="as_json")
    return parser.parse_args()


def check(args: argparse.Namespace) -> dict:
    firmware = args.firmware.read_bytes()
    if not firmware:
        raise ValueError("firmware file is empty")
    limit = PACKED_LIMIT if ".packed." in args.firmware.name else FLASH_BYTES
    if len(firmware) > limit:
        raise ValueError(
            f"{args.firmware.name} is {len(firmware)} bytes, above the {limit}-byte limit"
        )

    database = validate_database(args.database, 0x40000)
    result = {
        "firmware": {"path": str(args.firmware), "size": len(firmware), "limit": limit},
        "database": {"path": str(args.database), "size": len(database), "format": "K5DB v3"},
        "device_probe": "not_run",
    }
    return result


def main() -> int:
    args = parse_args()
    result = check(args)
    if args.as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(
            f"Compatibility checks passed: {result['firmware']['path']} + "
            f"{result['database']['path']}"
        )
        print("Hardware probe: not run (use check_device_compatibility.py --port COM4)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
