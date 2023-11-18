# © 2018 Gerard Marull-Paretas <gerard@teslabs.com>
# © 2014 Mark Harviston <mark.harviston@gmail.com>
# © 2014 Arve Knudsen <arve.knudsen@gmail.com>
# BSD License

"""Windows specific Quamash functionality."""

import asyncio
import sys

try:
    import _winapi
    from asyncio import windows_events
    import _overlapped
except ImportError:  # noqa
    pass  # w/o guarding this import py.test can't gather doctests on platforms w/o _winapi

import math

from . import QtCore, _make_signaller
from ._common import with_logger

UINT32_MAX = 0xFFFFFFFF


class _ProactorEventLoop(asyncio.ProactorEventLoop):

    """Proactor based event loop."""

    def __init__(self):
        super().__init__(_IocpProactor())

        self.__event_signaller = _make_signaller(QtCore, list)
        self.__event_signal = self.__event_signaller.signal
        self.__event_signal.connect(self._process_events)
        self.__event_poller = _EventPoller(self.__event_signal)

    def _process_events(self, events):
        """Process events from proactor."""
        for f, callback, transferred, key, ov in events:
            try:
                self._logger.debug("Invoking event callback %s", callback)
                value = callback(transferred, key, ov)
            except OSError as e:
                self._logger.debug("Event callback failed", exc_info=sys.exc_info())
                if not f.done():
                    f.set_exception(e)
            else:
                if not f.cancelled():
                    f.set_result(value)

    def _before_run_forever(self):
        self.__event_poller.start(self._proactor)

    def _after_run_forever(self):
        self.__event_poller.stop()


@with_logger
class _IocpProactor(windows_events.IocpProactor):
    def __init__(self):
        self.__events = []
        super(_IocpProactor, self).__init__()
        self._lock = QtCore.QMutex()

    def select(self, timeout=None):
        """Override in order to handle events in a threadsafe manner."""
        if not self.__events:
            self._poll(timeout)
        tmp = self.__events
        self.__events = []
        return tmp

    def close(self):
        self._logger.debug("Closing")
        super(_IocpProactor, self).close()

    # Wrap all I/O submission methods to acquire the internal lock first; listed
    # in the order they appear in the base class source code.

    def recv(self, conn, nbytes, flags=0):
        with QtCore.QMutexLocker(self._lock):
            return super(_IocpProactor, self).recv(conn, nbytes, flags)

    def recv_into(self, conn, buf, flags=0):
        with QtCore.QMutexLocker(self._lock):
            return super(_IocpProactor, self).recv_into(conn, buf, flags)

    def recvfrom(self, conn, nbytes, flags=0):
        with QtCore.QMutexLocker(self._lock):
            return super(_IocpProactor, self).recvfrom(conn, nbytes, flags)

    def recvfrom_into(self, conn, buf, flags=0):
        with QtCore.QMutexLocker(self._lock):
            return super(_IocpProactor, self).recvfrom_into(conn, buf, flags)

    def sendto(self, conn, buf, flags=0, addr=None):
        with QtCore.QMutexLocker(self._lock):
            return super(_IocpProactor, self).sendto(conn, buf, flags, addr)

    def send(self, conn, buf, flags=0):
        with QtCore.QMutexLocker(self._lock):
            return super(_IocpProactor, self).send(conn, buf, flags)

    def accept(self, listener):
        with QtCore.QMutexLocker(self._lock):
            return super(_IocpProactor, self).accept(listener)

    def connect(self, conn, address):
        with QtCore.QMutexLocker(self._lock):
            return super(_IocpProactor, self).connect(conn, address)

    def sendfile(self, sock, file, offset, count):
        with QtCore.QMutexLocker(self._lock):
            return super(_IocpProactor, self).sendfile(sock, file, offset, count)

    def accept_pipe(self, pipe):
        with QtCore.QMutexLocker(self._lock):
            return super(_IocpProactor, self).accept_pipe(pipe)

    # connect_pipe() does not actually use the delayed completion machinery.

    # This takes care of wait_for_handle() too.
    def _wait_for_handle(self, handle, timeout, _is_cancel):
        with QtCore.QMutexLocker(self._lock):
            return super(_IocpProactor, self)._wait_for_handle(
                handle, timeout, _is_cancel
            )

    def _poll(self, timeout=None):
        """Override in order to handle events in a threadsafe manner."""
        if timeout is None:
            ms = UINT32_MAX  # wait for eternity
        elif timeout < 0:
            raise ValueError("negative timeout")
        else:
            # GetQueuedCompletionStatus() has a resolution of 1 millisecond,
            # round away from zero to wait *at least* timeout seconds.
            ms = math.ceil(timeout * 1e3)
            if ms >= UINT32_MAX:
                raise ValueError("timeout too big")

        while True:
            status = _overlapped.GetQueuedCompletionStatus(self._iocp, ms)
            if status is None:
                break
            ms = 0

            with QtCore.QMutexLocker(self._lock):
                err, transferred, key, address = status
                try:
                    f, ov, obj, callback = self._cache.pop(address)
                except KeyError:
                    # key is either zero, or it is used to return a pipe
                    # handle which should be closed to avoid a leak.
                    if key not in (0, _overlapped.INVALID_HANDLE_VALUE):
                        _winapi.CloseHandle(key)
                    continue

                if obj in self._stopped_serving:
                    f.cancel()
                # Futures might already be resolved or cancelled
                elif not f.done():
                    self.__events.append((f, callback, transferred, key, ov))

        # Remove unregistered futures
        for ov in self._unregistered:
            self._cache.pop(ov.address, None)
        self._unregistered.clear()


@with_logger
class _EventWorker(QtCore.QThread):
    def __init__(self, proactor, parent):
        super().__init__()

        self.__stop = False
        self.__proactor = proactor
        self.__sig_events = parent.sig_events
        self.__semaphore = QtCore.QSemaphore()

    def start(self):
        super().start()
        self.__semaphore.acquire()

    def stop(self):
        self.__stop = True
        # Wait for thread to end
        self.wait()

    def run(self):
        self._logger.debug("Thread started")
        self.__semaphore.release()

        while not self.__stop:
            events = self.__proactor.select(0.01)
            if events:
                self._logger.debug("Got events from poll: %s", events)
                self.__sig_events.emit(events)

        self._logger.debug("Exiting thread")


@with_logger
class _EventPoller:

    """Polling of events in separate thread."""

    def __init__(self, sig_events):
        self.sig_events = sig_events

    def start(self, proactor):
        self._logger.debug("Starting (proactor: %s)...", proactor)
        self.__worker = _EventWorker(proactor, self)
        self.__worker.start()

    def stop(self):
        self._logger.debug("Stopping worker thread...")
        self.__worker.stop()
