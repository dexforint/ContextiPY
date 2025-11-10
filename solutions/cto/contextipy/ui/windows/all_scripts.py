"""All scripts management window with grid display and configuration."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

try:  # pragma: no cover
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import (
        QCheckBox,
        QHBoxLayout,
        QHeaderView,
        QLabel,
        QMainWindow,
        QMessageBox,
        QPushButton,
        QTableWidget,
        QTableWidgetItem,
        QVBoxLayout,
        QWidget,
    )
except ImportError:  # pragma: no cover
    Qt = None  # type: ignore[assignment]
    QCheckBox = object  # type: ignore[assignment,misc]
    QHBoxLayout = object  # type: ignore[assignment,misc]
    QHeaderView = object  # type: ignore[assignment,misc]
    QLabel = object  # type: ignore[assignment,misc]
    QMainWindow = object  # type: ignore[assignment,misc]
    QMessageBox = object  # type: ignore[assignment,misc]
    QPushButton = object  # type: ignore[assignment,misc]
    QTableWidget = object  # type: ignore[assignment,misc]
    QTableWidgetItem = object  # type: ignore[assignment,misc]
    QVBoxLayout = object  # type: ignore[assignment,misc]
    QWidget = object  # type: ignore[assignment,misc]
    PYSIDE_AVAILABLE = False
else:
    PYSIDE_AVAILABLE = True

if TYPE_CHECKING:
    from contextipy.execution.context_entry import ContextEntryCoordinator
    from contextipy.scanner.registry import RegisteredScript, ScriptMetadataRegistry

from ..icons import APP_ICON_NAME, get_standard_icons, load_icon
from ..theme import get_theme
from ..widgets import Heading, PrimaryButton, SecondaryButton, SecondaryLabel


class ScriptModel:
    """Model holding script data."""

    def __init__(self) -> None:
        self.scripts: list[RegisteredScript] = []

    def update_scripts(self, scripts: list[RegisteredScript]) -> None:
        """Update the list of scripts."""
        self.scripts = scripts


class AllScriptsWindow(QMainWindow):
    """Window displaying all registered scripts with management capabilities."""

    def __init__(
        self,
        *,
        registry: ScriptMetadataRegistry | None = None,
        coordinator: ContextEntryCoordinator | None = None,
        get_scripts: Callable[[], list[RegisteredScript]] | None = None,
        rescan: Callable[[], None] | None = None,
        set_enabled: Callable[[str, bool], None] | None = None,
        set_startup: Callable[[str, bool], None] | None = None,
        run_script: Callable[[str], tuple[bool, str | None]] | None = None,
    ) -> None:
        """Initialize the all scripts window.

        Args:
            registry: Optional script metadata registry.
            coordinator: Optional context entry coordinator for running scripts.
            get_scripts: Optional callable to fetch current scripts.
            rescan: Optional callable to trigger registry rescan.
            set_enabled: Optional callable to set script enabled state.
            set_startup: Optional callable to set script startup state.
            run_script: Optional callable to run a script. Returns (success, error_message).
        """
        if not PYSIDE_AVAILABLE:
            raise RuntimeError("PySide6 is not available")

        super().__init__()

        self._registry = registry
        self._coordinator = coordinator
        self._model = ScriptModel()
        self._standard_icons = get_standard_icons()
        self._registered_scripts: set[str] = set()
        self._registered_services: set[str] = set()
        self._script_lookup: dict[str, "RegisteredScript"] = {}

        if get_scripts is not None:
            self._get_scripts = get_scripts
        elif self._registry is not None:
            self._get_scripts = self._fetch_scripts_from_registry
        else:
            self._get_scripts = lambda: []

        if rescan is not None:
            self._rescan = rescan
        elif self._registry is not None:
            self._rescan = self._rescan_via_registry
        else:
            self._rescan = lambda: None

        if set_enabled is not None:
            self._set_enabled = set_enabled
        elif self._registry is not None:
            self._set_enabled = self._set_enabled_via_registry
        else:
            self._set_enabled = lambda script_id, enabled: None

        if set_startup is not None:
            self._set_startup = set_startup
        elif self._registry is not None:
            self._set_startup = self._set_startup_via_registry
        else:
            self._set_startup = lambda script_id, startup: None

        if run_script is not None:
            self._run_script = run_script
        elif self._coordinator is not None:
            self._run_script = self._run_script_via_coordinator
        else:
            self._run_script = lambda script_id: (False, "Координатор не настроен")

        theme = get_theme()
        spacing = theme.spacing

        self.setWindowTitle("Все скрипты")
        self.setMinimumSize(1000, 600)

        icon = load_icon(APP_ICON_NAME)
        if not icon.isNull():
            self.setWindowIcon(icon)

        central_widget = QWidget(self)
        central_layout = QVBoxLayout(central_widget)
        central_layout.setSpacing(spacing.lg)
        central_layout.setContentsMargins(spacing.xl, spacing.xl, spacing.xl, spacing.xl)

        header = Heading("Все скрипты", level=1)
        header.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        central_layout.addWidget(header)

        subtitle = SecondaryLabel("Управление зарегистрированными скриптами и сервисами")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        central_layout.addWidget(subtitle)

        toolbar_layout = QHBoxLayout()
        toolbar_layout.addStretch(1)

        refresh_button = PrimaryButton("Обновить")
        refresh_button.setIcon(self._standard_icons.get("refresh"))
        refresh_button.clicked.connect(self._on_refresh)
        toolbar_layout.addWidget(refresh_button)

        central_layout.addLayout(toolbar_layout)

        self._table = QTableWidget(self)
        self._table.setColumnCount(8)
        self._table.setHorizontalHeaderLabels([
            "Иконка",
            "ID",
            "Тип",
            "Название",
            "Описание",
            "Меню",
            "Автозапуск",
            "Действия",
        ])

        header_view = self._table.horizontalHeader()
        header_view.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header_view.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header_view.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header_view.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header_view.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        header_view.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header_view.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        header_view.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)

        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.setAlternatingRowColors(True)

        central_layout.addWidget(self._table, stretch=1)

        self.setCentralWidget(central_widget)

        self._refresh_view()

    def _fetch_scripts_from_registry(self) -> list[RegisteredScript]:
        """Fetch scripts from the registry."""
        if self._registry is None:
            return []
        scripts_dict = self._registry.list_scripts()
        return list(scripts_dict.values())

    def _rescan_via_registry(self) -> None:
        """Trigger rescan via registry."""
        if self._registry is not None:
            self._registry.rescan()

    def _set_enabled_via_registry(self, script_id: str, enabled: bool) -> None:
        """Set script enabled state via registry."""
        if self._registry is not None:
            try:
                self._registry.set_enabled(script_id, enabled)
            except KeyError:
                pass

    def _set_startup_via_registry(self, script_id: str, startup: bool) -> None:
        """Set script startup state via registry."""
        if self._registry is not None:
            try:
                self._registry.set_startup(script_id, startup)
            except KeyError:
                pass

    def _run_script_via_coordinator(self, script_id: str) -> tuple[bool, str | None]:
        """Run script via coordinator."""
        if self._coordinator is None:
            return (False, "Координатор не настроен")
        try:
            result = self._coordinator.execute_script(script_id)
            return (result.success, result.message)
        except Exception as exc:
            return (False, str(exc))

    def _register_with_coordinator(self, script: RegisteredScript) -> tuple[bool, str | None]:
        """Register a script with the coordinator if not already registered.

        Args:
            script: Script to register.

        Returns:
            Tuple of (success, error_message).
        """
        if self._coordinator is None:
            return (True, None)

        script_id = script.script_id

        if script.scanned.kind == "service":
            if script_id in self._registered_services:
                return (True, None)
            try:
                self._coordinator.register_module_target(script.scanned.module, script.scanned.qualname.split(":")[-1])
                self._registered_services.add(script_id)
                return (True, None)
            except Exception as exc:
                return (False, f"Не удалось зарегистрировать сервис: {exc}")
        else:
            if script_id in self._registered_scripts:
                return (True, None)
            try:
                self._coordinator.register_module_target(script.scanned.module, script.scanned.qualname.split(":")[-1])
                self._registered_scripts.add(script_id)
                return (True, None)
            except Exception as exc:
                return (False, f"Не удалось зарегистрировать скрипт: {exc}")

    def _on_refresh(self) -> None:
        """Handle refresh button click."""
        try:
            self._rescan()
            self._refresh_view()
            self._show_info_dialog("Обновление", "Реестр скриптов успешно обновлен")
        except Exception as exc:
            self._show_error_dialog("Ошибка обновления", str(exc))

    def _refresh_view(self) -> None:
        """Refresh the view by fetching current scripts and updating the UI."""
        try:
            scripts = self._get_scripts()
            scripts_sorted = sorted(scripts, key=lambda s: (s.scanned.group, s.scanned.title))
            self._model.update_scripts(scripts_sorted)
            self._script_lookup = {s.script_id: s for s in scripts_sorted}
            current_ids = set(self._script_lookup.keys())
            self._registered_scripts.intersection_update(current_ids)
            self._registered_services.intersection_update(current_ids)
            self._update_ui()
        except Exception:
            pass

    def _update_ui(self) -> None:
        """Update the UI based on the current model."""
        self._table.setRowCount(0)

        if not self._model.scripts:
            return

        current_group: tuple[str, ...] | None = None

        for script in self._model.scripts:
            if script.scanned.group != current_group:
                current_group = script.scanned.group
                if current_group:
                    self._add_group_separator(current_group)

            self._add_script_row(script)

    def _add_group_separator(self, group: tuple[str, ...]) -> None:
        """Add a group separator row to the table.

        Args:
            group: Group hierarchy tuple.
        """
        row_position = self._table.rowCount()
        self._table.insertRow(row_position)

        group_text = " / ".join(group)
        group_item = QTableWidgetItem(f"📁 {group_text}")
        group_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
        font = group_item.font()
        font.setBold(True)
        group_item.setFont(font)

        empty_item = QTableWidgetItem()
        empty_item.setFlags(Qt.ItemFlag.NoItemFlags)
        self._table.setItem(row_position, 0, empty_item)
        self._table.setSpan(row_position, 1, 1, 7)
        self._table.setItem(row_position, 1, group_item)

    def _add_script_row(self, script: RegisteredScript) -> None:
        """Add a script row to the table.

        Args:
            script: Registered script to display.
        """
        row_position = self._table.rowCount()
        self._table.insertRow(row_position)

        icon_item = QTableWidgetItem()
        if script.scanned.icon:
            icon = load_icon(script.scanned.icon)
            if not icon.isNull():
                icon_item.setIcon(icon)
        icon_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
        self._table.setItem(row_position, 0, icon_item)

        id_item = QTableWidgetItem(script.script_id)
        id_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
        self._table.setItem(row_position, 1, id_item)

        type_map = {
            "oneshot_script": "Скрипт",
            "service": "Сервис",
            "service_script": "Сервис-скрипт",
        }
        type_text = type_map.get(script.scanned.kind, script.scanned.kind)
        type_item = QTableWidgetItem(type_text)
        type_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
        self._table.setItem(row_position, 2, type_item)

        title_item = QTableWidgetItem(script.scanned.title)
        title_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
        self._table.setItem(row_position, 3, title_item)

        description_item = QTableWidgetItem(script.scanned.description)
        description_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
        self._table.setItem(row_position, 4, description_item)

        menu_checkbox_widget = QWidget()
        menu_checkbox_layout = QHBoxLayout(menu_checkbox_widget)
        menu_checkbox_layout.setContentsMargins(0, 0, 0, 0)
        menu_checkbox_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        menu_checkbox = QCheckBox()
        menu_checkbox.setChecked(script.enabled)
        menu_checkbox.stateChanged.connect(
            lambda state, sid=script.script_id: self._on_enabled_changed(sid, state == Qt.CheckState.Checked.value)
        )
        menu_checkbox_layout.addWidget(menu_checkbox)
        self._table.setCellWidget(row_position, 5, menu_checkbox_widget)

        startup_checkbox_widget = QWidget()
        startup_checkbox_layout = QHBoxLayout(startup_checkbox_widget)
        startup_checkbox_layout.setContentsMargins(0, 0, 0, 0)
        startup_checkbox_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        startup_checkbox = QCheckBox()
        startup_checkbox.setChecked(script.startup)
        startup_checkbox.stateChanged.connect(
            lambda state, sid=script.script_id: self._on_startup_changed(sid, state == Qt.CheckState.Checked.value)
        )
        startup_checkbox_layout.addWidget(startup_checkbox)
        self._table.setCellWidget(row_position, 6, startup_checkbox_widget)

        actions_widget = QWidget()
        actions_layout = QHBoxLayout(actions_widget)
        actions_layout.setContentsMargins(4, 4, 4, 4)
        actions_layout.setSpacing(4)

        params_button = SecondaryButton("⚙")
        params_button.setToolTip("Параметры")
        params_button.clicked.connect(
            lambda _checked=False, sid=script.script_id: self._on_edit_parameters(sid)
        )
        actions_layout.addWidget(params_button)

        can_run, run_tooltip = self._get_run_capabilities(script)
        run_button = SecondaryButton("▶")
        run_button.setToolTip(run_tooltip)
        run_button.setEnabled(can_run)
        run_button.clicked.connect(
            lambda _checked=False, sid=script.script_id: self._on_run_script(sid)
        )
        actions_layout.addWidget(run_button)

        self._table.setCellWidget(row_position, 7, actions_widget)

    def _can_run_script(self, script: RegisteredScript) -> bool:
        """Check if a script can be run (no file inputs required).

        Args:
            script: Script to check.

        Returns:
            True if script can be run without file inputs.
        """
        can_run, _ = self._get_run_capabilities(script)
        return can_run

    def _get_parameters_metadata(self, script: RegisteredScript) -> list[Any] | None:
        """Get parameter metadata for a script by loading its module.

        Args:
            script: Script to get parameter metadata for.

        Returns:
            List of ParameterMetadata if available, None otherwise.
        """
        if not script.scanned.parameters:
            return None

        if self._coordinator is None:
            return None

        try:
            import importlib
            from contextipy.core.decorators import get_metadata

            module_name = script.scanned.module
            qualname = script.scanned.qualname.split(":")[-1]

            module = importlib.import_module(module_name)
            target = getattr(module, qualname, None)
            if target is None:
                return None

            metadata = get_metadata(target)
            if metadata is None:
                return None

            return list(metadata.parameters)
        except Exception:
            return None

    def _get_run_capabilities(self, script: RegisteredScript) -> tuple[bool, str]:
        """Get run button capabilities for a script.

        Args:
            script: Script to check.

        Returns:
            Tuple of (can_run, tooltip_text).
        """
        if script.scanned.kind == "service":
            return (False, "Сервисы не могут быть запущены напрямую")

        if script.scanned.accepts and len(script.scanned.accepts) > 0:
            return (False, "Требуются файлы на входе")

        return (True, "Запустить")

    def _on_enabled_changed(self, script_id: str, enabled: bool) -> None:
        """Handle menu visibility checkbox change.

        Args:
            script_id: Script ID.
            enabled: New enabled state.
        """
        try:
            self._set_enabled(script_id, enabled)
        except Exception as exc:
            self._show_error_dialog("Ошибка", f"Не удалось изменить видимость: {exc}")

    def _on_startup_changed(self, script_id: str, startup: bool) -> None:
        """Handle startup checkbox change.

        Args:
            script_id: Script ID.
            startup: New startup state.
        """
        try:
            self._set_startup(script_id, startup)
        except Exception as exc:
            self._show_error_dialog("Ошибка", f"Не удалось изменить автозапуск: {exc}")

    def _on_edit_parameters(self, script_id: str) -> None:
        """Handle edit parameters button click.

        Args:
            script_id: Script ID.
        """
        script = self._script_lookup.get(script_id)
        if script is None:
            self._show_error_dialog("Ошибка", f"Скрипт '{script_id}' не найден")
            return

        try:
            from .params_editor import ParamsEditorWindow

            parameters_metadata = self._get_parameters_metadata(script)

            def save_callback(sid: str, params: dict[str, Any]) -> None:
                if self._registry is not None:
                    self._registry.set_parameter_overrides(sid, params)
                self._refresh_view()

            editor = ParamsEditorWindow(
                script=script,
                parameters_metadata=parameters_metadata,
                save_callback=save_callback,
                parent=self,
            )
            editor.exec()
        except Exception as exc:
            self._show_error_dialog(
                "Ошибка редактора параметров",
                f"Не удалось открыть редактор параметров: {exc}",
            )

    def _on_run_script(self, script_id: str) -> None:
        """Handle run script button click.

        Args:
            script_id: Script ID to run.
        """
        script = self._script_lookup.get(script_id)
        if script is None:
            self._show_error_dialog("Ошибка запуска", f"Скрипт '{script_id}' не найден")
            return

        can_run, tooltip = self._get_run_capabilities(script)
        if not can_run:
            self._show_error_dialog("Запуск недоступен", tooltip)
            return

        try:
            if self._coordinator is not None:
                success, error_message = self._register_with_coordinator(script)
                if not success:
                    self._show_error_dialog(
                        "Ошибка подготовки",
                        error_message or f"Не удалось подготовить скрипт '{script_id}'",
                    )
                    return

                service_id = script.scanned.related_service_id
                if service_id:
                    related_service = self._script_lookup.get(service_id)
                    if related_service is None:
                        self._show_error_dialog(
                            "Ошибка подготовки",
                            f"Не найден связанный сервис '{service_id}'",
                        )
                        return

                    success, error_message = self._register_with_coordinator(related_service)
                    if not success:
                        self._show_error_dialog(
                            "Ошибка подготовки",
                            error_message or f"Не удалось подготовить сервис '{service_id}'",
                        )
                        return

            success, message = self._run_script(script_id)
            if success:
                self._show_info_dialog("Запуск скрипта", message or f"Скрипт '{script_id}' успешно выполнен")
            else:
                self._show_error_dialog("Ошибка запуска", message or f"Не удалось запустить скрипт '{script_id}'")
        except Exception as exc:
            self._show_error_dialog("Ошибка запуска", str(exc))

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


__all__ = [
    "AllScriptsWindow",
    "ScriptModel",
]
