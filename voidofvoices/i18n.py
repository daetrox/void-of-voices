"""Idiomas: los textos se escriben en español y se traducen con T().

El idioma se fija al arrancar (cambiarlo pide reiniciar la app).
"""

import locale

from .i18n_en import EN

LANGUAGES = {"es": "Español", "en": "English"}
_lang = "es"


def system_language():
    try:
        loc = (locale.getlocale()[0] or "").lower()
    except Exception:
        loc = ""
    return "es" if loc.startswith("es") else "en"


def set_language(lang):
    global _lang
    _lang = lang if lang in LANGUAGES else system_language()


def language():
    return _lang


def T(text):
    """Traduce un texto en español al idioma actual."""
    if _lang == "es" or not text:
        return text
    return EN.get(text, text)
