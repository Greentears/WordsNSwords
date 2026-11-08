# Python Flashcards

A small desktop vocabulary flashcard application built with Python and PySide6.

## Features

- Load vocabulary from JSON
- Large visual flashcards
- Reveal/hide translations
- Move cards between levels at any time (without having to reveal them first)
- Progress bar and session statistics
- Shuffle
- Restart
- Four learning levels per card: To verify → Learning → Almost there → Known (plus New for unanswered cards), saved in the JSON itself (`"level": 0-3`)
- Filter the deck by any level, or only *New* cards
- Quick set: 10 random cards from any level (To verify, Learning, Almost there, Known, New or all cards)
- The counters under the progress bar (All / To verify / Learning / Almost there / Known / New) are buttons: click one to show only that category
- Archived: a Known card can be archived (**5**, the Archive button or Card menu). Archived cards (`"level": 4`) are hidden everywhere – All, quizzes, quick sets, sentences – and only appear under Study → Show → Archived. Moving an archived card to any level (1–4) brings it back
- Type-the-answer quiz (Study → Quiz, **Ctrl+T**): choose which levels to include (default: To verify, Learning, Almost there), how many cards and the direction. A *Smart mix* option picks a bit of every level (about 45% Almost there, 35% Learning, 20% To verify; Known and New are left out). Failed words get a counter (`"fails"` in the JSON), shown on the card; **F** shows the failed words, worst first
- Fill-in-the-blank quiz (Study → Fill-in-the-blank quiz, **Ctrl+B**): the example sentence with the word missing; you type it in the right form. The English meaning of the missing word is shown in brackets next to the blank; the **Hint** button (Ctrl+H) shows the English sentence and the dictionary form. Same level choices and Smart mix as the typed quiz; wrong answers also count towards the fails counter. Cards whose word can't be found in their sentence are skipped
- Search box (top right, **Ctrl+F**): finds cards by word, translation or sentence (ignores case and Polish accents; archived cards included). Enter jumps back to the cards; clear the box to return to all cards
- Dark mode (View → Dark mode, **Ctrl+D**): remembered the next time you start the app
- Extra sentences (View → Show extra sentences, **Ctrl+Shift+S**) and grammar tables (View → Show grammar tables, **Ctrl+Shift+G**) can each be switched off; both choices are remembered. Switching the sentences off also keeps them out of the fill-in-the-blank quiz
- Verb tables: when you reveal a verb card, a small table shows ja / ty / on-ona-ono / my / wy / oni-one (present tense, or future for perfective verbs). The tables live in `verbs.json` next to `words.json` (`card`, `verbs` → `infinitive`, `aspect`, `forms`); add your own there
- Noun and numeral tables: revealing a noun card shows all seven cases (mianownik … wołacz) in singular and plural; numerals (dziesięć, dwanaście, dwadzieścia, dwieście) get one column. For a numeral use `"gender": "num"` and `null` for the plural. Cards use the nominative (mianownik) as the main form. The tables live in `nouns.json` next to `words.json` (`card`, `nouns` → `lemma`, `gender`, `singular`, `plural`: seven forms each, `null` = no such form)
- Adjective tables: revealing an adjective card shows seven cases x masculine / feminine / neuter / plural. They live in `adjectives.json` (`card`, `adjectives` → `lemma`, `forms` with `m`, `f`, `n`, `pl`: seven forms each). Adverbs and fixed phrases don't decline, so they have no table
- More examples: `examples.json` holds extra sentences per card (`"word": [{"pl": ..., "en": ...}]`). They are shown under the card on reveal, and the fill-in-the-blank quiz picks randomly between the card's sentence and its extra examples
- Sentence practice (Study → Sentence practice, **Ctrl+P**): new example sentences built from your words (mixing To verify / Learning / Almost there, plus a few helper words so they make sense). They live in `sentences.json` next to `words.json` (`pl`, `en`, `words`); add your own there. Reveal shows the translation and which of your cards were used
- Switch between Polish-first and English-first (Study → Show English first, **E**); the choice is remembered
- **Vocabulary Dungeon** (Dungeon → Enter the dungeon…, **Ctrl+G**): a small retro RPG in its own window. See [Vocabulary Dungeon](#vocabulary-dungeon) below
- Keyboard shortcuts
- Persistent overall statistics
- UTF-8 support for languages such as Polish

## JSON format

Your vocabulary file should be a JSON list:

```json
[
    {
        "word": "pies",
        "translation": "dog",
        "sentence": "Mój pies lubi biegać po parku.",
        "sentence_translation": "My dog likes to run in the park."
    },
    {
        "word": "kot",
        "translation": "cat"
    }
]
```

The `sentence` and `sentence_translation` fields are optional; when present they are shown when you reveal the card. You can use any language pair. For example, Polish → English, French → Polish, etc.

## Installation

Python 3.10+ is recommended.

Create a virtual environment:

### Windows

```powershell
python -m venv .venv
.venv\Scripts\activate
```

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run:

```bash
python main.py
```

## Easy launch on Windows

- Double-click `run.bat`: it creates the virtual environment and installs the
  dependencies on first run, then opens the app.
- For a real `Flashcards.exe`, double-click `build_exe.bat` once. The app appears in
  `dist\Flashcards\`. Keep the exe inside the WordsNSwords folder: it finds your words in `users\<name>\pl-en\` and saves your progress in `local\<name>\pl-en\` (not in git).

## Vocabulary Dungeon

Open it with **Dungeon → Enter the dungeon…** (**Ctrl+G**). You are the *Adventurer*. Pick a dungeon on the map screen;
some unlock with your level:

| Dungeon | Needs | What it is |
|---|---|---|
| The Cellar of Words | level 1 | 8 rooms, Dungeon Boss |
| The Endless Tower | level 3 | floor after floor, ever stronger; no end |
| The Whispering Forest | level 4 | 8 rooms, Forest Guardian |
| The Library of Sentences | level 6 | **sentence battles** (see below), Grand Librarian |
| The Frozen Citadel | level 8 | 9 rooms, Elder Dragon |
| The Review Dungeon | missed words | only the words you missed, replayable as often as you like (monsters 25% tougher, rewards 25% smaller); answer a missed word correctly twice in a row to clear it |

Story dungeons mix monster rooms with rest rooms (heal), treasure rooms and a boss, and can be replayed.

**The Endless Tower**: every floor is a fight, every 5th floor is a resting place, and **every 10th floor has a boss
that drops an item** (floor 10: Sword of the Tower, 20: Warden's Mail, 30: Scholar's Crown, then Stormcaller, Titan
Plate, Chrono Amulet; after that bundles of potions, bombs and scrolls). Trophies are far stronger than shop gear and
can't be bought. If you already own one it is sold for 60% of its price. Monsters grow stronger with every floor, enrage
from floor 20 and start asking sentence questions from floor 15. Your progress and best floor are kept.

**Sentence battles** (Library of Sentences, and deeper tower floors): the monster shows a Polish sentence with a
missing word (from your cards' example sentences and `examples.json`); you type the missing word in the right form.
The English meaning of the word is shown above; item hints reveal the sentence translation. Cards without a usable
sentence are asked as normal questions.

**How a fight works**

- A word appears; type its translation and press **Enter**. Correct → you hit the monster. Wrong → it hits you.
- Answers are forgiving: alternatives ("run / operated by" accepts *run*, *run by* or *operated by*), optional
  brackets, a missing "to", articles, little modifiers ("little corner / nook" accepts *corner*), missing Polish
  accents and a single typo in longer words all count. You may even type the whole card text with its slashes.
- Stronger monsters sometimes ask **English → Polish** instead, switching from question to question.
- **Skip** shows the answer, counts as wrong and the monster hits half as hard. After a mistake the message shows the
  original word and its translation. Hints only come from items (see the shop).
- **Monster abilities** are shown under the monster: armor (your hits do less), regeneration when you err, enrage
  below half HP, life steal, combos after repeated mistakes, and a **time limit** per word (a countdown appears).
- Win a fight for XP and coins; enough XP gives a level (more max HP and attack, full heal). If you are defeated you
  can retry the room with full HP against a fresh monster. **Esc** / *Back to map* leaves a fight; it is saved.

**Shop** (button on the map screen). Spend coins on:

- *One-time items*, used in fights from the item bar: Letter Scroll (first letter), Counting Rune (letter count),
  Oracle's Eye (both), Healing Potion, Elixir of Life, Fire Bomb / Lightning Rune / Meteor Scroll (direct damage),
  Ward Scroll (absorbs one hit), Passage Scroll (skip a word for free), Tome of Wisdom (double XP) and
  Golden Idol (double coins).
- *Equipment* (permanent, one weapon, one armor, one charm, one companion): swords (+attack), armor (+max HP, less damage taken) and
  charms (+coins, +XP, longer time limits, a Phoenix Feather that saves you once per
  fight). Better gear costs more and needs a higher level. Buy it once and switch freely in the shop.
- *Companions* (expensive, 900–4500 coins, one at a time): Pixie (heals after every correct answer), War Hawk (+5 damage),
  Wise Owl (+15% XP and coins), Shadow Cat (20% dodge), Stone Turtle (a free ward every fight) and Baby Dragon (+10 damage
  and healing). They appear as pixel sprites next to your hero in fights and in the inventory.

**Sell tab** (in the shop): switch from *Buy* to *Sell* to sell items for 60% of their price (`SELL_FRACTION` in
`dungeon/config.py`). One-time items go one at a time; equipment is sold (and unequipped), and you can buy it back.

**Inventory** (button on the map screen): your hero on the left, drawn with the gear he wears (a different look for every
weapon, armor and charm; shields and helmets come with the heavier armors), and a Path of Exile style doll on the right:
weapon on the left, companion above the armor, charm at the top right and a belt of slots for your one-time items.
Underneath: the gear you own but don't wear (with an Equip button). The fight screen shows the same hero.

**Bosses** take more questions to beat and favour the words you know least (To verify, Learning, New).

**Which words are asked**: all cards except archived ones, favouring words you are still learning. Words you miss come
back more often until you answer them correctly twice in a row; the map shows how many are waiting. The game **never
changes** a card's level or fail count and never writes to `words.json`.

**Saved progress** is `dungeon_progress.json` in your local folder (`local/<name>/pl-en/`) (player, coins, items, equipment, progress per
dungeon, best tower floor, statistics, missed words, current fight). It is written safely (temporary file + rename, with a `.bak` backup);
if it is damaged the backup is used, or the game starts fresh. Delete the file to restart the game from scratch.

**Tuning**: numbers (HP, damage, XP curve, monster stats and abilities, word weights) are in `dungeon/config.py`, the
shop catalogue in `dungeon/items.py`, dungeons in `dungeon/dungeons.py` (plain data: add one to add an adventure).
Set `None: 0` in `LEVEL_WEIGHTS` to leave never-answered (New) cards out.

**Tests**: `python -m unittest discover tests` (the game rules don't need PySide6).

## Keyboard shortcuts

| Key | Action |
|---|---|
| Space | Reveal / hide translation |
| ← | Previous card |
| → | Next card |
| S | Shuffle |
| R | Restart |
| 1 / 2 / 3 / 4 | Move card to To verify / Learning / Almost there / Known |
| Ctrl+1 … Ctrl+4 | Show only that level (W = to verify, K = known) |
| A / N | Show all / new cards |
| E | Switch English-first / Polish-first |
| Q | Quick set: 10 random cards to verify (other levels: Study → Quick set) |
| Ctrl+T | Type-the-answer quiz |
| Ctrl+G | Vocabulary Dungeon |
| F | Show words failed in a quiz |
| Ctrl+O | Open JSON |
| Ctrl+Q | Quit |

## Project structure

```text
flashcards/
├── main.py          # Application entry point
├── ui.py            # PySide6 main window
├── flashcards.py    # Deck logic (levels, filters, answer checking, fill-in-the-blank)
├── quiz.py          # Typed quiz and fill-in-the-blank dialogs
├── sentences.py     # Sentence practice
├── theme.py         # Light / dark styles
├── verbs.py nouns.py adjectives.py examples.py   # Tables and examples shown on reveal
├── progress.py      # Persistent statistics
├── dungeon_ui.py    # Vocabulary Dungeon window (PySide6)
├── dungeon/         # Dungeon game logic, no Qt: config, models, battle, answers, selector, items, inventory, rewards, manager, repository, sprites (+ sprites_draw: the shape-drawn creatures), tower, cloze
├── tests/           # Unit tests (python -m unittest discover tests)
├── dungeon_progress.json   # Created by the game on first play
├── (words live in ../users/<name>/pl-en/, progress in ../local/<name>/pl-en/)
├── verbs.json nouns.json adjectives.json         # Conjugation / declension tables
├── sentences.json examples.json                  # Practice sentences, extra examples per card
├── run.bat build_exe.bat requirements.txt
└── README.md
```

## Notes

Each card gets a `"level"` field (0 = To verify, 1 = Learning, 2 = Almost there, 3 = Known)
in your JSON file when you answer it, so progress survives closing the app. Cards without
the field are "new". Older files with `"known": true/false` are converted automatically
(true → Known, false → To verify).
Study → Show filters the deck by those marks. Other keys
in your JSON are preserved. Study → Reset saved progress removes all levels and fail counts.

Aggregate session statistics are stored in:

```text
~/.flashcards/progress.json
```


