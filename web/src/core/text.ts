// Text helpers: ports of the helpers in flashcards.py (accent stripping, normalising, folding).

export function stripAccents(text: string): string {
  text = text.replace(/ł/g, "l").replace(/Ł/g, "L");
  return text.normalize("NFD").replace(/\p{Mn}/gu, "");
}

const splitWs = (s: string): string[] => s.split(/\s+/).filter(Boolean);

export function normalise(text: string): string {
  text = text.toLowerCase().replace(/’/g, "'");
  text = text.replace(/[?!.,;:…"„”]/g, " ");
  return splitWs(text).join(" ");
}

/** Lower-case and accent-free, for searching. */
export function fold(text: string): string {
  return splitWs(stripAccents(text.toLowerCase())).join(" ");
}

/** Remove "(optional parts)" like Python's re.sub(r"\s*\([^)]*\)", "", s). */
export function dropBrackets(text: string): string {
  return text.replace(/\s*\([^)]*\)/g, "");
}

export type Rng = () => number;

export function shuffle<T>(arr: T[], rng: Rng = Math.random): T[] {
  for (let i = arr.length - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1));
    [arr[i], arr[j]] = [arr[j], arr[i]];
  }
  return arr;
}

/** random.sample: k distinct items, in random order. */
export function sample<T>(arr: T[], k: number, rng: Rng = Math.random): T[] {
  return shuffle(arr.slice(), rng).slice(0, k);
}
