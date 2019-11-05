import sys
import asyncio

import aiohttp
from qasync import QEventLoop, asyncSlot, asyncClose

# from PyQt5.QtWidgets import (
from PySide2.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QTextEdit, QPushButton,
    QVBoxLayout)


class MainWindow(QWidget):
    """Main window."""

    _DEF_URL = 'https://jsonplaceholder.typicode.com/todos/1'
    """str: Default URL."""

    _SESSION_TIMEOUT = 1.
    """float: Session timeout."""

    def __init__(self):
        super().__init__()

        self.setLayout(QVBoxLayout())

        self.lblStatus = QLabel('Idle', self)
        self.layout().addWidget(self.lblStatus)

        self.editUrl = QLineEdit(self._DEF_URL, self)
        self.layout().addWidget(self.editUrl)

        self.editResponse = QTextEdit('', self)
        self.layout().addWidget(self.editResponse)

        self.btnFetch = QPushButton('Fetch', self)
        self.btnFetch.clicked.connect(self.on_btnFetch_clicked)
        self.layout().addWidget(self.btnFetch)

        self.session = aiohttp.ClientSession(
            loop=asyncio.get_event_loop(),
            timeout=aiohttp.ClientTimeout(total=self._SESSION_TIMEOUT))

    @asyncClose
    async def closeEvent(self, event):
        await self.session.close()

    @asyncSlot()
    async def on_btnFetch_clicked(self):
        self.btnFetch.setEnabled(False)
        self.lblStatus.setText('Fetching...')

        try:
            async with self.session.get(self.editUrl.text()) as r:
                self.editResponse.setText(await r.text())
        except Exception as exc:
            self.lblStatus.setText('Error: {}'.format(exc))
        else:
            self.lblStatus.setText('Finished!')
        finally:
            self.btnFetch.setEnabled(True)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    mainWindow = MainWindow()
    mainWindow.show()

    with loop:
        sys.exit(loop.run_forever())