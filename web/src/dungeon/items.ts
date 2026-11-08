// The shop catalogue (data from data.json).
import data from "./data.json";

export const CONSUMABLE = "consumable", EQUIPMENT = "equipment";
export const WEAPON = "weapon", ARMOR = "armor", CHARM = "charm", COMPANION = "companion";
export const SLOTS = [WEAPON, ARMOR, CHARM, COMPANION];
export const HEAL = "heal", HEAL_FULL = "heal_full", DAMAGE = "damage";
export const FIRST_LETTER = "first_letter", LETTER_COUNT = "letter_count", FULL_HINT = "full_hint";
export const WARD = "ward", FREE_SKIP = "free_skip", XP_BOOST = "xp_boost", COIN_BOOST = "coin_boost";

export interface Item {
  key: string; name: string; description: string; price: number; kind: string; level: number;
  slot: string | null; effect: string | null; value: number;
  hp: number; attack: number; reduction: number; xp_pct: number; coin_pct: number; time: number; phoenix: boolean;
  heal_on_correct: number; bonus_damage: number; dodge_pct: number; start_ward: boolean;
  shop: boolean; icon: string;
}

export const ITEM_LIST: Item[] = data.items as Item[];
export const ITEMS: Record<string, Item> = Object.fromEntries(ITEM_LIST.map((i) => [i.key, i]));
export const isEquipment = (i: Item): boolean => i.kind === EQUIPMENT;
export const REMOVED_EQUIPMENT: Record<string, number> = data.removed_equipment;
export const TOWER_LOOT: string[] = data.tower.loot;
export const TOWER_BUNDLES: [string, number][] = data.tower.bundles as [string, number][];
