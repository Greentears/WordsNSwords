// Grammar tables and extra examples shown under a revealed card (collapsible, scrollable).
import { h } from "./h";
import type { App } from "../state";
import type { Adjective, Noun, Verb } from "../core/tables";

const CASES: [string, string][] = [
  ["Mianownik", "kto? co?"], ["Dopełniacz", "kogo? czego?"], ["Celownik", "komu? czemu?"], ["Biernik", "kogo? co?"],
  ["Narzędnik", "z kim? z czym?"], ["Miejscownik", "o kim? o czym?"], ["Wołacz", "o!"],
];
const GENDERS: Record<string, string> = { m: "masculine", f: "feminine", n: "neuter", pl: "plural only", num: "" };
const PRONOUNS = ["ja", "ty", "on / ona / ono", "my", "wy", "oni / one"];
const ASPECT: Record<string, string> = { imperfective: "present tense", perfective: "future tense (perfective verbs have no present)" };

const scroll = (t: HTMLElement) => h("div", { class: "scroll-x" }, t);
const cell = (v: string | null | undefined, bold = false) =>
  v ? h("td", null, bold ? h("b", null, v) : v) : h("td", { class: "muted" }, "–");
const caseCell = (i: number) => h("th", { scope: "row" }, CASES[i][0], " ", h("span", { class: "q" }, CASES[i][1]));

function details(title: string, sub: string, body: Node, open = false): HTMLElement {
  const d = h("details", { class: "fold" }, h("summary", null, h("span", { class: "fold-title" }, title), sub && h("span", { class: "fold-sub" }, sub)), body);
  d.open = open;
  return d;
}

function verbTable(v: Verb): HTMLElement {
  const rows = [0, 3].map((s) => h("tr", null, [0, 1, 2].map((k) => h("td", null, h("span", { class: "lbl" }, PRONOUNS[s + k]), h("b", null, String(v.forms[s + k]))))));
  const extra = (title: string, forms: string[] | undefined, labels: string[]) =>
    Array.isArray(forms) && forms.length === labels.length
      ? [h("div", { class: "cap" }, title), h("table", { class: "grid center" }, h("tr", null, forms.map((f, i) => h("td", null, h("span", { class: "lbl" }, labels[i]), String(f)))))]
      : [];
  return h("div", null,
    h("div", { class: "cap" }, [v.infinitive, ASPECT[v.aspect ?? ""]].filter(Boolean).join(" · ")),
    scroll(h("table", { class: "grid center" }, rows)),
    ...extra("past tense", v.past, ["on", "ona", "ono", "oni", "one"]),
    ...extra("imperative", v.imperative, ["ty", "my", "wy"]));
}

function nounTable(n: Noun): HTMLElement {
  const numeral = n.gender === "num";
  const g = GENDERS[n.gender ?? ""] ?? "";
  const caption = `${n.lemma ?? ""} · ${numeral ? "numeral" : "noun"}${g ? ", " + g : ""}`;
  const head = h("tr", null, h("th"), h("th", null, numeral ? "forms" : "singular"), !numeral && h("th", null, n.rare_plural ? "plural (rare)" : "plural"));
  const rows = CASES.map((_, i) => h("tr", null, caseCell(i), cell(n.singular[i], i === 0), !numeral && cell(n.plural[i], i === 0)));
  return h("div", null, h("div", { class: "cap" }, caption), scroll(h("table", { class: "grid" }, head, rows)));
}

function adjTable(a: Adjective): HTMLElement {
  const cols: ["m" | "f" | "n" | "pl", string][] = [["m", "masculine"], ["f", "feminine"], ["n", "neuter"], ["pl", "plural"]];
  const head = h("tr", null, h("th"), cols.map(([, l]) => h("th", null, l)));
  const rows = CASES.map((_, i) => h("tr", null, caseCell(i), cols.map(([k]) => cell(a.forms[k][i], i === 0))));
  return h("div", null, h("div", { class: "cap" }, `${a.lemma ?? ""} · adjective`), scroll(h("table", { class: "grid" }, head, rows)));
}

/** Everything that appears under a revealed card; null when there is nothing to show. */
export function extras(app: App, word: string): HTMLElement | null {
  const parts: HTMLElement[] = [];
  const s = app.settings;
  if (s.showGrammar) {
    const v = app.conj[word], n = app.decl[word], a = app.adj[word];
    if (v) parts.push(details("Verb forms", v.map((x) => x.infinitive).filter(Boolean).join(", "), h("div", null, v.map(verbTable))));
    if (n) parts.push(details(n.every((x) => x.gender === "num") ? "Numeral forms" : "Noun cases", n.map((x) => x.lemma).filter(Boolean).join(", "), h("div", null, n.map(nounTable))));
    if (a) parts.push(details("Adjective forms", a.map((x) => x.lemma).filter(Boolean).join(", "), h("div", null, a.map(adjTable))));
  }
  const ex = s.showExamples ? app.examples[word] : undefined;
  if (ex) {
    parts.push(details("More examples", `${ex.length}`, h("div", { class: "examples" }, ex.map(([pl, en]) => h("p", null, h("span", { class: "pl" }, pl), h("span", { class: "en" }, en)))), true));
  }
  return parts.length ? h("div", { class: "extras" }, parts) : null;
}
