# OpenAir Project Architecture & Conventions

## Overview
OpenAir brings bare-metal C++ DSP ports of Airwindows audio algorithms into Ableton Live as native Max for Live (M4L) devices with custom GUIs, parameter mappings, and metering.

- **Author / Brand**: `macchinette`
- **Current Version**: `0.0.1` (pre-release)
- **License**: MIT / Open Source (Airwindows algorithms by Chris Johnson)

## Repository Directory Roles
- `externals/`:
  - Contains compiled binary externals for both platforms:
    - **Windows**: `airfx.<name>~.mxe64` (PE32+ 64-bit DLL)
    - **macOS**: `airfx.<name>~.mxo` (Universal Mach-O bundle containing `x86_64` and `arm64`)
  - 401 Airwindows algorithms exist in this folder.
  - **Rule**: Do not delete or rename existing externals. These serve as the master pool.
- `m4lplugins/`:
  - Active development workspace for `.amxd` Max for Live devices.
  - Files here are authored/maintained by the user.
  - **Rule**: Do not delete or move files out of `m4lplugins/`. Keep original `.amxd` files intact.
- `patchers/`:
  - Standard Max package directory for patchers. In the repository working tree, this directory is left clean. The release toolchain (`tools/`) maps devices from `m4lplugins/` into `patchers/` inside the distribution `.zip`.
- `docs/`:
  - Max reference pages (`.maxref.xml`) and help files (`.maxhelp`) providing documentation for Max and M4L.
- `release/`:
  - Target destination directory for all automatically built distribution `.zip` files.
- `tools/`:
  - Reusable Python toolchain for inspecting `.amxd` dependencies, assembling cross-platform release archives, and verifying archive integrity.
- `.agents/`:
  - Agent customizations, skills, and architectural rules.

## Packaging & Distribution Conventions
1. **Standard Max Package Structure**:
   All release archives must unpack as a self-contained Max Package folder named `OpenAir/`:
   ```
   OpenAir/
   ├── package-info.json
   ├── README.md
   ├── docs/
   ├── externals/
   └── patchers/
   ```
2. **Dynamic Dependency Discovery**:
   - Never hardcode the list of externals. Always inspect the `.amxd` patcher JSON to discover which `airfx.*~` objects are referenced.
3. **Cross-Platform POSIX Attributes**:
   - When building `.zip` archives on Windows, set POSIX file permissions (`0o755` for executables inside `.mxo` bundles, `0o644` for files, `0o755` for directories) so macOS users do not encounter permission denied errors upon extraction.
4. **macOS Gatekeeper Policy**:
   - Do NOT distribute executable helper scripts (e.g. `.command` files) inside release archives.
   - Instruct macOS users directly via `README.md` and documentation on how to clear quarantine flags:
     `xattr -cr ~/Documents/Max\ 8/Packages/OpenAir` (or `Max\ 9`).

## 1-Month Roadmap & Public Open Source Launch
- **First Open Source Project**: OpenAir marks `macchinette`'s debut into the open-source community.
- **Weekly Release Cadence**:
  - **Week 0 (Today)**: v0.0.1 Patreon pre-release (10 core devices, toolchain foundation).
  - **Week 1**: v0.0.2 Dynamics & saturation wave + dev template scaffolding.
  - **Week 2**: v0.0.3 Space & EQ wave + GitHub Pages site preview.
  - **Week 3**: v0.0.4 Release Candidate (RC) + Full 401-external bundle automation.
  - **Week 4**: Public Launch (v1.0.0 on GitHub + GitHub Pages + social campaign).
- **Post-Launch Automation Target**: Automated CI/CD release builds, issue triage, automated change notes, and community feedback integration.
- **Planning Directory (`/.todo/`)**: Stores weekly tasks, social media release plans, and distribution drafts. Keep ignored from git.
