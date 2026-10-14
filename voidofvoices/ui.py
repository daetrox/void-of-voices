"""Interfaz gráfica de Void of Voices (PySide6)."""

import json
import os
from collections import Counter
import sys
import time
from pathlib import Path

import threading

from PySide6.QtCore import QObject, QProcess, QSize, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QAction, QDesktopServices, QFontDatabase, QIcon, QKeySequence, QShortcut
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import (
    QApplication, QButtonGroup, QCheckBox, QComboBox, QFileDialog, QFrame, QGridLayout,
    QHBoxLayout, QInputDialog, QLabel, QLineEdit, QMainWindow, QMenu, QMessageBox,
    QProgressBar, QPushButton, QSizePolicy, QSpinBox, QStackedWidget, QSystemTrayIcon,
    QToolButton, QVBoxLayout, QWidget,
)

from . import (APP_ID, APP_NAME, CONFIG_FILE, EMOJI_FONT, ICON_PATH, IS_WINDOWS, MIC_NAME, REPO_URL,
               __version__, devices, migrate_legacy, packs, system)
from . import soundboard as sb
from .dsp import (ENHANCE_PRESETS, EQ_BANDS, QUICK_VOICES, VOICE_BANK, VOICE_KEYS, Denoiser,
                  Params, all_voices)
from .engine import AudioEngine, Preview
from .hotkeys import ACTIONS, GlobalHotkeys, HyprlandBinds, pretty, to_portal
from .i18n import LANGUAGES, T, language, set_language
from .widgets import (ACCENT, SLIDERS, STYLE, CheckListDialog, LevelMeter, ParamSlider, RoundToggle,
                      IconPicker, KeyButton, card, dark_palette, glyph_icon, iconize, key_capture, scroll_page)
from .windows import QuickVoicesWindow, SoundPanelWindow

DEFAULT_SLOTS = ["Robot", "Demonio", "Femenina", "Ardilla", "Radio"]
IS_HYPRLAND = "hyprland" in os.environ.get("XDG_CURRENT_DESKTOP", "").lower()


def default_hotkeys(cfg):
    """Atajos: los generales, F1–F12 para las 12 primeras voces del banco y los
    guardados, convirtiendo los de versiones anteriores (voces rápidas 1–5 y
    atajos de sonidos que solo funcionaban con la ventana activa)."""
    trig = {sid: t for sid, _, t in ACTIONS}
    trig.update({f"voice:{n}": f"F{i}" for i, n in enumerate(list(all_voices())[:12], start=1)})
    saved = dict(cfg.get("hotkeys", {}))
    slots = cfg.get("voice_slots", DEFAULT_SLOTS)
    for i in range(5):
        old = saved.pop(f"voice_{i + 1}", None)
        if old and i < len(slots) and slots[i]:
            saved.setdefault(f"voice:{slots[i]}", old)
    for sid, m in cfg.get("sounds", {}).items():
        if m.get("hotkey"):
            saved.setdefault(f"sound:{sid}", to_portal(m.pop("hotkey")))
    trig.update(saved)
    return trig
MY_SOUNDS = "Mis sonidos"


class _VBCableJob(QObject):
    """Descarga VB-Cable en segundo plano y avisa a la interfaz con señales."""
    progress = Signal(float)
    done = Signal(str)
    failed = Signal(str)

    def start(self):
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        try:
            self.done.emit(str(devices.download_vbcable(self.progress.emit)))
        except Exception as e:
            self.failed.emit(str(e))


class MainWindow(QMainWindow):
    def __init__(self, cfg):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(QIcon(str(ICON_PATH)))
        self.resize(1060, 700)
        self.setAcceptDrops(True)
        self.cfg = cfg
        self.engine = AudioEngine()
        self.hotkeys = GlobalHotkeys(self)
        self.sliders = []          # (key, ParamSlider); key = ("eq", i) para bandas
        self.voice_buttons = []    # (owner, nombre, botón)
        self.custom_voices = {}    # nombre → dict de parámetros de voz
        self.voice_slots = list(DEFAULT_SLOTS)
        self.current_voice = None
        self.last_voice = None     # (nombre o None, dict de parámetros de voz)
        self.params = Params()
        self.sound_buttons = {}    # id → [botón, …] (página y panel)
        self.sound_sections = {}   # owner → [(título, [(nombre, botón)])]
        self.sound_cfg = {}        # id → {name, icon, volume, loop, hotkey}
        self.user_sounds = []
        self.window_state = cfg.get("windows", {})
        self.hotkey_triggers = default_hotkeys(cfg)
        self.key_buttons = {}      # id → KeyButton
        self.hypr_binds = HyprlandBinds(cfg.get("hypr_binds"), self) if IS_HYPRLAND else None
        if self.hypr_binds:
            self.hypr_binds.reloaded.connect(self._show_triggers)
        self._fallback_shortcuts = []
        self._previews = {}
        self._toggles = []         # (botón de encendido, botón de silencio) de otras ventanas
        self._msg = None
        self._quitting = False
        self.quick = None
        self.panel = None

        root = QWidget(objectName="root")
        self.setCentralWidget(root)
        outer = QHBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(self._build_sidebar())
        right = QVBoxLayout()
        right.setSpacing(0)
        right.addWidget(self._build_header())
        self.pages = QStackedWidget()
        for build in (self._page_mic, self._page_voices, self._page_sounds, self._page_effects,
                      self._page_enhance, self._page_eq, self._page_settings):
            self.pages.addWidget(build())
        right.addWidget(self.pages, 1)
        self.status = QLabel(T("Apagado"), objectName="status")
        right.addWidget(self.status)
        outer.addLayout(right, 1)

        self._build_tray()
        self._load_config()
        self.hotkeys.activated.connect(self._on_hotkey)
        self.hotkeys.deactivated.connect(self._on_hotkey_release)
        self.hotkeys.changed.connect(self._on_hotkeys_changed)
        self.hotkeys.status.connect(self._on_hotkeys_status)
        self._start_hotkeys()
        self.timer = QTimer(self, interval=33, timeout=self._tick)
        self.timer.start()
        for key, cls in (("quick_voices", QuickVoicesWindow), ("sound_panel", SoundPanelWindow)):
            if self.window_state.get(key, {}).get("open"):
                QTimer.singleShot(200, lambda k=key: self.toggle_window(k))

    # ================================================================ estructura
    def _build_sidebar(self):
        bar = QFrame(objectName="sidebar")
        bar.setFixedWidth(104)
        lay = QVBoxLayout(bar)
        lay.setContentsMargins(0, 44, 0, 0)
        lay.setSpacing(2)
        self.nav = QButtonGroup(self)
        items = [("mic", "Micrófono"), ("drama", "Voces"), ("volume-2", "Sonidos"), ("sparkles", "Efectos"),
                 ("headphones", "Mejora"), ("sliders-vertical", "Ecualizador"), ("settings", "Ajustes")]
        for i, (glyph, name) in enumerate(items):
            b = QToolButton(objectName="nav")
            b.setText(T(name))
            b.setIcon(glyph_icon(glyph))
            b.setIconSize(QSize(24, 24))
            b.setCheckable(True)
            b.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
            b.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            b.setMinimumHeight(62)
            b.setCursor(Qt.PointingHandCursor)
            self.nav.addButton(b, i)
            lay.addWidget(b)
        self.nav.button(0).setChecked(True)
        self.nav.idClicked.connect(lambda i: self.pages.setCurrentIndex(i))
        lay.addStretch()
        return bar

    def _goto(self, index):
        self.nav.button(index).setChecked(True)
        self.pages.setCurrentIndex(index)

    def _build_header(self):
        h = QFrame(objectName="header")
        lay = QVBoxLayout(h)
        lay.setContentsMargins(20, 12, 20, 12)
        title = QLabel(APP_NAME, objectName="title")
        title.setAlignment(Qt.AlignCenter)
        lay.addWidget(title)
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(QLabel(T("Dispositivo de entrada:")))
        self.device = QComboBox()
        self.device.currentIndexChanged.connect(self._on_device)
        row.addWidget(self.device)
        refresh = QPushButton("⟳", objectName="ghost")
        refresh.setToolTip(T("Actualizar dispositivos"))
        refresh.clicked.connect(lambda: self._fill_devices())
        row.addWidget(refresh)
        row.addStretch()
        lay.addLayout(row)
        return h

    def _add_slider(self, lay, key):
        label, lo, hi, steps, unit, _ = SLIDERS[key]
        s = ParamSlider(label, lo, hi, steps, unit)
        s.key = key
        s.changed.connect(self._on_slider)
        self.sliders.append((key, s))
        lay.addWidget(s)
        return s

    def _pill(self, text, slot, tip=None):
        b = iconize(QPushButton(T(text), objectName="pill"))
        b.setCursor(Qt.PointingHandCursor)
        if tip:
            b.setToolTip(T(tip))
        b.clicked.connect(slot)
        return b

    # ------------------------------------------------------------ página: micrófono
    def _page_mic(self):
        page = QWidget()
        grid = QGridLayout(page)
        grid.setContentsMargins(28, 14, 28, 14)
        grid.setHorizontalSpacing(28)

        col = QVBoxLayout()
        if IS_WINDOWS:
            self.vb_banner = QFrame(objectName="banner")
            bl = QHBoxLayout(self.vb_banner)
            bl.setContentsMargins(12, 8, 12, 8)
            self.vb_text = QLabel(T("⚠ Falta el micrófono virtual para que Discord y otras apps oigan tu voz. "
                                    "Se instala gratis con un clic (VB-Cable)."))
            self.vb_text.setWordWrap(True)
            self.vb_text.setOpenExternalLinks(True)
            bl.addWidget(self.vb_text, 1)
            self.vb_button = QPushButton(T("Instalar con 1 clic"), objectName="apply")
            self.vb_button.setCursor(Qt.PointingHandCursor)
            self.vb_button.clicked.connect(self.install_vbcable)
            bl.addWidget(self.vb_button)
            self.vb_banner.setVisible(not devices.virtual_mic_ready())
            col.addWidget(self.vb_banner)

        top = QHBoxLayout()
        self.meter = LevelMeter()
        top.addStretch()
        top.addWidget(self.meter)
        top.addSpacing(30)
        self.power = RoundToggle(170, T("ENCENDIDO"), T("APAGADO"), T("ACTIVO"), T("ACTIVAR"))
        self.power.setToolTip(T("Encender o apagar el micrófono virtual"))
        self.power.toggled.connect(self._on_power)
        top.addWidget(self.power)
        top.addSpacing(14)
        side_btns = QVBoxLayout()
        self.listen = RoundToggle(104, T("ESCUCHANDO"), T("ESCUCHAR"), "ON", "OFF", glyph="headphones")
        self.listen.setToolTip(T("Escuchar tu voz modificada por los altavoces/auriculares"))
        self.listen.toggled.connect(self._on_monitor)
        side_btns.addWidget(self.listen)
        self.mute = RoundToggle(104, T("SILENCIADO"), T("SILENCIAR"), "ON", "OFF", glyph="mic-off")
        self.mute.setToolTip(T("Silenciar tu voz (los sonidos siguen funcionando)"))
        self.mute.toggled.connect(self.set_muted)
        side_btns.addWidget(self.mute)
        top.addLayout(side_btns)
        top.addStretch(2)
        col.addLayout(top)
        grid.addLayout(col, 0, 0)

        box, lay = card("Ajustes de voz")
        for key in ("pitch", "formant", "bass", "treble", "gain", "denoise"):
            self._add_slider(lay, key)
        grid.addWidget(box, 1, 0)

        side = QVBoxLayout()
        side.addWidget(QLabel(T("Voces rápidas"), objectName="section"))
        self.quick_grid = QGridLayout()
        self.quick_grid.setSpacing(10)
        side.addLayout(self.quick_grid)
        more = QPushButton(T("Ver todas las voces →"), objectName="link")
        more.setCursor(Qt.PointingHandCursor)
        more.clicked.connect(lambda: self._goto(1))
        side.addWidget(more)
        side.addSpacing(6)
        side.addWidget(self._pill("⇄ Normal / última voz", self.toggle_voice,
                                  "Alterna entre tu voz normal y la última voz usada"))
        side.addWidget(self._pill("🪟 Selector de voces", lambda: self.toggle_window("quick_voices")))
        side.addWidget(self._pill("🪟 Panel de sonidos", lambda: self.toggle_window("sound_panel")))
        side.addStretch()
        save = QPushButton(T("GUARDAR"), objectName="apply")
        save.setToolTip(T("Guardar los ajustes actuales como predeterminados"))
        save.setCursor(Qt.PointingHandCursor)
        save.clicked.connect(lambda: self._save_config(announce=True))
        side.addWidget(save)
        grid.addLayout(side, 0, 1, 2, 1)
        grid.setColumnStretch(0, 3)
        grid.setColumnStretch(1, 1)
        return page

    def _rebuild_quick_cards(self):
        self.forget_voice_buttons("mic")
        while self.quick_grid.count():
            w = self.quick_grid.takeAt(0).widget()
            if w:
                w.deleteLater()
        for i, name in enumerate(QUICK_VOICES):
            self.quick_grid.addWidget(self.voice_card(name, owner="mic", size=(110, 80)), i // 2, i % 2)

    # ------------------------------------------------------------ página: voces
    def _page_voices(self):
        area, lay = scroll_page()
        head = QHBoxLayout()
        head.addWidget(QLabel(T("Banco de voces"), objectName="section"))
        head.addStretch()
        for text, slot in (("＋ Guardar voz actual", self._save_custom_voice),
                           ("⬇ Importar…", self._import_voices_dialog),
                           ("⬆ Exportar…", self._export_voices)):
            b = iconize(QPushButton(T(text), objectName="ghost"))
            b.clicked.connect(slot)
            head.addWidget(b)
        lay.addLayout(head)
        hint = QLabel(T("Las voces cambian tono, timbre y efectos. La mejora de audio "
                        "(ruido, compresor…) y el ecualizador se mantienen."), objectName="muted")
        hint.setWordWrap(True)
        lay.addWidget(hint)

        for cat, voices in VOICE_BANK.items():
            lay.addWidget(QLabel(T(cat), objectName="category"))
            g = QGridLayout()
            g.setSpacing(10)
            for i, name in enumerate(voices):
                g.addWidget(self.voice_card(name, owner="bank"), i // 5, i % 5)
            lay.addLayout(g)

        lay.addWidget(QLabel(T("Mis voces"), objectName="category"))
        self.custom_grid = QGridLayout()
        self.custom_grid.setSpacing(10)
        lay.addLayout(self.custom_grid)
        self.custom_empty = QLabel(T("Ajusta los controles a tu gusto y pulsa «Guardar voz actual». "
                                     "Clic derecho sobre una voz propia para renombrarla o borrarla."),
                                   objectName="muted")
        self.custom_empty.setWordWrap(True)
        lay.addWidget(self.custom_empty)
        lay.addStretch()
        return area

    # ------------------------------------------------------------ página: sonidos
    def _page_sounds(self):
        area, lay = scroll_page()
        box, c = card("Soundboard",
                      T("Los sonidos se mezclan con tu voz en {}. Clic para reproducir (otro clic lo detiene). "
                        "Clic derecho: renombrar, icono, volumen, bucle, atajo. Arrastra aquí tus archivos de "
                        "audio o paquetes .vopack.").format(MIC_NAME))
        row = QHBoxLayout()
        for text, slot in (("＋ Añadir sonidos…", self._pick_sounds),
                           ("📦 Importar paquete…", self._import_pack_dialog),
                           ("📦 Exportar paquete…", self._export_pack),
                           ("🪟 Panel", lambda: self.toggle_window("sound_panel"))):
            b = iconize(QPushButton(T(text), objectName="ghost"))
            b.clicked.connect(slot)
            row.addWidget(b)
        row.addStretch()
        c.addLayout(row)
        row = QHBoxLayout()
        stop = iconize(QPushButton(T("⏹ Detener todo"), objectName="ghost"))
        stop.clicked.connect(self.stop_sounds)
        row.addWidget(stop)
        self.sound_filter = QLineEdit()
        self.sound_filter.setPlaceholderText(T("Buscar sonido…"))
        self.sound_filter.setClearButtonEnabled(True)
        self.sound_filter.textChanged.connect(lambda t: self.filter_sounds("page", t))
        row.addWidget(self.sound_filter, 1)
        c.addLayout(row)
        self.sfx_volume = ParamSlider("Volumen de sonidos", 0, 150, 1, " %")
        self.sfx_volume.changed.connect(lambda: self.set_sfx_volume(self.sfx_volume.value()))
        c.addWidget(self.sfx_volume)
        self.duck = ParamSlider("Bajar mi voz al sonar", 0, 100, 1, " %")
        self.duck.changed.connect(self._on_sfx_settings)
        c.addWidget(self.duck)
        self.sfx_monitor = QCheckBox(T("Oír los sonidos en mis auriculares"))
        self.sfx_monitor.toggled.connect(self._on_sfx_settings)
        c.addWidget(self.sfx_monitor)
        lay.addWidget(box)

        self.sounds_box = QVBoxLayout()
        self.sounds_box.setSpacing(8)
        lay.addLayout(self.sounds_box)
        lay.addStretch()
        return area

    # ------------------------------------------------------------ página: efectos
    def _page_effects(self):
        area, lay = scroll_page()
        cols = QHBoxLayout()
        cols.setSpacing(16)
        left, right = QVBoxLayout(), QVBoxLayout()
        left.setSpacing(16)
        right.setSpacing(16)
        groups = [
            (left, "Voz", "El susurro elimina el tono y deja solo el aire.",
             ("whisper", "vibrato", "tremolo")),
            (left, "Carácter", None,
             ("robot", "robot_freq", "radio", "distortion", "bitcrush", "underwater")),
            (right, "Modulación", None, ("chorus", "phaser")),
            (right, "Espacio", None, ("echo", "echo_time", "reverb", "reverb_size")),
        ]
        for col, title, sub, keys in groups:
            box, c = card(title, sub)
            for key in keys:
                self._add_slider(c, key)
            col.addWidget(box)
        right.addStretch()
        left.addStretch()
        cols.addLayout(left, 1)
        cols.addLayout(right, 1)
        lay.addLayout(cols)
        reset = QPushButton(T("Quitar todos los efectos"), objectName="ghost")
        reset.clicked.connect(lambda: self.apply_voice("Natural"))
        lay.addWidget(reset, 0, Qt.AlignRight)
        return area

    # ------------------------------------------------------------ página: mejora
    def _page_enhance(self):
        area, lay = scroll_page()
        box, c = card("Perfiles de mejora", "Limpian y equilibran tu micrófono antes de aplicar la voz.")
        row = QHBoxLayout()
        self.enhance_group = QButtonGroup(self)
        for name in ENHANCE_PRESETS:
            b = QPushButton(T(name), objectName="ghost")
            b.setCheckable(True)
            b.clicked.connect(lambda _=False, n=name: self._apply_enhance(n))
            self.enhance_group.addButton(b)
            row.addWidget(b)
        row.addStretch()
        c.addLayout(row)
        lay.addWidget(box)

        box, c = card("Ruido")
        s = self._add_slider(c, "denoise")
        if not Denoiser.available:
            s.setEnabled(False)
            s.setToolTip(T("Instala pyrnnoise para activar la supresión de ruido IA"))
        vad = QHBoxLayout()
        vad.addWidget(QLabel(T("Voz detectada (IA):"), objectName="muted"))
        self.vad = QProgressBar()
        self.vad.setRange(0, 100)
        self.vad.setTextVisible(False)
        self.vad.setFixedHeight(8)
        vad.addWidget(self.vad, 1)
        c.addLayout(vad)
        self._add_slider(c, "noise_reduction")
        self._add_slider(c, "highpass")
        lay.addWidget(box)

        box, c = card("Dinámica y claridad")
        self._add_slider(c, "deesser")
        self._add_slider(c, "compressor")
        self.limiter = QCheckBox(T("Limitador (evita saturar y picos de volumen)"))
        self.limiter.toggled.connect(self._on_limiter)
        c.addWidget(self.limiter)
        lay.addWidget(box)
        lay.addStretch()
        return area

    # ------------------------------------------------------------ página: ecualizador
    def _page_eq(self):
        area, lay = scroll_page()
        box, c = card("Ecualizador de 5 bandas")
        row = QHBoxLayout()
        for i, f in enumerate(EQ_BANDS):
            label = f"{f // 1000} kHz" if f >= 1000 else f"{f} Hz"
            s = ParamSlider(label, -12, 12, 2, " dB", Qt.Vertical)
            s.setMinimumHeight(260)
            s.key = ("eq", i)
            s.changed.connect(self._on_slider)
            self.sliders.append((s.key, s))
            row.addWidget(s)
        c.addLayout(row)
        reset = QPushButton(T("Restablecer"), objectName="ghost")
        reset.clicked.connect(self._reset_eq)
        c.addWidget(reset, 0, Qt.AlignRight)
        lay.addWidget(box)
        lay.addStretch()
        return area

    # ------------------------------------------------------------ página: ajustes
    def _page_settings(self):
        area, lay = scroll_page()

        box, c = card("Audio")
        row = QHBoxLayout()
        row.addWidget(QLabel(T("Salida para «Escuchar»:")))
        self.monitor_out = QComboBox()
        self.monitor_out.currentIndexChanged.connect(self._on_monitor)
        row.addWidget(self.monitor_out)
        row.addStretch()
        c.addLayout(row)
        row = QHBoxLayout()
        row.addWidget(QLabel(T("Micrófono:")))
        self.ptt_mode = QComboBox()
        self.ptt_mode.addItem(T("Siempre abierto"), False)
        self.ptt_mode.addItem(T("Pulsar para hablar (mantén el atajo)"), True)
        self.ptt_mode.currentIndexChanged.connect(
            lambda: setattr(self.engine, "ptt_mode", self.ptt_mode.currentData()))
        row.addWidget(self.ptt_mode)
        row.addStretch()
        c.addLayout(row)
        row = QHBoxLayout()
        row.addWidget(QLabel(T("Motor de tono:")))
        self.mode = QComboBox()
        self.mode.addItem(T("Calidad: conserva formantes (~27 ms)"), True)
        self.mode.addItem(T("Baja latencia: sin formantes (~5 ms)"), False)
        self.mode.currentIndexChanged.connect(
            lambda: setattr(self.engine.processor, "quality", self.mode.currentData()))
        row.addWidget(self.mode)
        row.addStretch()
        c.addLayout(row)
        row = QHBoxLayout()
        row.addWidget(QLabel(T("Latencia de E/S (ms):")))
        self.latency = QSpinBox()
        self.latency.setRange(5, 200)
        self.latency.setValue(20)
        self.latency.valueChanged.connect(self._on_latency)
        row.addWidget(self.latency)
        row.addStretch()
        c.addLayout(row)
        self.bypass = QCheckBox(T("Bypass (pasar la voz sin ningún procesado)"))
        self.bypass.toggled.connect(lambda v: setattr(self.engine, "bypass", v))
        c.addWidget(self.bypass)
        info = QLabel(T("Con el modulador encendido, en Discord, OBS o cualquier otra app elige "
                        "<b>{}</b> como micrófono.").format(MIC_NAME), objectName="muted")
        info.setWordWrap(True)
        c.addSpacing(6)
        c.addWidget(info)
        lay.addWidget(box)

        box, c = card("Atajos de teclado",
                      "Funcionan aunque estés dentro de un juego o de otra app. Haz clic en una tecla y "
                      "pulsa la nueva; Retroceso la quita y Esc cancela.")
        self.hotkey_status = QLabel(objectName="muted")
        self.hotkey_status.setWordWrap(True)
        c.addWidget(self.hotkey_status)
        self.hotkey_filter = QLineEdit(placeholderText=T("Buscar acción, voz o sonido…"))
        self.hotkey_filter.textChanged.connect(self._filter_hotkeys)
        c.addWidget(self.hotkey_filter)
        self.hotkey_grid = QGridLayout()
        self.hotkey_grid.setHorizontalSpacing(12)
        self.hotkey_grid.setColumnStretch(3, 1)
        c.addLayout(self.hotkey_grid)
        row = QHBoxLayout()
        if system_hotkeys_in_desktop():
            b = QPushButton(T("Cambiar teclas en el sistema…"), objectName="ghost")
            b.clicked.connect(self.hotkeys.configure)
            row.addWidget(b)
        reset = QPushButton(T("Restablecer teclas"), objectName="ghost")
        reset.clicked.connect(self._reset_hotkeys)
        row.addWidget(reset)
        row.addStretch()
        c.addLayout(row)
        lay.addWidget(box)

        box, c = card("Voces rápidas", "Las que salen en el selector de voces y en el menú de la bandeja.")
        grid = QGridLayout()
        self.slot_combos = []
        for i in range(5):
            combo = QComboBox()
            combo.currentIndexChanged.connect(lambda _=0, i=i: self._on_slot_changed(i))
            self.slot_combos.append(combo)
            grid.addWidget(combo, i // 3, i % 3)
        c.addLayout(grid)
        lay.addWidget(box)

        box, c = card("Aplicación")
        row = QHBoxLayout()
        row.addWidget(QLabel(T("Idioma:")))
        self.lang = QComboBox()
        for code, name in LANGUAGES.items():
            self.lang.addItem(name, code)
        self.lang.setCurrentIndex(max(0, self.lang.findData(language())))
        self.lang.currentIndexChanged.connect(self._on_language)
        row.addWidget(self.lang)
        row.addStretch()
        c.addLayout(row)
        self.tray_close = QCheckBox(T("Al cerrar la ventana, seguir funcionando en la bandeja del sistema"))
        c.addWidget(self.tray_close)
        self.autostart = QCheckBox(T("Iniciar con el sistema (minimizado en la bandeja)"))
        try:
            self.autostart.setChecked(system.autostart_enabled())
        except Exception:
            self.autostart.setEnabled(False)
        self.autostart.toggled.connect(self._on_autostart)
        c.addWidget(self.autostart)
        about = QLabel(f"{APP_NAME} {__version__} · <a href='{REPO_URL}'>{REPO_URL}</a>", objectName="muted")
        about.setOpenExternalLinks(True)
        c.addSpacing(6)
        c.addWidget(about)
        lay.addWidget(box)
        lay.addStretch()
        return area

    # ================================================================ voces
    def voice_names(self):
        return list(all_voices()) + sorted(self.custom_voices)

    def voice_label(self, name):
        return name if name in self.custom_voices else T(name)

    def _voice_icon(self, name):
        bank = all_voices()
        return bank[name][0] if name in bank else "star"

    def voice_card(self, name, owner, size=(104, 84), small=False):
        b = QToolButton(objectName="voiceSmall" if small else "voice")
        b.setText(self.voice_label(name))
        b.setToolTip(self.voice_label(name))
        b.setIcon(glyph_icon(self._voice_icon(name), 22 if small else 30, ACCENT))
        b.setIconSize(QSize(22, 22) if small else QSize(30, 30))
        b.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        b.setCheckable(True)
        b.setMinimumSize(*((86, 60) if small else size))
        b.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        b.setCursor(Qt.PointingHandCursor)
        b.clicked.connect(lambda _=False, n=name: self.apply_voice(n))
        if name in self.custom_voices:
            b.setContextMenuPolicy(Qt.CustomContextMenu)
            b.customContextMenuRequested.connect(lambda _pos, n=name, w=b: self._custom_menu(n, w))
        self.voice_buttons.append((owner, name, b))
        return b

    def forget_voice_buttons(self, owner):
        self.voice_buttons = [v for v in self.voice_buttons if v[0] != owner]

    def mark_current_voice(self):
        for _, n, b in self.voice_buttons:
            b.setChecked(n == self.current_voice)

    def _voice_params(self, name):
        if name in self.custom_voices:
            return Params.from_dict(self.custom_voices[name])
        return all_voices()[name][1].copy()

    def _voice_snapshot(self):
        d = self.params.to_dict()
        return {k: d[k] for k in VOICE_KEYS}

    def _is_natural(self):
        nat = Params().to_dict()
        return all(abs(float(self._voice_snapshot()[k]) - float(nat[k])) < 1e-6 for k in VOICE_KEYS)

    def _set_voice(self, params_dict, name):
        p = self.params.copy()
        for k in VOICE_KEYS:
            setattr(p, k, float(params_dict[k]))
        self._show_params(p)
        self._push(p)
        self.current_voice = name
        self.mark_current_voice()

    def apply_voice(self, name):
        if name not in all_voices() and name not in self.custom_voices:
            return
        if not self._is_natural():
            self.last_voice = (self.current_voice, self._voice_snapshot())
        voice = self._voice_params(name).to_dict()
        self._set_voice(voice, name)
        if name != "Natural":
            self.last_voice = (name, {k: voice[k] for k in VOICE_KEYS})
        self._flash(T("Voz «{}» aplicada").format(self.voice_label(name)))

    def toggle_voice(self):
        """Alterna entre la voz normal y la última voz usada."""
        if self._is_natural():
            if not self.last_voice:
                self._flash(T("Aún no has usado ninguna voz"))
                return
            name, snap = self.last_voice
            self._set_voice(snap, name)
            self._flash(T("Voz «{}»").format(self.voice_label(name) if name else T("personalizada")))
        else:
            self.last_voice = (self.current_voice, self._voice_snapshot())
            self._set_voice(Params().to_dict(), "Natural")
            self._flash(T("Voz normal"))

    # ---------------------------------------------------- voces propias
    def _rebuild_custom(self):
        self.forget_voice_buttons("custom")
        while self.custom_grid.count():
            w = self.custom_grid.takeAt(0).widget()
            if w:
                w.deleteLater()
        for i, name in enumerate(sorted(self.custom_voices)):
            self.custom_grid.addWidget(self.voice_card(name, owner="custom"), i // 5, i % 5)
        self.custom_empty.setVisible(not self.custom_voices)
        self._fill_slot_combos()
        self._build_hotkey_rows()
        if self.quick:
            self.quick.rebuild()
        self.mark_current_voice()

    def _unique_voice_name(self, name):
        base, n, out = name, 2, name
        while out in self.custom_voices or out in all_voices():
            out = f"{base} ({n})"
            n += 1
        return out

    def _custom_menu(self, name, widget):
        m = QMenu(self)
        a_ren = m.addAction(T("Renombrar…"))
        a_exp = m.addAction(T("Exportar…"))
        m.addSeparator()
        a_del = m.addAction(T("Borrar «{}»").format(name))
        act = m.exec(widget.mapToGlobal(widget.rect().center()))
        if act is a_del:
            del self.custom_voices[name]
            self.voice_slots = [s if s != name else "" for s in self.voice_slots]
            self.hotkey_triggers.pop(f"voice:{name}", None)
        elif act is a_ren:
            new, ok = QInputDialog.getText(self, T("Renombrar"), T("Nombre:"), text=name)
            new = new.strip()[:40]
            if not ok or not new or new == name:
                return
            new = self._unique_voice_name(new)
            self.custom_voices[new] = self.custom_voices.pop(name)
            self.voice_slots = [s if s != name else new for s in self.voice_slots]
            if f"voice:{name}" in self.hotkey_triggers:
                self.hotkey_triggers[f"voice:{new}"] = self.hotkey_triggers.pop(f"voice:{name}")
            if self.current_voice == name:
                self.current_voice = new
        elif act is a_exp:
            self._export_voices([name])
            return
        else:
            return
        self._rebuild_custom()
        self._save_config()

    def _save_custom_voice(self):
        name, ok = QInputDialog.getText(self, T("Guardar voz"), T("Nombre de la voz:"))
        name = name.strip()[:40]
        if not ok or not name:
            return
        if name in all_voices():
            QMessageBox.warning(self, APP_NAME, T("Ya existe una voz del banco con ese nombre."))
            return
        self.custom_voices[name] = self._voice_snapshot()
        self.current_voice = name
        self._rebuild_custom()
        self._save_config()

    def _export_voices(self, names=None):
        if not self.custom_voices:
            QMessageBox.information(self, APP_NAME, T("Primero guarda alguna voz con «Guardar voz actual»."))
            return
        if names is None:
            dlg = CheckListDialog(self, T("Exportar voces"), T("Elige las voces que quieres compartir:"),
                                  [(n, n) for n in sorted(self.custom_voices)])
            if not dlg.exec():
                return
            names = dlg.selected()
        if not names:
            return
        default = str(Path.home() / (("mis-voces" if len(names) > 1 else names[0]) + packs.VOICE_EXT))
        path, _ = QFileDialog.getSaveFileName(self, T("Exportar voces"), default,
                                              T("Voces de Void of Voices") + f" (*{packs.VOICE_EXT})")
        if not path:
            return
        if not path.endswith(packs.VOICE_EXT):
            path += packs.VOICE_EXT
        packs.export_voices(path, {n: self.custom_voices[n] for n in names})
        self._flash(T("{} voz/voces exportada(s)").format(len(names)))

    def _import_voices_dialog(self):
        path, _ = QFileDialog.getOpenFileName(self, T("Importar voces"), str(Path.home()),
                                              T("Voces de Void of Voices") + f" (*{packs.VOICE_EXT} *{packs.LEGACY_VOICE_EXT} *.json)")
        if path:
            self._import_voices(path)

    def _import_voices(self, path):
        try:
            voices = packs.import_voices(path)
        except packs.PackError as e:
            QMessageBox.warning(self, APP_NAME, T("No se pudo importar: {}").format(e))
            return
        for name, params in voices.items():
            self.custom_voices[self._unique_voice_name(name)] = params
        self._rebuild_custom()
        self._save_config()
        self._goto(1)
        self._flash(T("{} voz/voces importada(s) en «Mis voces»").format(len(voices)))

    # ================================================================ parámetros
    def _show_params(self, p):
        for key, s in self.sliders:
            if isinstance(key, tuple):
                s.set_value(p.eq[key[1]])
            else:
                s.set_value(getattr(p, key) * SLIDERS[key][5])
        self.limiter.blockSignals(True)
        self.limiter.setChecked(p.limiter > 0)
        self.limiter.blockSignals(False)

    def _push(self, p):
        self.params = p
        self.engine.processor.set_params(p.copy())

    def _on_slider(self):
        s = self.sender()
        p = self.params.copy()
        if isinstance(s.key, tuple):
            p.eq[s.key[1]] = s.value()
        else:
            setattr(p, s.key, s.value() / SLIDERS[s.key][5])
        self._show_params(p)   # sincroniza sliders duplicados
        self._push(p)
        if s.key in VOICE_KEYS:
            self.current_voice = None
            self.mark_current_voice()

    def _on_limiter(self, on):
        p = self.params.copy()
        p.limiter = 1.0 if on else 0.0
        self._push(p)

    def _apply_enhance(self, name):
        p = self.params.copy()
        for k, v in ENHANCE_PRESETS[name].items():
            setattr(p, k, float(v))
        self._show_params(p)
        self._push(p)
        self._flash(T("Perfil de mejora «{}» aplicado").format(T(name)))

    def _reset_eq(self):
        p = self.params.copy()
        p.eq = [0.0] * len(EQ_BANDS)
        self._show_params(p)
        self._push(p)

    # ================================================================ soundboard
    def _sound_entries(self):
        return self.user_sounds + sb.builtin_sounds()

    def _sound_meta(self, entry):
        name = entry.get("name_en", entry["name"]) if language() == "en" else entry["name"]
        m = dict(name=name, icon=entry["icon"], volume=100, loop=False, hotkey="")
        m.update(self.sound_cfg.get(entry["id"], {}))
        return m

    def _set_meta(self, sid, **kw):
        self.sound_cfg.setdefault(sid, {}).update(kw)
        self._rebuild_sounds()
        self._save_config()

    def _rebuild_sounds(self):
        self._entries = {e["id"]: e for e in self._sound_entries()}
        self.sound_buttons = {}
        self.rebuild_sound_view("page")
        if self.panel:
            self.rebuild_sound_view("panel")
        self._build_hotkey_rows()

    def rebuild_sound_view(self, owner):
        if not hasattr(self, "_entries"):
            self._entries = {e["id"]: e for e in self._sound_entries()}
        box = self.sounds_box if owner == "page" else self.panel.box
        while box.count():
            item = box.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                lay = item.layout()
                while lay.count():
                    w = lay.takeAt(0).widget()
                    if w:
                        w.deleteLater()
                lay.deleteLater()
        for sid in list(self.sound_buttons):
            self.sound_buttons[sid] = [(o, b) for o, b in self.sound_buttons[sid] if o != owner]
        small = owner == "panel"
        cols = 5
        cats = {}
        for e in self._entries.values():
            cats.setdefault(e["category"], []).append(e)
        if MY_SOUNDS not in cats and owner == "page":
            cats = {MY_SOUNDS: [], **cats}
        sections = []
        for cat, entries in cats.items():
            title = QLabel(T(cat), objectName="category")
            box.addWidget(title)
            g = QGridLayout()
            g.setSpacing(8 if small else 10)
            if not entries:
                hint = QLabel(T("Aún no has añadido sonidos: usa «Añadir sonidos…» o arrastra "
                                "archivos (WAV, MP3, OGG, FLAC)."), objectName="muted")
                hint.setWordWrap(True)
                g.addWidget(hint, 0, 0, 1, cols)
            buttons = []
            for i, e in enumerate(entries):
                m = self._sound_meta(e)
                key = self.trigger_text(f"sound:{e['id']}")
                label = m["name"] + (f"\n⌨ {key}" if key else "")
                b = QToolButton(objectName="voiceSmall" if small else "voice")
                b.setText(label)
                b.setIcon(glyph_icon(m["icon"], 22 if small else 26))
                b.setIconSize(QSize(22, 22) if small else QSize(26, 26))
                b.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
                b.setCheckable(True)
                b.setMinimumSize(*((96, 62) if small else (118, 78)))
                b.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                b.setCursor(Qt.PointingHandCursor)
                tip = T("{} · volumen {} %").format(m["name"], m["volume"]) + (T(" · en bucle") if m["loop"] else "")
                b.setToolTip(tip)
                b.clicked.connect(lambda _=False, s=e["id"]: self.play_sound(s))
                b.setContextMenuPolicy(Qt.CustomContextMenu)
                b.customContextMenuRequested.connect(lambda _pos, s=e["id"], w=b: self._sound_menu(s, w))
                g.addWidget(b, i // cols, i % cols)
                self.sound_buttons.setdefault(e["id"], []).append((owner, b))
                buttons.append((m["name"].lower(), b))
            for c in range(cols):
                g.setColumnStretch(c, 1)
            box.addLayout(g)
            sections.append((title, buttons))
        if small:
            box.addStretch()
        self.sound_sections[owner] = sections
        edit = self.sound_filter if owner == "page" else self.panel.search
        self.filter_sounds(owner, edit.text())
        if owner == "panel":
            self.panel.volume.set_value(self.sfx_volume.value())

    def filter_sounds(self, owner, text):
        text = text.strip().lower()
        for title, buttons in self.sound_sections.get(owner, []):
            visible = 0
            for name, b in buttons:
                show = not text or text in name
                b.setVisible(show)
                visible += show
            title.setVisible(not text or visible > 0)

    def set_sfx_volume(self, v):
        self.engine.soundboard.volume = v / 100
        for s in (self.sfx_volume, getattr(self.panel, "volume", None)):
            if s and s.value() != v:
                s.set_value(v)

    def _on_sfx_settings(self):
        self.engine.soundboard.volume = self.sfx_volume.value() / 100
        self.engine.duck = self.duck.value() / 100
        self.engine.sfx_monitor = self.sfx_monitor.isChecked()

    def play_sound(self, sid):
        e = self._entries.get(sid)
        if not e:
            return
        m = self._sound_meta(e)
        gain = m["volume"] / 100
        try:
            if self.engine.running:
                self.engine.soundboard.play(sid, e["path"], gain, m["loop"])
            else:
                old = self._previews.pop(sid, None)
                if old and old.active:
                    old.stop()
                    return
                data = self.engine.soundboard.preload(sid, e["path"]) * gain * self.engine.soundboard.volume
                sink = self.monitor_out.currentData() or devices.default_output()
                self._previews[sid] = Preview(data, sink)
                self._flash(T("Vista previa en tus altavoces — enciende el modulador para enviarlo al micrófono"))
        except Exception as ex:
            QMessageBox.warning(self, APP_NAME, T("No se pudo reproducir «{}»:\n{}").format(m["name"], ex))

    def stop_sounds(self):
        self.engine.soundboard.stop_all()
        for p in self._previews.values():
            p.stop()
        self._previews.clear()

    def _sound_menu(self, sid, widget):
        e = self._entries[sid]
        m = self._sound_meta(e)
        menu = QMenu(self)
        a_name = menu.addAction(T("Renombrar…"))
        a_icon = menu.addAction(T("Cambiar icono…"))
        a_vol = menu.addAction(T("Volumen… ({} %)").format(m["volume"]))
        a_loop = menu.addAction(T("Repetir en bucle"))
        a_loop.setCheckable(True)
        a_loop.setChecked(m["loop"])
        a_key = menu.addAction(T("Asignar atajo de teclado…"))
        a_nokey = menu.addAction(T("Quitar atajo")) if self.hotkey_triggers.get(f"sound:{sid}") else None
        a_reset = menu.addAction(T("Restablecer")) if self.sound_cfg.get(sid) else None
        a_del = None
        if not e.get("builtin"):
            menu.addSeparator()
            a_del = menu.addAction(T("Eliminar sonido"))
        act = menu.exec(widget.mapToGlobal(widget.rect().center()))
        if act is None:
            return
        if act is a_name:
            name, ok = QInputDialog.getText(self, T("Renombrar"), T("Nombre:"), text=m["name"])
            if ok and name.strip():
                self._set_meta(sid, name=name.strip()[:40])
        elif act is a_icon:
            picker = IconPicker(self, m["icon"])
            if picker.exec() and picker.value:
                self._set_meta(sid, icon=picker.value)
        elif act is a_vol:
            v, ok = QInputDialog.getInt(self, T("Volumen"), T("Volumen del sonido (%):"), m["volume"], 0, 300, 5)
            if ok:
                self._set_meta(sid, volume=v)
        elif act is a_loop:
            self._set_meta(sid, loop=a_loop.isChecked())
        elif act is a_key:
            key = key_capture(self, T("Atajo de teclado"), T("Pulsa la combinación para «{}»:").format(m["name"]))
            if key:
                self._set_hotkey(f"sound:{sid}", to_portal(key))
        elif act is a_nokey:
            self._set_hotkey(f"sound:{sid}", "")
        elif act is a_reset:
            self.sound_cfg.pop(sid, None)
            self._rebuild_sounds()
            self._save_config()
        elif act is a_del:
            self.engine.soundboard.forget(sid)
            sb.delete_user_file(e)
            self.user_sounds = [u for u in self.user_sounds if u["id"] != sid]
            self.sound_cfg.pop(sid, None)
            self._rebuild_sounds()
            self._save_config()

    def _pick_sounds(self):
        exts = " ".join(f"*{x}" for x in sb.IMPORT_EXTS)
        files, _ = QFileDialog.getOpenFileNames(self, T("Añadir sonidos"), str(Path.home()), f"Audio ({exts})")
        self._import_sounds(files)

    def _import_sounds(self, files):
        added, errors = 0, []
        for f in files:
            if not f or Path(f).suffix.lower() not in sb.IMPORT_EXTS:
                if f:
                    errors.append(T("{}: formato no soportado").format(Path(f).name))
                continue
            try:
                entry = sb.import_file(f)
                entry["category"] = MY_SOUNDS
                self.user_sounds.append(entry)
                added += 1
            except Exception as ex:
                errors.append(f"{Path(f).name}: {ex}")
        if added:
            self._rebuild_sounds()
            self._save_config()
            self._flash(T("{} sonido(s) añadido(s) a «Mis sonidos»").format(added))
        if errors:
            QMessageBox.warning(self, APP_NAME, T("No se pudieron añadir:") + "\n" + "\n".join(errors))

    def _export_pack(self):
        entries = list(self._entries.values())
        items = [(e["id"], f"{self._sound_meta(e)['icon']}  {self._sound_meta(e)['name']}  ·  {T(e['category'])}")
                 for e in entries]
        mine = {e["id"] for e in entries if not e.get("builtin")}
        dlg = CheckListDialog(self, T("Exportar paquete de sonidos"),
                              T("Elige los sonidos del paquete (se guardan con su nombre, icono, volumen y bucle):"),
                              items, checked=mine or None)
        if not dlg.exec():
            return
        ids = dlg.selected()
        if not ids:
            return
        name, ok = QInputDialog.getText(self, T("Exportar paquete de sonidos"), T("Nombre del paquete:"),
                                        text=T("Mis sonidos"))
        if not ok or not name.strip():
            return
        path, _ = QFileDialog.getSaveFileName(self, T("Exportar paquete de sonidos"),
                                              str(Path.home() / (name.strip() + packs.PACK_EXT)),
                                              T("Paquete de sonidos") + f" (*{packs.PACK_EXT})")
        if not path:
            return
        if not path.endswith(packs.PACK_EXT):
            path += packs.PACK_EXT
        sounds = []
        for sid in ids:
            e = self._entries[sid]
            m = self._sound_meta(e)
            sounds.append(dict(path=e["path"], name=m["name"], icon=m["icon"], volume=m["volume"], loop=m["loop"]))
        try:
            packs.export_sound_pack(path, name.strip(), sounds)
        except OSError as ex:
            QMessageBox.warning(self, APP_NAME, str(ex))
            return
        self._flash(T("Paquete exportado con {} sonido(s)").format(len(sounds)))

    def _import_pack_dialog(self):
        path, _ = QFileDialog.getOpenFileName(self, T("Importar paquete de sonidos"), str(Path.home()),
                                              T("Paquete de sonidos") + f" (*{packs.PACK_EXT} *{packs.LEGACY_PACK_EXT} *.zip)")
        if path:
            self._import_pack(path)

    def _import_pack(self, path):
        try:
            name, entries, metas, errors = packs.import_sound_pack(path)
        except packs.PackError as e:
            QMessageBox.warning(self, APP_NAME, T("No se pudo importar: {}").format(e))
            return
        self.user_sounds.extend(entries)
        self.sound_cfg.update(metas)
        self._rebuild_sounds()
        self._save_config()
        self._goto(2)
        self._flash(T("Paquete «{}» importado: {} sonido(s)").format(name, len(entries)))
        if errors:
            QMessageBox.warning(self, APP_NAME, T("No se pudieron añadir:") + "\n" + "\n".join(errors))

    # arrastrar y soltar en cualquier parte de la ventana
    def dragEnterEvent(self, ev):
        if ev.mimeData().hasUrls():
            ev.acceptProposedAction()

    def dropEvent(self, ev):
        files = [u.toLocalFile() for u in ev.mimeData().urls() if u.isLocalFile()]
        audio = []
        for f in files:
            ext = Path(f).suffix.lower()
            if ext in (packs.PACK_EXT, packs.LEGACY_PACK_EXT):
                self._import_pack(f)
            elif ext in (packs.VOICE_EXT, packs.LEGACY_VOICE_EXT):
                self._import_voices(f)
            else:
                audio.append(f)
        if audio:
            self._import_sounds(audio)

    # ================================================================ ventanas extra
    def toggle_window(self, key):
        if key == "quick_voices":
            if not self.quick:
                self.quick = QuickVoicesWindow(self)
            self.quick.toggle()
        else:
            if not self.panel:
                self.panel = SoundPanelWindow(self)
                self.rebuild_sound_view("panel")
            self.panel.toggle()

    def register_toggles(self, power_btn, mute_btn):
        self._toggles.append((power_btn, mute_btn))

    # ================================================================ atajos
    def _start_hotkeys(self):
        self.hotkey_status.setText(T("Conectando con el sistema…"))
        if not self.hotkeys.start(self._hotkey_actions()):
            self._enable_fallback_shortcuts(T("Atajos globales no disponibles en este sistema."))

    def _hotkey_items(self):
        """[(sección, id, texto, icono)] de todo lo que puede tener atajo."""
        items = [("General", sid, T(desc), None) for sid, desc, _ in ACTIONS]
        items += [("Voces", f"voice:{n}", self.voice_label(n), self._voice_icon(n)) for n in self.voice_names()]
        for sid, e in getattr(self, "_entries", {}).items():
            m = self._sound_meta(e)
            items.append(("Sonidos", f"sound:{sid}", m["name"], m["icon"]))
        return items

    def _hotkey_actions(self):
        return [(sid, text, self.hotkey_triggers.get(sid, "")) for _, sid, text, _ in self._hotkey_items()]

    def _build_hotkey_rows(self):
        g = self.hotkey_grid
        while g.count():
            w = g.takeAt(0).widget()
            if w:
                w.deleteLater()
        self.key_buttons, self._hotkey_rows = {}, []
        r, section, head = 0, None, None
        for sec, sid, text, icon in self._hotkey_items():
            if sec != section:
                section = sec
                head = QLabel(T(sec), objectName="category")
                g.addWidget(head, r, 0, 1, 3)
                r += 1
            ic = QLabel()
            if icon:
                ic.setPixmap(glyph_icon(icon, 18, ACCENT).pixmap(18, 18))
            label = QLabel(text)
            key = KeyButton(self.hotkey_triggers.get(sid, ""))
            key.changed.connect(lambda t, s=sid: self._set_hotkey(s, t))
            g.addWidget(ic, r, 0)
            g.addWidget(label, r, 1)
            g.addWidget(key, r, 2)
            self.key_buttons[sid] = key
            self._hotkey_rows.append((text.lower(), (ic, label, key), head))
            r += 1
        self._show_triggers()
        self._filter_hotkeys(self.hotkey_filter.text())

    def _filter_hotkeys(self, text):
        words = text.lower().split()
        shown = set()
        for name, widgets, head in self._hotkey_rows:
            ok = all(w in name for w in words)
            for w in widgets:
                w.setVisible(ok)
            if ok:
                shown.add(head)
        for _, _, head in self._hotkey_rows:
            head.setVisible(head in shown)

    def _show_triggers(self):
        """Teclas en los botones y conflictos en rojo; en Hyprland, además, las pone."""
        system = self.hotkeys.backend == "portal" and system_hotkeys_in_desktop()
        busy = set()
        if self.hypr_binds and self.hotkeys.backend == "portal":
            before = dict(self.hypr_binds.applied)
            busy = self.hypr_binds.apply(self._hotkey_actions())
            if self.hypr_binds.applied != before:
                self._save_config()
        used = Counter(self.hotkey_triggers.get(s, "").lower() for s in self.key_buttons)
        for sid, key in self.key_buttons.items():
            t = self.hotkey_triggers.get(sid, "")
            key.setEnabled(not system)
            key.set_trigger(t, (self.hotkeys.triggers.get(sid) or "—") if system else None)
            key.set_conflict(not system and bool(t) and (used[t.lower()] > 1 or sid in busy))
            key.setToolTip(T("Hyprland ya usa esta tecla para otra cosa: elige otra.") if sid in busy
                           else T("Esta tecla ya la usa otra acción.") if key.property("conflict") else "")

    def _set_hotkey(self, sid, trigger):
        self.hotkey_triggers[sid] = trigger
        self._save_config()
        self.hotkeys.stop()
        self._start_hotkeys()
        if sid.startswith("sound:"):
            self._rebuild_sounds()
        else:
            self._show_triggers()
        if self.quick:
            self.quick.rebuild()

    def _reset_hotkeys(self):
        if QMessageBox.question(self, APP_NAME, T("¿Volver a las teclas predeterminadas?")) != QMessageBox.Yes:
            return
        self.hotkey_triggers = default_hotkeys({"voice_slots": self.voice_slots})
        self._set_hotkey("toggle_voice", self.hotkey_triggers["toggle_voice"])
        self._rebuild_sounds()

    def _on_hotkeys_changed(self, triggers):
        if self.hotkeys.backend == "portal" and IS_HYPRLAND:
            self.hotkey_status.setText(T("Atajos globales activos. Las teclas en rojo ya las usa Hyprland u "
                                         "otra acción: pasa el ratón por encima para saber cuál."))
        elif self.hotkeys.backend == "portal":
            self.hotkey_status.setText(T("Atajos globales activos. Puedes cambiar las teclas en la "
                                         "configuración del sistema."))
        elif self.hotkeys.backend == "windows":
            self.hotkey_status.setText(T("Atajos globales activos."))
        self._show_triggers()
        if self.quick:
            self.quick.rebuild()

    def _on_hotkeys_status(self, msg):
        if msg and not self.hotkeys.backend:
            self._enable_fallback_shortcuts(msg)
        elif msg:
            self.hotkey_status.setText(msg)

    def _enable_fallback_shortcuts(self, reason):
        """Si no hay atajos globales, los mismos atajos funcionan con la app activa."""
        for sc in self._fallback_shortcuts:
            sc.setEnabled(False)
            sc.deleteLater()
        self._fallback_shortcuts = []
        for sid, trig in self.hotkey_triggers.items():
            if not trig:
                continue
            sc = QShortcut(QKeySequence(pretty(trig).replace("Espacio", "Space")), self)
            sc.setContext(Qt.ApplicationShortcut)
            sc.activated.connect(lambda s=sid: self._on_hotkey(s))
            self._fallback_shortcuts.append(sc)
        self._show_triggers()
        self.hotkey_status.setText(reason + " " + T("Los atajos funcionarán solo con la ventana de la app activa."))

    def trigger_text(self, sid):
        """Tecla asignada, tal como la verá el usuario ("" si no tiene)."""
        if self.hotkeys.backend == "portal" and system_hotkeys_in_desktop():
            return self.hotkeys.triggers.get(sid, "")
        t = self.hotkey_triggers.get(sid, "")
        return pretty(t) if t else ""

    def _on_hotkey(self, sid):
        if sid == "toggle_voice":
            self.toggle_voice()
        elif sid.startswith("voice:"):
            if sid[6:] in self.voice_names():
                self.apply_voice(sid[6:])
        elif sid.startswith("sound:"):
            if sid[6:] in getattr(self, "_entries", {}):
                self.play_sound(sid[6:])
        elif sid == "mute":
            self.set_muted(not self.engine.muted)
        elif sid == "ptt":
            self.engine.ptt_down = True
        elif sid == "power":
            self.set_power(not self.power.isChecked())
        elif sid == "stop_sounds":
            self.stop_sounds()
        elif sid in ("quick_voices", "sound_panel"):
            self.toggle_window(sid)

    def _on_hotkey_release(self, sid):
        if sid == "ptt":
            self.engine.ptt_down = False

    def _fill_slot_combos(self):
        names = self.voice_names()
        for i, combo in enumerate(self.slot_combos):
            combo.blockSignals(True)
            combo.clear()
            combo.addItem("—", "")
            for n in names:
                combo.addItem(self.voice_label(n), n)
            current = self.voice_slots[i] if i < len(self.voice_slots) else ""
            combo.setCurrentIndex(max(0, combo.findData(current)))
            combo.blockSignals(False)

    def _on_slot_changed(self, i):
        while len(self.voice_slots) < 5:
            self.voice_slots.append("")
        self.voice_slots[i] = self.slot_combos[i].currentData() or ""
        if self.quick:
            self.quick.rebuild()
        self._save_config()

    # ================================================================ audio
    def _fill_devices(self, select=None):
        current = select or self.device.currentData()
        self.device.blockSignals(True)
        self.device.clear()
        try:
            default = devices.default_input()
            for name, desc in devices.list_inputs():
                self.device.addItem(desc, name)
            sinks = devices.list_outputs()
        except Exception as e:
            self._flash(T("Error leyendo dispositivos: {}").format(e), 8)
            sinks, default = [], None
        idx = self.device.findData(current or default)
        self.device.setCurrentIndex(max(idx, 0))
        self.device.blockSignals(False)
        self.engine.source = self.device.currentData()

        cur_sink = self.monitor_out.currentData()
        self.monitor_out.blockSignals(True)
        self.monitor_out.clear()
        self.monitor_out.addItem(T("Predeterminada del sistema"), None)
        for name, desc in sinks:
            self.monitor_out.addItem(desc, name)
        self.monitor_out.setCurrentIndex(max(self.monitor_out.findData(cur_sink), 0))
        self.monitor_out.blockSignals(False)
        if IS_WINDOWS and hasattr(self, "vb_banner"):
            self.vb_banner.setVisible(not devices.virtual_mic_ready())

    # ---------------------------------------------------- VB-Cable (Windows)
    def install_vbcable(self):
        if self.engine.running:
            self.set_power(False)   # PortAudio no puede recargar dispositivos con el audio abierto
        self.vb_button.setEnabled(False)
        self.vb_text.setText(T("Descargando VB-Cable desde su web oficial…"))
        self._vb_job = _VBCableJob()
        self._vb_job.progress.connect(
            lambda f: self.vb_text.setText(T("Descargando VB-Cable desde su web oficial… {} %").format(int(f * 100))))
        self._vb_job.done.connect(self._vbcable_downloaded)
        self._vb_job.failed.connect(self._vbcable_failed)
        self._vb_job.start()

    def _vbcable_downloaded(self, setup):
        try:
            devices.launch_vbcable_setup(setup)
        except devices.VBCableError as e:
            self._vbcable_failed(str(e))
            return
        self.vb_text.setText(T("En la ventana de VB-Cable pulsa «Install Driver» y acepta. "
                               "Void of Voices lo detectará solo cuando termine."))
        self._vb_tries = 0
        self._vb_timer = QTimer(self, interval=3000, timeout=self._vbcable_poll)
        self._vb_timer.start()

    def _vbcable_poll(self):
        self._vb_tries += 1
        if not self.engine.running:
            try:
                devices.refresh()
            except Exception:
                pass
        if devices.virtual_mic_ready():
            self._vb_timer.stop()
            self._fill_devices()
            self.vb_banner.hide()
            QMessageBox.information(self, APP_NAME, T("¡Micrófono virtual instalado! Enciende Void of Voices y, "
                                                      "en Discord u otras apps, elige «CABLE Output» como micrófono."))
        elif self._vb_tries >= 100:   # ~5 minutos
            self._vb_timer.stop()
            self.vb_button.setEnabled(True)
            self.vb_text.setText(T("Si ya terminaste la instalación de VB-Cable, reinicia el PC para completarla."))

    def _vbcable_failed(self, err):
        self.vb_button.setEnabled(True)
        if err == "cancelado":
            self.vb_text.setText(T("Instalación cancelada. Pulsa el botón cuando quieras intentarlo de nuevo."))
            return
        QDesktopServices.openUrl(QUrl(devices.VBCABLE_URL))
        self.vb_text.setText(T("No se pudo instalar automáticamente ({}). Te abrí la web oficial de VB-Cable "
                               "para instalarlo desde ahí.").format(err))

    def _on_device(self):
        self.engine.source = self.device.currentData()
        self.engine.restart()

    def _on_monitor(self):
        self.engine.monitor_sink = self.monitor_out.currentData()
        self.engine.monitor = self.listen.isChecked()

    def _on_latency(self, v):
        self.engine.latency_ms = v
        self.engine.restart()

    def set_power(self, on):
        if self.power.isChecked() != on:
            self.power.setChecked(on)   # dispara _on_power

    def _on_power(self, on):
        try:
            if on:
                self.engine.start()
            else:
                self.engine.stop()
        except Exception as e:
            self.power.blockSignals(True)
            self.power.setChecked(False)
            self.power.blockSignals(False)
            QMessageBox.critical(self, APP_NAME, T("No se pudo iniciar el audio:\n{}").format(e))
        self._update_tray()

    def set_muted(self, on):
        self.engine.muted = bool(on)
        if self.mute.isChecked() != self.engine.muted:
            self.mute.blockSignals(True)
            self.mute.setChecked(self.engine.muted)
            self.mute.blockSignals(False)
        self._flash(T("Micrófono silenciado") if on else T("Micrófono activo"))
        self._update_tray()

    def _flash(self, msg, secs=3):
        self._msg = (msg, time.monotonic() + secs)
        self.status.setText(msg)

    def _tick(self):
        e = self.engine
        self.meter.set_levels(e.level_in, e.level_out)
        self.vad.setValue(int(e.processor.denoiser.speech_prob * 100) if e.running else 0)
        playing = e.soundboard.playing_ids() if e.running else {s for s, p in self._previews.items() if p.active}
        for sid, btns in self.sound_buttons.items():
            for _, b in btns:
                if b.isChecked() != (sid in playing):
                    b.setChecked(sid in playing)
        for power_btn, mute_btn in self._toggles:
            if power_btn and power_btn.isChecked() != e.running:
                power_btn.setChecked(e.running)
            if mute_btn and mute_btn.isChecked() != e.muted:
                mute_btn.setChecked(e.muted)
        if e.error:
            self.status.setText(f"⚠ {e.error}")
            if not e.running and self.power.isChecked():
                self.power.setChecked(False)
        elif self._msg and time.monotonic() < self._msg[1]:
            self.status.setText(self._msg[0])
        elif e.running:
            state = []
            if e.muted:
                state.append(T("silenciado"))
            elif e.ptt_mode and not e.ptt_down:
                key = self.hotkeys.triggers.get("ptt") or pretty(self.hotkey_triggers.get("ptt", ""))
                state.append(T("mantén {} para hablar").format(key))
            if e.monitor:
                state.append(T("escuchando"))
            extra = (" · " + " · ".join(state)) if state else ""
            self.status.setText(T("● En vivo — micrófono virtual «{}» activo").format(MIC_NAME) +
                                f" ({self.device.currentText()}){extra}")
        else:
            self.status.setText(T("Apagado"))

    # ================================================================ bandeja
    def _build_tray(self):
        self.tray = None
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        self.tray = QSystemTrayIcon(QIcon(str(ICON_PATH)), self)
        self.tray.setToolTip(APP_NAME)
        menu = QMenu()
        self.tray_power = QAction(T("Encendido"), menu, checkable=True)
        self.tray_power.triggered.connect(self.set_power)
        self.tray_mute = QAction(T("Silenciar micrófono"), menu, checkable=True)
        self.tray_mute.triggered.connect(self.set_muted)
        menu.addAction(self.tray_power)
        menu.addAction(self.tray_mute)
        menu.addSeparator()
        menu.addAction(glyph_icon("arrow-left-right", 16), T("⇄ Normal / última voz").partition(" ")[2],
                       self.toggle_voice)
        self.tray_voices = menu.addMenu(T("Voces rápidas"))
        self.tray_voices.aboutToShow.connect(self._fill_tray_voices)
        menu.addSeparator()
        menu.addAction(T("Selector de voces"), lambda: self.toggle_window("quick_voices"))
        menu.addAction(T("Panel de sonidos"), lambda: self.toggle_window("sound_panel"))
        menu.addAction(T("Mostrar ventana principal"), self.show_main)
        menu.addSeparator()
        menu.addAction(T("Salir"), self.quit_app)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(lambda r: self.show_main() if r == QSystemTrayIcon.Trigger else None)
        self.tray.show()

    def _fill_tray_voices(self):
        self.tray_voices.clear()
        for i, name in enumerate(self.voice_slots):
            if name:
                act = self.tray_voices.addAction(f"{i + 1}. {self.voice_label(name)}",
                                                 lambda n=name: self.apply_voice(n))
                act.setCheckable(True)
                act.setChecked(name == self.current_voice)

    def _update_tray(self):
        if not self.tray:
            return
        self.tray_power.setChecked(self.engine.running)
        self.tray_mute.setChecked(self.engine.muted)
        state = T("encendido") if self.engine.running else T("apagado")
        if self.engine.muted:
            state += " · " + T("silenciado")
        self.tray.setToolTip(f"{APP_NAME} — {state}")

    def show_main(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def quit_app(self):
        self._quitting = True
        self.close()

    # ================================================================ config
    def _on_language(self):
        lang = self.lang.currentData()
        if lang == language():
            return
        self._save_config()
        r = QMessageBox.question(self, APP_NAME, T("El idioma se aplicará al reiniciar la app. ¿Reiniciar ahora?"))
        if r == QMessageBox.Yes:
            cmd = system.launch_command()
            self.quit_app()
            QProcess.startDetached(cmd[0], cmd[1:])

    def _on_autostart(self, on):
        try:
            system.set_autostart(on)
        except Exception as e:
            QMessageBox.warning(self, APP_NAME, str(e))

    def _load_config(self):
        cfg = self.cfg
        self._fill_devices(cfg.get("source"))
        self.monitor_out.setCurrentIndex(max(self.monitor_out.findData(cfg.get("monitor_sink")), 0))
        self.listen.setChecked(cfg.get("monitor", False))
        self.mode.setCurrentIndex(0 if cfg.get("quality", True) else 1)
        self.engine.processor.quality = self.mode.currentData()
        self.ptt_mode.setCurrentIndex(1 if cfg.get("ptt_mode") else 0)
        self.engine.ptt_mode = self.ptt_mode.currentData()
        self.latency.blockSignals(True)
        self.latency.setValue(cfg.get("latency_ms", 20))
        self.latency.blockSignals(False)
        self.engine.latency_ms = self.latency.value()
        self.tray_close.setChecked(cfg.get("close_to_tray", True))
        self.custom_voices = cfg.get("custom_voices", {})
        slots = cfg.get("voice_slots", DEFAULT_SLOTS)
        self.voice_slots = (list(slots) + [""] * 5)[:5]
        last = cfg.get("last_voice")
        self.last_voice = (last.get("name"), last.get("params")) if isinstance(last, dict) else None
        self._rebuild_quick_cards()
        self._rebuild_custom()
        p = Params.from_dict(cfg.get("params", {}))
        self._show_params(p)
        self._push(p)
        self.current_voice = cfg.get("current_voice")
        self.mark_current_voice()
        self._on_monitor()
        self.sound_cfg = cfg.get("sounds", {})
        self.user_sounds = [u for u in cfg.get("user_sounds", []) if Path(u["path"]).exists()]
        self.sfx_volume.set_value(cfg.get("sfx_volume", 80))
        self.duck.set_value(cfg.get("duck", 0))
        self.sfx_monitor.setChecked(cfg.get("sfx_monitor", True))
        self._on_sfx_settings()
        self._rebuild_sounds()
        self._update_tray()

    def _save_config(self, announce=False):
        for w in (self.quick, self.panel):
            if w and w.isVisible():
                w.save_state()
        data = {
            "language": language(),
            "source": self.device.currentData(),
            "monitor": self.listen.isChecked(),
            "monitor_sink": self.monitor_out.currentData(),
            "quality": self.mode.currentData(),
            "ptt_mode": bool(self.ptt_mode.currentData()),
            "latency_ms": self.latency.value(),
            "close_to_tray": self.tray_close.isChecked(),
            "params": self.params.to_dict(),
            "current_voice": self.current_voice,
            "last_voice": {"name": self.last_voice[0], "params": self.last_voice[1]} if self.last_voice else None,
            "custom_voices": self.custom_voices,
            "voice_slots": self.voice_slots,
            "hotkeys": self.hotkey_triggers,
            "hypr_binds": self.hypr_binds.applied if self.hypr_binds else {},
            "sounds": self.sound_cfg,
            "user_sounds": [{k: u[k] for k in ("id", "path", "name", "icon", "category")} for u in self.user_sounds],
            "sfx_volume": self.sfx_volume.value(),
            "duck": self.duck.value(),
            "sfx_monitor": self.sfx_monitor.isChecked(),
            "windows": self.window_state,
        }
        data["language"] = self.lang.currentData() if hasattr(self, "lang") else language()
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        if announce:
            self._flash(T("Ajustes guardados"))

    def closeEvent(self, ev):
        if self.tray and self.tray_close.isChecked() and not self._quitting:
            ev.ignore()
            self.hide()
            self._save_config()
            if not self.cfg.get("tray_hint_shown"):
                self.cfg["tray_hint_shown"] = True
                self.tray.showMessage(APP_NAME, T("Sigo funcionando en la bandeja del sistema. "
                                                  "Usa «Salir» en su menú para cerrarme del todo."),
                                      QIcon(str(ICON_PATH)), 5000)
            return
        if self.hypr_binds:
            self.hypr_binds.clear()
        self._save_config()
        for w in (self.quick, self.panel):
            if w:
                w.close()
        self.stop_sounds()
        self.hotkeys.stop()
        self.engine.stop()
        if self.tray:
            self.tray.hide()
        super().closeEvent(ev)
        QApplication.instance().quit()


def system_hotkeys_in_desktop():
    """En KDE/GNOME las teclas se cambian en la configuración del escritorio
    (portal). En Hyprland el portal no asigna teclas: se eligen en la app."""
    return not IS_WINDOWS and not IS_HYPRLAND


def _load_cfg():
    try:
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def selftest():
    """Comprobación sin ventana para la compilación automática (CI)."""
    import numpy as np
    from .dsp import Processor
    from .soundboard import builtin_sounds, load_audio
    p = Processor()
    params = Params(pitch=5, formant=3, robot=0.5, reverb=0.4, chorus=0.3, denoise=1.0, compressor=0.5)
    p.set_params(params)
    x = (np.random.default_rng(0).standard_normal(48000) * 0.1).astype(np.float32)
    y = np.concatenate([p.process(x[i:i + 256]) for i in range(0, len(x), 256)])
    # Que la voz cambie de verdad: un tono de 220 Hz a +12 semitonos debe salir a ~440 Hz.
    p = Processor()
    p.set_params(Params(pitch=12))
    t = np.arange(48000) / 48000
    tone = (0.3 * np.sin(2 * np.pi * 220 * t)).astype(np.float32)
    out = np.concatenate([p.process(tone[i:i + 256]) for i in range(0, len(tone), 256)])[24000:]
    peak = float(np.argmax(np.abs(np.fft.rfft(out))) * 48000 / len(out))
    sounds = builtin_sounds()
    data = load_audio(sounds[0]["path"])
    dsp_ok = bool(np.isfinite(y).all()) and abs(peak - 440) < 20
    # Los programas del sistema no deben heredar las librerías empaquetadas (ver main).
    host_env = "_internal" not in os.environ.get("LD_LIBRARY_PATH", "")
    ok = dsp_ok and host_env and Denoiser.available and len(sounds) > 40 and len(data) > 1000
    print(f"{APP_NAME} {__version__} selftest: rnnoise={Denoiser.available} sonidos={len(sounds)} "
          f"tono={peak:.0f}Hz dsp={'ok' if dsp_ok else 'ERROR'} entorno={'ok' if host_env else 'ERROR'} "
          f"-> {'OK' if ok else 'FALLO'}")
    return 0 if ok else 1


def main():
    # Selector de archivos nativo del escritorio (KDE/GNOME) vía portal.
    if getattr(sys, "frozen", False) and not IS_WINDOWS:
        # PyInstaller pone sus librerías en LD_LIBRARY_PATH y los programas del
        # sistema que lanzamos (pactl, hyprctl…) cargarían su libstdc++ antigua y
        # fallarían. El proceso actual ya las tiene resueltas: se restaura el original.
        orig = os.environ.pop("LD_LIBRARY_PATH_ORIG", None)
        if orig is None:
            os.environ.pop("LD_LIBRARY_PATH", None)
        else:
            os.environ["LD_LIBRARY_PATH"] = orig
    if "--selftest" in sys.argv:
        return selftest()
    if not IS_WINDOWS:
        os.environ.setdefault("QT_QPA_PLATFORMTHEME", "xdgdesktopportal")
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(__version__)
    app.setDesktopFileName(APP_ID)
    app.setWindowIcon(QIcon(str(ICON_PATH)))
    QFontDatabase.addApplicationFont(str(EMOJI_FONT))
    app.setQuitOnLastWindowClosed(False)

    # Una sola instancia: si ya hay una abierta, se le pide que se muestre.
    server_name = f"voidofvoices-{os.environ.get('USER') or os.environ.get('USERNAME') or 'user'}"
    sock = QLocalSocket()
    sock.connectToServer(server_name)
    if sock.waitForConnected(300):
        sock.write(b"show")
        sock.flush()
        sock.waitForBytesWritten(300)
        return 0
    QLocalServer.removeServer(server_name)
    server = QLocalServer()
    server.listen(server_name)

    migrate_legacy()
    cfg = _load_cfg()
    set_language(cfg.get("language"))
    system.remove_legacy_integration()
    system.install_desktop_entry()
    app.setStyle("Fusion")
    app.setPalette(dark_palette())
    app.setStyleSheet(STYLE)
    w = MainWindow(cfg)
    server.newConnection.connect(lambda: (server.nextPendingConnection(), w.show_main()))
    if "--tray" in sys.argv and w.tray:
        pass  # arranca oculta en la bandeja
    else:
        w.show()
    return app.exec()
