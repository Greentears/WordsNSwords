"""Run the desktop app's own functions and write tests/golden.json for the TypeScript tests.

Usage: python3 tools/make_golden.py [path/to/flashcards]   (default ../desktop)
"""
import json, random, sys, tempfile, types
from pathlib import Path
from unittest.mock import MagicMock

src = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent.parent / "desktop").resolve()
sys.path.insert(0, str(src))
for mod in ("PySide6", "PySide6.QtCore", "PySide6.QtGui", "PySide6.QtWidgets"):
    sys.modules.setdefault(mod, MagicMock())
# sentences.py subclasses QDialog: give the stubs real classes.
sys.modules["PySide6.QtWidgets"].QDialog = type("QDialog", (), {})

import flashcards as F
FIX = Path(__file__).resolve().parent.parent.parent / "tests" / "fixtures" / "pl-en"
from verbs import load_conjugations
from nouns import load_declensions
from adjectives import load_adjectives
from examples import load_examples

random.seed(12345)
deck = F.FlashcardDeck.from_json(FIX / "words.json")
conj = load_conjugations(FIX / "verbs.json")
decl = load_declensions(FIX / "nouns.json")
adj = load_adjectives(FIX / "adjectives.json")
ex = load_examples(FIX / "examples.json")

forms = {}
for w, vs in conj.items():
    forms.setdefault(w, []).extend(f for v in vs for f in v["forms"] + v.get("past", []) + v.get("imperative", []) if f)
for w, ns in decl.items():
    forms.setdefault(w, []).extend(f for n in ns for f in n["singular"] + n["plural"] if f)
for w, aa in adj.items():
    forms.setdefault(w, []).extend(f for a in aa for col in a["forms"].values() for f in col if f)

out = {}

# 1. check_answer ----------------------------------------------------------
checks = []
def add_check(given, expected, ia=True):
    checks.append({"given": given, "expected": expected, "ignore_accents": ia,
                   "result": list(F.check_answer(given, expected, ia))})
for w in deck.words:
    for exp in (w.word, w.translation):
        stripped = F._strip_accents(exp)
        first = exp.split(" / ")[0]
        no_br = __import__("re").sub(r"\s*\([^)]*\)", "", exp)
        for given in {exp, exp.upper(), exp + "!", " " + exp + " ", stripped, first, no_br,
                      exp[:-1], exp.replace(" ", "  "), "to " + exp, exp[3:] if exp.startswith("to ") else exp,
                      exp.replace("(", "").replace(")", ""), "wrong answer"}:
            add_check(given, exp)
        add_check(stripped, exp, False)
        add_check(exp, exp, False)
for given, exp in [
    ("", "pies"), ("   ", "pies"), ("PIES", "pies"), ("zolw", "żółw"), ("żółw", "zolw"), ("Łódź", "lodz"),
    ("lodz", "Łódź"), ("run by", "run / operated by"), ("operated by", "run / operated by"),
    ("allow", "to allow"), ("to allow", "to allow"), ("pochodzic", "pochodzić (z)"), ("pochodzić z", "pochodzić (z)"),
    ("it’s", "it's"), ("hello?!", "hello"), ("a / b", "a / b"), ("b", "a / b"), ("a/b", "a / b"),
    ("dziękuję…", "dziękuję"), ("„cześć”", "cześć"), ("kot", "Kot"), ("to", "to be"), ("be", "to be"),
]:
    add_check(given, exp)
    add_check(given, exp, False)
out["check"] = checks

# 2. blank_sentence --------------------------------------------------------
blanks = []
for w in deck.words:
    sentences = [w.sentence] + [e[0] for e in ex.get(w.word, [])]
    for s in sentences:
        for fm in (None, forms.get(w.word)):
            r = F.blank_sentence(w, fm, s)
            blanks.append({"word": w.word, "sentence": w.sentence, "text": s, "use_forms": fm is not None,
                           "result": list(r) if r else None})
out["blank"] = blanks

# 3. smart mix counts (the allocation is deterministic, only *which* cards is random)
mix = []
def synth(c0, c1, c2, c3, cn, c4):
    ws = []
    for lv, n in ((0, c0), (1, c1), (2, c2), (3, c3), (None, cn), (4, c4)):
        for i in range(n):
            ws.append(F.Word(f"w{lv}-{i}", "t", level=lv))
    return F.FlashcardDeck(ws)
for sizes in [(30, 30, 30, 5, 5, 2), (0, 0, 10, 0, 0, 0), (2, 40, 3, 4, 4, 0), (20, 1, 1, 9, 9, 0), (5, 5, 5, 0, 0, 0), (0, 3, 0, 0, 0, 0), (50, 50, 50, 0, 0, 0), (1, 1, 1, 1, 1, 1), (0, 0, 0, 9, 9, 9)]:
    d = synth(*sizes)
    for size in (1, 2, 3, 7, 10, 13, 20, 40, 100, 1000):
        ids = d.mixed_sample(size)
        counts = {str(lv): sum(1 for i in ids if d.words[i].level == lv) for lv in (0, 1, 2)}
        mix.append({"sizes": list(sizes), "size": size, "n": len(ids), "counts": counts,
                    "unique": len(set(ids)) == len(ids)})
    # with an 'allowed' restriction (first half of ids)
    allowed = set(range(0, len(d.words), 2))
    ids = d.mixed_sample(10, allowed=allowed)
    mix.append({"sizes": list(sizes), "size": 10, "allowed": "even", "n": len(ids),
                "counts": {str(lv): sum(1 for i in ids if d.words[i].level == lv) for lv in (0, 1, 2)}})
out["mix"] = mix

# 4. search ----------------------------------------------------------------
queries = ["pies", "PIES", "dog", "zolw", "żółw", "lodz", "łódź", "zz", "a", "e", " ", "cze", "bardzo", "to be", "kot", "miasto",
           "park", "ą", "ó", "wszystko", "drzwi", "  dog  ", "mój pies"]
searches = []
d = F.FlashcardDeck.from_json(FIX / "words.json")
for q in queries:
    n = d.search(q)
    searches.append({"query": q, "count": n, "ids": list(d._order)})
out["search"] = searches

# 5. filters, ordering, mark, archive on a synthetic deck with fails --------
def mk():
    ws = [F.Word(f"w{i}", f"t{i}", level=lv, fails=fl) for i, (lv, fl) in enumerate(
        [(None, 0), (0, 3), (1, 0), (2, 5), (3, 1), (4, 9), (0, 0), (3, 0), (None, 2), (1, 7), (4, 0), (2, 2)])]
    return F.FlashcardDeck(ws)
d = mk()
filters = {}
for mode in ("all", "new", "level0", "level1", "level2", "level3", "level4", "failed"):
    d.set_mode(mode); filters[mode] = list(d._order)
out["filters"] = filters
d = mk(); d.set_mode("level1")
ops = []
def snap(): return {"levels": [w.level for w in d.words], "fails": [w.fails for w in d.words], "index": d.index,
                    "order": list(d._order), "results": {str(k): v for k, v in d.results.items()}}
d.mark(3); ops.append(["mark", 3, snap()])
d.next(); d.mark(4); ops.append(["mark", 4, snap()])  # level 1 card cannot be archived
d.next() if not d.is_last else None; ops.append(["next", None, snap()])
d.record_fail(0); ops.append(["fail", 0, snap()])
d.restart(); ops.append(["restart", None, snap()])
d.set_mode("level3"); d.mark(4); ops.append(["archive known", 4, snap()])
d.set_mode("all"); ops.append(["all after archive", None, snap()])
d.set_mode("level4"); d.mark(1); ops.append(["unarchive", 1, snap()])
out["ops"] = ops
out["counts"] = {"active": mk().active_count, "new": mk().new_count, "levels": [mk().level_count(i) for i in range(5)]}

# 6. serialisation: byte-exact save() ---------------------------------------
messy = [
    {"word": " pies ", "translation": "dog ", "sentence": " Mój pies. ", "sentence_translation": "My dog.", "level": 2, "fails": 3, "tag": "x", "zz": [1, {"a": "ż"}]},
    {"word": "kot", "translation": "cat", "known": True},
    {"word": "ptak", "translation": "bird", "known": False, "extra": None},
    {"word": "ryba", "translation": "fish", "level": 9, "fails": -2},
    {"word": "koń", "translation": "horse", "level": 4, "fails": 0, "sentence": ""},
    {"word": "a/b \"q\"  ", "translation": "t\\n", "level": True, "fails": 2.5},
]
tmp = Path(tempfile.mkdtemp()) / "m.json"
tmp.write_text(json.dumps(messy, ensure_ascii=False), encoding="utf-8")
md = F.FlashcardDeck.from_json(tmp)
md.save()
out["serialise"] = {"input": messy, "output": tmp.read_text(encoding="utf-8")}
rt = Path(tempfile.mkdtemp()) / "w.json"
rt.write_bytes((FIX / "words.json").read_bytes())
rd = F.FlashcardDeck.from_json(rt); rd.save()
norm = lambda b: b.replace(b"\r\n", b"\n").rstrip(b"\n")
out["roundtrip"] = {"same_as_source": norm(rt.read_bytes()) == norm((FIX / "words.json").read_bytes())}
bad = []
for data in ({}, [], [1], [{"word": "", "translation": "x"}], [{"word": "a", "translation": " "}], [{"word": 1, "translation": "x"}]):
    p = Path(tempfile.mkdtemp()) / "b.json"; p.write_text(json.dumps(data))
    try: F.FlashcardDeck.from_json(p); bad.append({"data": data, "error": None})
    except ValueError as e: bad.append({"data": data, "error": str(e)})
out["invalid"] = bad

# 7. table loaders ----------------------------------------------------------
out["tables"] = {
    "conj": {k: len(v) for k, v in conj.items()}, "decl": {k: len(v) for k, v in decl.items()},
    "adj": {k: len(v) for k, v in adj.items()}, "examples": {k: [list(p) for p in v] for k, v in ex.items()},
    "forms": forms,
}

# 8. sentences --------------------------------------------------------------
import sentences as S
sents = S.load_sentences(FIX / "sentences.json")
sd = mk()
out["sentences"] = {"loaded": len(sents)}
real = F.FlashcardDeck.from_json(FIX / "words.json")
# deterministic part: which sentences are eligible and their weights (via a hook on random)
eligible = []
by_word = {w.word: w for w in real.words}
for s in sents:
    levels = [by_word[t].level for t in s.get("words", []) if t in by_word]
    learning = [lv for lv in levels if lv in F.MIX_WEIGHTS]
    wgt = 0.0 if not learning else float(sum(F.MIX_WEIGHTS[lv] for lv in learning)) * (1.5 if len(set(learning)) > 1 else 1)
    eligible.append(wgt)
out["sentences"]["weights"] = eligible
# give the real deck some levels so weights vary
random.seed(7)
for w in real.words:
    w.level = random.choice([None, 0, 1, 2, 3, 4])
eligible = []
by_word = {w.word: w for w in real.words}
for s in sents:
    levels = [by_word[t].level for t in s.get("words", []) if t in by_word]
    learning = [lv for lv in levels if lv in F.MIX_WEIGHTS]
    eligible.append(0.0 if not learning else float(sum(F.MIX_WEIGHTS[lv] for lv in learning)) * (1.5 if len(set(learning)) > 1 else 1))
out["sentences"]["levels"] = [w.level for w in real.words]
out["sentences"]["weights_random_levels"] = eligible
# check the Python picker is consistent with these weights: every pick has weight > 0
picks = S.pick_sentences(real, sents, 40)
out["sentences"]["python_pick_all_positive"] = all(eligible[sents.index(p)] > 0 for p in picks)

Path(__file__).resolve().parent.parent.joinpath("tests", "golden.json").write_text(
    json.dumps(out, ensure_ascii=False), encoding="utf-8")
print({k: (len(v) if hasattr(v, "__len__") else v) for k, v in out.items()})
