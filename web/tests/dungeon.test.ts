// The TypeScript dungeon rules must reproduce the Python game exactly: every answer check, every tower floor,
// and 15 scripted playthroughs replayed with the recorded random numbers (tests/dungeon_golden.json,
// made by tools/make_dungeon_golden.py).
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { parseWords } from "../src/core/deck";
import { loadExamples } from "../src/core/tables";
import { GameManager, MemoryRepository, GameError, MONSTERS, abilities, answers, tower, xpToNext } from "../src/dungeon";

const read = (p: string) => JSON.parse(readFileSync(new URL(p, import.meta.url), "utf8"));
const golden = read("./dungeon_golden.json");
const wordsJson = read("../../tests/fixtures/pl-en/words.json");
const examples = loadExamples(read("../../tests/fixtures/pl-en/examples.json"));
const plain = (x: unknown) => JSON.parse(JSON.stringify(x ?? null));

test("answer checking: accepted forms, primary spelling and 'check' agree with Python", () => {
  for (const f of golden.answers.forms) {
    assert.deepEqual([...answers.acceptedForms(f.expected, f.reverse)].sort(), f.forms, `forms of ${JSON.stringify(f.expected)} reverse=${f.reverse}`);
    assert.equal(answers.primary(f.expected, f.reverse), f.primary, `primary of ${JSON.stringify(f.expected)}`);
  }
  for (const c of golden.answers.check) {
    assert.deepEqual(answers.check(c.given, c.expected, c.reverse), c.result, `check(${JSON.stringify(c.given)}, ${JSON.stringify(c.expected)}, ${c.reverse})`);
  }
});

test("tower floors, monster abilities and the XP table agree with Python", () => {
  for (const f of golden.tower.floors) {
    const room = tower.floorRoom(f.floor - 1);
    assert.deepEqual(plain(room), f.room, `floor ${f.floor} room`);
    if (f.spec) {
      assert.deepEqual(plain(tower.monsterFor(f.floor)), f.spec, `floor ${f.floor} monster`);
      assert.deepEqual(abilities(room.spec!), f.abilities, `floor ${f.floor} abilities`);
    }
  }
  for (const m of golden.tower.monsters) assert.deepEqual(abilities(MONSTERS[m.key]), m.abilities, m.key);
  golden.tower.xp_table.forEach((x: number, n: number) => assert.equal(xpToNext(n), x, `xp_to_next(${n})`));
});

function snapMini(m: GameManager) {
  const b = m.battle;
  return {
    player: plain(m.player), dungeon: m.dungeon ? m.dungeon.key : null,
    battle: b && {
      monster_key: b.monster.spec.key, monster_hp: b.monster.hp, spec: plain(b.monster.spec), state: b.state, ward: b.ward,
      phoenix: b.phoenix, time_bonus: b.time_bonus, xp_mult: b.xp_mult, coin_mult: b.coin_mult,
      consecutive_wrong: b.consecutive_wrong, questions_asked: b.questions_asked, question: plain(b.question),
      companion: b.companion, heal_on_correct: b.heal_on_correct, bonus_damage: b.bonus_damage, dodge_pct: b.dodge_pct,
    },
  };
}
function snapFull(m: GameManager, repo: MemoryRepository) {
  return {
    stats: m.stats, run: m.run, missed: m.missed.to_dict(), progress: m.progress, inventory: plain(m.inventory.to_dict()),
    saved_fight: plain(m.saved_fight), outcome: plain(m.outcome), recent: [...m.selector.recent], only_missed: m.selector.only_missed,
    state: plain(repo.data), missed_count: m.missed_count, has_words: m.has_words,
  };
}

function perform(m: GameManager, op: string, args: unknown[]): unknown {
  try {
    switch (op) {
      case "shop": return m.shop().map((e) => ({ key: e.item.key, count: e.count, owned: e.owned, equipped: e.equipped, problem: e.problem }));
      case "sellable": return m.sellable().map((e) => ({ key: e.item.key, count: e.count, value: e.value, equipped: e.equipped }));
      case "usable_items": return m.usable_items().map(([i, n]) => [i.key, n]);
      default: return plain((m as unknown as Record<string, (...a: unknown[]) => unknown>)[op](...args));
    }
  } catch (e) {
    if (e instanceof GameError) return { error: e.message };
    throw e;
  }
}

for (const sc of golden.scenarios) {
  test(`playthrough "${sc.name}" (${sc.steps.length} steps, ${sc.rng.length} random draws)`, () => {
    const words = parseWords(wordsJson);
    words.forEach((w, i) => { w.level = sc.levels[i]; });
    let used = 0;
    const rng = () => { assert.ok(used < sc.rng.length, "the game drew more random numbers than Python did"); return sc.rng[used++]; };
    const repo = new MemoryRepository(sc.initial_state ? JSON.parse(JSON.stringify(sc.initial_state)) : null);
    const m = new GameManager({ words }, examples, repo, rng);
    assert.deepEqual(snapMini(m), sc.init.snap, "initial state");
    assert.deepEqual(plain(snapFull(m, repo)), { ...sc.init.full, state: plain(sc.init.full.state) }, "initial full state");
    assert.equal(used, sc.init.draws);
    sc.steps.forEach((s: any, i: number) => {
      const where = `step ${i} ${s.op}(${s.args.map((a: unknown) => JSON.stringify(a)).join(", ")})`;
      const res = perform(m, s.op, s.args);
      assert.deepEqual(res, s.result, `${where}: result`);
      assert.deepEqual(snapMini(m), s.snap, `${where}: state`);
      assert.equal(used, s.draws, `${where}: random numbers drawn`);
      if (s.full) assert.deepEqual(plain(snapFull(m, repo)), plain(s.full), `${where}: full state`);
    });
    assert.equal(used, sc.rng.length, "all recorded random numbers were used");
  });
}

// ---- Review Guru and boss weights (same rules as tests/test_stage7.py on the desktop)
function reviewGame(missedCount: number) {
  const words = parseWords(wordsJson);
  words.forEach((w) => { w.level = 1; });
  const missed: Record<string, number> = {};
  words.slice(0, missedCount).forEach((w) => { missed[w.word] = 0; });
  const repo = new MemoryRepository({ player: { level: 5, coins: 0, max_hp: 70, hp: 70 }, missed });
  return new GameManager({ words }, examples, repo, Math.random);
}

test("Review Guru: one monster whose HP is 5 to 10 hits, depending on the missed words", () => {
  for (const [missed, hits] of [[2, 5], [7, 7], [30, 10]]) {
    const m = reviewGame(missed);
    m.select_dungeon("review"); m.enter_room();
    assert.equal(m.battle!.monster.name, "Review Guru");
    assert.equal(m.battle!.monster.max_hp, m.player.attack_power * hits, `${missed} missed words`);
  }
});

test("Review Guru: failed words are listed once, with their meaning, and kept while the fight is saved", () => {
  const m = reviewGame(6);
  m.select_dungeon("review"); m.enter_room();
  for (let i = 0; i < 4; i++) { m.next_question(); m.answer("zzz"); m.player.hp = m.player.max_hp; }
  const failed = m.review_failed_words;
  assert.ok(failed.length >= 1 && failed.length <= 4);
  assert.equal(new Set(failed.map(([w]) => w)).size, failed.length);
  for (const [w, t] of failed) assert.equal(t, m.deck.words.find((x) => x.word === w)!.translation);
  m.leave(); m.select_dungeon("review");
  assert.deepEqual(m.review_failed_words, failed);
});

test("bosses ask Learning and Almost there words, never new ones, and fall back when none exist", () => {
  const words = parseWords(wordsJson);
  words.forEach((w) => { w.level = 3; });          // only known cards
  const m = new GameManager({ words }, examples, new MemoryRepository(null), Math.random);
  m.select_dungeon("cellar");
  m.progress.cellar.room = 7;                       // the boss room
  m.enter_room();
  assert.ok(m.battle!.monster.spec.boss);
  assert.ok(m.next_question() !== null);
});
