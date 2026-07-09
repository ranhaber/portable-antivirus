from __future__ import annotations

import json
import subprocess
from pathlib import Path

from portable_av.mount.filesystem_info import FilesystemInfo, SUPPORTED_FILESYSTEMS


class DeviceDetectorError(RuntimeError):
    pass


def _run(command: list[str]) -> str:
    try:
        completed = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        raise DeviceDetectorError(f"Command failed: {' '.join(command)}") from exc
    return completed.stdout


def resolve_partition_device(device: str) -> str:
    """Return a partition node for mount; pick first child partition when needed."""
    device_path = Path(device)
    if not device_path.exists():
        raise DeviceDetectorError(f"Device not found: {device}")

    blockdevices = json.loads(_run(["lsblk", "-J", "-o", "NAME,TYPE,PATH"]))
    nodes = blockdevices.get("blockdevices", [])

    def walk(node: dict) -> dict | None:
        if node.get("path") == str(device_path):
            return node
        for child in node.get("children") or []:
            found = walk(child)
            if found is not None:
                return found
        return None

    for node in nodes:
        match = walk(node)
        if match is None:
            continue
        if match.get("type") == "part":
            return str(device_path)
        children = match.get("children") or []
        for child in children:
            if child.get("type") == "part":
                return child["path"]
        raise DeviceDetectorError(f"No mountable partition found for {device}")
    raise DeviceDetectorError(f"Device not present in lsblk output: {device}")


def inspect_device(device: str) -> FilesystemInfo:
    partition = resolve_partition_device(device)
    export = _run(["blkid", "-o", "export", partition])

    values: dict[str, str] = {}
    for line in export.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key] = value.strip('"')

    filesystem = values.get("TYPE", "unknown")
    size_bytes = None
    try:
        size_payload = json.loads(_run(["lsblk", "-J", "-b", "-o", "SIZE,PATH", partition]))
        for node in size_payload.get("blockdevices", []):
            if node.get("path") == partition:
                size_bytes = int(node.get("size") or 0)
    except DeviceDetectorError:
        size_bytes = None

    return FilesystemInfo(
        device=partition,
        filesystem=filesystem,
        label=values.get("LABEL"),
        uuid=values.get("UUID"),
        size_bytes=size_bytes,
        supported=filesystem in SUPPORTED_FILESYSTEMS,
    )
