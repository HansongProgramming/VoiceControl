import sys
import json
import os
import subprocess
import threading
import time
from pathlib import Path
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QPushButton, QLabel, QLineEdit, 
                            QComboBox, QListWidget, QListWidgetItem, QMessageBox,
                            QDialog, QTextEdit, QSystemTrayIcon, QMenu, QGraphicsDropShadowEffect,
                            QGraphicsOpacityEffect, QScrollArea, QFrame)
from PyQt6.QtCore import (Qt, QTimer, pyqtSignal, QObject, QSize, QPoint, 
                         QPropertyAnimation, QEasingCurve, QParallelAnimationGroup,
                         QRect, QEasingCurve)
from PyQt6.QtGui import QColor, QIcon, QFont, QPainter, QBrush, QLinearGradient, QPainterPath, QFontDatabase, QAction
import speech_recognition as sr
import pyautogui

# Set High DPI attributes BEFORE creating QApplication
if hasattr(Qt, 'AA_EnableHighDpiScaling'):
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)

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
        self.microphone = None
        self._stop_event = threading.Event()
        
    def run(self):
        # Initialize microphone in thread
        try:
            self.microphone = sr.Microphone()
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
        except Exception as e:
            self.signals.error_occurred.emit(f"Mic init error: {e}")
            return
            
        while not self._stop_event.is_set():
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
            else:
                time.sleep(0.1)
    
    def execute_action(self, action, trigger):
        try:
            cmd_type = action.get("type")
            
            if cmd_type == "command":
                command = action.get("command", "")
                subprocess.Popen(command, shell=True, creationflags=subprocess.CREATE_NEW_CONSOLE)
                    
            elif cmd_type == "application":
                app_path = action.get("app_path", "")
                subprocess.Popen(app_path, shell=True)
                
            elif cmd_type == "combined":
                app_path = action.get("app_path", "")
                subprocess.Popen(app_path, shell=True)
                time.sleep(2)
                command = action.get("command", "")
                if command:
                    subprocess.Popen(command, shell=True, creationflags=subprocess.CREATE_NEW_CONSOLE)
            
            self.signals.command_executed.emit(trigger)
            
        except Exception as e:
            self.signals.error_occurred.emit(f"Execution error: {e}")
    
    def toggle_listening(self, state):
        self.listening = state
        self.signals.listening_status.emit(state)
    
    def stop(self):
        self._stop_event.set()

class AddCommandDialog(QDialog):
    def __init__(self, parent=None, edit_data=None):
        super().__init__(parent)
        self.edit_data = edit_data
        self.setWindowTitle("Voice Commander - Add Command" if not edit_data else "Voice Commander - Edit Command")
        self.setFixedSize(420, 520)
        self.setup_ui()
        self.apply_styles()
        
        if edit_data:
            self.load_data()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        header = QLabel("Configure Voice Command")
        header.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)
        
        # Trigger phrase
        layout.addWidget(QLabel("Voice Trigger Phrase:"))
        self.trigger_input = QLineEdit()
        self.trigger_input.setPlaceholderText("e.g., 'wake up its time to work'")
        layout.addWidget(self.trigger_input)
        
        # Action Type
        layout.addWidget(QLabel("Action Type:"))
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Command", "Application", "Combined"])
        self.type_combo.currentTextChanged.connect(self.on_type_changed)
        layout.addWidget(self.type_combo)
        
        # Stacked widget for different types
        self.type_container = QFrame()
        type_layout = QVBoxLayout(self.type_container)
        type_layout.setContentsMargins(0, 0, 0, 0)
        type_layout.setSpacing(8)
        
        # Command Section
        self.command_widget = QWidget()
        cmd_layout = QVBoxLayout(self.command_widget)
        cmd_layout.setContentsMargins(0, 0, 0, 0)
        cmd_layout.setSpacing(8)
        
        preset_label = QLabel("Quick Select:")
        preset_label.setStyleSheet("color: #888; font-size: 11px;")
        cmd_layout.addWidget(preset_label)
        
        self.preset_combo = QComboBox()
        self.preset_combo.addItem("Custom Command")
        self.preset_combo.addItems([f"{k} - {v['desc']}" for k, v in PRESETS.items()])
        self.preset_combo.currentTextChanged.connect(self.on_preset_changed)
        cmd_layout.addWidget(self.preset_combo)
        
        cmd_layout.addWidget(QLabel("Command:"))
        self.command_input = QLineEdit()
        self.command_input.setPlaceholderText("Enter command to execute...")
        cmd_layout.addWidget(self.command_input)
        
        type_layout.addWidget(self.command_widget)
        
        # Application Section
        self.app_widget = QWidget()
        app_layout = QVBoxLayout(self.app_widget)
        app_layout.setContentsMargins(0, 0, 0, 0)
        app_layout.setSpacing(8)
        
        app_preset_label = QLabel("Quick Select:")
        app_preset_label.setStyleSheet("color: #888; font-size: 11px;")
        app_layout.addWidget(app_preset_label)
        
        self.app_preset_combo = QComboBox()
        self.app_preset_combo.addItem("Custom Application")
        self.app_preset_combo.addItems([f"{k} - {v}" for k, v in APP_PRESETS.items()])
        self.app_preset_combo.currentTextChanged.connect(self.on_app_preset_changed)
        app_layout.addWidget(self.app_preset_combo)
        
        app_layout.addWidget(QLabel("Application Path:"))
        self.app_input = QLineEdit()
        self.app_input.setPlaceholderText("Path to executable...")
        app_layout.addWidget(self.app_input)
        
        type_layout.addWidget(self.app_widget)
        self.app_widget.hide()
        
        # Combined Section
        self.combined_widget = QWidget()
        combined_layout = QVBoxLayout(self.combined_widget)
        combined_layout.setContentsMargins(0, 0, 0, 0)
        combined_layout.setSpacing(8)
        
        combined_layout.addWidget(QLabel("Application to Open:"))
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
        self.combined_cmd_input.setPlaceholderText("Command executed after app opens...")
        combined_layout.addWidget(self.combined_cmd_input)
        
        delay_info = QLabel("Tip: App opens first, waits 2s, then runs command")
        delay_info.setStyleSheet("color: #666; font-size: 10px; font-style: italic;")
        combined_layout.addWidget(delay_info)
        
        type_layout.addWidget(self.combined_widget)
        self.combined_widget.hide()
        
        layout.addWidget(self.type_container)
        
        # Description
        layout.addWidget(QLabel("Description (optional):"))
        self.desc_input = QLineEdit()
        self.desc_input.setPlaceholderText("What this command does...")
        layout.addWidget(self.desc_input)
        
        layout.addStretch()
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("cancel_btn")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)
        
        self.save_btn = QPushButton("Save Command")
        self.save_btn.setObjectName("save_btn")
        self.save_btn.clicked.connect(self.accept)
        self.save_btn.setDefault(True)
        btn_layout.addWidget(self.save_btn)
        
        layout.addLayout(btn_layout)
    
    def apply_styles(self):
        self.setStyleSheet("""
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
        """)
    
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
            self.command_input.setStyleSheet("")
        else:
            key = text.split(" - ")[0]
            if key in PRESETS:
                self.command_input.setText(PRESETS[key]["cmd"])
                self.command_input.setEnabled(False)
                self.command_input.setStyleSheet("color: #888;")
    
    def on_app_preset_changed(self, text):
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
    
    def on_combined_app_changed(self, text):
        if text == "Custom":
            self.combined_app_input.setEnabled(True)
            self.combined_app_input.setText("")
            self.combined_app_input.setStyleSheet("")
        else:
            self.combined_app_input.setEnabled(False)
            self.combined_app_input.setText(APP_PRESETS.get(text, ""))
            self.combined_app_input.setStyleSheet("color: #888;")
    
    def load_data(self):
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
    
    def get_data(self):
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

class CompactVoiceWidget(QMainWindow):
    def __init__(self):
        super().__init__()
        self.commands = {}
        self.load_commands()
        
        # Window setup - use Tool tip for cleaner look, but not layered for stability
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool |
            Qt.WindowType.MSWindowsFixedSizeDialogHint
        )
        
        # Size and position
        self.widget_width = 300
        self.widget_height_collapsed = 70
        self.widget_height_expanded = 420
        
        self.setFixedSize(self.widget_width, self.widget_height_collapsed)
        
        # Position in bottom-right corner
        screen = QApplication.primaryScreen().availableGeometry()
        self.target_x = screen.width() - self.widget_width - 20
        self.target_y_collapsed = screen.height() - self.widget_height_collapsed - 20
        self.target_y_expanded = screen.height() - self.widget_height_expanded - 20
        
        self.move(self.target_x, self.target_y_collapsed)
        
        self.expanded = False
        self.listening = False
        self.dragging = False
        self.drag_position = None
        
        # Setup voice recognition
        self.voice_signals = VoiceSignals()
        self.voice_signals.text_detected.connect(self.on_text_detected)
        self.voice_signals.command_executed.connect(self.on_command_executed)
        self.voice_signals.error_occurred.connect(self.on_error)
        self.voice_signals.listening_status.connect(self.on_listening_status)
        
        self.voice_thread = VoiceThread(self.voice_signals, self.commands)
        self.voice_thread.start()
        
        self.setup_ui()
        self.apply_styles()
        self.create_tray_icon()
        
        # Animation timers
        self.pulse_timer = QTimer()
        self.pulse_timer.timeout.connect(self.update_pulse)
        self.pulse_value = 0
        
        # Hide error timer
        self.error_timer = QTimer()
        self.error_timer.timeout.connect(self.clear_error)
        self.error_timer.setSingleShot(True)
    
    def setup_ui(self):
        # Central widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # Main layout
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(12, 12, 12, 12)
        self.main_layout.setSpacing(8)
        
        # Header (always visible)
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(10)
        
        # Mic button with custom styling
        self.mic_btn = QPushButton("🎤")
        self.mic_btn.setFixedSize(46, 46)
        self.mic_btn.setFont(QFont("Segoe UI Emoji", 18))
        self.mic_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mic_btn.clicked.connect(self.toggle_listening)
        self.mic_btn.setToolTip("Click to start/stop listening")
        header_layout.addWidget(self.mic_btn)
        
        # Text container
        text_container = QWidget()
        text_layout = QVBoxLayout(text_container)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(2)
        
        # Status text
        self.status_label = QLabel("Ready")
        self.status_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        text_layout.addWidget(self.status_label)
        
        # Subtitle
        self.subtitle_label = QLabel("Click mic to listen")
        self.subtitle_label.setFont(QFont("Segoe UI", 9))
        self.subtitle_label.setStyleSheet("color: #888;")
        text_layout.addWidget(self.subtitle_label)
        
        header_layout.addWidget(text_container, stretch=1)
        
        # Expand button
        self.expand_btn = QPushButton("⋮")
        self.expand_btn.setFixedSize(36, 36)
        self.expand_btn.setFont(QFont("Segoe UI", 14))
        self.expand_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.expand_btn.clicked.connect(self.toggle_expand)
        self.expand_btn.setToolTip("Settings")
        header_layout.addWidget(self.expand_btn)
        
        self.main_layout.addWidget(header)
        
        # Separator
        self.separator = QFrame()
        self.separator.setFrameShape(QFrame.Shape.HLine)
        self.separator.setStyleSheet("color: #333;")
        self.separator.hide()
        self.main_layout.addWidget(self.separator)
        
        # Expanded content container
        self.expanded_container = QWidget()
        expanded_layout = QVBoxLayout(self.expanded_container)
        expanded_layout.setContentsMargins(0, 0, 0, 0)
        expanded_layout.setSpacing(10)
        
        # Stats row
        stats_widget = QWidget()
        stats_layout = QHBoxLayout(stats_widget)
        stats_layout.setContentsMargins(0, 0, 0, 0)
        
        self.count_label = QLabel(f"📋 {len(self.commands)} commands")
        self.count_label.setFont(QFont("Segoe UI", 10))
        stats_layout.addWidget(self.count_label)
        
        self.executed_label = QLabel("✓ 0 executed")
        self.executed_label.setFont(QFont("Segoe UI", 10))
        self.executed_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        stats_layout.addWidget(self.executed_label)
        
        expanded_layout.addWidget(stats_widget)
        
        # Commands list with scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        
        self.list_widget = QListWidget()
        self.list_widget.setMaximumHeight(180)
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(self.list_widget)
        expanded_layout.addWidget(scroll)
        
        # Action buttons
        btn_widget = QWidget()
        btn_layout = QHBoxLayout(btn_widget)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(6)
        
        add_btn = QPushButton("+ Add")
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.clicked.connect(self.add_command)
        add_btn.setToolTip("Add new voice command")
        btn_layout.addWidget(add_btn)
        
        edit_btn = QPushButton("✎ Edit")
        edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        edit_btn.clicked.connect(self.edit_command)
        edit_btn.setToolTip("Edit selected command")
        btn_layout.addWidget(edit_btn)
        
        del_btn = QPushButton("🗑")
        del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        del_btn.clicked.connect(self.delete_command)
        del_btn.setToolTip("Delete selected command")
        del_btn.setFixedWidth(40)
        btn_layout.addWidget(del_btn)
        
        expanded_layout.addWidget(btn_widget)
        
        # Import/Export
        import_btn = QPushButton("📁 Import/Export")
        import_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        import_btn.clicked.connect(self.show_import_export)
        import_btn.setStyleSheet("""
            QPushButton {
                background-color: #2a2a3e;
                font-size: 11px;
            }
        """)
        expanded_layout.addWidget(import_btn)
        
        self.expanded_container.hide()
        self.main_layout.addWidget(self.expanded_container)
        
        self.refresh_list()
    
    def apply_styles(self):
        self.setStyleSheet("""
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
            QPushButton#mic_btn:listening {
                background-color: #e94560;
                border: 2px solid #ff5577;
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
        """)
        
        self.mic_btn.setObjectName("mic_btn")
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw rounded rectangle background
        path = QPainterPath()
        path.addRoundedRect(self.rect().adjusted(1, 1, -1, -1), 16, 16)
        
        # Gradient background
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0, QColor(15, 15, 30, 250))
        gradient.setColorAt(1, QColor(10, 10, 20, 250))
        
        painter.fillPath(path, QBrush(gradient))
        
        # Border
        painter.setPen(QColor(42, 42, 78, 200))
        painter.drawPath(path)
    
    def create_tray_icon(self):
        self.tray_icon = QSystemTrayIcon(self)
        
        # Create a simple icon programmatically
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(233, 69, 96))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(4, 4, 56, 56)
        # Draw mic symbol
        painter.setBrush(QColor(255, 255, 255))
        painter.drawRoundedRect(28, 20, 8, 20, 2, 2)
        painter.drawEllipse(24, 36, 16, 12)
        painter.end()
        icon = QIcon(pixmap)
        
        self.tray_icon.setIcon(icon)
        self.tray_icon.setToolTip("Voice Commander - Ready")
        
        tray_menu = QMenu()
        show_action = QAction("Show/Hide", self)
        show_action.triggered.connect(self.toggle_visibility)
        
        listen_action = QAction("Start Listening", self)
        listen_action.triggered.connect(self.toggle_listening)
        
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.quit_app)
        
        tray_menu.addAction(show_action)
        tray_menu.addAction(listen_action)
        tray_menu.addSeparator()
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.tray_activated)
        self.tray_icon.show()
    
    def tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.toggle_visibility()
    
    def toggle_visibility(self):
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.raise_()
            self.activateWindow()
    
    def toggle_expand(self):
        self.expanded = not self.expanded
        
        # Animate geometry change
        self.anim = QPropertyAnimation(self, b"geometry")
        self.anim.setDuration(250)
        self.anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        
        current_geo = self.geometry()
        
        if self.expanded:
            target_y = self.target_y_expanded
            target_height = self.widget_height_expanded
            self.expand_btn.setText("−")
            self.separator.show()
            self.expanded_container.show()
        else:
            target_y = self.target_y_collapsed
            target_height = self.widget_height_collapsed
            self.expand_btn.setText("⋮")
            self.separator.hide()
            self.expanded_container.hide()
        
        new_geo = QRect(self.target_x, target_y, self.widget_width, target_height)
        self.anim.setStartValue(current_geo)
        self.anim.setEndValue(new_geo)
        self.anim.start()
    
    def toggle_listening(self):
        self.listening = not self.listening
        self.voice_thread.toggle_listening(self.listening)
        
        if self.listening:
            self.mic_btn.setStyleSheet("""
                background-color: #e94560;
                border: 2px solid #ff5577;
                border-radius: 23px;
            """)
            self.status_label.setText("Listening...")
            self.subtitle_label.setText("Say your command")
            self.pulse_timer.start(30)
            if self.tray_icon:
                self.tray_icon.setToolTip("Voice Commander - Listening...")
        else:
            self.mic_btn.setStyleSheet("")
            self.status_label.setText("Ready")
            self.subtitle_label.setText("Click mic to listen")
            self.pulse_timer.stop()
            if self.tray_icon:
                self.tray_icon.setToolTip("Voice Commander - Ready")
    
    def update_pulse(self):
        if not self.listening:
            return
        
        self.pulse_value = (self.pulse_value + 1) % 60
        intensity = abs(self.pulse_value - 30) / 30
        
        # Subtle glow effect
        glow = int(233 + (255 - 233) * intensity)
        self.mic_btn.setStyleSheet(f"""
            background-color: #e94560;
            border: 2px solid rgb({glow}, 85, 119);
            border-radius: 23px;
        """)
    
    def on_text_detected(self, text):
        self.status_label.setText(text[:25] + "..." if len(text) > 25 else text)
        if "Heard:" in text:
            self.subtitle_label.setStyleSheet("color: #e94560;")
        else:
            self.subtitle_label.setStyleSheet("color: #888;")
    
    def on_command_executed(self, trigger):
        self.status_label.setText(f"✓ Done!")
        self.subtitle_label.setText(f"Executed: {trigger[:20]}...")
        self.subtitle_label.setStyleSheet("color: #4ade80;")
        
        current = int(self.executed_label.text().split()[1])
        self.executed_label.setText(f"✓ {current + 1} executed")
        
        # Flash effect
        QTimer.singleShot(100, lambda: self.setStyleSheet(self.styleSheet() + "QMainWindow { border: 2px solid #4ade80; }"))
        QTimer.singleShot(400, lambda: self.setStyleSheet(self.styleSheet().replace("QMainWindow { border: 2px solid #4ade80; }", "")))
        
        # Reset after delay
        QTimer.singleShot(2000, lambda: self.subtitle_label.setStyleSheet("color: #888;") if not self.listening else None)
    
    def on_error(self, error):
        self.status_label.setText("⚠ Error")
        self.subtitle_label.setText(error[:30] + "..." if len(error) > 30 else error)
        self.subtitle_label.setStyleSheet("color: #ff4444;")
        self.error_timer.start(3000)
    
    def clear_error(self):
        if not self.listening:
            self.status_label.setText("Ready")
            self.subtitle_label.setText("Click mic to listen")
            self.subtitle_label.setStyleSheet("color: #888;")
    
    def on_listening_status(self, status):
        if not status and not self.listening:
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
            QMessageBox.warning(self, "Voice Commander", "Please select a command to edit")
            return
        
        trigger = current.data(Qt.ItemDataRole.UserRole)
        if trigger in self.commands:
            dialog = AddCommandDialog(self, self.commands[trigger])
            if dialog.exec() == QDialog.DialogCode.Accepted:
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
        
        msg = QMessageBox(self)
        msg.setWindowTitle("Voice Commander")
        msg.setText(f"Delete command '{trigger}'?")
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg.setDefaultButton(QMessageBox.StandardButton.No)
        msg.setStyleSheet("""
            QMessageBox {
                background-color: #0f0f1e;
                color: white;
            }
            QPushButton {
                background-color: #e94560;
                color: white;
                padding: 8px 16px;
                border-radius: 6px;
            }
        """)
        
        if msg.exec() == QMessageBox.StandardButton.Yes:
            del self.commands[trigger]
            self.save_commands()
            self.refresh_list()
            self.voice_thread.commands = self.commands
    
    def refresh_list(self):
        self.list_widget.clear()
        for trigger, data in self.commands.items():
            item = QListWidgetItem()
            desc = data.get("description", "") or f"{data.get('type', 'command').title()} action"
            display = f'"{trigger}"\n  → {desc}'
            item.setText(display)
            item.setData(Qt.ItemDataRole.UserRole, trigger)
            item.setToolTip(f"Type: {data.get('type', 'unknown')}")
            self.list_widget.addItem(item)
        
        self.count_label.setText(f"📋 {len(self.commands)} commands")
    
    def show_import_export(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Voice Commander - Import/Export")
        dialog.setFixedSize(480, 450)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #0f0f1e;
                color: white;
                border: 1px solid #e94560;
            }
            QTextEdit {
                background-color: #1a1a2e;
                color: #4ade80;
                border: 1px solid #2a2a3e;
                border-radius: 8px;
                padding: 10px;
                font-family: Consolas, monospace;
                font-size: 11px;
            }
        """)
        
        layout = QVBoxLayout(dialog)
        layout.setSpacing(12)
        
        header = QLabel("Configuration JSON")
        header.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)
        
        info = QLabel("Copy this to backup, or paste to restore:")
        info.setStyleSheet("color: #888;")
        layout.addWidget(info)
        
        text_edit = QTextEdit()
        text_edit.setPlaceholderText("Paste JSON here to import...")
        text_edit.setText(json.dumps(list(self.commands.values()), indent=2))
        layout.addWidget(text_edit)
        
        btn_layout = QHBoxLayout()
        
        import_btn = QPushButton("📥 Import from Text")
        import_btn.clicked.connect(lambda: self.do_import(text_edit.toPlainText(), dialog))
        btn_layout.addWidget(import_btn)
        
        copy_btn = QPushButton("📋 Copy to Clipboard")
        copy_btn.clicked.connect(lambda: self.copy_to_clipboard(text_edit.toPlainText()))
        btn_layout.addWidget(copy_btn)
        
        close_btn = QPushButton("Close")
        close_btn.setStyleSheet("background-color: #2a2a3e;")
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
                
                msg = QMessageBox(self)
                msg.setWindowTitle("Voice Commander")
                msg.setText(f"Successfully imported {len(data)} commands!")
                msg.setStyleSheet("""
                    QMessageBox { background-color: #0f0f1e; color: white; }
                    QPushButton { background-color: #e94560; color: white; padding: 8px 16px; border-radius: 6px; }
                """)
                msg.exec()
                
                dialog.close()
            else:
                raise ValueError("Invalid format - expected a list")
        except Exception as e:
            msg = QMessageBox(self)
            msg.setWindowTitle("Voice Commander")
            msg.setText(f"Import failed: {str(e)}")
            msg.setIcon(QMessageBox.Icon.Critical)
            msg.setStyleSheet("""
                QMessageBox { background-color: #0f0f1e; color: white; }
                QPushButton { background-color: #e94560; color: white; padding: 8px 16px; border-radius: 6px; }
            """)
            msg.exec()
    
    def copy_to_clipboard(self, text):
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        
        msg = QMessageBox(self)
        msg.setWindowTitle("Voice Commander")
        msg.setText("Configuration copied to clipboard!")
        msg.setStyleSheet("""
            QMessageBox { background-color: #0f0f1e; color: white; }
            QPushButton { background-color: #e94560; color: white; padding: 8px 16px; border-radius: 6px; }
        """)
        msg.exec()
    
    def load_commands(self):
        if CONFIG_PATH.exists():
            try:
                with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        self.commands = {item["trigger"]: item for item in data}
                    else:
                        self.commands = data
            except Exception as e:
                print(f"Error loading config: {e}")
                self.commands = {}
        else:
            self.commands = {}
    
    def save_commands(self):
        try:
            with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
                json.dump(list(self.commands.values()), f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving config: {e}")
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = True
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
    
    def mouseMoveEvent(self, event):
        if self.dragging and event.buttons() == Qt.MouseButton.LeftButton:
            new_pos = event.globalPosition().toPoint() - self.drag_position
            # Keep within screen bounds
            screen = QApplication.primaryScreen().availableGeometry()
            new_x = max(0, min(new_pos.x(), screen.width() - self.width()))
            new_y = max(0, min(new_pos.y(), screen.height() - self.height()))
            self.move(new_x, new_y)
            # Update target positions
            self.target_x = new_x
            if self.expanded:
                self.target_y_expanded = new_y
            else:
                self.target_y_collapsed = new_y
            event.accept()
    
    def mouseReleaseEvent(self, event):
        self.dragging = False
    
    def quit_app(self):
        self.voice_thread.stop()
        self.voice_thread.join(timeout=1)
        QApplication.quit()
    
    def closeEvent(self, event):
        event.ignore()
        self.hide()
        if self.tray_icon:
            self.tray_icon.showMessage(
                "Voice Commander",
                "Running in background. Click tray icon to restore.",
                QSystemTrayIcon.MessageIcon.Information,
                2000
            )

def main():
    # Create application
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    
    # Set application font
    font = QFont("Segoe UI", 9)
    font.setStyleHint(QFont.StyleHint.SansSerif)
    app.setFont(font)
    
    # Create and show widget
    widget = CompactVoiceWidget()
    widget.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()