import copy
import json
import tempfile
import unittest
from pathlib import Path

from newwords import check_and_merge, merge, validate

GOOD = {
    "words": [{"word": "pies", "translation": "dog", "sentence": "Mam psa.", "sentence_translation": "I have a dog."},
              {"word": "biec", "translation": "to run"}],
    "verbs": [{"card": "biec", "verbs": [{"infinitive": "biec", "aspect": "imperfective",
               "forms": ["biegnę", "biegniesz", "biegnie", "biegniemy", "biegniecie", "biegną"],
               "past": ["biegł", "biegła", "biegło", "biegli", "biegły"], "imperative": ["biegnij", "biegnijmy", "biegnijcie"]}]}],
    "nouns": [{"card": "pies", "nouns": [{"lemma": "pies", "gender": "m", "singular": ["pies", "psa", "psu", "psa", "psem", "psie", "psie"],
               "plural": ["psy", "psów", "psom", "psy", "psami", "psach", "psy"]}]}],
    "adjectives": [],
    "examples": {"pies": [{"pl": "Pies śpi.", "en": "The dog sleeps."}]},
    "sentences": [{"pl": "Pies biegnie.", "en": "The dog runs.", "words": ["pies", "biec"]}],
}


class ValidateTests(unittest.TestCase):
    def test_good_answer_passes(self):
        self.assertEqual(validate(GOOD), [])

    def test_each_kind_of_mistake_is_named(self):
        def bad(change):
            data = copy.deepcopy(GOOD)
            change(data)
            return validate(data)
        self.assertTrue(any("6 forms" in e for e in bad(lambda d: d["verbs"][0]["verbs"][0]["forms"].pop())))
        self.assertTrue(any("aspect" in e for e in bad(lambda d: d["verbs"][0]["verbs"][0].update(aspect="x"))))
        self.assertTrue(any("gender" in e for e in bad(lambda d: d["nouns"][0]["nouns"][0].update(gender="x"))))
        self.assertTrue(any("7 cases" in e for e in bad(lambda d: d["nouns"][0]["nouns"][0]["plural"].pop())))
        self.assertTrue(any("not in words" in e for e in bad(lambda d: d["nouns"][0].update(card="kot"))))
        self.assertTrue(any("both" in e for e in bad(lambda d: d["words"][0].pop("sentence_translation"))))
        self.assertTrue(any("missing: kot" in e for e in bad(lambda d: d["sentences"][0]["words"].append("kot"))))
        self.assertTrue(any("Unknown keys" in e for e in bad(lambda d: d.update(extra=1))))
        self.assertTrue(validate([]))

    def test_numerals_may_have_no_plural(self):
        data = {"words": [{"word": "dziesięć", "translation": "ten"}],
                "nouns": [{"card": "dziesięć", "nouns": [{"lemma": "dziesięć", "gender": "num",
                           "singular": ["a"] * 7, "plural": [None] * 7}]}]}
        self.assertEqual(validate(data), [])

    def test_cards_already_in_the_deck_count(self):
        data = {"nouns": GOOD["nouns"]}
        self.assertTrue(validate(data))
        self.assertEqual(validate(data, {"pies"}), [])


class MergeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)

    def test_merge_adds_everything_and_never_touches_existing(self):
        (self.dir / "words.json").write_text(json.dumps([{"word": "pies", "translation": "DOG (mine)"}]))
        added = merge(self.dir, GOOD)
        self.assertEqual((added["words"], added["skipped"], added["verbs"], added["nouns"]), (1, 1, 1, 1))
        words = json.loads((self.dir / "words.json").read_text())
        self.assertEqual([w["word"] for w in words], ["pies", "biec"])
        self.assertEqual(words[0]["translation"], "DOG (mine)")
        self.assertEqual(merge(self.dir, GOOD)["words"], 0)               # running it twice adds nothing
        self.assertEqual(len(json.loads((self.dir / "examples.json").read_text())["pies"]), 1)
        self.assertEqual(len(json.loads((self.dir / "sentences.json").read_text())), 1)

    def test_fenced_answer_and_errors(self):
        errors, added = check_and_merge(self.dir, "```json\n" + json.dumps(GOOD) + "\n```")
        self.assertEqual((errors, added["words"]), ([], 2))
        errors, added = check_and_merge(self.dir, "Sure! Here you go: {")
        self.assertTrue(errors and not added)
        bad = copy.deepcopy(GOOD)
        bad["verbs"][0]["verbs"][0]["forms"] = []
        before = (self.dir / "words.json").read_text()
        errors, added = check_and_merge(self.dir, json.dumps(bad))
        self.assertTrue(errors)
        self.assertEqual((self.dir / "words.json").read_text(), before)    # a bad answer changes nothing


if __name__ == "__main__":
    unittest.main()
