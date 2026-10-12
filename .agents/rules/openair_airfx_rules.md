# OpenAir & airfx Repository Architecture and Workflow Rules

This document defines the persistent architectural memory, development rules, and release protocols for the `OpenAir` and `airfx` toolchain.

---

## 1. Two-Tier Repository Architecture

1. **`airfx` (C++ DSP Engine & Single Source of Truth for Externals)**:
   - Contains Min-API + Airwindows C++ DSP sources in `source/airwindohhs/include/`.
   - Stores all compiled cross-platform Max externals exclusively in `externals/`:
     - macOS: Universal Binary bundles (`.mxo`) supporting `arm64` and `x86_64`.
     - Windows: PE32+ 64-bit DLLs (`.mxe64`).
   - Maintained as an independent directory (`../airfx`) on disk.
   - Built via CMake (`build_mac` on macOS, `build_win` on Windows).
   - Linked to Max as `Packages/airfx` so Max and Ableton Live resolve externals dynamically during development.
   - Can be released independently as an official Cycling '74 Max Package for Max developers.

2. **`OpenAir` (M4L Device Suite & Packaging Toolchain)**:
   - Contains pure native Ableton Live Max for Live audio devices in `m4lplugins/*.amxd`.
   - Devices remain **unfrozen lightweight JSON patchers** during development (~20-60KB).
   - Does NOT store redundant compiled externals in git.
   - Release toolchain (`tools/cli.py build`) sources externals directly from `../airfx/externals/`, auto-freezes devices into standalone cross-platform AMXDs, and bundles the official release package.

---

## 2. Core Operational Rules

### Rule 1: Never Manually Freeze Devices During Development
- **Do NOT click "Freeze" in the Max editor GUI during daily development**.
- In Max for Live, GUI freezing bakes binary snapshots into collective containers (`ampf`), causing Ableton Live to extract cached files to `temp64-live/mxt`. Stale cache extractions cause directory collisions (`error -1 making directory`), lock contention, and shadow real external updates.
- Keep devices in `m4lplugins/` in standard unfrozen development format. Ableton Live loads externals dynamically from the symlinked `Packages/airfx`.
- When building releases, `python tools/cli.py build` automatically constructs mathematically compliant Max collective containers with explicit MS-DOS directory (`0x10`) and file (`0x20`) attributes directly into the release package.

### Rule 2: Max Package Symlinks for Local Development
- Both repositories must be symlinked into the official Max Packages directory:
  - **macOS**:
    ```bash
    ln -sfn "/Users/dave/Documents/GitHub/OpenAir" "$HOME/Documents/Max 9/Packages/OpenAir"
    ln -sfn "/Users/dave/Documents/GitHub/airfx" "$HOME/Documents/Max 9/Packages/airfx"
    ```
  - **Windows (Command Prompt as Admin or Developer Mode)**:
    ```cmd
    mklink /D "%USERPROFILE%\Documents\Max 9\Packages\OpenAir" "C:\path\to\OpenAir"
    mklink /D "%USERPROFILE%\Documents\Max 9\Packages\airfx" "C:\path\to\airfx"
    ```
- Do **not** dump loose externals into `~/Documents/Max 9/Library/`. Having loose binaries in `Library/` shadows package binaries and produces duplicate search path warnings.

### Rule 3: Single Source of Truth for Externals
- Compiled externals (`.mxo` and `.mxe64`) are managed **exclusively in `airfx/externals/`**.
- Do not create a duplicate `externals/` folder in `OpenAir`.
- macOS builds update `.mxo` bundles in `airfx/externals/`.
- Windows builds update `.mxe64` files in `airfx/externals/`.
- All Windows `.mxe64` binaries in `airfx/externals/` must remain preserved when developing on macOS.

---

## 3. Toolchain CLI Commands

Always use `tools/cli.py` for repository operations:

```bash
# 1. Inspect devices, mapping, and external availability in airfx
python tools/cli.py inspect

# 2. Unfreeze devices for lightweight development (if previously frozen)
python tools/cli.py unfreeze --all
python tools/cli.py unfreeze --device OA_galactic.amxd

# 3. Freeze devices for standalone M4L testing
python tools/cli.py freeze --all
python tools/cli.py freeze --device OA_galactic.amxd

# 4. Build official release ZIP package + SHA256 checksum
# (Automatically freezes devices from airfx/externals and packages the release)
python tools/cli.py build [--version 0.1.0]

# 5. Verify release package integrity and cross-platform headers
python tools/cli.py verify [release/OpenAir_v0.1.0.zip]
```

---

## 4. Collective Binary Specification Reference

When constructing frozen Max collectives (`ampf`):
1. **Container**:
   - `ampf` chunk (len 4, `aaaa`)
   - `meta` chunk (len 4, `\x07\x00\x00\x00`)
   - `ptch` chunk (little-endian length of `mx@c` payload)
2. **`mx@c` Payload**:
   - 16-byte header: `b'mx@c\x00\x00\x00\x10\x00\x00\x00\x00' + struct.pack('>I', dlst_offset)`
   - JSON patcher data (offset 16, 4-byte padded)
   - Windows `.mxe64` binary (4-byte padded)
   - `iLaX` header (`\x00\x00\x00\x00`)
   - Zip of `.mxo` bundle:
     - `create_system = 10` (Windows NT / MS-DOS)
     - `external_attr = 0x10` for directory entries (CRITICAL: prevents `error -1 making directory`)
     - `external_attr = 0x20` for file entries
   - Raw Mach-O executable binary
   - Raw `Info.plist`
   - `dlst` directory table containing matching `dire` entries: `JSON`, `mx64`, `iLaX`, `zipfile`, `executable`, `plist`.
