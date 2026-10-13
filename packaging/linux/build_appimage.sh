#!/usr/bin/env bash
# Crea VoidOfVoices-<versión>-x86_64.AppImage a partir de dist/VoidOfVoices (PyInstaller).
# Uso: packaging/linux/build_appimage.sh <versión> [carpeta_dist]
set -euo pipefail
VERSION="${1:?versión}"
DIST="${2:-dist/VoidOfVoices}"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
APPDIR="$(mktemp -d)/VoidOfVoices.AppDir"
APP_ID="io.github.daetrox.VoidOfVoices"

mkdir -p "$APPDIR/usr/lib/voidofvoices" "$APPDIR/usr/share/applications" \
         "$APPDIR/usr/share/icons/hicolor/256x256/apps" "$APPDIR/usr/share/metainfo"
cp -a "$DIST/." "$APPDIR/usr/lib/voidofvoices/"

cat > "$APPDIR/AppRun" <<'RUN'
#!/bin/sh
HERE="$(dirname "$(readlink -f "$0")")"
exec "$HERE/usr/lib/voidofvoices/voidofvoices" "$@"
RUN
chmod +x "$APPDIR/AppRun"

cat > "$APPDIR/$APP_ID.desktop" <<DESK
[Desktop Entry]
Type=Application
Name=Void of Voices
GenericName=Voice changer
Comment=Cambia tu voz en tiempo real y lanza sonidos
Exec=voidofvoices
Icon=$APP_ID
Terminal=false
Categories=AudioVideo;Audio;
X-AppImage-Version=$VERSION
DESK
cp "$APPDIR/$APP_ID.desktop" "$APPDIR/usr/share/applications/"
cp "$ROOT/voidofvoices/assets/icon.png" "$APPDIR/$APP_ID.png"
cp "$ROOT/voidofvoices/assets/icon.png" "$APPDIR/usr/share/icons/hicolor/256x256/apps/$APP_ID.png"
ln -sf "$APP_ID.png" "$APPDIR/.DirIcon"

TOOL="${APPIMAGETOOL:-appimagetool}"
if ! command -v "$TOOL" >/dev/null 2>&1; then
    TOOL="$(mktemp -d)/appimagetool"
    curl -fsSL -o "$TOOL" \
        "https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage"
    chmod +x "$TOOL"
fi
OUT="$ROOT/VoidOfVoices-$VERSION-x86_64.AppImage"
ARCH=x86_64 "$TOOL" --appimage-extract-and-run --no-appstream "$APPDIR" "$OUT"
echo "AppImage: $OUT"
