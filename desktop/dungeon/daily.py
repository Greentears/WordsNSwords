"""The Daily Challenge: one short dungeon per day, the same for everybody.

The date decides everything (which monsters, in which order, today's twist), through a tiny random
generator that the phone version copies exactly, so both show the same challenge. How strong the monsters
are depends on the player's level when the day's run starts (the "tier": a Tower floor). One run a day;
finishing it on consecutive days builds a streak that adds to the reward.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import date, timedelta

from . import config, tower
from .models import BOSS, MONSTER, REST, Dungeon, Room

KEY = "daily"
MIN_LEVEL = 3
TIER_BONUS = 2              # the monsters stand for the Tower floor (level + this)
MAX_TIER = 80
STREAK_STEP = 0.10          # extra reward per streak day after the first ...
STREAK_MAX = 0.50           # ... up to this much

MASK = 0xFFFFFFFF
# (key, name, what it does)
TWISTS = (
    ("glass", "Glass cannons", "Monsters have 30% less HP but hit 35% harder."),
    ("iron", "Iron hides", "Every monster is armored: your hits do 2 less."),
    ("fury", "Fury", "Every monster enrages below half HP."),
    ("mirror", "Mirror day", "Monsters often ask for the foreign word."),
    ("sentences", "Sentence day", "Monsters often speak in sentences: fill in the blank."),
    ("feast", "Feast day", "Rewards are 50% bigger. The monsters are the usual ones."),
)
ROOM_NAMES = ("Torn Archive", "Whispering Stacks", "Ink-stained Hall", "Dusty Reading Room", "Forgotten Annex",
              "Candlelit Stair", "Cracked Lectern", "Paper Maze")
BOSS_NAMES = ("The Daily Guardian", "The Day's Warden", "The Keeper of Today")


def hash32(text: str) -> int:
    """FNV-1a over the UTF-8 bytes of `text`."""
    h = 2166136261
    for byte in text.encode("utf-8"):
        h = ((h ^ byte) * 16777619) & MASK
    return h


class Rng:
    """mulberry32: small, fast, and easy to copy exactly into TypeScript."""

    def __init__(self, seed: int):
        self.a = seed & MASK

    def next(self) -> float:
        self.a = (self.a + 0x6D2B79F5) & MASK
        t = self.a
        t = ((t ^ (t >> 15)) * (t | 1)) & MASK
        t ^= (t + (((t ^ (t >> 7)) * (t | 61)) & MASK)) & MASK
        return ((t ^ (t >> 14)) & MASK) / 4294967296

    def below(self, n: int) -> int:
        return int(self.next() * n)


def tier_for(level: int) -> int:
    return max(2, min(MAX_TIER, level + TIER_BONUS))


def yesterday(day: str) -> str:
    return (date.fromisoformat(day) - timedelta(days=1)).isoformat()


def streak_bonus(streak: int) -> float:
    """Extra share of the completion reward for a streak of this many days."""
    return min(STREAK_MAX, STREAK_STEP * max(0, streak - 1))


def twist_for(day: str) -> tuple[str, str, str]:
    return TWISTS[Rng(hash32("twist:" + day)).below(len(TWISTS))]


def build(day: str, tier: int) -> Dungeon:
    """Today's dungeon: fight, fight, rest, fight, fight, boss."""
    rng = Rng(hash32("rooms:" + day))
    twist = twist_for(day)[0]
    pool = tower.MONSTER_ORDER[: min(len(tower.MONSTER_ORDER), (tier - 1) // 2 + 3)]
    names = list(ROOM_NAMES)
    rooms = []
    fights = 0
    for slot in range(6):
        if slot == 2:
            rooms.append(Room(REST, "A Quiet Corner", heal_fraction=0.4))
            continue
        boss = slot == 5
        if boss:
            base = config.MONSTERS[tower.BOSS_ORDER[rng.below(min(len(tower.BOSS_ORDER), 1 + tier // 10))]]
        else:
            base = config.MONSTERS[pool[rng.below(len(pool))]]
        spec = tower.scale_monster(base, tier + fights + (2 if boss else 0), boss)
        spec = _twisted(spec, twist)
        title = BOSS_NAMES[rng.below(len(BOSS_NAMES))] if boss else names.pop(rng.below(len(names)))
        rooms.append(Room(BOSS if boss else MONSTER, title, monster=spec.key, spec=spec))
        fights += 1
    boss_spec = rooms[-1].spec
    scale = 1.5 if twist == "feast" else 1.0
    return Dungeon(
        key=KEY, name="Daily Challenge", kind="daily", min_level=MIN_LEVEL,
        description=f"Today's twist: {twist_for(day)[1]}. {twist_for(day)[2]}",
        rooms=tuple(rooms), complete_xp=boss_spec.xp, complete_coins=round(boss_spec.coins * 1.5),
        reward_scale=scale,
    )


def _twisted(spec: config.MonsterSpec, twist: str) -> config.MonsterSpec:
    if twist == "glass":
        return replace(spec, max_hp=max(1, round(spec.max_hp * 0.7)), damage=max(1, round(spec.damage * 1.35)))
    if twist == "iron":
        return replace(spec, armor=spec.armor + 2)
    if twist == "fury":
        return replace(spec, enrage=True)
    if twist == "mirror":
        return replace(spec, reverse_chance=max(spec.reverse_chance, 0.5))
    if twist == "sentences":
        return replace(spec, cloze_chance=max(spec.cloze_chance, 0.5))
    return spec
