"""Where a user's words live (in the repository) and where their progress lives (on this computer).

    <repo>/users/<name>/<deck>/words.json ...   the cards (shared through GitHub)
    <repo>/users/_template/<deck>/              the starter deck for a new name
    <repo>/local/<name>/<deck>/progress.json    levels and fails    (not in git)
                               dungeon_progress.json, stats.json
    <repo>/local/user.txt                       the name you entered (also the hero's name)
"""
from __future__ import annotations

import re
import shutil
import unicodedata
from dataclasses import dataclass
from pathlib import Path

DEFAULT_DECK = "pl-en"
TEMPLATE = "_template"


def slug(name: str) -> str:
    """The folder name for a user: lower case, no accents, letters / digits / - only."""
    text = unicodedata.normalize("NFKD", name.strip().lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9_-]+", "-", text).strip("-_")


@dataclass(frozen=True)
class Workspace:
    root: Path
    user: str          # the name as typed (also the hero's name)
    deck: str = DEFAULT_DECK

    @property
    def slug_name(self) -> str:
        return slug(self.user)

    @property
    def content_dir(self) -> Path:
        return self.root / "users" / slug(self.user) / self.deck

    @property
    def words_path(self) -> Path:
        return self.content_dir / "words.json"

    @property
    def local_dir(self) -> Path:
        return self.root / "local" / slug(self.user) / self.deck

    @property
    def hero_path(self) -> Path:
        """Which hero (female or male) this player chose: one choice per player, for every deck."""
        return self.root / "local" / slug(self.user) / "hero.json"

    @property
    def progress_path(self) -> Path:
        return self.local_dir / "progress.json"

    @property
    def dungeon_path(self) -> Path:
        return self.local_dir / "dungeon_progress.json"

    @property
    def stats_path(self) -> Path:
        return self.local_dir / "stats.json"

    @property
    def exists(self) -> bool:
        return self.words_path.is_file()

    def create_from_template(self) -> bool:
        """Copy the starter deck into users/<name>/<deck>. False if there is no starter deck."""
        source = self.root / "users" / TEMPLATE / self.deck
        if not source.is_dir():
            return False
        shutil.copytree(source, self.content_dir, dirs_exist_ok=True)
        return self.exists


def find_root(start: Path) -> Path | None:
    """The repository folder: the nearest parent of `start` that has a users/ folder."""
    for folder in [start, *start.parents][:5]:
        if (folder / "users").is_dir():
            return folder
    return None


def saved_user(root: Path) -> str:
    try:
        return (root / "local" / "user.txt").read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def save_user(root: Path, name: str) -> None:
    path = root / "local" / "user.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(name.strip(), encoding="utf-8")


def template_decks(root: Path) -> list[str]:
    """The languages that have a starter deck (users/_template/<deck>/words.json)."""
    return decks_of(root, TEMPLATE) or [DEFAULT_DECK]


def is_new_name(root: Path, name: str) -> bool:
    """True when the repository has no words at all for this name (so it must pick a language)."""
    return not decks_of(root, name)


def decks_of(root: Path, name: str) -> list[str]:
    """The languages (deck folders with a words.json) this name has in the repository."""
    folder = root / "users" / slug(name)
    try:
        return sorted(d.name for d in folder.iterdir() if (d / "words.json").is_file())
    except OSError:
        return []


def saved_deck(root: Path) -> str:
    try:
        return (root / "local" / "deck.txt").read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def save_deck(root: Path, deck: str) -> None:
    path = root / "local" / "deck.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(deck.strip(), encoding="utf-8")


def choose_deck(root: Path, name: str, preferred: str = "") -> str | None:
    """The deck to open: the preferred one if it exists, the only one, or None when the user must choose
    (several decks) / DEFAULT_DECK when the name has none yet (a new name starts from the starter deck)."""
    decks = decks_of(root, name)
    if not decks:
        return DEFAULT_DECK
    if preferred in decks:
        return preferred
    return decks[0] if len(decks) == 1 else None
