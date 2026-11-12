"""Write tests/grammar_golden.json: every grammar question the desktop code makes from the starter decks.

Usage: python3 tools/make_grammar_golden.py
"""
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root / "desktop"))
for mod in ("PySide6", "PySide6.QtCore", "PySide6.QtGui", "PySide6.QtWidgets"):
    sys.modules.setdefault(mod, MagicMock())
import adjectives, french, grammar, nouns, verbs  # noqa: E402


def pool(lang, d):
    d = root / "users" / "_template" / d
    if lang == "fr":
        return grammar.build_pool("fr", french.load_verbs(d / "verbs.json"), french.load_nouns(d / "nouns.json"),
                                  french.load_adjectives(d / "adjectives.json"))
    return grammar.build_pool("pl", verbs.load_conjugations(d / "verbs.json"), nouns.load_declensions(d / "nouns.json"),
                              adjectives.load_adjectives(d / "adjectives.json"))


out = {}
for lang, d in (("pl", "pl-en"), ("fr", "fr-en")):
    p = pool(lang, d)
    out[lang] = {cat: [{"category": q.category, "card": q.card, "stem": q.stem, "label": q.label, "hint": q.hint,
                        "answers": list(q.answers)} for q in qs] for cat, qs in p.items()}
checks = []
for lang in ("pl", "fr"):
    for cat, qs in out[lang].items():
        for item in qs[:12]:
            q = grammar.Question(**{**item, "answers": tuple(item["answers"])})
            for text in (item["answers"][0], item["answers"][0].upper(), grammar.fold(item["answers"][0]), "zzz", ""):
                checks.append({"lang": lang, "q": item, "text": text, "verdict": grammar.check(q, text, lang)})
out["checks"] = checks
(Path(__file__).resolve().parent.parent / "tests" / "grammar_golden.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print({k: {c: len(v) for c, v in out[k].items()} for k in ("pl", "fr")}, len(checks), "checks")
