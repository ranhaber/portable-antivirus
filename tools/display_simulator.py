#!/usr/bin/env python3
"""Terminal display simulator for pre-HAT development."""

from __future__ import annotations

import argparse
import asyncio
import json

import websockets


def _render(payload: dict) -> str:
    event_type = payload.get("type", "unknown")
    body = payload.get("payload", {})
    if event_type == "scan_progress":
        return (
            f"[main] {body.get('state')} {body.get('stage')} "
            f"{body.get('files_scanned')} files threats={body.get('threats')} "
            f"file={body.get('current_file')}"
        )
    if event_type == "drive_mounted":
        return f"[aux-left] {body.get('label') or body.get('device')} {body.get('filesystem')}"
    if event_type == "drive_removed":
        return "[aux-left] Drive removed"
    if event_type == "threat_detected":
        return f"[main] THREAT {body.get('signature')} in {body.get('file_path')}"
    if event_type == "scan_completed":
        return (
            f"[main] complete {body.get('status')} "
            f"{body.get('files_scanned')} files threats={body.get('threats')}"
        )
    if event_type == "scan_started":
        return f"[main] started {body.get('mode')} scan_id={body.get('scan_id')}"
    return f"[event] {event_type} {json.dumps(body, sort_keys=True)}"


async def run(url: str) -> None:
    print(f"Connecting to {url}")
    async with websockets.connect(url) as websocket:
        print("Display simulator ready. Ctrl+C to exit.")
        while True:
            message = await websocket.recv()
            payload = json.loads(message)
            print(_render(payload))


def main() -> None:
    parser = argparse.ArgumentParser(description="Portable AV display simulator")
    parser.add_argument(
        "--url",
        default="ws://127.0.0.1:8080/api/v1/scan/events",
        help="WebSocket event stream URL",
    )
    args = parser.parse_args()
    try:
        asyncio.run(run(args.url))
    except KeyboardInterrupt:
        print("\nSimulator stopped.")


if __name__ == "__main__":
    main()
