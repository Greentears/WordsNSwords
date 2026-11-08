// Forgiving answer checking for the dungeon (both directions): exact port of dungeon/answers.py.
import { stripAccents } from "../core/text";

const SOFT_MODIFIERS = new Set(["little", "small", "big", "large", "great", "very", "really", "quite", "some",
  "certain", "the", "a", "an", "my", "your", "his", "her", "our", "their", "one's", "someone's", "somebody's", "something"]);
const ARTICLES = ["a", "an", "the"];
const AUXILIARIES = new Set(["is", "are", "am", "was", "were"]);
const MIN_TYPO_LENGTH = 6;

const words = (s: string): string[] => s.split(/\s+/).filter(Boolean);

function norm(text: string): string {
  return words(text.toLowerCase().replace(/’/g, "'").replace(/-/g, " ").replace(/[?!.,;:…"„”]/g, " ")).join(" ");
}

/** The card side as token lists, one per alternative (notes in brackets dropped, or kept as words). */
function alternatives(expected: string, keepBrackets = false): string[][] {
  const text = keepBrackets ? expected.replace(/[()]/g, " ") : expected.replace(/\([^)]*\)/g, " ");
  const out: string[][] = [];
  for (const part of text.split(/\s*\/\s*/)) {
    const tokens = words(norm(part));
    if (tokens.length) out.push(tokens);
  }
  return out;
}

/** Shorter spellings of one alternative that should also be accepted. */
function variants(tokens: string[], reverse: boolean): string[][] {
  const result = [tokens];
  if (reverse) {   // Polish: reflexive "się" may be left out
    const trimmed = tokens.filter((t) => t !== "się");
    if (trimmed.length && trimmed.length !== tokens.length) result.push(trimmed);
    return result;
  }
  let work = tokens;
  while (work.length > 1 && AUXILIARIES.has(work[0])) { work = work.slice(1); result.push(work); }
  if (work[0] === "to" && work[1] === "be" && work.length > 2) { work = work.slice(2); result.push(work); }
  else if ((work[0] === "to" || work[0] === "be") && work.length > 1) { work = work.slice(1); result.push(work); }
  while (work.length > 1 && SOFT_MODIFIERS.has(work[0])) { work = work.slice(1); result.push(work); }
  return result;
}

/** Every normalised string that counts as a correct answer for `expected`. */
export function acceptedForms(expected: string, reverse = false): Set<string> {
  const alts = alternatives(expected);
  const bases = [...alts];
  if (expected.includes("(")) bases.push(...alternatives(expected, true));
  if (alts.length > 1) {
    const first = alts[0];
    for (const alt of alts.slice(1)) {
      if (first.length > 1) bases.push([...first.slice(0, -1), ...alt]);        // "can I try" + "taste it"
      else if (alt.length > first.length) bases.push([first[0], ...alt.slice(1)]); // "run" + "operated by" -> "run by"
    }
  }
  const forms = new Set<string>();
  for (const tokens of bases) {
    for (const v of variants(tokens, reverse)) {
      const text = v.join(" ");
      if (text && !ARTICLES.includes(text)) forms.add(text);
    }
  }
  return forms;
}

/** The main spelling of a card side (first alternative, no notes, no leading "to "). */
export function primary(expected: string, reverse = false): string {
  const alts = alternatives(expected);
  if (!alts.length) return expected.trim();
  let tokens = alts[0];
  if (!reverse && tokens[0] === "to" && tokens.length > 1) tokens = tokens.slice(1);
  return tokens.join(" ");
}

function distanceAtMostOne(a: string, b: string): boolean {
  if (a === b) return true;
  if (Math.abs(a.length - b.length) > 1) return false;
  if (a.length === b.length) {
    const diffs: number[] = [];
    for (let i = 0; i < a.length; i++) if (a[i] !== b[i]) diffs.push(i);
    if (diffs.length === 1) return true;
    return diffs.length === 2 && diffs[1] === diffs[0] + 1 && a[diffs[0]] === b[diffs[1]] && a[diffs[1]] === b[diffs[0]];
  }
  const [short, long] = a.length < b.length ? [a, b] : [b, a];
  let i = 0;
  while (i < short.length && short[i] === long[i]) i++;
  return short.slice(i) === long.slice(i + 1);
}

/** A crude English stem so that lack / lacks / lacking / lacked match. */
function stem(token: string): string {
  for (const suffix of ["ing", "ed", "es", "s"]) {
    if (token.endsWith(suffix) && token.length > suffix.length + 2) { token = token.slice(0, -suffix.length); break; }
  }
  if (token.length > 3 && token[token.length - 1] === token[token.length - 2] && !"aeiouls".includes(token[token.length - 1])) token = token.slice(0, -1);
  return token.length > 3 && token.endsWith("e") ? token.slice(0, -1) : token;
}
const stems = (text: string): string => words(text).map(stem).join(" ");

/** [correct, exact]. `exact` is false when accents or a small typo were forgiven. */
export function check(given: string, expected: string, reverse = false): [boolean, boolean] {
  if (given.includes("/")) {   // the whole card text typed with its slashes: every part must fit
    const parts = given.split(/\s*\/\s*/).filter((p) => norm(p));
    if (parts.length > 1) {
      const results = parts.map((p) => check(p, expected, reverse));
      if (results.every(([ok]) => ok)) return [true, results.every(([, exact]) => exact)];
    }
  }
  const typed = norm(given.replace(/\//g, " "));
  if (!typed) return [false, false];
  const guesses = new Set([typed]);
  const unbracketed = norm(given.replace(/\//g, " ").replace(/\([^)]*\)/g, " "));
  if (unbracketed) guesses.add(unbracketed);
  const w = typed.split(" ");
  if (!reverse && w.length > 1) {
    for (const lead of [ARTICLES, ["to"]]) if (lead.includes(w[0])) guesses.add(w.slice(1).join(" "));
    if (w[0] === "to" && w[1] === "be" && w.length > 2) guesses.add(w.slice(2).join(" "));
  }
  const forms = acceptedForms(expected, reverse);
  for (const g of guesses) if (forms.has(g)) return [true, true];
  const folded = new Set([...forms].map(stripAccents));
  for (const g of guesses) if (folded.has(stripAccents(g))) return [true, false];
  if (!reverse) {   // same word in another verb form: lack / lacking
    const stemmed = new Set([...forms].map(stems));
    for (const g of guesses) if (stemmed.has(stems(g))) return [true, false];
  }
  for (const g of guesses) {
    const gf = stripAccents(g);
    for (const f of folded) if (f.length >= MIN_TYPO_LENGTH && distanceAtMostOne(gf, f)) return [true, false];
  }
  return [false, false];
}
