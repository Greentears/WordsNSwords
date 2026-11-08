from __future__ import annotations

import json
import random
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path


# "Smart mix": share of each category being learned (Known / New are left out).
MIX_WEIGHTS = {2: 45, 1: 35, 0: 20}


# Learning levels, from "to verify" up to "known".
LEVELS = [
    (0, "To verify", "✕"),
    (1, "Learning", "◔"),
    (2, "Almost there", "◑"),
    (3, "Known", "✓"),
]
LEVEL_NAMES = {n: name for n, name, _ in LEVELS}
TOP_LEVEL = LEVELS[-1][0]
# Archived cards are Known cards that are hidden everywhere except Study -> Show -> Archived.
ARCHIVED = 4


def level_name(level: int | None) -> str:
    """Display name of a level: new / to verify / ... / known / archived."""
    if level is None:
        return "new"
    if level == ARCHIVED:
        return "archived"
    return LEVEL_NAMES[level].lower()


def level_icon(level: int | None) -> str:
    if level is None:
        return "●"
    if level == ARCHIVED:
        return "▣"
    return next(icon for lv, _, icon in LEVELS if lv == level)


@dataclass
class Word:
    word: str
    translation: str
    sentence: str = ""  # optional example sentence
    sentence_translation: str = ""  # optional translation of the sentence
    level: int | None = None  # None = new; 0 = to verify ... 3 = known; 4 = archived
    fails: int = 0  # how many times this word was failed in a quiz
    extra: dict = field(default_factory=dict)  # any other keys in the JSON, kept as-is


class FlashcardDeck:
    """Loads and manages a list of vocabulary flashcards."""

    ALL = "all"
    NEW = "new"        # not answered yet
    REVIEW = "level0"  # level 0: to verify
    LEARNING = "level1"
    ALMOST = "level2"
    KNOWN = "level3"
    ARCHIVE = "level4"  # archived (hidden from every other view)
    FAILED = "failed"  # words failed at least once in a quiz (worst first)
    QUICK = "quick"    # random sample of cards
    SEARCH = "search"  # cards matching a search text
    QUICK_SIZE = 10

    def __init__(self, words: list[Word] | None = None, path: str | Path | None = None,
                 progress_path: str | Path | None = None):
        self.words = words or []
        self.path = Path(path) if path else None
        # With a progress file, the word list is read-only and only levels / fails are saved.
        self.progress_path = Path(progress_path) if progress_path else None
        self.mode = self.ALL
        self._quick_ids: list[int] = []
        self._search_ids: list[int] = []
        self.index = 0
        self.results: dict[int, int] = {}  # level chosen per card in this pass
        self._order = self._build_order()

    def _build_order(self) -> list[int]:
        if self.mode == self.QUICK:
            return list(self._quick_ids)
        if self.mode == self.SEARCH:
            return list(self._search_ids)
        if self.mode == self.NEW:
            return [i for i, w in enumerate(self.words) if w.level is None]
        if self.mode == self.FAILED:
            failed = [i for i, w in enumerate(self.words)
                      if w.fails > 0 and w.level != ARCHIVED]
            return sorted(failed, key=lambda i: -self.words[i].fails)
        if self.mode.startswith("level"):
            target = int(self.mode[len("level"):])
            return [i for i, w in enumerate(self.words) if w.level == target]
        return [i for i, w in enumerate(self.words) if w.level != ARCHIVED]

    def set_mode(self, mode: str) -> None:
        self.mode = mode
        self.index = 0
        self.results.clear()
        self._order = self._build_order()

    def pool(self, levels: set | None = None, allowed: set | None = None) -> list[int]:
        """Card ids whose level is in `levels` (None inside the set = new cards).

        `levels=None` means every card except the archived ones. `allowed`, when
        given, restricts the result to those card ids.
        """
        if levels is None:
            ids = [i for i, w in enumerate(self.words) if w.level != ARCHIVED]
        else:
            ids = [i for i, w in enumerate(self.words) if w.level in levels]
        if allowed is not None:
            ids = [i for i in ids if i in allowed]
        return ids

    def search(self, query: str) -> int:
        """Show the cards whose word, translation or sentences contain `query`.

        Case and Polish accents are ignored. Archived cards are searched too.
        Returns the number of matches.
        """
        q = _fold(query)
        hits: list[tuple[int, int]] = []
        for i, w in enumerate(self.words):
            main = _fold(f"{w.word} {w.translation}")
            if q in main:
                hits.append((0, i))
            elif q in _fold(f"{w.sentence} {w.sentence_translation}"):
                hits.append((1, i))
        self._search_ids = [i for _, i in sorted(hits)]
        self.set_mode(self.SEARCH)
        return len(self._search_ids)

    def quick_set(self, levels: set | None = None, size: int | None = None) -> int:
        """Pick random cards from the given levels. Returns how many were picked."""
        size = size or self.QUICK_SIZE
        pool = self.pool(levels)
        self._quick_ids = random.sample(pool, min(size, len(pool)))
        self.set_mode(self.QUICK)
        return len(self._quick_ids)

    def mixed_sample(self, size: int, weights: dict | None = None,
                     allowed: set | None = None) -> list[int]:
        """Pick `size` random cards with a weighted mix of every level.

        Default weights: mostly "Almost there", fewer "Learning", fewer still
        "To verify". If a level has too few cards, its share is given to the
        other levels.
        """
        weights = weights or MIX_WEIGHTS
        pools = {key: self.pool({key}, allowed) for key in weights}
        pools = {k: random.sample(v, len(v)) for k, v in pools.items() if v}
        total_available = sum(len(v) for v in pools.values())
        size = min(size, total_available)

        picked: list[int] = []
        while len(picked) < size and pools:
            remaining = size - len(picked)
            weight_sum = sum(weights[k] for k in pools)
            # Largest-remainder allocation of the remaining slots.
            quotas = {k: remaining * weights[k] / weight_sum for k in pools}
            counts = {k: int(q) for k, q in quotas.items()}
            leftover = remaining - sum(counts.values())
            for k in sorted(pools, key=lambda k: quotas[k] - counts[k], reverse=True)[:leftover]:
                counts[k] += 1
            for k in list(pools):
                take = min(counts[k], len(pools[k]))
                picked += pools[k][:take]
                pools[k] = pools[k][take:]
                if not pools[k]:
                    del pools[k]
        random.shuffle(picked)
        return picked

    def record_fail(self, word_id: int) -> None:
        self.words[word_id].fails += 1
        self.save()

    def save(self) -> None:
        """Write the current levels back: to the progress file if there is one, else to the JSON file."""
        if self.progress_path:
            self._save_progress()
            return
        if not self.path:
            return
        data = []
        for w in self.words:
            item = dict(w.extra)
            item["word"] = w.word
            item["translation"] = w.translation
            if w.sentence:
                item["sentence"] = w.sentence
            if w.sentence_translation:
                item["sentence_translation"] = w.sentence_translation
            if w.level is not None:
                item["level"] = w.level
            if w.fails:
                item["fails"] = w.fails
            data.append(item)

        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        tmp.replace(self.path)

    def _save_progress(self) -> None:
        cards = {}
        for w in self.words:
            entry = {}
            if w.level is not None:
                entry["level"] = w.level
            if w.fails:
                entry["fails"] = w.fails
            if entry:
                cards[w.word] = entry
        self.progress_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.progress_path.with_suffix(self.progress_path.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump({"version": 1, "cards": cards}, f, ensure_ascii=False, indent=1)
        tmp.replace(self.progress_path)

    def _apply_progress(self, cards: dict) -> None:
        for w in self.words:
            entry = cards.get(w.word)
            entry = entry if isinstance(entry, dict) else {}
            level, fails = entry.get("level"), entry.get("fails")
            w.level = level if (isinstance(level, int) and not isinstance(level, bool)
                                and 0 <= level <= ARCHIVED) else None
            w.fails = fails if isinstance(fails, int) and not isinstance(fails, bool) and fails > 0 else 0

    def reset_progress(self) -> None:
        for w in self.words:
            w.level = None
            w.fails = 0
        self.save()
        self.set_mode(self.mode)

    @classmethod
    def from_json(cls, path: str | Path, progress_path: str | Path | None = None) -> "FlashcardDeck":
        """Load the cards. With `progress_path`, levels and fails live in that separate file
        (cards only in the words file); an older words file that still holds levels is used
        as the starting point when the progress file does not exist yet."""
        path = Path(path)

        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, list):
            raise ValueError("The JSON root must be a list.")

        words = []
        for i, item in enumerate(data):
            if not isinstance(item, dict):
                raise ValueError(f"Item #{i + 1} must be an object.")

            word = item.get("word")
            translation = item.get("translation")

            if not isinstance(word, str) or not word.strip():
                raise ValueError(f"Item #{i + 1} has an invalid 'word'.")

            if not isinstance(translation, str) or not translation.strip():
                raise ValueError(
                    f"Item #{i + 1} has an invalid 'translation'."
                )

            sentence = item.get("sentence")
            sentence_translation = item.get("sentence_translation")
            fails = item.get("fails")
            level = item.get("level")
            if not (isinstance(level, int) and not isinstance(level, bool)
                    and 0 <= level <= ARCHIVED):
                # Older files used "known": true/false.
                old = item.get("known")
                level = TOP_LEVEL if old is True else 0 if old is False else None
            extra = {
                k: v for k, v in item.items()
                if k not in ("word", "translation", "sentence", "sentence_translation", "level", "fails", "known")
            }
            words.append(
                Word(
                    word=word.strip(),
                    translation=translation.strip(),
                    sentence=sentence.strip() if isinstance(sentence, str) else "",
                    sentence_translation=(
                        sentence_translation.strip()
                        if isinstance(sentence_translation, str) else ""
                    ),
                    level=level,
                    fails=fails if isinstance(fails, int) and fails > 0 else 0,
                    extra=extra,
                )
            )

        if not words:
            raise ValueError("The JSON file contains no words.")

        deck = cls(words, path, progress_path)
        if progress_path and Path(progress_path).exists():
            try:
                with Path(progress_path).open("r", encoding="utf-8") as pf:
                    saved = json.load(pf)
                cards = saved.get("cards") if isinstance(saved, dict) else None
                if isinstance(cards, dict):
                    deck._apply_progress(cards)
            except (OSError, ValueError):
                pass     # unreadable progress file: keep whatever the words file holds
        return deck

    @property
    def total(self) -> int:
        return len(self._order)

    @property
    def current_number(self) -> int:
        return self.index + 1 if self._order else 0

    @property
    def current(self) -> Word:
        return self.words[self._order[self.index]]

    @property
    def current_id(self) -> int:
        return self._order[self.index]

    @property
    def overall_total(self) -> int:
        return len(self.words)

    def level_count(self, level: int) -> int:
        return sum(1 for w in self.words if w.level == level)

    @property
    def active_count(self) -> int:
        """Cards that are not archived."""
        return sum(1 for w in self.words if w.level != ARCHIVED)

    @property
    def new_count(self) -> int:
        return sum(1 for w in self.words if w.level is None)

    @property
    def session_known(self) -> int:
        return sum(1 for r in self.results.values() if r >= TOP_LEVEL)

    @property
    def session_unknown(self) -> int:
        return sum(1 for r in self.results.values() if r < TOP_LEVEL)

    @property
    def is_last(self) -> bool:
        return self.index >= self.total - 1

    def mark(self, level: int) -> None:
        """Move the current card to the given level and save.

        Only a Known card can be archived; any other card asked to go there is ignored.
        """
        if level == ARCHIVED and self.words[self.current_id].level != TOP_LEVEL:
            return
        self.results[self.current_id] = level
        self.words[self.current_id].level = level
        self.save()

    def next(self) -> None:
        if not self.is_last:
            self.index += 1

    def previous(self) -> None:
        if self.index > 0:
            self.index -= 1

    def shuffle(self) -> None:
        """Shuffle the cards currently shown and start again from the first."""
        self.restart(shuffle=True)

    def restart(self, shuffle: bool = False) -> None:
        """Start a new pass over the current view (saved progress is kept)."""
        self.index = 0
        self.results.clear()
        self._order = self._build_order()

        if shuffle:
            random.shuffle(self._order)


# ---------------------------------------------------------------------------
# Typed-answer checking (used by the quiz)
# ---------------------------------------------------------------------------

def _strip_accents(text: str) -> str:
    text = text.replace("ł", "l").replace("Ł", "L")
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(c for c in decomposed if unicodedata.category(c) != "Mn")


def _normalise(text: str) -> str:
    text = text.lower().replace("’", "'")
    text = re.sub(r"[?!.,;:…\"„”]", " ", text)
    return " ".join(text.split())


def accepted_answers(expected: str) -> list[str]:
    """All spellings accepted for a card side, e.g. 'istotna / ważna' -> both."""
    variants = [expected] + [part for part in expected.split(" / ") if part.strip()]
    result: list[str] = []
    for variant in variants:
        no_brackets = re.sub(r"\s*\([^)]*\)", "", variant)  # 'pochodzić (z)' -> 'pochodzić'
        for candidate in (variant, no_brackets):
            norm = _normalise(candidate)
            if not norm:
                continue
            result.append(norm)
            if norm.startswith("to "):  # English verbs: accept without "to "
                result.append(norm[3:])
    return result


def check_answer(given: str, expected: str, ignore_accents: bool = True) -> tuple[bool, bool]:
    """Compare a typed answer with a card side.

    Returns (correct, exact). `exact` is False when the answer was only accepted
    because accents (ą, ę, ł, ...) were ignored.
    """
    given_norm = _normalise(given)
    if not given_norm:
        return False, False

    accepted = accepted_answers(expected)
    if given_norm in accepted:
        return True, True
    if ignore_accents:
        stripped = _strip_accents(given_norm)
        if any(stripped == _strip_accents(a) for a in accepted):
            return True, False
    return False, False


def _fold(text: str) -> str:
    """Lower-case and accent-free, for searching."""
    return " ".join(_strip_accents(text.lower()).split())


# ---------------------------------------------------------------------------
# Fill-in-the-blank: find the word (in whatever form) inside its sentence
# ---------------------------------------------------------------------------

BLANK = "_____"
_TOKEN = re.compile(r"[^\W\d_]+(?:-[^\W\d_]+)*", re.UNICODE)


def _token_match(token: str, target: str, fuzzy: bool) -> bool:
    token, target = token.lower(), target.lower()
    if token == target:
        return True
    if not fuzzy or len(target) < 5 or len(token) < 4:
        return False
    common = 0
    # Compare without accents so ó/o, ą/a ... changes (powód / powodów) still match.
    for a, b in zip(_strip_accents(token), _strip_accents(target)):
        if a != b:
            break
        common += 1
    return common >= max(4, len(target) - 3)


def blank_sentence(
    word: "Word", extra_forms: list[str] | None = None, sentence: str | None = None
) -> tuple[str, str] | None:
    """Return (sentence with the word replaced by blanks, accepted answers).

    The card word is usually the dictionary form ("pozwalać"), the sentence has
    it inflected ("pozwalają"): a token matches when it is the same or only
    differs in the ending. Every occurrence (in whatever form) is blanked so
    none of them gives the answer away; the answer is the removed text, with
    different forms joined by " / ". `extra_forms` are other known forms of the
    word (from the declension / conjugation tables) that must match exactly.
    `sentence` replaces the card's own sentence (used for the extra examples).
    Returns None when the word is not found.
    """
    sentence = word.sentence if sentence is None else sentence
    if not sentence:
        return None
    tokens = [(m.group(), m.start(), m.end()) for m in _TOKEN.finditer(sentence)]
    variants = []
    for variant in word.word.split(" / "):
        variant = re.sub(r"\s*\([^)]*\)", "", variant).replace("...", " ")
        parts = [p.lower() for p in _TOKEN.findall(variant)]
        if parts:
            variants.append((parts, True))
    for form in extra_forms or []:
        for alt in form.split(" / "):
            parts = [p.lower() for p in _TOKEN.findall(alt)]
            if parts:
                variants.append((parts, False))

    spans: list[tuple[int, int]] = []  # token index ranges (inclusive)
    for parts, fuzzy in variants:
        for i in range(len(tokens) - len(parts) + 1):
            if all(_token_match(tokens[i + j][0], parts[j], fuzzy) for j in range(len(parts))):
                spans.append((i, i + len(parts) - 1))
    # keep the longest of any overlapping spans
    chosen: list[tuple[int, int]] = []
    for span in sorted(set(spans), key=lambda s: (s[0], -(s[1] - s[0]))):
        if not chosen or span[0] > chosen[-1][1]:
            chosen.append(span)
    if not chosen:
        return None

    out, pos, answers = [], 0, []
    for first, last in chosen:
        start, end = tokens[first][1], tokens[last][2]
        out.append(sentence[pos:start])
        out.append(BLANK)
        text = sentence[start:end]
        if text.lower() not in (a.lower() for a in answers):
            answers.append(text)
        pos = end
    out.append(sentence[pos:])
    return "".join(out), " / ".join(answers)
