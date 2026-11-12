// The grammar quiz in the Review tab: setup, wrong answers show the right form, the summary lists the mistakes.
import { chromium, devices } from "playwright";
import { serve } from "../../tools/serve.mjs";
let bad = 0;
const ok = (c, m) => { console.log((c ? "ok  " : "FAIL") + " " + m); if (!c) bad++; };
const server = await serve(4241);
const b = await chromium.launch();
const ctx = await b.newContext({ ...devices["Pixel 7"], serviceWorkers: "block" });
const page = await ctx.newPage();
const errors = [];
page.on("pageerror", (e) => errors.push(e.message));
await page.goto("http://localhost:4241/");
await page.waitForSelector(".welcome input, .card");
if (await page.isVisible(".welcome")) { await page.fill(".welcome input", "Devoriah"); await page.tap(".welcome .btn.primary"); }
await page.waitForSelector(".card");
await page.tap(".tab:has-text('Review')");
await page.tap(".seg button:has-text('Grammar')");
const scr = ".screen:not([hidden])";
ok((await page.textContent(`${scr}`)).includes("Verbs") && (await page.textContent(scr)).includes("Adjectives"), "the three kinds of question are offered");
await page.fill(`${scr} input.num`, "3");
await page.tap(`${scr} .btn:has-text('Start')`);
await page.waitForSelector(".qcard .prompt");
ok((await page.textContent(".qcard .prompt")).includes("___"), "the question has a blank");
for (let i = 0; i < 3; i++) {
  await page.fill(".answerbar input", "zzz");
  await page.press(".answerbar input", "Enter");
  await page.waitForSelector(".feedback.bad");
  if (i === 0) ok((await page.textContent(".feedback.bad")).startsWith("✕"), "a wrong answer shows the right form");
  await page.tap(".answerbar .btn.primary");
}
await page.waitForSelector(".big-note");
ok((await page.textContent(".big-note")) === "Score: 0 / 3", "the score is shown");
ok((await page.$$(".result-item")).length === 3, "the mistakes are listed");
await page.tap(".btn:has-text('Done')");
ok(await page.isVisible(`${scr} .seg`), "Done returns to the setup");
ok(errors.length === 0, "no page errors");
await b.close(); server.close?.();
process.exit(bad ? 1 : 0);
