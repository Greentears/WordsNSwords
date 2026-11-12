// Names: unknown name -> starter deck, hero name, update words keeps progress, old installs keep their data.
import { chromium, devices } from "playwright";
import { serve } from "../../tools/serve.mjs";

const server = await serve(4196);
const browser = await chromium.launch();
const errors = [];
const ok = (c, msg) => { if (!c) { console.error("FAIL:", msg); process.exitCode = 1; } else console.log("ok  ", msg); };
async function fresh() {
  const ctx = await browser.newContext({ ...devices["Pixel 7"], serviceWorkers: "block" });
  const page = await ctx.newPage();
  page.on("pageerror", (e) => errors.push(e.message));
  page.on("console", (m) => m.type() === "error" && !/404/.test(m.text()) && errors.push(m.text()));
  await page.goto("http://localhost:4196/");
  await page.waitForSelector(".welcome input");
  return page;
}
const ev = (page, f, a) => page.evaluate(f, a);
const sign = async (page, name) => { await page.fill(".welcome input", name); await page.tap(".welcome .btn.primary"); };

// ---- a name that is not in the repo
let page = await fresh();
await sign(page, "Zed Quux");
await page.waitForSelector(".welcome .btn:has-text('French')");
ok((await page.textContent(".welcome")).includes("Which language"), "an unknown name is asked which language to learn");
ok(await page.isVisible(".welcome .btn:has-text('Polish')"), "Polish and French are offered");
ok(!(await page.isVisible(".card")), "no deck is loaded behind it");
await page.tap(".welcome .btn:has-text('French')");
await page.waitForSelector(".card");
ok((await ev(page, () => window.__app.deckId)) === "fr-en", "the French starter deck is opened");
ok((await ev(page, () => window.__app.deck.words.length)) === 20, "the French starter deck has 20 cards");
ok((await ev(page, () => window.__app.deck.words[0].word)) === "s'apercevoir", "it is the French list Pacixii has");
// a second newcomer picks Polish
await ev(page, () => window.__app.pending);
const polish = await fresh();
await sign(polish, "Zed Polish");
await polish.waitForSelector(".welcome .btn:has-text('Polish')");
await polish.tap(".welcome .btn:has-text('Polish')");
await polish.waitForSelector(".card");
ok((await ev(polish, () => window.__app.deck.words.length)) === 20, "the Polish starter deck has 20 cards");
ok((await ev(polish, () => window.__app.deck.words[0].word)) === "bać się", "it holds known words of the Polish list");
ok((await ev(page, () => window.__app.game.player.name)) === "Zed Quux", "hero carries the name");
await page.tap(".tab:has-text('Dungeon')");
if (await page.$(".hero-pick")) await page.tap(".hero-pick >> nth=1");
await page.tap(".screen:not([hidden]) .btn:has-text('Gear')");
await page.waitForSelector(".doll");
ok((await page.textContent(".dg")).includes("Zed Quux"), "inventory shows the hero's name");
await ev(page, () => { window.__app.deck.words[0].level = 2; window.__app.saveWords(); return window.__app.pending; });
await page.reload();
await page.waitForSelector(".card");
ok(!(await page.isVisible(".welcome")), "reload goes straight into the app");
ok((await ev(page, () => window.__app.deck.words[0].level)) === 2, "progress is stored under the name");

// ---- Update words keeps progress, adds new cards (the repo list is faked with one extra card)
await page.route("**/users/zed-quux/pl-en/words.json", (r) => r.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([
  ...[...Array(15).keys()].map((i) => ({ word: `w${i}`, translation: `t${i}` })), { word: "pies", translation: "dog" }]) }));
await page.tap(".tab:has-text('More')");
await page.tap(".btn:has-text('Update words')");
await page.waitForTimeout(400);
ok((await ev(page, () => window.__app.deck.words.length)) >= 16, "update adds the new cards");
ok((await ev(page, () => window.__app.deck.words[0].level)) === 2, "update keeps the progress of existing cards");
await page.close();

// ---- the repo has a folder for this name: cards load without levels, per-name storage
page = await fresh();
await sign(page, "DEVORIAH");
await page.waitForSelector(".card");
ok((await ev(page, () => window.__app.deck.words.length)) === 323, "name matches the folder whatever the case");
ok((await ev(page, () => window.__app.deck.words.every((w) => w.level === null))), "repo cards carry no progress");
ok((await ev(page, () => Object.keys(window.__app.conj).length)) > 0, "tables are loaded from the same folder");
await page.close();

// ---- an install from before names existed keeps its words and progress
page = await fresh();
await ev(page, () => new Promise((resolve) => {
  const open = indexedDB.open("flashcards-web", 1);
  open.onsuccess = () => {
    const t = open.result.transaction("kv", "readwrite");
    t.objectStore("kv").put([{ word: "stary", translation: "old", level: 3 }, { word: "kot", translation: "cat", level: 1 }], "words");
    t.objectStore("kv").put({ sessions: 7 }, "stats");
    t.oncomplete = () => resolve();
  };
}));
await sign(page, "Maria");
await page.waitForSelector(".card");
ok((await ev(page, () => window.__app.deck.words.length)) === 2, "old words are kept, not replaced by the repo");
ok((await ev(page, () => window.__app.deck.words[0].level)) === 3, "old progress is kept");
ok((await ev(page, () => window.__app.stats.sessions)) === 7, "old statistics are kept");
await page.tap(".tab:has-text('More')");
await page.tap(".btn:has-text('Change')");
await page.tap(".sheet .btn:has-text('Change')");
await page.waitForSelector(".welcome input");
await sign(page, "Maria");
await page.waitForSelector(".card");
ok((await ev(page, () => window.__app.deck.words.length)) === 2, "changing the name and back finds the same data");
await page.close();

ok(errors.length === 0, "no console errors " + errors.join(" | "));
await browser.close(); server.close?.();
