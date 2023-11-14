import asyncio
import sys

import aiohttp

# from PyQt6.QtWidgets import (
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from qasync import QEventLoop, asyncClose, asyncSlot


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

        self.session = aiohttp.ClientSession()

    @asyncClose
    async def closeEvent(self, event):  # noqa:N802
        await self.session.close()

    @asyncSlot()
    async def on_btnFetch_clicked(self):  # noqa:N802
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


if __name__ == "__main__":
    app = QApplication(sys.argv)

    event_loop = QEventLoop(app)
    asyncio.set_event_loop(event_loop)
    app_close_event = asyncio.Event()

    main_window = MainWindow()
    main_window.show()

    def close_app():
        app_close_event.set()

    async def keep_app_lifecycle():
        await app_close_event.wait()

    app.aboutToQuit.connect(close_app)

    event_loop.run_until_complete(keep_app_lifecycle())
    event_loop.close()
