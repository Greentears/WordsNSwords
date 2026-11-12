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

MONSTER_ORDER = ("book_mimic", "ink_raven", "bat", "quill_stalker", "wolf", "forgotten_scribe", "treant", "witch",
                 "golem", "wraith", "warlord")
BOSS_ORDER = ("dust_moth", "guardian", "dragon")
HP_GROWTH, DAMAGE_GROWTH = 0.07, 0.045
XP_GROWTH, COIN_GROWTH = 0.02, 0.05      # rewards grow slower than monsters, or levels would run away
ABILITY_FROM_FLOOR = 15    # special abilities (see `special_abilities`) start here
SECOND_ABILITY_FROM_FLOOR = 45
ABILITY_ROTATION = ("unavoidable", "pierce", "percent_damage", "poison", "curse", "silence", "streak", "thief")
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


def special_abilities(floor: int, base: config.MonsterSpec, boss: bool | None = None) -> dict:
    """Extra abilities of a Tower monster: one rotating ability from floor 15 (two from floor 45); bosses
    always crush. Values grow with the floor. Only abilities the monster does not have yet are added."""
    extra: dict = {}
    keys: list[str] = []
    boss = is_boss_floor(floor) if boss is None else boss
    if boss:
        keys = ["percent_damage", "unavoidable" if (floor // 10) % 2 else "curse"]
    elif floor >= ABILITY_FROM_FLOOR:
        n = floor // 5
        keys = [ABILITY_ROTATION[n % len(ABILITY_ROTATION)]]
        if floor >= SECOND_ABILITY_FROM_FLOOR:
            keys.append(ABILITY_ROTATION[(n + 3) % len(ABILITY_ROTATION)])
    for key in keys:
        if getattr(base, key):
            continue
        if key == "percent_damage":
            extra[key] = min(0.12, 0.05 + 0.002 * floor + (0.02 if boss else 0))
        elif key == "poison":
            extra[key] = max(2, round(base.damage * (1 + DAMAGE_GROWTH * (floor - 1)) * 0.3))
        elif key == "streak":
            extra[key] = 3 if floor >= 60 else 2
        elif key == "thief":
            extra[key] = 5 + floor // 2
        else:
            extra[key] = True
    return extra


def scale_monster(base: config.MonsterSpec, floor: int, boss: bool | None = None,
                  cycle: int = 0) -> config.MonsterSpec:
    """`base` as it appears on `floor`: tougher with depth, with the abilities of that depth.
    (The daily challenge uses this too, with the floor its tier stands for.)"""
    boss = is_boss_floor(floor) if boss is None else boss
    depth = floor - 1
    boost = 1 + 0.4 * cycle     # a repeated boss comes back stronger
    extra = {}
    if floor >= CLOZE_FROM_FLOOR and not base.cloze_chance:
        extra["cloze_chance"] = 0.3
    if floor >= ENRAGE_FROM_FLOOR:
        extra["enrage"] = True
    if floor >= 2 * ENRAGE_FROM_FLOOR:
        extra["armor"] = base.armor + 2
    extra.update(special_abilities(floor, base, boss))
    return replace(
        base,
        max_hp=round(base.max_hp * (1 + HP_GROWTH * depth) * boost),
        damage=round(base.damage * (1 + DAMAGE_GROWTH * depth) * boost),
        xp=round(base.xp * (1 + XP_GROWTH * depth)),
        coins=round(base.coins * (1 + COIN_GROWTH * depth)),
        **extra,
    )


def monster_for(floor: int) -> config.MonsterSpec:
    """The monster of a floor, scaled to its depth."""
    if is_boss_floor(floor):
        base = config.MONSTERS[BOSS_ORDER[(floor // 10 - 1) % len(BOSS_ORDER)]]
    else:
        index = (floor - 1) // 2
        if index >= len(MONSTER_ORDER):  # past the roster: keep rotating the strongest ones
            index = len(MONSTER_ORDER) - 5 + floor % 5
        base = config.MONSTERS[MONSTER_ORDER[index]]
    cycle = (floor // 10 - 1) // len(BOSS_ORDER) if is_boss_floor(floor) else 0
    return scale_monster(base, floor, is_boss_floor(floor), cycle)


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
