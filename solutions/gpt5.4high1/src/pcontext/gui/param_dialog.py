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
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from pcontext.gui.backend import ParameterOwnerDetails
from pcontext.registrar.models import ParamArgumentManifest


@dataclass(slots=True)
class _EditorBinding:
    """
    Связка между декларацией параметра и конкретным Qt-виджетом.
    """

    parameter: ParamArgumentManifest
    widget: QWidget


def _int_minimum(parameter: ParamArgumentManifest) -> int:
    """
    Вычисляет минимально допустимое значение для int-виджета.
    """
    if parameter.ge is not None:
        return math.ceil(parameter.ge)
    if parameter.gt is not None:
        return math.floor(parameter.gt) + 1
    return -2_147_483_648


def _int_maximum(parameter: ParamArgumentManifest) -> int:
    """
    Вычисляет максимально допустимое значение для int-виджета.
    """
    if parameter.le is not None:
        return math.floor(parameter.le)
    if parameter.lt is not None:
        return math.ceil(parameter.lt) - 1
    return 2_147_483_647


def _float_minimum(parameter: ParamArgumentManifest) -> float:
    """
    Вычисляет минимум для float-виджета.
    """
    if parameter.ge is not None:
        return float(parameter.ge)
    if parameter.gt is not None:
        return float(parameter.gt) + 1e-9
    return -1_000_000_000.0


def _float_maximum(parameter: ParamArgumentManifest) -> float:
    """
    Вычисляет максимум для float-виджета.
    """
    if parameter.le is not None:
        return float(parameter.le)
    if parameter.lt is not None:
        return float(parameter.lt) - 1e-9
    return 1_000_000_000.0


class ParameterDialog(QDialog):
    """
    Диалог редактирования параметров скрипта, сервиса или service.script.
    """

    def __init__(
        self,
        details: ParameterOwnerDetails,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._details = details
        self._bindings: list[_EditorBinding] = []

        self.setWindowTitle(f"Параметры: {details.owner_title}")
        self.setModal(True)
        self.resize(560, 420)

        self._build_ui()

    def _build_ui(self) -> None:
        """
        Собирает содержимое окна.
        """
        root_layout = QVBoxLayout(self)

        info_label = QLabel(
            f"<b>{self._details.owner_title}</b><br>"
            f"ID: <code>{self._details.owner_id}</code>"
        )
        info_label.setTextFormat(Qt.TextFormat.RichText)
        info_label.setWordWrap(True)
        root_layout.addWidget(info_label)

        form_container = QWidget(self)
        form_layout = QFormLayout(form_container)
        form_layout.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow
        )

        for parameter in self._details.parameters:
            current_value = self._details.current_values.get(
                parameter.name, parameter.default
            )
            editor = self._create_editor(parameter, current_value)
            self._bindings.append(_EditorBinding(parameter=parameter, widget=editor))

            label_text = parameter.title or parameter.name
            if parameter.description:
                label_text = f"{label_text}\n{parameter.description}"

            label = QLabel(label_text)
            label.setWordWrap(True)
            form_layout.addRow(label, editor)

        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(form_container)
        root_layout.addWidget(scroll_area)

        buttons_layout = QHBoxLayout()

        reset_button = QPushButton("Сбросить")
        reset_button.clicked.connect(self._reset_to_defaults)
        buttons_layout.addWidget(reset_button)

        buttons_layout.addStretch(1)

        dialog_buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        dialog_buttons.accepted.connect(self._accept_with_validation)
        dialog_buttons.rejected.connect(self.reject)
        buttons_layout.addWidget(dialog_buttons)

        root_layout.addLayout(buttons_layout)

    def _create_editor(self, parameter: ParamArgumentManifest, value: Any) -> QWidget:
        """
        Создаёт Qt-редактор под конкретный тип параметра.
        """
        value_kind = parameter.value_type.kind

        if value_kind == "bool":
            checkbox = QCheckBox(self)
            checkbox.setChecked(bool(value))
            return checkbox

        if value_kind == "int":
            spinbox = QSpinBox(self)
            spinbox.setRange(_int_minimum(parameter), _int_maximum(parameter))
            spinbox.setValue(int(value))
            return spinbox

        if value_kind == "float":
            spinbox = QDoubleSpinBox(self)
            spinbox.setDecimals(6)
            spinbox.setRange(_float_minimum(parameter), _float_maximum(parameter))
            spinbox.setValue(float(value))
            return spinbox

        if value_kind == "enum":
            combobox = QComboBox(self)
            for enum_value in parameter.value_type.enum_values:
                combobox.addItem(str(enum_value), userData=enum_value)

            current_index = combobox.findData(value)
            if current_index >= 0:
                combobox.setCurrentIndex(current_index)

            return combobox

        line_edit = QLineEdit(self)
        line_edit.setText("" if value is None else str(value))
        return line_edit

    def _set_widget_value(self, binding: _EditorBinding, value: Any) -> None:
        """
        Устанавливает значение в уже созданный редактор.
        """
        widget = binding.widget
        parameter = binding.parameter

        if isinstance(widget, QCheckBox):
            widget.setChecked(bool(value))
            return

        if isinstance(widget, QSpinBox):
            widget.setValue(int(value))
            return

        if isinstance(widget, QDoubleSpinBox):
            widget.setValue(float(value))
            return

        if isinstance(widget, QComboBox):
            index = widget.findData(value)
            if index >= 0:
                widget.setCurrentIndex(index)
            return

        if isinstance(widget, QLineEdit):
            widget.setText("" if value is None else str(value))
            return

        raise TypeError(
            f"Неподдерживаемый тип редактора для параметра '{parameter.name}'."
        )

    def _read_widget_value(self, binding: _EditorBinding) -> Any:
        """
        Читает значение из редактора.
        """
        widget = binding.widget

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

        raise TypeError("Неподдерживаемый тип редактора.")

    def _reset_to_defaults(self) -> None:
        """
        Возвращает все поля к default-значениям.
        """
        for binding in self._bindings:
            self._set_widget_value(binding, binding.parameter.default)

    def _accept_with_validation(self) -> None:
        """
        Пытается закрыть диалог с сохранением.

        Здесь базовая валидация уже обеспечивается самими виджетами.
        """
        try:
            self.get_values()
        except Exception as error:  # noqa: BLE001
            QMessageBox.critical(
                self,
                "Ошибка параметров",
                str(error),
            )
            return

        self.accept()

    def get_values(self) -> dict[str, Any]:
        """
        Возвращает текущие значения всех параметров.
        """
        values: dict[str, Any] = {}

        for binding in self._bindings:
            values[binding.parameter.name] = self._read_widget_value(binding)

        return values
