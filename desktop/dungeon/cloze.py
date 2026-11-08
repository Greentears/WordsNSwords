"""Fill-in-the-blank questions for sentence battles, built from the deck's sentences.

Uses the card's own example sentence and the extra examples (examples.json) and
`flashcards.blank_sentence`, the same routine as the fill-in-the-blank quiz.
"""
from __future__ import annotations

import random
from typing import Any

from flashcards import blank_sentence


class ClozeSource:
    def __init__(self, deck: Any, examples: dict[str, list[tuple[str, str]]] | None = None,
                 rng: random.Random | None = None):
        self.deck = deck
        self.examples = examples or {}
        self.rng = rng or random.Random()

    def __call__(self, word_id: int) -> tuple[str, str, str] | None:
        """(sentence with a blank, accepted answers, English translation) or None."""
        card = self.deck.words[word_id]
        options: list[tuple[str, str]] = []
        if card.sentence.strip():
            options.append((card.sentence, card.sentence_translation))
        options.extend(self.examples.get(card.word, []))
        self.rng.shuffle(options)
        for sentence, english in options:
            found = blank_sentence(card, None, sentence)
            if found:
                return found[0], found[1], english
        return None
