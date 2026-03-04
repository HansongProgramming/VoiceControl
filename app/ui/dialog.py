from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.config import APP_PRESETS, PRESETS
from app.ui.styles import DIALOG_STYLE


class AddCommandDialog(QDialog):
    def __init__(self, parent=None, edit_data: dict = None):
        super().__init__(parent)
        self.edit_data = edit_data
        self.setWindowTitle(
            "Voice Commander - Edit Command"
            if edit_data
            else "Voice Commander - Add Command"
        )
        self.setFixedSize(420, 520)
        self._setup_ui()
        self.setStyleSheet(DIALOG_STYLE)
        if edit_data:
            self._load_data()

    # ------------------------------------------------------------------ UI --

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        header = QLabel("Configure Voice Command")
        header.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)

        layout.addWidget(QLabel("Voice Trigger Phrase:"))
        self.trigger_input = QLineEdit()
        self.trigger_input.setPlaceholderText("e.g., 'wake up its time to work'")
        layout.addWidget(self.trigger_input)

        layout.addWidget(QLabel("Action Type:"))
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Command", "Application", "Combined"])
        self.type_combo.currentTextChanged.connect(self._on_type_changed)
        layout.addWidget(self.type_combo)

        type_container = QFrame()
        type_layout = QVBoxLayout(type_container)
        type_layout.setContentsMargins(0, 0, 0, 0)
        type_layout.setSpacing(8)

        # -- Command section --
        self.command_widget = QWidget()
        cmd_layout = QVBoxLayout(self.command_widget)
        cmd_layout.setContentsMargins(0, 0, 0, 0)
        cmd_layout.setSpacing(8)

        ql = QLabel("Quick Select:")
        ql.setStyleSheet("color: #888; font-size: 11px;")
        cmd_layout.addWidget(ql)

        self.preset_combo = QComboBox()
        self.preset_combo.addItem("Custom Command")
        self.preset_combo.addItems([f"{k} - {v['desc']}" for k, v in PRESETS.items()])
        self.preset_combo.currentTextChanged.connect(self._on_preset_changed)
        cmd_layout.addWidget(self.preset_combo)

        cmd_layout.addWidget(QLabel("Command:"))
        self.command_input = QLineEdit()
        self.command_input.setPlaceholderText("Enter command to execute...")
        cmd_layout.addWidget(self.command_input)
        type_layout.addWidget(self.command_widget)

        # -- Application section --
        self.app_widget = QWidget()
        app_layout = QVBoxLayout(self.app_widget)
        app_layout.setContentsMargins(0, 0, 0, 0)
        app_layout.setSpacing(8)

        ql2 = QLabel("Quick Select:")
        ql2.setStyleSheet("color: #888; font-size: 11px;")
        app_layout.addWidget(ql2)

        self.app_preset_combo = QComboBox()
        self.app_preset_combo.addItem("Custom Application")
        self.app_preset_combo.addItems(
            [f"{k} - {v}" for k, v in APP_PRESETS.items()]
        )
        self.app_preset_combo.currentTextChanged.connect(self._on_app_preset_changed)
        app_layout.addWidget(self.app_preset_combo)

        app_layout.addWidget(QLabel("Application Path:"))
        self.app_input = QLineEdit()
        self.app_input.setPlaceholderText("Path to executable...")
        app_layout.addWidget(self.app_input)
        type_layout.addWidget(self.app_widget)
        self.app_widget.hide()

        # -- Combined section --
        self.combined_widget = QWidget()
        comb_layout = QVBoxLayout(self.combined_widget)
        comb_layout.setContentsMargins(0, 0, 0, 0)
        comb_layout.setSpacing(8)

        comb_layout.addWidget(QLabel("Application to Open:"))
        self.combined_app_preset = QComboBox()
        self.combined_app_preset.addItem("Custom")
        self.combined_app_preset.addItems(list(APP_PRESETS.keys()))
        self.combined_app_preset.currentTextChanged.connect(
            self._on_combined_app_changed
        )
        comb_layout.addWidget(self.combined_app_preset)

        self.combined_app_input = QLineEdit()
        self.combined_app_input.setPlaceholderText("Custom app path...")
        comb_layout.addWidget(self.combined_app_input)

        comb_layout.addWidget(QLabel("Command to run after (optional):"))
        self.combined_cmd_input = QLineEdit()
        self.combined_cmd_input.setPlaceholderText(
            "Command executed after app opens..."
        )
        comb_layout.addWidget(self.combined_cmd_input)

        tip = QLabel("Tip: App opens first, waits 2 s, then runs command")
        tip.setStyleSheet("color: #666; font-size: 10px; font-style: italic;")
        comb_layout.addWidget(tip)
        type_layout.addWidget(self.combined_widget)
        self.combined_widget.hide()

        layout.addWidget(type_container)

        layout.addWidget(QLabel("Description (optional):"))
        self.desc_input = QLineEdit()
        self.desc_input.setPlaceholderText("What this command does...")
        layout.addWidget(self.desc_input)

        layout.addStretch()

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("cancel_btn")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)

        self.save_btn = QPushButton("Save Command")
        self.save_btn.clicked.connect(self.accept)
        self.save_btn.setDefault(True)
        btn_layout.addWidget(self.save_btn)

        layout.addLayout(btn_layout)

    # ------------------------------------------------------------ Handlers --

    def _on_type_changed(self, text: str):
        self.command_widget.hide()
        self.app_widget.hide()
        self.combined_widget.hide()
        if text == "Command":
            self.command_widget.show()
        elif text == "Application":
            self.app_widget.show()
        elif text == "Combined":
            self.combined_widget.show()

    def _on_preset_changed(self, text: str):
        if text == "Custom Command":
            self.command_input.setText("")
            self.command_input.setEnabled(True)
            self.command_input.setStyleSheet("")
        else:
            key = text.split(" - ")[0]
            if key in PRESETS:
                self.command_input.setText(PRESETS[key]["cmd"])
                self.command_input.setEnabled(False)
                self.command_input.setStyleSheet("color: #888;")

    def _on_app_preset_changed(self, text: str):
        if text == "Custom Application":
            self.app_input.setText("")
            self.app_input.setEnabled(True)
            self.app_input.setStyleSheet("")
        else:
            key = text.split(" - ")[0]
            if key in APP_PRESETS:
                self.app_input.setText(APP_PRESETS[key])
                self.app_input.setEnabled(False)
                self.app_input.setStyleSheet("color: #888;")

    def _on_combined_app_changed(self, text: str):
        if text == "Custom":
            self.combined_app_input.setEnabled(True)
            self.combined_app_input.setText("")
            self.combined_app_input.setStyleSheet("")
        else:
            self.combined_app_input.setEnabled(False)
            self.combined_app_input.setText(APP_PRESETS.get(text, ""))
            self.combined_app_input.setStyleSheet("color: #888;")

    # ---------------------------------------------------------------- Data --

    def _load_data(self):
        self.trigger_input.setText(self.edit_data.get("trigger", ""))
        self.desc_input.setText(self.edit_data.get("description", ""))

        cmd_type = self.edit_data.get("type", "command")
        self.type_combo.setCurrentText(cmd_type.capitalize())

        if cmd_type == "command":
            cmd = self.edit_data.get("command", "")
            self.command_input.setText(cmd)
            for key, val in PRESETS.items():
                if val["cmd"] == cmd:
                    self.preset_combo.setCurrentText(f"{key} - {val['desc']}")
                    break

        elif cmd_type == "application":
            path = self.edit_data.get("app_path", "")
            self.app_input.setText(path)
            for key, val in APP_PRESETS.items():
                if val == path:
                    self.app_preset_combo.setCurrentText(f"{key} - {val}")
                    break

        elif cmd_type == "combined":
            self.combined_app_input.setText(self.edit_data.get("app_path", ""))
            self.combined_cmd_input.setText(self.edit_data.get("command", ""))

    def get_data(self) -> dict:
        data = {
            "trigger": self.trigger_input.text().strip(),
            "type": self.type_combo.currentText().lower(),
            "description": self.desc_input.text().strip(),
        }
        if data["type"] == "command":
            data["command"] = self.command_input.text().strip()
        elif data["type"] == "application":
            data["app_path"] = self.app_input.text().strip()
        elif data["type"] == "combined":
            data["app_path"] = self.combined_app_input.text().strip()
            data["command"] = self.combined_cmd_input.text().strip()
        return data
