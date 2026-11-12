"""Dress the hero in layers: base (t-shirt) + armour + weapon, all on one canvas.

The armour and sword pictures are item icons, so this fits each one to the hero's body (size and place)
and writes them as separate transparent layers. The game stacks the layers it needs for whatever the
hero wears, so one picture per item is enough (no picture for every sword/armour combination).
Used by import_art.py.
"""
from __future__ import annotations

import math

import numpy as np
from PIL import Image

# the shared canvas, in pixels of the 1024-high originals: (left, top, right, bottom)
CANVAS = (250, 20, 760, 1024)

# Where the body is, per hero (pixels of the 1024 originals), read off the t-shirt pictures.
BODY = {
    "m": {"shoulders": 270, "centre_x": 520, "neck_y": 214, "hand": (392, 566)},
    "f": {"shoulders": 205, "centre_x": 517, "neck_y": 222, "hand": (408, 556)},
}
REFERENCE_SHOULDERS = 270          # the male body, which ARMOUR below is described for
# armour key -> (width as drawn on the male hero, y of its top edge on the male hero)
ARMOUR = {
    "leather_vest": (232, 218),
    "chainmail": (318, 214),
    "plate_armor": (338, 196),
    "dragon_scale": (338, 196),
}
SWORD_LENGTH = 430                 # tip to pommel, in pixels of the 1024-high hero
SWORD_TIP_ANGLE = 138              # degrees clockwise from "up": blade across the body, pointing down and out


def _tip_and_pommel(im: Image.Image) -> tuple[tuple[float, float], tuple[float, float]]:
    a = np.asarray(im.getchannel("A")) > 60
    ys, xs = np.nonzero(a)
    top = ys.min()
    bottom = ys.max()
    tip = (xs[ys <= top + 3].mean(), float(top))
    pommel = (xs[ys >= bottom - 3].mean(), float(bottom))
    return tip, pommel


def fit_sword(sword: Image.Image, gender: str) -> tuple[Image.Image, tuple[int, int]]:
    """The sword turned and sized so its grip sits in the hero's hand: (image, top-left corner on the 1024 canvas)."""
    tip, pommel = _tip_and_pommel(sword)
    length = math.dist(tip, pommel)
    scale = SWORD_LENGTH / length
    sword = sword.resize((round(sword.width * scale), round(sword.height * scale)), Image.LANCZOS)
    tip, pommel = (tip[0] * scale, tip[1] * scale), (pommel[0] * scale, pommel[1] * scale)
    grip = (pommel[0] + (tip[0] - pommel[0]) * 0.17, pommel[1] + (tip[1] - pommel[1]) * 0.17)
    # angle of the tip direction now, clockwise from "up"
    now = math.degrees(math.atan2(tip[0] - pommel[0], -(tip[1] - pommel[1])))
    turn = SWORD_TIP_ANGLE - now                         # PIL rotates counter-clockwise: use -turn
    pad = int(SWORD_LENGTH)
    canvas = Image.new("RGBA", (sword.width + 2 * pad, sword.height + 2 * pad), (0, 0, 0, 0))
    canvas.alpha_composite(sword, (pad, pad))
    centre = (grip[0] + pad, grip[1] + pad)
    rotated = canvas.rotate(-turn, resample=Image.BICUBIC, center=centre)
    hand = BODY[gender]["hand"]
    return rotated, (round(hand[0] - centre[0]), round(hand[1] - centre[1]))


def fit_armour(armour: Image.Image, key: str, gender: str) -> tuple[Image.Image, tuple[int, int]]:
    """The armour sized to the hero's shoulders and centred on his chest: (image, top-left corner on the 1024 canvas)."""
    box = armour.getchannel("A").point(lambda v: 255 if v > 40 else 0).getbbox()
    armour = armour.crop(box)
    width, top = ARMOUR[key]
    body = BODY[gender]
    scale = width * body["shoulders"] / REFERENCE_SHOULDERS / armour.width
    armour = armour.resize((round(armour.width * scale), round(armour.height * scale)), Image.LANCZOS)
    return armour, (round(body["centre_x"] - armour.width / 2), round(top + body["neck_y"] - BODY["m"]["neck_y"]))


def on_canvas(layer: Image.Image, corner: tuple[int, int]) -> Image.Image:
    """`layer` on a transparent canvas the size of the originals (it may hang over the edges)."""
    full = Image.new("RGBA", (1024, 1024), (0, 0, 0, 0))
    full.paste(layer, corner, layer)
    return full
