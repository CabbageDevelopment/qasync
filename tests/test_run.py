import asyncio
from unittest.mock import ANY

import pytest

import qasync


@pytest.fixture
def get_event_loop_coro():
    async def coro(expected_debug):
        event_loop = asyncio.get_event_loop()
        assert type(event_loop) is qasync.QEventLoop
        assert event_loop.get_debug() == expected_debug
        await asyncio.sleep(0)

    return coro


def test_qasync_run_restores_loop(get_event_loop_coro):
    asyncio.set_event_loop(None)
    qasync.run(get_event_loop_coro(ANY))

    with pytest.raises(RuntimeError):
        _ = asyncio.get_event_loop()


def test_qasync_run_restores_policy(get_event_loop_coro):
    old_policy = asyncio.get_event_loop_policy()
    qasync.run(get_event_loop_coro(ANY))
    new_policy = asyncio.get_event_loop_policy()
    assert type(old_policy) is type(new_policy)


def test_qasync_run_with_debug_args(get_event_loop_coro):
    qasync.run(get_event_loop_coro(True), debug=True)
    qasync.run(get_event_loop_coro(False), debug=False)
