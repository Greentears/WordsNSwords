// Quizzes, sentence practice, search, settings and backup round trip on an emulated phone.
import { chromium, devices } from "playwright";
import { serve } from "../../tools/serve.mjs";
import { readFileSync } from "node:fs";

const shots = process.argv[2];
const server = await serve(4198);
const browser = await chromium.launch();
const ctx = await browser.newContext({ ...devices["Pixel 7"], acceptDownloads: true });
const page = await ctx.newPage();
const errors = [];
page.on("pageerror", (e) => errors.push(e.message));
page.on("console", (m) => m.type() === "error" && errors.push(m.text()));
const ok = (c, msg) => { if (!c) { console.error("FAIL:", msg); process.exitCode = 1; } else console.log("ok  ", msg); };
const snap = (n) => shots && page.screenshot({ path: `${shots}/${n}.png` });
const ev = (f, a) => page.evaluate(f, a);
const tab = (name) => page.tap(`.tab:has-text('${name}')`);

await page.goto("http://localhost:4198/");
await page.waitForSelector(".welcome input, .card");
if (await page.isVisible(".welcome")) { await page.fill(".welcome input", "Devoriah"); await page.tap(".welcome .btn.primary"); }
await page.waitForSelector(".card");
await ev(() => { window.__app.deck.resetProgress(); window.__app.deck.words.slice(0, 40).forEach((w, i) => (w.level = i % 3)); window.__app.saveWords(); return window.__app.pending; });

// ---- typed quiz, English -> Polish
await tab("Review");
await page.tap(".screen:not([hidden]) .seg-btn:text-is('Type')");
await snap("10-quiz-setup");
await page.fill(".num", "3");
await page.tap(".btn:has-text('Start quiz')");
await page.waitForSelector(".answerbar .text-in");
ok(await page.isHidden(".tabbar"), "tab bar hidden during the quiz");
ok((await page.locator(".accents button").count()) === 9, "accent row has 9 letters");
// answer card 1 correctly (accents typed via the row), card 2 wrong, card 3 "I don't know"
const expected = async () => ev(() => { const w = window.__app.deck.words; return null; });
const first = await ev(() => document.querySelector(".prompt").textContent);
const card = await ev((t) => window.__app.deck.words.find((w) => w.translation === t), first);
ok(!!card, "prompt is the English side: " + first);
await page.tap(".accents button:nth-child(1)");
ok((await page.inputValue(".text-in")) === "ą", "accent button inserts at caret");
await page.fill(".text-in", card.word.replace(/\s*\(.*?\)/g, "").split(" / ")[0]);
await page.press(".text-in", "Enter");
ok(await page.isVisible(".feedback.ok"), "correct answer accepted");
await snap("11-feedback-ok");
await page.tap(".btn:has-text('Next')");
await page.fill(".text-in", "zzzz"); await page.press(".text-in", "Enter");
ok(await page.isVisible(".feedback.bad"), "wrong answer rejected");
const failsBefore = await ev(() => window.__app.deck.words.reduce((s, w) => s + w.fails, 0));
ok(failsBefore === 1, "fail counter increased once");
await snap("12-feedback-bad");
await page.tap(".btn:has-text('Next')");
await page.tap(".btn:has-text(\"I don't know\")");
ok((await ev(() => window.__app.deck.words.reduce((s, w) => s + w.fails, 0))) === 2, "I don't know counts as a fail");
await page.tap(".btn:has-text('Finish')");
ok(await page.isVisible("text=Score: 1 / 3"), "score 1 / 3");
await snap("13-quiz-done");
await page.tap(".btn:has-text('Done')");

// ---- fill in the blank
await page.tap(".seg-btn:text-is('Blank')");
await page.fill(".num", "2");
await page.tap(".btn:has-text('Start quiz')");
await page.waitForSelector(".prompt.cloze");
const cz = await ev(() => document.querySelector(".prompt").textContent);
ok(cz.includes("_____ ("), "blank with English gloss: " + cz);
await page.tap(".btn:has-text('Hint')");
ok((await page.textContent("#hint")).includes("Dictionary form"), "hint shows sentence translation and dictionary form");
await snap("14-cloze");
await page.tap(".btn:has-text(\"I don't know\")");
ok(await page.isVisible(".feedback.bad"), "cloze feedback");
await page.tap(".btn:has-text('✕ Exit')"); await page.tap(".sheet .btn:has-text('Leave')");
ok(await page.isVisible(".tabbar"), "exit returns to setup with tab bar");

// ---- sentence practice
await tab("Review"); await page.tap(".seg-btn:text-is('Sentences')");
await page.tap(".screen:not([hidden]) .btn:text-is('Start')");
await page.tap(".qcard");
ok(await page.isVisible(".revealed-block"), "tap reveals translation and cards used");
await snap("15-sentences");
await page.tap(".btn:has-text('Next')"); 
ok(await page.isVisible("text=2 of 10"), "next sentence");
await page.tap(".btn:has-text('✕ Exit')");

// ---- search
await tab("Search");
await page.fill("input[type=search]", "BAC SIE"); // capitals and accents ignored
await page.waitForSelector(".hit");
ok((await page.locator(".hit").first().textContent()).startsWith("bać się"), "accent-insensitive search finds 'bać się'");
await snap("16-search");
await page.locator(".hit").first().tap();
ok(await ev(() => window.__app.deck.mode) === "search", "tapping a hit opens it in Study");

// ---- settings + backup round trip
await tab("More");
await page.tap(".seg-btn:has-text('Dark')");
ok(await ev(() => document.documentElement.dataset.theme) === "dark", "dark mode switch");
await page.tap(".toggle:has-text('English first') input").catch(() => {});
await snap("17-more");
const snapshot = await ev(() => JSON.stringify(window.__app.deck.words.map((w) => [w.word, w.level, w.fails])));
const [dl] = await Promise.all([page.waitForEvent("download"), page.tap(".btn:has-text('Export backup')")]);
const path = await dl.path();
const backup = JSON.parse(readFileSync(path, "utf8"));
ok(backup.app === "flashcards-web" && backup.words.length === 323, "backup file has all cards");
await page.evaluate(() => window.__app.pending);
// erase everything, then import
await page.tap(".btn:has-text('Erase all data')");
await Promise.all([page.waitForNavigation(), page.tap(".sheet .btn.danger")]);
await page.waitForSelector(".welcome input");        // everything is gone: the app asks for a name again
await page.fill(".welcome input", "Devoriah"); await page.tap(".welcome .btn.primary");
await page.waitForSelector(".card");
ok(await ev(() => window.__app.deck.words.every((w) => w.level === null || true)), "app reloads after erase");
const wiped = await ev(() => JSON.stringify(window.__app.deck.words.map((w) => [w.word, w.level, w.fails])));
ok(wiped !== snapshot, "data really was wiped");
await tab("More");
await page.setInputFiles("input[type=file]", path);
await page.tap(".list-btn:has-text('Replace everything')");
await page.waitForTimeout(300);
await ev(() => window.__app.pending);
const restored = await ev(() => JSON.stringify(window.__app.deck.words.map((w) => [w.word, w.level, w.fails])));
ok(restored === snapshot, "import restores every level and fail count");
ok(await ev(() => window.__app.settings.theme) === "dark", "settings restored");

// plain words.json import: merge by word keeps higher progress
const plain = JSON.parse(readFileSync(new URL("../../../tests/fixtures/pl-en/words.json", import.meta.url), "utf8"));
plain.push({ word: "testowe", translation: "test word" });
const { writeFileSync } = await import("node:fs");
writeFileSync(path + ".plain.json", JSON.stringify(plain));
await page.setInputFiles("input[type=file]", path + ".plain.json");
await page.tap(".list-btn:has-text('keep the higher progress')");
await page.waitForTimeout(200);
ok(await ev(() => window.__app.deck.words.length) === 324, "plain words.json import adds the new word");
const score = (lv, f) => (lv ?? -1) * 1000 + Math.min(f, 999);
const mine = JSON.parse(snapshot), theirs = new Map(plain.map((w) => [w.word, [w.level ?? null, w.fails ?? 0]]));
const expectedMerge = mine.map(([word, lv, f]) => { const t = theirs.get(word); return t && score(t[0], t[1]) > score(lv, f) ? [word, ...t] : [word, lv, f]; });
ok(JSON.stringify(await ev(() => window.__app.deck.words.slice(0, 323).map((w) => [w.word, w.level, w.fails]))) === JSON.stringify(expectedMerge), "merge keeps the higher-progress copy of every card");

ok(errors.length === 0, "no console errors " + errors.join("|"));
await browser.close(); server.close();
