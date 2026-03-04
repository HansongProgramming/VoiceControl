import subprocess
import threading
import time

import speech_recognition as sr
from PyQt6.QtCore import QObject, pyqtSignal


class VoiceSignals(QObject):
    text_detected = pyqtSignal(str)
    command_executed = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    listening_status = pyqtSignal(bool)


class VoiceThread(threading.Thread):
    def __init__(self, signals: VoiceSignals, commands_dict: dict):
        super().__init__(daemon=True)
        self.signals = signals
        self.commands = commands_dict
        self.listening = False
        self.recognizer = sr.Recognizer()
        self.microphone: sr.Microphone | None = None
        self._stop_event = threading.Event()

    # ---------------------------------------------------------------- run --

    def run(self):
        try:
            self.microphone = sr.Microphone()
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
        except Exception as e:
            self.signals.error_occurred.emit(f"Mic init error: {e}")
            return

        while not self._stop_event.is_set():
            if self.listening:
                self._listen_once()
            else:
                time.sleep(0.1)

    def _listen_once(self):
        try:
            with self.microphone as source:
                self.signals.text_detected.emit("Listening...")
                audio = self.recognizer.listen(source, timeout=1, phrase_time_limit=5)

            text = self.recognizer.recognize_google(audio).lower()
            self.signals.text_detected.emit(f"Heard: {text}")

            for trigger, action in self.commands.items():
                if trigger.lower() in text:
                    self._execute_action(action, trigger)
                    break

        except sr.WaitTimeoutError:
            pass
        except sr.UnknownValueError:
            pass
        except sr.RequestError as e:
            self.signals.error_occurred.emit(f"Speech error: {e}")
        except Exception as e:
            self.signals.error_occurred.emit(str(e))

    # ------------------------------------------------------------ execute --

    def _execute_action(self, action: dict, trigger: str):
        try:
            cmd_type = action.get("type")

            if cmd_type == "command":
                subprocess.Popen(
                    action.get("command", ""),
                    shell=True,
                    creationflags=subprocess.CREATE_NEW_CONSOLE,
                )

            elif cmd_type == "application":
                subprocess.Popen(action.get("app_path", ""), shell=True)

            elif cmd_type == "combined":
                subprocess.Popen(action.get("app_path", ""), shell=True)
                time.sleep(2)
                cmd = action.get("command", "")
                if cmd:
                    subprocess.Popen(
                        cmd,
                        shell=True,
                        creationflags=subprocess.CREATE_NEW_CONSOLE,
                    )

            self.signals.command_executed.emit(trigger)

        except Exception as e:
            self.signals.error_occurred.emit(f"Execution error: {e}")

    # ---------------------------------------------------------------- API --

    def toggle_listening(self, state: bool):
        self.listening = state
        self.signals.listening_status.emit(state)

    def stop(self):
        self._stop_event.set()
