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

    _DEF_URL: str = "https://jsonplaceholder.typicode.com/todos/1"
    """Default URL."""

    def __init__(self):
        super().__init__()

        self.setLayout(QVBoxLayout())

        self.lbl_status = QLabel("Idle", self)
        self.layout().addWidget(self.lbl_status)

        self.edit_url = QLineEdit(self._DEF_URL, self)
        self.layout().addWidget(self.edit_url)

        self.edit_response = QTextEdit("", self)
        self.layout().addWidget(self.edit_response)

        self.btn_fetch = QPushButton("Fetch", self)
        self.btn_fetch.clicked.connect(self.on_btn_fetch_clicked)
        self.layout().addWidget(self.btn_fetch)

        self.session: aiohttp.ClientSession

    @asyncClose
    async def closeEvent(self, event):  # noqa:N802
        await self.session.close()

    async def boot(self):
        self.session = aiohttp.ClientSession()

    @asyncSlot()
    async def on_btn_fetch_clicked(self):
        self.btn_fetch.setEnabled(False)
        self.lbl_status.setText("Fetching...")

        try:
            async with self.session.get(self.edit_url.text()) as r:
                self.edit_response.setText(await r.text())
        except Exception as exc:
            self.lbl_status.setText("Error: {}".format(exc))
        else:
            self.lbl_status.setText("Finished!")
        finally:
            self.btn_fetch.setEnabled(True)


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

    event_loop.create_task(main_window.boot())
    event_loop.run_until_complete(keep_app_lifecycle())
    event_loop.close()
