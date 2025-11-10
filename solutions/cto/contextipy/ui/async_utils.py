"""Helpers for integrating background work with PySide6's threading model."""

from __future__ import annotations

from functools import partial
from typing import TYPE_CHECKING, Any, Callable, Generic, TypeVar

try:  # pragma: no cover
    from PySide6.QtConcurrent import QFuture, QFutureWatcher, run
    from PySide6.QtCore import QObject, QRunnable, QThread, QThreadPool, Signal
except ImportError:  # pragma: no cover
    QFuture = None  # type: ignore[assignment]
    QFutureWatcher = None  # type: ignore[assignment]
    run = None  # type: ignore[assignment]
    QObject = object  # type: ignore[assignment,misc]
    QRunnable = object  # type: ignore[assignment,misc]
    QThread = None  # type: ignore[assignment]
    QThreadPool = None  # type: ignore[assignment]
    Signal = None  # type: ignore[assignment]
    PYSIDE_AVAILABLE = False
else:
    PYSIDE_AVAILABLE = True

__all__ = [
    "run_in_thread_pool",
    "run_in_thread",
    "FutureObserver",
]


T = TypeVar("T")


def run_in_thread_pool(
    function: Callable[..., T],
    /,
    *args: Any,
    thread_pool: "QThreadPool | None" = None,
    **kwargs: Any,
) -> "QFuture[T]":
    """Execute a callable on a Qt thread pool and return a QFuture.

    Args:
        function: Callable to execute.
        *args: Positional arguments passed to callable.
        thread_pool: Optional custom thread pool; defaults to the global pool.
        **kwargs: Keyword arguments for the callable.

    Returns:
        QFuture representing the asynchronous execution.
    """

    if not PYSIDE_AVAILABLE:
        raise RuntimeError("PySide6 is not available")

    callable_obj: Callable[..., T]
    if kwargs:
        callable_obj = partial(function, **kwargs)
    else:
        callable_obj = function

    if thread_pool is not None:
        return run(thread_pool, callable_obj, *args)  # type: ignore[misc]
    return run(callable_obj, *args)  # type: ignore[misc]



if PYSIDE_AVAILABLE:

    class _FunctionRunnable(QRunnable):
        """QRunnable wrapper for executing a Python callable on a QThread."""

        def __init__(self, function: Callable[..., T], *args: Any, **kwargs: Any) -> None:
            super().__init__()
            self._function = function
            self._args = args
            self._kwargs = kwargs
            self._result: T | None = None
            self._error: BaseException | None = None

        def run(self) -> None:  # type: ignore[override]
            try:
                self._result = self._function(*self._args, **self._kwargs)
            except BaseException as exc:  # pragma: no cover - propagate later
                self._error = exc

        @property
        def result(self) -> T | None:
            return self._result

        @property
        def error(self) -> BaseException | None:
            return self._error


    class FutureObserver(QObject, Generic[T]):
        """Convenience wrapper that bridges QFutureWatcher with Qt signals."""

        finished: Signal = Signal(object)
        failed: Signal = Signal(object)
        canceled: Signal = Signal()

        def __init__(self, future: QFuture[T]) -> None:
            super().__init__()
            self._future = future
            self._watcher: QFutureWatcher[T] = QFutureWatcher()
            self._watcher.setFuture(future)

            self._watcher.finished.connect(self._handle_finished)
            self._watcher.canceled.connect(self.canceled)

        def _handle_finished(self) -> None:
            if self._future.isCanceled():
                self.canceled.emit()
                return

            try:
                result = self._future.result()
            except BaseException as exc:  # pragma: no cover - propagate to listener
                self.failed.emit(exc)
            else:
                self.finished.emit(result)

        def watcher(self) -> QFutureWatcher[T]:
            """Return the underlying QFutureWatcher."""
            return self._watcher


    def run_in_thread(
        function: Callable[..., T],
        /,
        *args: Any,
        thread: "QThread | None" = None,
        **kwargs: Any,
    ) -> tuple["QThread", _FunctionRunnable]:
        """Execute a callable on a dedicated QThread.

        Args:
            function: Callable to execute.
            *args: Positional arguments passed to callable.
            thread: Optional pre-created QThread.
            **kwargs: Keyword arguments passed to callable.

        Returns:
            Tuple containing the thread and runnable. The caller is responsible for
            managing the thread's lifecycle.
        """

        runnable = _FunctionRunnable(function, *args, **kwargs)
        target_thread = thread or QThread()  # type: ignore[call-arg]

        def _start() -> None:
            runnable.run()
            target_thread.quit()

        target_thread.started.connect(_start)
        target_thread.start()

        return target_thread, runnable

else:

    class FutureObserver(Generic[T]):
        """Placeholder FutureObserver when PySide6 is unavailable."""

        def __init__(self, future: Any) -> None:  # noqa: D401 - simple runtime error
            raise RuntimeError("PySide6 is not available")

        def watcher(self) -> Any:  # pragma: no cover - not reachable
            raise RuntimeError("PySide6 is not available")

    def run_in_thread(
        function: Callable[..., T],
        /,
        *args: Any,
        thread: Any | None = None,
        **kwargs: Any,
    ) -> tuple[Any, Any]:
        """Placeholder implementation when PySide6 is unavailable."""

        raise RuntimeError("PySide6 is not available")
