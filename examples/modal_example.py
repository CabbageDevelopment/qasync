import asyncio
import sys

# from PyQt6.QtWidgets import
from PySide6.QtWidgets import QApplication, QMessageBox, QProgressBar

from qasync import QEventLoop, asyncWrap


async def master():
    progress = QProgressBar()
    progress.setRange(0, 99)
    progress.show()
    await first_50(progress)


async def first_50(progress):
    for i in range(50):
        progress.setValue(i)
        await asyncio.sleep(0.1)

    # Schedule the last 50% to run asynchronously
    asyncio.create_task(last_50(progress))

    # create a notification box, use helper to make entering event loop safe.
    result = await asyncWrap(
        lambda: QMessageBox.information(
            None, "Task Completed", "The first 50% of the task is completed."
        )
    )
    assert result == QMessageBox.StandardButton.Ok


async def last_50(progress):
    for i in range(50, 100):
        progress.setValue(i)
        await asyncio.sleep(0.1)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    event_loop = QEventLoop(app)
    asyncio.set_event_loop(event_loop)

    event_loop.run_until_complete(master())
    event_loop.close()
