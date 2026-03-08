from __future__ import annotations

import ctypes
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QStyle,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from pcontext.config import get_paths
from pcontext.runtime.menu_runtime import ChooserItem


@dataclass(frozen=True, slots=True)
class _RenderedRow:
    """
    Одна строка таблицы chooser после фильтрации и сортировки.
    """

    item: ChooserItem
    updated_display: str
    updated_sort_value: float
    last_used_display: str
    last_used_sort_value: float
    tags_display: str


def _utc_to_local_display(raw_value: str | None) -> tuple[str, float]:
    """
    Преобразует UTC ISO-время в строку локального времени и числовой ключ сортировки.
    """
    if not raw_value:
        return "—", 0.0

    try:
        dt_utc = datetime.fromisoformat(raw_value)
        dt_local = dt_utc.astimezone()
        return dt_local.strftime("%d.%m.%Y %H:%M:%S"), dt_local.timestamp()
    except ValueError:
        return raw_value, 0.0


class MenuChooserDialog(QDialog):
    """
    Диалог выбора команды PContext с поиском и сортировкой.
    """

    SORT_RECENT = "recent"
    SORT_NAME = "name"
    SORT_UPDATED = "updated"
    SORT_POPULARITY = "popularity"

    DEFAULT_COLUMN_WIDTHS = [240, 280, 170, 170, 150, 90, 170, 170]

    def __init__(
        self,
        current_folder: str | None,
        items: list[ChooserItem],
        *,
        initial_sort_mode: str | None = None,
        initial_geometry: dict[str, int] | None = None,
        initial_column_widths: list[int] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._current_folder = current_folder
        self._items = items

        self.setWindowTitle("PContext")
        self.resize(1120, 620)
        self.setModal(True)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)

        self._build_ui()
        self._apply_initial_sort_mode(initial_sort_mode)
        self._apply_initial_geometry(initial_geometry)
        self._apply_initial_column_widths(initial_column_widths)
        self._refresh_table()

        QShortcut(QKeySequence("Ctrl+F"), self, activated=self._focus_search)
        QTimer.singleShot(0, self._bring_to_front)

    def _build_ui(self) -> None:
        """
        Собирает интерфейс chooser-диалога.
        """
        layout = QVBoxLayout(self)

        header_text = "Выберите команду PContext"
        if self._current_folder:
            short_folder = self._current_folder
            if len(short_folder) > 120:
                short_folder = short_folder[:117] + "..."
            header_text += f"\n\nКонтекст:\n{short_folder}"

        self._header_label = QLabel(header_text, self)
        self._header_label.setWordWrap(True)
        if self._current_folder:
            self._header_label.setToolTip(self._current_folder)
        layout.addWidget(self._header_label)

        controls_layout = QHBoxLayout()

        self._search_edit = QLineEdit(self)
        self._search_edit.setPlaceholderText(
            "Поиск по названию, описанию, сервису или тегам"
        )
        self._search_edit.textChanged.connect(self._refresh_table)
        controls_layout.addWidget(self._search_edit)

        self._sort_combo = QComboBox(self)
        self._sort_combo.addItem("По последнему применению", self.SORT_RECENT)
        self._sort_combo.addItem("По названию", self.SORT_NAME)
        self._sort_combo.addItem("По дате обновления", self.SORT_UPDATED)
        self._sort_combo.addItem("По популярности", self.SORT_POPULARITY)
        self._sort_combo.currentIndexChanged.connect(self._refresh_table)
        controls_layout.addWidget(self._sort_combo)

        layout.addLayout(controls_layout)

        self._summary_label = QLabel(self)
        self._summary_label.setWordWrap(True)
        layout.addWidget(self._summary_label)

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

        header = self._table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)

        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.itemDoubleClicked.connect(
            lambda _item: self._accept_with_validation()
        )
        layout.addWidget(self._table)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            Qt.Orientation.Horizontal,
            self,
        )
        buttons.accepted.connect(self._accept_with_validation)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _apply_initial_sort_mode(self, sort_mode: str | None) -> None:
        """
        Применяет сохранённую сортировку chooser.
        """
        if not sort_mode:
            return

        index = self._sort_combo.findData(sort_mode)
        if index >= 0:
            self._sort_combo.setCurrentIndex(index)

    def _apply_initial_geometry(self, geometry: dict[str, int] | None) -> None:
        """
        Применяет сохранённые размеры и позицию окна.
        """
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
        """
        Применяет сохранённые размеры колонок.
        """
        effective_widths = (
            widths
            if widths and len(widths) == self._table.columnCount()
            else self.DEFAULT_COLUMN_WIDTHS
        )

        for index, width in enumerate(effective_widths):
            if isinstance(width, int) and width > 40:
                self._table.setColumnWidth(index, width)

    def export_geometry_state(self) -> dict[str, int]:
        """
        Возвращает текущее положение и размер chooser.
        """
        geometry = self.geometry()
        return {
            "x": geometry.x(),
            "y": geometry.y(),
            "width": geometry.width(),
            "height": geometry.height(),
        }

    def export_column_widths(self) -> list[int]:
        """
        Возвращает текущую ширину всех колонок таблицы.
        """
        return [
            self._table.columnWidth(index) for index in range(self._table.columnCount())
        ]

    def current_sort_mode(self) -> str:
        """
        Возвращает текущий режим сортировки chooser.
        """
        value = self._sort_combo.currentData()
        return value if isinstance(value, str) else self.SORT_RECENT

    def _focus_search(self) -> None:
        """
        Переводит фокус в поле поиска.
        """
        self._search_edit.setFocus()
        self._search_edit.selectAll()

    def _bring_to_front(self) -> None:
        """
        Пытается принудительно поднять chooser поверх других окон.
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

    def _refresh_table(self) -> None:
        """
        Перестраивает таблицу после фильтрации и сортировки.
        """
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
        """
        Готовит список строк chooser с фильтрацией и сортировкой.
        """
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
        """
        Собирает короткие теги команды.
        """
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
        """
        Возвращает иконку строки chooser.
        """
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
        """
        Заполняет одну строку таблицы chooser.
        """
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
        """
        Пытается завершить выбор с подтверждением.
        """
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
        """
        Возвращает id выбранного пункта.
        """
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
