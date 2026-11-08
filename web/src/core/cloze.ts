// Fill-in-the-blank: exact port of flashcards.blank_sentence.
import { dropBrackets, stripAccents } from "./text";
import type { Word } from "./deck";

export const BLANK = "_____";
const TOKEN_SRC = "[\\p{L}\\p{Nl}\\p{No}]+(?:-[\\p{L}\\p{Nl}\\p{No}]+)*";
const tokenRe = () => new RegExp(TOKEN_SRC, "gu");

function tokenMatch(token: string, target: string, fuzzy: boolean): boolean {
  token = token.toLowerCase();
  target = target.toLowerCase();
  if (token === target) return true;
  if (!fuzzy || Array.from(target).length < 5 || Array.from(token).length < 4) return false;
  const a = Array.from(stripAccents(token));
  const b = Array.from(stripAccents(target));
  let common = 0;
  for (let i = 0; i < Math.min(a.length, b.length); i++) {
    if (a[i] !== b[i]) break;
    common++;
  }
  return common >= Math.max(4, Array.from(target).length - 3);
}

const partsOf = (s: string): string[] => (s.match(tokenRe()) ?? []).map((p) => p.toLowerCase());

/** [sentence with blanks, accepted answers joined by " / "], or null when the word isn't found. */
export function blankSentence(
  word: Pick<Word, "word" | "sentence">,
  extraForms?: string[] | null,
  sentence?: string | null,
): [string, string] | null {
  const text = sentence == null ? word.sentence : sentence;
  if (!text) return null;
  const tokens = [...text.matchAll(tokenRe())].map((m) => ({ s: m[0], start: m.index!, end: m.index! + m[0].length }));
  const variants: [string[], boolean][] = [];
  for (let variant of word.word.split(" / ")) {
    variant = dropBrackets(variant).replace(/\.\.\./g, " ");
    const parts = partsOf(variant);
    if (parts.length) variants.push([parts, true]);
  }
  for (const form of extraForms ?? []) {
    for (const alt of form.split(" / ")) {
      const parts = partsOf(alt);
      if (parts.length) variants.push([parts, false]);
    }
  }
  const seen = new Set<string>();
  const spans: [number, number][] = [];
  for (const [parts, fuzzy] of variants) {
    for (let i = 0; i + parts.length <= tokens.length; i++) {
      let ok = true;
      for (let j = 0; j < parts.length; j++) {
        if (!tokenMatch(tokens[i + j].s, parts[j], fuzzy)) { ok = false; break; }
      }
      if (ok) {
        const key = `${i},${i + parts.length - 1}`;
        if (!seen.has(key)) { seen.add(key); spans.push([i, i + parts.length - 1]); }
      }
    }
  }
  spans.sort((x, y) => x[0] - y[0] || (y[1] - y[0]) - (x[1] - x[0]));
  const chosen: [number, number][] = [];
  for (const span of spans) {
    if (!chosen.length || span[0] > chosen[chosen.length - 1][1]) chosen.push(span);
  }
  if (!chosen.length) return null;
  const out: string[] = [];
  const answers: string[] = [];
  let pos = 0;
  for (const [first, last] of chosen) {
    const start = tokens[first].start;
    const end = tokens[last].end;
    out.push(text.slice(pos, start), BLANK);
    const piece = text.slice(start, end);
    if (!answers.some((a) => a.toLowerCase() === piece.toLowerCase())) answers.push(piece);
    pos = end;
  }
  out.push(text.slice(pos));
  return [out.join(""), answers.join(" / ")];
}
