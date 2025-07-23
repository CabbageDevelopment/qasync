import asyncio
import os

import pytest

import qasync

@pytest.fixture
def get_event_loop_coro(expected_loop):
    async def coro():
        event_loop = asyncio.get_event_loop()
        
        assert type(event_loop).__name__ == expected_loop
        await asyncio.sleep(0)
    return coro

@pytest.fixture
def expected_loop():
    return "QIOCPEventLoop" if os.name == "nt" else "QSelectorEventLoop"

def test_run_with_contextmanager(get_event_loop_coro):
    asyncio.set_event_loop(None)
    qasync.run(get_event_loop_coro())

    with pytest.raises(RuntimeError):
        _ = asyncio.get_event_loop()

def test_run_reset_policy(get_event_loop_coro, expected_loop):
    old_loop = asyncio.new_event_loop()
    qasync.run(get_event_loop_coro())
    new_loop = asyncio.new_event_loop()
    assert type(old_loop) == type(new_loop)
