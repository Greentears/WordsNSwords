"""Golden data for the TypeScript port of the dungeon pixel sprites.

Records sprite_pixels() for every key in SPRITE_KEYS and hero_pixels() for every combination of
(none + each weapon) x (none + each armor) x (none + each charm) from dungeon/items.py, loot-only items included.
Grids are stored as 32 rows of palette indices (-1 = transparent) into one shared colour list.

    python3 tools/make_sprite_golden.py [path-to-desktop-folder]   ->  tests/sprite_golden.json
"""
import itertools, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parent / "desktop"
sys.path.insert(0, str(PY))

from dungeon import items  # noqa: E402
from dungeon.sprites import SPRITE_KEYS, SIZE, hero_pixels, sprite_pixels  # noqa: E402

palette: list[str] = []
index: dict[str, int] = {}


def encode(grid):
    assert len(grid) == SIZE and all(len(r) == SIZE for r in grid)
    rows = []
    for row in grid:
        r = []
        for c in row:
            if c is None:
                r.append(-1)
            else:
                if c not in index:
                    index[c] = len(palette)
                    palette.append(c)
                r.append(index[c])
        rows.append(r)
    return rows


def slot_keys(slot):
    return [k for k, i in items.ITEMS.items() if i.slot == slot]


weapons, armors, charms = (slot_keys(s) for s in (items.WEAPON, items.ARMOR, items.CHARM))
sprites = {k: encode(sprite_pixels(k)) for k in SPRITE_KEYS}
heroes = [{"weapon": w, "armor": a, "charm": c, "grid": encode(hero_pixels(w, a, c))}
          for w, a, c in itertools.product([None, *weapons], [None, *armors], [None, *charms])]

out = ROOT / "tests" / "sprite_golden.json"
out.write_text(json.dumps({"size": SIZE, "palette": palette, "keys": list(SPRITE_KEYS), "weapons": weapons,
                           "armors": armors, "charms": charms, "sprites": sprites, "heroes": heroes},
                          separators=(",", ":")))
print(f"{out}: {len(sprites)} sprites, {len(heroes)} hero combinations, {len(palette)} colours, "
      f"{out.stat().st_size / 1e6:.2f} MB")
