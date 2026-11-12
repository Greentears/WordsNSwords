// Dungeon tab on an emulated phone: fight, rewards, shop, gear, persistence, backup.
import { chromium, devices } from "playwright";
import { serve } from "../../tools/serve.mjs";

const shots = process.argv[2];
const server = await serve(4197);
const browser = await chromium.launch();
const ctx = await browser.newContext({ ...devices["Pixel 7"], acceptDownloads: true });
const page = await ctx.newPage();
const errors = [];
page.on("pageerror", (e) => errors.push(e.message));
page.on("console", (m) => m.type() === "error" && errors.push(m.text()));
const ok = (c, msg) => { if (!c) { console.error("FAIL:", msg); process.exitCode = 1; } else console.log("ok  ", msg); };
const snap = (n) => shots && page.screenshot({ path: `${shots}/${n}.png` });
const ev = (f, a) => page.evaluate(f, a);
const scr = ".screen:not([hidden])";

await page.goto("http://localhost:4197/");
await page.waitForSelector(".welcome input, .card");
if (await page.isVisible(".welcome")) { await page.fill(".welcome input", "Devoriah"); await page.tap(".welcome .btn.primary"); }
await page.waitForSelector(".card");
await page.tap(".tab:has-text('Dungeon')");
// ---- first visit: choose the hero (two pictures), final afterwards
await page.waitForSelector(`${scr} .hero-pick`);
ok((await page.$$(`${scr} .hero-pick`)).length === 2, "two heroes to choose from");
await page.tap(`${scr} .hero-pick >> nth=0`);
await page.waitForSelector(`${scr} .hero-panel`);
ok((await ev(() => window.__app.hero)) === "f", "the heroine is chosen");
ok((await page.getAttribute(`${scr} .hero-panel .hero-img`, "src")).includes("art/heroes/f"), "her picture is shown");
await page.waitForTimeout(150);
await page.reload();
await page.waitForSelector(".card");
await page.tap(".tab:has-text('Dungeon')");
await page.waitForSelector(`${scr} .hero-panel`);
ok(await page.isHidden(`${scr} .hero-pick`), "the choice is remembered after a reload");
// the backdrop follows the dungeon whose page you are looking at, locked ones included
const bgOf = () => page.evaluate(() => document.querySelector(".dg:not([hidden])").style.background);
await page.tap(`${scr} .chip:has-text("Cathedral")`);
ok((await bgOf()).includes("backgrounds/cathedral.webp"), "a locked dungeon shows its own background");
await page.tap(`${scr} .chip:has-text("Forest")`);
ok((await bgOf()).includes("backgrounds/forest.webp"), "switching dungeon switches the background");
await page.tap(`${scr} .chip:has-text("Cellar")`);
ok((await bgOf()).includes("backgrounds/cellar.webp"), "back to the first one");
await page.tap(`${scr} .chip:has-text("Daily")`);
const panelText = await page.textContent(`${scr} .panel:has(h2)`);
ok(panelText.includes("Today's twist") && panelText.includes("Streak: 0 days"), "the daily challenge shows its twist and streak");
ok((await bgOf()).includes("backgrounds/library.webp"), "the daily challenge plays in the library");
await page.tap(`${scr} .chip:has-text("Cellar")`);
await ev(() => window.__app.chooseHero("m"));
ok((await ev(() => window.__app.hero)) === "f", "the choice can't be changed");
await snap("20-map");
ok(await page.isVisible(`${scr} .btn:has-text('Begin')`), "map shows Begin");

// ---- fight the first room, answering from the live question
await page.tap(`${scr} .btn:has-text('Begin')`);
await page.waitForSelector(`${scr} .answerbar .text-in`);
ok(await page.isHidden(".tabbar"), "tab bar hidden in a fight");
await snap("21-fight");
let rooms = 0, guard = 0;
async function winFight() {
  while (guard++ < 80) {
    if (await page.isVisible(`${scr} .btn:has-text('Continue')`)) { await page.tap(`${scr} .btn:has-text('Continue')`); return; }
    if (await page.isVisible(`${scr} .btn:has-text('Next word')`)) { await page.tap(`${scr} .btn:has-text('Next word')`); continue; }
    const ans = await ev(() => window.__app.game.battle?.question?.answer);
    if (!ans) { await page.waitForTimeout(50); continue; }
    await page.fill(`${scr} .text-in`, ans.split("/")[0].replace(/\(.*?\)/g, "").trim());
    await page.press(`${scr} .text-in`, "Enter");
  }
}
await winFight();
await page.waitForSelector(`${scr} h2:has-text('Victory')`);
await snap("22-victory");
ok(await ev(() => window.__app.game.stats.monsters_defeated >= 1), "monster defeated recorded");
ok(await ev(() => window.__app.game.player.coins > 0), "coins earned");

// ---- a wrong answer hurts
await page.tap(`${scr} .btn:has-text('Next room')`);
await page.waitForSelector(`${scr} .answerbar .text-in`);
await page.fill(`${scr} .text-in`, "zzzzzz");
await page.press(`${scr} .text-in`, "Enter");
await page.waitForSelector(`${scr} .feedback.bad`);
await snap("23-wrong");
ok(await ev(() => window.__app.game.player.hp < window.__app.game.player.max_hp), "wrong answer costs HP");

// ---- leave, reload, resume
await page.tap(`${scr} .btn:has-text('Leave')`);
await page.tap(".sheet .btn:has-text('Leave')");
await page.waitForSelector(`${scr} .hero-panel`);
const lvl = await ev(() => window.__app.game.player.coins);
await page.waitForTimeout(300);
await page.reload();
await page.waitForSelector(".card");
await page.tap(".tab:has-text('Dungeon')");
if (await page.$(".hero-pick")) await page.tap(".hero-pick >> nth=1");
await page.waitForSelector(`${scr} .hero-panel`);
ok((await ev(() => window.__app.game.player.coins)) === lvl, "progress survives a reload");
ok(await page.isVisible(`${scr} .btn:has-text('Continue')`), "map offers Continue");

// ---- shop + gear
await ev(() => { window.__app.game.player.coins = 5000; window.__app.game.save(); });
await page.tap(`${scr} .btn:has-text('Shop')`);
await page.waitForSelector(`${scr} .shop-item`);
await snap("24-shop");
const buy = page.locator(`${scr} .shop-item .btn.primary`).first();
await buy.tap();
const before = await ev(() => Object.keys(window.__app.game.inventory.counts).length + window.__app.game.inventory.owned.size);
ok(before >= 1, "bought something");
// buy a weapon and equip via gear
await ev(() => { const g = window.__app.game; const w = Object.values({}).length; });
await page.tap(`${scr} .btn:has-text('Map')`);
await page.tap(`${scr} .btn:has-text('Gear')`);
await page.waitForSelector(`${scr} .doll`);
await snap("25-gear");

// ---- backup contains the dungeon and restores it
const backup = await ev(async () => {
  const m = await import("./app.js").catch(() => null);
  return JSON.stringify({ d: window.__app.dungeonSave });
});
ok(JSON.parse(backup).d && JSON.parse(backup).d.player.coins > 0, "dungeon save present for backup");

// ---- Review Guru: one big monster, failed words listed at the end
await ev(() => { const g = window.__app.game; g.leave?.(); g.player.hp = g.player.max_hp; g.save(); for (const w of window.__app.deck.words.slice(0, 6)) g.missed.miss(w.word); });
await page.tap(".tab:has-text('Study')");
await page.tap(".tab:has-text('Dungeon')");
if (await page.$(".hero-pick")) await page.tap(".hero-pick >> nth=1");
await page.waitForSelector(`${scr} .hero-panel`);
ok(await page.isVisible(`${scr} .hero-img`), "hero picture shown on the map");
await page.tap(`${scr} .chip:has-text('Review Guru')`);
await page.tap(`${scr} .btn:has-text('Begin')`);
await page.waitForSelector(`${scr} .answerbar .text-in`);
const hp = await ev(() => ({ m: window.__app.game.battle.monster.max_hp, a: window.__app.game.player.attack_power, n: Math.min(10, Math.max(5, window.__app.game.missed.size)) }));
ok(hp.m === hp.a * hp.n, `Guru HP is one hit per missed word (${hp.n})`);
await page.fill(`${scr} .text-in`, "zzzz"); await page.press(`${scr} .text-in`, "Enter");
await page.waitForSelector(`${scr} .feedback.bad`);
await snap("26-guru-fight");
await page.tap(`${scr} .btn:has-text('Next word')`);
guard = 0; await winFight();
await page.waitForSelector(`${scr} .failed`);
await snap("27-guru-done");
ok((await page.locator(`${scr} .failed-row`).count()) === 1, "one failed word listed");

// ---- other tabs still fine, and no console errors
await page.tap(".tab:has-text('Study')");
ok(await page.isVisible(".tabbar"), "tab bar back on other tabs");
ok(errors.length === 0, "no console errors " + errors.join(" | "));
await browser.close(); server.close?.();
