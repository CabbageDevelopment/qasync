# © 2018 Gerard Marull-Paretas <gerard@teslabs.com>
# © 2014 Mark Harviston <mark.harviston@gmail.com>
# © 2014 Arve Knudsen <arve.knudsen@gmail.com>
# BSD License
import logging
import threading
import time
import weakref
from concurrent.futures import TimeoutError

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
    for cls in (
        qasync.QThreadExecutor,
        qasync._QThreadWorker,
        qasync.QThreadPoolExecutor,
    ):
        logger_name = cls.__qualname__
        if cls.__module__ is not None:
            logger_name = f"{cls.__module__}.{logger_name}"
        logger = logging.getLogger(logger_name)
        logger.addHandler(logging.NullHandler())
        logger.propagate = False


@pytest.fixture(params=[qasync.QThreadExecutor, qasync.QThreadPoolExecutor])
def executor(request):
    exe = get_executor(request)
    request.addfinalizer(lambda: safe_shutdown(exe))
    return exe


def get_executor(request):
    if request.param is qasync.QThreadPoolExecutor:
        pool = qasync.QtCore.QThreadPool()
        pool.setMaxThreadCount(5)
        return request.param(pool)
    else:
        return request.param(5)


def safe_shutdown(executor):
    try:
        executor.shutdown()
    except Exception:
        pass
    if isinstance(executor, qasync.QThreadPoolExecutor):
        # empty the underlying QThreadPool object
        executor.pool.waitForDone()


@pytest.fixture(params=[qasync.QThreadExecutor, qasync.QThreadPoolExecutor])
def shutdown_executor(request):
    exe = get_executor(request)
    exe.shutdown()
    return exe


def test_shutdown_after_shutdown(shutdown_executor):
    with pytest.raises(RuntimeError):
        shutdown_executor.shutdown()


def test_ctx_after_shutdown(shutdown_executor):
    with pytest.raises(RuntimeError):
        with shutdown_executor:
            pass


def _test_submit_after_shutdown(shutdown_executor):
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


def test_map(executor):
    """Basic test of executor map functionality"""
    results = list(executor.map(lambda x: x + 1, range(10)))
    assert results == [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]


@pytest.mark.parametrize("cancel", [True, False])
def test_map_timeout(executor, cancel):
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
    assert duration < 0.05

    executor.shutdown(wait=True, cancel_futures=cancel)
    if not cancel:
        # they were not cancelled
        assert set(results) == {0, 1, 2, 3, 4, 5, 6, 7, 8, 9}
    else:
        # only about half of the tasks should have completed
        # because the max number of workers is 5 and the rest of
        # the tasks were not started at the time of the cancel.
        assert set(results) != {0, 1, 2, 3, 4, 5, 6, 7, 8, 9}


def test_context(executor):
    """Test that the context manager will shutdown executor"""
    with executor:
        f = executor.submit(lambda: 42)
        assert f.result() == 42

    with pytest.raises(RuntimeError):
        executor.submit(lambda: 42)


def test_default_pool_executor():
    """Test that using the global instance of QThreadPool works"""
    with qasync.QThreadPoolExecutor() as executor:
        f = executor.submit(lambda: 42)
        assert f.result() == 42
