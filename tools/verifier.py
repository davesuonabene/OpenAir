"""
Verifier module: Validates an OpenAir release ZIP archive for integrity,
file layout, POSIX permissions, and cross-platform native binary formats.
"""

from dataclasses import dataclass, field
import json
import os
import struct
from typing import Dict, List, Optional
import zipfile


@dataclass
class VerificationResult:
    zip_path: str
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    patchers_found: List[str] = field(default_factory=list)
    externals_found_win: List[str] = field(default_factory=list)
    externals_found_mac: List[str] = field(default_factory=list)
    macho_verified: Dict[str, str] = field(default_factory=dict)
    pe_verified: Dict[str, str] = field(default_factory=dict)
    file_count: int = 0
    total_uncompressed_bytes: int = 0


def _check_pe_header(data: bytes) -> str:
    """Check if byte data represents a valid PE32+ (x64) binary."""
    if len(data) < 64 or data[:2] != b"MZ":
        return "Invalid (No MZ signature)"
    pe_offset = int.from_bytes(data[0x3C:0x40], "little")
    if len(data) < pe_offset + 24:
        return "Invalid (Truncated PE header)"
    sig = data[pe_offset : pe_offset + 4]
    if sig != b"PE\x00\x00":
        return "Invalid (No PE signature)"
    machine = int.from_bytes(data[pe_offset + 4 : pe_offset + 6], "little")
    if machine == 0x8664:
        return "PE32+ (x86_64 / Windows 64-bit)"
    elif machine == 0xAA64:
        return "PE32+ (ARM64)"
    elif machine == 0x14C:
        return "PE (x86 32-bit)"
    return f"PE Machine {hex(machine)}"


def _check_macho_header(data: bytes) -> str:
    """Check if byte data represents a Universal Mach-O binary."""
    if len(data) < 8:
        return "Invalid (Too short)"
    magic = data[:4]
    if magic == b"\xca\xfe\xba\xbe":  # FAT / Universal binary
        num_fat = struct.unpack(">I", data[4:8])[0]
        archs = []
        offset = 8
        for _ in range(num_fat):
            if len(data) < offset + 20:
                break
            cputype = struct.unpack(">I", data[offset : offset + 4])[0]
            if cputype == 7 | 0x01000000:
                archs.append("x86_64")
            elif cputype == 12 | 0x01000000:
                archs.append("arm64")
            elif cputype == 7:
                archs.append("x86")
            else:
                archs.append(f"cpu_{hex(cputype)}")
            offset += 20
        return f"Universal Mach-O ({', '.join(archs)})"
    elif magic == b"\xcf\xfa\xed\xfe":
        return "Mach-O 64-bit (Little Endian)"
    elif magic == b"\xfe\xed\xfa\xcf":
        return "Mach-O 64-bit (Big Endian)"
    return f"Unknown Mach-O magic: {magic}"


def verify_release_zip(zip_path: str) -> VerificationResult:
    """Verify an OpenAir release ZIP archive."""
    result = VerificationResult(zip_path=zip_path, is_valid=True)

    if not os.path.isfile(zip_path):
        result.is_valid = False
        result.errors.append(f"ZIP file does not exist: {zip_path}")
        return result

    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            corrupt_file = zf.testzip()
            if corrupt_file:
                result.is_valid = False
                result.errors.append(f"Corrupt file in ZIP: {corrupt_file}")
                return result

            names = zf.namelist()
            result.file_count = len(names)

            # Check root folder convention
            if not any(n.startswith("OpenAir/") for n in names):
                result.errors.append(
                    "Archive does not contain root 'OpenAir/' folder"
                )
                result.is_valid = False

            # Check mandatory files
            if "OpenAir/package-info.json" not in names:
                result.errors.append("Missing OpenAir/package-info.json")
                result.is_valid = False
            else:
                try:
                    pkg_bytes = zf.read("OpenAir/package-info.json")
                    pkg = json.loads(pkg_bytes.decode("utf-8"))
                    if pkg.get("author") != "macchinette":
                        result.warnings.append(
                            f"package-info.json author is '{pkg.get('author')}', expected 'macchinette'"
                        )
                except Exception as e:
                    result.errors.append(f"Invalid package-info.json: {e}")
                    result.is_valid = False

            if "OpenAir/README.md" not in names:
                result.warnings.append("OpenAir/README.md not found in archive")

            for info in zf.infolist():
                result.total_uncompressed_bytes += info.file_size
                name = info.filename

                # Collect patchers
                if name.startswith("OpenAir/patchers/") and name.endswith(
                    ".amxd"
                ):
                    result.patchers_found.append(os.path.basename(name))

                # Collect Windows externals
                if name.startswith("OpenAir/externals/") and name.endswith(
                    ".mxe64"
                ):
                    ext_name = os.path.basename(name)[:-6]
                    result.externals_found_win.append(ext_name)
                    # Check PE format
                    header_bytes = zf.read(name)[:512]
                    result.pe_verified[ext_name] = _check_pe_header(
                        header_bytes
                    )

                # Collect Mac externals
                if "/Contents/MacOS/" in name and not name.endswith("/"):
                    ext_name = os.path.basename(name)
                    result.externals_found_mac.append(ext_name)
                    # Check Mach-O format
                    header_bytes = zf.read(name)[:512]
                    result.macho_verified[ext_name] = _check_macho_header(
                        header_bytes
                    )

                    # Check POSIX executable permission
                    perm = (info.external_attr >> 16) & 0o777
                    if perm != 0o755:
                        result.warnings.append(
                            f"Binary {name} has POSIX mode {oct(perm)}, expected 0o755"
                        )

            # Check that every patcher has matching externals
            # Map patchers to externals
            for p in result.patchers_found:
                # read amxd from zip
                amxd_bytes = zf.read(f"OpenAir/patchers/{p}")
                from tools.inspector import parse_amxd_patcher, extract_externals_from_patcher
                patch_dict = parse_amxd_patcher(amxd_bytes)
                if patch_dict:
                    matches = extract_externals_from_patcher(patch_dict)
                else:
                    matches = []
                for clean in matches:
                    if clean == "airfx.__":
                        continue
                    if clean not in result.externals_found_win:
                        result.errors.append(
                            f"Device {p} references {clean} but .mxe64 is missing in ZIP"
                        )
                        result.is_valid = False
                    if clean not in result.externals_found_mac:
                        result.errors.append(
                            f"Device {p} references {clean} but .mxo is missing in ZIP"
                        )
                        result.is_valid = False

    except Exception as e:
        result.is_valid = False
        result.errors.append(f"Failed to read ZIP: {e}")

    if result.errors:
        result.is_valid = False

    return result
