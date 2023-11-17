# qasync

[![Maintenance](https://img.shields.io/maintenance/yes/2023)](https://pypi.org/project/qasync)
[![PyPI](https://img.shields.io/pypi/v/qasync)](https://pypi.org/project/qasync)
[![PyPI - License](https://img.shields.io/pypi/l/qasync)](/LICENSE)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/qasync)](https://pypi.org/project/qasync)
[![PyPI - Download](https://img.shields.io/pypi/dm/qasync)](https://pypi.org/project/qasync)
[![GitHub Workflow Status](https://img.shields.io/github/actions/workflow/status/CabbageDevelopment/qasync/main.yml)](https://github.com/CabbageDevelopment/qasync/actions/workflows/main.yml)

## Introduction

`qasync` allows coroutines to be used in PyQt/PySide applications by providing an implementation of the `PEP 3156` event loop.

With `qasync`, you can use `asyncio` functionalities directly inside Qt app's event loop, in the main thread. Using async functions for Python tasks can be much easier and cleaner than using `threading.Thread` or `QThread`.

If you need some CPU-intensive tasks to be executed in parallel, `qasync` also got that covered, providing `QEventLoop.run_in_executor` which is functionally identical to that of `asyncio`.

### Basic Example

```python
import sys
import asyncio

from qasync import QEventLoop, QApplication
from PySide6.QtWidgets import QWidget, QVBoxLayout

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.setLayout(QVBoxLayout())
        self.lbl_status = QLabel("Idle", self)
        self.layout().addWidget(self.lbl_status)

    @asyncClose
    async def closeEvent(self, event):
        pass

    @asyncSlot()
    async def onMyEvent(self):
        pass


if __name__ == "__main__":
    app = QApplication(sys.argv)

    event_loop = QEventLoop(app)
    asyncio.set_event_loop(event_loop)

    app_close_event = asyncio.Event()
    app.aboutToQuit.connect(app_close_event.set)

    main_window = MainWindow()
    main_window.show()

    with event_loop:
        event_loop.run_until_complete(app_close_event.wait())
```

More detailed examples can be found [here](https://github.com/CabbageDevelopment/qasync/tree/master/examples).

### The Future of `qasync`

`qasync` is a fork of [asyncqt](https://github.com/gmarull/asyncqt), which is a fork of [quamash](https://github.com/harvimt/quamash). `qasync` was created because those are no longer maintained. May it live longer than its predecessors.

**`qasync` will continue to be maintained, and will still be accepting pull requests.**

## Requirements

- Python >= 3.8
- PyQt5/PyQt6 or PySide2/PySide6

`qasync` is tested on Ubuntu, Windows and MacOS.

If you need Python 3.6 or 3.7 support, use the [v0.25.0](https://github.com/CabbageDevelopment/qasync/releases/tag/v0.25.0) tag/release.

## Installation

To install `qasync`, use `pip`:

```
pip install qasync
```

## License

You may use, modify and redistribute this software under the terms of the [BSD License](http://opensource.org/licenses/BSD-2-Clause). See [LICENSE](/LICENSE).
