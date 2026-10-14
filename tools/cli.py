"""
CLI entry point for the OpenAir release toolchain.

Usage:
  python tools/cli.py inspect [--airfx-dir ../airfx]
  python tools/cli.py build [--version 0.0.1] [--airfx-dir ../airfx] [--full] [--out-dir release/]
  python tools/cli.py freeze [--device OA_galactic.amxd] [--all] [--airfx-dir ../airfx]
  python tools/cli.py unfreeze [--device OA_galactic.amxd] [--all]
  python tools/cli.py verify [zip_path]
"""

import argparse
import os
import sys

# Ensure repository root is on sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACE_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

from tools.builder import build_release_package
from tools.inspector import inspect_workspace
from tools.packager import freeze_device, unfreeze_device
from tools.screenshot_batch import render_plugin_screenshot, DEVICE_CONFIGS
from tools.verifier import verify_release_zip


def cmd_inspect(args):
    print("=" * 70)
    print("OpenAir Toolchain: Inspecting Devices & Dependencies")
    print("=" * 70)

    result = inspect_workspace(WORKSPACE_ROOT, airfx_root=args.airfx_dir)

    print(f"\nFound {len(result.devices)} device(s) in m4lplugins/:")
    print(f"  - Production devices ({len(result.production_devices)}):")
    for d in result.production_devices:
        print(f"      * {d}")
    print(f"  - Template devices ({len(result.template_devices)}):")
    for d in result.template_devices:
        print(f"      * {d}")

    print("\nDetailed Device Dependency Mapping:")
    print(f"{'Device':<32} {'Status':<12} {'Externals':<25}")
    print("-" * 70)
    for dev in result.devices:
        status = "Template" if dev.is_template else "Ready"
        ext_str = ", ".join(dev.referenced_externals) or "(None)"
        print(f"{dev.name:<32} {status:<12} {ext_str:<25}")

    print(
        f"\nTotal Unique Required Externals ({len(result.all_required_externals)}):"
    )
    for ext in sorted(result.all_required_externals):
        win_ok = "[Win OK]" if ext in result.available_win_externals else "[Win MISSING]"
        mac_ok = "[Mac OK]" if ext in result.available_mac_externals else "[Mac MISSING]"
        print(f"  - {ext:<30} {win_ok:<12} {mac_ok:<12}")

    if result.missing_externals:
        print("\nWARNING: Missing externals detected:")
        for m in sorted(result.missing_externals):
            print(f"  ! {m}")
        return 1
    else:
        print("\nAll required Windows and macOS externals are available in airfx!")
        return 0


def cmd_freeze(args):
    print("=" * 70)
    print("OpenAir Toolchain: Freezing M4L Devices for Standalone Distribution")
    print("=" * 70)

    m4l_dir = os.path.join(WORKSPACE_ROOT, "m4lplugins")
    default_airfx = os.path.abspath(os.path.join(WORKSPACE_ROOT, "..", "airfx"))
    src_airfx = args.airfx_dir or default_airfx
    externals_dir = os.path.join(src_airfx, "externals")

    devices_to_freeze = []
    if args.device:
        devices_to_freeze.append(args.device)
    elif args.all:
        for f in sorted(os.listdir(m4l_dir)):
            if f.endswith(".amxd") and f != "OA_init.amxd":
                devices_to_freeze.append(f)
    else:
        print("Please specify --device <filename.amxd> or --all")
        return 1

    success_count = 0
    for dev_name in devices_to_freeze:
        dev_path = os.path.join(m4l_dir, dev_name)
        if not os.path.isfile(dev_path):
            print(f"Error: {dev_name} not found in m4lplugins/")
            continue
        if freeze_device(dev_path, externals_dir):
            success_count += 1

    print(f"\nFreezing complete! {success_count}/{len(devices_to_freeze)} device(s) successfully packaged.")
    return 0 if success_count == len(devices_to_freeze) else 1


def cmd_unfreeze(args):
    print("=" * 70)
    print("OpenAir Toolchain: Unfreezing M4L Devices for Lightweight Development")
    print("=" * 70)

    m4l_dir = os.path.join(WORKSPACE_ROOT, "m4lplugins")
    devices_to_unfreeze = []
    if args.device:
        devices_to_unfreeze.append(args.device)
    elif args.all:
        for f in sorted(os.listdir(m4l_dir)):
            if f.endswith(".amxd") and f != "OA_init.amxd":
                devices_to_unfreeze.append(f)
    else:
        print("Please specify --device <filename.amxd> or --all")
        return 1

    success_count = 0
    for dev_name in devices_to_unfreeze:
        dev_path = os.path.join(m4l_dir, dev_name)
        if not os.path.isfile(dev_path):
            print(f"Error: {dev_name} not found in m4lplugins/")
            continue
        if unfreeze_device(dev_path):
            success_count += 1

    print(f"\nUnfreezing complete! {success_count}/{len(devices_to_unfreeze)} device(s) converted to lightweight dev format.")
    return 0 if success_count == len(devices_to_unfreeze) else 1


def cmd_screenshot(args):
    print("=" * 70)
    print("OpenAir Toolchain: Rendering High-Res Device Screenshots")
    print("=" * 70)

    out_dir = args.out_dir or os.path.join(WORKSPACE_ROOT, "media", "v0.0.1")
    plugins = [args.device] if args.device else sorted(list(DEVICE_CONFIGS.keys()))

    success_count = 0
    for p in plugins:
        if render_plugin_screenshot(p, out_dir=out_dir):
            success_count += 1
        time.sleep(0.5)

    import subprocess
    subprocess.run(["taskkill", "/F", "/IM", "Max.exe"], capture_output=True)

    print(f"\nScreenshot render complete: {success_count}/{len(plugins)} captured successfully to {out_dir}")
    return 0 if success_count == len(plugins) else 1


def cmd_build(args):
    print("=" * 70)
    print("OpenAir Toolchain: Building Cross-Platform Release Package")
    print("=" * 70)

    curated = not args.full
    mode_str = "Curated (Only needed externals)" if curated else "Full (All externals)"
    print(f"Mode:    {mode_str}")
    if args.version:
        print(f"Version: {args.version}")
    if args.out_dir:
        print(f"Out Dir: {args.out_dir}")

    build_res = build_release_package(
        workspace_root=WORKSPACE_ROOT,
        airfx_root=args.airfx_dir,
        out_dir=args.out_dir,
        version=args.version,
        curated=curated,
        freeze_devices=not args.no_freeze,
    )

    print("\nBuild Complete!")
    print(f"  Zip Path:           {build_res.zip_path}")
    print(f"  SHA256:             {build_res.sha256}")
    print(f"  Total Files:        {build_res.file_count}")
    print(f"  Uncompressed Size:  {build_res.uncompressed_size / (1024*1024):.2f} MB")
    print(f"  Compressed Size:    {build_res.compressed_size / (1024*1024):.2f} MB")
    print(f"  Devices Included:   {len(build_res.devices_included)}")
    print(f"  Externals Included: {len(build_res.externals_included)}")

    print("\nAuto-Verifying generated archive...")
    v_res = verify_release_zip(build_res.zip_path)
    if v_res.is_valid:
        print("Archive verification PASSED successfully!")
        return 0
    else:
        print("Archive verification FAILED with errors:")
        for err in v_res.errors:
            print(f"  x {err}")
        return 1


def cmd_verify(args):
    zip_path = args.zip_path
    if not zip_path:
        rel_dir = os.path.join(WORKSPACE_ROOT, "release")
        if os.path.isdir(rel_dir):
            zips = [
                os.path.join(rel_dir, f)
                for f in os.listdir(rel_dir)
                if f.endswith(".zip")
            ]
            if zips:
                zip_path = max(zips, key=os.path.getmtime)

    if not zip_path or not os.path.exists(zip_path):
        print(f"Error: No ZIP file found to verify at '{zip_path}'.")
        return 1

    print("=" * 70)
    print(f"OpenAir Toolchain: Verifying Release Archive: {os.path.basename(zip_path)}")
    print("=" * 70)

    res = verify_release_zip(zip_path)
    print(f"Archive Valid: {res.is_valid}")
    print(f"Total Files:   {res.file_count}")
    print(f"Total Size:    {res.total_uncompressed_bytes / (1024*1024):.2f} MB")
    print(f"Devices ({len(res.patchers_found)}):")
    for p in sorted(res.patchers_found):
        print(f"  - {p}")

    print(f"\nExternals ({len(res.externals_found_win)} Windows, {len(res.externals_found_mac)} macOS):")
    for ext in sorted(set(res.externals_found_win) | set(res.externals_found_mac)):
        pe_info = res.pe_verified.get(ext, "Missing PE")
        macho_info = res.macho_verified.get(ext, "Missing Mach-O")
        print(f"  - {ext:<30} Win: {pe_info:<22} Mac: {macho_info}")

    if res.warnings:
        print("\nWarnings:")
        for w in res.warnings:
            print(f"  ! {w}")

    if res.errors:
        print("\nErrors:")
        for e in res.errors:
            print(f"  x {e}")
        return 1

    print("\nAll verification checks passed!")
    return 0


def main():
    parser = argparse.ArgumentParser(description="OpenAir Release Toolchain")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Inspect command
    inspect_parser = subparsers.add_parser("inspect", help="Inspect M4L devices and external dependencies")
    inspect_parser.add_argument("--airfx-dir", help="Path to airfx repo root (default: ../airfx)")

    # Freeze command
    freeze_parser = subparsers.add_parser("freeze", help="Freeze M4L devices into standalone collectives")
    freeze_parser.add_argument("--device", help="Specific device name (e.g. OA_galactic.amxd)")
    freeze_parser.add_argument("--all", action="store_true", help="Freeze all production devices")
    freeze_parser.add_argument("--airfx-dir", help="Path to airfx repo root (default: ../airfx)")

    # Unfreeze command
    unfreeze_parser = subparsers.add_parser("unfreeze", help="Unfreeze M4L devices for lightweight rapid development")
    unfreeze_parser.add_argument("--device", help="Specific device name (e.g. OA_galactic.amxd)")
    unfreeze_parser.add_argument("--all", action="store_true", help="Unfreeze all production devices")

    # Build command
    build_parser = subparsers.add_parser("build", help="Build release ZIP package")
    build_parser.add_argument("--version", help="Version override (e.g. 0.0.1)")
    build_parser.add_argument("--out-dir", help="Output directory (defaults to release/)")
    build_parser.add_argument("--airfx-dir", help="Path to airfx repo root (default: ../airfx)")
    build_parser.add_argument("--no-freeze", action="store_true", help="Do not auto-freeze devices inside release zip")
    build_parser.add_argument("--full", action="store_true", help="Include all externals instead of curated selection")

    # Verify command
    verify_parser = subparsers.add_parser("verify", help="Verify a release ZIP package")
    verify_parser.add_argument("zip_path", nargs="?", help="Path to ZIP file (defaults to latest in release/)")

    # Screenshot command
    screenshot_parser = subparsers.add_parser("screenshot", help="Render clean high-res device screenshots without borders")
    screenshot_parser.add_argument("--device", help="Specific device name (e.g. OA_totape8.amxd)")
    screenshot_parser.add_argument("--out-dir", help="Output directory (defaults to media/v0.0.1/)")

    args = parser.parse_args()
    if args.command == "inspect":
        sys.exit(cmd_inspect(args))
    elif args.command == "freeze":
        sys.exit(cmd_freeze(args))
    elif args.command == "unfreeze":
        sys.exit(cmd_unfreeze(args))
    elif args.command == "screenshot":
        sys.exit(cmd_screenshot(args))
    elif args.command == "build":
        sys.exit(cmd_build(args))
    elif args.command == "verify":
        sys.exit(cmd_verify(args))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
