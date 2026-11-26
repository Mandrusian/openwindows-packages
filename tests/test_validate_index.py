"""Unit tests for OpenWindows package catalog validation."""

from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import validate_index


def _make_package(**overrides: object) -> dict[str, object]:
    """Return a valid package entry with optional field overrides."""
    entry: dict[str, object] = {
        "id": "example-app",
        "version": "1.0.0",
        "architecture": "amd64",
        "apiLevel": 1,
        "release": "https://example.com/releases/example-app-1.0.0-amd64.opw",
        "sha256": "a" * 64,
        "signature": "https://example.com/releases/example-app-1.0.0-amd64.opw.sig",
    }
    entry.update(overrides)
    return entry


class ValidateIndexTests(unittest.TestCase):
    """Tests for catalog schema and semantic validation."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.schema = json.loads(
            (REPO_ROOT / "index.schema.json").read_text(encoding="utf-8")
        )

    def test_repo_catalog_is_valid(self) -> None:
        errors = validate_index.validate_files(
            REPO_ROOT / "index.json",
            REPO_ROOT / "index.schema.json",
        )
        self.assertEqual(errors, [])

    def test_valid_populated_catalog_passes(self) -> None:
        catalog = {
            "schemaVersion": 1,
            "packages": [
                _make_package(id="example-de", architecture="amd64"),
                _make_package(
                    id="example-de",
                    architecture="x86",
                    release="https://example.com/releases/example-de-1.0.0-x86.opw",
                    signature="https://example.com/releases/example-de-1.0.0-x86.opw.sig",
                ),
            ],
        }
        self.assertEqual(validate_index.validate_catalog(catalog, self.schema), [])

    def test_rejects_invalid_top_level_shapes(self) -> None:
        bad_cases: list[object] = [
            [],
            {},
            {"schemaVersion": 2, "packages": []},
            {"schemaVersion": True, "packages": []},
            {"schemaVersion": 1.0, "packages": []},
            {"schemaVersion": 1, "packages": [], "extra": 1},
            {"schemaVersion": 1, "packages": {}},
        ]
        for bad in bad_cases:
            with self.subTest(bad=bad):
                errors = validate_index.validate_catalog(bad, self.schema)
                self.assertTrue(errors)

    def test_rejects_invalid_package_fields(self) -> None:
        bad_packages: list[object] = [
            "not-an-object",
            _make_package(id="invalid.id"),
            _make_package(id=""),
            _make_package(version=""),
            _make_package(version="1.0.0 beta"),
            _make_package(architecture="arm64"),
            _make_package(apiLevel=0),
            _make_package(apiLevel=True),
            _make_package(apiLevel="1"),
            _make_package(sha256="a" * 63),
            _make_package(sha256="z" * 64),
            _make_package(release="ftp://example.com/pkg.opw"),
            _make_package(release="/relative/path.opw"),
            _make_package(signature="https://example.com/pkg.opw with spaces"),
            _make_package(
                release="https://example.com/same.opw",
                signature="https://example.com/same.opw",
            ),
            _make_package(extraField="nope"),
        ]
        for pkg in bad_packages:
            with self.subTest(pkg=pkg):
                catalog = {"schemaVersion": 1, "packages": [pkg]}
                errors = validate_index.validate_catalog(catalog, self.schema)
                self.assertTrue(errors)

        missing_required = copy.deepcopy(_make_package())
        del missing_required["signature"]
        errors = validate_index.validate_catalog(
            {"schemaVersion": 1, "packages": [missing_required]},
            self.schema,
        )
        self.assertTrue(errors)

    def test_rejects_duplicate_package_release(self) -> None:
        catalog = {
            "schemaVersion": 1,
            "packages": [
                _make_package(id="dup-app", version="1.0.0", architecture="amd64"),
                _make_package(
                    id="dup-app",
                    version="1.0.0",
                    architecture="amd64",
                    sha256="b" * 64,
                ),
            ],
        }
        errors = validate_index.validate_catalog(catalog, self.schema)
        self.assertTrue(any("duplicate package release" in err for err in errors))

    def test_cli_exit_codes(self) -> None:
        self.assertEqual(
            validate_index.main(
                [
                    "--index",
                    str(REPO_ROOT / "index.json"),
                    "--schema",
                    str(REPO_ROOT / "index.schema.json"),
                ]
            ),
            0,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            bad_file = Path(tmpdir) / "bad.json"
            bad_file.write_text("{not json", encoding="utf-8")
            self.assertEqual(
                validate_index.main(
                    [
                        "--index",
                        str(bad_file),
                        "--schema",
                        str(REPO_ROOT / "index.schema.json"),
                    ]
                ),
                1,
            )


if __name__ == "__main__":
    unittest.main()
