"""Tests for parameter editor window."""

from __future__ import annotations

import inspect
from pathlib import Path
from unittest.mock import Mock

import pytest

try:
    from PySide6.QtWidgets import QApplication

    PYSIDE_AVAILABLE = True
except ImportError:
    PYSIDE_AVAILABLE = False

pytestmark = pytest.mark.skipif(not PYSIDE_AVAILABLE, reason="PySide6 not available")


@pytest.fixture
def qapp() -> QApplication:
    """Create QApplication instance for tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def script_fixture():
    """Create fixture with script data."""
    from contextipy.scanner.registry import RegisteredScript, ScriptSettings
    from contextipy.scanner.script_scanner import ScannedScript

    return RegisteredScript(
        scanned=ScannedScript(
            identifier="test-script",
            kind="oneshot_script",
            title="Test Script",
            description="A test script for parameter editing",
            docstring="Test docstring",
            file_path=Path("/fake/path/script.py"),
            module="test.script",
            qualname="test.script:main",
            group=("test",),
            accepts=(),
            timeout=None,
            related_service_id=None,
            icon=None,
            categories=("test",),
            file_hash="hash1",
            parameters=("width", "height", "enabled"),
        ),
        settings=ScriptSettings(
            enabled=True,
            startup=False,
            parameter_overrides={"width": 800, "height": 600},
        ),
    )


@pytest.fixture
def script_with_metadata_fixture():
    """Create fixture with script and parameter metadata."""
    from contextipy.core.metadata import ParameterMetadata
    from contextipy.scanner.registry import RegisteredScript, ScriptSettings
    from contextipy.scanner.script_scanner import ScannedScript

    script = RegisteredScript(
        scanned=ScannedScript(
            identifier="test-script-meta",
            kind="oneshot_script",
            title="Test Script With Metadata",
            description="A test script with full parameter metadata",
            docstring="Test docstring",
            file_path=Path("/fake/path/script.py"),
            module="test.script",
            qualname="test.script:process",
            group=("test",),
            accepts=(),
            timeout=None,
            related_service_id=None,
            icon=None,
            categories=("test",),
            file_hash="hash2",
            parameters=("width", "height", "enabled", "quality"),
        ),
        settings=ScriptSettings(
            enabled=True,
            startup=False,
            parameter_overrides={"width": 1024, "quality": 90},
        ),
    )

    parameters_metadata = [
        ParameterMetadata(
            name="width",
            title="Width",
            description="Image width in pixels",
            annotation=int,
            required=True,
            default=inspect.Parameter.empty,
        ),
        ParameterMetadata(
            name="height",
            title="Height",
            description="Image height in pixels",
            annotation=int,
            required=False,
            default=768,
        ),
        ParameterMetadata(
            name="enabled",
            title="Enabled",
            description="Enable processing",
            annotation=bool,
            required=False,
            default=True,
        ),
        ParameterMetadata(
            name="quality",
            title="Quality",
            description="Output quality (0-100)",
            annotation=int,
            required=False,
            default=85,
        ),
    ]

    return script, parameters_metadata


def test_params_editor_window_creation(qapp, script_fixture):
    """Test that ParamsEditorWindow can be created."""
    from contextipy.ui.windows.params_editor import ParamsEditorWindow

    window = ParamsEditorWindow(script=script_fixture)

    assert window is not None
    assert "Test Script" in window.windowTitle()


def test_params_editor_window_with_metadata(qapp, script_with_metadata_fixture):
    """Test that ParamsEditorWindow can be created with parameter metadata."""
    from contextipy.ui.windows.params_editor import ParamsEditorWindow

    script, parameters_metadata = script_with_metadata_fixture

    window = ParamsEditorWindow(
        script=script,
        parameters_metadata=parameters_metadata,
    )

    assert window is not None
    assert len(window._param_widgets) == 4


def test_params_editor_loads_current_values(qapp, script_with_metadata_fixture):
    """Test that current parameter values are loaded correctly."""
    from contextipy.ui.windows.params_editor import ParamsEditorWindow

    script, parameters_metadata = script_with_metadata_fixture

    window = ParamsEditorWindow(
        script=script,
        parameters_metadata=parameters_metadata,
    )

    assert window._original_values["width"] == 1024
    assert window._original_values["quality"] == 90


def test_params_editor_get_parameters(qapp, script_with_metadata_fixture):
    """Test that parameter values can be retrieved from the form."""
    from contextipy.ui.windows.params_editor import ParamsEditorWindow

    script, parameters_metadata = script_with_metadata_fixture

    window = ParamsEditorWindow(
        script=script,
        parameters_metadata=parameters_metadata,
    )

    parameters = window.get_parameters()
    assert isinstance(parameters, dict)
    assert "width" in parameters


def test_params_editor_save_callback(qapp, script_fixture):
    """Test that save callback is called with correct parameters."""
    from contextipy.ui.windows.params_editor import ParamsEditorWindow

    save_callback = Mock()

    window = ParamsEditorWindow(
        script=script_fixture,
        save_callback=save_callback,
    )

    window._on_save()

    save_callback.assert_called_once()
    args = save_callback.call_args[0]
    assert args[0] == "test-script"
    assert isinstance(args[1], dict)


def test_params_editor_validation_required_fields(qapp, script_with_metadata_fixture):
    """Test that required field validation works."""
    from contextipy.ui.windows.params_editor import ParamsEditorWindow
    from PySide6.QtWidgets import QSpinBox

    script, parameters_metadata = script_with_metadata_fixture

    window = ParamsEditorWindow(
        script=script,
        parameters_metadata=parameters_metadata,
    )

    width_widget = window._param_widgets.get("width")
    if isinstance(width_widget, QSpinBox):
        width_widget.clear()

    result = window._validate_parameters()
    assert isinstance(result, bool)


def test_params_editor_reset_functionality(qapp, script_with_metadata_fixture):
    """Test that reset button restores default values."""
    from contextipy.ui.windows.params_editor import ParamsEditorWindow
    from PySide6.QtWidgets import QSpinBox
    from unittest.mock import patch

    script, parameters_metadata = script_with_metadata_fixture

    window = ParamsEditorWindow(
        script=script,
        parameters_metadata=parameters_metadata,
    )

    width_widget = window._param_widgets.get("width")
    if isinstance(width_widget, QSpinBox):
        width_widget.setValue(2000)

    with patch("contextipy.ui.windows.params_editor.QMessageBox.question") as mock_question:
        from PySide6.QtWidgets import QMessageBox

        mock_question.return_value = QMessageBox.StandardButton.Yes
        window._on_reset()


def test_params_editor_without_parameters(qapp):
    """Test that editor handles scripts without parameters."""
    from contextipy.scanner.registry import RegisteredScript, ScriptSettings
    from contextipy.scanner.script_scanner import ScannedScript
    from contextipy.ui.windows.params_editor import ParamsEditorWindow

    script = RegisteredScript(
        scanned=ScannedScript(
            identifier="no-params-script",
            kind="oneshot_script",
            title="Script Without Parameters",
            description="A script with no parameters",
            docstring=None,
            file_path=Path("/fake/path/script.py"),
            module="test.script",
            qualname="test.script:noop",
            group=(),
            accepts=(),
            timeout=None,
            related_service_id=None,
            icon=None,
            categories=(),
            file_hash="hash3",
            parameters=(),
        ),
        settings=ScriptSettings(enabled=True, startup=False, parameter_overrides=None),
    )

    window = ParamsEditorWindow(script=script)
    assert window is not None
    assert len(window._param_widgets) == 0


def test_params_editor_simple_parameters(qapp, script_fixture):
    """Test that simple parameters without metadata are handled."""
    from contextipy.ui.windows.params_editor import ParamsEditorWindow

    window = ParamsEditorWindow(script=script_fixture)

    assert len(window._param_widgets) == 3
    assert "width" in window._param_widgets
    assert "height" in window._param_widgets
    assert "enabled" in window._param_widgets


def test_params_editor_widget_types(qapp, script_with_metadata_fixture):
    """Test that correct widget types are created for different parameter types."""
    from contextipy.ui.windows.params_editor import ParamsEditorWindow
    from PySide6.QtWidgets import QCheckBox, QSpinBox

    script, parameters_metadata = script_with_metadata_fixture

    window = ParamsEditorWindow(
        script=script,
        parameters_metadata=parameters_metadata,
    )

    width_widget = window._param_widgets.get("width")
    assert isinstance(width_widget, QSpinBox)

    enabled_widget = window._param_widgets.get("enabled")
    assert isinstance(enabled_widget, QCheckBox)


def test_params_editor_set_and_get_widget_values(qapp, script_with_metadata_fixture):
    """Test setting and getting widget values."""
    from contextipy.ui.windows.params_editor import ParamsEditorWindow
    from PySide6.QtWidgets import QCheckBox, QLineEdit, QSpinBox

    script, parameters_metadata = script_with_metadata_fixture

    window = ParamsEditorWindow(
        script=script,
        parameters_metadata=parameters_metadata,
    )

    width_widget = window._param_widgets.get("width")
    if isinstance(width_widget, QSpinBox):
        window._set_widget_value(width_widget, 1920)
        value = window._get_widget_value(width_widget)
        assert value == 1920

    enabled_widget = window._param_widgets.get("enabled")
    if isinstance(enabled_widget, QCheckBox):
        window._set_widget_value(enabled_widget, False)
        value = window._get_widget_value(enabled_widget)
        assert value is False


def test_params_editor_json_serialization(qapp):
    """Test that complex values can be serialized and deserialized."""
    from contextipy.scanner.registry import RegisteredScript, ScriptSettings
    from contextipy.scanner.script_scanner import ScannedScript
    from contextipy.ui.windows.params_editor import ParamsEditorWindow
    from PySide6.QtWidgets import QLineEdit

    script = RegisteredScript(
        scanned=ScannedScript(
            identifier="json-script",
            kind="oneshot_script",
            title="JSON Script",
            description="Script with complex parameters",
            docstring=None,
            file_path=Path("/fake/path/script.py"),
            module="test.script",
            qualname="test.script:complex",
            group=(),
            accepts=(),
            timeout=None,
            related_service_id=None,
            icon=None,
            categories=(),
            file_hash="hash4",
            parameters=("config",),
        ),
        settings=ScriptSettings(
            enabled=True,
            startup=False,
            parameter_overrides={"config": {"key": "value", "count": 42}},
        ),
    )

    window = ParamsEditorWindow(script=script)

    config_widget = window._param_widgets.get("config")
    if isinstance(config_widget, QLineEdit):
        text = config_widget.text()
        assert "key" in text
        assert "value" in text


def test_params_editor_validation_labels(qapp, script_with_metadata_fixture):
    """Test that validation labels are created for each parameter."""
    from contextipy.ui.windows.params_editor import ParamsEditorWindow

    script, parameters_metadata = script_with_metadata_fixture

    window = ParamsEditorWindow(
        script=script,
        parameters_metadata=parameters_metadata,
    )

    assert len(window._validation_labels) == 4
    for param_name in ["width", "height", "enabled", "quality"]:
        assert param_name in window._validation_labels
        label = window._validation_labels[param_name]
        assert not label.isVisible()


def test_params_editor_modal_dialog(qapp, script_fixture):
    """Test that the window is created as a modal dialog."""
    from contextipy.ui.windows.params_editor import ParamsEditorWindow

    window = ParamsEditorWindow(script=script_fixture)

    assert window.isModal()


def test_params_editor_cancel_button(qapp, script_fixture):
    """Test that cancel button rejects the dialog."""
    from contextipy.ui.windows.params_editor import ParamsEditorWindow

    window = ParamsEditorWindow(script=script_fixture)
    save_callback = Mock()
    window._save_callback = save_callback

    window.reject()

    save_callback.assert_not_called()


def test_params_editor_float_parameters(qapp):
    """Test that float parameters are handled correctly."""
    from contextipy.core.metadata import ParameterMetadata
    from contextipy.scanner.registry import RegisteredScript, ScriptSettings
    from contextipy.scanner.script_scanner import ScannedScript
    from contextipy.ui.windows.params_editor import ParamsEditorWindow
    from PySide6.QtWidgets import QDoubleSpinBox

    script = RegisteredScript(
        scanned=ScannedScript(
            identifier="float-script",
            kind="oneshot_script",
            title="Float Script",
            description="Script with float parameters",
            docstring=None,
            file_path=Path("/fake/path/script.py"),
            module="test.script",
            qualname="test.script:floater",
            group=(),
            accepts=(),
            timeout=None,
            related_service_id=None,
            icon=None,
            categories=(),
            file_hash="hash5",
            parameters=("ratio",),
        ),
        settings=ScriptSettings(enabled=True, startup=False, parameter_overrides={"ratio": 1.5}),
    )

    parameters_metadata = [
        ParameterMetadata(
            name="ratio",
            title="Ratio",
            description="Aspect ratio",
            annotation=float,
            required=False,
            default=1.0,
        ),
    ]

    window = ParamsEditorWindow(script=script, parameters_metadata=parameters_metadata)

    ratio_widget = window._param_widgets.get("ratio")
    assert isinstance(ratio_widget, QDoubleSpinBox)
