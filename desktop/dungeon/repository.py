"""Saving and loading the game state (dungeon_progress.json).

The file is separate from the vocabulary JSON, written atomically (temp file,
fsync, rename) and keeps one backup of the previous save, so a crash or a
corrupt file never loses more than the last step.
"""
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 2   # 2 added "inventory"; version-1 files load fine


def default_state() -> dict[str, Any]:
    return {
        "version": SCHEMA_VERSION,
        "player": {},
        "dungeons": {},   # key -> {"room": int, "unlocked": int, "completed": bool, "times": int}
        "run": {},        # totals of the current run through a dungeon
        "stats": {},      # lifetime statistics
        "missed": {},     # card word -> correct answers in a row since the last miss
        "inventory": {},  # {"items": {key: count}, "owned": [keys], "equipped": {slot: key}}
        "fight": None,    # {"dungeon", "room", "monster_hp"} while a fight is in progress
    }


class GameProgressRepository:
    def __init__(self, path: str | Path):
        self.path = Path(path)

    @property
    def backup_path(self) -> Path:
        return self.path.with_name(self.path.name + ".bak")

    def _read(self, path: Path) -> dict[str, Any] | None:
        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError):
            return None
        return data if isinstance(data, dict) else None

    def load(self) -> dict[str, Any]:
        """The saved state merged over the defaults; a fresh state if nothing usable exists."""
        data = self._read(self.path)
        if data is None and self.path.exists():
            # Unreadable main file: keep a copy for inspection, fall back to the backup.
            try:
                shutil.copyfile(self.path, self.path.with_name(self.path.name + ".corrupt"))
            except OSError:
                pass
        if data is None:
            data = self._read(self.backup_path)
        state = default_state()
        if data:
            for key in state:
                if key in data:
                    state[key] = data[key]
        return state

    def save(self, state: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_name(self.path.name + ".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        if self.path.exists() and self._read(self.path) is not None:
            try:
                shutil.copyfile(self.path, self.backup_path)
            except OSError:
                pass
        os.replace(tmp, self.path)
