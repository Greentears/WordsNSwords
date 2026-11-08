// Fill-in-the-blank questions for sentence battles, from the deck's sentences and the extra examples.
import { blankSentence } from "../core/cloze";
import type { Example } from "../core/tables";
import type { DeckLike } from "./selector";
import { shuffleInPlace, type Rng } from "./util";

export class ClozeSource {
  constructor(public deck: DeckLike, public examples: Record<string, Example[]>, public rng: Rng) {}

  /** [sentence with a blank, accepted answers, English translation] or null. */
  call(wordId: number): [string, string, string] | null {
    const card = this.deck.words[wordId];
    const options: [string, string][] = [];
    if (card.sentence.trim()) options.push([card.sentence, card.sentence_translation]);
    options.push(...(Object.hasOwn(this.examples, card.word) ? this.examples[card.word] : []));
    shuffleInPlace(options, this.rng);
    for (const [sentence, english] of options) {
      const found = blankSentence(card, null, sentence);
      if (found) return [found[0], found[1], english];
    }
    return null;
  }
}
