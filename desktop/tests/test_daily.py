import json
import random
import tempfile
import unittest
from pathlib import Path

from dungeon import daily
from dungeon.battle import ACTIVE
from dungeon.manager import GameManager
from flashcards import FlashcardDeck, Word


def deck():
    return FlashcardDeck([Word(f"p{i}", f"en{i}", level=1) for i in range(12)])


class RngTests(unittest.TestCase):
    def test_same_date_same_challenge(self):
        a, b = daily.build("2026-11-11", 12), daily.build("2026-11-11", 12)
        self.assertEqual([(r.title, r.spec) for r in a.rooms], [(r.title, r.spec) for r in b.rooms])
        other = daily.build("2026-11-12", 12)
        self.assertNotEqual([r.title for r in a.rooms], [r.title for r in other.rooms])

    def test_shape_and_scaling(self):
        d = daily.build("2026-11-11", 12)
        self.assertEqual([r.kind for r in d.rooms], ["monster", "monster", "rest", "monster", "monster", "boss"])
        low, high = daily.build("2026-11-11", 4), daily.build("2026-11-11", 40)
        self.assertGreater(high.rooms[-1].spec.max_hp, low.rooms[-1].spec.max_hp)

    def test_streak_bonus(self):
        self.assertEqual([daily.streak_bonus(n) for n in (0, 1, 2, 3, 6, 20)], [0, 0, 0.1, 0.2, 0.5, 0.5])
        self.assertEqual(daily.yesterday("2026-03-01"), "2026-02-28")


class DailyRunTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "dungeon_progress.json"
        self.day = "2026-11-11"

    def tearDown(self):
        self.tmp.cleanup()

    def gm(self):
        self.path.write_text(json.dumps({"player": {"level": 12, "max_hp": 2000, "hp": 2000}})
                             if not self.path.exists() else self.path.read_text(), encoding="utf-8")
        return GameManager(deck(), self.path, random.Random(1), today=lambda: self.day)

    def run_day(self, gm):
        gm.select_dungeon("daily")
        last = None
        while gm.current_room() is not None:
            last = gm.enter_room()
            if gm.battle is not None:
                while gm.battle.state == ACTIVE:
                    gm.answer(gm.next_question().answer)
                last = gm.outcome
            gm.player.hp = gm.player.max_hp
        return last

    def status(self, gm):
        return next(s for s in gm.dungeons() if s.key == "daily")

    def test_one_run_a_day_then_locked(self):
        gm = self.gm()
        out = self.run_day(gm)
        self.assertTrue(out.dungeon_completed)
        st = self.status(gm)
        self.assertEqual(st.unavailable, "Done today. Come back tomorrow!")
        with self.assertRaises(ValueError):
            gm.select_dungeon("daily")

    def test_new_day_opens_again_and_streak_grows(self):
        gm = self.gm()
        first = self.run_day(gm)
        self.assertIn("Daily streak: 1 day", first.messages[-1])
        self.day = "2026-11-12"
        gm = self.gm()
        self.assertIsNone(self.status(gm).unavailable)
        second = self.run_day(gm)
        self.assertIn("Daily streak: 2 days (+10% reward)", second.messages[-1])
        self.assertEqual(gm.daily_streak(), 2)

    def test_a_missed_day_breaks_the_streak(self):
        gm = self.gm()
        self.run_day(gm)
        self.day = "2026-11-14"
        gm = self.gm()
        self.assertEqual(gm.daily_streak(), 0)
        self.assertIn("Daily streak: 1 day", self.run_day(gm).messages[-1])

    def test_progress_resets_each_day_and_is_saved(self):
        gm = self.gm()
        gm.select_dungeon("daily")
        gm.enter_room()
        while gm.battle.state == ACTIVE:
            gm.answer(gm.next_question().answer)
        self.assertEqual(gm.progress["daily"]["room"], 1)
        gm = self.gm()                                  # same day: continues
        self.assertEqual(gm.progress["daily"]["room"], 1)
        self.day = "2026-11-12"                         # next day: starts over
        gm = self.gm()
        self.assertEqual(gm.progress["daily"]["room"], 0)

    def test_tier_is_fixed_once_started(self):
        gm = self.gm()
        gm.select_dungeon("daily")
        tier = gm.progress["daily"]["tier"]
        gm.enter_room()
        while gm.battle.state == ACTIVE:
            gm.answer(gm.next_question().answer)
        gm.player.level += 5
        gm.dungeons()
        self.assertEqual(gm.progress["daily"]["tier"], tier)

    def test_low_level_cannot_enter(self):
        self.path.write_text(json.dumps({"player": {"level": 1}}), encoding="utf-8")
        gm = GameManager(deck(), self.path, random.Random(1), today=lambda: self.day)
        self.assertEqual(self.status(gm).unavailable, f"Requires level {daily.MIN_LEVEL}")


if __name__ == "__main__":
    unittest.main()
