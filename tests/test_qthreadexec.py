# © 2018 Gerard Marull-Paretas <gerard@teslabs.com>
# © 2014 Mark Harviston <mark.harviston@gmail.com>
# © 2014 Arve Knudsen <arve.knudsen@gmail.com>
# BSD License
import logging
import threading
import weakref
from concurrent.futures import Future, TimeoutError
from unittest.mock import Mock, patch

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


@pytest.fixture
def executor0():
    """
    Provides a QThreadExecutor with max_workers=0 for deterministic testing.
    """
    executor = qasync.QThreadExecutor(max_workers=0)
    try:
        yield executor
    finally:
        executor.shutdown(wait=True, cancel_futures=False)


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
def test_shutdown_cancel_futures(executor0, cancel):
    """Test that shutdown with cancel_futures=True cancels all remaining futures in the queue."""

    futures = [executor0.submit(lambda: None) for _ in range(10)]

    # Shutdown with cancel_futures parameter
    executor0.shutdown(wait=False, cancel_futures=cancel)

    if cancel:
        # All futures should be cancelled since no workers consumed them
        cancelled_count = sum(1 for f in futures if f.cancelled())
        assert cancelled_count == 10, (
            f"Expected all 10 futures to be cancelled, got {cancelled_count}"
        )
    else:
        # No futures should be cancelled, they should still be pending
        cancelled_count = sum(1 for f in futures if f.cancelled())
        assert cancelled_count == 0, (
            f"Expected no futures to be cancelled, got {cancelled_count}"
        )


def test_map(executor):
    """Basic test of executor map functionality"""
    results = list(executor.map(lambda x: x + 1, range(10)))
    assert results == [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

    results = list(executor.map(lambda x, y: x + y, range(10), range(9)))
    assert results == [0, 2, 4, 6, 8, 10, 12, 14, 16]


def test_map_timeout(executor0):
    """Test that map with timeout propagates the timeout parameter to future.result()"""

    f = Mock(spec=Future)
    f.result = Mock(side_effect=TimeoutError("Timeout"))
    f.cancel = Mock(return_value=True)

    with patch.object(executor0, "submit", return_value=f):
        with pytest.raises(TimeoutError, match="Timeout"):
            list(executor0.map(lambda x: x, [1], timeout=0.5))

    # Verify the timeout parameter was passed to result() (not None)
    # Note: The timeout is calculated as (deadline - time.monotonic()), so it will be
    # slightly less than 0.5 due to the time taken to submit futures and start iteration
    assert f.result.called
    f_timeout = f.result.call_args[0][0] if f.result.call_args[0] else None
    assert f_timeout is not None
    assert f_timeout <= 0.5


def test_map_error(executor0):
    """Test that map with an exception will raise, and remaining tasks are cancelled"""

    # Create 3 futures: one success, one exception, one to be cancelled
    mock_futures = []

    # First future succeeds
    f0 = Mock(spec=Future)
    f0.result = Mock(return_value=0)
    f0.cancel = Mock(return_value=True)
    mock_futures.append(f0)

    # Second future raises an exception
    f1 = Future()
    f1.set_exception(ValueError("Test error"))
    mock_futures.append(f1)

    # Third future should be cancelled
    f2 = Mock(spec=Future)
    f2.result = Mock(return_value=2)
    f2.cancel = Mock(return_value=True)
    mock_futures.append(f2)

    with patch.object(executor0, "submit", side_effect=mock_futures):
        with pytest.raises(ValueError, match="Test error"):
            list(executor0.map(lambda x: x, range(3)))

    # Verify the third future was cancelled when the exception occurred
    assert f2.cancel.called, "Future after exception should have been cancelled"


def test_map_start(executor0):
    """Test that map starts tasks immediately, before iterating"""

    # Mock future that returns immediately
    mock_future = Mock(spec=Future)
    mock_future.result = Mock(return_value=0)
    mock_future.cancel = Mock(return_value=True)

    with patch.object(executor0, "submit", return_value=mock_future) as mock_submit:
        # Create the map - submit should be called immediately
        m = executor0.map(lambda x: x, range(1))

        # Verify submit was called before we start iterating
        mock_submit.assert_called_once()

        # Now iterate to verify the result
        assert list(m) == [0]


def test_map_close(executor0):
    """Test that closing a running map cancels all remaining tasks."""

    # Create mock futures with proper result() method
    mock_futures = []
    for i in range(10):
        mock_future = Mock(spec=Future)
        mock_future.cancel = Mock(return_value=True)
        mock_future.result = Mock(return_value=i)
        mock_futures.append(mock_future)

    # Mock submit to return our pre-created futures
    with patch.object(executor0, "submit", side_effect=mock_futures):
        m = executor0.map(lambda x: x, range(10))
        # must start the generator so that close() has any effect
        assert next(m) == 0
        m.close()

    # All futures should have cancel() called:
    # - The first one via _result_or_cancel after next() consumed it
    # - The rest via the finally block when the generator is closed
    for i, f in enumerate(mock_futures):
        assert f.cancel.called, f"Future {i} should have been cancelled"
