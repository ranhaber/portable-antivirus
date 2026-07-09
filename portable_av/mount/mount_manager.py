from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
from pathlib import Path

from portable_av.common.domain import DriveInfo
from portable_av.common.paths import AppPaths
from portable_av.mount.device_detector import DeviceDetectorError, inspect_device, resolve_partition_device
from portable_av.mount.notify_engine import notify_drive_event

logger = logging.getLogger(__name__)

MOUNT_ROOT = Path("/mnt/portable-av")
MOUNT_FLAGS = "ro,nosuid,nodev,noexec"


class MountManagerError(RuntimeError):
    pass


class MountManager:
    def __init__(self, *, mount_root: Path = MOUNT_ROOT, runtime_dir: Path | None = None) -> None:
        self._mount_root = mount_root
        self._runtime_dir = runtime_dir or Path("/run/portable-av")
        self._mount_root.mkdir(parents=True, exist_ok=True)
        self._runtime_dir.mkdir(parents=True, exist_ok=True)

    @property
    def drive_state_path(self) -> Path:
        return self._runtime_dir / "drive.json"

    def mount_readonly(self, device: str) -> DriveInfo:
        info = inspect_device(device)
        if not info.supported:
            raise MountManagerError(f"Unsupported filesystem: {info.filesystem}")

        mount_id = info.uuid or Path(info.device).name
        mount_path = self._mount_root / mount_id
        mount_path.mkdir(parents=True, exist_ok=True)

        if self._is_mounted(mount_path):
            logger.info("Already mounted at %s", mount_path)
        else:
            command = self._build_mount_command(info.device, info.filesystem, mount_path)
            try:
                subprocess.run(command, check=True, capture_output=True, text=True)
            except subprocess.CalledProcessError as exc:
                raise MountManagerError(exc.stderr or str(exc)) from exc

        drive = DriveInfo(
            device=info.device,
            mount_path=mount_path,
            label=info.label,
            uuid=info.uuid,
            filesystem=info.filesystem,
            size_bytes=info.size_bytes,
            readonly=True,
        )
        self._write_drive_state(drive)
        return drive

    def unmount(self, device: str | None = None) -> None:
        state = self._read_drive_state()
        mount_path = None
        if state:
            mount_path = Path(state["mount_path"])
        elif device:
            info = inspect_device(device)
            mount_id = info.uuid or Path(info.device).name
            mount_path = self._mount_root / mount_id

        if mount_path and self._is_mounted(mount_path):
            subprocess.run(["umount", str(mount_path)], check=False, capture_output=True, text=True)
        if self.drive_state_path.exists():
            self.drive_state_path.unlink()

    def _build_mount_command(self, device: str, filesystem: str, mount_path: Path) -> list[str]:
        if filesystem == "ntfs":
            return ["ntfs-3g", "-o", MOUNT_FLAGS, device, str(mount_path)]
        extra = ",noload" if filesystem.startswith("ext") else ""
        return ["mount", "-t", filesystem, "-o", f"{MOUNT_FLAGS}{extra}", device, str(mount_path)]

    def _is_mounted(self, mount_path: Path) -> bool:
        try:
            with open("/proc/mounts", encoding="utf-8") as handle:
                target = str(mount_path.resolve())
                for line in handle:
                    parts = line.split()
                    if len(parts) >= 2 and parts[1] == target:
                        return True
        except OSError:
            return False
        return False

    def _write_drive_state(self, drive: DriveInfo) -> None:
        payload = {
            "device": drive.device,
            "mount_path": str(drive.mount_path),
            "label": drive.label,
            "uuid": drive.uuid,
            "filesystem": drive.filesystem,
            "size_bytes": drive.size_bytes,
            "readonly": drive.readonly,
        }
        self.drive_state_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    def _read_drive_state(self) -> dict | None:
        if not self.drive_state_path.is_file():
            return None
        return json.loads(self.drive_state_path.read_text(encoding="utf-8"))


def _engine_url() -> str:
    host = os.environ.get("PORTABLE_AV_API_HOST", "127.0.0.1")
    port = os.environ.get("PORTABLE_AV_API_PORT", "8080")
    return f"http://{host}:{port}/api/v1/internal/drive"


def _internal_token(runtime_dir: Path) -> str:
    token_path = runtime_dir / "internal.token"
    if not token_path.is_file():
        raise MountManagerError(f"Internal token file not found: {token_path}")
    return token_path.read_text(encoding="utf-8").strip()


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Portable AV read-only mount helper")
    parser.add_argument("--device", help="Block device path, e.g. /dev/sda1")
    parser.add_argument("--unmount", action="store_true", help="Unmount current or specified device")
    parser.add_argument("--runtime-dir", default=os.environ.get("PORTABLE_AV_RUNTIME", "/run/portable-av"))
    args = parser.parse_args(argv)

    runtime_dir = Path(args.runtime_dir)
    manager = MountManager(runtime_dir=runtime_dir)

    try:
        if args.unmount:
            manager.unmount(args.device)
            notify_drive_event(
                _engine_url(),
                _internal_token(runtime_dir),
                {"event": "removed", "device": args.device or ""},
            )
            return 0

        if not args.device:
            parser.error("--device is required unless --unmount is set")
        partition = resolve_partition_device(args.device)
        drive = manager.mount_readonly(partition)
        notify_drive_event(
            _engine_url(),
            _internal_token(runtime_dir),
            {
                "event": "mounted",
                "device": drive.device,
                "mount_path": str(drive.mount_path),
                "label": drive.label,
                "uuid": drive.uuid,
                "filesystem": drive.filesystem,
                "size_bytes": drive.size_bytes,
                "readonly": drive.readonly,
            },
        )
        logger.info("Mounted %s at %s", drive.device, drive.mount_path)
        return 0
    except (DeviceDetectorError, MountManagerError) as exc:
        logger.error("%s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
