// GameManager: the single entry point the interface talks to. Port of dungeon/manager.py.
// It owns the player, inventory, dungeon progress and the current fight, saves after every action
// and never modifies the vocabulary deck.
import * as config from "./config";
import * as items from "./items";
import { ACTIVE, DEFEAT, VICTORY, Battle, type AnswerResult, type Question } from "./battle";
import { ClozeSource } from "./cloze";
import { DAILY_KEY, DAILY_MAX_TIER, buildDaily, streakBonus, tierFor, yesterday } from "./daily";
import { DUNGEONS } from "./dungeons";
import { Inventory } from "./inventory";
import { ITEMS, ITEM_LIST, isEquipment, type Item } from "./items";
import { Monster, Player, TREASURE, dungeonEndless, dungeonRoom, dungeonRoomCount, isFight, type Dungeon, type Room } from "./models";
import { SCHEMA_VERSION, mergeState, type Repository } from "./repository";
import { RUN_KEYS, STAT_KEYS, RewardManager, cleanCounters, type Reward } from "./rewards";
import { MissedWords, VocabularySelector, type DeckLike } from "./selector";
import type { Example } from "../core/tables";
import * as statRules from "./stats";
import { GameError, isDict, isInt, pyRound, type Rng } from "./util";

export interface DungeonStatus {
  key: string; name: string; description: string;
  room: number;             // index of the next room to play
  total_rooms: number; completed: boolean; times: number; in_progress: boolean;
  min_level: number; locked: boolean; kind: string; endless: boolean;
  best: number;             // tower: highest floor cleared
  unavailable: string | null;  // why it can't be entered right now (null = open)
  note: string;                // daily challenge: your streak
}

export interface RoomOutcome {
  kind: string; title: string; reward: Reward; dungeon_completed: boolean; final_reward: Reward | null;
  run: Record<string, number>;   // totals, for the completion screen
  loot: string | null;           // a boss drop, e.g. "Loot: Sword of the Tower!"
}
/** All messages of an outcome, in the order the desktop shows them. */
export function outcomeMessages(o: RoomOutcome): string[] {
  const msgs = [...o.reward.messages];
  if (o.loot) msgs.push(o.loot);
  if (o.final_reward) msgs.push(...o.final_reward.messages);
  return msgs;
}

export interface ShopEntry { item: Item; count: number; owned: boolean; equipped: boolean; problem: string | null; price: number }
export interface SellEntry { item: Item; count: number; value: number; equipped: boolean }
export interface ItemUse { ok: boolean; message: string; state: string; hint: string | null; result: AnswerResult | null }
const itemUse = (ok: boolean, message: string): ItemUse => ({ ok, message, state: ACTIVE, hint: null, result: null });

interface Progress {
  room: number; completed: boolean; times: number; best: number;
  date?: string; last_done?: string; tier?: number; streak?: number; best_streak?: number;    // daily challenge only
}
interface SavedFight { dungeon: unknown; room: unknown; monster_hp: unknown }

export class GameManager {
  player: Player;
  inventory: Inventory;
  stats: Record<string, number>;
  run: Record<string, number>;
  missed: MissedWords;
  selector: VocabularySelector;
  cloze: ClozeSource;
  rewards: RewardManager;
  progress: Record<string, Progress> = {};
  /** The dungeons of today (the daily one changes with the date). */
  defs: Record<string, Dungeon> = {};
  /** The language being learned, for texts (the interface sets it). */
  language = "Polish";
  private today: () => string;
  dungeon: Dungeon | null = null;
  battle: Battle | null = null;
  outcome: RoomOutcome | null = null;
  saved_fight: SavedFight | null;
  /** Review fight: card word -> meaning, in order of the first miss. */
  review_failed = new Map<string, string>();

  constructor(public deck: DeckLike, examples: Record<string, Example[]>, public repo: Repository, public rng: Rng,
    today?: () => string) {
    this.today = today ?? (() => { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`; });
    const state = mergeState(repo.load()) as unknown as Record<string, unknown>;
    this.player = Player.from_dict(state.player);
    this.inventory = new Inventory(state.inventory);
    this.stats = cleanCounters(state.stats, STAT_KEYS);
    this.run = cleanCounters(state.run, RUN_KEYS);
    this.missed = new MissedWords(state.missed);
    this.selector = new VocabularySelector(deck, this.missed, rng);
    this.cloze = new ClozeSource(deck, examples, rng);
    this.rewards = new RewardManager(this.player, this.stats, this.run);
    if (this.inventory.refund) {          // equipment that was removed from the game
      this.player.coins += this.inventory.refund;
      this.inventory.refund = 0;
    }
    this.progress[DAILY_KEY] = GameManager.cleanProgress(state.dungeons, DAILY_KEY, 6);
    for (const [key, dungeon] of Object.entries(DUNGEONS)) {
      this.progress[key] = GameManager.cleanProgress(state.dungeons, key, dungeonRoomCount(dungeon));
    }
    this.saved_fight = isDict(state.fight) ? (state.fight as unknown as SavedFight) : null;
    this.refreshDaily();
    this.applyGear();
    if (!this.player.is_alive) {          // saved while dead: come back healthy, fight restarts
      this.player.hp = this.player.max_hp;
      this.saved_fight = null;
    }
  }

  // -- loading helpers ---------------------------------------------------------------------------
  private static cleanProgress(saved: unknown, key: string, rooms: number | null): Progress {
    const entry = isDict(saved) && isDict(saved[key]) ? (saved[key] as Record<string, unknown>) : {};
    const count = (name: string, high: number) => {
      const v = entry[name];
      return isInt(v) ? Math.max(0, Math.min(high, v)) : 0;
    };
    const out: Progress = { room: count("room", rooms === null ? 1e6 : rooms), completed: entry.completed === true,
      times: count("times", 1e6), best: count("best", 1e6) };
    if (key === DAILY_KEY) {
      const day = (name: string): string => {
        const v = entry[name];
        return typeof v === "string" && /^\d{4}-\d{2}-\d{2}$/.test(v) && !Number.isNaN(Date.parse(v)) ? v : "";
      };
      Object.assign(out, { date: day("date"), last_done: day("last_done"), tier: count("tier", DAILY_MAX_TIER),
        streak: count("streak", 1e6), best_streak: count("best_streak", 1e6) });
    }
    return out;
  }

  /** Make the daily challenge the one of today's date (a new day starts a fresh run). */
  private refreshDaily(): void {
    const today = this.today();
    const p = this.progress[DAILY_KEY];
    if (p.date !== today) {
      Object.assign(p, { date: today, room: 0, completed: false, tier: 0 });
      if (this.saved_fight && this.saved_fight.dungeon === DAILY_KEY) this.saved_fight = null;
    }
    if ((p.room === 0 && !p.completed) || !p.tier) p.tier = tierFor(this.player.level);   // the strength is fixed once the run starts
    const built = buildDaily(today, p.tier as number);
    this.defs = { [DAILY_KEY]: built, ...DUNGEONS };
    if (this.dungeon && this.dungeon.key === DAILY_KEY) this.dungeon = built;
  }

  /** Days in a row the challenge was finished, counting up to yesterday or today (0 once it is broken). */
  dailyStreak(): number {
    const p = this.progress[DAILY_KEY];
    const today = this.today();
    return p.last_done === today || p.last_done === yesterday(today) ? (p.streak as number) : 0;
  }

  private dailyNote(): string {
    const streak = this.dailyStreak();
    const bonus = !this.progress[DAILY_KEY].completed ? pyRound(streakBonus(streak + 1) * 100) : 0;
    return `Streak: ${streak} day${streak !== 1 ? "s" : ""}` + (bonus ? ` (today's reward +${bonus}%)` : "");
  }

  /** Count today's win in the streak; returns the streak's extra share of the reward. */
  private finishDaily(p: Progress): number {
    const today = this.today();
    p.streak = p.last_done === yesterday(today) ? (p.streak as number) + 1 : 1;
    p.best_streak = Math.max(p.best_streak as number, p.streak);
    p.last_done = today;
    return streakBonus(p.streak);
  }

  /** Bring the player's stats in line with what is equipped. */
  private applyGear(): void {
    const t = this.inventory.totals();
    const p = this.player;
    const delta = t.hp - p.gear_hp;
    p.max_hp = Math.max(1, p.max_hp + delta);
    p.gear_hp = t.hp;
    if (delta > 0 && p.is_alive) p.hp += delta;
    p.hp = Math.min(p.hp, p.max_hp);
    p.gear_attack = t.attack;
    p.gear_reduction = t.reduction;
    const extra = p.effects.hp - p.stat_hp;      // Constitution works like gear HP
    p.max_hp = Math.max(1, p.max_hp + extra);
    p.stat_hp = p.effects.hp;
    if (extra > 0 && p.is_alive) p.hp += extra;
    p.hp = Math.min(p.hp, p.max_hp);
  }

  // -- queries ----------------------------------------------------------------------------------
  get missed_count(): number { return this.missed.size; }
  get has_words(): boolean { return this.selector.candidates().length > 0; }

  /** Why a dungeon can't be entered right now (null = it can). */
  unavailable_reason(key: string): string | null {
    this.refreshDaily();
    const d = this.defs[key];
    if (this.player.level < d.min_level) return `Requires level ${d.min_level}`;
    const p = this.progress[key];
    if (d.kind === "daily" && p.completed) return "Done today. Come back tomorrow!";
    const inProgress = 0 < p.room && p.room < (dungeonRoomCount(d) ?? 0);
    if (d.kind === "review" && !this.missed.size && !inProgress) return "No missed words to review";
    return null;
  }

  dungeons(): DungeonStatus[] {
    this.refreshDaily();
    return Object.entries(this.defs).map(([key, d]) => {
      const p = this.progress[key];
      const count = dungeonRoomCount(d);
      const started = p.room > 0 && (count === null || p.room < count);
      return { key, name: d.name, description: d.description, room: p.room, total_rooms: count ?? 0, completed: p.completed,
        times: p.times, in_progress: started, min_level: d.min_level, locked: this.player.level < d.min_level, kind: d.kind,
        endless: dungeonEndless(d), best: p.best, unavailable: this.unavailable_reason(key),
        note: d.kind === "daily" ? this.dailyNote() : "" };
    });
  }

  /** The next room to play in the selected dungeon; null when it is finished. */
  current_room(): Room | null {
    if (this.dungeon === null) return null;
    return dungeonRoom(this.dungeon, this.progress[this.dungeon.key].room);
  }
  get room_index(): number { return this.dungeon ? this.progress[this.dungeon.key].room : 0; }

  // -- dungeon selection ------------------------------------------------------------------------
  /** Choose a dungeon. A finished dungeon (or `restart`) starts again from room 1. */
  select_dungeon(key: string, restart = false): void {
    const reason = this.unavailable_reason(key);
    const dungeon = this.defs[key];
    if (reason) throw new GameError(`${dungeon.name}: ${reason}`);
    const p = this.progress[key];
    const count = dungeonRoomCount(dungeon);
    if (restart || (count !== null && p.room >= count)) {
      p.room = 0;
      this.run = cleanCounters({}, RUN_KEYS);
      this.rewards.run = this.run;
      this.saved_fight = null;
      this.review_failed = new Map();
    } else if (this.saved_fight && this.saved_fight.dungeon !== key) this.saved_fight = null;
    if (dungeon.kind === "review" && !this.saved_fight) this.review_failed = new Map();   // a fresh review
    this.dungeon = dungeon;
    this.selector.only_missed = dungeon.kind === "review";
    this.battle = null;
    this.outcome = null;
    this.save();
  }

  // -- rooms ------------------------------------------------------------------------------------
  /** Enter the current room. Fight rooms start (or resume) a battle and return null; treasure and rest resolve at once. */
  enter_room(): RoomOutcome | null {
    const room = this.current_room();
    if (room === null) throw new GameError("no room to enter");
    this.outcome = null;
    if (isFight(room)) {
      this.battle = this.newBattle(room);
      return null;
    }
    this.battle = null;
    const reward = room.kind === TREASURE ? this.rewards.treasure(room) : this.rewards.rest(room);
    return this.roomCleared(room, reward);
  }

  private newBattle(room: Room, fresh = false): Battle {
    let spec = room.spec ?? config.MONSTERS[room.monster as string];
    const d = this.dungeon!;
    if (d.hp_scale !== 1.0 || d.damage_scale !== 1.0) {
      spec = { ...spec, max_hp: Math.max(1, pyRound(spec.max_hp * d.hp_scale)), damage: Math.max(1, pyRound(spec.damage * d.damage_scale)) };
    }
    if (d.kind === "review") spec = { ...spec, max_hp: this.reviewHp() };
    let hp: number | null = null;
    const fight = this.saved_fight;
    this.saved_fight = null;
    this.outcome = null;
    if (!this.player.is_alive) {   // came back after a defeat: heal, fresh monster
      this.player.hp = this.player.max_hp;
      fresh = true;
    }
    if (!fresh && fight && fight.dungeon === d.key && fight.room === this.room_index && isInt(fight.monster_hp)) hp = fight.monster_hp;
    const battle = new Battle(this.player, Monster.spawn(spec, hp), this.selector, this.rng);
    battle.language = this.language;
    const gear = this.inventory.totals();
    battle.phoenix = gear.phoenix;
    battle.time_bonus = gear.time + this.player.effects.time_bonus;
    battle.cloze_source = (id) => this.cloze.call(id);
    battle.ward = gear.start_ward;
    battle.companion = gear.companion;
    battle.heal_on_correct = gear.heal_on_correct;
    battle.bonus_damage = gear.bonus_damage;
    battle.dodge_pct = gear.dodge_pct;
    return battle;
  }

  private needBattle(): Battle {
    if (!this.battle) throw new GameError("no fight in progress");
    return this.battle;
  }

  next_question(): Question | null { return this.battle ? this.battle.next_question() : null; }
  answer(text: string): AnswerResult { return this.afterAnswer(this.needBattle().submit(text)); }
  skip(): AnswerResult {
    this.stats.skips += 1;
    return this.afterAnswer(this.needBattle().skip());
  }
  /** The question's time limit ran out. */
  timeout(): AnswerResult { return this.afterAnswer(this.needBattle().timeout()); }

  private meaning(word: string): string {
    return this.deck.words.find((w) => w.word === word)?.translation ?? "";
  }

  /** Every word failed during the current review, as [Polish, English], first miss first. */
  get review_failed_words(): [string, string][] { return [...this.review_failed.entries()]; }

  /** HP of the Review Guru: about one correct answer per missed word (5 to 10 of them). */
  private reviewHp(): number {
    const words = Math.min(config.REVIEW_MAX_WORDS, Math.max(config.REVIEW_MIN_WORDS, this.missed.size));
    const perHit = this.player.attack_power + this.inventory.totals().bonus_damage;
    return Math.max(1, perHit * words);
  }

  private afterAnswer(result: AnswerResult): AnswerResult {
    if (result.free) { /* neither right nor wrong */ }
    else if (result.correct) { this.stats.correct_answers += 1; this.run.correct += 1; }
    else {
      this.stats.wrong_answers += 1; this.run.wrong += 1;
      if (this.dungeon !== null && this.dungeon.kind === "review" && result.word && !this.review_failed.has(result.word)) {
        this.review_failed.set(result.word, this.meaning(result.word));
      }
    }
    if (result.cleared_from_missed) { this.stats.words_cleared += 1; this.run.cleared += 1; }
    if (result.state === DEFEAT) this.stats.deaths += 1;
    this.finishIfWon();
    this.save();
    return result;
  }

  /** Pay out the monster's rewards once, the moment it is dead. */
  private finishIfWon(): void {
    if (this.battle === null || this.battle.state !== VICTORY || this.outcome !== null) return;
    const gear = this.inventory.totals();
    const d = this.dungeon!;
    const fx = this.player.effects;
    const b = this.battle;
    let wisdom = 0.0;       // extra XP for answers on words you are still learning (not in the replayable review)
    if (d.kind !== "review" && b.correct_count) wisdom = (fx.wisdom_xp_pct * b.hard_correct) / b.correct_count;
    const reward = this.rewards.monster_defeated(
      b.monster.spec,
      (1 + (gear.xp_pct + wisdom) / 100) * b.xp_mult * d.reward_scale,
      (1 + (gear.coin_pct + fx.coin_pct) / 100) * b.coin_mult * d.reward_scale,
    );
    if (b.stolen) {
      this.player.coins += b.stolen;
      reward.messages.push(`You take back the ${b.stolen} stolen coins.`);
    }
    if (fx.victory_heal_pct) {
      const healed = this.player.heal(pyRound((this.player.max_hp * fx.victory_heal_pct) / 100));
      if (healed) reward.messages.push(`You recover ${healed} HP.`);
    }
    this.outcome = this.roomCleared(this.current_room()!, reward);
  }

  private roomCleared(room: Room, reward: Reward): RoomOutcome {
    const d = this.dungeon!;
    const p = this.progress[d.key];
    this.rewards.room_cleared();
    p.room += 1;
    this.saved_fight = null;
    const outcome: RoomOutcome = { kind: room.kind, title: room.title, reward, dungeon_completed: false, final_reward: null, run: {}, loot: null };
    if (dungeonEndless(d)) p.best = Math.max(p.best, p.room);
    if (room.drop) outcome.loot = this.giveLoot(room);
    const count = dungeonRoomCount(d);
    if (count !== null && p.room >= count) {
      p.completed = true;
      p.times += 1;
      outcome.dungeon_completed = true;
      const share = d.kind === "daily" ? 1 + this.finishDaily(p) : 1;
      outcome.final_reward = this.rewards.dungeon_completed(pyRound(d.complete_xp * d.reward_scale * share), pyRound(d.complete_coins * d.reward_scale * share));
      if (d.kind === "daily") {
        const streak = p.streak as number;
        outcome.final_reward.messages.push(`Daily streak: ${streak} day${streak !== 1 ? "s" : ""}` + (share > 1 ? ` (+${pyRound((share - 1) * 100)}% reward)` : ""));
      }
      outcome.run = { ...this.run };
    }
    this.save();
    return outcome;
  }

  /** Hand over a boss drop. Gear you already own is sold at the normal sell price. */
  private giveLoot(room: Room): string {
    const item = ITEMS[room.drop as string];
    if (isEquipment(item) && this.inventory.has(item.key)) {
      const coins = this.inventory.sell_value(item, this.sell_fraction);
      this.rewards.bonus_coins(coins);
      return `Loot: ${item.name} (you already own it: sold for ${coins} coins)`;
    }
    this.inventory.give(item.key, room.drop_count);
    this.applyGear();
    const times = room.drop_count > 1 ? ` x${room.drop_count}` : "";
    return `Loot: ${item.name}${times}!`;
  }

  /** After a defeat: heal fully and face the same room again with a fresh monster. */
  retry(): void {
    if (this.battle === null || this.battle.state !== DEFEAT) throw new GameError("not defeated");
    this.player.hp = this.player.max_hp;
    this.battle = this.newBattle(this.current_room()!, true);
    this.save();
  }

  /** Leave the fight (back to the map). The fight is saved and resumes later. */
  leave(): void {
    if (this.battle !== null && this.battle.state === ACTIVE && this.dungeon !== null) {
      this.saved_fight = { dungeon: this.dungeon.key, room: this.room_index, monster_hp: this.battle.monster.hp };
    }
    this.battle = null;
    this.save();
  }

  // -- items ------------------------------------------------------------------------------------
  /** One-time items the player carries, with their counts. */
  usable_items(): [Item, number][] { return Object.entries(this.inventory.counts).map(([k, n]) => [ITEMS[k], n]); }

  /** Use a one-time item in the current fight. Unusable items are not consumed. */
  use_item(key: string): ItemUse {
    const item = Object.hasOwn(ITEMS, key) ? ITEMS[key] : undefined;
    const battle = this.battle;
    if (!item || isEquipment(item)) return itemUse(false, "That can't be used.");
    if (battle === null || battle.state !== ACTIVE) return itemUse(false, "You can only use items during a fight.");
    if (this.inventory.count(key) <= 0) return itemUse(false, `You have no ${item.name}.`);
    if (battle.monster.spec.silence) return itemUse(false, `The ${battle.monster.name} silences you: no items in this fight.`);
    const q = battle.question;
    const eff = item.effect;
    const use = itemUse(true, "");

    if (eff === items.HEAL || eff === items.HEAL_FULL) {
      const p = this.player;
      if (p.hp >= p.max_hp) return itemUse(false, "You are already at full health.");
      const amount = eff === items.HEAL_FULL ? p.max_hp : pyRound((p.max_hp * item.value * (100 + p.effects.item_pct)) / 100);
      use.message = `You drink the ${item.name} and recover ${battle.heal_player(amount)} HP.`;
    } else if (eff === items.DAMAGE) {
      const dealt = battle.monster.take_damage(Math.trunc((item.value * (100 + this.player.effects.item_pct)) / 100));
      use.message = `The ${item.name} hits the ${battle.monster.name} for ${dealt} damage!`;
      if (!battle.monster.is_alive) use.message += ` The ${battle.monster.name} is defeated!`;
    } else if (eff === items.FIRST_LETTER || eff === items.LETTER_COUNT || eff === items.FULL_HINT) {
      if (q === null) return itemUse(false, "There is no word to reveal right now.");
      const first = eff === items.FIRST_LETTER || eff === items.FULL_HINT;
      const count = eff === items.LETTER_COUNT || eff === items.FULL_HINT;
      if ((!first || q.show_first) && (!count || q.show_count)) return itemUse(false, "That is already revealed.");
      use.hint = battle.reveal(first, count);
      use.message = `You use the ${item.name}.`;
    } else if (eff === items.WARD) {
      if (battle.ward) return itemUse(false, "A ward is already active.");
      battle.ward = true;
      use.message = "A shimmering ward surrounds you. The next hit is absorbed.";
    } else if (eff === items.FREE_SKIP) {
      if (q === null) return itemUse(false, "There is no word to skip right now.");
      use.result = battle.free_skip();
      use.message = use.result.message;
    } else if (eff === items.XP_BOOST) {
      if (battle.xp_mult > 1) return itemUse(false, "Already active for this fight.");
      battle.xp_mult = item.value;
      use.message = "Your mind sharpens: double XP if you win this fight.";
    } else if (eff === items.COIN_BOOST) {
      if (battle.coin_mult > 1) return itemUse(false, "Already active for this fight.");
      battle.coin_mult = item.value;
      use.message = "The idol glows: double coins if you win this fight.";
    } else return itemUse(false, "Nothing happens.");

    this.inventory.consume(key);
    this.stats.items_used += 1;
    use.state = battle.state;
    this.finishIfWon();
    this.save();
    return use;
  }

  // -- shop -------------------------------------------------------------------------------------
  shop(): ShopEntry[] {
    const out: ShopEntry[] = [];
    for (const item of ITEM_LIST) {
      if (!item.shop && !this.inventory.has(item.key)) continue;   // loot-only gear appears once you have found it
      out.push({ item, count: this.inventory.count(item.key), owned: this.inventory.has(item.key),
        equipped: isEquipment(item) && this.inventory.is_equipped(item.key), problem: this.inventory.buy_problem(item, this.player, this.price(item)), price: this.price(item) });
    }
    return out;
  }

  /** What `item` costs this hero: Charisma gives a discount. */
  price(item: Item): number { return Math.max(1, pyRound((item.price * (100 - this.player.effects.discount_pct)) / 100)); }

  /** The share of an item's price you get when selling it (Charisma raises it). */
  get sell_fraction(): number { return config.SELL_FRACTION + this.player.effects.sell_bonus_pct / 100; }

  /** Buy an item; throws a GameError (with the reason) if that isn't possible. */
  buy(key: string): string {
    const item = ITEMS[key];
    const price = this.price(item);
    this.inventory.buy(item, this.player, price);
    this.stats.items_bought += 1;
    this.stats.coins_spent += price;
    this.applyGear();
    this.save();
    return `Bought ${item.name} for ${price} coins.`;
  }

  /** [weapon, armor, charm] item keys the hero is wearing, for drawing him. */
  hero_look(): [string | null, string | null, string | null] {
    const eq = this.inventory.equipped;
    return [eq.weapon ?? null, eq.armor ?? null, eq.charm ?? null];
  }

  /** Everything the player could sell, with its sell value. */
  sellable(): SellEntry[] {
    const out: SellEntry[] = [];
    for (const item of ITEM_LIST) {
      if (this.inventory.sell_problem(item) === null) {
        out.push({ item, count: this.inventory.count(item.key), value: this.inventory.sell_value(item, this.sell_fraction),
          equipped: isEquipment(item) && this.inventory.is_equipped(item.key) });
      }
    }
    return out;
  }

  /** Sell one item (equipment is unequipped); throws a GameError if not possible. */
  sell(key: string): string {
    const item = ITEMS[key];
    const coins = this.inventory.sell(item, this.player, this.sell_fraction);
    this.stats.items_sold += 1;
    this.applyGear();
    this.save();
    return `Sold ${item.name} for ${coins} coins.`;
  }

  equip(key: string): void { this.inventory.equip(key); this.applyGear(); this.save(); }
  unequip(slot: string): void { this.inventory.unequip(slot); this.applyGear(); this.save(); }

  // -- stats ------------------------------------------------------------------------------------
  private checkCanChangeStats(): void {
    if (this.battle !== null && this.battle.state === ACTIVE) throw new GameError("You can't change your stats during a fight.");
  }

  /** Put `count` unspent points into `stat`; throws a GameError if that isn't possible. */
  spend_point(stat: string, count = 1): void {
    this.checkCanChangeStats();
    if (!(statRules.STAT_KEYS as readonly string[]).includes(stat)) throw new GameError("Unknown stat.");
    if (count < 1 || count > this.player.stat_points) throw new GameError("You don't have that many points.");
    this.player.stat_points -= count;
    this.player.stats[stat as statRules.StatKey] += count;
    this.applyGear();
    this.save();
  }

  get respec_cost(): number { return statRules.respecCost(this.player.level, this.player.respecs); }

  /** Take every point back (the first time free, then for coins). Returns the coins paid. */
  respec(): number {
    this.checkCanChangeStats();
    const cost = this.respec_cost;
    if (cost > this.player.coins) throw new GameError(`A respec costs ${cost} coins.`);
    const spent = Object.values(this.player.stats).reduce((a, b) => a + b, 0);
    if (spent === 0) throw new GameError("You have no points to take back.");
    this.player.coins -= cost;
    this.player.stat_points += spent;
    this.player.stats = statRules.emptyStats();
    this.player.respecs += 1;
    this.applyGear();
    this.save();
    return cost;
  }

  // -- persistence ------------------------------------------------------------------------------
  save(): void {
    let fight: unknown = null;
    if (this.battle !== null && this.battle.state === ACTIVE && this.dungeon !== null) {
      fight = { dungeon: this.dungeon.key, room: this.room_index, monster_hp: this.battle.monster.hp };
    } else if (this.saved_fight) fight = this.saved_fight;
    try {
      this.repo.save({
        version: SCHEMA_VERSION, player: this.player.to_dict(), dungeons: this.progress, run: this.run, stats: this.stats,
        missed: this.missed.to_dict(), inventory: this.inventory.to_dict(), fight,
      });
    } catch { /* a failed save must never crash the game */ }
  }
}
