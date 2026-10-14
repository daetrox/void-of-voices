"""Soundboard: biblioteca de sonidos y mezclador que se suma al micrófono virtual."""

import hashlib
import json
import shutil
import threading
import uuid
from pathlib import Path

import numpy as np
from pedalboard.io import AudioFile

from . import DATA_DIR, ICON_IMAGE_EXTS, MAX_ICON_BYTES, RESOURCE_DIR, USER_ICON_DIR
from .dsp import SAMPLE_RATE

BUILTIN_DIR = RESOURCE_DIR / "sounds"
USER_DIR = DATA_DIR / "sounds"
IMPORT_EXTS = (".wav", ".mp3", ".ogg", ".flac", ".aiff", ".aif")
MAX_SECONDS = 120


def load_audio(path):
    """Decodifica un archivo a float32 mono a 48 kHz."""
    with AudioFile(str(path)).resampled_to(SAMPLE_RATE) as f:
        if f.frames > SAMPLE_RATE * MAX_SECONDS:
            raise ValueError(f"dura más de {MAX_SECONDS} s")
        data = f.read(f.frames)
    return np.ascontiguousarray(data.mean(axis=0), dtype=np.float32)


def builtin_sounds():
    try:
        items = json.loads((BUILTIN_DIR / "sounds.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    for it in items:
        it["path"] = str(BUILTIN_DIR / it["file"])
        it["builtin"] = True
    return items


def import_file(src):
    """Copia un archivo del usuario a su biblioteca y devuelve la entrada."""
    src = Path(src)
    load_audio(src)  # valida que se pueda leer antes de copiar
    USER_DIR.mkdir(parents=True, exist_ok=True)
    sid = uuid.uuid4().hex[:10]
    dst = USER_DIR / f"{sid}{src.suffix.lower()}"
    shutil.copy2(src, dst)
    return {"id": f"user:{sid}", "path": str(dst), "name": src.stem[:40],
            "icon": "audio-lines", "category": "Mis sonidos", "builtin": False}


def save_user_icon(data, ext):
    """Guarda una imagen de icono en la biblioteca y devuelve «img:archivo»."""
    ext = ext.lower()
    if ext not in ICON_IMAGE_EXTS or len(data) > MAX_ICON_BYTES:
        raise ValueError(ext if ext not in ICON_IMAGE_EXTS else "> 2 MB")
    USER_ICON_DIR.mkdir(parents=True, exist_ok=True)
    name = hashlib.sha1(data).hexdigest()[:12] + ext
    (USER_ICON_DIR / name).write_bytes(data)
    return f"img:{name}"


def delete_user_file(entry):
    try:
        Path(entry["path"]).unlink()
    except OSError:
        pass


class Soundboard:
    """Mezclador en tiempo real. ``play`` se llama desde la UI y ``mix``
    desde el hilo de audio; un lock protege la lista de reproducciones."""

    def __init__(self):
        self.volume = 0.8
        self._cache = {}
        self._playing = {}  # id → [datos, posición, ganancia, bucle]
        self._lock = threading.Lock()

    def preload(self, sid, path):
        if sid not in self._cache:
            self._cache[sid] = load_audio(path)
        return self._cache[sid]

    def forget(self, sid):
        self.stop(sid)
        self._cache.pop(sid, None)

    def play(self, sid, path, gain=1.0, loop=False):
        """Reproduce; si ya sonaba, lo detiene (comportamiento de interruptor).
        Devuelve True si empezó a sonar."""
        data = self.preload(sid, path)
        with self._lock:
            if sid in self._playing:
                del self._playing[sid]
                return False
            self._playing[sid] = [data, 0, gain, loop]
            return True

    def stop(self, sid):
        with self._lock:
            self._playing.pop(sid, None)

    def stop_all(self):
        with self._lock:
            self._playing.clear()

    def playing_ids(self):
        with self._lock:
            return set(self._playing)

    def mix(self, n):
        if not self._playing:
            return None
        out = np.zeros(n, dtype=np.float32)
        with self._lock:
            for sid in list(self._playing):
                data, pos, gain, loop = self._playing[sid]
                done = 0
                while done < n:
                    take = min(n - done, len(data) - pos)
                    out[done:done + take] += data[pos:pos + take] * gain
                    done += take
                    pos += take
                    if pos >= len(data):
                        if not loop:
                            break
                        pos = 0
                if pos >= len(data) and not loop:
                    del self._playing[sid]
                else:
                    self._playing[sid][1] = pos
        return out * self.volume
