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

The `.opw` file is a signed Microsoft Cabinet archive containing this manifest and `payload\` files. The executables inside remain ordinary `.exe`/`.dll` files. Current `wpk` commands are `install <file.opw> [--system]`, `list`, `run <application-id>`, and `set-de <environment-id>`. Installs are per-user by default; `--system` requests a machine-wide install and requires an administrator token.

The catalog index is currently empty. Package-ID downloads, uninstall, upgrades, and pinned project-publisher keys are not implemented yet. No package is listed until its source, license, AMD64 build, hash manifest, signature, and runtime behavior have been reviewed.

No package is listed until its source, license, AMD64 build, hash manifest, and runtime behavior have been reviewed.

