// The Vocabulary Dungeon tab: map, fight, result messages, shop and gear.
// All rules live in src/dungeon (a port of the desktop game); this file is only the touch interface.
import {
  ACTIVE, ARMOR, CHARM, COMPANION, DEFEAT, GameError, ITEMS, SELL_FRACTION, SPRITE_KEYS, VICTORY, WEAPON,
  abilities, dungeonEndless, isEquipment, isFight, outcomeMessages, spritePixels, SIZE,
  type AnswerResult, type DungeonStatus, type Item, type Question, type RoomOutcome,
} from "../dungeon";
import { STAT_KEYS, STAT_NAMES, DESCRIPTIONS as STAT_DESCRIPTIONS, effectText } from "../dungeon/stats";
import { artUrl, hasArt, heroArt, heroChoiceAvailable, sceneKey } from "../art";
import { accentRow, answerInput } from "./quiz";
import { languageInfo } from "../state";
import { clear, h } from "./h";
import { seg, type Shell } from "./shell";

const ITEM_ICONS: Record<string, string> = {
  letter_scroll: "📜", count_rune: "🔢", oracle_eye: "🔮", small_potion: "🧪", big_potion: "⚗️", fire_bomb: "💣",
  lightning: "⚡", meteor: "☄️", ward_scroll: "🛡️", passage_scroll: "🌀", wisdom_tome: "📖", golden_idol: "🗿",
};
const SLOT_ICONS: Record<string, string> = { weapon: "🗡️", armor: "🧥", charm: "📿", companion: "🐾" };
const SLOT_NAMES: Record<string, string> = { weapon: "Weapon", armor: "Armor", charm: "Charm", companion: "Companion" };
const itemEmoji = (i: Item) => (isEquipment(i) ? i.icon || SLOT_ICONS[i.slot ?? ""] : ITEM_ICONS[i.key] ?? i.icon ?? "✦");
/** The picture of an item or companion if it has one, else its emoji. */
function itemIcon(i: Item): Node {
  const kind = i.slot === COMPANION ? "companions" : "items";
  return hasArt(kind, i.key) ? h("img", { class: "item-img", src: artUrl(kind, i.key), alt: i.name, draggable: false }) : document.createTextNode(itemEmoji(i));
}

type Pixels = (string | null)[][];
function sprite(pixels: Pixels, cls = ""): HTMLCanvasElement {
  const c = h("canvas", { width: SIZE, height: SIZE, class: "sprite " + cls }) as HTMLCanvasElement;
  const ctx = c.getContext("2d");
  if (ctx) pixels.forEach((row, y) => row.forEach((col, x) => { if (col) { ctx.fillStyle = col; ctx.fillRect(x, y, 1, 1); } }));
  return c;
}
const monsterSprite = (key: string, cls = ""): HTMLElement =>
  hasArt("monsters", key) ? h("img", { class: "sprite-img " + cls, src: artUrl("monsters", key), alt: key, draggable: false })
    : sprite(spritePixels(SPRITE_KEYS.includes(key) ? key : "slime"), cls);

function bar(value: number, max: number, cls: string, label?: string): HTMLElement {
  const pct = max > 0 ? Math.max(0, Math.min(100, (value / max) * 100)) : 0;
  return h("div", { class: "bar " + cls, role: "progressbar", "aria-valuenow": value, "aria-valuemax": max },
    h("div", { class: "bar-fill", style: { width: pct + "%" } }), h("span", { class: "bar-text" }, label ?? `${value} / ${max}`));
}

export function dungeonScreen(shell: Shell) {
  const { app } = shell;
  const root = h("section", { class: "screen dg" });
  let view: "map" | "fight" | "message" | "shop" | "gear" | "stats" = "map";
  const needsHero = () => !app.hero && heroChoiceAvailable();
  let selected: string | null = null;
  let shopMode: "buy" | "sell" = "buy";
  let message: { outcome: RoomOutcome | null; defeat: boolean } | null = null;
  // fight state
  const fs = { q: null as Question | null, remaining: 0, fb: null as { text: string; ok: boolean } | null, end: false, hint: "", flash: "" };
  let timer: number | null = null;

  const gm = () => app.game;
  /** The hero picture for his gender and the weapon and armor he wears (hero.png before there was art). */
  const heroImg = (cls = "") => {
    const worn = gm().inventory.equipped;
    const src = heroArt(app.hero, !!worn[WEAPON], !!worn[ARMOR]) ?? "hero.png";
    return h("img", { class: "hero-img " + cls, src, alt: "Your hero", draggable: false });
  };
  const fail = (e: unknown) => { shell.toast(e instanceof GameError || e instanceof Error ? e.message : "Something went wrong."); };

  // ------------------------------------------------------------------ timer
  function stopTimer() { if (timer !== null) { clearInterval(timer); timer = null; } }
  function startTimer() {
    stopTimer();
    const q = fs.q;
    if (!q || !q.time_limit || fs.end || view !== "fight") return;
    if (fs.remaining <= 0) fs.remaining = q.time_limit;
    timer = window.setInterval(() => {
      fs.remaining -= 1;
      const t = root.querySelector(".timer");
      if (t) { t.textContent = `⏱ ${Math.max(0, fs.remaining)}s`; t.classList.toggle("low", fs.remaining <= 3); }
      if (fs.remaining <= 0) { stopTimer(); apply(() => gm().timeout()); }
    }, 1000);
  }
  document.addEventListener("visibilitychange", () => {
    if (root.hidden) return;
    if (document.hidden) stopTimer(); else if (view === "fight") startTimer();
  });

  // ------------------------------------------------------------------ routing
  function show() {
    const g = gm();
    if (g.deck !== app.deck) { app.resetGame(app.dungeonSave); }
    if (view === "fight" && !gm().battle) view = "map";
    render();
  }
  function pause() { stopTimer(); }
  /** The dungeon's scenery behind its map, fights and messages, under a dark layer that keeps the text readable. */
  function applyBackdrop(mapKey?: string) {
    const key = view === "map" ? mapKey : gm().dungeon?.key;      // on the map: the dungeon whose page you are looking at
    const o = view === "message" ? message?.outcome : null;     // a rest or treasure room has its own picture
    const scene = o && (o.kind === "treasure" || o.kind === "rest") ? sceneKey(o.kind, key) : null;
    const pic = scene ?? (key === "daily" ? "library" : key);      // the daily challenge plays among the shelves
    const on = !!pic && (view === "map" || view === "fight" || view === "message") && hasArt("backgrounds", pic);
    const shade = scene ? "linear-gradient(rgba(8,6,14,.8), rgba(8,6,14,.06) 55%)"      // rest / treasure: bright below the text
      : "linear-gradient(rgba(8,6,14,.68), rgba(8,6,14,.68))";
    const fit = "center / cover fixed";
    root.style.background = on ? `${shade}, url(${artUrl("backgrounds", pic!)}) ${fit}` : "";
  }

  function render() {
    stopTimer();
    if (view !== "map") applyBackdrop();            // the map sets its own, for the dungeon you are viewing
    if (needsHero()) { shell.fullscreen(false); return renderHeroChoice(); }
    shell.fullscreen(view === "fight");
    if (view === "map") return renderMap();
    if (view === "fight") return renderFight();
    if (view === "message") return renderMessage();
    if (view === "shop") return renderShop();
    if (view === "stats") return renderStats();
    return renderGear();
  }
  function go(v: typeof view) { view = v; render(); }

  // ------------------------------------------------------------------ first visit: choose the hero
  function renderHeroChoice() {
    clear(root);
    const pick = (g: "f" | "m") => h("button", { class: "hero-pick", type: "button", "aria-label": g === "f" ? "Play as the heroine" : "Play as the hero",
      onclick: () => { app.chooseHero(g); render(); } },
      h("img", { src: heroArt(g, false, false) ?? "", alt: "", draggable: false }), h("b", null, g === "f" ? "Heroine" : "Hero"));
    root.append(h("div", { class: "hero-choice" }, h("h2", null, "Choose your hero"),
      h("p", { class: "muted" }, "Tap the hero you want to play. You can't change this later."),
      h("div", { class: "hero-picks" }, pick("f"), pick("m"))));
  }

  // ------------------------------------------------------------------ map
  function defaultKey(list: DungeonStatus[]): string {
    const g = gm();
    return (g.dungeon && list.find((d) => d.key === g.dungeon!.key)?.key) || list.find((d) => d.in_progress && !d.locked)?.key
      || list.find((d) => !d.locked && !d.completed)?.key || list[0].key;
  }

  function playerPanel(): HTMLElement {
    const p = gm().player;
    return h("div", { class: "panel hero-panel" },
      heroImg("hero-sm"),
      h("div", { class: "hero-info" },
        h("div", { class: "hero-name" }, `${p.name} · Lv ${p.level}`),
        bar(p.hp, p.max_hp, "hp", `HP ${p.hp} / ${p.max_hp}`),
        bar(p.xp, p.xp_needed, "xp", `XP ${p.xp} / ${p.xp_needed}`),
        h("div", { class: "coins" }, `🪙 ${p.coins}`),
        p.stat_points ? h("div", { class: "points-hint" }, `✨ ${p.stat_points} stat point${p.stat_points > 1 ? "s" : ""} to spend`) : null));
  }

  function renderMap() {
    const g = gm();
    const list = g.dungeons();
    if (!selected || !list.some((d) => d.key === selected)) selected = defaultKey(list);
    const cur = list.find((d) => d.key === selected)!;
    applyBackdrop(selected);
    const d = g.defs[cur.key];
    clear(root);

    const chips = h("div", { class: "chips" }, list.map((s) =>
      h("button", { class: "chip" + (s.key === selected ? " on" : ""), type: "button", onclick: () => { selected = s.key; renderMap(); } },
        s.locked ? "🔒" : s.kind === "daily" ? (s.completed ? "✔" : "📅") : s.completed ? "✔" : "", s.name, s.endless && s.best ? h("b", null, `${s.best}`) : null)));

    const rooms = h("div", { class: "rooms" });
    if (dungeonEndless(d)) {
      rooms.append(h("div", { class: "room cur" }, h("span", { class: "room-ico" }, "🗼"),
        h("span", { class: "room-title" }, `Floor ${cur.room + 1}`), h("span", { class: "room-state" }, cur.best ? `Best: floor ${cur.best}` : "Not started")));
    } else {
      d.rooms.forEach((r, i) => {
        const done = i < cur.room || (cur.completed && cur.room >= d.rooms.length);
        const ico = r.kind === "boss" ? "👑" : r.kind === "treasure" ? "💰" : r.kind === "rest" ? "🔥" : "⚔";
        rooms.append(h("div", { class: "room" + (i === cur.room && !cur.completed ? " cur" : "") + (done ? " done" : "") },
          h("span", { class: "room-ico" }, ico), h("span", { class: "room-title" }, r.title), h("span", { class: "room-state" }, done ? "✓" : "")));
      });
    }

    const label = dungeonEndless(d) ? (cur.room > 0 ? `Continue: floor ${cur.room + 1}` : "Climb the tower")
      : cur.kind === "daily" ? (cur.completed ? "Done today" : cur.in_progress ? "Continue" : "Begin today's challenge")
      : cur.completed && cur.room >= d.rooms.length ? "Play again" : cur.in_progress ? "Continue" : "Begin";
    const go1 = h("button", { class: "btn primary wide sticky", type: "button", disabled: !!cur.unavailable || !g.has_words, onclick: () => begin(cur.key) }, label);
    const stats = g.stats;

    root.append(
      h("div", { class: "scroll-body stack" },
        h("header", { class: "top" }, h("h1", null, "Vocabulary Dungeon")),
        playerPanel(),
        h("div", { class: "btn-row", style: { marginTop: "0" } },
          h("button", { class: "btn", type: "button", onclick: () => go("gear") }, "🎒 Gear"),
          h("button", { class: "btn" + (gm().player.stat_points ? " primary" : ""), type: "button", onclick: () => go("stats") }, `📈 Stats${gm().player.stat_points ? ` (${gm().player.stat_points})` : ""}`),
          h("button", { class: "btn", type: "button", onclick: () => go("shop") }, "🛒 Shop")),
        chips,
        h("div", { class: "panel" }, h("h2", null, cur.name), h("p", { class: "muted" }, cur.description),
          cur.note ? h("p", { class: "streak" }, `🔥 ${cur.note}`) : null,
          cur.min_level > 1 ? h("p", { class: "muted" }, `Requires level ${cur.min_level}`) : null,
          cur.unavailable ? h("p", { class: "warn" }, cur.unavailable) : null,
          !g.has_words ? h("p", { class: "warn" }, "No cards to fight with yet. Add some words first.") : null),
        rooms, go1,
        cur.in_progress && !dungeonEndless(d) && cur.kind !== "daily" ? h("button", { class: "btn ghost", type: "button", onclick: async () => { if (await shell.confirm("Restart this dungeon?", "You go back to room 1. Your level, coins and gear stay.", "Restart")) begin(cur.key, true); } }, "Restart from room 1") : null,
        h("p", { class: "muted small-note" }, `Missed words to review: ${g.missed_count} · Monsters defeated: ${stats.monsters_defeated ?? 0} · Right ${stats.correct_answers ?? 0} / wrong ${stats.wrong_answers ?? 0} · Dungeons cleared: ${stats.dungeons_completed ?? 0}`)));
  }

  function begin(key: string, restart = false) {
    try {
      const g = gm();
      g.select_dungeon(key, restart);
      const out = g.enter_room();
      if (out) { message = { outcome: out, defeat: false }; go("message"); return; }
      newQuestion(); go("fight");
    } catch (e) { fail(e); render(); }
  }

  // ------------------------------------------------------------------ fight
  function newQuestion() {
    const q = gm().next_question();
    fs.q = q; fs.fb = null; fs.end = false; fs.hint = ""; fs.flash = ""; fs.remaining = q?.time_limit ?? 0;
    if (!q) { shell.toast("No usable card for this fight."); gm().leave(); view = "map"; }
  }

  function apply(fn: () => AnswerResult) {
    stopTimer();
    try {
      const r = fn();
      fs.fb = { text: r.message, ok: r.correct || r.free }; fs.q = null; fs.end = r.state !== ACTIVE;
      fs.flash = r.damage_dealt ? "m" : r.damage_taken ? "p" : "";
      renderFight();
    } catch (e) { fail(e); }
  }

  function useItem(key: string) {
    try {
      const u = gm().use_item(key);
      if (!u.ok) { shell.toast(u.message); return; }
      if (u.result) { apply(() => u.result!); return; }
      if (u.hint) fs.hint = u.hint;
      fs.fb = { text: u.message, ok: true };
      if (u.state !== ACTIVE) { fs.end = true; fs.q = null; fs.flash = "m"; }
      renderFight();
    } catch (e) { fail(e); }
  }

  function finishFight() {
    const g = gm();
    if (g.battle?.state === VICTORY && g.outcome) { message = { outcome: g.outcome, defeat: false }; }
    else message = { outcome: null, defeat: true };
    go("message");
  }

  async function leaveFight() {
    if (!(await shell.confirm("Leave the fight?", "The monster keeps its current health. You can continue later.", "Leave"))) return;
    stopTimer(); gm().leave(); go("map");
  }

  function renderFight() {
    const g = gm();
    const b = g.battle;
    if (!b) { view = "map"; return renderMap(); }
    stopTimer();
    clear(root);
    const spec = b.monster.spec, q = fs.q;
    const p = g.player;
    const comp = g.inventory.equipped[COMPANION];

    const prompt = h("div", { class: "panel prompt-card" });
    if (q) {
      const what = (q.kind === "cloze") ? "Fill in the blank" : q.reverse ? `Type it in ${languageInfo(app.deckId).name}` : "Translate to English";
      prompt.append(h("div", { class: "muted" }, what), h("div", { class: "prompt" + ((q.kind === "cloze") ? " cloze" : "") }, q.prompt));
      if ((q.kind === "cloze") && q.gloss) prompt.append(h("div", { class: "muted" }, `Meaning: ${q.gloss}`));
      if (q.time_limit) prompt.append(h("div", { class: "timer" }, `⏱ ${Math.max(0, fs.remaining || q.time_limit)}s`));
      const hint = fs.hint || (q.show_first || q.show_count ? b.hint_text() : "");
      if (hint) prompt.append(h("div", { class: "hinttext" }, hint));
    } else if (fs.end) prompt.append(h("div", { class: "prompt" }, b.state === VICTORY ? `${spec.name} defeated!` : "You have fallen…"));
    else prompt.append(h("div", { class: "muted" }, "Next word…"));

    const arena = h("div", { class: "arena" },
      h("div", { class: "side" }, h("div", { class: "pair" }, heroImg("hero" + (fs.flash === "p" ? " flash" : "")),
        comp ? h("span", { class: "companion" }, itemIcon(ITEMS[comp])) : null),
        bar(p.hp, p.max_hp, "hp", `${p.hp}/${p.max_hp}`)),
      h("div", { class: "vs" }, "VS"),
      h("div", { class: "side" }, monsterSprite(spec.key, "monster" + (fs.flash === "m" ? " flash" : "")), bar(b.monster.hp, b.monster.max_hp, "mhp", `${b.monster.name} ${b.monster.hp}/${b.monster.max_hp}`)));
    const abil = abilities(spec, languageInfo(app.deckId).name);

    const items = g.usable_items();
    const itemBar = items.length === 0 ? null : h("div", { class: "itembar" },
      items.map(([it, n]) => h("button", { class: "item-btn", type: "button", title: it.name, "aria-label": `${it.name}: ${it.description}`, disabled: fs.end,
        onclick: () => useItem(it.key) }, h("span", null, itemIcon(it)), h("b", null, `×${n}`))));

    const mid = h("div", { class: "scroll-body stack fight-body" },
      h("div", { class: "fight-head" }, h("div", null, h("b", null, spec.name), spec.boss ? " 👑" : ""), h("button", { class: "btn small ghost", type: "button", onclick: leaveFight }, "Leave")),
      prompt, arena, abil.length ? h("div", { class: "muted abil" }, abil.join(" · ")) : null,
      fs.fb ? h("div", { class: "feedback " + (fs.fb.ok ? "ok" : "bad"), role: "status" }, fs.fb.text) : null);

    const bottom = h("div", { class: "answerbar" }, itemBar);
    if (fs.end) {
      bottom.append(h("button", { class: "btn primary wide", type: "button", onclick: finishFight }, "Continue"));
    } else if (!q) {
      bottom.append(h("button", { class: "btn primary wide", type: "button", onclick: () => { newQuestion(); view === "fight" ? renderFight() : render(); } }, "Next word"));
    } else {
      const input = answerInput(q.reverse ? `Type it in ${languageInfo(app.deckId).name}…` : "Type it in English…", languageInfo(app.deckId).code);
      const submit = () => { const t = input.value.trim(); if (t) apply(() => gm().answer(t)); };
      input.addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); submit(); } });
      bottom.append(...(q.reverse ? [accentRow(input, app.deckId)] : []), input,
        h("div", { class: "actions" },
          h("button", { class: "btn", type: "button", onclick: () => apply(() => gm().skip()) }, "Skip"),
          h("button", { class: "btn primary", type: "button", onclick: submit }, "⚔ Attack")));
      setTimeout(() => input.focus(), 0);
    }
    root.append(mid, bottom);
    fs.flash = "";
    if (q && !fs.end) startTimer();
  }

  // ------------------------------------------------------------------ messages
  /** After a review fight: every word you failed, with its meaning. */
  function failedBlock(): HTMLElement[] {
    const g = gm();
    if (g.dungeon?.kind !== "review") return [];
    const failed = g.review_failed_words;
    if (!failed.length) return [h("p", { class: "outcome-line" }, "No words failed. Perfect review!")];
    return [h("div", { class: "panel failed" }, h("h2", null, `Words you failed (${failed.length})`),
      ...failed.map(([w, t]) => h("div", { class: "failed-row" }, h("b", null, w), h("span", { class: "muted" }, t))))];
  }

  function renderMessage() {
    const g = gm();
    clear(root);
    const m = message!;
    const body = h("div", { class: "scroll-body stack center" });
    const btns = h("div", { class: "stack" });
    if (m.defeat) {
      body.append(heroImg("hero-msg"), h("h2", null, "Defeated"),
        h("p", { class: "muted" }, "You wake up healed. The monster has recovered too. Use your missed words as practice and try again."), ...failedBlock());
      btns.append(
        h("button", { class: "btn primary wide", type: "button", onclick: () => { try { g.retry(); newQuestion(); go("fight"); } catch (e) { fail(e); } } }, "Try again"),
        h("button", { class: "btn wide", type: "button", onclick: () => go("shop") }, "Visit the shop"),
        h("button", { class: "btn wide", type: "button", onclick: () => { g.leave(); go("map"); } }, "Back to the map"));
    } else {
      const o = m.outcome!;
      const key = o.kind === "treasure" ? "treasure" : o.kind === "rest" ? "rest" : g.battle?.monster.spec.key ?? "slime";
      const place = (o.kind === "treasure" || o.kind === "rest") && sceneKey(o.kind, g.dungeon?.key);   // the room's picture is the backdrop
      body.append(place ? h("span") : o.kind === "treasure" || o.kind === "rest" ? sprite(spritePixels(key), "big") : monsterSprite(key, "big dead"),
        h("h2", null, o.dungeon_completed ? "Dungeon complete!" : o.kind === "treasure" ? "Treasure!" : o.kind === "rest" ? "A moment of rest" : "Victory!"),
        h("p", { class: "muted" }, o.title),
        ...outcomeMessages(o).map((t) => h("p", { class: "outcome-line" }, t)));
      body.append(...failedBlock());
      if (o.dungeon_completed) body.append(h("p", { class: "muted" }, `This run: ${o.run.monsters ?? 0} monsters · ${o.run.correct ?? 0} right, ${o.run.wrong ?? 0} wrong ${g.dungeon?.kind === "review" ? "" : `· ${o.run.xp ?? 0} XP · ${o.run.coins ?? 0} coins`}`.trim()));
      const next = g.dungeon && !o.dungeon_completed ? (dungeonEndless(g.dungeon) ? "Next floor" : "Next room") : null;
      if (next) btns.append(h("button", { class: "btn primary wide", type: "button", onclick: () => begin(g.dungeon!.key) }, next));
      btns.append(h("button", { class: "btn wide" + (next ? "" : " primary"), type: "button", onclick: () => { g.leave(); go("map"); } }, "Back to the map"),
        h("button", { class: "btn wide ghost", type: "button", onclick: () => go("shop") }, "Visit the shop"));
    }
    root.append(body, h("div", { class: "answerbar" + (m.outcome && (m.outcome.kind === "rest" || m.outcome.kind === "treasure") ? " over" : "") }, btns));
  }

  // ------------------------------------------------------------------ shop
  function renderShop() {
    const g = gm();
    const old = root.querySelector(".scroll-body")?.scrollTop ?? 0;
    clear(root);
    const body = h("div", { class: "scroll-body stack" },
      h("header", { class: "top row-top" }, h("button", { class: "btn small", type: "button", onclick: () => go("map") }, "‹ Map"), h("h1", null, "Shop"), h("span", { class: "coins" }, `🪙 ${g.player.coins}`)),
      seg<"buy" | "sell">([["buy", "Buy"], ["sell", "Sell"]], shopMode, (v) => { shopMode = v; renderShop(); }));
    const card = (it: Item, extra: string, action: HTMLElement) =>
      h("div", { class: "shop-item" }, h("span", { class: "si-ico" }, itemIcon(it)),
        h("div", { class: "si-text" }, h("b", null, it.name), h("span", { class: "muted" }, it.description), extra ? h("span", { class: "muted" }, extra) : null), action);
    if (shopMode === "buy") {
      const entries = g.shop();
      const sections: [string, (e: typeof entries[number]) => boolean][] = [
        ["One-time items", (e) => !isEquipment(e.item)], ["Weapons", (e) => e.item.slot === WEAPON], ["Armor", (e) => e.item.slot === ARMOR],
        ["Charms", (e) => e.item.slot === CHARM], ["Companions", (e) => e.item.slot === COMPANION]];
      for (const [title, pick] of sections) {
        const list = entries.filter(pick);
        if (!list.length) continue;
        body.append(h("h2", null, title));
        for (const e of list) {
          const it = e.item;
          let action: HTMLElement;
          if (isEquipment(it) && e.owned) {
            action = e.equipped ? h("span", { class: "tag" }, "Equipped") :
              h("button", { class: "btn small", type: "button", onclick: () => { g.equip(it.key); shell.toast(`${it.name} equipped.`); renderShop(); } }, "Equip");
          } else {
            action = h("button", { class: "btn small primary", type: "button", disabled: !!e.problem, title: e.problem ?? "",
              onclick: () => { try { shell.toast(g.buy(it.key)); } catch (err) { fail(err); } renderShop(); } }, e.problem ?? `🪙 ${it.price}`);
          }
          body.append(card(it, [!isEquipment(it) && e.count ? `You carry ${e.count}` : "", it.level > 1 ? `Level ${it.level}` : "" ].filter(Boolean).join(" · "), action));
        }
      }
    } else {
      const sell = g.sellable();
      if (!sell.length) body.append(h("p", { class: "muted" }, "Nothing to sell."));
      body.append(h("p", { class: "muted" }, `Items sell for ${Math.round(SELL_FRACTION * 100)}% of their price.`));
      for (const s of sell) {
        body.append(card(s.item, s.count ? `You carry ${s.count}` : s.equipped ? "Currently equipped" : "",
          h("button", { class: "btn small", type: "button", onclick: async () => {
            if ((s.equipped || s.value >= 1000) && !(await shell.confirm(`Sell ${s.item.name}?`, `You get ${s.value} coins.${s.equipped ? " It is equipped right now." : ""}`, "Sell", true))) return;
            try { shell.toast(g.sell(s.item.key)); } catch (err) { fail(err); }
            renderShop();
          } }, `Sell 🪙 ${s.value}`)));
      }
    }
    root.append(body);
    body.scrollTop = old;
  }

  // ------------------------------------------------------------------ stats
  /** Points chosen on the stats screen but not applied yet: they only count after "Close & confirm". */
  let staged: Record<string, number> = {};
  const stagedTotal = () => Object.values(staged).reduce((a, n) => a + n, 0);

  function renderStats(note = "") {
    const g = gm();
    const p = g.player;
    const old = root.querySelector(".scroll-body")?.scrollTop ?? 0;
    clear(root);
    const left = p.stat_points - stagedTotal();
    const shown = (key: string) => (p.stats as Record<string, number>)[key] + (staged[key] ?? 0);
    const view = Object.fromEntries(STAT_KEYS.map((k) => [k, shown(k)])) as typeof p.stats;
    const stage = (stat: string, n: number) => { staged[stat] = Math.max(0, (staged[stat] ?? 0) + Math.min(n, left)); renderStats(); };
    const unstage = (stat: string) => { staged[stat] = Math.max(0, (staged[stat] ?? 0) - 1); renderStats(); };
    const row = (key: (typeof STAT_KEYS)[number]) => h("div", { class: "shop-item stat-row" },
      h("div", { class: "si-text" },
        h("b", null, `${STAT_NAMES[key]}: ${shown(key)}`, staged[key] ? h("span", { class: "points-hint" }, ` (+${staged[key]})`) : null),
        h("span", { class: "muted" }, STAT_DESCRIPTIONS[key]),
        h("span", { class: "stat-now" }, effectText(key, view, SELL_FRACTION))),
      h("div", { class: "stat-btns" },
        staged[key] ? h("button", { class: "btn small ghost", type: "button", "aria-label": `Take 1 point back from ${STAT_NAMES[key]}`, onclick: () => unstage(key) }, "−1") : null,
        h("button", { class: "btn small", type: "button", disabled: left < 1, "aria-label": `Add 1 point to ${STAT_NAMES[key]}`, onclick: () => stage(key, 1) }, "+1"),
        left > 5 ? h("button", { class: "btn small", type: "button", "aria-label": `Add 5 points to ${STAT_NAMES[key]}`, onclick: () => stage(key, 5) }, "+5") : null));
    const cost = g.respec_cost;
    const spent = STAT_KEYS.reduce((a, k) => a + p.stats[k], 0);
    const respec = async () => {
      if (!(await shell.confirm("Reset your points?", cost ? `This costs ${cost} coins and gives all ${spent} spent points back.` : `The first reset is free. All ${spent} spent points come back.`, cost ? `Pay ${cost}` : "Reset"))) return;
      try { staged = {}; g.respec(); renderStats("Points reset. Spend them again."); } catch (e) { if (e instanceof GameError) renderStats(e.message); else throw e; }
    };
    const confirmAndClose = () => {
      try {
        for (const [stat, n] of Object.entries(staged)) if (n > 0) g.spend_point(stat, n);
      } catch (e) { if (e instanceof GameError) { staged = {}; renderStats(e.message); return; } throw e; }
      staged = {};
      go("map");
    };
    const leave = async () => {
      if (stagedTotal() && !(await shell.confirm("Leave without confirming?", `The ${stagedTotal()} point${stagedTotal() > 1 ? "s" : ""} you chose will not be applied.`, "Leave"))) return;
      staged = {}; go("map");
    };
    const body = h("div", { class: "scroll-body stack" },
      h("header", { class: "top row-top" }, h("button", { class: "btn small", type: "button", onclick: leave }, "‹ Map"), h("h1", null, "Stats"), h("span", { class: "coins" }, `🪙 ${p.coins}`)),
      h("div", { class: "panel" }, h("b", null, `${p.name} · Level ${p.level}`),
        h("p", { class: left ? "points-hint" : "muted" }, left ? `✨ ${left} point${left > 1 ? "s" : ""} to spend` : p.stat_points ? "All points placed. Tap Close & confirm to apply them." : "No points to spend. You get 2 per level."),
        note ? h("p", { class: "warn" }, note) : null),
      STAT_KEYS.map(row),
      h("button", { class: "btn ghost", type: "button", disabled: spent === 0 || stagedTotal() > 0, onclick: respec }, cost ? `Reset points (${cost} coins)` : "Reset points (first one is free)"),
      h("button", { class: "btn primary wide", type: "button", onclick: confirmAndClose }, stagedTotal() ? "Close & confirm" : "Close"));
    root.append(body);
    body.scrollTop = old;
  }

  // ------------------------------------------------------------------ gear / inventory
  function renderGear() {
    const g = gm();
    const inv = g.inventory, p = g.player, t = inv.totals();
    clear(root);
    const slot = (name: string): HTMLElement => {
      const key = inv.equipped[name];
      const it = key ? ITEMS[key] : null;
      return h("button", { class: "slot s-" + name + (it ? " filled" : ""), type: "button", "aria-label": it ? `${SLOT_NAMES[name]}: ${it.name}. Tap to unequip` : `${SLOT_NAMES[name]}: empty`,
        onclick: () => { if (it) { g.unequip(name); renderGear(); } } },
        h("span", { class: "slot-ico" }, it ? itemIcon(it) : SLOT_ICONS[name]), h("span", { class: "slot-name" }, it ? it.name : SLOT_NAMES[name]));
    };
    const bonus: string[] = [];
    if (t.hp) bonus.push(`+${t.hp} HP`); if (t.attack) bonus.push(`+${t.attack} attack`); if (t.reduction) bonus.push(`−${t.reduction} damage taken`);
    if (t.xp_pct) bonus.push(`+${t.xp_pct}% XP`); if (t.coin_pct) bonus.push(`+${t.coin_pct}% coins`); if (t.time) bonus.push(`+${t.time}s per timed word`);
    if (t.phoenix) bonus.push("Phoenix: survive one lethal hit"); if (t.heal_on_correct) bonus.push(`Heal ${t.heal_on_correct} per right answer`);
    if (t.bonus_damage) bonus.push(`+${t.bonus_damage} damage`); if (t.dodge_pct) bonus.push(`${t.dodge_pct}% dodge`); if (t.start_ward) bonus.push("Starts each fight with a ward");

    const bag = g.usable_items();
    const stash = [...inv.owned].map((k) => ITEMS[k]).filter((it) => !inv.is_equipped(it.key));
    root.append(h("div", { class: "scroll-body stack" },
      h("header", { class: "top row-top" }, h("button", { class: "btn small", type: "button", onclick: () => go("map") }, "‹ Map"), h("h1", null, "Gear"), h("span", { class: "coins" }, `🪙 ${p.coins}`)),
      h("div", { class: "doll" + (hasArt("ui", "panel") ? " framed" : "") }, slot("weapon"), h("div", { class: "doll-mid" }, slot("companion"), slot("armor")), slot("charm"),
        h("div", { class: "doll-hero" }, heroImg("hero-big"),
          inv.equipped.companion ? h("span", { class: "doll-pet" }, itemIcon(ITEMS[inv.equipped.companion])) : null)),
      h("div", { class: "panel" }, h("b", null, `${p.name} · Level ${p.level}`),
        h("p", { class: "muted" }, `HP ${p.max_hp} · Attack ${p.attack_power}`), h("p", { class: "muted" }, bonus.length ? bonus.join(" · ") : "No equipment bonuses yet.")),
      h("h2", null, "Belt"), bag.length ? h("div", { class: "belt" }, bag.map(([it, n]) =>
        h("div", { class: "belt-cell", title: it.description }, h("span", null, itemIcon(it)), h("b", null, `×${n}`), h("small", null, it.name)))) : h("p", { class: "muted" }, "Empty. Potions and scrolls are in the shop."),
      h("h2", null, "Stash"), stash.length ? h("div", { class: "stack" }, stash.map((it) =>
        h("div", { class: "shop-item" }, h("span", { class: "si-ico" }, itemIcon(it)), h("div", { class: "si-text" }, h("b", null, it.name), h("span", { class: "muted" }, it.description)),
          h("button", { class: "btn small", type: "button", onclick: () => { g.equip(it.key); renderGear(); } }, "Equip")))) : h("p", { class: "muted" }, "Nothing in the stash.")));
  }

  Object.assign(root, { show, pause });
  return root;
}
