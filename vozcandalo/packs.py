"""Importar y exportar voces (.vzvoice, JSON) y paquetes de sonidos (.vzpack, ZIP)."""

import json
import uuid
import zipfile
from pathlib import Path

from . import __version__
from .dsp import Params, VOICE_KEYS
from .soundboard import IMPORT_EXTS, USER_DIR, load_audio

VOICE_EXT = ".vzvoice"
PACK_EXT = ".vzpack"
_VOICE_TYPE = "vozcandalo-voices"
_PACK_TYPE = "vozcandalo-soundpack"
MAX_PACK_SOUNDS = 300
MAX_SOUND_BYTES = 40 * 1024 * 1024


class PackError(Exception):
    pass


# ------------------------------------------------------------------ voces

def export_voices(path, voices):
    """voices: {nombre: {parámetros de voz}}"""
    data = {"type": _VOICE_TYPE, "version": 1, "app_version": __version__,
            "voices": [{"name": n, "params": {k: v[k] for k in VOICE_KEYS if k in v}}
                       for n, v in voices.items()]}
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False))


def import_voices(path):
    """Devuelve {nombre: parámetros} validados (valores numéricos dentro de rango)."""
    try:
        data = json.loads(Path(path).read_text())
    except (OSError, ValueError) as e:
        raise PackError(str(e))
    if not isinstance(data, dict) or data.get("type") != _VOICE_TYPE:
        raise PackError("no es un archivo de voces de Vozcándalo")
    default = Params()
    out = {}
    for item in data.get("voices", [])[:200]:
        name = str(item.get("name", "")).strip()[:40]
        params = item.get("params", {})
        if not name or not isinstance(params, dict):
            continue
        clean = {}
        for k in VOICE_KEYS:
            v = params.get(k, getattr(default, k))
            try:
                clean[k] = max(-48.0, min(2000.0, float(v)))
            except (TypeError, ValueError):
                clean[k] = getattr(default, k)
        out[name] = clean
    if not out:
        raise PackError("el archivo no contiene voces")
    return out


# ---------------------------------------------------------------- sonidos

def export_sound_pack(path, pack_name, sounds):
    """sounds: lista de dicts {path, name, icon, volume, loop}."""
    manifest = {"type": _PACK_TYPE, "version": 1, "app_version": __version__,
                "name": pack_name, "sounds": []}
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as z:
        for i, s in enumerate(sounds, start=1):
            src = Path(s["path"])
            arc = f"sounds/{i:03d}{src.suffix.lower()}"
            z.write(src, arc)
            manifest["sounds"].append({"file": arc, "name": s["name"], "icon": s.get("icon", "🔊"),
                                       "volume": int(s.get("volume", 100)), "loop": bool(s.get("loop"))})
        z.writestr("manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False))


def import_sound_pack(path):
    """Extrae el paquete a la biblioteca del usuario.

    Devuelve (nombre_del_paquete, [entradas], {id: meta}). Solo lee los archivos
    que nombra el manifiesto, con nombres de destino generados por la app.
    """
    try:
        z = zipfile.ZipFile(path)
    except (OSError, zipfile.BadZipFile) as e:
        raise PackError(str(e))
    with z:
        try:
            manifest = json.loads(z.read("manifest.json"))
        except (KeyError, ValueError):
            raise PackError("falta manifest.json")
        if manifest.get("type") != _PACK_TYPE:
            raise PackError("no es un paquete de sonidos de Vozcándalo")
        pack = str(manifest.get("name") or Path(path).stem).strip()[:40]
        names = set(z.namelist())
        USER_DIR.mkdir(parents=True, exist_ok=True)
        entries, metas, errors = [], {}, []
        for item in manifest.get("sounds", [])[:MAX_PACK_SOUNDS]:
            arc = str(item.get("file", ""))
            ext = Path(arc).suffix.lower()
            if arc not in names or ext not in IMPORT_EXTS:
                errors.append(arc)
                continue
            if z.getinfo(arc).file_size > MAX_SOUND_BYTES:
                errors.append(arc)
                continue
            sid = uuid.uuid4().hex[:10]
            dst = USER_DIR / f"{sid}{ext}"
            dst.write_bytes(z.read(arc))
            try:
                load_audio(dst)
            except Exception:
                dst.unlink(missing_ok=True)
                errors.append(arc)
                continue
            entry = {"id": f"user:{sid}", "path": str(dst),
                     "name": str(item.get("name", sid))[:40], "icon": str(item.get("icon", "🔊"))[:2],
                     "category": pack, "builtin": False}
            entries.append(entry)
            vol = item.get("volume", 100)
            metas[entry["id"]] = {"volume": max(0, min(300, int(vol) if isinstance(vol, (int, float)) else 100)),
                                  "loop": bool(item.get("loop"))}
    if not entries:
        raise PackError("no se pudo importar ningún sonido")
    return pack, entries, metas, errors
