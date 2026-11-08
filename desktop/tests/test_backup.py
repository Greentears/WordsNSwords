import json
import unittest
from datetime import datetime, timezone

from backup import make_backup, merge_progress, parse_import, progress_score
from flashcards import FlashcardDeck, Word


def deck():
    return FlashcardDeck([Word("pies", "dog", "Mój pies.", "My dog.", level=1, fails=2, extra={"tag": "x"}),
                          Word("kot", "cat"), Word("dom", "house", level=3)])


class BackupTests(unittest.TestCase):
    def test_backup_has_the_phone_format(self):
        data = make_backup(deck(), {"version": 2}, datetime(2026, 11, 8, 12, 0, tzinfo=timezone.utc))
        self.assertEqual((data["app"], data["version"]), ("flashcards-web", 1))
        self.assertEqual(data["exportedAt"], "2026-11-08T12:00:00.000Z")
        self.assertEqual(data["words"][0], {"tag": "x", "word": "pies", "translation": "dog", "sentence": "Mój pies.",
                                            "sentence_translation": "My dog.", "level": 1, "fails": 2})
        self.assertEqual(data["words"][1], {"word": "kot", "translation": "cat"})
        self.assertEqual(data["dungeon"], {"version": 2})
        self.assertNotIn("dungeon", make_backup(deck()))

    def test_round_trip_through_parse(self):
        cards, dungeon = parse_import(json.dumps(make_backup(deck(), {"player": {}})))
        self.assertEqual([c["word"] for c in cards], ["pies", "kot", "dom"])
        self.assertEqual(dungeon, {"player": {}})

    def test_plain_word_list_and_errors(self):
        self.assertEqual(parse_import('[{"word": "a", "translation": "b"}]')[1], None)
        for bad in ("nope", '{"app": "other"}', "[]", '[{"translation": "x"}]'):
            with self.assertRaises(ValueError):
                parse_import(bad)

    def test_higher_keeps_the_most_advanced_card_and_skips_unknown_ones(self):
        d = deck()
        r = merge_progress(d, [{"word": "pies", "level": 0}, {"word": "kot", "level": 2, "fails": 1},
                               {"word": "dom", "level": 3}, {"word": "nowy", "level": 1}])
        self.assertEqual(r, {"updated": 1, "unchanged": 2, "skipped": 1})
        self.assertEqual([(w.level, w.fails) for w in d.words], [(1, 2), (2, 1), (3, 0)])

    def test_replace_lets_the_backup_win(self):
        d = deck()
        merge_progress(d, [{"word": "pies", "level": 0}, {"word": "dom"}], "replace")
        self.assertEqual([(w.level, w.fails) for w in d.words], [(0, 0), (None, 0), (None, 0)][:1] + [(None, 0), (None, 0)])

    def test_score_order(self):
        self.assertLess(progress_score(None, 5), progress_score(0, 0))
        self.assertLess(progress_score(2, 999), progress_score(3, 0))


if __name__ == "__main__":
    unittest.main()
