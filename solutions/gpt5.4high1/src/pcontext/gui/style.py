from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QPushButton, QTableWidget
import qdarktheme


_MODERN_STYLESHEET = """
QWidget {
    color: #eef2f7;
    font-family: "Segoe UI", "Microsoft YaHei UI", sans-serif;
    font-size: 10pt;
    outline: none;
}

QMainWindow, QDialog {
    background: #1e2128;
}

QFrame[card="true"] {
    background: #262a33;
    border: 1px solid #353946;
    border-radius: 16px;
}

QLabel[role="sectionTitle"] {
    font-size: 13pt;
    font-weight: 600;
    color: #ffffff;
}

QLabel[role="muted"] {
    color: #b6beca;
}

QStatusBar {
    background: #1a1d23;
    border-top: 1px solid #323743;
    color: #c9d2de;
}

QTabWidget::pane {
    border: none;
    top: -1px;
}

QTabBar::tab {
    background: #262a33;
    border: 1px solid #353946;
    border-bottom: none;
    border-top-left-radius: 10px;
    border-top-right-radius: 10px;
    padding: 10px 18px;
    margin-right: 4px;
    color: #d7dde7;
}

QTabBar::tab:selected {
    background: #4b7dff;
    border-color: #4b7dff;
    color: #ffffff;
}

QTabBar::tab:hover:!selected {
    background: #2d313b;
}

QPushButton {
    background: #313640;
    border: 1px solid #434957;
    border-radius: 10px;
    padding: 8px 14px;
    min-height: 18px;
    color: #eef2f7;
}

QPushButton:hover {
    background: #3a404d;
    border-color: #4e5667;
}

QPushButton:pressed {
    background: #272c35;
}

QPushButton:disabled {
    background: #262a33;
    border-color: #353946;
    color: #798292;
}

QPushButton[role="primary"] {
    background: #4b7dff;
    border-color: #4b7dff;
    color: white;
    font-weight: 600;
}

QPushButton[role="primary"]:hover {
    background: #5a89ff;
    border-color: #5a89ff;
}

QPushButton[role="primary"]:pressed {
    background: #3d6ff2;
    border-color: #3d6ff2;
}

QLineEdit,
QComboBox,
QAbstractSpinBox,
QPlainTextEdit,
QTableWidget {
    background: #20242c;
    border: 1px solid #3a404b;
    border-radius: 10px;
    selection-background-color: #4b7dff;
    selection-color: white;
    color: #eef2f7;
}

QLineEdit,
QAbstractSpinBox {
    padding: 8px 10px;
}

QComboBox {
    padding: 6px 10px;
}

QComboBox::drop-down {
    width: 24px;
    border: none;
}

QComboBox QAbstractItemView {
    background: #262a33;
    border: 1px solid #3a404b;
    selection-background-color: #4b7dff;
    selection-color: white;
    color: #eef2f7;
}

QPlainTextEdit {
    padding: 10px;
}

QTableWidget {
    gridline-color: transparent;
    alternate-background-color: #242832;
    padding: 0px;
}

QMenu {
    background: #20242c;
    color: #eef2f7;
    border: 1px solid #3a404b;
    padding: 6px;
}

QMenu::item {
    background: transparent;
    color: #eef2f7;
    padding: 8px 24px 8px 12px;
    border-radius: 8px;
    margin: 2px 4px;
}

QMenu::item:selected {
    background: #4b7dff;
    color: white;
}

QMenu::separator {
    height: 1px;
    background: #3a404b;
    margin: 6px 8px;
}

QCheckBox {
    spacing: 8px;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 6px;
    border: 1px solid #4a5160;
    background: #20242c;
}

QCheckBox::indicator:checked {
    background: #4b7dff;
    border-color: #4b7dff;
}

QToolTip {
    background: #16181d;
    color: #eef2f7;
    border: 1px solid #3a404b;
    padding: 6px 8px;
}

QScrollBar:vertical {
    background: transparent;
    width: 12px;
    margin: 2px;
}

QScrollBar::handle:vertical {
    background: #4a5160;
    min-height: 28px;
    border-radius: 6px;
}

QScrollBar::handle:vertical:hover {
    background: #5a6273;
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    background: transparent;
    height: 12px;
    margin: 2px;
}

QScrollBar::handle:horizontal {
    background: #4a5160;
    min-width: 28px;
    border-radius: 6px;
}

QScrollBar::handle:horizontal:hover {
    background: #5a6273;
}

QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {
    width: 0px;
}

QMessageBox {
    background: #1f2229;
}

QMessageBox QLabel {
    min-width: 420px;
}
"""


_TABLE_HEADER_STYLESHEET = """
QHeaderView::section {
    background-color: #1b1f26;
    color: #ffffff;
    border: none;
    border-right: 1px solid #2e3440;
    border-bottom: 1px solid #2e3440;
    padding: 10px 12px;
    font-weight: 700;
}

QHeaderView {
    background-color: #1b1f26;
}
"""


def apply_modern_style(application: QApplication) -> None:
    """
    Применяет базовую современную тему ко всему приложению.
    """
    qdarktheme.setup_theme("auto")
    application.setStyleSheet(application.styleSheet() + "\n" + _MODERN_STYLESHEET)


def configure_table(table: QTableWidget) -> None:
    """
    Приводит таблицу к более современному виду и жёстко задаёт стиль заголовков.
    """
    table.setShowGrid(False)
    table.setAlternatingRowColors(True)
    table.setWordWrap(False)
    table.verticalHeader().setDefaultSectionSize(38)
    table.verticalHeader().setVisible(False)

    horizontal_header = table.horizontalHeader()
    horizontal_header.setDefaultAlignment(
        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
    )
    horizontal_header.setStyleSheet(_TABLE_HEADER_STYLESHEET)

    table.verticalHeader().setStyleSheet(_TABLE_HEADER_STYLESHEET)


def set_button_role(button: QPushButton, role: str | None) -> None:
    """
    Назначает визуальную роль кнопке.
    """
    button.setProperty("role", role if role is not None else "")
    button.style().unpolish(button)
    button.style().polish(button)
    button.update()
