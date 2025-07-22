import qasync
import asyncio

def test_run_with_contextmanager(application):
    async def coro():
        event_loop = asyncio.get_event_loop()
        assert type(event_loop).__name__ == "QSelectorEventLoop"
        await asyncio.sleep(0)

    qasync.run(coro())

    event_loop = asyncio.get_event_loop()
    assert type(event_loop).__name__ != "QSelectorEventLoop"
