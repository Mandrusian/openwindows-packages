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

[Files]
bin\example-shell.exe=<sha256>
```

`wpk install <package-id>` resolves an entry from `index.json`. `wpk install C:\path\package.opw` installs a downloaded package file. A normal install is per-user; `sudo wpk install ...` requests a machine-wide install.

No package is listed until its source, license, AMD64 build, hash manifest, and runtime behavior have been reviewed.

