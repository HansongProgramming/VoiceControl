import os
import sys

# Suppress the benign "SetProcessDpiAwarenessContext() failed" warning that
# appears when a parent process (UAC / terminal) has already set DPI awareness
# before Qt gets a chance to do so.
os.environ.setdefault("QT_LOGGING_RULES", "qt.qpa.window=false")

from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication

from app.ui.widget import CompactVoiceWidget


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    font = QFont("Segoe UI", 9)
    font.setStyleHint(QFont.StyleHint.SansSerif)
    app.setFont(font)

    widget = CompactVoiceWidget()
    widget.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
