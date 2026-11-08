"""Forgiving answer checking for the dungeon (both directions).

The quizzes use the strict `flashcards.check_answer`; the dungeon is a game, so it
also accepts the natural short forms of a card side:

* alternatives: "run / operated by" -> "run", "run by", "operated by"
* a shared tail or head:  "can I try / taste it?" -> "can I taste it"
* optional text in brackets, a leading "to ", "to be ", articles
* soft modifiers: "little corner / nook" -> "corner"
* Polish: a missing "się", missing accents, "wzruszony / wzruszona" either form
* one typo in answers of 6 or more letters (reported as not exact)
"""
from __future__ import annotations

import re

from flashcards import _strip_accents

SOFT_MODIFIERS = frozenset({
    "little", "small", "big", "large", "great", "very", "really", "quite", "some",
    "certain", "the", "a", "an", "my", "your", "his", "her", "our", "their",
    "one's", "someone's", "somebody's", "something",
})
ARTICLES = ("a", "an", "the")
AUXILIARIES = frozenset({"is", "are", "am", "was", "were"})
MIN_TYPO_LENGTH = 6


def _norm(text: str) -> str:
    text = text.lower().replace("’", "'").replace("-", " ")
    text = re.sub(r"[?!.,;:…\"„”]", " ", text)
    return " ".join(text.split())


def _alternatives(expected: str, keep_brackets: bool = False) -> list[list[str]]:
    """The card side as token lists, one per alternative.

    Bracketed notes are dropped, or (keep_brackets) kept as ordinary words, so that both
    "zmierzać (do)" -> "zmierzać" and "zmierzać do" are understood."""
    if keep_brackets:
        text = re.sub(r"[()]", " ", expected)
    else:
        text = re.sub(r"\([^)]*\)", " ", expected)
    out = []
    for part in re.split(r"\s*/\s*", text):
        tokens = _norm(part).split()
        if tokens:
            out.append(tokens)
    return out


def _variants(tokens: list[str], reverse: bool) -> list[list[str]]:
    """Shorter spellings of one alternative that should also be accepted."""
    result = [tokens]
    if reverse:  # Polish: reflexive "się" may be left out
        trimmed = [t for t in tokens if t != "się"]
        if trimmed and trimmed != tokens:
            result.append(trimmed)
        return result
    work = tokens
    while len(work) > 1 and work[0] in AUXILIARIES:   # "is missing" -> "missing"
        work = work[1:]
        result.append(work)
    if work[:2] == ["to", "be"] and len(work) > 2:
        work = work[2:]
        result.append(work)
    elif work[0] in ("to", "be") and len(work) > 1:
        work = work[1:]
        result.append(work)
    while len(work) > 1 and work[0] in SOFT_MODIFIERS:
        work = work[1:]
        result.append(work)
    return result


def accepted_forms(expected: str, reverse: bool = False) -> set[str]:
    """Every normalised string that counts as a correct answer for `expected`."""
    alts = _alternatives(expected)
    bases = list(alts)
    if "(" in expected:
        bases += _alternatives(expected, keep_brackets=True)
    if len(alts) > 1:
        first = alts[0]
        for alt in alts[1:]:
            if len(first) > 1:                       # "can I try" + "taste it"
                bases.append(first[:-1] + alt)
            elif len(alt) > len(first):              # "run" + "operated by" -> "run by"
                bases.append(first + alt[1:])
    forms: set[str] = set()
    for tokens in bases:
        for variant in _variants(tokens, reverse):
            text = " ".join(variant)
            if text and text not in ARTICLES:
                forms.add(text)
    return forms


def primary(expected: str, reverse: bool = False) -> str:
    """The main spelling of a card side (first alternative, no notes, no leading "to ")."""
    alts = _alternatives(expected)
    if not alts:
        return expected.strip()
    tokens = alts[0]
    if not reverse and tokens[0] == "to" and len(tokens) > 1:
        tokens = tokens[1:]
    return " ".join(tokens)


def _distance_at_most_one(a: str, b: str) -> bool:
    if a == b:
        return True
    if abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        diffs = [i for i in range(len(a)) if a[i] != b[i]]
        if len(diffs) == 1:
            return True
        return (len(diffs) == 2 and diffs[1] == diffs[0] + 1
                and a[diffs[0]] == b[diffs[1]] and a[diffs[1]] == b[diffs[0]])  # swap
    short, long_ = (a, b) if len(a) < len(b) else (b, a)
    i = 0
    while i < len(short) and short[i] == long_[i]:
        i += 1
    return short[i:] == long_[i + 1:]


def _stem(token: str) -> str:
    """A crude English stem so that lack / lacks / lacking / lacked match."""
    for suffix in ("ing", "ed", "es", "s"):
        if token.endswith(suffix) and len(token) > len(suffix) + 2:
            token = token[: -len(suffix)]
            break
    if len(token) > 3 and token[-1] == token[-2] and token[-1] not in "aeiouls":
        token = token[:-1]
    return token[:-1] if len(token) > 3 and token.endswith("e") else token


def _stems(text: str) -> str:
    return " ".join(_stem(t) for t in text.split())


def check(given: str, expected: str, reverse: bool = False) -> tuple[bool, bool]:
    """(correct, exact). `exact` is False when accents or a small typo were forgiven."""
    if "/" in given:  # the whole card text typed with its slashes: every part must fit
        parts = [p for p in re.split(r"\s*/\s*", given) if _norm(p)]
        if len(parts) > 1:
            results = [check(p, expected, reverse) for p in parts]
            if all(ok for ok, _ in results):
                return True, all(exact for _, exact in results)
    typed = _norm(given.replace("/", " "))
    if not typed:
        return False, False
    guesses = {typed}
    unbracketed = _norm(re.sub(r"\([^)]*\)", " ", given.replace("/", " ")))
    if unbracketed:
        guesses.add(unbracketed)
    words = typed.split()
    if not reverse and len(words) > 1:
        for lead in (ARTICLES, ("to",)):
            if words[0] in lead:
                guesses.add(" ".join(words[1:]))
        if words[:2] == ["to", "be"] and len(words) > 2:
            guesses.add(" ".join(words[2:]))
    forms = accepted_forms(expected, reverse)
    if guesses & forms:
        return True, True
    folded = {_strip_accents(f) for f in forms}
    if any(_strip_accents(g) in folded for g in guesses):
        return True, False
    if not reverse:  # same word in another verb form: lack / lacking
        stemmed = {_stems(f) for f in forms}
        if any(_stems(g) in stemmed for g in guesses):
            return True, False
    for g in guesses:
        gf = _strip_accents(g)
        for f in folded:
            if len(f) >= MIN_TYPO_LENGTH and _distance_at_most_one(gf, f):
                return True, False
    return False, False
