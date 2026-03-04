MAIN_STYLE = """
QMainWindow {
    background-color: #0f0f1e;
    border: 1px solid #2a2a4e;
    border-radius: 16px;
}
QWidget {
    background-color: transparent;
    color: #ffffff;
}
QPushButton {
    background-color: #e94560;
    color: white;
    border: none;
    border-radius: 8px;
    padding: 8px 16px;
    font-weight: 600;
    font-size: 12px;
}
QPushButton:hover {
    background-color: #ff5577;
}
QPushButton:pressed {
    background-color: #c93350;
}
QPushButton#mic_btn {
    background-color: #1a1a2e;
    border: 2px solid #3a3a4e;
    border-radius: 23px;
    font-size: 20px;
}
QPushButton#mic_btn:hover {
    border: 2px solid #e94560;
    background-color: #252538;
}
QListWidget {
    background-color: #1a1a2e;
    border: 1px solid #2a2a3e;
    border-radius: 10px;
    padding: 5px;
    color: white;
    outline: none;
}
QListWidget::item {
    background-color: #252538;
    border-radius: 6px;
    padding: 10px;
    margin: 3px;
    border: 1px solid transparent;
}
QListWidget::item:selected {
    background-color: #e94560;
    border: 1px solid #ff5577;
}
QListWidget::item:hover {
    background-color: #303048;
    border: 1px solid #404058;
}
QScrollBar:vertical {
    background: #1a1a2e;
    width: 8px;
    border-radius: 4px;
}
QScrollBar::handle:vertical {
    background: #3a3a4e;
    border-radius: 4px;
    min-height: 20px;
}
QScrollBar::handle:vertical:hover {
    background: #e94560;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
"""

DIALOG_STYLE = """
QDialog {
    background-color: #0f0f1e;
    color: #ffffff;
    border: 1px solid #e94560;
}
QLabel {
    color: #b0b0b0;
    font-size: 12px;
    font-weight: 600;
    margin-top: 8px;
}
QLineEdit, QComboBox {
    background-color: #1a1a2e;
    color: #ffffff;
    border: 2px solid #2a2a3e;
    border-radius: 8px;
    padding: 10px;
    font-size: 13px;
    selection-background-color: #e94560;
}
QLineEdit:focus, QComboBox:focus {
    border: 2px solid #e94560;
}
QLineEdit:hover, QComboBox:hover {
    border: 2px solid #3a3a4e;
}
QPushButton {
    background-color: #e94560;
    color: white;
    border: none;
    border-radius: 8px;
    padding: 12px 24px;
    font-weight: bold;
    font-size: 13px;
}
QPushButton:hover {
    background-color: #ff5577;
}
QPushButton:pressed {
    background-color: #c93350;
}
QPushButton#cancel_btn {
    background-color: #2a2a3e;
}
QPushButton#cancel_btn:hover {
    background-color: #3a3a4e;
}
QComboBox::drop-down {
    border: none;
    width: 30px;
}
QComboBox::down-arrow {
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 5px solid #e94560;
    margin-right: 10px;
}
QComboBox QAbstractItemView {
    background-color: #1a1a2e;
    color: white;
    selection-background-color: #e94560;
    border: 1px solid #e94560;
    border-radius: 4px;
}
"""

MSGBOX_STYLE = """
QMessageBox { background-color: #0f0f1e; color: white; }
QPushButton { background-color: #e94560; color: white; padding: 8px 16px; border-radius: 6px; }
"""

IMPORT_EXPORT_STYLE = """
QDialog {
    background-color: #0f0f1e;
    color: white;
    border: 1px solid #e94560;
}
QLabel { color: #b0b0b0; font-size: 12px; }
QTextEdit {
    background-color: #1a1a2e;
    color: #4ade80;
    border: 1px solid #2a2a3e;
    border-radius: 8px;
    padding: 10px;
    font-family: Consolas, monospace;
    font-size: 11px;
}
QPushButton {
    background-color: #e94560;
    color: white;
    border: none;
    border-radius: 8px;
    padding: 10px 18px;
    font-weight: bold;
    font-size: 12px;
}
QPushButton:hover { background-color: #ff5577; }
QPushButton#close_btn { background-color: #2a2a3e; }
QPushButton#close_btn:hover { background-color: #3a3a4e; }
"""
