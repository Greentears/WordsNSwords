"""Conjugation tables (verbs.json) shown when a verb card is revealed."""
from __future__ import annotations

import json
from html import escape
from pathlib import Path

PRONOUNS = ["ja", "ty", "on / ona / ono", "my", "wy", "oni / one"]
PAST_LABELS = ["on", "ona", "ono", "oni", "one"]
IMPERATIVE_LABELS = ["ty", "my", "wy"]
ASPECT_LABEL = {
    "imperfective": "present tense",
    "perfective": "future tense (perfective verbs have no present)",
}


def load_conjugations(path: Path) -> dict[str, list[dict]]:
    """Read verbs.json -> {card word: [{"infinitive", "aspect", "forms": [6]}]}.

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
        verbs = [
            v for v in item.get("verbs", [])
            if isinstance(v, dict) and isinstance(v.get("forms"), list) and len(v["forms"]) == 6
        ]
        if verbs:
            result[item["card"]] = verbs
    return result


def _row(title: str, forms, labels: list[str], muted: str) -> str:
    """One extra line (past tense / imperative) under the present-tense table."""
    if not isinstance(forms, list) or len(forms) != len(labels):
        return ""
    cells = "".join(
        f'<td style="padding:1px 12px; text-align:center;">'
        f'<span style="color:{muted}; font-size:11px;">{escape(label)}</span><br>'
        f'<span style="font-size:15px;">{escape(str(form))}</span></td>'
        for label, form in zip(labels, forms)
    )
    return (
        f'<div style="color:{muted}; font-size:12px; text-align:center;">{title}</div>'
        f'<table align="center" cellspacing="0"><tr>{cells}</tr></table>'
    )


def conjugation_html(verbs: list[dict], muted: str) -> str:
    """Small tables: two rows of three persons for each verb on the card."""
    blocks = []
    for verb in verbs:
        caption = f"{verb.get('infinitive', '')} · {ASPECT_LABEL.get(verb.get('aspect'), '')}".strip(" ·")
        rows = []
        for start in (0, 3):
            cells = "".join(
                f'<td style="padding:2px 18px; text-align:center;">'
                f'<span style="color:{muted}; font-size:12px;">{escape(PRONOUNS[i])}</span><br>'
                f'<b style="font-size:17px;">{escape(str(verb["forms"][i]))}</b></td>'
                for i in range(start, start + 3)
            )
            rows.append(f"<tr>{cells}</tr>")
        extra = _row("past tense", verb.get("past"), PAST_LABELS, muted) + _row(
            "imperative", verb.get("imperative"), IMPERATIVE_LABELS, muted
        )
        blocks.append(
            f'<div style="color:{muted}; font-size:12px; text-align:center;">{escape(caption)}</div>'
            f'<table align="center" cellspacing="0">{"".join(rows)}</table>' + extra
        )
    return "<br>".join(blocks)
