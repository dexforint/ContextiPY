from __future__ import annotations

import threading
from typing import Any, cast

from PySide6.QtCore import QObject, Signal, Slot

from pcontext.gui.ask_dialog import AskDialog
from pcontext.runtime.question_models import QuestionFormSchema


class GuiAskBridge(QObject):
    """
    Мост между IPC-потоком агента и GUI-потоком для Ask(...).
    """

    ask_requested = Signal(object, object)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.ask_requested.connect(self._ask_impl)

    def ask_user(self, schema: QuestionFormSchema) -> dict[str, Any] | None:
        """
        Синхронно просит GUI-поток показать форму и вернуть ответ.
        """
        payload: dict[str, object] = {
            "event": threading.Event(),
            "result": None,
        }

        self.ask_requested.emit(schema, payload)

        event = cast(threading.Event, payload["event"])
        event.wait()

        result = payload["result"]
        if result is None:
            return None

        return cast(dict[str, Any], result)

    @Slot(object, object)
    def _ask_impl(self, schema_object: object, payload_object: object) -> None:
        """
        Реально открывает Ask-диалог в GUI-потоке.
        """
        schema = cast(QuestionFormSchema, schema_object)
        payload = cast(dict[str, object], payload_object)

        try:
            dialog = AskDialog(schema)
            if dialog.exec():
                payload["result"] = dialog.get_answers()
            else:
                payload["result"] = None
        finally:
            event = cast(threading.Event, payload["event"])
            event.set()
