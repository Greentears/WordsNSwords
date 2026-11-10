// Hero stats: points, and what each stat does. Same rules as desktop/dungeon/stats.py (checked by the golden tests).
//
// Flat effects (damage, HP, item power, coins) grow without a limit. Effects that stop making sense past a
// point (dodge, discounts, sell price, extra XP) approach a limit with diminishing returns:
//   bounded(points, limit, k) = limit * points / (points + k)
import { isDict } from "./util";

export const STAT_KEYS = ["strength", "constitution", "dexterity", "intelligence", "charisma", "wisdom"] as const;
export type StatKey = (typeof STAT_KEYS)[number];
export type Stats = Record<StatKey, number>;
export const STAT_NAMES: Record<StatKey, string> = {
  strength: "Strength", constitution: "Constitution", dexterity: "Dexterity",
  intelligence: "Intelligence", charisma: "Charisma", wisdom: "Wisdom",
};
export const DESCRIPTIONS: Record<StatKey, string> = {
  strength: "More damage; high Strength also ignores monster armor.",
  constitution: "More max HP, and you recover some HP after every victory.",
  dexterity: "A chance to dodge hits, and more time on timed questions.",
  intelligence: "Healing and damage items are stronger.",
  charisma: "More coins from fights, cheaper shop prices, better sell prices.",
  wisdom: "Extra XP when you answer words you are still learning.",
};

export const POINTS_PER_LEVEL = 2;
export const STRENGTH_ATTACK_PCT = 2.5, STRENGTH_PIERCE_EVERY = 5;
export const CONSTITUTION_HP = 5, CONSTITUTION_VICTORY_HEAL_PCT = 1.0, CONSTITUTION_VICTORY_HEAL_MAX = 50.0;
export const DEXTERITY_DODGE_LIMIT = 35.0, DEXTERITY_DODGE_K = 35.0, DEXTERITY_TIME_EVERY = 3;
export const INTELLIGENCE_ITEM_PCT = 3.0;
export const CHARISMA_COIN_PCT = 1.5;
export const CHARISMA_DISCOUNT_LIMIT = 25.0, CHARISMA_DISCOUNT_K = 25.0;
export const CHARISMA_SELL_LIMIT = 20.0, CHARISMA_SELL_K = 25.0;
export const WISDOM_XP_LIMIT = 50.0, WISDOM_XP_K = 17.0;
export const DODGE_TOTAL_LIMIT = 35.0;
export const RESPEC_BASE_COST = 50, RESPEC_COST_PER_LEVEL = 10;

/** The first respec is free; later ones cost coins that grow with the level. */
export const respecCost = (level: number, respecs: number): number => (respecs <= 0 ? 0 : RESPEC_BASE_COST + RESPEC_COST_PER_LEVEL * level);
export const bounded = (points: number, limit: number, k: number): number => (points > 0 ? (limit * points) / (points + k) : 0.0);

export interface Effects {
  attack_pct: number; armor_ignore: number; hp: number; victory_heal_pct: number; dodge_pct: number; time_bonus: number;
  item_pct: number; coin_pct: number; discount_pct: number; sell_bonus_pct: number; wisdom_xp_pct: number;
}

export const emptyStats = (): Stats => ({ strength: 0, constitution: 0, dexterity: 0, intelligence: 0, charisma: 0, wisdom: 0 });

/** A stats object with exactly the six keys; anything invalid becomes 0. */
export function cleanStats(data: unknown): Stats {
  const d = isDict(data) ? data : {};
  const out = emptyStats();
  for (const key of STAT_KEYS) {
    const v = d[key];
    out[key] = typeof v === "number" && Number.isInteger(v) && v >= 0 && v <= 1_000_000 ? v : 0;
  }
  return out;
}

export function effects(stats: Partial<Stats>): Effects {
  const s = { ...emptyStats(), ...stats };
  return {
    attack_pct: STRENGTH_ATTACK_PCT * s.strength,
    armor_ignore: Math.floor(s.strength / STRENGTH_PIERCE_EVERY),
    hp: CONSTITUTION_HP * s.constitution,
    victory_heal_pct: Math.min(CONSTITUTION_VICTORY_HEAL_MAX, CONSTITUTION_VICTORY_HEAL_PCT * s.constitution),
    dodge_pct: bounded(s.dexterity, DEXTERITY_DODGE_LIMIT, DEXTERITY_DODGE_K),
    time_bonus: Math.floor(s.dexterity / DEXTERITY_TIME_EVERY),
    item_pct: INTELLIGENCE_ITEM_PCT * s.intelligence,
    coin_pct: CHARISMA_COIN_PCT * s.charisma,
    discount_pct: bounded(s.charisma, CHARISMA_DISCOUNT_LIMIT, CHARISMA_DISCOUNT_K),
    sell_bonus_pct: bounded(s.charisma, CHARISMA_SELL_LIMIT, CHARISMA_SELL_K),
    wisdom_xp_pct: bounded(s.wisdom, WISDOM_XP_LIMIT, WISDOM_XP_K),
  };
}

/** 12.5 -> "12.5", 10 -> "10" (one decimal at most). */
const num = (x: number): string => { const t = x.toFixed(1); return t.endsWith(".0") ? t.slice(0, -2) : t; };

/** What the points in `stat` give right now, e.g. "+12.5% damage · ignores 2 armor". */
export function effectText(stat: StatKey, stats: Partial<Stats>, sellFraction = 0.6): string {
  const fx = effects(stats);
  switch (stat) {
    case "strength": return `+${num(fx.attack_pct)}% damage` + (fx.armor_ignore ? ` · ignores ${fx.armor_ignore} armor` : "");
    case "constitution": return `+${fx.hp} max HP · ${num(fx.victory_heal_pct)}% HP back after a win`;
    case "dexterity": return `${num(fx.dodge_pct)}% dodge · +${fx.time_bonus}s on timed words`;
    case "intelligence": return `+${num(fx.item_pct)}% item power`;
    case "charisma": return `+${num(fx.coin_pct)}% coins · -${num(fx.discount_pct)}% shop prices · sells for ${num(sellFraction * 100 + fx.sell_bonus_pct)}%`;
    case "wisdom": return `+${num(fx.wisdom_xp_pct)}% XP on words you are still learning`;
  }
}
