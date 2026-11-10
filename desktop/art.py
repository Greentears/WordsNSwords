"""Finding the game's pictures (assets/art/...) and remembering which hero a player chose.

No Qt in here, so it can be tested. Every picture is optional: without one the game draws its
pixel-art sprite or an emoji, so art can be added a little at a time (tools/import_art.py).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HEROES = ("f", "m")      # female, male


def art_dir() -> Path:
    base = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent
    return base / "assets" / "art"


def art_file(kind: str, key: str) -> Path | None:
    """assets/art/<kind>/<key>.png if it exists (kind: monsters, companions, items, heroes)."""
    path = art_dir() / kind / f"{key}.png"
    return path if path.is_file() else None


def background_file(key: str) -> Path | None:
    """The scenery behind a dungeon's map and fights (assets/art/backgrounds/<dungeon>.jpg)."""
    path = art_dir() / "backgrounds" / f"{key}.jpg"
    return path if path.is_file() else None


OUTDOOR_DUNGEONS = ("forest", "citadel")      # every other dungeon is indoors


def scene_file(kind: str, dungeon_key: str) -> Path | None:
    """The picture for a rest or treasure room, indoor or outdoor like its dungeon."""
    place = "outdoor" if dungeon_key in OUTDOOR_DUNGEONS else "indoor"
    return background_file(f"{kind}_{place}")


def ui_file(name: str) -> Path | None:
    """Screen furniture: slot_square, slot_armor, slot_weapon, panel."""
    return art_file("ui", name)


def hero_file(gender: str, weapon: bool = False, armor: bool = False) -> Path | None:
    """The hero picture for the gear he wears: bare, with a sword, with armour, or both."""
    look = gender + ("_armour" if armor else "") + ("_sword" if weapon else "")
    return art_file("heroes", look) or art_file("heroes", gender)


def hero_choice_available() -> bool:
    return all(art_file("heroes", g) for g in HEROES)


def load_hero(path: Path) -> str | None:
    """The hero a player chose ("f" or "m"), or None if they haven't chosen yet."""
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8")).get("hero")
    except (OSError, ValueError, AttributeError):
        return None
    return value if value in HEROES else None


def save_hero(path: Path, gender: str) -> None:
    """Remember the choice. It is final: an existing choice is never overwritten."""
    if gender not in HEROES:
        raise ValueError(f"unknown hero {gender!r}")
    path = Path(path)
    if load_hero(path):
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"hero": gender}), encoding="utf-8")
