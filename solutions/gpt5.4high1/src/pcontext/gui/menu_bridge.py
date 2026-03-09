from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import cast

from PySide6.QtCore import QObject, QTimer

from pcontext.gui.backend import GuiBackend
from pcontext.gui.menu_dialog import MenuChooserDialog
from pcontext.runtime.menu_runtime import ChooserItem


@dataclass(slots=True)
class _PendingChooserRequest:
    """
    Один отложенный запрос на открытие chooser.

    Запрос создаётся в IPC-потоке, а затем обрабатывается GUI-потоком.
    """

    created_at_monotonic: float
    current_folder: str | None
    items: list[ChooserItem]
    payload: dict[str, object]


class GuiMenuBridge(QObject):
    """
    Мост между IPC-потоком агента и GUI-потоком для выбора команды.

    Здесь намеренно не используется Qt signal для передачи payload напрямую
    в собранной Windows-версии. Вместо этого IPC-поток кладёт запрос в очередь,
    а GUI-поток забирает его по таймеру. Это надёжнее для frozen/PyInstaller build.
    """

    def __init__(
        self,
        backend: GuiBackend,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._backend = backend
        self._queue_lock = threading.Lock()
        self._queue: deque[_PendingChooserRequest] = deque()
        self._is_processing = False

        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(50)
        self._poll_timer.timeout.connect(self._process_pending_requests)
        self._poll_timer.start()

    def choose_menu_item(
        self,
        current_folder: str | None,
        items: list[ChooserItem],
    ) -> str | None:
        """
        Синхронно просит GUI-поток показать chooser и вернуть выбранный id.
        """
        payload: dict[str, object] = {
            "event": threading.Event(),
            "result": None,
        }

        request = _PendingChooserRequest(
            created_at_monotonic=time.monotonic(),
            current_folder=current_folder,
            items=items,
            payload=payload,
        )

        with self._queue_lock:
            self._queue.append(request)

        event = cast(threading.Event, payload["event"])
        event.wait()

        result = payload["result"]
        if result is None:
            return None

        return cast(str, result)

    def _process_pending_requests(self) -> None:
        """
        Обрабатывает очередь chooser-запросов в GUI-потоке.
        """
        if self._is_processing:
            return

        request: _PendingChooserRequest | None = None

        with self._queue_lock:
            if self._queue:
                # Небольшая задержка после клика по меню Explorer.
                # Это помогает избежать конфликтов с закрывающимся контекстным меню.
                candidate = self._queue[0]
                if (time.monotonic() - candidate.created_at_monotonic) >= 0.22:
                    request = self._queue.popleft()

        if request is None:
            return

        self._is_processing = True
        try:
            self._run_request(request)
        finally:
            self._is_processing = False

    def _run_request(self, request: _PendingChooserRequest) -> None:
        """
        Реально показывает chooser и возвращает результат вызывающей стороне.
        """
        payload = request.payload
        event = cast(threading.Event, payload["event"])

        dialog = MenuChooserDialog(
            current_folder=request.current_folder,
            items=request.items,
            initial_sort_mode=self._backend.get_setting(
                GuiBackend.SETTINGS_CHOOSER_SORT,
                MenuChooserDialog.SORT_RECENT,
            ),
            initial_geometry=self._backend.get_setting(
                GuiBackend.SETTINGS_CHOOSER_GEOMETRY,
                None,
            ),
            initial_column_widths=self._backend.get_setting(
                GuiBackend.SETTINGS_CHOOSER_COLUMN_WIDTHS,
                None,
            ),
        )

        try:
            dialog.mark_shown()
            dialog.bring_to_front()

            result_code = dialog.exec()

            self._backend.set_setting(
                GuiBackend.SETTINGS_CHOOSER_SORT,
                dialog.current_sort_mode(),
            )
            self._backend.set_setting(
                GuiBackend.SETTINGS_CHOOSER_GEOMETRY,
                dialog.export_geometry_state(),
            )
            self._backend.set_setting(
                GuiBackend.SETTINGS_CHOOSER_COLUMN_WIDTHS,
                dialog.export_column_widths(),
            )

            if result_code == MenuChooserDialog.DialogCode.Accepted:
                payload["result"] = dialog.get_selected_menu_item_id()
            else:
                payload["result"] = None
        finally:
            event.set()
