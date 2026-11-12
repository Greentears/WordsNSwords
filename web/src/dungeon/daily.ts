// The Daily Challenge: one short dungeon per day, the same for everybody. Port of dungeon/daily.py.
// The date decides everything through a tiny random generator that matches the desktop one exactly.
import data from "./data.json";
import * as config from "./config";
import type { MonsterSpec } from "./config";
import { BOSS, MONSTER, REST, makeRoom, type Dungeon, type Room } from "./models";
import { scaleMonster } from "./tower";
import { pyRound } from "./util";

const D = data.daily;
const T = data.tower;
export const DAILY_KEY = "daily";
export const DAILY_MIN_LEVEL = D.min_level;
export const DAILY_MAX_TIER = D.max_tier;

/** FNV-1a over the UTF-8 bytes of `text`. */
export function hash32(text: string): number {
  let h = 2166136261;
  for (const byte of new TextEncoder().encode(text)) h = Math.imul(h ^ byte, 16777619) >>> 0;
  return h;
}

/** mulberry32. */
export class DailyRng {
  private a: number;
  constructor(seed: number) { this.a = seed >>> 0; }
  next(): number {
    this.a = (this.a + 0x6d2b79f5) >>> 0;
    let t = this.a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  }
  below(n: number): number { return Math.floor(this.next() * n); }
}

export const tierFor = (level: number): number => Math.max(2, Math.min(D.max_tier, level + D.tier_bonus));

export function yesterday(day: string): string {
  const d = new Date(day + "T00:00:00Z");
  d.setUTCDate(d.getUTCDate() - 1);
  return d.toISOString().slice(0, 10);
}

export const streakBonus = (streak: number): number => Math.min(D.streak_max, D.streak_step * Math.max(0, streak - 1));

/** [key, name, what it does] */
export function twistFor(day: string): [string, string, string] {
  return D.twists[new DailyRng(hash32("twist:" + day)).below(D.twists.length)] as [string, string, string];
}

function twisted(spec: MonsterSpec, twist: string): MonsterSpec {
  if (twist === "glass") return { ...spec, max_hp: Math.max(1, pyRound(spec.max_hp * 0.7)), damage: Math.max(1, pyRound(spec.damage * 1.35)) };
  if (twist === "iron") return { ...spec, armor: spec.armor + 2 };
  if (twist === "fury") return { ...spec, enrage: true };
  if (twist === "mirror") return { ...spec, reverse_chance: Math.max(spec.reverse_chance, 0.5) };
  if (twist === "sentences") return { ...spec, cloze_chance: Math.max(spec.cloze_chance, 0.5) };
  return spec;
}

/** Today's dungeon: fight, fight, rest, fight, fight, boss. */
export function buildDaily(day: string, tier: number): Dungeon {
  const rng = new DailyRng(hash32("rooms:" + day));
  const tw = twistFor(day);
  const pool = T.monster_order.slice(0, Math.min(T.monster_order.length, Math.floor((tier - 1) / 2) + 3));
  const names = [...D.room_names];
  const rooms: Room[] = [];
  let fights = 0;
  for (let slot = 0; slot < 6; slot++) {
    if (slot === 2) { rooms.push(makeRoom({ kind: REST, title: "A Quiet Corner", heal_fraction: 0.4 })); continue; }
    const boss = slot === 5;
    const base = boss
      ? config.MONSTERS[T.boss_order[rng.below(Math.min(T.boss_order.length, 1 + Math.floor(tier / 10)))]]
      : config.MONSTERS[pool[rng.below(pool.length)]];
    const spec = twisted(scaleMonster(base, tier + fights + (boss ? 2 : 0), boss), tw[0]);
    const title = boss ? D.boss_names[rng.below(D.boss_names.length)] : names.splice(rng.below(names.length), 1)[0];
    rooms.push(makeRoom({ kind: boss ? BOSS : MONSTER, title, monster: spec.key, spec }));
    fights++;
  }
  const bossSpec = rooms[rooms.length - 1].spec as MonsterSpec;
  return {
    key: DAILY_KEY, name: "Daily Challenge", kind: "daily", min_level: D.min_level,
    description: `Today's twist: ${tw[1]}. ${tw[2]}`, rooms,
    complete_xp: bossSpec.xp, complete_coins: pyRound(bossSpec.coins * 1.5),
    reward_scale: tw[0] === "feast" ? 1.5 : 1.0, hp_scale: 1.0, damage_scale: 1.0, room_factory: null,
  };
}
