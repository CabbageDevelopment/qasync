# © 2018 Gerard Marull-Paretas <gerard@teslabs.com>
# © 2014 Mark Harviston <mark.harviston@gmail.com>
# © 2014 Arve Knudsen <arve.knudsen@gmail.com>
# BSD License

import pytest
import qasync


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
