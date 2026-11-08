// Quiz session logic (typed + fill-in-the-blank): the non-UI parts of quiz.py.
import { checkAnswer } from "./answer";
import { BLANK, blankSentence } from "./cloze";
import { FlashcardDeck, levelName, type Word } from "./deck";
import type { Example } from "./tables";
import { shuffle, type Rng } from "./text";

export interface SetupChoice {
  mix: boolean;
  levels: Set<number | null>;
  count: number;
  all: boolean;
  allowed?: Set<number> | null;
}

/** Card ids for a quiz, as QuizSetupDialog.card_ids does. */
export function quizCardIds(deck: FlashcardDeck, c: SetupChoice, rng: Rng = Math.random): number[] {
  if (c.mix) return deck.mixedSample(Math.max(1, c.count), undefined, c.allowed);
  const pool = shuffle(deck.pool(c.levels, c.allowed), rng);
  return c.all ? pool : pool.slice(0, Math.max(1, c.count));
}

/** Cards whose sentence (or an extra example) contains the word: the cloze quiz can use only those. */
export function clozeAllowed(deck: FlashcardDeck, forms: Record<string, string[]>, examples: Record<string, Example[]>): Set<number> {
  const allowed = new Set<number>();
  deck.words.forEach((w, i) => {
    const sentences = [w.sentence, ...(examples[w.word] ?? []).map((e) => e[0])];
    if (sentences.some((s) => blankSentence(w, forms[w.word], s) !== null)) allowed.add(i);
  });
  return allowed;
}

export interface Feedback { ok: boolean; exact: boolean; expected: string; fails: number; sentence: [string, string] }

export class QuizSession {
  position = 0;
  results: [number, boolean][] = [];
  answered = false;
  private chosen = new Map<string, [string, string]>();

  constructor(
    public deck: FlashcardDeck,
    public ids: number[],
    public englishPrompt: boolean,
    public ignoreAccents: boolean,
    public cloze?: { forms: Record<string, string[]>; examples: Record<string, Example[]>; rng?: Rng },
  ) {}

  get word(): Word { return this.deck.words[this.ids[this.position]]; }
  get wordId(): number { return this.ids[this.position]; }
  get total(): number { return this.ids.length; }
  get isLast(): boolean { return this.position >= this.ids.length - 1; }

  /** Cloze: the card's sentence or one extra example, picked once per card for the session. */
  currentSentence(): [string, string] {
    const w = this.word;
    if (!this.chosen.has(w.word)) {
      const options: [string, string][] = [[w.sentence, w.sentence_translation], ...(this.cloze?.examples[w.word] ?? [])];
      shuffle(options, this.cloze?.rng);
      const forms = this.cloze?.forms[w.word];
      const usable = options.filter((o) => blankSentence(w, forms, o[0]) !== null);
      this.chosen.set(w.word, usable[0] ?? [w.sentence, w.sentence_translation]);
    }
    return this.chosen.get(w.word)!;
  }

  currentBlank(): [string, string] {
    return blankSentence(this.word, this.cloze?.forms[this.word.word], this.currentSentence()[0]) ?? ["", ""];
  }

  promptText(): string {
    if (this.cloze) return this.currentBlank()[0].replace(BLANK, `${BLANK} (${this.word.translation})`);
    return this.englishPrompt ? this.word.translation : this.word.word;
  }

  expectedText(): string {
    if (this.cloze) return this.currentBlank()[1];
    return this.englishPrompt ? this.word.word : this.word.translation;
  }

  /** "New", "Learning" ... shown next to the prompt. */
  pill(): string {
    const w = this.word;
    return w.level === null ? "New" : levelName(w.level).replace(/^./, (c) => c.toUpperCase());
  }

  hint(): string { return `“${this.currentSentence()[1]}”\n\nDictionary form: ${this.word.word}`; }

  private feedback(ok: boolean, exact: boolean): Feedback {
    const id = this.wordId;
    this.answered = true;
    this.results.push([id, ok]);
    if (!ok) this.deck.recordFail(id);
    return {
      ok, exact, expected: this.expectedText(), fails: this.word.fails,
      sentence: this.cloze ? this.currentSentence() : [this.word.sentence, this.word.sentence_translation],
    };
  }

  /** Empty answer counts as "I don't know", like Enter on the desktop. */
  submit(given: string): Feedback | null {
    if (this.answered) return null;
    if (!given.trim()) return this.dontKnow();
    const [ok, exact] = checkAnswer(given, this.expectedText(), this.ignoreAccents);
    return this.feedback(ok, exact);
  }

  dontKnow(): Feedback | null {
    return this.answered ? null : this.feedback(false, false);
  }

  /** Move on; returns true when the quiz is finished. */
  next(): boolean {
    if (!this.answered) return false;
    if (this.isLast) return true;
    this.position++;
    this.answered = false;
    return false;
  }

  get score(): number { return this.results.filter(([, ok]) => ok).length; }
  get failedWords(): Word[] { return this.results.filter(([, ok]) => !ok).map(([i]) => this.deck.words[i]); }
}
