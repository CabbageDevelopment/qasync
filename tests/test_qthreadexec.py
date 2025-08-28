# © 2018 Gerard Marull-Paretas <gerard@teslabs.com>
# © 2014 Mark Harviston <mark.harviston@gmail.com>
# © 2014 Arve Knudsen <arve.knudsen@gmail.com>
# BSD License
import logging
import threading
import time
import weakref
from concurrent.futures import CancelledError, TimeoutError
from itertools import islice
from unittest import mock

import pytest

import qasync

_TestObject = type("_TestObject", (object,), {})


@pytest.fixture
def disable_executor_logging():
    """
    When running under pytest, leftover LogRecord objects
    keep references to objects in the scope that logging was called in.
    To avoid issues with tests targeting stale references,
    we disable logging for QThreadExecutor and _QThreadWorker classes.
    """
    for cls in (qasync.QThreadExecutor, qasync._QThreadWorker):
        logger_name = cls.__qualname__
        if cls.__module__ is not None:
            logger_name = f"{cls.__module__}.{logger_name}"
        logger = logging.getLogger(logger_name)
        logger.addHandler(logging.NullHandler())
        logger.propagate = False


@pytest.fixture
def executor(request):
    exe = qasync.QThreadExecutor(5)
    request.addfinalizer(exe.shutdown)
    return exe


@pytest.fixture
def shutdown_executor():
    exe = qasync.QThreadExecutor(5)
    exe.shutdown()
    return exe


@pytest.mark.parametrize("wait", [True, False])
def test_shutdown_after_shutdown(shutdown_executor, wait):
    # it is safe to shutdown twice
    shutdown_executor.shutdown(wait=wait)


def test_ctx_after_shutdown(shutdown_executor):
    # it is safe to enter and exit the context after shutdown
    with shutdown_executor:
        pass


def test_submit_after_shutdown(shutdown_executor):
    with pytest.raises(RuntimeError):
        shutdown_executor.submit(None)


def test_stack_recursion_limit(executor):
    # Test that worker threads have sufficient stack size for the default
    # sys.getrecursionlimit. If not this should fail with SIGSEGV or SIGBUS
    # (or event SIGILL?)
    def rec(a, *args, **kwargs):
        rec(a, *args, **kwargs)

    fs = [executor.submit(rec, 1) for _ in range(10)]
    for f in fs:
        with pytest.raises(RecursionError):
            f.result()


def test_no_stale_reference_as_argument(executor, disable_executor_logging):
    test_obj = _TestObject()
    test_obj_collected = threading.Event()

    # Reference to weakref has to be kept for callback to work
    _ = weakref.ref(test_obj, lambda *_: test_obj_collected.set())
    # Submit object as argument to the executor
    future = executor.submit(lambda *_: None, test_obj)
    del test_obj
    # Wait for future to resolve
    future.result()

    collected = test_obj_collected.wait(timeout=1)
    assert collected is True, (
        "Stale reference to executor argument not collected within timeout."
    )


def test_no_stale_reference_as_result(executor, disable_executor_logging):
    # Get object as result out of executor
    test_obj = executor.submit(lambda: _TestObject()).result()
    test_obj_collected = threading.Event()

    # Reference to weakref has to be kept for callback to work
    _ = weakref.ref(test_obj, lambda *_: test_obj_collected.set())
    del test_obj

    collected = test_obj_collected.wait(timeout=1)
    assert collected is True, (
        "Stale reference to executor result not collected within timeout."
    )


def test_context(executor):
    """Test that the context manager will shutdown executor"""
    with executor:
        f = executor.submit(lambda: 42)
        assert f.result() == 42

    # it can be entered again
    with executor:
        # but will fail when we submit
        with pytest.raises(RuntimeError):
            executor.submit(lambda: 42)


@pytest.mark.parametrize("cancel", [True, False])
def test_shutdown_cancel_futures(executor, cancel):
    """Test that shutdown with cancel_futures=True cancels all remaining futures in the queue."""

    def task():
        time.sleep(0.01)

    # Submit ten tasks to the executor
    futures = [executor.submit(task) for _ in range(10)]
    # shut it down
    executor.shutdown(cancel_futures=cancel)

    cancels = 0
    for future in futures:
        try:
            future.result(timeout=0.01)
        except CancelledError:
            cancels += 1

    if cancel:
        assert cancels > 0
    else:
        assert cancels == 0


def test_map(executor):
    """Basic test of executor map functionality"""
    results = list(executor.map(lambda x: x + 1, range(10)))
    assert results == [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

    results = list(executor.map(lambda x, y: x + y, range(10), range(9)))
    assert results == [0, 2, 4, 6, 8, 10, 12, 14, 16]


def test_map_timeout(executor):
    """Test that map with timeout raises TimeoutError and cancels futures"""
    results = []

    def func(x):
        nonlocal results
        time.sleep(0.05)
        results.append(x)
        return x

    start = time.monotonic()
    with pytest.raises(TimeoutError):
        list(executor.map(func, range(10), timeout=0.01))
    duration = time.monotonic() - start
    # this test is flaky on some platforms, so we give it a wide bearth.
    assert duration < 0.1

    executor.shutdown(wait=True)
    # only about half of the tasks should have completed
    # because the max number of workers is 5 and the rest of
    # the tasks were not started at the time of the cancel.
    assert set(results) != {0, 1, 2, 3, 4, 5, 6, 7, 8, 9}


def test_map_error(executor):
    """Test that map with an exception will raise, and remaining tasks are cancelled"""
    results = []

    def func(x):
        nonlocal results
        time.sleep(0.05)
        if len(results) == 5:
            raise ValueError("Test error")
        results.append(x)
        return x

    with pytest.raises(ValueError):
        list(executor.map(func, range(15)))

    executor.shutdown(wait=True, cancel_futures=False)
    assert len(results) <= 10, "Final 5 at least should have been cancelled"


@pytest.mark.parametrize("cancel", [True, False])
def test_map_shutdown(executor, cancel):
    results = []

    def func(x):
        nonlocal results
        time.sleep(0.05)
        results.append(x)
        return x

    # Get the first few results.
    # Keep the iterator alive so that it isn't closed when its reference is dropped.
    m = executor.map(func, range(15))
    values = list(islice(m, 5))
    assert values == [0, 1, 2, 3, 4]

    executor.shutdown(wait=True, cancel_futures=cancel)
    if cancel:
        assert len(results) < 15, "Some tasks should have been cancelled"
    else:
        assert len(results) == 15, "All tasks should have been completed"
    m.close()


def test_map_start(executor):
    """Test that map starts tasks immediately, before iterating"""
    e = threading.Event()
    m = executor.map(lambda x: (e.set(), x), range(1))
    e.wait(timeout=0.1)
    assert list(m) == [(None, 0)]


def test_map_close(executor):
    """Test that closing a running map cancels all remaining tasks."""
    results = []
    def func(x):
        nonlocal results
        time.sleep(0.05)
        results.append(x)
        return x
    m = executor.map(func, range(10))
    # must start the generator so that close() has any effect
    assert next(m) == 0
    m.close()
    executor.shutdown(wait=True, cancel_futures=False)
    assert len(results) < 10, "Some tasks should have been cancelled"


def test_closing(executor):
    """Test that closing context manager works as expected"""
    # mock the shutdown method of the executor
    with mock.patch.object(executor, "shutdown") as mock_shutdown:
        with executor.closing():
            pass

        # ensure that shutdown was called with (False, cancel_futures=False)
        mock_shutdown.assert_called_once_with(wait=False, cancel_futures=False)

    with mock.patch.object(executor, "shutdown") as mock_shutdown:
        with executor.closing(wait=True, cancel_futures=True):
            pass

        # ensure that shutdown was called with (False, cancel_futures=False)
        mock_shutdown.assert_called_once_with(wait=True, cancel_futures=True)
