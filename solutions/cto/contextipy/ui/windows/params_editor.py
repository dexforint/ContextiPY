"""Parameter editor window for script configuration."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

try:  # pragma: no cover
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import (
        QCheckBox,
        QComboBox,
        QDialog,
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
except ImportError:  # pragma: no cover
    Qt = None  # type: ignore[assignment]
    QCheckBox = object  # type: ignore[assignment,misc]
    QComboBox = object  # type: ignore[assignment,misc]
    QDialog = object  # type: ignore[assignment,misc]
    QDoubleSpinBox = object  # type: ignore[assignment,misc]
    QFormLayout = object  # type: ignore[assignment,misc]
    QHBoxLayout = object  # type: ignore[assignment,misc]
    QLabel = object  # type: ignore[assignment,misc]
    QLineEdit = object  # type: ignore[assignment,misc]
    QMessageBox = object  # type: ignore[assignment,misc]
    QPushButton = object  # type: ignore[assignment,misc]
    QScrollArea = object  # type: ignore[assignment,misc]
    QSpinBox = object  # type: ignore[assignment,misc]
    QVBoxLayout = object  # type: ignore[assignment,misc]
    QWidget = object  # type: ignore[assignment,misc]
    PYSIDE_AVAILABLE = False
else:
    PYSIDE_AVAILABLE = True

if TYPE_CHECKING:
    from contextipy.core.metadata import ParameterMetadata
    from contextipy.scanner.registry import RegisteredScript

from ..icons import APP_ICON_NAME, load_icon
from ..theme import get_theme
from ..widgets import Heading, PrimaryButton, SecondaryButton


class ParamsEditorWindow(QDialog):
    """Window for editing script parameters with dynamic form generation."""

    def __init__(
        self,
        *,
        script: RegisteredScript,
        parameters_metadata: list[ParameterMetadata] | None = None,
        save_callback: Callable[[str, dict[str, Any]], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        """Initialize the parameter editor window.

        Args:
            script: The registered script to edit parameters for.
            parameters_metadata: Optional list of parameter metadata for dynamic form generation.
            save_callback: Optional callback to save parameters. Receives script_id and parameters dict.
            parent: Parent widget.
        """
        if not PYSIDE_AVAILABLE:
            raise RuntimeError("PySide6 is not available")

        super().__init__(parent)

        self._script = script
        self._parameters_metadata = parameters_metadata or []
        self._save_callback = save_callback
        self._param_widgets: dict[str, QWidget] = {}
        self._validation_labels: dict[str, QLabel] = {}
        self._original_values: dict[str, Any] = {}

        theme = get_theme()
        self._spacing = theme.spacing

        self.setWindowTitle(f"Параметры: {script.scanned.title}")
        self.setMinimumSize(500, 400)
        self.setModal(True)

        icon = load_icon(APP_ICON_NAME)
        if not icon.isNull():
            self.setWindowIcon(icon)

        self._setup_ui()
        self._load_current_values()

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(self._spacing.lg)
        main_layout.setContentsMargins(
            self._spacing.xl,
            self._spacing.xl,
            self._spacing.xl,
            self._spacing.xl,
        )

        header = Heading(f"Параметры скрипта", level=2)
        header.setAlignment(Qt.AlignmentFlag.AlignLeft)
        main_layout.addWidget(header)

        script_info = QLabel(
            f"<b>{self._script.scanned.title}</b><br/>"
            f"<small>{self._script.scanned.description}</small>"
        )
        script_info.setWordWrap(True)
        main_layout.addWidget(script_info)

        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)

        form_widget = QWidget()
        form_layout = QFormLayout(form_widget)
        form_layout.setSpacing(self._spacing.md)
        form_layout.setContentsMargins(0, 0, 0, 0)

        if self._parameters_metadata:
            for param_meta in self._parameters_metadata:
                self._add_parameter_field(form_layout, param_meta)
        elif self._script.scanned.parameters:
            for param_name in self._script.scanned.parameters:
                self._add_simple_parameter_field(form_layout, param_name)
        else:
            no_params_label = QLabel("Этот скрипт не имеет настраиваемых параметров.")
            no_params_label.setProperty("secondary", True)
            form_layout.addRow(no_params_label)

        scroll_area.setWidget(form_widget)
        main_layout.addWidget(scroll_area, stretch=1)

        button_layout = QHBoxLayout()
        button_layout.setSpacing(self._spacing.md)

        reset_button = SecondaryButton("Сбросить")
        reset_button.setToolTip("Сбросить все параметры к значениям по умолчанию")
        reset_button.clicked.connect(self._on_reset)
        button_layout.addWidget(reset_button)

        button_layout.addStretch(1)

        cancel_button = SecondaryButton("Отмена")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        save_button = PrimaryButton("Сохранить")
        save_button.clicked.connect(self._on_save)
        button_layout.addWidget(save_button)

        main_layout.addLayout(button_layout)

    def _add_parameter_field(
        self, layout: QFormLayout, param_meta: ParameterMetadata
    ) -> None:
        """Add a parameter field to the form with full metadata.

        Args:
            layout: The form layout to add the field to.
            param_meta: Parameter metadata containing type and validation info.
        """
        widget_container = QWidget()
        container_layout = QVBoxLayout(widget_container)
        container_layout.setSpacing(4)
        container_layout.setContentsMargins(0, 0, 0, 0)

        widget = self._create_widget_for_type(param_meta)
        self._param_widgets[param_meta.name] = widget
        container_layout.addWidget(widget)

        validation_label = QLabel()
        validation_label.setProperty("error", True)
        validation_label.setWordWrap(True)
        validation_label.hide()
        self._validation_labels[param_meta.name] = validation_label
        container_layout.addWidget(validation_label)

        label_text = f"{param_meta.title}"
        if param_meta.required:
            label_text += " *"
        label_widget = QLabel(label_text)
        label_widget.setToolTip(param_meta.description)

        layout.addRow(label_widget, widget_container)

    def _add_simple_parameter_field(self, layout: QFormLayout, param_name: str) -> None:
        """Add a simple parameter field without full metadata.

        Args:
            layout: The form layout to add the field to.
            param_name: Name of the parameter.
        """
        widget_container = QWidget()
        container_layout = QVBoxLayout(widget_container)
        container_layout.setSpacing(4)
        container_layout.setContentsMargins(0, 0, 0, 0)

        widget = QLineEdit()
        widget.setPlaceholderText(f"Введите значение для {param_name}")
        self._param_widgets[param_name] = widget
        container_layout.addWidget(widget)

        validation_label = QLabel()
        validation_label.setProperty("error", True)
        validation_label.setWordWrap(True)
        validation_label.hide()
        self._validation_labels[param_name] = validation_label
        container_layout.addWidget(validation_label)

        layout.addRow(QLabel(param_name), widget_container)

    def _create_widget_for_type(self, param_meta: ParameterMetadata) -> QWidget:
        """Create an appropriate widget based on parameter type annotation.

        Args:
            param_meta: Parameter metadata.

        Returns:
            Widget suitable for the parameter type.
        """
        annotation = param_meta.annotation

        if annotation is None:
            widget = QLineEdit()
            widget.setPlaceholderText(param_meta.description)
            return widget

        annotation_str = str(annotation)

        if annotation is bool or "bool" in annotation_str.lower():
            checkbox = QCheckBox()
            return checkbox

        if annotation is int or "int" in annotation_str.lower():
            spinbox = QSpinBox()
            spinbox.setRange(-2147483648, 2147483647)
            if not param_meta.required and param_meta.default != inspect.Parameter.empty:
                try:
                    spinbox.setValue(int(param_meta.default))
                except (TypeError, ValueError):
                    pass
            return spinbox

        if annotation is float or "float" in annotation_str.lower():
            spinbox = QDoubleSpinBox()
            spinbox.setRange(-1e10, 1e10)
            spinbox.setDecimals(4)
            if not param_meta.required and param_meta.default != inspect.Parameter.empty:
                try:
                    spinbox.setValue(float(param_meta.default))
                except (TypeError, ValueError):
                    pass
            return spinbox

        if hasattr(annotation, "__origin__"):
            origin = getattr(annotation, "__origin__", None)
            if origin is list or origin is tuple:
                widget = QLineEdit()
                widget.setPlaceholderText("Введите значения через запятую")
                return widget

        widget = QLineEdit()
        widget.setPlaceholderText(param_meta.description)
        return widget

    def _load_current_values(self) -> None:
        """Load current parameter values from the script settings."""
        overrides = self._script.settings.parameter_overrides or {}

        for param_name, widget in self._param_widgets.items():
            value = overrides.get(param_name)
            self._original_values[param_name] = value

            if value is not None:
                self._set_widget_value(widget, value)
            else:
                param_meta = self._get_parameter_metadata(param_name)
                if param_meta and param_meta.default != inspect.Parameter.empty:
                    self._set_widget_value(widget, param_meta.default)

    def _set_widget_value(self, widget: QWidget, value: Any) -> None:
        """Set the value of a widget.

        Args:
            widget: The widget to set the value for.
            value: The value to set.
        """
        if isinstance(widget, QCheckBox):
            widget.setChecked(bool(value))
        elif isinstance(widget, QSpinBox):
            try:
                widget.setValue(int(value))
            except (TypeError, ValueError):
                pass
        elif isinstance(widget, QDoubleSpinBox):
            try:
                widget.setValue(float(value))
            except (TypeError, ValueError):
                pass
        elif isinstance(widget, QComboBox):
            index = widget.findText(str(value))
            if index >= 0:
                widget.setCurrentIndex(index)
        elif isinstance(widget, QLineEdit):
            if isinstance(value, (list, tuple, dict)):
                widget.setText(json.dumps(value))
            else:
                widget.setText(str(value))

    def _get_widget_value(self, widget: QWidget) -> Any:
        """Get the value from a widget.

        Args:
            widget: The widget to get the value from.

        Returns:
            The widget's current value.
        """
        if isinstance(widget, QCheckBox):
            return widget.isChecked()
        elif isinstance(widget, QSpinBox):
            return widget.value()
        elif isinstance(widget, QDoubleSpinBox):
            return widget.value()
        elif isinstance(widget, QComboBox):
            return widget.currentText()
        elif isinstance(widget, QLineEdit):
            text = widget.text().strip()
            if not text:
                return None
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return text
        return None

    def _get_parameter_metadata(self, param_name: str) -> ParameterMetadata | None:
        """Get metadata for a parameter by name.

        Args:
            param_name: Name of the parameter.

        Returns:
            Parameter metadata if found, None otherwise.
        """
        for param_meta in self._parameters_metadata:
            if param_meta.name == param_name:
                return param_meta
        return None

    def _validate_parameters(self) -> bool:
        """Validate all parameters and show feedback.

        Returns:
            True if all parameters are valid, False otherwise.
        """
        all_valid = True

        for param_name, widget in self._param_widgets.items():
            validation_label = self._validation_labels.get(param_name)
            param_meta = self._get_parameter_metadata(param_name)

            try:
                value = self._get_widget_value(widget)

                if param_meta and param_meta.required and value is None:
                    if validation_label:
                        validation_label.setText("Это поле обязательно")
                        validation_label.show()
                    all_valid = False
                else:
                    if validation_label:
                        validation_label.hide()

            except Exception as exc:
                if validation_label:
                    validation_label.setText(f"Ошибка: {exc}")
                    validation_label.show()
                all_valid = False

        return all_valid

    def _on_reset(self) -> None:
        """Handle reset button click."""
        reply = QMessageBox.question(
            self,
            "Сбросить параметры",
            "Вы уверены, что хотите сбросить все параметры к значениям по умолчанию?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            for param_name, widget in self._param_widgets.items():
                param_meta = self._get_parameter_metadata(param_name)
                if param_meta and param_meta.default != inspect.Parameter.empty:
                    self._set_widget_value(widget, param_meta.default)
                else:
                    if isinstance(widget, QCheckBox):
                        widget.setChecked(False)
                    elif isinstance(widget, QSpinBox):
                        widget.setValue(0)
                    elif isinstance(widget, QDoubleSpinBox):
                        widget.setValue(0.0)
                    elif isinstance(widget, QLineEdit):
                        widget.clear()

                validation_label = self._validation_labels.get(param_name)
                if validation_label:
                    validation_label.hide()

    def _on_save(self) -> None:
        """Handle save button click."""
        if not self._validate_parameters():
            QMessageBox.warning(
                self,
                "Ошибка валидации",
                "Пожалуйста, исправьте ошибки валидации перед сохранением.",
            )
            return

        parameters: dict[str, Any] = {}
        for param_name, widget in self._param_widgets.items():
            value = self._get_widget_value(widget)
            if value is not None:
                parameters[param_name] = value

        if self._save_callback:
            try:
                self._save_callback(self._script.script_id, parameters)
                self.accept()
            except Exception as exc:
                QMessageBox.critical(
                    self,
                    "Ошибка сохранения",
                    f"Не удалось сохранить параметры: {exc}",
                )
        else:
            self.accept()

    def get_parameters(self) -> dict[str, Any]:
        """Get the current parameter values from the form.

        Returns:
            Dictionary of parameter names to values.
        """
        parameters: dict[str, Any] = {}
        for param_name, widget in self._param_widgets.items():
            value = self._get_widget_value(widget)
            if value is not None:
                parameters[param_name] = value
        return parameters


import inspect

__all__ = [
    "ParamsEditorWindow",
]
