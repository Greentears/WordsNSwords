import json
import unittest
from pathlib import Path

import french
import newwords
from flashcards import Word, blank_sentence

ROOT = Path(__file__).resolve().parent.parent.parent
PACIXII = ROOT / "users" / "pacixii" / "fr-en"
TENSES = {t: [f"{p} x" for p in ("je", "tu", "il/elle", "nous", "vous", "ils/elles")] for t in french.TENSES}
GOOD = {
    "words": [{"word": "manger", "translation": "to eat"}, {"word": "maison", "translation": "house"}, {"word": "grand", "translation": "big"}],
    "verbs": [{"card": "manger", "verbs": [{"infinitive": "manger", "tenses": TENSES}]}],
    "nouns": [{"card": "maison", "nouns": [{"lemma": "maison", "gender": "f", "singular": "la maison", "plural": "les maisons"}]}],
    "adjectives": [{"card": "grand", "adjectives": [{"lemma": "grand", "forms": {"ms": "grand", "fs": "grande", "mp": "grands", "fp": "grandes"}}]}],
}


class FrenchValidationTests(unittest.TestCase):
    def test_good_answer(self):
        self.assertEqual(newwords.validate(GOOD, set(), "fr"), [])

    def test_the_polish_format_is_refused_for_french(self):
        polish = {"words": [{"word": "a", "translation": "b"}],
                  "verbs": [{"card": "a", "verbs": [{"infinitive": "a", "aspect": "imperfective", "forms": list("123456")}]}]}
        errors = newwords.validate(polish, set(), "fr")
        self.assertTrue(any('needs "tenses"' in e for e in errors), errors)
        self.assertEqual(newwords.validate(polish, set(), "pl"), [])

    def test_each_problem_is_named(self):
        bad = json.loads(json.dumps(GOOD))
        bad["verbs"][0]["verbs"][0]["tenses"]["futur"] = ["a"]
        del bad["verbs"][0]["verbs"][0]["tenses"]["imparfait"]
        bad["nouns"][0]["nouns"][0]["gender"] = "n"
        bad["adjectives"][0]["adjectives"][0]["forms"].pop("fp")
        errors = newwords.validate(bad, set(), "fr")
        self.assertEqual(len(errors), 4, errors)
        self.assertTrue(any("tenses.futur" in e for e in errors))
        self.assertTrue(any("tenses.imparfait" in e for e in errors))

    def test_noun_plural_may_be_null(self):
        data = json.loads(json.dumps(GOOD))
        data["nouns"][0]["nouns"][0]["plural"] = None
        self.assertEqual(newwords.validate(data, set(), "fr"), [])

    def test_language_of(self):
        self.assertEqual(newwords.language_of("fr-en"), "fr")
        self.assertEqual(newwords.language_of("pl-en"), "pl")
        self.assertEqual(newwords.language_of("d"), "pl")


class FrenchFormsTests(unittest.TestCase):
    def test_expand_optional(self):
        self.assertEqual(french.expand_optional("aperçu"), ["aperçu"])
        self.assertEqual(french.expand_optional("aperçu(e)"), ["aperçu", "aperçue"])
        self.assertEqual(french.expand_optional("aperçu(e)(s)"), ["aperçu", "aperçus", "aperçue", "aperçues"])

    def test_cloze_forms_drop_pronouns(self):
        self.assertEqual(french.cloze_forms(["il/elle s'est aperçu(e)"]), ["est aperçu", "est aperçue"])
        self.assertEqual(french.cloze_forms(["j'ai négligé", "nous nous méfions", "je me méfie"]),
                         ["ai négligé", "méfions", "méfie"])

    def test_blank_finds_a_conjugated_form_in_a_sentence(self):
        data = {k: json.loads((PACIXII / f"{k}.json").read_text(encoding="utf-8")) for k in ("verbs", "nouns", "adjectives")}
        forms = french.known_forms(*(french.load_verbs(PACIXII / "verbs.json"), french.load_nouns(PACIXII / "nouns.json"),
                                    french.load_adjectives(PACIXII / "adjectives.json")))
        word = Word(word="négliger", translation="to neglect", sentence="Il a négligé ses études pendant des années.")
        blanked = blank_sentence(word, forms["négliger"])
        self.assertIsNotNone(blanked)
        self.assertIn("_____", blanked[0])
        word2 = Word(word="se méfier", translation="to be wary", sentence="Nous nous méfions de cette offre.")
        self.assertIsNotNone(blank_sentence(word2, forms["se méfier"]))


class PacixiiDataTests(unittest.TestCase):
    def test_all_tables_are_valid_french(self):
        data = {k: json.loads((PACIXII / f"{k}.json").read_text(encoding="utf-8")) for k in ("words", "verbs", "nouns", "adjectives", "examples", "sentences")}
        self.assertEqual(newwords.validate(data, set(), "fr"), [])

    def test_loaders_and_html(self):
        verbs = french.load_verbs(PACIXII / "verbs.json")
        self.assertEqual(len(verbs), 7)
        html = french.verb_html(verbs["se méfier"], "#888")
        for text in ("Passé composé", "Futur simple", "je me suis méfié(e)", "ils/elles se méfieraient"):
            self.assertIn(text, html)
        self.assertIn("les enjeux", french.noun_html(french.load_nouns(PACIXII / "nouns.json")["enjeu"], "#888"))
        self.assertIn("masculine", french.noun_html(french.load_nouns(PACIXII / "nouns.json")["enjeu"], "#888"))
        self.assertIn("approfondies", french.adjective_html(french.load_adjectives(PACIXII / "adjectives.json")["approfondi"], "#888"))

    def test_every_verb_has_six_forms_in_five_tenses(self):
        for entries in french.load_verbs(PACIXII / "verbs.json").values():
            for v in entries:
                for t in french.TENSES:
                    self.assertEqual(len(v["tenses"][t]), 6, (v["infinitive"], t))

    def test_missing_files_mean_no_tables(self):
        self.assertEqual(french.load_verbs(PACIXII / "nope.json"), {})


if __name__ == "__main__":
    unittest.main()
