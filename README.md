# 🌌 Void of Voices

**Tu voz entra en el vacío… y sale convertida en otra.**

Void of Voices cambia tu voz **mientras hablas**: puedes sonar como un robot, un demonio, una ardilla, un locutor de radio o un fantasma. También lanza sonidos de reacción (aplausos, trombón triste, ba-dum-tss…) en mitad de la partida o del directo. Tus amigos te oyen en **Discord, OBS, juegos o cualquier app** que use el micrófono.

![Void of Voices](docs/captura-microfono.png)

> 🐧 Linux · 🪟 Windows · Gratis y de código abierto · 🇪🇸 Español / 🇬🇧 English

---

## ⬇️ Descargar

Entra en **[Releases](https://github.com/daetrox/void-of-voices/releases/latest)** y baja la versión para tu sistema:

| Sistema | Archivo | Cómo se abre |
|---|---|---|
| 🐧 Linux | `VoidOfVoices-…-x86_64.AppImage` | Clic derecho → *Propiedades* → marca *Ejecutable*, y doble clic. |
| 🪟 Windows | `VoidOfVoices-…-Windows-Setup.exe` | Instálalo como cualquier programa. |
| 🪟 Windows sin instalar | `VoidOfVoices-…-Windows-portable.zip` | Descomprime y abre `VoidOfVoices.exe`. |

> **En Windows**, la primera vez la app te ofrece instalar el micrófono virtual **con un clic**. Es el driver gratuito [VB-Cable](https://vb-audio.com/Cable/): Void of Voices lo descarga de su web oficial, comprueba que es el archivo auténtico y abre su instalador. Solo tienes que pulsar *Install Driver*. En Linux no hace falta nada más.

## ✨ Qué puedes hacer

- 🎭 **26 voces listas para usar.** Grave, aguda, femenina, masculina, niño, anciano, robot, alien, demonio, monstruo, susurro, voz de 8 bits, radio, teléfono, megáfono, bajo el agua, cueva, catedral…
- 🎚️ **Crear tu propia voz.** Mueve el tono y el timbre por separado (pasas de voz de hombre a voz de mujer sin sonar a ardilla), añade eco, reverberación, distorsión… y guárdala con tu nombre.
- 🔊 **Soundboard con 52 sonidos reales.** Aplausos, abucheos, risas, grillos, trombón triste, bocina, gong, explosión, gato, perro… Añade los tuyos arrastrándolos a la ventana.
- ⌨️ **Atajos que funcionan dentro del juego.** Cambia de voz, silénciate o habla solo mientras mantienes una tecla, sin salir de la partida.
- 🪟 **Ventanas pequeñas.** Un selector de voces y un panel de sonidos que puedes dejar siempre a la vista.
- 📦 **Comparte con tus amigos.** Exporta tus voces (`.vovoice`) o un paquete con tus sonidos (`.vopack`), y ellos solo tienen que arrastrarlos a su Void of Voices.
- 🎧 **Micrófono más limpio.** Quita el ruido de fondo con IA (el ventilador, el teclado, la calle), suaviza las «eses» que pitan y equilibra el volumen.

![Banco de voces](docs/captura-voces.png)

## 🚀 Cómo empezar

1. Abre Void of Voices, elige tu micrófono arriba y pulsa el **botón grande** para encenderlo.
2. En Discord (o la app que uses), ve a *Ajustes de voz* y elige como micrófono:
   - en **Linux**: **VoidOfVoices_Mic**;
   - en **Windows**: **CABLE Output (VB-Audio)**.
3. Elige una voz… ¡y a hacer el escándalo! 🎉

### ⌨️ Atajos de teclado

| Atajo | Qué hace |
|---|---|
| `Ctrl+Alt+0` | Voz normal ↔ última voz usada |
| `Ctrl+Alt+1` … `Ctrl+Alt+5` | Tus 5 voces rápidas (elígelas en *Ajustes*) |
| `Ctrl+Alt+M` | Silenciar / activar el micrófono |
| `Ctrl+Alt+H` | Pulsar para hablar (actívalo en *Ajustes → Micrófono*) |
| `Ctrl+Alt+E` | Encender / apagar |
| `Ctrl+Alt+X` | Parar todos los sonidos |
| `Ctrl+Alt+V` / `Ctrl+Alt+B` | Abrir el selector de voces / el panel de sonidos |

<img src="docs/captura-selector.png" alt="Selector de voces" width="360">

En Linux, la primera vez el sistema te pedirá permiso para los atajos, y puedes cambiar las teclas en *Ajustes → Cambiar teclas en el sistema*. En Windows las cambias directamente en *Ajustes*.

## ❓ Preguntas rápidas

**Windows dice que la app es peligrosa o «no reconocida».**
Es un falso positivo habitual en programas pequeños que aún no tienen firma digital de pago. El código es abierto, y GitHub compila cada versión de forma automática y pública. Si te aparece *«Windows protegió tu PC»*, pulsa *Más información → Ejecutar de todas formas*. Estamos trabajando en firmar las descargas.

**No me oyen en Discord.**
Comprueba que el botón grande pone *ENCENDIDO* y que en Discord el micrófono es *VoidOfVoices_Mic* (Linux) o *CABLE Output* (Windows).

**Se me oye con un poco de retraso.**
En *Ajustes → Motor de tono*, elige *Baja latencia*. Ganas rapidez a cambio de un poco de naturalidad en los cambios de tono.

**Hay mucho ruido de fondo.**
Ve a *Mejora* y elige el perfil *Llamada limpia* o *Streaming*.

**¿Puedo cerrar la ventana?**
Sí: Void of Voices sigue funcionando en la bandeja del sistema (junto al reloj). Para cerrarlo del todo, usa *Salir* en su menú.

![Soundboard](docs/captura-sonidos.png)

## 🛠️ Para curiosos

<details>
<summary>Ejecutar desde el código fuente</summary>

```bash
git clone https://github.com/daetrox/void-of-voices.git
cd voidofvoices
./run.sh          # la primera vez prepara el entorno (Python 3.10+)
```

En Linux necesita PipeWire (o PulseAudio) con `pactl`, `parec` y `pacat`, que vienen de serie en casi todas las distros.
</details>

- Hecho en Python con PySide6 (Qt).
- El audio va por PipeWire/PulseAudio en Linux y por WASAPI en Windows.
- El tono y los formantes se cambian con un vocoder de fase con envolvente cepstral.
- La supresión de ruido usa [RNNoise](https://github.com/xiph/rnnoise) y los efectos [pedalboard](https://github.com/spotify/pedalboard).
- Las versiones para descargar se compilan solas con GitHub Actions (`.github/workflows/build.yml`).

| Carpeta | Qué hay |
|---|---|
| `voidofvoices/dsp.py` | Cadena de procesado, vocoder, RNNoise, banco de voces |
| `voidofvoices/engine.py` | Hilo de audio (backends PipeWire y WASAPI) |
| `voidofvoices/hotkeys.py` | Atajos globales (portal XDG / RegisterHotKey) |
| `voidofvoices/ui.py`, `windows.py`, `widgets.py` | Interfaz |
| `voidofvoices/packs.py` | Exportar e importar voces y paquetes de sonidos |
| `voidofvoices/i18n*.py` | Traducciones |
| `sounds/` | Sonidos incluidos; `tools/fetch_sounds.py` los vuelve a descargar |
| `packaging/` | PyInstaller, AppImage e instalador de Windows |

## 🙌 Créditos

**Colaboradores:** [@matsukiender-star](https://github.com/matsukiender-star) (Matsuki Ender).

Todos los sonidos incluidos son de dominio público (CC0): grabaciones de [Freesound](https://freesound.org) y voces de [Kenney](https://kenney.nl). La lista completa está en [`sounds/CREDITS.md`](sounds/CREDITS.md).
