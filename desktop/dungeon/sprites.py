"""Pixel-art sprites as text (no Qt here, so they can be unit-tested).

Each sprite is drawn as 16 rows of 8 characters: the left half. The right half is the
mirror image. The drawing is then scaled 2x (Scale2x), shaded and given glowing eyes. '.' is transparent; every
other character is a key into the sprite's palette.
"""
from __future__ import annotations

from .sprites_art import ART
from .sprites_draw import DRAWINGS, PALETTES as _DARK, hero_custom

_OUT = "#0b0912"

PALETTES: dict[str, dict[str, str]] = {
    "hero": {"o": _OUT, "h": "#6c7388", "H": "#aab2c8", "K": "#4d5367", "r": "#7a1a22",
             "e": "#ff9a2e", "g": "#c9a24a", "b": "#3a2a1c", "s": "#8a6a4a"},
    "slime": {"o": _OUT, "g": "#3f8a4a", "G": "#8fd68f", "w": "#e8ffe8", "e": "#b6ff3a"},
    "goblin": {"o": _OUT, "g": "#5a7a3a", "G": "#8aa860", "y": "#d9b44a", "e": "#ff5a2e",
               "w": "#e8e0c8", "b": "#5a3a1f"},
    "skeleton": {"o": _OUT, "w": "#cfc7ae", "d": "#8a8470", "e": "#ff3b2e"},
    "dark_knight": {"o": _OUT, "b": "#3a2a1c", "k": "#2c2e3d", "K": "#6b6f8a", "r": "#ff3b2e", "p": "#8a1f2f"},
    "boss": {"o": _OUT, "R": "#8c1c1c", "r": "#521010", "y": "#d9ccb0", "e": "#ffd23a",
             "w": "#e8e0c8"},
    "bat": {"o": _OUT, "p": "#4a2f70", "P": "#7a58a8", "r": "#ff3b2e", "w": "#e8e0c8"},
    "wolf": {"o": _OUT, "g": "#5a5e70", "G": "#9ca0b4", "w": "#e8e0c8", "y": "#d9b44a",
             "e": "#ff4a2e", "r": "#a82828"},
    "treant": {"o": _OUT, "b": "#4a3018", "B": "#7a5230", "g": "#2a5a30", "G": "#4f8f4a",
               "y": "#d9b44a", "e": "#ff9a2e"},
    "witch": {"o": _OUT, "p": "#3f2563", "P": "#7a52a8", "g": "#6a9a6a", "y": "#c9a24a",
              "e": "#7dff6a", "w": "#e8e0c8"},
    "golem": {"o": _OUT, "i": "#7aa8c0", "I": "#bfe0f0", "b": "#3a6a8a", "e": "#5aa0ff",
              "w": "#e8f4ff"},
    "wraith": {"o": _OUT, "c": "#3f4f80", "C": "#8aa0d8", "e": "#7dffb0", "k": "#1c2240"},
    "dragon": {"o": _OUT, "g": "#2f6a38", "G": "#5aa860", "y": "#c9a24a", "r": "#ff6a1f",
               "e": "#ffb42e", "w": "#e8e0c8", "d": "#1f4a26"},
    "treasure": {"o": _OUT, "b": "#7a4a20", "y": "#d9b44a"},
    "rest": {"o": _OUT, "b": "#5a3a1f", "y": "#e8b84a", "r": "#ff6a2e"},
}

PALETTES.update(_DARK)

_HALVES: dict[str, list[str]] = {
    "hero": [
        "oh......", "ohh..ooo", ".ohooHHH", "..ohHHHH", "..ohhhhh", "..ohoeee",
        "..ohhhhh", ".oooohhh", "oHHoKKKK", "oHHoKgKK", "ohhoKKKK", ".orrKbbb",
        ".orrKKKK", "..orhhhh", "..oohhhh", "..ooobbb",
    ],
    "slime": [
        "........", "........", "........", "......oo", "....oogg", "...ogGGg",
        "..ogGggg", "..oggwwg", "..oggewg", "..ogggoo", ".oggggg.", ".ogggggg",
        ".ooooooo", "........", "........", "........",
    ],
    "goblin": [
        "........", "........", "......oo", "....ooGg", "oo.oGggg", "ogoggggg",
        ".oggyegg", ".ogggggg", "..ogwgwg", "..oobbbb", ".obbbbbb", ".ogbbbbb",
        "..obbbbb", "..oggo..", "..oggo..", "..oooo..",
    ],
    "skeleton": [
        "........", "....oooo", "...owwww", "...owwww", "...oweew", "...oweew",
        "...owwwo", "....owow", "....oooo", "..owwwwo", "..oooooo", "..owwwwo",
        "..oooooo", "...owwo.", "...owwo.", "..oowwoo",
    ],
    "dark_knight": [
        "......pp", "......pp", "....oooo", "...okkkk", "...okkkk", "...orrrr",
        "...okkkk", "..oookkk", ".oKKkkkk", ".oKkkkkk", ".okkkkkk", ".okkkkkk",
        "..okkkkk", "..okkko.", "..okkko.", "..ooooo.",
    ],
    "boss": [
        "y.......", "yy......", "oyy.oooo", ".oyoRRRR", ".oRRRRRR", ".oRRyeRR",
        ".oRRRRRR", "..oRwRRw", "..ooRRRR", "ooRRRRRR", "oRRRrrrr", "oRRrrrrr",
        "oRRrrrrr", ".ooRrrrr", "..oRRRo.", "..ooooo.",
    ],
    "bat": [
        "........", ".....o..", ".....opp", ".....orp", ".o...opp", "oPo..opw",
        "oPPo.oop", "oPPPooPp", "oPoPPPpp", ".o.oPPpp", "...ooPpp", ".....oop",
        "......oo", "........", "........", "........",
    ],
    "wolf": [
        "........", "..o...o.", "..oo.ooG", "..oGoGgg", "..oggggg", "..ogyegg",
        "..oggggg", "...ogGGG", "...ogowo", "....ogGG", "...oggGg", "..ogggGG",
        "..ogggGg", "..oggoog", "..ogo..o", "..ooo...",
    ],
    "treant": [
        "..g.g.gG", ".gGgGgGg", "gGgGgGgG", ".ogGgGgG", "..obbbBB", "..obebBB",
        "..obbbBB", "..obbyBB", "...obbbB", "..obbBBB", ".obbBBBB", ".obbBbBB",
        "..obBBbB", "..obbBbb", "..obbo.o", "..oooo..",
    ],
    "witch": [
        ".......o", "......op", ".....opp", "....oppp", "...opPPP", "..oppPpp",
        ".oooooPp", "...ogggg", "...ogeeg", "...oggwg", "....oopp", "..opppPp",
        ".oppPppP", ".opppppp", "..opppyy", "..oooooo",
    ],
    "golem": [
        "........", "...ooooo", "..oIIIii", "..oIiiii", "..oieeii", "..oiiiii",
        "..oobbbb", ".ooIIiii", "oIIiiibb", "oIiiibbb", "oIiibbbb", "ooiibbbb",
        "..oiiiib", "..oiiioo", "..oiiio.", "..ooooo.",
    ],
    "wraith": [
        "........", "....oooo", "...occcc", "..occkkk", "..ockeek", "..ockeek",
        "..occkkk", "..ocCcCc", "..occCcC", ".occcCcc", ".occcccC", "occcccCc",
        "occcCccc", ".ocCcccC", "..occcCc", "...o.occ",
    ],
    "dragon": [
        "o.......", "oo..o..o", "ogo.ogoG", "ogGoggGG", ".oggggGG", ".ogeegGG",
        ".oggggGG", "..ogwgww", "..oggrrr", "..oogggg", ".ogGGGgg", "ogGGyyGg",
        "ogGyyyyg", "ogGGyyyG", ".ogdoogg", "..ooo.oo",
    ],
    "treasure": [
        "........", "........", "........", "........", "........", "..oooooo",
        ".obbbbbb", ".obbbbbb", ".ooooooo", ".obbbbbb", ".obbbbyy", ".obbbbbb",
        ".ooooooo", "........", "........", "........",
    ],
    "rest": [
        "........", "........", ".......y", "......yy", "......yr", ".....yrr",
        ".....yyr", "....yyrr", "....yyyr", "...yyrrr", "..bbbyyy", ".bbbbbbb",
        "bbbooooo", "........", "........", "........",
    ],
}


# Same drawing, different colours: key -> (drawing, palette)
ALIASES: dict[str, tuple[str, dict[str, str]]] = {
    "ink_slime": ("slime", {**PALETTES["slime"], "g": "#3b3a8f", "G": "#8f8fe0"}),
    "paper_goblin": ("goblin", {**PALETTES["goblin"], "g": "#e8dcc0", "G": "#fff6de",
                                "b": "#8a6a3b"}),
    "page_wraith": ("wraith", {**PALETTES["wraith"], "c": "#b09a6a", "C": "#efe0b0",
                               "k": "#3a2f1c"}),
    "tome_knight": ("dark_knight", {**PALETTES["dark_knight"], "k": "#6b3f2a", "K": "#c9a36b",
                                    "r": "#7dffb0", "p": "#2f6fd0"}),
    "librarian": ("witch", {**PALETTES["witch"], "p": "#9a6a1a", "P": "#e0b24a", "g": "#e8c9a0"}),
    "review_guru": ("witch", {**PALETTES["witch"], "p": "#1f6b6b", "P": "#5fd0c0", "g": "#d9c3a0"}),
    "guardian": ("treant", {"o": _OUT, "b": "#4b5a2a", "B": "#7a8f3a", "g": "#2f7d3a",
                            "G": "#f2c14e", "y": "#7dffb0", "e": _OUT}),
    "warlord": ("dark_knight", {"o": _OUT, "k": "#7a2020", "K": "#d8a64a", "r": "#ffe14d",
                                "p": "#e04848"}),
}


BASE = 16     # the hand-drawn grid
SIZE = 32     # the rendered sprite (the drawing scaled 2x and shaded)


def _grid(key: str) -> list[str]:
    """The drawing for `key` as a SIZE x SIZE grid of palette characters."""
    key = ALIASES[key][0] if key in ALIASES else key
    if key in DRAWINGS:
        return DRAWINGS[key]()
    if key in ART:
        art = ART[key]
        assert len(art) <= SIZE, key
        halves = [r[-(SIZE // 2):].rjust(SIZE // 2, ".") for r in art]
        blank = "." * (SIZE // 2)
        halves = [blank] * (SIZE - len(halves)) + halves
        return [h + h[::-1] for h in halves]
    return _scale2x([half + half[::-1] for half in _HALVES[key]])


def sprite_rows(key: str) -> list[str]:
    """The SIZE x SIZE grid of palette characters (symmetric) for `key`."""
    return _grid(key)


def _scale2x(rows: list[str]) -> list[str]:
    """Scale2x: doubles the drawing and smooths its diagonals without blurring."""
    h, w = len(rows), len(rows[0])

    def at(x: int, y: int, default: str) -> str:
        return rows[y][x] if 0 <= x < w and 0 <= y < h else default

    out = [[""] * (w * 2) for _ in range(h * 2)]
    for y in range(h):
        for x in range(w):
            p = rows[y][x]
            a, b = at(x, y - 1, p), at(x + 1, y, p)
            c, d = at(x - 1, y, p), at(x, y + 1, p)
            out[2 * y][2 * x] = a if c == a and c != d and a != b else p
            out[2 * y][2 * x + 1] = b if a == b and a != c and b != d else p
            out[2 * y + 1][2 * x] = c if d == c and d != b and c != a else p
            out[2 * y + 1][2 * x + 1] = d if b == d and b != a and d != c else p
    return ["".join(r) for r in out]


def _mix(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))  # type: ignore[return-value]


def _rgb(colour: str) -> tuple[int, int, int]:
    return int(colour[1:3], 16), int(colour[3:5], 16), int(colour[5:7], 16)


def _hex(rgb) -> str:
    return "#%02x%02x%02x" % tuple(max(0, min(255, round(v))) for v in rgb)


def _is_glow(colour: str) -> bool:
    r, g, b = _rgb(colour)
    return max(r, g, b) >= 200 and (max(r, g, b) - min(r, g, b)) >= 90


def _shade(rows: list[str], palette: dict[str, str]) -> list[list[str | None]]:
    """Dark-fantasy look: top-left light, shadowed lower edges, grit, glowing eyes."""
    n = len(rows)

    def ch(x: int, y: int) -> str:
        return rows[y][x] if 0 <= x < n and 0 <= y < n else "."

    glow = {k for k, v in palette.items() if k != "o" and _is_glow(v) and k in "e r".replace(" ", "")}
    glow = {k for k in glow if k == "e" or (k == "r" and palette[k] == "#ff3b2e")}
    out: list[list[str | None]] = []
    for y in range(n):
        line: list[str | None] = []
        for x in range(n):
            c = rows[y][x]
            if c == ".":
                line.append(None)
                continue
            base = _rgb(palette[c])
            if c == "o":
                line.append(_hex(base))
                continue
            if c in glow:
                line.append(_hex(base))
                continue
            factor = 1.18 - 0.42 * (x + y) / (2 * n - 2)
            if ch(x, y - 1) in ".o":
                factor *= 1.12            # lit upper edge
            if ch(x - 1, y) in ".o":
                factor *= 1.06
            if ch(x, y + 1) in ".o" or ch(x + 1, y) in ".o":
                factor *= 0.72            # shadowed lower / right edge
            factor *= 1 + (((x * 73856093) ^ (y * 19349663)) % 9 - 4) / 100   # grit
            colour = tuple(v * factor for v in base)
            for dx in (-2, -1, 0, 1, 2):
                for dy in (-2, -1, 0, 1, 2):
                    if (dx or dy) and ch(x + dx, y + dy) in glow:
                        dist = max(abs(dx), abs(dy))
                        colour = _mix(colour, _rgb(palette[ch(x + dx, y + dy)]), 0.34 / dist)  # type: ignore[arg-type]
                        break
            line.append(_hex(colour))
        out.append(line)
    return out


def sprite_pixels(key: str) -> list[list[str | None]]:
    """The finished SIZE x SIZE image as colour strings ('#rrggbb'), None for transparent."""
    palette = {**PALETTES[ALIASES[key][0]], **ALIASES[key][1]} if key in ALIASES else PALETTES[key]
    return _shade(_grid(key), palette)


def hero_pixels(weapon: str | None = None, armor: str | None = None,
                charm: str | None = None) -> list[list[str | None]]:
    """The hero drawn with the gear he wears (item keys, None = nothing equipped)."""
    rows, palette = hero_custom(weapon, armor, charm)
    return _shade(rows, palette)


SPRITE_KEYS = tuple(dict.fromkeys((*DRAWINGS, *ART, *_HALVES))) + tuple(ALIASES)
