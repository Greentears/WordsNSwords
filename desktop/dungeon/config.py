"""All balance numbers and monster stats in one place (no game logic here).

Change a value here to rebalance the game; nothing else needs to be edited.
"""
from __future__ import annotations

from dataclasses import dataclass

# --- Player -----------------------------------------------------------------
DEFAULT_PLAYER_NAME = "Adventurer"
BASE_MAX_HP = 30
LEVEL_HP_GAIN = 10          # extra max HP per level
LEVEL_UP_HEAL_FRACTION = 1.0  # 1.0 = full heal on level-up
BASE_PLAYER_DAMAGE = 10
PLAYER_DAMAGE_PER_LEVEL = 2
DAMAGE_SPREAD = 0.15        # +-15 % random variation on every hit


def xp_to_next(level: int) -> int:
    """XP needed to go from `level` to `level + 1`."""
    return 150 + 100 * (max(1, level) - 1)


# --- Combat -----------------------------------------------------------------
# A monster never hits for more than this share of the player's max HP, so a
# couple of mistakes can't wipe you out: the game is about learning.
MAX_HIT_FRACTION = 0.30
SKIP_DAMAGE_FACTOR = 0.5    # skipping: the monster hits half as hard, no XP

# --- Vocabulary selection ---------------------------------------------------
# Higher weight = picked more often. None = a card that was never answered.
LEVEL_WEIGHTS: dict[int | None, float] = {
    1: 4.0,   # Learning: high priority
    2: 3.0,   # Almost there: normal
    0: 2.0,   # To verify: lower priority
    3: 1.0,   # Known: occasional
    None: 2.0,  # New cards (never studied); set to 0 to leave them out
}
# Bosses are about learning: mostly Learning and Almost there words, now and then a
# "To verify" word. They never ask new or known words (unless no other card exists).
BOSS_LEVEL_WEIGHTS: dict[int | None, float] = {
    1: 5.0,   # Learning
    2: 4.0,   # Almost there
    0: 1.5,   # To verify: now and then
}
MISSED_WEIGHT_BONUS = 2.0   # words missed in the dungeon come back more often
RECENT_WINDOW = 10          # a word isn't repeated within this many questions
MISSED_CLEAR_STREAK = 2     # correct answers in a row that clear a missed word

# --- Review Guru ------------------------------------------------------------
# The review fight is one monster whose HP is sized to about this many correct answers:
# as many as you have missed words, but at least MIN and at most MAX.
REVIEW_MIN_WORDS = 5
REVIEW_MAX_WORDS = 10

# --- Rewards ----------------------------------------------------------------
ROOM_CLEAR_COINS = 5
DUNGEON_COMPLETE_XP = 100    # defaults; a dungeon can set its own
DUNGEON_COMPLETE_COINS = 50


# --- Monster abilities ------------------------------------------------------
ENRAGE_HP_FRACTION = 0.5    # enraged monsters hit harder below this share of their HP
ENRAGE_FACTOR = 1.5
COMBO_STEP = 0.3            # extra damage per wrong answer in a row ...
COMBO_MAX_STACKS = 3        # ... up to this many
POISON_TURNS = 3            # answers after a poisoned hit that cost HP ...
POISON_MIN_HP = 1           # ... but poison never kills: it leaves at least this much
CURSE_HEAL_FACTOR = 0.5     # healing while cursed
LIFESTEAL_FRACTION = 0.5    # share of the damage dealt that the monster heals
PHOENIX_REVIVE_FRACTION = 0.3

# --- Shop -------------------------------------------------------------------
SELL_FRACTION = 0.6   # share of an item's price you get when selling it
MAX_ITEM_STACK = 99


# --- Monsters ---------------------------------------------------------------
@dataclass(frozen=True)
class MonsterSpec:
    key: str
    name: str
    max_hp: int
    damage: int
    xp: int
    coins: int
    boss: bool = False
    # abilities (all optional)
    reverse_chance: float = 0.0  # chance that a question is English -> Polish
    armor: int = 0               # flat damage taken off every hit you deal
    regen: int = 0               # HP it heals each time you get a word wrong
    enrage: bool = False         # hits harder when below half HP
    lifesteal: bool = False      # heals when it hurts you
    combo: bool = False          # hits harder after several wrong answers in a row
    time_limit: int = 0          # seconds per question (0 = no limit)
    cloze_chance: float = 0.0    # chance of a fill-in-the-blank sentence question
    # abilities that counter hero stats and gear
    unavoidable: bool = False    # its hits can't be dodged (a ward still absorbs them)
    pierce: bool = False         # ignores your armor's damage reduction
    percent_damage: float = 0.0  # extra damage per hit as a share of your max HP
    poison: int = 0              # HP lost after each of the next POISON_TURNS answers
    curse: bool = False          # healing is halved during the fight
    silence: bool = False        # no items during the fight
    streak: int = 0              # only hurt by the Nth correct answer in a row (and later ones)
    thief: int = 0               # coins stolen per mistake (given back when you win)

    @property
    def abilities(self) -> list[str]:
        return self.abilities_for("Polish")

    def abilities_for(self, language: str) -> list[str]:
        """The ability texts, naming the language the player is learning."""
        out = []
        if self.reverse_chance:
            out.append(f"Sometimes asks for the {language} word" if self.reverse_chance < 0.5
                       else f"Often asks for the {language} word")
        if self.armor:
            out.append(f"Armored: your hits do {self.armor} less")
        if self.regen:
            out.append(f"Regenerates {self.regen} HP when you err")
        if self.enrage:
            out.append("Enrages below half HP")
        if self.lifesteal:
            out.append("Heals when it hits you")
        if self.combo:
            out.append("Hits harder after repeated mistakes")
        if self.time_limit:
            out.append(f"Impatient: {self.time_limit}s per word")
        if self.cloze_chance:
            out.append("Speaks in sentences: fill in the blank")
        if self.unavoidable:
            out.append("Unavoidable: its hits can't be dodged")
        if self.pierce:
            out.append("Piercing: ignores your damage reduction")
        if self.percent_damage:
            out.append(f"Crushing: hits for {round(self.percent_damage * 100)}% of your max HP extra")
        if self.poison:
            out.append(f"Poison: {self.poison} HP after each of the next {POISON_TURNS} answers")
        if self.curse:
            out.append("Curse: your healing is halved")
        if self.silence:
            out.append("Silence: no items in this fight")
        if self.streak:
            out.append(f"Shielded: only {self.streak} correct answers in a row break through")
        if self.thief:
            out.append(f"Thief: steals {self.thief} coins per mistake (returned if you win)")
        return out


MONSTERS: dict[str, MonsterSpec] = {
    spec.key: spec
    for spec in (
        # The Cellar of Words
        MonsterSpec("book_mimic", "Book Mimic", max_hp=20, damage=3, xp=10, coins=3),
        MonsterSpec("ink_raven", "Ink Raven", max_hp=35, damage=5, xp=20, coins=6),
        MonsterSpec("quill_stalker", "Quill Stalker", max_hp=50, damage=7, xp=30, coins=10,
                    reverse_chance=0.25),
        MonsterSpec("forgotten_scribe", "Forgotten Scribe", max_hp=70, damage=9, xp=50, coins=18,
                    reverse_chance=0.4, armor=2),
        MonsterSpec("dust_moth", "Dust Moth", max_hp=150, damage=12, xp=120, coins=60, boss=True,
                    reverse_chance=0.4, enrage=True),
        # The Whispering Forest
        MonsterSpec("bat", "Vampire Bat", max_hp=40, damage=6, xp=25, coins=10,
                    reverse_chance=0.2, lifesteal=True),
        MonsterSpec("wolf", "Dire Wolf", max_hp=60, damage=8, xp=35, coins=14,
                    reverse_chance=0.3, combo=True),
        MonsterSpec("treant", "Treant", max_hp=90, damage=9, xp=55, coins=25,
                    reverse_chance=0.3, armor=2, regen=6),
        MonsterSpec("witch", "Hedge Witch", max_hp=75, damage=11, xp=60, coins=30,
                    reverse_chance=0.5, time_limit=25, curse=True),
        MonsterSpec("guardian", "Forest Guardian", max_hp=210, damage=13, xp=200, coins=100,
                    boss=True, reverse_chance=0.5, armor=1, regen=5, enrage=True),
        # The Frozen Citadel
        MonsterSpec("golem", "Ice Golem", max_hp=120, damage=12, xp=70, coins=35,
                    reverse_chance=0.4, armor=4, streak=2),
        MonsterSpec("wraith", "Frost Wraith", max_hp=95, damage=13, xp=80, coins=40,
                    reverse_chance=0.5, lifesteal=True, time_limit=20, unavoidable=True),
        MonsterSpec("warlord", "Warlord", max_hp=160, damage=15, xp=110, coins=55,
                    reverse_chance=0.6, enrage=True, combo=True, pierce=True),
        MonsterSpec("dragon", "Elder Dragon", max_hp=320, damage=17, xp=300, coins=160,
                    boss=True, reverse_chance=0.6, armor=2, regen=6, enrage=True,
                    time_limit=30, percent_damage=0.08),
        # The Review Guru (its HP is set when the fight starts, see GameManager._review_hp)
        MonsterSpec("review_guru", "Review Guru", max_hp=100, damage=6, xp=100, coins=55,
                    reverse_chance=0.3),
        # The Library of Sentences (fill-in-the-blank)
        MonsterSpec("ink_slime", "Ink Slime", max_hp=60, damage=7, xp=40, coins=14,
                    cloze_chance=1.0),
        MonsterSpec("paper_goblin", "Paper Goblin", max_hp=80, damage=9, xp=55, coins=20,
                    cloze_chance=1.0, thief=8),
        MonsterSpec("page_wraith", "Page Wraith", max_hp=100, damage=11, xp=70, coins=28,
                    cloze_chance=0.8, reverse_chance=0.2, lifesteal=True, poison=3),
        MonsterSpec("tome_knight", "Tome Knight", max_hp=130, damage=13, xp=90, coins=36,
                    cloze_chance=0.8, reverse_chance=0.2, armor=3, silence=True),
        MonsterSpec("librarian", "Grand Librarian", max_hp=270, damage=15, xp=240, coins=130,
                    boss=True, cloze_chance=0.8, reverse_chance=0.2, regen=5, enrage=True,
                    time_limit=35, curse=True, silence=True),
        # The Sunken Cathedral
        MonsterSpec("drowned_acolyte", "Drowned Acolyte", max_hp=140, damage=14, xp=90, coins=45,
                    reverse_chance=0.5, thief=10),
        MonsterSpec("barnacle_crawler", "Barnacle Crawler", max_hp=170, damage=14, xp=100, coins=50,
                    reverse_chance=0.4, armor=4, regen=5, streak=2),
        MonsterSpec("siren", "Siren", max_hp=165, damage=15, xp=120, coins=60,
                    reverse_chance=0.6, lifesteal=True, silence=True),
        MonsterSpec("drowned_knight", "Drowned Knight", max_hp=200, damage=18, xp=150, coins=75,
                    reverse_chance=0.6, armor=3, combo=True, pierce=True),
        MonsterSpec("abyssal_bishop", "Abyssal Bishop", max_hp=400, damage=20, xp=400, coins=220,
                    boss=True, reverse_chance=0.6, cloze_chance=0.4, armor=2, regen=6, enrage=True,
                    time_limit=30, percent_damage=0.08, curse=True),
    )
}
