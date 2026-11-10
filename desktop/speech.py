"""Reading a word aloud with the computer's own voices (Qt text-to-speech: Windows voices).

Nothing is downloaded or sent anywhere. Polish and French only work when Windows has a voice for them
(Settings -> Time & language -> Speech). The Qt part is imported lazily so the app still runs without it.
"""
from __future__ import annotations

import re

LANGUAGE_NAMES = {"pl": "Polish", "fr": "French", "en": "English", "de": "German", "es": "Spanish",
                  "it": "Italian", "nl": "Dutch"}


def spoken_text(word: str) -> str:
    """What to say for a card's word: brackets are dropped ('pochodzić (z)' -> 'pochodzić z')."""
    return re.sub(r"\s+", " ", re.sub(r"[()]", " ", word)).strip()


def language_code(deck: str | None) -> str:
    """The language being learned, from a deck id like 'pl-en'."""
    return (deck or "pl-en").split("-")[0]


class Speaker:
    """Say a word in the language being learned. speak() returns a message if it can't, else None."""

    def __init__(self) -> None:
        self._engine = None
        self._failed: str | None = None

    def _load(self):
        if self._engine is not None or self._failed:
            return self._engine
        try:
            from PySide6.QtTextToSpeech import QTextToSpeech
            self._engine = QTextToSpeech()
        except Exception as error:      # module or engine missing on this computer
            self._failed = f"This computer can't read aloud ({error.__class__.__name__})."
        return self._engine

    def speak(self, word: str, code: str) -> str | None:
        text = spoken_text(word)
        if not text:
            return None
        engine = self._load()
        if engine is None:
            return self._failed
        from PySide6.QtCore import QLocale
        wanted = {"pl": QLocale.Language.Polish, "fr": QLocale.Language.French, "en": QLocale.Language.English,
                  "de": QLocale.Language.German, "es": QLocale.Language.Spanish, "it": QLocale.Language.Italian,
                  "nl": QLocale.Language.Dutch}.get(code)
        name = LANGUAGE_NAMES.get(code, code.upper())
        locales = [loc for loc in engine.availableLocales() if loc.language() == wanted]
        if not locales:
            return f"No {name} voice is installed in Windows (Settings, Time & language, Speech)."
        engine.stop()
        engine.setLocale(locales[0])
        voices = engine.availableVoices()
        if voices:
            engine.setVoice(voices[0])
        engine.setRate(-0.15)           # a little slower, easier to catch while learning
        engine.say(text)
        return None
