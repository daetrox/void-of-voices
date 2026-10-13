#!/usr/bin/env bash
# Crea Vozcandalo-<versión>-x86_64.AppImage a partir de dist/Vozcandalo (PyInstaller).
# Uso: packaging/linux/build_appimage.sh <versión> [carpeta_dist]
set -euo pipefail
VERSION="${1:?versión}"
DIST="${2:-dist/Vozcandalo}"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
APPDIR="$(mktemp -d)/Vozcandalo.AppDir"
APP_ID="io.github.daetrox.Vozcandalo"

mkdir -p "$APPDIR/usr/lib/vozcandalo" "$APPDIR/usr/share/applications" \
         "$APPDIR/usr/share/icons/hicolor/256x256/apps" "$APPDIR/usr/share/metainfo"
cp -a "$DIST/." "$APPDIR/usr/lib/vozcandalo/"

cat > "$APPDIR/AppRun" <<'RUN'
#!/bin/sh
HERE="$(dirname "$(readlink -f "$0")")"
exec "$HERE/usr/lib/vozcandalo/vozcandalo" "$@"
RUN
chmod +x "$APPDIR/AppRun"

cat > "$APPDIR/$APP_ID.desktop" <<DESK
[Desktop Entry]
Type=Application
Name=Vozcándalo
GenericName=Voice changer
Comment=Cambia tu voz en tiempo real y lanza sonidos
Exec=vozcandalo
Icon=$APP_ID
Terminal=false
Categories=AudioVideo;Audio;
X-AppImage-Version=$VERSION
DESK
cp "$APPDIR/$APP_ID.desktop" "$APPDIR/usr/share/applications/"
cp "$ROOT/vozcandalo/assets/icon.png" "$APPDIR/$APP_ID.png"
cp "$ROOT/vozcandalo/assets/icon.png" "$APPDIR/usr/share/icons/hicolor/256x256/apps/$APP_ID.png"
ln -sf "$APP_ID.png" "$APPDIR/.DirIcon"

TOOL="${APPIMAGETOOL:-appimagetool}"
if ! command -v "$TOOL" >/dev/null 2>&1; then
    TOOL="$(mktemp -d)/appimagetool"
    curl -fsSL -o "$TOOL" \
        "https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage"
    chmod +x "$TOOL"
fi
OUT="$ROOT/Vozcandalo-$VERSION-x86_64.AppImage"
ARCH=x86_64 "$TOOL" --appimage-extract-and-run --no-appstream "$APPDIR" "$OUT"
echo "AppImage: $OUT"
