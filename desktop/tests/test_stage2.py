import copy
import random
import unittest
from collections import Counter

from dungeon import config
from dungeon.battle import ACTIVE, DEFEAT, VICTORY, Battle
from dungeon.models import Monster, Player
from dungeon.selector import MissedWords, VocabularySelector
from flashcards import ARCHIVED, FlashcardDeck, Word


def make_deck(n_each: int = 3) -> FlashcardDeck:
    words = []
    for level in (None, 0, 1, 2, 3, ARCHIVED):
        for i in range(n_each):
            words.append(Word(f"pl{level}_{i}", f"to en{level}_{i}", sentence=f"Zdanie {level}{i}.",
                              level=level, fails=i))
    return FlashcardDeck(words)


def snapshot(deck):
    return [(w.word, w.translation, w.level, w.fails) for w in deck.words]


def new_battle(deck=None, monster="book_mimic", seed=1, player=None):
    deck = deck or make_deck()
    rng = random.Random(seed)
    sel = VocabularySelector(deck, rng=rng)
    return Battle(player or Player(), Monster.spawn(config.MONSTERS[monster]), sel, rng)


class MissedWordsTests(unittest.TestCase):
    def test_clears_after_streak(self):
        m = MissedWords()
        m.miss("a")
        self.assertEqual(len(m), 1)
        self.assertFalse(m.correct("a"))
        self.assertTrue(m.correct("a"))
        self.assertEqual(len(m), 0)

    def test_miss_resets_streak(self):
        m = MissedWords()
        m.miss("a")
        m.correct("a")
        m.miss("a")
        self.assertFalse(m.correct("a"))
        self.assertIn("a", m)

    def test_correct_on_unknown_word_noop(self):
        m = MissedWords()
        self.assertFalse(m.correct("zzz"))
        self.assertEqual(len(m), 0)

    def test_round_trip_and_bad_data(self):
        m = MissedWords({"a": 1, "b": 0, 5: 1, "c": "x", "d": True})
        self.assertEqual(m.words(), ["a", "b"])
        self.assertEqual(MissedWords(m.to_dict()).to_dict(), m.to_dict())
        self.assertEqual(len(MissedWords("junk")), 0)


class SelectorTests(unittest.TestCase):
    def test_never_picks_archived(self):
        deck = make_deck()
        sel = VocabularySelector(deck, rng=random.Random(0))
        for _ in range(300):
            self.assertNotEqual(deck.words[sel.pick()].level, ARCHIVED)

    def test_new_cards_can_be_switched_off(self):
        deck = make_deck()
        sel = VocabularySelector(deck, rng=random.Random(0), weights={**config.LEVEL_WEIGHTS, None: 0})
        for _ in range(200):
            self.assertIsNotNone(deck.words[sel.pick()].level)

    def test_learning_words_come_up_more_than_known(self):
        deck = make_deck(n_each=1)
        counts = Counter()
        for seed in range(2000):
            sel = VocabularySelector(deck, rng=random.Random(seed))
            counts[deck.words[sel.pick()].level] += 1
        self.assertGreater(counts[1], counts[3] * 2)

    def test_missed_words_weighted_higher(self):
        deck = make_deck(n_each=1)
        target = next(w.word for w in deck.words if w.level == 3)
        plain = hit = 0
        for seed in range(3000):
            if deck.words[VocabularySelector(deck, rng=random.Random(seed)).pick()].word == target:
                plain += 1
            sel = VocabularySelector(deck, MissedWords({target: 0}), random.Random(seed))
            if deck.words[sel.pick()].word == target:
                hit += 1
        self.assertGreater(hit, plain * 1.5)

    def test_recent_words_not_repeated_while_others_exist(self):
        deck = make_deck(n_each=3)  # 15 usable cards, window 10
        sel = VocabularySelector(deck, rng=random.Random(4))
        picks = [sel.pick() for _ in range(config.RECENT_WINDOW)]
        self.assertEqual(len(set(picks)), len(picks))

    def test_tiny_deck_avoids_immediate_repeat(self):
        deck = FlashcardDeck([Word("a", "x", level=1), Word("b", "y", level=1)])
        sel = VocabularySelector(deck, rng=random.Random(2))
        picks = [sel.pick() for _ in range(20)]
        self.assertTrue(all(a != b for a, b in zip(picks, picks[1:])))

    def test_single_card_deck_still_works(self):
        sel = VocabularySelector(FlashcardDeck([Word("a", "x", level=1)]))
        self.assertEqual([sel.pick(), sel.pick()], [0, 0])

    def test_empty_or_all_archived_returns_none(self):
        self.assertIsNone(VocabularySelector(FlashcardDeck([])).pick())
        self.assertIsNone(VocabularySelector(FlashcardDeck([Word("a", "x", level=ARCHIVED)])).pick())

    def test_cards_without_translation_skipped(self):
        deck = FlashcardDeck([Word("a", "", level=1), Word("b", "y", level=1)])
        sel = VocabularySelector(deck)
        self.assertEqual({sel.pick() for _ in range(10)}, {1})


class BattleTests(unittest.TestCase):
    def test_correct_answer_damages_monster(self):
        b = new_battle()
        q = b.next_question()
        r = b.submit(q.answer)
        self.assertTrue(r.correct)
        self.assertGreater(r.damage_dealt, 0)
        self.assertEqual(r.damage_taken, 0)
        self.assertEqual(b.monster.hp, b.monster.max_hp - r.damage_dealt)
        self.assertEqual(b.player.hp, b.player.max_hp)
        self.assertIn("Correct!", r.message)

    def test_wrong_answer_damages_player(self):
        b = new_battle()
        b.next_question()
        r = b.submit("definitely wrong")
        self.assertFalse(r.correct)
        self.assertGreater(r.damage_taken, 0)
        self.assertEqual(b.monster.hp, b.monster.max_hp)
        self.assertIn("Incorrect!", r.message)
        self.assertIn(r.expected, r.message)

    def test_empty_answer_is_wrong(self):
        b = new_battle()
        b.next_question()
        self.assertFalse(b.submit("   ").correct)

    def test_accent_and_to_prefix_accepted(self):
        deck = FlashcardDeck([Word("a", "to run away", level=1)])
        b = new_battle(deck)
        b.next_question()
        self.assertTrue(b.submit("Run Away").correct)
        deck = FlashcardDeck([Word("żółw", "łódź", level=1)])
        b = new_battle(deck)
        b.next_question()
        r = b.submit("lodz")
        self.assertTrue(r.correct)
        self.assertFalse(r.exact)

    def test_alternatives_accepted(self):
        deck = FlashcardDeck([Word("a", "important / significant", level=1)])
        b = new_battle(deck)
        b.next_question()
        self.assertTrue(b.submit("significant").correct)

    def test_victory(self):
        b = new_battle()
        r = None
        for _ in range(20):
            q = b.next_question()
            if q is None:
                break
            r = b.submit(q.answer)
        self.assertEqual(b.state, VICTORY)
        self.assertEqual(r.state, VICTORY)
        self.assertEqual(b.monster.hp, 0)
        self.assertIn("defeated", r.message)
        self.assertIsNone(b.next_question())

    def test_defeat_and_hp_never_negative(self):
        b = new_battle(monster="dust_moth", player=Player(hp=5, max_hp=30))
        for _ in range(10):
            if b.next_question() is None:
                break
            b.submit("nope")
        self.assertEqual(b.state, DEFEAT)
        self.assertEqual(b.player.hp, 0)
        self.assertEqual(b.monster.hp, b.monster.max_hp)

    def test_monster_hit_is_capped(self):
        b = new_battle(monster="dust_moth", player=Player())
        cap = int(b.player.max_hp * config.MAX_HIT_FRACTION)
        for seed in range(50):
            b = new_battle(monster="dust_moth", seed=seed)
            b.next_question()
            self.assertLessEqual(b.submit("x").damage_taken, cap)

    def test_skip_counts_as_wrong_with_half_damage_and_reveals(self):
        full, half = [], []
        for seed in range(40):
            b = new_battle(monster="quill_stalker", seed=seed)
            b.next_question()
            r = b.skip()
            half.append(r.damage_taken)
            self.assertTrue(r.skipped)
            self.assertFalse(r.correct)
            self.assertEqual(r.damage_dealt, 0)
            self.assertIn(r.expected, r.message)
            b = new_battle(monster="quill_stalker", seed=seed)
            b.next_question()
            full.append(b.submit("x").damage_taken)
        self.assertLess(sum(half), sum(full))

    def test_missed_word_tracked_and_cleared(self):
        deck = FlashcardDeck([Word("a", "x", level=1)])
        b = new_battle(deck, monster="dust_moth")
        b.next_question()
        b.submit("wrong")
        self.assertEqual(len(b.missed), 1)
        b.next_question()
        b.submit("x")
        b.next_question()
        r = b.submit("x")
        self.assertTrue(r.cleared_from_missed)
        self.assertEqual(len(b.missed), 0)

    def test_skip_adds_to_missed(self):
        b = new_battle()
        b.next_question()
        b.skip()
        self.assertEqual(len(b.missed), 1)

    def test_no_question_raises(self):
        b = new_battle()
        with self.assertRaises(RuntimeError):
            b.submit("x")
        b.next_question()
        b.submit("x")
        with self.assertRaises(RuntimeError):
            b.submit("x")  # answered already, no new question

    def test_empty_deck_gives_no_question(self):
        self.assertIsNone(new_battle(FlashcardDeck([])).next_question())

    def test_battle_never_changes_the_deck(self):
        deck = make_deck()
        before = copy.deepcopy(snapshot(deck))
        b = new_battle(deck, monster="dust_moth", seed=9)
        for i in range(40):
            q = b.next_question()
            if q is None:
                break
            (b.submit(q.answer) if i % 3 else b.skip() if i % 2 else b.submit("zzz"))
            if b.state != ACTIVE:
                break
        self.assertEqual(snapshot(deck), before)

    def test_player_level_raises_damage(self):
        low = new_battle(player=Player(level=1)).player.attack_power
        high = new_battle(player=Player(level=5)).player.attack_power
        self.assertGreater(high, low)


if __name__ == "__main__":
    unittest.main()
