asyncqt - asyncio + PyQt5/PySide2
======================

.. image:: https://travis-ci.org/gmarull/asyncqt.svg?branch=master
    :target: https://travis-ci.org/gmarull/asyncqt
    :alt: Build Status

.. image:: https://ci.appveyor.com/api/projects/status/s74qrypga40somf1?svg=true
    :target: https://ci.appveyor.com/project/gmarull/asyncqt
    :alt: Build Status

.. image:: https://codecov.io/gh/gmarull/asyncqt/branch/master/graph/badge.svg
    :target: https://codecov.io/gh/gmarull/asyncqt
    :alt: Coverage

.. image:: https://img.shields.io/pypi/v/asyncqt.svg
    :target: https://pypi.python.org/pypi/asyncqt
    :alt: PyPI Version

``asyncqt`` is an implementation of the ``PEP 3156`` event-loop with Qt. This
package is a fork of ``quamash`` focusing on modern Python versions, with
some extra utilities, examples and simplified CI.

Requirements
============

``asyncqt`` requires Python >= 3.5 and PyQt5 or PySide2. The Qt API can be
explicitely set by using the ``QT_API`` environment variable.

Installation
============

``pip install asyncqt``

Examples
========

You can find usage examples in the ``examples`` folder.
