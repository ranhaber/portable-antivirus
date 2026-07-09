from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from portable_av.common.config_loader import load_config
from portable_av.common.models import ScanMode, ScanState, ThreatAction
from portable_av.common.paths import AppPaths
from portable_av.engine.scan_controller import ScanController
from portable_av.history.repository import HistoryRepository


async def _run_scan(
    *,
    config_path: Path,
    scan_path: Path,
    mode: ScanMode,
    auto_continue: bool,
) -> int:
    config = load_config(config_path)
    paths = AppPaths(
        config_file=config_path,
        data=Path("var/lib/portable-av"),
        logs=Path("var/log/portable-av"),
        runtime=Path("var/run/portable-av"),
        temp=Path("var/tmp/portable-av"),
    )
    paths.ensure_runtime_dirs()
    repository = HistoryRepository(paths.history_db)
    repository.initialize()
    controller = ScanController(config=config, paths=paths, history_repository=repository)

    async def auto_continue_on_threat() -> None:
        while True:
            await asyncio.sleep(0.1)
            progress = controller.get_progress()
            if progress.state == ScanState.THREAT_PROMPT:
                await controller.handle_threat_action(
                    ThreatAction.CONTINUE if auto_continue else ThreatAction.STOP
                )

    watcher = asyncio.create_task(auto_continue_on_threat())
    scan_id = await controller.start_scan(mode, requested_by="cli", scan_root=scan_path)
    print(f"Started scan {scan_id} on {scan_path}")
    while True:
        progress = controller.get_progress()
        if progress.state in {ScanState.COMPLETE, ScanState.IDLE}:
            break
        await asyncio.sleep(0.5)
    watcher.cancel()
    record = repository.get_scan(scan_id)
    print(f"Finished: status={record['status'] if record else 'unknown'} threats={progress.threats}")
    if record and record.get("report_txt_path"):
        print(f"Report: {record['report_txt_path']}")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Portable AV headless scan CLI")
    parser.add_argument("scan_path", type=Path, help="Directory to scan")
    parser.add_argument("--config", type=Path, default=Path("config/dev.config.json"))
    parser.add_argument("--mode", choices=["quick", "full"], default="quick")
    parser.add_argument(
        "--auto-continue",
        action="store_true",
        help="Continue scanning after threat detection",
    )
    args = parser.parse_args()
    raise SystemExit(
        asyncio.run(
            _run_scan(
                config_path=args.config,
                scan_path=args.scan_path,
                mode=ScanMode(args.mode),
                auto_continue=args.auto_continue,
            )
        )
    )


if __name__ == "__main__":
    main()
