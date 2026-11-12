import random
import unittest
from pathlib import Path

import adjectives
import french
import grammar
import nouns
import verbs

USERS = Path(__file__).resolve().parents[2] / "users"


def pool(language):
    d = USERS / ("_template/fr-en" if language == "fr" else "_template/pl-en")
    if language == "fr":
        return grammar.build_pool("fr", french.load_verbs(d / "verbs.json"), french.load_nouns(d / "nouns.json"),
                                  french.load_adjectives(d / "adjectives.json"))
    return grammar.build_pool("pl", verbs.load_conjugations(d / "verbs.json"), nouns.load_declensions(d / "nouns.json"),
                              adjectives.load_adjectives(d / "adjectives.json"))


class GrammarTests(unittest.TestCase):
    def test_both_languages_make_questions_in_every_category(self):
        for lang in ("pl", "fr"):
            p = pool(lang)
            for cat in grammar.CATEGORIES:
                self.assertTrue(p[cat], f"{lang} {cat}")

    def test_every_question_accepts_its_own_answers(self):
        for lang in ("pl", "fr"):
            for qs in pool(lang).values():
                for q in qs:
                    self.assertIn("___", q.stem)
                    for a in q.answers:
                        self.assertEqual(grammar.check(q, a, lang), "correct", (q, a))

    def test_polish_checks(self):
        q = grammar.Question("verbs", "bać się", "ja ___", "bać się · present", "", ("boję się", "boję"))
        self.assertEqual(grammar.check(q, "  Boję się ", "pl"), "correct")
        self.assertEqual(grammar.check(q, "boje sie", "pl"), "accents")
        self.assertEqual(grammar.check(q, "boisz się", "pl"), "wrong")
        self.assertEqual(grammar.check(q, "", "pl"), "wrong")

    def test_reflexive_se_may_be_left_out(self):
        q = next(x for x in pool("pl")["verbs"] if "się" in x.stem + x.label)
        self.assertTrue(any(" " not in a for a in q.answers))

    def test_french_checks_ignore_the_subject_and_read_optional_letters(self):
        q = grammar.Question("verbs", "x", "il/elle ___", "t", "", ("est aperçu", "est aperçue"))
        self.assertEqual(grammar.check(q, "il/elle est aperçue", "fr"), "correct")
        self.assertEqual(grammar.check(q, "est apercu", "fr"), "accents")
        self.assertEqual(grammar.check(q, "a aperçu", "fr"), "wrong")
        plural = next(x for x in pool("fr")["nouns"] if x.card == "enjeu")
        self.assertEqual(grammar.check(plural, "les enjeux", "fr"), "correct")
        self.assertEqual(grammar.check(plural, "enjeux", "fr"), "correct")

    def test_pick_is_varied_and_without_repeats(self):
        p = pool("pl")
        got = grammar.pick(p, grammar.CATEGORIES, 12, random.Random(3))
        self.assertEqual(len(got), 12)
        self.assertEqual(len(set(got)), 12)
        self.assertGreater(len({q.category for q in got}), 1)
        only = grammar.pick(p, ["nouns"], 5, random.Random(3))
        self.assertTrue(all(q.category == "nouns" for q in only))
        self.assertEqual(len(grammar.pick(p, ["nouns"], 10**6, random.Random(1))), len(p["nouns"]))


if __name__ == "__main__":
    unittest.main()
