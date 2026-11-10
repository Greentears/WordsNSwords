"""Hero stats: points, and what each stat does. Pure functions; every number is in this file.

Flat effects (damage, HP, item power, coins) grow without a limit. Effects that stop making sense
past a point (dodge, discounts, sell price, extra XP) approach a limit with diminishing returns:
    bounded(points, limit, k) = limit * points / (points + k)
so the first point is worth about limit/k and every further point a little less, but never 0.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

STAT_KEYS = ("strength", "constitution", "dexterity", "intelligence", "charisma", "wisdom")
STAT_NAMES = {"strength": "Strength", "constitution": "Constitution", "dexterity": "Dexterity",
              "intelligence": "Intelligence", "charisma": "Charisma", "wisdom": "Wisdom"}

POINTS_PER_LEVEL = 2

# --- effects per point -------------------------------------------------------
STRENGTH_ATTACK_PCT = 2.5        # % more damage (of level + gear damage)
STRENGTH_PIERCE_EVERY = 5        # every this many points ignores 1 monster armor
CONSTITUTION_HP = 5              # max HP
CONSTITUTION_VICTORY_HEAL_PCT = 1.0   # % of max HP healed after each victory (up to ...)
CONSTITUTION_VICTORY_HEAL_MAX = 50.0
DEXTERITY_DODGE_LIMIT, DEXTERITY_DODGE_K = 35.0, 35.0       # % dodge (together with a companion's)
DEXTERITY_TIME_EVERY = 3         # every this many points: +1 second on timed questions
INTELLIGENCE_ITEM_PCT = 3.0      # % stronger healing and damage items
CHARISMA_COIN_PCT = 1.5          # % more coins from fights
CHARISMA_DISCOUNT_LIMIT, CHARISMA_DISCOUNT_K = 25.0, 25.0   # % off shop prices
CHARISMA_SELL_LIMIT, CHARISMA_SELL_K = 20.0, 25.0           # % of price added to the sell value (60% -> up to 80%)
WISDOM_XP_LIMIT, WISDOM_XP_K = 50.0, 17.0   # % extra XP, scaled by the share of hard words you got right

DODGE_TOTAL_LIMIT = 35.0         # stat dodge + companion dodge never exceed this

# --- respec -------------------------------------------------------------------
RESPEC_BASE_COST = 50
RESPEC_COST_PER_LEVEL = 10


def respec_cost(level: int, respecs: int) -> int:
    """The first respec is free; later ones cost coins that grow with the level."""
    return 0 if respecs <= 0 else RESPEC_BASE_COST + RESPEC_COST_PER_LEVEL * level


def bounded(points: int, limit: float, k: float) -> float:
    return limit * points / (points + k) if points > 0 else 0.0


@dataclass(frozen=True)
class Effects:
    attack_pct: float = 0.0
    armor_ignore: int = 0
    hp: int = 0
    victory_heal_pct: float = 0.0
    dodge_pct: float = 0.0
    time_bonus: int = 0
    item_pct: float = 0.0
    coin_pct: float = 0.0
    discount_pct: float = 0.0
    sell_bonus_pct: float = 0.0
    wisdom_xp_pct: float = 0.0


def clean_stats(data: Any) -> dict[str, int]:
    """A stats dict with exactly the six keys; anything invalid becomes 0."""
    data = data if isinstance(data, dict) else {}
    out = {}
    for key in STAT_KEYS:
        v = data.get(key)
        out[key] = v if isinstance(v, int) and not isinstance(v, bool) and 0 <= v <= 10**6 else 0
    return out


def effects(stats: dict[str, int]) -> Effects:
    s = {k: stats.get(k, 0) for k in STAT_KEYS}
    return Effects(
        attack_pct=STRENGTH_ATTACK_PCT * s["strength"],
        armor_ignore=s["strength"] // STRENGTH_PIERCE_EVERY,
        hp=CONSTITUTION_HP * s["constitution"],
        victory_heal_pct=min(CONSTITUTION_VICTORY_HEAL_MAX, CONSTITUTION_VICTORY_HEAL_PCT * s["constitution"]),
        dodge_pct=bounded(s["dexterity"], DEXTERITY_DODGE_LIMIT, DEXTERITY_DODGE_K),
        time_bonus=s["dexterity"] // DEXTERITY_TIME_EVERY,
        item_pct=INTELLIGENCE_ITEM_PCT * s["intelligence"],
        coin_pct=CHARISMA_COIN_PCT * s["charisma"],
        discount_pct=bounded(s["charisma"], CHARISMA_DISCOUNT_LIMIT, CHARISMA_DISCOUNT_K),
        sell_bonus_pct=bounded(s["charisma"], CHARISMA_SELL_LIMIT, CHARISMA_SELL_K),
        wisdom_xp_pct=bounded(s["wisdom"], WISDOM_XP_LIMIT, WISDOM_XP_K),
    )


DESCRIPTIONS = {
    "strength": "More damage; high Strength also ignores monster armor.",
    "constitution": "More max HP, and you recover some HP after every victory.",
    "dexterity": "A chance to dodge hits, and more time on timed questions.",
    "intelligence": "Healing and damage items are stronger.",
    "charisma": "More coins from fights, cheaper shop prices, better sell prices.",
    "wisdom": "Extra XP when you answer words you are still learning.",
}


def _num(x: float) -> str:
    """12.5 -> '12.5', 10.0 -> '10' (one decimal at most)."""
    text = f"{x:.1f}"
    return text[:-2] if text.endswith(".0") else text


def effect_text(stat: str, stats: dict[str, int], sell_fraction: float = 0.6) -> str:
    """What the points in `stat` give right now, e.g. '+12.5% damage · ignores 2 armor'."""
    fx = effects(stats)
    if stat == "strength":
        text = f"+{_num(fx.attack_pct)}% damage"
        return text + (f" · ignores {fx.armor_ignore} armor" if fx.armor_ignore else "")
    if stat == "constitution":
        return f"+{fx.hp} max HP · {_num(fx.victory_heal_pct)}% HP back after a win"
    if stat == "dexterity":
        return f"{_num(fx.dodge_pct)}% dodge · +{fx.time_bonus}s on timed words"
    if stat == "intelligence":
        return f"+{_num(fx.item_pct)}% item power"
    if stat == "charisma":
        return (f"+{_num(fx.coin_pct)}% coins · -{_num(fx.discount_pct)}% shop prices · "
                f"sells for {_num(sell_fraction * 100 + fx.sell_bonus_pct)}%")
    if stat == "wisdom":
        return f"+{_num(fx.wisdom_xp_pct)}% XP on words you are still learning"
    return ""
