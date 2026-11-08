// One fight: the player translates words, the monster hits back on mistakes. Port of dungeon/battle.py.
import * as config from "./config";
import { check, primary } from "./answers";
import { Monster, type Player } from "./models";
import type { MissedWords, VocabularySelector } from "./selector";
import { GameError, choiceIndex, pyInt, pyRound, uniform, type Rng } from "./util";

export const ACTIVE = "active", VICTORY = "victory", DEFEAT = "defeat";

export interface Question {
  word_id: number;
  prompt: string;          // what is shown (Polish word, or the English meaning when reversed)
  answer: string;          // expected answer, exactly as on the card
  reverse: boolean;        // true: the player types the Polish word
  show_first: boolean;     // first letter revealed (item / charm)
  show_count: boolean;     // letter count revealed (item)
  time_limit: number;      // seconds, 0 = unlimited
  kind: string;            // "word" or "cloze"
  gloss: string;           // cloze: English meaning of the missing word
  context: string;         // cloze: English translation of the sentence
}
const newQuestion = (word_id: number, prompt: string, answer: string, reverse: boolean, time_limit: number,
  extra: Partial<Question> = {}): Question =>
  ({ word_id, prompt, answer, reverse, show_first: false, show_count: false, time_limit, kind: "word", gloss: "", context: "", ...extra });
export const isCloze = (q: Question): boolean => q.kind === "cloze";
export const targetLanguage = (q: Question): string => (q.reverse ? "Polish" : "English");

export interface AnswerResult {
  correct: boolean; skipped: boolean; expected: string;
  exact: boolean;               // false when accepted only after forgiving accents / a typo
  damage_dealt: number; damage_taken: number; message: string; state: string; word: string;
  cleared_from_missed: boolean; free: boolean; timed_out: boolean;
}
const result = (r: Partial<AnswerResult> & Pick<AnswerResult, "correct" | "skipped" | "expected" | "exact" | "damage_dealt" | "damage_taken" | "message" | "state">): AnswerResult =>
  ({ word: "", cleared_from_missed: false, free: false, timed_out: false, ...r });

export class Battle {
  question: Question | null = null;
  questions_asked = 0;
  consecutive_wrong = 0;
  // set by the manager from equipment / items
  ward = false;               // the next monster hit is absorbed
  phoenix = false;            // survive one lethal hit
  time_bonus = 0;             // extra seconds on timed questions
  xp_mult = 1.0;
  coin_mult = 1.0;
  cloze_source: ((wordId: number) => [string, string, string] | null) | null = null;
  companion = "";
  heal_on_correct = 0;
  bonus_damage = 0;
  dodge_pct = 0;
  rng: Rng;

  constructor(public player: Player, public monster: Monster, public selector: VocabularySelector, rng?: Rng) {
    this.rng = rng ?? selector.rng;
  }

  get state(): string {
    if (!this.player.is_alive) return DEFEAT;
    if (!this.monster.is_alive) return VICTORY;
    return ACTIVE;
  }
  get missed(): MissedWords { return this.selector.missed; }

  /** A card for the next question; a boss falls back to the normal weights if its own find nothing. */
  private pick(): number | null {
    let id = this.selector.pick(this.weights());
    if (id === null && this.monster.spec.boss) id = this.selector.pick(undefined);
    return id;
  }

  private weights() { return this.monster.spec.boss ? config.BOSS_LEVEL_WEIGHTS : undefined; }

  /** Start a new question; null if the fight is over or the deck has no usable card. */
  next_question(): Question | null {
    if (this.state !== ACTIVE) return null;
    const spec = this.monster.spec;
    const limit = spec.time_limit ? spec.time_limit + this.time_bonus : 0;
    let wordId: number | null = null;
    if (this.cloze_source && this.rng() < spec.cloze_chance) {
      for (let n = 0; n < 30; n++) {              // look for a card with a usable sentence
        wordId = this.pick();
        const found = wordId !== null ? this.cloze_source(wordId) : null;
        if (found) {
          const [blanked, answer, english] = found;
          const card = this.selector.deck.words[wordId!];
          this.question = newQuestion(wordId!, blanked, answer, true, limit, { kind: "cloze", gloss: card.translation, context: english });
          this.questions_asked += 1;
          return this.question;
        }
        if (wordId === null) break;
      }
    }
    if (wordId === null) wordId = this.pick();
    if (wordId === null) return null;
    const card = this.selector.deck.words[wordId];
    const reverse = this.rng() < spec.reverse_chance;
    this.question = reverse
      ? newQuestion(wordId, card.translation, card.word, true, limit)
      : newQuestion(wordId, card.word, card.translation, false, limit);
    this.questions_asked += 1;
    return this.question;
  }

  /** Everything currently revealed about the answer. */
  hint_text(): string {
    const q = this.requireQuestion();
    const card = this.selector.deck.words[q.word_id];
    const main = primary(q.answer, q.reverse);
    const parts = main.split(/\s+/).filter(Boolean);
    const lines = [`${parts.length} word${parts.length !== 1 ? "s" : ""}`];
    if (q.show_first) lines.push(`Starts with “${main.slice(0, 1)}”`);
    if (q.show_count) lines.push(`${parts.map((w) => w.length).join(" + ")} letters`);
    if (isCloze(q)) {
      if (q.context) lines.push(q.context);
      return lines.join("\n");
    }
    const sentence = (q.reverse ? card.sentence_translation : card.sentence).trim();
    if (sentence) lines.push(sentence);
    return lines.join("\n");
  }

  /** Item hint: reveals letters without any damage penalty. */
  reveal(first = false, count = false): string {
    const q = this.requireQuestion();
    q.show_first = q.show_first || first;
    q.show_count = q.show_count || count;
    return this.hint_text();
  }

  submit(text: string): AnswerResult {
    const q = this.requireQuestion();
    const [correct, exact] = check(text, q.answer, q.reverse);
    return correct ? this.playerHits(q, exact) : this.monsterHits(q, "wrong", text);
  }

  /** Give up on the question: counts as wrong, but the monster hits half as hard. */
  skip(): AnswerResult { return this.monsterHits(this.requireQuestion(), "skip"); }
  /** The time ran out: a wrong answer. */
  timeout(): AnswerResult { return this.monsterHits(this.requireQuestion(), "timeout"); }

  /** Skip scroll: reveal the answer and move on with no penalty at all. */
  free_skip(): AnswerResult {
    const q = this.requireQuestion();
    const word = this.selector.deck.words[q.word_id].word;
    this.question = null;
    return result({ correct: false, skipped: true, expected: q.answer, exact: false, damage_dealt: 0, damage_taken: 0,
      message: `You read the scroll. "${q.prompt}" is "${q.answer}".`, state: this.state, word, free: true });
  }

  private requireQuestion(): Question {
    if (this.state !== ACTIVE || this.question === null) throw new GameError("no active question");
    return this.question;
  }

  private vary(base: number): number {
    const spread = config.DAMAGE_SPREAD;
    return Math.max(1, pyRound(base * (1 + uniform(this.rng, -spread, spread))));
  }

  private healMonster(amount: number): number {
    const gained = Math.max(0, Math.min(amount, this.monster.max_hp - this.monster.hp));
    this.monster.hp += gained;
    return gained;
  }

  private playerHits(q: Question, exact: boolean): AnswerResult {
    const base = this.player.attack_power;
    const amount = Math.max(1, this.vary(base) - this.monster.spec.armor) + this.bonus_damage;
    const dealt = this.monster.take_damage(amount);
    const word = this.selector.deck.words[q.word_id].word;
    const cleared = this.missed.correct(word);
    this.consecutive_wrong = 0;
    this.question = null;
    let message = `Correct! You dealt ${dealt} damage.`;
    if (!exact) message += ` (Spelling: "${primary(q.answer, q.reverse)}")`;
    if (this.heal_on_correct) {
      const healed = this.player.heal(this.heal_on_correct);
      if (healed) message += ` ${this.companion} heals you for ${healed} HP.`;
    }
    if (!this.monster.is_alive) message += ` The ${this.monster.name} is defeated!`;
    return result({ correct: true, skipped: false, expected: q.answer, exact, damage_dealt: dealt, damage_taken: 0, message,
      state: this.state, word, cleared_from_missed: cleared });
  }

  private monsterDamage(mode: string): number {
    const spec = this.monster.spec;
    let base = spec.damage;
    if (mode === "skip") base *= config.SKIP_DAMAGE_FACTOR;
    if (spec.enrage && this.monster.hp <= this.monster.max_hp * config.ENRAGE_HP_FRACTION) base *= config.ENRAGE_FACTOR;
    if (spec.combo) {
      const stacks = Math.min(config.COMBO_MAX_STACKS, this.consecutive_wrong);
      base *= 1 + config.COMBO_STEP * stacks;
    }
    return base;
  }

  private monsterHits(q: Question, mode: string, given = ""): AnswerResult {
    const spec = this.monster.spec;
    const base = this.monsterDamage(mode);
    const hit = base >= 3 ? [-1, 0, 1][choiceIndex(this.rng, 3)] : 0;
    const cap = Math.max(1, pyInt(this.player.max_hp * config.MAX_HIT_FRACTION));
    let amount = Math.max(1, Math.min(cap, Math.max(1, pyRound(base) + hit) - this.player.gear_reduction));
    const notes: string[] = [];
    if (this.ward) {
      this.ward = false;
      amount = 0;
      notes.push("Your ward absorbs the blow!");
    } else if (this.dodge_pct && this.rng() * 100 < this.dodge_pct) {
      amount = 0;
      notes.push(`${this.companion} helps you dodge!`);
    }
    const taken = this.player.take_damage(amount);
    if (!this.player.is_alive && this.phoenix) {
      this.phoenix = false;
      this.player.hp = Math.max(1, pyRound(this.player.max_hp * config.PHOENIX_REVIVE_FRACTION));
      notes.push("The Phoenix Feather burns and you rise again!");
    }
    if (spec.lifesteal && taken > 0) {
      const healed = this.healMonster(pyRound(taken * config.LIFESTEAL_FRACTION));
      if (healed) notes.push(`The ${this.monster.name} drains ${healed} HP.`);
    }
    if (spec.regen) {
      const healed = this.healMonster(spec.regen);
      if (healed) notes.push(`The ${this.monster.name} regenerates ${healed} HP.`);
    }
    this.consecutive_wrong += 1;

    const word = this.selector.deck.words[q.word_id].word;
    this.missed.miss(word);
    this.question = null;
    const lead = ({ skip: "Skipped!", timeout: "Time's up!" } as Record<string, string>)[mode] ?? "Incorrect!";
    const meaning = isCloze(q) ? `The missing word was "${q.answer}".`
      : q.reverse ? `"${q.prompt}" in Polish is "${q.answer}".` : `"${q.prompt}" means "${q.answer}".`;
    let message = `${lead} ${meaning} `;
    if (given.trim()) message += `You answered "${given.trim()}". `;
    message += taken ? `The ${this.monster.name} attacks you for ${taken} damage.` : `The ${this.monster.name} attacks, but misses you.`;
    if (notes.length) message += " " + notes.join(" ");
    if (!this.player.is_alive) message += " You have fallen...";
    return result({ correct: false, skipped: mode === "skip", expected: q.answer, exact: false, damage_dealt: 0, damage_taken: taken,
      message, state: this.state, word, timed_out: mode === "timeout" });
  }
}
export { Monster };
