"""Balance table: how do the stat builds fare against the Tower? (expected values, no randomness)

    python tools/simulate_balance.py

For a hero of a given level and build, against a given Tower floor, with answer accuracy p:
  questions  = how many words you must answer to win  (more = more practice)
  hp lost    = expected share of your max HP lost in that fight
  xp         = XP of the victory (with the Wisdom bonus for hard words)
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "desktop"))
from dungeon import config, stats as S, tower  # noqa: E402
from dungeon.models import Player  # noqa: E402

BUILDS = {   # share of the points per stat
    "no points": {},
    "glass cannon": {"strength": 0.6, "dexterity": 0.4},
    "tank": {"constitution": 0.6, "strength": 0.4},
    "scholar": {"wisdom": 0.6, "intelligence": 0.4},
    "merchant": {"charisma": 0.7, "intelligence": 0.3},
    "all-round": {k: 1 / 6 for k in S.STAT_KEYS},
}
GEAR = {10: (9, 0, 0), 20: (20, 80, 3), 30: (34, 160, 6)}     # attack, hp, reduction a player of that level might own


def hero(level: int, build: dict) -> Player:
    points = S.POINTS_PER_LEVEL * (level - 1)
    st = {k: round(points * build.get(k, 0)) for k in S.STAT_KEYS}
    atk, hp, red = GEAR[level]
    p = Player(level=level, stats=st)
    p.gear_attack, p.gear_reduction = atk, red
    p.stat_hp = S.effects(st).hp
    p.max_hp = config.BASE_MAX_HP + config.LEVEL_HP_GAIN * (level - 1) + hp + p.stat_hp
    return p


def fight(p: Player, floor: int, accuracy: float = 0.8):
    m = tower.monster_for(floor)
    fx = p.effects
    dmg = max(1, p.attack_power - max(0, m.armor - fx.armor_ignore))
    kills = math.ceil(m.max_hp / dmg)                       # correct answers needed
    questions = kills / accuracy
    wrong = questions - kills
    hit = min(max(1, m.damage - p.gear_reduction), config.MAX_HIT_FRACTION * p.max_hp)
    hp_lost = wrong * (1 - min(fx.dodge_pct, S.DODGE_TOTAL_LIMIT) / 100) * hit
    xp = m.xp * (1 + fx.wisdom_xp_pct / 100 * 0.5)          # about half of the answers are hard words
    return questions, 100 * hp_lost / p.max_hp, xp


def main():
    for level in (10, 20, 30):
        print(f"\n=== level {level} (gear: +{GEAR[level][0]} attack, +{GEAR[level][1]} HP, -{GEAR[level][2]} per hit) ===")
        floors = (10, 30, 50, 80)
        print(f"{'build':<14}" + "".join(f"  floor {f:<3} q / hp% / xp   " for f in floors))
        for name, build in BUILDS.items():
            p = hero(level, build)
            cells = []
            for f in floors:
                q, lost, xp = fight(p, f)
                cells.append(f"{q:6.0f} / {lost:4.0f}% / {xp:4.0f}  ")
            print(f"{name:<14}" + "".join(f"  {c}" for c in cells))


if __name__ == "__main__":
    main()
