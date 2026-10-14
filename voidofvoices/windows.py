"""Ventanas independientes: selector rápido de voces y panel de sonidos.

Son vistas ligeras: toda la lógica vive en MainWindow (``ctrl``), que también
mantiene sincronizados los botones de todas las ventanas.
"""

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (QCheckBox, QGridLayout, QHBoxLayout, QLabel, QLineEdit,
                               QPushButton, QScrollArea, QVBoxLayout, QWidget)

from . import APP_NAME, ICON_PATH
from .i18n import T
from .widgets import ParamSlider, iconize


class _ToolWindow(QWidget):
    key = ""

    def __init__(self, ctrl, title, size):
        super().__init__(None, Qt.Window)
        self.ctrl = ctrl
        self.setObjectName("window")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setWindowTitle(f"{title} — {APP_NAME}")
        self.setWindowIcon(QIcon(str(ICON_PATH)))
        self.resize(*size)
        geo = ctrl.window_state.get(self.key, {}).get("geometry")
        if geo:
            self.restoreGeometry(QByteArray.fromBase64(geo.encode()))

    def set_on_top(self, on):
        visible = self.isVisible()
        self.setWindowFlag(Qt.WindowStaysOnTopHint, on)
        if visible:
            self.show()
        self.ctrl.window_state.setdefault(self.key, {})["on_top"] = on

    def _on_top_box(self):
        box = QCheckBox(T("Siempre encima"))
        box.setChecked(self.ctrl.window_state.get(self.key, {}).get("on_top", True))
        box.toggled.connect(self.set_on_top)
        self.setWindowFlag(Qt.WindowStaysOnTopHint, box.isChecked())
        return box

    def save_state(self):
        st = self.ctrl.window_state.setdefault(self.key, {})
        st["geometry"] = bytes(self.saveGeometry().toBase64()).decode()
        st["open"] = self.isVisible()

    def toggle(self):
        if self.isVisible() and self.isActiveWindow():
            self.hide()
        else:
            self.show()
            self.raise_()
            self.activateWindow()

    def closeEvent(self, ev):
        self.save_state()
        self.ctrl.window_state[self.key]["open"] = False
        super().closeEvent(ev)


def _search_box(placeholder, callback):
    e = QLineEdit()
    e.setPlaceholderText(placeholder)
    e.setClearButtonEnabled(True)
    e.textChanged.connect(callback)
    return e


def _scroll(inner):
    area = QScrollArea()
    area.setWidgetResizable(True)
    area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    inner.setObjectName("page")
    area.setWidget(inner)
    return area


class QuickVoicesWindow(_ToolWindow):
    key = "quick_voices"

    def __init__(self, ctrl):
        super().__init__(ctrl, T("Selector de voces"), (430, 560))
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(10)

        row = QHBoxLayout()
        self.power = iconize(QPushButton(T("⏻ Encendido"), objectName="pill"))
        self.power.setCheckable(True)
        self.power.clicked.connect(lambda on: ctrl.set_power(on))
        row.addWidget(self.power)
        self.mute = iconize(QPushButton(T("🔇 Silencio"), objectName="pill"))
        self.mute.setCheckable(True)
        self.mute.setProperty("warn", True)
        self.mute.clicked.connect(lambda on: ctrl.set_muted(on))
        row.addWidget(self.mute)
        toggle = iconize(QPushButton(T("⇄ Normal / última"), objectName="pill"))
        toggle.setToolTip(T("Alterna entre tu voz normal y la última voz usada"))
        toggle.clicked.connect(ctrl.toggle_voice)
        row.addWidget(toggle)
        lay.addLayout(row)
        ctrl.register_toggles(self.power, self.mute)

        lay.addWidget(QLabel(T("Voces rápidas"), objectName="category"))
        self.slots = QGridLayout()
        self.slots.setSpacing(8)
        lay.addLayout(self.slots)

        lay.addWidget(QLabel(T("Todas las voces"), objectName="category"))
        self.search = _search_box(T("Buscar voz…"), self._filter)
        lay.addWidget(self.search)
        inner = QWidget()
        self.grid = QGridLayout(inner)
        self.grid.setSpacing(8)
        self.grid.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(_scroll(inner), 1)
        lay.addWidget(self._on_top_box())
        self.rebuild()

    def rebuild(self):
        c = self.ctrl
        c.forget_voice_buttons("quick")
        for g in (self.slots, self.grid):
            while g.count():
                w = g.takeAt(0).widget()
                if w:
                    w.deleteLater()
        for i, name in enumerate(c.voice_slots):
            if not name:
                continue
            b = c.voice_card(name, owner="quick", small=True)
            key = c.trigger_text(f"voice:{name}")
            b.setText(f"{b.text()}\n{key}" if key else b.text())
            self.slots.addWidget(b, 0, i)
        self._items = []
        for i, name in enumerate(c.voice_names()):
            b = c.voice_card(name, owner="quick", small=True)
            self.grid.addWidget(b, i // 4, i % 4)
            self._items.append((c.voice_label(name).lower(), b))
        for col in range(4):
            self.grid.setColumnStretch(col, 1)
        self.grid.setRowStretch(self.grid.rowCount(), 1)
        c.mark_current_voice()
        self._filter(self.search.text())

    def _filter(self, text):
        text = text.strip().lower()
        for name, b in getattr(self, "_items", []):
            b.setVisible(not text or text in name)


class SoundPanelWindow(_ToolWindow):
    key = "sound_panel"

    def __init__(self, ctrl):
        super().__init__(ctrl, T("Panel de sonidos"), (620, 520))
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(10)
        row = QHBoxLayout()
        stop = iconize(QPushButton(T("⏹ Detener todo"), objectName="pill"))
        stop.clicked.connect(ctrl.stop_sounds)
        row.addWidget(stop)
        self.mute = iconize(QPushButton(T("🔇 Silencio"), objectName="pill"))
        self.mute.setCheckable(True)
        self.mute.setProperty("warn", True)
        self.mute.clicked.connect(lambda on: ctrl.set_muted(on))
        row.addWidget(self.mute)
        self.search = _search_box(T("Buscar sonido…"), lambda t: ctrl.filter_sounds("panel", t))
        row.addWidget(self.search, 1)
        lay.addLayout(row)
        ctrl.register_toggles(None, self.mute)

        self.volume = ParamSlider("Volumen de sonidos", 0, 150, 1, " %")
        self.volume.changed.connect(lambda: ctrl.set_sfx_volume(self.volume.value()))
        lay.addWidget(self.volume)

        inner = QWidget()
        self.box = QVBoxLayout(inner)
        self.box.setSpacing(6)
        self.box.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(_scroll(inner), 1)
        lay.addWidget(self._on_top_box())
