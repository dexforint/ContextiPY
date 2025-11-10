"""Processes status window showing oneshot executions with ability to stop."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

try:  # pragma: no cover
    from PySide6.QtCore import QTimer, Qt
    from PySide6.QtWidgets import (
        QHBoxLayout,
        QLabel,
        QMainWindow,
        QMessageBox,
        QScrollArea,
        QVBoxLayout,
        QWidget,
    )
except ImportError:  # pragma: no cover
    QTimer = object  # type: ignore[assignment,misc]
    Qt = None  # type: ignore[assignment]
    QHBoxLayout = object  # type: ignore[assignment,misc]
    QLabel = object  # type: ignore[assignment,misc]
    QMainWindow = object  # type: ignore[assignment,misc]
    QMessageBox = object  # type: ignore[assignment,misc]
    QScrollArea = object  # type: ignore[assignment,misc]
    QVBoxLayout = object  # type: ignore[assignment,misc]
    QWidget = object  # type: ignore[assignment,misc]
    PYSIDE_AVAILABLE = False
else:
    PYSIDE_AVAILABLE = True

if TYPE_CHECKING:
    from contextipy.execution.script_runner import ScriptResult
    from contextipy.ui.theme import Spacing

from ..icons import APP_ICON_NAME, load_icon
from ..theme import Spacing, get_theme
from ..widgets import Card, Heading, SecondaryButton, SecondaryLabel, VStack


@dataclass
class ProcessInfo:
    """Information about a running process."""

    process_id: str
    script_id: str
    started_at: float
    is_running: bool = True
    result: ScriptResult | None = None


class ProcessModel:
    """Model holding process data."""

    def __init__(self) -> None:
        self.processes: list[ProcessInfo] = []

    def update_processes(self, processes: list[ProcessInfo]) -> None:
        """Update the list of processes."""
        self.processes = processes


class ProcessesWindow(QMainWindow):
    """Window displaying running processes with ability to stop them."""

    def __init__(
        self,
        *,
        get_processes: Callable[[], list[ProcessInfo]] | None = None,
        stop_process: Callable[[str], tuple[bool, str | None]] | None = None,
        refresh_interval: int = 1000,
    ) -> None:
        """Initialize the processes window.

        Args:
            get_processes: Optional callable to fetch current processes.
            stop_process: Optional callable to stop a process. Returns (success, error_message).
            refresh_interval: Refresh interval in milliseconds (default: 1000).
        """
        if not PYSIDE_AVAILABLE:
            raise RuntimeError("PySide6 is not available")

        super().__init__()

        self._model = ProcessModel()
        self._get_processes = get_processes or (lambda: [])
        self._stop_process = stop_process or (lambda process_id: (True, None))
        self._refresh_interval = refresh_interval

        theme = get_theme()
        spacing = theme.spacing

        self.setWindowTitle("Процессы")
        self.setMinimumSize(600, 400)

        icon = load_icon(APP_ICON_NAME)
        if not icon.isNull():
            self.setWindowIcon(icon)

        central_widget = QWidget(self)
        central_layout = QVBoxLayout(central_widget)
        central_layout.setSpacing(spacing.lg)
        central_layout.setContentsMargins(spacing.xl, spacing.xl, spacing.xl, spacing.xl)

        header = Heading("Процессы", level=1)
        header.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        central_layout.addWidget(header)

        subtitle = SecondaryLabel("Управление одноразовыми выполнениями скриптов")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        central_layout.addWidget(subtitle)

        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)

        self._processes_container = VStack(parent=scroll_area)
        scroll_area.setWidget(self._processes_container)

        central_layout.addWidget(scroll_area, stretch=1)

        self.setCentralWidget(central_widget)

        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._refresh_view)
        self._refresh_timer.start(self._refresh_interval)

        self._refresh_view()

    def _refresh_view(self) -> None:
        """Refresh the view by fetching current processes and updating the UI."""
        try:
            processes = self._get_processes()
            self._model.update_processes(processes)
            self._update_ui()
        except Exception:
            pass

    def _update_ui(self) -> None:
        """Update the UI based on the current model."""
        layout: QVBoxLayout = self._processes_container.layout()  # type: ignore[assignment]

        while layout.count():
            item = layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()

        theme = get_theme()
        spacing = theme.spacing

        if not self._model.processes:
            no_processes_label = SecondaryLabel("Нет запущенных процессов")
            no_processes_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            layout.addWidget(no_processes_label)
            return

        for process in self._model.processes:
            process_card = self._create_process_card(process, spacing)
            layout.addWidget(process_card)

        layout.addStretch(1)

    def _create_process_card(self, process: ProcessInfo, spacing: Spacing) -> Card:
        """Create a card widget for a process.

        Args:
            process: Process information.
            spacing: Theme spacing value.

        Returns:
            Card widget representing the process.
        """
        card = Card()
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(spacing.md)

        title_label = QLabel(f"<b>{process.script_id}</b>")
        card_layout.addWidget(title_label)

        id_label = SecondaryLabel(f"ID процесса: {process.process_id}")
        card_layout.addWidget(id_label)

        status_text = "Выполняется" if process.is_running else "Завершён"
        status_label = SecondaryLabel(f"Статус: {status_text}")
        card_layout.addWidget(status_label)

        started_time = datetime.fromtimestamp(process.started_at).strftime("%Y-%m-%d %H:%M:%S")
        started_label = SecondaryLabel(f"Запущен: {started_time}")
        card_layout.addWidget(started_label)

        if not process.is_running and process.result:
            result = process.result
            result_text = "Успешно" if result.success else "Ошибка"
            result_label = SecondaryLabel(f"Результат: {result_text}")
            card_layout.addWidget(result_label)

            if result.error_message:
                error_label = SecondaryLabel(f"Ошибка: {result.error_message}")
                card_layout.addWidget(error_label)

        button_layout = QHBoxLayout()
        button_layout.addStretch(1)

        if process.is_running:
            stop_button = SecondaryButton("Остановить")
            stop_button.clicked.connect(
                lambda _checked=False, process_id=process.process_id: self._on_stop_process(process_id)
            )
            button_layout.addWidget(stop_button)

        card_layout.addLayout(button_layout)

        return card

    def _on_stop_process(self, process_id: str) -> None:
        """Handle stop process button click.

        Args:
            process_id: ID of the process to stop.
        """
        try:
            success, error_message = self._stop_process(process_id)
            if not success:
                self._show_error_dialog(
                    "Ошибка остановки процесса",
                    error_message or f"Не удалось остановить процесс: {process_id}",
                )
            else:
                self._refresh_view()
        except Exception as exc:
            self._show_error_dialog("Ошибка остановки процесса", str(exc))

    def _show_error_dialog(self, title: str, message: str) -> None:
        """Show an error message dialog.

        Args:
            title: Dialog title.
            message: Error message.
        """
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Icon.Critical)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg_box.exec()

    def closeEvent(self, event: "QCloseEvent") -> None:  # type: ignore[name-defined]  # noqa: F821
        """Handle window close event.

        Args:
            event: Close event.
        """
        self._refresh_timer.stop()
        super().closeEvent(event)  # type: ignore[misc]
