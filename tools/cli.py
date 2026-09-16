"""
CLI entry point for the OpenAir release toolchain.

Usage:
  python tools/cli.py inspect
  python tools/cli.py build [--version 0.0.1] [--full] [--out-dir release/]
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
from tools.verifier import verify_release_zip


def cmd_inspect(args):
    print("=" * 70)
    print("OpenAir Toolchain: Inspecting Devices & Dependencies")
    print("=" * 70)

    result = inspect_workspace(WORKSPACE_ROOT)

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
        print("\nAll required Windows and macOS externals are available!")
        return 0


def cmd_build(args):
    print("=" * 70)
    print("OpenAir Toolchain: Building Cross-Platform Release Package")
    print("=" * 70)

    curated = not args.full
    mode_str = "Curated (Only needed externals)" if curated else "Full (All 401 externals)"
    print(f"Mode:    {mode_str}")
    if args.version:
        print(f"Version: {args.version}")
    if args.out_dir:
        print(f"Out Dir: {args.out_dir}")

    build_res = build_release_package(
        workspace_root=WORKSPACE_ROOT,
        out_dir=args.out_dir,
        version=args.version,
        curated=curated,
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
        # Default to the newest zip in release/
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
    subparsers.add_parser("inspect", help="Inspect M4L devices and external dependencies")

    # Build command
    build_parser = subparsers.add_parser("build", help="Build release ZIP package")
    build_parser.add_argument("--version", help="Version override (e.g. 0.0.1)")
    build_parser.add_argument("--out-dir", help="Output directory (defaults to release/)")
    build_parser.add_argument("--full", action="store_true", help="Include all 401 externals instead of curated selection")

    # Verify command
    verify_parser = subparsers.add_parser("verify", help="Verify a release ZIP package")
    verify_parser.add_argument("zip_path", nargs="?", help="Path to ZIP file (defaults to latest in release/)")

    args = parser.parse_args()
    if args.command == "inspect":
        sys.exit(cmd_inspect(args))
    elif args.command == "build":
        sys.exit(cmd_build(args))
    elif args.command == "verify":
        sys.exit(cmd_verify(args))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
