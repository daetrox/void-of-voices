"""Atajos de teclado globales (funcionan aunque la ventana no tenga el foco).

- Linux: portal org.freedesktop.portal.GlobalShortcuts (KDE Plasma 6, GNOME 48+).
  El sistema muestra un diálogo la primera vez y el usuario cambia las teclas
  en la configuración del escritorio (ConfigureShortcuts).
- Windows: RegisterHotKey de user32, con las teclas que elija el usuario.

Los atajos se describen con el formato del portal: «CTRL+ALT+m», «CTRL+ALT+space».
"""

import secrets
import threading

from PySide6.QtCore import QObject, Signal

from . import APP_ID, IS_LINUX, IS_WINDOWS

# id, descripción (español, se traduce en la UI), atajo sugerido
ACTIONS = [
    ("toggle_voice", "Voz normal ↔ última voz", "CTRL+ALT+0"),
    ("voice_1", "Voz rápida 1", "CTRL+ALT+1"),
    ("voice_2", "Voz rápida 2", "CTRL+ALT+2"),
    ("voice_3", "Voz rápida 3", "CTRL+ALT+3"),
    ("voice_4", "Voz rápida 4", "CTRL+ALT+4"),
    ("voice_5", "Voz rápida 5", "CTRL+ALT+5"),
    ("mute", "Silenciar / activar micrófono", "CTRL+ALT+m"),
    ("ptt", "Pulsar para hablar (mantener)", "CTRL+ALT+h"),
    ("power", "Encender / apagar", "CTRL+ALT+e"),
    ("stop_sounds", "Detener sonidos", "CTRL+ALT+x"),
    ("quick_voices", "Abrir selector de voces", "CTRL+ALT+v"),
    ("sound_panel", "Abrir panel de sonidos", "CTRL+ALT+b"),
]


def pretty(trigger):
    """«CTRL+ALT+m» → «Ctrl+Alt+M»."""
    names = {"CTRL": "Ctrl", "ALT": "Alt", "SHIFT": "Shift", "LOGO": "Meta", "space": "Espacio"}
    return "+".join(names.get(p, p.upper() if len(p) == 1 else p.capitalize()) for p in trigger.split("+"))


def to_portal(qt_seq):
    """Texto de QKeySequence («Ctrl+Alt+M») → formato portal («CTRL+ALT+m»)."""
    mods = {"ctrl": "CTRL", "alt": "ALT", "shift": "SHIFT", "meta": "LOGO"}
    parts = qt_seq.split("+")
    out = [mods[p.lower()] for p in parts[:-1] if p.lower() in mods]
    key = parts[-1]
    out.append("space" if key.lower() == "space" else key.lower() if len(key) == 1 else key)
    return "+".join(out)


class GlobalHotkeys(QObject):
    activated = Signal(str)
    deactivated = Signal(str)
    changed = Signal(dict)     # id → texto del atajo asignado
    status = Signal(str)       # mensaje de estado/error para la UI

    def __init__(self, parent=None):
        super().__init__(parent)
        self.backend = None
        self.triggers = {}
        self._impl = None

    @property
    def can_configure_in_system(self):
        return self.backend == "portal"

    def start(self, triggers):
        """triggers: id → atajo (formato portal). En Linux son solo sugerencias."""
        self.stop()
        if IS_LINUX:
            self._impl = _PortalHotkeys(self)
        elif IS_WINDOWS:
            self._impl = _WindowsHotkeys(self)
        else:
            return False
        ok = self._impl.start(triggers)
        if not ok:
            self._impl = None
        return ok

    def stop(self):
        if self._impl:
            self._impl.stop()
        self._impl = None
        self.backend = None

    def configure(self):
        if self._impl and hasattr(self._impl, "configure"):
            self._impl.configure()


# ------------------------------------------------------------------ Linux

class _PortalHotkeys:
    PATH = "/org/freedesktop/portal/desktop"
    BUS = "org.freedesktop.portal.Desktop"
    IFACE = "org.freedesktop.portal.GlobalShortcuts"

    def __init__(self, owner):
        self.owner = owner
        self.router = None
        self.session = None
        self._stop = threading.Event()

    def start(self, triggers):
        try:
            from jeepney import DBusAddress  # noqa: F401
        except ImportError:
            self.owner.status.emit("jeepney no está instalado")
            return False
        threading.Thread(target=self._run, args=(dict(triggers),), daemon=True).start()
        return True

    def _request(self, member, signature, body, token):
        """Llama a un método del portal que responde con una señal Request.Response."""
        from jeepney import DBusAddress, MatchRule, new_method_call
        from jeepney.bus_messages import message_bus
        sender = self.router.unique_name[1:].replace(".", "_")
        path = f"{self.PATH}/request/{sender}/{token}"
        rule = MatchRule(type="signal", interface="org.freedesktop.portal.Request",
                         member="Response", path=path)
        self.router.send_and_get_reply(message_bus.AddMatch(rule))
        addr = DBusAddress(self.PATH, bus_name=self.BUS, interface=self.IFACE)
        with self.router.filter(rule) as q:
            self.router.send_and_get_reply(new_method_call(addr, member, signature, body), timeout=10)
            # BindShortcuts puede esperar a que el usuario confirme el diálogo.
            msg = q.get(timeout=300)
        code, results = msg.body
        if code != 0:
            raise RuntimeError(f"{member} cancelado ({code})")
        return results

    def _run(self, triggers):
        from jeepney import DBusAddress, HeaderFields, MatchRule, new_method_call
        from jeepney.bus_messages import message_bus
        from jeepney.io.threading import open_dbus_router
        from .i18n import T
        try:
            self._cm = open_dbus_router(bus="SESSION")
            self.router = self._cm.__enter__()
            # Identifica la app ante el portal (necesita el .desktop instalado).
            try:
                reg = DBusAddress(self.PATH, bus_name=self.BUS, interface="org.freedesktop.host.portal.Registry")
                self.router.send_and_get_reply(new_method_call(reg, "Register", "sa{sv}", (APP_ID, {})), timeout=5)
            except Exception:
                pass
            token = "vz" + secrets.token_hex(4)
            res = self._request("CreateSession", "a{sv}", ({
                "handle_token": ("s", token),
                "session_handle_token": ("s", "vzs" + secrets.token_hex(4)),
            },), token)
            self.session = res["session_handle"][1]

            shortcuts = [(sid, {"description": ("s", T(desc)),
                                "preferred_trigger": ("s", triggers.get(sid, trig))})
                         for sid, desc, trig in ACTIONS]
            token = "vz" + secrets.token_hex(4)
            res = self._request("BindShortcuts", "oa(sa{sv})sa{sv}",
                                (self.session, shortcuts, "", {"handle_token": ("s", token)}), token)
            self._publish(res.get("shortcuts", ("", []))[1])
            self.owner.backend = "portal"
            self.owner.status.emit("")

            rule = MatchRule(type="signal", interface=self.IFACE, path=self.PATH)
            self.router.send_and_get_reply(message_bus.AddMatch(rule))
            with self.router.filter(rule) as q:
                while not self._stop.is_set():
                    try:
                        msg = q.get(timeout=0.5)
                    except Exception:
                        continue
                    member = msg.header.fields.get(HeaderFields.member)
                    if not msg.body or msg.body[0] != self.session:
                        continue
                    if member == "Activated":
                        self.owner.activated.emit(msg.body[1])
                    elif member == "Deactivated":
                        self.owner.deactivated.emit(msg.body[1])
                    elif member == "ShortcutsChanged":
                        self._publish(msg.body[1])
        except Exception as e:
            self.owner.backend = None
            self.owner.status.emit(T("Atajos globales no disponibles: {}").format(e))

    def _publish(self, items):
        trig = {}
        for sid, props in items:
            desc = props.get("trigger_description", ("s", ""))[1]
            trig[sid] = desc
        self.owner.triggers = trig
        self.owner.changed.emit(trig)

    def configure(self):
        if not (self.router and self.session):
            return
        from jeepney import DBusAddress, new_method_call
        addr = DBusAddress(self.PATH, bus_name=self.BUS, interface=self.IFACE)
        try:
            self.router.send_and_get_reply(
                new_method_call(addr, "ConfigureShortcuts", "osa{sv}", (self.session, "", {})), timeout=10)
        except Exception as e:
            self.owner.status.emit(str(e))

    def stop(self):
        self._stop.set()
        if self.router:
            try:
                self._cm.__exit__(None, None, None)
            except Exception:
                pass


# ---------------------------------------------------------------- Windows

class _WindowsHotkeys:
    WM_HOTKEY = 0x0312
    WM_QUIT = 0x0012
    MODS = {"CTRL": 0x2, "ALT": 0x1, "SHIFT": 0x4, "LOGO": 0x8}
    MOD_NOREPEAT = 0x4000

    def __init__(self, owner):
        self.owner = owner
        self.thread_id = None
        self._thread = None

    @classmethod
    def parse(cls, trigger):
        parts = trigger.split("+")
        mods = 0
        for p in parts[:-1]:
            mods |= cls.MODS.get(p.upper(), 0)
        key = parts[-1]
        if key.lower() == "space":
            vk = 0x20
        elif len(key) == 1:
            vk = ord(key.upper())
        elif key.upper().startswith("F") and key[1:].isdigit():
            vk = 0x6F + int(key[1:])
        else:
            return None
        return mods, vk

    def start(self, triggers):
        self.triggers = {sid: triggers.get(sid, trig) for sid, _, trig in ACTIONS}
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        return True

    def _run(self):
        import ctypes
        from ctypes import wintypes
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        self.thread_id = kernel32.GetCurrentThreadId()
        ids, failed = {}, []
        for n, (sid, trig) in enumerate(self.triggers.items(), start=1):
            parsed = self.parse(trig) if trig else None
            if not parsed:
                continue
            mods, vk = parsed
            if user32.RegisterHotKey(None, n, mods | self.MOD_NOREPEAT, vk):
                ids[n] = (sid, vk)
            else:
                failed.append(pretty(trig))
        self.owner.backend = "windows"
        self.owner.triggers = {sid: pretty(t) for sid, t in self.triggers.items() if t}
        self.owner.changed.emit(self.owner.triggers)
        if failed:
            from .i18n import T
            self.owner.status.emit(T("Atajos ocupados por otra app: {}").format(", ".join(failed)))
        msg = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            if msg.message == self.WM_HOTKEY and msg.wParam in ids:
                sid, vk = ids[msg.wParam]
                self.owner.activated.emit(sid)
                if sid == "ptt":
                    threading.Thread(target=self._wait_release, args=(sid, vk), daemon=True).start()
        for n in ids:
            user32.UnregisterHotKey(None, n)

    def _wait_release(self, sid, vk):
        import ctypes
        import time
        while ctypes.windll.user32.GetAsyncKeyState(vk) & 0x8000:
            time.sleep(0.02)
        self.owner.deactivated.emit(sid)

    def stop(self):
        if self.thread_id:
            import ctypes
            ctypes.windll.user32.PostThreadMessageW(self.thread_id, self.WM_QUIT, 0, 0)
            if self._thread:
                self._thread.join(timeout=1)
        self.thread_id = None
