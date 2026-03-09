from __future__ import annotations

import ctypes
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent, QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QStyle,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from pcontext.config import get_paths
from pcontext.gui.style import configure_table, set_button_role
from pcontext.runtime.menu_runtime import ChooserItem


@dataclass(frozen=True, slots=True)
class _RenderedRow:
    item: ChooserItem
    updated_display: str
    updated_sort_value: float
    last_used_display: str
    last_used_sort_value: float
    tags_display: str


def _utc_to_local_display(raw_value: str | None) -> tuple[str, float]:
    if not raw_value:
        return "—", 0.0

    try:
        dt_utc = datetime.fromisoformat(raw_value)
        dt_local = dt_utc.astimezone()
        return dt_local.strftime("%d.%m.%Y %H:%M:%S"), dt_local.timestamp()
    except ValueError:
        return raw_value, 0.0


class MenuChooserDialog(QDialog):
    SORT_RECENT = "recent"
    SORT_NAME = "name"
    SORT_UPDATED = "updated"
    SORT_POPULARITY = "popularity"

    DEFAULT_COLUMN_WIDTHS = [240, 280, 170, 150, 170, 150, 90, 170]

    def __init__(
        self,
        current_folder: str | None,
        items: list[ChooserItem],
        *,
        initial_sort_mode: str | None = None,
        initial_geometry: dict[str, int] | None = None,
        initial_column_widths: list[int] | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._current_folder = current_folder
        self._items = items

        self._shown_at_monotonic: float | None = None
        self._startup_close_guard_seconds = 0.6

        self.setWindowTitle("PContext")
        self.resize(1180, 680)
        self.setModal(True)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)

        self._build_ui()
        self._apply_initial_sort_mode(initial_sort_mode)
        self._apply_initial_geometry(initial_geometry)
        self._apply_initial_column_widths(initial_column_widths)
        self._refresh_table()

        QShortcut(QKeySequence("Ctrl+F"), self, activated=self._focus_search)

    def _build_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setSpacing(14)

        header_card = QFrame(self)
        header_card.setProperty("card", "true")
        header_layout = QVBoxLayout(header_card)
        header_layout.setContentsMargins(18, 18, 18, 18)
        header_layout.setSpacing(10)

        title_label = QLabel("Выберите команду PContext", header_card)
        title_label.setProperty("role", "sectionTitle")
        header_layout.addWidget(title_label)

        context_text = self._current_folder or "Контекст не передан"
        short_context = (
            context_text if len(context_text) <= 140 else context_text[:137] + "..."
        )
        self._context_label = QLabel(f"Контекст: {short_context}", header_card)
        self._context_label.setProperty("role", "muted")
        self._context_label.setToolTip(context_text)
        self._context_label.setWordWrap(True)
        header_layout.addWidget(self._context_label)

        root_layout.addWidget(header_card)

        controls_card = QFrame(self)
        controls_card.setProperty("card", "true")
        controls_layout_outer = QVBoxLayout(controls_card)
        controls_layout_outer.setContentsMargins(18, 18, 18, 18)
        controls_layout_outer.setSpacing(12)

        controls_row = QHBoxLayout()
        controls_row.setSpacing(10)

        self._search_edit = QLineEdit(self)
        self._search_edit.setPlaceholderText(
            "Поиск по названию, описанию, сервису или тегам"
        )
        self._search_edit.setClearButtonEnabled(True)
        self._search_edit.textChanged.connect(self._refresh_table)
        controls_row.addWidget(self._search_edit, 1)

        self._sort_combo = QComboBox(self)
        self._sort_combo.addItem("По последнему применению", self.SORT_RECENT)
        self._sort_combo.addItem("По названию", self.SORT_NAME)
        self._sort_combo.addItem("По дате обновления", self.SORT_UPDATED)
        self._sort_combo.addItem("По популярности", self.SORT_POPULARITY)
        self._sort_combo.currentIndexChanged.connect(self._refresh_table)
        controls_row.addWidget(self._sort_combo)

        controls_layout_outer.addLayout(controls_row)

        self._summary_label = QLabel(self)
        self._summary_label.setProperty("role", "muted")
        self._summary_label.setWordWrap(True)
        controls_layout_outer.addWidget(self._summary_label)

        root_layout.addWidget(controls_card)

        table_card = QFrame(self)
        table_card.setProperty("card", "true")
        table_layout = QVBoxLayout(table_card)
        table_layout.setContentsMargins(18, 18, 18, 18)
        table_layout.setSpacing(12)

        self._table = QTableWidget(self)
        self._table.setColumnCount(8)
        self._table.setHorizontalHeaderLabels(
            [
                "Название",
                "Описание",
                "Теги",
                "Тип",
                "Сервис",
                "Обновлено",
                "Запусков",
                "Последнее применение",
            ]
        )
        configure_table(self._table)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.itemDoubleClicked.connect(
            lambda _item: self._accept_with_validation()
        )
        table_layout.addWidget(self._table)

        buttons_row = QHBoxLayout()
        buttons_row.addStretch(1)

        self._cancel_button = QPushButton("Отмена", self)
        self._cancel_button.clicked.connect(self.reject)
        buttons_row.addWidget(self._cancel_button)

        self._run_button = QPushButton("Запустить", self)
        set_button_role(self._run_button, "primary")
        self._run_button.clicked.connect(self._accept_with_validation)
        buttons_row.addWidget(self._run_button)

        table_layout.addLayout(buttons_row)
        root_layout.addWidget(table_card)

    def _apply_initial_sort_mode(self, sort_mode: str | None) -> None:
        if not sort_mode:
            return

        index = self._sort_combo.findData(sort_mode)
        if index >= 0:
            self._sort_combo.setCurrentIndex(index)

    def _apply_initial_geometry(self, geometry: dict[str, int] | None) -> None:
        if not geometry:
            return

        x = geometry.get("x")
        y = geometry.get("y")
        width = geometry.get("width")
        height = geometry.get("height")

        if not all(isinstance(value, int) for value in (x, y, width, height)):
            return

        if width <= 200 or height <= 150:
            return

        self.setGeometry(x, y, width, height)

    def _apply_initial_column_widths(self, widths: list[int] | None) -> None:
        effective_widths = (
            widths
            if widths and len(widths) == self._table.columnCount()
            else self.DEFAULT_COLUMN_WIDTHS
        )

        for index, width in enumerate(effective_widths):
            if isinstance(width, int) and width > 40:
                self._table.setColumnWidth(index, width)

    def export_geometry_state(self) -> dict[str, int]:
        geometry = self.geometry()
        return {
            "x": geometry.x(),
            "y": geometry.y(),
            "width": geometry.width(),
            "height": geometry.height(),
        }

    def export_column_widths(self) -> list[int]:
        return [
            self._table.columnWidth(index) for index in range(self._table.columnCount())
        ]

    def current_sort_mode(self) -> str:
        value = self._sort_combo.currentData()
        return value if isinstance(value, str) else self.SORT_RECENT

    def mark_shown(self) -> None:
        """
        Помечает момент фактического показа окна.
        """
        self._shown_at_monotonic = time.monotonic()

    def bring_to_front(self) -> None:
        """
        Пытается поднять chooser поверх других окон.
        """
        self.show()
        self.raise_()
        self.activateWindow()
        self._focus_search()

        try:
            hwnd = int(self.winId())
            user32 = ctypes.windll.user32
            user32.ShowWindow(hwnd, 9)
            user32.SetForegroundWindow(hwnd)
        except Exception:
            pass

    def _focus_search(self) -> None:
        self._search_edit.setFocus()
        self._search_edit.selectAll()

    def _startup_close_guard_active(self) -> bool:
        if self._shown_at_monotonic is None:
            return True
        return (
            time.monotonic() - self._shown_at_monotonic
        ) < self._startup_close_guard_seconds

    def reject(self) -> None:
        if self._startup_close_guard_active():
            return
        super().reject()

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        if self._startup_close_guard_active():
            event.ignore()
            return
        super().closeEvent(event)

    def _refresh_table(self) -> None:
        rows = self._build_rows()
        self._table.setRowCount(len(rows))

        for row_index, row in enumerate(rows):
            self._fill_table_row(row_index, row)

        self._summary_label.setText(
            f"Найдено команд: {len(rows)} из {len(self._items)} | "
            f"Сортировка: {self._sort_combo.currentText()}"
        )

        if rows:
            self._table.selectRow(0)

    def _build_rows(self) -> list[_RenderedRow]:
        search_value = self._search_edit.text().strip().lower()
        sort_mode = self._sort_combo.currentData()

        rows: list[_RenderedRow] = []

        for item in self._items:
            tags_display = self._build_tags_display(item)

            haystack = " ".join(
                value
                for value in (
                    item.title,
                    item.description or "",
                    item.service_title or "",
                    tags_display,
                )
            ).lower()

            if search_value and search_value not in haystack:
                continue

            updated_display, updated_sort_value = _utc_to_local_display(
                item.updated_at_utc
            )
            last_used_display, last_used_sort_value = _utc_to_local_display(
                item.last_used_utc
            )

            rows.append(
                _RenderedRow(
                    item=item,
                    updated_display=updated_display,
                    updated_sort_value=updated_sort_value,
                    last_used_display=last_used_display,
                    last_used_sort_value=last_used_sort_value,
                    tags_display=tags_display,
                )
            )

        if sort_mode == self.SORT_NAME:
            rows.sort(key=lambda row: (row.item.title.lower(), row.item.id))
        elif sort_mode == self.SORT_UPDATED:
            rows.sort(
                key=lambda row: (
                    -row.updated_sort_value,
                    row.item.title.lower(),
                    row.item.id,
                )
            )
        elif sort_mode == self.SORT_POPULARITY:
            rows.sort(
                key=lambda row: (
                    -row.item.launch_count,
                    -row.last_used_sort_value,
                    row.item.title.lower(),
                    row.item.id,
                )
            )
        else:
            rows.sort(
                key=lambda row: (
                    -row.last_used_sort_value,
                    -row.item.launch_count,
                    -row.updated_sort_value,
                    row.item.title.lower(),
                    row.item.id,
                )
            )

        return rows

    def _build_tags_display(self, item: ChooserItem) -> str:
        tags: list[str] = []

        if item.has_parameters:
            tags.append("params")

        if item.kind == "service_script":
            tags.append("service")

        if item.registration_status == "error":
            tags.append("broken")
        elif item.registration_status == "untracked":
            tags.append("untracked")

        return " • ".join(tags) if tags else "—"

    def _resolve_row_icon(self, item: ChooserItem) -> QIcon:
        if item.icon_name:
            icon_path = Path(item.icon_name)
            if not icon_path.is_absolute():
                icon_path = get_paths().icons / item.icon_name

            if icon_path.is_file():
                icon = QIcon(str(icon_path))
                if not icon.isNull():
                    return icon

        app_style = QApplication.style()
        if item.kind == "service_script":
            return app_style.standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)

        return app_style.standardIcon(QStyle.StandardPixmap.SP_FileIcon)

    def _fill_table_row(self, row_index: int, row: _RenderedRow) -> None:
        item = row.item
        kind_text = "Oneshot" if item.kind == "oneshot_script" else "Service method"
        service_text = item.service_title or "—"
        description_text = item.description or "—"

        title_item = QTableWidgetItem(self._resolve_row_icon(item), item.title)
        title_item.setData(Qt.ItemDataRole.UserRole, item.id)
        title_item.setToolTip(item.id)
        self._table.setItem(row_index, 0, title_item)

        description_item = QTableWidgetItem(description_text)
        description_item.setToolTip(description_text)
        self._table.setItem(row_index, 1, description_item)

        tags_item = QTableWidgetItem(row.tags_display)
        tags_item.setToolTip(row.tags_display)
        self._table.setItem(row_index, 2, tags_item)

        self._table.setItem(row_index, 3, QTableWidgetItem(kind_text))
        self._table.setItem(row_index, 4, QTableWidgetItem(service_text))
        self._table.setItem(row_index, 5, QTableWidgetItem(row.updated_display))
        self._table.setItem(row_index, 6, QTableWidgetItem(str(item.launch_count)))
        self._table.setItem(row_index, 7, QTableWidgetItem(row.last_used_display))

    def _accept_with_validation(self) -> None:
        selected_id = self.get_selected_menu_item_id()
        if selected_id is None:
            QMessageBox.warning(
                self,
                "PContext",
                "Нужно выбрать команду.",
            )
            return

        self.accept()

    def get_selected_menu_item_id(self) -> str | None:
        current_row = self._table.currentRow()
        if current_row < 0:
            return None

        title_item = self._table.item(current_row, 0)
        if title_item is None:
            return None

        value = title_item.data(Qt.ItemDataRole.UserRole)
        if isinstance(value, str):
            return value

        return None
