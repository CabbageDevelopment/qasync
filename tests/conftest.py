"""
Copyright (c) 2018 Gerard Marull-Paretas <gerard@teslabs.com>
Copyright (c) 2014 Mark Harviston <mark.harviston@gmail.com>
Copyright (c) 2014 Arve Knudsen <arve.knudsen@gmail.com>

BSD License
"""

import logging

from pytest import fixture

logging.basicConfig(
    level=logging.DEBUG, format="%(levelname)s\t%(filename)s:%(lineno)s %(message)s"
)


@fixture(scope="session")
def application():
    from qasync import QApplication

    return QApplication([])
