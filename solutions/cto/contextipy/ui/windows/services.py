"""Services status window showing running services with ability to stop."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import TYPE_CHECKING

try:  # pragma: no cover
    from PySide6.QtCore import QTimer, Qt
    from PySide6.QtWidgets import (
        QHBoxLayout,
        QLabel,
        QMainWindow,
        QMessageBox,
        QScrollArea,
        QVBoxLayout,
        QWidget,
    )
except ImportError:  # pragma: no cover
    QTimer = object  # type: ignore[assignment,misc]
    Qt = None  # type: ignore[assignment]
    QHBoxLayout = object  # type: ignore[assignment,misc]
    QLabel = object  # type: ignore[assignment,misc]
    QMainWindow = object  # type: ignore[assignment,misc]
    QMessageBox = object  # type: ignore[assignment,misc]
    QScrollArea = object  # type: ignore[assignment,misc]
    QVBoxLayout = object  # type: ignore[assignment,misc]
    QWidget = object  # type: ignore[assignment,misc]
    PYSIDE_AVAILABLE = False
else:
    PYSIDE_AVAILABLE = True

from contextipy.execution import ServiceInfo, ServiceManager, ServiceState

if TYPE_CHECKING:
    from contextipy.ui.theme import Spacing

from ..icons import APP_ICON_NAME, load_icon
from ..theme import Spacing, get_theme
from ..widgets import Card, Heading, SecondaryButton, SecondaryLabel, VStack


class ServiceModel:
    """Model holding service data."""

    def __init__(self) -> None:
        self.services: list[ServiceInfo] = []

    def update_services(self, services: list[ServiceInfo]) -> None:
        """Update the list of services."""
        self.services = services


class ServicesWindow(QMainWindow):
    """Window displaying running services with ability to stop them."""

    def __init__(
        self,
        *,
        service_manager: ServiceManager | None = None,
        get_services: Callable[[], list[ServiceInfo]] | None = None,
        stop_service: Callable[[str], tuple[bool, str | None]] | None = None,
        refresh_interval: int = 2000,
    ) -> None:
        """Initialize the services window.

        Args:
            service_manager: Optional service manager providing runtime data.
            get_services: Optional callable to fetch current services.
            stop_service: Optional callable to stop a service. Returns (success, error_message).
            refresh_interval: Refresh interval in milliseconds (default: 2000).
        """
        if not PYSIDE_AVAILABLE:
            raise RuntimeError("PySide6 is not available")

        super().__init__()

        self._service_manager = service_manager
        self._model = ServiceModel()
        self._refresh_interval = refresh_interval

        if get_services is not None:
            self._get_services = get_services
        elif self._service_manager is not None:
            self._get_services = self._fetch_services
        else:
            self._get_services = self._empty_services

        if stop_service is not None:
            self._stop_service = stop_service
        elif self._service_manager is not None:
            self._stop_service = self._stop_via_manager
        else:
            self._stop_service = self._stop_unavailable

        theme = get_theme()
        spacing = theme.spacing

        self.setWindowTitle("Запущенные сервисы")
        self.setMinimumSize(600, 400)

        icon = load_icon(APP_ICON_NAME)
        if not icon.isNull():
            self.setWindowIcon(icon)

        central_widget = QWidget(self)
        central_layout = QVBoxLayout(central_widget)
        central_layout.setSpacing(spacing.lg)
        central_layout.setContentsMargins(spacing.xl, spacing.xl, spacing.xl, spacing.xl)

        header = Heading("Запущенные сервисы", level=1)
        header.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        central_layout.addWidget(header)

        subtitle = SecondaryLabel("Управление долгоживущими сервисными процессами")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        central_layout.addWidget(subtitle)

        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)

        self._services_container = VStack(parent=scroll_area)
        scroll_area.setWidget(self._services_container)

        central_layout.addWidget(scroll_area, stretch=1)

        self.setCentralWidget(central_widget)

        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._refresh_view)
        self._refresh_timer.start(self._refresh_interval)

        self._refresh_view()

    def _empty_services(self) -> list[ServiceInfo]:
        """Return empty list of services."""
        return []

    def _fetch_services(self) -> list[ServiceInfo]:
        """Fetch services from the service manager."""
        if self._service_manager is None:
            return []
        return self._service_manager.get_all_services()

    def _stop_unavailable(self, service_id: str) -> tuple[bool, str | None]:
        """Return error when stop is unavailable."""
        return (False, "Остановка сервиса недоступна")

    def _stop_via_manager(self, service_id: str) -> tuple[bool, str | None]:
        """Stop service via the service manager."""
        if self._service_manager is None:
            return (False, "Менеджер сервисов недоступен")
        try:
            success = self._service_manager.stop_service(service_id)
            if success:
                return (True, None)
            return (False, f"Не удалось остановить сервис {service_id}")
        except Exception as exc:
            return (False, str(exc))

    def _refresh_view(self) -> None:
        """Refresh the view by fetching current services and updating the UI."""
        try:
            services = self._get_services()
            filtered = [
                service
                for service in services
                if service.state in {ServiceState.RUNNING, ServiceState.STARTING}
            ]
            self._model.update_services(filtered)
            self._update_ui()
        except Exception:
            pass

    def _update_ui(self) -> None:
        """Update the UI based on the current model."""
        layout: QVBoxLayout = self._services_container.layout()  # type: ignore[assignment]

        while layout.count():
            item = layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()

        theme = get_theme()
        spacing = theme.spacing

        if not self._model.services:
            no_services_label = SecondaryLabel("Нет запущенных сервисов")
            no_services_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            layout.addWidget(no_services_label)
            return

        for service in self._model.services:
            service_card = self._create_service_card(service, spacing)
            layout.addWidget(service_card)

        layout.addStretch(1)

    def _create_service_card(self, service: ServiceInfo, spacing: Spacing) -> Card:
        """Create a card widget for a service.

        Args:
            service: Service information.
            spacing: Theme spacing value.

        Returns:
            Card widget representing the service.
        """
        card = Card()
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(spacing.md)

        title_label = QLabel(f"<b>{service.service_id}</b>")
        card_layout.addWidget(title_label)

        state_text = f"Состояние: {service.state.value}"
        state_label = SecondaryLabel(state_text)
        card_layout.addWidget(state_label)

        if service.started_at:
            started_time = datetime.fromtimestamp(service.started_at).strftime("%Y-%m-%d %H:%M:%S")
            started_label = SecondaryLabel(f"Запущен: {started_time}")
            card_layout.addWidget(started_label)

        if service.restart_count > 0:
            restart_label = SecondaryLabel(f"Перезапусков: {service.restart_count}")
            card_layout.addWidget(restart_label)

        if service.last_error:
            error_label = SecondaryLabel(f"Последняя ошибка: {service.last_error}")
            card_layout.addWidget(error_label)

        button_layout = QHBoxLayout()
        button_layout.addStretch(1)

        stop_button = SecondaryButton("Остановить")
        stop_button.clicked.connect(
            lambda _checked=False, service_id=service.service_id: self._on_stop_service(service_id)
        )
        button_layout.addWidget(stop_button)

        card_layout.addLayout(button_layout)

        return card

    def _on_stop_service(self, service_id: str) -> None:
        """Handle stop service button click.

        Args:
            service_id: ID of the service to stop.
        """
        try:
            success, error_message = self._stop_service(service_id)
            if not success:
                self._show_error_dialog(
                    "Ошибка остановки сервиса",
                    error_message or f"Не удалось остановить сервис: {service_id}",
                )
            else:
                self._refresh_view()
        except Exception as exc:
            self._show_error_dialog("Ошибка остановки сервиса", str(exc))

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

    def closeEvent(self, event: "QCloseEvent") -> None:  # type: ignore[name-defined]  # noqa: F821
        """Handle window close event.

        Args:
            event: Close event.
        """
        self._refresh_timer.stop()
        super().closeEvent(event)  # type: ignore[misc]
