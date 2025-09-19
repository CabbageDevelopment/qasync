# qasync

[![Maintenance](https://img.shields.io/maintenance/yes/2025)](https://pypi.org/project/qasync)
[![PyPI](https://img.shields.io/pypi/v/qasync)](https://pypi.org/project/qasync)
[![PyPI - License](https://img.shields.io/pypi/l/qasync)](/LICENSE)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/qasync)](https://pypi.org/project/qasync)
[![PyPI - Download](https://img.shields.io/pypi/dm/qasync)](https://pypi.org/project/qasync)
[![GitHub Workflow Status](https://img.shields.io/github/actions/workflow/status/CabbageDevelopment/qasync/main.yml)](https://github.com/CabbageDevelopment/qasync/actions/workflows/main.yml)

## Introduction

`qasync` allows coroutines to be used in PyQt/PySide applications by providing an implementation of the `PEP 3156` event loop.

With `qasync`, you can use `asyncio` functionalities directly inside Qt app's event loop, in the main thread. Using async functions for Python tasks can be much easier and cleaner than using `threading.Thread` or `QThread`.

If you need some CPU-intensive tasks to be executed in parallel, `qasync` also got that covered, providing `QEventLoop.run_in_executor` which is functionally identical to that of `asyncio`. By default `QThreadExecutor` is used, but any class implementing the `concurrent.futures.Executor` interface will do the job.

### Basic Example

```python
import asyncio
import sys

from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QApplication, QPushButton, QVBoxLayout, QWidget

import qasync
from qasync import QEventLoop, asyncClose, asyncSlot


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout()
        self.button = QPushButton("Load", self)
        self.button.clicked.connect(self.onButtonClicked)
        layout.addWidget(self.button)
        self.setLayout(layout)

    @asyncSlot()
    async def onButtonClicked(self):
        """
        Use async code in a slot by decorating it with @asyncSlot.
        """
        self.button.setText("Loading...")
        await asyncio.sleep(1)
        self.button.setText("Load")

    @asyncClose
    async def closeEvent(self, event: QCloseEvent):
        """
        Use async code in a closeEvent by decorating it with @asyncClose.
        """
        self.button.setText("Closing...")
        await asyncio.sleep(1)


async def main(app):
    app_close_event = asyncio.Event()
    app.aboutToQuit.connect(app_close_event.set)
    main_window = MainWindow()
    main_window.show()
    await app_close_event.wait()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    # for python 3.11 or newer
    asyncio.run(main(app), loop_factory=QEventLoop)
    # for python 3.10 or older
    # qasync.run(main(app))
```

More detailed examples can be found in the [examples](./examples/) directory.

### The Future of `qasync`

`qasync` is a fork of [asyncqt](https://github.com/gmarull/asyncqt), which is a fork of [quamash](https://github.com/harvimt/quamash). `qasync` was created because those are no longer maintained. May it live longer than its predecessors.

**`qasync` will continue to be maintained, and will still be accepting pull requests.**

## Requirements

- Python >=3.8, <3.14
- PyQt5/PyQt6 or PySide2/PySide6

`qasync` is tested on Ubuntu, Windows and MacOS.

If you need Python 3.6 or 3.7 support, use the [v0.25.0](https://github.com/CabbageDevelopment/qasync/releases/tag/v0.25.0) tag/release.

## Installation

To install using `uv`:

```bash
uv add qasync
```

To install using `pip`:

```bash
pip install qasync
```

## License

You may use, modify and redistribute this software under the terms of the [BSD License](http://opensource.org/licenses/BSD-2-Clause). See [LICENSE](/LICENSE).
