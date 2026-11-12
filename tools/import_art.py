"""Import the artwork: clean stray dots, resize, and write the copies the game uses.

    python3 tools/import_art.py <folder with your original PNGs> [<another folder> ...]

Your originals are only read, never changed. The tool looks at every PNG below the folders you
give it, matches each file name to a game name (see NAMES below), and writes
    desktop/assets/art/<kind>/<key>.png     for the PC game
    web/public/art/<kind>/<key>.webp        for the phone (smaller)
    web/src/art.json                        which pictures exist (the phone reads this)
Anything without a picture keeps its drawn pixel version, so you can add art a little at a time.
Re-run it whenever you add or change pictures.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]
PC_OUT = ROOT / "desktop" / "assets" / "art"
WEB_OUT = ROOT / "web" / "public" / "art"
INDEX = ROOT / "web" / "src" / "art.json"

# file name (without the _<size>[-version] ending) -> (kind, game key)
NAMES: dict[str, tuple[str, str]] = {
    # monsters
    "abyssal_bishop": ("monsters", "abyssal_bishop"), "barnacle_crawler": ("monsters", "barnacle_crawler"),
    "book_mimic": ("monsters", "book_mimic"), "dire_wolf": ("monsters", "wolf"),
    "drowned_acolyte": ("monsters", "drowned_acolyte"), "drowned_knight": ("monsters", "drowned_knight"),
    "dust_moth": ("monsters", "dust_moth"), "elder_dragon": ("monsters", "dragon"),
    "forest_guardian": ("monsters", "guardian"), "forgotten_scribe": ("monsters", "forgotten_scribe"),
    "frost_wraith": ("monsters", "wraith"), "grand_librarian": ("monsters", "librarian"),
    "guru_review": ("monsters", "review_guru"), "hedge_witch": ("monsters", "witch"),
    "ice_golem": ("monsters", "golem"), "ink_raven": ("monsters", "ink_raven"),
    "ink_slime": ("monsters", "ink_slime"), "page_wraith": ("monsters", "page_wraith"),
    "paper_goblin": ("monsters", "paper_goblin"), "quill_stalker": ("monsters", "quill_stalker"),
    "siren": ("monsters", "siren"), "tome_knight": ("monsters", "tome_knight"),
    "treant": ("monsters", "treant"), "vampire_bat": ("monsters", "bat"), "warlord": ("monsters", "warlord"),
    "slime": ("monsters", "slime"), "goblin": ("monsters", "goblin"), "skeleton": ("monsters", "skeleton"),
    "dark_knight": ("monsters", "dark_knight"), "dungeon_boss": ("monsters", "boss"),
    # companions
    "baby_dragon": ("companions", "baby_dragon"), "cat_shadow": ("companions", "shadow_cat"),
    "pixi": ("companions", "pixie"), "stone_turtle": ("companions", "stone_turtle"),
    "war_hawk": ("companions", "hawk"), "wise_owl": ("companions", "owl"),
    # consumables and charms
    "counting_rune": ("items", "count_rune"), "elixir_of_life": ("items", "big_potion"),
    "fire_bomb": ("items", "fire_bomb"), "golden_idol": ("items", "golden_idol"),
    "healing_potion": ("items", "small_potion"), "hourglass_amulet": ("items", "time_amulet"),
    "letter_scroll": ("items", "letter_scroll"), "lightning_rune": ("items", "lightning"),
    "lucky_clover": ("items", "lucky_clover"), "meteor_scroll": ("items", "meteor"),
    "oracles_eye": ("items", "oracle_eye"), "passage_scroll": ("items", "passage_scroll"),
    "pheonix_feather": ("items", "phoenix_feather"), "phoenix_feather": ("items", "phoenix_feather"),
    "sages_ring": ("items", "sages_ring"), "tome_of_wisdom": ("items", "wisdom_tome"),
    "ward_scroll": ("items", "ward_scroll"),
    # equipment: one sword and one armour picture for now (more can be added by key)
    "sword": ("items", "iron_sword"), "armour": ("items", "leather_vest"),
    "chainmail": ("items", "chainmail"), "plate_armour": ("items", "plate_armor"),
    "dragon_scale_mail": ("items", "dragon_scale"), "wooden_sword": ("items", "wooden_sword"),
    "iron_sword": ("items", "iron_sword"), "steel_blade": ("items", "steel_blade"),
    "runed_blade": ("items", "runed_blade"), "dragon_fang": ("items", "dragon_fang"),
}
# the hero, by file name: (gender, look). Files are not resized individually: all looks of one
# hero share one canvas, so he doesn't jump when he puts on a sword.
HEROES: dict[str, tuple[str, str]] = {
    "main_character": ("m", "base"), "character_sword": ("m", "sword"), "character_armour": ("m", "armour"),
    "character_armour_sword": ("m", "armour_sword"),
    "character_f": ("f", "base"), "character_f_sword": ("f", "sword"), "character_f_armour": ("f", "armour"),
    "character_f_armour_sword": ("f", "armour_sword"),
}
# dungeon backgrounds (file name -> dungeon key) and the screen furniture
BACKGROUNDS = {"cellar_of_words": "cellar", "whispering_forest": "forest", "library_of_sentences": "library",
               "frozen_citadel": "citadel", "sunken_cathedral": "cathedral", "review_guru": "review",
               "endless_tower": "tower",
               # rest and treasure scenes, indoors and outdoors
               "firecamp": "rest_outdoor", "firecamp_indoor": "rest_indoor",
               "treasure_indoor": "treasure_indoor", "treasure_outdoor": "treasure_outdoor"}
UI = {"slot_square": "slot_square", "slot_rectangle": "slot_armor", "slot_weapon": "slot_weapon",
      "character_slot": "panel",
      # faint silhouettes shown inside empty equipment slots
      "empty_weapon_slot": "empty_weapon", "empty_armour_slot": "empty_armor",
      "empty_charm_slot": "empty_charm", "empty_companion_slot": "empty_companion"}
MAX_SIDE = {"monsters": 512, "heroes": 640, "companions": 256, "items": 192,
            "backgrounds": 1280, "ui": 1024}   # pixels, PC
WEB_SIDE = {"monsters": 384, "heroes": 512, "companions": 192, "items": 128,
            "backgrounds": 960, "ui": 768}     # pixels, phone


def stem_key(path: Path) -> str:
    """'Sword_448' / 'ink_slime_1024-3' / 'Character_F_1024' -> 'sword' / 'ink_slime' / 'character_f'."""
    s = path.stem.lower()
    s = re.sub(r"-\d+$", "", s)          # version suffix
    s = re.sub(r"_(\d{2,4})(x\d{2,4})?$", "", s)    # size suffix (448 or 1920x1088)
    return s


def clean(im: Image.Image) -> Image.Image:
    """Remove faint specks: keep only the main picture and parts close to it."""
    im = im.convert("RGBA")
    a = np.asarray(im)[..., 3]
    solid = a > 40
    if not solid.any():
        return im
    # small separate specks are noise; anything bigger (a feather, a spark, a sword) is kept
    labels, n = ndimage.label(solid, structure=np.ones((3, 3), bool))
    sizes = ndimage.sum(solid, labels, range(1, n + 1))
    smallest = 400 * (im.width / 1024) ** 2
    keep = [i + 1 for i, size in enumerate(sizes) if size >= smallest]
    mask = ndimage.binary_dilation(np.isin(labels, keep), iterations=2)     # keep the soft edges
    arr = np.array(im)
    arr[..., 3] = np.where(mask & (a >= 12), a, 0)       # also drops nearly invisible haze
    return Image.fromarray(arr, "RGBA")


def resized(im: Image.Image, side: int) -> Image.Image:
    if max(im.size) <= side:
        return im
    k = side / max(im.size)
    return im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS)


def clear_haze(im: Image.Image) -> Image.Image:
    """Frames: the see-through middle sometimes holds faint specks; make them fully transparent."""
    arr = np.array(im.convert("RGBA"))
    arr[arr[..., 3] < 24] = 0
    solid = arr[..., 3] > 0
    labels, n = ndimage.label(solid, structure=np.ones((3, 3), bool))
    sizes = ndimage.sum(solid, labels, range(1, n + 1))
    for i, size in enumerate(sizes, start=1):          # loose specks in the empty middle
        if size < 0.01 * max(sizes):
            arr[labels == i] = 0
    return Image.fromarray(arr, "RGBA")


def save(im: Image.Image, kind: str, key: str) -> None:
    (PC_OUT / kind).mkdir(parents=True, exist_ok=True)
    (WEB_OUT / kind).mkdir(parents=True, exist_ok=True)
    if kind == "backgrounds":          # big scenery: JPEG on the PC, lighter WebP on the phone
        resized(im, MAX_SIDE[kind]).save(PC_OUT / kind / f"{key}.jpg", quality=88)
        resized(im, WEB_SIDE[kind]).save(WEB_OUT / kind / f"{key}.webp", quality=78, method=6)
        return
    resized(im, MAX_SIDE[kind]).save(PC_OUT / kind / f"{key}.png", optimize=True)
    resized(im, WEB_SIDE[kind]).save(WEB_OUT / kind / f"{key}.webp", quality=88, method=6)


def main(folders: list[str]) -> int:
    files = sorted(p for f in folders for p in Path(f).rglob("*.png"))
    if not files:
        print("No PNG files found.")
        return 1
    index: dict[str, list[str]] = {"monsters": [], "companions": [], "items": [], "heroes": [],
                                   "backgrounds": [], "ui": []}
    if INDEX.exists():                  # adding a few pictures keeps the ones imported earlier
        for kind, keys in json.loads(INDEX.read_text(encoding="utf-8")).items():
            index.setdefault(kind, []).extend(keys)
    unknown = []
    hero_names: dict[str, str] = {}
    for path in files:
        name = stem_key(path)
        if name in HEROES:
            gender, look = HEROES[name]
            hero_names[f"{gender}_{look}" if look != "base" else gender] = str(path)
            continue
        if name in BACKGROUNDS:
            save(Image.open(path).convert("RGB"), "backgrounds", BACKGROUNDS[name])
            if BACKGROUNDS[name] not in index["backgrounds"]:
                index["backgrounds"].append(BACKGROUNDS[name])
            continue
        if name in UI:
            im = Image.open(path)
            if UI[name] == "panel":
                im = im.convert("RGB")
            elif not UI[name].startswith("empty_"):      # silhouettes are faint on purpose
                im = clear_haze(im)
            save(im, "ui", UI[name])
            if UI[name] not in index["ui"]:
                index["ui"].append(UI[name])
            continue
        if name not in NAMES:
            unknown.append(path.name)
            continue
        kind, key = NAMES[name]
        save(clean(Image.open(path)), kind, key)
        if key not in index[kind]:
            index[kind].append(key)
    if hero_names:                                      # all looks share one crop, cleaned alike
        images = {k: clean(Image.open(p)) for k, p in hero_names.items()}
        boxes = [b for b in (im.getchannel("A").getbbox() for im in images.values()) if b]
        pad = 12
        crop = (max(0, min(b[0] for b in boxes) - pad), max(0, min(b[1] for b in boxes) - pad),
                max(b[2] for b in boxes) + pad, max(b[3] for b in boxes) + pad)
        images = {k: im.crop(crop) for k, im in images.items()}
        for k, im in images.items():
            save(im, "heroes", k)
            if k not in index["heroes"]:
                index["heroes"].append(k)
    for kind in index:
        index[kind] = sorted(set(index[kind]))
    INDEX.write_text(json.dumps(index, indent=1), encoding="utf-8")
    print({k: len(v) for k, v in index.items()})
    if unknown:
        print("Not recognised (left out):", ", ".join(unknown))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]) if len(sys.argv) > 1 else print(__doc__) or 1)
