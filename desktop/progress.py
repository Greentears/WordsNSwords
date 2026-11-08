from __future__ import annotations

import json
from pathlib import Path


class ProgressStore:
    """Stores lightweight review statistics between sessions."""

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def load(self) -> dict:
        if not self.path.exists():
            return {}

        try:
            with self.path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}

    def save(self, data: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)

        temporary = self.path.with_suffix(".tmp")
        with temporary.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        temporary.replace(self.path)

    def update_session(self, total: int, known: int, unknown: int) -> None:
        data = self.load()

        data["sessions"] = data.get("sessions", 0) + 1
        data["cards_reviewed"] = data.get("cards_reviewed", 0) + total
        data["known"] = data.get("known", 0) + known
        data["unknown"] = data.get("unknown", 0) + unknown

        self.save(data)

    def get_stats(self) -> dict:
        return self.load()
