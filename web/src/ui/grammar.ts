// Grammar quiz (Review tab): fill in the blank with the right ending, case or tense. Port of desktop/grammar_ui.py.
import { h, clear } from "./h";
import { CATEGORIES, CATEGORY_NAMES, buildPool, check, pick, type Category, type Question } from "../core/grammar";
import { languageInfo } from "../state";
import { accentRow, answerInput } from "./quiz";
import { REVIEW_TABS, seg, type ReviewHost, type ReviewMode, type Shell } from "./shell";

export function grammarScreen(shell: Shell, host: ReviewHost): HTMLElement {
  const { app } = shell;
  const root = h("section", { class: "screen" });
  const chosen = new Set<Category>(CATEGORIES);
  let count = 10;
  const code = () => languageInfo(app.deckId).code;
  const pool = () => buildPool(code(), app);

  function setup() {
    shell.fullscreen(false);
    clear(root);
    const p = pool();
    const available = CATEGORIES.filter((c) => p[c].length);
    for (const c of [...chosen]) if (!p[c].length) chosen.delete(c);
    const countIn = h("input", { class: "num", type: "number", inputMode: "numeric", min: "1", max: "999", value: String(count), "aria-label": "Number of questions" }) as HTMLInputElement;
    countIn.addEventListener("input", () => { count = Math.max(1, parseInt(countIn.value, 10) || 10); });
    const start = h("button", { class: "btn primary wide sticky", disabled: !available.length, onclick: () => {
      const questions = pick(p, [...chosen], count);
      if (questions.length) run(questions); else shell.toast("Tick at least one kind of question.");
    } }, "Start");
    root.append(h("div", { class: "scroll-body stack" },
      h("header", { class: "top" }, h("h1", null, "Review")),
      seg<ReviewMode>(REVIEW_TABS, "grammar", (v) => { if (v !== "grammar") host.setMode(v); }),
      h("p", { class: "muted" }, available.length
        ? "Fill in the blank with the right ending, case or tense. The questions are made from your own verb, noun and adjective tables."
        : "There are no grammar tables for this deck yet (verbs, nouns, adjectives)."),
      h("div", { class: "group" }, CATEGORIES.map((c) => {
        const box = h("input", { type: "checkbox", checked: chosen.has(c), disabled: !p[c].length, "aria-label": CATEGORY_NAMES[c],
          onchange: (e: Event) => { if ((e.target as HTMLInputElement).checked) chosen.add(c); else chosen.delete(c); } });
        return h("label", { class: "row" }, h("span", { class: "row-text" }, h("span", { class: "row-title" }, CATEGORY_NAMES[c]), h("span", { class: "row-hint" }, `${p[c].length} questions`)), box);
      })),
      h("div", { class: "group" }, h("div", { class: "row" }, h("span", { class: "row-text" }, h("span", { class: "row-title" }, "Number of questions")), countIn)),
      start));
  }

  function run(questions: Question[]) {
    shell.fullscreen(true);
    let pos = 0, score = 0;
    const misses: Question[] = [];
    const input = answerInput("Type the missing form…", code());
    const bar = h("div", { style: { width: "0%" } });
    const counter = h("span", { class: "counter" });
    const body = h("div", { class: "run-body" });
    const answerbar = h("div", { class: "answerbar" });
    clear(root);
    const leave = async () => { if (pos > 0 && !(await shell.confirm("Leave the quiz?", "Your score so far will be lost.", "Leave"))) return; setup(); };
    root.append(
      h("header", { class: "top" }, h("div", { class: "top-row" }, h("button", { class: "btn small", onclick: leave }, "✕ Exit"), counter), h("div", { class: "bar" }, bar)),
      h("div", { class: "run" }, body, answerbar));

    function show() {
      const q = questions[pos];
      counter.textContent = `${pos + 1} of ${questions.length}`;
      bar.style.width = `${(pos / questions.length) * 100}%`;
      body.replaceChildren(h("div", { class: "qcard" },
        h("span", { class: "pill" }, q.label),
        q.hint ? h("p", { class: "hinttext" }, q.hint) : null,
        h("div", { class: "prompt f-m" }, q.stem)));
      input.value = ""; input.readOnly = false;
      answerbar.replaceChildren(input, accentRow(input, app.deckId),
        h("div", { class: "actions" }, h("button", { class: "btn primary wide", onclick: submit }, "Check")));
      input.focus({ preventScroll: true });
    }

    function submit() {
      const q = questions[pos];
      const verdict = check(q, input.value, code());
      let line: string;
      if (verdict === "wrong") { misses.push(q); line = `✕  ${q.answers[0]}` + (q.answers.length > 1 ? `\n(also: ${q.answers.slice(1).join(", ")})` : ""); }
      else { score++; line = verdict === "correct" ? "✓  Correct!" : `✓  Right, mind the accents: ${q.answers[0]}`; }
      body.querySelector(".qcard")!.append(h("p", { class: `feedback ${verdict === "wrong" ? "bad" : "ok"}` }, line));
      input.readOnly = true; input.blur();
      bar.style.width = `${((pos + 1) / questions.length) * 100}%`;
      const next = h("button", { class: "btn primary wide", onclick: () => { pos++; if (pos >= questions.length) finish(); else show(); } }, pos === questions.length - 1 ? "Finish" : "Next  →");
      answerbar.replaceChildren(next);
      (next as HTMLElement).focus({ preventScroll: true });
    }
    input.onkeydown = (e) => { if (e.key === "Enter") { e.preventDefault(); if (!input.readOnly) submit(); } };

    function finish() {
      shell.fullscreen(false);
      clear(root);
      root.append(h("div", { class: "scroll-body stack" },
        h("header", { class: "top" }, h("h1", null, "Quiz finished")),
        h("p", { class: "big-note" }, `Score: ${score} / ${questions.length}`),
        misses.length ? h("div", null, h("p", { class: "section-title" }, "To practise more"),
          h("div", { class: "results-list" }, misses.map((q) => h("div", { class: "result-item" }, h("span", null, h("b", null, q.stem.replace("___", q.answers[0])), h("small", null, q.label)))))) : h("p", { class: "muted", style: { textAlign: "center" } }, "No mistakes. 🎉"),
        h("div", { class: "btn-row" }, h("button", { class: "btn", onclick: () => run(pick(pool(), [...chosen], count)) }, "Again"), h("button", { class: "btn primary", onclick: setup }, "Done"))));
    }
    show();
  }

  setup();
  (root as any).reset = setup;
  return root;
}
