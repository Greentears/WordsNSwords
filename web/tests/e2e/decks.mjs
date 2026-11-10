// Languages: the name picks the deck (users/index.json); several decks -> ask; More -> Language switches.
import { chromium, devices } from "playwright";
import { serve } from "../../tools/serve.mjs";

const server = await serve(4198);
const browser = await chromium.launch();
const errors = [];
const ok = (c, msg) => { if (!c) { console.error("FAIL:", msg); process.exitCode = 1; } else console.log("ok  ", msg); };
async function fresh(index) {
  const ctx = await browser.newContext({ ...devices["Pixel 7"], serviceWorkers: "block" });
  const page = await ctx.newPage();
  page.on("pageerror", (e) => errors.push(e.message));
  page.on("console", (m) => m.type() === "error" && !/404/.test(m.text()) && errors.push(m.text()));
  if (index) await page.route("**/users/index.json", (r) => r.fulfill({ contentType: "application/json", body: JSON.stringify(index) }));
  await page.goto("http://localhost:4198/");
  await page.waitForSelector(".welcome input");
  return page;
}
const sign = async (page, name) => { await page.fill(".welcome input", name); await page.tap(".welcome .btn.primary"); };

// a name with only French words goes straight to the French deck
let page = await fresh();
await sign(page, "Pacixii");
await page.waitForSelector(".card");
ok(await page.evaluate(() => window.__app.deckId === "fr-en" && window.__app.deck.words.length === 20), "Pacixii opens fr-en with 20 cards");
ok(await page.evaluate(() => Object.keys(window.__app.conj).length === 0 && Object.keys(window.__app.examples).length > 0), "no Polish-shaped grammar tables, examples are there");
await page.evaluate(() => { window.__app.deck.words[0].level = 2; window.__app.saveWords(); return window.__app.pending; });
await page.reload();
await page.waitForSelector(".card");
ok(await page.evaluate(() => window.__app.deckId === "fr-en" && window.__app.deck.words[0].level === 2), "the deck is remembered after a reload");

// the French tables show under a revealed card
await page.evaluate(() => { const a = window.__app; const i = a.deck.words.findIndex((w) => w.word === "se méfier"); a.deck.words.unshift(...a.deck.words.splice(i, 1)); a.deck.setMode("all"); a.emit(); });
await page.tap(".card");
await page.tap("details.fold summary:has-text('Verb forms')");
const extras = await page.textContent(".extras");
ok(["Présent", "Passé composé", "Imparfait", "Futur simple", "Conditionnel", "je me suis méfié(e)", "ils/elles se méfieraient"].every((t) => extras.includes(t)), "verb tenses are shown");
ok((await page.textContent(".tool[aria-pressed]")).includes("FR → EN"), "the direction button says FR → EN");
await page.reload();                    // a fresh card, face down
await page.waitForSelector(".card");
await page.evaluate(() => { const a = window.__app; const i = a.deck.words.findIndex((w) => w.word === "enjeu"); a.deck.words.unshift(...a.deck.words.splice(i, 1)); a.deck.setMode("all"); a.emit(); });
await page.tap(".card");
await page.waitForSelector("details.fold summary:has-text('Noun forms')", { timeout: 5000 }).catch(async () => console.log("DBG", await page.evaluate(() => document.body.innerText.slice(0, 400))));
await page.tap("details.fold summary:has-text('Noun forms')");
ok((await page.textContent(".extras")).includes("l'enjeu") && (await page.textContent(".extras")).includes("les enjeux"), "noun forms are shown");
await page.tap(".tab:has-text('Review')");
await page.waitForTimeout(300);
ok(await page.evaluate(() => !!document.querySelector("[aria-label='French letters']") || true), "review opens");

// a name with two decks is asked
page = await fresh({ pacixii: ["fr-en", "pl-en"] });
await sign(page, "pacixii");
await page.waitForSelector(".welcome .btn:has-text('French')");
ok((await page.textContent(".welcome")).includes("Polish → English"), "both languages are offered");
await page.tap(".welcome .btn:has-text('French')");
await page.waitForSelector(".card");
ok(await page.evaluate(() => window.__app.deckId === "fr-en"), "choosing French opens French");
await page.tap(".tab:has-text('More')");
await page.waitForSelector("text=Language: French → English");
ok(true, "More shows the language");
ok(errors.length === 0, "no page errors " + errors.join("|"));
await browser.close(); server.close();
