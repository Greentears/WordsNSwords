import json
import tempfile
import unittest
from pathlib import Path

import art
from dungeon import config
from dungeon.dungeons import DUNGEONS


class ArtTests(unittest.TestCase):
    def test_hero_choice_is_remembered_and_final(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "sub" / "hero.json"
            self.assertIsNone(art.load_hero(path))
            art.save_hero(path, "f")
            self.assertEqual(art.load_hero(path), "f")
            art.save_hero(path, "m")                 # a second choice is ignored
            self.assertEqual(art.load_hero(path), "f")
            with self.assertRaises(ValueError):
                art.save_hero(Path(d) / "x.json", "z")

    def test_damaged_choice_file_means_no_choice(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "hero.json"
            for text in ("", "nope", "[]", json.dumps({"hero": "zebra"})):
                path.write_text(text)
                self.assertIsNone(art.load_hero(path))

    def test_hero_looks(self):
        for g in art.HEROES:
            for weapon in (False, True):
                for armor in (False, True):
                    self.assertTrue(art.hero_file(g, weapon, armor), (g, weapon, armor))

    def test_every_monster_has_a_picture_or_drawing(self):
        from dungeon.sprites import SPRITE_KEYS
        for key in config.MONSTERS:
            self.assertTrue(key in SPRITE_KEYS or art.art_file("monsters", key), key)

    def test_cathedral(self):
        d = DUNGEONS["cathedral"]
        self.assertTrue(d.rooms[-1].monster == "abyssal_bishop")
        for r in d.rooms:
            if r.is_fight:
                self.assertIn(r.monster, config.MONSTERS)
                self.assertTrue(art.art_file("monsters", r.monster), r.monster)


if __name__ == "__main__":
    unittest.main()


class SceneTests(unittest.TestCase):
    def test_rest_and_treasure_pictures_follow_the_setting(self):
        for kind in ("rest", "treasure"):
            outdoors = art.scene_file(kind, "forest")
            indoors = art.scene_file(kind, "library")
            self.assertTrue(outdoors and indoors)
            self.assertIn("outdoor", outdoors.name)
            self.assertIn("indoor", indoors.name)
            self.assertEqual(art.scene_file(kind, "citadel"), outdoors)
            self.assertEqual(art.scene_file(kind, "tower"), indoors)
