from __future__ import annotations

import threading
from typing import cast

from PySide6.QtCore import QObject, Signal, Slot

from pcontext.gui.backend import GuiBackend
from pcontext.gui.menu_dialog import MenuChooserDialog
from pcontext.runtime.menu_runtime import ChooserItem


class GuiMenuBridge(QObject):
    """
    Мост между IPC-потоком агента и GUI-потоком для выбора команды.
    """

    choose_requested = Signal(object, object, object)

    def __init__(
        self,
        backend: GuiBackend,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._backend = backend
        self.choose_requested.connect(self._choose_impl)

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

        self.choose_requested.emit(current_folder, items, payload)

        event = cast(threading.Event, payload["event"])
        event.wait()

        result = payload["result"]
        if result is None:
            return None

        return cast(str, result)

    @Slot(object, object, object)
    def _choose_impl(
        self,
        current_folder_object: object,
        items_object: object,
        payload_object: object,
    ) -> None:
        """
        Реально открывает chooser-диалог в GUI-потоке.
        """
        current_folder = cast(str | None, current_folder_object)
        items = cast(list[ChooserItem], items_object)
        payload = cast(dict[str, object], payload_object)

        try:
            dialog = MenuChooserDialog(
                current_folder=current_folder,
                items=items,
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
            if dialog.exec():
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
                payload["result"] = dialog.get_selected_menu_item_id()
            else:
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
                payload["result"] = None
        finally:
            event = cast(threading.Event, payload["event"])
            event.set()
