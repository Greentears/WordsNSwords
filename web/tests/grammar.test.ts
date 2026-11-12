import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { CATEGORIES, buildPool, check, pick } from "../src/core/grammar";
import { loadAdjectives, loadConjugations, loadDeclensions, loadFrAdjectives, loadFrNouns, loadFrVerbs } from "../src/core/tables";

const read = (p: string) => JSON.parse(readFileSync(new URL(p, import.meta.url), "utf8"));
const golden = read("./grammar_golden.json");
const dir = (d: string) => (n: string) => read(`../../users/_template/${d}/${n}.json`);
const pl = dir("pl-en"), fr = dir("fr-en");
const tables = {
  conj: loadConjugations(pl("verbs")), decl: loadDeclensions(pl("nouns")), adj: loadAdjectives(pl("adjectives")),
  frConj: loadFrVerbs(fr("verbs")), frDecl: loadFrNouns(fr("nouns")), frAdj: loadFrAdjectives(fr("adjectives")),
};

test("the questions are the same as the desktop app makes", () => {
  for (const lang of ["pl", "fr"]) assert.deepEqual(buildPool(lang, tables), golden[lang], lang);
});

test("answers are judged the same as on the desktop", () => {
  assert.ok(golden.checks.length > 100);
  for (const c of golden.checks) assert.equal(check(c.q, c.text, c.lang), c.verdict, `${c.lang} ${c.q.stem} ${JSON.stringify(c.text)}`);
});

test("pick gives different questions, from the chosen kinds only", () => {
  const pool = buildPool("pl", tables);
  let seed = 7;
  const random = () => { seed = (seed * 16807) % 2147483647; return seed / 2147483647; };
  const got = pick(pool, CATEGORIES, 12, random);
  assert.equal(got.length, 12);
  assert.equal(new Set(got).size, 12);
  assert.ok(new Set(got.map((x) => x.category)).size > 1);
  assert.ok(pick(pool, ["nouns"], 5, random).every((x) => x.category === "nouns"));
  assert.equal(pick(pool, ["nouns"], 1e6, random).length, pool.nouns.length);
});
