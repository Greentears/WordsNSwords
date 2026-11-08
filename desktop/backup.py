"""Backup files shared between the PC app and the phone app (the phone's "Export backup" format).

A backup is a JSON object: {"app": "flashcards-web", "version": 1, "exportedAt", "words": [...cards with
level / fails...], "settings": {...}, "stats": {...}, "dungeon": {...}}. The PC app writes only the words and the
dungeon save; it reads the words (and the dungeon save) of a backup made on the phone.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from flashcards import ARCHIVED, FlashcardDeck, Word

BACKUP_APP = "flashcards-web"      # the name the phone app already uses in its backups


def progress_score(level: int | None, fails: int) -> int:
    """A higher level wins, then more fails; new cards score lowest (same rule as the phone)."""
    return (-1 if level is None else level) * 1000 + min(fails, 999)


def make_backup(deck: FlashcardDeck, dungeon: dict | None = None, now: datetime | None = None) -> dict[str, Any]:
    words = []
    for w in deck.words:
        item: dict[str, Any] = dict(w.extra)
        item["word"], item["translation"] = w.word, w.translation
        if w.sentence:
            item["sentence"] = w.sentence
        if w.sentence_translation:
            item["sentence_translation"] = w.sentence_translation
        if w.level is not None:
            item["level"] = w.level
        if w.fails:
            item["fails"] = w.fails
        words.append(item)
    data: dict[str, Any] = {
        "app": BACKUP_APP, "version": 1,
        "exportedAt": (now or datetime.now(timezone.utc)).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
        "words": words,
    }
    if dungeon:
        data["dungeon"] = dungeon
    return data


def parse_import(text: str) -> tuple[list[dict], dict | None]:
    """(cards, dungeon save) of a backup, or of a plain words.json list. Raises ValueError with a readable message."""
    try:
        data = json.loads(text)
    except ValueError:
        raise ValueError("This file is not valid JSON.") from None
    if isinstance(data, list):
        cards, dungeon = data, None
    elif isinstance(data, dict) and data.get("app") == BACKUP_APP and isinstance(data.get("words"), list):
        cards = data["words"]
        dungeon = data["dungeon"] if isinstance(data.get("dungeon"), dict) else None
    else:
        raise ValueError("Unrecognised file: expected a backup made by the app, or a words.json list.")
    cards = [c for c in cards if isinstance(c, dict) and isinstance(c.get("word"), str)]
    if not cards:
        raise ValueError("The file contains no cards.")
    return cards, dungeon


def merge_progress(deck: FlashcardDeck, cards: list[dict], strategy: str = "higher") -> dict[str, int]:
    """Apply the levels / fails of `cards` to the deck's cards (matched by word).

    "higher": the card with more progress wins. "replace": the backup wins. Cards that are not in this
    deck are skipped: the word list itself belongs to the repository, not to the backup."""
    index = {w.word: w for w in deck.words}
    result = {"updated": 0, "unchanged": 0, "skipped": 0}
    for card in cards:
        mine: Word | None = index.get(card["word"])
        if mine is None:
            result["skipped"] += 1
            continue
        level, fails = card.get("level"), card.get("fails")
        level = level if isinstance(level, int) and not isinstance(level, bool) and 0 <= level <= ARCHIVED else None
        fails = fails if isinstance(fails, int) and not isinstance(fails, bool) and fails > 0 else 0
        take = strategy == "replace" or (strategy == "higher"
                                         and progress_score(level, fails) > progress_score(mine.level, mine.fails))
        if take and (level, fails) != (mine.level, mine.fails):
            mine.level, mine.fails = level, fails
            result["updated"] += 1
        else:
            result["unchanged"] += 1
    return result
