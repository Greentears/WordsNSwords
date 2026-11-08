"""One fight: the player translates words, the monster hits back on mistakes.

Pure game logic. The battle never touches a card's level or fail count; it
only reports what happened so the manager can save progress.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Callable

from . import config
from .answers import check, primary
from .models import Monster, Player
from .selector import MissedWords, VocabularySelector

ACTIVE, VICTORY, DEFEAT = "active", "victory", "defeat"


@dataclass
class Question:
    word_id: int
    prompt: str          # what is shown (Polish word, or English meaning when reversed)
    answer: str          # expected answer, exactly as on the card
    reverse: bool = False  # True: the player types the Polish word
    show_first: bool = False   # first letter revealed (item / charm)
    show_count: bool = False   # letter count revealed (item)
    time_limit: int = 0        # seconds, 0 = unlimited
    kind: str = "word"         # "word" or "cloze" (fill in the blank in a Polish sentence)
    gloss: str = ""            # cloze: English meaning of the missing word
    context: str = ""          # cloze: English translation of the sentence

    @property
    def target_language(self) -> str:
        return "Polish" if self.reverse else "English"

    @property
    def is_cloze(self) -> bool:
        return self.kind == "cloze"


@dataclass
class AnswerResult:
    correct: bool
    skipped: bool
    expected: str
    exact: bool                # False when accepted only after forgiving accents / a typo
    damage_dealt: int          # player -> monster
    damage_taken: int          # monster -> player
    message: str
    state: str                 # ACTIVE / VICTORY / DEFEAT after this answer
    word: str = ""
    cleared_from_missed: bool = False
    free: bool = False         # a free skip (scroll): counts as neither right nor wrong
    timed_out: bool = False


class Battle:
    def __init__(self, player: Player, monster: Monster, selector: VocabularySelector,
                 rng: random.Random | None = None):
        self.player = player
        self.monster = monster
        self.selector = selector
        self.rng = rng or selector.rng
        self.question: Question | None = None
        self.questions_asked = 0
        self.consecutive_wrong = 0
        # Set by the manager from equipment / items:
        self.ward = False            # the next monster hit is absorbed
        self.phoenix = False         # survive one lethal hit
        self.time_bonus = 0          # extra seconds on timed questions
        self.xp_mult = 1.0           # for the victory reward
        self.coin_mult = 1.0
        self.cloze_source: Callable[[int], tuple[str, str, str] | None] | None = None
        # companion
        self.companion = ""
        self.heal_on_correct = 0
        self.bonus_damage = 0
        self.dodge_pct = 0

    @property
    def state(self) -> str:
        if not self.player.is_alive:
            return DEFEAT
        if not self.monster.is_alive:
            return VICTORY
        return ACTIVE

    @property
    def missed(self) -> MissedWords:
        return self.selector.missed

    # -- questions ----------------------------------------------------------
    def next_question(self) -> Question | None:
        """Start a new question; None if the fight is over or the deck has no usable card."""
        if self.state != ACTIVE:
            return None
        spec = self.monster.spec
        limit = spec.time_limit + self.time_bonus if spec.time_limit else 0
        word_id = None
        if self.cloze_source and self.rng.random() < spec.cloze_chance:
            for _ in range(30):                 # look for a card with a usable sentence
                word_id = self._pick()
                found = self.cloze_source(word_id) if word_id is not None else None
                if found:
                    blanked, answer, english = found
                    card = self.selector.deck.words[word_id]
                    self.question = Question(word_id, blanked, answer, True, time_limit=limit,
                                             kind="cloze", gloss=card.translation, context=english)
                    self.questions_asked += 1
                    return self.question
                if word_id is None:
                    break
        word_id = word_id if word_id is not None else self._pick()
        if word_id is None:
            return None
        card = self.selector.deck.words[word_id]
        reverse = self.rng.random() < spec.reverse_chance
        if reverse:
            self.question = Question(word_id, card.translation, card.word, True, time_limit=limit)
        else:
            self.question = Question(word_id, card.word, card.translation, False, time_limit=limit)
        self.questions_asked += 1
        return self.question

    def _pick(self) -> int | None:
        """A card for the next question; a boss falls back to normal weights if its own find nothing."""
        word_id = self.selector.pick(self._weights())
        if word_id is None and self.monster.spec.boss:
            word_id = self.selector.pick(None)
        return word_id

    def _weights(self) -> dict | None:
        """Bosses favour the words you know least."""
        return config.BOSS_LEVEL_WEIGHTS if self.monster.spec.boss else None

    def hint_text(self) -> str:
        """Everything currently revealed about the answer."""
        q = self._require_question()
        card = self.selector.deck.words[q.word_id]
        main = primary(q.answer, q.reverse)
        if q.is_cloze:
            words = main.split()
            lines = [f"{len(words)} word{'s' if len(words) != 1 else ''}"]
            if q.show_first:
                lines.append(f"Starts with “{main[:1]}”")
            if q.show_count:
                lines.append(" + ".join(str(len(w)) for w in words) + " letters")
            if q.context:
                lines.append(q.context)
            return "\n".join(lines)
        words = main.split()
        lines = [f"{len(words)} word{'s' if len(words) != 1 else ''}"]
        if q.show_first:
            lines.append(f"Starts with “{main[:1]}”")
        if q.show_count:
            counts = " + ".join(str(len(w)) for w in words)
            lines.append(f"{counts} letters")
        sentence = (card.sentence_translation if q.reverse else card.sentence).strip()
        if sentence:
            lines.append(sentence)
        return "\n".join(lines)

    def reveal(self, first: bool = False, count: bool = False) -> str:
        """Item hint: reveals letters without any damage penalty."""
        q = self._require_question()
        q.show_first = q.show_first or first
        q.show_count = q.show_count or count
        return self.hint_text()

    def submit(self, text: str) -> AnswerResult:
        q = self._require_question()
        correct, exact = check(text, q.answer, q.reverse)
        if correct:
            return self._player_hits(q, exact)
        return self._monster_hits(q, "wrong", text)

    def skip(self) -> AnswerResult:
        """Give up on the question: counts as wrong, but the monster hits half as hard."""
        return self._monster_hits(self._require_question(), "skip")

    def timeout(self) -> AnswerResult:
        """The time ran out: a wrong answer."""
        return self._monster_hits(self._require_question(), "timeout")

    def free_skip(self) -> AnswerResult:
        """Skip scroll: reveal the answer and move on with no penalty at all."""
        q = self._require_question()
        word = self.selector.deck.words[q.word_id].word
        self.question = None
        return AnswerResult(False, True, q.answer, False, 0, 0,
                            f'You read the scroll. "{q.prompt}" is "{q.answer}".',
                            self.state, word, free=True)

    # -- internals ----------------------------------------------------------
    def _require_question(self) -> Question:
        if self.state != ACTIVE or self.question is None:
            raise RuntimeError("no active question")
        return self.question

    def _vary(self, base: float) -> int:
        spread = config.DAMAGE_SPREAD
        return max(1, round(base * (1 + self.rng.uniform(-spread, spread))))

    def _heal_monster(self, amount: int) -> int:
        gained = max(0, min(amount, self.monster.max_hp - self.monster.hp))
        self.monster.hp += gained
        return gained

    def _player_hits(self, q: Question, exact: bool) -> AnswerResult:
        base = self.player.attack_power
        amount = max(1, self._vary(base) - self.monster.spec.armor) + self.bonus_damage
        dealt = self.monster.take_damage(amount)
        word = self.selector.deck.words[q.word_id].word
        cleared = self.missed.correct(word)
        self.consecutive_wrong = 0
        self.question = None
        message = f"Correct! You dealt {dealt} damage."
        if not exact:
            message += f' (Spelling: "{primary(q.answer, q.reverse)}")'
        if self.heal_on_correct:
            healed = self.player.heal(self.heal_on_correct)
            if healed:
                message += f" {self.companion} heals you for {healed} HP."
        if not self.monster.is_alive:
            message += f" The {self.monster.name} is defeated!"
        return AnswerResult(True, False, q.answer, exact, dealt, 0, message,
                            self.state, word, cleared)

    def _monster_damage(self, mode: str) -> float:
        spec = self.monster.spec
        base = float(spec.damage)
        if mode == "skip":
            base *= config.SKIP_DAMAGE_FACTOR
        if spec.enrage and self.monster.hp <= self.monster.max_hp * config.ENRAGE_HP_FRACTION:
            base *= config.ENRAGE_FACTOR
        if spec.combo:
            stacks = min(config.COMBO_MAX_STACKS, self.consecutive_wrong)
            base *= 1 + config.COMBO_STEP * stacks
        return base

    def _monster_hits(self, q: Question, mode: str, given: str = "") -> AnswerResult:
        spec = self.monster.spec
        base = self._monster_damage(mode)
        hit = self.rng.choice((-1, 0, 1)) if base >= 3 else 0
        cap = max(1, int(self.player.max_hp * config.MAX_HIT_FRACTION))
        amount = max(1, min(cap, max(1, round(base) + hit) - self.player.gear_reduction))
        notes: list[str] = []
        if self.ward:
            self.ward = False
            amount = 0
            notes.append("Your ward absorbs the blow!")
        elif self.dodge_pct and self.rng.random() * 100 < self.dodge_pct:
            amount = 0
            notes.append(f"{self.companion} helps you dodge!")
        taken = self.player.take_damage(amount)
        if not self.player.is_alive and self.phoenix:
            self.phoenix = False
            self.player.hp = max(1, round(self.player.max_hp * config.PHOENIX_REVIVE_FRACTION))
            notes.append("The Phoenix Feather burns and you rise again!")
        if spec.lifesteal and taken > 0:
            healed = self._heal_monster(round(taken * config.LIFESTEAL_FRACTION))
            if healed:
                notes.append(f"The {self.monster.name} drains {healed} HP.")
        if spec.regen:
            healed = self._heal_monster(spec.regen)
            if healed:
                notes.append(f"The {self.monster.name} regenerates {healed} HP.")
        self.consecutive_wrong += 1

        word = self.selector.deck.words[q.word_id].word
        self.missed.miss(word)
        self.question = None
        lead = {"skip": "Skipped!", "timeout": "Time's up!"}.get(mode, "Incorrect!")
        if q.is_cloze:
            meaning = f'The missing word was "{q.answer}".'
        elif q.reverse:
            meaning = f'"{q.prompt}" in Polish is "{q.answer}".'
        else:
            meaning = f'"{q.prompt}" means "{q.answer}".'
        message = f'{lead} {meaning} '
        if given.strip():
            message += f'You answered "{given.strip()}". '
        message += (f"The {self.monster.name} attacks you for {taken} damage."
                    if taken else f"The {self.monster.name} attacks, but misses you.")
        if notes:
            message += " " + " ".join(notes)
        if not self.player.is_alive:
            message += " You have fallen..."
        return AnswerResult(False, mode == "skip", q.answer, False, 0, taken, message,
                            self.state, word, timed_out=mode == "timeout")
