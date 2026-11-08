import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { checkAnswer } from "../src/core/answer";
import { blankSentence } from "../src/core/cloze";
import { FlashcardDeck, parseWords, serializeWords, type Word } from "../src/core/deck";
import { knownForms, loadAdjectives, loadConjugations, loadDeclensions, loadExamples, loadSentences } from "../src/core/tables";
import { pickSentences, sentenceWeight } from "../src/core/sentences";
import { updateSession } from "../src/core/stats";

const read = (p: string) => readFileSync(new URL(p, import.meta.url), "utf8");
const golden = JSON.parse(read("./golden.json"));
const data = (n: string) => JSON.parse(read(`../../tests/fixtures/pl-en/${n}.json`));
const words = () => parseWords(data("words"));

test("check_answer matches Python on every card and tricky answers", () => {
  assert.ok(golden.check.length > 1000);
  for (const c of golden.check) {
    assert.deepEqual(checkAnswer(c.given, c.expected, c.ignore_accents), c.result, JSON.stringify(c));
  }
});

test("blank_sentence matches Python over every card sentence and example", () => {
  const ex = loadExamples(data("examples"));
  const forms = knownForms(loadConjugations(data("verbs")), loadDeclensions(data("nouns")), loadAdjectives(data("adjectives")));
  const byWord = new Map(words().map((w) => [w.word, w]));
  assert.ok(golden.blank.length > 500);
  let found = 0;
  for (const b of golden.blank) {
    const w = byWord.get(b.word)!;
    const r = blankSentence(w, b.use_forms ? forms[b.word] : null, b.text);
    assert.deepEqual(r, b.result, `${b.word} :: ${b.text}`);
    if (r) found++;
  }
  assert.ok(found > 300);
  assert.ok(ex["bać się"].length > 0);
});

test("smart mix gives the same allocation as Python and never repeats a card", () => {
  const synth = (sizes: number[]) => {
    const ws: Word[] = [];
    [0, 1, 2, 3, null, 4].forEach((lv, k) => {
      for (let i = 0; i < sizes[k]; i++) ws.push({ word: `w${lv}-${i}`, translation: "t", sentence: "", sentence_translation: "", level: lv, fails: 0, extra: {} });
    });
    return new FlashcardDeck(ws);
  };
  for (const m of golden.mix) {
    const d = synth(m.sizes);
    const ids = d.mixedSample(m.size, undefined, m.allowed ? new Set(d.words.map((_, i) => i).filter((i) => i % 2 === 0)) : null);
    assert.equal(ids.length, m.n, JSON.stringify(m));
    assert.equal(new Set(ids).size, ids.length);
    const counts: Record<string, number> = { "0": 0, "1": 0, "2": 0 };
    for (const i of ids) counts[String(d.words[i].level)]++;
    assert.deepEqual(counts, m.counts, JSON.stringify(m));
  }
});

test("smart mix proportions are about 45/35/20 on a big deck", () => {
  const ws: Word[] = [];
  for (const lv of [0, 1, 2]) for (let i = 0; i < 200; i++) ws.push({ word: `${lv}-${i}`, translation: "t", sentence: "", sentence_translation: "", level: lv, fails: 0, extra: {} });
  const ids = new FlashcardDeck(ws).mixedSample(100);
  const c = [0, 1, 2].map((lv) => ids.filter((i) => ws[i].level === lv).length);
  assert.deepEqual(c, [20, 35, 45]);
});

test("search matches Python (order, accents, archived included)", () => {
  const d = new FlashcardDeck(words());
  for (const s of golden.search) {
    assert.equal(d.search(s.query), s.count, s.query);
    assert.deepEqual(d.order, s.ids, s.query);
  }
});

const mk = () => new FlashcardDeck(
  [[null, 0], [0, 3], [1, 0], [2, 5], [3, 1], [4, 9], [0, 0], [3, 0], [null, 2], [1, 7], [4, 0], [2, 2]].map(([lv, fl], i) => ({
    word: `w${i}`, translation: `t${i}`, sentence: "", sentence_translation: "", level: lv as number | null, fails: fl as number, extra: {},
  })),
);

test("filters and failed ordering match Python", () => {
  const d = mk();
  for (const [mode, ids] of Object.entries(golden.filters)) {
    d.setMode(mode as any);
    assert.deepEqual(d.order, ids, mode);
  }
  assert.deepEqual([d.activeCount, d.newCount, [0, 1, 2, 3, 4].map((i) => d.levelCount(i))], [golden.counts.active, golden.counts.new, golden.counts.levels]);
});

test("mark / archive / restart behave like Python", () => {
  const d = mk();
  d.setMode("level1");
  const snap = () => ({ levels: d.words.map((w) => w.level), fails: d.words.map((w) => w.fails), index: d.index, order: [...d.order], results: Object.fromEntries([...d.results].map(([k, v]) => [String(k), v])) });
  const steps: Record<string, () => void> = {
    "mark:3": () => d.mark(3),
    "mark:4": () => { d.next(); d.mark(4); },
    "next:null": () => { if (!d.isLast) d.next(); },
    "fail:0": () => d.recordFail(0),
    "restart:null": () => d.restart(),
    "archive known:4": () => { d.setMode("level3"); d.mark(4); },
    "all after archive:null": () => d.setMode("all"),
    "unarchive:1": () => { d.setMode("level4"); d.mark(1); },
  };
  for (const [name, arg, expected] of golden.ops) {
    steps[`${name}:${arg}`]();
    assert.deepEqual(snap(), expected, name);
  }
});

test("saved JSON is byte-identical to the desktop app", () => {
  const out = serializeWords(parseWords(golden.serialise.input));
  assert.equal(out, golden.serialise.output);
  assert.equal(golden.roundtrip.same_as_source, true);
  assert.equal(serializeWords(words()), read("../../tests/fixtures/pl-en/words.json").replace(/\r\n/g, "\n").replace(/\n$/, ""));
});

test("invalid word files give the desktop error messages", () => {
  for (const b of golden.invalid) {
    if (b.error === null) assert.doesNotThrow(() => parseWords(b.data));
    else assert.throws(() => parseWords(b.data), { message: b.error });
  }
});

test("table loaders and known forms match Python", () => {
  const count = (o: Record<string, unknown[]>) => Object.fromEntries(Object.entries(o).map(([k, v]) => [k, v.length]));
  const conj = loadConjugations(data("verbs")), decl = loadDeclensions(data("nouns")), adj = loadAdjectives(data("adjectives"));
  assert.deepEqual(count(conj), golden.tables.conj);
  assert.deepEqual(count(decl), golden.tables.decl);
  assert.deepEqual(count(adj), golden.tables.adj);
  assert.deepEqual(loadExamples(data("examples")), golden.tables.examples);
  assert.deepEqual(knownForms(conj, decl, adj), golden.tables.forms);
});

test("sentence weights match Python and picks favour learning words", () => {
  const sents = loadSentences(data("sentences"));
  assert.equal(sents.length, golden.sentences.loaded);
  const d = new FlashcardDeck(words());
  assert.deepEqual(sents.map((s) => sentenceWeight(d, s)), golden.sentences.weights);
  d.words.forEach((w, i) => { w.level = golden.sentences.levels[i]; });
  assert.deepEqual(sents.map((s) => sentenceWeight(d, s)), golden.sentences.weights_random_levels);
  const picks = pickSentences(d, sents, 40);
  assert.equal(picks.length, 40);
  assert.ok(picks.every((p) => sentenceWeight(d, p) > 0));
});

test("session stats accumulate", () => {
  let s = updateSession({}, 10, 6, 4);
  s = updateSession(s, 5, 5, 0);
  assert.deepEqual(s, { sessions: 2, cards_reviewed: 15, known: 11, unknown: 4 });
});

import { QuizSession, quizCardIds, clozeAllowed } from "../src/core/quiz";
import { makeBackup, mergeWords, parseImport } from "../src/core/backup";

test("typed quiz session: correct, accent-only, wrong and don't-know, fails counted and saved", () => {
  const d = new FlashcardDeck(parseWords([
    { word: "żółw", translation: "turtle", level: 1 },
    { word: "pies", translation: "dog" },
    { word: "kot", translation: "cat", level: 2 },
  ]));
  let saved = 0;
  d.onSave = () => saved++;
  const q = new QuizSession(d, [0, 1, 2], true, true);
  assert.equal(q.promptText(), "turtle");
  assert.equal(q.pill(), "Learning");
  let f = q.submit("zolw")!;
  assert.deepEqual([f.ok, f.exact, f.expected], [true, false, "żółw"]);
  assert.equal(q.submit("again"), null);
  assert.equal(q.next(), false);
  f = q.submit("kot")!;
  assert.deepEqual([f.ok, f.fails], [false, 1]);
  assert.equal(q.pill(), "New");
  q.next();
  f = q.submit("   ")!;
  assert.equal(f.ok, false);
  assert.equal(q.next(), true);
  assert.equal(q.score, 1);
  assert.deepEqual(q.failedWords.map((w) => w.word), ["pies", "kot"]);
  assert.equal(saved, 2);
  assert.deepEqual(d.words.map((w) => w.fails), [0, 1, 1]);
});

test("cloze session blanks the word, shows the gloss, accepts the inflected form", () => {
  const d = new FlashcardDeck(parseWords([{ word: "pies", translation: "dog", sentence: "Mój pies lubi biegać.", sentence_translation: "My dog likes to run." }]));
  const q = new QuizSession(d, [0], true, true, { forms: {}, examples: {} });
  assert.equal(q.promptText(), "Mój _____ (dog) lubi biegać.");
  assert.match(q.hint(), /My dog likes to run\./);
  assert.equal(q.submit("pies")!.ok, true);
  assert.deepEqual(clozeAllowed(d, {}, {}), new Set([0]));
});

test("quizCardIds: levels, count, all, allowed", () => {
  const d = mk();
  const base = { mix: false, levels: new Set<number | null>([0, 1]), count: 2, all: false };
  assert.equal(quizCardIds(d, base).length, 2);
  assert.equal(quizCardIds(d, { ...base, all: true }).length, 4);
  assert.deepEqual(quizCardIds(d, { ...base, all: true, allowed: new Set([1]) }), [1]);
  assert.equal(quizCardIds(d, { ...base, mix: true, count: 5 }).length, 5);
});

test("backup export, plain words.json import and merge by word", () => {
  const cur = parseWords([{ word: "a", translation: "A", level: 1, fails: 2 }, { word: "b", translation: "B", level: 3 }]);
  const b = makeBackup(cur, { theme: "dark" }, { sessions: 3 });
  const back = parseImport(JSON.stringify(b));
  assert.equal(back.kind, "backup");
  assert.deepEqual(back.words, cur);
  assert.deepEqual(back.stats, { sessions: 3 });
  const plain = parseImport(JSON.stringify([{ word: "a", translation: "A2", level: 2 }, { word: "b", translation: "B", level: 0 }, { word: "c", translation: "C" }]));
  assert.equal(plain.kind, "words");
  const higher = mergeWords(cur, plain.words, "higher");
  assert.deepEqual([higher.added, higher.updated, higher.unchanged], [1, 1, 1]);
  assert.deepEqual(higher.words.map((w) => [w.word, w.translation, w.level, w.fails]), [["a", "A2", 2, 0], ["b", "B", 3, 0], ["c", "C", null, 0]]);
  const replaced = mergeWords(cur, plain.words, "replace");
  assert.deepEqual(replaced.words.map((w) => w.level), [2, 0, null]);
  const kept = mergeWords(cur, plain.words, "keep");
  assert.deepEqual(kept.words.map((w) => w.level), [1, 3, null]);
  assert.throws(() => parseImport("nope"), /not valid JSON/);
  assert.throws(() => parseImport("{}"), /Unrecognised/);
});
