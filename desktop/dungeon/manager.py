"""GameManager: the single entry point the interface talks to.

It owns the player, inventory, dungeon progress and the current fight, saves
after every action, and never modifies the vocabulary deck.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

from . import config, items
from .battle import ACTIVE, DEFEAT, VICTORY, AnswerResult, Battle, Question
from .cloze import ClozeSource
from .dungeons import DUNGEONS
from .inventory import Inventory
from .items import ITEMS, Item
from .models import Dungeon, Monster, Player, Room, TREASURE
from .repository import SCHEMA_VERSION, GameProgressRepository
from .rewards import RUN_KEYS, STAT_KEYS, Reward, RewardManager, clean_counters
from .selector import MissedWords, VocabularySelector
from examples import load_examples

SAVE_NAME = "dungeon_progress.json"


def save_path_for(words_json: str | Path) -> Path:
    """The dungeon save lives next to the vocabulary file but is a separate file."""
    return Path(words_json).with_name(SAVE_NAME)


@dataclass
class DungeonStatus:
    key: str
    name: str
    description: str
    room: int            # index of the next room to play
    total_rooms: int
    completed: bool      # finished at least once
    times: int           # how many times it was finished
    in_progress: bool    # started and not finished
    min_level: int = 1
    locked: bool = False  # player level is too low
    kind: str = "story"   # "story", "review" or "tower"
    endless: bool = False
    best: int = 0         # tower: highest floor cleared
    unavailable: str | None = None  # why it can't be entered right now (None = open)


@dataclass
class RoomOutcome:
    """What happened when a room was cleared or resolved."""
    kind: str
    title: str
    reward: Reward = field(default_factory=Reward)
    dungeon_completed: bool = False
    final_reward: Reward | None = None
    run: dict[str, int] = field(default_factory=dict)   # totals, for the completion screen
    loot: str | None = None   # a boss drop, e.g. "Sword of the Tower"

    @property
    def messages(self) -> list[str]:
        msgs = list(self.reward.messages)
        if self.loot:
            msgs.append(self.loot)
        if self.final_reward:
            msgs += self.final_reward.messages
        return msgs


@dataclass
class ShopEntry:
    item: Item
    count: int           # how many of a one-time item are carried
    owned: bool          # equipment bought
    equipped: bool
    problem: str | None  # why it can't be bought right now


@dataclass
class SellEntry:
    item: Item
    count: int           # carried (one-time items); 1 for equipment
    value: int           # coins you would get
    equipped: bool


@dataclass
class ItemUse:
    ok: bool
    message: str
    state: str = ACTIVE
    hint: str | None = None          # new hint text, for hint items
    result: AnswerResult | None = None  # for the Passage Scroll


class GameManager:
    def __init__(self, deck: Any, save_path: str | Path, rng: random.Random | None = None,
                 hero_name: str | None = None, examples_path: str | Path | None = None):
        self.deck = deck
        self.repo = GameProgressRepository(save_path)
        self.rng = rng or random.Random()
        state = self.repo.load()

        self.player = Player.from_dict(state["player"])
        if hero_name and hero_name.strip():
            self.player.name = hero_name.strip()
        self.inventory = Inventory(state["inventory"])
        self.stats = clean_counters(state["stats"], STAT_KEYS)
        self.run = clean_counters(state["run"], RUN_KEYS)
        self.review_failed: dict[str, str] = {}   # review fight: card word -> meaning, in order of the first miss
        self.missed = MissedWords(state["missed"])
        self.selector = VocabularySelector(deck, self.missed, self.rng)
        self.cloze = ClozeSource(deck, load_examples(Path(examples_path) if examples_path
                                                  else Path(save_path).with_name("examples.json")),
                                 self.rng)
        self.rewards = RewardManager(self.player, self.stats, self.run)
        if self.inventory.refund:          # equipment that was removed from the game
            self.player.coins += self.inventory.refund
            self.inventory.refund = 0
        self.progress: dict[str, dict[str, Any]] = {}
        for key, dungeon in DUNGEONS.items():
            self.progress[key] = self._clean_progress(state["dungeons"], key, dungeon.room_count)

        self.dungeon: Dungeon | None = None
        self.battle: Battle | None = None
        self.outcome: RoomOutcome | None = None
        self._saved_fight = state["fight"] if isinstance(state["fight"], dict) else None

        self._apply_gear()
        if not self.player.is_alive:  # saved while dead: come back healthy, fight restarts
            self.player.hp = self.player.max_hp
            self._saved_fight = None

    # -- loading helpers ----------------------------------------------------
    @staticmethod
    def _clean_progress(saved: Any, key: str, rooms: int | None) -> dict[str, Any]:
        entry = saved.get(key) if isinstance(saved, dict) else None
        entry = entry if isinstance(entry, dict) else {}

        def count(name: str, high: int) -> int:
            v = entry.get(name)
            return max(0, min(high, v)) if isinstance(v, int) and not isinstance(v, bool) else 0

        return {"room": count("room", 10**6 if rooms is None else rooms),
                "completed": entry.get("completed") is True,
                "times": count("times", 10**6), "best": count("best", 10**6)}

    def _apply_gear(self) -> None:
        """Bring the player's stats in line with what is equipped."""
        t = self.inventory.totals()
        p = self.player
        delta = t.hp - p.gear_hp
        p.max_hp = max(1, p.max_hp + delta)
        p.gear_hp = t.hp
        if delta > 0 and p.is_alive:
            p.hp += delta
        p.hp = min(p.hp, p.max_hp)
        p.gear_attack = t.attack
        p.gear_reduction = t.reduction

    # -- queries ------------------------------------------------------------
    @property
    def missed_count(self) -> int:
        return len(self.missed)

    @property
    def has_words(self) -> bool:
        return bool(self.selector.candidates())

    def unavailable_reason(self, key: str) -> str | None:
        """Why a dungeon can't be entered right now (None = it can)."""
        d = DUNGEONS[key]
        if self.player.level < d.min_level:
            return f"Requires level {d.min_level}"
        p = self.progress[key]
        in_progress = 0 < p["room"] < (d.room_count or 0)
        if d.kind == "review" and not self.missed and not in_progress:
            return "No missed words to review"
        return None

    def dungeons(self) -> list[DungeonStatus]:
        out = []
        for key, d in DUNGEONS.items():
            p = self.progress[key]
            count = d.room_count
            started = p["room"] > 0 and (count is None or p["room"] < count)
            out.append(DungeonStatus(key, d.name, d.description, p["room"], count or 0,
                                     p["completed"], p["times"], started, d.min_level,
                                     self.player.level < d.min_level, d.kind, d.endless,
                                     p["best"], self.unavailable_reason(key)))
        return out

    def current_room(self) -> Room | None:
        """The next room to play in the selected dungeon; None when it is finished."""
        if self.dungeon is None:
            return None
        return self.dungeon.room(self.progress[self.dungeon.key]["room"])

    @property
    def room_index(self) -> int:
        return self.progress[self.dungeon.key]["room"] if self.dungeon else 0

    # -- dungeon selection --------------------------------------------------
    def select_dungeon(self, key: str, restart: bool = False) -> None:
        """Choose a dungeon. A finished dungeon (or `restart=True`) starts again from room 1."""
        dungeon = DUNGEONS[key]
        reason = self.unavailable_reason(key)
        if reason:
            raise ValueError(f"{dungeon.name}: {reason}")
        p = self.progress[key]
        count = dungeon.room_count
        if restart or (count is not None and p["room"] >= count):
            p["room"] = 0
            self.run = clean_counters({}, RUN_KEYS)
            self.rewards.run = self.run
            self._saved_fight = None
            self.review_failed = {}
        elif self._saved_fight and self._saved_fight.get("dungeon") != key:
            self._saved_fight = None
        if dungeon.kind == "review" and not self._saved_fight:
            self.review_failed = {}     # a fresh review; continuing a saved fight keeps the list
        self.dungeon = dungeon
        self.selector.only_missed = dungeon.kind == "review"
        self.battle = None
        self.outcome = None
        self.save()

    # -- rooms --------------------------------------------------------------
    def enter_room(self) -> RoomOutcome | None:
        """Enter the current room.

        Fight rooms start (or resume) a battle and return None. Treasure and rest
        rooms resolve at once and return their outcome.
        """
        room = self.current_room()
        if room is None:
            raise RuntimeError("no room to enter")
        self.outcome = None
        if room.is_fight:
            self.battle = self._new_battle(room)
            return None
        self.battle = None
        reward = self.rewards.treasure(room) if room.kind == TREASURE else self.rewards.rest(room)
        return self._room_cleared(room, reward)

    def _new_battle(self, room: Room, fresh: bool = False) -> Battle:
        spec = room.spec or config.MONSTERS[room.monster]
        d = self.dungeon
        if d.hp_scale != 1.0 or d.damage_scale != 1.0:
            spec = replace(spec, max_hp=max(1, round(spec.max_hp * d.hp_scale)),
                           damage=max(1, round(spec.damage * d.damage_scale)))
        if d.kind == "review":
            spec = replace(spec, max_hp=self._review_hp())
        hp = None
        fight = self._saved_fight
        self._saved_fight = None
        self.outcome = None
        if not self.player.is_alive:  # came back after a defeat: heal, fresh monster
            self.player.hp = self.player.max_hp
            fresh = True
        if (not fresh and fight and fight.get("dungeon") == self.dungeon.key
                and fight.get("room") == self.room_index
                and isinstance(fight.get("monster_hp"), int)):
            hp = fight["monster_hp"]
        battle = Battle(self.player, Monster.spawn(spec, hp), self.selector, self.rng)
        gear = self.inventory.totals()
        battle.phoenix = gear.phoenix
        battle.time_bonus = gear.time
        battle.cloze_source = self.cloze
        battle.ward = gear.start_ward
        battle.companion = gear.companion
        battle.heal_on_correct = gear.heal_on_correct
        battle.bonus_damage = gear.bonus_damage
        battle.dodge_pct = gear.dodge_pct
        return battle

    def next_question(self) -> Question | None:
        return self.battle.next_question() if self.battle else None

    def answer(self, text: str) -> AnswerResult:
        return self._after_answer(self.battle.submit(text))

    def skip(self) -> AnswerResult:
        self.stats["skips"] += 1
        return self._after_answer(self.battle.skip())

    def timeout(self) -> AnswerResult:
        """The question's time limit ran out."""
        return self._after_answer(self.battle.timeout())

    def _meaning(self, word: str) -> str:
        return next((w.translation for w in self.deck.words if w.word == word), "")

    @property
    def review_failed_words(self) -> list[tuple[str, str]]:
        """Every word failed during the current review, as (Polish, English), first miss first."""
        return list(self.review_failed.items())

    def _review_hp(self) -> int:
        """HP of the Review Guru: about one correct answer per missed word (5 to 10 of them)."""
        words = min(config.REVIEW_MAX_WORDS, max(config.REVIEW_MIN_WORDS, len(self.missed)))
        per_hit = self.player.attack_power + self.inventory.totals().bonus_damage
        return max(1, per_hit * words)

    def _after_answer(self, result: AnswerResult) -> AnswerResult:
        if result.free:
            pass
        elif result.correct:
            self.stats["correct_answers"] += 1
            self.run["correct"] += 1
        else:
            self.stats["wrong_answers"] += 1
            self.run["wrong"] += 1
            if self.dungeon is not None and self.dungeon.kind == "review" and result.word:
                self.review_failed.setdefault(result.word, self._meaning(result.word))
        if result.cleared_from_missed:
            self.stats["words_cleared"] += 1
            self.run["cleared"] += 1
        if result.state == DEFEAT:
            self.stats["deaths"] += 1
        self._finish_if_won()
        self.save()
        return result

    def _finish_if_won(self) -> None:
        """Pay out the monster's rewards once, the moment it is dead."""
        if self.battle is None or self.battle.state != VICTORY or self.outcome is not None:
            return
        gear = self.inventory.totals()
        reward = self.rewards.monster_defeated(
            self.battle.monster.spec,
            xp_mult=(1 + gear.xp_pct / 100) * self.battle.xp_mult * self.dungeon.reward_scale,
            coin_mult=(1 + gear.coin_pct / 100) * self.battle.coin_mult * self.dungeon.reward_scale,
        )
        self.outcome = self._room_cleared(self.current_room(), reward)

    def _room_cleared(self, room: Room, reward: Reward) -> RoomOutcome:
        key = self.dungeon.key
        p = self.progress[key]
        self.rewards.room_cleared()
        p["room"] += 1
        self._saved_fight = None
        outcome = RoomOutcome(room.kind, room.title, reward)
        if self.dungeon.endless:
            p["best"] = max(p["best"], p["room"])
        if room.drop:
            outcome.loot = self._give_loot(room)
        count = self.dungeon.room_count
        if count is not None and p["room"] >= count:
            p["completed"] = True
            p["times"] += 1
            outcome.dungeon_completed = True
            outcome.final_reward = self.rewards.dungeon_completed(
                round(self.dungeon.complete_xp * self.dungeon.reward_scale),
                round(self.dungeon.complete_coins * self.dungeon.reward_scale))
            outcome.run = dict(self.run)
        self.save()
        return outcome

    def _give_loot(self, room: Room) -> str:
        """Hand over a boss drop. Gear you already own is sold at the normal sell price."""
        item = ITEMS[room.drop]
        if item.is_equipment and self.inventory.has(item.key):
            coins = self.inventory.sell_value(item)
            self.rewards.bonus_coins(coins)
            return f"Loot: {item.name} (you already own it: sold for {coins} coins)"
        self.inventory.give(item.key, room.drop_count)
        self._apply_gear()
        times = f" x{room.drop_count}" if room.drop_count > 1 else ""
        return f"Loot: {item.name}{times}!"

    def retry(self) -> None:
        """After a defeat: heal fully and face the same room again with a fresh monster."""
        if self.battle is None or self.battle.state != DEFEAT:
            raise RuntimeError("not defeated")
        self.player.hp = self.player.max_hp
        self.battle = self._new_battle(self.current_room(), fresh=True)
        self.save()

    def leave(self) -> None:
        """Leave the fight (back to the map). The fight is saved and resumes later."""
        if self.battle is not None and self.battle.state == ACTIVE and self.dungeon is not None:
            self._saved_fight = {"dungeon": self.dungeon.key, "room": self.room_index,
                                 "monster_hp": self.battle.monster.hp}
        self.battle = None
        self.save()

    # -- items --------------------------------------------------------------
    def usable_items(self) -> list[tuple[Item, int]]:
        """One-time items the player carries, with their counts."""
        return [(ITEMS[k], n) for k, n in self.inventory.counts.items()]

    def use_item(self, key: str) -> ItemUse:
        """Use a one-time item in the current fight. Unusable items are not consumed."""
        item = ITEMS.get(key)
        battle = self.battle
        if item is None or item.is_equipment:
            return ItemUse(False, "That can't be used.")
        if battle is None or battle.state != ACTIVE:
            return ItemUse(False, "You can only use items during a fight.")
        if self.inventory.count(key) <= 0:
            return ItemUse(False, f"You have no {item.name}.")
        q = battle.question
        eff = item.effect
        use = ItemUse(True, "")

        if eff in (items.HEAL, items.HEAL_FULL):
            p = self.player
            if p.hp >= p.max_hp:
                return ItemUse(False, "You are already at full health.")
            amount = p.max_hp if eff == items.HEAL_FULL else round(p.max_hp * item.value)
            use.message = f"You drink the {item.name} and recover {p.heal(amount)} HP."
        elif eff == items.DAMAGE:
            dealt = battle.monster.take_damage(int(item.value))
            use.message = f"The {item.name} hits the {battle.monster.name} for {dealt} damage!"
            if not battle.monster.is_alive:
                use.message += f" The {battle.monster.name} is defeated!"
        elif eff in (items.FIRST_LETTER, items.LETTER_COUNT, items.FULL_HINT):
            if q is None:
                return ItemUse(False, "There is no word to reveal right now.")
            first = eff in (items.FIRST_LETTER, items.FULL_HINT)
            count = eff in (items.LETTER_COUNT, items.FULL_HINT)
            if (not first or q.show_first) and (not count or q.show_count):
                return ItemUse(False, "That is already revealed.")
            use.hint = battle.reveal(first=first, count=count)
            use.message = f"You use the {item.name}."
        elif eff == items.WARD:
            if battle.ward:
                return ItemUse(False, "A ward is already active.")
            battle.ward = True
            use.message = "A shimmering ward surrounds you. The next hit is absorbed."
        elif eff == items.FREE_SKIP:
            if q is None:
                return ItemUse(False, "There is no word to skip right now.")
            use.result = battle.free_skip()
            use.message = use.result.message
        elif eff == items.XP_BOOST:
            if battle.xp_mult > 1:
                return ItemUse(False, "Already active for this fight.")
            battle.xp_mult = item.value
            use.message = "Your mind sharpens: double XP if you win this fight."
        elif eff == items.COIN_BOOST:
            if battle.coin_mult > 1:
                return ItemUse(False, "Already active for this fight.")
            battle.coin_mult = item.value
            use.message = "The idol glows: double coins if you win this fight."
        else:
            return ItemUse(False, "Nothing happens.")

        self.inventory.consume(key)
        self.stats["items_used"] += 1
        use.state = battle.state
        self._finish_if_won()
        self.save()
        return use

    # -- shop ---------------------------------------------------------------
    def shop(self) -> list[ShopEntry]:
        out = []
        for item in ITEMS.values():
            if not item.shop and not self.inventory.has(item.key):
                continue          # loot-only gear appears once you have found it
            out.append(ShopEntry(
                item, self.inventory.count(item.key), self.inventory.has(item.key),
                item.is_equipment and self.inventory.is_equipped(item.key),
                self.inventory.buy_problem(item, self.player)))
        return out

    def buy(self, key: str) -> str:
        """Buy an item; raises ValueError (with the reason) if that isn't possible."""
        item = ITEMS[key]
        self.inventory.buy(item, self.player)
        self.stats["items_bought"] += 1
        self.stats["coins_spent"] += item.price
        self._apply_gear()
        self.save()
        return f"Bought {item.name} for {item.price} coins."

    def hero_look(self) -> tuple[str | None, str | None, str | None]:
        """(weapon, armor, charm) item keys the hero is wearing, for drawing him."""
        eq = self.inventory.equipped
        return eq.get("weapon"), eq.get("armor"), eq.get("charm")

    def sellable(self) -> list[SellEntry]:
        """Everything the player could sell, with its sell value."""
        out = []
        for item in ITEMS.values():
            if self.inventory.sell_problem(item) is None:
                out.append(SellEntry(
                    item, self.inventory.count(item.key), self.inventory.sell_value(item),
                    item.is_equipment and self.inventory.is_equipped(item.key)))
        return out

    def sell(self, key: str) -> str:
        """Sell one item (equipment is unequipped); raises ValueError if not possible."""
        item = ITEMS[key]
        coins = self.inventory.sell(item, self.player)
        self.stats["items_sold"] += 1
        self._apply_gear()
        self.save()
        return f"Sold {item.name} for {coins} coins."

    def equip(self, key: str) -> None:
        self.inventory.equip(key)
        self._apply_gear()
        self.save()

    def unequip(self, slot: str) -> None:
        self.inventory.unequip(slot)
        self._apply_gear()
        self.save()

    # -- persistence --------------------------------------------------------
    def save(self) -> None:
        fight = None
        if self.battle is not None and self.battle.state == ACTIVE and self.dungeon is not None:
            fight = {"dungeon": self.dungeon.key, "room": self.room_index,
                     "monster_hp": self.battle.monster.hp}
        elif self._saved_fight:
            fight = self._saved_fight
        state = {
            "version": SCHEMA_VERSION,
            "player": self.player.to_dict(),
            "dungeons": self.progress,
            "run": self.run,
            "stats": self.stats,
            "missed": self.missed.to_dict(),
            "inventory": self.inventory.to_dict(),
            "fight": fight,
        }
        try:
            self.repo.save(state)
        except OSError:
            pass  # a failed save must never crash the game
