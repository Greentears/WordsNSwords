import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { STAT_KEYS, effectText, type Stats } from "../src/dungeon/stats";

const cases = JSON.parse(readFileSync(new URL("./effect_text_cases.json", import.meta.url), "utf8")) as { stats: Stats; text: Record<string, string> }[];
test("stat effect texts match the Python ones", () => {
  for (const c of cases) for (const k of STAT_KEYS) assert.equal(effectText(k, c.stats), c.text[k], k);
});
