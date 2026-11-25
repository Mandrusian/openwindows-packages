#!/usr/bin/env python3
"""Validate the OpenWindows package catalog against its JSON Schema."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INDEX_PATH = REPO_ROOT / "index.json"
DEFAULT_SCHEMA_PATH = REPO_ROOT / "index.schema.json"

TOP_LEVEL_KEYS = frozenset({"schemaVersion", "packages"})
PACKAGE_KEYS = frozenset(
    {
        "id",
        "version",
        "architecture",
        "apiLevel",
        "release",
        "sha256",
        "signature",
    }
)
VALID_ARCHITECTURES = frozenset({"amd64", "x86"})
VALID_URI_SCHEMES = frozenset({"https", "http"})

ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")
VERSION_PATTERN = re.compile(r"^\S+$")
SHA256_PATTERN = re.compile(r"^[A-Fa-f0-9]{64}$")


def _is_exact_int(value: object) -> bool:
    """Return True for integers, excluding booleans."""
    return isinstance(value, int) and not isinstance(value, bool)


def _is_valid_http_uri(value: object) -> bool:
    """Return True when value is a whitespace-free HTTP or HTTPS URI with a host."""
    if not isinstance(value, str) or not value or any(ch.isspace() for ch in value):
        return False
    parsed = urlsplit(value)
    return parsed.scheme.lower() in VALID_URI_SCHEMES and bool(parsed.netloc)


def _load_json(path: Path) -> Any:
    """Load a UTF-8 JSON file and return the decoded value."""
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _validate_with_jsonschema(
    index_data: object,
    schema_data: object,
    *,
    require_jsonschema: bool,
) -> list[str]:
    """Validate schema and index using jsonschema Draft 2020-12 when installed."""
    try:
        from jsonschema import Draft202012Validator, FormatChecker
        from jsonschema.exceptions import SchemaError
    except ImportError:
        if require_jsonschema:
            return ["jsonschema package is required but not installed"]
        return []

    try:
        Draft202012Validator.check_schema(schema_data)
    except SchemaError as exc:
        return [f"invalid JSON schema: {exc.message}"]

    format_checker = FormatChecker()

    @format_checker.checks("uri")
    def _check_uri(value: object) -> bool:
        return _is_valid_http_uri(value)

    validator = Draft202012Validator(schema_data, format_checker=format_checker)
    errors = sorted(validator.iter_errors(index_data), key=lambda err: list(err.path))
    formatted: list[str] = []
    for err in errors:
        location = ".".join(str(part) for part in err.path) or "<root>"
        formatted.append(f"schema error at {location}: {err.message}")
    return formatted


def _validate_package_entry(entry: object, index: int) -> list[str]:
    """Validate a single entry in the packages array."""
    prefix = f"packages[{index}]"
    if not isinstance(entry, dict):
        return [f"{prefix}: expected an object"]

    errors: list[str] = []
    keys = set(entry.keys())
    missing = sorted(PACKAGE_KEYS - keys)
    extra = sorted(keys - PACKAGE_KEYS)
    if missing:
        errors.append(f"{prefix}: missing required keys: {', '.join(missing)}")
    if extra:
        errors.append(f"{prefix}: unexpected keys: {', '.join(extra)}")

    pkg_id = entry.get("id")
    if "id" in entry and (
        not isinstance(pkg_id, str) or not ID_PATTERN.fullmatch(pkg_id)
    ):
        errors.append(
            f"{prefix}.id: must be a non-empty string matching ^[A-Za-z0-9_-]+$"
        )

    version = entry.get("version")
    if "version" in entry and (
        not isinstance(version, str) or not VERSION_PATTERN.fullmatch(version)
    ):
        errors.append(
            f"{prefix}.version: must be a non-empty string without whitespace"
        )

    arch = entry.get("architecture")
    if "architecture" in entry and (
        not isinstance(arch, str) or arch not in VALID_ARCHITECTURES
    ):
        errors.append(
            f"{prefix}.architecture: must be one of {sorted(VALID_ARCHITECTURES)}"
        )

    api_level = entry.get("apiLevel")
    if "apiLevel" in entry and (not _is_exact_int(api_level) or api_level < 1):
        errors.append(f"{prefix}.apiLevel: must be an integer >= 1")

    sha256 = entry.get("sha256")
    if "sha256" in entry and (
        not isinstance(sha256, str) or not SHA256_PATTERN.fullmatch(sha256)
    ):
        errors.append(f"{prefix}.sha256: must be a 64-character hexadecimal SHA-256")

    for field in ("release", "signature"):
        if field in entry and not _is_valid_http_uri(entry.get(field)):
            errors.append(
                f"{prefix}.{field}: must be a valid HTTP/HTTPS URI without whitespace"
            )

    if (
        isinstance(entry.get("release"), str)
        and isinstance(entry.get("signature"), str)
        and entry["release"] == entry["signature"]
    ):
        errors.append(f"{prefix}: release and signature URIs must not be identical")

    return errors


def validate_catalog(
    index_data: object,
    schema_data: object,
    *,
    require_jsonschema: bool = False,
) -> list[str]:
    """Validate decoded index data and schema data, returning a list of errors."""
    if not isinstance(schema_data, dict):
        return ["schema root must be a JSON object"]

    errors = _validate_with_jsonschema(
        index_data,
        schema_data,
        require_jsonschema=require_jsonschema,
    )

    if not isinstance(index_data, dict):
        errors.append("index root must be a JSON object")
        return errors

    keys = set(index_data.keys())
    missing = sorted(TOP_LEVEL_KEYS - keys)
    extra = sorted(keys - TOP_LEVEL_KEYS)
    if missing:
        errors.append(f"<root>: missing required keys: {', '.join(missing)}")
    if extra:
        errors.append(f"<root>: unexpected keys: {', '.join(extra)}")

    schema_version = index_data.get("schemaVersion")
    if "schemaVersion" in index_data and (
        not _is_exact_int(schema_version) or schema_version != 1
    ):
        errors.append("<root>.schemaVersion: must be integer 1")

    packages = index_data.get("packages")
    if "packages" in index_data:
        if not isinstance(packages, list):
            errors.append("<root>.packages: must be an array")
        else:
            seen_releases: set[tuple[str, str, str]] = set()
            for idx, entry in enumerate(packages):
                errors.extend(_validate_package_entry(entry, idx))
                if isinstance(entry, dict):
                    pkg_id = entry.get("id")
                    version = entry.get("version")
                    arch = entry.get("architecture")
                    if (
                        isinstance(pkg_id, str)
                        and isinstance(version, str)
                        and isinstance(arch, str)
                    ):
                        key = (pkg_id, version, arch)
                        if key in seen_releases:
                            errors.append(
                                f"packages[{idx}]: duplicate package release "
                                f"({pkg_id}, {version}, {arch})"
                            )
                        seen_releases.add(key)

    # Preserve order while deduplicating identical messages from jsonschema + direct checks.
    return list(dict.fromkeys(errors))


def validate_files(
    index_path: Path = DEFAULT_INDEX_PATH,
    schema_path: Path = DEFAULT_SCHEMA_PATH,
    *,
    require_jsonschema: bool = False,
) -> list[str]:
    """Load index and schema JSON files and validate them."""
    try:
        schema_data = _load_json(schema_path)
    except (OSError, json.JSONDecodeError) as exc:
        return [f"failed to load schema {schema_path}: {exc}"]

    try:
        index_data = _load_json(index_path)
    except (OSError, json.JSONDecodeError) as exc:
        return [f"failed to load index {index_path}: {exc}"]

    return validate_catalog(
        index_data,
        schema_data,
        require_jsonschema=require_jsonschema,
    )


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for catalog validation."""
    parser = argparse.ArgumentParser(
        description="Validate an OpenWindows package catalog against its JSON Schema.",
    )
    parser.add_argument(
        "--index",
        type=Path,
        default=DEFAULT_INDEX_PATH,
        help=f"Path to catalog JSON file (default: {DEFAULT_INDEX_PATH.name})",
    )
    parser.add_argument(
        "--schema",
        type=Path,
        default=DEFAULT_SCHEMA_PATH,
        help=f"Path to JSON Schema file (default: {DEFAULT_SCHEMA_PATH.name})",
    )
    parser.add_argument(
        "--require-jsonschema",
        action="store_true",
        help="Fail if the third-party jsonschema package is not installed.",
    )
    args = parser.parse_args(argv)

    errors = validate_files(
        args.index,
        args.schema,
        require_jsonschema=args.require_jsonschema,
    )
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(f"OK: {args.index} is valid against {args.schema}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
