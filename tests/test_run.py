import asyncio
import sys
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


@pytest.mark.skipif(sys.version_info < (3, 12), reason="Requires Python 3.12+")
def test_asyncio_run(application):
    """Test that QEventLoop is compatible with asyncio.run()"""
    done = False
    loop = None

    async def main():
        nonlocal done, loop
        assert loop.is_running()
        assert asyncio.get_running_loop() is loop
        await asyncio.sleep(0.01)
        done = True

    def factory():
        nonlocal loop
        loop = qasync.QEventLoop(application)
        return loop

    asyncio.run(main(), loop_factory=factory)
    assert done
    assert loop.is_closed()
    assert not loop.is_running()


@pytest.mark.skipif(sys.version_info < (3, 12), reason="Requires Python 3.12+")
def test_asyncio_run_cleanup(application):
    """Test that running tasks are cleaned up"""
    task = None
    cancelled = False

    async def main():
        nonlocal task, cancelled

        async def long_task():
            nonlocal cancelled
            try:
                await asyncio.sleep(10)
            except asyncio.CancelledError:
                cancelled = True

        task = asyncio.create_task(long_task())
        await asyncio.sleep(0.01)

    asyncio.run(main(), loop_factory=lambda: qasync.QEventLoop(application))
    assert cancelled


def test_qasync_run(application):
    """Test running with qasync.run()"""
    done = False
    loop = None

    async def main():
        nonlocal done, loop
        loop = asyncio.get_running_loop()
        assert loop.is_running()
        await asyncio.sleep(0.01)
        done = True

    # qasync.run uses an EventLoopPolicy to create the loop
    qasync.run(main())
    assert done
    assert loop.is_closed()
    assert not loop.is_running()
