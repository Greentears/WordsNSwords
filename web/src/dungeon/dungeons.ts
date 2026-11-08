// Dungeon definitions (data from data.json; the tower builds its floors in code).
import data from "./data.json";
import { makeRoom, type Dungeon, type Room } from "./models";
import { floorRoom } from "./tower";

export const DUNGEON_LIST: Dungeon[] = data.dungeons.map((d) => ({
  key: d.key, name: d.name, description: d.description,
  rooms: d.rooms.map((r) => makeRoom(r as unknown as Room)),
  min_level: d.min_level, complete_xp: d.complete_xp, complete_coins: d.complete_coins, kind: d.kind,
  reward_scale: d.reward_scale, hp_scale: d.hp_scale, damage_scale: d.damage_scale,
  room_factory: d.endless ? floorRoom : null,
}));
/** In map-screen order. */
export const DUNGEONS: Record<string, Dungeon> = Object.fromEntries(DUNGEON_LIST.map((d) => [d.key, d]));
