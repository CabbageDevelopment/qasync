import asyncio
import os

import pytest

import qasync


def test_run_with_contextmanager(application):
    async def coro():
        event_loop = asyncio.get_event_loop()
        assert (
            type(event_loop).__name__ == "QIOCPEventLoop"
            if os.name == "nt"
            else "QSelectorEventLoop"
        )
        await asyncio.sleep(0)

    asyncio.set_event_loop(None)
    qasync.run(coro())

    with pytest.raises(RuntimeError):
        _ = asyncio.get_event_loop()
