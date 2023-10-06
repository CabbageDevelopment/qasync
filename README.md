# qasync

[![Maintenance](https://img.shields.io/maintenance/yes/2023)](https://pypi.org/project/qasync)
[![PyPI](https://img.shields.io/pypi/v/qasync)](https://pypi.org/project/qasync)
[![PyPI - License](https://img.shields.io/pypi/l/qasync)](/LICENSE)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/qasync)](https://pypi.org/project/qasync)
[![PyPI - Download](https://img.shields.io/pypi/dm/qasync)](https://pypi.org/project/qasync)
[![GitHub Workflow Status](https://img.shields.io/github/actions/workflow/status/CabbageDevelopment/qasync/main.yml)](https://github.com/CabbageDevelopment/qasync/actions/workflows/main.yml)

## Introduction

`qasync` allows coroutines to be used in PyQt/PySide applications by providing an implementation of the `PEP 3156` event-loop.

`qasync` is a fork of [asyncqt](https://github.com/gmarull/asyncqt), which is a fork of [quamash](https://github.com/harvimt/quamash). May it live longer than its predecessors.

#### The future of `qasync`

`qasync` was created because `asyncqt` and `quamash` are no longer maintained.

**`qasync` will continue to be maintained, and will still be accepting pull requests.**

## Requirements

`qasync` requires Python >= 3.8, and PyQt5/PyQt6 or PySide2/PySide6. The library is tested on Ubuntu, Windows and MacOS.

If you need Python 3.6 or 3.7 support, use the [v0.25.0](https://github.com/CabbageDevelopment/qasync/releases/tag/v0.25.0) tag/release.

## Installation

To install `qasync`, use `pip`:

```
pip install qasync
```

## License

You may use, modify and redistribute this software under the terms of the [BSD License](http://opensource.org/licenses/BSD-2-Clause). See [LICENSE](/LICENSE).
