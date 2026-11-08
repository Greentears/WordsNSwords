"""XP, coins and healing handed out for fights, treasure, rest and completion."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from . import config
from .models import Player, Room

STAT_KEYS = (
    "monsters_defeated", "correct_answers", "wrong_answers", "xp_earned", "coins_earned",
    "rooms_cleared", "dungeons_completed", "deaths", "hints_used", "skips",
    "items_used", "items_bought", "coins_spent", "words_cleared", "items_sold",
)
RUN_KEYS = ("xp", "coins", "monsters", "correct", "wrong", "rooms", "cleared")


def clean_counters(data: Any, keys: tuple[str, ...]) -> dict[str, int]:
    """A counter dict with exactly `keys`; anything invalid in `data` becomes 0."""
    data = data if isinstance(data, dict) else {}
    out = {}
    for key in keys:
        value = data.get(key)
        out[key] = value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else 0
    return out


@dataclass
class Reward:
    xp: int = 0
    coins: int = 0
    healed: int = 0
    levels_gained: int = 0
    messages: list[str] = field(default_factory=list)


class RewardManager:
    """Applies rewards to the player and keeps the statistics up to date."""

    def __init__(self, player: Player, stats: dict[str, int], run: dict[str, int]):
        self.player = player
        self.stats = stats
        self.run = run

    def _grant(self, xp: int = 0, coins: int = 0) -> Reward:
        reward = Reward(xp=xp, coins=coins)
        self.player.coins += coins
        reward.levels_gained = self.player.add_xp(xp)
        self.stats["xp_earned"] += xp
        self.stats["coins_earned"] += coins
        self.run["xp"] += xp
        self.run["coins"] += coins
        if xp:
            reward.messages.append(f"+{xp} XP")
        if coins:
            reward.messages.append(f"+{coins} coins")
        if reward.levels_gained:
            reward.messages.append(
                f"Level up! You are now level {self.player.level} "
                f"(max HP {self.player.max_hp}, fully healed)."
            )
        return reward

    def monster_defeated(self, spec: config.MonsterSpec, xp_mult: float = 1.0,
                         coin_mult: float = 1.0) -> Reward:
        self.stats["monsters_defeated"] += 1
        self.run["monsters"] += 1
        return self._grant(round(spec.xp * xp_mult),
                           round((spec.coins + config.ROOM_CLEAR_COINS) * coin_mult))

    def treasure(self, room: Room) -> Reward:
        reward = self._grant(room.xp, room.coins)
        reward.messages.insert(0, "You open the chest.")
        return reward

    def rest(self, room: Room) -> Reward:
        healed = self.player.heal(round(self.player.max_hp * room.heal_fraction))
        reward = Reward(healed=healed)
        reward.messages.append(f"You rest and recover {healed} HP.")
        return reward

    def dungeon_completed(self, xp: int = config.DUNGEON_COMPLETE_XP,
                          coins: int = config.DUNGEON_COMPLETE_COINS) -> Reward:
        self.stats["dungeons_completed"] += 1
        reward = self._grant(xp, coins)
        reward.messages.insert(0, "Dungeon completed!")
        return reward

    def bonus_coins(self, coins: int) -> None:
        """Coins found outside a fight (e.g. selling a duplicate drop)."""
        self._grant(0, coins)

    def room_cleared(self) -> None:
        self.stats["rooms_cleared"] += 1
        self.run["rooms"] += 1
