"""Grammar quiz: fill in the blank with the right ending, case or tense (Polish and French).

Questions come from the tables you already have (verbs.json, nouns.json, adjectives.json), so they are
always about your own words. This module has no screen code; the PC window and the phone app both use it
(the phone has a copy in web/src/core/grammar.ts, checked against this one by a golden test).
"""
from __future__ import annotations

import random
import re
import unicodedata
from dataclasses import dataclass

import french

CATEGORIES = ("verbs", "nouns", "adjectives")
CATEGORY_NAMES = {"verbs": "Verbs", "nouns": "Nouns", "adjectives": "Adjectives"}

PL_PRONOUNS = ("ja", "ty", "on / ona / ono", "my", "wy", "oni / one")
PL_PAST = ("on", "ona", "ono", "oni", "one")
PL_IMPERATIVE = ("ty", "my", "wy")
PL_CASES = (("nominative", "kto? co?"), ("genitive", "kogo? czego?"), ("dative", "komu? czemu?"),
            ("accusative", "kogo? co?"), ("instrumental", "z kim? z czym?"), ("locative", "o kim? o czym?"),
            ("vocative", "o!"))
PL_ADJ = (("m", "masculine"), ("f", "feminine"), ("n", "neuter"), ("pl", "plural"))
FR_PRONOUN_CHECK = re.compile(r"^(?:j'|je |tu |il/elle |ils/elles |nous |vous )", re.IGNORECASE)


@dataclass(frozen=True)
class Question:
    category: str          # verbs / nouns / adjectives
    card: str              # the word on your card
    stem: str              # what is shown, with the blank: "ja ___"
    label: str             # what is asked: "denerwować się · present"
    hint: str              # extra help, may be empty
    answers: tuple[str, ...]   # every accepted answer (first one is shown when you are wrong)


def norm(text: str) -> str:
    text = unicodedata.normalize("NFC", text).lower().replace("’", "'").replace("‘", "'")
    return re.sub(r"\s+", " ", text).strip()


def fold(text: str) -> str:
    """norm() without accents (ł counts as l), to tell 'wrong ending' from 'only forgot the accents'."""
    text = norm(text).replace("ł", "l")
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))


def _variants(answer: str) -> list[str]:
    """The answer, and without a reflexive 'się' (you may leave it out)."""
    out = [answer]
    if re.search(r"(?:^|\s)się(?:\s|$)", answer):
        short = re.sub(r"\s+", " ", re.sub(r"(?:^|\s)się(?=\s|$)", " ", answer)).strip()
        if short:
            out.append(short)
    return out


def _slashes(form: str | None) -> list[str]:
    return [p.strip() for p in form.split(" / ")] if form else []


def _answers(forms: list[str]) -> tuple[str, ...]:
    seen: list[str] = []
    for form in forms:
        for v in _variants(form):
            if v and v not in seen:
                seen.append(v)
    return tuple(seen)


# ----------------------------------------------------------------------------- Polish
def _pl_verbs(verbs: dict) -> list[Question]:
    out = []
    for card, entries in verbs.items():
        for v in entries:
            inf = v.get("infinitive", card)
            tense = "future" if v.get("aspect") == "perfective" else "present"
            for pron, form in zip(PL_PRONOUNS, v.get("forms", [])):
                if form:
                    out.append(Question("verbs", card, f"{pron} ___", f"{inf} · {tense}", "", _answers([form])))
            for pron, form in zip(PL_PAST, v.get("past") or []):
                if form:
                    out.append(Question("verbs", card, f"{pron} ___", f"{inf} · past tense", "", _answers([form])))
            for pron, form in zip(PL_IMPERATIVE, v.get("imperative") or []):
                if form:
                    out.append(Question("verbs", card, f"{pron} ___", f"{inf} · imperative", "", _answers([form])))
    return out


def _pl_nouns(nouns: dict) -> list[Question]:
    out = []
    for card, entries in nouns.items():
        for n in entries:
            lemma = n.get("lemma", card)
            for number in ("singular", "plural"):
                for i, form in enumerate(n.get(number) or []):
                    if not form or (number == "singular" and i == 0):
                        continue
                    case, ask = PL_CASES[i]
                    out.append(Question("nouns", card, f"{lemma} → ___", f"{case} {number}", ask, _answers(_slashes(form))))
    return out


def _pl_adjectives(adjs: dict) -> list[Question]:
    out = []
    for card, entries in adjs.items():
        for a in entries:
            lemma = a.get("lemma", card)
            for key, name in PL_ADJ:
                for i, form in enumerate(a["forms"].get(key) or []):
                    if not form or i == 6 or (key == "m" and i == 0):
                        continue
                    case, ask = PL_CASES[i]
                    out.append(Question("adjectives", card, f"{lemma} → ___", f"{name} {case}", ask, _answers(_slashes(form))))
    return out


# ----------------------------------------------------------------------------- French
def _fr_verbs(verbs: dict) -> list[Question]:
    out = []
    for card, entries in verbs.items():
        for v in entries:
            inf = v.get("infinitive", card)
            for tense in french.TENSES:
                forms = v["tenses"].get(tense)
                if not (isinstance(forms, list) and len(forms) == 6):
                    continue
                for form in forms:
                    m = FR_PRONOUN_CHECK.match(form)
                    subject = m.group(0) if m else ""
                    rest = form[len(subject):]
                    answers = tuple(a for a in french.expand_optional(rest) if a)
                    if answers:
                        out.append(Question("verbs", card, f"{subject}___", f"{inf} · {french.TENSE_LABELS[tense]}", "", answers))
    return out


def _fr_nouns(nouns: dict) -> list[Question]:
    out = []
    for card, entries in nouns.items():
        for n in entries:
            sing, plur = n.get("singular"), n.get("plural")
            if sing and plur and sing != plur:
                article = re.match(r"^(?:l'|la |le |les |un |une |des )", plur, re.IGNORECASE)
                prefix = article.group(0) if article else ""
                answers = tuple(dict.fromkeys(a for a in (plur[len(prefix):], plur) if a))
                out.append(Question("nouns", card, f"{sing} → {prefix}___", "plural", "", answers))
    return out


def _fr_adjectives(adjs: dict) -> list[Question]:
    out = []
    for card, entries in adjs.items():
        for a in entries:
            base = a["forms"]["ms"]
            for key, name in french.ADJ_LABELS:
                if key != "ms" and a["forms"].get(key):
                    out.append(Question("adjectives", card, f"{base} → ___", name, "", (a["forms"][key],)))
    return out


def build_pool(language: str, verbs: dict, nouns: dict, adjectives: dict) -> dict[str, list[Question]]:
    """Every question the tables can make, by category. `language` is "pl" or "fr"."""
    if language == "fr":
        return {"verbs": _fr_verbs(verbs), "nouns": _fr_nouns(nouns), "adjectives": _fr_adjectives(adjectives)}
    return {"verbs": _pl_verbs(verbs), "nouns": _pl_nouns(nouns), "adjectives": _pl_adjectives(adjectives)}


def pick(pool: dict[str, list[Question]], categories, count: int, rng: random.Random) -> list[Question]:
    """`count` different questions: a category is drawn first (so a big table can't drown the others)."""
    left = {c: list(pool.get(c, [])) for c in categories if pool.get(c)}
    out: list[Question] = []
    while left and len(out) < count:
        cat = rng.choice(sorted(left))
        out.append(left[cat].pop(rng.randrange(len(left[cat]))))
        if not left[cat]:
            del left[cat]
    return out


def check(question: Question, text: str, language: str = "pl") -> str:
    """'correct', 'accents' (right letters, accents missing or wrong) or 'wrong'."""
    given = [norm(text)]
    if language == "fr":          # the subject may be typed too: "il/elle est aperçu"
        given.append(norm(FR_PRONOUN_CHECK.sub("", given[0], count=1)))
    given = [g for g in given if g]
    if any(g == norm(a) for g in given for a in question.answers):
        return "correct"
    if any(fold(g) == fold(a) for g in given for a in question.answers):
        return "accents"
    return "wrong"
