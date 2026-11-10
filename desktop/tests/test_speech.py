import unittest

from speech import language_code, spoken_text


class SpeechTests(unittest.TestCase):
    def test_brackets_are_not_read_out(self):
        self.assertEqual(spoken_text("pochodzić (z)"), "pochodzić z")
        self.assertEqual(spoken_text("  dobre / ładne   pachnie "), "dobre / ładne pachnie")
        self.assertEqual(spoken_text("()"), "")

    def test_language_comes_from_the_deck(self):
        self.assertEqual(language_code("pl-en"), "pl")
        self.assertEqual(language_code("fr-en"), "fr")
        self.assertEqual(language_code(None), "pl")


if __name__ == "__main__":
    unittest.main()
