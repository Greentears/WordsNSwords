import { h, clear } from "./h";
import { ARCHIVED, LEVELS, TOP_LEVEL, levelIcon, levelName, type Mode } from "../core/deck";
import type { Shell } from "./shell";
import { extras } from "./tables";

const CHIPS: { mode: Mode; label: string; count: (d: Shell["app"]["deck"]) => number }[] = [
  { mode: "all", label: "All", count: (d) => d.activeCount },
  { mode: "level0", label: "To verify", count: (d) => d.levelCount(0) },
  { mode: "level1", label: "Learning", count: (d) => d.levelCount(1) },
  { mode: "level2", label: "Almost there", count: (d) => d.levelCount(2) },
  { mode: "level3", label: "Known", count: (d) => d.levelCount(3) },
  { mode: "new", label: "New", count: (d) => d.newCount },
  { mode: "level4", label: "Archived", count: (d) => d.levelCount(ARCHIVED) },
];

const fontClass = (t: string) => (t.length <= 24 ? "f-l" : t.length <= 45 ? "f-m" : "f-s");

export function studyScreen(shell: Shell): HTMLElement {
  const { app } = shell;
  const deck = app.deck;
  const root = h("section", { class: "screen study" });
  let revealed = false;
  let finished = false;
  let label = ""; // shown for quick sets and searches
  let dismissedNudge = false;

  const resetCard = () => { revealed = false; };

  function setMode(mode: Mode) { deck.setMode(mode); finished = false; label = ""; resetCard(); render(); }

  function finish() {
    finished = true;
    const known = deck.sessionKnown, unknown = deck.sessionUnknown, total = known + unknown;
    app.recordSession(total, known, unknown);
    const pct = total ? Math.round((known / total) * 100) : 0;
    const body = h("div", { class: "sheet-body" },
      h("h2", null, "Session complete!"),
      h("ul", { class: "plain" }, LEVELS.map((l) => h("li", null, `${l.icon} ${l.name}: ${[...deck.results.values()].filter((r) => r === l.level).length}`))),
      h("p", { class: "big-note" }, `Known: ${pct}%`),
      h("div", { class: "btn-row" },
        h("button", { class: "btn", onclick: () => { close(); restart(); } }, "Go again"),
        h("button", { class: "btn primary", onclick: () => close() }, "Done")));
    const close = shell.sheet(body);
    render();
  }

  function answer(level: number) {
    if (!deck.total || finished) return;
    if (level === ARCHIVED && deck.current.level !== TOP_LEVEL) return;
    deck.mark(level);
    if (deck.isLast) { render(); finish(); return; }
    deck.next(); resetCard(); render();
  }

  function go(delta: number) {
    if (delta > 0 && !deck.isLast) deck.next();
    else if (delta < 0 && deck.index > 0) deck.previous();
    else return;
    resetCard(); render();
  }

  function restart(doShuffle = false) { deck.restart(doShuffle); finished = false; resetCard(); render(); }

  function quickSheet() {
    const options: [string, Set<number | null> | null, number][] = [
      ...LEVELS.map((l): [string, Set<number | null> | null, number] => [`${l.icon}  ${l.name}`, new Set([l.level]), deck.levelCount(l.level)]),
      ["●  New", new Set([null]), deck.newCount],
      ["All cards", null, deck.activeCount],
    ];
    const close = shell.sheet(h("div", { class: "sheet-body" }, h("h2", null, "Quick set"), h("p", { class: "muted" }, "10 random cards from…"),
      h("div", { class: "list" }, options.map(([name, levels, n]) =>
        h("button", { class: "list-btn", onclick: () => {
          if (!deck.pool(levels).length) { shell.toast("There are no cards in that level yet."); return; }
          close(); deck.quickSet(levels); finished = false; label = "Quick set"; resetCard(); render();
        } }, h("span", null, name), h("span", { class: "count" }, String(n)))))));
  }

  // --- swipe + tap on the card --------------------------------------------------
  function attachGestures(card: HTMLElement) {
    let sx = 0, sy = 0, active = false;
    card.addEventListener("pointerdown", (e) => { active = true; sx = e.clientX; sy = e.clientY; });
    card.addEventListener("pointercancel", () => { active = false; });
    card.addEventListener("pointerup", (e) => {
      if (!active) return; active = false;
      const dx = e.clientX - sx, dy = e.clientY - sy;
      if (Math.abs(dx) > 55 && Math.abs(dx) > Math.abs(dy) * 1.4) { go(dx < 0 ? 1 : -1); return; }
      if (Math.abs(dx) < 10 && Math.abs(dy) < 10) flip();
    });
    card.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); flip(); } });
  }

  function flip() {
    if (!deck.total || finished) return;
    revealed = !revealed;
    render();
  }

  function render() {
    const scrollTop = root.querySelector(".card-area")?.scrollTop ?? 0;
    clear(root);
    const eng = app.settings.englishFirst;

    // header: counter + progress
    const total = deck.total;
    root.append(h("header", { class: "top" },
      h("div", { class: "top-row" }, h("h1", null, label || "Study"), h("span", { class: "counter" }, total ? `${deck.currentNumber} / ${total}` : "0 / 0")),
      h("div", { class: "bar", role: "progressbar", "aria-valuemin": "0", "aria-valuemax": String(total), "aria-valuenow": String(deck.currentNumber) }, h("div", { style: { width: total ? `${(deck.currentNumber / total) * 100}%` : "0%" } }))));

    if (app.needsBackup && !dismissedNudge) {
      root.append(h("div", { class: "nudge" }, h("span", null, "Back up your progress"),
        h("button", { class: "btn small", onclick: () => shell.go("more") }, "Open More"),
        h("button", { class: "btn small ghost", "aria-label": "Dismiss", onclick: () => { dismissedNudge = true; render(); } }, "✕")));
    }

    // chips (counters that act as filters)
    const chips = h("div", { class: "chips", role: "tablist" });
    const list = [...CHIPS];
    const failedCount = deck.words.filter((w) => w.fails > 0 && w.level !== ARCHIVED).length;
    if (failedCount) list.push({ mode: "failed", label: "Failed", count: () => failedCount });
    for (const c of list) {
      const on = deck.mode === c.mode && !label;
      chips.append(h("button", { class: "chip" + (on ? " on" : ""), "aria-pressed": String(on), onclick: () => setMode(c.mode) }, c.label, h("b", null, String(c.count(deck)))));
    }
    root.append(chips);

    // tools
    root.append(h("div", { class: "tools" },
      h("button", { class: "tool", onclick: () => { deck.shuffle(); finished = false; resetCard(); render(); } }, "⤮ Shuffle"),
      h("button", { class: "tool", onclick: () => restart() }, "↺ Restart"),
      h("button", { class: "tool", onclick: quickSheet }, "⚡ Quick 10"),
      h("button", { class: "tool", "aria-pressed": String(eng), onclick: () => { app.settings.englishFirst = !eng; app.saveSettings(); resetCard(); render(); } }, eng ? "EN → PL" : "PL → EN")));

    // card
    const area = h("div", { class: "card-area" });
    if (!total) {
      area.append(h("div", { class: "empty" }, h("p", null, deck.mode === "search" ? "No cards match." : "No cards here yet."), h("button", { class: "btn primary", onclick: () => setMode("all") }, "Show all cards")));
    } else {
      const w = deck.current;
      const front = eng ? w.translation : w.word;
      const back = eng ? w.word : w.translation;
      const card = h("div", { class: "card" + (revealed ? " revealed" : ""), role: "button", tabindex: "0", "aria-label": revealed ? "Card, tap to hide the answer" : "Card, tap to reveal the answer" },
        h("div", { class: "card-meta" }, h("span", { class: `pill lv-${w.level ?? "n"}` }, `${levelIcon(w.level)} ${levelName(w.level)}`), w.fails > 0 && h("span", { class: "fails" }, `failed ${w.fails}×`)),
        h("div", { class: `front ${fontClass(front)}` }, front),
        revealed ? h("div", { class: `back ${fontClass(back)}` }, back) : h("div", { class: "tap-hint" }, "Tap to flip"),
        revealed && w.sentence && h("p", { class: "sentence" }, w.sentence),
        revealed && w.sentence_translation && h("p", { class: "sentence-tr" }, w.sentence_translation));
      attachGestures(card);
      area.append(card);
      if (revealed) { const ex = extras(app, w.word); if (ex) area.append(ex); }
    }
    root.append(area);
    area.scrollTop = scrollTop && revealed ? scrollTop : 0;

    // thumb-zone controls
    const canAnswer = !!total && !finished;
    const cur = total ? deck.current : null;
    const levelRow = h("div", { class: "levels" }, LEVELS.map((l) =>
      h("button", { class: `lvl lv-${l.level}` + (cur?.level === l.level ? " current" : ""), disabled: !canAnswer, onclick: () => answer(l.level) }, h("span", { class: "lvl-ico" }, l.icon), h("span", { class: "lvl-name" }, l.name))));
    const canArchive = canAnswer && cur?.level === TOP_LEVEL; // only Known cards can be archived
    const nav = h("div", { class: "nav" },
      h("button", { class: "nav-btn", "aria-label": "Previous card", disabled: deck.index === 0 || !total, onclick: () => go(-1) }, "‹"),
      canArchive && h("button", { class: "btn small archive", onclick: () => answer(ARCHIVED) }, "▣ Archive"),
      h("button", { class: "nav-btn", "aria-label": "Next card", disabled: deck.isLast || !total, onclick: () => go(1) }, "›"));
    root.append(h("footer", { class: "controls" }, levelRow, nav));
  }

  /** Called by other screens (search, failed words ...) that already prepared the deck. */
  (root as any).refresh = (newLabel = "") => { label = newLabel; finished = false; resetCard(); render(); };
  (root as any).render = render;
  render();
  return root;
}
