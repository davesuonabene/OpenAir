# OpenAir Development & Setup Guide

This guide describes how to develop, test, and release OpenAir Max for Live devices on macOS and Windows without breaking cross-platform compatibility.

---

## Architecture Overview

* **`airfx`** (C++ DSP Engine & Externals Repository): A fork of Airwindows for Max containing native Min-API C++ DSP code. Builds Universal binaries (`.mxo`) on macOS and 64-bit DLLs (`.mxe64`) on Windows. All compiled externals live exclusively in `airfx/externals/`.
* **`OpenAir`** (M4L Devices & Packaging Toolchain): Native Max for Live devices (`m4lplugins/*.amxd`) designed for Ableton Live. Kept unfrozen as lightweight JSON patchers during development. The release builder automatically freezes devices with externals from `airfx` into standalone distribution packages.

---

## 1. Setup on macOS

### Prerequisites
* Ableton Live 11 or 12 Suite (with Max for Live)
* Xcode Command Line Tools (`xcode-select --install`)
* Python 3.9+
* CMake (`brew install cmake`)

### Link Repositories as Max Packages
Run in Terminal:
```bash
mkdir -p "$HOME/Documents/Max 9/Packages"
ln -sfn "$PWD" "$HOME/Documents/Max 9/Packages/OpenAir"
ln -sfn "$PWD/../airfx" "$HOME/Documents/Max 9/Packages/airfx"
```

*(Note: Do not place loose externals in `~/Documents/Max 9/Library/airfx_v3`. The Max Packages folder handles all search paths cleanly without collisions).*

---

## 2. Setup on Windows (For your Windows Dev Machine)

### Prerequisites
* Windows 10/11 64-bit
* Ableton Live 11 or 12 Suite (with Max for Live)
* Visual Studio 2022 Community (with "Desktop development with C++")
* CMake for Windows
* Python 3.10+ (ensure "Add Python to PATH" is checked during installation)
* Git for Windows

### Clone Both Repositories Side-by-Side
```cmd
cd %USERPROFILE%\Documents\GitHub
git clone https://github.com/davesuonabene/airfx.git
git clone https://github.com/davesuonabene/OpenAir.git
```

### Link Repositories as Max Packages (Windows)
Open **Command Prompt as Administrator** (or enable Developer Mode in Windows Settings):
```cmd
mkdir "%USERPROFILE%\Documents\Max 9\Packages"
mklink /D "%USERPROFILE%\Documents\Max 9\Packages\OpenAir" "%USERPROFILE%\Documents\GitHub\OpenAir"
mklink /D "%USERPROFILE%\Documents\Max 9\Packages\airfx" "%USERPROFILE%\Documents\GitHub\airfx"
```

### Build Windows Externals (in airfx when modifying C++)
```cmd
cd %USERPROFILE%\Documents\GitHub\airfx
mkdir build_win
cd build_win
cmake .. -G "Visual Studio 17 2022" -A x64
cmake --build . --config Release
```
Compiled `.mxe64` files are output directly to `airfx/externals/` and are immediately discovered by Ableton Live via the `Packages/airfx` link.

---

## 3. Daily Workflow: Editing M4L Devices

1. **Open Ableton Live**.
2. Drag any device from `m4lplugins/` onto an audio track.
3. Click the **Edit** button in the device title bar to open the Max editor.
4. Customize dials, visual presentation, parameters, and routing.
5. Save in Max (`Cmd+S` on Mac, `Ctrl+S` on Windows).
6. **Important**: **Do NOT click "Freeze" in the Max UI**. Devices stay unfrozen during development so Ableton loads directly from your package folder without extracting cached files.

---

## 4. Release Toolchain Commands

All packaging, testing, and verification tasks are managed through `tools/cli.py`:

### Inspect Workspace & Dependencies
Checks all 10 production devices and verifies that both Windows `.mxe64` and Mac `.mxo` externals are present in `airfx/externals/`:
```bash
python tools/cli.py inspect
```

### Unfreeze Devices for Development
Converts devices to lightweight pure JSON format (~20-60KB) for rapid editing:
```bash
python tools/cli.py unfreeze --all
```

### Freeze Devices for Standalone Testing
Packages devices into self-contained collective format with both Mac and Windows binaries embedded, setting correct MS-DOS attributes:
```bash
python tools/cli.py freeze --all
```

### Build & Verify Release Package
Creates `release/OpenAir_vX.Y.Z.zip` (auto-freezing all devices from `airfx/externals/`), generates SHA256 checksum, and verifies binary signatures:
```bash
python tools/cli.py build --version 0.1.0
python tools/cli.py verify
```

---

## 5. Publishing Checklist

When you are ready to publish a release:
1. `python tools/cli.py inspect` (verify all 10 devices pass).
2. `python tools/cli.py build --version <VERSION>` (produces release zip).
3. `python tools/cli.py verify release/OpenAir_v<VERSION>.zip` (confirms clean headers).
4. `git tag -a v<VERSION> -m "Release <VERSION>"`
5. `git push origin main --tags`
6. Create a release on GitHub and upload the release `.zip` and `.sha256` files.
