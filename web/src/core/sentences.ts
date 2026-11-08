// Sentence practice selection: port of sentences.pick_sentences.
import { MIX_WEIGHTS, type FlashcardDeck } from "./deck";
import type { Rng } from "./text";
import type { SentenceItem } from "./tables";

export function sentenceWeight(deck: FlashcardDeck, s: SentenceItem): number {
  const byWord = new Map(deck.words.map((w) => [w.word, w]));
  const wOf = new Map(MIX_WEIGHTS);
  const levels = (s.words ?? []).filter((t) => byWord.has(t)).map((t) => byWord.get(t)!.level);
  const learning = levels.filter((lv): lv is number => lv !== null && wOf.has(lv));
  if (!learning.length) return 0;
  let total = learning.reduce((sum, lv) => sum + wOf.get(lv)!, 0);
  if (new Set(learning).size > 1) total *= 1.5;
  return total;
}

export function pickSentences(deck: FlashcardDeck, sentences: SentenceItem[], size: number, rng: Rng = Math.random): SentenceItem[] {
  let candidates: [SentenceItem, number][] = sentences.map((s) => [s, sentenceWeight(deck, s)] as [SentenceItem, number]).filter(([, w]) => w > 0);
  if (!candidates.length) candidates = sentences.map((s) => [s, 1] as [SentenceItem, number]);
  // Weighted random order without replacement (Efraimidis-Spirakis).
  const keyed = candidates.map(([s, w]) => ({ s, k: Math.pow(rng(), 1 / w) })).sort((a, b) => b.k - a.k);
  return keyed.slice(0, size).map((x) => x.s);
}
