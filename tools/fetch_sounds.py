#!/usr/bin/env python3
"""Descarga y prepara los sonidos incluidos del soundboard desde Freesound (CC0).

Uso: .venv/bin/python tools/fetch_sounds.py

Lee la selección de tools/freesound_selection.json, descarga la vista previa HQ
de cada sonido y la deja en sounds/freesound/<id>.ogg, recortada, sin silencio
inicial y con el volumen igualado. Después regenera sounds/sounds.json y
sounds/CREDITS.md.
"""

import json
import tempfile
import time
import urllib.request
from pathlib import Path

import numpy as np
from pedalboard.io import AudioFile

ROOT = Path(__file__).resolve().parent.parent
SOUNDS = ROOT / "sounds"
OUT = SOUNDS / "freesound"
FS = 48000
TARGET_RMS_DB = -20.0   # volumen percibido parecido entre sonidos
PEAK_DB = -1.0

# Voces grabadas de Kenney (CC0) que se conservan como categoría «Arcade».
KENNEY = [
    ("round_1.ogg", "«Round 1»", "1️⃣"), ("fight.ogg", "«Fight!»", "🥊"),
    ("combo_breaker.ogg", "«Combo breaker»", "💥"), ("multi_kill.ogg", "«Multi kill»", "🔥"),
    ("flawless_victory.ogg", "«Flawless victory»", "👑"), ("you_win.ogg", "«You win»", "🏅"),
    ("loser.ogg", "«Loser»", "🫠"), ("v_game_over.ogg", "«Game over»", "🕹"),
]


def process(src, max_s):
    with AudioFile(str(src)).resampled_to(FS) as f:
        x = f.read(f.frames).mean(axis=0)
    # Quita silencio inicial (umbral relativo al pico).
    thr = np.max(np.abs(x)) * 0.02
    start = int(np.argmax(np.abs(x) > thr))
    x = x[max(0, start - int(0.01 * FS)):]
    if max_s and len(x) > max_s * FS:
        x = x[:int(max_s * FS)]
        fade = int(0.6 * FS)
        x[-fade:] *= np.linspace(1, 0, fade) ** 2
    # Quita silencio final.
    nz = np.nonzero(np.abs(x) > thr)[0]
    if len(nz):
        x = x[:min(len(x), nz[-1] + int(0.15 * FS))]
    # Igualar volumen: RMS de las partes con sonido, con techo de pico.
    loud = x[np.abs(x) > thr]
    rms = np.sqrt(np.mean(loud ** 2)) if len(loud) else 1e-9
    g = 10 ** (TARGET_RMS_DB / 20) / (rms + 1e-9)
    g = min(g, 10 ** (PEAK_DB / 20) / (np.max(np.abs(x)) + 1e-9))
    return (x * g).astype(np.float32)


def main():
    sel = json.loads((ROOT / "tools" / "freesound_selection.json").read_text())
    OUT.mkdir(parents=True, exist_ok=True)
    catalog = []
    with tempfile.TemporaryDirectory() as tmp:
        for s in sel:
            dst = OUT / f"{s['fs_id']}.ogg"
            if not dst.exists():
                mp3 = Path(tmp) / f"{s['fs_id']}.mp3"
                req = urllib.request.Request(s["url"], headers={"User-Agent": "Vozcandalo"})
                mp3.write_bytes(urllib.request.urlopen(req, timeout=60).read())
                y = process(mp3, s["max_s"])
                with AudioFile(str(dst), "w", FS, 1) as f:
                    f.write(y[None, :])
                time.sleep(0.3)
            catalog.append({"id": f"builtin:freesound/{s['fs_id']}", "file": f"freesound/{s['fs_id']}.ogg",
                            "name": s["name"], "icon": s["icon"], "category": s["category"]})
            print("✓", s["name"])

    for f, name, icon in KENNEY:
        if (SOUNDS / "kenney" / f).exists():
            catalog.append({"id": f"builtin:kenney/{f}", "file": f"kenney/{f}",
                            "name": name, "icon": icon, "category": "Arcade"})
    (SOUNDS / "sounds.json").write_text(json.dumps(catalog, indent=1, ensure_ascii=False))

    lines = ["# Créditos de sonidos", "",
             "Todos los sonidos incluidos tienen licencia **CC0** (dominio público); "
             "los créditos no son obligatorios, pero se agradecen.", "",
             "## Freesound (freesound.org)", ""]
    for s in sel:
        lines.append(f"- {s['name']}: «{s['title']}» de {s['author']} — "
                     f"https://freesound.org/people/{s['author']}/sounds/{s['fs_id']}/")
    lines += ["", "## Kenney (kenney.nl)", "",
              "- Voces de *Voiceover Pack* y *Voiceover Pack: Fighter*, de Kenney Vleugels, vía OpenGameArt."]
    (SOUNDS / "CREDITS.md").write_text("\n".join(lines) + "\n")
    print(len(catalog), "sonidos en el catálogo")


if __name__ == "__main__":
    main()
