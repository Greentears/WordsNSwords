"""French grammar tables (verbs.json / nouns.json / adjectives.json of a fr-en deck).

    verbs:      {"card", "verbs": [{"infinitive", "tenses": {"present", "passe_compose", "imparfait", "futur", "conditionnel"}}]}
                each tense is a list of 6 forms: je, tu, il/elle, nous, vous, ils/elles
    nouns:      {"card", "nouns": [{"lemma", "gender": "m"|"f", "singular": "l'enjeu", "plural": "les enjeux" | null}]}
    adjectives: {"card", "adjectives": [{"lemma", "forms": {"ms", "fs", "mp", "fp"}}]}
"""
from __future__ import annotations

import itertools
import json
import re
from html import escape
from pathlib import Path

TENSES = ("present", "passe_compose", "imparfait", "futur", "conditionnel")
TENSE_LABELS = {"present": "Présent", "passe_compose": "Passé composé", "imparfait": "Imparfait",
                "futur": "Futur simple", "conditionnel": "Conditionnel"}
GENDERS = {"m": "masculine", "f": "feminine"}
ADJ_LABELS = (("ms", "masculine singular"), ("fs", "feminine singular"), ("mp", "masculine plural"), ("fp", "feminine plural"))

_SUBJECT = re.compile(r"^(?:j'|je |tu |il/elle |ils/elles |nous |vous )", re.IGNORECASE)
_REFLEXIVE = re.compile(r"^(?:me |m'|te |t'|se |s'|nous |vous )", re.IGNORECASE)
_ARTICLE = re.compile(r"^(?:l'|la |le |les |un |une |des )", re.IGNORECASE)
_OPTIONAL = re.compile(r"\(([^()]*)\)")


def _read_list(path: Path):
    try:
        with Path(path).open(encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return []
    return data if isinstance(data, list) else []


def _by_card(path: Path, key: str, ok) -> dict[str, list[dict]]:
    result: dict[str, list[dict]] = {}
    for item in _read_list(path):
        if not isinstance(item, dict) or not isinstance(item.get("card"), str):
            continue
        entries = [e for e in item.get(key, []) if isinstance(e, dict) and ok(e)]
        if entries:
            result[item["card"]] = entries
    return result


def _six(value) -> bool:
    return isinstance(value, list) and len(value) == 6


def load_verbs(path: Path) -> dict[str, list[dict]]:
    return _by_card(path, "verbs", lambda v: isinstance(v.get("tenses"), dict) and any(_six(v["tenses"].get(t)) for t in TENSES))


def load_nouns(path: Path) -> dict[str, list[dict]]:
    return _by_card(path, "nouns", lambda n: isinstance(n.get("singular"), str))


def load_adjectives(path: Path) -> dict[str, list[dict]]:
    return _by_card(path, "adjectives", lambda a: isinstance(a.get("forms"), dict) and all(isinstance(a["forms"].get(k), str) for k, _ in ADJ_LABELS))


def expand_optional(form: str) -> list[str]:
    """'aperçu(e)(s)' -> ['aperçu', 'aperçue', 'aperçus', 'aperçues'] (every combination of the bracketed letters)."""
    parts = _OPTIONAL.split(form)          # text, bracket, text, bracket, ...
    if len(parts) == 1:
        return [form]
    options = [[parts[i]] if i % 2 == 0 else ["", parts[i]] for i in range(len(parts))]
    seen: list[str] = []
    for combo in itertools.product(*options):
        text = "".join(combo)
        if text not in seen:
            seen.append(text)
    return seen


def cloze_forms(forms: list[str]) -> list[str]:
    """Forms as they appear in a sentence: no leading subject / reflexive pronoun, bracketed letters expanded.
    'il/elle s'est aperçu(e)' -> 'est aperçu', 'est aperçue'."""
    out: list[str] = []
    for form in forms:
        if not form:
            continue
        text = _SUBJECT.sub("", form.strip(), count=1)
        text = _REFLEXIVE.sub("", text, count=1)
        for variant in expand_optional(text):
            if variant and variant not in out:
                out.append(variant)
    return out


def known_forms(verbs: dict, nouns: dict, adjectives: dict) -> dict[str, list[str]]:
    """Every inflected form per card word, ready for the fill-in-the-blank quiz."""
    forms: dict[str, list[str]] = {}
    for word, entries in verbs.items():
        forms.setdefault(word, []).extend(cloze_forms([f for v in entries for t in TENSES for f in v["tenses"].get(t, [])]))
    for word, entries in nouns.items():
        raw = [f for n in entries for f in (n.get("singular"), n.get("plural")) if f]
        forms.setdefault(word, []).extend(cloze_forms([_ARTICLE.sub("", f) for f in raw]))
    for word, entries in adjectives.items():
        forms.setdefault(word, []).extend(cloze_forms([a["forms"][k] for a in entries for k, _ in ADJ_LABELS]))
    return forms


def verb_html(verbs: list[dict], muted: str) -> str:
    blocks = []
    for verb in verbs:
        tenses = [t for t in TENSES if _six(verb["tenses"].get(t))]
        head = "".join(f'<th style="padding:2px 10px; color:{muted}; font-size:12px; font-weight:normal;">{TENSE_LABELS[t]}</th>' for t in tenses)
        rows = []
        for i in range(6):
            cells = "".join(f'<td style="padding:1px 10px; font-size:14px;">{escape(str(verb["tenses"][t][i]))}</td>' for t in tenses)
            rows.append(f"<tr>{cells}</tr>")
        blocks.append(
            f'<div style="color:{muted}; font-size:12px; text-align:center;">{escape(str(verb.get("infinitive", "")))}</div>'
            f'<table align="center" cellspacing="0"><tr>{head}</tr>{"".join(rows)}</table>')
    return "<br>".join(blocks)


def noun_html(nouns: list[dict], muted: str) -> str:
    blocks = []
    for noun in nouns:
        gender = GENDERS.get(noun.get("gender"), "")
        caption = f"{noun.get('lemma', '')} · noun" + (f", {gender}" if gender else "")
        plural = noun.get("plural")
        blocks.append(
            f'<div style="color:{muted}; font-size:12px; text-align:center;">{escape(caption)}</div>'
            f'<table align="center" cellspacing="0"><tr>'
            f'<td style="padding:2px 18px; text-align:center;"><span style="color:{muted}; font-size:12px;">singular</span><br><b style="font-size:17px;">{escape(noun["singular"])}</b></td>'
            + (f'<td style="padding:2px 18px; text-align:center;"><span style="color:{muted}; font-size:12px;">plural</span><br><b style="font-size:17px;">{escape(plural)}</b></td>' if plural else "")
            + "</tr></table>")
    return "<br>".join(blocks)


def adjective_html(adjectives: list[dict], muted: str) -> str:
    blocks = []
    for adj in adjectives:
        cells = "".join(
            f'<td style="padding:2px 18px; text-align:center;"><span style="color:{muted}; font-size:12px;">{label}</span><br><b style="font-size:16px;">{escape(adj["forms"][k])}</b></td>'
            for k, label in ADJ_LABELS)
        blocks.append(
            f'<div style="color:{muted}; font-size:12px; text-align:center;">{escape(str(adj.get("lemma", "")))} · adjective</div>'
            f'<table align="center" cellspacing="0"><tr>{cells}</tr></table>')
    return "<br>".join(blocks)
