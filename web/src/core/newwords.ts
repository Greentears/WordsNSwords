/**
 * Check and merge new words made by an AI. Same rules as desktop/newwords.py (verified by tests/newwords.test.ts
 * against cases made with the Python code). Works on plain data, so it can run on a phone or in a test.
 */
export type Json = Record<string, unknown>;
export interface DeckData {
  words: Json[];
  verbs: Json[];
  nouns: Json[];
  adjectives: Json[];
  examples: Record<string, Json[]>;
  sentences: Json[];
}
export interface Counts { words: number; skipped: number; verbs: number; nouns: number; adjectives: number; examples: number; sentences: number }

const ASPECTS = ["imperfective", "perfective"];
const GENDERS = ["m", "f", "n", "pl", "num"];
// French (language "fr"): tenses are tables of 6 persons, nouns and adjectives are plain strings.
const FR_TENSES = ["present", "passe_compose", "imparfait", "futur", "conditionnel"];
const FR_GENDERS = ["m", "f"];
const FR_ADJ_FORMS = ["ms", "fs", "mp", "fp"];
/** "fr" for French decks ("fr-en"), "pl" (the original table format) for everything else. */
export const languageOf = (deck: string): string => (deck.split("-")[0] === "fr" ? "fr" : "pl");

const PARTS = ["words", "verbs", "nouns", "adjectives", "examples", "sentences"];

const isObj = (v: unknown): v is Json => typeof v === "object" && v !== null && !Array.isArray(v);
const isText = (v: unknown): v is string => typeof v === "string" && v.trim() !== "";
const forms = (v: unknown, count: number, allowNull = false) =>
  Array.isArray(v) && v.length === count && v.every((x) => isText(x) || (allowNull && x === null));

export function validate(data: unknown, existingCards: Iterable<string> = [], language = "pl"): string[] {
  const french = language === "fr";
  if (!isObj(data)) return ["The answer must be one JSON object with the keys words, verbs, nouns, adjectives, examples, sentences."];
  const errors: string[] = [];
  const known = new Set(existingCards);
  let words = data.words ?? [];
  if (!Array.isArray(words)) { errors.push('"words" must be a list.'); words = []; }
  (words as unknown[]).forEach((w, idx) => {
    const i = idx + 1;
    if (!isObj(w) || !isText(w.word) || !isText(w.translation)) { errors.push(`words #${i}: needs a "word" and a "translation".`); return; }
    known.add(w.word.trim());
    for (const key of ["sentence", "sentence_translation"]) {
      if (key in w && typeof w[key] !== "string") errors.push(`words "${w.word}": "${key}" must be text.`);
    }
    if (Boolean(w.sentence) !== Boolean(w.sentence_translation)) errors.push(`words "${w.word}": give both "sentence" and "sentence_translation", or neither.`);
  });
  for (const part of ["verbs", "nouns", "adjectives"]) {
    const entries = data[part] ?? [];
    if (!Array.isArray(entries)) { errors.push(`"${part}" must be a list.`); continue; }
    entries.forEach((e, idx) => {
      const where = `${part} #${idx + 1}`;
      if (!isObj(e) || !isText(e.card) || !Array.isArray(e[part]) || (e[part] as unknown[]).length === 0) {
        errors.push(`${where}: needs a "card" and a non-empty "${part}" list.`);
        return;
      }
      if (!known.has(e.card.trim())) errors.push(`${where}: card "${e.card}" is not in words (spell it exactly like the card).`);
      for (const item of e[part] as unknown[]) {
        if (!isObj(item)) errors.push(`${where}: every item must be an object.`);
        else if (part === "verbs" && french) {
          if (!isText(item.infinitive)) errors.push(`${where}: needs an "infinitive".`);
          const tenses = item.tenses;
          if (!isObj(tenses)) errors.push(`${where}: needs "tenses" with ${FR_TENSES.join(", ")} (6 forms each: je, tu, il/elle, nous, vous, ils/elles).`);
          else for (const t of FR_TENSES) if (!forms(tenses[t], 6)) errors.push(`${where}: "tenses.${t}" must be 6 forms (je, tu, il/elle, nous, vous, ils/elles).`);
        } else if (part === "nouns" && french) {
          if (!isText(item.lemma) || !FR_GENDERS.includes(item.gender as string) || !isText(item.singular) || !(item.plural === null || isText(item.plural))) {
            errors.push(`${where}: needs "lemma", "gender" (m or f), "singular" (with its article, e.g. "l'enjeu") and "plural" (or null).`);
          }
        } else if (part === "adjectives" && french) {
          const f = item.forms;
          if (!isText(item.lemma) || !isObj(f) || !FR_ADJ_FORMS.every((k) => isText(f[k]))) errors.push(`${where}: needs "lemma" and "forms" with ms, fs, mp, fp (one text each).`);
        } else if (part === "verbs") {
          if (!isText(item.infinitive) || !ASPECTS.includes(item.aspect as string)) errors.push(`${where}: needs "infinitive" and "aspect" (${ASPECTS.join(" or ")}).`);
          if (!forms(item.forms, 6)) errors.push(`${where}: "forms" must be 6 forms (ja, ty, on/ona/ono, my, wy, oni/one).`);
          if ("past" in item && !forms(item.past, 5)) errors.push(`${where}: "past" must be 5 forms (m, f, n, men plural, other plural).`);
          if ("imperative" in item && !forms(item.imperative, 3)) errors.push(`${where}: "imperative" must be 3 forms (ty, my, wy).`);
        } else if (part === "nouns") {
          if (!isText(item.lemma) || !GENDERS.includes(item.gender as string)) errors.push(`${where}: needs "lemma" and "gender" (${GENDERS.join(", ")}).`);
          if (!forms(item.singular, 7, true) || !forms(item.plural, 7, true)) errors.push(`${where}: "singular" and "plural" must each have 7 cases (null where none).`);
        } else {
          const f = item.forms;
          if (!isText(item.lemma) || !isObj(f) || !["m", "f", "n", "pl"].every((g) => forms(f[g], 7))) errors.push(`${where}: needs "lemma" and "forms" with m, f, n, pl of 7 cases each.`);
        }
      }
    });
  }
  const examples = data.examples ?? {};
  if (!isObj(examples)) errors.push('"examples" must be an object {card: [{"pl", "en"}]}.');
  else {
    for (const [card, items] of Object.entries(examples)) {
      if (!known.has(card)) errors.push(`examples: card "${card}" is not in words.`);
      if (!Array.isArray(items) || !items.every((x) => isObj(x) && isText(x.pl) && isText(x.en))) errors.push(`examples "${card}": must be a list of {"pl", "en"}.`);
    }
  }
  const sentences = data.sentences ?? [];
  if (!Array.isArray(sentences)) errors.push('"sentences" must be a list.');
  else {
    sentences.forEach((s, idx) => {
      const i = idx + 1;
      if (!isObj(s) || !isText(s.pl) || !isText(s.en) || !Array.isArray(s.words) || s.words.length === 0) errors.push(`sentences #${i}: needs "pl", "en" and a non-empty "words" list.`);
      else if (!(s.words as string[]).every((w) => known.has(w))) {
        errors.push(`sentences #${i}: "words" must be cards of the deck (missing: ${(s.words as string[]).filter((w) => !known.has(w)).join(", ")}).`);
      }
    });
  }
  const unknown = Object.keys(data).filter((k) => !PARTS.includes(k));
  if (unknown.length) errors.push(`Unknown keys: ${unknown.join(", ")}.`);
  return errors;
}

/** Python-style deep equality of two JSON values (used to skip duplicate examples). */
const same = (a: unknown, b: unknown) => JSON.stringify(a) === JSON.stringify(b);

/** Add `data` to `deck` (a copy is returned). Existing cards, tables and sentences are never changed. */
export function merge(deck: DeckData, data: Json): { deck: DeckData; counts: Counts } {
  const out: DeckData = JSON.parse(JSON.stringify(deck));
  const counts: Counts = { words: 0, skipped: 0, verbs: 0, nouns: 0, adjectives: 0, examples: 0, sentences: 0 };
  const have = new Set(out.words.map((w) => w.word as string));
  for (const w of (data.words as Json[] | undefined) ?? []) {
    const word = (w.word as string).trim();
    if (have.has(word)) { counts.skipped++; continue; }
    const card: Json = { word, translation: (w.translation as string).trim() };
    for (const key of ["sentence", "sentence_translation"]) if (w[key]) card[key] = (w[key] as string).trim();
    out.words.push(card);
    have.add(word);
    counts.words++;
  }
  for (const part of ["verbs", "nouns", "adjectives"] as const) {
    const done = new Set(out[part].map((e) => e.card as string));
    for (const entry of (data[part] as Json[] | undefined) ?? []) {
      if (!done.has(entry.card as string)) { out[part].push(entry); done.add(entry.card as string); counts[part]++; }
    }
  }
  const ex = (data.examples as Record<string, Json[]> | undefined) ?? {};
  for (const [card, items] of Object.entries(ex)) {
    const mine = (out.examples[card] ??= []);
    for (const item of items) if (!mine.some((m) => same(m, item))) { mine.push(item); counts.examples++; }
  }
  const seen = new Set(out.sentences.map((s) => s.pl as string));
  for (const s of (data.sentences as Json[] | undefined) ?? []) {
    if (!seen.has(s.pl as string)) { out.sentences.push(s); seen.add(s.pl as string); counts.sentences++; }
  }
  return { deck: out, counts };
}

/** Parse the AI's answer (it may be wrapped in a ```json fence). */
export function parseAnswer(text: string): { data?: Json; error?: string } {
  text = text.trim();
  if (text.startsWith("```")) {
    const nl = text.indexOf("\n");
    text = nl >= 0 ? text.slice(nl + 1) : "";
    const end = text.lastIndexOf("```");
    if (end >= 0) text = text.slice(0, end);
  }
  try {
    const data = JSON.parse(text);
    return { data };
  } catch (e) {
    return { error: `The answer is not valid JSON: ${(e as Error).message}` };
  }
}

/** Parse, validate and merge in one go. */
export function checkAndMerge(deck: DeckData, text: string, language = "pl"): { errors: string[]; deck?: DeckData; counts?: Counts; data?: Json } {
  const parsed = parseAnswer(text);
  if (parsed.error || !parsed.data) return { errors: [parsed.error ?? "Empty answer."] };
  const errors = validate(parsed.data, deck.words.map((w) => w.word as string), language);
  if (errors.length) return { errors };
  const r = merge(deck, parsed.data as Json);
  return { errors: [], deck: r.deck, counts: r.counts, data: parsed.data };
}

export function emptyDeck(): DeckData { return { words: [], verbs: [], nouns: [], adjectives: [], examples: {}, sentences: [] }; }

/** Several answers as ONE answer (for "Copy what I added"): the same shape the AI gives. */
export function combineAdditions(additions: Json[]): Json {
  let deck = emptyDeck();
  for (const a of additions) deck = merge(deck, a).deck;
  const out: Json = {};
  for (const [k, v] of Object.entries(deck)) if (Array.isArray(v) ? v.length : Object.keys(v).length) out[k] = v;
  return out;
}
