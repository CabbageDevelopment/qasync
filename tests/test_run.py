import qasync
import asyncio

def test_run_with_contextmanager():
    async def coro():
        event_loop = asyncio.get_event_loop()
        assert type(event_loop).__name__ == "QSelectorEventLoop"
        await asyncio.sleep(0)

    app = QApplication([])
    qasync.run(coro())

    event_loop = asyncio.get_event_loop()
    assert type(event_loop).__name__ != "QSelectorEventLoop"
