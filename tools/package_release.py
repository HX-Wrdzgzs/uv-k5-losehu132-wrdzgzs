#!/usr/bin/env python3
"""Create a reproducible public or personal UV-K5 release package.

The two releases differ in the firmware image itself.  The public image keeps
the Roger/tail menu entry but falls back to the normal Roger tone.  The
personal image embeds the single-tone frequency, gain, and silence sequence
generated from ``1.wav`` at build time.  No external ``tails.bin`` file is
used or copied by either package.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from pathlib import Path


DATA_FILES = (
    "repeaters.bin",
    "repeaters.build.json",
)
FIRMWARE_FILES = ("firmware.bin", "firmware.packed.bin")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("."))
    parser.add_argument(
        "--firmware-dir",
        type=Path,
        help="directory containing the already-built firmware.bin files; defaults to --source",
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--version", default="local")
    parser.add_argument(
        "--include-tails",
        action="store_true",
        help="label this package as the personal firmware variant with the embedded 1.wav whistle",
    )
    return parser.parse_args()


def ensure_output_is_external(source: Path, output: Path) -> None:
    source_resolved = source.resolve()
    output_resolved = output.resolve()
    same_tree = False
    if source_resolved.drive.lower() == output_resolved.drive.lower():
        try:
            same_tree = os.path.commonpath((str(source_resolved), str(output_resolved))) == str(source_resolved)
        except ValueError:
            same_tree = False
    if output_resolved == source_resolved or same_tree:
        raise ValueError("release output must be outside the source directory")
    if output_resolved.exists():
        existing = list(output_resolved.iterdir())
        if existing:
            raise FileExistsError(
                f"release output is not empty: {output_resolved}; choose a new directory"
            )


def build_package(
    source: Path,
    output: Path,
    version: str,
    include_tails: bool,
    firmware_source: Path | None = None,
) -> dict:
    ensure_output_is_external(source, output)
    output.mkdir(parents=True, exist_ok=True)

    firmware_source = (firmware_source or source).resolve()
    variant = "tail" if include_tails else "public"
    selected = list(DATA_FILES)

    files = []
    for name in selected:
        source_path = source / name
        if not source_path.is_file():
            if name in ("firmware.stable.bin", "firmware.stable.packed.bin"):
                # Stable variants are optional for a freshly-built local tree.
                continue
            raise FileNotFoundError(f"required release file is missing: {source_path}")
        target = output / name
        shutil.copy2(source_path, target)
        files.append({"name": name, "size": target.stat().st_size, "sha256": sha256(target)})

    for firmware_name in FIRMWARE_FILES:
        firmware_path = firmware_source / firmware_name
        if not firmware_path.is_file():
            raise FileNotFoundError(f"required firmware file is missing: {firmware_path}")
        output_name = f"{version}-{variant}" + firmware_name.removeprefix("firmware")
        target = output / output_name
        shutil.copy2(firmware_path, target)
        files.append({"name": output_name, "size": target.stat().st_size, "sha256": sha256(target)})

    manifest = {
        "schema": 1,
        "version": version,
        "package_kind": "personal" if include_tails else "public",
        "firmware_variant": variant,
        "tail_firmware_included": include_tails,
        "tail_resource_included": False,
        "tail_entry_point": (
            "embedded 1.wav single-tone/gain/silence sequence"
            if include_tails
            else "menu entry retained; normal Roger tone fallback"
        ),
        "files": files,
    }
    (output / "release-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (output / "SHA256SUMS.txt").write_text(
        "".join(f"{item['sha256']}  {item['name']}\n" for item in files), encoding="utf-8"
    )
    return manifest


def main() -> int:
    args = parse_args()
    source = args.source.resolve()
    output = args.output.resolve()
    firmware_source = args.firmware_dir.resolve() if args.firmware_dir else source
    manifest = build_package(source, output, args.version, args.include_tails, firmware_source)
    print(
        f"Created {manifest['package_kind']} release {manifest['version']}: "
        f"{len(manifest['files'])} files -> {output}"
    )
    print(f"Tail resources included: {'yes' if manifest['tail_resource_included'] else 'no'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
