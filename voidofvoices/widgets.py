"""Estilo y controles reutilizables de la interfaz."""

import math

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import (QColor, QFont, QIcon, QLinearGradient, QPainter, QPalette, QPen,
                           QPixmap, QRadialGradient)
from PySide6.QtWidgets import (
    QAbstractButton, QCheckBox, QDialog, QDialogButtonBox, QFrame, QHBoxLayout, QLabel,
    QListWidget, QListWidgetItem, QScrollArea, QSizePolicy, QSlider, QToolButton,
    QVBoxLayout, QWidget,
)

from .i18n import T

ACCENT = "#5ef0a0"
STYLE = f"""
* {{ font-family: "Inter", "Noto Sans", sans-serif; }}
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
