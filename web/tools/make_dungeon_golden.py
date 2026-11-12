"""Golden data for the TypeScript port of the Vocabulary Dungeon rules.

Plays scripted games with the real Python code and records every action, its result and the
game state afterwards, plus every random number drawn. The TypeScript tests replay the same
actions with the recorded random numbers and must get identical results.

    python3 tools/make_dungeon_golden.py [path-to-desktop-folder]   ->  tests/dungeon_golden.json
"""
import bisect, copy, dataclasses, itertools, json, random, shutil, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parent / "desktop"
sys.path.insert(0, str(PY))

import flashcards as fc  # noqa: E402
from dungeon import answers, config, daily, items, tower  # noqa: E402
from dungeon.battle import ACTIVE, DEFEAT, VICTORY  # noqa: E402
from dungeon.manager import GameManager  # noqa: E402

TODAY = "2026-01-15"      # the date every scripted game "runs" on (the daily challenge depends on it)
FIX = ROOT.parent / "tests" / "fixtures" / "pl-en"
WORDS = FIX / "words.json"
EXAMPLES = FIX / "examples.json"


class RecRandom(random.Random):
    """A Random whose every method is built from random() alone, and which logs each draw.

    The TypeScript port only needs a `random()` function: it replays this log.
    """

    def __init__(self, seed):
        super().__init__(seed)
        self.log = []

    def random(self):
        v = super().random()
        self.log.append(v)
        return v

    def uniform(self, a, b):
        return a + (b - a) * self.random()

    def choice(self, seq):
        return seq[int(self.random() * len(seq))]

    def choices(self, population, weights=None, *, cum_weights=None, k=1):
        assert weights is not None and k == 1
        cum = list(itertools.accumulate(weights))
        total = cum[-1] + 0.0
        hi = len(cum) - 1
        return [population[bisect.bisect(cum, self.random() * total, 0, hi)]]

    def shuffle(self, x):
        for i in reversed(range(1, len(x))):
            j = int(self.random() * (i + 1))
            x[i], x[j] = x[j], x[i]


def jsonable(x):
    if dataclasses.is_dataclass(x) and not isinstance(x, type):
        return {f.name: jsonable(getattr(x, f.name)) for f in dataclasses.fields(x)}
    if isinstance(x, dict):
        return {str(k): jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple, set)):
        return [jsonable(v) for v in x]
    return x


# ---------------------------------------------------------------------------
# 1. answer checking
# ---------------------------------------------------------------------------
def answers_golden():
    words = json.loads(WORDS.read_text(encoding="utf-8"))
    pol = random.Random(7)
    seen, table, forms = set(), [], []

    def typo(s):
        if len(s) < 4:
            return s + "x"
        i = pol.randrange(1, len(s) - 1)
        kind = pol.randrange(3)
        if kind == 0:
            return s[:i] + s[i + 1:]
        if kind == 1:
            return s[:i] + s[i + 1] + s[i] + s[i + 2:] if i + 2 <= len(s) else s
        return s[:i] + "q" + s[i + 1:]

    for w in words:
        for expected, reverse in ((w["translation"], False), (w["word"], True)):
            if (expected, reverse) not in seen:
                seen.add((expected, reverse))
                forms.append({"expected": expected, "reverse": reverse,
                              "forms": sorted(answers.accepted_forms(expected, reverse)),
                              "primary": answers.primary(expected, reverse)})
            prim = answers.primary(expected, reverse)
            parts = [p for p in expected.replace("(", " (").split("/") if p.strip()]
            givens = [expected, prim, expected.upper(), fc._strip_accents(prim), typo(prim),
                      "to " + prim, "the " + prim, "zzzz", "", "  ", prim + " extra",
                      w["word" if not reverse else "translation"]]
            givens += [p.strip() for p in parts[:3]]
            if len(parts) > 1:
                givens.append(" / ".join(p.strip() for p in parts))
            for g in givens:
                table.append({"expected": expected, "reverse": reverse, "given": g,
                              "result": list(answers.check(g, expected, reverse))})
    return {"check": table, "forms": forms}


# ---------------------------------------------------------------------------
# 2. tower
# ---------------------------------------------------------------------------
def tower_golden():
    out = []
    for floor in range(1, 131):
        room = tower.floor_room(floor - 1)
        spec = tower.monster_for(floor) if room.spec else None
        out.append({"floor": floor, "room": jsonable(room), "spec": jsonable(spec),
                    "abilities": spec.abilities if spec else None})
    monsters = [{"key": m.key, "abilities": m.abilities} for m in config.MONSTERS.values()]
    return {"floors": out, "monsters": monsters,
            "xp_table": [config.xp_to_next(n) for n in range(0, 80)]}


# ---------------------------------------------------------------------------
# 2b. daily challenge
# ---------------------------------------------------------------------------
def daily_golden():
    builds = []
    for day in ("2026-01-15", "2026-02-28", "2026-03-01", "2026-11-11", "2026-11-12", "2027-07-04", "2028-02-29"):
        for tier in (2, 5, 13, 22, 47, 80):
            d = daily.build(day, tier)
            builds.append({"day": day, "tier": tier, "twist": list(daily.twist_for(day)),
                           "dungeon": {"name": d.name, "description": d.description, "kind": d.kind,
                                       "min_level": d.min_level, "complete_xp": d.complete_xp,
                                       "complete_coins": d.complete_coins, "reward_scale": d.reward_scale,
                                       "rooms": jsonable(d.rooms)}})
    rng = [daily.Rng(daily.hash32(t)).next() for t in ("x", "rooms:2026-11-11", "twist:2026-11-11", "")]
    return {"builds": builds, "hashes": {t: daily.hash32(t) for t in ("x", "rooms:2026-11-11", "")}, "rng": rng,
            "streak": [daily.streak_bonus(n) for n in range(0, 12)], "tiers": [daily.tier_for(n) for n in range(1, 90)],
            "yesterday": {d: daily.yesterday(d) for d in ("2026-03-01", "2026-01-01", "2028-03-01")}}


# ---------------------------------------------------------------------------
# 3. playthroughs
# ---------------------------------------------------------------------------
class Runner:
    def __init__(self, name, initial_state, seed, level_scheme=0):
        self.name, self.seed, self.initial_state = name, seed, initial_state
        self.tmp = Path(tempfile.mkdtemp())
        shutil.copy(EXAMPLES, self.tmp / "examples.json")
        shutil.copy(WORDS, self.tmp / "words.json")
        if initial_state is not None:
            (self.tmp / "dungeon_progress.json").write_text(json.dumps(initial_state), encoding="utf-8")
        self.deck = fc.FlashcardDeck.from_json(self.tmp / "words.json")
        self.levels = [[None, 0, 1, 2, 3, 4][(i * 7 + level_scheme) % 6] for i in range(len(self.deck.words))]
        for w, lv in zip(self.deck.words, self.levels):
            w.level = lv
        self.rng = RecRandom(seed)
        self.m = GameManager(self.deck, self.tmp / "dungeon_progress.json", rng=self.rng, today=lambda: TODAY)
        self.steps = []
        self.init = {"snap": self.snap_mini(), "full": self.snap_full(), "draws": len(self.rng.log)}

    # -- snapshots
    def snap_mini(self):
        m, b = self.m, self.m.battle
        out = {"player": jsonable(m.player), "dungeon": m.dungeon.key if m.dungeon else None, "battle": None}
        if b:
            out["battle"] = {
                "monster_key": b.monster.spec.key, "monster_hp": b.monster.hp, "spec": jsonable(b.monster.spec),
                "state": b.state, "ward": b.ward, "phoenix": b.phoenix, "time_bonus": b.time_bonus,
                "xp_mult": b.xp_mult, "coin_mult": b.coin_mult, "consecutive_wrong": b.consecutive_wrong,
                "questions_asked": b.questions_asked, "question": jsonable(b.question),
                "companion": b.companion, "heal_on_correct": b.heal_on_correct,
                "bonus_damage": b.bonus_damage, "dodge_pct": b.dodge_pct,
                "correct_count": b.correct_count, "hard_correct": b.hard_correct}
        return out

    def snap_full(self):
        m = self.m
        saved = m.repo.path
        state = json.loads(saved.read_text(encoding="utf-8")) if saved.exists() else None
        # deep copy: the manager mutates these dicts later, and the snapshot must not change with them
        return copy.deepcopy({"stats": m.stats, "run": m.run, "missed": m.missed.to_dict(), "progress": m.progress,
                              "inventory": m.inventory.to_dict(), "saved_fight": m._saved_fight,
                              "outcome": jsonable(m.outcome), "recent": list(m.selector._recent),
                              "only_missed": m.selector.only_missed, "state": state,
                              "missed_count": m.missed_count, "has_words": m.has_words})

    # -- one action
    def step(self, op, *args):
        m = self.m
        try:
            if op == "shop":
                res = [{"key": e.item.key, "count": e.count, "owned": e.owned, "equipped": e.equipped,
                        "problem": e.problem, "price": e.price} for e in m.shop()]
            elif op == "sellable":
                res = [{"key": e.item.key, "count": e.count, "value": e.value, "equipped": e.equipped}
                       for e in m.sellable()]
            elif op == "usable_items":
                res = [[i.key, n] for i, n in m.usable_items()]
            elif op == "dungeons":
                res = jsonable(m.dungeons())
            elif op == "respec_cost":
                res = m.respec_cost
            elif op == "current_room":
                res = jsonable(m.current_room())
            else:
                res = jsonable(getattr(m, op)(*args))
        except (ValueError, RuntimeError) as exc:
            res = {"error": str(exc)}
        rec = {"op": op, "args": list(args), "result": res, "snap": self.snap_mini(),
               "draws": len(self.rng.log)}
        if len(self.steps) % 8 == 0 or op in ("select_dungeon", "enter_room", "retry", "leave", "buy", "sell"):
            rec["full"] = self.snap_full()
        self.steps.append(rec)
        return res

    def finish(self):
        for q in ("dungeons", "shop", "sellable", "usable_items"):
            self.step(q)
        self.steps[-1]["full"] = self.snap_full()
        return {"name": self.name, "seed": self.seed, "initial_state": self.initial_state, "levels": self.levels,
                "init": self.init, "steps": self.steps, "rng": self.rng.log}


def fight(r, pol, p_correct=0.8, p_item=0.0, p_skip=0.05, max_questions=300):
    """Play the current fight until it is won or lost."""
    m = r.m
    n = 0
    while m.battle is not None and m.battle.state == ACTIVE and n < max_questions:
        n += 1
        q = r.step("next_question")
        if q is None:
            break
        qo = m.battle.question
        if p_item and m.inventory.counts and pol.random() < p_item:
            key = pol.choice(sorted(m.inventory.counts))
            r.step("use_item", key)
            if m.battle.state != ACTIVE or m.battle.question is None:
                continue
        roll = pol.random()
        if roll < p_correct:
            alts = [qo.answer, answers.primary(qo.answer, qo.reverse),
                    fc._strip_accents(answers.primary(qo.answer, qo.reverse))]
            prim = answers.primary(qo.answer, qo.reverse)
            if len(prim) >= 7:
                alts.append(prim[:3] + prim[4:])      # one typo
            r.step("answer", pol.choice(alts))
        elif roll < p_correct + p_skip:
            r.step("skip")
        elif qo.time_limit and roll < p_correct + 2 * p_skip:
            r.step("timeout")
        else:
            r.step("answer", pol.choice(["zzzz", "", "nie wiem", "the wrong thing"]))


def run_dungeon(r, pol, key, restart=False, floors=None, max_defeats=4, **kw):
    m = r.m
    res = r.step("select_dungeon", key, restart)
    if isinstance(res, dict) and "error" in res:
        return
    defeats, rooms = 0, 0
    while rooms < (floors or 60):
        room = m.current_room()
        if room is None:
            break
        r.step("enter_room")
        rooms += 1
        if room.is_fight:
            fight(r, pol, **kw)
            while m.battle is not None and m.battle.state == DEFEAT:
                defeats += 1
                if defeats > max_defeats:
                    r.step("leave")
                    return
                r.step("retry")
                fight(r, pol, **kw)
            if m.battle is None:
                return


def player_state(level=1, coins=0, hp=None, **extra):
    max_hp = 30 + 10 * (level - 1)
    return {"version": 2, "player": {"name": "Adventurer", "level": level, "xp": 0, "hp": hp if hp is not None else max_hp,
                                      "max_hp": max_hp, "coins": coins, "gear_hp": 0}, **extra}


CONSUMABLES = ["letter_scroll", "count_rune", "oracle_eye", "small_potion", "big_potion", "fire_bomb", "lightning",
               "meteor", "ward_scroll", "passage_scroll", "wisdom_tome", "golden_idol"]


def scenarios():
    out = []

    # S1: fresh game, the Cellar, then a first shopping trip
    r = Runner("cellar_fresh", None, 11)
    pol = random.Random(101)
    run_dungeon(r, pol, "cellar", p_correct=0.85)
    r.step("buy", "small_potion"); r.step("buy", "wooden_sword"); r.step("buy", "meteor"); r.step("sell", "wooden_sword")
    out.append(r.finish())

    # S2: Whispering Forest with a started kit and lots of item use
    st = player_state(6, 300, inventory={"items": {k: 3 for k in CONSUMABLES}, "owned": ["wooden_sword", "leather_vest", "lucky_clover"],
                                         "equipped": {"weapon": "wooden_sword", "armor": "leather_vest", "charm": "lucky_clover"}},
                      missed={"bać się": 0, "czajnik": 1})
    r = Runner("forest_items", st, 22, level_scheme=1)
    run_dungeon(r, random.Random(102), "forest", p_correct=0.72, p_item=0.25)
    out.append(r.finish())

    # S3: Library of Sentences (cloze fights)
    st = player_state(8, 500, inventory={"items": {"small_potion": 5, "oracle_eye": 2, "passage_scroll": 3, "ward_scroll": 2},
                                         "owned": ["iron_sword", "chainmail", "time_amulet"],
                                         "equipped": {"weapon": "iron_sword", "armor": "chainmail", "charm": "time_amulet"}})
    r = Runner("library_cloze", st, 33, level_scheme=2)
    run_dungeon(r, random.Random(103), "library", p_correct=0.7, p_item=0.2)
    out.append(r.finish())

    # S4: Frozen Citadel with companions
    st = player_state(12, 2000, inventory={"items": {k: 2 for k in CONSUMABLES},
                                           "owned": ["steel_blade", "plate_armor", "sages_ring", "pixie", "owl"],
                                           "equipped": {"weapon": "steel_blade", "armor": "plate_armor", "charm": "sages_ring", "companion": "pixie"}})
    r = Runner("citadel_gear", st, 44, level_scheme=3)
    run_dungeon(r, random.Random(104), "citadel", p_correct=0.8, p_item=0.12)
    r.step("equip", "owl"); r.step("unequip", "charm")
    out.append(r.finish())

    # S5: Review dungeon (only missed words), played twice
    words = json.loads(WORDS.read_text(encoding="utf-8"))
    missed = {w["word"]: i % 2 for i, w in enumerate(words[:30])}
    st = player_state(5, 100, missed=missed)
    r = Runner("review_missed", st, 55, level_scheme=4)
    pol = random.Random(105)
    run_dungeon(r, pol, "review", p_correct=0.8)
    run_dungeon(r, pol, "review", restart=True, p_correct=0.8)
    out.append(r.finish())

    # S6: Endless Tower with full tower gear: bosses, loot, enrage, cloze floors
    st = player_state(25, 50, inventory={"items": {"small_potion": 20, "big_potion": 10, "passage_scroll": 9},
                                         "owned": ["tower_blade", "tower_mail", "tower_crown", "stormcaller", "titan_plate", "chrono_amulet", "baby_dragon", "phoenix_feather"],
                                         "equipped": {"weapon": "stormcaller", "armor": "titan_plate", "charm": "chrono_amulet", "companion": "baby_dragon"}})
    r = Runner("tower_climb", st, 66, level_scheme=5)
    run_dungeon(r, random.Random(106), "tower", floors=24, p_correct=0.9, p_item=0.05)
    out.append(r.finish())

    # S7: a weak player: defeats, retries, leaving mid-fight and resuming
    r = Runner("defeat_retry_resume", None, 77)
    pol = random.Random(107)
    r.step("select_dungeon", "cellar", False); r.step("enter_room")
    fight(r, pol, p_correct=0.1, p_skip=0.2, max_questions=40)
    if r.m.battle and r.m.battle.state == DEFEAT:
        r.step("retry")
    r.step("next_question"); r.step("leave")
    r.step("select_dungeon", "forest", False)     # level too low
    r.step("select_dungeon", "cellar", False); r.step("enter_room")   # resumes with the saved monster hp
    fight(r, pol, p_correct=0.9)
    r.step("retry")                                # not defeated -> error
    out.append(r.finish())

    # S8: shop script with every kind of error
    st = player_state(14, 9000, inventory={"items": {"small_potion": 98}, "owned": ["pixie"], "equipped": {"companion": "pixie"}})
    r = Runner("shop_script", st, 88)
    r.step("shop"); r.step("sellable")
    for key in ["small_potion", "small_potion", "iron_sword", "iron_sword", "tower_blade", "meteor", "dragon_fang", "steel_blade",
                "dragon_scale", "plate_armor", "time_amulet", "phoenix_feather", "baby_dragon", "hawk", "owl", "golden_idol"]:
        r.step("buy", key)
    for key in ["steel_blade", "iron_sword", "nonexistent_is_skipped"] [:2]:
        r.step("equip", key)
    r.step("equip", "stormcaller"); r.step("unequip", "weapon"); r.step("unequip", "weapon"); r.step("equip", "hawk")
    for key in ["small_potion", "iron_sword", "hawk", "dragon_fang", "pixie", "meteor", "golden_idol"]:
        r.step("sell", key)
    for key in ["use_item"]:
        r.step("use_item", "small_potion")        # not in a fight
        r.step("use_item", "iron_sword")          # equipment
    r.step("shop"); r.step("sellable")
    out.append(r.finish())

    # S9: phoenix feather, dodge and a starting ward, with a player who often errs
    st = player_state(10, 0, inventory={"items": {"ward_scroll": 4, "small_potion": 6, "fire_bomb": 6},
                                         "owned": ["phoenix_feather", "shadow_cat", "stone_turtle", "iron_sword"],
                                         "equipped": {"charm": "phoenix_feather", "companion": "shadow_cat", "weapon": "iron_sword"}})
    r = Runner("phoenix_dodge", st, 99, level_scheme=1)
    pol = random.Random(109)
    run_dungeon(r, pol, "cellar", p_correct=0.35, p_item=0.3, max_defeats=6)
    r.step("equip", "stone_turtle")
    run_dungeon(r, pol, "cellar", restart=True, p_correct=0.4, p_item=0.1, max_defeats=6)
    out.append(r.finish())

    # S9b: a lethal hit with a Phoenix Feather equipped (very low HP to start with)
    st = player_state(5, 0, hp=3, inventory={"items": {"small_potion": 2}, "owned": ["phoenix_feather"], "equipped": {"charm": "phoenix_feather"}})
    r = Runner("phoenix_lowhp", st, 98, level_scheme=3)
    run_dungeon(r, random.Random(119), "cellar", p_correct=0.2, p_skip=0.3, max_defeats=3)
    out.append(r.finish())

    # S9c: tower with ordinary gear: new boss loot at floors 10 and 20, bundles later
    st = player_state(22, 0, inventory={"items": {"small_potion": 30, "big_potion": 5}, "owned": ["dragon_fang", "dragon_scale", "time_amulet"],
                                         "equipped": {"weapon": "dragon_fang", "armor": "dragon_scale", "charm": "time_amulet"}})
    r = Runner("tower_loot", st, 97, level_scheme=2)
    run_dungeon(r, random.Random(120), "tower", floors=32, p_correct=0.92, p_item=0.04)
    r.step("shop"); r.step("sellable")
    out.append(r.finish())

    # S9d: deep Tower climb with abilities (floors 15-50), items used, thief coins, poison, silence
    st = player_state(40, 120, inventory={"items": {"small_potion": 40, "big_potion": 20, "passage_scroll": 9},
                                          "owned": ["tower_blade", "tower_mail", "tower_crown"],
                                          "equipped": {"weapon": "tower_blade", "armor": "tower_mail", "charm": "tower_crown"}})
    st["dungeons"] = {"tower": {"room": 13, "best": 13}}
    r = Runner("tower_abilities", st, 131, level_scheme=5)
    run_dungeon(r, random.Random(131), "tower", floors=40, p_correct=0.75, p_item=0.15, max_defeats=6)
    out.append(r.finish())

    # S9e: library dungeon: shields, poison, silence, curse, thief
    st = player_state(30, 200, inventory={"items": {"small_potion": 30, "big_potion": 10}, "owned": [], "equipped": {}})
    r = Runner("library_abilities", st, 132, level_scheme=2)
    run_dungeon(r, random.Random(132), "library", p_correct=0.7, p_item=0.2, max_defeats=6)
    out.append(r.finish())

    # S9f: the Sunken Cathedral (many abilities per monster, cloze mixed with word questions)
    st = player_state(26, 300, inventory={"items": {"small_potion": 40, "big_potion": 15}, "owned": ["dragon_fang", "dragon_scale", "time_amulet"],
                                           "equipped": {"weapon": "dragon_fang", "armor": "dragon_scale", "charm": "time_amulet"}})
    r = Runner("cathedral", st, 133, level_scheme=2)
    run_dungeon(r, random.Random(133), "cathedral", p_correct=0.8, p_item=0.15, max_defeats=6)
    out.append(r.finish())

    # S11: a hero who put points into every stat, in the Forest (timed questions, armor) with items
    stats = {"strength": 12, "constitution": 9, "dexterity": 30, "intelligence": 14, "charisma": 20, "wisdom": 25}
    st = player_state(9, 400, inventory={"items": {"small_potion": 5, "fire_bomb": 5, "lightning": 3, "wisdom_tome": 1},
                                         "owned": ["iron_sword", "shadow_cat"], "equipped": {"weapon": "iron_sword", "companion": "shadow_cat"}})
    st["player"].update({"stats": stats, "stat_points": 0, "stat_hp": 45, "max_hp": 30 + 80 + 45, "hp": 30 + 80 + 45, "respecs": 0})
    r = Runner("stats_build_forest", st, 111, level_scheme=1)
    run_dungeon(r, random.Random(121), "forest", p_correct=0.7, p_item=0.3)
    r.step("shop"); r.step("sellable")
    for key in ("iron_sword", "chainmail", "lucky_clover", "small_potion", "meteor"):
        r.step("buy", key)
    r.step("sell", "iron_sword")
    out.append(r.finish())

    # S12: spending points (with every error), a respec, and stat-built fights in the Review and Cellar
    words = json.loads(WORDS.read_text(encoding="utf-8"))
    st = player_state(7, 30, missed={w["word"]: 0 for w in words[:8]})     # a save from before stats: 12 points are granted
    r = Runner("stats_spend_respec", st, 112, level_scheme=2)
    for stat, n in (("strength", 3), ("constitution", 4), ("wisdom", 2), ("luck", 1), ("charisma", 0), ("charisma", 99), ("dexterity", 3)):
        r.step("spend_point", stat, n)
    r.step("respec_cost")
    r.step("respec")                                       # free the first time
    r.step("respec")                                       # nothing to take back
    r.step("spend_point", "constitution", 6); r.step("spend_point", "charisma", 6)
    r.step("respec")                                       # no coins for the second one
    r.step("shop")
    pol = random.Random(122)
    run_dungeon(r, pol, "review", p_correct=0.75)
    r.step("select_dungeon", "cellar", False); r.step("enter_room")
    r.step("spend_point", "strength", 1)                   # not during a fight
    r.step("respec")
    fight(r, pol, p_correct=0.8)
    r.step("respec_cost")
    out.append(r.finish())

    # S13: a pure Dexterity hero who is often wrong: dodges, and the dodged words are still missed words
    st = player_state(10, 0)
    st["player"].update({"stats": {"dexterity": 80}, "stat_points": 0})
    r = Runner("stats_dodge", st, 113, level_scheme=3)
    run_dungeon(r, random.Random(123), "cellar", p_correct=0.3, p_item=0.0, max_defeats=6)
    out.append(r.finish())

    # S10: damaged or odd save files
    odd = {
        "garbage_types": {"version": "x", "player": {"name": 5, "level": "9", "xp": -4, "hp": 99999, "max_hp": "big", "coins": True},
                          "dungeons": {"cellar": {"room": 999, "completed": "yes", "times": -1}, "tower": {"room": 5, "best": 7}},
                          "stats": {"correct_answers": 4, "wrong_answers": "x"}, "run": [], "missed": {"pies": 5, 3: 1, "kot": True},
                          "inventory": {"items": {"small_potion": 500, "nope": 3, "ward_scroll": -2}, "owned": ["iron_sword", "ghost", "scholars_monocle"],
                                        "equipped": {"weapon": "iron_sword", "armor": "iron_sword", "bogus": "x"}},
                          "fight": "nothing"},
        "garbage_stats": player_state(6, 0, hp=50) | {"player": {"level": 6, "max_hp": 80, "hp": 80, "stats": {"strength": -3, "wisdom": "x", "dexterity": 2.5, "charisma": 4},
                                                                  "stat_points": "many", "stat_hp": 9999, "respecs": -1}},
        "dead_player_saved_fight": player_state(3, 10, hp=0, fight={"dungeon": "cellar", "room": 1, "monster_hp": 7}),
        "resume_saved_fight": player_state(3, 10, fight={"dungeon": "cellar", "room": 2, "monster_hp": 5},
                                           dungeons={"cellar": {"room": 2, "completed": False, "times": 0, "best": 0}}),
        "finished_dungeon_restart": player_state(2, 0, dungeons={"cellar": {"room": 8, "completed": True, "times": 3, "best": 0}}),
    }
    for name, st in odd.items():
        r = Runner("odd_save_" + name, st, 5, level_scheme=2)
        r.step("dungeons")
        r.step("select_dungeon", "cellar", False)
        r.step("enter_room")
        if r.m.battle:
            r.step("next_question")
            r.step("skip")
            r.step("leave")
        r.step("select_dungeon", "review", False)
        r.step("select_dungeon", "tower", False)
        out.append(r.finish())
    return out


if __name__ == "__main__":
    golden = {"answers": answers_golden(), "tower": tower_golden(), "daily": daily_golden(), "scenarios": scenarios()}
    out = ROOT / "tests" / "dungeon_golden.json"
    out.write_text(json.dumps(golden, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    size = out.stat().st_size / 1e6
    print(f"wrote {out.relative_to(ROOT)} ({size:.1f} MB):", len(golden["answers"]["check"]), "answer checks,",
          sum(len(s["steps"]) for s in golden["scenarios"]), "steps in", len(golden["scenarios"]), "scenarios")
    for s in golden["scenarios"]:
        print(f"  {s['name']:34s} {len(s['steps']):4d} steps {len(s['rng']):5d} draws")
