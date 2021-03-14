import functools
import sys
import asyncio
import time
import qasync

# from PyQt5.QtWidgets import (
from PySide2.QtWidgets import QApplication, QProgressBar
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


qasync.run(master())
