"""
Builder module: Assembles the OpenAir Max Package and creates a cross-platform release ZIP.
"""

from dataclasses import dataclass, field
import hashlib
import json
import os
import shutil
import stat
import time
from typing import List, Optional, Set
import zipfile

from tools.inspector import inspect_workspace


@dataclass
class BuildResult:
    zip_path: str
    sha256: str
    file_count: int
    uncompressed_size: int
    compressed_size: int
    devices_included: List[str] = field(default_factory=list)
    externals_included: List[str] = field(default_factory=list)
    version: str = "0.0.1"
    curated: bool = True


def _compute_sha256(file_path: str) -> str:
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def _add_file_to_zip(
    zf: zipfile.ZipFile, src_path: str, arcname: str, is_executable: bool = False
):
    """Add a file to a zipfile preserving POSIX permissions (compatible with macOS unzip)."""
    with open(src_path, "rb") as f:
        data = f.read()

    mtime = time.localtime(os.path.getmtime(src_path))[:6]
    zinfo = zipfile.ZipInfo(arcname, mtime)
    zinfo.create_system = 3  # UNIX
    zinfo.compress_type = zipfile.ZIP_DEFLATED

    if is_executable:
        zinfo.external_attr = (0o755 | stat.S_IFREG) << 16
    else:
        zinfo.external_attr = (0o644 | stat.S_IFREG) << 16

    zf.writestr(zinfo, data)


def _add_dir_to_zip(zf: zipfile.ZipFile, arcname: str):
    """Add a directory entry to zipfile with POSIX permissions."""
    if not arcname.endswith("/"):
        arcname += "/"
    zinfo = zipfile.ZipInfo(arcname)
    zinfo.create_system = 3  # UNIX
    zinfo.compress_type = zipfile.ZIP_STORED
    zinfo.external_attr = (0o755 | stat.S_IFDIR) << 16
    zf.writestr(zinfo, b"")


def build_release_package(
    workspace_root: str,
    out_dir: Optional[str] = None,
    version: Optional[str] = None,
    curated: bool = True,
) -> BuildResult:
    """Build the release ZIP package."""
    # Read package-info.json for default metadata
    pkg_info_path = os.path.join(workspace_root, "package-info.json")
    pkg_data = {}
    if os.path.exists(pkg_info_path):
        with open(pkg_info_path, "r", encoding="utf-8") as f:
            pkg_data = json.load(f)

    rel_version = version or pkg_data.get("version", "0.0.1")

    # Destination folder
    out_folder = out_dir or os.path.join(workspace_root, "release")
    os.makedirs(out_folder, exist_ok=True)

    zip_filename = (
        f"OpenAir_v{rel_version}.zip"
        if curated
        else f"OpenAir_Full_v{rel_version}.zip"
    )
    zip_path = os.path.join(out_folder, zip_filename)

    # Inspect workspace
    inspection = inspect_workspace(workspace_root)
    devices_to_include = inspection.production_devices

    # Determine externals to include
    externals_dir = os.path.join(workspace_root, "externals")
    externals_to_include: Set[str] = set()

    if curated:
        externals_to_include = inspection.all_required_externals
    else:
        # Include all available externals in externals/
        for f in os.listdir(externals_dir):
            if f.endswith(".mxe64"):
                externals_to_include.add(f[:-6])
            elif f.endswith(".mxo"):
                externals_to_include.add(f[:-4])

    # Build ZIP archive
    file_count = 0
    uncompressed_size = 0

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # Base package directories
        base_dir = "OpenAir"
        _add_dir_to_zip(zf, f"{base_dir}/")
        _add_dir_to_zip(zf, f"{base_dir}/docs/")
        _add_dir_to_zip(zf, f"{base_dir}/externals/")
        _add_dir_to_zip(zf, f"{base_dir}/patchers/")

        # 1. package-info.json (ensure updated version/author)
        pkg_data["version"] = rel_version
        pkg_json_str = json.dumps(pkg_data, indent=4).encode("utf-8")
        zinfo = zipfile.ZipInfo(f"{base_dir}/package-info.json")
        zinfo.create_system = 3
        zinfo.compress_type = zipfile.ZIP_DEFLATED
        zinfo.external_attr = (0o644 | stat.S_IFREG) << 16
        zf.writestr(zinfo, pkg_json_str)
        file_count += 1
        uncompressed_size += len(pkg_json_str)

        # 2. README.md
        readme_path = os.path.join(workspace_root, "README.md")
        if os.path.exists(readme_path):
            sz = os.path.getsize(readme_path)
            _add_file_to_zip(
                zf, readme_path, f"{base_dir}/README.md", is_executable=False
            )
            file_count += 1
            uncompressed_size += sz

        # 3. docs/ (.maxref.xml and documentation files)
        docs_dir = os.path.join(workspace_root, "docs")
        if os.path.isdir(docs_dir):
            for doc_file in os.listdir(docs_dir):
                doc_path = os.path.join(docs_dir, doc_file)
                if os.path.isfile(doc_path):
                    sz = os.path.getsize(doc_path)
                    _add_file_to_zip(
                        zf,
                        doc_path,
                        f"{base_dir}/docs/{doc_file}",
                        is_executable=False,
                    )
                    file_count += 1
                    uncompressed_size += sz

        # 4. patchers/ (copy from m4lplugins/)
        m4l_dir = os.path.join(workspace_root, "m4lplugins")
        for dev_name in sorted(devices_to_include):
            src_dev = os.path.join(m4l_dir, dev_name)
            if os.path.isfile(src_dev):
                sz = os.path.getsize(src_dev)
                _add_file_to_zip(
                    zf,
                    src_dev,
                    f"{base_dir}/patchers/{dev_name}",
                    is_executable=False,
                )
                file_count += 1
                uncompressed_size += sz

        # 5. externals/ (.mxe64 and .mxo bundles)
        for ext_name in sorted(list(externals_to_include)):
            # Windows external: .mxe64
            win_ext = os.path.join(externals_dir, f"{ext_name}.mxe64")
            if os.path.isfile(win_ext):
                sz = os.path.getsize(win_ext)
                _add_file_to_zip(
                    zf,
                    win_ext,
                    f"{base_dir}/externals/{ext_name}.mxe64",
                    is_executable=False,
                )
                file_count += 1
                uncompressed_size += sz

            # macOS bundle: .mxo
            mac_ext = os.path.join(externals_dir, f"{ext_name}.mxo")
            if os.path.isdir(mac_ext):
                # Walk bundle directory
                for root, dirs, files in os.walk(mac_ext):
                    rel_to_ext = os.path.relpath(root, externals_dir)
                    # Normalize slashes for zip
                    arc_dir = (
                        f"{base_dir}/externals/{rel_to_ext}".replace(
                            "\\", "/"
                        ).rstrip("/")
                        + "/"
                    )
                    _add_dir_to_zip(zf, arc_dir)

                    for file in files:
                        src_file = os.path.join(root, file)
                        rel_file = os.path.relpath(src_file, externals_dir)
                        arc_file = f"{base_dir}/externals/{rel_file}".replace(
                            "\\", "/"
                        )

                        # Executable binaries inside MacOS/ directory
                        is_exec = (
                            "/Contents/MacOS/" in arc_file
                            or "\\Contents\\MacOS\\" in src_file
                        )

                        sz = os.path.getsize(src_file)
                        _add_file_to_zip(
                            zf, src_file, arc_file, is_executable=is_exec
                        )
                        file_count += 1
                        uncompressed_size += sz

    compressed_size = os.path.getsize(zip_path)
    sha256_hash = _compute_sha256(zip_path)

    # Write companion sha256 file
    with open(f"{zip_path}.sha256", "w", encoding="utf-8") as f:
        f.write(f"{sha256_hash}  {os.path.basename(zip_path)}\n")

    return BuildResult(
        zip_path=zip_path,
        sha256=sha256_hash,
        file_count=file_count,
        uncompressed_size=uncompressed_size,
        compressed_size=compressed_size,
        devices_included=sorted(devices_to_include),
        externals_included=sorted(list(externals_to_include)),
        version=rel_version,
        curated=curated,
    )
