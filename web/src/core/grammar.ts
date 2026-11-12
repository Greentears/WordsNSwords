// Grammar quiz: fill in the blank with the right ending, case or tense (Polish and French). Port of desktop/grammar.py.
import { FR_ADJ_LABELS, FR_TENSES, FR_TENSE_LABELS, expandOptional } from "./tables";
import type { Adjective, FrAdjective, FrNoun, FrVerb, Noun, Verb } from "./tables";

export const CATEGORIES = ["verbs", "nouns", "adjectives"] as const;
export type Category = (typeof CATEGORIES)[number];
export const CATEGORY_NAMES: Record<Category, string> = { verbs: "Verbs", nouns: "Nouns", adjectives: "Adjectives" };

const PL_PRONOUNS = ["ja", "ty", "on / ona / ono", "my", "wy", "oni / one"];
const PL_PAST = ["on", "ona", "ono", "oni", "one"];
const PL_IMPERATIVE = ["ty", "my", "wy"];
const PL_CASES: [string, string][] = [["nominative", "kto? co?"], ["genitive", "kogo? czego?"], ["dative", "komu? czemu?"],
  ["accusative", "kogo? co?"], ["instrumental", "z kim? z czym?"], ["locative", "o kim? o czym?"], ["vocative", "o!"]];
const PL_ADJ: ["m" | "f" | "n" | "pl", string][] = [["m", "masculine"], ["f", "feminine"], ["n", "neuter"], ["pl", "plural"]];
const FR_SUBJECT = /^(?:j'|je |tu |il\/elle |ils\/elles |nous |vous )/i;
const FR_ARTICLE = /^(?:l'|la |le |les |un |une |des )/i;

export interface Question {
  category: Category;
  card: string;
  stem: string;      // what is shown, with the blank: "ja ___"
  label: string;     // what is asked: "denerwować się · present"
  hint: string;
  answers: string[]; // every accepted answer (the first one is shown when you are wrong)
}
export type Pool = Record<Category, Question[]>;

export const norm = (text: string): string =>
  text.normalize("NFC").toLowerCase().replace(/[’‘]/g, "'").replace(/\s+/g, " ").trim();

/** norm() without accents (ł counts as l). */
export const fold = (text: string): string => norm(text).replace(/ł/g, "l").normalize("NFKD").replace(/[̀-ͯ]/g, "");

function variants(answer: string): string[] {
  const out = [answer];
  if (/(?:^|\s)się(?:\s|$)/.test(answer)) {       // the reflexive "się" may be left out
    const short = answer.replace(/(?:^|\s)się(?=\s|$)/g, " ").replace(/\s+/g, " ").trim();
    if (short) out.push(short);
  }
  return out;
}
const slashes = (form: string | null | undefined): string[] => (form ? form.split(" / ").map((p) => p.trim()) : []);
function answersOf(forms: string[]): string[] {
  const seen: string[] = [];
  for (const f of forms) for (const v of variants(f)) if (v && !seen.includes(v)) seen.push(v);
  return seen;
}
const q = (category: Category, card: string, stem: string, label: string, hint: string, answers: string[]): Question =>
  ({ category, card, stem, label, hint, answers });

function plVerbs(verbs: Record<string, Verb[]>): Question[] {
  const out: Question[] = [];
  for (const [card, entries] of Object.entries(verbs)) for (const v of entries) {
    const inf = v.infinitive ?? card;
    const tense = v.aspect === "perfective" ? "future" : "present";
    const add = (pronouns: string[], forms: (string | null)[] | undefined, what: string) =>
      pronouns.forEach((p, i) => { const f = forms?.[i]; if (f) out.push(q("verbs", card, `${p} ___`, `${inf} · ${what}`, "", answersOf([f]))); });
    add(PL_PRONOUNS, v.forms, tense);
    add(PL_PAST, v.past, "past tense");
    add(PL_IMPERATIVE, v.imperative, "imperative");
  }
  return out;
}

function plNouns(nouns: Record<string, Noun[]>): Question[] {
  const out: Question[] = [];
  for (const [card, entries] of Object.entries(nouns)) for (const n of entries) {
    const lemma = n.lemma ?? card;
    for (const number of ["singular", "plural"] as const) (n[number] ?? []).forEach((form, i) => {
      if (!form || (number === "singular" && i === 0)) return;
      const [name, ask] = PL_CASES[i];
      out.push(q("nouns", card, `${lemma} → ___`, `${name} ${number}`, ask, answersOf(slashes(form))));
    });
  }
  return out;
}

function plAdjectives(adjs: Record<string, Adjective[]>): Question[] {
  const out: Question[] = [];
  for (const [card, entries] of Object.entries(adjs)) for (const a of entries) {
    const lemma = a.lemma ?? card;
    for (const [key, name] of PL_ADJ) (a.forms[key] ?? []).forEach((form, i) => {
      if (!form || i === 6 || (key === "m" && i === 0)) return;
      const [cname, ask] = PL_CASES[i];
      out.push(q("adjectives", card, `${lemma} → ___`, `${name} ${cname}`, ask, answersOf(slashes(form))));
    });
  }
  return out;
}

function frVerbs(verbs: Record<string, FrVerb[]>): Question[] {
  const out: Question[] = [];
  for (const [card, entries] of Object.entries(verbs)) for (const v of entries) {
    const inf = v.infinitive ?? card;
    for (const tense of FR_TENSES) {
      const forms = v.tenses[tense];
      if (!(Array.isArray(forms) && forms.length === 6)) continue;
      for (const form of forms) {
        const m = FR_SUBJECT.exec(form);
        const subject = m ? m[0] : "";
        const answers = expandOptional(form.slice(subject.length)).filter(Boolean);
        if (answers.length) out.push(q("verbs", card, `${subject}___`, `${inf} · ${FR_TENSE_LABELS[tense]}`, "", answers));
      }
    }
  }
  return out;
}

function frNouns(nouns: Record<string, FrNoun[]>): Question[] {
  const out: Question[] = [];
  for (const [card, entries] of Object.entries(nouns)) for (const n of entries) {
    const { singular: sing, plural: plur } = n;
    if (sing && plur && sing !== plur) {
      const prefix = FR_ARTICLE.exec(plur)?.[0] ?? "";
      out.push(q("nouns", card, `${sing} → ${prefix}___`, "plural", "", [...new Set([plur.slice(prefix.length), plur].filter(Boolean))]));
    }
  }
  return out;
}

function frAdjectives(adjs: Record<string, FrAdjective[]>): Question[] {
  const out: Question[] = [];
  for (const [card, entries] of Object.entries(adjs)) for (const a of entries) {
    for (const [key, name] of FR_ADJ_LABELS) if (key !== "ms" && a.forms[key]) out.push(q("adjectives", card, `${a.forms.ms} → ___`, name, "", [a.forms[key]]));
  }
  return out;
}

export interface Tables {
  conj: Record<string, Verb[]>; decl: Record<string, Noun[]>; adj: Record<string, Adjective[]>;
  frConj: Record<string, FrVerb[]>; frDecl: Record<string, FrNoun[]>; frAdj: Record<string, FrAdjective[]>;
}

/** Every question the tables can make, by category. `language` is "pl" or "fr". */
export function buildPool(language: string, t: Tables): Pool {
  return language === "fr"
    ? { verbs: frVerbs(t.frConj), nouns: frNouns(t.frDecl), adjectives: frAdjectives(t.frAdj) }
    : { verbs: plVerbs(t.conj), nouns: plNouns(t.decl), adjectives: plAdjectives(t.adj) };
}

/** `count` different questions: a category is drawn first, so a big table can't drown the others. */
export function pick(pool: Pool, categories: readonly Category[], count: number, random: () => number = Math.random): Question[] {
  const left = new Map<Category, Question[]>();
  for (const c of categories) if (pool[c]?.length) left.set(c, [...pool[c]]);
  const out: Question[] = [];
  while (left.size && out.length < count) {
    const cats = [...left.keys()].sort();
    const cat = cats[Math.floor(random() * cats.length)];
    const list = left.get(cat)!;
    out.push(list.splice(Math.floor(random() * list.length), 1)[0]);
    if (!list.length) left.delete(cat);
  }
  return out;
}

export type Verdict = "correct" | "accents" | "wrong";
export function check(question: Question, text: string, language = "pl"): Verdict {
  const given = [norm(text)];
  if (language === "fr") given.push(norm(given[0].replace(FR_SUBJECT, "")));
  const g = given.filter(Boolean);
  if (g.some((x) => question.answers.some((a) => x === norm(a)))) return "correct";
  if (g.some((x) => question.answers.some((a) => fold(x) === fold(a)))) return "accents";
  return "wrong";
}
