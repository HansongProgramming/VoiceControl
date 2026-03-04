from pathlib import Path

CONFIG_PATH = Path.home() / ".voice_commander_config.json"

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
