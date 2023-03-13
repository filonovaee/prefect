"""
Utilities for enforcement of timeouts in synchronous and asynchronous contexts.
"""

import asyncio
import contextlib
import ctypes
import math
import signal
import sys
import threading
import time
from typing import Callable, List, Optional, Type

import anyio

from prefect.logging import get_logger

# TODO: We should update the format for this logger to include the current thread
logger = get_logger("prefect._internal.concurrency.timeouts")


class CancelledError(asyncio.CancelledError):
    pass


class CancelContext:
    """
    Tracks if a cancel context manager was cancelled.

    A context cannot be marked as cancelled after it is reported as completed.
    """

    def __init__(
        self, timeout: Optional[float], cancel: Callable[[], None] = None
    ) -> None:
        self._timeout = timeout
        self._deadline = get_deadline(timeout)
        self._cancelled: bool = False
        self._chained: List["CancelContext"] = []
        self._lock = threading.Lock()
        self._completed = False
        self._cancel = cancel

    @property
    def timeout(self) -> Optional[float]:
        return self._timeout

    @property
    def deadline(self) -> Optional[float]:
        return self._deadline

    def cancel(self):
        if self.mark_cancelled():
            logger.debug("Cancelling %r", self)
            return self._cancel()

    def cancelled(self):
        with self._lock:
            return self._cancelled

    def completed(self):
        with self._lock:
            return self._completed

    def mark_cancelled(self) -> bool:
        with self._lock:
            if self._completed:
                return False  # Do not mark completed tasks as cancelled

            logger.debug("Marked %r as cancelled", self)
            self._cancelled = True
            for ctx in self._chained:
                ctx.mark_cancelled()

            return True

    def mark_completed(self) -> bool:
        with self._lock:
            if self._cancelled:
                return False  # Do not mark cancelled tasks as completed

            logger.debug("Marked %r as completed", self)
            self._completed = True
            return True

    def chain(self, ctx: "CancelContext") -> None:
        """
        When this context is marked as cancelled, mark the given context as cancelled
        too.

        If this context is already cancelled, the given context will be marked as
        cancelled immediately.
        """
        with self._lock:
            if self._cancelled:
                ctx.mark_cancelled()
            else:
                self._chained.append(ctx)

    def __repr__(self) -> str:
        timeout = f" timeout={self._timeout:.2f}" if self._timeout else ""
        return f"<CancelContext at {hex(id(self))}{timeout}>"


def get_deadline(timeout: Optional[float]):
    """
    Compute an deadline given a timeout.

    Uses a monotonic clock.
    """
    if timeout is None:
        return None

    return time.monotonic() + timeout


@contextlib.contextmanager
def cancel_async_at(deadline: Optional[float]):
    """
    Cancel any async calls within the context if it does not exit by the given deadline.

    Deadlines must be computed with the monotonic clock. See `get_deadline`.

    A timeout error will be raised on the next `await` when the timeout expires.

    Yields a `CancelContext`.
    """
    timeout = max(0, deadline - time.monotonic()) if deadline else None
    try:
        with anyio.CancelScope(
            deadline=deadline if deadline is not None else math.inf
        ) as scope:
            ctx = CancelContext(timeout=timeout, cancel=scope.cancel)
            yield ctx
    finally:
        if scope.cancel_called:
            ctx.mark_cancelled()
            raise (
                TimeoutError()
                if deadline is not None and time.monotonic() >= deadline
                else CancelledError()
            )
        else:
            ctx.mark_completed()


@contextlib.contextmanager
def cancel_async_after(timeout: Optional[float]):
    """
    Cancel any async calls within the context if it does not exit after the given
    timeout.

    A timeout error will be raised on the next `await` when the timeout expires.

    Yields a `CancelContext`.
    """
    deadline = (time.monotonic() + timeout) if timeout is not None else None
    with cancel_async_at(deadline) as ctx:
        yield ctx


@contextlib.contextmanager
def cancel_sync_at(deadline: Optional[float]):
    """
    Cancel any sync calls within the context if it does not exit by the given deadline.

    Deadlines must be computed with the monotonic clock. See `get_deadline`.

    The cancel method varies depending on if this is called in the main thread or not.
    See `cancel_sync_after` for details

    Yields a `CancelContext`.
    """
    timeout = max(0, deadline - time.monotonic()) if deadline is not None else None

    with cancel_sync_after(timeout) as ctx:
        yield ctx


@contextlib.contextmanager
def cancel_sync_after(timeout: Optional[float]):
    """
    Cancel any sync calls within the context if it does not exit after the given
    timeout.

    The timeout method varies depending on if this is called in the main thread or not.
    See `_alarm_based_timeout` and `_watcher_thread_based_timeout` for details.

    Yields a `CancelContext`.
    """
    if sys.platform.startswith("win"):
        # Timeouts cannot be enforced on Windows
        if timeout is not None:
            logger.warning(
                (
                    f"Entered cancel context on Windows; %.2f timeout will not be"
                    f" enforced."
                ),
                timeout,
            )
        yield CancelContext(timeout=None, cancel=lambda: None)
        return

    if threading.current_thread() is threading.main_thread():
        method = _alarm_based_timeout
        method_name = "alarm"
    else:
        method = _watcher_thread_based_timeout
        method_name = "watcher"

    with method(timeout) as ctx:
        logger.debug(
            f"Entered synchronous %s based cancel context %r",
            method_name,
            ctx,
        )
        yield ctx


@contextlib.contextmanager
def _alarm_based_timeout(timeout: Optional[float]):
    """
    Enforce a timeout using an alarm.

    Sets an alarm for `timeout` seconds, then raises a timeout error if the context is
    not exited before the deadline.

    !!! Alarms cannot be floats, so the timeout is rounded up to the nearest integer.

    Alarms have the benefit of interrupt sys calls like `sleep`, but signals are always
    raised in the main thread and this cannot be used elsewhere.
    """
    current_thread = threading.current_thread()
    if not current_thread is threading.main_thread():
        raise ValueError("Alarm based timeouts can only be used in the main thread.")

    deadline = get_deadline(timeout)

    def raise_alarm_as_timeout(*_):
        logger.debug(
            "Cancel fired for alarm based timeout of thread %r", current_thread.name
        )
        ctx.mark_cancelled()
        raise (
            TimeoutError()
            if timeout is not None and time.monotonic() >= deadline
            else CancelledError()
        )

    # Create a context that raises an alarm signal on cancellation
    ctx = CancelContext(
        timeout=timeout, cancel=lambda: signal.raise_signal(signal.SIGALRM)
    )

    # Capture alarm signals and raise a timeout
    signal.signal(signal.SIGALRM, raise_alarm_as_timeout)

    # Set a timer to raise an alarm signal
    if timeout is not None:
        # Use `setitimer` instead of `signal.alarm` for float support; raises a SIGALRM
        previous = signal.setitimer(signal.ITIMER_REAL, timeout)

    try:
        yield ctx
    finally:
        if timeout is not None:
            # Clear the alarm when the context exits
            signal.setitimer(signal.ITIMER_REAL, *previous)
        ctx.mark_completed()


@contextlib.contextmanager
def _watcher_thread_based_timeout(timeout: Optional[float]):
    """
    Enforce a timeout using a watcher thread.

    Creates a thread that sleeps for `timeout` seconds, then sends a timeout error to
    the supervised (current) thread if the context is not exited before the deadline.

    Note this will not interrupt sys calls like `sleep`.
    """
    event = threading.Event()
    supervised_thread = threading.current_thread()
    cancel = lambda: _send_exception_to_thread(supervised_thread, CancelledError)
    ctx = CancelContext(timeout=timeout, cancel=cancel)

    def timeout_enforcer():
        time.sleep(timeout)
        if not event.is_set():
            logger.debug(
                "Cancel fired for watcher based timeout of thread %r",
                supervised_thread.name,
            )
            ctx.mark_cancelled()
            _send_exception_to_thread(supervised_thread, TimeoutError)

    if timeout is not None:
        enforcer = threading.Thread(target=timeout_enforcer, daemon=True)
        enforcer.start()

    try:
        yield ctx
    finally:
        event.set()
        ctx.mark_completed()


def _send_exception_to_thread(thread: threading.Thread, exc_type: Type[BaseException]):
    """
    Raise an exception in a thread.

    This will not interrupt long-running system calls like `sleep` or `wait`.
    """
    ret = ctypes.pythonapi.PyThreadState_SetAsyncExc(
        ctypes.c_long(thread.ident), ctypes.py_object(exc_type)
    )
    if ret == 0:
        raise ValueError("Thread not found.")
