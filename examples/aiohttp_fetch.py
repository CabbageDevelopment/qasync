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

    app_close_event = asyncio.Event()
    app.aboutToQuit.connect(app_close_event.set)

    main_window = MainWindow()
    main_window.show()

    async def async_main():
        asyncio.create_task(main_window.boot())
        await app_close_event.wait()

    # for 3.11 or older use qasync.run instead of asyncio.run
    # qasync.run(async_main())
    asyncio.run(async_main(), loop_factory=QEventLoop)
