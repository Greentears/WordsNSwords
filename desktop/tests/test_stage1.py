import json
import tempfile
import unittest
from pathlib import Path

from dungeon import config
from dungeon.models import Monster, Player
from dungeon.repository import GameProgressRepository, default_state


class PlayerTests(unittest.TestCase):
    def test_starts_at_level_one(self):
        p = Player()
        self.assertEqual((p.level, p.xp, p.hp, p.max_hp, p.coins), (1, 0, config.BASE_MAX_HP, config.BASE_MAX_HP, 0))
        self.assertEqual(p.name, "Adventurer")

    def test_level_up_raises_max_hp_and_heals(self):
        p = Player()
        p.hp = 5
        gained = p.add_xp(config.xp_to_next(1))
        self.assertEqual(gained, 1)
        self.assertEqual(p.level, 2)
        self.assertEqual(p.xp, 0)
        self.assertEqual(p.max_hp, config.BASE_MAX_HP + config.LEVEL_HP_GAIN)
        self.assertEqual(p.hp, p.max_hp)

    def test_several_levels_at_once_and_leftover_xp(self):
        p = Player()
        need = config.xp_to_next(1) + config.xp_to_next(2)
        self.assertEqual(p.add_xp(need + 7), 2)
        self.assertEqual((p.level, p.xp), (3, 7))

    def test_damage_and_heal_are_clamped(self):
        p = Player()
        self.assertEqual(p.take_damage(1000), config.BASE_MAX_HP)
        self.assertFalse(p.is_alive)
        self.assertEqual(p.heal(1000), config.BASE_MAX_HP)
        self.assertEqual(p.heal(5), 0)

    def test_negative_xp_ignored(self):
        p = Player()
        p.add_xp(-50)
        self.assertEqual(p.xp, 0)

    def test_round_trip(self):
        p = Player(name="Ola", level=4, xp=12, hp=20, max_hp=60, coins=33)
        self.assertEqual(Player.from_dict(p.to_dict()), p)

    def test_bad_saved_data_falls_back_to_defaults(self):
        for bad in (None, 5, "x", [], {"level": "abc", "hp": -4, "max_hp": 0, "name": 3, "coins": True}):
            p = Player.from_dict(bad)
            self.assertGreaterEqual(p.level, 1)
            self.assertGreaterEqual(p.max_hp, 1)
            self.assertTrue(0 <= p.hp <= p.max_hp)
            self.assertTrue(p.name)
            self.assertEqual(p.coins, 0)

    def test_saved_xp_cannot_exceed_level_threshold(self):
        p = Player.from_dict({"level": 1, "xp": 10**6})
        self.assertLess(p.xp, p.xp_needed)


class MonsterConfigTests(unittest.TestCase):
    def test_required_monsters_and_fields(self):
        for key in ("book_mimic", "ink_raven", "quill_stalker", "forgotten_scribe", "dust_moth"):
            spec = config.MONSTERS[key]
            self.assertTrue(spec.name)
            self.assertGreater(spec.max_hp, 0)
            self.assertGreater(spec.damage, 0)
            self.assertGreater(spec.xp, 0)
            self.assertGreaterEqual(spec.coins, 0)

    def test_difficulty_increases(self):
        order = [config.MONSTERS[k] for k in ("book_mimic", "ink_raven", "quill_stalker", "forgotten_scribe", "dust_moth")]
        self.assertEqual([m.max_hp for m in order], sorted(m.max_hp for m in order))
        self.assertTrue(config.MONSTERS["dust_moth"].boss)

    def test_spawn_and_damage(self):
        m = Monster.spawn(config.MONSTERS["book_mimic"])
        self.assertEqual(m.hp, m.max_hp)
        m.take_damage(5)
        self.assertEqual(m.hp, m.max_hp - 5)
        m.take_damage(999)
        self.assertFalse(m.is_alive)


class RepositoryTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = Path(self.dir.name) / "dungeon_progress.json"
        self.repo = GameProgressRepository(self.path)

    def tearDown(self):
        self.dir.cleanup()

    def test_missing_file_gives_fresh_state(self):
        self.assertEqual(self.repo.load(), default_state())

    def test_save_and_load(self):
        state = default_state()
        state["player"] = Player(coins=9).to_dict()
        self.repo.save(state)
        self.assertEqual(self.repo.load()["player"]["coins"], 9)
        self.assertFalse(self.path.with_name(self.path.name + ".tmp").exists())

    def test_corrupt_file_falls_back_to_backup(self):
        state = default_state()
        state["player"] = Player(coins=1).to_dict()
        self.repo.save(state)
        state["player"] = Player(coins=2).to_dict()
        self.repo.save(state)          # backup now holds coins=1
        self.path.write_text("{ not json", encoding="utf-8")
        self.assertEqual(self.repo.load()["player"]["coins"], 1)
        self.assertTrue(self.path.with_name(self.path.name + ".corrupt").exists())

    def test_corrupt_file_without_backup_gives_fresh_state(self):
        self.path.write_text("[1, 2", encoding="utf-8")
        self.assertEqual(self.repo.load(), default_state())

    def test_wrong_json_type_ignored(self):
        self.path.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
        self.assertEqual(self.repo.load(), default_state())

    def test_unknown_keys_dropped_known_keys_kept(self):
        self.path.write_text(json.dumps({"stats": {"x": 1}, "junk": 5}), encoding="utf-8")
        loaded = self.repo.load()
        self.assertEqual(loaded["stats"], {"x": 1})
        self.assertNotIn("junk", loaded)


if __name__ == "__main__":
    unittest.main()
