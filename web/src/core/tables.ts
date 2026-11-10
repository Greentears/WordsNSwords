// Loaders for verbs / nouns / adjectives / examples / sentences JSON: ports of the Python loaders.
export interface Verb { infinitive?: string; aspect?: string; forms: string[]; past?: string[]; imperative?: string[] }
export interface Noun { lemma?: string; gender?: string; singular: (string | null)[]; plural: (string | null)[]; rare_plural?: boolean }
export interface Adjective { lemma?: string; forms: Record<"m" | "f" | "n" | "pl", (string | null)[]> }
export type Example = [string, string];
export interface SentenceItem { pl: string; en: string; words?: string[] }

const isObj = (v: unknown): v is Record<string, any> => v !== null && typeof v === "object" && !Array.isArray(v);
const isStr = (v: unknown): v is string => typeof v === "string";

function byCard<T>(data: unknown, key: string, ok: (v: any) => boolean): Record<string, T[]> {
  const result: Record<string, T[]> = {};
  for (const item of Array.isArray(data) ? data : []) {
    if (!isObj(item) || !isStr(item.card)) continue;
    const list = (Array.isArray(item[key]) ? item[key] : []).filter(ok);
    if (list.length) result[item.card] = list;
  }
  return result;
}

export const loadConjugations = (data: unknown) =>
  byCard<Verb>(data, "verbs", (v) => isObj(v) && Array.isArray(v.forms) && v.forms.length === 6);

export const loadDeclensions = (data: unknown) =>
  byCard<Noun>(data, "nouns", (n) => isObj(n) && Array.isArray(n.singular) && n.singular.length === 7 && Array.isArray(n.plural) && n.plural.length === 7);

export const loadAdjectives = (data: unknown) =>
  byCard<Adjective>(data, "adjectives", (a) =>
    isObj(a) && isObj(a.forms) && (["m", "f", "n", "pl"] as const).every((k) => Array.isArray(a.forms[k]) && a.forms[k].length === 7));

export function loadExamples(data: unknown): Record<string, Example[]> {
  const result: Record<string, Example[]> = {};
  if (!isObj(data)) return result;
  for (const [word, items] of Object.entries(data)) {
    if (!Array.isArray(items)) continue;
    const pairs: Example[] = items
      .filter((e) => isObj(e) && isStr(e.pl) && e.pl.trim())
      .map((e) => [e.pl, e.en ?? ""] as Example);
    if (pairs.length) result[word] = pairs;
  }
  return result;
}

export function loadSentences(data: unknown): SentenceItem[] {
  if (!Array.isArray(data)) throw new Error("sentences.json must be a list.");
  return data.filter((s) => isObj(s) && s.pl && s.en) as SentenceItem[];
}

/** Every inflected form per card word (port of ui._known_forms). */
export function knownForms(
  conj: Record<string, Verb[]>, decl: Record<string, Noun[]>, adj: Record<string, Adjective[]>,
): Record<string, string[]> {
  const forms: Record<string, string[]> = {};
  const add = (w: string, fs: (string | null | undefined)[]) => {
    (forms[w] ??= []).push(...(fs.filter(Boolean) as string[]));
  };
  for (const [w, verbs] of Object.entries(conj)) for (const v of verbs) add(w, [...v.forms, ...(v.past ?? []), ...(v.imperative ?? [])]);
  for (const [w, nouns] of Object.entries(decl)) for (const n of nouns) add(w, [...n.singular, ...n.plural]);
  for (const [w, adjs] of Object.entries(adj)) for (const a of adjs) for (const col of Object.values(a.forms)) add(w, col);
  return forms;
}

// ------------------------------------------------------------------ French (ports of desktop/french.py)
export const FR_TENSES = ["present", "passe_compose", "imparfait", "futur", "conditionnel"] as const;
export const FR_TENSE_LABELS: Record<string, string> = { present: "Présent", passe_compose: "Passé composé", imparfait: "Imparfait", futur: "Futur simple", conditionnel: "Conditionnel" };
export const FR_ADJ_LABELS: [FrAdjKey, string][] = [["ms", "masculine singular"], ["fs", "feminine singular"], ["mp", "masculine plural"], ["fp", "feminine plural"]];
export type FrAdjKey = "ms" | "fs" | "mp" | "fp";
export interface FrVerb { infinitive?: string; tenses: Record<string, string[]> }
export interface FrNoun { lemma?: string; gender?: string; singular: string; plural?: string | null }
export interface FrAdjective { lemma?: string; forms: Record<FrAdjKey, string> }

const six = (v: unknown): v is string[] => Array.isArray(v) && v.length === 6;
export const loadFrVerbs = (data: unknown) =>
  byCard<FrVerb>(data, "verbs", (v) => isObj(v) && isObj(v.tenses) && FR_TENSES.some((t) => six(v.tenses[t])));
export const loadFrNouns = (data: unknown) => byCard<FrNoun>(data, "nouns", (n) => isObj(n) && isStr(n.singular));
export const loadFrAdjectives = (data: unknown) =>
  byCard<FrAdjective>(data, "adjectives", (a) => isObj(a) && isObj(a.forms) && FR_ADJ_LABELS.every(([k]) => isStr(a.forms[k])));

const SUBJECT = /^(?:j'|je |tu |il\/elle |ils\/elles |nous |vous )/i;
const REFLEXIVE = /^(?:me |m'|te |t'|se |s'|nous |vous )/i;
const ARTICLE = /^(?:l'|la |le |les |un |une |des )/i;

/** 'aperçu(e)(s)' -> every combination of the bracketed letters, in the same order as the Python code. */
export function expandOptional(form: string): string[] {
  const parts = form.split(/\(([^()]*)\)/);
  if (parts.length === 1) return [form];
  let combos: string[] = [""];
  parts.forEach((part, i) => {
    const options = i % 2 === 0 ? [part] : ["", part];
    combos = combos.flatMap((c) => options.map((o) => c + o));
  });
  return [...new Set(combos)];
}

/** Forms as they appear in a sentence: no leading subject / reflexive pronoun, bracketed letters expanded. */
export function clozeForms(forms: (string | null | undefined)[]): string[] {
  const out: string[] = [];
  for (const form of forms) {
    if (!form) continue;
    const text = form.trim().replace(SUBJECT, "").replace(REFLEXIVE, "");
    for (const v of expandOptional(text)) if (v && !out.includes(v)) out.push(v);
  }
  return out;
}

export function frKnownForms(conj: Record<string, FrVerb[]>, decl: Record<string, FrNoun[]>, adj: Record<string, FrAdjective[]>): Record<string, string[]> {
  const forms: Record<string, string[]> = {};
  const add = (w: string, fs: string[]) => { (forms[w] ??= []).push(...fs); };
  for (const [w, verbs] of Object.entries(conj)) add(w, clozeForms(verbs.flatMap((v) => FR_TENSES.flatMap((t) => v.tenses[t] ?? []))));
  for (const [w, nouns] of Object.entries(decl)) add(w, clozeForms(nouns.flatMap((n) => [n.singular, n.plural]).filter(Boolean).map((f) => (f as string).replace(ARTICLE, ""))));
  for (const [w, adjs] of Object.entries(adj)) add(w, clozeForms(adjs.flatMap((a) => FR_ADJ_LABELS.map(([k]) => a.forms[k]))));
  return forms;
}
