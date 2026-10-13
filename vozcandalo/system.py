"""Integración con el escritorio: menú de aplicaciones e inicio con el sistema."""

import os
import shlex
import shutil
import sys
from pathlib import Path

from . import APP_ID, APP_NAME, ICON_PATH, IS_WINDOWS, RESOURCE_DIR


def launch_command():
    """Orden para volver a abrir la app (AppImage, ejecutable o código fuente)."""
    if os.environ.get("APPIMAGE"):
        return [os.environ["APPIMAGE"]]
    if getattr(sys, "frozen", False):
        return [sys.executable]
    run = RESOURCE_DIR / ("run.sh" if not IS_WINDOWS else "main.py")
    return [str(run)] if not IS_WINDOWS else [sys.executable, str(run)]


def _desktop_entry(extra_args=""):
    cmd = " ".join(shlex.quote(c) for c in launch_command())
    return f"""[Desktop Entry]
Type=Application
Name={APP_NAME}
GenericName=Modulador de voz
GenericName[en]=Voice changer
Comment=Cambia tu voz en tiempo real y lanza sonidos
Comment[en]=Change your voice in real time and play sounds
Exec={cmd}{extra_args}
Icon={APP_ID}
Terminal=false
Categories=AudioVideo;Audio;
Keywords=voz;voice;changer;soundboard;micrófono;microphone;
StartupWMClass={APP_ID}
"""


def install_desktop_entry():
    """Instala (o actualiza) el lanzador en el menú de aplicaciones de Linux.
    También es necesario para que el portal de atajos globales reconozca la app."""
    if IS_WINDOWS:
        return
    data = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    icon_dst = data / "icons" / "hicolor" / "scalable" / "apps" / f"{APP_ID}.svg"
    try:
        if ICON_PATH.exists() and (not icon_dst.exists() or icon_dst.read_bytes() != ICON_PATH.read_bytes()):
            icon_dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ICON_PATH, icon_dst)
        dst = data / "applications" / f"{APP_ID}.desktop"
        content = _desktop_entry()
        if not dst.exists() or dst.read_text(encoding="utf-8") != content:
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(content, encoding="utf-8")
    except OSError:
        pass


def _autostart_file():
    cfg = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return cfg / "autostart" / f"{APP_ID}.desktop"


_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def autostart_enabled():
    if IS_WINDOWS:
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY) as k:
                winreg.QueryValueEx(k, "Vozcandalo")
            return True
        except OSError:
            return False
    return _autostart_file().exists()


def set_autostart(enabled):
    """Arranca la app minimizada en la bandeja al iniciar sesión."""
    if IS_WINDOWS:
        import subprocess
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
            if enabled:
                winreg.SetValueEx(k, "Vozcandalo", 0, winreg.REG_SZ,
                                  subprocess.list2cmdline(launch_command() + ["--tray"]))
            else:
                try:
                    winreg.DeleteValue(k, "Vozcandalo")
                except OSError:
                    pass
        return
    f = _autostart_file()
    if enabled:
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(_desktop_entry(" --tray"), encoding="utf-8")
    elif f.exists():
        f.unlink()
