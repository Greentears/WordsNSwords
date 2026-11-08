"""Procedurally drawn 32x32 sprites in a gritty dark-fantasy style (Qt-free).

Instead of typing pixel grids, each creature is built from a few shapes (rects,
ellipses, polygons, lines) on a small canvas; a dark outline is added automatically
and `sprites._shade` adds the lighting, grit and glowing eyes. Unlike the older
mirrored art these figures can be asymmetric (sword on one side, shield on the other).
"""
from __future__ import annotations

N = 32


class Canvas:
    def __init__(self) -> None:
        self.g = [["."] * N for _ in range(N)]

    def px(self, x: int, y: int, c: str) -> None:
        if 0 <= x < N and 0 <= y < N:
            self.g[y][x] = c

    def get(self, x: int, y: int) -> str:
        return self.g[y][x] if 0 <= x < N and 0 <= y < N else "."

    def rect(self, x0, y0, x1, y1, c) -> None:
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                self.px(x, y, c)

    def ellipse(self, cx, cy, rx, ry, c) -> None:
        for y in range(int(cy - ry) - 1, int(cy + ry) + 2):
            for x in range(int(cx - rx) - 1, int(cx + rx) + 2):
                if ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1.0:
                    self.px(x, y, c)

    def poly(self, pts, c) -> None:
        n = len(pts)
        ys = [p[1] for p in pts]
        for y in range(min(ys), max(ys) + 1):
            xs = []
            for i in range(n):
                (x1, y1), (x2, y2) = pts[i], pts[(i + 1) % n]
                if (y1 <= y < y2) or (y2 <= y < y1):
                    xs.append(x1 + (y - y1) * (x2 - x1) / (y2 - y1))
            xs.sort()
            for a, b in zip(xs[::2], xs[1::2]):
                for x in range(round(a), round(b) + 1):
                    self.px(x, y, c)

    def line(self, x0, y0, x1, y1, c, w: int = 1) -> None:
        steps = max(abs(x1 - x0), abs(y1 - y0), 1)
        for i in range(steps + 1):
            x = round(x0 + (x1 - x0) * i / steps)
            y = round(y0 + (y1 - y0) * i / steps)
            for dx in range(w):
                self.px(x + dx, y, c)

    def mirror(self, c_from: int = 0) -> None:
        """Copy the left half onto the right (for the symmetric parts of a figure)."""
        for y in range(N):
            for x in range(N // 2):
                if self.g[y][x] != ".":
                    self.g[y][N - 1 - x] = self.g[y][x]

    def outline(self) -> list[str]:
        out = [row[:] for row in self.g]
        for y in range(N):
            for x in range(N):
                if self.g[y][x] == ".":
                    if any(self.get(x + dx, y + dy) not in ".o"
                           for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                        out[y][x] = "o"
        return ["".join(r) for r in out]


def _finish(c: Canvas) -> list[str]:
    return c.outline()


# --------------------------------------------------------------------------- hero
def hero() -> list[str]:
    c = Canvas()
    # cape
    c.poly([(9, 11), (23, 11), (26, 27), (6, 27)], "r")
    # legs and boots
    c.rect(11, 22, 14, 28, "K"); c.rect(17, 22, 20, 28, "K")
    c.rect(10, 28, 14, 30, "b"); c.rect(17, 28, 21, 30, "b")
    # torso (plate)
    c.poly([(10, 11), (22, 11), (21, 23), (11, 23)], "h")
    c.rect(13, 13, 18, 18, "H"); c.rect(10, 20, 21, 21, "b"); c.rect(15, 20, 16, 21, "g")
    # pauldrons
    c.ellipse(9, 11, 3.5, 3, "H"); c.ellipse(23, 11, 3.5, 3, "K")
    c.rect(6, 9, 7, 10, "H"); c.rect(24, 9, 25, 10, "K")   # spikes
    # helmet with visor slit and horns
    c.ellipse(16, 6, 5, 5.5, "h"); c.rect(11, 6, 21, 8, "h")
    c.rect(12, 6, 20, 6, "K"); c.rect(13, 6, 19, 6, "e")   # glowing visor
    c.rect(15, 2, 17, 4, "H")
    c.line(11, 3, 8, 0, "H"); c.line(21, 3, 24, 0, "H")
    # left arm + kite shield
    c.rect(7, 13, 9, 19, "K")
    c.poly([(2, 15), (10, 15), (10, 24), (6, 28), (2, 24)], "K")
    c.rect(3, 16, 9, 17, "h"); c.rect(5, 16, 6, 24, "g"); c.rect(3, 19, 9, 20, "g")
    # right arm + longsword
    c.rect(22, 13, 24, 19, "h"); c.rect(23, 19, 25, 21, "b")
    c.rect(26, 20, 26, 21, "g"); c.rect(24, 17, 28, 17, "g")
    c.rect(26, 2, 27, 17, "H"); c.rect(27, 3, 27, 16, "h"); c.px(26, 1, "H")
    return _finish(c)


# --------------------------------------------------------------------------- monsters
def slime() -> list[str]:
    c = Canvas()
    c.poly([(5, 28), (7, 17), (11, 11), (16, 8), (21, 11), (25, 17), (27, 28)], "g")
    c.ellipse(16, 21, 11, 8, "g")
    c.ellipse(13, 14, 4, 3, "G")                 # sheen
    c.ellipse(11, 20, 2.2, 3, "w"); c.ellipse(21, 20, 2.2, 3, "w")
    c.rect(10, 20, 12, 22, "e"); c.rect(20, 20, 22, 22, "e")
    c.rect(12, 26, 20, 26, "o")                   # toothless maw
    for x in (13, 16, 19):
        c.rect(x, 26, x, 27, "w")
    c.rect(4, 28, 28, 29, "g")
    for x in (7, 14, 24):
        c.rect(x, 29, x + 1, 30, "g")             # drips
    return _finish(c)


def goblin() -> list[str]:
    c = Canvas()
    c.poly([(7, 10), (1, 5), (11, 8)], "g"); c.poly([(25, 10), (31, 5), (21, 8)], "g")   # ears
    c.ellipse(16, 10, 6, 6, "g")
    c.rect(11, 9, 14, 10, "e"); c.rect(18, 9, 21, 10, "e")                                # eyes
    c.rect(12, 14, 20, 15, "o"); c.px(13, 15, "w"); c.px(15, 15, "w"); c.px(17, 15, "w"); c.px(19, 15, "w")
    c.poly([(9, 17), (23, 17), (24, 27), (8, 27)], "b")                                   # tunic
    c.rect(9, 22, 23, 23, "y")
    c.rect(5, 18, 8, 20, "g"); c.rect(24, 18, 27, 20, "g")                                # arms
    c.rect(3, 12, 4, 21, "b"); c.poly([(1, 9), (6, 9), (3, 14)], "w")                     # spear
    c.rect(26, 21, 30, 22, "w"); c.rect(25, 20, 26, 23, "b")                              # knife
    c.rect(10, 27, 13, 30, "g"); c.rect(19, 27, 22, 30, "g")
    return _finish(c)


def skeleton() -> list[str]:
    c = Canvas()
    c.ellipse(16, 6, 5, 5, "w"); c.rect(12, 9, 20, 11, "w")
    c.rect(11, 5, 14, 8, "o"); c.rect(18, 5, 21, 8, "o")
    c.rect(12, 6, 13, 7, "e"); c.rect(19, 6, 20, 7, "e")
    c.px(16, 9, "o"); c.px(15, 10, "o"); c.px(17, 10, "o")
    for x in (13, 15, 17, 19):
        c.rect(x, 11, x, 12, "o")
    c.rect(15, 13, 16, 22, "d")                                                          # spine
    for y in (14, 16, 18, 20):
        c.rect(10, y, 21, y, "w"); c.rect(11, y + 1, 20, y + 1, "d")                       # ribs
    c.rect(8, 13, 11, 14, "w"); c.rect(21, 13, 24, 14, "w")                              # shoulders
    c.rect(7, 15, 8, 24, "w"); c.rect(24, 15, 25, 21, "w")                               # arms
    c.rect(11, 22, 20, 24, "d"); c.rect(13, 24, 18, 24, "w")                             # pelvis
    c.rect(12, 25, 13, 30, "w"); c.rect(18, 25, 19, 30, "w")
    c.rect(11, 30, 14, 30, "d"); c.rect(17, 30, 20, 30, "d")
    c.rect(26, 8, 26, 22, "d"); c.poly([(24, 8), (28, 8), (26, 2)], "w")                 # spear
    c.line(4, 22, 7, 14, "d", 2)                                                         # rusty blade hand
    return _finish(c)


def dark_knight() -> list[str]:
    c = Canvas()
    c.poly([(8, 12), (24, 12), (27, 30), (5, 30)], "p")                                  # tattered cloak
    c.poly([(10, 11), (22, 11), (21, 24), (11, 24)], "k")
    c.rect(14, 14, 17, 19, "K")
    c.rect(10, 22, 21, 23, "b")
    c.rect(11, 24, 14, 29, "k"); c.rect(17, 24, 20, 29, "k"); c.rect(10, 29, 14, 30, "K"); c.rect(17, 29, 21, 30, "K")
    c.ellipse(8, 11, 4, 3.5, "K"); c.ellipse(24, 11, 4, 3.5, "K")
    for x in (5, 7, 9):
        c.px(x, 7, "K"); c.px(x, 8, "K")
    for x in (23, 25, 27):
        c.px(x, 7, "K"); c.px(x, 8, "K")
    c.ellipse(16, 6, 5, 5.5, "k"); c.rect(12, 5, 20, 7, "k")
    c.rect(13, 6, 19, 6, "r")                                                            # burning visor
    c.poly([(13, 1), (19, 1), (17, -3), (15, -3)], "p")
    c.rect(7, 13, 9, 20, "k"); c.rect(23, 13, 25, 20, "k")
    c.rect(27, 6, 28, 22, "K"); c.rect(25, 20, 30, 21, "b"); c.rect(27, 22, 28, 24, "b")  # greatsword
    c.px(27, 5, "K"); c.px(28, 4, "K")
    return _finish(c)


def boss() -> list[str]:
    c = Canvas()
    c.poly([(2, 24), (6, 12), (10, 16), (8, 28)], "r"); c.poly([(30, 24), (26, 12), (22, 16), (24, 28)], "r")   # wings
    c.poly([(8, 12), (24, 12), (26, 26), (22, 30), (10, 30), (6, 26)], "R")              # hulking body
    c.rect(13, 16, 19, 24, "r"); c.line(16, 14, 16, 26, "o")
    c.ellipse(16, 8, 6, 5.5, "R")
    c.poly([(9, 6), (4, 0), (12, 4)], "w"); c.poly([(23, 6), (28, 0), (20, 4)], "w")     # horns
    c.rect(11, 6, 14, 7, "e"); c.rect(18, 6, 21, 7, "e")
    c.rect(12, 11, 20, 12, "o")
    for x in (12, 14, 16, 18, 20):
        c.rect(x, 12, x, 13, "w")
    c.rect(3, 18, 8, 22, "R"); c.rect(24, 18, 29, 22, "R")                               # claws
    for x in (3, 5, 7):
        c.rect(x, 23, x, 25, "w")
    for x in (24, 26, 28):
        c.rect(x, 23, x, 25, "w")
    return _finish(c)


def bat() -> list[str]:
    c = Canvas()
    c.poly([(14, 12), (1, 6), (3, 14), (6, 13), (7, 19), (11, 16), (14, 22)], "p")
    c.poly([(18, 12), (31, 6), (29, 14), (26, 13), (25, 19), (21, 16), (18, 22)], "p")
    c.line(14, 12, 3, 9, "P"); c.line(18, 12, 29, 9, "P")
    c.ellipse(16, 15, 4, 6, "p"); c.ellipse(16, 9, 4, 4, "p")
    c.poly([(12, 8), (11, 1), (15, 6)], "p"); c.poly([(20, 8), (21, 1), (17, 6)], "p")   # ears
    c.rect(13, 9, 14, 10, "r"); c.rect(18, 9, 19, 10, "r")
    c.px(15, 12, "w"); c.px(17, 12, "w")
    c.line(14, 22, 13, 25, "P"); c.line(18, 22, 19, 25, "P")
    return _finish(c)


def wolf() -> list[str]:
    c = Canvas()
    c.poly([(4, 12), (14, 10), (22, 12), (26, 20), (22, 26), (6, 26)], "g")              # body
    c.poly([(22, 14), (30, 10), (31, 18), (27, 20)], "g")                                 # tail / back
    c.poly([(22, 8), (28, 3), (27, 10)], "G"); c.poly([(13, 8), (14, 3), (18, 7)], "G")  # ears
    c.ellipse(11, 12, 7, 6, "G"); c.poly([(1, 14), (6, 12), (6, 17), (1, 17)], "G")       # head + snout
    c.rect(1, 17, 7, 18, "o"); c.px(2, 18, "w"); c.px(4, 18, "w"); c.px(6, 18, "w")
    c.px(1, 14, "o"); c.px(2, 14, "o")
    c.rect(8, 10, 10, 11, "e")
    c.rect(7, 26, 9, 30, "g"); c.rect(11, 26, 13, 30, "g"); c.rect(20, 26, 22, 30, "g"); c.rect(24, 24, 26, 30, "g")
    c.line(9, 19, 11, 24, "r", 2)                                                         # bloody maw
    return _finish(c)


def treant() -> list[str]:
    c = Canvas()
    c.poly([(9, 12), (23, 12), (24, 28), (8, 28)], "b")                                   # trunk
    for x in (11, 15, 19):
        c.line(x, 13, x + 1, 27, "B")
    c.ellipse(16, 6, 9, 5.5, "g"); c.ellipse(9, 7, 5, 4, "G"); c.ellipse(23, 6, 5, 4, "g")  # foliage
    c.rect(11, 12, 14, 14, "o"); c.rect(18, 12, 21, 14, "o"); c.rect(12, 13, 13, 13, "e"); c.rect(19, 13, 20, 13, "e")
    c.rect(13, 18, 19, 20, "o"); c.rect(14, 20, 18, 21, "o")
    c.poly([(8, 14), (1, 22), (3, 26), (8, 20)], "b"); c.poly([(24, 14), (31, 22), (29, 26), (24, 20)], "b")
    c.rect(0, 25, 3, 27, "B"); c.rect(28, 25, 31, 27, "B")
    c.poly([(8, 28), (4, 31), (12, 31)], "b"); c.poly([(24, 28), (28, 31), (20, 31)], "b")
    c.px(7, 3, "y"); c.px(24, 4, "y")
    return _finish(c)


def witch() -> list[str]:
    c = Canvas()
    c.poly([(16, -4), (21, 8), (11, 8)], "p")                                             # hat tip
    c.poly([(16, 0), (18, 3), (14, 3)], "p")
    c.rect(6, 7, 26, 8, "p"); c.rect(11, 6, 21, 6, "y")                                   # brim + band
    c.ellipse(16, 12, 4.5, 4.5, "g")
    c.rect(12, 11, 14, 12, "e"); c.rect(18, 11, 20, 12, "e")
    c.px(16, 14, "o"); c.px(15, 15, "o"); c.px(17, 15, "o")
    c.poly([(11, 16), (21, 16), (26, 31), (6, 31)], "p")                                  # robe
    c.rect(15, 17, 17, 30, "P"); c.rect(11, 22, 21, 22, "y")
    c.rect(8, 17, 10, 23, "p"); c.rect(5, 22, 8, 24, "g")
    c.rect(24, 17, 26, 22, "p"); c.rect(25, 22, 27, 23, "g")
    c.rect(29, 6, 29, 29, "y"); c.ellipse(29, 5, 2, 2.5, "e")                             # staff + orb
    return _finish(c)


def golem() -> list[str]:
    c = Canvas()
    c.poly([(7, 11), (25, 11), (28, 24), (22, 29), (10, 29), (4, 24)], "i")
    c.rect(11, 14, 21, 22, "b"); c.poly([(12, 15), (20, 15), (16, 22)], "I")
    c.rect(10, 3, 22, 10, "i"); c.rect(11, 2, 21, 2, "I")
    c.rect(12, 5, 14, 6, "e"); c.rect(18, 5, 20, 6, "e")
    c.rect(2, 12, 7, 24, "i"); c.rect(25, 12, 30, 24, "i")
    c.rect(1, 22, 8, 27, "I"); c.rect(24, 22, 31, 27, "I")                                # fists
    for x in (3, 5, 7):
        c.px(x, 11, "I")
    for x in (25, 27, 29):
        c.px(x, 11, "I")
    c.rect(10, 29, 14, 31, "b"); c.rect(18, 29, 22, 31, "b")
    c.line(8, 14, 10, 20, "o"); c.line(23, 16, 21, 24, "o")                               # cracks
    return _finish(c)


def wraith() -> list[str]:
    c = Canvas()
    c.poly([(16, 1), (22, 6), (23, 14), (28, 31), (4, 31), (9, 14), (10, 6)], "c")        # hooded robe
    c.ellipse(16, 10, 5, 6, "k")
    c.rect(12, 9, 14, 10, "e"); c.rect(18, 9, 20, 10, "e")
    c.poly([(8, 18), (1, 26), (4, 28), (10, 24)], "C"); c.poly([(24, 18), (31, 26), (28, 28), (22, 24)], "C")
    for x in (6, 10, 14, 18, 22, 26):                                                    # tattered hem
        c.poly([(x - 2, 29), (x + 2, 29), (x, 31)], "c")
    c.line(14, 16, 12, 28, "C"); c.line(19, 16, 21, 28, "C")
    return _finish(c)


def dragon() -> list[str]:
    c = Canvas()
    c.poly([(1, 22), (6, 8), (12, 14), (10, 24)], "d"); c.poly([(31, 22), (26, 8), (20, 14), (22, 24)], "d")  # wings
    c.line(6, 8, 10, 24, "G"); c.line(26, 8, 22, 24, "G")
    c.poly([(9, 14), (23, 14), (25, 28), (21, 31), (11, 31), (7, 28)], "g")               # body
    c.poly([(13, 18), (19, 18), (20, 29), (12, 29)], "y")                                 # belly plates
    for y in (20, 23, 26):
        c.rect(13, y, 19, y, "G")
    c.poly([(11, 12), (21, 12), (19, 4), (13, 4)], "g")
    c.poly([(13, 4), (19, 4), (18, 0), (14, 0)], "g")
    c.poly([(11, 5), (7, 0), (13, 3)], "w"); c.poly([(21, 5), (25, 0), (19, 3)], "w")      # horns
    c.rect(12, 7, 14, 8, "e"); c.rect(18, 7, 20, 8, "e")
    c.rect(14, 10, 18, 12, "r"); c.px(15, 10, "w"); c.px(17, 10, "w")                     # glowing maw
    c.rect(8, 28, 10, 31, "g"); c.rect(22, 28, 24, 31, "g")
    return _finish(c)


def treasure() -> list[str]:
    c = Canvas()
    c.rect(5, 14, 26, 18, "b"); c.rect(5, 19, 26, 27, "b")
    c.rect(5, 18, 26, 18, "o"); c.rect(5, 14, 26, 14, "y"); c.rect(5, 27, 26, 27, "y")
    c.rect(7, 14, 8, 27, "y"); c.rect(23, 14, 24, 27, "y")
    c.rect(14, 17, 17, 22, "y"); c.rect(15, 19, 16, 20, "o")
    return _finish(c)


def rest() -> list[str]:
    c = Canvas()
    c.line(7, 30, 25, 26, "b", 2); c.line(7, 26, 25, 30, "b", 2)                          # logs
    c.poly([(16, 4), (22, 14), (24, 24), (16, 27), (8, 24), (10, 14)], "r")
    c.poly([(16, 11), (20, 19), (21, 24), (16, 26), (11, 24), (12, 19)], "y")
    return _finish(c)


# --------------------------------------------------------------------------- companions
def pixie() -> list[str]:
    c = Canvas()
    c.poly([(14, 14), (3, 4), (2, 14), (13, 19)], "w"); c.poly([(18, 14), (29, 4), (30, 14), (19, 19)], "w")   # wings
    c.line(14, 14, 4, 6, "b"); c.line(18, 14, 28, 6, "b")
    c.ellipse(16, 8, 4, 4.5, "s"); c.rect(11, 3, 21, 5, "h"); c.poly([(11, 4), (9, 12), (12, 9)], "h")        # head + hair
    c.rect(13, 8, 14, 9, "e"); c.rect(18, 8, 19, 9, "e")
    c.poly([(12, 13), (20, 13), (22, 24), (10, 24)], "g")                                                       # dress
    c.rect(11, 18, 21, 18, "G")
    c.rect(13, 24, 14, 29, "s"); c.rect(18, 24, 19, 29, "s")
    c.px(6, 24, "e"); c.px(26, 20, "e"); c.px(4, 18, "w"); c.px(28, 28, "w")                                   # sparkles
    return _finish(c)


def hawk() -> list[str]:
    c = Canvas()
    c.poly([(13, 12), (0, 8), (1, 20), (6, 17), (9, 24), (13, 20)], "g")
    c.poly([(19, 12), (32, 8), (31, 20), (26, 17), (23, 24), (19, 20)], "g")
    for x in (3, 6, 9):
        c.line(x, 11, x, 17, "G"); c.line(32 - x, 11, 32 - x, 17, "G")
    c.ellipse(16, 17, 5, 8, "g"); c.ellipse(16, 18, 3, 6, "G")
    c.ellipse(16, 8, 4.5, 4.5, "g"); c.rect(12, 4, 20, 5, "G")
    c.poly([(14, 9), (18, 9), (16, 14)], "y")                                                                   # beak
    c.rect(12, 7, 14, 8, "e"); c.rect(18, 7, 20, 8, "e")
    c.poly([(13, 24), (19, 24), (21, 31), (11, 31)], "g")
    c.rect(11, 28, 13, 31, "y"); c.rect(19, 28, 21, 31, "y")
    return _finish(c)


def owl() -> list[str]:
    c = Canvas()
    c.poly([(9, 8), (7, 1), (13, 5)], "g"); c.poly([(23, 8), (25, 1), (19, 5)], "g")                           # ear tufts
    c.ellipse(16, 17, 9, 12, "g"); c.ellipse(16, 8, 8, 6, "g")
    c.poly([(7, 14), (2, 22), (6, 27), (9, 24)], "G"); c.poly([(25, 14), (30, 22), (26, 27), (23, 24)], "G")  # wings
    c.ellipse(12, 9, 3.2, 3.2, "w"); c.ellipse(20, 9, 3.2, 3.2, "w")
    c.rect(11, 8, 13, 10, "e"); c.rect(19, 8, 21, 10, "e")
    c.poly([(15, 11), (17, 11), (16, 14)], "y")
    c.ellipse(16, 20, 5, 7, "G")
    for y in (17, 20, 23):
        c.rect(14, y, 18, y, "g")
    c.rect(11, 28, 14, 31, "y"); c.rect(18, 28, 21, 31, "y")
    return _finish(c)


def shadow_cat() -> list[str]:
    c = Canvas()
    c.poly([(8, 12), (22, 12), (26, 24), (24, 28), (8, 28), (5, 22)], "g")
    c.line(25, 24, 30, 16, "g", 2); c.line(30, 16, 28, 9, "g", 2)                                               # tail
    c.ellipse(12, 10, 6, 5.5, "g")
    c.poly([(6, 7), (7, 0), (12, 5)], "g"); c.poly([(18, 7), (17, 0), (12, 5)], "g")
    c.px(7, 3, "G"); c.px(17, 3, "G")
    c.rect(8, 9, 9, 10, "e"); c.rect(14, 9, 15, 10, "e")
    c.px(11, 12, "w"); c.px(8, 14, "w"); c.px(14, 14, "w")
    c.rect(8, 28, 11, 31, "g"); c.rect(19, 28, 22, 31, "g")
    c.line(10, 16, 10, 26, "G"); c.line(15, 17, 16, 26, "G")
    return _finish(c)


def stone_turtle() -> list[str]:
    c = Canvas()
    c.ellipse(16, 17, 13, 10, "g")                                                                              # shell
    c.poly([(5, 20), (27, 20), (29, 26), (3, 26)], "g")
    for x, y in ((11, 13), (16, 11), (21, 13), (13, 18), (19, 18)):
        c.rect(x - 2, y - 1, x + 2, y + 2, "G")
    c.ellipse(16, 6, 4, 3.5, "s"); c.rect(14, 5, 15, 6, "e"); c.rect(18, 5, 19, 6, "e")
    c.rect(4, 26, 9, 30, "s"); c.rect(23, 26, 28, 30, "s"); c.rect(11, 27, 15, 30, "s"); c.rect(17, 27, 21, 30, "s")
    c.px(8, 16, "m"); c.px(24, 18, "m"); c.px(14, 22, "m")                                                      # moss
    return _finish(c)


def baby_dragon() -> list[str]:
    c = Canvas()
    c.poly([(11, 14), (2, 4), (3, 16), (10, 20)], "d"); c.poly([(21, 14), (30, 4), (29, 16), (22, 20)], "d")   # wings
    c.line(2, 4, 8, 19, "G"); c.line(30, 4, 24, 19, "G")
    c.ellipse(16, 20, 7, 8, "g"); c.ellipse(16, 21, 4, 6, "y")
    c.ellipse(16, 9, 6, 5.5, "g")
    c.poly([(11, 5), (8, 0), (14, 3)], "w"); c.poly([(21, 5), (24, 0), (18, 3)], "w")
    c.rect(12, 8, 14, 9, "e"); c.rect(18, 8, 20, 9, "e")
    c.rect(14, 12, 18, 13, "r"); c.px(15, 11, "w"); c.px(17, 11, "w")
    c.rect(10, 27, 13, 31, "g"); c.rect(19, 27, 22, 31, "g")
    c.line(22, 26, 29, 29, "g", 2)                                                                              # tail
    c.px(16, 13, "r")
    return _finish(c)


# --------------------------------------------------------------------------- adaptive hero
# armor key -> (main, light, dark, trim, glow, helm style, pauldron size, cape, shield style, pattern)
ARMOR_LOOK = {
    None: ("#6a5a48", "#6a5a48", "#3a2f26", "#3a2f26", "#ff9a2e", "none", 0, False, None, None),
    "leather_vest": ("#6a4528", "#8a5e38", "#3a2414", "#b8903a", "#ff9a2e", "cap", 1, False, None, "strap"),
    "chainmail": ("#7a8094", "#a6adc0", "#444a5c", "#b8903a", "#ff9a2e", "coif", 2, False, "round", "mail"),
    "plate_armor": ("#7c849a", "#c2cadc", "#3c4152", "#c9a24a", "#ff9a2e", "visor", 3, True, "kite", "plate"),
    "dragon_scale": ("#2f6a38", "#5aa860", "#183a1e", "#c9a24a", "#ffb42e", "horned", 3, True, "kite", "scale"),
    "tower_mail": ("#4a3a62", "#8a74b0", "#221a33", "#e0b84a", "#7dffb0", "crest", 4, True, "tower", "plate"),
    "titan_plate": ("#8a5a2a", "#d9a24a", "#3a2412", "#ffd25a", "#ffe14d", "horned", 4, True, "tower", "plate"),
}
# weapon key -> (blade, highlight, guard, length, width, runes)
WEAPON_LOOK = {
    "wooden_sword": ("#7a5230", "#a07848", "#4a3018", 10, 2, False),
    "iron_sword": ("#8a90a0", "#c2c8d6", "#5a4630", 12, 2, False),
    "steel_blade": ("#aab2c8", "#e4eaf8", "#c9a24a", 13, 2, False),
    "runed_blade": ("#8a96b8", "#d0daf8", "#c9a24a", 14, 2, True),
    "dragon_fang": ("#d8d2bc", "#fffbe8", "#2f6a38", 15, 3, True),
    "tower_blade": ("#d9b44a", "#fff0a8", "#4a3a62", 16, 3, True),
    "stormcaller": ("#5a90e0", "#d0f0ff", "#c9a24a", 16, 3, True),
}
CHARM_COLOURS = {
    "lucky_clover": "#4fcf6a", "time_amulet": "#4ac8e8", "sages_ring": "#b070ff",
    "phoenix_feather": "#ff7a2e", "tower_crown": "#ffd25a", "chrono_amulet": "#7dffe8",
}


def hero_custom(weapon: str | None, armor: str | None, charm: str | None):
    """The hero as he looks with the given gear: returns (rows, palette)."""
    m_, M_, d_, trim, glow, helm, paul, cape, shield, pattern = ARMOR_LOOK.get(armor, ARMOR_LOOK[None])
    pal = {"o": "#0b0912", "s": "#c9a07a", "h": "#4a3322", "b": "#2e2118", "t": "#3d3226",
           "m": m_, "M": M_, "d": d_, "g": trim, "e": glow, "r": "#6e1520",
           "a": CHARM_COLOURS.get(charm or "", "#000000"), "u": "#5a4630", "U": "#8a6a44"}
    wl = WEAPON_LOOK.get(weapon or "")
    if wl:
        pal.update({"w": wl[0], "W": wl[1], "G": wl[2]})
    c = Canvas()
    armoured = armor is not None
    if cape:
        c.poly([(9, 11), (23, 11), (26, 27), (6, 27)], "r")
    # legs and boots
    leg = "d" if armoured and pattern in ("mail", "plate", "scale") else "t"
    c.rect(11, 22, 14, 28, leg); c.rect(17, 22, 20, 28, leg)
    c.rect(10, 28, 14, 30, "b"); c.rect(17, 28, 21, 30, "b")
    # torso
    c.poly([(10, 11), (22, 11), (21, 23), (11, 23)], "m")
    if pattern == "mail":
        for y in range(12, 22):
            for x in range(11, 21):
                if (x + y) % 2 == 0:
                    c.px(x, y, "M")
    elif pattern == "scale":
        for y in range(12, 22, 2):
            for x in range(11 + (y // 2) % 2, 21, 2):
                c.px(x, y, "M")
    elif pattern == "plate":
        c.rect(13, 13, 18, 18, "M"); c.rect(15, 13, 16, 18, "m")
    elif pattern == "strap":
        c.line(11, 12, 20, 21, "g"); c.line(12, 12, 21, 21, "d")
    else:
        c.rect(14, 11, 17, 12, "s")                 # open collar
    c.rect(10, 20, 21, 21, "b"); c.rect(15, 20, 16, 21, "g")
    # arms
    arm = "m" if armoured else "c" if False else "m"
    c.rect(7, 13, 9, 19, arm); c.rect(22, 13, 24, 19, arm)
    c.rect(7, 19, 9, 21, "s" if not armoured or pattern in ("strap", None) else "d")
    c.rect(22, 19, 24, 21, "s" if not armoured or pattern in ("strap", None) else "d")
    # pauldrons
    if paul:
        r = 2.2 + paul * 0.5
        c.ellipse(9, 11, r, r - 0.5, "M"); c.ellipse(23, 11, r, r - 0.5, "M")
        if paul >= 3:
            c.rect(6, 8, 7, 9, "M"); c.rect(25, 8, 26, 9, "M")
            c.px(9, 8, "g"); c.px(23, 8, "g")
    # head
    c.rect(14, 9, 18, 11, "s")
    c.ellipse(16, 6, 4.5, 5, "s")
    c.rect(13, 6, 14, 6, "o"); c.rect(18, 6, 19, 6, "o")          # eyes
    if helm == "none":
        c.rect(11, 2, 21, 4, "h"); c.rect(11, 4, 12, 7, "h"); c.rect(20, 4, 21, 7, "h")
    elif helm == "cap":
        c.ellipse(16, 4, 5.2, 3.2, "m"); c.rect(11, 4, 21, 4, "d")
    elif helm == "coif":
        c.ellipse(16, 5, 5.5, 5.5, "m"); c.rect(13, 5, 19, 9, "s")
        c.rect(13, 6, 14, 6, "o"); c.rect(18, 6, 19, 6, "o")
        c.rect(11, 8, 21, 11, "m")
        for y in range(2, 12):
            for x in range(10, 23):
                if c.get(x, y) == "m" and (x + y) % 2 == 0:
                    c.px(x, y, "M")
    else:
        c.ellipse(16, 5.5, 5.5, 6, "m"); c.rect(11, 5, 21, 9, "m")
        c.rect(12, 6, 20, 7, "d"); c.rect(13, 6, 19, 6, "e")
        c.rect(15, 8, 17, 10, "d")
        if helm == "horned":
            c.line(11, 3, 7, -1, "M", 2); c.line(21, 3, 25, -1, "M", 2)
        if helm == "crest":
            c.rect(14, -1, 18, 2, "r"); c.rect(15, 2, 17, 4, "g")
    if charm == "tower_crown":
        c.rect(12, 1, 20, 2, "a"); c.px(12, 0, "a"); c.px(16, 0, "a"); c.px(20, 0, "a")
    # shield
    if shield == "round":
        c.ellipse(5, 19, 5, 5, "u"); c.ellipse(5, 19, 2, 2, "U"); c.px(5, 19, "g")
    elif shield == "kite":
        c.poly([(1, 13), (9, 13), (9, 23), (5, 28), (1, 23)], "d")
        c.rect(2, 14, 8, 15, "M"); c.rect(4, 14, 5, 25, "g"); c.rect(2, 19, 8, 20, "g")
    elif shield == "tower":
        c.poly([(0, 11), (9, 11), (9, 24), (4, 30), (0, 24)], "d")
        c.rect(1, 12, 8, 13, "M"); c.rect(3, 12, 6, 28, "g"); c.rect(1, 18, 8, 19, "g")
        c.px(4, 21, "e"); c.px(5, 21, "e")
    # weapon (right hand)
    c.rect(23, 19, 25, 21, "s" if not armoured or pattern in ("strap", None) else "d")
    if wl:
        length, width, runes = wl[3], wl[4], wl[5]
        top = 20 - length
        for dx in range(width):
            c.rect(26 + dx, top, 26 + dx, 19, "W" if dx == 0 else "w")
        c.px(26, top - 1, "W")
        c.rect(24, 18, 26 + width, 18, "G")                        # crossguard
        c.rect(26, 20, 26, 22, "b")                                # grip
        c.px(26, 23, "G")
        if runes:
            for y in range(top + 2, 17, 3):
                c.px(26 + width - 1, y, "e")
    # charm pendant
    if charm and charm != "tower_crown":
        c.rect(15, 14, 16, 15, "a"); c.px(15, 13, "g"); c.px(16, 13, "g")
    return c.outline(), pal


DRAWINGS = {
    "hero": hero, "slime": slime, "goblin": goblin, "skeleton": skeleton,
    "dark_knight": dark_knight, "boss": boss, "bat": bat, "wolf": wolf, "treant": treant,
    "witch": witch, "golem": golem, "wraith": wraith, "dragon": dragon,
    "treasure": treasure, "rest": rest,
    "pixie": pixie, "hawk": hawk, "owl": owl, "shadow_cat": shadow_cat,
    "stone_turtle": stone_turtle, "baby_dragon": baby_dragon,
}

# Darker, grittier palettes (letters keep their meaning so recolours still work).
PALETTES = {
    "hero": {"o": "#0b0912", "h": "#6a7186", "H": "#b4bccf", "K": "#3c4152", "r": "#6e1520",
             "e": "#ff9a2e", "g": "#b8903a", "b": "#2e2118", "s": "#8a6a4a"},
    "slime": {"o": "#0b0912", "g": "#2f6a3a", "G": "#7bc07b", "w": "#e8ffe8", "e": "#b6ff3a"},
    "goblin": {"o": "#0b0912", "g": "#48642e", "G": "#7a9854", "y": "#b8943a", "e": "#ff5a2e",
               "w": "#d8d0b8", "b": "#47301a"},
    "skeleton": {"o": "#0b0912", "w": "#c4bca2", "d": "#6e6856", "e": "#ff3b2e"},
    "dark_knight": {"o": "#0b0912", "b": "#2e2118", "k": "#22242f", "K": "#555972",
                    "r": "#ff3b2e", "p": "#6a1626"},
    "boss": {"o": "#0b0912", "R": "#7a1616", "r": "#3f0c0c", "y": "#d9ccb0", "e": "#ffd23a",
             "w": "#ddd2b8"},
    "bat": {"o": "#0b0912", "p": "#3a2458", "P": "#684a96", "r": "#ff3b2e", "w": "#e8e0c8"},
    "wolf": {"o": "#0b0912", "g": "#464a5c", "G": "#858aa0", "w": "#e8e0c8", "y": "#d9b44a",
             "e": "#ff4a2e", "r": "#a82828"},
    "treant": {"o": "#0b0912", "b": "#3a2612", "B": "#664422", "g": "#1f4a26", "G": "#3f7a3a",
               "y": "#d9b44a", "e": "#ff9a2e"},
    "witch": {"o": "#0b0912", "p": "#2f1a4d", "P": "#66409a", "g": "#5a8a5a", "y": "#b8903a",
              "e": "#7dff6a", "w": "#e8e0c8"},
    "golem": {"o": "#0b0912", "i": "#5f8aa2", "I": "#b0d4e6", "b": "#2e5670", "e": "#5aa0ff",
              "w": "#e8f4ff"},
    "wraith": {"o": "#0b0912", "c": "#334270", "C": "#7a90c8", "e": "#7dffb0", "k": "#141a34"},
    "dragon": {"o": "#0b0912", "g": "#27582f", "G": "#4f9456", "y": "#b8903a", "r": "#ff6a1f",
               "e": "#ffb42e", "w": "#e0d6bc", "d": "#183a1e"},
    "treasure": {"o": "#0b0912", "b": "#6a3e1a", "y": "#d9b44a"},
    "rest": {"o": "#0b0912", "b": "#4a2e18", "y": "#ffd25a", "r": "#e8501a"},
    "pixie": {"o": "#0b0912", "w": "#bfe8ff", "b": "#6a9ac8", "s": "#e8c9a0", "h": "#d94a8a",
              "g": "#3fae7a", "G": "#8fe8b8", "e": "#ff3b2e"},
    "hawk": {"o": "#0b0912", "g": "#6a4a2a", "G": "#c9a46a", "y": "#e0b83a", "e": "#ff9a2e"},
    "owl": {"o": "#0b0912", "g": "#7a6a52", "G": "#c9b896", "w": "#f2ecd8", "y": "#d9a43a",
            "e": "#ffb42e"},
    "shadow_cat": {"o": "#0b0912", "g": "#2a2638", "G": "#5a5478", "e": "#7dffb0", "w": "#e8e0c8"},
    "stone_turtle": {"o": "#0b0912", "g": "#5a6270", "G": "#9aa4b4", "s": "#6a7a52", "e": "#ffb42e",
                     "m": "#4f8f4a"},
    "baby_dragon": {"o": "#0b0912", "g": "#a83a2a", "G": "#e0644a", "y": "#e0b86a", "d": "#6a1e1e",
                    "r": "#ff6a1f", "e": "#ffd23a", "w": "#e8e0c8"},
}
