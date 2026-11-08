import tempfile
import unittest
from pathlib import Path

import addwords

ROOT = Path(__file__).resolve().parent.parent.parent


class AddWordsTests(unittest.TestCase):
    def test_word_lines_accepts_bullets_numbers_and_blank_lines(self):
        self.assertEqual(addwords.word_lines("1. kot\n- pić\n\n  * zielony \n2) a b"), "- kot\n- pić\n- zielony\n- a b")

    def test_prompt_has_words_inserted_for_each_language(self):
        for deck in ("pl-en", "fr-en"):
            text = addwords.build_prompt(ROOT, deck, "kot\npić")
            self.assertTrue(text.rstrip().endswith("- kot\n- pić"), deck)
            self.assertNotIn("{WORDS}", text)

    def test_empty_list_is_refused(self):
        with self.assertRaises(ValueError):
            addwords.build_prompt(ROOT, "pl-en", " \n ")

    def test_missing_prompt_raises_oserror(self):
        with tempfile.TemporaryDirectory() as d, self.assertRaises(OSError):
            addwords.build_prompt(Path(d), "pl-en", "kot")

    def test_readme_prompts_match_the_prompt_files(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("sync", ROOT / "tools" / "sync_readme_prompts.py")
        mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
        self.assertTrue(mod.sync(check=True), "run: python tools/sync_readme_prompts.py")

    def test_summary_and_problem_message(self):
        self.assertEqual(addwords.summary({"words": 2, "skipped": 1, "verbs": 0}), "Added: 2 new words, 1 already there.")
        self.assertIn("- a", addwords.problems_message(["a", "b"]))


if __name__ == "__main__":
    unittest.main()
