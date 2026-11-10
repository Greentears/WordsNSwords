"""Monster abilities that counter hero stats and gear: unavoidable, piercing, crushing, poison, curse,
silence, shield (streak) and thief."""
import random
import unittest
from dataclasses import replace

from dungeon import config, tower
from dungeon.models import Monster
from tests.test_stats import ManagerStatTests


class AbilityTests(ManagerStatTests):
    def fight(self, level=10, hp=10_000, **spec):
        gm = self.hero(level)
        gm.select_dungeon("cellar")
        gm.enter_room()
        base = replace(gm.battle.monster.spec, max_hp=hp, damage=20, regen=0, lifesteal=False, enrage=False,
                       armor=0, time_limit=0, combo=False, **spec)
        gm.battle.monster = Monster(base, hp)
        return gm

    def wrong(self, gm):
        gm.next_question()
        return gm.answer("zzzz")

    def right(self, gm):
        q = gm.next_question()
        return gm.answer(q.answer)

    # -- unavoidable -------------------------------------------------------------
    def test_unavoidable_hits_cannot_be_dodged(self):
        for unavoidable, expected_misses in ((False, True), (True, False)):
            gm = self.fight(unavoidable=unavoidable)
            gm.battle.dodge_pct = 100                   # would dodge everything (capped at 35% in play)
            gm.player.stats["dexterity"] = 10**6
            gm.player.max_hp = gm.player.hp = 10**6          # survive the whole test
            gm.battle.rng = random.Random(5)
            hits = [self.wrong(gm).damage_taken for _ in range(40)]
            self.assertEqual(any(h == 0 for h in hits), expected_misses, unavoidable)

    def test_a_ward_still_stops_unavoidable_hits(self):
        gm = self.fight(unavoidable=True)
        gm.battle.ward = True
        self.assertEqual(self.wrong(gm).damage_taken, 0)

    # -- piercing ---------------------------------------------------------------
    def test_piercing_ignores_damage_reduction(self):
        results = []
        for pierce in (False, True):
            gm = self.fight(pierce=pierce)
            gm.player.gear_reduction = 8
            gm.battle.rng = random.Random(3)
            results.append(self.wrong(gm).damage_taken)
        self.assertLess(results[0], results[1])
        self.assertGreaterEqual(results[1], 19)

    # -- crushing (percent damage) ---------------------------------------------------
    def test_percent_damage_scales_with_max_hp_but_stays_under_the_cap(self):
        gm = self.fight(percent_damage=0.1)
        gm.battle.rng = random.Random(3)
        plain = self.fight()
        plain.battle.rng = random.Random(3)
        extra = self.wrong(gm).damage_taken - self.wrong(plain).damage_taken
        self.assertEqual(extra, round(gm.player.max_hp * 0.1))
        big = self.fight(percent_damage=5.0)
        self.assertEqual(self.wrong(big).damage_taken, int(big.player.max_hp * config.MAX_HIT_FRACTION))

    # -- poison ---------------------------------------------------------------
    def test_poison_hurts_for_a_few_answers_and_never_kills(self):
        gm = self.fight(poison=5)
        first = self.wrong(gm)
        self.assertIn("poisoned", first.message)
        hp = gm.player.hp
        second = self.right(gm)
        self.assertEqual(hp - gm.player.hp, 5)
        self.assertIn("poison burns", second.message)
        self.right(gm)
        self.right(gm)
        hp = gm.player.hp
        self.right(gm)                                  # the poison has run out
        self.assertEqual(gm.player.hp, hp)
        gm.battle.poison_turns = 3
        gm.player.hp = 3
        self.right(gm)
        self.assertEqual(gm.player.hp, config.POISON_MIN_HP)

    def test_a_dodged_hit_does_not_poison(self):
        gm = self.fight(poison=5)
        gm.battle.ward = True
        self.wrong(gm)
        self.assertEqual(gm.battle.poison_turns, 0)

    # -- curse and silence ----------------------------------------------------------
    def test_curse_halves_healing(self):
        gm = self.fight(curse=True)
        plain = self.fight()
        for m in (gm, plain):
            m.player.hp = 1
            m.inventory.counts["small_potion"] = 1
        use = gm.use_item("small_potion")
        normal = plain.use_item("small_potion")
        gained, full = gm.player.hp - 1, plain.player.hp - 1
        self.assertEqual(gained, round(full * config.CURSE_HEAL_FACTOR))
        self.assertTrue(use.ok and normal.ok)

    def test_silence_blocks_items_without_using_them_up(self):
        gm = self.fight(silence=True)
        gm.inventory.counts["small_potion"] = 2
        gm.player.hp = 5
        use = gm.use_item("small_potion")
        self.assertFalse(use.ok)
        self.assertIn("silences you", use.message)
        self.assertEqual((gm.inventory.counts["small_potion"], gm.player.hp), (2, 5))

    # -- shield -------------------------------------------------------------------
    def test_shield_needs_a_streak_of_correct_answers(self):
        gm = self.fight(streak=3)
        mon = gm.battle.monster
        self.assertEqual(self.right(gm).damage_dealt, 0)
        self.assertEqual(self.right(gm).damage_dealt, 0)
        self.assertEqual(mon.hp, mon.max_hp)
        self.assertGreater(self.right(gm).damage_dealt, 0)           # the third in a row breaks through
        self.assertGreater(self.right(gm).damage_dealt, 0)
        self.wrong(gm)                                                # a mistake rebuilds the shield
        self.assertEqual(self.right(gm).damage_dealt, 0)

    def test_shielded_correct_answers_still_clear_missed_words(self):
        gm = self.fight(streak=3)
        r = self.right(gm)
        self.assertTrue(r.correct)
        self.assertIn("shield holds", r.message)

    # -- thief --------------------------------------------------------------------
    def test_thief_steals_and_gives_back_on_victory(self):
        gm = self.fight(hp=60, thief=10)
        gm.player.coins = 25
        self.wrong(gm)
        self.wrong(gm)
        self.wrong(gm)
        self.assertEqual(gm.player.coins, 0)                          # only what you had: 10 + 10 + 5
        self.assertEqual(gm.battle.stolen, 25)
        gm.battle.monster.hp = 1
        before = gm.player.coins
        self.right(gm)
        self.assertGreaterEqual(gm.player.coins - before, 25)
        self.assertTrue(any("stolen coins" in m for m in gm.outcome.reward.messages))

    def test_a_thief_in_a_lost_fight_keeps_the_coins(self):
        gm = self.fight(thief=10)
        gm.player.coins = 30
        self.wrong(gm)
        self.assertEqual(gm.player.coins, 20)

    # -- texts and the Tower -----------------------------------------------------------
    def test_every_ability_has_a_text(self):
        spec = replace(config.MONSTERS["book_mimic"], unavoidable=True, pierce=True, percent_damage=0.08, poison=3, curse=True,
                       silence=True, streak=2, thief=8)
        text = " ".join(spec.abilities)
        for word in ("dodged", "damage reduction", "8% of your max HP", "Poison: 3 HP", "healing is halved", "no items",
                     "2 correct answers in a row", "8 coins"):
            self.assertIn(word, text)

    def test_tower_adds_abilities_from_floor_15_and_bosses_crush(self):
        self.assertEqual([k for k in ("unavoidable", "pierce", "percent_damage", "poison", "curse", "silence", "streak", "thief")
                          if getattr(tower.monster_for(14), k)], [])
        for floor in range(16, 60):
            spec = tower.monster_for(floor)
            if floor % 5 == 0:
                continue
            found = [k for k in tower.ABILITY_ROTATION if getattr(spec, k)]
            self.assertTrue(found, floor)
        for floor in (10, 20, 30, 40):
            self.assertGreater(tower.monster_for(floor).percent_damage, 0, floor)
        self.assertGreaterEqual(tower.monster_for(20).percent_damage, 0.05)
        self.assertLessEqual(tower.monster_for(500).percent_damage, 0.12)

    def test_the_cellar_stays_plain(self):
        for key in ("book_mimic", "ink_raven", "quill_stalker", "forgotten_scribe", "dust_moth"):
            spec = config.MONSTERS[key]
            self.assertFalse(any((spec.unavoidable, spec.pierce, spec.percent_damage, spec.poison, spec.curse, spec.silence,
                                  spec.streak, spec.thief)), key)


if __name__ == "__main__":
    unittest.main()
