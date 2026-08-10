#!/usr/bin/env python3
"""Write repeaters.bin to the UV-K5 expanded EEPROM with read-back verification.

The script uses the firmware's normal encrypted serial protocol and the custom
0x052B/0x0538 high-address commands. It defaults to validation-only mode; pass
--write explicitly to modify EEPROM.
"""

from __future__ import annotations

import argparse
import secrets
import struct
import sys
import time
from pathlib import Path

try:
    import serial
except ImportError:  # pragma: no cover - environment dependent
    serial = None

DB_HEADER_FORMAT = "<4sBBHII"
REGION_HEADER_FORMAT = "<4sBBBBHHI"
DB_HEADER_SIZE = struct.calcsize(DB_HEADER_FORMAT)
REGION_HEADER_SIZE = struct.calcsize(REGION_HEADER_FORMAT)
DB_MAGIC = b"K5DB"
REGION_MAGIC = b"K5RI"
DB_VERSION = 3
DB_ENTRY_SIZE = 16
EEPROM_START_ADDRESS = 0x40000
TAILS_START_ADDRESS = 0x43000
TAIL_HEADER_FORMAT = "<4sBBHHHHH"
TAIL_HEADER_SIZE = struct.calcsize(TAIL_HEADER_FORMAT)
TAIL_MAGIC = b"K5TL"
EEPROM_DATA_END_ADDRESS = 0x7BFFF
DEFAULT_CHUNK_SIZE = 64
XOR_TABLE = bytes((22, 108, 20, 230, 46, 145, 13, 64, 33, 53, 213, 64, 19, 3, 233, 128))


class ProtocolError(RuntimeError):
    pass


def crc16_xmodem(data: bytes) -> int:
    crc = 0
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            crc <<= 1
            if crc & 0x10000:
                crc = (crc ^ 0x1021) & 0xFFFF
    return crc & 0xFFFF


def xor_bytes(data: bytes) -> bytes:
    return bytes(value ^ XOR_TABLE[index % len(XOR_TABLE)] for index, value in enumerate(data))


def make_frame(payload: bytes) -> bytes:
    if len(payload) > 255:
        raise ValueError("protocol payload exceeds 255 bytes")
    encrypted = xor_bytes(payload + struct.pack("<H", crc16_xmodem(payload)))
    return struct.pack(">HBB", 0xABCD, len(payload), 0) + encrypted + struct.pack(">H", 0xDCBA)


def read_exact(port: serial.Serial, size: int) -> bytes:
    data = port.read(size)
    if len(data) != size:
        raise ProtocolError(f"serial short read: expected {size}, got {len(data)}")
    return data


def receive_reply(port: serial.Serial) -> bytes:
    header = read_exact(port, 4)
    if header[0:2] != b"\xAB\xCD" or header[3] != 0:
        raise ProtocolError(f"invalid reply header: {header.hex(' ')}")
    payload_length = header[2]
    encrypted = read_exact(port, payload_length)
    footer = read_exact(port, 4)
    if footer[2:4] != b"\xDC\xBA":
        raise ProtocolError(f"invalid reply footer: {footer.hex(' ')}")
    return xor_bytes(encrypted)


def send_command(port: serial.Serial, payload: bytes) -> bytes:
    port.write(make_frame(payload))
    port.flush()
    return receive_reply(port)


def command_id(reply: bytes) -> int:
    if len(reply) < 4:
        raise ProtocolError("reply is shorter than the command header")
    return struct.unpack_from("<H", reply, 0)[0]


class ExpandedEepromClient:
    def __init__(self, port: serial.Serial, timestamp: int) -> None:
        self.port = port
        self.timestamp = timestamp

    def hello(self) -> str:
        payload = struct.pack("<HHI", 0x0514, 4, self.timestamp)
        reply = send_command(self.port, payload)
        if command_id(reply) != 0x0515:
            raise ProtocolError(f"unexpected hello response 0x{command_id(reply):04X}")
        version = reply[4:20].split(b"\x00", 1)[0].decode("ascii", errors="replace")
        return version or "unknown"

    def read(self, address: int, length: int) -> bytes:
        if not 1 <= length <= 128:
            raise ValueError("read length must be between 1 and 128 bytes")
        high = (address >> 16) & 0xFFFF
        low = address & 0xFFFF
        # Header.Size stays 8 for compatibility with the existing CHIRP driver;
        # the two low-address bytes follow the normal command fields.
        payload = struct.pack("<HHHBBI", 0x052B, 8, high, length, 0, self.timestamp)
        payload += struct.pack("<H", low)
        reply = send_command(self.port, payload)
        if command_id(reply) != 0x051C or len(reply) < 8 + length:
            raise ProtocolError("invalid high-address read response")
        returned_high = struct.unpack_from("<H", reply, 4)[0]
        returned_size = reply[6]
        if returned_high != high or returned_size != length:
            raise ProtocolError("read response address or length mismatch")
        return reply[8 : 8 + length]

    def write(self, address: int, data: bytes) -> None:
        if not data or len(data) > 120:
            raise ValueError("write block must contain 1 to 120 bytes")
        high = (address >> 16) & 0xFFFF
        low = address & 0xFFFF
        payload = struct.pack(
            "<HHHBBI",
            0x0538,
            len(data) + 10,
            high,
            len(data) + 2,
            0,
            self.timestamp,
        )
        payload += struct.pack("<H", low) + data
        reply = send_command(self.port, payload)
        if command_id(reply) != 0x051E or len(reply) < 6:
            raise ProtocolError("invalid high-address write acknowledgement")
        returned_high = struct.unpack_from("<H", reply, 4)[0]
        if returned_high != high:
            raise ProtocolError("write acknowledgement address mismatch")


def validate_database(path: Path, start_address: int) -> bytes:
    data = path.read_bytes()
    if len(data) < DB_HEADER_SIZE + REGION_HEADER_SIZE:
        raise ValueError("database is shorter than the K5DB v3 headers")
    magic, version, entry_size, count, source_date, index_offset = struct.unpack_from(
        DB_HEADER_FORMAT, data, 0
    )
    if magic != DB_MAGIC:
        raise ValueError("database magic is not K5DB")
    if version != DB_VERSION or entry_size != DB_ENTRY_SIZE:
        raise ValueError(f"unsupported database format version={version}, entry_size={entry_size}")
    entries_end = DB_HEADER_SIZE + count * entry_size
    if index_offset < entries_end or index_offset + REGION_HEADER_SIZE > len(data):
        raise ValueError("invalid K5DB v3 region-index offset")

    (region_magic, region_version, province_size, city_size, province_count,
     city_count, payload_crc16, city_table_offset) = struct.unpack_from(
        REGION_HEADER_FORMAT, data, index_offset
    )
    if region_magic != REGION_MAGIC or region_version != 1:
        raise ValueError("invalid K5DB v3 region-index header")
    if province_size != 16 or city_size != 16 or not (34 <= province_count <= 35):
        raise ValueError("unsupported K5DB v3 region-index structure")
    minimum_city_offset = REGION_HEADER_SIZE + province_count * province_size
    if city_table_offset < minimum_city_offset:
        raise ValueError("invalid K5DB v3 city-table offset")
    expected_size = index_offset + city_table_offset + city_count * city_size
    if expected_size != len(data):
        raise ValueError(f"database size mismatch: index expects {expected_size}, file has {len(data)}")
    crc_payload = data[DB_HEADER_SIZE:index_offset] + data[index_offset + REGION_HEADER_SIZE:expected_size]
    if crc16_xmodem(crc_payload) != payload_crc16:
        raise ValueError("K5DB v3 payload CRC16 mismatch")

    end_address = start_address + len(data) - 1
    if start_address < EEPROM_START_ADDRESS or end_address > EEPROM_DATA_END_ADDRESS:
        raise ValueError(
            f"database range 0x{start_address:05X}~0x{end_address:05X} is outside "
            f"0x{EEPROM_START_ADDRESS:05X}~0x{EEPROM_DATA_END_ADDRESS:05X}"
        )
    print(
        f"Validated {path}: {count} analogue records, {city_count} cities, {len(data)} bytes, "
        f"source date {source_date or 'unknown'}, EEPROM 0x{start_address:05X}~0x{end_address:05X}"
    )
    return data


def validate_tail_blob(path: Path) -> bytes:
    data = path.read_bytes()
    if len(data) < TAIL_HEADER_SIZE:
        raise ValueError("tails.bin is shorter than its header")
    magic, version, segment_size, rll_count, rfg_count, rll_offset, rfg_offset, payload_crc = struct.unpack_from(
        TAIL_HEADER_FORMAT, data, 0
    )
    if magic != TAIL_MAGIC or version != 1 or segment_size != 7:
        raise ValueError("unsupported tail resource format")
    if not (1 <= rll_count <= 300 and rfg_count == 0):
        raise ValueError("invalid RLL-only segment count")
    if rll_offset != TAIL_HEADER_SIZE or rfg_offset != rll_offset + rll_count * segment_size:
        raise ValueError("invalid tail resource offsets")
    expected_size = rfg_offset + rfg_count * segment_size
    if expected_size != len(data):
        raise ValueError(f"tail resource size mismatch: expected {expected_size}, got {len(data)}")
    if crc16_xmodem(data[TAIL_HEADER_SIZE:]) != payload_crc:
        raise ValueError("tail resource CRC16 mismatch")
    end_address = TAILS_START_ADDRESS + len(data) - 1
    if end_address > EEPROM_DATA_END_ADDRESS:
        raise ValueError("tail resource exceeds expanded EEPROM data range")
    print(
        f"Validated {path}: RLL {rll_count} segments, "
        f"{len(data)} bytes, EEPROM 0x{TAILS_START_ADDRESS:05X}~0x{end_address:05X}"
    )
    return data


def split_blocks(data: bytes, start_address: int, chunk_size: int):
    offset = 0
    while offset < len(data):
        address = start_address + offset
        # Never cross a 64KB high-address bank in one command.
        bank_remaining = 0x10000 - (address & 0xFFFF)
        size = min(chunk_size, bank_remaining, len(data) - offset)
        yield address, data[offset : offset + size]
        offset += size


def first_mismatch(expected: bytes, actual: bytes) -> int | None:
    for index, (expected_byte, actual_byte) in enumerate(zip(expected, actual)):
        if expected_byte != actual_byte:
            return index
    if len(expected) != len(actual):
        return min(len(expected), len(actual))
    return None


def format_database_header(data: bytes) -> str:
    if len(data) < DB_HEADER_SIZE:
        return f"short header ({len(data)} bytes)"
    magic, version, entry_size, count, source_date, index_offset = struct.unpack_from(
        DB_HEADER_FORMAT, data, 0
    )
    return (
        f"magic={magic!r}, version={version}, entry_size={entry_size}, "
        f"count={count}, source_date={source_date}, index_offset=0x{index_offset:X}"
    )


def read_device_database(
    client: ExpandedEepromClient,
    expected: bytes,
    start_address: int,
    chunk_size: int,
) -> bytes:
    read_back = bytearray()
    for address, block in split_blocks(expected, start_address, chunk_size):
        read_back.extend(client.read(address, len(block)))
        percent = len(read_back) * 100 // len(expected)
        print(f"\rRead {percent:3d}%  0x{address:05X}", end="", flush=True)
    print()
    return bytes(read_back)


def parse_int(value: str) -> int:
    return int(value, 0)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("port", nargs="?", default="COM4")
    parser.add_argument("database", nargs="?", type=Path, default=Path("repeaters.bin"))
    parser.add_argument("--address", type=parse_int, default=EEPROM_START_ADDRESS)
    parser.add_argument("--baud", type=int, default=38400)
    parser.add_argument("--chunk-size", type=int, default=DEFAULT_CHUNK_SIZE)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--write", action="store_true", help="perform the EEPROM write with read-back verification")
    mode.add_argument(
        "--verify-device",
        action="store_true",
        help="read the device EEPROM and compare it with the local database without writing",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        data = validate_database(args.database, args.address)
        tails_path = Path("tails.bin")
        tails_data = validate_tail_blob(tails_path)
        if not 8 <= args.chunk_size <= 120:
            raise ValueError("chunk size must be between 8 and 120 bytes")
        if not args.write and not args.verify_device:
            print(
                "Validation-only mode. Add --verify-device for a read-only device comparison "
                "or --write for a verified EEPROM update."
            )
            return 0
        if serial is None:
            raise RuntimeError("pyserial is required: python -m pip install pyserial")

        timestamp = secrets.randbits(32)
        with serial.Serial(args.port, args.baud, timeout=2.0, write_timeout=2.0) as port:
            port.reset_input_buffer()
            port.reset_output_buffer()
            client = ExpandedEepromClient(port, timestamp)
            version = client.hello()
            print(f"Connected to firmware: {version}")

            if args.verify_device:
                for resource_path, expected, start_address in (
                    (args.database, data, args.address),
                    (tails_path, tails_data, TAILS_START_ADDRESS),
                ):
                    device_data = read_device_database(client, expected, start_address, args.chunk_size)
                    mismatch = first_mismatch(expected, device_data)
                    if mismatch is not None:
                        if resource_path == args.database:
                            print(f"Expected header: {format_database_header(expected)}", file=sys.stderr)
                            print(f"Device header:   {format_database_header(device_data)}", file=sys.stderr)
                        if mismatch < len(expected) and mismatch < len(device_data):
                            raise ProtocolError(
                                f"device mismatch at 0x{start_address + mismatch:05X}: "
                                f"expected 0x{expected[mismatch]:02X}, got 0x{device_data[mismatch]:02X}"
                            )
                        raise ProtocolError(
                            f"device length mismatch at 0x{start_address + mismatch:05X}: "
                            f"expected {len(expected)} bytes, got {len(device_data)}"
                        )
                    print(
                        f"Device EEPROM matches {resource_path} exactly: {len(expected)} bytes at "
                        f"0x{start_address:05X}~0x{start_address + len(expected) - 1:05X}."
                    )
                return 0

            written = 0
            resources = (
                (args.database, data, args.address),
                (tails_path, tails_data, TAILS_START_ADDRESS),
            )
            total_size = sum(len(resource) for _, resource, _ in resources)
            for resource_path, resource, start_address in resources:
                print(f"Writing {resource_path} at 0x{start_address:05X}")
                for address, block in split_blocks(resource, start_address, args.chunk_size):
                    client.write(address, block)
                    time.sleep(0.012)
                    read_back = client.read(address, len(block))
                    if read_back != block:
                        mismatch = next(
                            index for index, (expected, actual) in enumerate(zip(block, read_back)) if expected != actual
                        )
                        raise ProtocolError(
                            f"verification failed at 0x{address + mismatch:05X}: "
                            f"expected 0x{block[mismatch]:02X}, got 0x{read_back[mismatch]:02X}"
                        )
                    written += len(block)
                    percent = written * 100 // total_size
                    print(f"\rVerified {percent:3d}%  0x{address:05X}", end="", flush=True)
                print()

        print(f"EEPROM update verified: {written} bytes written and read back successfully.")
        return 0
    except (OSError, ValueError, RuntimeError, ProtocolError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
