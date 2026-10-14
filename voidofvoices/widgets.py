"""Estilo y controles reutilizables de la interfaz."""

import math
from functools import lru_cache
from pathlib import Path

from PySide6.QtCore import QByteArray, QEvent, QObject, QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import (QColor, QFont, QIcon, QKeySequence, QLinearGradient, QPainter, QPalette, QPen,
                           QPixmap, QRadialGradient)
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QAbstractButton, QCheckBox, QDialog, QDialogButtonBox, QFileDialog, QFrame, QGridLayout, QHBoxLayout,
    QLabel, QLayout,
    QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QPushButton, QScrollArea, QSizePolicy,
    QSlider, QTabWidget, QToolButton, QVBoxLayout, QWidget,
)

from . import ICON_DIR, USER_ICON_DIR
from .hotkeys import pretty, to_portal
from .i18n import T

# Prefijos de los textos de botones → icono SVG (los textos los conservan para traducirse).
PREFIX_ICONS = {"⇄": "arrow-left-right", "🪟": "app-window", "＋": "plus", "⬇": "download",
                "⬆": "upload", "📦": "package", "⏹": "square-stop", "⏻": "power", "🔇": "mic-off"}

ACCENT = "#5ef0a0"
STYLE = f"""
* {{ font-family: "Inter", "Noto Sans", "Twemoji Mozilla", sans-serif; }}
QMainWindow, #root, #window {{ background: #232527; }}
QToolButton#voiceSmall {{
    background: #2a2c2f; border: 1px solid #3f6e57; border-radius: 8px;
    padding: 4px; font-size: 12px;
}}
QToolButton#voiceSmall:hover {{ border-color: {ACCENT}; }}
QToolButton#voiceSmall:checked {{ border: 2px solid {ACCENT}; background: #2d3a33; }}
QPushButton#pill {{
    background: #2c2e31; border: 1px solid #44474b; border-radius: 14px;
    padding: 6px 14px; font-weight: 600;
}}
QPushButton#pill:hover {{ border-color: {ACCENT}; }}
QPushButton#pill:checked {{ background: #2f5e46; border-color: {ACCENT}; }}
QPushButton#pill[warn="true"]:checked {{ background: #5e2f2f; border-color: #f07a5e; }}
#banner {{ background: #3a3220; border: 1px solid #806a2e; border-radius: 8px; }}
#banner QLabel {{ color: #f3e3b5; }}
#key {{ color: {ACCENT}; font-family: monospace; }}
QToolButton#option {{
    background: #24262a; border: 1px solid #3f6e57; border-radius: 10px; padding: 6px; font-size: 12px;
}}
QToolButton#option:hover {{ border-color: {ACCENT}; background: #22302a; }}
QToolButton#cardToggle {{ background: transparent; border: none; color: {ACCENT}; font-size: 14px; font-weight: 600; }}
#vsep {{ background: #3f4246; max-width: 1px; }}
#meterLabel {{ font-size: 13px; font-weight: 700; letter-spacing: 1px; }}
QToolButton#deckDots {{ background: transparent; border: none; padding: 3px; margin: 2px; }}
QToolButton#deckDots:hover {{ background: #3a3c40; border-radius: 5px; }}
QPushButton#keybind {{
    background: #1c1e20; border: 1px solid #45484d; border-bottom-width: 3px; border-radius: 6px;
    padding: 5px 12px; color: #e8eaec; font-weight: 600;
}}
QPushButton#keybind:hover {{ border-color: {ACCENT}; }}
QPushButton#keybind[capturing="true"] {{ border-color: {ACCENT}; color: {ACCENT}; background: #22302a; }}
QPushButton#keybind[conflict="true"] {{ border-color: #e05555; color: #ff8a8a; }}
QPushButton#keybind:disabled {{ color: #9a9ea3; }}
QListWidget {{ background: #1c1d1f; border: 1px solid #3a3d41; border-radius: 6px; }}
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

@lru_cache(maxsize=None)
def glyph_icon(text, size=28, color="#d9dcdf"):
    """Icono SVG de Lucide si ``text`` es su nombre («mic»), imagen del usuario
    si es «img:archivo»; si no, el carácter/emoji."""
    pm = QPixmap(size * 2, size * 2)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    if text.startswith("img:"):
        img = QPixmap(str(USER_ICON_DIR / Path(text[4:]).name))
        if not img.isNull():
            img = img.scaled(int(size * 1.6), int(size * 1.6), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            p.drawPixmap((pm.width() - img.width()) // 2, (pm.height() - img.height()) // 2, img)
        p.end()
        return QIcon(pm)
    svg = ICON_DIR / f"{text}.svg"
    if text and "/" not in text and svg.is_file():
        data = svg.read_bytes().replace(b"currentColor", color.encode())
        QSvgRenderer(QByteArray(data)).render(p, QRectF(size * 0.25, size * 0.25, size * 1.5, size * 1.5))
        p.end()
        return QIcon(pm)
    f = QFont()
    f.setFamilies([f.family(), "Twemoji Mozilla"])
    f.setPixelSize(int(size * 1.5))
    p.setFont(f)
    p.setPen(QColor(color))
    p.drawText(pm.rect(), Qt.AlignCenter, text)
    p.end()
    return QIcon(pm)


def iconize(button, size=16):
    """«⏹ Detener todo» → icono SVG + «Detener todo»."""
    head, _, rest = button.text().partition(" ")
    if head in PREFIX_ICONS and rest:
        button.setText(rest)
        button.setIcon(glyph_icon(PREFIX_ICONS[head], size))
    return button


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
            side = int(44 * k)
            icon = glyph_icon(self.glyph, side, "#f0f2f4" if on else "#9a9ea3")
            p.drawPixmap(int(c.x() - side / 2), int(c.y() - 62 * k), icon.pixmap(side, side))
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
    """Medidor horizontal por segmentos con escala de -60 a 0 dBFS y caída suave."""

    SEGMENTS = 40
    TICKS = (-60, -48, -36, -24, -12, 0)

    def __init__(self):
        super().__init__()
        self.setMinimumSize(150, 40)
        self.level = 0.0

    def set_level(self, v):
        new = max(0.0, min(1.0, (20 * math.log10(v + 1e-9) + 60) / 60))
        self.level = max(new, self.level - 0.04)
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, bar = self.width(), 16
        seg = w / self.SEGMENTS
        lit = round(self.level * self.SEGMENTS)
        p.setPen(Qt.NoPen)
        for i in range(self.SEGMENTS):
            frac = (i + 1) / self.SEGMENTS
            color = ACCENT if frac <= 0.8 else "#f0c05e" if frac <= 0.95 else "#f05e5e"
            p.setBrush(QColor(color) if i < lit else QColor("#3a3d41"))
            p.drawRoundedRect(QRectF(i * seg + 1, 0, seg - 3, bar), 2, 2)
        f = QFont(self.font())
        f.setPointSizeF(7.5)
        p.setFont(f)
        p.setPen(QColor("#8a8e93"))
        for db in self.TICKS:
            x = (db + 60) / 60 * (w - 1)
            p.drawLine(QPointF(x, bar + 3), QPointF(x, bar + 6))
            label = f"{db} dB" if db == 0 else str(db)
            align = Qt.AlignLeft if db == -60 else Qt.AlignRight if db == 0 else Qt.AlignHCenter
            rect = QRectF(x - (0 if db == -60 else 44 if db == 0 else 22), bar + 7, 44, 14)
            p.drawText(rect, align, label)


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
            name = QLabel(T(label))
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
            name = QLabel(T(label))
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
        lay.addWidget(QLabel(T(title), objectName="cardTitle"))
    if subtitle:
        s = QLabel(T(subtitle), objectName="muted")
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



class CheckListDialog(QDialog):
    """Lista con casillas para elegir qué exportar."""

    def __init__(self, parent, title, text, items, checked=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(420, 480)
        lay = QVBoxLayout(self)
        lbl = QLabel(text)
        lbl.setWordWrap(True)
        lay.addWidget(lbl)
        self.list = QListWidget()
        for key, label in items:
            it = QListWidgetItem(label)
            it.setData(Qt.UserRole, key)
            it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
            it.setCheckState(Qt.Checked if (checked is None or key in checked) else Qt.Unchecked)
            self.list.addItem(it)
        lay.addWidget(self.list, 1)
        row = QHBoxLayout()
        all_ = QCheckBox(T("Marcar todo"))
        all_.setChecked(checked is None)
        all_.toggled.connect(lambda on: [self.list.item(i).setCheckState(Qt.Checked if on else Qt.Unchecked)
                                         for i in range(self.list.count())])
        row.addWidget(all_)
        row.addStretch()
        lay.addLayout(row)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)

    def selected(self):
        return [self.list.item(i).data(Qt.UserRole) for i in range(self.list.count())
                if self.list.item(i).checkState() == Qt.Checked]


def key_capture(parent, title, text):
    """Pide una combinación de teclas; devuelve el texto de QKeySequence o ''."""
    from PySide6.QtWidgets import QKeySequenceEdit
    dlg = QDialog(parent)
    dlg.setWindowTitle(title)
    v = QVBoxLayout(dlg)
    v.addWidget(QLabel(text))
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


class IconPicker(QDialog):
    """Elige el icono de un sonido: SVG de Lucide, emoji o imagen propia.
    Tras exec(), ``value`` tiene el texto del icono (ver glyph_icon)."""

    EMOJIS = ["🔊", "🎵", "🎶", "🎤", "🎧", "📢", "📣", "🔔", "🎺", "🎸", "🥁", "🎹", "👏", "🙌",
              "😂", "🤣", "😮", "😱", "😭", "😡", "😈", "👻", "🤖", "👽", "💀", "🔥", "💥", "⚡",
              "💣", "🎉", "🎊", "🏆", "👑", "💰", "💸", "❤️", "💔", "👍", "👎", "👋", "🤘", "✨",
              "⭐", "💫", "🐶", "🐱", "🐔", "🦆", "🐸", "🐍", "🦁", "🐮", "🚨", "🚀", "🚗", "🚓",
              "⏰", "☎️", "💬", "❓", "❗", "💯", "🎮", "🕹️", "👾", "🍕", "🍺", "💩", "🤡", "🗿"]

    # Sin búsqueda se muestran primero estos (los útiles para sonidos).
    SUGGESTED = ("audio-lines music music-2 mic megaphone bell bell-ring drum guitar piano volume-2 laugh "
                 "smile frown angry annoyed ghost skull bot flame zap bomb siren party-popper trophy crown "
                 "gem coins banknote heart heart-crack thumbs-up thumbs-down hand hand-metal sparkles star "
                 "rocket car ambulance phone phone-call clock alarm-clock door-open dog cat bird fish rabbit "
                 "squirrel rat bug snail turtle egg pizza beer coffee cake gamepad-2 joystick swords sword "
                 "shield target crosshair gift").split()

    def __init__(self, parent, current=""):
        super().__init__(parent)
        self.setWindowTitle(T("Elegir icono"))
        self.resize(600, 500)
        self.value = None
        v = QVBoxLayout(self)
        tabs = QTabWidget()
        v.addWidget(tabs)

        page = QWidget()
        lay = QVBoxLayout(page)
        self.search = QLineEdit(placeholderText=T("Buscar icono en inglés: dog, music, fire, laugh…"))
        lay.addWidget(self.search)
        self.grid = self._grid()
        lay.addWidget(self.grid)
        self._names = sorted(p.stem for p in ICON_DIR.glob("*.svg"))
        self.search.textChanged.connect(self._filter)
        self._filter("")
        tabs.addTab(page, T("Iconos"))

        page = QWidget()
        lay = QVBoxLayout(page)
        grid = self._grid()
        for e in self.EMOJIS:
            grid.addItem(self._item(e))
        lay.addWidget(grid)
        row = QHBoxLayout()
        self.emoji = QLineEdit(placeholderText=T("…o escribe o pega cualquier emoji"))
        use = QPushButton(T("Usar"), objectName="ghost")
        use.clicked.connect(lambda: self.emoji.text().strip() and self._choose(self.emoji.text().strip()[:8]))
        row.addWidget(self.emoji)
        row.addWidget(use)
        lay.addLayout(row)
        tabs.addTab(page, T("Emoji"))

        page = QWidget()
        lay = QVBoxLayout(page)
        lay.addWidget(QLabel(T("Una imagen tuya: PNG, JPG, SVG, WebP o GIF de hasta 2 MB.")))
        pick = QPushButton(T("Elegir imagen…"), objectName="ghost")
        pick.clicked.connect(self._pick_image)
        lay.addWidget(pick, 0, Qt.AlignLeft)
        lay.addStretch()
        tabs.addTab(page, T("Imagen"))

        bb = QDialogButtonBox(QDialogButtonBox.Cancel)
        bb.button(QDialogButtonBox.Cancel).setText(T("Cancelar"))
        bb.rejected.connect(self.reject)
        v.addWidget(bb)
        if current.startswith("img:"):
            tabs.setCurrentIndex(2)
        elif current and not (ICON_DIR / f"{current}.svg").is_file():
            tabs.setCurrentIndex(1)

    def _grid(self):
        lw = QListWidget()
        lw.setViewMode(QListWidget.IconMode)
        lw.setIconSize(QSize(28, 28))
        lw.setGridSize(QSize(50, 50))
        lw.setResizeMode(QListWidget.Adjust)
        lw.setMovement(QListWidget.Static)
        lw.setUniformItemSizes(True)
        lw.itemClicked.connect(lambda it: self._choose(it.data(Qt.UserRole)))
        return lw

    def _item(self, icon):
        it = QListWidgetItem(glyph_icon(icon, 24), "")
        it.setToolTip(icon)
        it.setData(Qt.UserRole, icon)
        return it

    def _filter(self, text):
        self.grid.clear()
        words = text.lower().split()
        names = [n for n in self._names if all(w in n for w in words)]
        if not words:
            names = self.SUGGESTED + [n for n in names if n not in self.SUGGESTED]
        # ponytail: solo los 400 primeros resultados; dibujar los 2.000+ iconos tarda segundos.
        for name in names[:400]:
            self.grid.addItem(self._item(name))

    def _choose(self, value):
        self.value = value
        self.accept()

    def _pick_image(self):
        from .soundboard import save_user_icon
        exts = " ".join(f"*{x}" for x in (".png", ".jpg", ".jpeg", ".svg", ".webp", ".gif"))
        path, _ = QFileDialog.getOpenFileName(self, T("Elegir imagen"), str(Path.home()), f"{T('Imágenes')} ({exts})")
        if not path:
            return
        try:
            self._choose(save_user_icon(Path(path).read_bytes(), Path(path).suffix))
        except (OSError, ValueError) as e:
            QMessageBox.warning(self, T("Elegir imagen"), T("No se pudo usar la imagen: {}").format(e))


class KeyButton(QPushButton):
    """Botón de tecla al estilo de los menús de controles de los juegos: clic,
    pulsar la tecla y listo. Esc cancela; Retroceso o Supr quitan la tecla."""

    changed = Signal(str)   # atajo en formato portal («CTRL+ALT+m», «F1»); "" = sin tecla
    MODIFIERS = (Qt.Key_Shift, Qt.Key_Control, Qt.Key_Alt, Qt.Key_Meta, Qt.Key_AltGr, Qt.Key_Super_L,
                 Qt.Key_Super_R)

    def __init__(self, trigger=""):
        super().__init__(objectName="keybind")
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumWidth(150)
        self.setFocusPolicy(Qt.StrongFocus)
        self.capturing = False
        self.trigger = trigger
        self.clicked.connect(self._start)
        self.set_trigger(trigger)

    def set_trigger(self, trigger, shown=None):
        """shown: texto a mostrar si no es el del atajo (p. ej. el que asignó el sistema)."""
        self.trigger = trigger
        self.setText(shown if shown is not None else (pretty(trigger) if trigger else "—"))

    def _flag(self, name, on):
        if self.property(name) != on:
            self.setProperty(name, on)
            self.style().unpolish(self)
            self.style().polish(self)

    def set_conflict(self, on):
        self._flag("conflict", on)

    def _start(self):
        self.capturing = True
        self._flag("capturing", True)
        self.setText(T("> Pulsa una tecla <"))
        self.grabKeyboard()

    def _stop(self):
        self.capturing = False
        self._flag("capturing", False)
        self.releaseKeyboard()
        self.set_trigger(self.trigger)

    def keyPressEvent(self, e):
        if not self.capturing:
            return super().keyPressEvent(e)
        key = e.key()
        if key in self.MODIFIERS:
            return
        if key == Qt.Key_Escape:
            return self._stop()
        new = "" if key in (Qt.Key_Backspace, Qt.Key_Delete) else \
            to_portal(QKeySequence(e.keyCombination()).toString())
        digit = self._physical_digit(e)
        if new and digit and e.modifiers() & Qt.ShiftModifier:
            # Shift+1 llega como «!» (o «"», «·»… según la distribución): se usa la tecla física.
            new = "+".join(new.split("+")[:-1] + [digit])
        self.trigger = new
        self._stop()
        self.changed.emit(new)

    @staticmethod
    def _physical_digit(e):
        """Número de la fila superior pulsado, sea cual sea la distribución del teclado."""
        import sys
        if sys.platform == "win32":
            vk = e.nativeVirtualKey()          # VK_0..VK_9 no dependen de Shift
            return chr(vk) if 0x30 <= vk <= 0x39 else ""
        sc = e.nativeScanCode()                # keycode de X11/Wayland: 10..19 = 1..0
        # ponytail: solo la fila de números; otras teclas con Shift quedan como las da Qt.
        return "1234567890"[sc - 10] if 10 <= sc <= 19 else ""

    def focusOutEvent(self, e):
        if self.capturing:
            self._stop()
        super().focusOutEvent(e)


class SaveVoiceDialog(QDialog):
    """Nombre e icono para guardar los ajustes actuales como una voz propia."""

    def __init__(self, parent, name="", icon="star"):
        super().__init__(parent)
        self.setWindowTitle(T("Guardar voz"))
        self.icon = icon
        v = QVBoxLayout(self)
        v.addWidget(QLabel(T("Nombre e icono de la voz:")))
        row = QHBoxLayout()
        self.icon_btn = QToolButton(objectName="voice")
        self.icon_btn.setIconSize(QSize(30, 30))
        self.icon_btn.setFixedSize(56, 56)
        self.icon_btn.setToolTip(T("Elegir icono"))
        self.icon_btn.clicked.connect(self._pick)
        row.addWidget(self.icon_btn)
        self.name = QLineEdit(name, placeholderText=T("Mi voz"))
        self.name.setMaxLength(40)
        row.addWidget(self.name, 1)
        v.addLayout(row)
        bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        bb.button(QDialogButtonBox.Save).setText(T("Guardar"))
        bb.button(QDialogButtonBox.Cancel).setText(T("Cancelar"))
        bb.accepted.connect(lambda: self.name.text().strip() and self.accept())
        bb.rejected.connect(self.reject)
        v.addWidget(bb)
        self._show_icon()
        self.name.setFocus()

    def _show_icon(self):
        self.icon_btn.setIcon(glyph_icon(self.icon, 30, ACCENT))

    def _pick(self):
        picker = IconPicker(self, self.icon)
        if picker.exec() and picker.value:
            self.icon = picker.value
            self._show_icon()


class FlowRow(QWidget):
    """Fila de tarjetas que pasa a la línea siguiente las que no caben.
    Las de ``stretch`` (índices) se estiran para llenar su línea."""

    def __init__(self, widgets, stretch=(), spacing=14):
        super().__init__()
        self.items, self.stretch, self.spacing = list(widgets), set(stretch), spacing
        self.v = QVBoxLayout(self)
        self.v.setContentsMargins(0, 0, 0, 0)
        self.v.setSpacing(spacing)
        self.v.setSizeConstraint(QLayout.SetNoConstraint)   # el ancho mínimo lo da minimumSizeHint
        self._rows = None
        self._apply([list(range(len(self.items)))])

    def _rows_for(self, width):
        rows, cur, used = [], [], 0
        for i, w in enumerate(self.items):
            need = w.sizeHint().width()
            if cur and used + self.spacing + need > width:
                rows.append(cur)
                cur, used = [], 0
            used += (self.spacing if cur else 0) + need
            cur.append(i)
        return rows + [cur] if cur else rows

    def _apply(self, rows):
        self._rows = rows
        while self.v.count():
            lay = self.v.takeAt(0).layout()
            while lay and lay.count():
                lay.takeAt(0)
        for row in rows:
            h = QHBoxLayout()
            h.setSpacing(self.spacing)
            for i in row:
                h.addWidget(self.items[i], 1 if i in self.stretch else 0)
            if not self.stretch & set(row):
                h.addStretch()
            self.v.addLayout(h)
        self.updateGeometry()

    def resizeEvent(self, e):
        rows = self._rows_for(e.size().width())
        if rows != self._rows:
            self._apply(rows)
        super().resizeEvent(e)

    def minimumSizeHint(self):
        return QSize(max(w.minimumSizeHint().width() for w in self.items), self.v.minimumSize().height())

    def sizeHint(self):
        return QSize(super().sizeHint().width(), self.v.sizeHint().height())


class ReflowGrid(QWidget):
    """Rejilla de casillas con tantas columnas como quepan (hasta ``max_cols``);
    las filas se reparten la altura disponible."""

    def __init__(self, cell_width, max_cols=6, spacing=8):
        super().__init__()
        self.cell_width, self.max_cols, self.spacing = cell_width, max_cols, spacing
        self.g = QGridLayout(self)
        self.g.setContentsMargins(0, 0, 0, 0)
        self.g.setSpacing(spacing)
        self.g.setSizeConstraint(QLayout.SetNoConstraint)
        self.cells, self.cols = [], 0

    def set_widgets(self, widgets):
        for w in self.cells:
            w.deleteLater()
        self.cells = list(widgets)
        for w in self.cells:
            w.setParent(self)
            w.show()
        self.cols = 0
        self._place(self.width())

    def _place(self, width):
        cols = max(1, min(self.max_cols, (width + self.spacing) // (self.cell_width + self.spacing)))
        if cols == self.cols:
            return
        self.cols = cols
        while self.g.count():
            self.g.takeAt(0)
        for i, w in enumerate(self.cells):
            self.g.addWidget(w, i // cols, i % cols)
        for c in range(self.max_cols):
            self.g.setColumnStretch(c, 1 if c < cols else 0)
        for r in range(len(self.cells)):
            self.g.setRowStretch(r, 1 if r <= (len(self.cells) - 1) // cols else 0)
        self.updateGeometry()

    def resizeEvent(self, e):
        self._place(e.size().width())
        super().resizeEvent(e)

    def minimumSizeHint(self):
        return QSize(self.cell_width, self.g.minimumSize().height())


class _TileScaler(QObject):
    """Ajusta icono y letra de una casilla a su tamaño: en pantalla completa
    las casillas crecen y con tamaños fijos se veían vacías."""

    def eventFilter(self, obj, ev):
        if ev.type() == QEvent.Resize:
            w, h = obj.width(), obj.height()
            side = int(max(26, min(h * 0.38, w * 0.3, 64)))
            if obj.iconSize().width() != side:
                obj.setIconSize(QSize(side, side))
                obj.setIcon(glyph_icon(obj.property("glyph"), side, obj.property("glyphColor")))
                obj.setStyleSheet(f"font-size: {int(max(13, min(h * 0.12, 19)))}px;")
        return False


_scaler = None


def scale_with_size(button, glyph, color="#d9dcdf"):
    """Hace que el icono (``glyph``) y el texto de ``button`` crezcan con él."""
    global _scaler
    _scaler = _scaler or _TileScaler()
    button.setProperty("glyph", glyph)
    button.setProperty("glyphColor", color)
    button.installEventFilter(_scaler)
