// Deck logic: port of flashcards.FlashcardDeck (levels, filters, search, quick set, smart mix).
import { fold, sample, shuffle, type Rng } from "./text";

export const MIX_WEIGHTS: [number, number][] = [[2, 45], [1, 35], [0, 20]];

export const LEVELS: { level: number; name: string; icon: string }[] = [
  { level: 0, name: "To verify", icon: "✕" },
  { level: 1, name: "Learning", icon: "◔" },
  { level: 2, name: "Almost there", icon: "◑" },
  { level: 3, name: "Known", icon: "✓" },
];
export const TOP_LEVEL = 3;
export const ARCHIVED = 4;

export function levelName(level: number | null): string {
  if (level === null) return "new";
  if (level === ARCHIVED) return "archived";
  return LEVELS.find((l) => l.level === level)!.name.toLowerCase();
}

export function levelIcon(level: number | null): string {
  if (level === null) return "●";
  if (level === ARCHIVED) return "▣";
  return LEVELS.find((l) => l.level === level)!.icon;
}

export interface Word {
  word: string;
  translation: string;
  sentence: string;
  sentence_translation: string;
  level: number | null;
  fails: number;
  extra: Record<string, unknown>;
}

export type Mode = "all" | "new" | "level0" | "level1" | "level2" | "level3" | "level4" | "failed" | "quick" | "search";

const isInt = (v: unknown): v is number => typeof v === "number" && Number.isInteger(v);

/** Validate and convert the JSON of words.json. Throws Error with the same messages as the desktop app. */
export function parseWords(data: unknown): Word[] {
  if (!Array.isArray(data)) throw new Error("The JSON root must be a list.");
  const words: Word[] = [];
  data.forEach((item, i) => {
    if (item === null || typeof item !== "object" || Array.isArray(item)) throw new Error(`Item #${i + 1} must be an object.`);
    const o = item as Record<string, unknown>;
    const { word, translation, sentence, sentence_translation, fails } = o;
    if (typeof word !== "string" || !word.trim()) throw new Error(`Item #${i + 1} has an invalid 'word'.`);
    if (typeof translation !== "string" || !translation.trim()) throw new Error(`Item #${i + 1} has an invalid 'translation'.`);
    let level: number | null;
    if (isInt(o.level) && o.level >= 0 && o.level <= ARCHIVED) level = o.level;
    else level = o.known === true ? TOP_LEVEL : o.known === false ? 0 : null;
    const extra: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(o)) {
      if (!["word", "translation", "sentence", "sentence_translation", "level", "fails", "known"].includes(k)) extra[k] = v;
    }
    words.push({
      word: word.trim(),
      translation: translation.trim(),
      sentence: typeof sentence === "string" ? sentence.trim() : "",
      sentence_translation: typeof sentence_translation === "string" ? sentence_translation.trim() : "",
      level,
      fails: isInt(fails) && fails > 0 ? fails : 0,
      extra,
    });
  });
  if (!words.length) throw new Error("The JSON file contains no words.");
  return words;
}

/** The exact object the desktop app writes for one card (key order included). */
export function wordToJson(w: Word): Record<string, unknown> {
  const item: Record<string, unknown> = { ...w.extra };
  item.word = w.word;
  item.translation = w.translation;
  if (w.sentence) item.sentence = w.sentence;
  if (w.sentence_translation) item.sentence_translation = w.sentence_translation;
  if (w.level !== null) item.level = w.level;
  if (w.fails) item.fails = w.fails;
  return item;
}

/** Same bytes as Python's json.dump(data, ensure_ascii=False, indent=4). */
export function serializeWords(words: Word[]): string {
  return JSON.stringify(words.map(wordToJson), null, 4);
}

export class FlashcardDeck {
  static QUICK_SIZE = 10;
  words: Word[];
  mode: Mode = "all";
  index = 0;
  results = new Map<number, number>();
  private quickIds: number[] = [];
  private searchIds: number[] = [];
  order: number[];
  /** Called after every change that must be saved. */
  onSave?: (words: Word[]) => void;
  rng: Rng;

  constructor(words: Word[] = [], rng: Rng = Math.random) {
    this.words = words;
    this.rng = rng;
    this.order = this.buildOrder();
  }

  private buildOrder(): number[] {
    const ids = this.words.map((_, i) => i);
    if (this.mode === "quick") return [...this.quickIds];
    if (this.mode === "search") return [...this.searchIds];
    if (this.mode === "new") return ids.filter((i) => this.words[i].level === null);
    if (this.mode === "failed") {
      return ids.filter((i) => this.words[i].fails > 0 && this.words[i].level !== ARCHIVED)
        .sort((a, b) => this.words[b].fails - this.words[a].fails);
    }
    if (this.mode.startsWith("level")) {
      const target = Number(this.mode.slice(5));
      return ids.filter((i) => this.words[i].level === target);
    }
    return ids.filter((i) => this.words[i].level !== ARCHIVED);
  }

  setMode(mode: Mode): void {
    this.mode = mode;
    this.index = 0;
    this.results.clear();
    this.order = this.buildOrder();
  }

  /** Card ids whose level is in `levels` (null in the set = new cards). `levels` undefined = all but archived. */
  pool(levels?: Set<number | null> | null, allowed?: Set<number> | null): number[] {
    let ids: number[];
    if (!levels) ids = this.words.map((_, i) => i).filter((i) => this.words[i].level !== ARCHIVED);
    else ids = this.words.map((_, i) => i).filter((i) => levels.has(this.words[i].level));
    if (allowed) ids = ids.filter((i) => allowed.has(i));
    return ids;
  }

  /** Case- and accent-insensitive search; archived cards included. Returns the number of matches. */
  search(query: string): number {
    const q = fold(query);
    const hits: [number, number][] = [];
    this.words.forEach((w, i) => {
      if (fold(`${w.word} ${w.translation}`).includes(q)) hits.push([0, i]);
      else if (fold(`${w.sentence} ${w.sentence_translation}`).includes(q)) hits.push([1, i]);
    });
    hits.sort((a, b) => a[0] - b[0] || a[1] - b[1]);
    this.searchIds = hits.map(([, i]) => i);
    this.setMode("search");
    return this.searchIds.length;
  }

  quickSet(levels?: Set<number | null> | null, size?: number): number {
    const n = size || FlashcardDeck.QUICK_SIZE;
    const pool = this.pool(levels);
    this.quickIds = sample(pool, Math.min(n, pool.length), this.rng);
    this.setMode("quick");
    return this.quickIds.length;
  }

  /** Weighted mix of the learning levels (largest-remainder allocation, shortages go to other levels). */
  mixedSample(size: number, weights: [number, number][] = MIX_WEIGHTS, allowed?: Set<number> | null): number[] {
    const wOf = new Map(weights);
    let pools: [number, number[]][] = [];
    for (const [key] of weights) {
      const p = this.pool(new Set([key]), allowed);
      if (p.length) pools.push([key, shuffle(p.slice(), this.rng)]);
    }
    const totalAvailable = pools.reduce((s, [, v]) => s + v.length, 0);
    size = Math.min(size, totalAvailable);
    const picked: number[] = [];
    while (picked.length < size && pools.length) {
      const remaining = size - picked.length;
      const weightSum = pools.reduce((s, [k]) => s + wOf.get(k)!, 0);
      const quotas = new Map(pools.map(([k]) => [k, (remaining * wOf.get(k)!) / weightSum]));
      const counts = new Map(pools.map(([k]) => [k, Math.trunc(quotas.get(k)!)]));
      let leftover = remaining - [...counts.values()].reduce((s, c) => s + c, 0);
      const byRemainder = pools.map(([k]) => k).sort((a, b) => (quotas.get(b)! - counts.get(b)!) - (quotas.get(a)! - counts.get(a)!));
      for (const k of byRemainder.slice(0, leftover)) counts.set(k, counts.get(k)! + 1);
      pools = pools.map(([k, v]): [number, number[]] => {
        const take = Math.min(counts.get(k)!, v.length);
        picked.push(...v.slice(0, take));
        return [k, v.slice(take)];
      }).filter(([, v]) => v.length > 0);
    }
    return shuffle(picked, this.rng);
  }

  private save(): void { this.onSave?.(this.words); }

  recordFail(id: number): void { this.words[id].fails += 1; this.save(); }

  resetProgress(): void {
    for (const w of this.words) { w.level = null; w.fails = 0; }
    this.save();
    this.setMode(this.mode);
  }

  get total(): number { return this.order.length; }
  get currentNumber(): number { return this.order.length ? this.index + 1 : 0; }
  get current(): Word { return this.words[this.order[this.index]]; }
  get currentId(): number { return this.order[this.index]; }
  get overallTotal(): number { return this.words.length; }
  levelCount(level: number): number { return this.words.filter((w) => w.level === level).length; }
  get activeCount(): number { return this.words.filter((w) => w.level !== ARCHIVED).length; }
  get newCount(): number { return this.words.filter((w) => w.level === null).length; }
  get sessionKnown(): number { return [...this.results.values()].filter((r) => r >= TOP_LEVEL).length; }
  get sessionUnknown(): number { return [...this.results.values()].filter((r) => r < TOP_LEVEL).length; }
  get isLast(): boolean { return this.index >= this.total - 1; }

  /** Move the current card to `level`; only a Known card can be archived. */
  mark(level: number): void {
    if (level === ARCHIVED && this.words[this.currentId].level !== TOP_LEVEL) return;
    this.results.set(this.currentId, level);
    this.words[this.currentId].level = level;
    this.save();
  }

  next(): void { if (!this.isLast) this.index++; }
  previous(): void { if (this.index > 0) this.index--; }
  shuffle(): void { this.restart(true); }

  restart(doShuffle = false): void {
    this.index = 0;
    this.results.clear();
    this.order = this.buildOrder();
    if (doShuffle) shuffle(this.order, this.rng);
  }
}
