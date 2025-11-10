from __future__ import annotations

"""UI rendering for questions using a PySide6 modal dialog."""

from enum import Enum
from typing import Any, Mapping, MutableMapping

try:  # pragma: no cover
    from PySide6.QtWidgets import (
        QApplication,
        QComboBox,
        QDialog,
        QDoubleSpinBox,
        QFileDialog,
        QFormLayout,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QPushButton,
        QScrollArea,
        QSpinBox,
        QVBoxLayout,
        QWidget,
    )
except ImportError:  # pragma: no cover
    QApplication = None  # type: ignore[assignment]
    QComboBox = object  # type: ignore[assignment,misc]
    QDialog = object  # type: ignore[assignment,misc]
    QDoubleSpinBox = object  # type: ignore[assignment,misc]
    QFileDialog = None  # type: ignore[assignment]
    QFormLayout = object  # type: ignore[assignment,misc]
    QHBoxLayout = object  # type: ignore[assignment,misc]
    QLabel = object  # type: ignore[assignment,misc]
    QLineEdit = object  # type: ignore[assignment,misc]
    QPushButton = object  # type: ignore[assignment,misc]
    QScrollArea = object  # type: ignore[assignment,misc]
    QSpinBox = object  # type: ignore[assignment,misc]
    QVBoxLayout = object  # type: ignore[assignment,misc]
    QWidget = object  # type: ignore[assignment,misc]
    PYSIDE_AVAILABLE = False
else:
    PYSIDE_AVAILABLE = True


class WidgetKind(str, Enum):
    """Enumeration describing the widget type required for a question."""

    TEXT = "text"
    INTEGER = "integer"
    FLOAT = "float"
    ENUM = "enum"
    IMAGE = "image"


def determine_widget_kind(question: Mapping[str, Any]) -> WidgetKind:
    """Determine the widget type required to display *question*.

    Args:
        question: Question descriptor produced by ``Questions.ui_schema``.

    Returns:
        A :class:`WidgetKind` describing the required widget.
    """

    kind = str(question.get("kind", "text")).lower()
    if kind == "image":
        return WidgetKind.IMAGE

    enum_values = question.get("enum")
    if enum_values:
        return WidgetKind.ENUM

    ge = question.get("ge")
    le = question.get("le")
    default = question.get("default")

    numeric_kinds = {
        "number",
        "numeric",
        "int",
        "integer",
        "float",
        "double",
    }

    if kind in {"int", "integer"}:
        return WidgetKind.INTEGER
    if kind in {"float", "double"}:
        return WidgetKind.FLOAT

    if kind in numeric_kinds or ge is not None or le is not None or isinstance(default, (int, float)):
        if _is_float_like(ge) or _is_float_like(le) or isinstance(default, float):
            return WidgetKind.FLOAT
        return WidgetKind.INTEGER

    return WidgetKind.TEXT


def validate_value(question: Mapping[str, Any], value: Any) -> tuple[bool, str | None]:
    """Validate *value* against *question* metadata.

    Args:
        question: Question descriptor from ``Questions.ui_schema``.
        value: Value provided by the user.

    Returns:
        Tuple of ``(is_valid, error_message)`` where ``error_message`` is ``None``
        when the value is valid.
    """

    required = bool(question.get("required", True))

    if value is None:
        if required:
            return False, "This field is required"
        return True, None

    if isinstance(value, str) and not value.strip():
        if required:
            return False, "This field is required"
        return True, None

    widget_kind = determine_widget_kind(question)

    if widget_kind is WidgetKind.INTEGER:
        try:
            numeric = int(value)
        except (TypeError, ValueError):
            return False, "Value must be an integer"
        return _validate_numeric_bounds(question, float(numeric))

    if widget_kind is WidgetKind.FLOAT:
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return False, "Value must be a number"
        return _validate_numeric_bounds(question, numeric)

    if widget_kind is WidgetKind.ENUM:
        enum_values = tuple(question.get("enum", ()))
        if not enum_values:
            return True, None

        raw_value = str(value)
        raw_name = raw_value.split(".")[-1]

        for enum_entry in enum_values:
            entry_str = str(enum_entry)
            if raw_value == entry_str:
                return True, None
            if raw_name == entry_str.split(".")[-1]:
                return True, None
        return False, f"Value must be one of: {', '.join(str(v) for v in enum_values)}"

    # Text and image questions only require the non-empty check handled above.
    return True, None


def ask(schema: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Render questions in the UI and collect answers.

    Args:
        schema: List of question descriptors to render.

    Returns:
        Dictionary of answers if the user completes the form, ``None`` if the user cancels.
    """

    if not PYSIDE_AVAILABLE:
        raise RuntimeError("PySide6 is not available")

    app = QApplication.instance()
    if app is None:
        raise RuntimeError("QApplication must be initialized before calling ask()")

    dialog = AskDialog(schema)
    result = dialog.exec()
    if result == QDialog.DialogCode.Accepted:  # type: ignore[attr-defined]
        return dialog.get_answers()
    return None


class AskDialog(QDialog):
    """Modal dialog for rendering Ask questions."""

    def __init__(self, schema: list[dict[str, Any]], parent: QWidget | None = None) -> None:
        if not PYSIDE_AVAILABLE:
            raise RuntimeError("PySide6 is not available")

        super().__init__(parent)
        self._schema = schema
        self._widgets: MutableMapping[str, QWidget] = {}
        self._validation_labels: MutableMapping[str, QLabel] = {}

        self.setWindowTitle("Questions")
        self.setModal(True)
        self.setMinimumWidth(480)

        self._setup_ui()

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(24, 24, 24, 24)

        header = QLabel("<h2>Please provide the following information:</h2>")
        main_layout.addWidget(header)

        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)

        form_widget = QWidget()
        form_layout = QFormLayout(form_widget)
        form_layout.setSpacing(12)
        form_layout.setContentsMargins(0, 0, 0, 0)

        for question_def in self._schema:
            self._add_question_field(form_layout, question_def)

        scroll_area.setWidget(form_widget)
        main_layout.addWidget(scroll_area, stretch=1)

        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)
        button_layout.addStretch(1)

        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        ok_button = QPushButton("OK")
        ok_button.setDefault(True)
        ok_button.clicked.connect(self._on_ok_clicked)
        button_layout.addWidget(ok_button)

        main_layout.addLayout(button_layout)

    def _add_question_field(self, layout: QFormLayout, question_def: dict[str, Any]) -> None:
        name = question_def["name"]
        title = question_def["title"]
        description = question_def.get("description")
        default = question_def.get("default")
        required = bool(question_def.get("required", True))

        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setSpacing(4)
        container_layout.setContentsMargins(0, 0, 0, 0)

        widget = self._create_widget_for_question(question_def)
        self._widgets[name] = widget

        if default is not None:
            self._set_widget_value(widget, default, question_def)

        container_layout.addWidget(widget)

        validation_label = QLabel()
        validation_label.setStyleSheet("color: #d32f2f; font-size: 11px;")
        validation_label.setWordWrap(True)
        validation_label.hide()
        self._validation_labels[name] = validation_label
        container_layout.addWidget(validation_label)

        label_text = title + (" *" if required else "")
        label_widget = QLabel(label_text)

        if description:
            label_widget.setToolTip(description)
            widget.setToolTip(description)

        layout.addRow(label_widget, container)

    def _create_widget_for_question(self, question_def: Mapping[str, Any]) -> QWidget:
        widget_kind = determine_widget_kind(question_def)

        if widget_kind is WidgetKind.IMAGE:
            return self._create_file_picker_widget(question_def)

        if widget_kind is WidgetKind.ENUM:
            return self._create_enum_widget(question_def)

        if widget_kind in {WidgetKind.INTEGER, WidgetKind.FLOAT}:
            return self._create_numeric_widget(question_def, widget_kind)

        return self._create_text_widget(question_def)

    def _create_text_widget(self, question_def: Mapping[str, Any]) -> QLineEdit:
        widget = QLineEdit()
        description = question_def.get("description")
        if description:
            widget.setPlaceholderText(description)
        return widget

    def _create_numeric_widget(self, question_def: Mapping[str, Any], kind: WidgetKind) -> QWidget:
        ge = question_def.get("ge")
        le = question_def.get("le")

        if kind is WidgetKind.FLOAT:
            widget = QDoubleSpinBox()
            widget.setDecimals(4)
            minimum = float(ge) if ge is not None else -1e9
            maximum = float(le) if le is not None else 1e9
            widget.setRange(minimum, maximum)
        else:
            widget = QSpinBox()
            minimum = int(ge) if ge is not None else -2_147_483_648
            maximum = int(le) if le is not None else 2_147_483_647
            widget.setRange(minimum, maximum)

        if ge is not None:
            try:
                widget.setValue(int(ge) if kind is WidgetKind.INTEGER else float(ge))
            except (TypeError, ValueError):  # pragma: no cover - defensive
                pass
        return widget

    def _create_enum_widget(self, question_def: Mapping[str, Any]) -> QComboBox:
        widget = QComboBox()
        enum_values = list(question_def.get("enum", []))
        required = bool(question_def.get("required", True))

        if not required:
            widget.addItem("", None)

        for value in enum_values:
            value_str = str(value)
            display = value_str.split(".")[-1] if "." in value_str else value_str
            widget.addItem(display, value_str)

        return widget

    def _create_file_picker_widget(self, question_def: Mapping[str, Any]) -> QWidget:
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        line_edit = QLineEdit()
        line_edit.setPlaceholderText("Select an image file...")
        layout.addWidget(line_edit, stretch=1)

        browse_button = QPushButton("Browse...")

        def on_browse() -> None:
            formats = tuple(question_def.get("formats", ("png", "jpg", "jpeg", "gif", "bmp", "webp")))
            patterns = " ".join(f"*.{ext}" for ext in formats)
            filter_str = f"Image files ({patterns});;All files (*.*)"

            if QFileDialog is None:  # pragma: no cover - defensive
                return

            file_path, _ = QFileDialog.getOpenFileName(self, "Select Image", "", filter_str)
            if file_path:
                line_edit.setText(file_path)

        browse_button.clicked.connect(on_browse)
        layout.addWidget(browse_button)

        container.setProperty("lineEdit", line_edit)
        return container

    def _set_widget_value(self, widget: QWidget, value: Any, question_def: Mapping[str, Any]) -> None:
        widget_kind = determine_widget_kind(question_def)

        if isinstance(widget, QLineEdit):
            widget.setText(str(value))
        elif isinstance(widget, QSpinBox):
            try:
                widget.setValue(int(value))
            except (TypeError, ValueError):  # pragma: no cover - defensive
                widget.setValue(widget.minimum())
        elif isinstance(widget, QDoubleSpinBox):
            try:
                widget.setValue(float(value))
            except (TypeError, ValueError):  # pragma: no cover - defensive
                widget.setValue(widget.minimum())
        elif isinstance(widget, QComboBox):
            value_str = str(value)
            for index in range(widget.count()):
                if widget.itemData(index) == value_str:
                    widget.setCurrentIndex(index)
                    break
        elif widget_kind is WidgetKind.IMAGE:
            line_edit = widget.property("lineEdit")
            if line_edit:
                line_edit.setText(str(value))

    def _get_widget_value(self, widget: QWidget, question_def: Mapping[str, Any]) -> Any:
        widget_kind = determine_widget_kind(question_def)

        if isinstance(widget, QLineEdit):
            text = widget.text().strip()
            return text or None
        if isinstance(widget, QSpinBox):
            return widget.value()
        if isinstance(widget, QDoubleSpinBox):
            return widget.value()
        if isinstance(widget, QComboBox):
            data = widget.currentData()
            if data is not None:
                return data
            text = widget.currentText().strip()
            return text or None
        if widget_kind is WidgetKind.IMAGE:
            line_edit = widget.property("lineEdit")
            if line_edit:
                text = line_edit.text().strip()
                return text or None
        return None

    def _validate_answers(self) -> bool:
        all_valid = True

        for question_def in self._schema:
            name = question_def["name"]
            widget = self._widgets[name]
            validation_label = self._validation_labels[name]

            value = self._get_widget_value(widget, question_def)
            is_valid, error = validate_value(question_def, value)

            if not is_valid:
                validation_label.setText(error or "Invalid value")
                validation_label.show()
                all_valid = False
            else:
                validation_label.hide()

        return all_valid

    def _on_ok_clicked(self) -> None:
        if self._validate_answers():
            self.accept()

    def get_answers(self) -> dict[str, Any]:
        answers: dict[str, Any] = {}

        for question_def in self._schema:
            name = question_def["name"]
            widget = self._widgets[name]
            value = self._get_widget_value(widget, question_def)
            if value is not None:
                answers[name] = value

        return answers


def _is_float_like(value: Any) -> bool:
    try:
        return isinstance(value, float) and not float(value).is_integer()
    except (TypeError, ValueError):  # pragma: no cover - defensive
        return False


def _validate_numeric_bounds(question: Mapping[str, Any], value: float) -> tuple[bool, str | None]:
    ge = question.get("ge")
    le = question.get("le")

    if ge is not None and value < float(ge):
        return False, f"Value must be >= {ge}"
    if le is not None and value > float(le):
        return False, f"Value must be <= {le}"
    return True, None


__all__ = [
    "ask",
    "AskDialog",
    "WidgetKind",
    "determine_widget_kind",
    "validate_value",
]
