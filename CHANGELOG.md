# Cambios

## 0.2.5
- **Windows: los emojis ya se ven.** Los iconos con emoji (sonidos, paneles rápidos, selector de iconos) se dibujaban con la fuente Twemoji y en Windows no aparecían. Ahora se dibujan desde los SVG de Twemoji 15.0 incluidos en la app (los 3.720 emojis), igual que los iconos de Lucide, así que se ven idénticos en cualquier sistema (contribución de [@matsukiender-star](https://github.com/matsukiender-star), #3).

## 0.2.4
- **Linux:** si `XDG_CONFIG_HOME` o `XDG_DATA_HOME` están vacías o son rutas relativas, se ignoran como pide la especificación XDG y se usan `~/.config` y `~/.local/share`. Antes la configuración acababa en la carpeta desde donde se abría la app. Una sola función (`env_dir()`) resuelve ahora esas carpetas para la configuración, los datos, el lanzador, el inicio automático y los atajos de Hyprland (contribución de [@matsukiender-star](https://github.com/matsukiender-star), #2).

## 0.2.3
- **La app funciona ya fuera del equipo donde se desarrolló** (contribución de [@matsukiender-star](https://github.com/matsukiender-star)):
  - **Iconos en blanco** en Fedora/Nobara y distros recientes: el Qt de PySide6 no dibuja Noto Color Emoji COLRv1. Se incluyen los emojis Twemoji y los iconos SVG de Lucide para toda la interfaz.
  - **Micrófonos «(null)»** en sistemas en español: `pactl -f json` devuelve `(null)` en las descripciones con acentos; ahora se lee la salida de texto.
  - **AppImage**: los programas del sistema que lanza la app (`pactl`, `parec`, `pacat`, `hyprctl`) ya no heredan la libstdc++ empaquetada (error `GLIBCXX_3.4.32 not found`).
  - **Windows**: si VB-Cable queda como dispositivo predeterminado, ya no se usa como micrófono ni como salida para escuchar.
- **Windows**: instalador único con tema oscuro (Inno Setup 6.7.3) que instala la app y, si falta VB-Cable, lo descarga de la web oficial verificando su SHA-256 y abre su instalador al terminar.
- **Atajos**: sección propia «Atajos» con filas *voz o sonido + tecla* y «＋ Añadir atajo»; admite combinaciones (`Shift+1`, `Alt+F1`) y marca en rojo las teclas repetidas. Los atajos de sonidos pasan a ser globales. En **Hyprland** la app pone sus teclas con `hyprctl` sin pisar las ya existentes, y las quita al salir.
- **Interfaz rediseñada**: menú *Panel, Voz conf, Mejora, Voces, Sonidos, Atajos, Ajustes*. El **Panel** añade medidores horizontales en dB y paneles rápidos de voces y sonidos (6×2, cambiables con clic derecho) que se adaptan al tamaño de la ventana. **Voz conf** reúne ajustes, efectos y ecualizador con «Guardar como voz…». Apartados **Personalizados** para voces y sonidos propios, cuyo icono puede ser un SVG, un emoji o una imagen propia que viaja dentro de los `.vopack`. Ya no hay botón GUARDAR: los ajustes se guardan solos.
- **Pruebas**: el `selftest` comprueba ahora que la voz cambia de verdad (220 Hz → 440 Hz con +12 semitonos) y que la AppImage no pasa sus librerías a los programas del sistema; la CI compila y pasa el selftest en Linux y Windows.

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
