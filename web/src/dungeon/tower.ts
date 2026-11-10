// The Endless Tower: floors are generated from the floor number, so it never ends.
import data from "./data.json";
import * as config from "./config";
import type { MonsterSpec } from "./config";
import { TOWER_BUNDLES, TOWER_LOOT } from "./items";
import { BOSS, MONSTER, REST, makeRoom, type Room } from "./models";
import { pyRound } from "./util";

const T = data.tower;
export const isBossFloor = (floor: number): boolean => floor % 10 === 0;

/** The item [key, count] the boss of this floor drops. */
export function lootFor(floor: number): [string, number] {
  const n = Math.floor(floor / 10);
  if (n <= TOWER_LOOT.length) return [TOWER_LOOT[n - 1], 1];
  return TOWER_BUNDLES[(n - TOWER_LOOT.length - 1) % TOWER_BUNDLES.length];
}

/** Extra abilities of a Tower monster: one rotating ability from the ability floor (two later); bosses always crush. */
function specialAbilities(floor: number, base: MonsterSpec): Partial<MonsterSpec> {
  const extra: Record<string, number | boolean> = {};
  let keys: string[] = [];
  if (isBossFloor(floor)) keys = ["percent_damage", Math.floor(floor / 10) % 2 ? "unavoidable" : "curse"];
  else if (floor >= T.ability_from_floor) {
    const n = Math.floor(floor / 5);
    keys = [T.ability_rotation[n % T.ability_rotation.length]];
    if (floor >= T.second_ability_from_floor) keys.push(T.ability_rotation[(n + 3) % T.ability_rotation.length]);
  }
  for (const key of keys) {
    if ((base as unknown as Record<string, unknown>)[key]) continue;
    if (key === "percent_damage") extra[key] = Math.min(0.12, 0.05 + 0.002 * floor + (isBossFloor(floor) ? 0.02 : 0));
    else if (key === "poison") extra[key] = Math.max(2, pyRound(base.damage * (1 + T.damage_growth * (floor - 1)) * 0.3));
    else if (key === "streak") extra[key] = floor >= 60 ? 3 : 2;
    else if (key === "thief") extra[key] = 5 + Math.floor(floor / 2);
    else extra[key] = true;
  }
  return extra as Partial<MonsterSpec>;
}

/** The monster of a floor, scaled to its depth. */
export function monsterFor(floor: number): MonsterSpec {
  let base: MonsterSpec;
  if (isBossFloor(floor)) base = config.MONSTERS[T.boss_order[(Math.floor(floor / 10) - 1) % T.boss_order.length]];
  else {
    let index = Math.floor((floor - 1) / 2);
    if (index >= T.monster_order.length) index = T.monster_order.length - 5 + (floor % 5);  // past the roster: keep rotating the strongest
    base = config.MONSTERS[T.monster_order[index]];
  }
  const depth = floor - 1;
  const cycle = isBossFloor(floor) ? Math.floor((Math.floor(floor / 10) - 1) / T.boss_order.length) : 0;
  const boost = 1 + 0.4 * cycle;      // a repeated boss comes back stronger
  const extra: Partial<MonsterSpec> = {};
  if (floor >= T.cloze_from_floor && !base.cloze_chance) extra.cloze_chance = 0.3;
  if (floor >= T.enrage_from_floor) extra.enrage = true;
  if (floor >= 2 * T.enrage_from_floor) extra.armor = base.armor + 2;
  Object.assign(extra, specialAbilities(floor, base));
  return {
    ...base,
    max_hp: pyRound(base.max_hp * (1 + T.hp_growth * depth) * boost),
    damage: pyRound(base.damage * (1 + T.damage_growth * depth) * boost),
    xp: pyRound(base.xp * (1 + T.xp_growth * depth)),
    coins: pyRound(base.coins * (1 + T.coin_growth * depth)),
    ...extra,
  };
}

/** The room for floor `index + 1`. */
export function floorRoom(index: number): Room {
  const floor = index + 1;
  if (floor % 5 === 0 && !isBossFloor(floor)) return makeRoom({ kind: REST, title: `Floor ${floor}: Resting Place`, heal_fraction: 0.5 });
  const spec = monsterFor(floor);
  if (isBossFloor(floor)) {
    const [drop, count] = lootFor(floor);
    return makeRoom({ kind: BOSS, title: `Floor ${floor}: ${spec.name}`, monster: spec.key, spec, drop, drop_count: count });
  }
  return makeRoom({ kind: MONSTER, title: `Floor ${floor}`, monster: spec.key, spec });
}
