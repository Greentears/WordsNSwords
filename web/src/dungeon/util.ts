// Helpers that reproduce Python behaviour the rules rely on.

/** Random source: a function returning [0, 1). Everything else is built on it (see `rng.ts`). */
export type Rng = () => number;

/** Python's round(): halves go to the even neighbour (JavaScript's Math.round rounds them up). */
export function pyRound(x: number): number {
  const f = Math.floor(x);
  const d = x - f;
  if (d < 0.5) return f;
  if (d > 0.5) return f + 1;
  return f % 2 === 0 ? f : f + 1;
}

/** Python's int() on a float: truncation towards zero. */
export const pyInt = (x: number): number => Math.trunc(x);

export class GameError extends Error {
  constructor(message: string) { super(message); this.name = "GameError"; }
}

export const isDict = (x: unknown): x is Record<string, unknown> => typeof x === "object" && x !== null && !Array.isArray(x);
/** A real integer (not a boolean, not a float), like `isinstance(x, int) and not isinstance(x, bool)`. */
export const isInt = (x: unknown): x is number => typeof x === "number" && Number.isInteger(x);

/** `value` as an integer clamped to [low, high]; `dflt` for anything that isn't a number. */
export function clampInt(value: unknown, dflt: number, low = 0, high = 1e9): number {
  if (typeof value !== "number" || !Number.isFinite(value)) return dflt;
  return Math.max(low, Math.min(high, Math.trunc(value)));
}

// ---- random helpers, all built on one random() so a recorded stream can be replayed -------------
export const uniform = (rng: Rng, a: number, b: number): number => a + (b - a) * rng();
export const choiceIndex = (rng: Rng, n: number): number => Math.trunc(rng() * n);

/** random.choices(population, weights)[0] as an index (Python: bisect on the cumulative weights). */
export function weightedIndex(rng: Rng, weights: number[]): number {
  const cum: number[] = [];
  let sum = 0;
  for (const w of weights) { sum += w; cum.push(sum); }
  const x = rng() * (cum[cum.length - 1] + 0.0);
  let lo = 0, hi = cum.length - 1;
  while (lo < hi) {
    const mid = (lo + hi) >> 1;
    if (x < cum[mid]) hi = mid; else lo = mid + 1;
  }
  return lo;
}

export function shuffleInPlace<T>(x: T[], rng: Rng): void {
  for (let i = x.length - 1; i >= 1; i--) {
    const j = Math.trunc(rng() * (i + 1));
    [x[i], x[j]] = [x[j], x[i]];
  }
}
