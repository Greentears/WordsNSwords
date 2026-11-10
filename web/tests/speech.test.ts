import test from "node:test";
import assert from "node:assert/strict";
import { languageTag, spokenText } from "../src/core/speech";

test("the language being learned is spoken", () => {
  assert.equal(languageTag("pl-en"), "pl-PL");
  assert.equal(languageTag("fr-en"), "fr-FR");
  assert.equal(languageTag("xx-en"), "xx");
});

test("brackets are not read out", () => {
  assert.equal(spokenText("pochodzić (z)"), "pochodzić z");
  assert.equal(spokenText("  dobre / ładne   pachnie "), "dobre / ładne pachnie");
});
