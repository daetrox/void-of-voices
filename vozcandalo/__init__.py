"""Vozcándalo: cambia tu voz en tiempo real y lánzala como micrófono virtual."""

import json
import shutil
from pathlib import Path

__version__ = "0.1.0"

APP_NAME = "Vozcándalo"
APP_ID = "io.github.daetrox.Vozcandalo"
MIC_NAME = "Vozcandalo_Mic"

CONFIG_DIR = Path.home() / ".config" / "vozcandalo"
CONFIG_FILE = CONFIG_DIR / "config.json"
DATA_DIR = Path.home() / ".local" / "share" / "vozcandalo"

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
