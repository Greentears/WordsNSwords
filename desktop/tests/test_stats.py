import random
import unittest
from dataclasses import replace

from dungeon import config, stats
from dungeon.battle import ACTIVE, VICTORY
from dungeon.items import ITEMS
from dungeon.manager import GameManager
from dungeon.models import Monster, Player
from tests.test_stage3 import Base


class EffectTests(unittest.TestCase):
    def fx(self, **points):
        return stats.effects({**{k: 0 for k in stats.STAT_KEYS}, **points})

    def test_no_points_no_effect(self):
        self.assertEqual(self.fx(), stats.Effects())

    def test_flat_effects_grow_without_a_limit(self):
        self.assertEqual(self.fx(strength=10).attack_pct, 25)
        self.assertEqual(self.fx(strength=400).attack_pct, 1000)
        self.assertEqual(self.fx(constitution=1000).hp, 5000)
        self.assertEqual(self.fx(intelligence=100).item_pct, 300)
        self.assertEqual(self.fx(charisma=100).coin_pct, 150)

    def test_limited_effects_approach_their_limit_but_never_pass_it(self):
        for stat, field, limit in (("dexterity", "dodge_pct", 35), ("charisma", "discount_pct", 25),
                                   ("charisma", "sell_bonus_pct", 20), ("wisdom", "wisdom_xp_pct", 50)):
            values = [getattr(self.fx(**{stat: n}), field) for n in (1, 10, 50, 500, 10**6)]
            self.assertEqual(values, sorted(values), field)           # more points never hurt
            self.assertLess(len(set(values)), len(values) + 1)
            self.assertTrue(all(0 < v < limit for v in values), field)
            self.assertGreater(values[1] - values[0], 0)
            self.assertGreater(values[2] - values[1], (values[3] - values[2]) / 10)  # diminishing returns

    def test_first_points_are_worth_about_limit_over_k(self):
        self.assertAlmostEqual(self.fx(dexterity=1).dodge_pct, 1.0, places=1)
        self.assertAlmostEqual(self.fx(charisma=1).discount_pct, 0.96, places=1)

    def test_steps_and_caps(self):
        self.assertEqual(self.fx(strength=4).armor_ignore, 0)
        self.assertEqual(self.fx(strength=15).armor_ignore, 3)
        self.assertEqual(self.fx(dexterity=8).time_bonus, 2)
        self.assertEqual(self.fx(constitution=80).victory_heal_pct, 50)

    def test_clean_stats(self):
        self.assertEqual(stats.clean_stats({"strength": 3, "wisdom": -1, "charisma": True, "x": 5})["strength"], 3)
        self.assertEqual(stats.clean_stats("junk"), {k: 0 for k in stats.STAT_KEYS})
        self.assertEqual(stats.clean_stats({"wisdom": -1, "charisma": True}), {k: 0 for k in stats.STAT_KEYS})

    def test_respec_cost(self):
        self.assertEqual(stats.respec_cost(10, 0), 0)
        self.assertEqual(stats.respec_cost(10, 1), 150)


class PlayerTests(unittest.TestCase):
    def test_level_up_gives_points(self):
        p = Player()
        p.add_xp(config.xp_to_next(1) + config.xp_to_next(2))
        self.assertEqual((p.level, p.stat_points), (3, 4))

    def test_old_save_gets_its_points_back_once(self):
        p = Player.from_dict({"level": 7})
        self.assertEqual(p.stat_points, 12)
        again = Player.from_dict(p.to_dict())
        self.assertEqual(again.stat_points, 12)          # now stored, not recalculated
        spent = Player.from_dict({**p.to_dict(), "stat_points": 0, "stats": {"strength": 12}})
        self.assertEqual((spent.stat_points, spent.stats["strength"]), (0, 12))

    def test_bad_saved_values(self):
        p = Player.from_dict({"level": 3, "stats": {"strength": "x"}, "stat_points": -5, "respecs": "a"})
        self.assertEqual((p.stats["strength"], p.stat_points, p.respecs), (0, 0, 0))

    def test_strength_changes_attack_power(self):
        p = Player()
        p.stats["strength"] = 10
        self.assertEqual(p.attack_power, round(10 * 1.25))


class ManagerStatTests(Base):
    heroes = 0

    def hero(self, level=10, **points):
        type(self).heroes += 1          # every hero has its own save file
        gm = GameManager(self.deck, self.path.with_name(f"hero{self.heroes}.json"), random.Random(1))
        gm.player.level = level
        gm.player.stat_points = 2 * (level - 1) + 2000     # plenty, so tests can try big builds
        gm.player.max_hp = gm.player.hp = config.BASE_MAX_HP + config.LEVEL_HP_GAIN * (level - 1)
        for k, n in points.items():
            gm.spend_point(k, n)
        return gm

    def test_spend_and_refuse(self):
        gm = self.hero(5)
        points = gm.player.stat_points
        gm.spend_point("strength", 3)
        self.assertEqual((gm.player.stats["strength"], gm.player.stat_points), (3, points - 3))
        for bad in (("luck", 1), ("strength", 0), ("strength", points)):
            with self.assertRaises(ValueError):
                gm.spend_point(*bad)

    def test_no_changes_during_a_fight(self):
        gm = self.hero(5)
        gm.select_dungeon("cellar")
        gm.enter_room()
        with self.assertRaises(ValueError):
            gm.spend_point("strength")
        with self.assertRaises(ValueError):
            gm.respec()

    def test_constitution_raises_max_hp_and_heals_the_new_hp(self):
        gm = self.hero(5)
        before = gm.player.max_hp
        gm.spend_point("constitution", 4)
        self.assertEqual(gm.player.max_hp, before + 20)
        self.assertEqual(gm.player.hp, gm.player.max_hp)
        self.assertEqual(gm.player.stat_hp, 20)

    def test_constitution_hp_survives_save_and_load_and_a_respec(self):
        gm = self.hero(5, constitution=4)
        base = config.BASE_MAX_HP + config.LEVEL_HP_GAIN * 4
        gm.save()
        again = GameManager(self.deck, gm.repo.path, random.Random(1))
        self.assertEqual(again.player.max_hp, base + 20)
        self.assertEqual(again.player.stats["constitution"], 4)
        again.respec()
        self.assertEqual(again.player.max_hp, base)
        self.assertEqual((again.player.stat_points, again.player.stats["constitution"]), (2008, 0))
        self.assertLessEqual(again.player.hp, base)

    def test_first_respec_is_free_then_it_costs_coins(self):
        gm = self.hero(5, strength=2)
        self.assertEqual(gm.respec_cost, 0)
        self.assertEqual(gm.respec(), 0)
        gm.spend_point("wisdom", 2)
        self.assertEqual(gm.respec_cost, 50 + 10 * 5)
        with self.assertRaises(ValueError):
            gm.respec()                      # no coins
        gm.player.coins = 100
        self.assertEqual(gm.respec(), 100)
        self.assertEqual(gm.player.coins, 0)
        with self.assertRaises(ValueError):
            gm.respec()                      # nothing to take back

    def test_strength_makes_hits_stronger_and_ignores_armor(self):
        weak = self.hero(10)
        strong = self.hero(10, strength=20)
        self.assertGreater(strong.player.attack_power, weak.player.attack_power)
        self.assertEqual(strong.player.effects.armor_ignore, 4)

    def test_dodge_stacks_with_a_companion_but_never_passes_the_limit(self):
        gm = self.hero(10, dexterity=10**3)
        gm.select_dungeon("cellar")
        gm.enter_room()
        b = gm.battle
        b.dodge_pct = 20
        self.assertLessEqual(min(stats.DODGE_TOTAL_LIMIT, b.dodge_pct + b.player.effects.dodge_pct), 35)
        dodged = 0
        for _ in range(300):
            if b.state != ACTIVE:
                break
            b.next_question()
            hp = b.player.hp
            r = b.skip()
            dodged += r.damage_taken == 0 and hp == b.player.hp
            b.player.hp = b.player.max_hp
        self.assertGreater(dodged, 0)
        self.assertLess(dodged, 300)         # never every time

    def test_a_dodged_hit_still_counts_as_a_missed_word(self):
        gm = self.hero(10, dexterity=500)
        gm.select_dungeon("cellar")
        gm.enter_room()
        for _ in range(40):
            q = gm.next_question()
            gm.answer("definitely wrong")
            gm.player.hp = gm.player.max_hp
            if gm.battle.state != ACTIVE:
                break
        self.assertGreater(gm.missed_count, 0)

    def test_timed_questions_get_dexterity_seconds(self):
        gm = self.hero(10, dexterity=9)
        gm.select_dungeon("forest")
        gm.player.level = 10
        gm.enter_room()
        self.assertEqual(gm.battle.time_bonus, 3)

    def test_charisma_lowers_prices_and_raises_sell_value(self):
        plain = self.hero(10)
        rich = self.hero(10, charisma=25)
        item = ITEMS["iron_sword"]
        self.assertEqual(plain.price(item), item.price)
        self.assertLess(rich.price(item), item.price)
        self.assertGreater(rich.price(item), item.price * 0.7)
        rich.player.coins = 10**5
        before = rich.player.coins
        rich.buy("iron_sword")
        self.assertEqual(before - rich.player.coins, rich.price(item))
        sold_plain = plain.inventory.sell_value(item, plain.sell_fraction)
        sold_rich = rich.inventory.sell_value(item, rich.sell_fraction)
        self.assertGreater(sold_rich, sold_plain)
        self.assertLessEqual(rich.sell_fraction, config.SELL_FRACTION + 0.2)
        self.assertTrue(any(e.price == rich.price(e.item) for e in rich.shop()))

    def test_charisma_gives_more_coins_from_a_fight(self):
        gm = self.hero(10)
        rich = self.hero(10, charisma=40)
        for m in (gm, rich):
            m.select_dungeon("cellar")
            m.enter_room()
        self.win_fight(gm)
        self.win_fight(rich)
        self.assertGreater(rich.player.coins, gm.player.coins)

    def test_intelligence_strengthens_items(self):
        smart = self.hero(10, intelligence=30)
        plain = self.hero(10)
        for m in (smart, plain):
            m.select_dungeon("cellar")
            m.enter_room()
            m.inventory.counts["fire_bomb"] = 1
            m.inventory.counts["small_potion"] = 1
            m.battle.monster = Monster(replace(m.battle.monster.spec, max_hp=500), 500)
        a = plain.use_item("fire_bomb")
        b = smart.use_item("fire_bomb")
        self.assertIn("for 20 damage", a.message)
        self.assertIn("for 38 damage", b.message)       # 20 * 1.9
        for m in (smart, plain):
            m.player.hp = 1
        a = plain.use_item("small_potion")
        b = smart.use_item("small_potion")
        self.assertLess(plain.player.hp, smart.player.hp)

    def test_victory_heal_from_constitution(self):
        gm = self.hero(10, constitution=10)
        gm.select_dungeon("cellar")
        gm.enter_room()
        gm.player.hp = 1
        self.win_fight(gm)
        self.assertIn("You recover", " ".join(gm.outcome.messages))
        self.assertGreater(gm.player.hp, 1)

    def test_wisdom_adds_xp_for_hard_words_only(self):
        def xp_of(points, levels):
            gm = self.hero(10, **points)
            for w in gm.deck.words:
                w.level = levels
            gm.select_dungeon("cellar")
            gm.enter_room()
            self.win_fight(gm)
            return gm.outcome.reward.xp
        hard_plain, hard_wise = xp_of({}, 1), xp_of({"wisdom": 30}, 1)
        easy_plain, easy_wise = xp_of({}, 3), xp_of({"wisdom": 30}, 3)
        self.assertGreater(hard_wise, hard_plain)
        self.assertEqual(easy_wise, easy_plain)

    def test_wisdom_does_not_boost_the_review_dungeon(self):
        def xp_of(points):
            gm = self.hero(10, **points)
            for w in gm.deck.words[:6]:
                gm.missed.miss(w.word)
            gm.select_dungeon("review")
            gm.enter_room()
            self.win_fight(gm)
            return gm.outcome.reward.xp
        self.assertEqual(xp_of({}), xp_of({"wisdom": 40}))


if __name__ == "__main__":
    unittest.main()


class EffectTextTests(unittest.TestCase):
    def test_texts(self):
        full = {"strength": 10, "constitution": 7, "dexterity": 30, "intelligence": 4, "charisma": 20, "wisdom": 25}
        self.assertEqual(stats.effect_text("strength", full), "+25% damage · ignores 2 armor")
        self.assertEqual(stats.effect_text("constitution", full), "+35 max HP · 7% HP back after a win")
        self.assertEqual(stats.effect_text("intelligence", full), "+12% item power")
        self.assertEqual(stats.effect_text("strength", {}), "+0% damage")
        self.assertEqual(stats.effect_text("nothing", full), "")
