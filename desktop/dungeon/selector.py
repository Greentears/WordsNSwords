"""Choosing which vocabulary card each question uses.

Reads the deck but never changes it: levels and fail counts stay untouched.
"""
from __future__ import annotations

import random
from collections import deque
from typing import Any, Protocol

from flashcards import ARCHIVED

from . import config


class _DeckLike(Protocol):
    words: list


class MissedWords:
    """Words answered wrongly in the dungeon, with the streak of correct answers since.

    A word leaves the list after `MISSED_CLEAR_STREAK` correct answers in a row.
    Keyed by the card's Polish word so it survives reordering of words.json.
    """

    def __init__(self, data: Any = None):
        self._streaks: dict[str, int] = {}
        if isinstance(data, dict):
            for word, streak in data.items():
                if isinstance(word, str) and isinstance(streak, int) and not isinstance(streak, bool):
                    self._streaks[word] = max(0, min(streak, config.MISSED_CLEAR_STREAK - 1))

    def __len__(self) -> int:
        return len(self._streaks)

    def __contains__(self, word: object) -> bool:
        return word in self._streaks

    def words(self) -> list[str]:
        return sorted(self._streaks)

    def miss(self, word: str) -> None:
        self._streaks[word] = 0

    def correct(self, word: str) -> bool:
        """Register a correct answer; True when this cleared the word from the list."""
        if word not in self._streaks:
            return False
        self._streaks[word] += 1
        if self._streaks[word] >= config.MISSED_CLEAR_STREAK:
            del self._streaks[word]
            return True
        return False

    def to_dict(self) -> dict[str, int]:
        return dict(self._streaks)


class VocabularySelector:
    def __init__(self, deck: _DeckLike, missed: MissedWords | None = None,
                 rng: random.Random | None = None,
                 weights: dict[int | None, float] | None = None):
        self.deck = deck
        self.missed = missed if missed is not None else MissedWords()
        self.rng = rng or random.Random()
        self.weights = dict(config.LEVEL_WEIGHTS if weights is None else weights)
        self._recent: deque[int] = deque(maxlen=config.RECENT_WINDOW)
        self.only_missed = False   # review mode: ask only words you missed (when there are any)

    def weight(self, word_id: int, weights: dict | None = None) -> float:
        w = self.deck.words[word_id]
        if w.level == ARCHIVED or not w.word.strip() or not w.translation.strip():
            return 0.0
        value = float((self.weights if weights is None else weights).get(w.level, 0.0))
        if value > 0 and w.word in self.missed:
            value *= config.MISSED_WEIGHT_BONUS
        return value

    def candidates(self, weights: dict | None = None) -> list[int]:
        ids = [i for i in range(len(self.deck.words)) if self.weight(i, weights) > 0]
        if self.only_missed:
            missed = [i for i in ids if self.deck.words[i].word in self.missed]
            ids = missed or ids
        return ids

    def pick(self, weights: dict | None = None) -> int | None:
        """A card id, or None when nothing in the deck can be asked.

        Cards seen in the last `RECENT_WINDOW` questions are skipped while enough
        other cards exist; with a tiny deck only the previous card is avoided.
        """
        ids = self.candidates(weights)
        if not ids:
            return None
        fresh = [i for i in ids if i not in self._recent]
        if not fresh:
            last = self._recent[-1] if self._recent else None
            fresh = [i for i in ids if i != last] or ids
        choice = self.rng.choices(fresh, weights=[self.weight(i, weights) for i in fresh], k=1)[0]
        self._recent.append(choice)
        return choice
