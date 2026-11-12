"""Dungeon definitions (data only). Add a new Dungeon here to add a new adventure."""
from __future__ import annotations

from . import tower
from .models import BOSS, MONSTER, REST, TREASURE, Dungeon, Room

CELLAR = Dungeon(
    key="cellar",
    name="The Cellar of Words",
    description="Eight rooms under the old library. Something big guards the last one.",
    rooms=(
        Room(MONSTER, "Damp Corridor", monster="book_mimic"),
        Room(MONSTER, "Mossy Hall", monster="book_mimic"),
        Room(MONSTER, "Goblin Den", monster="ink_raven"),
        Room(REST, "Quiet Alcove", heal_fraction=0.5),
        Room(TREASURE, "Forgotten Chest", coins=20, xp=15),
        Room(MONSTER, "Bone Crypt", monster="quill_stalker"),
        Room(MONSTER, "Knight's Gate", monster="forgotten_scribe"),
        Room(BOSS, "Throne of Words", monster="dust_moth"),
    ),
)

FOREST = Dungeon(
    key="forest",
    name="The Whispering Forest",
    description="Bats, wolves and a witch who hates waiting. Monsters here may ask for the word in the language you are learning.",
    min_level=4,
    complete_xp=200,
    complete_coins=120,
    rooms=(
        Room(MONSTER, "Moonlit Path", monster="bat"),
        Room(MONSTER, "Hollow Oak", monster="wolf"),
        Room(REST, "Mushroom Glade", heal_fraction=0.4),
        Room(TREASURE, "Hunter's Cache", coins=60, xp=40),
        Room(MONSTER, "Thorn Maze", monster="treant"),
        Room(MONSTER, "Witch's Hut", monster="witch"),
        Room(REST, "Spring of Light", heal_fraction=0.6),
        Room(BOSS, "Heart of the Forest", monster="guardian"),
    ),
)

CITADEL = Dungeon(
    key="citadel",
    name="The Frozen Citadel",
    description="Armoured golems, draining wraiths and a dragon at the top. Bring potions.",
    min_level=8,
    complete_xp=300,
    complete_coins=250,
    rooms=(
        Room(MONSTER, "Frozen Gate", monster="golem"),
        Room(MONSTER, "Icy Stairs", monster="wraith"),
        Room(REST, "Warm Hearth", heal_fraction=0.4),
        Room(TREASURE, "Frozen Hoard", coins=150, xp=80),
        Room(MONSTER, "Hall of Frost", monster="golem"),
        Room(MONSTER, "Wraith Gallery", monster="wraith"),
        Room(REST, "Ember Pit", heal_fraction=0.5),
        Room(MONSTER, "Warlord's Court", monster="warlord"),
        Room(BOSS, "Dragon's Roost", monster="dragon"),
    ),
)

LIBRARY = Dungeon(
    key="library",
    name="The Library of Sentences",
    description="Sentence battles: the monsters speak in full sentences and you fill in the missing word.",
    min_level=6,
    complete_xp=250,
    complete_coins=200,
    rooms=(
        Room(MONSTER, "Reading Room", monster="ink_slime"),
        Room(MONSTER, "Paper Cellar", monster="paper_goblin"),
        Room(MONSTER, "Ink Pool", monster="ink_slime"),
        Room(REST, "Reading Nook", heal_fraction=0.5),
        Room(TREASURE, "Forbidden Shelf", coins=80, xp=50),
        Room(MONSTER, "Whispering Stacks", monster="page_wraith"),
        Room(MONSTER, "Hall of Tomes", monster="tome_knight"),
        Room(BOSS, "The Grand Archive", monster="librarian"),
    ),
)

CATHEDRAL = Dungeon(
    key="cathedral",
    name="The Sunken Cathedral",
    description="A drowned cathedral: sirens, knights and a bishop in the deep. "
                "Every monster here has nasty abilities: read them before you fight.",
    min_level=12,
    complete_xp=500,
    complete_coins=400,
    rooms=(
        Room(MONSTER, "Flooded Nave", monster="drowned_acolyte"),
        Room(MONSTER, "Barnacle Crypt", monster="barnacle_crawler"),
        Room(REST, "Dry Chapel", heal_fraction=0.4),
        Room(TREASURE, "Sunken Reliquary", coins=250, xp=120),
        Room(MONSTER, "Siren's Pool", monster="siren"),
        Room(MONSTER, "Drowned Cloister", monster="drowned_acolyte"),
        Room(REST, "Air Pocket", heal_fraction=0.5),
        Room(MONSTER, "Knights' Hall", monster="drowned_knight"),
        Room(BOSS, "The Drowned Altar", monster="abyssal_bishop"),
    ),
)

REVIEW = Dungeon(
    key="review",
    name="The Review Guru",
    description="One long fight against the Review Guru, who asks the words you missed. "
                "It lasts about as many words as you have missed (5 to 10). Answer a missed word "
                "correctly twice in a row to clear it. At the end you see every word you failed.",
    kind="review",
    complete_xp=0,           # the Guru's own reward is the whole payout: shown once
    complete_coins=0,
    reward_scale=0.75,       # replayable as often as you like, for a bit less
    rooms=(
        Room(MONSTER, "The Guru's Study", monster="review_guru"),
    ),
)

TOWER = Dungeon(
    key="tower",
    name="The Endless Tower",
    description="Floor after floor, ever stronger. A resting place every 5 floors, and a boss with "
                "a drop every 10.",
    min_level=3,
    kind="tower",
    rooms=(),
    room_factory=tower.floor_room,
)

# Order on the map screen.
DUNGEONS: dict[str, Dungeon] = {d.key: d for d in (CELLAR, FOREST, LIBRARY, CITADEL, CATHEDRAL, REVIEW, TOWER)}
