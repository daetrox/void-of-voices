"""Micrófono virtual y enumeración de dispositivos vía pactl (PipeWire-Pulse)."""

import json
import subprocess

from . import MIC_NAME

SINK_NAME = "voidofvoices_sink"
SOURCE_NAME = "voidofvoices_mic"
# Nombres de versiones anteriores, para limpiar módulos que hayan quedado cargados.
_LEGACY = ("vozcandalo_sink", "vozcandalo_mic", "audiomodulator_sink", "audiomodulator_mic")


def _pactl(*args):
    return subprocess.run(["pactl", *args], capture_output=True, text=True, check=True).stdout


def list_sources():
    """Devuelve [(name, description)] de micrófonos reales (sin monitores ni el nuestro)."""
    out = []
    for s in json.loads(_pactl("-f", "json", "list", "sources")):
        name = s["name"]
        if name.endswith(".monitor") or name in (SOURCE_NAME, SINK_NAME, *_LEGACY):
            continue
        out.append((name, s.get("description") or name))
    return out


def list_sinks():
    out = []
    for s in json.loads(_pactl("-f", "json", "list", "sinks")):
        if s["name"] == SINK_NAME:
            continue
        out.append((s["name"], s.get("description") or s["name"]))
    return out


def default_source():
    return _pactl("get-default-source").strip()


def default_sink():
    return _pactl("get-default-sink").strip()


def _our_modules():
    # El JSON de pactl no incluye el índice del módulo; usamos la salida corta.
    ids = []
    for line in _pactl("list", "short", "modules").splitlines():
        if any(n in line for n in (SINK_NAME, SOURCE_NAME, *_LEGACY)):
            ids.append(line.split("\t", 1)[0])
    return ids


def remove():
    # Primero el remap-source (depende del sink).
    for mid in reversed(_our_modules()):
        subprocess.run(["pactl", "unload-module", mid], capture_output=True)


def create():
    """Crea un sink nulo donde escribimos el audio y un micrófono virtual
    que expone su monitor como fuente de entrada normal para otras apps."""
    remove()
    _pactl("load-module", "module-null-sink",
           f"sink_name={SINK_NAME}", "channels=1", "channel_map=mono",
           "rate=48000",
           "sink_properties=device.description=VoidOfVoices_Salida")
    _pactl("load-module", "module-remap-source",
           f"master={SINK_NAME}.monitor", f"source_name={SOURCE_NAME}",
           "channels=1", "channel_map=mono",
           f"source_properties=device.description={MIC_NAME}")
