// Phone-emulation check: offline install, study 20 cards, change levels, reload, progress intact.
import { chromium, devices } from "playwright";
import { serve } from "../../tools/serve.mjs";

const shots = process.argv[2];
const server = await serve(4199);
const browser = await chromium.launch();
const ctx = await browser.newContext({ ...devices["Pixel 7"], serviceWorkers: "allow" });
const page = await ctx.newPage();
const errors = [];
page.on("pageerror", (e) => errors.push(e.message));
page.on("console", (m) => m.type() === "error" && errors.push(m.text()));
const ok = (c, msg) => { if (!c) { console.error("FAIL:", msg); process.exitCode = 1; } else console.log("ok  ", msg); };
const snap = (n) => shots && page.screenshot({ path: `${shots}/${n}.png` });

await page.goto("http://localhost:4199/");
await page.waitForSelector(".welcome input, .card");
if (await page.isVisible(".welcome")) { await page.fill(".welcome input", "Devoriah"); await page.tap(".welcome .btn.primary"); }
await page.waitForSelector(".card");
await page.evaluate(() => navigator.serviceWorker.ready);
await page.waitForTimeout(500);
await page.evaluate(() => { window.__app.deck.resetProgress(); return window.__app.pending; });
await page.reload(); await page.waitForSelector(".card");
ok(await page.evaluate(() => !!navigator.serviceWorker.controller), "service worker controls the page");
await snap("01-study");

// study 20 cards: tap to flip, then pick levels 0..2 in rotation
const before = await page.evaluate(() => window.__app.deck.words.filter((w) => w.level !== null).length);
const marked = [];
for (let i = 0; i < 20; i++) {
  await page.tap(".card");
  if (i === 0) await snap("02-revealed");
  const id = await page.evaluate(() => window.__app.deck.currentId);
  const lv = i % 3;
  await page.tap(`.levels .lv-${lv}`);
  marked.push([id, lv]);
}
const after = await page.evaluate(() => window.__app.deck.words.filter((w) => w.level !== null).length);
ok(before === 0 && after === 20, `20 cards marked (${before} -> ${after})`);
await page.evaluate(() => window.__app.pending);
await page.reload();
await page.waitForSelector(".card");
const lvls = await page.evaluate((m) => m.map(([id]) => window.__app.deck.words[id].level), marked);
ok(JSON.stringify(lvls) === JSON.stringify(marked.map(([, l]) => l)), "levels survive a reload");

// offline reload
await ctx.setOffline(true);
await page.reload();
await page.waitForSelector(".card");
ok(true, "opens offline");
await ctx.setOffline(false);

// swipe
const first = await page.evaluate(() => window.__app.deck.index);
const box = await page.locator(".card").boundingBox();
await page.mouse.move(box.x + box.width - 20, box.y + 60);
await page.mouse.down(); await page.mouse.move(box.x + 30, box.y + 66, { steps: 5 }); await page.mouse.up();
ok((await page.evaluate(() => window.__app.deck.index)) === first + 1, "swipe left goes to next card");

// chip filter + quick set
await page.tap(".chip:has-text('Learning')");
ok(await page.evaluate(() => window.__app.deck.mode) === "level1", "chip filters");
await page.tap(".tool:has-text('Quick')"); await page.tap(".list-btn:has-text('All cards')");
ok(await page.evaluate(() => window.__app.deck.total) === 10, "quick set = 10 cards");

// dark mode screenshot + landscape
await page.evaluate(() => { window.__app.settings.theme = "dark"; window.__app.saveSettings(); });
await page.tap(".card"); await snap("03-dark");
ok(errors.length === 0, "no console errors " + errors.join("|"));
await browser.close(); server.close();
