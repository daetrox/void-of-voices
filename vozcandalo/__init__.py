"""Vozcándalo: cambia tu voz en tiempo real y lánzala como micrófono virtual."""

import json
import os
import shutil
import sys
from pathlib import Path

__version__ = "0.2.0"

APP_NAME = "Vozcándalo"
APP_ID = "io.github.daetrox.Vozcandalo"
REPO_URL = "https://github.com/daetrox/vozcandalo"

IS_WINDOWS = sys.platform == "win32"
IS_LINUX = sys.platform.startswith("linux")

# En Linux el micrófono virtual lo crea la app; en Windows es VB-Cable.
MIC_NAME = "Vozcandalo_Mic" if not IS_WINDOWS else "CABLE Output (VB-Audio)"

if IS_WINDOWS:
    _base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")) / "Vozcandalo"
    CONFIG_DIR = _base
    DATA_DIR = _base
else:
    CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "vozcandalo"
    DATA_DIR = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "vozcandalo"
CONFIG_FILE = CONFIG_DIR / "config.json"

# Recursos (sonidos, icono): junto al paquete o dentro del ejecutable de PyInstaller.
RESOURCE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
ICON_PATH = RESOURCE_DIR / "vozcandalo" / "assets" / "icon.svg"

_LEGACY_CONFIG = Path.home() / ".config" / "audiomodulator" / "config.json"
_LEGACY_DATA = Path.home() / ".local" / "share" / "audiomodulator"


def migrate_legacy():
    """Trae la configuración y los sonidos de cuando la app se llamaba Audiomodulator."""
    if not CONFIG_FILE.exists() and _LEGACY_CONFIG.exists():
        try:
            cfg = json.loads(_LEGACY_CONFIG.read_text())
        except (OSError, ValueError):
            return
        if _LEGACY_DATA.exists() and not DATA_DIR.exists():
            shutil.copytree(_LEGACY_DATA, DATA_DIR)
        for u in cfg.get("user_sounds", []):
            u["path"] = u["path"].replace(str(_LEGACY_DATA), str(DATA_DIR))
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(json.dumps(cfg, indent=2, ensure_ascii=False))
