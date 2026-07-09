from __future__ import annotations

import asyncio
from contextlib import suppress

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from portable_av.api.dependencies import AppState
from portable_av.engine.event_bus import EventEnvelope

router = APIRouter(tags=["websocket"])


def _serialize_event(event: EventEnvelope) -> dict:
    return {
        "type": event.type,
        "timestamp": event.timestamp.isoformat(),
        "sequence": event.sequence,
        "payload": event.payload,
    }


@router.websocket("/scan/events")
async def scan_events(websocket: WebSocket) -> None:
    await websocket.accept()
    state: AppState = websocket.app.state.app_state
    latest = state.event_bus.latest_snapshot()
    if latest is not None:
        await websocket.send_json(_serialize_event(latest))

    async def forward_events() -> None:
        async for event in state.event_bus.subscribe():
            await websocket.send_json(_serialize_event(event))

    forward_task = asyncio.create_task(forward_events())
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        forward_task.cancel()
        with suppress(asyncio.CancelledError):
            await forward_task
