from __future__ import annotations

import threading
from collections.abc import Callable

from PySide6.QtCore import QObject, Signal


class BackgroundTask(QObject):
    """
    Простая фоновая задача для GUI.

    Функция выполняется в отдельном Python-потоке, а результат
    возвращается обратно в GUI через Qt-сигнал.
    """

    finished = Signal(object, object)

    def __init__(
        self,
        function: Callable[[], object],
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._function = function
        self.success_handler: Callable[[object], None] | None = None
        self.error_title: str = "Ошибка"

    def start(self) -> None:
        """
        Запускает задачу в фоне.
        """
        thread = threading.Thread(
            target=self._run,
            daemon=True,
            name="pcontext-gui-task",
        )
        thread.start()

    def _run(self) -> None:
        """
        Выполняет пользовательскую функцию и отправляет результат обратно в GUI.
        """
        try:
            result = self._function()
            error: object | None = None
        except Exception as exc:  # noqa: BLE001
            result = None
            error = exc

        self.finished.emit(result, error)
