// Plain data: Player, Monster, Room, Dungeon.
import * as config from "./config";
import type { MonsterSpec } from "./config";
import { clampInt, isDict, pyRound } from "./util";
import * as statRules from "./stats";

export class Player {
  name = config.DEFAULT_PLAYER_NAME;
  level = 1;
  xp = 0;                    // XP collected towards the next level
  hp = config.BASE_MAX_HP;
  max_hp = config.BASE_MAX_HP;
  coins = 0;
  gear_hp = 0;               // part of max_hp that comes from equipment
  gear_attack = 0;           // set from equipment (not saved)
  gear_reduction = 0;
  stat_hp = 0;               // part of max_hp that comes from Constitution
  stats: statRules.Stats = statRules.emptyStats();
  stat_points = 0;           // points not spent yet
  respecs = 0;               // how many times the points were reset

  get xp_needed(): number { return config.xpToNext(this.level); }
  get is_alive(): boolean { return this.hp > 0; }
  get effects(): statRules.Effects { return statRules.effects(this.stats); }
  get attack_power(): number {
    const raw = config.BASE_PLAYER_DAMAGE + config.PLAYER_DAMAGE_PER_LEVEL * (this.level - 1) + this.gear_attack;
    return pyRound((raw * (100 + this.effects.attack_pct)) / 100);
  }

  /** Lose up to `amount` HP; returns the HP actually lost. */
  take_damage(amount: number): number {
    const lost = Math.max(0, Math.min(amount, this.hp));
    this.hp -= lost;
    return lost;
  }

  heal(amount: number): number {
    const gained = Math.max(0, Math.min(amount, this.max_hp - this.hp));
    this.hp += gained;
    return gained;
  }

  /** Add XP, levelling up as often as needed; returns the levels gained. */
  add_xp(amount: number): number {
    this.xp += Math.max(0, amount);
    let gained = 0;
    while (this.xp >= this.xp_needed) {
      this.xp -= this.xp_needed;
      this.level += 1;
      this.stat_points += statRules.POINTS_PER_LEVEL;
      this.max_hp += config.LEVEL_HP_GAIN;
      this.heal(pyRound(this.max_hp * config.LEVEL_UP_HEAL_FRACTION));
      gained += 1;
    }
    return gained;
  }

  to_dict() {
    return { name: this.name, level: this.level, xp: this.xp, hp: this.hp, max_hp: this.max_hp, coins: this.coins, gear_hp: this.gear_hp, stat_hp: this.stat_hp, stats: { ...this.stats }, stat_points: this.stat_points, respecs: this.respecs };
  }

  /** Build a player from saved data; bad or missing values fall back to defaults. */
  static from_dict(data: unknown): Player {
    const d = isDict(data) ? data : {};
    const p = new Player();
    const max_hp = clampInt(d.max_hp, config.BASE_MAX_HP, 1);
    p.name = typeof d.name === "string" && d.name.trim() ? d.name.trim() : config.DEFAULT_PLAYER_NAME;
    p.level = clampInt(d.level, 1, 1, 999);
    p.xp = clampInt(d.xp, 0);
    p.hp = clampInt(d.hp, max_hp, 0, max_hp);
    p.max_hp = max_hp;
    p.coins = clampInt(d.coins, 0);
    p.gear_hp = clampInt(d.gear_hp, 0, 0, Math.max(0, max_hp - 1));
    p.stat_hp = clampInt(d.stat_hp, 0, 0, Math.max(0, max_hp - 1));
    p.stats = statRules.cleanStats(d.stats);
    p.respecs = clampInt(d.respecs, 0);
    // a save from before stats: every level already reached gives its points
    p.stat_points = "stat_points" in d ? clampInt(d.stat_points, 0) : statRules.POINTS_PER_LEVEL * (p.level - 1);
    p.xp = Math.min(p.xp, p.xp_needed - 1);
    return p;
  }
}

export class Monster {
  constructor(public spec: MonsterSpec, public hp: number) {}
  static spawn(spec: MonsterSpec, hp: number | null = null): Monster {
    return new Monster(spec, hp === null ? spec.max_hp : Math.max(1, Math.min(hp, spec.max_hp)));
  }
  get max_hp(): number { return this.spec.max_hp; }
  get name(): string { return this.spec.name; }
  get is_alive(): boolean { return this.hp > 0; }
  take_damage(amount: number): number {
    const lost = Math.max(0, Math.min(amount, this.hp));
    this.hp -= lost;
    return lost;
  }
}

export const MONSTER = "monster", BOSS = "boss", TREASURE = "treasure", REST = "rest";

export interface Room {
  kind: string; title: string; monster: string | null; coins: number; xp: number; heal_fraction: number;
  spec: MonsterSpec | null;     // a one-off monster (the tower), else `monster`
  drop: string | null; drop_count: number;
}
export const makeRoom = (r: Partial<Room> & Pick<Room, "kind" | "title">): Room => ({
  monster: null, coins: 0, xp: 0, heal_fraction: 0, spec: null, drop: null, drop_count: 1, ...r,
});
export const isFight = (r: Room): boolean => r.kind === MONSTER || r.kind === BOSS;

export interface Dungeon {
  key: string; name: string; description: string; rooms: Room[]; min_level: number;
  complete_xp: number; complete_coins: number; kind: string;       // "story", "review" or "tower"
  reward_scale: number; hp_scale: number; damage_scale: number;
  room_factory: ((index: number) => Room) | null;                 // endless dungeons build rooms on demand
}
export const dungeonEndless = (d: Dungeon): boolean => d.room_factory !== null;
export const dungeonRoomCount = (d: Dungeon): number | null => (d.room_factory ? null : d.rooms.length);
export const dungeonRoom = (d: Dungeon, index: number): Room | null =>
  d.room_factory ? d.room_factory(index) : index >= 0 && index < d.rooms.length ? d.rooms[index] : null;
