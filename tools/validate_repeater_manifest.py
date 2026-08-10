#!/usr/bin/env python3
"""Validate that the built K5DB manifest contains analogue FM records only."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

DIGITAL_TOKENS = ("DMR", "C4FM", "D-STAR", "DSTAR", "P25", "NXDN", "YSF")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", nargs="?", type=Path, default=Path("repeaters.build.json"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        payload = json.loads(args.manifest.read_text(encoding="utf-8"))
        if payload.get("format", {}).get("version") != 3:
            raise ValueError("manifest is not K5DB v3")
        records = payload.get("records")
        if not isinstance(records, list) or not records:
            raise ValueError("manifest has no records")

        errors: list[str] = []
        for index, record in enumerate(records, start=1):
            mode = str(record.get("mode") or "").upper().strip()
            if mode != "FM" or any(token in mode for token in DIGITAL_TOKENS):
                errors.append(f"record #{index} {record.get('callsign', '')}: mode={mode!r}")
            priority = record.get("source_priority")
            if priority not in (0, 1, 2, 3):
                errors.append(
                    f"record #{index} {record.get('callsign', '')}: source_priority={priority!r}"
                )
            exact_source = record.get("source_id")
            if not isinstance(exact_source, int) or not 0 <= exact_source <= 6:
                errors.append(
                    f"record #{index} {record.get('callsign', '')}: source_id={exact_source!r}"
                )
            if not str(record.get("province") or "").strip() or not str(record.get("city") or "").strip():
                errors.append(f"record #{index} {record.get('callsign', '')}: missing province/city")

        if errors:
            raise ValueError("manifest validation failed:\n  - " + "\n  - ".join(errors))

        print(
            f"Validated {args.manifest}: {len(records)} analogue-FM records, "
            f"0 digital-only records, {payload.get('city_count', 0)} cities"
        )
        return 0
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
