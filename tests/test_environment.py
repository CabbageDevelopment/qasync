"""
BSD License
"""

import importlib
import sys
import types

import pytest
from pytest import MonkeyPatch

from qasync import QT_ALL, _get_qt_flavor


def _purge_qt(mp: MonkeyPatch):
    """Ensure no Qt modules are loaded."""
    for name in QT_ALL:
        mp.delitem(sys.modules, name, raising=False)


def _stub_import(mp: MonkeyPatch, available=()):
    """Patch importlib.import_module to only 'exist' for certain modules."""

    def fake_import(name):
        if name in available:
            return types.ModuleType(name)
        raise ImportError

    mp.setattr(importlib, "import_module", fake_import)


def test_env_exact():
    with MonkeyPatch.context() as mp:
        _purge_qt(mp)
        _stub_import(mp)
        mp.setenv("QT_API", "PySide6")
        assert _get_qt_flavor() == "PySide6"


def test_env_invalid_raises():
    with MonkeyPatch.context() as mp:
        _purge_qt(mp)
        _stub_import(mp)
        mp.setenv("QT_API", "QT")
        with pytest.raises(ImportError):
            _get_qt_flavor()


def test_already_imported_precedence():
    with MonkeyPatch.context() as mp:
        _purge_qt(mp)
        _stub_import(mp)
        mp.delenv("QT_API", raising=False)
        mp.setitem(sys.modules, "PySide2", types.ModuleType("PySide2"))
        mp.setitem(sys.modules, "PyQt5", types.ModuleType("PyQt5"))
        assert _get_qt_flavor() == next(n for n in QT_ALL if n in ("PyQt5", "PySide2"))


def test_first_available_import():
    with MonkeyPatch.context() as mp:
        _purge_qt(mp)
        _stub_import(mp, available=("PySide6",))
        mp.delenv("QT_API", raising=False)
        assert _get_qt_flavor() == "PySide6"


def test_none_available_raises():
    with MonkeyPatch.context() as mp:
        _purge_qt(mp)
        _stub_import(mp)
        mp.delenv("QT_API", raising=False)
        with pytest.raises(ImportError):
            _get_qt_flavor()


def test_env_overrides_imported():
    with MonkeyPatch.context() as mp:
        _purge_qt(mp)
        _stub_import(mp)
        mp.setitem(sys.modules, "PyQt6", types.ModuleType("PyQt6"))
        mp.setenv("QT_API", "PySide2")
        assert _get_qt_flavor() == "PySide2"
