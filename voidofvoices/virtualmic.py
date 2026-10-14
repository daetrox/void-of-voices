"""Micrófono virtual y enumeración de dispositivos vía pactl (PipeWire-Pulse)."""

import os
import subprocess

from . import MIC_NAME

SINK_NAME = "voidofvoices_sink"
SOURCE_NAME = "voidofvoices_mic"
# Nombres de versiones anteriores, para limpiar módulos que hayan quedado cargados.
_LEGACY = ("vozcandalo_sink", "vozcandalo_mic", "audiomodulator_sink", "audiomodulator_mic")


def _pactl(*args):
    # LC_ALL=C: claves «Name:»/«Description:» en inglés sea cual sea el idioma del sistema.
    return subprocess.run(["pactl", *args], capture_output=True, text=True, encoding="utf-8",
                          check=True, env={**os.environ, "LC_ALL": "C"}).stdout


def _list(kind):
    """[(name, description)] leyendo la salida de texto: con «-f json», pactl
    devuelve «(null)» en las descripciones con acentos («Estéreo analógico»)."""
    out, name = [], None
    for line in _pactl("list", kind).splitlines():
        line = line.strip()
        if line.startswith("Name: "):
            name = line[6:]
        elif line.startswith("Description: ") and name:
            out.append((name, line[13:] or name))
            name = None
    return out


def list_sources():
    """Devuelve [(name, description)] de micrófonos reales (sin monitores ni el nuestro)."""
    return [(n, d) for n, d in _list("sources")
            if not n.endswith(".monitor") and n not in (SOURCE_NAME, SINK_NAME, *_LEGACY)]


def list_sinks():
    return [(n, d) for n, d in _list("sinks") if n != SINK_NAME]


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
