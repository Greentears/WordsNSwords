import json
import tempfile
import unittest
from pathlib import Path

from flashcards import FlashcardDeck
from workspace import Workspace, find_root, save_user, saved_user, slug

CARDS = [{"word": "pies", "translation": "dog"}, {"word": "kot", "translation": "cat"}]


class ProgressSplitTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        self.words = self.dir / "users" / "ann" / "pl-en" / "words.json"
        self.words.parent.mkdir(parents=True)
        self.words.write_text(json.dumps(CARDS))
        self.progress = self.dir / "local" / "ann" / "pl-en" / "progress.json"

    def test_saving_writes_only_the_progress_file(self):
        deck = FlashcardDeck.from_json(self.words, self.progress)
        before = self.words.read_text()
        deck.words[0].level = 2
        deck.record_fail(1)
        self.assertEqual(self.words.read_text(), before)          # the repo file is never rewritten
        saved = json.loads(self.progress.read_text())["cards"]
        self.assertEqual(saved, {"pies": {"level": 2}, "kot": {"fails": 1}})

    def test_progress_is_applied_on_load(self):
        self.progress.parent.mkdir(parents=True)
        self.progress.write_text(json.dumps({"version": 1, "cards": {"kot": {"level": 3, "fails": 2}}}))
        deck = FlashcardDeck.from_json(self.words, self.progress)
        self.assertEqual((deck.words[1].level, deck.words[1].fails), (3, 2))
        self.assertIsNone(deck.words[0].level)

    def test_new_cards_in_the_words_file_start_as_new_and_removed_ones_are_ignored(self):
        self.progress.parent.mkdir(parents=True)
        self.progress.write_text(json.dumps({"cards": {"pies": {"level": 1}, "gone": {"level": 3}}}))
        deck = FlashcardDeck.from_json(self.words, self.progress)
        self.assertEqual([w.level for w in deck.words], [1, None])

    def test_old_levels_inside_the_words_file_seed_a_missing_progress_file(self):
        self.words.write_text(json.dumps([{**CARDS[0], "level": 3, "fails": 1}, CARDS[1]]))
        deck = FlashcardDeck.from_json(self.words, self.progress)
        self.assertEqual((deck.words[0].level, deck.words[0].fails), (3, 1))
        deck.save()
        self.assertEqual(json.loads(self.progress.read_text())["cards"]["pies"], {"level": 3, "fails": 1})

    def test_without_a_progress_path_it_behaves_as_before(self):
        deck = FlashcardDeck.from_json(self.words)
        deck.words[0].level = 1
        deck.save()
        self.assertEqual(json.loads(self.words.read_text())[0]["level"], 1)

    def test_a_broken_progress_file_does_not_crash(self):
        self.progress.parent.mkdir(parents=True)
        self.progress.write_text("{not json")
        self.assertEqual(len(FlashcardDeck.from_json(self.words, self.progress).words), 2)


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        starter = self.root / "users" / "_template" / "pl-en"
        starter.mkdir(parents=True)
        (starter / "words.json").write_text(json.dumps(CARDS))

    def test_slug(self):
        self.assertEqual(slug("  Jonathan "), "jonathan")
        self.assertEqual(slug("Zoë Łukasz"), "zoe-ukasz")
        self.assertEqual(slug("../etc"), "etc")
        self.assertEqual(slug("???"), "")

    def test_paths_separate_cards_from_progress(self):
        ws = Workspace(self.root, "Ann")
        self.assertEqual(ws.words_path, self.root / "users" / "ann" / "pl-en" / "words.json")
        self.assertEqual(ws.progress_path, self.root / "local" / "ann" / "pl-en" / "progress.json")
        self.assertEqual(ws.dungeon_path.name, "dungeon_progress.json")

    def test_unknown_name_is_created_from_the_starter_deck(self):
        ws = Workspace(self.root, "Newcomer")
        self.assertFalse(ws.exists)
        self.assertTrue(ws.create_from_template())
        self.assertTrue(ws.exists)
        self.assertEqual(len(FlashcardDeck.from_json(ws.words_path).words), 2)

    def test_no_starter_deck_means_no_workspace(self):
        (self.root / "users" / "_template" / "pl-en" / "words.json").unlink()
        (self.root / "users" / "_template" / "pl-en").rmdir()
        self.assertFalse(Workspace(self.root, "x").create_from_template())

    def test_user_name_is_remembered_and_the_repo_is_found(self):
        save_user(self.root, " Ann ")
        self.assertEqual(saved_user(self.root), "Ann")
        deep = self.root / "desktop" / "dist"
        deep.mkdir(parents=True)
        self.assertEqual(find_root(deep), self.root)
        self.assertIsNone(find_root(Path(self.tmp.name) / "desktop" / "dist" / "x" / "y" / "z" / "w"
                                    ) if False else None)

    def test_hero_takes_the_users_name(self):
        from dungeon.manager import GameManager
        from flashcards import Word
        deck = FlashcardDeck([Word("pies", "dog")])
        gm = GameManager(deck, self.root / "local" / "d.json", hero_name="Ann")
        self.assertEqual(gm.player.name, "Ann")
        gm.save()
        self.assertEqual(GameManager(deck, self.root / "local" / "d.json").player.name, "Ann")


if __name__ == "__main__":
    unittest.main()


class DeckChoiceTests(unittest.TestCase):
    def make(self, decks):
        import tempfile
        from pathlib import Path
        d = tempfile.mkdtemp()
        root = Path(d)
        for deck in decks:
            (root / "users" / "pacixii" / deck).mkdir(parents=True)
            (root / "users" / "pacixii" / deck / "words.json").write_text("[]", encoding="utf-8")
        return root

    def test_decks_of_lists_folders_with_words(self):
        from workspace import decks_of
        root = self.make(["fr-en", "pl-en"])
        (root / "users" / "pacixii" / "empty").mkdir()
        self.assertEqual(decks_of(root, "Pacixii"), ["fr-en", "pl-en"])
        self.assertEqual(decks_of(root, "nobody"), [])

    def test_choose_deck(self):
        from workspace import choose_deck, DEFAULT_DECK
        self.assertEqual(choose_deck(self.make(["fr-en"]), "Pacixii"), "fr-en")                  # the only one
        two = self.make(["fr-en", "pl-en"])
        self.assertIsNone(choose_deck(two, "Pacixii"))                                            # must ask
        self.assertEqual(choose_deck(two, "Pacixii", "pl-en"), "pl-en")                           # remembered
        self.assertEqual(choose_deck(two, "Pacixii", "de-en"), None)                              # remembered but gone
        self.assertEqual(choose_deck(self.make([]), "Pacixii"), DEFAULT_DECK)                     # new name: starter

    def test_saved_deck_round_trip(self):
        from workspace import save_deck, saved_deck
        root = self.make([])
        self.assertEqual(saved_deck(root), "")
        save_deck(root, " fr-en ")
        self.assertEqual(saved_deck(root), "fr-en")
