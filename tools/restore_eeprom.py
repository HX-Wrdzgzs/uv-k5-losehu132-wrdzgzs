#!/usr/bin/env python3
"""Restore a backup with calibration bytes protected by default.

Without both ``--write`` and ``--confirm-restore`` this command only validates
the backup and prints the ranges that would be restored.  The RSSI calibration
bytes at 0x1EC0-0x1ECF are skipped unless the user explicitly supplies
``--include-calibration --confirm-calibration``.
"""

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
    from .write_eeprom_repeaters import ExpandedEepromClient, first_mismatch
except ImportError:  # pragma: no cover - direct script execution
    from write_eeprom_repeaters import ExpandedEepromClient, first_mismatch


CALIBRATION_RANGES = ((0x1EC0, 0x1ED0),)


def parse_int(value: str) -> int:
    return int(value, 0)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("backup", type=Path)
    parser.add_argument("--port", default="COM4")
    parser.add_argument("--start", type=parse_int)
    parser.add_argument("--chunk-size", type=int, default=128)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--confirm-restore", action="store_true")
    parser.add_argument("--include-calibration", action="store_true")
    parser.add_argument("--confirm-calibration", action="store_true")
    return parser.parse_args()


def load_metadata(backup: Path) -> dict:
    sidecar = backup.with_suffix(backup.suffix + ".json")
    if not sidecar.is_file():
        return {}
    return json.loads(sidecar.read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def segments(start: int, length: int, include_calibration: bool):
    end = start + length
    boundaries = {start, end}
    if not include_calibration:
        for left, right in CALIBRATION_RANGES:
            if start < right and left < end:
                boundaries.update((max(start, left), min(end, right)))
    points = sorted(boundaries)
    for left, right in zip(points, points[1:]):
        if left < right and (include_calibration or not any(a <= left < b for a, b in CALIBRATION_RANGES)):
            yield left, right


def main() -> int:
    args = parse_args()
    if not args.backup.is_file():
        raise SystemExit(f"backup not found: {args.backup}")
    metadata = load_metadata(args.backup)
    data = args.backup.read_bytes()
    if metadata.get("sha256") and metadata["sha256"] != digest(args.backup):
        raise SystemExit("backup SHA-256 does not match its sidecar")
    start = args.start if args.start is not None else int(metadata.get("start", 0))
    if start < 0 or start + len(data) > 0x80000:
        raise SystemExit("restore range must stay inside 0x00000-0x7FFFF")
    if not 1 <= args.chunk_size <= 128:
        raise SystemExit("chunk size must be between 1 and 128 bytes")
    if args.include_calibration and not args.confirm_calibration:
        raise SystemExit("--include-calibration also requires --confirm-calibration")

    safe_segments = list(segments(start, len(data), args.include_calibration))
    print(f"Backup validated: {len(data)} bytes, SHA-256 {digest(args.backup)}")
    print(f"Restore segments: {', '.join(f'0x{a:05X}-0x{b - 1:05X}' for a, b in safe_segments)}")
    if not args.write or not args.confirm_restore:
        print("Validation-only mode. Add --write --confirm-restore to modify the device.")
        return 0
    if serial is None:
        raise SystemExit("pyserial is required for restore")

    timestamp = secrets.randbits(32)
    with serial.Serial(args.port, 38400, timeout=1.5) as port:
        client = ExpandedEepromClient(port, timestamp)
        firmware_version = client.hello()
        for segment_start, segment_end in safe_segments:
            cursor = segment_start
            while cursor < segment_end:
                size = min(args.chunk_size, segment_end - cursor)
                offset = cursor - start
                block = data[offset : offset + size]
                client.write(cursor, block)
                actual = client.read(cursor, size)
                mismatch = first_mismatch(block, actual)
                if mismatch is not None:
                    raise RuntimeError(f"read-back mismatch at 0x{cursor + mismatch:05X}")
                cursor += size
                print(f"\rWrote 0x{cursor:05X}", end="", flush=True)
    print()
    print(f"Restore verified on firmware {firmware_version}; calibration protected={not args.include_calibration}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
