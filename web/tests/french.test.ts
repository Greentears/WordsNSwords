import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { clozeForms, expandOptional, frKnownForms, loadFrAdjectives, loadFrNouns, loadFrVerbs } from "../src/core/tables";

const golden = JSON.parse(readFileSync(new URL("./french_golden.json", import.meta.url), "utf8")) as {
  expand: Record<string, string[]>; cloze: Record<string, string[]>; known: Record<string, string[]>;
};
const pv = new URL("../../users/pacixii/fr-en/", import.meta.url);
const read = (n: string) => JSON.parse(readFileSync(new URL(n, pv), "utf8"));

test("french: bracketed letters expand like the Python code", () => {
  for (const [form, want] of Object.entries(golden.expand)) assert.deepEqual(expandOptional(form), want, form);
});

test("french: forms lose their pronouns like the Python code", () => {
  for (const [form, want] of Object.entries(golden.cloze)) assert.deepEqual(clozeForms([form]), want, form);
});

test("french: the forms of every Pacixii card match the Python code", () => {
  const known = frKnownForms(loadFrVerbs(read("verbs.json")), loadFrNouns(read("nouns.json")), loadFrAdjectives(read("adjectives.json")));
  assert.deepEqual(known, golden.known);
});

test("french: loaders keep good tables and drop broken ones", () => {
  assert.equal(Object.keys(loadFrVerbs(read("verbs.json"))).length, 7);
  assert.deepEqual(loadFrVerbs([{ card: "a", verbs: [{ infinitive: "a", tenses: { present: ["1"] } }] }]), {});
  assert.deepEqual(loadFrNouns([{ card: "a", nouns: [{ lemma: "a", singular: 3 }] }]), {});
  assert.equal(Object.keys(loadFrAdjectives(read("adjectives.json"))).length, 5);
});
