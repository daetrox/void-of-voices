"""Hilo de audio: parec (micro) → Processor → pacat (micro virtual / monitor)."""

import subprocess
import threading

import numpy as np

from . import virtualmic
from .dsp import Processor, SAMPLE_RATE
from .soundboard import Soundboard

BLOCK = 256  # muestras por bloque (~5,3 ms a 48 kHz)
_FMT = ["--raw", "--format=float32le", f"--rate={SAMPLE_RATE}", "--channels=1"]


def _rec(source, latency_ms):
    return subprocess.Popen(
        ["parec", *_FMT, f"--latency-msec={latency_ms}", "-d", source,
         "--client-name=Vozcandalo", "--stream-name=Entrada"],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=0)


def _play(sink, latency_ms, name):
    return subprocess.Popen(
        ["pacat", "--playback", *_FMT, f"--latency-msec={latency_ms}", "-d", sink,
         "--client-name=Vozcandalo", f"--stream-name={name}"],
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
        self.level_in = 0.0
        self.level_out = 0.0
        self.error = None
        self._thread = None
        self._stop = threading.Event()

    @property
    def running(self):
        return self._thread is not None and self._thread.is_alive()

    def start(self):
        if self.running:
            return
        self.error = None
        virtualmic.create()
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)
        self._thread = None
        self.level_in = self.level_out = 0.0
        virtualmic.remove()

    def restart(self):
        if self.running:
            self._stop.set()
            self._thread.join(timeout=2)
            self._stop.clear()
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()

    def _run(self):
        source = self.source or virtualmic.default_source()
        nbytes = BLOCK * 4
        rec = _rec(source, self.latency_ms)
        out = _play(virtualmic.SINK_NAME, self.latency_ms, "Micrófono virtual")
        mon = None
        mon_sink = None
        fallback_sink = virtualmic.default_sink()
        try:
            while not self._stop.is_set():
                data = rec.stdout.read(nbytes)
                if not data:
                    self.error = f"No se pudo leer de «{source}»"
                    break
                while len(data) < nbytes:
                    more = rec.stdout.read(nbytes - len(data))
                    if not more:
                        break
                    data += more
                if len(data) < nbytes:
                    self.error = f"No se pudo leer de «{source}»"
                    break
                x = np.frombuffer(data, dtype=np.float32)
                y = x if self.bypass else self.processor.process(x)
                sfx = self.soundboard.mix(len(y))
                mixed = y if sfx is None else y * (1.0 - self.duck) + sfx
                mixed = np.clip(mixed, -1.0, 1.0).astype(np.float32)
                self.level_in = float(np.max(np.abs(x)))
                self.level_out = float(np.max(np.abs(mixed)))
                out.stdin.write(mixed.tobytes())

                # Monitor: la voz (si «Escuchar») y/o los sonidos, activable en caliente.
                if self.monitor:
                    mon_sig = mixed if (self.sfx_monitor or sfx is None) else y
                elif self.sfx_monitor and sfx is not None:
                    mon_sig = sfx
                else:
                    mon_sig = np.zeros_like(y)
                buf = np.clip(mon_sig, -1.0, 1.0).astype(np.float32).tobytes()
                want = (self.monitor_sink or fallback_sink) if (self.monitor or self.sfx_monitor) else None
                if want != mon_sink:
                    _kill(mon)
                    mon = _play(want, self.latency_ms, "Monitor") if want else None
                    mon_sink = want
                if mon:
                    try:
                        mon.stdin.write(buf)
                    except BrokenPipeError:
                        mon = mon_sink = None
        except BrokenPipeError:
            self.error = "Se cerró la salida al micrófono virtual"
        finally:
            _kill(rec)
            _kill(out)
            _kill(mon)
