from __future__ import annotations

from collections.abc import Callable
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


class ServicesTab(QWidget):
    """
    Вкладка управления сервисами.
    """

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
        """
        Перерисовывает таблицу сервисов.
        """
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
        """
        Запускает или останавливает сервис в фоне.
        """
        self._show_status("Выполняется операция с сервисом...", 0)

        function = lambda: (
            self._backend.stop_service(service_id)
            if currently_running
            else lambda: self._backend.start_service(service_id)
        )

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
        """
        Запускает фоновую задачу.
        """
        task = BackgroundTask(function, self)
        task.success_handler = success_handler
        task.error_title = error_title
        task.finished.connect(self._on_task_finished)
        self._active_tasks.append(task)
        task.start()

    @Slot(object, object)
    def _on_task_finished(self, result_obj: object, error_obj: object) -> None:
        """
        Получает результат фоновой задачи.
        """
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
        """
        Обрабатывает результат запуска или остановки сервиса.
        """
        result = cast(ServiceControlResult, result_obj)

        if result.accepted:
            self._show_status(result.message, 7000)
        else:
            QMessageBox.warning(self, "Сервисы", result.message)

        self._refresh_all()


class ScriptsTab(QWidget):
    """
    Вкладка со скриптами и service.script-методами.
    """

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
        """
        Перерисовывает список скриптов.
        """
        items = self._backend.list_script_items()
        self._table.setRowCount(len(items))

        for row_index, item in enumerate(items):
            self._fill_row(row_index, item)

    def _fill_row(self, row_index: int, item: ScriptListItem) -> None:
        """
        Заполняет одну строку таблицы скриптов.
        """
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
        """
        Открывает окно редактирования параметров.
        """
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
        """
        Пытается запустить сценарий без входных файлов в фоне.

        Это важно для Ask(...): GUI-поток должен оставаться свободным,
        иначе форма вопросов не сможет открыться.
        """
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
        """
        Запускает фоновую задачу.
        """
        task = BackgroundTask(function, self)
        task.success_handler = success_handler
        task.error_title = error_title
        task.finished.connect(self._on_task_finished)
        self._active_tasks.append(task)
        task.start()

    @Slot(object, object)
    def _on_task_finished(self, result_obj: object, error_obj: object) -> None:
        """
        Получает результат фоновой задачи.
        """
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
        """
        Обрабатывает результат прямого запуска сценария.
        """
        accepted, message = cast(tuple[bool, str], result_obj)

        if accepted:
            self._show_status(message, 8000)
        else:
            QMessageBox.warning(self, "Запуск", message)

        self._refresh_all()


class SettingsTab(QWidget):
    """
    Вкладка настроек приложения.
    """

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

        save_button = QPushButton("Сохранить настройки", self)
        save_button.clicked.connect(self._save_settings)

        reload_button = QPushButton("Пересканировать скрипты", self)
        reload_button.clicked.connect(self._reload_registry)

        info_label = QLabel(
            f"Папка скриптов: <code>{paths.scripts}</code><br>"
            f"SQLite: <code>{paths.state_db}</code>"
        )
        info_label.setWordWrap(True)

        buttons_row = QHBoxLayout()
        buttons_row.addWidget(save_button)
        buttons_row.addWidget(reload_button)
        buttons_row.addStretch(1)

        layout = QVBoxLayout(self)
        layout.addWidget(self._autostart_checkbox)
        layout.addWidget(self._disable_notifications_checkbox)
        layout.addWidget(info_label)
        layout.addLayout(buttons_row)
        layout.addStretch(1)

        self.refresh_data()

    def refresh_data(self) -> None:
        """
        Загружает сохранённые настройки в виджеты.
        """
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

    def _save_settings(self) -> None:
        """
        Сохраняет настройки приложения.
        """
        self._backend.set_setting(
            GuiBackend.SETTINGS_AUTOSTART,
            self._autostart_checkbox.isChecked(),
        )
        self._backend.set_setting(
            GuiBackend.SETTINGS_DISABLE_NOTIFICATIONS,
            self._disable_notifications_checkbox.isChecked(),
        )
        self._show_status("Настройки сохранены.", 5000)

    def _reload_registry(self) -> None:
        """
        Перезагружает каталог пользовательских скриптов в фоне.
        """
        self._show_status("Идёт перерегистрация скриптов...", 0)
        self._run_task(
            self._backend.reload_registry,
            self._handle_reload_result,
            "Перерегистрация",
        )

    def _run_task(
        self,
        function: Callable[[], object],
        success_handler: Callable[[object], None],
        error_title: str,
    ) -> None:
        """
        Запускает фоновую задачу.
        """
        task = BackgroundTask(function, self)
        task.success_handler = success_handler
        task.error_title = error_title
        task.finished.connect(self._on_task_finished)
        self._active_tasks.append(task)
        task.start()

    @Slot(object, object)
    def _on_task_finished(self, result_obj: object, error_obj: object) -> None:
        """
        Получает результат фоновой задачи.
        """
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
        """
        Показывает результат перезагрузки каталога.
        """
        command_count, service_count, failure_count = cast(
            tuple[int, int, int], result_obj
        )

        QMessageBox.information(
            self,
            "Перерегистрация",
            (
                f"Каталог обновлён.\n\n"
                f"Команд: {command_count}\n"
                f"Сервисов: {service_count}\n"
                f"Ошибок: {failure_count}"
            ),
        )
        self._refresh_all()


class LogsTab(QWidget):
    """
    Вкладка последних логов запусков.
    """

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
        """
        Перерисовывает журнал запусков.
        """
        logs = self._backend.list_logs(limit=100)
        self._table.setRowCount(len(logs))

        for row_index, log_record in enumerate(logs):
            self._table.setItem(
                row_index, 0, QTableWidgetItem(log_record.created_at_utc)
            )
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
            self._table.setItem(row_index, 4, QTableWidgetItem(log_record.message))

            replay_button = QPushButton("Повторить", self)
            replay_button.setEnabled(log_record.action_json is not None)
            replay_button.clicked.connect(
                partial(self._replay_action, log_record.log_id)
            )
            self._table.setCellWidget(row_index, 5, replay_button)

    def _replay_action(self, log_id: int) -> None:
        """
        Повторяет сохранённое действие из лога в фоне.
        """
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
        """
        Запускает фоновую задачу.
        """
        task = BackgroundTask(function, self)
        task.success_handler = success_handler
        task.error_title = error_title
        task.finished.connect(self._on_task_finished)
        self._active_tasks.append(task)
        task.start()

    @Slot(object, object)
    def _on_task_finished(self, result_obj: object, error_obj: object) -> None:
        """
        Получает результат фоновой задачи.
        """
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
        """
        Обрабатывает результат повтора действия.
        """
        result_message = cast(str, result_obj)
        self._show_status(result_message, 7000)
        self._refresh_all()


class MainWindow(QMainWindow):
    """
    Главное окно PContext.
    """

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
        self.resize(1100, 720)

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
        """
        Показывает короткое сообщение в строке состояния.
        """
        self.statusBar().showMessage(message, timeout_ms)

    def refresh_all(self) -> None:
        """
        Обновляет все вкладки окна.
        """
        self._services_tab.refresh_data()
        self._scripts_tab.refresh_data()
        self._settings_tab.refresh_data()
        self._logs_tab.refresh_data()

    def show_services_tab(self) -> None:
        """
        Показывает вкладку сервисов.
        """
        self.refresh_all()
        self._tab_widget.setCurrentWidget(self._services_tab)
        self.show_normal_activated()

    def show_scripts_tab(self) -> None:
        """
        Показывает вкладку скриптов.
        """
        self.refresh_all()
        self._tab_widget.setCurrentWidget(self._scripts_tab)
        self.show_normal_activated()

    def show_settings_tab(self) -> None:
        """
        Показывает вкладку настроек.
        """
        self.refresh_all()
        self._tab_widget.setCurrentWidget(self._settings_tab)
        self.show_normal_activated()

    def show_logs_tab(self) -> None:
        """
        Показывает вкладку логов.
        """
        self.refresh_all()
        self._tab_widget.setCurrentWidget(self._logs_tab)
        self.show_normal_activated()

    def show_normal_activated(self) -> None:
        """
        Делает окно видимым и активным.
        """
        self.show()
        self.raise_()
        self.activateWindow()

    def request_exit(self) -> None:
        """
        Полностью завершает приложение по команде из tray icon.
        """
        self._allow_close = True
        self.hide()
        self.close()

        application = QApplication.instance()
        if application is not None:
            application.quit()

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        """
        При обычном закрытии окно не убивается, а скрывается в tray.
        """
        if self._allow_close:
            event.accept()
            return

        self.hide()
        self.statusBar().showMessage("Окно скрыто в tray.")
        event.ignore()
