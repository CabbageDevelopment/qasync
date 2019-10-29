"""
Implementation of the PEP 3156 Event-Loop with Qt.

Copyright (c) 2018 Gerard Marull-Paretas <gerard@teslabs.com>
Copyright (c) 2014 Mark Harviston <mark.harviston@gmail.com>
Copyright (c) 2014 Arve Knudsen <arve.knudsen@gmail.com>

BSD License
"""

__author__ = ('Gerard Marull-Paretas <gerard@teslabs.com>, '
              'Mark Harviston <mark.harviston@gmail.com>, '
              'Arve Knudsen <arve.knudsen@gmail.com>')
__version__ = '0.8.0.dev0'
__url__ = 'https://github.com/gmarull/asyncqt'
__license__ = 'BSD'
__all__ = ['QEventLoop', 'QThreadExecutor', 'asyncSlot', 'asyncClose']

import sys
import os
import asyncio
import time
import itertools
from queue import Queue
from concurrent.futures import Future
import logging
import importlib
import functools


logger = logging.getLogger(__name__)


try:
    QtModuleName = os.environ['QT_API']
except KeyError:
    QtModule = None
else:
    logger.info('Forcing use of {} as Qt Implementation'.format(QtModuleName))
    QtModule = importlib.import_module(QtModuleName)

if not QtModule:
    for QtModuleName in ('PyQt5', 'PySide2'):
        try:
            QtModule = importlib.import_module(QtModuleName)
        except ImportError:
            continue
        else:
            break
    else:
        raise ImportError('No Qt implementations found')

logger.info('Using Qt Implementation: {}'.format(QtModuleName))

QtCore = importlib.import_module(QtModuleName + '.QtCore', package=QtModuleName)
QtGui = importlib.import_module(QtModuleName + '.QtGui', package=QtModuleName)
if QtModuleName == 'PyQt5':
    from PyQt5 import QtWidgets
    from PyQt5.QtCore import pyqtSlot as Slot
    QApplication = QtWidgets.QApplication
elif QtModuleName == 'PySide2':
    from PySide2 import QtWidgets
    from PySide2.QtCore import Slot
    QApplication = QtWidgets.QApplication


from ._common import with_logger  # noqa


@with_logger
class _QThreadWorker(QtCore.QThread):

    """
    Read jobs from the queue and then execute them.

    For use by the QThreadExecutor
    """

    def __init__(self, queue, num):
        self.__queue = queue
        self.__stop = False
        self.__num = num
        super().__init__()

    def run(self):
        queue = self.__queue
        while True:
            command = queue.get()
            if command is None:
                # Stopping...
                break

            future, callback, args, kwargs = command
            self._logger.debug(
                '#{} got callback {} with args {} and kwargs {} from queue'
                .format(self.__num, callback, args, kwargs),
            )
            if future.set_running_or_notify_cancel():
                self._logger.debug('Invoking callback')
                try:
                    r = callback(*args, **kwargs)
                except Exception as err:
                    self._logger.debug('Setting Future exception: {}'.format(err))
                    future.set_exception(err)
                else:
                    self._logger.debug('Setting Future result: {}'.format(r))
                    future.set_result(r)
            else:
                self._logger.debug('Future was canceled')

        self._logger.debug('Thread #{} stopped'.format(self.__num))

    def wait(self):
        self._logger.debug('Waiting for thread #{} to stop...'.format(self.__num))
        super().wait()


@with_logger
class QThreadExecutor:

    """
    ThreadExecutor that produces QThreads.

    Same API as `concurrent.futures.Executor`

    >>> from asyncqt import QThreadExecutor
    >>> with QThreadExecutor(5) as executor:
    ...     f = executor.submit(lambda x: 2 + x, 2)
    ...     r = f.result()
    ...     assert r == 4
    """

    def __init__(self, max_workers=10):
        super().__init__()
        self.__max_workers = max_workers
        self.__queue = Queue()
        self.__workers = [_QThreadWorker(self.__queue, i + 1) for i in range(max_workers)]
        self.__been_shutdown = False

        for w in self.__workers:
            w.start()

    def submit(self, callback, *args, **kwargs):
        if self.__been_shutdown:
            raise RuntimeError("QThreadExecutor has been shutdown")

        future = Future()
        self._logger.debug(
            'Submitting callback {} with args {} and kwargs {} to thread worker queue'
            .format(callback, args, kwargs))
        self.__queue.put((future, callback, args, kwargs))
        return future

    def map(self, func, *iterables, timeout=None):
        raise NotImplementedError("use as_completed on the event loop")

    def shutdown(self, wait=True):
        if self.__been_shutdown:
            raise RuntimeError("QThreadExecutor has been shutdown")

        self.__been_shutdown = True

        self._logger.debug('Shutting down')
        for i in range(len(self.__workers)):
            # Signal workers to stop
            self.__queue.put(None)
        if wait:
            for w in self.__workers:
                w.wait()

    def __enter__(self, *args):
        if self.__been_shutdown:
            raise RuntimeError("QThreadExecutor has been shutdown")
        return self

    def __exit__(self, *args):
        self.shutdown()


def _make_signaller(qtimpl_qtcore, *args):
    class Signaller(qtimpl_qtcore.QObject):
        try:
            signal = qtimpl_qtcore.Signal(*args)
        except AttributeError:
            signal = qtimpl_qtcore.pyqtSignal(*args)
    return Signaller()


@with_logger
class _SimpleTimer(QtCore.QObject):
    def __init__(self):
        super().__init__()
        self.__callbacks = {}
        self._stopped = False

    def add_callback(self, handle, delay=0):
        timerid = self.startTimer(delay * 1000)
        self._logger.debug("Registering timer id {0}".format(timerid))
        assert timerid not in self.__callbacks
        self.__callbacks[timerid] = handle
        return handle

    def timerEvent(self, event):  # noqa: N802
        timerid = event.timerId()
        self._logger.debug("Timer event on id {0}".format(timerid))
        if self._stopped:
            self._logger.debug("Timer stopped, killing {}".format(timerid))
            self.killTimer(timerid)
            del self.__callbacks[timerid]
        else:
            try:
                handle = self.__callbacks[timerid]
            except KeyError as e:
                self._logger.debug(str(e))
                pass
            else:
                if handle._cancelled:
                    self._logger.debug("Handle {} cancelled".format(handle))
                else:
                    self._logger.debug("Calling handle {}".format(handle))
                    handle._run()
            finally:
                del self.__callbacks[timerid]
                handle = None
            self.killTimer(timerid)

    def stop(self):
        self._logger.debug("Stopping timers")
        self._stopped = True


@with_logger
class _QEventLoop:

    """
    Implementation of asyncio event loop that uses the Qt Event loop.

    >>> import asyncio
    >>>
    >>> app = getfixture('application')
    >>>
    >>> async def xplusy(x, y):
    ...     await asyncio.sleep(.1)
    ...     assert x + y == 4
    ...     await asyncio.sleep(.1)
    >>>
    >>> loop = QEventLoop(app)
    >>> asyncio.set_event_loop(loop)
    >>> with loop:
    ...     loop.run_until_complete(xplusy(2, 2))
    """

    def __init__(self, app=None, set_running_loop=True):
        self.__app = app or QApplication.instance()
        assert self.__app is not None, 'No QApplication has been instantiated'
        self.__is_running = False
        self.__debug_enabled = False
        self.__default_executor = None
        self.__exception_handler = None
        self._read_notifiers = {}
        self._write_notifiers = {}
        self._timer = _SimpleTimer()

        self.__call_soon_signaller = signaller = _make_signaller(QtCore, object, tuple)
        self.__call_soon_signal = signaller.signal
        signaller.signal.connect(lambda callback, args: self.call_soon(callback, *args))

        assert self.__app is not None
        super().__init__()
        
        if set_running_loop:
            asyncio.events._set_running_loop(self)

    def run_forever(self):
        """Run eventloop forever."""
        self.__is_running = True
        self._before_run_forever()

        try:
            self._logger.debug('Starting Qt event loop')
            rslt = self.__app.exec_()
            self._logger.debug('Qt event loop ended with result {}'.format(rslt))
            return rslt
        finally:
            self._after_run_forever()
            self.__is_running = False

    def run_until_complete(self, future):
        """Run until Future is complete."""
        self._logger.debug('Running {} until complete'.format(future))
        future = asyncio.ensure_future(future, loop=self)

        def stop(*args): self.stop()  # noqa
        future.add_done_callback(stop)
        try:
            self.run_forever()
        finally:
            future.remove_done_callback(stop)
        self.__app.processEvents()  # run loop one last time to process all the events
        if not future.done():
            raise RuntimeError('Event loop stopped before Future completed.')

        self._logger.debug('Future {} finished running'.format(future))
        return future.result()

    def stop(self):
        """Stop event loop."""
        if not self.__is_running:
            self._logger.debug('Already stopped')
            return

        self._logger.debug('Stopping event loop...')
        self.__is_running = False
        self.__app.exit()
        self._logger.debug('Stopped event loop')

    def is_running(self):
        """Return True if the event loop is running, False otherwise."""
        return self.__is_running

    def close(self):
        """
        Release all resources used by the event loop.

        The loop cannot be restarted after it has been closed.
        """
        if self.is_running():
            raise RuntimeError("Cannot close a running event loop")
        if self.is_closed():
            return

        self._logger.debug('Closing event loop...')
        if self.__default_executor is not None:
            self.__default_executor.shutdown()

        super().close()

        self._timer.stop()
        self.__app = None

        for notifier in itertools.chain(self._read_notifiers.values(), self._write_notifiers.values()):
            notifier.setEnabled(False)

        self._read_notifiers = None
        self._write_notifiers = None

    def call_later(self, delay, callback, *args, context=None):
        """Register callback to be invoked after a certain delay."""
        if asyncio.iscoroutinefunction(callback):
            raise TypeError("coroutines cannot be used with call_later")
        if not callable(callback):
            raise TypeError('callback must be callable: {}'.format(type(callback).__name__))

        self._logger.debug(
            'Registering callback {} to be invoked with arguments {} after {} second(s)'
            .format(callback, args, delay))

        if sys.version_info >= (3, 7):
            return self._add_callback(asyncio.Handle(callback, args, self, context=context), delay)
        return self._add_callback(asyncio.Handle(callback, args, self), delay)

    def _add_callback(self, handle, delay=0):
        return self._timer.add_callback(handle, delay)

    def call_soon(self, callback, *args, context=None):
        """Register a callback to be run on the next iteration of the event loop."""
        return self.call_later(0, callback, *args, context=context)

    def call_at(self, when, callback, *args, context=None):
        """Register callback to be invoked at a certain time."""
        return self.call_later(when - self.time(), callback, *args, context=context)

    def time(self):
        """Get time according to event loop's clock."""
        return time.monotonic()

    def add_reader(self, fd, callback, *args):
        """Register a callback for when a file descriptor is ready for reading."""
        self._check_closed()

        try:
            existing = self._read_notifiers[fd]
        except KeyError:
            pass
        else:
            # this is necessary to avoid race condition-like issues
            existing.setEnabled(False)
            existing.activated.disconnect()
            # will get overwritten by the assignment below anyways

        notifier = QtCore.QSocketNotifier(fd, QtCore.QSocketNotifier.Read)
        notifier.setEnabled(True)
        self._logger.debug('Adding reader callback for file descriptor {}'.format(fd))
        notifier.activated.connect(
            lambda: self.__on_notifier_ready(
                self._read_notifiers, notifier, fd, callback, args)  # noqa: C812
        )
        self._read_notifiers[fd] = notifier

    def remove_reader(self, fd):
        """Remove reader callback."""
        if self.is_closed():
            return

        self._logger.debug('Removing reader callback for file descriptor {}'.format(fd))
        try:
            notifier = self._read_notifiers.pop(fd)
        except KeyError:
            return False
        else:
            notifier.setEnabled(False)
            return True

    def add_writer(self, fd, callback, *args):
        """Register a callback for when a file descriptor is ready for writing."""
        self._check_closed()
        try:
            existing = self._write_notifiers[fd]
        except KeyError:
            pass
        else:
            # this is necessary to avoid race condition-like issues
            existing.setEnabled(False)
            existing.activated.disconnect()
            # will get overwritten by the assignment below anyways

        notifier = QtCore.QSocketNotifier(fd, QtCore.QSocketNotifier.Write)
        notifier.setEnabled(True)
        self._logger.debug('Adding writer callback for file descriptor {}'.format(fd))
        notifier.activated.connect(
            lambda: self.__on_notifier_ready(
                self._write_notifiers, notifier, fd, callback, args)  # noqa: C812
        )
        self._write_notifiers[fd] = notifier

    def remove_writer(self, fd):
        """Remove writer callback."""
        if self.is_closed():
            return

        self._logger.debug('Removing writer callback for file descriptor {}'.format(fd))
        try:
            notifier = self._write_notifiers.pop(fd)
        except KeyError:
            return False
        else:
            notifier.setEnabled(False)
            return True

    def __notifier_cb_wrapper(self, notifiers, notifier, fd, callback, args):
        # This wrapper gets called with a certain delay. We cannot know
        # for sure that the notifier is still the current notifier for
        # the fd.
        if notifiers.get(fd, None) is not notifier:
            return
        try:
            callback(*args)
        finally:
            # The notifier might have been overriden by the
            # callback. We must not re-enable it in that case.
            if notifiers.get(fd, None) is notifier:
                notifier.setEnabled(True)
            else:
                notifier.activated.disconnect()

    def __on_notifier_ready(self, notifiers, notifier, fd, callback, args):
        if fd not in notifiers:
            self._logger.warning(
                'Socket notifier for fd {} is ready, even though it should be disabled, not calling {} and disabling'
                .format(fd, callback),
            )
            notifier.setEnabled(False)
            return

        # It can be necessary to disable QSocketNotifier when e.g. checking
        # ZeroMQ sockets for events
        assert notifier.isEnabled()
        self._logger.debug('Socket notifier for fd {} is ready'.format(fd))
        notifier.setEnabled(False)
        self.call_soon(
            self.__notifier_cb_wrapper,
            notifiers, notifier, fd, callback, args)

    # Methods for interacting with threads.

    def call_soon_threadsafe(self, callback, *args, context=None):
        """Thread-safe version of call_soon."""
        self.__call_soon_signal.emit(callback, args)

    def run_in_executor(self, executor, callback, *args):
        """Run callback in executor.

        If no executor is provided, the default executor will be used, which defers execution to
        a background thread.
        """
        self._logger.debug('Running callback {} with args {} in executor'.format(callback, args))
        if isinstance(callback, asyncio.Handle):
            assert not args
            assert not isinstance(callback, asyncio.TimerHandle)
            if callback._cancelled:
                f = asyncio.Future()
                f.set_result(None)
                return f
            callback, args = callback.callback, callback.args

        if executor is None:
            self._logger.debug('Using default executor')
            executor = self.__default_executor

        if executor is None:
            self._logger.debug('Creating default executor')
            executor = self.__default_executor = QThreadExecutor()

        return asyncio.wrap_future(executor.submit(callback, *args))

    def set_default_executor(self, executor):
        self.__default_executor = executor

    # Error handlers.

    def set_exception_handler(self, handler):
        self.__exception_handler = handler

    def default_exception_handler(self, context):
        """Handle exceptions.

        This is the default exception handler.

        This is called when an exception occurs and no exception
        handler is set, and can be called by a custom exception
        handler that wants to defer to the default behavior.

        context parameter has the same meaning as in
        `call_exception_handler()`.
        """
        self._logger.debug('Default exception handler executing')
        message = context.get('message')
        if not message:
            message = 'Unhandled exception in event loop'

        try:
            exception = context['exception']
        except KeyError:
            exc_info = False
        else:
            exc_info = (type(exception), exception, exception.__traceback__)

        log_lines = [message]
        for key in [k for k in sorted(context) if k not in {'message', 'exception'}]:
            log_lines.append('{}: {!r}'.format(key, context[key]))

        self.__log_error('\n'.join(log_lines), exc_info=exc_info)

    def call_exception_handler(self, context):
        if self.__exception_handler is None:
            try:
                self.default_exception_handler(context)
            except Exception:
                # Second protection layer for unexpected errors
                # in the default implementation, as well as for subclassed
                # event loops with overloaded "default_exception_handler".
                self.__log_error('Exception in default exception handler', exc_info=True)

            return

        try:
            self.__exception_handler(self, context)
        except Exception as exc:
            # Exception in the user set custom exception handler.
            try:
                # Let's try the default handler.
                self.default_exception_handler({
                    'message': 'Unhandled error in custom exception handler',
                    'exception': exc,
                    'context': context,
                })
            except Exception:
                # Guard 'default_exception_handler' in case it's
                # overloaded.
                self.__log_error(
                    'Exception in default exception handler while handling an unexpected error '
                    'in custom exception handler', exc_info=True)

    # Debug flag management.

    def get_debug(self):
        return self.__debug_enabled

    def set_debug(self, enabled):
        super().set_debug(enabled)
        self.__debug_enabled = enabled

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.stop()
        self.close()

    @classmethod
    def __log_error(cls, *args, **kwds):
        # In some cases, the error method itself fails, don't have a lot of options in that case
        try:
            cls._logger.error(*args, **kwds)
        except: # noqa E722
            sys.stderr.write('{!r}, {!r}\n'.format(args, kwds))


from ._unix import _SelectorEventLoop  # noqa
QSelectorEventLoop = type('QSelectorEventLoop', (_QEventLoop, _SelectorEventLoop), {})

if os.name == 'nt':
    from ._windows import _ProactorEventLoop
    QIOCPEventLoop = type('QIOCPEventLoop', (_QEventLoop, _ProactorEventLoop), {})
    QEventLoop = QIOCPEventLoop
else:
    QEventLoop = QSelectorEventLoop


class _Cancellable:
    def __init__(self, timer, loop):
        self.__timer = timer
        self.__loop = loop

    def cancel(self):
        self.__timer.stop()


def asyncClose(fn):
    """Allow to run async code before application is closed."""
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        f = asyncio.ensure_future(fn(*args, **kwargs))
        while not f.done():
            QApplication.instance().processEvents()

    return wrapper


def asyncSlot(*args):
    """Make a Qt async slot run on asyncio loop."""
    def outer_decorator(fn):
        @Slot(*args)
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            asyncio.ensure_future(fn(*args, **kwargs))
        return wrapper
    return outer_decorator
