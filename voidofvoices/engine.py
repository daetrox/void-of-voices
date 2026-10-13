"""Hilo de audio: micrófono → Processor (+ soundboard) → micrófono virtual / monitor.

Dos backends de E/S con la misma interfaz:
- _PulseIO (Linux): procesos parec/pacat, sin dependencias nativas.
- _SoundDeviceIO (Windows): streams WASAPI de sounddevice.
"""

import subprocess
import threading

import numpy as np

from . import IS_WINDOWS, devices
from .dsp import Processor, SAMPLE_RATE
from .i18n import T
from .soundboard import Soundboard

BLOCK = 256  # muestras por bloque (~5,3 ms a 48 kHz)
_FMT = ["--raw", "--format=float32le", f"--rate={SAMPLE_RATE}", "--channels=1"]


# ------------------------------------------------------------- backend Linux

def _pacat(sink, latency_ms, name):
    return subprocess.Popen(
        ["pacat", "--playback", *_FMT, f"--latency-msec={latency_ms}", "-d", sink,
         "--client-name=VoidOfVoices", f"--stream-name={name}"],
        stdin=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=0)


def _kill(proc):
    if proc is None:
        return
    try:
        if proc.stdin:
            proc.stdin.close()
    except OSError:
        pass
    proc.terminate()
    try:
        proc.wait(timeout=1)
    except subprocess.TimeoutExpired:
        proc.kill()


class _PulseIO:
    def __init__(self, source, out_dev, latency_ms):
        self.latency = latency_ms
        self.rec = subprocess.Popen(
            ["parec", *_FMT, f"--latency-msec={latency_ms}", "-d", source,
             "--client-name=VoidOfVoices", "--stream-name=Entrada"],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=0)
        self.out = _pacat(out_dev, latency_ms, "Micrófono virtual") if out_dev else None
        self.mon = None
        self.mon_dev = None

    def read(self, n):
        nbytes = n * 4
        data = self.rec.stdout.read(nbytes)
        while data and len(data) < nbytes:
            more = self.rec.stdout.read(nbytes - len(data))
            if not more:
                break
            data += more
        if not data or len(data) < nbytes:
            return None
        return np.frombuffer(data, dtype=np.float32)

    def write(self, y):
        if self.out:
            self.out.stdin.write(y.tobytes())

    def monitor(self, dev, y):
        if dev != self.mon_dev:
            _kill(self.mon)
            self.mon = _pacat(dev, self.latency, "Monitor") if dev else None
            self.mon_dev = dev
        if self.mon:
            try:
                self.mon.stdin.write(y.tobytes())
            except BrokenPipeError:
                self.mon = self.mon_dev = None

    def close(self):
        _kill(self.rec)
        _kill(self.out)
        _kill(self.mon)


# ----------------------------------------------------------- backend Windows

class _SoundDeviceIO:
    def __init__(self, source, out_dev, latency_ms):
        import sounddevice as sd
        self.sd = sd
        self.latency = latency_ms / 1000
        self.extra = sd.WasapiSettings(auto_convert=True) if IS_WINDOWS else None
        self.inp = self._stream(sd.InputStream, devices.resolve(source, "input"))
        self.out = self._stream(sd.OutputStream, devices.resolve(out_dev, "output")) if out_dev else None
        self.mon = None
        self.mon_dev = None

    def _stream(self, cls, device):
        s = cls(samplerate=SAMPLE_RATE, channels=1, dtype="float32", blocksize=BLOCK,
                latency=self.latency, device=device, extra_settings=self.extra)
        s.start()
        return s

    def read(self, n):
        data, _ = self.inp.read(n)
        return np.ascontiguousarray(data[:, 0])

    def write(self, y):
        if self.out:
            self.out.write(y[:, None])

    def monitor(self, dev, y):
        if dev != self.mon_dev:
            if self.mon:
                self.mon.close()
            self.mon = self._stream(self.sd.OutputStream, devices.resolve(dev, "output")) if dev else None
            self.mon_dev = dev
        if self.mon:
            self.mon.write(y[:, None])

    def close(self):
        for s in (self.inp, self.out, self.mon):
            if s:
                try:
                    s.close()
                except Exception:
                    pass


_IO = _SoundDeviceIO if IS_WINDOWS else _PulseIO


# ------------------------------------------------------------- vista previa

class Preview:
    """Reproduce un sonido solo en los altavoces (con el modulador apagado)."""

    def __init__(self, data, sink):
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, args=(data, sink), daemon=True)
        self._thread.start()

    def _run(self, data, sink):
        data = np.clip(data, -1, 1).astype(np.float32)
        try:
            if IS_WINDOWS:
                import sounddevice as sd
                with sd.OutputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32",
                                     device=devices.resolve(sink, "output")) as s:
                    for i in range(0, len(data), 4800):
                        if self._stop.is_set():
                            break
                        s.write(data[i:i + 4800, None])
            else:
                proc = _pacat(sink, 60, "Vista previa")
                try:
                    for i in range(0, len(data), 4800):
                        if self._stop.is_set():
                            break
                        proc.stdin.write(data[i:i + 4800].tobytes())
                    proc.stdin.close()
                    while proc.poll() is None and not self._stop.wait(0.05):
                        pass
                finally:
                    _kill(proc)
        except Exception:
            pass

    @property
    def active(self):
        return self._thread.is_alive()

    def stop(self):
        self._stop.set()


# ------------------------------------------------------------------ motor

class AudioEngine:
    def __init__(self):
        self.processor = Processor()
        self.soundboard = Soundboard()
        self.sfx_monitor = True   # oír los sonidos del soundboard uno mismo
        self.duck = 0.0           # 0..1: cuánto bajar la voz mientras suena un sonido
        self.source = None
        self.monitor_sink = None
        self.monitor = False
        self.latency_ms = 20
        self.bypass = False
        self.muted = False        # silencio rápido (los sonidos siguen sonando)
        self.ptt_mode = False     # pulsar para hablar
        self.ptt_down = False
        self.level_in = 0.0
        self.level_out = 0.0
        self.error = None
        self._voice_gain = 1.0
        self._thread = None
        self._stop = threading.Event()

    @property
    def running(self):
        return self._thread is not None and self._thread.is_alive()

    @property
    def voice_open(self):
        return not self.muted and (not self.ptt_mode or self.ptt_down)

    def start(self):
        if self.running:
            return
        self.error = None
        devices.setup_virtual_mic()
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)
        self._thread = None
        self.level_in = self.level_out = 0.0
        devices.teardown_virtual_mic()

    def restart(self):
        if self.running:
            self._stop.set()
            self._thread.join(timeout=2)
            self._stop.clear()
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()

    def _run(self):
        source = self.source or devices.default_input()
        fallback_sink = devices.default_output()
        try:
            io = _IO(source, devices.virtual_output(), self.latency_ms)
        except Exception as e:
            self.error = T("No se pudo abrir el audio: {}").format(e)
            return
        try:
            while not self._stop.is_set():
                x = io.read(BLOCK)
                if x is None:
                    self.error = T("No se pudo leer de «{}»").format(source)
                    break
                y = x if self.bypass else self.processor.process(x)

                # Silencio / pulsar para hablar con rampa corta para evitar clics.
                target = 1.0 if self.voice_open else 0.0
                if target != self._voice_gain or target < 1.0:
                    ramp = np.linspace(self._voice_gain, target, len(y), dtype=np.float32)
                    y = y * ramp
                    self._voice_gain = target

                sfx = self.soundboard.mix(len(y))
                mixed = y if sfx is None else y * (1.0 - self.duck) + sfx
                mixed = np.clip(mixed, -1.0, 1.0).astype(np.float32)
                self.level_in = float(np.max(np.abs(x)))
                self.level_out = float(np.max(np.abs(mixed)))
                io.write(mixed)

                # Monitor: la voz (si «Escuchar») y/o los sonidos, activable en caliente.
                if self.monitor:
                    mon_sig = mixed if (self.sfx_monitor or sfx is None) else y
                elif self.sfx_monitor and sfx is not None:
                    mon_sig = sfx
                else:
                    mon_sig = np.zeros_like(y)
                want = (self.monitor_sink or fallback_sink) if (self.monitor or self.sfx_monitor) else None
                io.monitor(want, np.clip(mon_sig, -1.0, 1.0).astype(np.float32))
        except (BrokenPipeError, OSError) as e:
            self.error = T("Se cerró la salida de audio: {}").format(e)
        except Exception as e:  # p. ej. errores de PortAudio en Windows
            self.error = T("Error de audio: {}").format(e)
        finally:
            io.close()
