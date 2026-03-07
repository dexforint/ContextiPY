from __future__ import annotations

import sys

import qdarktheme
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from pcontext.agent.server import AgentRuntime
from pcontext.config import PContextPaths, get_paths
from pcontext.gui.action_bridge import GuiActionBridge
from pcontext.gui.ask_bridge import GuiAskBridge
from pcontext.gui.backend import GuiBackend
from pcontext.gui.icons import load_application_icon
from pcontext.gui.main_window import MainWindow
from pcontext.runtime.action_executor import (
    ActionExecutionHooks,
    clear_action_execution_hooks,
    install_action_execution_hooks,
)
from pcontext.runtime.ask_runtime import (
    AskExecutionHooks,
    clear_ask_execution_hooks,
    install_ask_execution_hooks,
)


def run_gui(paths: PContextPaths | None = None) -> int:
    """
    Запускает tray-приложение PContext.
    """
    resolved_paths = paths if paths is not None else get_paths()

    application = QApplication.instance()
    if application is None:
        application = QApplication(sys.argv)

    application.setApplicationName("PContext")
    application.setQuitOnLastWindowClosed(False)

    qdarktheme.setup_theme("auto")

    app_icon = load_application_icon(resolved_paths, application)
    application.setWindowIcon(app_icon)

    runtime = AgentRuntime(resolved_paths)
    runtime.start()

    backend = GuiBackend(runtime.application)
    window = MainWindow(backend, resolved_paths)
    window.setWindowIcon(app_icon)

    tray_icon = _create_tray_icon(application, window, app_icon)

    action_bridge = GuiActionBridge(
        tray_icon=tray_icon, backend=backend, parent=application
    )
    ask_bridge = GuiAskBridge(parent=application)

    install_action_execution_hooks(
        ActionExecutionHooks(
            show_text=action_bridge.show_text,
            show_notification=action_bridge.show_notification,
        )
    )
    install_ask_execution_hooks(
        AskExecutionHooks(
            ask_user=ask_bridge.ask_user,
        )
    )

    tray_icon.show()
    window.show()

    try:
        return application.exec()
    finally:
        clear_ask_execution_hooks()
        clear_action_execution_hooks()
        tray_icon.hide()
        runtime.stop()


def _create_tray_icon(
    application: QApplication,
    window: MainWindow,
    icon: QIcon,
) -> QSystemTrayIcon:
    """
    Создаёт и настраивает иконку в системном трее.
    """
    tray_icon = QSystemTrayIcon(icon, application)
    tray_icon.setToolTip("PContext")

    menu = QMenu()

    services_action = QAction("Сервисы", menu)
    services_action.triggered.connect(window.show_services_tab)
    menu.addAction(services_action)

    scripts_action = QAction("Скрипты", menu)
    scripts_action.triggered.connect(window.show_scripts_tab)
    menu.addAction(scripts_action)

    settings_action = QAction("Настройки", menu)
    settings_action.triggered.connect(window.show_settings_tab)
    menu.addAction(settings_action)

    logs_action = QAction("Логи", menu)
    logs_action.triggered.connect(window.show_logs_tab)
    menu.addAction(logs_action)

    menu.addSeparator()

    exit_action = QAction("Выход", menu)
    exit_action.triggered.connect(window.request_exit)
    menu.addAction(exit_action)

    tray_icon.setContextMenu(menu)
    tray_icon.activated.connect(lambda reason: _handle_tray_activation(reason, window))
    return tray_icon


def _handle_tray_activation(
    reason: QSystemTrayIcon.ActivationReason, window: MainWindow
) -> None:
    """
    Обрабатывает клик по иконке трея.
    """
    if reason in {
        QSystemTrayIcon.ActivationReason.Trigger,
        QSystemTrayIcon.ActivationReason.DoubleClick,
    }:
        window.show_scripts_tab()
