# Cambios

## 0.2.2
- Windows: instalación del micrófono virtual (VB-Cable) con un clic desde la app. Lo descarga de la web oficial, verifica su huella SHA-256, abre su instalador y detecta solo cuándo está listo. El instalador de la app ya no manda a descargarlo a mano.

## 0.2.1
- La app pasa a llamarse **Void of Voices** (antes Vozcándalo). Migra sola la configuración, las voces, los sonidos, el lanzador y el inicio automático.
- Windows: información de versión en el `.exe`, sin UPX y con el bootloader de PyInstaller compilado en la propia CI para reducir falsos positivos del antivirus. Firma digital opcional en la CI (secretos `WINDOWS_CERT_PFX` / `WINDOWS_CERT_PASSWORD`).
- Extensiones `.vovoice` y `.vopack`; las antiguas `.vzvoice` y `.vzpack` se siguen importando.

## 0.2.0
- Atajos de teclado globales (portal de KDE/GNOME en Linux, RegisterHotKey en Windows): voz normal ↔ última voz, 5 voces rápidas configurables, silencio, pulsar para hablar, encender/apagar, detener sonidos y abrir ventanas.
- Ventana independiente «Selector de voces» y ventana «Panel de sonidos».
- Silencio rápido y modo «pulsar para hablar».
- Interfaz en español e inglés.
- Exportar/importar voces propias (`.vzvoice`) y paquetes de sonidos (`.vzpack`).
- Icono en la bandeja del sistema, inicio con el sistema, una sola instancia y lanzador en el menú de aplicaciones.
- Versión para Windows (WASAPI + VB-Cable) y compilación automática: AppImage, instalador y ZIP portable.

## 0.1.0
- Primera versión: micrófono virtual, 26 voces, efectos, mejora de audio con IA y soundboard con 52 sonidos.
