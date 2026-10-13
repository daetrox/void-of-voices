# PyInstaller: genera dist/Vozcandalo/ (carpeta con el ejecutable y sus librerías).
# Uso: pyinstaller packaging/vozcandalo.spec
import importlib.util
import sys
from pathlib import Path

ROOT = Path(SPECPATH).parent
WIN = sys.platform == "win32"

# Librería nativa de RNNoise (sin importar el paquete pyrnnoise, que arrastra dependencias pesadas).
rnn = Path(importlib.util.find_spec("pyrnnoise").submodule_search_locations[0])
rnn_lib = rnn / ("rnnoise.dll" if WIN else "librnnoise.so")

datas = [
    (str(ROOT / "sounds"), "sounds"),
    (str(ROOT / "vozcandalo" / "assets"), "vozcandalo/assets"),
]
hidden = ["sounddevice", "_sounddevice_data"] if WIN else ["jeepney", "jeepney.io.threading"]

a = Analysis(
    [str(ROOT / "main.py")],
    pathex=[str(ROOT)],
    binaries=[(str(rnn_lib), "pyrnnoise")],
    datas=datas,
    hiddenimports=hidden,
    excludes=["tkinter", "matplotlib", "audiolab", "pyrnnoise", "PIL", "IPython", "pytest",
              "PySide6.QtWebEngineCore", "PySide6.QtQml", "PySide6.QtQuick", "PySide6.Qt3DCore",
              "PySide6.QtPdf", "PySide6.QtMultimedia"],
    noarchive=False,
)
# Fuera: integración GTK (arrastra GTK del sistema que compila) y módulos Qt que no se usan.
DROP = ("libgtk-3", "libgdk-3", "libglycin", "libqgtk3", "libQt6Qml", "libQt6Quick", "libQt6Pdf",
        "libQt6VirtualKeyboard", "Qt6Qml", "Qt6Quick", "Qt6Pdf")
a.binaries = [b for b in a.binaries if not any(d in b[0] for d in DROP)]

pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="Vozcandalo" if WIN else "vozcandalo",
    console=False,
    icon=str(ROOT / "vozcandalo" / "assets" / "icon.ico") if WIN else None,
)
coll = COLLECT(exe, a.binaries, a.datas, name="Vozcandalo")
