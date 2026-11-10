import { test } from "node:test";
import assert from "node:assert/strict";
import { heroArt, sceneKey } from "../src/art";

test("rest and treasure pictures follow the dungeon's setting", () => {
  for (const kind of ["rest", "treasure"] as const) {
    assert.equal(sceneKey(kind, "forest"), `${kind}_outdoor`);
    assert.equal(sceneKey(kind, "citadel"), `${kind}_outdoor`);
    assert.equal(sceneKey(kind, "library"), `${kind}_indoor`);
    assert.equal(sceneKey(kind, "tower"), `${kind}_indoor`);
  }
});

test("the hero picture follows his gear", () => {
  assert.equal(heroArt(null, true, true), null);
  assert.equal(heroArt("f", false, false), "art/heroes/f.webp");
  assert.equal(heroArt("m", true, false), "art/heroes/m_sword.webp");
  assert.equal(heroArt("m", true, true), "art/heroes/m_armour_sword.webp");
});
