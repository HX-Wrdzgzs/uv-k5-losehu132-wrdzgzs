#!/usr/bin/env python3
"""Validate, verify, or write only the K5DB repeater database.

This is the public-package-friendly entry point: ``tails.bin`` is optional and
is never required for the database operation.  Use ``--tails`` only for a
private package and ``--write-tails`` when the private tail resource should be
written too.
"""

from __future__ import annotations

import argparse
import secrets
from pathlib import Path

try:
    import serial
except ImportError:  # pragma: no cover - environment dependent
    serial = None

try:
    from .write_eeprom_repeaters import (
        ExpandedEepromClient,
        TAILS_START_ADDRESS,
        first_mismatch,
        split_blocks,
        validate_database,
        validate_tail_blob,
    )
except ImportError:  # pragma: no cover - direct script execution
    from write_eeprom_repeaters import (
        ExpandedEepromClient,
        TAILS_START_ADDRESS,
        first_mismatch,
        split_blocks,
        validate_database,
        validate_tail_blob,
    )


def parse_int(value: str) -> int:
    return int(value, 0)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("port", nargs="?", default="COM4")
    parser.add_argument("database", nargs="?", type=Path, default=Path("repeaters.bin"))
    parser.add_argument("--tails", type=Path)
    parser.add_argument("--address", type=parse_int, default=0x40000)
    parser.add_argument("--baud", type=int, default=38400)
    parser.add_argument("--chunk-size", type=int, default=64)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--verify-device", action="store_true")
    parser.add_argument("--write-tails", action="store_true")
    parser.add_argument("--confirm", action="store_true", help="confirm the requested EEPROM write")
    return parser.parse_args()


def read_range(client: ExpandedEepromClient, expected: bytes, address: int, chunk_size: int) -> bytes:
    result = bytearray()
    for current, block in split_blocks(expected, address, chunk_size):
        result.extend(client.read(current, len(block)))
    return bytes(result)


def write_range(client: ExpandedEepromClient, data: bytes, address: int, chunk_size: int) -> None:
    for current, block in split_blocks(data, address, chunk_size):
        client.write(current, block)
        actual = client.read(current, len(block))
        mismatch = first_mismatch(block, actual)
        if mismatch is not None:
            raise RuntimeError(f"read-back mismatch at 0x{current + mismatch:05X}")


def main() -> int:
    args = parse_args()
    database = validate_database(args.database, args.address)
    tails = None
    if args.tails:
        tails = validate_tail_blob(args.tails)
    if args.write_tails and tails is None:
        raise SystemExit("--write-tails requires --tails")
    if not 8 <= args.chunk_size <= 120:
        raise SystemExit("chunk size must be between 8 and 120 bytes")
    if not args.write and not args.verify_device:
        print("Validation-only mode. Use --verify-device or --write --confirm for device access.")
        return 0
    if args.write and not args.confirm:
        raise SystemExit("refusing EEPROM write without --confirm")
    if serial is None:
        raise SystemExit("pyserial is required for device access")

    timestamp = secrets.randbits(32)
    with serial.Serial(args.port, args.baud, timeout=1.5) as port:
        client = ExpandedEepromClient(port, timestamp)
        version = client.hello()
        if args.write:
            write_range(client, database, args.address, args.chunk_size)
            if args.write_tails:
                write_range(client, tails, TAILS_START_ADDRESS, args.chunk_size)
            print(f"EEPROM update verified on {args.port} ({version})")
        else:
            actual = read_range(client, database, args.address, args.chunk_size)
            mismatch = first_mismatch(database, actual)
            if mismatch is not None:
                raise RuntimeError(f"database mismatch at 0x{args.address + mismatch:05X}")
            if tails is not None:
                actual_tails = read_range(client, tails, TAILS_START_ADDRESS, args.chunk_size)
                mismatch = first_mismatch(tails, actual_tails)
                if mismatch is not None:
                    raise RuntimeError(f"tail resource mismatch at 0x{TAILS_START_ADDRESS + mismatch:05X}")
            print(f"Device database verified on {args.port} ({version}); no writes performed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
