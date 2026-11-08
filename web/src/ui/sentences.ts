// Sentence practice: tap to reveal the translation and the cards that were used (port of sentences.py).
import { h, clear } from "./h";
import { levelName } from "../core/deck";
import { pickSentences } from "../core/sentences";
import type { SentenceItem } from "../core/tables";
import type { Shell } from "./shell";
import { seg, type ReviewHost, type ReviewMode } from "./shell";

export function sentencesScreen(shell: Shell, host: ReviewHost): HTMLElement {
  const { app } = shell;
  const root = h("section", { class: "screen" });
  let count = 10;

  function setup() {
    shell.fullscreen(false);
    clear(root);
    let english = app.settings.englishFirst;
    const countIn = h("input", { class: "num", type: "number", inputMode: "numeric", min: "1", max: "9999", value: String(count), "aria-label": "Number of sentences" }) as HTMLInputElement;
    countIn.addEventListener("input", () => { count = Math.max(1, parseInt(countIn.value, 10) || 10); });
    root.append(h("div", { class: "scroll-body stack" },
      h("header", { class: "top" }, h("h1", null, "Review")),
      seg<ReviewMode>([["typed", "Type"], ["cloze", "Blank"], ["sentences", "Sentences"]], "sentences", (v) => { if (v !== "sentences") host.setMode(v); }),
      h("p", { class: "muted" }, `Practise with new sentences built from your words: mostly Almost there, plus Learning and To verify. ${app.sentences.length} sentences available.`),
      h("div", { class: "group" }, h("div", { class: "row" }, h("span", { class: "row-text" }, h("span", { class: "row-title" }, "Number of sentences")), countIn)),
      seg<"en" | "pl">([["en", "English → Polish"], ["pl", "Polish → English"]], english ? "en" : "pl", (v) => { english = v === "en"; }),
      h("button", { class: "btn primary wide sticky", disabled: !app.sentences.length, onclick: () => {
        const items = pickSentences(app.deck, app.sentences, count);
        if (items.length) run(items, english); else shell.toast("No sentences available.");
      } }, "Start")));
  }

  function run(items: SentenceItem[], english: boolean) {
    shell.fullscreen(true);
    let pos = 0, revealed = false;
    const byWord = new Map(app.deck.words.map((w) => [w.word, w]));

    function render() {
      clear(root);
      const it = items[pos];
      const [prompt, answer] = english ? [it.en, it.pl] : [it.pl, it.en];
      const last = pos === items.length - 1;
      const used = (it.words ?? []).map((t) => byWord.get(t)).filter((c) => !!c);
      const reveal = () => { revealed = true; render(); };
      const advance = () => { if (!revealed) { reveal(); return; } if (last) { setup(); return; } pos++; revealed = false; render(); };
      const card = h("div", { class: "qcard", style: { alignItems: "stretch", textAlign: "left", cursor: revealed ? "default" : "pointer" } },
        h("span", { class: "pill" }, english ? "English" : "Polish"),
        h("p", { class: "sentence-big" }, prompt),
        revealed ? h("div", { class: "revealed-block", style: { boxShadow: "none", padding: "12px 0 0", borderTop: "1px solid var(--line)", borderRadius: 0 } },
          h("p", { class: "sentence-big", style: { color: "var(--accent)" } }, answer),
          used.length ? h("div", { class: "muted" }, used.map((c) => h("p", null, h("b", null, c!.word), ` – ${c!.translation} `, h("i", null, `(${levelName(c!.level)})`)))) : null)
          : h("p", { class: "tap-hint", style: { textAlign: "center" } }, "Tap to reveal"));
      if (!revealed) card.addEventListener("click", reveal);
      root.append(
        h("header", { class: "top" },
          h("div", { class: "top-row" }, h("button", { class: "btn small", onclick: setup }, "✕ Exit"), h("span", { class: "counter" }, `${pos + 1} of ${items.length}`)),
          h("div", { class: "bar" }, h("div", { style: { width: `${((pos + 1) / items.length) * 100}%` } }))),
        h("div", { class: "run" }, h("div", { class: "run-body" }, card),
          h("div", { class: "answerbar" }, h("div", { class: "actions" },
            h("button", { class: "btn", disabled: pos === 0, onclick: () => { pos--; revealed = false; render(); } }, "‹ Previous"),
            h("button", { class: "btn primary", style: { flex: "2" }, onclick: advance }, !revealed ? "Reveal" : last ? "Finish" : "Next  →")))));
    }
    render();
  }

  setup();
  (root as any).reset = setup;
  return root;
}
