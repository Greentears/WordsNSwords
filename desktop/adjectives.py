"""Adjective tables (adjectives.json): seven cases x masculine / feminine / neuter / plural."""
from __future__ import annotations

import json
from html import escape
from pathlib import Path

from nouns import CASES

COLUMNS = [("m", "masculine"), ("f", "feminine"), ("n", "neuter"), ("pl", "plural (virile / other)")]


def load_adjectives(path: Path) -> dict[str, list[dict]]:
    """Read adjectives.json -> {card word: [{"lemma", "forms": {"m","f","n","pl": [7]}}]}.

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
        adjectives = []
        for adj in item.get("adjectives", []):
            forms = adj.get("forms") if isinstance(adj, dict) else None
            if isinstance(forms, dict) and all(
                isinstance(forms.get(key), list) and len(forms[key]) == 7 for key, _ in COLUMNS
            ):
                adjectives.append(adj)
        if adjectives:
            result[item["card"]] = adjectives
    return result


def _cell(form, bold: bool, muted: str) -> str:
    if not form:
        return f'<td style="padding:1px 12px; color:{muted};">–</td>'
    text = escape(str(form))
    return f'<td style="padding:1px 12px;">{"<b>" + text + "</b>" if bold else text}</td>'


def _one_table(adj: dict, muted: str) -> str:
    head = "".join(
        f'<td style="padding:1px 12px; color:{muted}; font-size:12px;">{label}</td>'
        for _, label in COLUMNS
    )
    rows = [f"<tr><td></td>{head}</tr>"]
    for i, (case, question) in enumerate(CASES):
        label = (
            f'<td style="padding:1px 10px 1px 0;"><span style="font-size:12px;">{case}</span> '
            f'<span style="color:{muted}; font-size:11px;">{escape(question)}</span></td>'
        )
        cells = "".join(_cell(adj["forms"][key][i], i == 0, muted) for key, _ in COLUMNS)
        rows.append(f"<tr>{label}{cells}</tr>")
    return (
        f'<div style="color:{muted}; font-size:12px;" align="center">{escape(adj.get("lemma", ""))} · adjective</div>'
        f'<table cellspacing="0" cellpadding="0" align="center" style="font-size:14px;">{"".join(rows)}</table>'
    )


def adjective_html(adjectives: list[dict], muted: str) -> str:
    """One table per adjective (stacked: the tables are wide)."""
    return "<br>".join(_one_table(a, muted) for a in adjectives)
