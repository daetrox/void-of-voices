"""Void of Voices: cambia tu voz en tiempo real y lánzala como micrófono virtual."""

import json
import os
import shutil
import sys
from pathlib import Path

__version__ = "0.2.2"

APP_NAME = "Void of Voices"
APP_ID = "io.github.daetrox.VoidOfVoices"
REPO_URL = "https://github.com/daetrox/void-of-voices"

IS_WINDOWS = sys.platform == "win32"
IS_LINUX = sys.platform.startswith("linux")

# En Linux el micrófono virtual lo crea la app; en Windows es VB-Cable.
MIC_NAME = "VoidOfVoices_Mic" if not IS_WINDOWS else "CABLE Output (VB-Audio)"

if IS_WINDOWS:
    _base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")) / "VoidOfVoices"
    CONFIG_DIR = _base
    DATA_DIR = _base
else:
    CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "voidofvoices"
    DATA_DIR = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "voidofvoices"
CONFIG_FILE = CONFIG_DIR / "config.json"

# Recursos (sonidos, icono): junto al paquete o dentro del ejecutable de PyInstaller.
RESOURCE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
ICON_PATH = RESOURCE_DIR / "voidofvoices" / "assets" / "icon.svg"
# Emojis propios: Qt no dibuja el Noto Color Emoji COLRv1 de Fedora y otras distros
# recientes (los iconos salían en blanco).
EMOJI_FONT = RESOURCE_DIR / "voidofvoices" / "assets" / "Twemoji.Mozilla.ttf"

# Nombres anteriores de la app (Vozcándalo, Audiomodulator): (carpeta de config, carpeta de datos).
if IS_WINDOWS:
    _LEGACY = [(_base.parent / "Vozcandalo", _base.parent / "Vozcandalo")]
else:
    _LEGACY = [(CONFIG_DIR.parent / n, DATA_DIR.parent / n) for n in ("vozcandalo", "audiomodulator")]


def migrate_legacy():
    """Trae la configuración y los sonidos de versiones con el nombre anterior."""
    if CONFIG_FILE.exists():
        return
    for old_cfg_dir, old_data in _LEGACY:
        old_cfg = old_cfg_dir / "config.json"
        if not old_cfg.exists():
            continue
        try:
            cfg = json.loads(old_cfg.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if (old_data / "sounds").exists() and not (DATA_DIR / "sounds").exists():
            shutil.copytree(old_data / "sounds", DATA_DIR / "sounds")
        for u in cfg.get("user_sounds", []):
            u["path"] = u["path"].replace(str(old_data), str(DATA_DIR))
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
        return
