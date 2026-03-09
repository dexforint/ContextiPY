from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from functools import partial
from typing import cast

from PySide6.QtCore import Slot
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from pcontext.agent.service_manager import ServiceControlResult
from pcontext.config import PContextPaths
from pcontext.gui.backend import GuiBackend, ScriptListItem
from pcontext.gui.tasks import BackgroundTask
from pcontext.storage.models import RegistrationModuleRecord


def _format_log_timestamp(raw_value: str) -> tuple[str, str]:
    try:
        dt_utc = datetime.fromisoformat(raw_value)
        dt_local = dt_utc.astimezone()

        display_text = dt_local.strftime("%d.%m.%Y %H:%M:%S")
        tooltip_text = (
            f"Локальное время: {dt_local.strftime('%d.%m.%Y %H:%M:%S %Z')}\n"
            f"UTC: {dt_utc.strftime('%Y-%m-%d %H:%M:%S %z')}"
        )
        return display_text, tooltip_text
    except ValueError:
        return raw_value, raw_value


def _shorten_text(value: str | None, max_length: int = 140) -> str:
    if not value:
        return "—"
    if len(value) <= max_length:
        return value
    return value[: max_length - 3] + "..."


class ServicesTab(QWidget):
    def __init__(
        self,
        backend: GuiBackend,
        refresh_all: Callable[[], None],
        show_status: Callable[[str, int], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._backend = backend
        self._refresh_all = refresh_all
        self._show_status = show_status
        self._active_tasks: list[BackgroundTask] = []

        self._table = QTableWidget(self)
        self._table.setColumnCount(6)
        self._table.setHorizontalHeaderLabels(
            ["Название", "ID", "Статус", "Автостарт", "Методов", "Действие"]
        )
        self._table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self._table.verticalHeader().setVisible(False)

        refresh_button = QPushButton("Обновить", self)
        refresh_button.clicked.connect(self.refresh_data)

        layout = QVBoxLayout(self)
        layout.addWidget(refresh_button)
        layout.addWidget(self._table)

    def refresh_data(self) -> None:
        services = self._backend.list_services()
        self._table.setRowCount(len(services))

        for row_index, service in enumerate(services):
            self._table.setItem(row_index, 0, QTableWidgetItem(service.title))
            self._table.setItem(row_index, 1, QTableWidgetItem(service.service_id))
            self._table.setItem(
                row_index,
                2,
                QTableWidgetItem("Запущен" if service.running else "Остановлен"),
            )
            self._table.setItem(
                row_index,
                3,
                QTableWidgetItem("Да" if service.on_startup else "Нет"),
            )
            self._table.setItem(
                row_index, 4, QTableWidgetItem(str(service.script_count))
            )

            action_button = QPushButton(
                "Остановить" if service.running else "Запустить", self
            )
            action_button.clicked.connect(
                partial(self._toggle_service, service.service_id, service.running)
            )
            self._table.setCellWidget(row_index, 5, action_button)

    def _toggle_service(self, service_id: str, currently_running: bool) -> None:
        self._show_status("Выполняется операция с сервисом...", 0)

        if currently_running:
            self._run_task(
                lambda: self._backend.stop_service(service_id),
                self._handle_service_result,
                "Сервисы",
            )
        else:
            self._run_task(
                lambda: self._backend.start_service(service_id),
                self._handle_service_result,
                "Сервисы",
            )

    def _run_task(
        self,
        function: Callable[[], object],
        success_handler: Callable[[object], None],
        error_title: str,
    ) -> None:
        task = BackgroundTask(function, self)
        task.success_handler = success_handler
        task.error_title = error_title
        task.finished.connect(self._on_task_finished)
        self._active_tasks.append(task)
        task.start()

    @Slot(object, object)
    def _on_task_finished(self, result_obj: object, error_obj: object) -> None:
        sender = self.sender()
        if isinstance(sender, BackgroundTask):
            try:
                self._active_tasks.remove(sender)
            except ValueError:
                pass

            if error_obj is not None:
                QMessageBox.warning(self, sender.error_title, str(error_obj))
                self._refresh_all()
                return

            if sender.success_handler is not None:
                sender.success_handler(result_obj)

    def _handle_service_result(self, result_obj: object) -> None:
        result = cast(ServiceControlResult, result_obj)

        if result.accepted:
            self._show_status(result.message, 7000)
        else:
            QMessageBox.warning(self, "Сервисы", result.message)

        self._refresh_all()


class ScriptsTab(QWidget):
    def __init__(
        self,
        backend: GuiBackend,
        refresh_all: Callable[[], None],
        show_status: Callable[[str, int], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._backend = backend
        self._refresh_all = refresh_all
        self._show_status = show_status
        self._active_tasks: list[BackgroundTask] = []

        self._table = QTableWidget(self)
        self._table.setColumnCount(6)
        self._table.setHorizontalHeaderLabels(
            ["Название", "Тип", "Описание", "Сервис", "Параметры", "Запуск"]
        )
        self._table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self._table.verticalHeader().setVisible(False)

        refresh_button = QPushButton("Обновить", self)
        refresh_button.clicked.connect(self.refresh_data)

        layout = QVBoxLayout(self)
        layout.addWidget(refresh_button)
        layout.addWidget(self._table)

    def refresh_data(self) -> None:
        items = self._backend.list_script_items()
        self._table.setRowCount(len(items))

        for row_index, item in enumerate(items):
            self._fill_row(row_index, item)

    def _fill_row(self, row_index: int, item: ScriptListItem) -> None:
        type_label = "Oneshot" if item.kind == "oneshot_script" else "Service method"
        service_label = item.service_title or "—"
        description = item.description or "—"

        self._table.setItem(row_index, 0, QTableWidgetItem(item.title))
        self._table.setItem(row_index, 1, QTableWidgetItem(type_label))
        self._table.setItem(row_index, 2, QTableWidgetItem(description))
        self._table.setItem(row_index, 3, QTableWidgetItem(service_label))

        params_button = QPushButton("Настроить", self)
        params_button.setEnabled(item.parameter_count > 0)
        params_button.clicked.connect(partial(self._open_params_dialog, item.owner_id))
        self._table.setCellWidget(row_index, 4, params_button)

        run_button = QPushButton("Запустить", self)
        run_button.setEnabled(item.direct_run_enabled)
        run_button.clicked.connect(partial(self._invoke_direct, item.owner_id))
        self._table.setCellWidget(row_index, 5, run_button)

    def _open_params_dialog(self, owner_id: str) -> None:
        from pcontext.gui.param_dialog import ParameterDialog

        details = self._backend.get_parameter_owner(owner_id)
        if details is None:
            QMessageBox.critical(
                self,
                "Параметры",
                f"Не удалось найти параметры для '{owner_id}'.",
            )
            return

        dialog = ParameterDialog(details, self)
        if dialog.exec():
            self._backend.save_parameter_values(owner_id, dialog.get_values())
            self._show_status("Значения параметров сохранены.", 5000)
            self._refresh_all()

    def _invoke_direct(self, owner_id: str) -> None:
        self._show_status("Сценарий выполняется...", 0)
        self._run_task(
            lambda: self._backend.invoke_direct(owner_id),
            self._handle_direct_invocation_result,
            "Запуск",
        )

    def _run_task(
        self,
        function: Callable[[], object],
        success_handler: Callable[[object], None],
        error_title: str,
    ) -> None:
        task = BackgroundTask(function, self)
        task.success_handler = success_handler
        task.error_title = error_title
        task.finished.connect(self._on_task_finished)
        self._active_tasks.append(task)
        task.start()

    @Slot(object, object)
    def _on_task_finished(self, result_obj: object, error_obj: object) -> None:
        sender = self.sender()
        if isinstance(sender, BackgroundTask):
            try:
                self._active_tasks.remove(sender)
            except ValueError:
                pass

            if error_obj is not None:
                QMessageBox.warning(self, sender.error_title, str(error_obj))
                self._refresh_all()
                return

            if sender.success_handler is not None:
                sender.success_handler(result_obj)

    def _handle_direct_invocation_result(self, result_obj: object) -> None:
        accepted, message = cast(tuple[bool, str], result_obj)

        if accepted:
            self._show_status(message, 8000)
        else:
            QMessageBox.warning(self, "Запуск", message)

        self._refresh_all()


class SettingsTab(QWidget):
    def __init__(
        self,
        backend: GuiBackend,
        paths: PContextPaths,
        refresh_all: Callable[[], None],
        show_status: Callable[[str, int], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._backend = backend
        self._paths = paths
        self._refresh_all = refresh_all
        self._show_status = show_status
        self._active_tasks: list[BackgroundTask] = []

        self._autostart_checkbox = QCheckBox(
            "Запускать программу при старте системы", self
        )
        self._disable_notifications_checkbox = QCheckBox(
            "Отключить уведомления",
            self,
        )

        self._info_label = QLabel(self)
        self._info_label.setWordWrap(True)

        self._windows_shell_label = QLabel(self)
        self._windows_shell_label.setWordWrap(True)

        self._launcher_log_view = QPlainTextEdit(self)
        self._launcher_log_view.setReadOnly(True)
        self._launcher_log_view.setMinimumHeight(180)

        self._registration_summary_label = QLabel(self)
        self._registration_summary_label.setWordWrap(True)

        self._failed_summary_label = QLabel(self)
        self._failed_summary_label.setWordWrap(True)

        self._registration_table = QTableWidget(self)
        self._registration_table.setColumnCount(7)
        self._registration_table.setHorizontalHeaderLabels(
            [
                "Файл",
                "Статус",
                "Зависимости",
                "Ошибка",
                "Обновлено",
                "Открыть",
                "Детали",
            ]
        )
        self._registration_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self._registration_table.verticalHeader().setVisible(False)

        save_button = QPushButton("Сохранить настройки", self)
        save_button.clicked.connect(self._save_settings)

        reload_button = QPushButton("Регистрация и обновление", self)
        reload_button.clicked.connect(self._reload_registry)

        open_scripts_button = QPushButton("Открыть папку со скриптами", self)
        open_scripts_button.clicked.connect(self._open_scripts_folder)

        open_runtime_button = QPushButton("Открыть runtime-папку", self)
        open_runtime_button.clicked.connect(self._open_runtime_folder)

        open_launcher_log_button = QPushButton("Открыть launcher.log", self)
        open_launcher_log_button.clicked.connect(self._open_launcher_log)

        refresh_diagnostics_button = QPushButton("Обновить диагностику", self)
        refresh_diagnostics_button.clicked.connect(self.refresh_data)

        buttons_row = QHBoxLayout()
        buttons_row.addWidget(save_button)
        buttons_row.addWidget(reload_button)
        buttons_row.addWidget(open_scripts_button)
        buttons_row.addWidget(open_runtime_button)
        buttons_row.addWidget(open_launcher_log_button)
        buttons_row.addWidget(refresh_diagnostics_button)
        buttons_row.addStretch(1)

        layout = QVBoxLayout(self)
        layout.addWidget(self._autostart_checkbox)
        layout.addWidget(self._disable_notifications_checkbox)
        layout.addWidget(self._info_label)
        layout.addLayout(buttons_row)
        layout.addWidget(self._windows_shell_label)
        layout.addWidget(self._launcher_log_view)
        layout.addWidget(self._registration_summary_label)
        layout.addWidget(self._failed_summary_label)
        layout.addWidget(self._registration_table)
        layout.addStretch(1)

        self.refresh_data()

    def refresh_data(self) -> None:
        self._autostart_checkbox.setChecked(
            bool(self._backend.get_setting(GuiBackend.SETTINGS_AUTOSTART, False))
        )
        self._disable_notifications_checkbox.setChecked(
            bool(
                self._backend.get_setting(
                    GuiBackend.SETTINGS_DISABLE_NOTIFICATIONS, False
                )
            )
        )

        venv_status = self._backend.get_shared_venv_status()
        self._info_label.setText(
            f"Папка скриптов: <code>{self._paths.scripts}</code><br>"
            f"Папка иконок: <code>{self._paths.icons}</code><br>"
            f"Общее venv: <code>{venv_status.venv_dir}</code><br>"
            f"Python в venv: <code>{venv_status.python_executable}</code><br>"
            f"site-packages: <code>{venv_status.site_packages_dir}</code><br>"
            f"venv существует: <b>{'Да' if venv_status.exists else 'Нет'}</b><br>"
            f"SQLite: <code>{self._paths.state_db}</code>"
        )

        shell_diag = self._backend.get_windows_shell_diagnostics()
        self._windows_shell_label.setText(
            f"Windows shell runtime: <code>{shell_diag.runtime_dir}</code><br>"
            f"dev-config: <code>{shell_diag.config_path}</code> "
            f"({'есть' if shell_diag.config_exists else 'нет'})<br>"
            f"GUI executable: <code>{shell_diag.gui_executable or '—'}</code><br>"
            f"Launcher exe: <code>{shell_diag.launcher_exe or '—'}</code><br>"
            f"Автозапуск GUI при отсутствии агента: "
            f"<b>{'Да' if shell_diag.auto_start_gui_if_missing else 'Нет' if shell_diag.auto_start_gui_if_missing is not None else '—'}</b><br>"
            f"endpoint: <code>{shell_diag.endpoint_path}</code> "
            f"({'есть' if shell_diag.endpoint_exists else 'нет'})<br>"
            f"Агент доступен: <b>{'Да' if shell_diag.agent_available else 'Нет'}</b><br>"
            f"launcher.log: <code>{shell_diag.launcher_log_path}</code> "
            f"({'есть' if shell_diag.launcher_log_exists else 'нет'})<br>"
            f"Ошибка config: <b>{shell_diag.config_error or '—'}</b>"
        )

        self._launcher_log_view.setPlainText(
            shell_diag.launcher_log_tail
            if shell_diag.launcher_log_tail
            else "launcher.log пуст."
        )

        modules = self._backend.list_registration_modules()
        failed_modules = self._backend.list_failed_registration_modules()
        registered_count = sum(1 for item in modules if item.status == "registered")
        error_count = sum(1 for item in modules if item.status == "error")

        self._registration_summary_label.setText(
            f"Снимки регистрации: {len(modules)} | Успешно: {registered_count} | Ошибки: {error_count}"
        )
        self._failed_summary_label.setText(f"Проблемных файлов: {len(failed_modules)}")

        self._registration_table.setRowCount(len(modules))
        for row_index, item in enumerate(modules):
            self._fill_registration_row(row_index, item)

    def _fill_registration_row(
        self, row_index: int, item: RegistrationModuleRecord
    ) -> None:
        file_item = QTableWidgetItem(item.relative_path)
        file_item.setToolTip(item.source_file)
        self._registration_table.setItem(row_index, 0, file_item)

        status_text = "OK" if item.status == "registered" else "Ошибка"
        status_item = QTableWidgetItem(status_text)
        self._registration_table.setItem(row_index, 1, status_item)

        dependencies_text = ", ".join(item.dependencies) if item.dependencies else "—"
        dependencies_item = QTableWidgetItem(dependencies_text)
        dependencies_item.setToolTip(
            "\n".join(item.dependencies) if item.dependencies else "Нет зависимостей"
        )
        self._registration_table.setItem(row_index, 2, dependencies_item)

        error_text = _shorten_text(item.error_message)
        error_item = QTableWidgetItem(error_text)
        error_item.setToolTip(item.error_message or "—")
        self._registration_table.setItem(row_index, 3, error_item)

        display_time, tooltip_time = _format_log_timestamp(item.updated_at_utc)
        time_item = QTableWidgetItem(display_time)
        time_item.setToolTip(tooltip_time)
        self._registration_table.setItem(row_index, 4, time_item)

        open_button = QPushButton("Открыть", self)
        open_button.clicked.connect(
            partial(self._open_registration_source, item.source_file)
        )
        self._registration_table.setCellWidget(row_index, 5, open_button)

        details_button = QPushButton("Ошибка", self)
        details_button.setEnabled(bool(item.error_message))
        details_button.clicked.connect(partial(self._show_registration_error, item))
        self._registration_table.setCellWidget(row_index, 6, details_button)

    def _show_registration_error(self, item: RegistrationModuleRecord) -> None:
        message_box = QMessageBox(self)
        message_box.setWindowTitle("Ошибка регистрации")
        message_box.setIcon(QMessageBox.Icon.Warning)
        message_box.setText(f"Файл: {item.relative_path}")
        message_box.setInformativeText(_shorten_text(item.error_message, 300))
        message_box.setDetailedText(item.error_message or "Нет текста ошибки.")
        message_box.exec()

    def _open_registration_source(self, source_file: str) -> None:
        try:
            result_message = self._backend.open_registration_module_source(source_file)
        except Exception as error:  # noqa: BLE001
            QMessageBox.warning(self, "Файл скрипта", str(error))
            return

        self._show_status(result_message, 5000)

    def _save_settings(self) -> None:
        self._backend.set_setting(
            GuiBackend.SETTINGS_AUTOSTART,
            self._autostart_checkbox.isChecked(),
        )
        self._backend.set_setting(
            GuiBackend.SETTINGS_DISABLE_NOTIFICATIONS,
            self._disable_notifications_checkbox.isChecked(),
        )
        self._show_status("Настройки сохранены.", 5000)

    def _open_scripts_folder(self) -> None:
        try:
            result_message = self._backend.open_scripts_folder()
        except Exception as error:  # noqa: BLE001
            QMessageBox.warning(self, "Скрипты", str(error))
            return

        self._show_status(result_message, 5000)

    def _open_runtime_folder(self) -> None:
        try:
            result_message = self._backend.open_runtime_folder()
        except Exception as error:  # noqa: BLE001
            QMessageBox.warning(self, "Runtime", str(error))
            return

        self._show_status(result_message, 5000)

    def _open_launcher_log(self) -> None:
        try:
            result_message = self._backend.open_launcher_log()
        except Exception as error:  # noqa: BLE001
            QMessageBox.warning(self, "Launcher log", str(error))
            return

        self._show_status(result_message, 5000)

    def _reload_registry(self) -> None:
        self._show_status("Идёт регистрация скриптов и зависимостей...", 0)
        self._run_task(
            self._backend.register_and_reload,
            self._handle_reload_result,
            "Регистрация",
        )

    def _run_task(
        self,
        function: Callable[[], object],
        success_handler: Callable[[object], None],
        error_title: str,
    ) -> None:
        task = BackgroundTask(function, self)
        task.success_handler = success_handler
        task.error_title = error_title
        task.finished.connect(self._on_task_finished)
        self._active_tasks.append(task)
        task.start()

    @Slot(object, object)
    def _on_task_finished(self, result_obj: object, error_obj: object) -> None:
        sender = self.sender()
        if isinstance(sender, BackgroundTask):
            try:
                self._active_tasks.remove(sender)
            except ValueError:
                pass

            if error_obj is not None:
                QMessageBox.warning(self, sender.error_title, str(error_obj))
                self._refresh_all()
                return

            if sender.success_handler is not None:
                sender.success_handler(result_obj)

    def _handle_reload_result(self, result_obj: object) -> None:
        (
            processed_files,
            changed_files,
            unchanged_files,
            removed_files,
            failed_files,
            installed_dependency_groups,
            venv_created,
        ) = cast(tuple[int, int, int, int, int, int, bool], result_obj)

        QMessageBox.information(
            self,
            "Регистрация",
            (
                f"Регистрация завершена.\n\n"
                f"Обработано файлов: {processed_files}\n"
                f"Изменено: {changed_files}\n"
                f"Без изменений: {unchanged_files}\n"
                f"Удалено: {removed_files}\n"
                f"Ошибок: {failed_files}\n"
                f"Групп зависимостей установлено: {installed_dependency_groups}\n"
                f"Новое venv создано: {'Да' if venv_created else 'Нет'}"
            ),
        )
        self._refresh_all()


class LogsTab(QWidget):
    def __init__(
        self,
        backend: GuiBackend,
        refresh_all: Callable[[], None],
        show_status: Callable[[str, int], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._backend = backend
        self._refresh_all = refresh_all
        self._show_status = show_status
        self._active_tasks: list[BackgroundTask] = []

        self._table = QTableWidget(self)
        self._table.setColumnCount(6)
        self._table.setHorizontalHeaderLabels(
            ["Время", "Имя", "Длительность", "Статус", "Сообщение", "Повтор"]
        )
        self._table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self._table.verticalHeader().setVisible(False)

        refresh_button = QPushButton("Обновить", self)
        refresh_button.clicked.connect(self.refresh_data)

        layout = QVBoxLayout(self)
        layout.addWidget(refresh_button)
        layout.addWidget(self._table)

    def refresh_data(self) -> None:
        logs = self._backend.list_logs(limit=100)
        self._table.setRowCount(len(logs))

        for row_index, log_record in enumerate(logs):
            display_time, tooltip_time = _format_log_timestamp(
                log_record.created_at_utc
            )
            time_item = QTableWidgetItem(display_time)
            time_item.setToolTip(tooltip_time)
            self._table.setItem(row_index, 0, time_item)

            self._table.setItem(row_index, 1, QTableWidgetItem(log_record.title))
            self._table.setItem(
                row_index,
                2,
                QTableWidgetItem(
                    "—"
                    if log_record.duration_ms is None
                    else f"{log_record.duration_ms} мс"
                ),
            )
            self._table.setItem(
                row_index,
                3,
                QTableWidgetItem("Успех" if log_record.success else "Ошибка"),
            )

            message_item = QTableWidgetItem(log_record.message)
            message_item.setToolTip(log_record.message)
            self._table.setItem(row_index, 4, message_item)

            replay_button = QPushButton("Повторить", self)
            replay_button.setEnabled(log_record.action_json is not None)
            replay_button.clicked.connect(
                partial(self._replay_action, log_record.log_id)
            )
            self._table.setCellWidget(row_index, 5, replay_button)

    def _replay_action(self, log_id: int) -> None:
        self._show_status("Повторяется действие из лога...", 0)
        self._run_task(
            lambda: self._backend.replay_log_action(log_id),
            self._handle_replay_result,
            "Логи",
        )

    def _run_task(
        self,
        function: Callable[[], object],
        success_handler: Callable[[object], None],
        error_title: str,
    ) -> None:
        task = BackgroundTask(function, self)
        task.success_handler = success_handler
        task.error_title = error_title
        task.finished.connect(self._on_task_finished)
        self._active_tasks.append(task)
        task.start()

    @Slot(object, object)
    def _on_task_finished(self, result_obj: object, error_obj: object) -> None:
        sender = self.sender()
        if isinstance(sender, BackgroundTask):
            try:
                self._active_tasks.remove(sender)
            except ValueError:
                pass

            if error_obj is not None:
                QMessageBox.warning(self, sender.error_title, str(error_obj))
                self._refresh_all()
                return

            if sender.success_handler is not None:
                sender.success_handler(result_obj)

    def _handle_replay_result(self, result_obj: object) -> None:
        result_message = cast(str, result_obj)
        self._show_status(result_message, 7000)
        self._refresh_all()


class MainWindow(QMainWindow):
    def __init__(
        self,
        backend: GuiBackend,
        paths: PContextPaths,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._backend = backend
        self._paths = paths
        self._allow_close = False

        self.setWindowTitle("PContext")
        self.resize(1100, 760)

        self._tab_widget = QTabWidget(self)
        self.setCentralWidget(self._tab_widget)

        self._services_tab = ServicesTab(
            backend, self.refresh_all, self.show_status_message, self
        )
        self._scripts_tab = ScriptsTab(
            backend, self.refresh_all, self.show_status_message, self
        )
        self._settings_tab = SettingsTab(
            backend,
            paths,
            self.refresh_all,
            self.show_status_message,
            self,
        )
        self._logs_tab = LogsTab(
            backend, self.refresh_all, self.show_status_message, self
        )

        self._tab_widget.addTab(self._services_tab, "Сервисы")
        self._tab_widget.addTab(self._scripts_tab, "Скрипты")
        self._tab_widget.addTab(self._settings_tab, "Настройки")
        self._tab_widget.addTab(self._logs_tab, "Логи")

        self.setStatusBar(QStatusBar(self))
        self.statusBar().showMessage("PContext запущен.")

        self.refresh_all()

    def show_status_message(self, message: str, timeout_ms: int = 5000) -> None:
        self.statusBar().showMessage(message, timeout_ms)

    def refresh_all(self) -> None:
        self._services_tab.refresh_data()
        self._scripts_tab.refresh_data()
        self._settings_tab.refresh_data()
        self._logs_tab.refresh_data()

    def show_services_tab(self) -> None:
        self.refresh_all()
        self._tab_widget.setCurrentWidget(self._services_tab)
        self.show_normal_activated()

    def show_scripts_tab(self) -> None:
        self.refresh_all()
        self._tab_widget.setCurrentWidget(self._scripts_tab)
        self.show_normal_activated()

    def show_settings_tab(self) -> None:
        self.refresh_all()
        self._tab_widget.setCurrentWidget(self._settings_tab)
        self.show_normal_activated()

    def show_logs_tab(self) -> None:
        self.refresh_all()
        self._tab_widget.setCurrentWidget(self._logs_tab)
        self.show_normal_activated()

    def show_normal_activated(self) -> None:
        self.show()
        self.raise_()
        self.activateWindow()

    def request_exit(self) -> None:
        self._allow_close = True
        self.hide()
        self.close()

        application = QApplication.instance()
        if application is not None:
            application.quit()

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        if self._allow_close:
            event.accept()
            return

        self.hide()
        self.statusBar().showMessage("Окно скрыто в tray.")
        event.ignore()
