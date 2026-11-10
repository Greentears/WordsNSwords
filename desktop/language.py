"""The language being learned (set when a deck is opened), for labels such as 'Show English -> type the French word'."""
NAMES = {"pl": "Polish", "fr": "French"}
ACCENTS = {"pl": "ą ę ł …", "fr": "é è ç …"}
_current = "pl"


def set_deck(deck: str) -> None:
    global _current
    _current = deck.split("-")[0] if deck else "pl"


def name() -> str:
    return NAMES.get(_current, _current.upper())


def accents() -> str:
    return ACCENTS.get(_current, "…")
