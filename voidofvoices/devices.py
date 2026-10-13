"""Dispositivos de audio y micrófono virtual, según el sistema.

- Linux: PipeWire/PulseAudio vía pactl (ver virtualmic.py). La app crea su
  propio micrófono virtual.
- Windows: WASAPI vía sounddevice. El micrófono virtual es VB-Cable (driver
  gratuito): la app escribe en «CABLE Input» y las demás apps graban de
  «CABLE Output».

Los dispositivos se identifican por un id de texto estable (nombre en pactl o
nombre del dispositivo en Windows).
"""

import hashlib
import tempfile
import urllib.request
import zipfile
from pathlib import Path

from . import IS_WINDOWS

VBCABLE_URL = "https://vb-audio.com/Cable/"
# Paquete oficial de VB-Cable. Su licencia no permite incluirlo en el instalador de
# otra app, así que se descarga de la web oficial cuando el usuario lo pide y se
# abre su propio instalador (donde acepta la licencia de VB-Audio).
VBCABLE_PACK_URL = "https://download.vb-audio.com/Download_CABLE/VBCABLE_Driver_Pack45.zip"
VBCABLE_PACK_SHA256 = "b950e39f01af1d04ea623c8f6d8eb9b6ea5c477c637295fabf20631c85116bfb"


class VBCableError(Exception):
    pass


def download_vbcable(progress=None):
    """Descarga y verifica el paquete oficial; devuelve la ruta del instalador x64.

    La huella SHA-256 evita ejecutar con permisos de administrador un archivo
    distinto del publicado por VB-Audio.
    """
    folder = Path(tempfile.gettempdir()) / "VoidOfVoices" / "vbcable"
    folder.mkdir(parents=True, exist_ok=True)
    zpath = folder / "VBCABLE_Driver_Pack.zip"
    req = urllib.request.Request(VBCABLE_PACK_URL, headers={"User-Agent": "VoidOfVoices"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r, open(zpath, "wb") as f:
            total = int(r.headers.get("Content-Length") or 0)
            done = 0
            while chunk := r.read(64 * 1024):
                f.write(chunk)
                done += len(chunk)
                if progress and total:
                    progress(done / total)
    except OSError as e:
        raise VBCableError(str(e))
    if hashlib.sha256(zpath.read_bytes()).hexdigest() != VBCABLE_PACK_SHA256:
        raise VBCableError("checksum")
    with zipfile.ZipFile(zpath) as z:
        z.extractall(folder / "pack")
    setup = folder / "pack" / "VBCABLE_Setup_x64.exe"
    if not setup.exists():
        raise VBCableError("VBCABLE_Setup_x64.exe")
    return setup


def launch_vbcable_setup(setup):
    """Abre el instalador de VB-Cable como administrador (Windows muestra el aviso UAC)."""
    import ctypes
    rc = ctypes.windll.shell32.ShellExecuteW(None, "runas", str(setup), None, str(Path(setup).parent), 1)
    if rc <= 32:
        raise VBCableError("cancelado" if rc == 5 else f"ShellExecute {rc}")

if IS_WINDOWS:
    import sounddevice as sd

    def _hostapi():
        """Índice de WASAPI (baja latencia) o, si no hay, la API por defecto."""
        for i, api in enumerate(sd.query_hostapis()):
            if "WASAPI" in api["name"]:
                return i
        return sd.default.hostapi

    def _devices(kind):
        api = _hostapi()
        key = "max_input_channels" if kind == "input" else "max_output_channels"
        return [(i, d) for i, d in enumerate(sd.query_devices()) if d["hostapi"] == api and d[key] > 0]

    def resolve(dev_id, kind):
        """Nombre → índice de sounddevice (None = predeterminado)."""
        if not dev_id:
            return None
        for i, d in _devices(kind):
            if d["name"] == dev_id:
                return i
        return None

    def list_inputs():
        return [(d["name"], d["name"]) for _, d in _devices("input")
                if not d["name"].startswith("CABLE Output")]

    def list_outputs():
        return [(d["name"], d["name"]) for _, d in _devices("output")
                if not d["name"].startswith("CABLE Input")]

    def _default(kind):
        """Predeterminado de Windows, salvo que sea VB-Cable (su instalador suele
        ponerse por defecto): leeríamos/escucharíamos nuestro propio micrófono virtual."""
        api = sd.query_hostapis(_hostapi())
        idx = api["default_input_device" if kind == "input" else "default_output_device"]
        name = sd.query_devices(idx)["name"] if idx >= 0 else None
        if name and not name.startswith("CABLE"):
            return name
        real = list_inputs() if kind == "input" else list_outputs()
        return real[0][0] if real else None

    def default_input():
        return _default("input")

    def default_output():
        return _default("output")

    def virtual_output():
        """Dispositivo donde escribir la voz para que otras apps la oigan."""
        for _, d in _devices("output"):
            if d["name"].startswith("CABLE Input"):
                return d["name"]
        return None

    def virtual_mic_ready():
        return virtual_output() is not None

    def refresh():
        """PortAudio guarda la lista de dispositivos al iniciarse: la recarga para
        ver dispositivos nuevos (no usar con streams abiertos)."""
        sd._terminate()
        sd._initialize()

    def setup_virtual_mic():
        pass

    def teardown_virtual_mic():
        pass

else:
    from . import virtualmic

    def resolve(dev_id, kind):
        return dev_id

    def list_inputs():
        return virtualmic.list_sources()

    def list_outputs():
        return virtualmic.list_sinks()

    def default_input():
        return virtualmic.default_source()

    def default_output():
        return virtualmic.default_sink()

    def virtual_output():
        return virtualmic.SINK_NAME

    def virtual_mic_ready():
        return True

    def refresh():
        pass

    def setup_virtual_mic():
        virtualmic.create()

    def teardown_virtual_mic():
        virtualmic.remove()
