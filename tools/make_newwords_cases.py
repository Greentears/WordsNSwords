"""Make web/tests/newwords_cases.json: answers fed to the Python validator/merger, with its verdicts.
The TypeScript port must give the same errors and the same merged deck (web/tests/newwords.test.ts)."""
import json, shutil, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "desktop"))
import newwords  # noqa: E402

FIX = ROOT / "tests" / "fixtures" / "pl-en"
PARTS = ("words", "verbs", "nouns", "adjectives", "examples", "sentences")
Q7 = ["a", "b", "c", "d", "e", "f", "g"]
good = {
    "words": [
        {"word": "kot", "translation": "cat", "sentence": "Mam kota.", "sentence_translation": "I have a cat."},
        {"word": "pić", "translation": "to drink"},
        {"word": "  zielony ", "translation": "green "},
    ],
    "verbs": [{"card": "pić", "verbs": [{"infinitive": "pić", "aspect": "imperfective", "forms": list("123456"),
                                          "past": list("12345"), "imperative": list("123")}]}],
    "nouns": [{"card": "kot", "nouns": [{"lemma": "kot", "gender": "m", "singular": Q7, "plural": Q7[:6] + [None]}]}],
    "adjectives": [{"card": "zielony", "adjectives": [{"lemma": "zielony", "forms": {g: Q7 for g in ("m", "f", "n", "pl")}}]}],
    "examples": {"kot": [{"pl": "Kot śpi.", "en": "The cat sleeps."}]},
    "sentences": [{"pl": "Kot pije.", "en": "The cat drinks.", "words": ["kot", "pić"]}],
}
existing = json.loads((FIX / "words.json").read_text(encoding="utf-8"))[0]["word"]
cases = {
    "good": json.dumps(good),
    "fenced": "```json\n" + json.dumps(good, ensure_ascii=False) + "\n```",
    "not json": "Sure! Here are your words:",
    "empty": "",
    "list": "[]",
    "empty object": "{}",
    "existing skipped": json.dumps({"words": [{"word": existing, "translation": "changed"}, {"word": "nowy", "translation": "new"}]}),
    "duplicate examples": json.dumps({"examples": {existing: [{"pl": "A.", "en": "B."}, {"pl": "A.", "en": "B."}]}}),
    "bad word": json.dumps({"words": [{"word": "", "translation": "x"}, {"word": "a"}, {"word": "b", "translation": "c", "sentence": "x"}]}),
    "unknown card": json.dumps({"verbs": [{"card": "nic", "verbs": [{"infinitive": "x", "aspect": "other", "forms": ["1"]}]}], "examples": {"nic": "x"}}),
    "bad nouns": json.dumps({"words": [{"word": "q", "translation": "q"}], "nouns": [{"card": "q", "nouns": [{"lemma": "q", "gender": "x", "singular": ["a"], "plural": []}]}], "adjectives": [{"card": "q", "adjectives": [{"lemma": "q", "forms": {"m": Q7}}]}]}),
    "bad sentences": json.dumps({"sentences": [{"pl": "x", "en": "y", "words": []}, {"pl": "x", "en": "y", "words": ["zzz", existing]}, 5]}),
    "unknown keys": json.dumps({"foo": 1, "words": "no"}),
    "bad types": json.dumps({"verbs": "x", "examples": [], "sentences": {}}),
    "verb extras": json.dumps({"words": [{"word": "q", "translation": "q"}], "verbs": [{"card": "q", "verbs": [{"infinitive": "q", "aspect": "perfective", "forms": list("123456"), "past": ["1"], "imperative": ["1"]}]}]}),
}
out = []
for name, text in cases.items():
    tmp = Path(tempfile.mkdtemp())
    folder = tmp / "d"
    shutil.copytree(FIX, folder)
    errors, counts = newwords.check_and_merge(folder, text)
    result = {p: json.loads((folder / f"{p}.json").read_text(encoding="utf-8")) if (folder / f"{p}.json").exists() else ([] if p not in ("examples",) else {}) for p in PARTS}
    out.append({"name": name, "text": text, "errors": errors, "counts": counts, "result": result})
    shutil.rmtree(tmp)
base = {p: json.loads((FIX / f"{p}.json").read_text(encoding="utf-8")) if (FIX / f"{p}.json").exists() else ([] if p != "examples" else {}) for p in PARTS}
(ROOT / "web" / "tests" / "newwords_cases.json").write_text(json.dumps({"base": base, "cases": out}, ensure_ascii=False), encoding="utf-8")
print(len(out), "cases;", sum(1 for c in out if not c["errors"]), "valid")
