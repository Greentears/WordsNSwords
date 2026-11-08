// Backup export / import. A backup holds words (with levels and fails), settings and stats.
// Import also accepts a plain desktop words.json (a list of cards).
import { parseWords, wordToJson, ARCHIVED, type Word } from "./deck";
import type { Stats } from "./stats";

export const BACKUP_APP = "flashcards-web";
export interface Backup { app: string; version: 1; exportedAt: string; words: Record<string, unknown>[]; settings: Record<string, unknown>; stats: Stats; dungeon?: unknown }

export function makeBackup(words: Word[], settings: Record<string, unknown>, stats: Stats, now = new Date(), dungeon: unknown = null): Backup {
  return { app: BACKUP_APP, version: 1, exportedAt: now.toISOString(), words: words.map(wordToJson), settings, stats, ...(dungeon ? { dungeon } : {}) };
}

export type MergeStrategy = "higher" | "replace" | "keep";

/** Progress score: a higher level wins, then more fails. New cards score lowest. */
export function progressScore(w: Word): number {
  return (w.level === null ? -1 : w.level) * 1000 + Math.min(w.fails, 999);
}

export interface ImportResult { kind: "backup" | "words"; words: Word[]; settings?: Record<string, unknown>; stats?: Stats; added: number; updated: number; unchanged: number }

/** Merge `incoming` cards into `current` by `word`. */
export function mergeWords(current: Word[], incoming: Word[], strategy: MergeStrategy): { words: Word[]; added: number; updated: number; unchanged: number } {
  const out = current.map((w) => ({ ...w, extra: { ...w.extra } }));
  const index = new Map(out.map((w, i) => [w.word, i]));
  let added = 0, updated = 0, unchanged = 0;
  for (const inc of incoming) {
    const i = index.get(inc.word);
    if (i === undefined) { index.set(inc.word, out.length); out.push({ ...inc, extra: { ...inc.extra } }); added++; continue; }
    const cur = out[i];
    // Text fields (translation, sentences, extra keys) come from the import; progress follows the strategy.
    const useIncomingProgress = strategy === "replace" || (strategy === "higher" && progressScore(inc) > progressScore(cur));
    const next: Word = {
      ...cur, translation: inc.translation, sentence: inc.sentence, sentence_translation: inc.sentence_translation,
      extra: { ...cur.extra, ...inc.extra },
      level: useIncomingProgress ? inc.level : cur.level, fails: useIncomingProgress ? inc.fails : cur.fails,
    };
    if (JSON.stringify(wordToJson(next)) === JSON.stringify(wordToJson(cur))) unchanged++;
    else { out[i] = next; updated++; }
  }
  return { words: out, added, updated, unchanged };
}

/** Parse the text of an imported file: a backup or a desktop words.json. Throws Error with a readable message. */
export function parseImport(text: string): { kind: "backup" | "words"; words: Word[]; settings?: Record<string, unknown>; stats?: Stats; dungeon?: unknown } {
  let data: unknown;
  try { data = JSON.parse(text); } catch { throw new Error("This file is not valid JSON."); }
  if (Array.isArray(data)) return { kind: "words", words: parseWords(data) };
  if (data && typeof data === "object" && (data as Backup).app === BACKUP_APP && Array.isArray((data as Backup).words)) {
    const b = data as Backup;
    return { kind: "backup", words: parseWords(b.words), settings: b.settings, stats: b.stats, dungeon: b.dungeon };
  }
  throw new Error("Unrecognised file: expected a flashcards backup or a words.json list.");
}

export const isArchived = (w: Word) => w.level === ARCHIVED;
