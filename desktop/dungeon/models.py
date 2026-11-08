"""Plain data classes: Player, Monster, Room, Dungeon."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from . import config


def _int(value: Any, default: int, low: int = 0, high: int = 10**9) -> int:
    """`value` as an int clamped to [low, high]; `default` for anything else."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return default
    return max(low, min(high, int(value)))


@dataclass
class Player:
    name: str = config.DEFAULT_PLAYER_NAME
    level: int = 1
    xp: int = 0            # XP collected towards the next level
    hp: int = config.BASE_MAX_HP
    max_hp: int = config.BASE_MAX_HP
    coins: int = 0
    gear_hp: int = 0        # part of max_hp that comes from equipment
    gear_attack: int = 0    # set from equipment (not saved)
    gear_reduction: int = 0  # set from equipment (not saved)

    @property
    def xp_needed(self) -> int:
        return config.xp_to_next(self.level)

    @property
    def is_alive(self) -> bool:
        return self.hp > 0

    @property
    def attack_power(self) -> int:
        return (config.BASE_PLAYER_DAMAGE + config.PLAYER_DAMAGE_PER_LEVEL * (self.level - 1)
                + self.gear_attack)

    def take_damage(self, amount: int) -> int:
        """Lose up to `amount` HP; returns the HP actually lost."""
        lost = max(0, min(amount, self.hp))
        self.hp -= lost
        return lost

    def heal(self, amount: int) -> int:
        """Restore up to `amount` HP; returns the HP actually restored."""
        gained = max(0, min(amount, self.max_hp - self.hp))
        self.hp += gained
        return gained

    def add_xp(self, amount: int) -> int:
        """Add XP, levelling up as often as needed; returns the levels gained."""
        self.xp += max(0, amount)
        gained = 0
        while self.xp >= self.xp_needed:
            self.xp -= self.xp_needed
            self.level += 1
            self.max_hp += config.LEVEL_HP_GAIN
            self.heal(round(self.max_hp * config.LEVEL_UP_HEAL_FRACTION))
            gained += 1
        return gained

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name, "level": self.level, "xp": self.xp,
            "hp": self.hp, "max_hp": self.max_hp, "coins": self.coins,
            "gear_hp": self.gear_hp,
        }

    @classmethod
    def from_dict(cls, data: Any) -> "Player":
        """Build a player from saved data; bad or missing values fall back to defaults."""
        data = data if isinstance(data, dict) else {}
        name = data.get("name")
        max_hp = _int(data.get("max_hp"), config.BASE_MAX_HP, low=1)
        player = cls(
            name=name.strip() if isinstance(name, str) and name.strip() else config.DEFAULT_PLAYER_NAME,
            level=_int(data.get("level"), 1, low=1, high=999),
            xp=_int(data.get("xp"), 0),
            hp=_int(data.get("hp"), max_hp, high=max_hp),
            max_hp=max_hp,
            coins=_int(data.get("coins"), 0),
            gear_hp=_int(data.get("gear_hp"), 0, high=max(0, max_hp - 1)),
        )
        player.xp = min(player.xp, player.xp_needed - 1)
        return player


@dataclass
class Monster:
    spec: config.MonsterSpec
    hp: int

    @classmethod
    def spawn(cls, spec: config.MonsterSpec, hp: int | None = None) -> "Monster":
        return cls(spec, spec.max_hp if hp is None else max(1, min(hp, spec.max_hp)))

    @property
    def max_hp(self) -> int:
        return self.spec.max_hp

    @property
    def name(self) -> str:
        return self.spec.name

    @property
    def is_alive(self) -> bool:
        return self.hp > 0

    def take_damage(self, amount: int) -> int:
        lost = max(0, min(amount, self.hp))
        self.hp -= lost
        return lost


# Room kinds
MONSTER, BOSS, TREASURE, REST = "monster", "boss", "treasure", "rest"


@dataclass(frozen=True)
class Room:
    kind: str
    title: str
    monster: str | None = None     # key into config.MONSTERS (monster / boss rooms)
    coins: int = 0                 # treasure reward
    xp: int = 0                    # treasure reward
    heal_fraction: float = 0.0     # rest rooms
    spec: config.MonsterSpec | None = None  # a one-off monster (the tower), else `monster`
    drop: str | None = None        # item key the monster drops
    drop_count: int = 1

    @property
    def is_fight(self) -> bool:
        return self.kind in (MONSTER, BOSS)


@dataclass(frozen=True)
class Dungeon:
    key: str
    name: str
    description: str
    rooms: tuple[Room, ...]
    min_level: int = 1                           # player level needed to enter
    complete_xp: int = config.DUNGEON_COMPLETE_XP
    complete_coins: int = config.DUNGEON_COMPLETE_COINS
    kind: str = "story"                          # "story", "review" or "tower"
    reward_scale: float = 1.0                    # multiplies every XP / coin reward
    hp_scale: float = 1.0                        # monsters here are tougher (or weaker)
    damage_scale: float = 1.0
    room_factory: Callable[[int], Room] | None = None  # endless dungeons build rooms on demand

    @property
    def endless(self) -> bool:
        return self.room_factory is not None

    @property
    def room_count(self) -> int | None:
        """Number of rooms, or None for an endless dungeon."""
        return None if self.endless else len(self.rooms)

    def room(self, index: int) -> Room | None:
        if self.room_factory is not None:
            return self.room_factory(index)
        return self.rooms[index] if 0 <= index < len(self.rooms) else None
