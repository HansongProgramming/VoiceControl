import json

from PyQt6.QtCore import (
    QEasingCurve,
    QPropertyAnimation,
    QRect,
    QRectF,
    Qt,
    QTimer,
)
from PyQt6.QtGui import (
    QAction,
    QBrush,
    QColor,
    QFont,
    QIcon,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPixmap,
)
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSystemTrayIcon,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app import storage
from app.ui.dialog import AddCommandDialog
from app.ui.styles import IMPORT_EXPORT_STYLE, MAIN_STYLE, MSGBOX_STYLE
from app.voice import VoiceSignals, VoiceThread


class CompactVoiceWidget(QMainWindow):
    def __init__(self):
        super().__init__()

        self.commands = storage.load_commands()
        self._executed_count = 0

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.MSWindowsFixedSizeDialogHint
        )

        self.widget_width = 300
        self.widget_height_collapsed = 70
        self.widget_height_expanded = 420
        self.setFixedSize(self.widget_width, self.widget_height_collapsed)

        screen = QApplication.primaryScreen().availableGeometry()
        self.target_x = screen.width() - self.widget_width - 20
        self.target_y_collapsed = screen.height() - self.widget_height_collapsed - 20
        self.target_y_expanded = screen.height() - self.widget_height_expanded - 20
        self.move(self.target_x, self.target_y_collapsed)

        self.expanded = False
        self.listening = False
        self.dragging = False
        self.drag_position = None

        # Voice engine
        self.voice_signals = VoiceSignals()
        self.voice_signals.text_detected.connect(self._on_text_detected)
        self.voice_signals.command_executed.connect(self._on_command_executed)
        self.voice_signals.error_occurred.connect(self._on_error)
        self.voice_signals.listening_status.connect(self._on_listening_status)

        self.voice_thread = VoiceThread(self.voice_signals, self.commands)
        self.voice_thread.start()

        self._setup_ui()
        self.setStyleSheet(MAIN_STYLE)
        self._create_tray_icon()

        # Pulse animation timer
        self.pulse_timer = QTimer()
        self.pulse_timer.timeout.connect(self._update_pulse)
        self.pulse_value = 0

        # Auto-clear error timer
        self.error_timer = QTimer()
        self.error_timer.timeout.connect(self._clear_error)
        self.error_timer.setSingleShot(True)

    # ------------------------------------------------------------------ UI --

    def _setup_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(12, 12, 12, 12)
        self.main_layout.setSpacing(8)

        # Header (always visible)
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(10)

        self.mic_btn = QPushButton("🎤")
        self.mic_btn.setObjectName("mic_btn")
        self.mic_btn.setFixedSize(46, 46)
        self.mic_btn.setFont(QFont("Segoe UI Emoji", 18))
        self.mic_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mic_btn.clicked.connect(self.toggle_listening)
        self.mic_btn.setToolTip("Click to start/stop listening")
        header_layout.addWidget(self.mic_btn)

        text_container = QWidget()
        text_layout = QVBoxLayout(text_container)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(2)

        self.status_label = QLabel("Ready")
        self.status_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        text_layout.addWidget(self.status_label)

        self.subtitle_label = QLabel("Click mic to listen")
        self.subtitle_label.setFont(QFont("Segoe UI", 9))
        self.subtitle_label.setStyleSheet("color: #888;")
        text_layout.addWidget(self.subtitle_label)

        header_layout.addWidget(text_container, stretch=1)

        self.expand_btn = QPushButton("⋮")
        self.expand_btn.setFixedSize(36, 36)
        self.expand_btn.setFont(QFont("Segoe UI", 14))
        self.expand_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.expand_btn.clicked.connect(self.toggle_expand)
        self.expand_btn.setToolTip("Settings")
        header_layout.addWidget(self.expand_btn)

        self.main_layout.addWidget(header)

        self.separator = QFrame()
        self.separator.setFrameShape(QFrame.Shape.HLine)
        self.separator.setStyleSheet("color: #333;")
        self.separator.hide()
        self.main_layout.addWidget(self.separator)

        # Expanded panel (hidden by default)
        self.expanded_container = QWidget()
        expanded_layout = QVBoxLayout(self.expanded_container)
        expanded_layout.setContentsMargins(0, 0, 0, 0)
        expanded_layout.setSpacing(10)

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

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        self.list_widget = QListWidget()
        self.list_widget.setMaximumHeight(180)
        self.list_widget.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        scroll.setWidget(self.list_widget)
        expanded_layout.addWidget(scroll)

        btn_widget = QWidget()
        btn_layout = QHBoxLayout(btn_widget)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(6)

        add_btn = QPushButton("+ Add")
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.clicked.connect(self._add_command)
        add_btn.setToolTip("Add new voice command")
        btn_layout.addWidget(add_btn)

        edit_btn = QPushButton("✎ Edit")
        edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        edit_btn.clicked.connect(self._edit_command)
        edit_btn.setToolTip("Edit selected command")
        btn_layout.addWidget(edit_btn)

        del_btn = QPushButton("🗑")
        del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        del_btn.clicked.connect(self._delete_command)
        del_btn.setToolTip("Delete selected command")
        del_btn.setFixedWidth(40)
        btn_layout.addWidget(del_btn)
        expanded_layout.addWidget(btn_widget)

        import_btn = QPushButton("📁 Import/Export")
        import_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        import_btn.clicked.connect(self._show_import_export)
        import_btn.setStyleSheet(
            "QPushButton { background-color: #2a2a3e; font-size: 11px; }"
        )
        expanded_layout.addWidget(import_btn)

        self.expanded_container.hide()
        self.main_layout.addWidget(self.expanded_container)

        # Live transcription area
        self.transcript_edit = QTextEdit()
        self.transcript_edit.setReadOnly(True)
        self.transcript_edit.setMaximumHeight(80)
        self.transcript_edit.setStyleSheet("background: #181828; color: #e0e0e0; font-size: 11px; border-radius: 8px;")
        expanded_layout.insertWidget(1, self.transcript_edit)
        self._refresh_list()

    # ------------------------------------------------------- Tray icon --

    def _create_tray_icon(self):
        self.tray_icon = QSystemTrayIcon(self)

        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(233, 69, 96))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(4, 4, 56, 56)
        painter.setBrush(QColor(255, 255, 255))
        painter.drawRoundedRect(28, 20, 8, 20, 2, 2)
        painter.drawEllipse(24, 36, 16, 12)
        painter.end()
        self.tray_icon.setIcon(QIcon(pixmap))
        self.tray_icon.setToolTip("Voice Commander - Ready")

        tray_menu = QMenu()

        show_action = QAction("Show/Hide", self)
        show_action.triggered.connect(self._toggle_visibility)

        listen_action = QAction("Start Listening", self)
        listen_action.triggered.connect(self.toggle_listening)

        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self._quit_app)

        tray_menu.addAction(show_action)
        tray_menu.addAction(listen_action)
        tray_menu.addSeparator()
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._tray_activated)
        self.tray_icon.show()

    # ---------------------------------------------------- Paint / Mouse --

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        path = QPainterPath()
        rect = self.rect().adjusted(1, 1, -1, -1)
        path.addRoundedRect(QRectF(rect), 16, 16)

        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0, QColor(15, 15, 30, 250))
        gradient.setColorAt(1, QColor(10, 10, 20, 250))
        painter.fillPath(path, QBrush(gradient))

        painter.setPen(QColor(42, 42, 78, 200))
        painter.drawPath(path)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = True
            self.drag_position = (
                event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            )
            event.accept()

    def mouseMoveEvent(self, event):
        if self.dragging and event.buttons() == Qt.MouseButton.LeftButton:
            new_pos = event.globalPosition().toPoint() - self.drag_position
            screen = QApplication.primaryScreen().availableGeometry()
            new_x = max(0, min(new_pos.x(), screen.width() - self.width()))
            new_y = max(0, min(new_pos.y(), screen.height() - self.height()))
            self.move(new_x, new_y)
            self.target_x = new_x
            if self.expanded:
                self.target_y_expanded = new_y
            else:
                self.target_y_collapsed = new_y
            event.accept()

    def mouseReleaseEvent(self, event):
        self.dragging = False

    # -------------------------------------------------------- Public API --

    def toggle_listening(self):
        self.listening = not self.listening
        self.voice_thread.toggle_listening(self.listening)

        if self.listening:
            self.mic_btn.setStyleSheet(
                "background-color: #e94560;"
                " border: 2px solid #ff5577;"
                " border-radius: 23px;"
            )
            self.status_label.setText("Listening...")
            self.subtitle_label.setText("Say your command")
            self.pulse_timer.start(30)
            self.tray_icon.setToolTip("Voice Commander - Listening...")
        else:
            self.mic_btn.setStyleSheet("")
            self.status_label.setText("Ready")
            self.subtitle_label.setText("Click mic to listen")
            self.pulse_timer.stop()
            self.tray_icon.setToolTip("Voice Commander - Ready")

    def toggle_expand(self):
        self.expanded = not self.expanded

        self._anim = QPropertyAnimation(self, b"geometry")
        self._anim.setDuration(250)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self._anim.setStartValue(self.geometry())

        if self.expanded:
            target_y = self.target_y_expanded
            target_h = self.widget_height_expanded
            self.expand_btn.setText("−")
            self.separator.show()
            self.expanded_container.show()
        else:
            target_y = self.target_y_collapsed
            target_h = self.widget_height_collapsed
            self.expand_btn.setText("⋮")
            self.separator.hide()
            self.expanded_container.hide()

        self._anim.setEndValue(
            QRect(self.target_x, target_y, self.widget_width, target_h)
        )
        self._anim.start()

    # -------------------------------------------------------- Voice slots --

    def _on_text_detected(self, text: str):
        # Only update transcript area on recognized phrases
        if text.startswith("Heard:"):
            phrase = text[len("Heard:"):].strip()
            if phrase:
                self.transcript_edit.append(phrase)
            self.status_label.setText(phrase[:25] + "..." if len(phrase) > 25 else phrase)
            self.subtitle_label.setStyleSheet("color: #e94560;")
        else:
            # Only update status/subtitle, not transcript
            self.status_label.setText(text[:25] + "..." if len(text) > 25 else text)
            color = "#888"
            self.subtitle_label.setStyleSheet(f"color: {color};")

    def _on_command_executed(self, trigger: str):
        self.status_label.setText("✓ Done!")
        self.subtitle_label.setText(f"Executed: {trigger[:20]}...")
        self.subtitle_label.setStyleSheet("color: #4ade80;")

        self._executed_count += 1
        self.executed_label.setText(f"✓ {self._executed_count} executed")

        base = self.styleSheet()
        QTimer.singleShot(
            100,
            lambda: self.setStyleSheet(
                base + "QMainWindow { border: 2px solid #4ade80; }"
            ),
        )
        QTimer.singleShot(400, lambda: self.setStyleSheet(base))
        QTimer.singleShot(
            2000,
            lambda: self.subtitle_label.setStyleSheet("color: #888;")
            if not self.listening
            else None,
        )

    def _on_error(self, error: str):
        self.status_label.setText("⚠ Error")
        self.subtitle_label.setText(error[:30] + "..." if len(error) > 30 else error)
        self.subtitle_label.setStyleSheet("color: #ff4444;")
        self.error_timer.start(3000)

    def _clear_error(self):
        if not self.listening:
            self.status_label.setText("Ready")
            self.subtitle_label.setText("Click mic to listen")
            self.subtitle_label.setStyleSheet("color: #888;")

    def _on_listening_status(self, status: bool):
        if not status and not self.listening:
            self.mic_btn.setStyleSheet("")

    def _update_pulse(self):
        if not self.listening:
            return
        self.pulse_value = (self.pulse_value + 1) % 60
        intensity = abs(self.pulse_value - 30) / 30
        glow = int(233 + (255 - 233) * intensity)
        self.mic_btn.setStyleSheet(
            f"background-color: #e94560;"
            f" border: 2px solid rgb({glow}, 85, 119);"
            f" border-radius: 23px;"
        )

    # ------------------------------------------------- Command management --

    def _add_command(self):
        dialog = AddCommandDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            if data["trigger"]:
                self.commands[data["trigger"]] = data
                storage.save_commands(self.commands)
                self._refresh_list()
                self.voice_thread.commands = self.commands

    def _edit_command(self):
        current = self.list_widget.currentItem()
        if not current:
            QMessageBox.warning(
                self, "Voice Commander", "Please select a command to edit"
            )
            return

        trigger = current.data(Qt.ItemDataRole.UserRole)
        if trigger not in self.commands:
            return

        dialog = AddCommandDialog(self, self.commands[trigger])
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_data = dialog.get_data()
            if new_data["trigger"] != trigger:
                del self.commands[trigger]
            self.commands[new_data["trigger"]] = new_data
            storage.save_commands(self.commands)
            self._refresh_list()
            self.voice_thread.commands = self.commands

    def _delete_command(self):
        current = self.list_widget.currentItem()
        if not current:
            return

        trigger = current.data(Qt.ItemDataRole.UserRole)
        msg = QMessageBox(self)
        msg.setWindowTitle("Voice Commander")
        msg.setText(f"Delete command '{trigger}'?")
        msg.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        msg.setDefaultButton(QMessageBox.StandardButton.No)
        msg.setStyleSheet(MSGBOX_STYLE)

        if msg.exec() == QMessageBox.StandardButton.Yes:
            del self.commands[trigger]
            storage.save_commands(self.commands)
            self._refresh_list()
            self.voice_thread.commands = self.commands

    def _refresh_list(self):
        self.list_widget.clear()
        for trigger, data in self.commands.items():
            item = QListWidgetItem()
            desc = data.get("description") or f"{data.get('type', 'command').title()} action"
            item.setText(f'"{trigger}"\n  → {desc}')
            item.setData(Qt.ItemDataRole.UserRole, trigger)
            item.setToolTip(f"Type: {data.get('type', 'unknown')}")
            self.list_widget.addItem(item)
        self.count_label.setText(f"📋 {len(self.commands)} commands")

    # ------------------------------------------------------ Import/Export --

    def _show_import_export(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Voice Commander - Import/Export")
        dialog.setFixedSize(480, 450)
        dialog.setStyleSheet(IMPORT_EXPORT_STYLE)

        layout = QVBoxLayout(dialog)
        layout.setSpacing(12)

        header = QLabel("Configuration JSON")
        header.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)

        info = QLabel("Copy this to backup, or paste to restore:")
        layout.addWidget(info)

        text_edit = QTextEdit()
        text_edit.setPlaceholderText("Paste JSON here to import...")
        text_edit.setText(json.dumps(list(self.commands.values()), indent=2))
        layout.addWidget(text_edit)

        btn_layout = QHBoxLayout()

        import_btn = QPushButton("📥 Import from Text")
        import_btn.clicked.connect(
            lambda: self._do_import(text_edit.toPlainText(), dialog)
        )
        btn_layout.addWidget(import_btn)

        copy_btn = QPushButton("📋 Copy to Clipboard")
        copy_btn.clicked.connect(
            lambda: self._copy_to_clipboard(text_edit.toPlainText())
        )
        btn_layout.addWidget(copy_btn)

        close_btn = QPushButton("Close")
        close_btn.setObjectName("close_btn")
        close_btn.clicked.connect(dialog.close)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)
        dialog.exec()

    def _do_import(self, text: str, dialog: QDialog):
        try:
            data = json.loads(text)
            if not isinstance(data, list):
                raise ValueError("Expected a JSON list")
            self.commands = {
                item["trigger"]: item for item in data if "trigger" in item
            }
            storage.save_commands(self.commands)
            self._refresh_list()
            self.voice_thread.commands = self.commands

            msg = QMessageBox(self)
            msg.setWindowTitle("Voice Commander")
            msg.setText(f"Successfully imported {len(data)} commands!")
            msg.setStyleSheet(MSGBOX_STYLE)
            msg.exec()
            dialog.close()

        except Exception as e:
            msg = QMessageBox(self)
            msg.setWindowTitle("Voice Commander")
            msg.setText(f"Import failed: {e}")
            msg.setIcon(QMessageBox.Icon.Critical)
            msg.setStyleSheet(MSGBOX_STYLE)
            msg.exec()

    def _copy_to_clipboard(self, text: str):
        QApplication.clipboard().setText(text)
        msg = QMessageBox(self)
        msg.setWindowTitle("Voice Commander")
        msg.setText("Configuration copied to clipboard!")
        msg.setStyleSheet(MSGBOX_STYLE)
        msg.exec()

    # --------------------------------------------------------- Tray / App --

    def _tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._toggle_visibility()

    def _toggle_visibility(self):
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.raise_()
            self.activateWindow()

    def _quit_app(self):
        self.voice_thread.stop()
        self.voice_thread.join(timeout=1)
        QApplication.quit()

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self.tray_icon.showMessage(
            "Voice Commander",
            "Running in background. Click tray icon to restore.",
            QSystemTrayIcon.MessageIcon.Information,
            2000,
        )
