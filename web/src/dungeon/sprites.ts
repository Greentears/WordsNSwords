// Pixel-art sprites (port of dungeon/sprites.py): 32x32 colour grids ("#rrggbb" or null for transparent)
// for monsters, companions and the hero (whose look depends on the equipped gear). UI-free.
import { pyRound } from "./util";
import { ALIASES, ART, HALVES, PALETTES, type Palette } from "./sprites_art";
import { DRAWINGS, heroCustom } from "./sprites_draw";

export const BASE = 16;   // the hand-drawn grid
export const SIZE = 32;   // the rendered sprite (the drawing scaled 2x and shaded)

export type Pixels = (string | null)[][];

const has = (o: object, k: string): boolean => Object.hasOwn(o, k);
const reverse = (s: string): string => [...s].reverse().join("");

/** The drawing for `key` as a SIZE x SIZE grid of palette characters. */
function grid(key: string): string[] {
  if (has(ALIASES, key)) key = ALIASES[key][0];
  if (has(DRAWINGS, key)) return DRAWINGS[key]();
  if (has(ART, key)) {
    const art = ART[key];
    if (art.length > SIZE) throw new Error(key);
    let halves = art.map((r) => r.slice(-(SIZE / 2)).padStart(SIZE / 2, "."));
    const blank = ".".repeat(SIZE / 2);
    halves = [...new Array<string>(SIZE - halves.length).fill(blank), ...halves];
    return halves.map((h) => h + reverse(h));
  }
  return scale2x(HALVES[key].map((half) => half + reverse(half)));
}

/** The SIZE x SIZE grid of palette characters (symmetric) for `key`. */
export const spriteRows = (key: string): string[] => grid(key);

/** Scale2x: doubles the drawing and smooths its diagonals without blurring. */
function scale2x(rows: string[]): string[] {
  const h = rows.length, w = rows[0].length;
  const at = (x: number, y: number, dflt: string): string => (0 <= x && x < w && 0 <= y && y < h ? rows[y][x] : dflt);
  const out = Array.from({ length: h * 2 }, () => new Array<string>(w * 2).fill(""));
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      const p = rows[y][x];
      const a = at(x, y - 1, p), b = at(x + 1, y, p);
      const c = at(x - 1, y, p), d = at(x, y + 1, p);
      out[2 * y][2 * x] = c === a && c !== d && a !== b ? a : p;
      out[2 * y][2 * x + 1] = a === b && a !== c && b !== d ? b : p;
      out[2 * y + 1][2 * x] = d === c && d !== b && c !== a ? c : p;
      out[2 * y + 1][2 * x + 1] = b === d && b !== a && d !== c ? d : p;
    }
  }
  return out.map((r) => r.join(""));
}

type Rgb = [number, number, number];

const mix = (a: number[], b: number[], t: number): Rgb =>
  [0, 1, 2].map((i) => pyRound(a[i] + (b[i] - a[i]) * t)) as Rgb;

const rgb = (colour: string): Rgb =>
  [parseInt(colour.slice(1, 3), 16), parseInt(colour.slice(3, 5), 16), parseInt(colour.slice(5, 7), 16)];

const hex = (c: number[]): string =>
  "#" + c.map((v) => Math.max(0, Math.min(255, pyRound(v))).toString(16).padStart(2, "0")).join("");

function isGlow(colour: string): boolean {
  const [r, g, b] = rgb(colour);
  const hi = Math.max(r, g, b);
  return hi >= 200 && hi - Math.min(r, g, b) >= 90;
}

/** Dark-fantasy look: top-left light, shadowed lower edges, grit, glowing eyes. */
function shade(rows: string[], palette: Palette): Pixels {
  const n = rows.length;
  const ch = (x: number, y: number): string => (0 <= x && x < n && 0 <= y && y < n ? rows[y][x] : ".");
  const pal = (k: string): string => {
    if (!has(palette, k)) throw new Error(`no palette colour for ${JSON.stringify(k)}`);
    return palette[k];
  };
  const glow = new Set<string>();
  for (const [k, v] of Object.entries(palette)) {
    if (k !== "o" && isGlow(v) && (k === "e" || (k === "r" && v === "#ff3b2e"))) glow.add(k);
  }
  const out: Pixels = [];
  for (let y = 0; y < n; y++) {
    const line: (string | null)[] = [];
    for (let x = 0; x < n; x++) {
      const c = rows[y][x];
      if (c === ".") { line.push(null); continue; }
      const base = rgb(pal(c));
      if (c === "o" || glow.has(c)) { line.push(hex(base)); continue; }
      let factor = 1.18 - (0.42 * (x + y)) / (2 * n - 2);
      const up = ch(x, y - 1), left = ch(x - 1, y), down = ch(x, y + 1), right = ch(x + 1, y);
      if (up === "." || up === "o") factor *= 1.12;            // lit upper edge
      if (left === "." || left === "o") factor *= 1.06;
      if (down === "." || down === "o" || right === "." || right === "o") factor *= 0.72;   // shadowed lower / right edge
      // grit: Python ints are unbounded, JS bit operators are 32-bit; both operands are < 2^32, so >>> 0 is exact
      factor *= 1 + (((((x * 73856093) ^ (y * 19349663)) >>> 0) % 9) - 4) / 100;
      let colour: number[] = base.map((v) => v * factor);
      for (let dx = -2; dx <= 2; dx++) {
        for (let dy = -2; dy <= 2; dy++) {
          if ((dx || dy) && glow.has(ch(x + dx, y + dy))) {
            const dist = Math.max(Math.abs(dx), Math.abs(dy));
            colour = mix(colour, rgb(pal(ch(x + dx, y + dy))), 0.34 / dist);
            break;   // leaves the dy loop only, like the Python
          }
        }
      }
      line.push(hex(colour));
    }
    out.push(line);
  }
  return out;
}

/** The finished SIZE x SIZE image as colour strings ('#rrggbb'), null for transparent. */
export function spritePixels(key: string): Pixels {
  const palette: Palette = has(ALIASES, key) ? { ...PALETTES[ALIASES[key][0]], ...ALIASES[key][1] } : PALETTES[key];
  if (!palette) throw new Error(`unknown sprite ${JSON.stringify(key)}`);
  return shade(grid(key), palette);
}

/** The hero drawn with the gear he wears (item keys, null/undefined = nothing equipped). */
export function heroPixels(weapon?: string | null, armor?: string | null, charm?: string | null): Pixels {
  const [rows, palette] = heroCustom(weapon, armor, charm);
  return shade(rows, palette);
}

export const SPRITE_KEYS: readonly string[] = [
  ...new Set([...Object.keys(DRAWINGS), ...Object.keys(ART), ...Object.keys(HALVES)]),
  ...Object.keys(ALIASES),
];
