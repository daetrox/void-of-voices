"""Interfaz gráfica de Vozcándalo (PySide6)."""

import json
import math
import subprocess
import threading
import time
from pathlib import Path

import numpy as np

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import (QColor, QFont, QIcon, QKeySequence, QLinearGradient, QPainter, QPen,
                           QPalette, QPixmap, QRadialGradient, QShortcut)
from PySide6.QtWidgets import (
    QAbstractButton, QApplication, QButtonGroup, QCheckBox, QComboBox, QFrame,
    QGridLayout, QHBoxLayout, QInputDialog, QLabel, QMainWindow, QMenu, QMessageBox,
    QProgressBar, QPushButton, QScrollArea, QSizePolicy, QSlider, QSpinBox,
    QStackedWidget, QToolButton, QVBoxLayout, QWidget, QDialog, QDialogButtonBox,
    QFileDialog, QKeySequenceEdit, QLineEdit,
)

from . import APP_ID, APP_NAME, CONFIG_FILE, MIC_NAME, __version__, migrate_legacy, virtualmic
from .dsp import (ENHANCE_KEYS, ENHANCE_PRESETS, EQ_BANDS, QUICK_VOICES, VOICE_BANK,
                  VOICE_KEYS, Denoiser, Params, all_voices)
from . import soundboard as sb
from .engine import AudioEngine, _FMT

CONFIG = CONFIG_FILE

ACCENT = "#5ef0a0"
STYLE = f"""
* {{ font-family: "Inter", "Noto Sans", sans-serif; }}
QMainWindow, #root {{ background: #232527; }}
QScrollArea, #page {{ background: transparent; border: none; }}
QScrollBar:vertical {{ background: transparent; width: 8px; }}
QScrollBar::handle:vertical {{ background: #44474b; border-radius: 4px; min-height: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
#sidebar {{ background: #1c1d1f; border-right: 1px solid #2c2e31; }}
#header {{ background: #26282b; border-bottom: 1px solid #2c2e31; }}
#title {{ font-size: 20px; font-weight: 500; }}
QToolButton#nav {{
    background: transparent; border: none; border-left: 3px solid transparent;
    color: #9a9ea3; font-size: 12px; padding: 8px 4px;
}}
QToolButton#nav:hover {{ color: #e6e8ea; }}
QToolButton#nav:checked {{ color: #e6e8ea; background: #26282b; border-left: 3px solid {ACCENT}; }}
QComboBox {{
    background: #1c1d1f; border: 1px solid #3a3d41; border-radius: 6px;
    padding: 4px 10px; min-width: 240px;
}}
QComboBox QAbstractItemView {{ background: #1c1d1f; selection-background-color: #2f5e46; }}
#card {{ background: #2c2e31; border-radius: 10px; }}
#cardTitle {{ font-size: 15px; font-weight: 600; }}
#section {{ font-size: 15px; font-weight: 600; }}
#category {{ font-size: 13px; font-weight: 600; color: {ACCENT}; padding-top: 8px; }}
#muted {{ color: #8a8e93; font-size: 12px; }}
#value {{ color: #c8cbcf; }}
QSlider::groove:horizontal {{ height: 4px; background: #44474b; border-radius: 2px; }}
QSlider::sub-page:horizontal {{ background: {ACCENT}; border-radius: 2px; }}
QSlider::handle:horizontal {{
    background: #d9dcdf; width: 16px; height: 16px; margin: -6px 0; border-radius: 8px;
}}
QSlider::groove:vertical {{ width: 4px; background: #44474b; border-radius: 2px; }}
QSlider::add-page:vertical {{ background: {ACCENT}; border-radius: 2px; }}
QSlider::handle:vertical {{
    background: #d9dcdf; width: 16px; height: 16px; margin: 0 -6px; border-radius: 8px;
}}
QToolButton#voice {{
    background: #2a2c2f; border: 1px solid #3f6e57; border-radius: 10px;
    padding: 6px; font-size: 13px;
}}
QToolButton#voice:hover {{ border-color: {ACCENT}; }}
QToolButton#voice:checked {{ border: 2px solid {ACCENT}; background: #2d3a33; }}
QPushButton#apply {{
    background: {ACCENT}; color: #10241a; border: none; border-radius: 8px;
    font-size: 15px; font-weight: 600; padding: 10px;
}}
QPushButton#apply:hover {{ background: #7cf5b4; }}
QPushButton#ghost {{
    background: transparent; border: 1px solid #3a3d41; border-radius: 6px; padding: 6px 14px;
}}
QPushButton#ghost:hover, QPushButton#ghost:checked {{ border-color: {ACCENT}; }}
QPushButton#ghost:checked {{ background: #2d3a33; }}
QPushButton#link {{ background: transparent; border: none; color: {ACCENT}; text-align: left; }}
QCheckBox::indicator {{ width: 18px; height: 18px; }}
QSpinBox {{ background: #1c1d1f; border: 1px solid #3a3d41; border-radius: 6px; padding: 3px 6px; }}
QLineEdit, QKeySequenceEdit QLineEdit {{
    background: #1c1d1f; color: #f0f2f4; border: 1px solid #4a4d52; border-radius: 6px;
    padding: 6px 10px; selection-background-color: #2f5e46;
}}
QLineEdit:focus {{ border-color: {ACCENT}; }}
QMenu {{ background: #2c2e31; border: 1px solid #44474b; padding: 4px; }}
QMenu::item {{ padding: 6px 18px; border-radius: 4px; }}
QMenu::item:selected {{ background: #2f5e46; }}
QMenu::separator {{ height: 1px; background: #44474b; margin: 4px 8px; }}
QDialog QPushButton, QMessageBox QPushButton {{
    background: #34373b; border: 1px solid #4a4d52; border-radius: 6px; padding: 6px 16px; min-width: 70px;
}}
QDialog QPushButton:hover, QMessageBox QPushButton:hover {{ border-color: {ACCENT}; }}
QToolTip {{ background: #2c2e31; color: #e6e8ea; border: 1px solid #44474b; padding: 4px; }}
QProgressBar {{ background: #34373b; border: none; border-radius: 4px; height: 8px; }}
QProgressBar::chunk {{ background: {ACCENT}; border-radius: 4px; }}
#status {{ color: #8a8e93; font-size: 12px; padding: 4px 14px; }}
"""

# key → (etiqueta, mín, máx (en unidades mostradas), pasos por unidad, unidad, factor)
# valor del parámetro = valor mostrado / factor
SLIDERS = {
    "pitch": ("Tono", -12, 12, 2, " st", 1),
    "formant": ("Formantes (timbre)", -12, 12, 2, " st", 1),
    "bass": ("Graves", -12, 12, 2, " dB", 1),
    "treble": ("Agudos", -12, 12, 2, " dB", 1),
    "gain": ("Ganancia", -12, 12, 2, " dB", 1),
    "whisper": ("Susurro", 0, 100, 1, " %", 100),
    "vibrato": ("Vibrato", 0, 100, 1, " %", 100),
    "tremolo": ("Trémolo", 0, 100, 1, " %", 100),
    "robot": ("Robot (modulación)", 0, 100, 1, " %", 100),
    "robot_freq": ("Frecuencia robot", 20, 400, 1, " Hz", 1),
    "radio": ("Radio / teléfono", 0, 100, 1, " %", 100),
    "distortion": ("Distorsión", 0, 100, 1, " %", 100),
    "bitcrush": ("Bitcrush (8-bit)", 0, 100, 1, " %", 100),
    "underwater": ("Bajo el agua", 0, 100, 1, " %", 100),
    "chorus": ("Chorus", 0, 100, 1, " %", 100),
    "phaser": ("Phaser", 0, 100, 1, " %", 100),
    "echo": ("Eco (mezcla)", 0, 100, 1, " %", 100),
    "echo_time": ("Eco (tiempo)", 30, 1000, 1, " ms", 1000),
    "reverb": ("Reverberación", 0, 100, 1, " %", 100),
    "reverb_size": ("Tamaño de sala", 0, 100, 1, " %", 100),
    "denoise": ("Supresión de ruido IA", 0, 100, 1, " %", 100),
    "noise_reduction": ("Puerta de ruido", 0, 10, 1, "", 1),
    "highpass": ("Filtro paso alto", 0, 200, 1, " Hz", 1),
    "deesser": ("De-esser (sibilancias)", 0, 100, 1, " %", 100),
    "compressor": ("Compresor", 0, 100, 1, " %", 100),
}


# ------------------------------------------------------------- widgets

def glyph_icon(text, size=28):
    """Icono a partir de un carácter/emoji, para no depender de ficheros."""
    pm = QPixmap(size * 2, size * 2)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    f = QFont()
    f.setPixelSize(int(size * 1.5))
    p.setFont(f)
    p.setPen(QColor("#d9dcdf"))
    p.drawText(pm.rect(), Qt.AlignCenter, text)
    p.end()
    return QIcon(pm)


class RoundToggle(QAbstractButton):
    """Botón circular con anillo y LED; se usa para Encender y Escuchar."""

    def __init__(self, size, on_text, off_text, on_sub, off_sub, glyph=None):
        super().__init__()
        self.setCheckable(True)
        self.setFixedSize(size, size)
        self.setCursor(Qt.PointingHandCursor)
        self.texts = (on_text, off_text, on_sub, off_sub)
        self.glyph = glyph

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        on = self.isChecked()
        accent = QColor(ACCENT)
        s = self.width()
        k = s / 170  # escala respecto al botón grande
        r = QRectF(self.rect()).adjusted(12 * k, 12 * k, -12 * k, -12 * k)
        c = r.center()

        if on:  # halo
            g = QRadialGradient(c, r.width() / 2 + 12 * k)
            glow = QColor(accent)
            glow.setAlpha(90)
            g.setColorAt(0.75, glow)
            g.setColorAt(1.0, QColor(0, 0, 0, 0))
            p.setPen(Qt.NoPen)
            p.setBrush(g)
            p.drawEllipse(QRectF(self.rect()))

        body = QLinearGradient(r.topLeft(), r.bottomLeft())
        body.setColorAt(0, QColor("#3a3c40"))
        body.setColorAt(1, QColor("#26282b"))
        p.setBrush(body)
        p.setPen(QPen(accent if on else QColor("#4a4d52"), max(3.0, 6 * k)))
        p.drawEllipse(r.adjusted(4 * k, 4 * k, -4 * k, -4 * k))

        on_text, off_text, on_sub, off_sub = self.texts
        if self.glyph:
            f = QFont(self.font())
            f.setPixelSize(int(40 * k))
            p.setFont(f)
            p.setPen(QColor("#f0f2f4") if on else QColor("#9a9ea3"))
            p.drawText(QRectF(r.left(), c.y() - 62 * k, r.width(), 44 * k), Qt.AlignCenter, self.glyph)
        else:
            led = QRectF(0, 0, 18 * k, 18 * k)
            led.moveCenter(c - QPointF(0, 34 * k))
            p.setPen(Qt.NoPen)
            p.setBrush(accent if on else QColor("#55595e"))
            p.drawEllipse(led)

        f = QFont(self.font())
        f.setPointSizeF(13 * k if not self.glyph else 7.5)
        f.setWeight(QFont.DemiBold)
        p.setFont(f)
        p.setPen(QColor("#f0f2f4") if on else QColor("#9a9ea3"))
        p.drawText(QRectF(r.left(), c.y() - 14 * k, r.width(), 24 * k), Qt.AlignCenter,
                   on_text if on else off_text)

        f.setPointSizeF(max(6.5, 8 * k))
        f.setWeight(QFont.Normal)
        p.setFont(f)
        pill = QRectF(0, 0, 66 * k + 8, 18 * k + 2)
        pill.moveCenter(c + QPointF(0, 24 * k))
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#2f5e46") if on else QColor("#34373b"))
        p.drawRoundedRect(pill, pill.height() / 2, pill.height() / 2)
        p.setPen(accent if on else QColor("#9a9ea3"))
        p.drawText(pill, Qt.AlignCenter, on_sub if on else off_sub)


class LevelMeter(QWidget):
    """Dos barras verticales (entrada/salida) con caída suave."""

    def __init__(self):
        super().__init__()
        self.setFixedSize(60, 150)
        self.levels = [0.0, 0.0]

    def set_levels(self, a, b):
        def db(v):  # -60..0 dBFS → 0..1
            return max(0.0, min(1.0, (20 * math.log10(v + 1e-9) + 60) / 60))
        new = [db(a), db(b)]
        self.levels = [max(n, o - 0.04) for n, o in zip(new, self.levels)]
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        h = self.height() - 22
        for i, lv in enumerate(self.levels):
            x = 12 + i * 22
            p.setPen(Qt.NoPen)
            p.setBrush(QColor("#34373b"))
            p.drawRoundedRect(QRectF(x, 0, 12, h), 3, 3)
            fill = h * lv
            p.setBrush(QColor(ACCENT) if lv < 0.9 else QColor("#f0c05e"))
            p.drawRoundedRect(QRectF(x, h - fill, 12, fill), 3, 3)
        p.setPen(QColor(ACCENT))
        f = QFont(self.font())
        f.setPointSize(8)
        p.setFont(f)
        p.drawText(QRectF(0, h + 4, self.width(), 16), Qt.AlignCenter, "IN   OUT")


class ParamSlider(QWidget):
    """Fila: etiqueta · slider · valor actual (o columna si es vertical)."""
    changed = Signal()

    def __init__(self, label, lo, hi, steps=1, unit="", orientation=Qt.Horizontal):
        super().__init__()
        self.steps = steps
        self.unit = unit
        self.slider = QSlider(orientation)
        self.slider.setRange(int(lo * steps), int(hi * steps))
        self.slider.valueChanged.connect(self._on_change)
        self.slider.setCursor(Qt.PointingHandCursor)
        self.value_lbl = QLabel(objectName="value")

        if orientation == Qt.Horizontal:
            lay = QHBoxLayout(self)
            lay.setContentsMargins(0, 2, 0, 2)
            name = QLabel(label)
            name.setFixedWidth(170)
            lay.addWidget(name)
            lay.addWidget(self.slider, 1)
            self.value_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.value_lbl.setFixedWidth(64)
            lay.addWidget(self.value_lbl)
        else:
            lay = QVBoxLayout(self)
            self.value_lbl.setAlignment(Qt.AlignCenter)
            lay.addWidget(self.value_lbl)
            lay.addWidget(self.slider, 1, Qt.AlignHCenter)
            name = QLabel(label)
            name.setAlignment(Qt.AlignCenter)
            lay.addWidget(name)
        self._on_change(self.slider.value(), emit=False)

    def _on_change(self, v, emit=True):
        val = v / self.steps
        txt = f"{val:+g}" if self.slider.minimum() < 0 else f"{val:g}"
        self.value_lbl.setText(f"{txt}{self.unit}")
        if emit:
            self.changed.emit()

    def value(self):
        return self.slider.value() / self.steps

    def set_value(self, v):
        self.slider.blockSignals(True)
        self.slider.setValue(round(v * self.steps))
        self.slider.blockSignals(False)
        self._on_change(self.slider.value(), emit=False)


def card(title=None, subtitle=None):
    f = QFrame(objectName="card")
    lay = QVBoxLayout(f)
    lay.setContentsMargins(18, 14, 18, 14)
    if title:
        lay.addWidget(QLabel(title, objectName="cardTitle"))
    if subtitle:
        s = QLabel(subtitle, objectName="muted")
        s.setWordWrap(True)
        lay.addWidget(s)
    return f, lay


def scroll_page():
    """Página con scroll; devuelve (widget_para_el_stack, layout_del_contenido)."""
    area = QScrollArea()
    area.setWidgetResizable(True)
    area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    inner = QWidget(objectName="page")
    lay = QVBoxLayout(inner)
    lay.setContentsMargins(28, 20, 28, 20)
    lay.setSpacing(16)
    area.setWidget(inner)
    return area, lay


# ------------------------------------------------------------- ventana

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(1040, 680)
        self.engine = AudioEngine()
        self.sliders = []        # (key, ParamSlider); key = ("eq", i) para bandas
        self.voice_buttons = []  # (nombre, botón) de todas las tarjetas de voz
        self.custom_voices = {}  # nombre → dict de parámetros de voz
        self.params = Params()
        self._custom_shown = set()
        self.sound_buttons = {}   # id → botón
        self.sound_cfg = {}       # id → {name, icon, volume, loop, hotkey}
        self.user_sounds = []
        self._shortcuts = []
        self._previews = {}       # id → proceso pacat (vista previa con el modulador apagado)
        self._msg = None

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
        self.status = QLabel("Apagado", objectName="status")
        right.addWidget(self.status)
        outer.addLayout(right, 1)

        self._load_config()
        self.timer = QTimer(self, interval=33, timeout=self._tick)
        self.timer.start()

    # ---------------------------------------------------- construcción
    def _build_sidebar(self):
        bar = QFrame(objectName="sidebar")
        bar.setFixedWidth(104)
        lay = QVBoxLayout(bar)
        lay.setContentsMargins(0, 50, 0, 0)
        lay.setSpacing(2)
        self.nav = QButtonGroup(self)
        items = [("🎙", "Micrófono"), ("🎭", "Voces"), ("🔊", "Sonidos"), ("✨", "Efectos"),
                 ("🎧", "Mejora"), ("🎚", "Ecualizador"), ("⚙", "Ajustes")]
        for i, (glyph, name) in enumerate(items):
            b = QToolButton(objectName="nav")
            b.setText(name)
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
        row.addWidget(QLabel("Dispositivo de entrada:"))
        self.device = QComboBox()
        self.device.currentIndexChanged.connect(self._on_device)
        row.addWidget(self.device)
        refresh = QPushButton("⟳", objectName="ghost")
        refresh.setToolTip("Actualizar dispositivos")
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

    def _voice_card(self, name, icon, size=(104, 84)):
        b = QToolButton(objectName="voice")
        b.setText(name)
        b.setIcon(glyph_icon(icon, 30))
        b.setIconSize(QSize(30, 30))
        b.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        b.setCheckable(True)
        b.setMinimumSize(*size)
        b.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        b.setCursor(Qt.PointingHandCursor)
        b.clicked.connect(lambda _=False, n=name: self._apply_voice(n))
        self.voice_buttons.append((name, b))
        return b

    def _page_mic(self):
        page = QWidget()
        grid = QGridLayout(page)
        grid.setContentsMargins(28, 16, 28, 16)
        grid.setHorizontalSpacing(28)

        top = QHBoxLayout()
        self.meter = LevelMeter()
        top.addStretch()
        top.addWidget(self.meter)
        top.addSpacing(36)
        self.power = RoundToggle(170, "ENCENDIDO", "APAGADO", "ACTIVO", "ACTIVAR")
        self.power.setToolTip("Encender o apagar el micrófono virtual")
        self.power.toggled.connect(self._on_power)
        top.addWidget(self.power)
        top.addSpacing(16)
        self.listen = RoundToggle(110, "ESCUCHANDO", "ESCUCHAR", "ON", "OFF", glyph="🎧")
        self.listen.setToolTip("Escuchar tu voz modificada por los altavoces/auriculares")
        self.listen.toggled.connect(self._on_monitor)
        top.addWidget(self.listen, 0, Qt.AlignVCenter)
        top.addStretch(2)
        grid.addLayout(top, 0, 0)

        box, lay = card("Ajustes de voz")
        for key in ("pitch", "formant", "bass", "treble", "gain", "denoise"):
            self._add_slider(lay, key)
        grid.addWidget(box, 1, 0)

        side = QVBoxLayout()
        side.addWidget(QLabel("Voces rápidas", objectName="section"))
        pg = QGridLayout()
        pg.setSpacing(10)
        bank = all_voices()
        for i, name in enumerate(QUICK_VOICES):
            pg.addWidget(self._voice_card(name, bank[name][0], (110, 84)), i // 2, i % 2)
        side.addLayout(pg)
        more = QPushButton("Ver todas las voces →", objectName="link")
        more.setCursor(Qt.PointingHandCursor)
        more.clicked.connect(lambda: self._goto(1))
        side.addWidget(more)
        side.addStretch()
        save = QPushButton("GUARDAR", objectName="apply")
        save.setToolTip("Guardar los ajustes actuales como predeterminados")
        save.setCursor(Qt.PointingHandCursor)
        save.clicked.connect(self._save_config)
        side.addWidget(save)
        grid.addLayout(side, 0, 1, 2, 1)
        grid.setColumnStretch(0, 3)
        grid.setColumnStretch(1, 1)
        return page

    def _page_voices(self):
        area, lay = scroll_page()
        head = QHBoxLayout()
        head.addWidget(QLabel("Banco de voces", objectName="section"))
        head.addStretch()
        add = QPushButton("＋ Guardar voz actual", objectName="ghost")
        add.clicked.connect(self._save_custom_voice)
        head.addWidget(add)
        lay.addLayout(head)
        hint = QLabel("Las voces cambian tono, timbre y efectos. La mejora de audio "
                      "(ruido, compresor…) y el ecualizador se mantienen.", objectName="muted")
        hint.setWordWrap(True)
        lay.addWidget(hint)

        for cat, voices in VOICE_BANK.items():
            lay.addWidget(QLabel(cat, objectName="category"))
            g = QGridLayout()
            g.setSpacing(10)
            for i, (name, (icon, _)) in enumerate(voices.items()):
                g.addWidget(self._voice_card(name, icon), i // 5, i % 5)
            lay.addLayout(g)

        lay.addWidget(QLabel("Mis voces", objectName="category"))
        self.custom_grid = QGridLayout()
        self.custom_grid.setSpacing(10)
        lay.addLayout(self.custom_grid)
        self.custom_empty = QLabel("Ajusta los controles a tu gusto y pulsa «＋ Guardar voz actual». "
                                   "Clic derecho sobre una voz propia para borrarla.",
                                   objectName="muted")
        self.custom_empty.setWordWrap(True)
        lay.addWidget(self.custom_empty)
        lay.addStretch()
        return area

    def _page_sounds(self):
        area, lay = scroll_page()
        area.setAcceptDrops(True)
        area.dragEnterEvent = lambda ev: ev.acceptProposedAction() if ev.mimeData().hasUrls() else None
        area.dragMoveEvent = area.dragEnterEvent
        area.dropEvent = lambda ev: self._import_sounds([u.toLocalFile() for u in ev.mimeData().urls()])

        box, c = card("Soundboard",
                      f"Los sonidos se mezclan con tu voz en {MIC_NAME}. Clic para reproducir "
                      "(otro clic lo detiene). Clic derecho: renombrar, icono, volumen, bucle, atajo. "
                      "Arrastra aquí tus archivos de audio para añadirlos.")
        row = QHBoxLayout()
        add = QPushButton("＋ Añadir sonidos…", objectName="ghost")
        add.clicked.connect(self._pick_sounds)
        row.addWidget(add)
        stop = QPushButton("⏹ Detener todo", objectName="ghost")
        stop.clicked.connect(self._stop_sounds)
        row.addWidget(stop)
        self.sound_filter = QLineEdit()
        self.sound_filter.setPlaceholderText("Buscar sonido…")
        self.sound_filter.setClearButtonEnabled(True)
        self.sound_filter.textChanged.connect(self._filter_sounds)
        row.addWidget(self.sound_filter, 1)
        c.addLayout(row)
        self.sfx_volume = ParamSlider("Volumen de sonidos", 0, 150, 1, " %")
        self.sfx_volume.changed.connect(self._on_sfx_settings)
        c.addWidget(self.sfx_volume)
        self.duck = ParamSlider("Bajar mi voz al sonar", 0, 100, 1, " %")
        self.duck.changed.connect(self._on_sfx_settings)
        c.addWidget(self.duck)
        self.sfx_monitor = QCheckBox("Oír los sonidos en mis auriculares")
        self.sfx_monitor.toggled.connect(self._on_sfx_settings)
        c.addWidget(self.sfx_monitor)
        lay.addWidget(box)

        self.sounds_box = QVBoxLayout()
        self.sounds_box.setSpacing(8)
        lay.addLayout(self.sounds_box)
        lay.addStretch()
        return area

    # ---------------------------------------------------- soundboard
    def _sound_entries(self):
        return self.user_sounds + sb.builtin_sounds()

    def _sound_meta(self, entry):
        m = dict(name=entry["name"], icon=entry["icon"], volume=100, loop=False, hotkey="")
        m.update(self.sound_cfg.get(entry["id"], {}))
        return m

    def _set_meta(self, sid, **kw):
        self.sound_cfg.setdefault(sid, {}).update(kw)
        self._rebuild_sounds()
        self._save_config()

    def _rebuild_sounds(self):
        while self.sounds_box.count():
            item = self.sounds_box.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                lay = item.layout()
                while lay.count():
                    w = lay.takeAt(0).widget()
                    if w:
                        w.deleteLater()
                lay.deleteLater()
        for sc in self._shortcuts:
            sc.setEnabled(False)
            sc.deleteLater()
        self._shortcuts = []
        self.sound_buttons = {}
        self._sound_entry = {}

        cats = {}
        for e in self._sound_entries():
            cats.setdefault(e["category"], []).append(e)
        if "Mis sonidos" not in cats:
            cats = {"Mis sonidos": [], **cats}
        self._sound_sections = []
        for cat, entries in cats.items():
            title = QLabel(cat, objectName="category")
            self.sounds_box.addWidget(title)
            g = QGridLayout()
            g.setSpacing(10)
            if not entries:
                hint = QLabel("Aún no has añadido sonidos: usa «＋ Añadir sonidos…» o arrastra "
                              "archivos (WAV, MP3, OGG, FLAC).", objectName="muted")
                hint.setWordWrap(True)
                g.addWidget(hint, 0, 0, 1, 5)
            buttons = []
            for i, e in enumerate(entries):
                m = self._sound_meta(e)
                label = m["name"] + (f"\n⌨ {m['hotkey']}" if m["hotkey"] else "")
                b = QToolButton(objectName="voice")
                b.setText(label)
                b.setIcon(glyph_icon(m["icon"], 26))
                b.setIconSize(QSize(26, 26))
                b.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
                b.setCheckable(True)
                b.setMinimumSize(118, 78)
                b.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                b.setCursor(Qt.PointingHandCursor)
                tip = f"{m['name']} · volumen {m['volume']} %" + (" · en bucle" if m["loop"] else "")
                b.setToolTip(tip)
                b.clicked.connect(lambda _=False, sid=e["id"]: self._play_sound(sid))
                b.setContextMenuPolicy(Qt.CustomContextMenu)
                b.customContextMenuRequested.connect(
                    lambda _pos, sid=e["id"], w=b: self._sound_menu(sid, w))
                g.addWidget(b, i // 5, i % 5)
                self.sound_buttons[e["id"]] = b
                self._sound_entry[e["id"]] = e
                buttons.append((m["name"].lower(), b))
                if m["hotkey"]:
                    sc = QShortcut(QKeySequence(m["hotkey"]), self)
                    sc.setContext(Qt.ApplicationShortcut)
                    sc.activated.connect(lambda sid=e["id"]: self._play_sound(sid))
                    self._shortcuts.append(sc)
            for col in range(5):
                g.setColumnStretch(col, 1)
            self.sounds_box.addLayout(g)
            self._sound_sections.append((title, buttons))
        self._filter_sounds(self.sound_filter.text())

    def _filter_sounds(self, text):
        text = text.strip().lower()
        for title, buttons in getattr(self, "_sound_sections", []):
            visible = 0
            for name, b in buttons:
                show = not text or text in name
                b.setVisible(show)
                visible += show
            title.setVisible(not text or visible > 0)

    def _on_sfx_settings(self):
        sbd = self.engine.soundboard
        sbd.volume = self.sfx_volume.value() / 100
        self.engine.duck = self.duck.value() / 100
        self.engine.sfx_monitor = self.sfx_monitor.isChecked()

    def _play_sound(self, sid):
        e = self._sound_entry.get(sid)
        if not e:
            return
        m = self._sound_meta(e)
        gain = m["volume"] / 100
        try:
            if self.engine.running:
                self.engine.soundboard.play(sid, e["path"], gain, m["loop"])
            else:
                self._preview(sid, e["path"], gain)
        except Exception as ex:
            QMessageBox.warning(self, APP_NAME, f"No se pudo reproducir «{m['name']}»:\n{ex}")

    def _preview(self, sid, path, gain):
        """Con el modulador apagado, reproduce solo en tus altavoces."""
        old = self._previews.pop(sid, None)
        if old and old.poll() is None:
            old.terminate()
            return
        data = self.engine.soundboard.preload(sid, path) * gain * self.engine.soundboard.volume
        sink = self.monitor_out.currentData() or virtualmic.default_sink()
        proc = subprocess.Popen(["pacat", "--playback", *_FMT, "-d", sink,
                                 "--client-name=Vozcandalo", "--stream-name=Vista previa"],
                                stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
        def feed():
            try:
                proc.stdin.write(np.clip(data, -1, 1).astype(np.float32).tobytes())
                proc.stdin.close()
            except (BrokenPipeError, ValueError):
                pass
        threading.Thread(target=feed, daemon=True).start()
        self._previews[sid] = proc
        self._flash("Vista previa en tus altavoces — enciende el modulador para enviarlo al micrófono")

    def _preview_ids(self):
        return {sid for sid, p in self._previews.items() if p.poll() is None}

    def _stop_sounds(self):
        self.engine.soundboard.stop_all()
        for p in self._previews.values():
            if p.poll() is None:
                p.terminate()
        self._previews.clear()

    def _sound_menu(self, sid, widget):
        e = self._sound_entry[sid]
        m = self._sound_meta(e)
        menu = QMenu(self)
        a_name = menu.addAction("Renombrar…")
        a_icon = menu.addAction("Cambiar icono…")
        a_vol = menu.addAction(f"Volumen… ({m['volume']} %)")
        a_loop = menu.addAction("Repetir en bucle")
        a_loop.setCheckable(True)
        a_loop.setChecked(m["loop"])
        a_key = menu.addAction("Asignar atajo de teclado…")
        a_nokey = menu.addAction("Quitar atajo") if m["hotkey"] else None
        a_reset = None if not self.sound_cfg.get(sid) else menu.addAction("Restablecer")
        a_del = None
        if not e.get("builtin"):
            menu.addSeparator()
            a_del = menu.addAction("Eliminar sonido")
        act = menu.exec(widget.mapToGlobal(widget.rect().center()))
        if act is None:
            return
        if act is a_name:
            name, ok = QInputDialog.getText(self, "Renombrar", "Nombre:", text=m["name"])
            if ok and name.strip():
                self._set_meta(sid, name=name.strip()[:40])
        elif act is a_icon:
            icon, ok = QInputDialog.getText(self, "Icono", "Emoji o carácter:", text=m["icon"])
            if ok and icon.strip():
                self._set_meta(sid, icon=icon.strip()[:2])
        elif act is a_vol:
            v, ok = QInputDialog.getInt(self, "Volumen", "Volumen del sonido (%):", m["volume"], 0, 300, 5)
            if ok:
                self._set_meta(sid, volume=v)
        elif act is a_loop:
            self._set_meta(sid, loop=a_loop.isChecked())
        elif act is a_key:
            key = self._ask_shortcut(m["name"])
            if key:
                for other, cfg in self.sound_cfg.items():  # un atajo, un sonido
                    if cfg.get("hotkey") == key:
                        cfg["hotkey"] = ""
                self._set_meta(sid, hotkey=key)
        elif act is a_nokey:
            self._set_meta(sid, hotkey="")
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

    def _ask_shortcut(self, name):
        dlg = QDialog(self)
        dlg.setWindowTitle("Atajo de teclado")
        v = QVBoxLayout(dlg)
        v.addWidget(QLabel(f"Pulsa la combinación para «{name}»\n(funciona con la ventana activa):"))
        edit = QKeySequenceEdit()
        edit.setMaximumSequenceLength(1)
        v.addWidget(edit)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)
        v.addWidget(bb)
        edit.setFocus()
        if dlg.exec() == QDialog.Accepted:
            return edit.keySequence().toString()
        return ""

    def _pick_sounds(self):
        exts = " ".join(f"*{x}" for x in sb.IMPORT_EXTS)
        files, _ = QFileDialog.getOpenFileNames(self, "Añadir sonidos", str(Path.home()),
                                                f"Audio ({exts})")
        self._import_sounds(files)

    def _import_sounds(self, files):
        added, errors = 0, []
        for f in files:
            if not f or Path(f).suffix.lower() not in sb.IMPORT_EXTS:
                if f:
                    errors.append(f"{Path(f).name}: formato no soportado")
                continue
            try:
                self.user_sounds.append(sb.import_file(f))
                added += 1
            except Exception as ex:
                errors.append(f"{Path(f).name}: {ex}")
        if added:
            self._rebuild_sounds()
            self._save_config()
            self._flash(f"{added} sonido(s) añadido(s) a «Mis sonidos»")
        if errors:
            QMessageBox.warning(self, APP_NAME, "No se pudieron añadir:\n" + "\n".join(errors))

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
        reset = QPushButton("Quitar todos los efectos", objectName="ghost")
        reset.clicked.connect(lambda: self._apply_voice("Natural"))
        lay.addWidget(reset, 0, Qt.AlignRight)
        return area

    def _page_enhance(self):
        area, lay = scroll_page()
        box, c = card("Perfiles de mejora",
                      "Limpian y equilibran tu micrófono antes de aplicar la voz.")
        row = QHBoxLayout()
        self.enhance_group = QButtonGroup(self)
        for name in ENHANCE_PRESETS:
            b = QPushButton(name, objectName="ghost")
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
            s.setToolTip("Instala pyrnnoise para activar la supresión de ruido IA")
        vad = QHBoxLayout()
        vad.addWidget(QLabel("Voz detectada (IA):", objectName="muted"))
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
        self.limiter = QCheckBox("Limitador (evita saturar y picos de volumen)")
        self.limiter.toggled.connect(self._on_limiter)
        c.addWidget(self.limiter)
        lay.addWidget(box)
        lay.addStretch()
        return area

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
        reset = QPushButton("Restablecer", objectName="ghost")
        reset.clicked.connect(self._reset_eq)
        c.addWidget(reset, 0, Qt.AlignRight)
        lay.addWidget(box)
        lay.addStretch()
        return area

    def _page_settings(self):
        area, lay = scroll_page()
        box, c = card("Audio")
        row = QHBoxLayout()
        row.addWidget(QLabel("Salida para «Escuchar»:"))
        self.monitor_out = QComboBox()
        self.monitor_out.currentIndexChanged.connect(self._on_monitor)
        row.addWidget(self.monitor_out)
        row.addStretch()
        c.addLayout(row)

        row = QHBoxLayout()
        row.addWidget(QLabel("Motor de tono:"))
        self.mode = QComboBox()
        self.mode.addItem("Calidad: conserva formantes (~27 ms)", True)
        self.mode.addItem("Baja latencia: sin formantes (~5 ms)", False)
        self.mode.currentIndexChanged.connect(
            lambda: setattr(self.engine.processor, "quality", self.mode.currentData()))
        row.addWidget(self.mode)
        row.addStretch()
        c.addLayout(row)

        row = QHBoxLayout()
        row.addWidget(QLabel("Latencia de E/S (ms):"))
        self.latency = QSpinBox()
        self.latency.setRange(5, 200)
        self.latency.setValue(20)
        self.latency.valueChanged.connect(self._on_latency)
        row.addWidget(self.latency)
        row.addStretch()
        c.addLayout(row)

        self.bypass = QCheckBox("Bypass (pasar la voz sin ningún procesado)")
        self.bypass.toggled.connect(lambda v: setattr(self.engine, "bypass", v))
        c.addWidget(self.bypass)
        info = QLabel(
            "Con el modulador encendido, en Discord, OBS o cualquier otra app elige "
            f"<b>{MIC_NAME}</b> como micrófono.", objectName="muted")
        info.setWordWrap(True)
        c.addSpacing(8)
        c.addWidget(info)
        lay.addWidget(box)
        lay.addStretch()
        return area

    # ---------------------------------------------------- parámetros
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
        # Sincroniza los sliders duplicados (p. ej. «denoise» en dos páginas).
        self._show_params(p)
        if s.key in VOICE_KEYS:
            self._mark_voice(None)
        self._push(p)

    def _on_limiter(self, on):
        p = self.params.copy()
        p.limiter = 1.0 if on else 0.0
        self._push(p)

    def _mark_voice(self, name):
        for n, b in self.voice_buttons:
            b.setChecked(n == name)

    def _voice_params(self, name):
        if name in self.custom_voices:
            return Params.from_dict(self.custom_voices[name])
        return all_voices()[name][1].copy()

    def _apply_voice(self, name):
        voice = self._voice_params(name)
        p = self.params.copy()
        for k in VOICE_KEYS:
            setattr(p, k, getattr(voice, k))
        self._show_params(p)
        self._push(p)
        self._mark_voice(name)
        self._flash(f"Voz «{name}» aplicada")

    def _apply_enhance(self, name):
        p = self.params.copy()
        for k, v in ENHANCE_PRESETS[name].items():
            setattr(p, k, float(v))
        self._show_params(p)
        self._push(p)
        self._flash(f"Perfil de mejora «{name}» aplicado")

    def _reset_eq(self):
        p = self.params.copy()
        p.eq = [0.0] * len(EQ_BANDS)
        self._show_params(p)
        self._push(p)

    # ---------------------------------------------------- voces propias
    def _rebuild_custom(self):
        self.voice_buttons = [(n, b) for n, b in self.voice_buttons if n not in self._custom_shown]
        while self.custom_grid.count():
            w = self.custom_grid.takeAt(0).widget()
            if w:
                w.deleteLater()
        for i, name in enumerate(sorted(self.custom_voices)):
            b = self._voice_card(name, "⭐")
            b.setContextMenuPolicy(Qt.CustomContextMenu)
            b.customContextMenuRequested.connect(lambda _pos, n=name, w=b: self._custom_menu(n, w))
            self.custom_grid.addWidget(b, i // 5, i % 5)
        self._custom_shown = set(self.custom_voices)
        self.custom_empty.setVisible(not self.custom_voices)

    def _custom_menu(self, name, widget):
        m = QMenu(self)
        act = m.addAction(f"Borrar «{name}»")
        if m.exec(widget.mapToGlobal(widget.rect().center())) is act:
            del self.custom_voices[name]
            self._rebuild_custom()
            self._save_config()

    def _save_custom_voice(self):
        name, ok = QInputDialog.getText(self, "Guardar voz", "Nombre de la voz:")
        name = name.strip()
        if not ok or not name:
            return
        if name in all_voices():
            QMessageBox.warning(self, APP_NAME, "Ya existe una voz del banco con ese nombre.")
            return
        d = self.params.to_dict()
        self.custom_voices[name] = {k: d[k] for k in VOICE_KEYS}
        self._rebuild_custom()
        self._mark_voice(name)
        self._save_config()

    # ---------------------------------------------------- audio
    def _fill_devices(self, select=None):
        current = select or self.device.currentData()
        self.device.blockSignals(True)
        self.device.clear()
        try:
            default = virtualmic.default_source()
            for name, desc in virtualmic.list_sources():
                self.device.addItem(desc, name)
            sinks = virtualmic.list_sinks()
        except Exception as e:
            self._flash(f"Error leyendo dispositivos: {e}", 8)
            sinks, default = [], None
        idx = self.device.findData(current or default)
        self.device.setCurrentIndex(max(idx, 0))
        self.device.blockSignals(False)
        self.engine.source = self.device.currentData()

        cur_sink = self.monitor_out.currentData()
        self.monitor_out.blockSignals(True)
        self.monitor_out.clear()
        self.monitor_out.addItem("Predeterminada del sistema", None)
        for name, desc in sinks:
            self.monitor_out.addItem(desc, name)
        self.monitor_out.setCurrentIndex(max(self.monitor_out.findData(cur_sink), 0))
        self.monitor_out.blockSignals(False)

    def _on_device(self):
        self.engine.source = self.device.currentData()
        self.engine.restart()

    def _on_monitor(self):
        self.engine.monitor_sink = self.monitor_out.currentData()
        self.engine.monitor = self.listen.isChecked()

    def _on_latency(self, v):
        self.engine.latency_ms = v
        self.engine.restart()

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
            QMessageBox.critical(self, APP_NAME, f"No se pudo iniciar el audio:\n{e}")

    def _flash(self, msg, secs=3):
        self._msg = (msg, time.monotonic() + secs)
        self.status.setText(msg)

    def _tick(self):
        e = self.engine
        self.meter.set_levels(e.level_in, e.level_out)
        self.vad.setValue(int(e.processor.denoiser.speech_prob * 100) if e.running else 0)
        playing = e.soundboard.playing_ids() if e.running else self._preview_ids()
        for sid, b in self.sound_buttons.items():
            if b.isChecked() != (sid in playing):
                b.setChecked(sid in playing)
        if e.error:
            self.status.setText(f"⚠ {e.error}")
            if not e.running and self.power.isChecked():
                self.power.setChecked(False)
        elif self._msg and time.monotonic() < self._msg[1]:
            self.status.setText(self._msg[0])
        elif e.running:
            extra = " · escuchando" if e.monitor else ""
            self.status.setText(f"● En vivo — micrófono virtual «{MIC_NAME}» activo "
                                f"({self.device.currentText()}){extra}")
        else:
            self.status.setText("Apagado")

    # ---------------------------------------------------- config
    def _load_config(self):
        cfg = {}
        try:
            cfg = json.loads(CONFIG.read_text())
        except (OSError, ValueError):
            pass
        self._fill_devices(cfg.get("source"))
        self.monitor_out.setCurrentIndex(max(self.monitor_out.findData(cfg.get("monitor_sink")), 0))
        self.listen.setChecked(cfg.get("monitor", False))
        self.mode.setCurrentIndex(0 if cfg.get("quality", True) else 1)
        self.engine.processor.quality = self.mode.currentData()
        self.latency.blockSignals(True)
        self.latency.setValue(cfg.get("latency_ms", 20))
        self.latency.blockSignals(False)
        self.engine.latency_ms = self.latency.value()
        self.custom_voices = cfg.get("custom_voices", {})
        self._custom_shown = set()
        self._rebuild_custom()
        p = Params.from_dict(cfg.get("params", {}))
        self._show_params(p)
        self._push(p)
        self._on_monitor()
        self.sound_cfg = cfg.get("sounds", {})
        self.user_sounds = [u for u in cfg.get("user_sounds", []) if Path(u["path"]).exists()]
        self.sfx_volume.set_value(cfg.get("sfx_volume", 80))
        self.duck.set_value(cfg.get("duck", 0))
        self.sfx_monitor.setChecked(cfg.get("sfx_monitor", True))
        self._on_sfx_settings()
        self._rebuild_sounds()

    def _save_config(self):
        CONFIG.parent.mkdir(parents=True, exist_ok=True)
        CONFIG.write_text(json.dumps({
            "source": self.device.currentData(),
            "monitor": self.listen.isChecked(),
            "monitor_sink": self.monitor_out.currentData(),
            "quality": self.mode.currentData(),
            "latency_ms": self.latency.value(),
            "params": self.params.to_dict(),
            "custom_voices": self.custom_voices,
            "sounds": self.sound_cfg,
            "user_sounds": [{k: u[k] for k in ("id", "path", "name", "icon", "category")}
                            for u in self.user_sounds],
            "sfx_volume": self.sfx_volume.value(),
            "duck": self.duck.value(),
            "sfx_monitor": self.sfx_monitor.isChecked(),
        }, indent=2, ensure_ascii=False))
        self._flash(f"Ajustes guardados en {CONFIG}")

    def closeEvent(self, ev):
        self._stop_sounds()
        self._save_config()
        self.engine.stop()
        super().closeEvent(ev)


def dark_palette():
    """Paleta oscura completa: la usan también los diálogos estándar de Qt
    (abrir archivo, renombrar, avisos), que no siguen la hoja de estilos."""
    pal = QPalette()
    colors = {
        QPalette.Window: "#232527", QPalette.WindowText: "#e6e8ea",
        QPalette.Base: "#1c1d1f", QPalette.AlternateBase: "#26282b",
        QPalette.Text: "#f0f2f4", QPalette.PlaceholderText: "#8a8e93",
        QPalette.Button: "#34373b", QPalette.ButtonText: "#e6e8ea",
        QPalette.Highlight: "#2f5e46", QPalette.HighlightedText: "#ffffff",
        QPalette.ToolTipBase: "#2c2e31", QPalette.ToolTipText: "#e6e8ea",
        QPalette.Link: ACCENT, QPalette.BrightText: "#ffffff",
        QPalette.Light: "#4a4d52", QPalette.Midlight: "#3a3d41", QPalette.Mid: "#2c2e31",
        QPalette.Dark: "#1a1b1d", QPalette.Shadow: "#000000",
    }
    for role, c in colors.items():
        pal.setColor(role, QColor(c))
    for role in (QPalette.WindowText, QPalette.Text, QPalette.ButtonText):
        pal.setColor(QPalette.Disabled, role, QColor("#6a6e73"))
    return pal


def main():
    import os
    import sys
    # Usa el selector de archivos nativo del escritorio (KDE/GNOME) vía portal.
    os.environ.setdefault("QT_QPA_PLATFORMTHEME", "xdgdesktopportal")
    app = QApplication(sys.argv)
    migrate_legacy()
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(__version__)
    app.setDesktopFileName(APP_ID)
    app.setStyle("Fusion")
    app.setPalette(dark_palette())
    app.setStyleSheet(STYLE)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())
