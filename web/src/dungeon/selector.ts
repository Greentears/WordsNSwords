// Choosing which vocabulary card each question uses. Reads the deck, never changes it.
import * as config from "./config";
import type { Weights } from "./config";
import type { Word } from "../core/deck";
import { ARCHIVED } from "../core/deck";
import { isDict, isInt, weightedIndex, type Rng } from "./util";

export interface DeckLike { words: Word[] }

/** Words answered wrongly in the dungeon, with the streak of correct answers since. */
export class MissedWords {
  private streaks = new Map<string, number>();

  constructor(data: unknown = null) {
    if (isDict(data)) {
      for (const [word, streak] of Object.entries(data)) {
        if (isInt(streak)) this.streaks.set(word, Math.max(0, Math.min(streak, config.MISSED_CLEAR_STREAK - 1)));
      }
    }
  }

  get size(): number { return this.streaks.size; }
  has(word: string): boolean { return this.streaks.has(word); }
  words(): string[] { return [...this.streaks.keys()].sort(); }
  miss(word: string): void { this.streaks.set(word, 0); }

  /** Register a correct answer; true when this cleared the word from the list. */
  correct(word: string): boolean {
    const s = this.streaks.get(word);
    if (s === undefined) return false;
    if (s + 1 >= config.MISSED_CLEAR_STREAK) { this.streaks.delete(word); return true; }
    this.streaks.set(word, s + 1);
    return false;
  }

  to_dict(): Record<string, number> { return Object.fromEntries(this.streaks); }
}

export class VocabularySelector {
  weights: Weights;
  recent: number[] = [];
  only_missed = false;   // review mode: ask only words you missed (when there are any)

  constructor(public deck: DeckLike, public missed: MissedWords, public rng: Rng, weights?: Weights) {
    this.weights = new Map(weights ?? config.LEVEL_WEIGHTS);
  }

  weight(wordId: number, weights?: Weights): number {
    const w = this.deck.words[wordId];
    if (w.level === ARCHIVED || !w.word.trim() || !w.translation.trim()) return 0;
    let value = (weights ?? this.weights).get(w.level) ?? 0;
    if (value > 0 && this.missed.has(w.word)) value *= config.MISSED_WEIGHT_BONUS;
    return value;
  }

  candidates(weights?: Weights): number[] {
    let ids = this.deck.words.map((_, i) => i).filter((i) => this.weight(i, weights) > 0);
    if (this.only_missed) {
      const missed = ids.filter((i) => this.missed.has(this.deck.words[i].word));
      if (missed.length) ids = missed;
    }
    return ids;
  }

  /** A card id, or null when nothing in the deck can be asked. Recently asked cards are skipped. */
  pick(weights?: Weights): number | null {
    const ids = this.candidates(weights);
    if (!ids.length) return null;
    let fresh = ids.filter((i) => !this.recent.includes(i));
    if (!fresh.length) {
      const last = this.recent.length ? this.recent[this.recent.length - 1] : null;
      fresh = ids.filter((i) => i !== last);
      if (!fresh.length) fresh = ids;
    }
    const choice = fresh[weightedIndex(this.rng, fresh.map((i) => this.weight(i, weights)))];
    this.recent.push(choice);
    if (this.recent.length > config.RECENT_WINDOW) this.recent.shift();
    return choice;
  }
}
