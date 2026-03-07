from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QDoubleSpinBox,
    QVBoxLayout,
    QWidget,
)

from pcontext.runtime.question_models import QuestionFieldSchema, QuestionFormSchema


@dataclass(slots=True)
class _FieldBinding:
    """
    Связка между схемой поля и Qt-редактором.
    """

    field: QuestionFieldSchema
    widget: QWidget


def _int_minimum(field: QuestionFieldSchema) -> int:
    """
    Возвращает нижнюю границу для int-поля.
    """
    if field.ge is not None:
        return math.ceil(field.ge)
    if field.gt is not None:
        return math.floor(field.gt) + 1
    return -2_147_483_648


def _int_maximum(field: QuestionFieldSchema) -> int:
    """
    Возвращает верхнюю границу для int-поля.
    """
    if field.le is not None:
        return math.floor(field.le)
    if field.lt is not None:
        return math.ceil(field.lt) - 1
    return 2_147_483_647


def _float_minimum(field: QuestionFieldSchema) -> float:
    """
    Возвращает нижнюю границу для float-поля.
    """
    if field.ge is not None:
        return float(field.ge)
    if field.gt is not None:
        return float(field.gt) + 1e-9
    return -1_000_000_000.0


def _float_maximum(field: QuestionFieldSchema) -> float:
    """
    Возвращает верхнюю границу для float-поля.
    """
    if field.le is not None:
        return float(field.le)
    if field.lt is not None:
        return float(field.lt) - 1e-9
    return 1_000_000_000.0


class _PathEditor(QWidget):
    """
    Поле ввода пути с кнопкой выбора файла.
    """

    def __init__(self, *, image_only: bool, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._image_only = image_only

        self._line_edit = QLineEdit(self)
        self._browse_button = QPushButton("Обзор", self)
        self._browse_button.clicked.connect(self._browse)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._line_edit)
        layout.addWidget(self._browse_button)

    def set_value(self, value: str) -> None:
        """
        Устанавливает текст пути.
        """
        self._line_edit.setText(value)

    def value(self) -> str:
        """
        Возвращает текущее значение.
        """
        return self._line_edit.text()

    def _browse(self) -> None:
        """
        Открывает диалог выбора файла.
        """
        file_filter = (
            "Изображения (*.png *.jpg *.jpeg *.bmp *.webp *.gif *.tif *.tiff)"
            if self._image_only
            else "Все файлы (*)"
        )

        selected_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выбор файла",
            "",
            file_filter,
        )

        if selected_path:
            self._line_edit.setText(selected_path)


class AskDialog(QDialog):
    """
    Модальный диалог Ask(...).
    """

    def __init__(
        self,
        schema: QuestionFormSchema,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._schema = schema
        self._bindings: list[_FieldBinding] = []

        self.setWindowTitle(schema.title)
        self.resize(600, 460)
        self.setModal(True)

        self._build_ui()

    def _build_ui(self) -> None:
        """
        Собирает интерфейс формы.
        """
        root_layout = QVBoxLayout(self)

        form_container = QWidget(self)
        form_layout = QFormLayout(form_container)
        form_layout.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow
        )

        for field in self._schema.fields:
            editor = self._create_editor(field)
            self._bindings.append(_FieldBinding(field=field, widget=editor))

            label_text = field.title
            if field.description:
                label_text = f"{label_text}\n{field.description}"

            form_layout.addRow(label_text, editor)

        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(form_container)
        root_layout.addWidget(scroll_area)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            Qt.Orientation.Horizontal,
            self,
        )
        buttons.accepted.connect(self._accept_with_validation)
        buttons.rejected.connect(self.reject)
        root_layout.addWidget(buttons)

    def _create_editor(self, field: QuestionFieldSchema) -> QWidget:
        """
        Создаёт редактор под конкретное поле.
        """
        if field.format == "image_path":
            editor = _PathEditor(image_only=True, parent=self)
            if field.default_value is not None:
                editor.set_value(str(field.default_value))
            return editor

        if field.value_kind == "bool":
            checkbox = QCheckBox(self)
            checkbox.setChecked(bool(field.default_value))
            return checkbox

        if field.value_kind == "int":
            spinbox = QSpinBox(self)
            spinbox.setRange(_int_minimum(field), _int_maximum(field))
            spinbox.setValue(
                int(field.default_value) if field.default_value is not None else 0
            )
            return spinbox

        if field.value_kind == "float":
            spinbox = QDoubleSpinBox(self)
            spinbox.setDecimals(6)
            spinbox.setRange(_float_minimum(field), _float_maximum(field))
            spinbox.setValue(
                float(field.default_value) if field.default_value is not None else 0.0
            )
            return spinbox

        if field.value_kind == "enum":
            combobox = QComboBox(self)
            for enum_value in field.enum_values:
                combobox.addItem(str(enum_value), userData=enum_value)

            if field.default_value is not None:
                index = combobox.findData(field.default_value)
                if index >= 0:
                    combobox.setCurrentIndex(index)

            return combobox

        line_edit = QLineEdit(self)
        if field.default_value is not None:
            line_edit.setText(str(field.default_value))
        return line_edit

    def _read_value(self, binding: _FieldBinding) -> Any:
        """
        Читает значение из Qt-виджета.
        """
        widget = binding.widget

        if isinstance(widget, _PathEditor):
            return widget.value()

        if isinstance(widget, QCheckBox):
            return widget.isChecked()

        if isinstance(widget, QSpinBox):
            return widget.value()

        if isinstance(widget, QDoubleSpinBox):
            return widget.value()

        if isinstance(widget, QComboBox):
            return widget.currentData()

        if isinstance(widget, QLineEdit):
            return widget.text()

        raise TypeError("Неподдерживаемый тип Ask-редактора.")

    def _accept_with_validation(self) -> None:
        """
        Пытается закрыть форму с подтверждением.
        """
        try:
            self.get_answers()
        except Exception as error:  # noqa: BLE001
            QMessageBox.warning(self, "Ask", str(error))
            return

        self.accept()

    def get_answers(self) -> dict[str, Any]:
        """
        Возвращает собранные ответы пользователя.
        """
        answers: dict[str, Any] = {}

        for binding in self._bindings:
            value = self._read_value(binding)
            field = binding.field

            if (
                field.required
                and field.value_kind in {"str", "path", "unknown"}
                and field.format != "image_path"
            ):
                if isinstance(value, str) and not value:
                    raise ValueError(
                        f"Поле '{field.title}' обязательно для заполнения."
                    )

            if field.required and field.format == "image_path":
                if isinstance(value, str) and not value:
                    raise ValueError(f"Нужно выбрать файл для поля '{field.title}'.")

            answers[field.name] = value

        return answers
