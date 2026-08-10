#!/usr/bin/env python3
"""Read-only UV-K5 expanded-EEPROM compatibility probe."""

from __future__ import annotations

import argparse
import json

try:
    import serial
except ImportError:  # pragma: no cover - environment dependent
    serial = None

try:
    from .write_eeprom_repeaters import ExpandedEepromClient
except ImportError:  # pragma: no cover - direct script execution
    from write_eeprom_repeaters import ExpandedEepromClient


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", default="COM4")
    parser.add_argument("--baud", type=int, default=38400)
    parser.add_argument("--json", action="store_true", dest="as_json")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if serial is None:
        raise SystemExit("pyserial is required for a hardware probe")

    timestamp = 0x4B355632
    with serial.Serial(args.port, args.baud, timeout=1.5) as port:
        client = ExpandedEepromClient(port, timestamp)
        version = client.hello()
        client.read(0x40000, 1)
        client.read(0x7FFFF, 1)

    result = {
        "port": args.port,
        "baud": args.baud,
        "firmware_version": version,
        "expanded_eeprom_range": "0x40000-0x7FFFF",
        "read_only": True,
        "writes_performed": False,
        "model_identification": "protocol-compatible UV-K5 expanded EEPROM; model label not asserted",
    }
    if args.as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Device probe passed on {args.port}: firmware={version}")
        print("Read-only capacity check passed for 0x40000-0x7FFFF; no writes performed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
