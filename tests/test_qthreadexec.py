# © 2018 Gerard Marull-Paretas <gerard@teslabs.com>
# © 2014 Mark Harviston <mark.harviston@gmail.com>
# © 2014 Arve Knudsen <arve.knudsen@gmail.com>
# BSD License
import threading
import weakref
import logging

import pytest

import qasync


_TestObject = type("_TestObject", (object,), {})


@pytest.fixture(autouse=True)
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


def test_shutdown_after_shutdown(shutdown_executor):
    with pytest.raises(RuntimeError):
        shutdown_executor.shutdown()


def test_ctx_after_shutdown(shutdown_executor):
    with pytest.raises(RuntimeError):
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


def test_no_stale_reference_as_argument(executor):
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
    assert (
        collected is True
    ), "Stale reference to executor argument not collected within timeout."


def test_no_stale_reference_as_result(executor):
    # Get object as result out of executor
    test_obj = executor.submit(lambda: _TestObject()).result()
    test_obj_collected = threading.Event()

    # Reference to weakref has to be kept for callback to work
    _ = weakref.ref(test_obj, lambda *_: test_obj_collected.set())
    del test_obj

    collected = test_obj_collected.wait(timeout=1)
    assert (
        collected is True
    ), "Stale reference to executor result not collected within timeout."
