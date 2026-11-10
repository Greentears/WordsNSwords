import unittest

from dungeon import config
from dungeon.dungeons import DUNGEONS
from dungeon.sprites import SIZE, SPRITE_KEYS, sprite_pixels, sprite_rows


class SpriteTests(unittest.TestCase):
    def test_every_sprite_is_square(self):
        for key in SPRITE_KEYS:
            rows = sprite_rows(key)
            self.assertEqual(len(rows), SIZE, key)
            for row in rows:
                self.assertEqual(len(row), SIZE, key)

    def test_every_pixel_has_a_colour(self):
        for key in SPRITE_KEYS:
            pixels = sprite_pixels(key)
            self.assertEqual((len(pixels), len(pixels[0])), (SIZE, SIZE), key)
            self.assertTrue(any(c for row in pixels for c in row), key)
            for row in pixels:
                for c in row:
                    self.assertTrue(c is None or (c.startswith("#") and len(c) == 7), key)

    def test_all_game_entities_have_sprites(self):
        from art import art_file
        # a monster needs a drawing or a picture (assets/art/monsters)
        drawn = lambda key: key in SPRITE_KEYS or art_file("monsters", key)
        self.assertTrue({"hero", "treasure", "rest"} <= set(SPRITE_KEYS))
        for key in config.MONSTERS:
            self.assertTrue(drawn(key), key)
        for d in DUNGEONS.values():
            for r in d.rooms:
                if r.is_fight:
                    self.assertTrue(drawn(r.monster), r.monster)


if __name__ == "__main__":
    unittest.main()
