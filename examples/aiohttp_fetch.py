import asyncio
import functools
import sys

import aiohttp

# from PyQt5.QtWidgets import (
from PySide2.QtWidgets import (
    QWidget,
    QLabel,
    QLineEdit,
    QTextEdit,
    QPushButton,
    QVBoxLayout,
)

import qasync
from qasync import asyncSlot, asyncClose, QApplication


class MainWindow(QWidget):
    """Main window."""

    _DEF_URL = "https://jsonplaceholder.typicode.com/todos/1"
    """str: Default URL."""

    _SESSION_TIMEOUT = 1.0
    """float: Session timeout."""

    def __init__(self):
        super().__init__()

        self.setLayout(QVBoxLayout())

        self.lblStatus = QLabel("Idle", self)
        self.layout().addWidget(self.lblStatus)

        self.editUrl = QLineEdit(self._DEF_URL, self)
        self.layout().addWidget(self.editUrl)

        self.editResponse = QTextEdit("", self)
        self.layout().addWidget(self.editResponse)

        self.btnFetch = QPushButton("Fetch", self)
        self.btnFetch.clicked.connect(self.on_btnFetch_clicked)
        self.layout().addWidget(self.btnFetch)

        self.session = aiohttp.ClientSession(
            loop=asyncio.get_event_loop(),
            timeout=aiohttp.ClientTimeout(total=self._SESSION_TIMEOUT),
        )

    @asyncClose
    async def closeEvent(self, event):
        await self.session.close()

    @asyncSlot()
    async def on_btnFetch_clicked(self):
        self.btnFetch.setEnabled(False)
        self.lblStatus.setText("Fetching...")

        try:
            async with self.session.get(self.editUrl.text()) as r:
                self.editResponse.setText(await r.text())
        except Exception as exc:
            self.lblStatus.setText("Error: {}".format(exc))
        else:
            self.lblStatus.setText("Finished!")
        finally:
            self.btnFetch.setEnabled(True)


async def main():
    def close_future(future, loop):
        loop.call_later(10, future.cancel)
        future.cancel()

    loop = asyncio.get_event_loop()
    future = asyncio.Future()

    app = QApplication.instance()
    if hasattr(app, "aboutToQuit"):
        getattr(app, "aboutToQuit").connect(
            functools.partial(close_future, future, loop)
        )

    mainWindow = MainWindow()
    mainWindow.show()

    await future
    return True


if __name__ == "__main__":
    try:
        qasync.run(main())
    except asyncio.exceptions.CancelledError:
        sys.exit(0)
