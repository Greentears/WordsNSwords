"""The shop catalogue: one-time items and permanent equipment (data only)."""
from __future__ import annotations

from dataclasses import dataclass

CONSUMABLE, EQUIPMENT = "consumable", "equipment"
WEAPON, ARMOR, CHARM, COMPANION = "weapon", "armor", "charm", "companion"
SLOTS = (WEAPON, ARMOR, CHARM, COMPANION)

# Consumable effects
HEAL, HEAL_FULL, DAMAGE = "heal", "heal_full", "damage"
FIRST_LETTER, LETTER_COUNT, FULL_HINT = "first_letter", "letter_count", "full_hint"
WARD, FREE_SKIP, XP_BOOST, COIN_BOOST = "ward", "free_skip", "xp_boost", "coin_boost"


@dataclass(frozen=True)
class Item:
    key: str
    name: str
    description: str
    price: int
    kind: str
    level: int = 1            # player level needed to buy it
    slot: str | None = None   # equipment only
    effect: str | None = None  # consumables only
    value: float = 0          # strength of the effect
    # equipment bonuses
    hp: int = 0
    attack: int = 0
    reduction: int = 0        # damage taken off every monster hit
    xp_pct: int = 0
    coin_pct: int = 0
    time: int = 0             # extra seconds on timed questions
    phoenix: bool = False     # survive one lethal hit per fight
    # companion effects
    heal_on_correct: int = 0  # HP restored after every correct answer
    bonus_damage: int = 0     # extra damage on every correct answer
    dodge_pct: int = 0        # chance to avoid a monster hit
    start_ward: bool = False  # every fight begins with a ward
    # presentation / availability
    shop: bool = True         # False: only found as loot
    icon: str = ""

    @property
    def is_equipment(self) -> bool:
        return self.kind == EQUIPMENT


def _c(key, name, desc, price, effect, value=0, level=1) -> Item:
    return Item(key, name, desc, price, CONSUMABLE, level=level, effect=effect, value=value)


def _e(key, name, desc, price, slot, level, **bonus) -> Item:
    return Item(key, name, desc, price, EQUIPMENT, level=level, slot=slot, **bonus)


ITEMS: dict[str, Item] = {i.key: i for i in (
    # --- one-time items ---
    _c("letter_scroll", "Letter Scroll", "Reveals the first letter of the answer.", 15, FIRST_LETTER),
    _c("count_rune", "Counting Rune", "Reveals how many letters the answer has.", 15, LETTER_COUNT),
    _c("oracle_eye", "Oracle's Eye", "Reveals the first letter and the letter count.",
       35, FULL_HINT, level=3),
    _c("small_potion", "Healing Potion", "Restores 40% of your max HP.", 25, HEAL, 0.4),
    _c("big_potion", "Elixir of Life", "Fully restores your HP.", 70, HEAL_FULL, level=3),
    _c("fire_bomb", "Fire Bomb", "Deals 20 damage to the monster.", 30, DAMAGE, 20),
    _c("lightning", "Lightning Rune", "Deals 55 damage to the monster.", 90, DAMAGE, 55, level=4),
    _c("meteor", "Meteor Scroll", "Deals 140 damage to the monster.", 260, DAMAGE, 140, level=8),
    _c("ward_scroll", "Ward Scroll", "Absorbs the next monster hit completely.", 40, WARD),
    _c("passage_scroll", "Passage Scroll", "Skip the current word: no damage, no penalty.", 35, FREE_SKIP),
    _c("wisdom_tome", "Tome of Wisdom", "Doubles the XP of this fight's victory.", 80, XP_BOOST, 2, level=3),
    _c("golden_idol", "Golden Idol", "Doubles the coins of this fight's victory.", 60, COIN_BOOST, 2, level=3),
    # --- weapons ---
    _e("wooden_sword", "Wooden Sword", "+2 attack.", 40, WEAPON, 1, attack=2),
    _e("iron_sword", "Iron Sword", "+5 attack.", 130, WEAPON, 3, attack=5),
    _e("steel_blade", "Steel Blade", "+9 attack.", 320, WEAPON, 5, attack=9),
    _e("runed_blade", "Runed Blade", "+14 attack.", 750, WEAPON, 8, attack=14),
    _e("dragon_fang", "Dragon Fang", "+20 attack.", 1600, WEAPON, 12, attack=20),
    # --- armor ---
    _e("leather_vest", "Leather Vest", "+10 max HP.", 60, ARMOR, 1, hp=10),
    _e("chainmail", "Chainmail", "+25 max HP, monster hits do 1 less.", 220, ARMOR, 4, hp=25, reduction=1),
    _e("plate_armor", "Plate Armor", "+50 max HP, monster hits do 2 less.", 650, ARMOR, 7, hp=50, reduction=2),
    _e("dragon_scale", "Dragon Scale Mail", "+80 max HP, monster hits do 3 less.", 1500, ARMOR, 11,
       hp=80, reduction=3),
    # --- charms ---
    _e("lucky_clover", "Lucky Clover", "+15% coins from fights.", 150, CHARM, 2, coin_pct=15),
    _e("time_amulet", "Hourglass Amulet", "+8 seconds on timed questions.", 300, CHARM, 5, time=8),
    _e("sages_ring", "Sage's Ring", "+25% XP from fights.", 450, CHARM, 6, xp_pct=25),
    _e("phoenix_feather", "Phoenix Feather", "Once per fight you survive a deadly blow and rise with 30% HP.",
       1000, CHARM, 8, phoenix=True),
    # --- companions (one at a time; expensive) ---
    _e("pixie", "Pixie", "Heals you for 3 HP after every correct answer.", 900, COMPANION, 5,
       heal_on_correct=3, icon="🧚"),
    _e("hawk", "War Hawk", "Adds 5 damage to every correct answer.", 1500, COMPANION, 7,
       bonus_damage=5, icon="🦅"),
    _e("owl", "Wise Owl", "+15% XP and +15% coins from fights.", 1800, COMPANION, 8,
       xp_pct=15, coin_pct=15, icon="🦉"),
    _e("shadow_cat", "Shadow Cat", "20% chance to dodge a monster's hit.", 2200, COMPANION, 9,
       dodge_pct=20, icon="🐈"),
    _e("stone_turtle", "Stone Turtle", "Every fight starts with a free ward.", 2800, COMPANION, 11,
       start_ward=True, icon="🐢"),
    _e("baby_dragon", "Baby Dragon", "+10 damage and 2 HP healed on every correct answer.", 4500,
       COMPANION, 13, bonus_damage=10, heal_on_correct=2, icon="🐉"),
    # --- tower trophies: only dropped by tower bosses ---
    _e("tower_blade", "Sword of the Tower", "+26 attack.", 1200, WEAPON, 1, attack=26, shop=False),
    _e("tower_mail", "Warden's Mail", "+110 max HP, monster hits do 4 less.", 1200, ARMOR, 1,
       hp=110, reduction=4, shop=False),
    _e("tower_crown", "Scholar's Crown", "+30% XP and +30% coins.",
       1200, CHARM, 1, xp_pct=30, coin_pct=30, shop=False),
    _e("stormcaller", "Stormcaller", "+34 attack.", 1800, WEAPON, 1, attack=34, shop=False),
    _e("titan_plate", "Titan Plate", "+160 max HP, monster hits do 6 less.", 1800, ARMOR, 1,
       hp=160, reduction=6, shop=False),
    _e("chrono_amulet", "Chrono Amulet", "+15 seconds on timed questions and a Phoenix rebirth.", 1800,
       CHARM, 1, time=15, phoenix=True, shop=False),
)}

# Equipment that used to exist: owners are refunded its price when the save is loaded.
REMOVED_EQUIPMENT = {"scholars_monocle": 260}

# Tower bosses (floor 10, 20, 30 ...) drop these in order, then bundles of one-time items.
TOWER_LOOT = ("tower_blade", "tower_mail", "tower_crown", "stormcaller", "titan_plate", "chrono_amulet")
TOWER_BUNDLES = (("meteor", 3), ("big_potion", 3), ("passage_scroll", 5), ("ward_scroll", 5),
                 ("lightning", 5), ("wisdom_tome", 3))

CONSUMABLE_KEYS = tuple(k for k, i in ITEMS.items() if i.kind == CONSUMABLE)
EQUIPMENT_KEYS = tuple(k for k, i in ITEMS.items() if i.kind == EQUIPMENT)
