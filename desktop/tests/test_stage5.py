import json
FIXTURES = __import__("pathlib").Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "pl-en"
import random
import tempfile
import unittest
from pathlib import Path

from dungeon import config, items
from dungeon.answers import accepted_forms, check, primary
from dungeon.battle import ACTIVE, DEFEAT, VICTORY, Battle
from dungeon.dungeons import DUNGEONS
from dungeon.inventory import Inventory
from dungeon.manager import GameManager
from dungeon.models import BOSS, Monster, Player
from dungeon.selector import VocabularySelector
from flashcards import FlashcardDeck, Word


class AnswerTests(unittest.TestCase):
    def ok(self, given, expected, reverse=False):
        self.assertTrue(check(given, expected, reverse)[0], f"{given!r} vs {expected!r}")

    def bad(self, given, expected, reverse=False):
        self.assertFalse(check(given, expected, reverse)[0], f"{given!r} vs {expected!r}")

    def test_reported_examples(self):
        for g in ("run by", "run", "operated by", "Run / operated by"):
            self.ok(g, "run / operated by")
        for g in ("corner", "nook", "little corner", "a corner"):
            self.ok(g, "little corner / nook")

    def test_shared_head_and_tail(self):
        self.ok("can I taste it", "can I try / taste it?")
        self.ok("wedding reception", "wedding party / reception")

    def test_brackets_to_and_articles(self):
        self.ok("miss", "to miss (someone / something)")
        self.ok("cook", "to cook / boil")
        self.ok("boil", "to cook / boil")
        self.ok("the pancake", "pancake / crepe")
        self.ok("chit chat", "chit-chat / small talk")
        self.ok("tap water", "tap water (colloquial)")

    def test_wrong_stays_wrong(self):
        self.bad("kitchen", "to cook / boil")
        self.bad("away", "to run away")
        self.bad("walk", "talk")
        self.bad("", "x")
        self.bad("the", "the")

    def test_polish_direction(self):
        self.ok("wzruszona", "wzruszony / wzruszona", True)
        self.ok("bać", "bać się", True)
        self.ok("bac sie", "bać się", True)
        self.ok("dobre pachnie", "dobre / ładne pachnie", True)
        self.ok("zmierzać", "zmierzać (do)", True)
        self.assertEqual(check("zmierzac", "zmierzać (do)", True), (True, False))

    def test_typo_tolerance_only_for_longer_words(self):
        self.assertEqual(check("quantiti", "quantity / amount"), (True, False))
        self.ok("recieve", "receive")       # swapped letters
        self.bad("cat", "cut")
        self.bad("cost", "coat")

    def test_exact_flag(self):
        self.assertEqual(check("run by", "run / operated by"), (True, True))

    def test_primary(self):
        self.assertEqual(primary("to cook / boil"), "cook")
        self.assertEqual(primary("bać się", True), "bać się")

    def test_every_card_accepts_itself_both_ways(self):
        words = json.loads(FIXTURES.joinpath("words.json")
                           .read_text(encoding="utf-8"))
        for c in words:
            for side, rev in ((c["translation"], False), (c["word"], True)):
                self.assertTrue(check(side, side, rev)[0], side)
                self.assertTrue(accepted_forms(side, rev), side)


def deck():
    return FlashcardDeck([Word(f"p{i}", f"en{i}", sentence=f"Zdanie {i}.",
                               sentence_translation=f"Sentence {i}.", level=1) for i in range(12)])


def battle(monster="book_mimic", player=None, seed=1, **flags):
    rng = random.Random(seed)
    b = Battle(player or Player(), Monster.spawn(config.MONSTERS[monster]),
               VocabularySelector(deck(), rng=rng), rng)
    for k, v in flags.items():
        setattr(b, k, v)
    return b


class MechanicsTests(unittest.TestCase):
    def test_reverse_questions_ask_polish(self):
        spec = config.MonsterSpec("t", "T", 500, 1, 1, 1, reverse_chance=1.0)
        config.MONSTERS["t"] = spec
        try:
            b = battle("t")
            q = b.next_question()
            self.assertTrue(q.reverse)
            self.assertTrue(q.prompt.startswith("en"))
            self.assertTrue(b.submit(q.answer).correct)
            self.assertIn("Sentence", b.hint_text() if b.question else "Sentence")
        finally:
            del config.MONSTERS["t"]

    def test_forward_only_when_chance_zero(self):
        b = battle("book_mimic")
        for _ in range(10):
            q = b.next_question()
            self.assertFalse(q.reverse)
            b.submit("zzz")
            if b.state != ACTIVE:
                break

    def test_armor_reduces_player_damage(self):
        a = battle("book_mimic", seed=3)
        b = battle("forgotten_scribe", seed=3)
        da = db = 0
        a.next_question(); da = a.submit(a.question.answer).damage_dealt
        q = b.next_question(); db = b.submit(q.answer).damage_dealt
        self.assertLessEqual(db, da)
        self.assertGreaterEqual(db, 1)

    def test_regen_heals_on_wrong(self):
        b = battle("treant")
        b.next_question(); b.submit(b.question.answer)       # damage it
        hp = b.monster.hp
        b.next_question()
        r = b.submit("nope")
        self.assertGreater(b.monster.hp, hp)
        self.assertIn("regenerates", r.message)

    def test_enrage_hits_harder_when_low(self):
        calm = battle("dust_moth")
        low = battle("dust_moth")
        low.monster.hp = 10
        self.assertGreater(low._monster_damage("wrong"), calm._monster_damage("wrong"))

    def test_lifesteal_heals_monster(self):
        b = battle("bat")
        b.monster.hp = 10
        b.next_question()
        b.submit("zzz")
        self.assertGreater(b.monster.hp, 10)

    def test_combo_stacks_and_resets(self):
        b = battle("wolf")
        base = b._monster_damage("wrong")
        b.consecutive_wrong = 3
        self.assertAlmostEqual(b._monster_damage("wrong"), base * 1.9)
        b.consecutive_wrong = 10
        self.assertAlmostEqual(b._monster_damage("wrong"), base * 1.9)
        b.next_question(); b.submit(b.question.answer)
        self.assertEqual(b.consecutive_wrong, 0)

    def test_timeout_is_wrong(self):
        b = battle("witch")
        q = b.next_question()
        self.assertEqual(q.time_limit, 25)
        r = b.timeout()
        self.assertTrue(r.timed_out)
        self.assertFalse(r.correct)
        self.assertGreater(r.damage_taken, 0)
        self.assertIn("Time's up", r.message)
        self.assertEqual(len(b.missed), 1)

    def test_time_bonus(self):
        b = battle("witch", time_bonus=8)
        self.assertEqual(b.next_question().time_limit, 33)
        self.assertEqual(battle("book_mimic").next_question().time_limit, 0)

    def test_gear_reduction_and_floor(self):
        p = Player(); p.gear_reduction = 100
        b = battle("dust_moth", player=p)
        b.next_question()
        self.assertEqual(b.submit("x").damage_taken, 1)

    def test_ward_absorbs_once(self):
        b = battle("ink_raven", ward=True)
        b.next_question()
        r = b.submit("x")
        self.assertEqual(r.damage_taken, 0)
        self.assertIn("ward", r.message)
        b.next_question()
        self.assertGreater(b.submit("x").damage_taken, 0)

    def test_phoenix_revives_once(self):
        p = Player(hp=1, max_hp=100)
        b = battle("ink_raven", player=p, phoenix=True)
        b.next_question()
        r = b.submit("x")
        self.assertEqual(b.state, ACTIVE)
        self.assertEqual(p.hp, 30)
        self.assertIn("Phoenix", r.message)
        p.hp = 1
        b.next_question()
        b.submit("x")
        self.assertEqual(b.state, DEFEAT)

    def test_reveal_items_show_letters_without_changing_damage(self):
        for seed in range(10):
            plain, rev = battle(seed=seed), battle(seed=seed)
            q = plain.next_question(); q2 = rev.next_question()
            text = rev.reveal(first=True, count=True)
            self.assertIn("Starts with", text)
            self.assertIn("letters", text)
            self.assertEqual(plain.submit(q.answer).damage_dealt, rev.submit(q2.answer).damage_dealt)

    def test_mistake_shows_the_original_word(self):
        b = battle()
        q = b.next_question()
        self.assertIn(f'"{q.prompt}" means "{q.answer}"', b.submit("zzz").message)

    def test_brakuje_style_answers(self):
        for g in ("to lack", "lack", "missing", "is missing", "lacking"):
            self.assertTrue(check(g, "is missing / is lacking")[0], g)
        self.assertFalse(check("cat", "is missing / is lacking")[0])

    def test_free_skip_has_no_penalty(self):
        b = battle()
        b.next_question()
        r = b.free_skip()
        self.assertTrue(r.free)
        self.assertEqual((r.damage_taken, r.damage_dealt), (0, 0))
        self.assertEqual(len(b.missed), 0)
        self.assertEqual(b.player.hp, b.player.max_hp)

    def test_ability_descriptions(self):
        self.assertEqual(config.MONSTERS["book_mimic"].abilities, [])
        self.assertTrue(config.MONSTERS["dragon"].abilities)


class InventoryTests(unittest.TestCase):
    def test_catalogue_sane(self):
        for item in items.ITEMS.values():
            self.assertGreater(item.price, 0)
            self.assertGreaterEqual(item.level, 1)
            if item.is_equipment:
                self.assertIn(item.slot, items.SLOTS)
            else:
                self.assertTrue(item.effect)
        for slot in items.SLOTS:   # better gear costs more and needs more level
            tier = sorted((i for i in items.ITEMS.values() if i.slot == slot and i.shop),
                          key=lambda i: i.price)
            self.assertEqual([i.level for i in tier], sorted(i.level for i in tier))

    def test_buy_rules(self):
        inv, p = Inventory(), Player(coins=500)
        with self.assertRaises(ValueError):
            inv.buy(items.ITEMS["iron_sword"], p)        # level 3
        p.level = 3
        inv.buy(items.ITEMS["iron_sword"], p)
        self.assertEqual(p.coins, 370)
        with self.assertRaises(ValueError):
            inv.buy(items.ITEMS["iron_sword"], p)        # already owned
        self.assertEqual(p.coins, 370)

    def test_buy_consumable_and_coins(self):
        inv, p = Inventory(), Player(coins=50)
        inv.buy(items.ITEMS["letter_scroll"], p)
        inv.buy(items.ITEMS["letter_scroll"], p)
        self.assertEqual((inv.count("letter_scroll"), p.coins), (2, 20))
        with self.assertRaises(ValueError):
            inv.buy(items.ITEMS["fire_bomb"], p)         # 30 > 20
        self.assertEqual(p.coins, 20)

    def test_first_equipment_is_worn_second_is_not(self):
        inv, p = Inventory(), Player(coins=1000, level=5)
        inv.buy(items.ITEMS["wooden_sword"], p)
        inv.buy(items.ITEMS["iron_sword"], p)
        self.assertEqual(inv.equipped["weapon"], "wooden_sword")
        inv.equip("iron_sword")
        self.assertEqual(inv.totals().attack, 5)

    def test_round_trip_and_garbage(self):
        inv, p = Inventory(), Player(coins=1000, level=5)
        inv.buy(items.ITEMS["fire_bomb"], p)
        inv.buy(items.ITEMS["chainmail"], p)
        self.assertEqual(Inventory(inv.to_dict()).to_dict(), inv.to_dict())
        g = Inventory({"items": {"nope": 3, "fire_bomb": -1, "ward_scroll": "x", "meteor": 500},
                       "owned": ["nope", "wooden_sword", 4, "fire_bomb"],
                       "equipped": {"weapon": "iron_sword", "armor": "wooden_sword", "bad": "x"}})
        self.assertEqual(g.counts, {"meteor": config.MAX_ITEM_STACK})
        self.assertEqual(g.owned, {"wooden_sword"})
        self.assertEqual(g.equipped, {})
        self.assertEqual(Inventory("junk").to_dict(), Inventory().to_dict())


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "dungeon_progress.json"

    def tearDown(self):
        self.tmp.cleanup()

    def gm(self, seed=1, state=None):
        if state is not None:
            self.path.write_text(json.dumps(state), encoding="utf-8")
        return GameManager(deck(), self.path, random.Random(seed))

    def fight(self, gm, dungeon="cellar", room=0):
        gm.select_dungeon(dungeon)
        gm.progress[dungeon]["room"] = room
        assert gm.enter_room() is None
        gm.next_question()


class ShopManagerTests(Base):
    def test_equipment_changes_stats_and_persists(self):
        gm = self.gm(state={"player": {"level": 5, "coins": 2000, "max_hp": 70, "hp": 70}})
        gm.buy("steel_blade"); gm.buy("chainmail")
        p = gm.player
        self.assertEqual(p.gear_attack, 9)
        self.assertEqual((p.max_hp, p.hp, p.gear_hp, p.gear_reduction), (95, 95, 25, 1))
        gm2 = self.gm()
        self.assertEqual((gm2.player.max_hp, gm2.player.gear_attack, gm2.player.gear_reduction), (95, 9, 1))
        self.assertEqual(gm2.player.coins, 2000 - 320 - 220)

    def test_unequip_lowers_max_hp_cleanly(self):
        gm = self.gm(state={"player": {"level": 5, "coins": 500, "max_hp": 70, "hp": 70}})
        gm.buy("chainmail")
        gm.unequip("armor")
        self.assertEqual((gm.player.max_hp, gm.player.hp, gm.player.gear_hp), (70, 70, 0))
        gm.equip("chainmail")
        self.assertEqual(gm.player.max_hp, 95)

    def test_level_up_with_gear_keeps_bonus(self):
        gm = self.gm(state={"player": {"level": 2, "coins": 500, "max_hp": 40, "hp": 40}})
        gm.buy("leather_vest")
        gm.player.add_xp(10_000)
        self.assertEqual(gm.player.gear_hp, 10)
        gm.unequip("armor")
        self.assertEqual(gm.player.max_hp, gm.player.max_hp)
        self.assertEqual(gm.player.gear_hp, 0)

    def test_shop_listing_and_problems(self):
        gm = self.gm(state={"player": {"coins": 20}})
        entries = {e.item.key: e for e in gm.shop()}
        self.assertIsNone(entries["letter_scroll"].problem)
        self.assertEqual(entries["fire_bomb"].problem, "Not enough coins")
        self.assertEqual(entries["iron_sword"].problem, "Requires level 3")
        with self.assertRaises(ValueError):
            gm.buy("fire_bomb")
        self.assertEqual(gm.player.coins, 20)

    def test_stats_for_purchases(self):
        gm = self.gm(state={"player": {"coins": 100}})
        gm.buy("letter_scroll")
        self.assertEqual((gm.stats["items_bought"], gm.stats["coins_spent"]), (1, 15))

    def test_gear_bonus_effects_in_fight(self):
        gm = self.gm(state={"player": {"level": 8, "coins": 3000, "max_hp": 100, "hp": 100}})
        gm.buy("phoenix_feather"); gm.buy("time_amulet")  # second charm is not worn
        self.fight(gm)
        self.assertTrue(gm.battle.phoenix)
        self.assertEqual(gm.battle.time_bonus, 0)
        gm.leave(); gm.equip("time_amulet")
        gm.select_dungeon("cellar"); gm.enter_room()
        self.assertFalse(gm.battle.phoenix)
        self.assertEqual(gm.battle.time_bonus, 8)


class ItemUseTests(Base):
    def stocked(self, **counts):
        return self.gm(state={"player": {"level": 5}, "inventory": {"items": counts}})

    def test_only_in_fight(self):
        gm = self.stocked(fire_bomb=1)
        r = gm.use_item("fire_bomb")
        self.assertFalse(r.ok)
        self.assertEqual(gm.inventory.count("fire_bomb"), 1)

    def test_bomb_damages_and_is_consumed(self):
        gm = self.stocked(fire_bomb=2)
        self.fight(gm, room=5)      # skeleton, 50 hp
        r = gm.use_item("fire_bomb")
        self.assertTrue(r.ok)
        self.assertEqual(gm.battle.monster.hp, 30)
        self.assertEqual(gm.inventory.count("fire_bomb"), 1)
        self.assertEqual(gm.stats["items_used"], 1)

    def test_bomb_can_win_fight_and_pays_rewards_once(self):
        gm = self.stocked(meteor=1)
        self.fight(gm, room=0)
        coins = gm.player.coins
        r = gm.use_item("meteor")
        self.assertEqual(r.state, VICTORY)
        self.assertIsNotNone(gm.outcome)
        self.assertGreater(gm.player.coins, coins)
        self.assertEqual(gm.room_index, 1)
        gm._finish_if_won()
        self.assertEqual(gm.room_index, 1)
        self.assertEqual(gm.stats["monsters_defeated"], 1)

    def test_potion_heals_and_not_wasted_at_full_hp(self):
        gm = self.stocked(small_potion=1)
        self.fight(gm)
        self.assertFalse(gm.use_item("small_potion").ok)
        self.assertEqual(gm.inventory.count("small_potion"), 1)
        gm.player.hp = 1
        self.assertTrue(gm.use_item("small_potion").ok)
        self.assertEqual(gm.player.hp, 1 + round(gm.player.max_hp * 0.4))
        self.assertEqual(gm.inventory.count("small_potion"), 0)

    def test_hint_items(self):
        gm = self.stocked(letter_scroll=2, count_rune=1, oracle_eye=1)
        self.fight(gm)
        r = gm.use_item("letter_scroll")
        self.assertIn("Starts with", r.hint)
        self.assertFalse(gm.use_item("letter_scroll").ok)      # already revealed, not consumed
        self.assertEqual(gm.inventory.count("letter_scroll"), 1)
        self.assertIn("letters", gm.use_item("count_rune").hint)
        self.assertFalse(gm.use_item("oracle_eye").ok)         # everything is already revealed
        self.assertEqual(gm.inventory.count("oracle_eye"), 1)

    def test_ward_scroll(self):
        gm = self.stocked(ward_scroll=2)
        self.fight(gm)
        self.assertTrue(gm.use_item("ward_scroll").ok)
        self.assertFalse(gm.use_item("ward_scroll").ok)
        hp = gm.player.hp
        gm.answer("zzz")
        self.assertEqual(gm.player.hp, hp)

    def test_passage_scroll_is_free_and_not_counted(self):
        gm = self.stocked(passage_scroll=1)
        self.fight(gm)
        r = gm.use_item("passage_scroll")
        self.assertTrue(r.ok and r.result.free)
        self.assertEqual((gm.stats["wrong_answers"], gm.stats["skips"]), (0, 0))
        self.assertEqual(gm.missed_count, 0)
        self.assertIsNotNone(gm.next_question())

    def test_boost_items_double_rewards(self):
        base = self.stocked(); self.fight(base)
        while base.battle.state == ACTIVE:
            base.answer(base.battle.question.answer); base.next_question()
        gm = self.stocked(wisdom_tome=1, golden_idol=1)
        gm.use_item("wisdom_tome")  # no fight yet: refused
        self.fight(gm)
        self.assertTrue(gm.use_item("wisdom_tome").ok)
        self.assertTrue(gm.use_item("golden_idol").ok)
        while gm.battle.state == ACTIVE:
            gm.answer(gm.battle.question.answer); gm.next_question()
        spec = config.MONSTERS["book_mimic"]
        self.assertEqual(gm.outcome.reward.xp, spec.xp * 2)
        self.assertEqual(gm.outcome.reward.coins, (spec.coins + config.ROOM_CLEAR_COINS) * 2)
        self.assertEqual(base.outcome.reward.xp, spec.xp)

    def test_charm_percentages(self):
        gm = self.gm(state={"player": {"level": 8, "coins": 3000},
                            "inventory": {"owned": ["sages_ring"], "equipped": {"charm": "sages_ring"}}})
        self.fight(gm)
        while gm.battle.state == ACTIVE:
            gm.answer(gm.battle.question.answer); gm.next_question()
        self.assertEqual(gm.outcome.reward.xp, round(config.MONSTERS["book_mimic"].xp * 1.25))

    def test_timeout_via_manager(self):
        gm = self.gm(state={"player": {"level": 8}})
        self.fight(gm, "forest", room=5)
        self.assertEqual(gm.battle.question.time_limit, 25)
        r = gm.timeout()
        self.assertTrue(r.timed_out)
        self.assertEqual(gm.stats["wrong_answers"], 1)

    def test_items_persist(self):
        gm = self.stocked(fire_bomb=3)
        self.fight(gm, room=5)
        gm.use_item("fire_bomb")
        gm2 = self.gm()
        self.assertEqual(gm2.inventory.count("fire_bomb"), 2)


class DungeonUnlockTests(Base):
    def test_dungeons_exist_and_are_valid(self):
        self.assertGreaterEqual(len(DUNGEONS), 6)
        for d in DUNGEONS.values():
            if d.endless:
                continue
            if d.kind == "story":
                self.assertEqual(d.rooms[-1].kind, BOSS)
            for r in d.rooms:
                if r.is_fight:
                    self.assertIn(r.monster, config.MONSTERS)
                    self.assertEqual(config.MONSTERS[r.monster].boss, r.kind == BOSS)

    def test_locked_until_level(self):
        gm = self.gm()
        st = {s.key: s for s in gm.dungeons()}
        self.assertFalse(st["cellar"].locked)
        self.assertTrue(st["forest"].locked)
        with self.assertRaises(ValueError):
            gm.select_dungeon("forest")
        gm.player.level = 4
        gm.select_dungeon("forest")
        self.assertEqual(gm.dungeon.key, "forest")

    def test_progress_independent_per_dungeon(self):
        gm = self.gm(state={"player": {"level": 9}})
        gm.select_dungeon("cellar"); gm.enter_room()
        while gm.battle.state == ACTIVE:
            gm.next_question(); gm.answer(gm.battle.question.answer)
        gm.leave()
        gm.select_dungeon("forest")
        self.assertEqual(gm.room_index, 0)
        gm.select_dungeon("cellar")
        self.assertEqual(gm.room_index, 1)

    def test_every_finite_dungeon_can_be_completed(self):
        for key, d in DUNGEONS.items():
            if d.endless:
                continue
            gm = self.gm(state={"player": {"level": 20, "max_hp": 500, "hp": 500},
                                "missed": {"p1": 0, "p2": 0}})
            gm.select_dungeon(key, restart=True)
            last = None
            for _ in range(len(d.rooms)):
                if gm.current_room().is_fight:
                    gm.enter_room()
                    while gm.battle.state == ACTIVE:
                        q = gm.next_question()
                        gm.answer(q.answer)
                    last = gm.outcome
                else:
                    last = gm.enter_room()
            self.assertTrue(last.dungeon_completed, key)
            if d.complete_xp:         # the Review Guru pays everything with its own victory
                self.assertIn(f"+{round(d.complete_xp * d.reward_scale)} XP", last.final_reward.messages)
            else:
                self.assertNotIn("XP", " ".join(last.final_reward.messages))

    def test_old_version1_save_loads(self):
        old = {"version": 1,
               "player": {"name": "Adventurer", "level": 5, "xp": 75, "hp": 70, "max_hp": 70, "coins": 200},
               "dungeons": {"cellar": {"room": 8, "completed": True, "times": 1}},
               "run": {}, "stats": {"deaths": 1}, "missed": {"kącik": 0}, "fight": None}
        gm = self.gm(state=old)
        self.assertEqual((gm.player.level, gm.player.coins, gm.player.max_hp), (5, 200, 70))
        self.assertEqual(gm.inventory.counts, {})
        self.assertEqual(gm.stats["deaths"], 1)
        self.assertFalse({s.key: s for s in gm.dungeons()}["forest"].locked)   # level 5 >= 4
        self.assertTrue({s.key: s for s in gm.dungeons()}["citadel"].locked)


if __name__ == "__main__":
    unittest.main()
