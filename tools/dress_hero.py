"""Dress the hero by layering: the plain hero in a T-shirt, with armour and weapon pictures put on top.

Armour and weapons are drawn once each (flat pictures) and fitted onto the hero here, so a new sword or
armour costs one picture instead of a new hero picture for every combination. All layers of a hero share
one canvas, so on screen they are simply stacked in this order:

    base (T-shirt hero)  ->  shirt (the T-shirt darkened, when armour is worn)  ->  armour  ->  head  ->  weapon  ->  hand

Fitting numbers are in 1024-pixel hero coordinates (the size of the pictures the hero was drawn at).
"""
from __future__ import annotations

import numpy as np
from PIL import Image
from scipy import ndimage

# per hero: x of the body's middle, width of the T-shirt (sleeve to sleeve), y of the neck and of the shirt's
# hem, and where the hand that holds the sword is
HEROES = {
    "m": dict(cx=513, shirt_w=256, neck=236, hem=496, hand=(392, 575)),
    "f": dict(cx=516, shirt_w=201, neck=236, hem=470, hand=(428, 585)),
}
# armour width, as a multiple of the T-shirt's (the default is for anything not listed)
ARMOUR_WIDTH = {"leather_vest": 0.80, "chainmail": 1.22, "dragon_scale": 1.25, "plate_armor": 1.25}
DEFAULT_ARMOUR_WIDTH = 1.2
SWORD_LENGTH = 330
SHIRT_DARKNESS = 0.22


def _trim(layer: Image.Image) -> Image.Image:
    return layer.crop(layer.getchannel("A").getbbox())


def _open_neck(piece: Image.Image) -> Image.Image:
    """Armour pictures have a black hole at the collar; make it see-through so the hero's own neck shows."""
    arr = np.array(piece)
    h, w = arr.shape[:2]
    dark = (arr[..., :3].max(axis=2) < 45) & (arr[..., 3] > 0)
    zone = np.zeros_like(dark)
    zone[: int(h * 0.30), int(w * 0.25): int(w * 0.75)] = True
    labels, n = ndimage.label(dark & zone)
    for i in range(1, n + 1):
        comp = labels == i
        if comp.sum() > 40:
            arr[ndimage.binary_dilation(comp, iterations=1), 3] = 0
    return Image.fromarray(arr)


def armour_layer(art: Image.Image, key: str, hero: str, size) -> Image.Image:
    spec = HEROES[hero]
    piece = _trim(art)
    k = spec["shirt_w"] * ARMOUR_WIDTH.get(key, DEFAULT_ARMOUR_WIDTH) / piece.width
    piece = piece.resize((round(piece.width * k), round(piece.height * k)), Image.LANCZOS)
    piece = _open_neck(piece)
    out = Image.new("RGBA", size)
    out.alpha_composite(piece, (round(spec["cx"] - piece.width / 2), spec["neck"] - 8))
    return out


def shirt_layer(base: Image.Image, hero: str) -> Image.Image:
    """The T-shirt alone, darkened: what shows around the armour is an undershirt, not a bright T-shirt."""
    spec = HEROES[hero]
    a = np.array(base).astype(int)
    r, g, b, alpha = a[..., 0], a[..., 1], a[..., 2], a[..., 3]
    mask = (alpha > 40) & (r > 100) & (r < 250) & (abs(r - g) < 24) & (abs(g - b) < 34) & (r - b > 3)
    mask[spec["hem"] + 10:] = False
    mask[:190] = False
    labels, n = ndimage.label(mask)
    if not n:
        return Image.new("RGBA", base.size)
    sizes = ndimage.sum(mask, labels, range(1, n + 1))
    # the largest piece is the shirt; keep every other sizeable piece too (shoulder patches the shading split off)
    core = np.isin(labels, [i + 1 for i, sz in enumerate(sizes) if sz >= max(150, 0.01 * sizes.max())])
    core = ndimage.binary_fill_holes(ndimage.binary_closing(core, iterations=3))
    # grow over the shirt's lit and shaded edges, but never onto skin (skin is much redder than the cloth)
    grown = ndimage.binary_dilation(core, iterations=5) & (alpha > 0) & ((r - b) < 40)
    mask = core | grown
    mask[spec["hem"] + 10:] = False
    arr = np.array(base)
    out = np.zeros_like(arr)
    out[mask] = arr[mask]
    out[..., :3] = (out[..., :3] * SHIRT_DARKNESS).astype(np.uint8)
    return Image.fromarray(out)


def head_layer(base: Image.Image, hero: str) -> Image.Image:
    """Head and neck, drawn over the armour's collar."""
    arr = np.array(base)
    neck = HEROES[hero]["neck"]
    arr[neck:, :, 3] = 0
    # above the neck line keep only head, hair and skin: any cloth up there (the T-shirt's shoulders) must stay hidden
    r, b = arr[..., 0].astype(int), arr[..., 2].astype(int)
    cloth = (r > 120) & ((r - b) < 40) & (abs(r - arr[..., 1].astype(int)) < 24)
    cloth[:neck - 40] = False                  # hair and face are higher than this
    arr[cloth, 3] = 0
    return Image.fromarray(arr)


def weapon_layer(art: Image.Image, hero: str, size) -> Image.Image:
    """The weapon held in the hero's hand, blade down and a little outward."""
    sword = _trim(art).transpose(Image.FLIP_TOP_BOTTOM)
    k = SWORD_LENGTH / sword.height
    sword = sword.resize((round(sword.width * k), round(sword.height * k)), Image.LANCZOS)
    grip = np.array(sword.getchannel("A"))[: max(4, int(sword.height * 0.12))]
    _, xs = np.nonzero(grip > 40)
    anchor_x, anchor_y = xs.mean(), sword.height * 0.06
    hand = HEROES[hero]["hand"]
    out = Image.new("RGBA", size)
    out.alpha_composite(sword, (round(hand[0] - anchor_x), round(hand[1] - anchor_y)))
    return out


HAND_BOX = 46     # half the size of the square around the hand that is drawn over the sword's grip


def hand_layer(base: Image.Image, hero: str) -> Image.Image:
    """The hero's hand, drawn over the sword's grip so the sword looks held, not floating beside it."""
    x, y = HEROES[hero]["hand"]
    arr = np.array(base)
    keep = np.zeros(arr.shape[:2], bool)
    keep[y - HAND_BOX: y + HAND_BOX, x - HAND_BOX: x + HAND_BOX] = True
    r, b = arr[..., 0].astype(int), arr[..., 2].astype(int)
    keep &= (r - b) > 40                      # skin only
    arr[~keep, 3] = 0
    return Image.fromarray(arr)
