#!/usr/bin/env python3
"""Check that a public UV-K5 release contains no private tail resources."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

ALLOWED_FILES = {
    # Legacy public packages used generic firmware filenames.
    "firmware.bin",
    "firmware.packed.bin",
    "firmware.stable.bin",
    "firmware.stable.packed.bin",
    "repeaters.bin",
    "repeaters.stable.bin",
    "repeaters_manifest.json",
    "repeaters.build.json",
    "manifest.json",
    "sha256sums.txt",
    "release-manifest.json",
    "SHA256SUMS.txt",
}
FORBIDDEN_NAMES = {"tails.bin", "tails.stable.bin", "1.wav"}
PUBLIC_FIRMWARE_NAME = re.compile(r"^.+-public(?:\.packed)?\.bin$")


def is_allowed_file(name: str) -> bool:
    return name in ALLOWED_FILES or bool(PUBLIC_FIRMWARE_NAME.fullmatch(Path(name).name))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", type=Path, help="public package directory")
    return parser.parse_args()


def main() -> int:
    package = parse_args().package
    if not package.is_dir():
        raise SystemExit(f"package directory does not exist: {package}")

    files = sorted(path.relative_to(package).as_posix() for path in package.rglob("*") if path.is_file())
    forbidden = [name for name in files if Path(name).name in FORBIDDEN_NAMES or "tail" in Path(name).name.lower()]
    unexpected = [name for name in files if not is_allowed_file(name)]
    if forbidden:
        raise SystemExit(f"private tail resource found: {', '.join(forbidden)}")
    if unexpected:
        raise SystemExit(f"unexpected public-release file: {', '.join(unexpected)}")

    manifest_paths = [path for path in (package / "manifest.json", package / "release-manifest.json") if path.exists()]
    for manifest_path in manifest_paths:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        entries = manifest.get("files", manifest.get("artifacts", []))
        if isinstance(entries, dict):
            entries = [{"name": name, **value} for name, value in entries.items()]
        for entry in entries:
            name = entry.get("name")
            if not name or name not in files:
                raise SystemExit(f"manifest references missing file: {name}")
            expected = entry.get("sha256")
            if expected and sha256(package / name) != expected:
                raise SystemExit(f"sha256 mismatch: {name}")

    print(json.dumps({"package": str(package), "files": files, "private_tail_resources": False}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
