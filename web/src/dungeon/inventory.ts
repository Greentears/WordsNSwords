// What the player owns: one-time items, equipment and what is equipped.
import * as config from "./config";
import { COMPANION, CONSUMABLE, EQUIPMENT, ITEMS, REMOVED_EQUIPMENT, SLOTS, isEquipment, type Item } from "./items";
import type { Player } from "./models";
import { GameError, isDict, isInt } from "./util";

export interface GearTotals {
  hp: number; attack: number; reduction: number; xp_pct: number; coin_pct: number; time: number; phoenix: boolean;
  heal_on_correct: number; bonus_damage: number; dodge_pct: number; start_ward: boolean; companion: string;
}

export class Inventory {
  counts: Record<string, number> = {};
  owned = new Set<string>();
  equipped: Record<string, string> = {};
  refund = 0;     // coins owed for equipment that no longer exists

  constructor(data: unknown = null) {
    const d = isDict(data) ? data : {};
    const counts = d.items;
    if (isDict(counts)) {
      for (const [key, n] of Object.entries(counts)) {
        const item = Object.hasOwn(ITEMS, key) ? ITEMS[key] : undefined;
        if (item && item.kind === CONSUMABLE && isInt(n) && n > 0) this.counts[key] = Math.min(n, config.MAX_ITEM_STACK);
      }
    }
    const owned = d.owned;
    if (Array.isArray(owned)) {
      for (const key of owned) {
        if (typeof key === "string" && Object.hasOwn(REMOVED_EQUIPMENT, key)) this.refund += REMOVED_EQUIPMENT[key];
        if (typeof key === "string" && Object.hasOwn(ITEMS, key) && ITEMS[key].kind === EQUIPMENT) this.owned.add(key);
      }
    }
    const equipped = d.equipped;
    if (isDict(equipped)) {
      for (const [slot, key] of Object.entries(equipped)) {
        if (SLOTS.includes(slot) && typeof key === "string" && this.owned.has(key) && ITEMS[key].slot === slot) this.equipped[slot] = key;
      }
    }
  }

  to_dict() {
    return { items: { ...this.counts }, owned: [...this.owned].sort(), equipped: { ...this.equipped } };
  }

  count(key: string): number { return this.counts[key] ?? 0; }
  has(key: string): boolean { return this.owned.has(key); }
  is_equipped(key: string): boolean { return this.equipped[ITEMS[key].slot ?? ""] === key; }

  totals(): GearTotals {
    const t: GearTotals = { hp: 0, attack: 0, reduction: 0, xp_pct: 0, coin_pct: 0, time: 0, phoenix: false,
      heal_on_correct: 0, bonus_damage: 0, dodge_pct: 0, start_ward: false, companion: "" };
    for (const key of Object.values(this.equipped)) {
      const i = ITEMS[key];
      t.hp += i.hp; t.attack += i.attack; t.reduction += i.reduction; t.xp_pct += i.xp_pct; t.coin_pct += i.coin_pct;
      t.time += i.time; t.phoenix = t.phoenix || i.phoenix; t.heal_on_correct += i.heal_on_correct;
      t.bonus_damage += i.bonus_damage; t.dodge_pct += i.dodge_pct; t.start_ward = t.start_ward || i.start_ward;
      if (i.slot === COMPANION) t.companion = i.name;
    }
    return t;
  }

  /** Why the player cannot buy `item` right now (null = they can). */
  buy_problem(item: Item, player: Player): string | null {
    if (isEquipment(item) && this.owned.has(item.key)) return "Already owned";
    if (!item.shop) return "Not for sale";
    if (!isEquipment(item) && this.count(item.key) >= config.MAX_ITEM_STACK) return "You can't carry more";
    if (player.level < item.level) return `Requires level ${item.level}`;
    if (player.coins < item.price) return "Not enough coins";
    return null;
  }

  buy(item: Item, player: Player): void {
    const problem = this.buy_problem(item, player);
    if (problem) throw new GameError(problem);
    player.coins -= item.price;
    if (isEquipment(item)) {
      this.owned.add(item.key);
      if (!(item.slot! in this.equipped)) this.equipped[item.slot!] = item.key;   // first piece in a slot is worn at once
    } else this.counts[item.key] = this.count(item.key) + 1;
  }

  sell_value(item: Item): number { return Math.trunc(item.price * config.SELL_FRACTION); }

  sell_problem(item: Item): string | null {
    if (isEquipment(item)) return this.owned.has(item.key) ? null : "You don't own that";
    return this.count(item.key) > 0 ? null : "You have none left";
  }

  /** Sell one item for SELL_FRACTION of its price; returns the coins received. */
  sell(item: Item, player: Player): number {
    const problem = this.sell_problem(item);
    if (problem) throw new GameError(problem);
    if (isEquipment(item)) {
      this.owned.delete(item.key);
      if (this.equipped[item.slot!] === item.key) delete this.equipped[item.slot!];
    } else this.consume(item.key);
    const coins = this.sell_value(item);
    player.coins += coins;
    return coins;
  }

  /** Add an item found as loot (no coins involved). */
  give(key: string, count = 1): void {
    const item = ITEMS[key];
    if (isEquipment(item)) {
      this.owned.add(key);
      if (!(item.slot! in this.equipped)) this.equipped[item.slot!] = key;
    } else this.counts[key] = Math.min(config.MAX_ITEM_STACK, this.count(key) + count);
  }

  equip(key: string): void {
    if (!this.owned.has(key)) throw new GameError("You don't own that");
    this.equipped[ITEMS[key].slot!] = key;
  }

  unequip(slot: string): void { delete this.equipped[slot]; }

  consume(key: string): void {
    if (this.count(key) <= 0) throw new GameError("You have none left");
    this.counts[key] -= 1;
    if (this.counts[key] <= 0) delete this.counts[key];
  }
}
