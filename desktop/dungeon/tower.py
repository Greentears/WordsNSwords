"""The Endless Tower: floors are generated from the floor number, so it never ends.

Every floor is a fight; every 5th floor (not a boss floor) is a resting place.
Every 10th floor has a boss that drops an item (see `items.TOWER_LOOT`).
Monsters get stronger with every floor. No treasure rooms.
"""
from __future__ import annotations

from dataclasses import replace

from . import config
from .items import TOWER_BUNDLES, TOWER_LOOT
from .models import BOSS, MONSTER, REST, Room

MONSTER_ORDER = ("slime", "goblin", "bat", "skeleton", "wolf", "dark_knight", "treant", "witch",
                 "golem", "wraith", "warlord")
BOSS_ORDER = ("boss", "guardian", "dragon")
HP_GROWTH, DAMAGE_GROWTH = 0.07, 0.045
XP_GROWTH, COIN_GROWTH = 0.02, 0.05      # rewards grow slower than monsters, or levels would run away
CLOZE_FROM_FLOOR = 15      # sentence questions start appearing here
ENRAGE_FROM_FLOOR = 20     # all monsters enrage below half HP from here on


def is_boss_floor(floor: int) -> bool:
    return floor % 10 == 0


def loot_for(floor: int) -> tuple[str, int]:
    """The item (key, count) the boss of this floor drops."""
    n = floor // 10
    if n <= len(TOWER_LOOT):
        return TOWER_LOOT[n - 1], 1
    return TOWER_BUNDLES[(n - len(TOWER_LOOT) - 1) % len(TOWER_BUNDLES)]


def monster_for(floor: int) -> config.MonsterSpec:
    """The monster of a floor, scaled to its depth."""
    if is_boss_floor(floor):
        base = config.MONSTERS[BOSS_ORDER[(floor // 10 - 1) % len(BOSS_ORDER)]]
    else:
        index = (floor - 1) // 2
        if index >= len(MONSTER_ORDER):  # past the roster: keep rotating the strongest ones
            index = len(MONSTER_ORDER) - 5 + floor % 5
        base = config.MONSTERS[MONSTER_ORDER[index]]
    depth = floor - 1
    cycle = (floor // 10 - 1) // len(BOSS_ORDER) if is_boss_floor(floor) else 0
    boost = 1 + 0.4 * cycle     # a repeated boss comes back stronger
    extra = {}
    if floor >= CLOZE_FROM_FLOOR and not base.cloze_chance:
        extra["cloze_chance"] = 0.3
    if floor >= ENRAGE_FROM_FLOOR:
        extra["enrage"] = True
    if floor >= 2 * ENRAGE_FROM_FLOOR:
        extra["armor"] = base.armor + 2
    return replace(
        base,
        max_hp=round(base.max_hp * (1 + HP_GROWTH * depth) * boost),
        damage=round(base.damage * (1 + DAMAGE_GROWTH * depth) * boost),
        xp=round(base.xp * (1 + XP_GROWTH * depth)),
        coins=round(base.coins * (1 + COIN_GROWTH * depth)),
        **extra,
    )


def floor_room(index: int) -> Room:
    """The room for floor `index + 1`."""
    floor = index + 1
    if floor % 5 == 0 and not is_boss_floor(floor):
        return Room(REST, f"Floor {floor}: Resting Place", heal_fraction=0.5)
    spec = monster_for(floor)
    if is_boss_floor(floor):
        drop, count = loot_for(floor)
        return Room(BOSS, f"Floor {floor}: {spec.name}", monster=spec.key, spec=spec,
                    drop=drop, drop_count=count)
    return Room(MONSTER, f"Floor {floor}", monster=spec.key, spec=spec)
