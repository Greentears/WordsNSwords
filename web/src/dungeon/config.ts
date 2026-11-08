// All balance numbers and monster stats, loaded from data.json (made by tools/export_dungeon_data.py).
import data from "./data.json";

export interface MonsterSpec {
  key: string; name: string; max_hp: number; damage: number; xp: number; coins: number; boss: boolean;
  reverse_chance: number; armor: number; regen: number; enrage: boolean; lifesteal: boolean; combo: boolean;
  time_limit: number; cloze_chance: number;
}

const k = data.constants;
export const DEFAULT_PLAYER_NAME: string = data.default_player_name;
export const BASE_MAX_HP = k.BASE_MAX_HP, LEVEL_HP_GAIN = k.LEVEL_HP_GAIN, LEVEL_UP_HEAL_FRACTION = k.LEVEL_UP_HEAL_FRACTION;
export const BASE_PLAYER_DAMAGE = k.BASE_PLAYER_DAMAGE, PLAYER_DAMAGE_PER_LEVEL = k.PLAYER_DAMAGE_PER_LEVEL, DAMAGE_SPREAD = k.DAMAGE_SPREAD;
export const MAX_HIT_FRACTION = k.MAX_HIT_FRACTION, SKIP_DAMAGE_FACTOR = k.SKIP_DAMAGE_FACTOR;
export const MISSED_WEIGHT_BONUS = k.MISSED_WEIGHT_BONUS, RECENT_WINDOW = k.RECENT_WINDOW, MISSED_CLEAR_STREAK = k.MISSED_CLEAR_STREAK;
export const ROOM_CLEAR_COINS = k.ROOM_CLEAR_COINS, DUNGEON_COMPLETE_XP = k.DUNGEON_COMPLETE_XP, DUNGEON_COMPLETE_COINS = k.DUNGEON_COMPLETE_COINS;
export const ENRAGE_HP_FRACTION = k.ENRAGE_HP_FRACTION, ENRAGE_FACTOR = k.ENRAGE_FACTOR, COMBO_STEP = k.COMBO_STEP, COMBO_MAX_STACKS = k.COMBO_MAX_STACKS;
export const LIFESTEAL_FRACTION = k.LIFESTEAL_FRACTION, PHOENIX_REVIVE_FRACTION = k.PHOENIX_REVIVE_FRACTION;
export const SELL_FRACTION = k.SELL_FRACTION, MAX_ITEM_STACK = k.MAX_ITEM_STACK;
export const REVIEW_MIN_WORDS = k.REVIEW_MIN_WORDS, REVIEW_MAX_WORDS = k.REVIEW_MAX_WORDS;

export type Weights = Map<number | null, number>;
export const LEVEL_WEIGHTS: Weights = new Map(data.level_weights as unknown as [number | null, number][]);
export const BOSS_LEVEL_WEIGHTS: Weights = new Map(data.boss_level_weights as unknown as [number | null, number][]);

/** XP needed to go from `level` to `level + 1`. */
export const xpToNext = (level: number): number => 40 + 20 * (Math.max(1, level) - 1);

export const MONSTERS: Record<string, MonsterSpec> = Object.fromEntries((data.monsters as MonsterSpec[]).map((m) => [m.key, m]));

/** Short texts under a monster describing its abilities. */
export function abilities(s: MonsterSpec): string[] {
  const out: string[] = [];
  if (s.reverse_chance) out.push(s.reverse_chance < 0.5 ? "Sometimes asks for the Polish word" : "Often asks for the Polish word");
  if (s.armor) out.push(`Armored: your hits do ${s.armor} less`);
  if (s.regen) out.push(`Regenerates ${s.regen} HP when you err`);
  if (s.enrage) out.push("Enrages below half HP");
  if (s.lifesteal) out.push("Heals when it hits you");
  if (s.combo) out.push("Hits harder after repeated mistakes");
  if (s.time_limit) out.push(`Impatient: ${s.time_limit}s per word`);
  if (s.cloze_chance) out.push("Speaks in sentences: fill in the blank");
  return out;
}
