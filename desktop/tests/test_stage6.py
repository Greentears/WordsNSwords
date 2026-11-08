import json
import random
import tempfile
import unittest
from pathlib import Path

from dungeon import config, tower
from dungeon.battle import ACTIVE, VICTORY, Battle
from dungeon.cloze import ClozeSource
from dungeon.dungeons import DUNGEONS
from dungeon.items import COMPANION, ITEMS, TOWER_BUNDLES, TOWER_LOOT
from dungeon.manager import GameManager
from dungeon.models import BOSS, MONSTER, REST, TREASURE, Monster, Player
from dungeon.selector import MissedWords, VocabularySelector
from flashcards import FlashcardDeck, Word


def deck():
    words = [Word("pozwalać", "to allow", sentence="W tym parku nie pozwalają psom biegać.",
                  sentence_translation="Dogs are not allowed to run here.", level=1),
             Word("dom", "house", sentence="Mój dom jest duży.",
                  sentence_translation="My house is big.", level=2)]
    words += [Word(f"p{i}", f"en{i}", level=1) for i in range(10)]
    return FlashcardDeck(words)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "dungeon_progress.json"

    def tearDown(self):
        self.tmp.cleanup()

    def gm(self, state=None, seed=1):
        if state is not None:
            self.path.write_text(json.dumps(state), encoding="utf-8")
        return GameManager(deck(), self.path, random.Random(seed))

    def strong(self, **extra):
        player = {"level": 30, "max_hp": 900, "hp": 900, "coins": 0}
        player.update(extra)
        return {"player": player}

    def win(self, gm):
        while gm.battle.state == ACTIVE:
            gm.answer(gm.next_question().answer)


class TowerLayoutTests(unittest.TestCase):
    def test_floor_pattern(self):
        for floor in range(1, 201):
            room = tower.floor_room(floor - 1)
            self.assertNotEqual(room.kind, TREASURE)
            if floor % 10 == 0:
                self.assertEqual(room.kind, BOSS)
                self.assertTrue(room.drop)
                self.assertTrue(room.spec.boss)
            elif floor % 5 == 0:
                self.assertEqual(room.kind, REST)
            else:
                self.assertEqual(room.kind, MONSTER)
                self.assertIsNone(room.drop)

    def test_monsters_grow_stronger(self):
        a, b = tower.monster_for(1), tower.monster_for(49)
        self.assertGreater(b.max_hp, a.max_hp * 2)
        self.assertGreater(tower.monster_for(100).damage, tower.monster_for(50).damage)
        self.assertGreater(tower.monster_for(40).max_hp, tower.monster_for(10).max_hp)
        self.assertTrue(tower.monster_for(25).enrage)

    def test_every_floor_monster_is_drawable_and_valid(self):
        from dungeon.sprites import SPRITE_KEYS
        for floor in range(1, 150):
            spec = tower.monster_for(floor)
            self.assertIn(spec.key, SPRITE_KEYS)
            self.assertGreater(spec.max_hp, 0)

    def test_loot_order_then_bundles(self):
        for i, key in enumerate(TOWER_LOOT):
            self.assertEqual(tower.loot_for(10 * (i + 1)), (key, 1))
        for n in range(len(TOWER_LOOT) + 1, len(TOWER_LOOT) + 20):
            key, count = tower.loot_for(10 * n)
            self.assertIn((key, count), TOWER_BUNDLES)
            self.assertIn(key, ITEMS)

    def test_loot_items_are_not_for_sale(self):
        for key in TOWER_LOOT:
            self.assertFalse(ITEMS[key].shop)


class TowerPlayTests(Base):
    def test_ten_floors_drop_first_trophy(self):
        gm = self.gm(self.strong())
        gm.select_dungeon("tower")
        outcomes = []
        for floor in range(1, 11):
            room = gm.current_room()
            if room.is_fight:
                gm.enter_room()
                self.win(gm)
                outcomes.append(gm.outcome)
            else:
                outcomes.append(gm.enter_room())
        self.assertEqual(gm.room_index, 10)
        self.assertEqual(gm.progress["tower"]["best"], 10)
        self.assertEqual(outcomes[4].kind, REST)          # floor 5
        self.assertIsNone(outcomes[0].loot)
        self.assertIn("Sword of the Tower", outcomes[9].loot)
        self.assertTrue(gm.inventory.has("tower_blade"))
        self.assertEqual(gm.inventory.equipped["weapon"], "tower_blade")
        self.assertEqual(gm.player.gear_attack, 26)
        self.assertFalse(outcomes[9].dungeon_completed)   # the tower never ends
        self.assertIsNotNone(gm.current_room())

    def test_duplicate_trophy_is_sold(self):
        gm = self.gm(self.strong())
        gm.select_dungeon("tower")
        gm.inventory.give("tower_blade")
        gm.progress["tower"]["room"] = 9
        coins = gm.player.coins
        gm.enter_room()
        self.win(gm)
        self.assertIn("sold for 720 coins", gm.outcome.loot)
        self.assertGreaterEqual(gm.player.coins, coins + 600)

    def test_bundle_drop_gives_items(self):
        gm = self.gm(self.strong())
        gm.select_dungeon("tower")
        gm.progress["tower"]["room"] = 6 * 10 + 9      # floor 70: first bundle
        gm.enter_room()
        self.win(gm)
        key, count = tower.loot_for(70)
        self.assertEqual(gm.inventory.count(key), count)

    def test_progress_and_best_persist_and_restart_keeps_best(self):
        gm = self.gm(self.strong())
        gm.select_dungeon("tower")
        for _ in range(3):
            gm.enter_room()
            self.win(gm)
        gm2 = self.gm()
        st = {s.key: s for s in gm2.dungeons()}["tower"]
        self.assertEqual((st.room, st.best, st.endless, st.in_progress), (3, 3, True, True))
        gm2.select_dungeon("tower")
        self.assertEqual(gm2.room_index, 3)
        gm2.select_dungeon("tower", restart=True)
        self.assertEqual(gm2.room_index, 0)
        self.assertEqual(gm2.progress["tower"]["best"], 3)

    def test_tower_fight_resumes_with_monster_hp(self):
        gm = self.gm({"player": {"level": 3, "max_hp": 50, "hp": 50}})
        gm.select_dungeon("tower")
        gm.enter_room()
        gm.answer(gm.next_question().answer)
        hp = gm.battle.monster.hp
        self.assertGreater(hp, 0)
        gm2 = self.gm()
        gm2.select_dungeon("tower")
        gm2.enter_room()
        self.assertEqual(gm2.battle.monster.hp, hp)
        self.assertEqual(gm2.battle.monster.spec.max_hp, tower.monster_for(1).max_hp)

    def test_tower_needs_level(self):
        gm = self.gm()
        self.assertEqual({s.key: s for s in gm.dungeons()}["tower"].unavailable, "Requires level 3")
        with self.assertRaises(ValueError):
            gm.select_dungeon("tower")

    def test_owned_trophy_shows_in_shop_only_after_found(self):
        gm = self.gm(self.strong())
        self.assertNotIn("tower_blade", [e.item.key for e in gm.shop()])
        gm.inventory.give("tower_blade")
        entry = [e for e in gm.shop() if e.item.key == "tower_blade"][0]
        self.assertTrue(entry.owned)
        self.assertEqual(entry.problem or "Already owned", "Already owned")
        with self.assertRaises(ValueError):
            gm.buy("tower_blade")


class CompanionTests(Base):
    def test_companions_are_expensive_and_gated(self):
        comps = [i for i in ITEMS.values() if i.slot == COMPANION]
        self.assertGreaterEqual(len(comps), 5)
        self.assertGreaterEqual(min(c.price for c in comps), 900)
        weapons = [i.price for i in ITEMS.values() if i.slot == "weapon" and i.shop]
        self.assertGreater(max(c.price for c in comps), sorted(weapons)[2])
        self.assertEqual(sorted(c.level for c in comps), [c.level for c in sorted(comps, key=lambda c: c.price)])

    def test_only_one_companion_and_swap(self):
        gm = self.gm(self.strong(coins=5000))
        gm.buy("pixie"); gm.buy("hawk")
        self.assertEqual(gm.inventory.equipped["companion"], "pixie")
        gm.equip("hawk")
        self.assertEqual(gm.inventory.equipped["companion"], "hawk")
        self.assertEqual(gm.player.coins, 5000 - 900 - 1500)

    def test_pixie_heals_hawk_hits_harder(self):
        base = self.gm(self.strong(), seed=5)
        pix = self.gm(self.strong(coins=1000), seed=5); pix.buy("pixie")
        hawk = self.gm(self.strong(coins=2000), seed=5); hawk.buy("hawk")
        for g in (base, pix, hawk):
            g.select_dungeon("cellar"); g.enter_room(); g.next_question()
        base.player.hp = pix.player.hp = 100; hawk.player.hp = 100
        rb = base.answer(base.battle.question.answer)
        rp = pix.answer(pix.battle.question.answer)
        rh = hawk.answer(hawk.battle.question.answer)
        self.assertEqual(base.player.hp, 100)
        self.assertEqual(pix.player.hp, 103)
        self.assertIn("Pixie heals", rp.message)
        self.assertGreaterEqual(rh.damage_dealt, rb.damage_dealt)
        self.assertGreater(hawk.stats["xp_earned"] + hawk.battle.monster.max_hp - hawk.battle.monster.hp, 0)

    def test_hawk_adds_flat_damage(self):
        rng = random.Random(3)
        sel = VocabularySelector(deck(), rng=rng)
        a = Battle(Player(), Monster.spawn(config.MONSTERS["boss"]), sel, random.Random(9))
        b = Battle(Player(), Monster.spawn(config.MONSTERS["boss"]), sel, random.Random(9))
        b.bonus_damage = 5
        a.next_question(); b.next_question()
        self.assertEqual(b.submit(b.question.answer).damage_dealt - a.submit(a.question.answer).damage_dealt, 5)

    def test_shadow_cat_dodges(self):
        sel = VocabularySelector(deck(), rng=random.Random(1))
        b = Battle(Player(), Monster.spawn(config.MONSTERS["boss"]), sel, random.Random(1))
        b.dodge_pct = 100; b.companion = "Shadow Cat"
        b.next_question()
        r = b.submit("zzz")
        self.assertEqual(r.damage_taken, 0)
        self.assertIn("dodge", r.message)

    def test_turtle_starts_every_fight_with_a_ward(self):
        gm = self.gm(self.strong(coins=3000))
        gm.buy("stone_turtle")
        gm.select_dungeon("cellar"); gm.enter_room()
        self.assertTrue(gm.battle.ward)
        hp = gm.player.hp
        gm.next_question(); gm.answer("zzz")
        self.assertEqual(gm.player.hp, hp)

    def test_owl_percentages_stack_with_charm(self):
        gm = self.gm(self.strong(coins=5000))
        gm.buy("owl"); gm.buy("sages_ring")
        self.assertEqual(gm.inventory.totals().xp_pct, 40)
        self.assertEqual(gm.inventory.totals().companion, "Wise Owl")

    def test_baby_dragon_is_the_top_end(self):
        self.assertEqual(max((i for i in ITEMS.values() if i.slot == COMPANION), key=lambda i: i.price).key,
                         "baby_dragon")


class ReviewTests(Base):
    def test_unavailable_without_missed_words(self):
        gm = self.gm()
        st = {s.key: s for s in gm.dungeons()}["review"]
        self.assertEqual(st.unavailable, "No missed words to review")
        with self.assertRaises(ValueError):
            gm.select_dungeon("review")

    def test_only_missed_words_are_asked_and_cleared(self):
        gm = self.gm({"missed": {"p1": 0, "p2": 0, "dom": 1}, "player": {"level": 5}})
        gm.select_dungeon("review")
        seen, asked = set(), 0
        while asked < 40 and gm.current_room() is not None and gm.stats["words_cleared"] < 1:
            room = gm.current_room()
            if not room.is_fight:
                gm.enter_room()
                continue
            gm.enter_room()
            while gm.battle.state == ACTIVE and asked < 40 and gm.stats["words_cleared"] < 1:
                q = gm.next_question()
                asked += 1
                seen.add(deck().words[q.word_id].word)
                gm.answer(q.answer)
        self.assertTrue(seen <= {"p1", "p2", "dom"}, seen)
        self.assertGreaterEqual(gm.stats["words_cleared"], 1)
        self.assertEqual(gm.run["cleared"], gm.stats["words_cleared"])

    def test_clearing_needs_two_in_a_row(self):
        gm = self.gm({"missed": {"p1": 0}, "player": {"level": 5}})
        gm.select_dungeon("review"); gm.enter_room()
        gm.next_question()
        self.assertEqual(deck().words[gm.battle.question.word_id].word, "p1")
        gm.answer(gm.battle.question.answer)
        self.assertEqual(gm.missed_count, 1)
        gm.next_question(); gm.answer(gm.battle.question.answer)
        self.assertEqual(gm.missed_count, 0)

    def test_normal_dungeons_use_all_words_again(self):
        gm = self.gm({"missed": {"p1": 0}, "player": {"level": 5}})
        gm.select_dungeon("review")
        self.assertTrue(gm.selector.only_missed)
        gm.select_dungeon("cellar")
        self.assertFalse(gm.selector.only_missed)
        self.assertGreater(len(gm.selector.candidates()), 1)

    def test_run_can_continue_after_everything_is_cleared(self):
        gm = self.gm({"missed": {"p1": 1}, "player": {"level": 5}})
        gm.select_dungeon("review"); gm.enter_room()
        gm.next_question(); gm.answer(gm.battle.question.answer)   # may clear p1
        gm.leave()
        gm2 = self.gm()
        st = {s.key: s for s in gm2.dungeons()}["review"]
        if st.in_progress:
            self.assertIsNone(st.unavailable)

    def test_review_completion_rewards(self):
        gm = self.gm({"missed": {"p1": 0}, "player": {"level": 20, "max_hp": 500, "hp": 500}})
        gm.select_dungeon("review")
        last = None
        while gm.current_room() is not None:
            if gm.current_room().is_fight:
                gm.enter_room(); self.win(gm); last = gm.outcome
            else:
                last = gm.enter_room()
        self.assertTrue(last.dungeon_completed)
        self.assertEqual(gm.stats["dungeons_completed"], 1)


class SentenceBattleTests(Base):
    def test_cloze_source(self):
        src = ClozeSource(deck(), rng=random.Random(1))
        blanked, answer, english = src(0)
        self.assertIn("_____", blanked)
        self.assertEqual(answer, "pozwalają")
        self.assertIn("allowed", english)
        self.assertIsNone(src(2))           # card without a sentence

    def test_extra_examples_are_used(self):
        src = ClozeSource(deck(), {"dom": [("Kupili nowy dom.", "They bought a new house.")]},
                          random.Random(2))
        seen = {src(1)[2] for _ in range(40)}
        self.assertEqual(seen, {"My house is big.", "They bought a new house."})

    def test_library_monsters_ask_for_sentences(self):
        gm = self.gm({"player": {"level": 8, "max_hp": 200, "hp": 200}})
        gm.select_dungeon("library"); gm.enter_room()
        kinds = set()
        for _ in range(20):
            q = gm.next_question()
            if q is None:
                break
            kinds.add(q.kind)
            if q.is_cloze:
                self.assertIn("_____", q.prompt)
                self.assertTrue(q.reverse)
                self.assertTrue(q.gloss)
            gm.answer(q.answer)
            if gm.battle.state != ACTIVE:
                break
        self.assertIn("cloze", kinds)

    def test_cloze_answers_are_forgiving_and_wrong_shows_answer(self):
        rng = random.Random(1)
        sel = VocabularySelector(FlashcardDeck([deck().words[0]]), rng=rng)
        b = Battle(Player(), Monster.spawn(config.MONSTERS["ink_slime"]), sel, rng)
        b.cloze_source = ClozeSource(sel.deck, rng=rng)
        q = b.next_question()
        self.assertTrue(q.is_cloze)
        self.assertEqual(b.submit("POZWALAJA").exact, False)       # accents forgiven
        q = b.next_question()
        r = b.submit("nope")
        self.assertIn('The missing word was "pozwalają"', r.message)

    def test_hint_for_cloze_shows_translation_and_letters(self):
        rng = random.Random(1)
        sel = VocabularySelector(FlashcardDeck([deck().words[0]]), rng=rng)
        b = Battle(Player(), Monster.spawn(config.MONSTERS["ink_slime"]), sel, rng)
        b.cloze_source = ClozeSource(sel.deck, rng=rng)
        b.next_question()
        text = b.reveal(first=True, count=True)
        self.assertIn("Starts with “p”", text)
        self.assertIn("allowed", text)

    def test_falls_back_to_normal_questions_without_sentences(self):
        d = FlashcardDeck([Word("kot", "cat", level=1)])
        rng = random.Random(1)
        sel = VocabularySelector(d, rng=rng)
        b = Battle(Player(), Monster.spawn(config.MONSTERS["ink_slime"]), sel, rng)
        b.cloze_source = ClozeSource(d, rng=rng)
        q = b.next_question()
        self.assertEqual((q.kind, q.prompt), ("word", "kot"))

    def test_only_cloze_monsters_ask_sentences(self):
        sel = VocabularySelector(deck(), rng=random.Random(1))
        b = Battle(Player(), Monster.spawn(config.MONSTERS["slime"]), sel, random.Random(1))
        b.cloze_source = ClozeSource(deck())
        for _ in range(10):
            self.assertEqual(b.next_question().kind, "word")
            b.submit("zzz")
            if b.state != ACTIVE:
                break

    def test_loads_examples_json_next_to_save(self):
        (Path(self.tmp.name) / "examples.json").write_text(
            json.dumps({"dom": [{"pl": "Widzę duży dom.", "en": "I see a big house."}]}), encoding="utf-8")
        gm = self.gm()
        self.assertIn("dom", gm.cloze.examples)


if __name__ == "__main__":
    unittest.main()
