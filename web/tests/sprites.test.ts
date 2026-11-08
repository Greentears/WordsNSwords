// The TypeScript sprites must reproduce the Python pixels exactly: every monster/companion sprite and the hero
// with every combination of weapon, armor and charm (tests/sprite_golden.json, made by tools/make_sprite_golden.py).
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { SIZE, SPRITE_KEYS, heroPixels, spritePixels } from "../src/dungeon";

interface Hero { weapon: string | null; armor: string | null; charm: string | null; grid: number[][] }
const golden = JSON.parse(readFileSync(new URL("./sprite_golden.json", import.meta.url), "utf8")) as {
  size: number; palette: string[]; keys: string[]; weapons: string[]; armors: string[]; charms: string[];
  sprites: Record<string, number[][]>; heroes: Hero[];
};

/** Compares a grid with its golden version; returns a description of the first difference or null. */
function firstMismatch(actual: (string | null)[][], expected: number[][]): string | null {
  if (actual.length !== SIZE) return `${actual.length} rows instead of ${SIZE}`;
  for (let y = 0; y < SIZE; y++) {
    if (actual[y].length !== SIZE) return `row ${y} has ${actual[y].length} entries instead of ${SIZE}`;
    for (let x = 0; x < SIZE; x++) {
      const want = expected[y][x] < 0 ? null : golden.palette[expected[y][x]];
      if (actual[y][x] !== want) return `pixel x=${x} y=${y}: got ${actual[y][x]}, expected ${want}`;
    }
  }
  return null;
}

test("sprite size and key list match Python", () => {
  assert.equal(SIZE, 32);
  assert.equal(golden.size, 32);
  assert.deepEqual([...SPRITE_KEYS], golden.keys);
});

test("every sprite is identical to the Python pixels and 32x32", () => {
  for (const key of golden.keys) {
    const bad = firstMismatch(spritePixels(key), golden.sprites[key]);
    assert.equal(bad, null, `sprite ${key}: ${bad}`);
  }
});

test("the hero is identical for every weapon x armor x charm combination", () => {
  assert.equal(golden.heroes.length, (golden.weapons.length + 1) * (golden.armors.length + 1) * (golden.charms.length + 1));
  for (const h of golden.heroes) {
    const bad = firstMismatch(heroPixels(h.weapon, h.armor, h.charm), h.grid);
    assert.equal(bad, null, `hero weapon=${h.weapon} armor=${h.armor} charm=${h.charm}: ${bad}`);
  }
  // the defaults mean "nothing equipped"
  assert.deepEqual(heroPixels(), heroPixels(null, null, null));
});
