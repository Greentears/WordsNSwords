"""Make web/tests/french_golden.json: what desktop/french.py does with some forms (the TypeScript port must agree)."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "desktop"))
import french  # noqa: E402

SAMPLES = ["aperçu", "aperçu(e)", "aperçu(e)(s)", "il/elle s'est aperçu(e)", "j'ai négligé", "je m'aperçois", "nous nous méfions",
           "vous vous êtes méfié(e)(s)", "ils/elles se sont aperçu(e)s", "tu t'es aperçu(e)", "je parviens à", "Il/elle remet en question",
           "je suis parvenu(e) à", "", "nous nous sommes méfié(e)s", "ils/elles s'apercevaient"]
pv = ROOT / "users" / "pacixii" / "fr-en"
verbs, nouns, adjs = (french.load_verbs(pv / "verbs.json"), french.load_nouns(pv / "nouns.json"), french.load_adjectives(pv / "adjectives.json"))
golden = {
    "expand": {s: french.expand_optional(s) for s in SAMPLES if s},
    "cloze": {s: french.cloze_forms([s]) for s in SAMPLES},
    "known": french.known_forms(verbs, nouns, adjs),
}
(ROOT / "web" / "tests" / "french_golden.json").write_text(json.dumps(golden, ensure_ascii=False), encoding="utf-8")
print(len(golden["known"]), "cards")
