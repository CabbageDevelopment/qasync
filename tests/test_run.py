import qasync
import asyncio
from qasync import QApplication

def test_run_with_contextmanager(application):
    async def coro():
        event_loop = asyncio.get_event_loop()
        assert type(event_loop).__name__ == "QSelectorEventLoop"
        await asyncio.sleep(0)

    qasync.run(coro())

    try:
        event_loop = asyncio.get_event_loop()
    except:
        event_loop = None
    assert type(event_loop).__name__ != "QSelectorEventLoop"
