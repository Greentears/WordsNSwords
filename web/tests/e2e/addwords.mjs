// Add words: prompt is built from the list, bad answers are explained, a good answer adds cards + tables and survives a reload.
import { chromium, devices } from "playwright";
import { serve } from "../../tools/serve.mjs";

const server = await serve(4197);
const browser = await chromium.launch();
const errors = [];
const ok = (c, msg) => { if (!c) { console.error("FAIL:", msg); process.exitCode = 1; } else console.log("ok  ", msg); };
const ctx = await browser.newContext({ ...devices["Pixel 7"], serviceWorkers: "block", permissions: ["clipboard-read", "clipboard-write"] });
const page = await ctx.newPage();
page.on("pageerror", (e) => errors.push(e.message));
page.on("console", (m) => m.type() === "error" && !/404/.test(m.text()) && errors.push(m.text()));
await page.goto("http://localhost:4197/");
await page.waitForSelector(".welcome input");
await page.fill(".welcome input", "Devoriah"); await page.tap(".welcome .btn.primary");
await page.waitForSelector(".card");
const before = await page.evaluate(() => window.__app.deck.words.length);
await page.tap(".tab:has-text('More')");
await page.tap(".btn:has-text('Add words')");
await page.waitForSelector(".sheet.open textarea");
const areas = page.locator(".sheet.open textarea");
await areas.nth(0).fill("1. kot\n- pić\n\n  zielony");
await page.tap(".sheet.open .btn:has-text('Copy the prompt')");
await page.waitForTimeout(300);
const clip = await page.evaluate(() => navigator.clipboard.readText()).catch(() => "");
ok(clip.includes("WORDS:\n- kot\n- pić\n- zielony") && !clip.includes("{WORDS}"), "prompt copied with the words inserted");

await areas.nth(1).fill("not json at all");
await page.tap(".sheet.open .btn:has-text('Check and add')");
await page.waitForSelector(".aw-bad");
ok((await page.textContent(".aw-bad")).includes("Nothing was added"), "invalid JSON is refused");
ok((await page.evaluate(() => window.__app.deck.words.length)) === before, "nothing was added");

const Q7 = ["a", "b", "c", "d", "e", "f", "g"];
const good = { words: [{ word: "kot", translation: "cat" }, { word: "pić", translation: "to drink" }],
  verbs: [{ card: "pić", verbs: [{ infinitive: "pić", aspect: "imperfective", forms: ["1", "2", "3", "4", "5", "6"] }] }],
  nouns: [{ card: "kot", nouns: [{ lemma: "kot", gender: "m", singular: Q7, plural: Q7 }] }],
  sentences: [{ pl: "Kot pije.", en: "The cat drinks.", words: ["kot", "pić"] }] };
await areas.nth(1).fill(JSON.stringify({ ...good, verbs: [{ card: "nope", verbs: [] }] }));
await page.tap(".sheet.open .btn:has-text('Check and add')");
await page.waitForSelector(".aw-bad");
ok((await page.textContent(".aw-result")).includes("Copy the problems"), "problems come with a copy button");

await areas.nth(1).fill("```json\n" + JSON.stringify(good) + "\n```");
await page.tap(".sheet.open .btn:has-text('Check and add')");
await page.waitForSelector(".aw-ok");
const added = await page.evaluate(() => ({ n: window.__app.deck.words.length, has: window.__app.deck.words.some((w) => w.word === "kot"), conj: !!window.__app.conj["pić"], decl: !!window.__app.decl["kot"] }));
ok(added.n === before + 2, "the two new cards are appended");
ok(added.has && added.conj && added.decl, "cards and tables are available");
await page.evaluate(() => window.__app.pending);
await page.reload();
await page.waitForSelector(".card");
ok(await page.evaluate(() => !!window.__app.decl["kot"] && window.__app.deck.words.some((w) => w.word === "kot")), "survives a reload");

// ---- send for review (GitHub is a fake served by the test)
const calls = [];
await page.route("https://api.github.com/**", async (route) => {
  const req = route.request(); const url = new URL(req.url()); const path = url.pathname.replace("/repos/Greentears/WordsNSwords", "");
  const cors = { "access-control-allow-origin": "*", "access-control-allow-headers": "*", "access-control-allow-methods": "*" };
  if (req.method() === "OPTIONS") return route.fulfill({ status: 204, headers: cors });
  calls.push(`${req.method()} ${path} ${req.headers().authorization ?? ""}`);
  const json = (status, body) => route.fulfill({ status, headers: cors, contentType: "application/json", body: JSON.stringify(body) });
  if (req.method() === "GET" && path.endsWith("/words.json")) return json(200, { sha: "s1", content: Buffer.from('[{"word":"a","translation":"b"}]').toString("base64") });
  if (req.method() === "GET" && path.includes("/contents/")) return json(404, {});
  if (path === "/git/ref/heads/main") return json(200, { object: { sha: "H" } });
  if (path === "/git/refs") return json(201, {});
  if (path === "/pulls") return json(201, { html_url: "https://github.com/Greentears/WordsNSwords/pull/9" });
  return json(200, {});
});
await page.tap(".tab:has-text('More')");
await page.tap(".btn:has-text('Add words')");
await page.waitForSelector(".aw-pending");
ok((await page.textContent(".aw-send")).includes("1 answer added here, not sent yet"), "unsent additions are announced after a reload");
await page.tap(".sheet.open .btn:has-text('Copy what I added instead')");
await page.waitForTimeout(200);
const copied = JSON.parse(await page.evaluate(() => navigator.clipboard.readText()));
ok(copied.words.length === 2 && copied.sentences.length === 1, "fallback copies the combined answer");
await page.fill(".aw-send input[type=password]", "ghp_secret");
await page.tap(".aw-send .btn:has-text('Save token')");
await page.waitForSelector(".aw-send .btn:has-text('Send for review')");
await page.tap(".aw-send .btn:has-text('Send for review')");
await page.waitForSelector(".aw-send a");
ok((await page.textContent(".aw-send a")).endsWith("/pull/9"), "pull request link is shown");
ok(calls.some((c) => c === "POST /pulls Bearer ghp_secret") && calls.some((c) => c.startsWith("PUT /contents/users/devoriah/pl-en/words.json")), "token is sent as Bearer, files are committed");
ok((await page.evaluate(() => window.__app.unsent.length)) === 0, "nothing is pending after sending");
ok(!JSON.stringify(await page.evaluate(() => { const a = window.__app; return { s: a.settings, d: a.deck.words.length, st: a.stats }; })).includes("ghp_secret"), "token is not in settings or stats");
ok(errors.length === 0, "no page errors " + errors.join("|"));
await browser.close(); server.close();
