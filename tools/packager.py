"""
Packager module: Packages M4L devices (.amxd) into self-contained frozen collectives,
or unfreezes them for rapid development.

Follows the official Cycling '74 Max Collective (ampf / mx@c) binary format:
- Embeds Windows .mxe64 binary
- Embeds macOS .mxo bundle with MS-DOS 0x10 directory attributes and 0x20 file attributes
- Writes dlst table of contents containing JSON, mx64, iLaX, zipfile, executable, and plist entries
"""

from dataclasses import dataclass
import io
import json
import os
import struct
import zipfile
from typing import List, Optional, Tuple

from tools.inspector import parse_amxd_patcher, extract_externals_from_patcher


def _pad4(data: bytes) -> bytes:
    rem = len(data) % 4
    if rem != 0:
        data += b"\x00" * (4 - rem)
    return data


def _make_tag(tag: str, val: bytes) -> bytes:
    tag_b = tag.encode("latin1")
    val_padded = _pad4(val)
    tlen = 8 + len(val_padded)
    return tag_b + struct.pack(">I", tlen) + val_padded


def _make_dire(
    ftype: bytes,
    fnam: str,
    sz: int,
    offset: int,
    flag: bytes = b"\x00\x00\x00\x00",
    mdat: bytes = b"\xe6\xcf>\xad",
) -> bytes:
    fnam_b = _pad4(fnam.encode("latin1") + b"\x00")
    tags = [
        _make_tag("type", ftype),
        _make_tag("fnam", fnam_b),
        _make_tag("sz32", struct.pack(">I", sz)),
        _make_tag("of32", struct.pack(">I", offset)),
        _make_tag("vers", b"\x00\x00\x00\x00"),
        _make_tag("flag", flag),
        _make_tag("mdat", mdat),
    ]
    payload = b"".join(tags)
    return b"dire" + struct.pack(">I", 8 + len(payload)) + payload


def _build_mac_bundle_zip(mac_bundle_path: str) -> bytes:
    """Build a zip of the .mxo bundle with MS-DOS attributes for Max collective extraction."""
    zip_buf = io.BytesIO()
    ext_dir = os.path.dirname(mac_bundle_path)
    bundle_name = os.path.basename(mac_bundle_path)

    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(mac_bundle_path):
            dirs.sort()
            files.sort()
            rel_root = os.path.relpath(root, ext_dir).replace(os.sep, "/") + "/"
            zinfo = zipfile.ZipInfo(rel_root)
            zinfo.create_system = 10  # Windows NT / MS-DOS
            zinfo.external_attr = 0x10  # Directory flag
            zf.writestr(zinfo, b"")

            for file in files:
                src_file = os.path.join(root, file)
                arc_file = os.path.relpath(src_file, ext_dir).replace(os.sep, "/")
                with open(src_file, "rb") as sf:
                    sdata = sf.read()
                zinfo = zipfile.ZipInfo(arc_file)
                zinfo.create_system = 10
                zinfo.external_attr = 0x20  # Archive/file flag
                zinfo.compress_type = zipfile.ZIP_DEFLATED
                zf.writestr(zinfo, sdata)

    return zip_buf.getvalue()


def freeze_device(
    amxd_path: str,
    externals_dir: str,
    out_path: Optional[str] = None,
) -> bool:
    """Freeze an AMXD device by embedding Windows and macOS externals into collective format."""
    out_file = out_path or amxd_path

    with open(amxd_path, "rb") as f:
        orig_data = f.read()

    # Extract clean patcher JSON
    patcher_dict = parse_amxd_patcher(amxd_path)
    if not patcher_dict:
        print(f"Error: Could not parse patcher from {amxd_path}")
        return False

    dev_name = os.path.basename(amxd_path)
    json_bytes = json.dumps({"patcher": patcher_dict}, indent=4).encode("utf-8")

    # Find referenced airfx external
    refs = extract_externals_from_patcher(patcher_dict)
    if not refs:
        print(f"Warning: No airfx external referenced in {dev_name}")
        return False

    ext_name = refs[0]
    win_path = os.path.join(externals_dir, f"{ext_name}.mxe64")
    mac_bundle = os.path.join(externals_dir, f"{ext_name}.mxo")

    has_win = os.path.isfile(win_path)
    has_mac = os.path.isdir(mac_bundle)

    if not has_win and not has_mac:
        print(f"Error: Neither Windows nor Mac external found for {ext_name}")
        return False

    # Read Windows binary
    win_data = b""
    if has_win:
        with open(win_path, "rb") as wf:
            win_data = wf.read()

    # Read Mac binary & plist
    mac_zip = b""
    mac_exec = b""
    mac_plist = b""
    if has_mac:
        mac_zip = _build_mac_bundle_zip(mac_bundle)
        exec_file = os.path.join(mac_bundle, f"Contents/MacOS/{ext_name}")
        plist_file = os.path.join(mac_bundle, "Contents/Info.plist")
        if os.path.isfile(exec_file):
            with open(exec_file, "rb") as ef:
                mac_exec = ef.read()
        if os.path.isfile(plist_file):
            with open(plist_file, "rb") as pf:
                mac_plist = pf.read()

    # Assemble mx@c body
    mxc_body = bytearray()
    dires = []

    # 1. JSON patcher
    off_json = 16
    mxc_body += json_bytes
    rem = len(mxc_body) % 4
    if rem:
        mxc_body += b"\x00" * (4 - rem)
    dires.append(
        _make_dire(
            b"JSON",
            dev_name,
            len(json_bytes),
            off_json,
            flag=b"\x00\x00\x00\x11",
        )
    )

    # 2. Windows mxe64
    if has_win and win_data:
        off_win = 16 + len(mxc_body)
        mxc_body += win_data
        rem = len(mxc_body) % 4
        if rem:
            mxc_body += b"\x00" * (4 - rem)
        dires.append(
            _make_dire(b"mx64", f"{ext_name}.mxe64", len(win_data), off_win)
        )

    # 3. Mac bundle elements (iLaX, zipfile, executable, plist)
    if has_mac and mac_zip:
        off_ilax = 16 + len(mxc_body)
        mxc_body += b"\x00\x00\x00\x00"
        dires.append(_make_dire(b"iLaX", f"{ext_name}.mxo", 4, off_ilax))

        off_zip = 16 + len(mxc_body)
        mxc_body += mac_zip
        rem = len(mxc_body) % 4
        if rem:
            mxc_body += b"\x00" * (4 - rem)
        dires.append(
            _make_dire(b"\x00\x00\x00\x00", f"{ext_name}/zipfile", len(mac_zip), off_zip)
        )

        if mac_exec:
            off_exec = 16 + len(mxc_body)
            mxc_body += mac_exec
            rem = len(mxc_body) % 4
            if rem:
                mxc_body += b"\x00" * (4 - rem)
            dires.append(
                _make_dire(
                    b"\x00\x00\x00\x00",
                    f"{ext_name}/executable",
                    len(mac_exec),
                    off_exec,
                )
            )

        if mac_plist:
            off_plist = 16 + len(mxc_body)
            mxc_body += mac_plist
            rem = len(mxc_body) % 4
            if rem:
                mxc_body += b"\x00" * (4 - rem)
            dires.append(
                _make_dire(
                    b"\x00\x00\x00\x00",
                    f"{ext_name}/plist",
                    len(mac_plist),
                    off_plist,
                )
            )

    # Directory list (dlst) table
    dlst_off = 16 + len(mxc_body)
    dlst_payload = b"".join(dires)
    dlst_chunk = b"dlst" + struct.pack(">I", 8 + len(dlst_payload)) + dlst_payload
    mxc_body += dlst_chunk

    # mx@c header
    mxc_hdr = b"mx@c\x00\x00\x00\x10\x00\x00\x00\x00" + struct.pack(">I", dlst_off)
    full_mxc = mxc_hdr + mxc_body

    # Full ampf container
    ampf_hdr = (
        b"ampf\x04\x00\x00\x00aaaameta\x04\x00\x00\x00\x07\x00\x00\x00ptch"
        + struct.pack("<I", len(full_mxc))
    )
    final_amxd = ampf_hdr + full_mxc

    with open(out_file, "wb") as f:
        f.write(final_amxd)

    print(f"Successfully frozen {dev_name} -> {out_file} ({len(final_amxd)} bytes)")
    return True


def is_collective(amxd_path: str) -> bool:
    """Check if an AMXD device is a frozen collective (contains mx@c header)."""
    with open(amxd_path, "rb") as f:
        header = f.read(128)
    return b"mx@c" in header


def unfreeze_device(amxd_path: str, out_path: Optional[str] = None) -> bool:
    """Unfreeze an AMXD device to lightweight development format (pure JSON in ampf container)."""
    out_file = out_path or amxd_path

    patcher_dict = parse_amxd_patcher(amxd_path)
    if not patcher_dict:
        print(f"Error: Could not parse patcher from {amxd_path}")
        return False

    dev_name = os.path.basename(amxd_path)
    json_bytes = json.dumps({"patcher": patcher_dict}, indent=4).encode("utf-8")

    # Lightweight ampf: ampf + meta (0=unfrozen) + ptch containing raw json
    ampf_hdr = (
        b"ampf\x04\x00\x00\x00aaaameta\x04\x00\x00\x00\x00\x00\x00\x00ptch"
        + struct.pack("<I", len(json_bytes))
    )
    final_amxd = ampf_hdr + json_bytes

    with open(out_file, "wb") as f:
        f.write(final_amxd)

    print(f"Successfully unfrozen {dev_name} -> {out_file} ({len(final_amxd)} bytes)")
    return True

