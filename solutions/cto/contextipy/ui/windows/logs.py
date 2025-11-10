"""Logs window displaying recent script executions with repeat functionality."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

try:  # pragma: no cover
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import (
        QComboBox,
        QHBoxLayout,
        QHeaderView,
        QLabel,
        QMainWindow,
        QMessageBox,
        QTableWidget,
        QTableWidgetItem,
        QTextEdit,
        QToolButton,
        QVBoxLayout,
        QWidget,
    )
except ImportError:  # pragma: no cover
    Qt = None  # type: ignore[assignment]
    QComboBox = object  # type: ignore[assignment,misc]
    QHBoxLayout = object  # type: ignore[assignment,misc]
    QHeaderView = object  # type: ignore[assignment,misc]
    QLabel = object  # type: ignore[assignment,misc]
    QMainWindow = object  # type: ignore[assignment,misc]
    QMessageBox = object  # type: ignore[assignment,misc]
    QTableWidget = object  # type: ignore[assignment,misc]
    QTableWidgetItem = object  # type: ignore[assignment,misc]
    QTextEdit = object  # type: ignore[assignment,misc]
    QToolButton = object  # type: ignore[assignment,misc]
    QVBoxLayout = object  # type: ignore[assignment,misc]
    QWidget = object  # type: ignore[assignment,misc]
    PYSIDE_AVAILABLE = False
else:
    PYSIDE_AVAILABLE = True

if TYPE_CHECKING:
    from contextipy.logging.logger import ExecutionLog

from ..icons import APP_ICON_NAME, load_icon
from ..theme import get_theme
from ..widgets import Card, Heading, PrimaryButton, SecondaryButton, SecondaryLabel


class LogsModel:
    """Model holding execution log data."""

    def __init__(self) -> None:
        self.logs: list[ExecutionLog] = []

    def update_logs(self, logs: list[ExecutionLog]) -> None:
        """Update the list of execution logs."""
        self.logs = logs


class LogDetailsDialog(QWidget):
    """Dialog for displaying detailed log information with expandable stdout/stderr."""

    def __init__(
        self,
        log: ExecutionLog,
        on_repeat: Callable[[str], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        """Initialize the log details dialog.

        Args:
            log: Execution log to display.
            on_repeat: Optional callback for repeat action button.
            parent: Parent widget.
        """
        if not PYSIDE_AVAILABLE:
            raise RuntimeError("PySide6 is not available")

        super().__init__(parent)

        theme = get_theme()
        spacing = theme.spacing

        self.setWindowTitle(f"Детали выполнения: {log.run_id}")
        self.setMinimumSize(700, 500)

        layout = QVBoxLayout(self)
        layout.setSpacing(spacing.md)
        layout.setContentsMargins(spacing.lg, spacing.lg, spacing.lg, spacing.lg)

        header = Heading(f"Детали: {log.script_id}", level=2)
        layout.addWidget(header)

        info_card = Card()
        info_layout = QVBoxLayout(info_card)
        info_layout.setSpacing(spacing.sm)

        info_layout.addWidget(QLabel(f"<b>Run ID:</b> {log.run_id}"))
        info_layout.addWidget(QLabel(f"<b>Скрипт:</b> {log.script_id}"))
        info_layout.addWidget(QLabel(f"<b>Статус:</b> {self._format_status(log.status)}"))
        info_layout.addWidget(QLabel(f"<b>Начало:</b> {log.start_time.strftime('%Y-%m-%d %H:%M:%S')}"))
        info_layout.addWidget(QLabel(f"<b>Конец:</b> {log.end_time.strftime('%Y-%m-%d %H:%M:%S')}"))
        duration = (log.end_time - log.start_time).total_seconds()
        info_layout.addWidget(QLabel(f"<b>Длительность:</b> {duration:.2f}s"))

        if log.exit_code is not None:
            info_layout.addWidget(QLabel(f"<b>Код выхода:</b> {log.exit_code}"))

        if log.timed_out:
            timeout_label = QLabel("<b>⏱ Тайм-аут</b>")
            timeout_label.setStyleSheet("color: orange;")
            info_layout.addWidget(timeout_label)

        if log.error_message:
            error_label = QLabel(f"<b>Ошибка:</b> {log.error_message}")
            error_label.setStyleSheet("color: red;")
            error_label.setWordWrap(True)
            info_layout.addWidget(error_label)

        layout.addWidget(info_card)

        if log.stdout_excerpt:
            layout.addWidget(self._create_expandable_text_section("STDOUT", log.stdout_excerpt))

        if log.stderr_excerpt:
            layout.addWidget(
                self._create_expandable_text_section("STDERR", log.stderr_excerpt, error=True)
            )

        button_layout = QHBoxLayout()
        button_layout.addStretch(1)

        if on_repeat:
            repeat_button = PrimaryButton("Повторить действие")
            repeat_button.clicked.connect(lambda: on_repeat(log.run_id))
            button_layout.addWidget(repeat_button)

        close_button = SecondaryButton("Закрыть")
        close_button.clicked.connect(self.close)
        button_layout.addWidget(close_button)

        layout.addLayout(button_layout)

    def _create_expandable_text_section(
        self, title: str, content: str, error: bool = False
    ) -> Card:
        """Create an expandable text section for stdout/stderr.

        Args:
            title: Section title (e.g., "STDOUT" or "STDERR").
            content: Text content to display.
            error: Whether this is error output (red styling).

        Returns:
            Card widget containing the expandable section.
        """
        theme = get_theme()
        spacing = theme.spacing

        card = Card()
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(spacing.sm)
        card_layout.setContentsMargins(spacing.sm, spacing.sm, spacing.sm, spacing.sm)

        header_layout = QHBoxLayout()
        header_layout.setSpacing(spacing.xs)
        title_label = QLabel(f"<b>{title}:</b>")
        if error:
            title_label.setStyleSheet("color: red;")
        header_layout.addWidget(title_label)

        toggle_button = QToolButton()
        toggle_button.setCheckable(True)
        toggle_button.setChecked(False)
        header_layout.addWidget(toggle_button)
        header_layout.addStretch(1)

        card_layout.addLayout(header_layout)

        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setPlainText(content)
        if error:
            text_edit.setStyleSheet("color: red;")
        text_edit.setMaximumHeight(200)
        text_edit.setVisible(False)
        card_layout.addWidget(text_edit)

        def update_state(checked: bool) -> None:
            text_edit.setVisible(checked)
            toggle_button.setText("▼" if checked else "▶")

        toggle_button.toggled.connect(update_state)
        update_state(False)

        return card

    def _format_status(self, status: str) -> str:
        """Format status with color HTML."""
        status_map = {
            "success": '<span style="color: green;">✓ Успех</span>',
            "failure": '<span style="color: red;">✗ Ошибка</span>',
            "error": '<span style="color: red;">✗ Исключение</span>',
        }
        return status_map.get(status, status)


class LogsWindow(QMainWindow):
    """Window displaying recent script executions with filters and repeat functionality."""

    def __init__(
        self,
        *,
        get_logs: Callable[[int, str | None, str | None], list[ExecutionLog]] | None = None,
        repeat_action: Callable[[str], tuple[bool, str | None]] | None = None,
    ) -> None:
        """Initialize the logs window.

        Args:
            get_logs: Optional callable to fetch execution logs.
                      Signature: (limit: int, status: str | None, script_id: str | None) -> list[ExecutionLog]
            repeat_action: Optional callable to repeat an action.
                          Signature: (run_id: str) -> (success: bool, error_message: str | None)
        """
        if not PYSIDE_AVAILABLE:
            raise RuntimeError("PySide6 is not available")

        super().__init__()

        self._model = LogsModel()
        self._get_logs = get_logs or (lambda limit, status, script_id: [])
        self._repeat_action = repeat_action or (lambda run_id: (True, None))
        self._detail_dialogs: dict[str, LogDetailsDialog] = {}

        theme = get_theme()
        spacing = theme.spacing

        self.setWindowTitle("Журнал выполнения")
        self.setMinimumSize(1100, 600)

        icon = load_icon(APP_ICON_NAME)
        if not icon.isNull():
            self.setWindowIcon(icon)

        central_widget = QWidget(self)
        central_layout = QVBoxLayout(central_widget)
        central_layout.setSpacing(spacing.lg)
        central_layout.setContentsMargins(spacing.xl, spacing.xl, spacing.xl, spacing.xl)

        header = Heading("Журнал выполнения", level=1)
        header.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        central_layout.addWidget(header)

        subtitle = SecondaryLabel("История выполнения скриптов с возможностью повтора")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        central_layout.addWidget(subtitle)

        filters_layout = QHBoxLayout()

        filters_layout.addWidget(QLabel("Статус:"))
        self._status_filter = QComboBox()
        self._status_filter.addItem("Все", None)
        self._status_filter.addItem("Успех", "success")
        self._status_filter.addItem("Ошибка", "failure")
        self._status_filter.addItem("Исключение", "error")
        self._status_filter.currentIndexChanged.connect(self._on_filter_changed)
        filters_layout.addWidget(self._status_filter)

        filters_layout.addWidget(QLabel("Скрипт:"))
        self._script_filter = QComboBox()
        self._script_filter.setMinimumWidth(200)
        self._script_filter.setEditable(True)
        self._script_filter.addItem("Все", None)
        self._script_filter.currentIndexChanged.connect(self._on_filter_changed)
        filters_layout.addWidget(self._script_filter)

        filters_layout.addStretch(1)

        refresh_button = PrimaryButton("Обновить")
        refresh_button.clicked.connect(self._refresh_view)
        filters_layout.addWidget(refresh_button)

        central_layout.addLayout(filters_layout)

        self._table = QTableWidget(self)
        self._table.setColumnCount(6)
        self._table.setHorizontalHeaderLabels([
            "Run ID",
            "Скрипт",
            "Начало",
            "Длительность",
            "Статус",
            "Действия",
        ])

        header_view = self._table.horizontalHeader()
        header_view.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header_view.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header_view.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header_view.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header_view.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header_view.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)

        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.setAlternatingRowColors(True)

        central_layout.addWidget(self._table, stretch=1)

        self.setCentralWidget(central_widget)

        self._refresh_view()

    def _on_filter_changed(self) -> None:
        """Handle filter change event."""
        self._refresh_view()

    def _refresh_view(self) -> None:
        """Refresh the view by fetching current logs and updating the UI."""
        try:
            status = self._status_filter.currentData()
            script_id_text = self._script_filter.currentText()
            script_id = None if script_id_text == "Все" else script_id_text

            logs = self._get_logs(50, status, script_id)
            self._model.update_logs(logs)

            self._update_script_filter(logs)
            self._update_ui()
        except Exception:
            pass

    def _update_script_filter(self, logs: list[ExecutionLog]) -> None:
        """Update script filter dropdown with unique script IDs from logs."""
        current_text = self._script_filter.currentText()

        unique_scripts = sorted(set(log.script_id for log in logs))

        self._script_filter.blockSignals(True)
        self._script_filter.clear()
        self._script_filter.addItem("Все", None)

        for script_id in unique_scripts:
            self._script_filter.addItem(script_id, script_id)

        index = self._script_filter.findText(current_text)
        if index >= 0:
            self._script_filter.setCurrentIndex(index)
        else:
            self._script_filter.setCurrentIndex(0)

        self._script_filter.blockSignals(False)

    def _update_ui(self) -> None:
        """Update the UI based on the current model."""
        self._table.setRowCount(0)

        if not self._model.logs:
            return

        for log in self._model.logs:
            self._add_log_row(log)

    def _add_log_row(self, log: ExecutionLog) -> None:
        """Add a log row to the table.

        Args:
            log: Execution log to display.
        """
        row_position = self._table.rowCount()
        self._table.insertRow(row_position)

        run_id_item = QTableWidgetItem(log.run_id[:8])
        run_id_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
        run_id_item.setToolTip(log.run_id)
        self._table.setItem(row_position, 0, run_id_item)

        script_item = QTableWidgetItem(log.script_id)
        script_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
        self._table.setItem(row_position, 1, script_item)

        start_time_str = log.start_time.strftime("%Y-%m-%d %H:%M:%S")
        start_item = QTableWidgetItem(start_time_str)
        start_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
        self._table.setItem(row_position, 2, start_item)

        duration = (log.end_time - log.start_time).total_seconds()
        duration_item = QTableWidgetItem(f"{duration:.2f}s")
        duration_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
        self._table.setItem(row_position, 3, duration_item)

        status_item = self._create_status_item(log)
        self._table.setItem(row_position, 4, status_item)

        actions_widget = QWidget()
        actions_layout = QHBoxLayout(actions_widget)
        actions_layout.setContentsMargins(4, 4, 4, 4)
        actions_layout.setSpacing(4)

        details_button = SecondaryButton("Детали")
        details_button.clicked.connect(
            lambda _checked=False, run_id=log.run_id: self._on_show_details(run_id)
        )
        actions_layout.addWidget(details_button)

        repeat_button = PrimaryButton("Повторить")
        repeat_button.clicked.connect(
            lambda _checked=False, run_id=log.run_id: self._on_repeat_action(run_id)
        )
        actions_layout.addWidget(repeat_button)

        self._table.setCellWidget(row_position, 5, actions_widget)

    def _create_status_item(self, log: ExecutionLog) -> QTableWidgetItem:
        """Create a status table item with appropriate styling.

        Args:
            log: Execution log.

        Returns:
            Styled table widget item.
        """
        status_text = {
            "success": "✓ Успех",
            "failure": "✗ Ошибка",
            "error": "✗ Исключение",
        }.get(log.status, log.status)

        status_item = QTableWidgetItem(status_text)
        status_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)

        if log.status == "success":
            status_item.setForeground(Qt.GlobalColor.darkGreen)
        else:
            status_item.setForeground(Qt.GlobalColor.red)

        if log.error_message:
            status_item.setToolTip(log.error_message)

        return status_item

    def _on_show_details(self, run_id: str) -> None:
        """Handle show details button click.

        Args:
            run_id: Run ID to show details for.
        """
        try:
            log = next((log for log in self._model.logs if log.run_id == run_id), None)
            if log is None:
                self._show_error_dialog("Ошибка", "Лог не найден")
                return

            existing_dialog = self._detail_dialogs.get(run_id)
            if existing_dialog is not None:
                existing_dialog.raise_()
                existing_dialog.activateWindow()
                return

            details_dialog = LogDetailsDialog(
                log=log,
                on_repeat=self._on_repeat_action,
                parent=self,
            )
            details_dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
            details_dialog.destroyed.connect(lambda _=None, rid=run_id: self._detail_dialogs.pop(rid, None))
            self._detail_dialogs[run_id] = details_dialog
            details_dialog.show()
        except Exception as exc:
            self._show_error_dialog("Ошибка отображения деталей", str(exc))

    def _on_repeat_action(self, run_id: str) -> None:
        """Handle repeat action button click.

        Args:
            run_id: Run ID to repeat.
        """
        try:
            success, error_message = self._repeat_action(run_id)
            if not success:
                self._show_error_dialog(
                    "Ошибка повтора действия",
                    error_message or f"Не удалось повторить действие для run_id: {run_id}",
                )
            else:
                self._show_info_dialog(
                    "Повтор действия",
                    "Действие успешно запущено повторно",
                )
                self._refresh_view()
        except KeyError:
            self._show_error_dialog(
                "Ошибка повтора действия",
                "Не удалось найти данные для повтора. Возможно, лог был удалён.",
            )
        except FileNotFoundError:
            self._show_error_dialog(
                "Ошибка повтора действия",
                "Один или несколько файлов, использованных в оригинальном выполнении, были удалены.",
            )
        except Exception as exc:
            self._show_error_dialog("Ошибка повтора действия", str(exc))

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

    def _show_info_dialog(self, title: str, message: str) -> None:
        """Show an info message dialog.

        Args:
            title: Dialog title.
            message: Info message.
        """
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Icon.Information)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg_box.exec()
