from __future__ import annotations

from PySide6.QtCore import QObject, Qt, Signal, Slot
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QPlainTextEdit,
    QPushButton,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from pcontext.gui.backend import GuiBackend


class TextViewerDialog(QDialog):
    """
    Простое окно показа текста с кнопками "Копировать" и "Закрыть".
    """

    def __init__(
        self,
        text: str,
        title: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._text = text

        self.setWindowTitle(title or "PContext Text")
        self.resize(720, 480)
        self.setModal(False)

        layout = QVBoxLayout(self)

        self._editor = QPlainTextEdit(self)
        self._editor.setReadOnly(True)
        self._editor.setPlainText(text)
        layout.addWidget(self._editor)

        buttons_layout = QHBoxLayout()

        copy_button = QPushButton("Копировать", self)
        copy_button.clicked.connect(self._copy_text)
        buttons_layout.addWidget(copy_button)

        buttons_layout.addStretch(1)

        close_button = QPushButton("Закрыть", self)
        close_button.clicked.connect(self.close)
        buttons_layout.addWidget(close_button)

        layout.addLayout(buttons_layout)

    def _copy_text(self) -> None:
        """
        Копирует весь текст окна в системный буфер обмена.
        """
        clipboard = QApplication.clipboard()
        clipboard.setText(self._text)


class GuiActionBridge(QObject):
    """
    Мост между фоновыми потоками агента и GUI-потоком Qt.

    Из IPC-потока или worker-потока нельзя безопасно открывать окна напрямую,
    поэтому мы перебрасываем такие действия в главный Qt-поток через сигналы.
    """

    show_text_requested = Signal(object, str)
    show_notification_requested = Signal(str, object)

    def __init__(
        self,
        tray_icon: QSystemTrayIcon,
        backend: GuiBackend,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._tray_icon = tray_icon
        self._backend = backend
        self._open_text_windows: list[TextViewerDialog] = []

        self.show_text_requested.connect(self._show_text_impl)
        self.show_notification_requested.connect(self._show_notification_impl)

    def show_text(self, title: str | None, text: str) -> None:
        """
        Просит GUI-поток показать окно с текстом.
        """
        self.show_text_requested.emit(title, text)

    def show_notification(self, title: str, description: str | None) -> None:
        """
        Просит GUI-поток показать уведомление tray icon.
        """
        self.show_notification_requested.emit(title, description)

    @Slot(object, str)
    def _show_text_impl(self, title: object, text: str) -> None:
        """
        Реально создаёт и показывает окно с текстом.
        """
        normalized_title = str(title) if title is not None else None

        dialog = TextViewerDialog(text=text, title=normalized_title)
        dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        dialog.destroyed.connect(
            lambda _=None, dlg=dialog: self._forget_text_window(dlg)
        )

        self._open_text_windows.append(dialog)
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

    @Slot(str, object)
    def _show_notification_impl(self, title: str, description: object) -> None:
        """
        Реально показывает уведомление, если они не отключены в настройках.
        """
        disable_notifications = bool(
            self._backend.get_setting(
                GuiBackend.SETTINGS_DISABLE_NOTIFICATIONS,
                False,
            )
        )
        if disable_notifications:
            return

        normalized_description = str(description) if description is not None else ""

        self._tray_icon.showMessage(
            title,
            normalized_description,
            QSystemTrayIcon.MessageIcon.Information,
            5000,
        )

    def _forget_text_window(self, dialog: TextViewerDialog) -> None:
        """
        Удаляет ссылку на уже закрытое окно текста.
        """
        try:
            self._open_text_windows.remove(dialog)
        except ValueError:
            pass
