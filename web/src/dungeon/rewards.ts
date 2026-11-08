// XP, coins and healing handed out for fights, treasure, rest and completion.
import * as config from "./config";
import type { MonsterSpec } from "./config";
import type { Player, Room } from "./models";
import { isDict, isInt, pyRound } from "./util";

export const STAT_KEYS = ["monsters_defeated", "correct_answers", "wrong_answers", "xp_earned", "coins_earned",
  "rooms_cleared", "dungeons_completed", "deaths", "hints_used", "skips", "items_used", "items_bought", "coins_spent",
  "words_cleared", "items_sold"];
export const RUN_KEYS = ["xp", "coins", "monsters", "correct", "wrong", "rooms", "cleared"];

/** A counter object with exactly `keys`; anything invalid in `data` becomes 0. */
export function cleanCounters(data: unknown, keys: string[]): Record<string, number> {
  const d = isDict(data) ? data : {};
  const out: Record<string, number> = {};
  for (const key of keys) {
    const v = d[key];
    out[key] = isInt(v) && v >= 0 ? v : 0;
  }
  return out;
}

export interface Reward { xp: number; coins: number; healed: number; levels_gained: number; messages: string[] }
const newReward = (xp = 0, coins = 0): Reward => ({ xp, coins, healed: 0, levels_gained: 0, messages: [] });

export class RewardManager {
  constructor(public player: Player, public stats: Record<string, number>, public run: Record<string, number>) {}

  private grant(xp = 0, coins = 0): Reward {
    const reward = newReward(xp, coins);
    this.player.coins += coins;
    reward.levels_gained = this.player.add_xp(xp);
    this.stats.xp_earned += xp;
    this.stats.coins_earned += coins;
    this.run.xp += xp;
    this.run.coins += coins;
    if (xp) reward.messages.push(`+${xp} XP`);
    if (coins) reward.messages.push(`+${coins} coins`);
    if (reward.levels_gained) {
      reward.messages.push(`Level up! You are now level ${this.player.level} (max HP ${this.player.max_hp}, fully healed).`);
    }
    return reward;
  }

  monster_defeated(spec: MonsterSpec, xp_mult = 1.0, coin_mult = 1.0): Reward {
    this.stats.monsters_defeated += 1;
    this.run.monsters += 1;
    return this.grant(pyRound(spec.xp * xp_mult), pyRound((spec.coins + config.ROOM_CLEAR_COINS) * coin_mult));
  }

  treasure(room: Room): Reward {
    const reward = this.grant(room.xp, room.coins);
    reward.messages.unshift("You open the chest.");
    return reward;
  }

  rest(room: Room): Reward {
    const healed = this.player.heal(pyRound(this.player.max_hp * room.heal_fraction));
    const reward = newReward();
    reward.healed = healed;
    reward.messages.push(`You rest and recover ${healed} HP.`);
    return reward;
  }

  dungeon_completed(xp = config.DUNGEON_COMPLETE_XP, coins = config.DUNGEON_COMPLETE_COINS): Reward {
    this.stats.dungeons_completed += 1;
    const reward = this.grant(xp, coins);
    reward.messages.unshift("Dungeon completed!");
    return reward;
  }

  /** Coins found outside a fight (e.g. selling a duplicate drop). */
  bonus_coins(coins: number): void { this.grant(0, coins); }

  room_cleared(): void {
    this.stats.rooms_cleared += 1;
    this.run.rooms += 1;
  }
}
