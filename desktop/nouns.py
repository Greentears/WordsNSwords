"""Declension tables (nouns.json): all seven cases, singular and plural."""
from __future__ import annotations

import json
from html import escape
from pathlib import Path

CASES = [
    ("Mianownik", "kto? co?"),
    ("Dopełniacz", "kogo? czego?"),
    ("Celownik", "komu? czemu?"),
    ("Biernik", "kogo? co?"),
    ("Narzędnik", "z kim? z czym?"),
    ("Miejscownik", "o kim? o czym?"),
    ("Wołacz", "o!"),
]
GENDERS = {"m": "masculine", "f": "feminine", "n": "neuter", "pl": "plural only", "num": ""}


def load_declensions(path: Path) -> dict[str, list[dict]]:
    """Read nouns.json -> {card word: [{"lemma", "gender", "singular", "plural"}]}.

    A missing or broken file simply means "no tables".
    """
    try:
        with Path(path).open(encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return {}
    result: dict[str, list[dict]] = {}
    for item in data if isinstance(data, list) else []:
        if not isinstance(item, dict) or not isinstance(item.get("card"), str):
            continue
        nouns = [
            n for n in item.get("nouns", [])
            if isinstance(n, dict)
            and isinstance(n.get("singular"), list) and len(n["singular"]) == 7
            and isinstance(n.get("plural"), list) and len(n["plural"]) == 7
        ]
        if nouns:
            result[item["card"]] = nouns
    return result


def _cell(form, bold: bool, muted: str) -> str:
    if not form:
        return f'<td style="padding:1px 14px; color:{muted};">–</td>'
    text = escape(str(form))
    return f'<td style="padding:1px 14px;">{"<b>" + text + "</b>" if bold else text}</td>'


def _one_table(noun: dict, muted: str) -> str:
    gender = GENDERS.get(noun.get("gender", ""), "")
    numeral = noun.get("gender") == "num"
    caption = f"{noun.get('lemma', '')} · " + ("numeral" if numeral else "noun") + (f", {gender}" if gender else "")
    plural_head = "plural (rare)" if noun.get("rare_plural") else "plural"
    head = f'<td style="padding:1px 14px; color:{muted}; font-size:12px;">{"forms" if numeral else "singular"}</td>'
    if not numeral:
        head += f'<td style="padding:1px 14px; color:{muted}; font-size:12px;">{plural_head}</td>'
    rows = [f"<tr><td></td>{head}</tr>"]
    for i, (case, question) in enumerate(CASES):
        label = (
            f'<td style="padding:1px 10px 1px 0;"><span style="font-size:12px;">{case}</span> '
            f'<span style="color:{muted}; font-size:11px;">{escape(question)}</span></td>'
        )
        cells = _cell(noun["singular"][i], i == 0, muted)
        if not numeral:
            cells += _cell(noun["plural"][i], i == 0, muted)
        rows.append(f"<tr>{label}{cells}</tr>")
    return (
        f'<div style="color:{muted}; font-size:12px;" align="center">{escape(caption)}</div>'
        f'<table cellspacing="0" cellpadding="0" align="center" style="font-size:14px;">{"".join(rows)}</table>'
    )


def declension_html(nouns: list[dict], muted: str) -> str:
    """One table per noun; two nouns on a card sit side by side."""
    tables = [_one_table(n, muted) for n in nouns]
    if len(tables) == 1:
        return tables[0]
    cells = "".join(f'<td style="padding:0 16px;" valign="top">{t}</td>' for t in tables)
    return f'<table align="center" cellspacing="0"><tr>{cells}</tr></table>'
