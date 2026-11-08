"""Check and merge new words made by an AI (or by hand) into a deck folder.

The input is ONE JSON object; every key is optional:

    {"words":      [{"word", "translation", "sentence", "sentence_translation"}],
     "verbs":      [{"card", "verbs": [{"infinitive", "aspect", "forms": [6], "past": [5], "imperative": [3]}]}],
     "nouns":      [{"card", "nouns": [{"lemma", "gender", "singular": [7], "plural": [7]}]}],
     "adjectives": [{"card", "adjectives": [{"lemma", "forms": {"m": [7], "f": [7], "n": [7], "pl": [7]}}]}],
     "examples":   {"card word": [{"pl", "en"}]},
     "sentences":  [{"pl", "en", "words": ["card word"]}]}

validate() lists every problem in plain words; merge() writes the deck's JSON files and never overwrites what
is already there (a card that exists is skipped, so your levels and edits are safe).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ASPECTS = ("imperfective", "perfective")
GENDERS = ("m", "f", "n", "pl", "num")
PARTS = ("words", "verbs", "nouns", "adjectives", "examples", "sentences")


def _is_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _forms(value: Any, count: int, allow_none: bool = False) -> bool:
    return (isinstance(value, list) and len(value) == count
            and all(_is_text(v) or (allow_none and v is None) for v in value))


def validate(data: Any, existing_cards: set[str] | None = None) -> list[str]:
    """Every problem found in `data`; an empty list means it can be merged."""
    if not isinstance(data, dict):
        return ["The answer must be one JSON object with the keys words, verbs, nouns, adjectives, examples, sentences."]
    errors: list[str] = []
    known = set(existing_cards or ())
    words = data.get("words", [])
    if not isinstance(words, list):
        errors.append('"words" must be a list.')
        words = []
    for i, w in enumerate(words, 1):
        if not isinstance(w, dict) or not _is_text(w.get("word")) or not _is_text(w.get("translation")):
            errors.append(f'words #{i}: needs a "word" and a "translation".')
            continue
        known.add(w["word"].strip())
        for key in ("sentence", "sentence_translation"):
            if key in w and not isinstance(w[key], str):
                errors.append(f'words "{w["word"]}": "{key}" must be text.')
        if bool(w.get("sentence")) != bool(w.get("sentence_translation")):
            errors.append(f'words "{w["word"]}": give both "sentence" and "sentence_translation", or neither.')
    for part in ("verbs", "nouns", "adjectives"):
        entries = data.get(part, [])
        if not isinstance(entries, list):
            errors.append(f'"{part}" must be a list.')
            continue
        for i, e in enumerate(entries, 1):
            where = f'{part} #{i}'
            if not isinstance(e, dict) or not _is_text(e.get("card")) or not isinstance(e.get(part), list) or not e[part]:
                errors.append(f'{where}: needs a "card" and a non-empty "{part}" list.')
                continue
            if e["card"].strip() not in known:
                errors.append(f'{where}: card "{e["card"]}" is not in words (spell it exactly like the card).')
            for item in e[part]:
                if not isinstance(item, dict):
                    errors.append(f'{where}: every item must be an object.')
                elif part == "verbs":
                    if not _is_text(item.get("infinitive")) or item.get("aspect") not in ASPECTS:
                        errors.append(f'{where}: needs "infinitive" and "aspect" ({" or ".join(ASPECTS)}).')
                    if not _forms(item.get("forms"), 6):
                        errors.append(f'{where}: "forms" must be 6 forms (ja, ty, on/ona/ono, my, wy, oni/one).')
                    if "past" in item and not _forms(item["past"], 5):
                        errors.append(f'{where}: "past" must be 5 forms (m, f, n, men plural, other plural).')
                    if "imperative" in item and not _forms(item["imperative"], 3):
                        errors.append(f'{where}: "imperative" must be 3 forms (ty, my, wy).')
                elif part == "nouns":
                    if not _is_text(item.get("lemma")) or item.get("gender") not in GENDERS:
                        errors.append(f'{where}: needs "lemma" and "gender" ({", ".join(GENDERS)}).')
                    if not _forms(item.get("singular"), 7, allow_none=True) or not _forms(item.get("plural"), 7, allow_none=True):
                        errors.append(f'{where}: "singular" and "plural" must each have 7 cases (null where none).')
                else:
                    forms = item.get("forms")
                    if not _is_text(item.get("lemma")) or not isinstance(forms, dict) \
                            or not all(_forms(forms.get(g), 7) for g in ("m", "f", "n", "pl")):
                        errors.append(f'{where}: needs "lemma" and "forms" with m, f, n, pl of 7 cases each.')
    examples = data.get("examples", {})
    if not isinstance(examples, dict):
        errors.append('"examples" must be an object {card: [{"pl", "en"}]}.')
    else:
        for card, items in examples.items():
            if card not in known:
                errors.append(f'examples: card "{card}" is not in words.')
            if not isinstance(items, list) or not all(isinstance(x, dict) and _is_text(x.get("pl")) and _is_text(x.get("en")) for x in items):
                errors.append(f'examples "{card}": must be a list of {{"pl", "en"}}.')
    sentences = data.get("sentences", [])
    if not isinstance(sentences, list):
        errors.append('"sentences" must be a list.')
    else:
        for i, s in enumerate(sentences, 1):
            if not isinstance(s, dict) or not _is_text(s.get("pl")) or not _is_text(s.get("en")) \
                    or not isinstance(s.get("words"), list) or not s["words"]:
                errors.append(f'sentences #{i}: needs "pl", "en" and a non-empty "words" list.')
            elif not all(w in known for w in s["words"]):
                errors.append(f'sentences #{i}: "words" must be cards of the deck (missing: '
                              f'{", ".join(w for w in s["words"] if w not in known)}).')
    unknown = [k for k in data if k not in PARTS]
    if unknown:
        errors.append(f'Unknown keys: {", ".join(unknown)}.')
    return errors


def _read(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def _write(path: Path, data: Any, indent: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=indent), encoding="utf-8")
    tmp.replace(path)


def merge(folder: str | Path, data: dict) -> dict[str, int]:
    """Add `data` to the deck folder. Existing cards, tables and sentences are never changed."""
    folder = Path(folder)
    words = _read(folder / "words.json", [])
    have = {w["word"] for w in words}
    added = {"words": 0, "skipped": 0, "verbs": 0, "nouns": 0, "adjectives": 0, "examples": 0, "sentences": 0}
    for w in data.get("words", []):
        if w["word"].strip() in have:
            added["skipped"] += 1
            continue
        card = {"word": w["word"].strip(), "translation": w["translation"].strip()}
        for key in ("sentence", "sentence_translation"):
            if w.get(key):
                card[key] = w[key].strip()
        words.append(card)
        have.add(card["word"])
        added["words"] += 1
    _write(folder / "words.json", words, 4)

    for part in ("verbs", "nouns", "adjectives"):
        table = _read(folder / f"{part}.json", [])
        done = {e["card"] for e in table}
        for entry in data.get(part, []):
            if entry["card"] not in done:
                table.append(entry)
                done.add(entry["card"])
                added[part] += 1
        if data.get(part):
            _write(folder / f"{part}.json", table, 2)

    if data.get("examples"):
        examples = _read(folder / "examples.json", {})
        for card, items in data["examples"].items():
            mine = examples.setdefault(card, [])
            for item in items:
                if item not in mine:
                    mine.append(item)
                    added["examples"] += 1
        _write(folder / "examples.json", examples, 2)

    if data.get("sentences"):
        sentences = _read(folder / "sentences.json", [])
        seen = {s["pl"] for s in sentences}
        for s in data["sentences"]:
            if s["pl"] not in seen:
                sentences.append(s)
                seen.add(s["pl"])
                added["sentences"] += 1
        _write(folder / "sentences.json", sentences, 2)
    return added


def parse_answer(text: str) -> tuple[Any, str | None]:
    """Parse the AI's answer (it may be wrapped in a ```json fence). Returns (data, error)."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else ""
        text = text.rsplit("```", 1)[0]
    try:
        return json.loads(text), None
    except ValueError as exc:
        return None, f"The answer is not valid JSON: {exc}"


def check_and_merge(folder: str | Path, text: str) -> tuple[list[str], dict[str, int]]:
    """Parse the AI's answer, validate it, merge it if it is fine."""
    data, error = parse_answer(text)
    if error:
        return [error], {}
    existing = {w["word"] for w in _read(Path(folder) / "words.json", [])}
    errors = validate(data, existing)
    return (errors, {}) if errors else ([], merge(folder, data))
