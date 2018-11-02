# © 2018 Gerard Marull-Paretas <gerard@teslabs.com>
# © 2014 Mark Harviston <mark.harviston@gmail.com>
# © 2014 Arve Knudsen <arve.knudsen@gmail.com>
# BSD License

import os
import logging
from pytest import fixture


logging.basicConfig(
    level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')


if os.name == 'nt':
    collect_ignore = ['quamash/_unix.py']
else:
    collect_ignore = ['quamash/_windows.py']


@fixture(scope='session')
def application():
    from asyncqt import QApplication
    return QApplication([])
