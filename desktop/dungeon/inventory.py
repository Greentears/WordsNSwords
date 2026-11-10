"""What the player owns: one-time items, equipment and what is equipped."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from . import config
from .items import COMPANION, CONSUMABLE, EQUIPMENT, ITEMS, REMOVED_EQUIPMENT, SLOTS, Item
from .models import Player


@dataclass
class GearTotals:
    hp: int = 0
    attack: int = 0
    reduction: int = 0
    xp_pct: int = 0
    coin_pct: int = 0
    time: int = 0
    phoenix: bool = False
    heal_on_correct: int = 0
    bonus_damage: int = 0
    dodge_pct: int = 0
    start_ward: bool = False
    companion: str = ""      # name of the companion, if any


class Inventory:
    def __init__(self, data: Any = None):
        self.counts: dict[str, int] = {}
        self.owned: set[str] = set()
        self.equipped: dict[str, str] = {}
        self.refund = 0          # coins owed for equipment that no longer exists
        data = data if isinstance(data, dict) else {}

        counts = data.get("items")
        for key, n in (counts.items() if isinstance(counts, dict) else ()):
            item = ITEMS.get(key)
            if item and item.kind == CONSUMABLE and isinstance(n, int) and not isinstance(n, bool) and n > 0:
                self.counts[key] = min(n, config.MAX_ITEM_STACK)
        owned = data.get("owned")
        for key in (owned if isinstance(owned, list) else ()):
            if isinstance(key, str) and key in REMOVED_EQUIPMENT:
                self.refund += REMOVED_EQUIPMENT[key]
            if isinstance(key, str) and key in ITEMS and ITEMS[key].kind == EQUIPMENT:
                self.owned.add(key)
        equipped = data.get("equipped")
        for slot, key in (equipped.items() if isinstance(equipped, dict) else ()):
            if slot in SLOTS and key in self.owned and ITEMS[key].slot == slot:
                self.equipped[slot] = key

    def to_dict(self) -> dict[str, Any]:
        return {"items": dict(self.counts), "owned": sorted(self.owned),
                "equipped": dict(self.equipped)}

    # -- queries ------------------------------------------------------------
    def count(self, key: str) -> int:
        return self.counts.get(key, 0)

    def has(self, key: str) -> bool:
        return key in self.owned

    def is_equipped(self, key: str) -> bool:
        return self.equipped.get(ITEMS[key].slot) == key

    def totals(self) -> GearTotals:
        t = GearTotals()
        for key in self.equipped.values():
            i = ITEMS[key]
            t.hp += i.hp
            t.attack += i.attack
            t.reduction += i.reduction
            t.xp_pct += i.xp_pct
            t.coin_pct += i.coin_pct
            t.time += i.time
            t.phoenix = t.phoenix or i.phoenix
            t.heal_on_correct += i.heal_on_correct
            t.bonus_damage += i.bonus_damage
            t.dodge_pct += i.dodge_pct
            t.start_ward = t.start_ward or i.start_ward
            if i.slot == COMPANION:
                t.companion = i.name
        return t

    # -- shopping -----------------------------------------------------------
    def buy_problem(self, item: Item, player: Player, price: int | None = None) -> str | None:
        """Why the player cannot buy `item` right now (None = they can)."""
        if item.is_equipment and item.key in self.owned:
            return "Already owned"
        if not item.shop:
            return "Not for sale"
        if not item.is_equipment and self.count(item.key) >= config.MAX_ITEM_STACK:
            return "You can't carry more"
        if player.level < item.level:
            return f"Requires level {item.level}"
        if player.coins < (item.price if price is None else price):
            return "Not enough coins"
        return None

    def buy(self, item: Item, player: Player, price: int | None = None) -> None:
        """Buy `item` for `price` coins (default: its list price)."""
        problem = self.buy_problem(item, player, price)
        if problem:
            raise ValueError(problem)
        player.coins -= item.price if price is None else price
        if item.is_equipment:
            self.owned.add(item.key)
            self.equipped.setdefault(item.slot, item.key)  # first piece in a slot is worn at once
        else:
            self.counts[item.key] = self.count(item.key) + 1

    def sell_value(self, item: Item, fraction: float | None = None) -> int:
        return int(item.price * (config.SELL_FRACTION if fraction is None else fraction))

    def sell_problem(self, item: Item) -> str | None:
        if item.is_equipment:
            return None if item.key in self.owned else "You don't own that"
        return None if self.count(item.key) > 0 else "You have none left"

    def sell(self, item: Item, player: Player, fraction: float | None = None) -> int:
        """Sell one item for SELL_FRACTION of its price; returns the coins received."""
        problem = self.sell_problem(item)
        if problem:
            raise ValueError(problem)
        if item.is_equipment:
            self.owned.discard(item.key)
            if self.equipped.get(item.slot) == item.key:
                del self.equipped[item.slot]
        else:
            self.consume(item.key)
        coins = self.sell_value(item, fraction)
        player.coins += coins
        return coins

    def give(self, key: str, count: int = 1) -> None:
        """Add an item found as loot (no coins involved)."""
        item = ITEMS[key]
        if item.is_equipment:
            self.owned.add(key)
            self.equipped.setdefault(item.slot, key)
        else:
            self.counts[key] = min(config.MAX_ITEM_STACK, self.count(key) + count)

    def equip(self, key: str) -> None:
        if key not in self.owned:
            raise ValueError("You don't own that")
        self.equipped[ITEMS[key].slot] = key

    def unequip(self, slot: str) -> None:
        self.equipped.pop(slot, None)

    def consume(self, key: str) -> None:
        if self.count(key) <= 0:
            raise ValueError("You have none left")
        self.counts[key] -= 1
        if self.counts[key] <= 0:
            del self.counts[key]
