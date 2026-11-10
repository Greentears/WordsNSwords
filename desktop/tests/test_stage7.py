import json
FIXTURES = __import__("pathlib").Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "pl-en"
import random
import tempfile
import unittest
from pathlib import Path

from dungeon import config
from dungeon.items import ITEMS
from dungeon.manager import GameManager
from flashcards import LEVEL_NAMES, FlashcardDeck, Word, blank_sentence

ROOT = Path(__file__).resolve().parent.parent


def deck():
    return FlashcardDeck([Word(f"p{i}", f"en{i}", level=1) for i in range(12)])


class SellTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "p.json"

    def tearDown(self):
        self.tmp.cleanup()

    def gm(self, coins=2000, level=10):
        self.path.write_text(json.dumps({"player": {"level": level, "coins": coins,
                                                    "max_hp": 100, "hp": 100}}))
        return GameManager(deck(), self.path, random.Random(1))

    def test_sell_fraction_is_sixty_percent(self):
        self.assertEqual(config.SELL_FRACTION, 0.6)
        gm = self.gm()
        gm.buy("steel_blade")
        before = gm.player.coins
        gm.sell("steel_blade")
        self.assertEqual(gm.player.coins - before, int(ITEMS["steel_blade"].price * 0.6))

    def test_selling_equipment_unequips_and_updates_stats(self):
        gm = self.gm()
        gm.buy("chainmail")
        self.assertGreater(gm.player.gear_reduction, 0)
        gm.sell("chainmail")
        self.assertFalse(gm.inventory.has("chainmail"))
        self.assertEqual((gm.player.gear_reduction, gm.player.gear_hp), (0, 0))
        self.assertEqual(gm.stats["items_sold"], 1)
        self.assertEqual(GameManager(deck(), self.path).inventory.owned, set())

    def test_can_buy_back_after_selling(self):
        gm = self.gm()
        gm.buy("chainmail"); gm.sell("chainmail"); gm.buy("chainmail")
        self.assertTrue(gm.inventory.has("chainmail"))

    def test_consumables_sold_one_at_a_time(self):
        gm = self.gm()
        gm.buy("small_potion"); gm.buy("small_potion")
        entry = [e for e in gm.sellable() if e.item.key == "small_potion"][0]
        self.assertEqual(entry.count, 2)
        gm.sell("small_potion")
        self.assertEqual(gm.inventory.count("small_potion"), 1)

    def test_cannot_sell_what_you_do_not_have(self):
        gm = self.gm()
        with self.assertRaises(ValueError):
            gm.sell("small_potion")
        with self.assertRaises(ValueError):
            gm.sell("chainmail")
        self.assertEqual(gm.sellable(), [])

    def test_buy_then_sell_never_profits(self):
        gm = self.gm()
        for key, item in ITEMS.items():
            if item.shop and item.level <= 10:
                self.assertLess(gm.inventory.sell_value(item), item.price)


class RenameAndDataTests(unittest.TestCase):
    def test_level_zero_renamed(self):
        self.assertIn("To verify", LEVEL_NAMES.values())
        self.assertNotIn("To review", LEVEL_NAMES.values())

    def test_new_words_present_and_in_nominative(self):
        words = {c["word"]: c for c in json.load(open(FIXTURES / "words.json", encoding="utf8"))}
        for w in ("płaszcz", "wymiotować", "zasada", "kierunek", "zmiana", "kostka",
                  "wkurzony", "wyższy koszt leczenia", "zamieszkać na stałe"):
            self.assertIn(w, words)
        for w in ("zasad", "kierunku", "zmiany", "kostki", "wkurzeni", "wymiotuję"):
            self.assertNotIn(w, words)
        self.assertEqual(len(words), len({c for c in words}))

    def test_table_entries_match_cards_and_examples_exist(self):
        words = {c["word"] for c in json.load(open(FIXTURES / "words.json", encoding="utf8"))}
        for name, key in (("nouns.json", "card"), ("verbs.json", "card"), ("adjectives.json", "card")):
            for e in json.load(open(FIXTURES / name, encoding="utf8")):
                self.assertIn(e[key], words, (name, e[key]))
        examples = json.load(open(FIXTURES / "examples.json", encoding="utf8"))
        for w in examples:
            self.assertIn(w, words)
        for w in ("płaszcz", "chronić", "możliwość"):
            self.assertEqual(len(examples[w]), 2)

    def test_new_cards_have_a_blankable_sentence(self):
        data = json.load(open(FIXTURES / "words.json", encoding="utf8"))
        for c in data[-26:]:
            if c["word"] == "wymiotować":
                continue          # needs the conjugation table, covered by the app
            w = Word(c["word"], c["translation"], c["sentence"], c["sentence_translation"])
            self.assertTrue(blank_sentence(w), c["word"])


if __name__ == "__main__":
    unittest.main()


class BossAndGearTests(unittest.TestCase):
    def test_boss_asks_harder_words_than_normal_monsters(self):
        from dungeon import config
        from dungeon.battle import Battle
        from dungeon.models import Monster, Player
        from dungeon.selector import VocabularySelector
        words = [Word(f"a{i}", f"x{i}", level=0) for i in range(30)] + \
                [Word(f"b{i}", f"y{i}", level=3) for i in range(30)]

        def share_hard(spec_key):
            rng = random.Random(3)
            sel = VocabularySelector(FlashcardDeck(words), rng=rng)
            b = Battle(Player(), Monster.spawn(config.MONSTERS[spec_key]), sel, rng)
            hard = 0
            for _ in range(400):
                q = b.next_question()
                hard += q.answer.startswith("x") or q.prompt.startswith("x")
                sel._recent.clear()
            return hard / 400
        self.assertGreater(share_hard("dust_moth"), share_hard("book_mimic") + 0.2)

    def test_bosses_have_more_hp(self):
        from dungeon import config
        self.assertGreaterEqual(config.MONSTERS["dust_moth"].max_hp, 150)

    def test_no_permanent_item_reveals_letters(self):
        for item in ITEMS.values():
            self.assertFalse(hasattr(item, "monocle"))
        self.assertNotIn("scholars_monocle", ITEMS)

    def test_old_monocle_owner_is_refunded(self):
        tmp = tempfile.TemporaryDirectory()
        path = Path(tmp.name) / "p.json"
        path.write_text(json.dumps({"player": {"level": 5, "coins": 10, "max_hp": 70, "hp": 70},
                                    "inventory": {"owned": ["scholars_monocle", "iron_sword"],
                                                  "equipped": {"charm": "scholars_monocle"}}}))
        gm = GameManager(deck(), path, random.Random(1))
        self.assertEqual(gm.player.coins, 270)
        self.assertEqual(gm.inventory.owned, {"iron_sword"})
        gm.save()
        self.assertEqual(GameManager(deck(), path).player.coins, 270)
        tmp.cleanup()


class CompanionSpriteTests(unittest.TestCase):
    def test_every_companion_has_a_sprite(self):
        from dungeon.items import COMPANION
        from dungeon.sprites import SPRITE_KEYS
        for key, item in ITEMS.items():
            if item.slot == COMPANION:
                self.assertIn(key, SPRITE_KEYS)


class AdaptiveHeroTests(unittest.TestCase):
    def test_every_gear_combination_draws(self):
        from dungeon.items import ARMOR, CHARM, WEAPON
        from dungeon.sprites import SIZE, hero_pixels
        weapons = [None] + [k for k, i in ITEMS.items() if i.slot == WEAPON]
        armors = [None] + [k for k, i in ITEMS.items() if i.slot == ARMOR]
        charms = [None] + [k for k, i in ITEMS.items() if i.slot == CHARM]
        for w in weapons:
            for a in armors:
                px = hero_pixels(w, a, charms[(len(w or "") + len(a or "")) % len(charms)])
                self.assertEqual((len(px), len(px[0])), (SIZE, SIZE))
                self.assertTrue(any(c for row in px for c in row))

    def test_gear_changes_the_picture(self):
        from dungeon.sprites import hero_pixels
        self.assertNotEqual(hero_pixels(), hero_pixels("iron_sword"))
        self.assertNotEqual(hero_pixels(None, "chainmail"), hero_pixels(None, "plate_armor"))
        self.assertNotEqual(hero_pixels("iron_sword", "plate_armor"),
                            hero_pixels("iron_sword", "plate_armor", "lucky_clover"))

    def test_manager_reports_the_look(self):
        tmp = tempfile.TemporaryDirectory()
        path = Path(tmp.name) / "p.json"
        path.write_text(json.dumps({"player": {"level": 9, "coins": 900, "max_hp": 100, "hp": 100}}))
        gm = GameManager(deck(), path, random.Random(1))
        self.assertEqual(gm.hero_look(), (None, None, None))
        gm.buy("iron_sword"); gm.buy("chainmail")
        self.assertEqual(gm.hero_look(), ("iron_sword", "chainmail", None))
        tmp.cleanup()


class ReviewAndAnswerTests(unittest.TestCase):
    def test_bracketed_part_may_be_typed_or_left_out(self):
        from dungeon.answers import check
        for text in ("zmierzać (do)", "zmierzać do", "zmierzać", "zmierzac do"):
            self.assertTrue(check(text, "zmierzać (do)", True)[0], text)
        self.assertFalse(check("zmierzać na", "zmierzać (do)", True)[0])
        self.assertTrue(check("to lack of", "to lack (of)")[0])

    def test_wrong_answer_message_shows_what_you_typed(self):
        import random as r
        from dungeon.battle import Battle
        from dungeon.models import Monster, Player
        from dungeon.selector import VocabularySelector
        from dungeon import config
        rng = r.Random(2)
        b = Battle(Player(), Monster.spawn(config.MONSTERS["book_mimic"]),
                   VocabularySelector(deck(), rng=rng), rng)
        b.next_question()
        self.assertIn('You answered "blah blah".', b.submit("blah blah").message)
        b.next_question()
        self.assertNotIn("You answered", b.skip().message)

    def _review_gm(self, missed, level=5, **extra):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / "p.json"
        player = {"level": level, "coins": 0, "max_hp": 70, "hp": 70}
        path.write_text(json.dumps({"player": player, "missed": missed, **extra}))
        return GameManager(deck(), path, random.Random(1))

    def test_review_guru_is_one_replayable_monster_that_pays_less(self):
        from dungeon.dungeons import REVIEW
        self.assertEqual(len(REVIEW.rooms), 1)
        self.assertEqual(REVIEW.rooms[0].monster, "review_guru")
        self.assertLess(REVIEW.reward_scale, 1.0)
        gm = self._review_gm({"p1": 0, "p2": 0},
                             dungeons={"review": {"room": 1, "completed": True, "times": 1}})
        self.assertIsNone(gm.unavailable_reason("review"))
        gm.select_dungeon("review")
        self.assertEqual(gm.room_index, 0)          # a finished review starts again
        gm.enter_room()
        self.assertEqual(gm.battle.monster.name, "Review Guru")

    def test_guru_hp_is_five_to_ten_hits_depending_on_missed_words(self):
        for missed, expected_hits in ((2, 5), (7, 7), (30, 10)):
            gm = self._review_gm({f"w{i}": 0 for i in range(missed)})
            gm.select_dungeon("review"); gm.enter_room()
            self.assertEqual(gm.battle.monster.max_hp, gm.player.attack_power * expected_hits, missed)

    def test_failed_words_are_listed_once_with_their_meaning(self):
        gm = self._review_gm({"p1": 0, "p2": 0})
        gm.select_dungeon("review"); gm.enter_room()
        for _ in range(3):
            q = gm.next_question()
            word = deck().words[q.word_id].word
            gm.answer("zzz")
            gm.battle.player.hp = gm.battle.player.max_hp
        failed = dict(gm.review_failed_words)
        self.assertTrue(failed and set(failed) <= {w.word for w in deck().words})
        self.assertEqual(len(failed), len(gm.review_failed_words))
        self.assertTrue(all(failed[w] == next(x.translation for x in deck().words if x.word == w) for w in failed))
        gm.select_dungeon("review")    # leaving and coming back keeps the list while the fight is saved
        gm.leave(); gm.select_dungeon("review")

    def test_boss_questions_focus_on_learning_and_almost_there(self):
        from dungeon import config
        w = config.BOSS_LEVEL_WEIGHTS
        self.assertGreater(w[1], w[2]); self.assertGreater(w[2], w[0]); self.assertGreater(w[0], 0)
        self.assertNotIn(None, w); self.assertNotIn(3, w)     # no new and no known words

    def test_boss_falls_back_to_any_card_when_none_qualify(self):
        from dungeon.battle import Battle
        from dungeon.models import Monster, Player
        from dungeon.selector import VocabularySelector
        rng = random.Random(3)
        d = deck()
        for card in d.words:
            card.level = 3          # only known cards: nothing the boss wants
        b = Battle(Player(), Monster.spawn(config.MONSTERS["dust_moth"]), VocabularySelector(d, rng=rng), rng)
        self.assertIsNotNone(b.next_question())
