// Typed quiz and fill-in-the-blank quiz (port of quiz.py), laid out for a phone.
import { h, clear } from "./h";
import { LEVELS, levelIcon } from "../core/deck";
import { QuizSession, clozeAllowed, quizCardIds, type Feedback } from "../core/quiz";
import { BLANK } from "../core/cloze";
import { MIX_WEIGHTS } from "../core/deck";
import type { Shell } from "./shell";
import { seg, toggleRow, type ReviewHost, type ReviewMode } from "./shell";

export const ACCENT_LETTERS = ["ą", "ć", "ę", "ł", "ń", "ó", "ś", "ź", "ż"];

/** Row of Polish letters above the keyboard; keeps the keyboard open and inserts at the caret. */
export function accentRow(input: HTMLInputElement): HTMLElement {
  const row = h("div", { class: "accents", role: "group", "aria-label": "Polish letters" });
  for (const ch of ACCENT_LETTERS) {
    const b = h("button", { type: "button", tabindex: "-1", "aria-label": ch }, ch);
    b.addEventListener("pointerdown", (e) => e.preventDefault()); // don't steal focus from the input
    b.addEventListener("mousedown", (e) => e.preventDefault());
    b.addEventListener("click", () => {
      const s = input.selectionStart ?? input.value.length, e = input.selectionEnd ?? s;
      input.value = input.value.slice(0, s) + ch + input.value.slice(e);
      input.setSelectionRange(s + 1, s + 1);
      input.focus();
    });
    row.append(b);
  }
  return row;
}

export function answerInput(placeholder: string): HTMLInputElement {
  return h("input", {
    class: "text-in", type: "text", autocapitalize: "off", autocomplete: "off", autocorrect: "off", spellcheck: false,
    enterKeyHint: "done", placeholder, lang: "pl", "aria-label": "Your answer",
  }) as HTMLInputElement;
}

type Kind = "typed" | "cloze";

export function quizScreen(shell: Shell, host: ReviewHost): HTMLElement {
  const { app } = shell;
  const deck = app.deck;
  const root = h("section", { class: "screen" });
  const opts = { kind: "typed" as Kind, mix: false, levels: new Set<number | null>([0, 1, 2]), count: 10, all: false, english: true, accents: true };

  const examples = () => (app.settings.showExamples ? app.examples : {});
  const allowedSet = () => (opts.kind === "cloze" ? clozeAllowed(deck, app.forms, examples()) : null);

  // ---------------------------------------------------------------- setup
  function setup() {
    shell.fullscreen(false);
    clear(root);
    const allowed = allowedSet();
    const body = h("div", { class: "scroll-body stack" });
    const avail = h("p", { class: "muted" });
    const startBtn = h("button", { class: "btn primary wide sticky", onclick: start }, "Start quiz");

    const refresh = () => {
      const n = opts.mix
        ? [...MIX_WEIGHTS].reduce((s, [k]) => s + deck.pool(new Set([k]), allowed).length, 0)
        : deck.pool(opts.levels, allowed).length;
      avail.textContent = opts.mix ? `Mixed from ${n} cards` : `${n} cards available with this selection`;
      (startBtn as HTMLButtonElement).disabled = n === 0;
    };

    body.append(
      h("header", { class: "top" }, h("h1", null, "Review")),
      seg<ReviewMode>([["typed", "Type"], ["cloze", "Blank"], ["sentences", "Sentences"]], opts.kind, (v) => { if (v === "sentences") host.setMode(v); else { opts.kind = v; setup(); } }),
    );
    if (opts.kind === "cloze") body.append(h("p", { class: "muted" }, "A Polish sentence with one word missing. The meaning is shown next to the blank; type the word in the right form."));

    const levelsBox = h("div", { class: "group" });
    const mixRow = toggleRow("Smart mix", "A bit of everything, mostly “Almost there” (45 / 35 / 20%). Known and New are left out.", opts.mix, (v) => {
      opts.mix = v; levelsBox.style.opacity = v ? ".45" : "1"; levelsBox.querySelectorAll("input").forEach((i) => ((i as HTMLInputElement).disabled = v));
      allBox.disabled = v; refresh();
    });
    body.append(h("div", { class: "group" }, mixRow));

    const levelRows: [number | null, string][] = [...LEVELS.map((l): [number | null, string] => [l.level, `${l.icon}  ${l.name}`]), [null, "●  New"]];
    for (const [lv, name] of levelRows) {
      const n = deck.pool(new Set([lv]), allowed).length;
      const box = h("input", { type: "checkbox", checked: opts.levels.has(lv), disabled: opts.mix }) as HTMLInputElement;
      box.addEventListener("change", () => { box.checked ? opts.levels.add(lv) : opts.levels.delete(lv); refresh(); });
      levelsBox.append(h("label", { class: "row check-row" }, h("span", { class: "row-text" }, h("span", { class: "row-title" }, name)), h("span", { class: "val" }, String(n)), box));
    }
    if (opts.mix) levelsBox.style.opacity = ".45";
    body.append(levelsBox, avail);

    const countIn = h("input", { class: "num", type: "number", inputMode: "numeric", min: "1", max: "9999", value: String(opts.count), "aria-label": "Number of cards" }) as HTMLInputElement;
    countIn.addEventListener("input", () => { opts.count = Math.max(1, parseInt(countIn.value, 10) || 10); });
    const allBox = h("input", { type: "checkbox", checked: opts.all, "aria-label": "All of them" }) as HTMLInputElement;
    allBox.addEventListener("change", () => { opts.all = allBox.checked; countIn.disabled = opts.all; });
    countIn.disabled = opts.all;
    body.append(h("div", { class: "group" },
      h("div", { class: "row" }, h("span", { class: "row-text" }, h("span", { class: "row-title" }, "Number of cards")), countIn),
      h("label", { class: "row check-row" }, h("span", { class: "row-text" }, h("span", { class: "row-title" }, "All of them")), allBox)));

    if (opts.kind === "typed") {
      body.append(seg<"en" | "pl">([["en", "English → Polish"], ["pl", "Polish → English"]], opts.english ? "en" : "pl", (v) => { opts.english = v === "en"; }));
    }
    body.append(h("div", { class: "group" }, toggleRow("Accept answers without Polish accents", "ą ę ł … are optional", opts.accents, (v) => { opts.accents = v; })));
    body.append(startBtn);
    root.append(body);
    refresh();
  }

  function start() {
    const ids = quizCardIds(deck, { mix: opts.mix, levels: opts.levels, count: opts.count, all: opts.all, allowed: allowedSet() });
    if (!ids.length) { shell.toast("No cards match this selection."); return; }
    const cloze = opts.kind === "cloze" ? { forms: app.forms, examples: examples() } : undefined;
    run(new QuizSession(deck, ids, cloze ? true : opts.english, opts.accents, cloze));
  }

  // ---------------------------------------------------------------- running
  function run(session: QuizSession) {
    shell.fullscreen(true);
    clear(root);
    const cloze = !!session.cloze;
    const input = answerInput(cloze ? "Type the missing word…" : session.englishPrompt ? "Type the Polish word…" : "Type the English word…");
    const bar = h("div", { style: { width: "0%" } });
    const counter = h("span", { class: "counter" });
    const body = h("div", { class: "run-body" });
    const answerbar = h("div", { class: "answerbar" });

    const leave = async () => {
      if (session.position > 0 || session.answered) {
        if (!(await shell.confirm("Leave the quiz?", "Answers you already gave stay saved.", "Leave"))) return;
      }
      setup();
    };
    root.append(
      h("header", { class: "top" },
        h("div", { class: "top-row" }, h("button", { class: "btn small", onclick: leave }, "✕ Exit"), counter),
        h("div", { class: "bar" }, bar)),
      h("div", { class: "run" }, body, answerbar));

    function showCard() {
      const w = session.word;
      counter.textContent = `${session.position + 1} of ${session.total}`;
      bar.style.width = `${(session.position / session.total) * 100}%`;
      const text = session.promptText();
      const size = text.length <= 24 ? "f-l" : text.length <= 45 ? "f-m" : "f-s";
      const prompt = h("div", { class: `prompt ${cloze ? "cloze" : size}` }, text);
      body.replaceChildren(
        h("div", { class: "qcard" }, prompt, h("span", { class: `pill lv-${w.level ?? "n"}` }, `${levelIcon(w.level)} ${session.pill()}`), h("p", { class: "hinttext", id: "hint" })));
      input.value = ""; input.readOnly = false;
      const hintBtn = h("button", { class: "btn", onclick: () => { document.getElementById("hint")!.textContent = session.hint(); (hintBtn as HTMLButtonElement).disabled = true; } }, "💡 Hint");
      answerbar.replaceChildren(
        input, accentRow(input),
        h("div", { class: "actions" },
          h("button", { class: "btn", onclick: () => reveal(session.dontKnow()) }, "I don't know"),
          cloze && hintBtn,
          h("button", { class: "btn primary", onclick: () => reveal(session.submit(input.value)) }, "Submit")));
      input.focus({ preventScroll: true });
    }

    function reveal(fb: Feedback | null) {
      if (!fb) return;
      const lines = fb.ok ? ["✓  Correct!", ...(fb.exact ? [] : [`Spelling: ${fb.expected}`])] : [`✕  Correct answer: ${fb.expected}`, `(failed ${fb.fails}× so far)`];
      const card = body.querySelector(".qcard")!;
      card.querySelector("#hint")?.remove();
      if (cloze) card.querySelector(".prompt")!.textContent = session.promptText().replace(`${BLANK} (${session.word.translation})`, `${fb.expected} (${session.word.translation})`);
      card.append(
        h("p", { class: `feedback ${fb.ok ? "ok" : "bad"}` }, lines.join("\n")),
        fb.sentence[0] && h("p", { class: "ans-sentence" }, fb.sentence[0]),
        fb.sentence[1] && h("p", { class: "ans-sentence-tr" }, fb.sentence[1]));
      input.readOnly = true; input.blur();
      bar.style.width = `${((session.position + 1) / session.total) * 100}%`;
      const nextBtn = h("button", { class: "btn primary wide", onclick: next }, session.isLast ? "Finish" : "Next  →");
      answerbar.replaceChildren(nextBtn);
      (nextBtn as HTMLElement).focus({ preventScroll: true });
    }

    function next() {
      if (session.next()) { finish(); return; }
      showCard();
    }

    input.onkeydown = (e) => {
      if (e.key !== "Enter") return;
      e.preventDefault();
      reveal(session.submit(input.value)); // empty answer counts as "I don't know"
    };

    function finish() {
      shell.fullscreen(false);
      const failed = session.failedWords;
      clear(root);
      root.append(h("div", { class: "scroll-body stack" },
        h("header", { class: "top" }, h("h1", null, "Quiz finished")),
        h("p", { class: "big-note" }, `Score: ${session.score} / ${session.results.length}`),
        failed.length ? h("div", null, h("p", { class: "section-title" }, "To practise more"),
          h("div", { class: "results-list" }, failed.map((w) => h("div", { class: "result-item" }, h("span", null, h("b", null, w.word), h("small", null, w.translation)), h("span", { class: "muted" }, `${w.fails}×`))))) : h("p", { class: "muted", style: { textAlign: "center" } }, "No mistakes. 🎉"),
        h("div", { class: "btn-row" }, h("button", { class: "btn", onclick: start }, "Again"), h("button", { class: "btn primary", onclick: setup }, "Done"))));
    }

    showCard();
  }

  setup();
  (root as any).reset = setup;
  (root as any).setKind = (k: Kind) => { opts.kind = k; setup(); };
  return root;
}
