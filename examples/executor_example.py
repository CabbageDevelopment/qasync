import asyncio
import functools
import sys
import time

# from PyQt6.QtWidgets import
from PySide6.QtWidgets import QApplication, QProgressBar

from qasync import QEventLoop, QThreadExecutor


async def master():
    progress = QProgressBar()
    progress.setRange(0, 99)
    progress.show()

    await first_50(progress)
    loop = asyncio.get_running_loop()
    with QThreadExecutor(1) as exec:
        await loop.run_in_executor(exec, functools.partial(last_50, progress), loop)


async def first_50(progress):
    for i in range(50):
        progress.setValue(i)
        await asyncio.sleep(0.1)


def last_50(progress, loop):
    for i in range(50, 100):
        loop.call_soon_threadsafe(progress.setValue, i)
        time.sleep(0.1)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # for 3.11 or older use qasync.run instead of asyncio.run
    # qasync.run(master())
    asyncio.run(master(), loop_factory=QEventLoop)
