"""Settings window for application configuration."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

try:  # pragma: no cover
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import (
        QCheckBox,
        QHBoxLayout,
        QLabel,
        QMainWindow,
        QMessageBox,
        QVBoxLayout,
        QWidget,
    )
except ImportError:  # pragma: no cover
    Qt = None  # type: ignore[assignment]
    QCheckBox = object  # type: ignore[assignment,misc]
    QHBoxLayout = object  # type: ignore[assignment,misc]
    QLabel = object  # type: ignore[assignment,misc]
    QMainWindow = object  # type: ignore[assignment,misc]
    QMessageBox = object  # type: ignore[assignment,misc]
    QVBoxLayout = object  # type: ignore[assignment,misc]
    QWidget = object  # type: ignore[assignment,misc]
    PYSIDE_AVAILABLE = False
else:
    PYSIDE_AVAILABLE = True

if TYPE_CHECKING:
    from contextipy.config.settings import Settings, SettingsStore

from ..icons import APP_ICON_NAME, load_icon
from ..theme import get_theme
from ..widgets import Card, Heading, PrimaryButton, SecondaryLabel, VStack


class SettingsWindow(QMainWindow):
    """Window for managing application settings."""

    def __init__(
        self,
        *,
        settings_store: SettingsStore | None = None,
        load_settings: Callable[[], Settings] | None = None,
        save_settings: Callable[[Settings], tuple[bool, str | None]] | None = None,
        on_autostart_change: Callable[[bool], tuple[bool, str | None]] | None = None,
    ) -> None:
        """Initialize the settings window.

        Args:
            settings_store: Optional SettingsStore for loading/saving settings.
            load_settings: Optional callable to load current settings.
            save_settings: Optional callable to save settings. Returns (success, error_message).
            on_autostart_change: Optional callable to handle auto-start toggle.
                Returns (success, error_message).
        """
        if not PYSIDE_AVAILABLE:
            raise RuntimeError("PySide6 is not available")

        super().__init__()

        self._settings_store = settings_store
        self._original_settings: Settings | None = None
        self._checkboxes: dict[str, QCheckBox] = {}

        if load_settings is not None:
            self._load_settings = load_settings
        elif self._settings_store is not None:
            self._load_settings = self._load_from_store
        else:
            self._load_settings = self._load_empty_settings

        if save_settings is not None:
            self._save_settings = save_settings
        elif self._settings_store is not None:
            self._save_settings = self._save_to_store
        else:
            self._save_settings = self._save_unavailable

        self._on_autostart_change = on_autostart_change or self._autostart_change_unavailable

        theme = get_theme()
        self._spacing = theme.spacing

        self.setWindowTitle("Настройки")
        self.setMinimumSize(500, 400)

        icon = load_icon(APP_ICON_NAME)
        if not icon.isNull():
            self.setWindowIcon(icon)

        self._setup_ui()
        self._load_current_settings()

    def _load_empty_settings(self) -> Settings:
        """Return empty settings."""
        from contextipy.config.settings import Settings

        return Settings()

    def _load_from_store(self) -> Settings:
        """Load settings from the settings store."""
        if self._settings_store is None:
            return self._load_empty_settings()
        return self._settings_store.load()

    def _save_unavailable(self, settings: Settings) -> tuple[bool, str | None]:
        """Return error when save is unavailable."""
        return (False, "Сохранение настроек недоступно")

    def _save_to_store(self, settings: Settings) -> tuple[bool, str | None]:
        """Save settings to the settings store."""
        if self._settings_store is None:
            return (False, "Хранилище настроек недоступно")
        try:
            self._settings_store.save(settings)
            return (True, None)
        except Exception as exc:
            return (False, str(exc))

    def _autostart_change_unavailable(self, enabled: bool) -> tuple[bool, str | None]:
        """Return success when auto-start change is unavailable."""
        return (True, None)

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        central_widget = QWidget(self)
        central_layout = QVBoxLayout(central_widget)
        central_layout.setSpacing(self._spacing.lg)
        central_layout.setContentsMargins(
            self._spacing.xl,
            self._spacing.xl,
            self._spacing.xl,
            self._spacing.xl,
        )

        header = Heading("Настройки приложения", level=1)
        header.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        central_layout.addWidget(header)

        subtitle = SecondaryLabel("Управление параметрами запуска и уведомлений")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        central_layout.addWidget(subtitle)

        settings_container = VStack(parent=central_widget)

        autostart_card = self._create_autostart_card()
        settings_container.addWidget(autostart_card)

        notifications_card = self._create_notifications_card()
        settings_container.addWidget(notifications_card)

        settings_container.addStretch(1)

        central_layout.addWidget(settings_container, stretch=1)

        button_layout = QHBoxLayout()
        button_layout.setSpacing(self._spacing.md)
        button_layout.addStretch(1)

        save_button = PrimaryButton("Сохранить")
        save_button.setToolTip("Сохранить изменения настроек")
        save_button.clicked.connect(self._on_save)
        button_layout.addWidget(save_button)

        central_layout.addLayout(button_layout)

        self.setCentralWidget(central_widget)

    def _create_autostart_card(self) -> Card:
        """Create the auto-start settings card."""
        card = Card()
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(self._spacing.md)

        title_label = QLabel("<b>Автозапуск</b>")
        card_layout.addWidget(title_label)

        description_label = SecondaryLabel(
            "Запускать приложение автоматически при входе в систему"
        )
        description_label.setWordWrap(True)
        card_layout.addWidget(description_label)

        checkbox = QCheckBox("Запускать при старте системы")
        self._checkboxes["launch_on_startup"] = checkbox
        card_layout.addWidget(checkbox)

        return card

    def _create_notifications_card(self) -> Card:
        """Create the notifications settings card."""
        card = Card()
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(self._spacing.md)

        title_label = QLabel("<b>Уведомления</b>")
        card_layout.addWidget(title_label)

        description_label = SecondaryLabel(
            "Показывать системные уведомления о событиях приложения"
        )
        description_label.setWordWrap(True)
        card_layout.addWidget(description_label)

        checkbox = QCheckBox("Включить уведомления")
        self._checkboxes["enable_notifications"] = checkbox
        card_layout.addWidget(checkbox)

        return card

    def _load_current_settings(self) -> None:
        """Load current settings and update UI."""
        try:
            settings = self._load_settings()
            self._original_settings = settings
            self._update_ui_from_settings(settings)
        except Exception as exc:
            self._show_error_dialog(
                "Ошибка загрузки настроек",
                f"Не удалось загрузить настройки: {exc}",
            )

    def _update_ui_from_settings(self, settings: Settings) -> None:
        """Update UI checkboxes from settings.

        Args:
            settings: Settings to display.
        """
        if "launch_on_startup" in self._checkboxes:
            self._checkboxes["launch_on_startup"].setChecked(settings.launch_on_startup)
        if "enable_notifications" in self._checkboxes:
            self._checkboxes["enable_notifications"].setChecked(settings.enable_notifications)

    def _get_current_settings(self) -> Settings:
        """Get current settings from UI.

        Returns:
            Settings reflecting current UI state.
        """
        from contextipy.config.settings import Settings

        return Settings(
            launch_on_startup=self._checkboxes.get("launch_on_startup", QCheckBox()).isChecked(),
            enable_notifications=self._checkboxes.get("enable_notifications", QCheckBox()).isChecked(),
        )

    def _on_save(self) -> None:
        """Handle save button click."""
        new_settings = self._get_current_settings()

        autostart_changed = (
            self._original_settings is None
            or new_settings.launch_on_startup != self._original_settings.launch_on_startup
        )

        if autostart_changed:
            success, error = self._on_autostart_change(new_settings.launch_on_startup)
            if not success:
                self._show_error_dialog(
                    "Ошибка автозапуска",
                    error or "Не удалось изменить настройки автозапуска",
                )
                return

        success, error = self._save_settings(new_settings)
        if not success:
            self._show_error_dialog(
                "Ошибка сохранения",
                error or "Не удалось сохранить настройки",
            )
            return

        self._original_settings = new_settings
        self._show_success_dialog("Настройки успешно сохранены")

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

    def _show_success_dialog(self, message: str) -> None:
        """Show a success message dialog.

        Args:
            message: Success message.
        """
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Icon.Information)
        msg_box.setWindowTitle("Успешно")
        msg_box.setText(message)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg_box.exec()


__all__ = [
    "SettingsWindow",
]
