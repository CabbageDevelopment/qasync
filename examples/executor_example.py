import sys
import asyncio
import time

# from PyQt5.QtWidgets import (
from PySide2.QtWidgets import (
    QApplication, QProgressBar)
from qasync import QEventLoop, QThreadExecutor


async def master():
    progress = QProgressBar()
    progress.setRange(0, 99)
    progress.show()

    await first_50()
    loop = asyncio.get_running_loop()
    with QThreadExecutor(1) as exec:
        await loop.run_in_executor(exec, last_50, loop)


async def first_50():
    for i in range(50):
        progress.setValue(i)
        await asyncio.sleep(.1)


def last_50(loop):
    for i in range(50, 100):
        loop.call_soon_threadsafe(progress.setValue, i)
        time.sleep(.1)


qasync.run(master())
