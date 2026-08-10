#!/usr/bin/env python3
"""Create a read-only UV-K5 EEPROM backup with a SHA-256 sidecar."""

from __future__ import annotations

import argparse
import hashlib
import json
import secrets
from pathlib import Path

try:
    import serial
except ImportError:  # pragma: no cover - environment dependent
    serial = None

try:
    from .write_eeprom_repeaters import ExpandedEepromClient
except ImportError:  # pragma: no cover - direct script execution
    from write_eeprom_repeaters import ExpandedEepromClient


def parse_int(value: str) -> int:
    return int(value, 0)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", default="COM4")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--start", type=parse_int, default=0)
    parser.add_argument("--length", type=parse_int, default=0x80000)
    parser.add_argument("--chunk-size", type=int, default=128)
    return parser.parse_args()


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    args = parse_args()
    if serial is None:
        raise SystemExit("pyserial is required for an EEPROM backup")
    if args.start < 0 or args.length <= 0 or args.start + args.length > 0x80000:
        raise SystemExit("backup range must stay inside the supported 0x00000-0x7FFFF EEPROM window")
    if not 1 <= args.chunk_size <= 128:
        raise SystemExit("chunk size must be between 1 and 128 bytes")
    if args.output.exists():
        raise SystemExit(f"refusing to overwrite existing backup: {args.output}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    timestamp = secrets.randbits(32)
    data = bytearray()
    with serial.Serial(args.port, 38400, timeout=1.5) as port:
        client = ExpandedEepromClient(port, timestamp)
        firmware_version = client.hello()
        for offset in range(0, args.length, args.chunk_size):
            address = args.start + offset
            size = min(args.chunk_size, args.length - offset)
            data.extend(client.read(address, size))
            print(f"\rRead {len(data) * 100 // args.length:3d}% 0x{address:05X}", end="", flush=True)
    print()
    args.output.write_bytes(data)
    sidecar = args.output.with_suffix(args.output.suffix + ".json")
    metadata = {
        "schema": 1,
        "port": args.port,
        "firmware_version": firmware_version,
        "start": args.start,
        "length": args.length,
        "sha256": digest(args.output),
        "calibration_ranges": [{"start": 0x1EC0, "end": 0x1ED0}],
        "read_only_operation": True,
    }
    sidecar.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Backup created: {args.output}")
    print(f"SHA-256: {metadata['sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
