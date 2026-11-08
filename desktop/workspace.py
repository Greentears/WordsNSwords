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
