import sys
import json
import os
import subprocess
import threading
import time
import webbrowser
from pathlib import Path
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QPushButton, QLabel, QLineEdit, 
                            QComboBox, QListWidget, QListWidgetItem, QMessageBox,
                            QDialog, QTextEdit, QSystemTrayIcon, QMenu, QGraphicsDropShadowEffect)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject, QSize, QPoint, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QColor, QIcon, QFont, QPainter, QBrush, QLinearGradient, QPalette, QAction
import speech_recognition as sr
import pyautogui
from PyQt6.QtWidgets import QGraphicsBlurEffect

# Configuration path
CONFIG_PATH = Path.home() / ".voice_commander_config.json"

# Preset commands
PRESETS = {
    "shutdown": {"cmd": "shutdown /s /t 0", "desc": "Shutdown PC"},
    "restart": {"cmd": "shutdown /r /t 0", "desc": "Restart PC"},
    "sleep": {"cmd": "rundll32.exe powrprof.dll,SetSuspendState 0,1,0", "desc": "Sleep Mode"},
    "lock": {"cmd": "rundll32.exe user32.dll,LockWorkStation", "desc": "Lock Screen"},
    "mute": {"cmd": "nircmd.exe mutesysvolume 1", "desc": "Mute Volume"},
    "unmute": {"cmd": "nircmd.exe mutesysvolume 0", "desc": "Unmute Volume"},
    "vol_up": {"cmd": "nircmd.exe changesysvolume 2000", "desc": "Volume Up"},
    "vol_down": {"cmd": "nircmd.exe changesysvolume -2000", "desc": "Volume Down"},
    "screenshot": {"cmd": "nircmd.exe savescreenshot screenshot.png", "desc": "Screenshot"},
}

APP_PRESETS = {
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "chrome": "chrome.exe",
    "firefox": "firefox.exe",
    "explorer": "explorer.exe",
    "cmd": "cmd.exe",
    "powershell": "powershell.exe",
    "taskmgr": "taskmgr.exe",
    "spotify": "spotify.exe",
}

class VoiceSignals(QObject):
    text_detected = pyqtSignal(str)
    command_executed = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    listening_status = pyqtSignal(bool)

class VoiceThread(threading.Thread):
    def __init__(self, signals, commands_dict):
        super().__init__(daemon=True)
        self.signals = signals
        self.commands = commands_dict
        self.listening = False
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        
        # Calibrate for ambient noise
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source)
    
    def run(self):
        while True:
            if self.listening:
                try:
                    with self.microphone as source:
                        self.signals.text_detected.emit("Listening...")
                        audio = self.recognizer.listen(source, timeout=1, phrase_time_limit=5)
                    
                    text = self.recognizer.recognize_google(audio).lower()
                    self.signals.text_detected.emit(f"Heard: {text}")
                    
                    # Check commands
                    for trigger, action in self.commands.items():
                        if trigger.lower() in text:
                            self.execute_action(action, trigger)
                            break
                            
                except sr.WaitTimeoutError:
                    pass
                except sr.UnknownValueError:
                    pass
                except sr.RequestError as e:
                    self.signals.error_occurred.emit(f"Speech error: {e}")
                except Exception as e:
                    self.signals.error_occurred.emit(str(e))
            time.sleep(0.1)
    
    def execute_action(self, action, trigger):
        try:
            cmd_type = action.get("type")
            
            if cmd_type == "command":
                command = action.get("command", "")
                if command.startswith("nircmd"):
                    # Try to use nircmd if available, otherwise skip
                    try:
                        subprocess.Popen(command, shell=True)
                    except:
                        pass
                else:
                    subprocess.Popen(command, shell=True)
                    
            elif cmd_type == "application":
                app_path = action.get("app_path", "")
                subprocess.Popen(app_path, shell=True)
                
            elif cmd_type == "combined":
                # Open app first
                app_path = action.get("app_path", "")
                subprocess.Popen(app_path, shell=True)
                time.sleep(2)  # Wait for app to open
                # Then run command
                command = action.get("command", "")
                if command:
                    subprocess.Popen(command, shell=True)
            
            self.signals.command_executed.emit(trigger)
            
        except Exception as e:
            self.signals.error_occurred.emit(f"Execution error: {e}")
    
    def toggle_listening(self, state):
        self.listening = state
        self.signals.listening_status.emit(state)

class AddCommandDialog(QDialog):
    def __init__(self, parent=None, edit_data=None):
        super().__init__(parent)
        self.edit_data = edit_data
        self.setWindowTitle("Add Command" if not edit_data else "Edit Command")
        self.setFixedSize(400, 500)
        self.setup_ui()
        self.apply_styles()
        
        if edit_data:
            self.load_data()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Trigger phrase
        layout.addWidget(QLabel("Voice Trigger:"))
        self.trigger_input = QLineEdit()
        self.trigger_input.setPlaceholderText("e.g., 'wake up its time to work'")
        layout.addWidget(self.trigger_input)
        
        # Action Type
        layout.addWidget(QLabel("Action Type:"))
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Command", "Application", "Combined"])
        self.type_combo.currentTextChanged.connect(self.on_type_changed)
        layout.addWidget(self.type_combo)
        
        # Command Section
        self.command_widget = QWidget()
        cmd_layout = QVBoxLayout(self.command_widget)
        cmd_layout.setContentsMargins(0, 0, 0, 0)
        
        self.preset_combo = QComboBox()
        self.preset_combo.addItem("Custom Command")
        self.preset_combo.addItems([f"{k} - {v['desc']}" for k, v in PRESETS.items()])
        self.preset_combo.currentTextChanged.connect(self.on_preset_changed)
        cmd_layout.addWidget(self.preset_combo)
        
        self.command_input = QLineEdit()
        self.command_input.setPlaceholderText("Enter command...")
        cmd_layout.addWidget(self.command_input)
        
        layout.addWidget(self.command_widget)
        
        # Application Section
        self.app_widget = QWidget()
        app_layout = QVBoxLayout(self.app_widget)
        app_layout.setContentsMargins(0, 0, 0, 0)
        
        self.app_preset_combo = QComboBox()
        self.app_preset_combo.addItem("Custom Application")
        self.app_preset_combo.addItems([f"{k} - {v}" for k, v in APP_PRESETS.items()])
        self.app_preset_combo.currentTextChanged.connect(self.on_app_preset_changed)
        app_layout.addWidget(self.app_preset_combo)
        
        self.app_input = QLineEdit()
        self.app_input.setPlaceholderText("Path to executable...")
        app_layout.addWidget(self.app_input)
        
        self.app_widget.hide()
        layout.addWidget(self.app_widget)
        
        # Combined Section
        self.combined_widget = QWidget()
        combined_layout = QVBoxLayout(self.combined_widget)
        combined_layout.setContentsMargins(0, 0, 0, 0)
        
        combined_layout.addWidget(QLabel("Application:"))
        self.combined_app_preset = QComboBox()
        self.combined_app_preset.addItem("Custom")
        self.combined_app_preset.addItems(list(APP_PRESETS.keys()))
        self.combined_app_preset.currentTextChanged.connect(self.on_combined_app_changed)
        combined_layout.addWidget(self.combined_app_preset)
        
        self.combined_app_input = QLineEdit()
        self.combined_app_input.setPlaceholderText("Custom app path...")
        combined_layout.addWidget(self.combined_app_input)
        
        combined_layout.addWidget(QLabel("Command to run after (optional):"))
        self.combined_cmd_input = QLineEdit()
        self.combined_cmd_input.setPlaceholderText("Command...")
        combined_layout.addWidget(self.combined_cmd_input)
        
        self.combined_widget.hide()
        layout.addWidget(self.combined_widget)
        
        # Description
        layout.addWidget(QLabel("Description (optional):"))
        self.desc_input = QLineEdit()
        self.desc_input.setPlaceholderText("What this command does...")
        layout.addWidget(self.desc_input)
        
        # Buttons
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self.accept)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)
        
        layout.addStretch()
    
    def apply_styles(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #1a1a2e;
                color: #eee;
                border-radius: 15px;
            }
            QLabel {
                color: #a0a0a0;
                font-size: 12px;
                font-weight: bold;
            }
            QLineEdit, QComboBox {
                background-color: #16213e;
                color: white;
                border: 1px solid #0f3460;
                border-radius: 8px;
                padding: 10px;
                font-size: 13px;
            }
            QLineEdit:focus, QComboBox:focus {
                border: 1px solid #e94560;
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
                background-color: #ff6b6b;
            }
            QPushButton#cancel_btn {
                background-color: #16213e;
            }
            QComboBox::drop-down {
                border: none;
                padding-right: 10px;
            }
            QComboBox QAbstractItemView {
                background-color: #16213e;
                color: white;
                selection-background-color: #e94560;
            }
        """)
        self.cancel_btn.setObjectName("cancel_btn")
    
    def on_type_changed(self, text):
        self.command_widget.hide()
        self.app_widget.hide()
        self.combined_widget.hide()
        
        if text == "Command":
            self.command_widget.show()
        elif text == "Application":
            self.app_widget.show()
        elif text == "Combined":
            self.combined_widget.show()
    
    def on_preset_changed(self, text):
        if text == "Custom Command":
            self.command_input.setText("")
            self.command_input.setEnabled(True)
        else:
            key = text.split(" - ")[0]
            if key in PRESETS:
                self.command_input.setText(PRESETS[key]["cmd"])
                self.command_input.setEnabled(False)
    
    def on_app_preset_changed(self, text):
        if text == "Custom Application":
            self.app_input.setText("")
            self.app_input.setEnabled(True)
        else:
            key = text.split(" - ")[0]
            if key in APP_PRESETS:
                self.app_input.setText(APP_PRESETS[key])
                self.app_input.setEnabled(False)
    
    def on_combined_app_changed(self, text):
        if text == "Custom":
            self.combined_app_input.setEnabled(True)
            self.combined_app_input.setText("")
        else:
            self.combined_app_input.setEnabled(False)
            self.combined_app_input.setText(APP_PRESETS.get(text, ""))
    
    def load_data(self):
        self.trigger_input.setText(self.edit_data.get("trigger", ""))
        self.desc_input.setText(self.edit_data.get("description", ""))
        
        cmd_type = self.edit_data.get("type", "command")
        self.type_combo.setCurrentText(cmd_type.capitalize())
        
        if cmd_type == "command":
            cmd = self.edit_data.get("command", "")
            self.command_input.setText(cmd)
            # Check if it matches a preset
            for key, val in PRESETS.items():
                if val["cmd"] == cmd:
                    self.preset_combo.setCurrentText(f"{key} - {val['desc']}")
                    break
        elif cmd_type == "application":
            path = self.edit_data.get("app_path", "")
            self.app_input.setText(path)
        elif cmd_type == "combined":
            self.combined_app_input.setText(self.edit_data.get("app_path", ""))
            self.combined_cmd_input.setText(self.edit_data.get("command", ""))
    
    def get_data(self):
        data = {
            "trigger": self.trigger_input.text(),
            "type": self.type_combo.currentText().lower(),
            "description": self.desc_input.text(),
        }
        
        if data["type"] == "command":
            data["command"] = self.command_input.text()
        elif data["type"] == "application":
            data["app_path"] = self.app_input.text()
        elif data["type"] == "combined":
            data["app_path"] = self.combined_app_input.text()
            data["command"] = self.combined_cmd_input.text()
        
        return data

class CompactVoiceWidget(QMainWindow):
    def __init__(self):
        super().__init__()
        self.commands = {}
        self.load_commands()
        
        # Setup window
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        
        # Size and position (bottom right)
        self.widget_width = 320
        self.widget_height_collapsed = 80
        self.widget_height_expanded = 450
        self.setFixedSize(self.widget_width, self.widget_height_collapsed)
        
        screen = QApplication.primaryScreen().geometry()
        self.move(screen.width() - self.widget_width - 20, 
                 screen.height() - self.widget_height_collapsed - 40)
        
        self.expanded = False
        self.listening = False
        
        # Setup voice recognition
        self.voice_signals = VoiceSignals()
        self.voice_signals.text_detected.connect(self.on_text_detected)
        self.voice_signals.command_executed.connect(self.on_command_executed)
        self.voice_signals.error_occurred.connect(self.on_error)
        self.voice_signals.listening_status.connect(self.on_listening_status)
        
        self.voice_thread = VoiceThread(self.voice_signals, self.commands)
        self.voice_thread.start()
        
        self.setup_ui()
        self.apply_glass_styles()
        self.create_tray_icon()
        
        # Animation timer for waveform
        self.wave_timer = QTimer()
        self.wave_timer.timeout.connect(self.update_waveform)
        self.wave_phase = 0
    
    def setup_ui(self):
        # Central widget with glass effect
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # Main layout
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        self.main_layout.setSpacing(10)
        
        # Header (always visible)
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        # Mic button with waveform effect
        self.mic_btn = QPushButton("🎤")
        self.mic_btn.setFixedSize(50, 50)
        self.mic_btn.setFont(QFont("Segoe UI", 20))
        self.mic_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mic_btn.clicked.connect(self.toggle_listening)
        header_layout.addWidget(self.mic_btn)
        
        # Status text
        self.status_label = QLabel("Click mic to start")
        self.status_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        header_layout.addWidget(self.status_label, stretch=1)
        
        # Expand/collapse button
        self.expand_btn = QPushButton("⚙")
        self.expand_btn.setFixedSize(40, 40)
        self.expand_btn.setFont(QFont("Segoe UI", 14))
        self.expand_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.expand_btn.clicked.connect(self.toggle_expand)
        header_layout.addWidget(self.expand_btn)
        
        self.main_layout.addWidget(header)
        
        # Expanded content
        self.expanded_widget = QWidget()
        expanded_layout = QVBoxLayout(self.expanded_widget)
        expanded_layout.setContentsMargins(0, 0, 0, 0)
        expanded_layout.setSpacing(10)
        
        # Stats
        stats_layout = QHBoxLayout()
        self.count_label = QLabel(f"Commands: {len(self.commands)}")
        self.count_label.setFont(QFont("Segoe UI", 10))
        stats_layout.addWidget(self.count_label)
        
        self.executed_label = QLabel("Executed: 0")
        self.executed_label.setFont(QFont("Segoe UI", 10))
        stats_layout.addWidget(self.executed_label)
        expanded_layout.addLayout(stats_layout)
        
        # Commands list
        self.list_widget = QListWidget()
        self.list_widget.setMaximumHeight(200)
        expanded_layout.addWidget(self.list_widget)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        add_btn = QPushButton("+ Add")
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.clicked.connect(self.add_command)
        btn_layout.addWidget(add_btn)
        
        edit_btn = QPushButton("Edit")
        edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        edit_btn.clicked.connect(self.edit_command)
        btn_layout.addWidget(edit_btn)
        
        del_btn = QPushButton("Delete")
        del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        del_btn.clicked.connect(self.delete_command)
        btn_layout.addWidget(del_btn)
        
        expanded_layout.addLayout(btn_layout)
        
        import_btn = QPushButton("Import/Export JSON")
        import_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        import_btn.clicked.connect(self.show_import_export)
        expanded_layout.addWidget(import_btn)
        
        self.expanded_widget.hide()
        self.main_layout.addWidget(self.expanded_widget)
        
        self.refresh_list()
    
    def apply_glass_styles(self):
        self.setStyleSheet("""
            QMainWindow {
                background: transparent;
            }
            QWidget {
                background: transparent;
                color: #ffffff;
            }
            QPushButton {
                background-color: rgba(233, 69, 96, 0.8);
                color: white;
                border: none;
                border-radius: 25px;
                font-weight: bold;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: rgba(233, 69, 96, 0.95);
            }
            QPushButton:pressed {
                background-color: rgba(200, 50, 70, 0.9);
            }
            QPushButton#mic_btn {
                background-color: rgba(15, 52, 96, 0.8);
                border: 2px solid rgba(233, 69, 96, 0.5);
            }
            QPushButton#mic_btn:hover {
                background-color: rgba(15, 52, 96, 0.95);
                border: 2px solid rgba(233, 69, 96, 0.8);
            }
            QPushButton#mic_btn.active {
                background-color: rgba(233, 69, 96, 0.9);
                border: 2px solid rgba(255, 255, 255, 0.5);
            }
            QListWidget {
                background-color: rgba(22, 33, 62, 0.6);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 10px;
                padding: 5px;
                color: white;
            }
            QListWidget::item {
                background-color: rgba(255, 255, 255, 0.05);
                border-radius: 5px;
                padding: 8px;
                margin: 2px;
            }
            QListWidget::item:selected {
                background-color: rgba(233, 69, 96, 0.6);
            }
            QListWidget::item:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
            QLabel {
                color: rgba(255, 255, 255, 0.9);
            }
            QLineEdit, QTextEdit {
                background-color: rgba(22, 33, 62, 0.8);
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 8px;
                padding: 8px;
                color: white;
            }
            QComboBox {
                background-color: rgba(22, 33, 62, 0.8);
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 8px;
                padding: 8px;
                color: white;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: #16213e;
                color: white;
                selection-background-color: #e94560;
            }
        """)
        
        self.mic_btn.setObjectName("mic_btn")
        
        # Add shadow effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 100))
        shadow.setOffset(0, 5)
        self.central_widget.setGraphicsEffect(shadow)
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Create glass gradient
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0, QColor(26, 26, 46, 220))
        gradient.setColorAt(1, QColor(22, 33, 62, 200))
        
        # Draw rounded rectangle with glass effect
        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(self.rect(), 20, 20)
        
        # Add subtle border
        painter.setPen(QColor(255, 255, 255, 30))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 20, 20)
    
    def create_tray_icon(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setToolTip("Voice Commander")
        
        # Create menu
        tray_menu = QMenu()
        show_action = QAction("Show", self)
        show_action.triggered.connect(self.show)
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.quit_app)
        
        tray_menu.addAction(show_action)
        tray_menu.addSeparator()
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.tray_activated)
        self.tray_icon.show()
    
    def tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show()
    
    def toggle_expand(self):
        self.expanded = not self.expanded
        
        # Animate size change
        target_height = self.widget_height_expanded if self.expanded else self.widget_height_collapsed
        
        self.animation = QPropertyAnimation(self, b"size")
        self.animation.setDuration(300)
        self.animation.setStartValue(self.size())
        self.animation.setEndValue(QSize(self.widget_width, target_height))
        self.animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.animation.start()
        
        if self.expanded:
            self.expanded_widget.show()
            self.expand_btn.setText("−")
            # Move up to accommodate expanded height
            screen = QApplication.primaryScreen().geometry()
            self.move(self.x(), screen.height() - target_height - 40)
        else:
            self.expanded_widget.hide()
            self.expand_btn.setText("⚙")
            screen = QApplication.primaryScreen().geometry()
            self.move(self.x(), screen.height() - self.widget_height_collapsed - 40)
    
    def toggle_listening(self):
        self.listening = not self.listening
        self.voice_thread.toggle_listening(self.listening)
        
        if self.listening:
            self.wave_timer.start(50)
        else:
            self.wave_timer.stop()
            self.status_label.setText("Click mic to start")
            self.mic_btn.setStyleSheet("")
    
    def update_waveform(self):
        if not self.listening:
            return
        
        # Create pulsing effect
        self.wave_phase += 0.2
        intensity = abs((self.wave_phase % 10) - 5) / 5
        
        color_val = int(233 + (255 - 233) * intensity)
        alpha = int(0.8 + 0.2 * intensity)
        
        self.mic_btn.setStyleSheet(f"""
            background-color: rgba({color_val}, 69, 96, {alpha});
            border: 2px solid rgba(255, 255, 255, {0.5 + 0.3 * intensity});
            border-radius: 25px;
        """)
    
    def on_text_detected(self, text):
        self.status_label.setText(text)
    
    def on_command_executed(self, trigger):
        self.status_label.setText(f"✓ Executed: {trigger}")
        current = int(self.executed_label.text().split(": ")[1])
        self.executed_label.setText(f"Executed: {current + 1}")
        
        # Flash success
        QTimer.singleShot(100, lambda: self.setStyleSheet(self.styleSheet() + """
            QMainWindow { border: 2px solid #4ade80; }
        """))
        QTimer.singleShot(300, self.apply_glass_styles)
    
    def on_error(self, error):
        self.status_label.setText(f"Error: {error[:30]}...")
    
    def on_listening_status(self, status):
        if not status:
            self.mic_btn.setStyleSheet("")
    
    def add_command(self):
        dialog = AddCommandDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            if data["trigger"]:
                self.commands[data["trigger"]] = data
                self.save_commands()
                self.refresh_list()
                self.voice_thread.commands = self.commands
    
    def edit_command(self):
        current = self.list_widget.currentItem()
        if not current:
            QMessageBox.warning(self, "Warning", "Please select a command to edit")
            return
        
        trigger = current.data(Qt.ItemDataRole.UserRole)
        if trigger in self.commands:
            dialog = AddCommandDialog(self, self.commands[trigger])
            if dialog.exec() == QDialog.DialogCode.Accepted:
                # Remove old trigger if changed
                new_data = dialog.get_data()
                if new_data["trigger"] != trigger:
                    del self.commands[trigger]
                
                self.commands[new_data["trigger"]] = new_data
                self.save_commands()
                self.refresh_list()
                self.voice_thread.commands = self.commands
    
    def delete_command(self):
        current = self.list_widget.currentItem()
        if not current:
            return
        
        trigger = current.data(Qt.ItemDataRole.UserRole)
        reply = QMessageBox.question(self, "Confirm", f"Delete command '{trigger}'?")
        
        if reply == QMessageBox.StandardButton.Yes:
            del self.commands[trigger]
            self.save_commands()
            self.refresh_list()
            self.voice_thread.commands = self.commands
    
    def refresh_list(self):
        self.list_widget.clear()
        for trigger, data in self.commands.items():
            item = QListWidgetItem()
            desc = data.get("description", "") or data.get("type", "command")
            display = f'"{trigger}"\n  → {desc}'
            item.setText(display)
            item.setData(Qt.ItemDataRole.UserRole, trigger)
            self.list_widget.addItem(item)
        
        self.count_label.setText(f"Commands: {len(self.commands)}")
    
    def show_import_export(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Import/Export")
        dialog.setFixedSize(450, 400)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #1a1a2e;
                color: white;
            }
        """)
        
        layout = QVBoxLayout(dialog)
        
        text_edit = QTextEdit()
        text_edit.setPlaceholderText("Paste JSON here to import, or copy current config from here...")
        text_edit.setText(json.dumps(list(self.commands.values()), indent=2))
        layout.addWidget(text_edit)
        
        btn_layout = QHBoxLayout()
        
        import_btn = QPushButton("Import")
        import_btn.clicked.connect(lambda: self.do_import(text_edit.toPlainText(), dialog))
        btn_layout.addWidget(import_btn)
        
        export_btn = QPushButton("Copy to Clipboard")
        export_btn.clicked.connect(lambda: self.copy_to_clipboard(text_edit.toPlainText()))
        btn_layout.addWidget(export_btn)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.close)
        btn_layout.addWidget(close_btn)
        
        layout.addLayout(btn_layout)
        dialog.exec()
    
    def do_import(self, text, dialog):
        try:
            data = json.loads(text)
            if isinstance(data, list):
                self.commands = {}
                for item in data:
                    if "trigger" in item:
                        self.commands[item["trigger"]] = item
                self.save_commands()
                self.refresh_list()
                self.voice_thread.commands = self.commands
                QMessageBox.information(self, "Success", f"Imported {len(data)} commands")
                dialog.close()
            else:
                raise ValueError("Invalid format")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to import: {str(e)}")
    
    def copy_to_clipboard(self, text):
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        QMessageBox.information(self, "Copied", "Configuration copied to clipboard!")
    
    def load_commands(self):
        if CONFIG_PATH.exists():
            try:
                with open(CONFIG_PATH, 'r') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        self.commands = {item["trigger"]: item for item in data}
                    else:
                        self.commands = data
            except:
                self.commands = {}
        else:
            self.commands = {}
    
    def save_commands(self):
        with open(CONFIG_PATH, 'w') as f:
            json.dump(list(self.commands.values()), f, indent=2)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_pos = event.globalPosition().toPoint()
    
    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.move(self.pos() + event.globalPosition().toPoint() - self.drag_pos)
            self.drag_pos = event.globalPosition().toPoint()
    
    def quit_app(self):
        self.voice_thread.listening = False
        QApplication.quit()
    
    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self.tray_icon.showMessage(
            "Voice Commander",
            "Running in background. Click tray icon to restore.",
            QSystemTrayIcon.MessageIcon.Information,
            2000
        )

def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    
    # Enable high DPI
    app.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    
    widget = CompactVoiceWidget()
    widget.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()