"""
Inspector module: Scans M4L devices (.amxd) and extracts external dependencies.
"""

from dataclasses import dataclass, field
import glob
import json
import os
import re
from typing import Dict, List, Optional, Set


@dataclass
class DeviceReport:
    name: str
    file_path: str
    file_size: int
    is_template: bool
    referenced_externals: List[str] = field(default_factory=list)
    missing_win_externals: List[str] = field(default_factory=list)
    missing_mac_externals: List[str] = field(default_factory=list)


@dataclass
class InspectionResult:
    devices: List[DeviceReport] = field(default_factory=list)
    all_required_externals: Set[str] = field(default_factory=set)
    available_win_externals: Set[str] = field(default_factory=set)
    available_mac_externals: Set[str] = field(default_factory=set)
    missing_externals: Set[str] = field(default_factory=set)
    template_devices: List[str] = field(default_factory=list)
    production_devices: List[str] = field(default_factory=list)


def parse_amxd_patcher(file_path_or_bytes) -> Optional[dict]:
    """Parse JSON patcher data from an AMXD file (path or raw bytes)."""
    if isinstance(file_path_or_bytes, (bytes, bytearray)):
        raw = bytes(file_path_or_bytes)
    else:
        with open(file_path_or_bytes, "rb") as f:
            raw = f.read()

    idx = raw.find(b'"patcher"')
    if idx == -1:
        return None

    brace_idx = raw.rfind(b"{", 0, idx)
    end_idx = raw.rfind(b"}")
    if brace_idx == -1 or end_idx == -1:
        return None

    try:
        txt = raw[brace_idx : end_idx + 1].decode("utf-8", errors="ignore")
        decoder = json.JSONDecoder()
        data, _ = decoder.raw_decode(txt)
        return data.get("patcher")
    except Exception:
        return None


def extract_externals_from_patcher(patcher: dict) -> List[str]:
    """Extract all airfx.* external references from a patcher dictionary."""
    externals = set()
    boxes = patcher.get("boxes", [])
    for b in boxes:
        box = b.get("box", {})
        text = box.get("text", "")
        # Look for tokens starting with airfx.
        for token in text.split():
            if token.startswith("airfx."):
                # Normalize token: strip commas, quotes, etc.
                clean_token = token.strip("\",'`;")
                if not clean_token.endswith("~") and not clean_token.endswith(
                    "__"
                ):
                    # In Max DSP objects almost always end in ~
                    clean_token += "~"
                externals.add(clean_token)
    return sorted(list(externals))


def inspect_workspace(
    workspace_root: str, airfx_root: Optional[str] = None
) -> InspectionResult:
    """Inspect all devices in m4lplugins/ and cross-reference with externals in airfx."""
    m4l_dir = os.path.join(workspace_root, "m4lplugins")
    
    # Locate externals in airfx (single source of truth)
    default_airfx = os.path.abspath(os.path.join(workspace_root, "..", "airfx"))
    src_airfx = airfx_root or default_airfx
    externals_dir = os.path.join(src_airfx, "externals")

    result = InspectionResult()
    if not os.path.isdir(m4l_dir):
        return result

    device_files = sorted(glob.glob(os.path.join(m4l_dir, "*.amxd")))

    for fpath in device_files:
        fname = os.path.basename(fpath)
        fsize = os.path.getsize(fpath)
        patcher = parse_amxd_patcher(fpath)

        if patcher is None:
            continue

        externals = extract_externals_from_patcher(patcher)
        # Check if it's a template device
        is_template = (
            fname == "OA_init.amxd"
            or any("__" in ext for ext in externals)
            or len(externals) == 0
        )

        rep = DeviceReport(
            name=fname,
            file_path=fpath,
            file_size=fsize,
            is_template=is_template,
            referenced_externals=externals,
        )

        if is_template:
            result.template_devices.append(fname)
        else:
            result.production_devices.append(fname)

        for ext in externals:
            if "__" in ext:
                continue
            result.all_required_externals.add(ext)

            win_path = os.path.join(externals_dir, f"{ext}.mxe64")
            mac_path = os.path.join(externals_dir, f"{ext}.mxo")

            if os.path.exists(win_path):
                result.available_win_externals.add(ext)
            else:
                rep.missing_win_externals.append(ext)
                result.missing_externals.add(f"{ext} (Windows .mxe64)")

            if os.path.isdir(mac_path):
                result.available_mac_externals.add(ext)
            else:
                rep.missing_mac_externals.append(ext)
                result.missing_externals.add(f"{ext} (macOS .mxo)")

        result.devices.append(rep)

    return result
