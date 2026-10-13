"""Dispositivos de audio y micrófono virtual, según el sistema.

- Linux: PipeWire/PulseAudio vía pactl (ver virtualmic.py). La app crea su
  propio micrófono virtual.
- Windows: WASAPI vía sounddevice. El micrófono virtual es VB-Cable (driver
  gratuito): la app escribe en «CABLE Input» y las demás apps graban de
  «CABLE Output».

Los dispositivos se identifican por un id de texto estable (nombre en pactl o
nombre del dispositivo en Windows).
"""

from . import IS_WINDOWS

VBCABLE_URL = "https://vb-audio.com/Cable/"

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
        api = sd.query_hostapis(_hostapi())
        idx = api["default_input_device" if kind == "input" else "default_output_device"]
        return sd.query_devices(idx)["name"] if idx >= 0 else None

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

    def setup_virtual_mic():
        virtualmic.create()

    def teardown_virtual_mic():
        virtualmic.remove()
