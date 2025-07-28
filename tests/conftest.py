"""
Copyright (c) 2018 Gerard Marull-Paretas <gerard@teslabs.com>
Copyright (c) 2014 Mark Harviston <mark.harviston@gmail.com>
Copyright (c) 2014 Arve Knudsen <arve.knudsen@gmail.com>

BSD License
"""

import logging
import os

from pytest import fixture

logging.basicConfig(
    level=logging.DEBUG, format="%(levelname)s\t%(filename)s:%(lineno)s %(message)s"
)


if os.name == "nt":
    collect_ignore = ["qasync/_unix.py"]
else:
    collect_ignore = ["qasync/_windows.py"]


@fixture(scope="session")
def application():
    from qasync import QApplication

    return QApplication([])
