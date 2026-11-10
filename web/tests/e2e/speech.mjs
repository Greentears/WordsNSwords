// The speaker button reads the word being learned (never the English side) and does not flip the card.
import { chromium, devices } from "playwright";
import { serve } from "../../tools/serve.mjs";
let bad = 0;
const ok = (c, m) => { console.log((c ? "ok  " : "FAIL") + " " + m); if (!c) bad++; };
const server = await serve(4236);
const b = await chromium.launch();
const ctx = await b.newContext({ ...devices["Pixel 7"], serviceWorkers: "block" });
await ctx.addInitScript(() => {
  window.__said = [];
  const voice = { lang: "pl-PL", name: "Fake Polish" };
  window.SpeechSynthesisUtterance = class { constructor(t) { this.text = t; } };
  Object.defineProperty(window, "speechSynthesis", { value: { getVoices: () => [voice], addEventListener() {}, removeEventListener() {}, cancel() {}, speak: (u) => window.__said.push({ text: u.text, lang: u.lang, voice: u.voice?.name }) } });
});
const page = await ctx.newPage();
await page.goto("http://localhost:4236/");
await page.waitForSelector(".welcome input, .card");
if (await page.isVisible(".welcome")) { await page.fill(".welcome input", "Devoriah"); await page.tap(".welcome .btn.primary"); }
await page.waitForSelector(".card");
const word = await page.evaluate(() => window.__app.deck.current.word);
const meaning = await page.evaluate(() => window.__app.deck.current.translation);
await page.tap(".card .speak");
await page.waitForTimeout(200);
let said = await page.evaluate(() => window.__said);
ok(said.length === 1 && said[0].lang === "pl-PL" && said[0].voice === "Fake Polish", "speaks with the Polish voice");
ok(said[0].text.replace(/\s+/g, " ") === word.replace(/[()]/g, " ").replace(/\s+/g, " ").trim(), "speaks the Polish word");
ok(!(await page.$(".card.revealed")), "tapping the speaker does not flip the card");
// English first: the Polish word is still the one spoken
await page.tap(".tool[aria-pressed]");
await page.waitForSelector(".card .speak");
await page.tap(".card .speak");
await page.waitForTimeout(200);
said = await page.evaluate(() => window.__said);
ok(said.length === 2 && said[1].text !== meaning, "in English-first mode it still speaks the Polish word");
await b.close(); server.close?.();
process.exit(bad ? 1 : 0);
