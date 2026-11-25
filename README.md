# OpenWindows package catalog

This repository is the public index for OpenWindows packages. It contains package metadata and release links only; no Windows Server source tree or OS images belong here.

## Package format

Packages use the `.opw` extension. The first format is a Microsoft Cabinet archive that can be read by Windows Server 2003 SetupAPI. Each archive contains `openwindows-package.ini`, a payload tree, and a SHA-256 index. Release packages must be signed; `wpk` must reject invalid signatures, mismatched hashes, path traversal, and architecture/API mismatches.

```ini
[Package]
Id=example-de
Name=Example Desktop
Version=1.0.0
Architecture=amd64
ApiLevel=1
Type=DesktopEnvironment
Shell=bin\example-shell.exe

[Hashes]
bin\example-shell.exe=<sha256>
```

Native applications use `Type=Application` and an `Executable` entry instead:

```ini
[Package]
Id=example-app
Name=Example App
Version=1.0.0
Architecture=amd64
ApiLevel=1
Type=Application
Executable=bin\example.exe

[Hashes]
bin\example.exe=<sha256>
```

The `.opw` file is a signed Microsoft Cabinet archive containing this manifest and `payload\` files. The executables inside remain ordinary `.exe`/`.dll` files. Current `wpk` commands are `install <file.opw> [--system]`, `list`, `run <application-id>`, `remove <package-id> [--system]`, and `set-de <environment-id>`. Installs are per-user by default; `--system` requests a machine-wide install and requires an administrator token. Removal targets only the registered package directory and refuses to remove the active/default desktop environment.

## Catalog format

The package index lives in [`index.json`](index.json) and is governed by [`index.schema.json`](index.schema.json) (JSON Schema Draft 2020-12):

- `schemaVersion`: integer `1`
- `packages`: array of package release entries, each requiring:
  - `id`: package identifier matching `^[A-Za-z0-9_-]+$`
  - `version`: non-empty version string without whitespace
  - `architecture`: `"amd64"` or `"x86"`
  - `apiLevel`: integer `>= 1`
  - `release`: HTTP/HTTPS URI to the signed `.opw` release asset
  - `sha256`: 64-character hexadecimal SHA-256 digest
  - `signature`: HTTP/HTTPS URI to the detached signature

Duplicate `(id, version, architecture)` entries and identical `release`/`signature` URIs are rejected during validation.

## Validation

Run the catalog validator and unit tests locally with Python 3:

```sh
python3 scripts/validate_index.py
python3 -m unittest discover -s tests -v
```

To also enforce JSON Schema Draft 2020-12 meta-schema validation via `jsonschema` (matching [`.github/workflows/validate.yml`](.github/workflows/validate.yml)):

```sh
uvx --from jsonschema python scripts/validate_index.py --require-jsonschema
uvx --from pytest --with jsonschema pytest -v
```

## Status and listing policy

The catalog index is currently empty. Package-ID downloads, upgrades, and pinned project-publisher keys are not implemented yet. No package is listed until its source, license, AMD64 build, hash manifest, signature, and runtime behavior have been reviewed.
