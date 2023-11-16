"""
Implementation of the PEP 3156 Event-Loop with Qt.

Copyright (c) 2018 Gerard Marull-Paretas <gerard@teslabs.com>
Copyright (c) 2014 Mark Harviston <mark.harviston@gmail.com>
Copyright (c) 2014 Arve Knudsen <arve.knudsen@gmail.com>

BSD License
"""

__author__ = (
    "Sam McCormack",
    "Gerard Marull-Paretas <gerard@teslabs.com>, "
    "Mark Harviston <mark.harviston@gmail.com>, "
    "Arve Knudsen <arve.knudsen@gmail.com>",
)
__all__ = ["QEventLoop", "QThreadExecutor", "asyncSlot", "asyncClose"]

import asyncio
import contextlib
import functools
import importlib
import inspect
import itertools
import logging
import os
import sys
import time
from concurrent.futures import Future
from queue import Queue

logger = logging.getLogger(__name__)

QtModule = None

# If QT_API env variable is given, use that or fail trying
qtapi_env = os.getenv("QT_API", "").strip().lower()
if qtapi_env:
    env_to_mod_map = {
        "pyqt5": "PyQt5",
        "pyqt6": "PyQt6",
        "pyqt": "PyQt4",
        "pyqt4": "PyQt4",
        "pyside6": "PySide6",
        "pyside2": "PySide2",
        "pyside": "PySide",
    }
    if qtapi_env in env_to_mod_map:
        QtModuleName = env_to_mod_map[qtapi_env]
    else:
        raise ImportError(
            "QT_API environment variable set ({}) but not one of [{}].".format(
                qtapi_env, ", ".join(env_to_mod_map.keys())
            )
        )

    logger.info("Forcing use of {} as Qt Implementation".format(QtModuleName))
    QtModule = importlib.import_module(QtModuleName)

# If a Qt lib is already imported, use that
if not QtModule:
    for QtModuleName in ("PyQt5", "PyQt6", "PySide2", "PySide6"):
        if QtModuleName in sys.modules:
            QtModule = sys.modules[QtModuleName]
            break

# Try importing qt libs
if not QtModule:
    for QtModuleName in ("PyQt5", "PyQt6", "PySide2", "PySide6"):
        try:
            QtModule = importlib.import_module(QtModuleName)
        except ImportError:
            continue
        else:
            break

if not QtModule:
    raise ImportError("No Qt implementations found")

QtCore = importlib.import_module(QtModuleName + ".QtCore", package=QtModuleName)
QtGui = importlib.import_module(QtModuleName + ".QtGui", package=QtModuleName)

if QtModuleName == "PyQt5":
    from PyQt5 import QtWidgets
    from PyQt5.QtCore import pyqtSlot as Slot

    QApplication = QtWidgets.QApplication

elif QtModuleName == "PyQt6":
    from PyQt6 import QtWidgets
    from PyQt6.QtCore import pyqtSlot as Slot

    QApplication = QtWidgets.QApplication

elif QtModuleName == "PySide2":
    from PySide2 import QtWidgets
    from PySide2.QtCore import Slot

    QApplication = QtWidgets.QApplication

elif QtModuleName == "PySide6":
    from PySide6 import QtWidgets
    from PySide6.QtCore import Slot

    QApplication = QtWidgets.QApplication

from ._common import with_logger  # noqa


@with_logger
class _QThreadWorker(QtCore.QThread):
    """
    Read jobs from the queue and then execute them.

    For use by the QThreadExecutor
    """

    def __init__(self, queue, num, stackSize=None):
        self.__queue = queue
        self.__stop = False
        self.__num = num
        super().__init__()
        if stackSize is not None:
            self.setStackSize(stackSize)

    def run(self):
        queue = self.__queue
        while True:
            command = queue.get()
            if command is None:
                # Stopping...
                break

            future, callback, args, kwargs = command
            self._logger.debug(
                "#%s got callback %s with args %s and kwargs %s from queue",
                self.__num,
                callback,
                args,
                kwargs,
            )
            if future.set_running_or_notify_cancel():
                self._logger.debug("Invoking callback")
                try:
                    r = callback(*args, **kwargs)
                except Exception as err:
                    self._logger.debug("Setting Future exception: %s", err)
                    future.set_exception(err)
                else:
                    self._logger.debug("Setting Future result: %s", r)
                    future.set_result(r)
            else:
                self._logger.debug("Future was canceled")

        self._logger.debug("Thread #%s stopped", self.__num)

    def wait(self):
        self._logger.debug("Waiting for thread #%s to stop...", self.__num)
        super().wait()


@with_logger
class QThreadExecutor:
    """
    ThreadExecutor that produces QThreads.

    Same API as `concurrent.futures.Executor`

    >>> from qasync import QThreadExecutor
    >>> with QThreadExecutor(5) as executor:
    ...     f = executor.submit(lambda x: 2 + x, 2)
    ...     r = f.result()
    ...     assert r == 4
    """

    def __init__(self, max_workers=10, stack_size=None):
        super().__init__()
        self.__max_workers = max_workers
        self.__queue = Queue()
        if stack_size is None:
            # Match cpython/Python/thread_pthread.h
            if sys.platform.startswith("darwin"):
                stack_size = 16 * 2**20
            elif sys.platform.startswith("freebsd"):
                stack_size = 4 * 2**20
            elif sys.platform.startswith("aix"):
                stack_size = 2 * 2**20
        self.__workers = [
            _QThreadWorker(self.__queue, i + 1, stack_size) for i in range(max_workers)
        ]
        self.__been_shutdown = False

        for w in self.__workers:
            w.start()

    def submit(self, callback, *args, **kwargs):
        if self.__been_shutdown:
            raise RuntimeError("QThreadExecutor has been shutdown")

        future = Future()
        self._logger.debug(
            "Submitting callback %s with args %s and kwargs %s to thread worker queue",
            callback,
            args,
            kwargs,
        )
        self.__queue.put((future, callback, args, kwargs))
        return future

    def map(self, func, *iterables, timeout=None):
        raise NotImplementedError("use as_completed on the event loop")

    def shutdown(self, wait=True):
        if self.__been_shutdown:
            raise RuntimeError("QThreadExecutor has been shutdown")

        self.__been_shutdown = True

        self._logger.debug("Shutting down")
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
        self.__debug_enabled = False

    def add_callback(self, handle, delay=0):
        timerid = self.startTimer(int(max(0, delay) * 1000))
        self.__log_debug("Registering timer id %s", timerid)
        assert timerid not in self.__callbacks
        self.__callbacks[timerid] = handle
        return handle

    def timerEvent(self, event):  # noqa: N802
        timerid = event.timerId()
        self.__log_debug("Timer event on id %s", timerid)
        if self._stopped:
            self.__log_debug("Timer stopped, killing %s", timerid)
            self.killTimer(timerid)
            del self.__callbacks[timerid]
        else:
            try:
                handle = self.__callbacks[timerid]
            except KeyError as e:
                self.__log_debug(e)
                pass
            else:
                if handle._cancelled:
                    self.__log_debug("Handle %s cancelled", handle)
                else:
                    self.__log_debug("Calling handle %s", handle)
                    handle._run()
            finally:
                del self.__callbacks[timerid]
                handle = None
            self.killTimer(timerid)

    def stop(self):
        self.__log_debug("Stopping timers")
        self._stopped = True

    def set_debug(self, enabled):
        self.__debug_enabled = enabled

    def __log_debug(self, *args, **kwargs):
        if self.__debug_enabled:
            self._logger.debug(*args, **kwargs)


def _fileno(fd):
    if isinstance(fd, int):
        return fd
    try:
        return int(fd.fileno())
    except (AttributeError, TypeError, ValueError):
        raise ValueError(f"Invalid file object: {fd!r}") from None


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

    If the event loop shall be used with an existing and already running QApplication
    it must be specified in the constructor via already_running=True
    In this case the user is responsible for loop cleanup with stop() and close()

    The set_running_loop parameter is there for backwards compatibility and does nothing.
    """

    def __init__(self, app=None, set_running_loop=False, already_running=False):
        self.__app = app or QApplication.instance()
        assert self.__app is not None, "No QApplication has been instantiated"
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

        # We have to set __is_running to True after calling
        # super().__init__() because of a bug in BaseEventLoop.
        if already_running:
            self.__is_running = True

            # it must be ensured that all pre- and
            # postprocessing for the eventloop is done
            self._before_run_forever()
            self.__app.aboutToQuit.connect(self._after_run_forever)

            # for asyncio to recognize the already running loop
            asyncio.events._set_running_loop(self)

    def run_forever(self):
        """Run eventloop forever."""

        if self.__is_running:
            raise RuntimeError("Event loop already running")

        self.__is_running = True
        self._before_run_forever()

        try:
            self.__log_debug("Starting Qt event loop")
            asyncio.events._set_running_loop(self)
            rslt = -1
            if hasattr(self.__app, "exec"):
                rslt = self.__app.exec()
            else:
                rslt = self.__app.exec_()
            self.__log_debug("Qt event loop ended with result %s", rslt)
            return rslt
        finally:
            asyncio.events._set_running_loop(None)
            self._after_run_forever()
            self.__is_running = False

    def run_until_complete(self, future):
        """Run until Future is complete."""

        if self.__is_running:
            raise RuntimeError("Event loop already running")

        self.__log_debug("Running %s until complete", future)
        future = asyncio.ensure_future(future, loop=self)

        def stop(*args):
            self.stop()  # noqa

        future.add_done_callback(stop)
        try:
            self.run_forever()
        finally:
            future.remove_done_callback(stop)
        self.__app.processEvents()  # run loop one last time to process all the events
        if not future.done():
            raise RuntimeError("Event loop stopped before Future completed.")

        self.__log_debug("Future %s finished running", future)
        return future.result()

    def stop(self):
        """Stop event loop."""
        if not self.__is_running:
            self.__log_debug("Already stopped")
            return

        self.__log_debug("Stopping event loop...")
        self.__is_running = False
        self.__app.exit()
        self.__log_debug("Stopped event loop")

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

        self.__log_debug("Closing event loop...")
        if self.__default_executor is not None:
            self.__default_executor.shutdown()

        super().close()

        self._timer.stop()
        self.__app = None

        for notifier in itertools.chain(
            self._read_notifiers.values(), self._write_notifiers.values()
        ):
            notifier.setEnabled(False)

        self._read_notifiers = None
        self._write_notifiers = None

    def call_later(self, delay, callback, *args, context=None):
        """Register callback to be invoked after a certain delay."""
        if asyncio.iscoroutinefunction(callback):
            raise TypeError("coroutines cannot be used with call_later")
        if not callable(callback):
            raise TypeError(
                "callback must be callable: {}".format(type(callback).__name__)
            )

        self.__log_debug(
            "Registering callback %s to be invoked with arguments %s after %s second(s)",
            callback,
            args,
            delay,
        )

        if sys.version_info >= (3, 7):
            return self._add_callback(
                asyncio.Handle(callback, args, self, context=context), delay
            )
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

    def _add_reader(self, fd, callback, *args):
        """Register a callback for when a file descriptor is ready for reading."""
        self._check_closed()

        try:
            existing = self._read_notifiers[fd]
        except KeyError:
            pass
        else:
            # this is necessary to avoid race condition-like issues
            existing.setEnabled(False)
            existing.activated["int"].disconnect()
            # will get overwritten by the assignment below anyways

        notifier = QtCore.QSocketNotifier(_fileno(fd), QtCore.QSocketNotifier.Type.Read)
        notifier.setEnabled(True)
        self.__log_debug("Adding reader callback for file descriptor %s", fd)
        notifier.activated["int"].connect(
            lambda: self.__on_notifier_ready(
                self._read_notifiers, notifier, fd, callback, args
            )  # noqa: C812
        )
        self._read_notifiers[fd] = notifier

    def _remove_reader(self, fd):
        """Remove reader callback."""
        if self.is_closed():
            return

        self.__log_debug("Removing reader callback for file descriptor %s", fd)
        try:
            notifier = self._read_notifiers.pop(fd)
        except KeyError:
            return False
        else:
            notifier.setEnabled(False)
            return True

    def _add_writer(self, fd, callback, *args):
        """Register a callback for when a file descriptor is ready for writing."""
        self._check_closed()
        try:
            existing = self._write_notifiers[fd]
        except KeyError:
            pass
        else:
            # this is necessary to avoid race condition-like issues
            existing.setEnabled(False)
            existing.activated["int"].disconnect()
            # will get overwritten by the assignment below anyways

        notifier = QtCore.QSocketNotifier(
            _fileno(fd),
            QtCore.QSocketNotifier.Type.Write,
        )
        notifier.setEnabled(True)
        self.__log_debug("Adding writer callback for file descriptor %s", fd)
        notifier.activated["int"].connect(
            lambda: self.__on_notifier_ready(
                self._write_notifiers, notifier, fd, callback, args
            )  # noqa: C812
        )
        self._write_notifiers[fd] = notifier

    def _remove_writer(self, fd):
        """Remove writer callback."""
        if self.is_closed():
            return

        self.__log_debug("Removing writer callback for file descriptor %s", fd)
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
                notifier.activated["int"].disconnect()

    def __on_notifier_ready(self, notifiers, notifier, fd, callback, args):
        if fd not in notifiers:
            self._logger.warning(
                "Socket notifier for fd %s is ready, even though it should "
                "be disabled, not calling %s and disabling",
                fd,
                callback,
            )
            notifier.setEnabled(False)
            return

        # It can be necessary to disable QSocketNotifier when e.g. checking
        # ZeroMQ sockets for events
        assert notifier.isEnabled()
        self.__log_debug("Socket notifier for fd %s is ready", fd)
        notifier.setEnabled(False)
        self.call_soon(
            self.__notifier_cb_wrapper, notifiers, notifier, fd, callback, args
        )

    # Methods for interacting with threads.

    def call_soon_threadsafe(self, callback, *args, context=None):
        """Thread-safe version of call_soon."""
        self.__call_soon_signal.emit(callback, args)

    def run_in_executor(self, executor, callback, *args):
        """Run callback in executor.

        If no executor is provided, the default executor will be used, which defers execution to
        a background thread.
        """
        self.__log_debug("Running callback %s with args %s in executor", callback, args)
        if isinstance(callback, asyncio.Handle):
            assert not args
            assert not isinstance(callback, asyncio.TimerHandle)
            if callback._cancelled:
                f = asyncio.Future()
                f.set_result(None)
                return f
            callback, args = callback.callback, callback.args

        if executor is None:
            self.__log_debug("Using default executor")
            executor = self.__default_executor

        if executor is None:
            self.__log_debug("Creating default executor")
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
        self.__log_debug("Default exception handler executing")
        message = context.get("message")
        if not message:
            message = "Unhandled exception in event loop"

        try:
            exception = context["exception"]
        except KeyError:
            exc_info = False
        else:
            exc_info = (type(exception), exception, exception.__traceback__)

        log_lines = [message]
        for key in [k for k in sorted(context) if k not in {"message", "exception"}]:
            log_lines.append("{}: {!r}".format(key, context[key]))

        self.__log_error("\n".join(log_lines), exc_info=exc_info)

    def call_exception_handler(self, context):
        if self.__exception_handler is None:
            try:
                self.default_exception_handler(context)
            except Exception:
                # Second protection layer for unexpected errors
                # in the default implementation, as well as for subclassed
                # event loops with overloaded "default_exception_handler".
                self.__log_error(
                    "Exception in default exception handler", exc_info=True
                )

            return

        try:
            self.__exception_handler(self, context)
        except Exception as exc:
            # Exception in the user set custom exception handler.
            try:
                # Let's try the default handler.
                self.default_exception_handler(
                    {
                        "message": "Unhandled error in custom exception handler",
                        "exception": exc,
                        "context": context,
                    }
                )
            except Exception:
                # Guard 'default_exception_handler' in case it's
                # overloaded.
                self.__log_error(
                    "Exception in default exception handler while handling an unexpected error "
                    "in custom exception handler",
                    exc_info=True,
                )

    # Debug flag management.

    def get_debug(self):
        return self.__debug_enabled

    def set_debug(self, enabled):
        super().set_debug(enabled)
        self.__debug_enabled = enabled
        self._timer.set_debug(enabled)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.stop()
        self.close()

    def __log_debug(self, *args, **kwargs):
        if self.__debug_enabled:
            self._logger.debug(*args, **kwargs)

    @classmethod
    def __log_error(cls, *args, **kwds):
        # In some cases, the error method itself fails, don't have a lot of options in that case
        try:
            cls._logger.error(*args, **kwds)
        except:  # noqa E722
            sys.stderr.write("{!r}, {!r}\n".format(args, kwds))


from ._unix import _SelectorEventLoop  # noqa

QSelectorEventLoop = type("QSelectorEventLoop", (_QEventLoop, _SelectorEventLoop), {})

if os.name == "nt":
    from ._windows import _ProactorEventLoop

    QIOCPEventLoop = type("QIOCPEventLoop", (_QEventLoop, _ProactorEventLoop), {})
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


def asyncSlot(*args, **kwargs):
    """Make a Qt async slot run on asyncio loop."""

    def _error_handler(task):
        try:
            task.result()
        except Exception:
            sys.excepthook(*sys.exc_info())

    def outer_decorator(fn):
        @Slot(*args, **kwargs)
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            # Qt ignores trailing args from a signal but python does
            # not so inspect the slot signature and if it's not
            # callable try removing args until it is.
            task = None
            while len(args):
                try:
                    inspect.signature(fn).bind(*args, **kwargs)
                except TypeError:
                    if len(args):
                        # Only convert args to a list if we need to pop()
                        args = list(args)
                        args.pop()
                        continue
                else:
                    task = asyncio.ensure_future(fn(*args, **kwargs))
                    task.add_done_callback(_error_handler)
                    break
            if task is None:
                raise TypeError(
                    "asyncSlot was not callable from Signal. Potential signature mismatch."
                )
            return task

        return wrapper

    return outer_decorator


class QEventLoopPolicyMixin:
    def new_event_loop(self):
        return QEventLoop(QApplication.instance() or QApplication(sys.argv))


class DefaultQEventLoopPolicy(
    QEventLoopPolicyMixin,
    asyncio.DefaultEventLoopPolicy,
):
    pass


@contextlib.contextmanager
def _set_event_loop_policy(policy):
    old_policy = asyncio.get_event_loop_policy()
    asyncio.set_event_loop_policy(policy)
    try:
        yield
    finally:
        asyncio.set_event_loop_policy(old_policy)


def run(*args, **kwargs):
    with _set_event_loop_policy(DefaultQEventLoopPolicy()):
        return asyncio.run(*args, **kwargs)
