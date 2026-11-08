// Search by word, translation or sentence (case and Polish accents ignored; archived included).
import { h, clear } from "./h";
import { FlashcardDeck, levelIcon, levelName } from "../core/deck";
import type { Shell } from "./shell";

const MAX_SHOWN = 100;

export function searchScreen(shell: Shell): HTMLElement {
  const { app } = shell;
  const root = h("section", { class: "screen" });
  const input = h("input", { class: "text-in", type: "search", placeholder: "Search words, meanings, sentences…", autocapitalize: "off", autocomplete: "off", autocorrect: "off", spellcheck: false, enterKeyHint: "search", "aria-label": "Search" }) as HTMLInputElement;
  const results = h("div", { class: "scroll-body" });
  let q = "";

  function renderResults() {
    clear(results);
    if (!q.trim()) { results.append(h("p", { class: "muted", style: { padding: "16px 0" } }, "Type part of a word, its meaning or a sentence. Accents and capitals don't matter.")); return; }
    const tmp = new FlashcardDeck(app.deck.words);
    const n = tmp.search(q);
    if (!n) { results.append(h("p", { class: "muted", style: { padding: "16px 0" } }, "No cards match.")); return; }
    const open = (position: number) => shell.studyView(() => { app.deck.search(q); app.deck.index = position; }, `Search: “${q.trim()}”`);
    const list = h("div", { class: "hits", style: { padding: "0" } });
    tmp.order.slice(0, MAX_SHOWN).forEach((id, pos) => {
      const w = app.deck.words[id];
      list.append(h("button", { class: "hit", onclick: () => open(pos) },
        h("span", null, h("b", null, w.word), h("span", { class: "tr" }, w.translation)),
        h("span", { class: `pill lv-${w.level ?? "n"}` }, `${levelIcon(w.level)} ${levelName(w.level)}`)));
    });
    results.append(
      h("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", margin: "8px 0" } },
        h("span", { class: "muted" }, `${n} card${n === 1 ? "" : "s"}${n > MAX_SHOWN ? ` (showing ${MAX_SHOWN})` : ""}`),
        h("button", { class: "btn small primary", onclick: () => open(0) }, "Study these")),
      list);
  }

  let timer = 0;
  input.addEventListener("input", () => { q = input.value; clearTimeout(timer); timer = window.setTimeout(renderResults, 120); });
  input.addEventListener("keydown", (e) => { if (e.key === "Enter") input.blur(); });
  root.append(h("header", { class: "top" }, h("h1", null, "Search"), h("div", { style: { marginTop: "10px" } }, input)), results);
  renderResults();
  (root as any).render = renderResults;
  return root;
}
