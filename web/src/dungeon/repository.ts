// Game state persistence (the schema is the same as the desktop dungeon_progress.json).
import { isDict } from "./util";

export const SCHEMA_VERSION = 2;

export interface GameState {
  version: number; player: unknown; dungeons: unknown; run: unknown; stats: unknown; missed: unknown;
  inventory: unknown; fight: unknown;
}

export function defaultState(): GameState {
  return { version: SCHEMA_VERSION, player: {}, dungeons: {}, run: {}, stats: {}, missed: {}, inventory: {}, fight: null };
}

/** Saved data merged over the defaults; a fresh state when nothing usable exists. */
export function mergeState(data: unknown): GameState {
  const state = defaultState() as unknown as Record<string, unknown>;
  if (isDict(data)) for (const key of Object.keys(state)) if (key in data) state[key] = data[key];
  return state as unknown as GameState;
}

/** Where the game keeps its save. The app stores it in IndexedDB; tests keep it in memory. */
export interface Repository {
  /** The raw saved object, or null when there is none. */
  load(): unknown;
  save(state: GameState): void;
}

export class MemoryRepository implements Repository {
  constructor(public data: unknown = null) {}
  load(): unknown { return this.data; }
  save(state: GameState): void { this.data = JSON.parse(JSON.stringify(state)); }
}
