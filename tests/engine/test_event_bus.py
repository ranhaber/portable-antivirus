import asyncio

import pytest

from portable_av.engine.event_bus import EventBus


@pytest.mark.asyncio
async def test_event_bus_publish_and_subscribe() -> None:
    bus = EventBus()
    received = []

    async def consumer() -> None:
        async for event in bus.subscribe():
            received.append(event)
            if len(received) >= 1:
                break

    task = asyncio.create_task(consumer())
    await asyncio.sleep(0.01)
    await bus.publish("scan_started", {"scan_id": "test-1"})
    await task

    assert received[0].type == "scan_started"
    assert received[0].payload["scan_id"] == "test-1"
    assert received[0].sequence == 1
