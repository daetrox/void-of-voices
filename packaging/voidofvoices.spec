# PyInstaller: genera dist/VoidOfVoices/ (carpeta con el ejecutable y sus librerías).
# Uso: pyinstaller packaging/voidofvoices.spec
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
    (str(ROOT / "voidofvoices" / "assets"), "voidofvoices/assets"),
]
hidden = ["sounddevice", "_sounddevice_data"] if WIN else ["jeepney", "jeepney.io.threading"]

# Versión de la app (sin importar el paquete, que necesita Qt).
VERSION = next(line.split('"')[1] for line in (ROOT / "voidofvoices" / "__init__.py").read_text(encoding="utf-8").splitlines()
               if line.startswith("__version__"))

# Información de versión del .exe (nombre, empresa, descripción): sin ella, las
# heurísticas de Windows Defender desconfían más del ejecutable.
version_file = None
if WIN:
    nums = tuple(int(x) for x in (VERSION.split("-")[0].split(".") + ["0", "0", "0"])[:4])
    version_file = Path(workpath) / "version_info.txt"
    version_file.parent.mkdir(parents=True, exist_ok=True)
    version_file.write_text(f"""VSVersionInfo(
  ffi=FixedFileInfo(filevers={nums}, prodvers={nums}, mask=0x3f, flags=0x0, OS=0x40004,
                    fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('040904B0', [
      StringStruct('CompanyName', 'daetrox'),
      StringStruct('FileDescription', 'Void of Voices - real-time voice changer and soundboard'),
      StringStruct('FileVersion', '{VERSION}'),
      StringStruct('InternalName', 'VoidOfVoices'),
      StringStruct('LegalCopyright', 'daetrox - github.com/daetrox/void-of-voices'),
      StringStruct('OriginalFilename', 'VoidOfVoices.exe'),
      StringStruct('ProductName', 'Void of Voices'),
      StringStruct('ProductVersion', '{VERSION}')])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
""", encoding="utf-8")

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
    name="VoidOfVoices" if WIN else "voidofvoices",
    console=False,
    upx=False,          # UPX dispara falsos positivos en los antivirus
    version=str(version_file) if version_file else None,
    icon=str(ROOT / "voidofvoices" / "assets" / "icon.ico") if WIN else None,
)
coll = COLLECT(exe, a.binaries, a.datas, upx=False, name="VoidOfVoices")
