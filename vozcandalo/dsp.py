"""Procesamiento de audio en tiempo real (mono, float32, bloques)."""

import ctypes
import math
from dataclasses import dataclass, field, asdict, fields

import numpy as np
import pedalboard as pb
from scipy.signal import sosfilt

try:
    from pyrnnoise import rnnoise as _rnn
except Exception:  # pragma: no cover - dependencia opcional
    _rnn = None

SAMPLE_RATE = 48000

EQ_BANDS = (60, 250, 1000, 4000, 12000)


@dataclass
class Params:
    # --- Voz
    pitch: float = 0.0          # semitonos, -12..+12
    formant: float = 0.0        # semitonos, -12..+12 (timbre; solo en modo calidad)
    whisper: float = 0.0        # 0..1
    vibrato: float = 0.0        # 0..1 (profundidad, ±1 semitono máx.)
    tremolo: float = 0.0        # 0..1
    bass: float = 0.0           # dB, low shelf 200 Hz
    treble: float = 0.0         # dB, high shelf 4 kHz
    # --- Carácter
    robot: float = 0.0          # 0..1 mezcla de modulación en anillo
    robot_freq: float = 55.0    # Hz
    radio: float = 0.0          # 0..1 filtro paso banda + saturación
    distortion: float = 0.0     # 0..1
    bitcrush: float = 0.0       # 0..1 (16 → 4 bits)
    underwater: float = 0.0     # 0..1 filtro paso bajo resonante
    # --- Modulación y espacio
    chorus: float = 0.0         # 0..1
    phaser: float = 0.0         # 0..1
    echo: float = 0.0           # 0..1 mezcla
    echo_time: float = 0.25     # segundos
    reverb: float = 0.0         # 0..1 mezcla
    reverb_size: float = 0.5    # 0..1
    # --- Mejora de audio
    denoise: float = 0.0        # 0..1 supresión de ruido IA (RNNoise)
    noise_reduction: float = 0.0  # 0..10 puerta de ruido
    highpass: float = 70.0      # Hz (0 = desactivado)
    deesser: float = 0.0        # 0..1
    compressor: float = 0.0     # 0..1
    limiter: float = 1.0        # 0/1
    gain: float = 0.0           # dB
    eq: list = field(default_factory=lambda: [0.0] * len(EQ_BANDS))

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, d):
        p = cls()
        for k, v in d.items():
            if hasattr(p, k):
                setattr(p, k, list(v) if k == "eq" else float(v))
        return p

    def copy(self):
        return Params.from_dict(self.to_dict())


# Ajustes que pertenecen al micrófono/usuario y no a la «voz»: los presets
# del banco no los tocan.
ENHANCE_KEYS = ("denoise", "noise_reduction", "highpass", "deesser",
                "compressor", "limiter", "gain", "eq")
VOICE_KEYS = tuple(f.name for f in fields(Params) if f.name not in ENHANCE_KEYS)


# ---------------------------------------------------------------- biquads
# Fórmulas del "Audio EQ Cookbook" (R. Bristow-Johnson).

def _norm(b0, b1, b2, a0, a1, a2):
    return [b0 / a0, b1 / a0, b2 / a0, 1.0, a1 / a0, a2 / a0]


def low_shelf(f0, gain_db, fs=SAMPLE_RATE, s=1.0):
    a = 10 ** (gain_db / 40)
    w = 2 * math.pi * f0 / fs
    cw, sw = math.cos(w), math.sin(w)
    alpha = sw / 2 * math.sqrt((a + 1 / a) * (1 / s - 1) + 2)
    sa = 2 * math.sqrt(a) * alpha
    return _norm(a * ((a + 1) - (a - 1) * cw + sa),
                 2 * a * ((a - 1) - (a + 1) * cw),
                 a * ((a + 1) - (a - 1) * cw - sa),
                 (a + 1) + (a - 1) * cw + sa,
                 -2 * ((a - 1) + (a + 1) * cw),
                 (a + 1) + (a - 1) * cw - sa)


def high_shelf(f0, gain_db, fs=SAMPLE_RATE, s=1.0):
    a = 10 ** (gain_db / 40)
    w = 2 * math.pi * f0 / fs
    cw, sw = math.cos(w), math.sin(w)
    alpha = sw / 2 * math.sqrt((a + 1 / a) * (1 / s - 1) + 2)
    sa = 2 * math.sqrt(a) * alpha
    return _norm(a * ((a + 1) + (a - 1) * cw + sa),
                 -2 * a * ((a - 1) + (a + 1) * cw),
                 a * ((a + 1) + (a - 1) * cw - sa),
                 (a + 1) - (a - 1) * cw + sa,
                 2 * ((a - 1) - (a + 1) * cw),
                 (a + 1) - (a - 1) * cw - sa)


def peaking(f0, gain_db, q=1.0, fs=SAMPLE_RATE):
    a = 10 ** (gain_db / 40)
    w = 2 * math.pi * f0 / fs
    alpha = math.sin(w) / (2 * q)
    cw = math.cos(w)
    return _norm(1 + alpha * a, -2 * cw, 1 - alpha * a,
                 1 + alpha / a, -2 * cw, 1 - alpha / a)


def highpass(f0, q=0.707, fs=SAMPLE_RATE):
    w = 2 * math.pi * f0 / fs
    alpha = math.sin(w) / (2 * q)
    cw = math.cos(w)
    return _norm((1 + cw) / 2, -(1 + cw), (1 + cw) / 2,
                 1 + alpha, -2 * cw, 1 - alpha)


def lowpass(f0, q=0.707, fs=SAMPLE_RATE):
    w = 2 * math.pi * f0 / fs
    alpha = math.sin(w) / (2 * q)
    cw = math.cos(w)
    return _norm((1 - cw) / 2, 1 - cw, (1 - cw) / 2,
                 1 + alpha, -2 * cw, 1 - alpha)


IDENTITY = [1.0, 0.0, 0.0, 1.0, 0.0, 0.0]


# ------------------------------------------------------ bloques con FIFO

class Framed:
    """Adapta un proceso de tamaño de trama fijo a bloques arbitrarios.

    Añade ``frame`` muestras de latencia (prellenado del FIFO de salida),
    lo que garantiza que siempre haya salida disponible.
    """

    def __init__(self, frame):
        self.frame = frame
        self.reset()

    def reset(self):
        self.inbuf = np.zeros(0, dtype=np.float32)
        self.outbuf = np.zeros(self.frame, dtype=np.float32)

    def run(self, x, fn):
        self.inbuf = np.concatenate([self.inbuf, x])
        outs = [self.outbuf]
        f = self.frame
        while len(self.inbuf) >= f:
            outs.append(fn(self.inbuf[:f]))
            self.inbuf = self.inbuf[f:]
        buf = np.concatenate(outs)
        self.outbuf = buf[len(x):]
        return buf[:len(x)]


# ---------------------------------------------------------- pitch shifters

class DelayLinePitch:
    """Pitch shift de baja latencia: dos lecturas de una línea de retardo
    cruzadas con ventanas sin². Desplaza también los formantes (efecto
    «ardilla» en subidas grandes)."""

    def __init__(self, window_ms=40.0, fs=SAMPLE_RATE):
        self.win = int(fs * window_ms / 1000)
        self.size = 1 << (self.win * 2 + 4096).bit_length()
        self.buf = np.zeros(self.size, dtype=np.float32)
        self.pos = 0
        self.phase = 0.0

    def process(self, x, semitones):
        n = len(x)
        idx = (self.pos + np.arange(n)) % self.size
        self.buf[idx] = x
        if abs(semitones) < 1e-3:
            self.pos = (self.pos + n) % self.size
            return x

        ratio = 2.0 ** (semitones / 12.0)
        step = (1.0 - ratio) / self.win
        phases = (self.phase + step * np.arange(1, n + 1)) % 1.0
        self.phase = float(phases[-1])

        out = np.zeros(n, dtype=np.float32)
        write_t = self.pos + np.arange(n)
        for ph in (phases, (phases + 0.5) % 1.0):
            delay = ph * self.win + 1.0
            rp = write_t - delay
            i0 = np.floor(rp).astype(np.int64)
            frac = (rp - i0).astype(np.float32)
            s0 = self.buf[i0 % self.size]
            s1 = self.buf[(i0 + 1) % self.size]
            out += (s0 + (s1 - s0) * frac) * np.sin(np.pi * ph).astype(np.float32) ** 2
        self.pos = (self.pos + n) % self.size
        return out


class SpectralVoice:
    """Vocoder de fase con envolvente cepstral.

    Separa la excitación (tono) de la envolvente espectral (formantes), así
    que tono y timbre se mueven por separado. También genera susurro
    sustituyendo la fase por ruido. Latencia ≈ N + H muestras (~27 ms).
    """

    N = 1024
    H = 256
    LIFTER = 40  # coeficientes cepstrales que forman la envolvente

    def __init__(self):
        n, h = self.N, self.H
        self.win = np.hanning(n + 1)[:-1].astype(np.float32)
        self.norm = 1.0 / (np.sum(self.win ** 2) / h)
        self.bins = n // 2 + 1
        self.k = np.arange(self.bins, dtype=np.float64)
        self.omega = 2 * np.pi * self.k * h / n
        self.framer = Framed(h)
        self.rng = np.random.default_rng()
        self.reset()

    def reset(self):
        self.frame = np.zeros(self.N, dtype=np.float32)
        self.prev_phase = np.zeros(self.bins)
        self.sum_phase = None
        self.ola = np.zeros(self.N, dtype=np.float32)
        self.framer.reset()

    def process(self, x, pitch, formant, whisper):
        self._args = (2.0 ** (pitch / 12), 2.0 ** (formant / 12), whisper)
        return self.framer.run(x, self._hop)

    def _hop(self, hop):
        ratio, fratio, whisper = self._args
        n, h = self.N, self.H
        self.frame = np.concatenate([self.frame[h:], hop])
        spec = np.fft.rfft(self.frame * self.win)
        mag = np.abs(spec)
        phase = np.angle(spec)

        dphi = phase - self.prev_phase - self.omega
        self.prev_phase = phase
        dphi -= 2 * np.pi * np.round(dphi / (2 * np.pi))
        advance = self.omega + dphi

        cep = np.fft.irfft(np.log(mag + 1e-9))
        cep[self.LIFTER:n - self.LIFTER + 1] = 0
        env = np.exp(np.fft.rfft(cep).real)
        flat = mag / env

        # Mapeo directo: cada bin de entrada va a round(k·ratio). Mantiene
        # los picos armónicos estrechos (la interpolación inversa los ensancha).
        dst = np.round(self.k * ratio).astype(np.int64)
        ok = dst < self.bins
        new_flat = np.zeros(self.bins)
        np.add.at(new_flat, dst[ok], flat[ok])
        if ratio < 1:  # varios bins caen en el mismo: compensa la suma
            new_flat *= ratio
        new_adv = np.zeros(self.bins)
        new_adv[dst[ok]] = advance[ok] * ratio
        if ratio > 1:  # huecos sin bin de origen: avance nominal
            empty = new_flat == 0
            new_adv[empty] = self.omega[empty]
        new_env = np.interp(self.k / fratio, self.k, env, right=0.0)
        new_mag = new_flat * new_env

        if self.sum_phase is None:
            # Parte de la fase real para conservar la relación entre bins
            # de un mismo pico (si no, suenan «en fase» y más fuerte).
            self.sum_phase = np.zeros(self.bins)
            self.sum_phase[dst[ok]] = phase[ok]
        self.sum_phase = (self.sum_phase + new_adv) % (2 * np.pi)
        out_spec = new_mag * np.exp(1j * self.sum_phase)
        if whisper > 0:
            noise = new_mag * np.exp(1j * self.rng.uniform(0, 2 * np.pi, self.bins))
            out_spec = out_spec * (1 - whisper) + noise * whisper

        y = np.fft.irfft(out_spec, n).astype(np.float32) * self.win * self.norm
        self.ola += y
        out = self.ola[:h].copy()
        self.ola = np.concatenate([self.ola[h:], np.zeros(h, dtype=np.float32)])
        return out


# ------------------------------------------------------------ RNNoise

class Denoiser:
    """Supresión de ruido con RNNoise (red neuronal, tramas de 10 ms)."""

    available = _rnn is not None

    def __init__(self):
        self.state = _rnn.create() if self.available else None
        self.framer = Framed(480)
        self.mix = 1.0
        self.speech_prob = 0.0

    def reset(self):
        self.framer.reset()

    def process(self, x, mix):
        if not self.available:
            return x
        self.mix = mix
        return self.framer.run(x, self._frame)

    def _frame(self, frame):
        buf = (frame * 32768.0).astype(np.float32)
        ptr = buf.ctypes.data_as(ctypes.POINTER(ctypes.c_float))
        self.speech_prob = float(_rnn.lib.rnnoise_process_frame(self.state, ptr, ptr))
        wet = buf / 32768.0
        return frame * (1 - self.mix) + wet * self.mix


# ------------------------------------------------------------- procesador

class Processor:
    def __init__(self, fs=SAMPLE_RATE):
        self.fs = fs
        self.params = Params()
        self.quality = True       # True: vocoder con formantes; False: baja latencia
        self.version = 0
        self._version = -1

        self.denoiser = Denoiser()
        self.delay_pitch = DelayLinePitch(fs=fs)
        self.spectral = SpectralVoice()
        self._spectral_on = False
        self._denoise_on = False

        self.pre_zi = np.zeros((1, 2))       # paso alto
        self.eq_zi = np.zeros((7, 2))        # shelves + 5 bandas
        self.deess_sos = np.array([highpass(5500, fs=fs), highpass(5500, fs=fs)])
        self.deess_zi = np.zeros((2, 2))
        self.deess_gain = 1.0
        self.radio_sos = np.array([highpass(500, fs=fs), lowpass(3200, fs=fs),
                                   highpass(500, fs=fs), lowpass(3200, fs=fs)])
        self.radio_zi = np.zeros((4, 2))
        self.lfo = 0.0
        self.robot_phase = 0.0

        self.gate = pb.NoiseGate(threshold_db=-60, ratio=8, attack_ms=2, release_ms=150)
        self.underwater_fx = pb.Pedalboard([
            pb.LadderFilter(mode=pb.LadderFilter.Mode.LPF24, cutoff_hz=500, resonance=0.4),
            pb.Chorus(rate_hz=0.6, depth=0.6, centre_delay_ms=12, mix=0.6)])
        self.bitcrush_fx = pb.Bitcrush(bit_depth=8)
        self.chorus_fx = pb.Chorus(rate_hz=1.2, depth=0.35, centre_delay_ms=8, feedback=0.1)
        self.phaser_fx = pb.Phaser(rate_hz=0.7, depth=0.7, feedback=0.5)
        self.delay_fx = pb.Delay(delay_seconds=0.25, feedback=0.4)
        self.reverb_fx = pb.Reverb()
        self.compressor_fx = pb.Compressor(threshold_db=-18, ratio=3, attack_ms=5, release_ms=120)
        self.makeup_db = 0.0
        self.limiter_fx = pb.Limiter(threshold_db=-1.0, release_ms=80)

    def set_params(self, p: Params):
        self.params = p
        self.version += 1

    # ---------------------------------------------------------- helpers
    def _pb(self, plugin, x):
        return plugin(x[None, :], self.fs, reset=False)[0].astype(np.float32)

    def _rebuild(self):
        p, fs = self.params, self.fs
        self.pre_sos = np.array([highpass(p.highpass, fs=fs) if p.highpass >= 20 else IDENTITY])
        sections = [low_shelf(200, p.bass, fs=fs), high_shelf(4000, p.treble, fs=fs)]
        sections += [peaking(f, g, q=1.1, fs=fs) for f, g in zip(EQ_BANDS, p.eq)]
        self.eq_sos = np.array(sections)

        # Puerta: 0 → off; 1..10 → umbral -60..-30 dBFS
        self.gate.threshold_db = -63 + p.noise_reduction * 3.3
        self.bitcrush_fx.bit_depth = 16 - p.bitcrush * 12
        self.chorus_fx.mix = p.chorus
        self.phaser_fx.mix = p.phaser
        self.delay_fx.delay_seconds = min(max(p.echo_time, 0.03), 1.5)
        self.delay_fx.mix = p.echo
        self.reverb_fx.room_size = p.reverb_size
        self.reverb_fx.wet_level = p.reverb * 0.6
        self.reverb_fx.dry_level = 1 - p.reverb * 0.4
        self.reverb_fx.damping = 0.5
        c = p.compressor
        self.compressor_fx.threshold_db = -6 - 24 * c
        self.compressor_fx.ratio = 1 + 5 * c
        self.makeup_db = 9 * c
        self._version = self.version

    def _deess(self, x, amount):
        hi, self.deess_zi = sosfilt(self.deess_sos, x, zi=self.deess_zi)
        hi = hi.astype(np.float32)
        e_hi = float(np.sqrt(np.mean(hi * hi)) + 1e-9)
        e_all = float(np.sqrt(np.mean(x * x)) + 1e-9)
        # Sibilancia = mucha energía >5,5 kHz respecto al total.
        ratio = e_hi / e_all
        thresh = 0.55 - 0.35 * amount
        target = 1.0 if ratio < thresh else max(0.15, thresh / ratio)
        coef = 0.6 if target < self.deess_gain else 0.15
        g = self.deess_gain + (target - self.deess_gain) * coef
        ramp = np.linspace(self.deess_gain, g, len(x), dtype=np.float32)
        self.deess_gain = g
        return x - hi * (1 - ramp)

    def _robot(self, x, mix, f):
        n = len(x)
        inc = 2 * np.pi * f / self.fs
        ph = self.robot_phase + inc * np.arange(n)
        self.robot_phase = float((ph[-1] + inc) % (2 * np.pi))
        wet = x * np.sin(ph).astype(np.float32) * 1.6
        return x * (1 - mix) + wet * mix

    def _radio(self, x, mix):
        wet, self.radio_zi = sosfilt(self.radio_sos, x, zi=self.radio_zi)
        wet = np.tanh(wet.astype(np.float32) * 3.0) * 0.6
        return x * (1 - mix) + wet * mix

    # ------------------------------------------------------------ cadena
    def process(self, x):
        p = self.params
        if self._version != self.version:
            self._rebuild()
        n = len(x)
        lfo_t = self.lfo + np.arange(n) / self.fs
        self.lfo = float(lfo_t[-1] + 1 / self.fs) % 1000.0

        # 1) Mejora de la señal de entrada
        x, self.pre_zi = sosfilt(self.pre_sos, x, zi=self.pre_zi)
        x = x.astype(np.float32)
        if p.denoise > 0 and self.denoiser.available:
            if not self._denoise_on:
                self.denoiser.reset()
                self._denoise_on = True
            x = self.denoiser.process(x, p.denoise)
        else:
            self._denoise_on = False
        if p.noise_reduction > 0:
            x = self._pb(self.gate, x)

        # 2) Voz: tono, formantes, susurro, vibrato
        pitch = p.pitch + p.vibrato * math.sin(2 * math.pi * 5.5 * lfo_t[0])
        # Decide por parámetros (no por el tono instantáneo) para no alternar
        # de motor con el vibrato.
        use_spectral = p.whisper > 0 or (self.quality and (
            abs(p.pitch) > 1e-3 or abs(p.formant) > 1e-3 or p.vibrato > 0))
        if use_spectral:
            if not self._spectral_on:
                self.spectral.reset()
                self._spectral_on = True
            x = self.spectral.process(x, pitch, p.formant if self.quality else pitch, p.whisper)
        else:
            self._spectral_on = False
            x = self.delay_pitch.process(x, pitch)

        y, self.eq_zi = sosfilt(self.eq_sos, x, zi=self.eq_zi)
        x = y.astype(np.float32)
        if p.deesser > 0:
            x = self._deess(x, p.deesser)

        # 3) Carácter
        if p.robot > 0:
            x = self._robot(x, p.robot, p.robot_freq)
        if p.radio > 0:
            x = self._radio(x, p.radio)
        if p.underwater > 0:
            wet = self._pb(self.underwater_fx, x)
            x = x * (1 - p.underwater) + wet * p.underwater
        if p.distortion > 0:
            drive = 1 + p.distortion * 20
            x = np.tanh(x * drive) / np.tanh(drive) * (1 - p.distortion * 0.5)
        if p.bitcrush > 0:
            x = self._pb(self.bitcrush_fx, x)
        if p.tremolo > 0:
            x = x * (1 - p.tremolo * 0.5 * (1 + np.sin(2 * np.pi * 6.0 * lfo_t))).astype(np.float32)

        # 4) Modulación y espacio
        if p.chorus > 0:
            x = self._pb(self.chorus_fx, x)
        if p.phaser > 0:
            x = self._pb(self.phaser_fx, x)
        if p.echo > 0:
            x = self._pb(self.delay_fx, x)
        if p.reverb > 0:
            x = self._pb(self.reverb_fx, x)

        # 5) Dinámica y salida
        if p.compressor > 0:
            x = self._pb(self.compressor_fx, x)
        x = x * (10 ** ((p.gain + self.makeup_db * (p.compressor > 0)) / 20))
        if p.limiter > 0:
            x = self._pb(self.limiter_fx, x)
        return np.clip(x, -1.0, 1.0).astype(np.float32)


# ---------------------------------------------------------- banco de voces

def V(**kw):
    return Params(**kw)


# categoría → {nombre: (icono, Params)}
VOICE_BANK = {
    "Básicas": {
        "Natural": ("🙂", V()),
        "Grave": ("🐻", V(pitch=-4, formant=-2, bass=3, treble=-1)),
        "Agudo": ("🐭", V(pitch=4, formant=2, bass=-3, treble=2)),
        "Locutor": ("🎙", V(pitch=-1, formant=-1, bass=4, treble=2)),
    },
    "Género": {
        "Femenina": ("👩", V(pitch=5, formant=3, bass=-3, treble=2)),
        "Masculina": ("👨", V(pitch=-5, formant=-3, bass=3, treble=-1)),
        "Niño": ("👦", V(pitch=7, formant=5, bass=-4, treble=1)),
        "Anciano": ("👴", V(pitch=-2, formant=-1, vibrato=0.35, tremolo=0.15, treble=-2)),
    },
    "Personajes": {
        "Ardilla": ("🐿", V(pitch=10, formant=9)),
        "Gigante": ("🗿", V(pitch=-9, formant=-6, bass=4, reverb=0.3, reverb_size=0.8)),
        "Demonio": ("😈", V(pitch=-10, formant=-4, bass=6, distortion=0.25, reverb=0.25, reverb_size=0.6)),
        "Fantasma": ("👻", V(pitch=-2, whisper=0.8, chorus=0.6, reverb=0.6, reverb_size=0.9)),
        "Robot": ("🤖", V(pitch=-2, robot=0.9, robot_freq=55, treble=2, echo=0.15, echo_time=0.06)),
        "Androide": ("🦾", V(robot=0.6, robot_freq=110, bitcrush=0.4, phaser=0.4)),
        "Alien": ("👽", V(pitch=3, formant=6, robot=0.5, robot_freq=280, phaser=0.6, reverb=0.2)),
        "Monstruo": ("👹", V(pitch=-12, formant=-8, distortion=0.4, bass=6, tremolo=0.2)),
        "Susurro": ("🤫", V(whisper=1.0, treble=4, bass=-4)),
        "Arcade 8-bit": ("👾", V(pitch=3, bitcrush=0.85, treble=2)),
    },
    "Ambientes": {
        "Radio": ("📻", V(radio=1.0, distortion=0.15)),
        "Teléfono": ("☎", V(radio=1.0, bitcrush=0.5)),
        "Walkie-talkie": ("📟", V(radio=1.0, distortion=0.4, bitcrush=0.3)),
        "Megáfono": ("📢", V(radio=0.8, distortion=0.55, echo=0.15, echo_time=0.12)),
        "Bajo el agua": ("🌊", V(underwater=1.0, vibrato=0.3)),
        "Cueva": ("🕳", V(echo=0.35, echo_time=0.35, reverb=0.5, reverb_size=0.85)),
        "Catedral": ("⛪", V(reverb=0.85, reverb_size=1.0)),
        "Estadio": ("🏟", V(echo=0.25, echo_time=0.5, reverb=0.6, reverb_size=0.95, chorus=0.3)),
    },
}

# Presets de mejora (solo tocan ENHANCE_KEYS).
ENHANCE_PRESETS = {
    "Desactivado": dict(denoise=0, noise_reduction=0, highpass=0, deesser=0, compressor=0, limiter=1),
    "Llamada limpia": dict(denoise=1.0, noise_reduction=3, highpass=90, deesser=0.3, compressor=0.4, limiter=1),
    "Streaming": dict(denoise=0.9, noise_reduction=2, highpass=80, deesser=0.5, compressor=0.6, limiter=1),
    "Podcast": dict(denoise=0.7, noise_reduction=1, highpass=70, deesser=0.6, compressor=0.7, limiter=1),
}


def all_voices():
    """{nombre: (icono, Params)} de todas las categorías."""
    out = {}
    for cat in VOICE_BANK.values():
        out.update(cat)
    return out


QUICK_VOICES = ("Natural", "Grave", "Femenina", "Robot", "Radio", "Demonio")
