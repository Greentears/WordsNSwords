"""Extra example sentences (examples.json): {card word: [{"pl", "en"}, ...]}."""
from __future__ import annotations

import json
from html import escape
from pathlib import Path


def load_examples(path: Path) -> dict[str, list[tuple[str, str]]]:
    """Read examples.json. A missing or broken file simply means "no examples"."""
    try:
        with Path(path).open(encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return {}
    result: dict[str, list[tuple[str, str]]] = {}
    if not isinstance(data, dict):
        return result
    for word, items in data.items():
        pairs = [
            (e["pl"], e.get("en", ""))
            for e in items
            if isinstance(e, dict) and isinstance(e.get("pl"), str) and e["pl"].strip()
        ] if isinstance(items, list) else []
        if pairs:
            result[word] = pairs
    return result


def examples_html(pairs: list[tuple[str, str]], muted: str) -> str:
    lines = [f'<div style="color:{muted}; font-size:12px;" align="center">more examples</div>']
    for pl, en in pairs:
        lines.append(
            f'<div align="center" style="font-size:16px;">{escape(pl)}<br>'
            f'<span style="color:{muted}; font-size:14px;">{escape(en)}</span></div>'
        )
    return "<br>".join(lines)
