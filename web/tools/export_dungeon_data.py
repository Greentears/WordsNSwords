"""Export the dungeon's data (balance numbers, monsters, items, dungeons) to src/dungeon/data.json.

Run after changing config.py / items.py / dungeons.py / tower.py constants on the desktop:
    python3 tools/export_dungeon_data.py [path-to-desktop-folder]
The rules code (answers, battle, manager ...) is ported by hand and checked with golden tests.
"""
import dataclasses, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parent / "desktop"
sys.path.insert(0, str(PY))

from dungeon import config, dungeons, items, tower  # noqa: E402


def room(r):
    return {"kind": r.kind, "title": r.title, "monster": r.monster, "coins": r.coins, "xp": r.xp,
            "heal_fraction": r.heal_fraction, "drop": r.drop, "drop_count": r.drop_count}


def build():
    consts = {k: v for k, v in vars(config).items()
              if k.isupper() and isinstance(v, (int, float)) and not isinstance(v, bool)}
    return {
        "constants": consts,
        "default_player_name": config.DEFAULT_PLAYER_NAME,
        "level_weights": [[k, v] for k, v in config.LEVEL_WEIGHTS.items()],
        "boss_level_weights": [[k, v] for k, v in config.BOSS_LEVEL_WEIGHTS.items()],
        "monsters": [dataclasses.asdict(m) for m in config.MONSTERS.values()],
        "items": [dataclasses.asdict(i) for i in items.ITEMS.values()],
        "removed_equipment": items.REMOVED_EQUIPMENT,
        "tower": {
            "monster_order": list(tower.MONSTER_ORDER), "boss_order": list(tower.BOSS_ORDER),
            "hp_growth": tower.HP_GROWTH, "damage_growth": tower.DAMAGE_GROWTH,
            "xp_growth": tower.XP_GROWTH, "coin_growth": tower.COIN_GROWTH,
            "ability_from_floor": tower.ABILITY_FROM_FLOOR, "second_ability_from_floor": tower.SECOND_ABILITY_FROM_FLOOR,
            "ability_rotation": list(tower.ABILITY_ROTATION),
            "cloze_from_floor": tower.CLOZE_FROM_FLOOR, "enrage_from_floor": tower.ENRAGE_FROM_FLOOR,
            "loot": list(items.TOWER_LOOT), "bundles": [list(b) for b in items.TOWER_BUNDLES],
        },
        "dungeons": [{
            "key": d.key, "name": d.name, "description": d.description, "rooms": [room(r) for r in d.rooms],
            "min_level": d.min_level, "complete_xp": d.complete_xp, "complete_coins": d.complete_coins,
            "kind": d.kind, "reward_scale": d.reward_scale, "hp_scale": d.hp_scale,
            "damage_scale": d.damage_scale, "endless": d.room_factory is not None,
        } for d in dungeons.DUNGEONS.values()],
    }


if __name__ == "__main__":
    out = ROOT / "src" / "dungeon" / "data.json"
    out.write_text(json.dumps(build(), ensure_ascii=False, indent=1), encoding="utf-8")
    print("wrote", out.relative_to(ROOT))
