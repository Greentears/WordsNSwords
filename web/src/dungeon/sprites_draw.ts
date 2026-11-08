// Procedurally drawn 32x32 sprites (port of dungeon/sprites_draw.py). Rows are strings of palette
// characters; "." is transparent and "o" the outline. `sprites.ts` adds lighting, grit and glowing eyes.
import { pyInt, pyRound } from "./util";
import { ARMOR_LOOK, CHARM_COLOURS, DEFAULT_ARMOR_LOOK, WEAPON_LOOK, type Palette } from "./sprites_art";

export const N = 32;

type Pt = readonly [number, number];

export class Canvas {
  g: string[][] = Array.from({ length: N }, () => new Array<string>(N).fill("."));

  px(x: number, y: number, c: string): void {
    if (0 <= x && x < N && 0 <= y && y < N) this.g[y][x] = c;
  }

  get(x: number, y: number): string {
    return 0 <= x && x < N && 0 <= y && y < N ? this.g[y][x] : ".";
  }

  rect(x0: number, y0: number, x1: number, y1: number, c: string): void {
    for (let y = y0; y <= y1; y++) for (let x = x0; x <= x1; x++) this.px(x, y, c);
  }

  ellipse(cx: number, cy: number, rx: number, ry: number, c: string): void {
    for (let y = pyInt(cy - ry) - 1; y < pyInt(cy + ry) + 2; y++) {
      for (let x = pyInt(cx - rx) - 1; x < pyInt(cx + rx) + 2; x++) {
        const a = (x - cx) / rx, b = (y - cy) / ry;
        if (a * a + b * b <= 1.0) this.px(x, y, c);
      }
    }
  }

  poly(pts: readonly Pt[], c: string): void {
    const n = pts.length;
    const ys = pts.map((p) => p[1]);
    const yMax = Math.max(...ys);
    for (let y = Math.min(...ys); y <= yMax; y++) {
      const xs: number[] = [];
      for (let i = 0; i < n; i++) {
        const [x1, y1] = pts[i], [x2, y2] = pts[(i + 1) % n];
        if ((y1 <= y && y < y2) || (y2 <= y && y < y1)) xs.push(x1 + ((y - y1) * (x2 - x1)) / (y2 - y1));
      }
      xs.sort((p, q) => p - q);
      for (let k = 0; k + 1 < xs.length; k += 2) {
        const hi = pyRound(xs[k + 1]);
        for (let x = pyRound(xs[k]); x <= hi; x++) this.px(x, y, c);
      }
    }
  }

  line(x0: number, y0: number, x1: number, y1: number, c: string, w = 1): void {
    const steps = Math.max(Math.abs(x1 - x0), Math.abs(y1 - y0), 1);
    for (let i = 0; i <= steps; i++) {
      const x = pyRound(x0 + ((x1 - x0) * i) / steps);
      const y = pyRound(y0 + ((y1 - y0) * i) / steps);
      for (let dx = 0; dx < w; dx++) this.px(x + dx, y, c);
    }
  }

  /** Copy the left half onto the right (for the symmetric parts of a figure). */
  mirror(): void {
    for (let y = 0; y < N; y++) for (let x = 0; x < N / 2; x++) if (this.g[y][x] !== ".") this.g[y][N - 1 - x] = this.g[y][x];
  }

  outline(): string[] {
    const out = this.g.map((row) => row.slice());
    for (let y = 0; y < N; y++) {
      for (let x = 0; x < N; x++) {
        if (this.g[y][x] === ".") {
          const solid = (dx: number, dy: number) => { const ch = this.get(x + dx, y + dy); return ch !== "." && ch !== "o"; };
          if (solid(1, 0) || solid(-1, 0) || solid(0, 1) || solid(0, -1)) out[y][x] = "o";
        }
      }
    }
    return out.map((r) => r.join(""));
  }
}

const finish = (c: Canvas): string[] => c.outline();

// --------------------------------------------------------------------------- hero
function hero(): string[] {
  const c = new Canvas();
  c.poly([[9, 11], [23, 11], [26, 27], [6, 27]], "r");
  c.rect(11, 22, 14, 28, "K"); c.rect(17, 22, 20, 28, "K");
  c.rect(10, 28, 14, 30, "b"); c.rect(17, 28, 21, 30, "b");
  c.poly([[10, 11], [22, 11], [21, 23], [11, 23]], "h");
  c.rect(13, 13, 18, 18, "H"); c.rect(10, 20, 21, 21, "b"); c.rect(15, 20, 16, 21, "g");
  c.ellipse(9, 11, 3.5, 3, "H"); c.ellipse(23, 11, 3.5, 3, "K");
  c.rect(6, 9, 7, 10, "H"); c.rect(24, 9, 25, 10, "K");
  c.ellipse(16, 6, 5, 5.5, "h"); c.rect(11, 6, 21, 8, "h");
  c.rect(12, 6, 20, 6, "K"); c.rect(13, 6, 19, 6, "e");
  c.rect(15, 2, 17, 4, "H");
  c.line(11, 3, 8, 0, "H"); c.line(21, 3, 24, 0, "H");
  c.rect(7, 13, 9, 19, "K");
  c.poly([[2, 15], [10, 15], [10, 24], [6, 28], [2, 24]], "K");
  c.rect(3, 16, 9, 17, "h"); c.rect(5, 16, 6, 24, "g"); c.rect(3, 19, 9, 20, "g");
  c.rect(22, 13, 24, 19, "h"); c.rect(23, 19, 25, 21, "b");
  c.rect(26, 20, 26, 21, "g"); c.rect(24, 17, 28, 17, "g");
  c.rect(26, 2, 27, 17, "H"); c.rect(27, 3, 27, 16, "h"); c.px(26, 1, "H");
  return finish(c);
}

// --------------------------------------------------------------------------- monsters
function slime(): string[] {
  const c = new Canvas();
  c.poly([[5, 28], [7, 17], [11, 11], [16, 8], [21, 11], [25, 17], [27, 28]], "g");
  c.ellipse(16, 21, 11, 8, "g");
  c.ellipse(13, 14, 4, 3, "G");
  c.ellipse(11, 20, 2.2, 3, "w"); c.ellipse(21, 20, 2.2, 3, "w");
  c.rect(10, 20, 12, 22, "e"); c.rect(20, 20, 22, 22, "e");
  c.rect(12, 26, 20, 26, "o");
  for (const x of [13, 16, 19]) c.rect(x, 26, x, 27, "w");
  c.rect(4, 28, 28, 29, "g");
  for (const x of [7, 14, 24]) c.rect(x, 29, x + 1, 30, "g");
  return finish(c);
}

function goblin(): string[] {
  const c = new Canvas();
  c.poly([[7, 10], [1, 5], [11, 8]], "g"); c.poly([[25, 10], [31, 5], [21, 8]], "g");
  c.ellipse(16, 10, 6, 6, "g");
  c.rect(11, 9, 14, 10, "e"); c.rect(18, 9, 21, 10, "e");
  c.rect(12, 14, 20, 15, "o"); c.px(13, 15, "w"); c.px(15, 15, "w"); c.px(17, 15, "w"); c.px(19, 15, "w");
  c.poly([[9, 17], [23, 17], [24, 27], [8, 27]], "b");
  c.rect(9, 22, 23, 23, "y");
  c.rect(5, 18, 8, 20, "g"); c.rect(24, 18, 27, 20, "g");
  c.rect(3, 12, 4, 21, "b"); c.poly([[1, 9], [6, 9], [3, 14]], "w");
  c.rect(26, 21, 30, 22, "w"); c.rect(25, 20, 26, 23, "b");
  c.rect(10, 27, 13, 30, "g"); c.rect(19, 27, 22, 30, "g");
  return finish(c);
}

function skeleton(): string[] {
  const c = new Canvas();
  c.ellipse(16, 6, 5, 5, "w"); c.rect(12, 9, 20, 11, "w");
  c.rect(11, 5, 14, 8, "o"); c.rect(18, 5, 21, 8, "o");
  c.rect(12, 6, 13, 7, "e"); c.rect(19, 6, 20, 7, "e");
  c.px(16, 9, "o"); c.px(15, 10, "o"); c.px(17, 10, "o");
  for (const x of [13, 15, 17, 19]) c.rect(x, 11, x, 12, "o");
  c.rect(15, 13, 16, 22, "d");
  for (const y of [14, 16, 18, 20]) { c.rect(10, y, 21, y, "w"); c.rect(11, y + 1, 20, y + 1, "d"); }
  c.rect(8, 13, 11, 14, "w"); c.rect(21, 13, 24, 14, "w");
  c.rect(7, 15, 8, 24, "w"); c.rect(24, 15, 25, 21, "w");
  c.rect(11, 22, 20, 24, "d"); c.rect(13, 24, 18, 24, "w");
  c.rect(12, 25, 13, 30, "w"); c.rect(18, 25, 19, 30, "w");
  c.rect(11, 30, 14, 30, "d"); c.rect(17, 30, 20, 30, "d");
  c.rect(26, 8, 26, 22, "d"); c.poly([[24, 8], [28, 8], [26, 2]], "w");
  c.line(4, 22, 7, 14, "d", 2);
  return finish(c);
}

function darkKnight(): string[] {
  const c = new Canvas();
  c.poly([[8, 12], [24, 12], [27, 30], [5, 30]], "p");
  c.poly([[10, 11], [22, 11], [21, 24], [11, 24]], "k");
  c.rect(14, 14, 17, 19, "K");
  c.rect(10, 22, 21, 23, "b");
  c.rect(11, 24, 14, 29, "k"); c.rect(17, 24, 20, 29, "k"); c.rect(10, 29, 14, 30, "K"); c.rect(17, 29, 21, 30, "K");
  c.ellipse(8, 11, 4, 3.5, "K"); c.ellipse(24, 11, 4, 3.5, "K");
  for (const x of [5, 7, 9]) { c.px(x, 7, "K"); c.px(x, 8, "K"); }
  for (const x of [23, 25, 27]) { c.px(x, 7, "K"); c.px(x, 8, "K"); }
  c.ellipse(16, 6, 5, 5.5, "k"); c.rect(12, 5, 20, 7, "k");
  c.rect(13, 6, 19, 6, "r");
  c.poly([[13, 1], [19, 1], [17, -3], [15, -3]], "p");
  c.rect(7, 13, 9, 20, "k"); c.rect(23, 13, 25, 20, "k");
  c.rect(27, 6, 28, 22, "K"); c.rect(25, 20, 30, 21, "b"); c.rect(27, 22, 28, 24, "b");
  c.px(27, 5, "K"); c.px(28, 4, "K");
  return finish(c);
}

function boss(): string[] {
  const c = new Canvas();
  c.poly([[2, 24], [6, 12], [10, 16], [8, 28]], "r"); c.poly([[30, 24], [26, 12], [22, 16], [24, 28]], "r");
  c.poly([[8, 12], [24, 12], [26, 26], [22, 30], [10, 30], [6, 26]], "R");
  c.rect(13, 16, 19, 24, "r"); c.line(16, 14, 16, 26, "o");
  c.ellipse(16, 8, 6, 5.5, "R");
  c.poly([[9, 6], [4, 0], [12, 4]], "w"); c.poly([[23, 6], [28, 0], [20, 4]], "w");
  c.rect(11, 6, 14, 7, "e"); c.rect(18, 6, 21, 7, "e");
  c.rect(12, 11, 20, 12, "o");
  for (const x of [12, 14, 16, 18, 20]) c.rect(x, 12, x, 13, "w");
  c.rect(3, 18, 8, 22, "R"); c.rect(24, 18, 29, 22, "R");
  for (const x of [3, 5, 7]) c.rect(x, 23, x, 25, "w");
  for (const x of [24, 26, 28]) c.rect(x, 23, x, 25, "w");
  return finish(c);
}

function bat(): string[] {
  const c = new Canvas();
  c.poly([[14, 12], [1, 6], [3, 14], [6, 13], [7, 19], [11, 16], [14, 22]], "p");
  c.poly([[18, 12], [31, 6], [29, 14], [26, 13], [25, 19], [21, 16], [18, 22]], "p");
  c.line(14, 12, 3, 9, "P"); c.line(18, 12, 29, 9, "P");
  c.ellipse(16, 15, 4, 6, "p"); c.ellipse(16, 9, 4, 4, "p");
  c.poly([[12, 8], [11, 1], [15, 6]], "p"); c.poly([[20, 8], [21, 1], [17, 6]], "p");
  c.rect(13, 9, 14, 10, "r"); c.rect(18, 9, 19, 10, "r");
  c.px(15, 12, "w"); c.px(17, 12, "w");
  c.line(14, 22, 13, 25, "P"); c.line(18, 22, 19, 25, "P");
  return finish(c);
}

function wolf(): string[] {
  const c = new Canvas();
  c.poly([[4, 12], [14, 10], [22, 12], [26, 20], [22, 26], [6, 26]], "g");
  c.poly([[22, 14], [30, 10], [31, 18], [27, 20]], "g");
  c.poly([[22, 8], [28, 3], [27, 10]], "G"); c.poly([[13, 8], [14, 3], [18, 7]], "G");
  c.ellipse(11, 12, 7, 6, "G"); c.poly([[1, 14], [6, 12], [6, 17], [1, 17]], "G");
  c.rect(1, 17, 7, 18, "o"); c.px(2, 18, "w"); c.px(4, 18, "w"); c.px(6, 18, "w");
  c.px(1, 14, "o"); c.px(2, 14, "o");
  c.rect(8, 10, 10, 11, "e");
  c.rect(7, 26, 9, 30, "g"); c.rect(11, 26, 13, 30, "g"); c.rect(20, 26, 22, 30, "g"); c.rect(24, 24, 26, 30, "g");
  c.line(9, 19, 11, 24, "r", 2);
  return finish(c);
}

function treant(): string[] {
  const c = new Canvas();
  c.poly([[9, 12], [23, 12], [24, 28], [8, 28]], "b");
  for (const x of [11, 15, 19]) c.line(x, 13, x + 1, 27, "B");
  c.ellipse(16, 6, 9, 5.5, "g"); c.ellipse(9, 7, 5, 4, "G"); c.ellipse(23, 6, 5, 4, "g");
  c.rect(11, 12, 14, 14, "o"); c.rect(18, 12, 21, 14, "o"); c.rect(12, 13, 13, 13, "e"); c.rect(19, 13, 20, 13, "e");
  c.rect(13, 18, 19, 20, "o"); c.rect(14, 20, 18, 21, "o");
  c.poly([[8, 14], [1, 22], [3, 26], [8, 20]], "b"); c.poly([[24, 14], [31, 22], [29, 26], [24, 20]], "b");
  c.rect(0, 25, 3, 27, "B"); c.rect(28, 25, 31, 27, "B");
  c.poly([[8, 28], [4, 31], [12, 31]], "b"); c.poly([[24, 28], [28, 31], [20, 31]], "b");
  c.px(7, 3, "y"); c.px(24, 4, "y");
  return finish(c);
}

function witch(): string[] {
  const c = new Canvas();
  c.poly([[16, -4], [21, 8], [11, 8]], "p");
  c.poly([[16, 0], [18, 3], [14, 3]], "p");
  c.rect(6, 7, 26, 8, "p"); c.rect(11, 6, 21, 6, "y");
  c.ellipse(16, 12, 4.5, 4.5, "g");
  c.rect(12, 11, 14, 12, "e"); c.rect(18, 11, 20, 12, "e");
  c.px(16, 14, "o"); c.px(15, 15, "o"); c.px(17, 15, "o");
  c.poly([[11, 16], [21, 16], [26, 31], [6, 31]], "p");
  c.rect(15, 17, 17, 30, "P"); c.rect(11, 22, 21, 22, "y");
  c.rect(8, 17, 10, 23, "p"); c.rect(5, 22, 8, 24, "g");
  c.rect(24, 17, 26, 22, "p"); c.rect(25, 22, 27, 23, "g");
  c.rect(29, 6, 29, 29, "y"); c.ellipse(29, 5, 2, 2.5, "e");
  return finish(c);
}

function golem(): string[] {
  const c = new Canvas();
  c.poly([[7, 11], [25, 11], [28, 24], [22, 29], [10, 29], [4, 24]], "i");
  c.rect(11, 14, 21, 22, "b"); c.poly([[12, 15], [20, 15], [16, 22]], "I");
  c.rect(10, 3, 22, 10, "i"); c.rect(11, 2, 21, 2, "I");
  c.rect(12, 5, 14, 6, "e"); c.rect(18, 5, 20, 6, "e");
  c.rect(2, 12, 7, 24, "i"); c.rect(25, 12, 30, 24, "i");
  c.rect(1, 22, 8, 27, "I"); c.rect(24, 22, 31, 27, "I");
  for (const x of [3, 5, 7]) c.px(x, 11, "I");
  for (const x of [25, 27, 29]) c.px(x, 11, "I");
  c.rect(10, 29, 14, 31, "b"); c.rect(18, 29, 22, 31, "b");
  c.line(8, 14, 10, 20, "o"); c.line(23, 16, 21, 24, "o");
  return finish(c);
}

function wraith(): string[] {
  const c = new Canvas();
  c.poly([[16, 1], [22, 6], [23, 14], [28, 31], [4, 31], [9, 14], [10, 6]], "c");
  c.ellipse(16, 10, 5, 6, "k");
  c.rect(12, 9, 14, 10, "e"); c.rect(18, 9, 20, 10, "e");
  c.poly([[8, 18], [1, 26], [4, 28], [10, 24]], "C"); c.poly([[24, 18], [31, 26], [28, 28], [22, 24]], "C");
  for (const x of [6, 10, 14, 18, 22, 26]) c.poly([[x - 2, 29], [x + 2, 29], [x, 31]], "c");
  c.line(14, 16, 12, 28, "C"); c.line(19, 16, 21, 28, "C");
  return finish(c);
}

function dragon(): string[] {
  const c = new Canvas();
  c.poly([[1, 22], [6, 8], [12, 14], [10, 24]], "d"); c.poly([[31, 22], [26, 8], [20, 14], [22, 24]], "d");
  c.line(6, 8, 10, 24, "G"); c.line(26, 8, 22, 24, "G");
  c.poly([[9, 14], [23, 14], [25, 28], [21, 31], [11, 31], [7, 28]], "g");
  c.poly([[13, 18], [19, 18], [20, 29], [12, 29]], "y");
  for (const y of [20, 23, 26]) c.rect(13, y, 19, y, "G");
  c.poly([[11, 12], [21, 12], [19, 4], [13, 4]], "g");
  c.poly([[13, 4], [19, 4], [18, 0], [14, 0]], "g");
  c.poly([[11, 5], [7, 0], [13, 3]], "w"); c.poly([[21, 5], [25, 0], [19, 3]], "w");
  c.rect(12, 7, 14, 8, "e"); c.rect(18, 7, 20, 8, "e");
  c.rect(14, 10, 18, 12, "r"); c.px(15, 10, "w"); c.px(17, 10, "w");
  c.rect(8, 28, 10, 31, "g"); c.rect(22, 28, 24, 31, "g");
  return finish(c);
}

function treasure(): string[] {
  const c = new Canvas();
  c.rect(5, 14, 26, 18, "b"); c.rect(5, 19, 26, 27, "b");
  c.rect(5, 18, 26, 18, "o"); c.rect(5, 14, 26, 14, "y"); c.rect(5, 27, 26, 27, "y");
  c.rect(7, 14, 8, 27, "y"); c.rect(23, 14, 24, 27, "y");
  c.rect(14, 17, 17, 22, "y"); c.rect(15, 19, 16, 20, "o");
  return finish(c);
}

function rest(): string[] {
  const c = new Canvas();
  c.line(7, 30, 25, 26, "b", 2); c.line(7, 26, 25, 30, "b", 2);
  c.poly([[16, 4], [22, 14], [24, 24], [16, 27], [8, 24], [10, 14]], "r");
  c.poly([[16, 11], [20, 19], [21, 24], [16, 26], [11, 24], [12, 19]], "y");
  return finish(c);
}

// --------------------------------------------------------------------------- companions
function pixie(): string[] {
  const c = new Canvas();
  c.poly([[14, 14], [3, 4], [2, 14], [13, 19]], "w"); c.poly([[18, 14], [29, 4], [30, 14], [19, 19]], "w");
  c.line(14, 14, 4, 6, "b"); c.line(18, 14, 28, 6, "b");
  c.ellipse(16, 8, 4, 4.5, "s"); c.rect(11, 3, 21, 5, "h"); c.poly([[11, 4], [9, 12], [12, 9]], "h");
  c.rect(13, 8, 14, 9, "e"); c.rect(18, 8, 19, 9, "e");
  c.poly([[12, 13], [20, 13], [22, 24], [10, 24]], "g");
  c.rect(11, 18, 21, 18, "G");
  c.rect(13, 24, 14, 29, "s"); c.rect(18, 24, 19, 29, "s");
  c.px(6, 24, "e"); c.px(26, 20, "e"); c.px(4, 18, "w"); c.px(28, 28, "w");
  return finish(c);
}

function hawk(): string[] {
  const c = new Canvas();
  c.poly([[13, 12], [0, 8], [1, 20], [6, 17], [9, 24], [13, 20]], "g");
  c.poly([[19, 12], [32, 8], [31, 20], [26, 17], [23, 24], [19, 20]], "g");
  for (const x of [3, 6, 9]) { c.line(x, 11, x, 17, "G"); c.line(32 - x, 11, 32 - x, 17, "G"); }
  c.ellipse(16, 17, 5, 8, "g"); c.ellipse(16, 18, 3, 6, "G");
  c.ellipse(16, 8, 4.5, 4.5, "g"); c.rect(12, 4, 20, 5, "G");
  c.poly([[14, 9], [18, 9], [16, 14]], "y");
  c.rect(12, 7, 14, 8, "e"); c.rect(18, 7, 20, 8, "e");
  c.poly([[13, 24], [19, 24], [21, 31], [11, 31]], "g");
  c.rect(11, 28, 13, 31, "y"); c.rect(19, 28, 21, 31, "y");
  return finish(c);
}

function owl(): string[] {
  const c = new Canvas();
  c.poly([[9, 8], [7, 1], [13, 5]], "g"); c.poly([[23, 8], [25, 1], [19, 5]], "g");
  c.ellipse(16, 17, 9, 12, "g"); c.ellipse(16, 8, 8, 6, "g");
  c.poly([[7, 14], [2, 22], [6, 27], [9, 24]], "G"); c.poly([[25, 14], [30, 22], [26, 27], [23, 24]], "G");
  c.ellipse(12, 9, 3.2, 3.2, "w"); c.ellipse(20, 9, 3.2, 3.2, "w");
  c.rect(11, 8, 13, 10, "e"); c.rect(19, 8, 21, 10, "e");
  c.poly([[15, 11], [17, 11], [16, 14]], "y");
  c.ellipse(16, 20, 5, 7, "G");
  for (const y of [17, 20, 23]) c.rect(14, y, 18, y, "g");
  c.rect(11, 28, 14, 31, "y"); c.rect(18, 28, 21, 31, "y");
  return finish(c);
}

function shadowCat(): string[] {
  const c = new Canvas();
  c.poly([[8, 12], [22, 12], [26, 24], [24, 28], [8, 28], [5, 22]], "g");
  c.line(25, 24, 30, 16, "g", 2); c.line(30, 16, 28, 9, "g", 2);
  c.ellipse(12, 10, 6, 5.5, "g");
  c.poly([[6, 7], [7, 0], [12, 5]], "g"); c.poly([[18, 7], [17, 0], [12, 5]], "g");
  c.px(7, 3, "G"); c.px(17, 3, "G");
  c.rect(8, 9, 9, 10, "e"); c.rect(14, 9, 15, 10, "e");
  c.px(11, 12, "w"); c.px(8, 14, "w"); c.px(14, 14, "w");
  c.rect(8, 28, 11, 31, "g"); c.rect(19, 28, 22, 31, "g");
  c.line(10, 16, 10, 26, "G"); c.line(15, 17, 16, 26, "G");
  return finish(c);
}

function stoneTurtle(): string[] {
  const c = new Canvas();
  c.ellipse(16, 17, 13, 10, "g");
  c.poly([[5, 20], [27, 20], [29, 26], [3, 26]], "g");
  for (const [x, y] of [[11, 13], [16, 11], [21, 13], [13, 18], [19, 18]]) c.rect(x - 2, y - 1, x + 2, y + 2, "G");
  c.ellipse(16, 6, 4, 3.5, "s"); c.rect(14, 5, 15, 6, "e"); c.rect(18, 5, 19, 6, "e");
  c.rect(4, 26, 9, 30, "s"); c.rect(23, 26, 28, 30, "s"); c.rect(11, 27, 15, 30, "s"); c.rect(17, 27, 21, 30, "s");
  c.px(8, 16, "m"); c.px(24, 18, "m"); c.px(14, 22, "m");
  return finish(c);
}

function babyDragon(): string[] {
  const c = new Canvas();
  c.poly([[11, 14], [2, 4], [3, 16], [10, 20]], "d"); c.poly([[21, 14], [30, 4], [29, 16], [22, 20]], "d");
  c.line(2, 4, 8, 19, "G"); c.line(30, 4, 24, 19, "G");
  c.ellipse(16, 20, 7, 8, "g"); c.ellipse(16, 21, 4, 6, "y");
  c.ellipse(16, 9, 6, 5.5, "g");
  c.poly([[11, 5], [8, 0], [14, 3]], "w"); c.poly([[21, 5], [24, 0], [18, 3]], "w");
  c.rect(12, 8, 14, 9, "e"); c.rect(18, 8, 20, 9, "e");
  c.rect(14, 12, 18, 13, "r"); c.px(15, 11, "w"); c.px(17, 11, "w");
  c.rect(10, 27, 13, 31, "g"); c.rect(19, 27, 22, 31, "g");
  c.line(22, 26, 29, 29, "g", 2);
  c.px(16, 13, "r");
  return finish(c);
}

// --------------------------------------------------------------------------- adaptive hero
/** The hero as he looks with the given gear: returns (rows, palette). */
export function heroCustom(weapon?: string | null, armor?: string | null, charm?: string | null): [string[], Palette] {
  const [m_, M_, d_, trim, glow, helm, paul, cape, shield, pattern] =
    (armor != null ? ARMOR_LOOK.get(armor) : undefined) ?? DEFAULT_ARMOR_LOOK;
  const pal: Palette = {
    o: "#0b0912", s: "#c9a07a", h: "#4a3322", b: "#2e2118", t: "#3d3226",
    m: m_, M: M_, d: d_, g: trim, e: glow, r: "#6e1520",
    a: CHARM_COLOURS.get(charm || "") ?? "#000000", u: "#5a4630", U: "#8a6a44",
  };
  const wl = WEAPON_LOOK.get(weapon || "");
  if (wl) { pal.w = wl[0]; pal.W = wl[1]; pal.G = wl[2]; }
  const c = new Canvas();
  const armoured = armor != null;
  if (cape) c.poly([[9, 11], [23, 11], [26, 27], [6, 27]], "r");
  // legs and boots
  const leg = armoured && (pattern === "mail" || pattern === "plate" || pattern === "scale") ? "d" : "t";
  c.rect(11, 22, 14, 28, leg); c.rect(17, 22, 20, 28, leg);
  c.rect(10, 28, 14, 30, "b"); c.rect(17, 28, 21, 30, "b");
  // torso
  c.poly([[10, 11], [22, 11], [21, 23], [11, 23]], "m");
  if (pattern === "mail") {
    for (let y = 12; y < 22; y++) for (let x = 11; x < 21; x++) if ((x + y) % 2 === 0) c.px(x, y, "M");
  } else if (pattern === "scale") {
    for (let y = 12; y < 22; y += 2) for (let x = 11 + (Math.floor(y / 2) % 2); x < 21; x += 2) c.px(x, y, "M");
  } else if (pattern === "plate") {
    c.rect(13, 13, 18, 18, "M"); c.rect(15, 13, 16, 18, "m");
  } else if (pattern === "strap") {
    c.line(11, 12, 20, 21, "g"); c.line(12, 12, 21, 21, "d");
  } else {
    c.rect(14, 11, 17, 12, "s");                 // open collar
  }
  c.rect(10, 20, 21, 21, "b"); c.rect(15, 20, 16, 21, "g");
  // arms
  const bare = !armoured || pattern === "strap" || pattern === null;
  c.rect(7, 13, 9, 19, "m"); c.rect(22, 13, 24, 19, "m");
  c.rect(7, 19, 9, 21, bare ? "s" : "d");
  c.rect(22, 19, 24, 21, bare ? "s" : "d");
  // pauldrons
  if (paul) {
    const r = 2.2 + paul * 0.5;
    c.ellipse(9, 11, r, r - 0.5, "M"); c.ellipse(23, 11, r, r - 0.5, "M");
    if (paul >= 3) {
      c.rect(6, 8, 7, 9, "M"); c.rect(25, 8, 26, 9, "M");
      c.px(9, 8, "g"); c.px(23, 8, "g");
    }
  }
  // head
  c.rect(14, 9, 18, 11, "s");
  c.ellipse(16, 6, 4.5, 5, "s");
  c.rect(13, 6, 14, 6, "o"); c.rect(18, 6, 19, 6, "o");          // eyes
  if (helm === "none") {
    c.rect(11, 2, 21, 4, "h"); c.rect(11, 4, 12, 7, "h"); c.rect(20, 4, 21, 7, "h");
  } else if (helm === "cap") {
    c.ellipse(16, 4, 5.2, 3.2, "m"); c.rect(11, 4, 21, 4, "d");
  } else if (helm === "coif") {
    c.ellipse(16, 5, 5.5, 5.5, "m"); c.rect(13, 5, 19, 9, "s");
    c.rect(13, 6, 14, 6, "o"); c.rect(18, 6, 19, 6, "o");
    c.rect(11, 8, 21, 11, "m");
    for (let y = 2; y < 12; y++) for (let x = 10; x < 23; x++) if (c.get(x, y) === "m" && (x + y) % 2 === 0) c.px(x, y, "M");
  } else {
    c.ellipse(16, 5.5, 5.5, 6, "m"); c.rect(11, 5, 21, 9, "m");
    c.rect(12, 6, 20, 7, "d"); c.rect(13, 6, 19, 6, "e");
    c.rect(15, 8, 17, 10, "d");
    if (helm === "horned") { c.line(11, 3, 7, -1, "M", 2); c.line(21, 3, 25, -1, "M", 2); }
    if (helm === "crest") { c.rect(14, -1, 18, 2, "r"); c.rect(15, 2, 17, 4, "g"); }
  }
  if (charm === "tower_crown") {
    c.rect(12, 1, 20, 2, "a"); c.px(12, 0, "a"); c.px(16, 0, "a"); c.px(20, 0, "a");
  }
  // shield
  if (shield === "round") {
    c.ellipse(5, 19, 5, 5, "u"); c.ellipse(5, 19, 2, 2, "U"); c.px(5, 19, "g");
  } else if (shield === "kite") {
    c.poly([[1, 13], [9, 13], [9, 23], [5, 28], [1, 23]], "d");
    c.rect(2, 14, 8, 15, "M"); c.rect(4, 14, 5, 25, "g"); c.rect(2, 19, 8, 20, "g");
  } else if (shield === "tower") {
    c.poly([[0, 11], [9, 11], [9, 24], [4, 30], [0, 24]], "d");
    c.rect(1, 12, 8, 13, "M"); c.rect(3, 12, 6, 28, "g"); c.rect(1, 18, 8, 19, "g");
    c.px(4, 21, "e"); c.px(5, 21, "e");
  }
  // weapon (right hand)
  c.rect(23, 19, 25, 21, bare ? "s" : "d");
  if (wl) {
    const length = wl[3], width = wl[4], runes = wl[5];
    const top = 20 - length;
    for (let dx = 0; dx < width; dx++) c.rect(26 + dx, top, 26 + dx, 19, dx === 0 ? "W" : "w");
    c.px(26, top - 1, "W");
    c.rect(24, 18, 26 + width, 18, "G");                        // crossguard
    c.rect(26, 20, 26, 22, "b");                                // grip
    c.px(26, 23, "G");
    if (runes) for (let y = top + 2; y < 17; y += 3) c.px(26 + width - 1, y, "e");
  }
  // charm pendant
  if (charm && charm !== "tower_crown") {
    c.rect(15, 14, 16, 15, "a"); c.px(15, 13, "g"); c.px(16, 13, "g");
  }
  return [c.outline(), pal];
}

export const DRAWINGS: Readonly<Record<string, () => string[]>> = {
  hero, slime, goblin, skeleton, dark_knight: darkKnight, boss, bat, wolf, treant,
  witch, golem, wraith, dragon, treasure, rest,
  pixie, hawk, owl, shadow_cat: shadowCat, stone_turtle: stoneTurtle, baby_dragon: babyDragon,
};
