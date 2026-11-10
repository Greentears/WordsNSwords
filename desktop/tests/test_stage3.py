import json
import random
import tempfile
import unittest
from pathlib import Path

from dungeon import config
from dungeon.battle import ACTIVE, DEFEAT, VICTORY
from dungeon.dungeons import DUNGEONS
from dungeon.manager import GameManager, save_path_for
from dungeon.models import BOSS, MONSTER, REST, TREASURE
from flashcards import FlashcardDeck, Word

KEY = "cellar"


def make_deck():
    return FlashcardDeck([Word(f"p{i}", f"en{i}", sentence=f"Zdanie {i}.", level=i % 4, fails=i)
                          for i in range(20)])


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "dungeon_progress.json"
        self.deck = make_deck()

    def tearDown(self):
        self.tmp.cleanup()

    def manager(self, seed=1):
        return GameManager(self.deck, self.path, random.Random(seed))

    def win_fight(self, gm):
        """Answer correctly until the current fight is won."""
        for _ in range(100):
            q = gm.next_question()
            if q is None:
                break
            gm.answer(q.answer)
        self.assertEqual(gm.battle.state, VICTORY)
        return gm.outcome

    def play_room(self, gm):
        room = gm.current_room()
        if room.is_fight:
            self.assertIsNone(gm.enter_room())
            return self.win_fight(gm)
        return gm.enter_room()


class DungeonDataTests(unittest.TestCase):
    def test_cellar_layout(self):
        rooms = DUNGEONS[KEY].rooms
        self.assertEqual(len(rooms), 8)
        self.assertEqual(rooms[-1].kind, BOSS)
        self.assertEqual(sum(r.kind == BOSS for r in rooms), 1)
        kinds = {r.kind for r in rooms}
        self.assertTrue({MONSTER, TREASURE, REST, BOSS} <= kinds)

    def test_all_monster_keys_exist(self):
        for d in DUNGEONS.values():
            for r in d.rooms:
                if r.is_fight:
                    self.assertIn(r.monster, config.MONSTERS)
                    self.assertEqual(config.MONSTERS[r.monster].boss, r.kind == BOSS)


class ProgressionTests(Base):
    def test_fresh_game(self):
        gm = self.manager()
        st = gm.dungeons()[0]
        self.assertEqual((st.room, st.completed, st.in_progress), (0, False, False))
        self.assertEqual(gm.player.name, "Adventurer")

    def test_win_fight_gives_rewards_and_advances(self):
        gm = self.manager()
        gm.select_dungeon(KEY)
        gm.enter_room()
        out = self.win_fight(gm)
        spec = config.MONSTERS["book_mimic"]
        self.assertEqual(out.reward.xp, spec.xp)
        self.assertEqual(out.reward.coins, spec.coins + config.ROOM_CLEAR_COINS)
        self.assertEqual(gm.player.coins, out.reward.coins)
        self.assertEqual(gm.room_index, 1)
        self.assertEqual(gm.stats["monsters_defeated"], 1)
        self.assertEqual(gm.stats["rooms_cleared"], 1)
        self.assertFalse(out.dungeon_completed)

    def test_level_up_through_fights(self):
        gm = self.manager()
        gm.select_dungeon(KEY)
        for _ in range(8):            # levels are slow on purpose: 150 XP for the first one
            self.play_room(gm)
        self.assertGreaterEqual(gm.player.level, 2)

    def test_rest_room_heals_half(self):
        gm = self.manager()
        gm.select_dungeon(KEY)
        gm.progress[KEY]["room"] = 3
        gm.player.hp = 1
        out = gm.enter_room()
        self.assertEqual(out.kind, REST)
        self.assertEqual(gm.player.hp, 1 + round(gm.player.max_hp * 0.5))
        self.assertEqual(gm.room_index, 4)

    def test_rest_never_overheals(self):
        gm = self.manager()
        gm.select_dungeon(KEY)
        gm.progress[KEY]["room"] = 3
        gm.enter_room()
        self.assertEqual(gm.player.hp, gm.player.max_hp)

    def test_treasure_room(self):
        gm = self.manager()
        gm.select_dungeon(KEY)
        gm.progress[KEY]["room"] = 4
        room = gm.current_room()
        out = gm.enter_room()
        self.assertEqual(out.kind, TREASURE)
        self.assertEqual(gm.player.coins, room.coins)
        self.assertEqual(gm.stats["xp_earned"], room.xp)

    def test_full_run_completes_dungeon(self):
        gm = self.manager()
        gm.select_dungeon(KEY)
        last = None
        for _ in range(8):
            last = self.play_room(gm)
        self.assertTrue(last.dungeon_completed)
        self.assertIsNotNone(last.final_reward)
        self.assertEqual(last.run["rooms"], 8)
        self.assertEqual(last.run["monsters"], 6)
        self.assertIsNone(gm.current_room())
        st = gm.dungeons()[0]
        self.assertTrue(st.completed)
        self.assertEqual(st.times, 1)
        self.assertEqual(gm.stats["dungeons_completed"], 1)
        self.assertGreaterEqual(last.run["xp"], config.DUNGEON_COMPLETE_XP)

    def test_replay_after_completion_restarts(self):
        gm = self.manager()
        gm.select_dungeon(KEY)
        for _ in range(8):
            self.play_room(gm)
        gm.select_dungeon(KEY)
        self.assertEqual(gm.room_index, 0)
        self.assertEqual(gm.run["rooms"], 0)
        self.assertTrue(gm.dungeons()[0].completed)  # remembered

    def test_enter_room_without_room_raises(self):
        gm = self.manager()
        with self.assertRaises(RuntimeError):
            gm.enter_room()


class DefeatTests(Base):
    def lose(self, gm):
        for _ in range(100):
            if gm.next_question() is None:
                break
            gm.answer("wrong!")
        self.assertEqual(gm.battle.state, DEFEAT)

    def test_defeat_counts_and_retry_restores(self):
        gm = self.manager()
        gm.select_dungeon(KEY)
        gm.enter_room()
        gm.next_question()
        gm.answer(gm.battle.question.answer)  # damage the monster first
        self.lose(gm)
        self.assertEqual(gm.stats["deaths"], 1)
        self.assertEqual(gm.player.hp, 0)
        self.assertEqual(gm.room_index, 0)
        gm.retry()
        self.assertEqual(gm.player.hp, gm.player.max_hp)
        self.assertEqual(gm.battle.monster.hp, gm.battle.monster.max_hp)
        self.assertEqual(gm.battle.state, ACTIVE)

    def test_retry_only_after_defeat(self):
        gm = self.manager()
        gm.select_dungeon(KEY)
        gm.enter_room()
        with self.assertRaises(RuntimeError):
            gm.retry()

    def test_reentering_after_defeat_is_healed(self):
        gm = self.manager()
        gm.select_dungeon(KEY)
        gm.enter_room()
        self.lose(gm)
        gm.leave()
        gm.enter_room()
        self.assertEqual(gm.battle.state, ACTIVE)
        self.assertEqual(gm.player.hp, gm.player.max_hp)

    def test_load_with_dead_player_restores_hp(self):
        gm = self.manager()
        gm.select_dungeon(KEY)
        gm.enter_room()
        self.lose(gm)
        gm2 = self.manager()
        self.assertEqual(gm2.player.hp, gm2.player.max_hp)


class PersistenceTests(Base):
    def test_save_file_next_to_words_json(self):
        self.assertEqual(save_path_for("/x/y/words.json"), Path("/x/y/dungeon_progress.json"))

    def test_progress_and_stats_survive_restart(self):
        gm = self.manager()
        gm.select_dungeon(KEY)
        gm.enter_room()
        self.win_fight(gm)
        coins, xp, stats = gm.player.coins, gm.player.xp, dict(gm.stats)
        gm2 = self.manager()
        self.assertEqual(gm2.player.coins, coins)
        self.assertEqual(gm2.player.xp, xp)
        self.assertEqual(gm2.stats, stats)
        gm2.select_dungeon(KEY)
        self.assertEqual(gm2.room_index, 1)
        self.assertTrue(gm2.dungeons()[0].in_progress)

    def test_fight_resumes_with_monster_hp(self):
        gm = self.manager()
        gm.select_dungeon(KEY)
        gm.enter_room()
        gm.next_question()
        gm.answer(gm.battle.question.answer)
        hp = gm.battle.monster.hp
        self.assertLess(hp, gm.battle.monster.max_hp)
        gm2 = self.manager()
        gm2.select_dungeon(KEY)
        gm2.enter_room()
        self.assertEqual(gm2.battle.monster.hp, hp)

    def test_leave_then_return_keeps_fight(self):
        gm = self.manager()
        gm.select_dungeon(KEY)
        gm.enter_room()
        gm.next_question()
        gm.answer(gm.battle.question.answer)
        hp = gm.battle.monster.hp
        gm.leave()
        gm.select_dungeon(KEY)
        gm.enter_room()
        self.assertEqual(gm.battle.monster.hp, hp)

    def test_missed_words_persist(self):
        gm = self.manager()
        gm.select_dungeon(KEY)
        gm.enter_room()
        gm.next_question()
        gm.answer("wrong")
        self.assertEqual(gm.missed_count, 1)
        self.assertEqual(self.manager().missed_count, 1)

    def test_saved_after_every_answer(self):
        gm = self.manager()
        gm.select_dungeon(KEY)
        gm.enter_room()
        gm.next_question()
        gm.answer("wrong")
        data = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(data["stats"]["wrong_answers"], 1)
        self.assertLess(data["player"]["hp"], data["player"]["max_hp"])

    def test_corrupt_save_starts_fresh_without_crashing(self):
        self.path.write_text("not json at all", encoding="utf-8")
        gm = self.manager()
        self.assertEqual(gm.player.level, 1)

    def test_garbage_values_are_sanitised(self):
        self.path.write_text(json.dumps({
            "player": {"level": "x", "hp": -5}, "stats": {"deaths": -3, "skips": "a"},
            "dungeons": {KEY: {"room": 999, "times": -1, "completed": "yes"}},
            "missed": ["a"], "fight": "dust_moth", "run": 7,
        }), encoding="utf-8")
        gm = self.manager()
        self.assertEqual(gm.stats["deaths"], 0)
        self.assertEqual(gm.progress[KEY]["room"], len(DUNGEONS[KEY].rooms))
        self.assertFalse(gm.progress[KEY]["completed"])
        self.assertEqual(gm.missed_count, 0)
        gm.select_dungeon(KEY)  # finished-looking dungeon restarts cleanly
        self.assertEqual(gm.room_index, 0)

    def test_stale_fight_for_other_room_is_ignored(self):
        self.path.write_text(json.dumps({
            "dungeons": {KEY: {"room": 0}},
            "fight": {"dungeon": KEY, "room": 5, "monster_hp": 3},
        }), encoding="utf-8")
        gm = self.manager()
        gm.select_dungeon(KEY)
        gm.enter_room()
        self.assertEqual(gm.battle.monster.hp, gm.battle.monster.max_hp)

    def test_unwritable_save_does_not_crash(self):
        gm = GameManager(self.deck, Path(self.tmp.name) / "file.txt" / "x.json", random.Random(1))
        (Path(self.tmp.name) / "file.txt").write_text("a")
        gm.select_dungeon(KEY)  # save fails silently
        self.assertIsNotNone(gm.dungeon)


class SafetyTests(Base):
    def test_words_json_and_levels_never_touched(self):
        words = Path(self.tmp.name) / "words.json"
        words.write_text("[]", encoding="utf-8")
        before = [(w.level, w.fails) for w in self.deck.words]
        gm = GameManager(self.deck, save_path_for(words), random.Random(3))
        gm.select_dungeon(KEY)
        for _ in range(8):
            if gm.current_room().is_fight:
                gm.enter_room()
                for i in range(30):
                    q = gm.next_question()
                    if q is None:
                        break
                    gm.skip() if i % 4 == 0 else gm.answer("wrong" if i % 3 else q.answer)
                    if gm.battle.state == DEFEAT:
                        gm.retry()
                if gm.battle.state != VICTORY:
                    gm.battle = None
                    gm.progress[KEY]["room"] += 1
            else:
                gm.enter_room()
        self.assertEqual([(w.level, w.fails) for w in self.deck.words], before)
        self.assertEqual(words.read_text(encoding="utf-8"), "[]")
        self.assertTrue(save_path_for(words).exists())

    def test_empty_deck_has_no_words(self):
        gm = GameManager(FlashcardDeck([]), self.path)
        self.assertFalse(gm.has_words)
        gm.select_dungeon(KEY)
        gm.enter_room()
        self.assertIsNone(gm.next_question())


if __name__ == "__main__":
    unittest.main()
