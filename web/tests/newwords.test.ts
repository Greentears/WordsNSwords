import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { checkAndMerge, languageOf, type DeckData } from "../src/core/newwords";

const { bases, cases } = JSON.parse(readFileSync(new URL("./newwords_cases.json", import.meta.url), "utf8")) as {
  bases: Record<string, DeckData>;
  cases: { deck: string; name: string; text: string; errors: string[]; counts: Record<string, number>; result: DeckData }[];
};

for (const c of cases) {
  test(`new words: ${c.name} matches the Python code`, () => {
    const r = checkAndMerge(JSON.parse(JSON.stringify(bases[c.deck])), c.text, languageOf(c.deck));
    if (c.name === "not json" || c.name === "empty") {
      assert.equal(r.errors.length, 1);                      // the JSON parser's own wording differs by language
      assert.match(r.errors[0], /not valid JSON/);
      return;
    }
    assert.deepEqual(r.errors, c.errors);
    if (!c.errors.length) {
      assert.deepEqual(r.counts, c.counts);
      assert.deepEqual(r.deck, c.result);
    }
  });
}
