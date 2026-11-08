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
