// Data tables of the sprite port (generated once from dungeon/sprites*.py; palettes already merged).

export type Palette = Record<string, string>;

/** Hand-drawn left halves (32 rows max); only used for keys without a procedural drawing. */
export const ART: Record<string, string[]> = {
  "hero": ["o...............", "oo.........ooooo", "ohoo......ohhHHH", ".ohoo....ohHHHHH", "..ohoo..ohhHHHHH", "...ohooohhhhhhHH", "....oooohhhhhhhh", ".....ohhhhhhhhhh", ".....ohhhhhhhhhh", ".....ohhooeeeeee", ".....ohhhhhhhhhh", ".....ohhhHhhhohh", "......ohhhhhhooo", ".....ooohhhhhhHH", "..ooooHHHHhhhKKK", ".oHHHHoHHhhKKKKK", "ohHHhhoKKKKKKKgg", "ohhhhhooKKKKKKgg", "oHhhhoooKKKKKKKg", ".ooooorrKKKKKKKK", "..orrrrrbbbbbbbb", "..orrrrrbbggbbgg", "..orrrrrKKKKKKKK", "..orrrrohhhhhhhh", "..orrrrohhhhhhHH", "...orrroohhhhhhh", "....ooo.ohhhhho.", ".......ohhHhhho.", ".......ohhhhhho.", "......obbbbbbbo.", "......ooooooooo."],
  "slime": ["oooooo", "ooGGGGgg", "oGGGgggggg", "oGGggggggggg", "ogggwwggggggg", "ogggweggggggg", "oggggggggggggg", "oggggggggggoooo", "ogggggggggggggg", "ogggggggggggggg", "oggggggggggggggg", "oooooooooooooooo"],
  "goblin": ["ooo......oooooo", "oGgo....oGGGgggg", "ogggoooogggggggg", ".ogggggggggggggg", "..oogggeeggggggg", "...ogggggggggggg", "....oggggwgwgggg", "....oogggooooooo", "......ooggggggg", "....ooobbbbbbbbb", "...obbbbbbbbbbbb", "..ogbbbbbbbbbbbb", "..ogbbbbbbbbyyyy", "..oggbbbbbbbbbbb", "...oggbbbbbbbbbb", "...ooobbbbbbbbbb", "....oggggggggo..", "....oggggggggo..", "...oobbbbbbbbo..", "...ooooooooooo.."],
  "skeleton": ["........oooooooo", ".......owwwwwwww", "......owwwwwwwww", "......owwwwwwwww", "......owwoooowww", "......owwoeeowww", "......owwoooowww", "......owwwwwwwww", ".......owwwwwwoo", "........owowowow", "........oooooooo", "..........oowwww", "...ooooowwwwwwww", "..owwwwowwwwwwoo", "..owdddowdddddoo", "..owwwwowwwwwwoo", "...owwwowwwwwwoo", "...owddowdddddoo", "....owwowwwwwooo", ".....oooowwwwooo", ".....owwwooowwoo", "....owwo.owwwwwo", "....owo..owwwwwo", "....owo..owdwwwo", "....owo...owwwwo", "...oowo...owwwwo", "..owwwo...oowwwo"],
  "dark_knight": [".........ppppppp", "........pppppppp", ".......ppppppppp", "......oooooooooo", ".....okkkkkkkkkk", ".....okkKKKKKKKK", ".....okkkkkkkkkk", ".....okkorrrrrrr", ".....okkkkkkkkkk", ".....okkkkkkooook", "......ookkkkkkkk", "....oooookkkkkkk", "..oKKKKKkkkkkkkk", ".oKKkkkKKkkkkkkk", "ooKkkkkkKkkkkppk", "oKkkkkkkkkkkkkpp", "ooKkkkkokkkkkkkk", ".oooooorkkkkkkkk", "..oppppobbbbbbbb", "..oppppokkkkkkkk", "..oppppokkkkkkkk", "...opppookkkkkkkk", "....ooo.okkkkko.", ".......okkKkkko.", ".......okkkkkko.", "......okkkkkkko.", "......ooooooooo."],
  "boss": ["y...............", "yy..............", "oyy......ooo....", ".oyy....oyyyo...", ".oyyoooooyyyoooo", "..oyyooRRRRRRRRR", "...oyoRRRRRRRRRR", "....ooRRrRRRRRRR", ".....oRReeRRRRRR", ".....oRRReeRRRRR", ".....oRRRRRRRRRR", ".....oRRwRRwRRRR", "......oRwwRwwRww", "......ooRRRRRRRR", ".....ooRRRRRRRRR", "..oooRRRRRrrRRRR", ".oRRRRRRRrrrrRRR", "oRRRRRRRrrrrrrrr", "oRRRRRRrrrrrrrrr", "oRRRRRrrrrrrrrrr", "oRRRRRrrrrrrrrrr", ".oRRRRrrrrrrrrrr", ".ooRRRrrrrrrrrrr", "..oRRRRrrrrrrrrr", "..oRRRRRroooooo.", "..ooRRRRRo......", "...oooooooo....."],
  "bat": ["o...............", "oo......o.....o.", "oPo.....opo..opp", "oPPo....oprooprr", "oPPPo...opwoopww", "oPPPPo..oppppppp", "oPPPPPooopppppPp", "oPPPPPPPPpppppPp", ".oPoPPPPPPpppppp", ".oP.oPPPPpppppp.", "..o..oPPoppppp..", ".....ooo.opppp..", "..........ooppp.", "...........oppo.", "............ooo."],
  "wolf": ["o.....o.........", "oo...oGo.....o.o", "oGoooGGgo...oGgo", "oGGGGGggoooooGgg", ".oGGgggggggggggg", "..ogggggggggggge", "..oggggggeegggge", "..ogggggggggggww", "...ogggggGGgggww", "...oggggooGGooww", "....oggggoowwwoo", "....ooggGGGggggg", "...oogggGGGGgggg", "..ogggggGGGGgggg", "..ogggggggggggog", "..oggggggggggoog", "..ogggggggggggg.", "..oggo.oggggggo.", "..ogGo.oggggggo.", "..ooo..ooooooo.."],
  "treant": ["..g.g.gG.G.g.gGg", ".gGgGgGgGgGgGgGg", "gGgGgGgGgGgGgGgG", ".ogGgGgGgGgGgGgG", "..obbbbbbbbbbbBB", "..obbbbbbbbbBBBB", "..obeebbbbbbbbBB", "..obeebbbbbbbbBB", "..obbbbbbbbbbBBB", "..obbbbooooooobb", "...obbbbbbbbbbBB", "..obbbBBbbbbbbBB", ".obbbbbBBbbbbbBB", "obbbBbbbBbbbbbBB", "obbBBbbbBBbbbbbB", "obbbBbbbbBbbbbbb", ".obbbbbbbbbbBbbb", ".obbbbbbbbbbbbbb", "..obbbbboobbbbbb", "..obbbo..obbbbbb", ".obbbo...obbbbbb", ".obbbbo..oobbbbb", ".ooooooo..ooooo."],
  "witch": ["..............oo", ".............opp", "............oppp", "...........opppp", "..........oppPPP", ".........opppPPp", "........oppppppp", "...oooooooooooPp", "....oooppppppppp", "......ogggggggggg", "......oggeeggggg", "......ogggggggggg", ".......oggwwgggg", "......ooogggggggg", ".....oppoooooooo", "....oppppppPPPPP", "...opppppppPPPPP", "..oppppPPppppppp", "..oppppPPppppppp", ".opppppppppppppp", ".opppppppppppyyp", ".opppppppppyyyyy", ".oppppppppppppyy", "..oppppppppppppp", "..ooppppppppppp.", "....oooooooooooo"],
  "golem": ["...oooooooooooo", "..oIIIIIIIIiiiii", "..oIIiiiiiiiiiii", "..oIiiiiiiiiiiii", "..oiiiieeeiiiiii", "..oiiiieeeiiiiii", "..oiiiiiiiiiiiii", "...oooiiiiooooii", ".oooIIIioiiiiiii", "oIIIIIiiiiiibbbb", "oIIIiiiiiibbbbbb", "oIIiiiiibbbbbbbb", "oIIiiiibbbbbbbbb", "ooIiiiibbbbbbbbb", ".oiiiiibbbbbbbbb", ".ooiiiiiibbbbbbb", "..oiiiiiiibbbbbb", "..oiiiiiiiiibbbb", "..oiiiiiiiiiiibb", "..oiiiiiiiiiiiii", "..oiiiioo.oiiiii", "..oiiiio...oiiii", "..oooooo...ooooo"],
  "wraith": ["......oooooooooo", ".....occcccccccc", "....occccccccccc", "...occckkkkkkkkk", "...occkkkkkkkkkk", "...occkkeeekkkkk", "...occkkeeekkkkk", "...occkkkkkkkkkk", "...occckkkkkkkkk", "....occcckkkkkkk", "....occcccccckkk", "...occccCccccccc", "..occcccccCccccc", "..occcccCcccccCc", ".occcCccccccCccc", ".occcccccCccccCc", "occcccCccccccccc", "occcccccccCccccc", "occCcccccccccccc", ".occcccccCcccccc", ".occccCcccccccCc", "..occccccCccccc.", "..ococcccocccoc.", "...o.ooc.oo.o.o."],
  "dragon": ["o...............", "oo....o.........", "ogo..ogo.....oo.", "ogGoogGGo...ogGo", ".oggggGGGoooogGg", ".ogggggggggggggg", ".ogeegggggggggge", ".oggggggggggggww", "..ogggggggggwwww", "..oogggggrrrrrrr", "...oggggggrrrrrr", "..oggGGGgggggggg", ".ogggGGGGggggggg", "ogGGgGyyyyGGgggg", "ogGGyyyyyyyyGGgg", "ogGyyyyyyyyyyGGg", "ogGyyyyyyyyyyGGg", "ogGGyyyyyyyyGGgg", ".ogGGyyyyyyGGggg", ".oggGGGGGGGGggg.", "..oggdoooooodogg", "..oddo.....oddog", "..oooo......oooo"],
};

/** 16x16 left halves; only used for keys without a procedural drawing or ART entry. */
export const HALVES: Record<string, string[]> = {
  "hero": ["oh......", "ohh..ooo", ".ohooHHH", "..ohHHHH", "..ohhhhh", "..ohoeee", "..ohhhhh", ".oooohhh", "oHHoKKKK", "oHHoKgKK", "ohhoKKKK", ".orrKbbb", ".orrKKKK", "..orhhhh", "..oohhhh", "..ooobbb"],
  "slime": ["........", "........", "........", "......oo", "....oogg", "...ogGGg", "..ogGggg", "..oggwwg", "..oggewg", "..ogggoo", ".oggggg.", ".ogggggg", ".ooooooo", "........", "........", "........"],
  "goblin": ["........", "........", "......oo", "....ooGg", "oo.oGggg", "ogoggggg", ".oggyegg", ".ogggggg", "..ogwgwg", "..oobbbb", ".obbbbbb", ".ogbbbbb", "..obbbbb", "..oggo..", "..oggo..", "..oooo.."],
  "skeleton": ["........", "....oooo", "...owwww", "...owwww", "...oweew", "...oweew", "...owwwo", "....owow", "....oooo", "..owwwwo", "..oooooo", "..owwwwo", "..oooooo", "...owwo.", "...owwo.", "..oowwoo"],
  "dark_knight": ["......pp", "......pp", "....oooo", "...okkkk", "...okkkk", "...orrrr", "...okkkk", "..oookkk", ".oKKkkkk", ".oKkkkkk", ".okkkkkk", ".okkkkkk", "..okkkkk", "..okkko.", "..okkko.", "..ooooo."],
  "boss": ["y.......", "yy......", "oyy.oooo", ".oyoRRRR", ".oRRRRRR", ".oRRyeRR", ".oRRRRRR", "..oRwRRw", "..ooRRRR", "ooRRRRRR", "oRRRrrrr", "oRRrrrrr", "oRRrrrrr", ".ooRrrrr", "..oRRRo.", "..ooooo."],
  "bat": ["........", ".....o..", ".....opp", ".....orp", ".o...opp", "oPo..opw", "oPPo.oop", "oPPPooPp", "oPoPPPpp", ".o.oPPpp", "...ooPpp", ".....oop", "......oo", "........", "........", "........"],
  "wolf": ["........", "..o...o.", "..oo.ooG", "..oGoGgg", "..oggggg", "..ogyegg", "..oggggg", "...ogGGG", "...ogowo", "....ogGG", "...oggGg", "..ogggGG", "..ogggGg", "..oggoog", "..ogo..o", "..ooo..."],
  "treant": ["..g.g.gG", ".gGgGgGg", "gGgGgGgG", ".ogGgGgG", "..obbbBB", "..obebBB", "..obbbBB", "..obbyBB", "...obbbB", "..obbBBB", ".obbBBBB", ".obbBbBB", "..obBBbB", "..obbBbb", "..obbo.o", "..oooo.."],
  "witch": [".......o", "......op", ".....opp", "....oppp", "...opPPP", "..oppPpp", ".oooooPp", "...ogggg", "...ogeeg", "...oggwg", "....oopp", "..opppPp", ".oppPppP", ".opppppp", "..opppyy", "..oooooo"],
  "golem": ["........", "...ooooo", "..oIIIii", "..oIiiii", "..oieeii", "..oiiiii", "..oobbbb", ".ooIIiii", "oIIiiibb", "oIiiibbb", "oIiibbbb", "ooiibbbb", "..oiiiib", "..oiiioo", "..oiiio.", "..ooooo."],
  "wraith": ["........", "....oooo", "...occcc", "..occkkk", "..ockeek", "..ockeek", "..occkkk", "..ocCcCc", "..occCcC", ".occcCcc", ".occcccC", "occcccCc", "occcCccc", ".ocCcccC", "..occcCc", "...o.occ"],
  "dragon": ["o.......", "oo..o..o", "ogo.ogoG", "ogGoggGG", ".oggggGG", ".ogeegGG", ".oggggGG", "..ogwgww", "..oggrrr", "..oogggg", ".ogGGGgg", "ogGGyyGg", "ogGyyyyg", "ogGGyyyG", ".ogdoogg", "..ooo.oo"],
  "treasure": ["........", "........", "........", "........", "........", "..oooooo", ".obbbbbb", ".obbbbbb", ".ooooooo", ".obbbbbb", ".obbbbyy", ".obbbbbb", ".ooooooo", "........", "........", "........"],
  "rest": ["........", "........", ".......y", "......yy", "......yr", ".....yrr", ".....yyr", "....yyrr", "....yyyr", "...yyrrr", "..bbbyyy", ".bbbbbbb", "bbbooooo", "........", "........", "........"],
};

/** Palettes of the procedural sprites (the dark ones; they override the older ones in sprites.py). */
export const PALETTES: Record<string, Palette> = {
  "hero": {"o": "#0b0912", "h": "#6a7186", "H": "#b4bccf", "K": "#3c4152", "r": "#6e1520", "e": "#ff9a2e", "g": "#b8903a", "b": "#2e2118", "s": "#8a6a4a"},
  "slime": {"o": "#0b0912", "g": "#2f6a3a", "G": "#7bc07b", "w": "#e8ffe8", "e": "#b6ff3a"},
  "goblin": {"o": "#0b0912", "g": "#48642e", "G": "#7a9854", "y": "#b8943a", "e": "#ff5a2e", "w": "#d8d0b8", "b": "#47301a"},
  "skeleton": {"o": "#0b0912", "w": "#c4bca2", "d": "#6e6856", "e": "#ff3b2e"},
  "dark_knight": {"o": "#0b0912", "b": "#2e2118", "k": "#22242f", "K": "#555972", "r": "#ff3b2e", "p": "#6a1626"},
  "boss": {"o": "#0b0912", "R": "#7a1616", "r": "#3f0c0c", "y": "#d9ccb0", "e": "#ffd23a", "w": "#ddd2b8"},
  "bat": {"o": "#0b0912", "p": "#3a2458", "P": "#684a96", "r": "#ff3b2e", "w": "#e8e0c8"},
  "wolf": {"o": "#0b0912", "g": "#464a5c", "G": "#858aa0", "w": "#e8e0c8", "y": "#d9b44a", "e": "#ff4a2e", "r": "#a82828"},
  "treant": {"o": "#0b0912", "b": "#3a2612", "B": "#664422", "g": "#1f4a26", "G": "#3f7a3a", "y": "#d9b44a", "e": "#ff9a2e"},
  "witch": {"o": "#0b0912", "p": "#2f1a4d", "P": "#66409a", "g": "#5a8a5a", "y": "#b8903a", "e": "#7dff6a", "w": "#e8e0c8"},
  "golem": {"o": "#0b0912", "i": "#5f8aa2", "I": "#b0d4e6", "b": "#2e5670", "e": "#5aa0ff", "w": "#e8f4ff"},
  "wraith": {"o": "#0b0912", "c": "#334270", "C": "#7a90c8", "e": "#7dffb0", "k": "#141a34"},
  "dragon": {"o": "#0b0912", "g": "#27582f", "G": "#4f9456", "y": "#b8903a", "r": "#ff6a1f", "e": "#ffb42e", "w": "#e0d6bc", "d": "#183a1e"},
  "treasure": {"o": "#0b0912", "b": "#6a3e1a", "y": "#d9b44a"},
  "rest": {"o": "#0b0912", "b": "#4a2e18", "y": "#ffd25a", "r": "#e8501a"},
  "pixie": {"o": "#0b0912", "w": "#bfe8ff", "b": "#6a9ac8", "s": "#e8c9a0", "h": "#d94a8a", "g": "#3fae7a", "G": "#8fe8b8", "e": "#ff3b2e"},
  "hawk": {"o": "#0b0912", "g": "#6a4a2a", "G": "#c9a46a", "y": "#e0b83a", "e": "#ff9a2e"},
  "owl": {"o": "#0b0912", "g": "#7a6a52", "G": "#c9b896", "w": "#f2ecd8", "y": "#d9a43a", "e": "#ffb42e"},
  "shadow_cat": {"o": "#0b0912", "g": "#2a2638", "G": "#5a5478", "e": "#7dffb0", "w": "#e8e0c8"},
  "stone_turtle": {"o": "#0b0912", "g": "#5a6270", "G": "#9aa4b4", "s": "#6a7a52", "e": "#ffb42e", "m": "#4f8f4a"},
  "baby_dragon": {"o": "#0b0912", "g": "#a83a2a", "G": "#e0644a", "y": "#e0b86a", "d": "#6a1e1e", "r": "#ff6a1f", "e": "#ffd23a", "w": "#e8e0c8"},
};

/** Same drawing, different colours: key -> [drawing, palette]. */
export const ALIASES: Record<string, readonly [string, Palette]> = {
  "ink_slime": ["slime", {"o": "#0b0912", "g": "#3b3a8f", "G": "#8f8fe0", "w": "#e8ffe8", "e": "#b6ff3a"}],
  "paper_goblin": ["goblin", {"o": "#0b0912", "g": "#e8dcc0", "G": "#fff6de", "y": "#b8943a", "e": "#ff5a2e", "w": "#d8d0b8", "b": "#8a6a3b"}],
  "page_wraith": ["wraith", {"o": "#0b0912", "c": "#b09a6a", "C": "#efe0b0", "e": "#7dffb0", "k": "#3a2f1c"}],
  "tome_knight": ["dark_knight", {"o": "#0b0912", "b": "#2e2118", "k": "#6b3f2a", "K": "#c9a36b", "r": "#7dffb0", "p": "#2f6fd0"}],
  "librarian": ["witch", {"o": "#0b0912", "p": "#9a6a1a", "P": "#e0b24a", "g": "#e8c9a0", "y": "#b8903a", "e": "#7dff6a", "w": "#e8e0c8"}],
  "review_guru": ["witch", {"o": "#0b0912", "p": "#1f6b6b", "P": "#5fd0c0", "g": "#d9c3a0", "y": "#b8903a", "e": "#7dff6a", "w": "#e8e0c8"}],
  "guardian": ["treant", {"o": "#0b0912", "b": "#4b5a2a", "B": "#7a8f3a", "g": "#2f7d3a", "G": "#f2c14e", "y": "#7dffb0", "e": "#0b0912"}],
  "warlord": ["dark_knight", {"o": "#0b0912", "k": "#7a2020", "K": "#d8a64a", "r": "#ffe14d", "p": "#e04848"}],
};

export type ArmorLook = readonly [string, string, string, string, string, string, number, boolean, string | null, string | null];
export const DEFAULT_ARMOR_LOOK: ArmorLook = ["#6a5a48", "#6a5a48", "#3a2f26", "#3a2f26", "#ff9a2e", "none", 0, false, null, null];
export const ARMOR_LOOK: ReadonlyMap<string, ArmorLook> = new Map<string, ArmorLook>([
  ["leather_vest", ["#6a4528", "#8a5e38", "#3a2414", "#b8903a", "#ff9a2e", "cap", 1, false, null, "strap"]],
  ["chainmail", ["#7a8094", "#a6adc0", "#444a5c", "#b8903a", "#ff9a2e", "coif", 2, false, "round", "mail"]],
  ["plate_armor", ["#7c849a", "#c2cadc", "#3c4152", "#c9a24a", "#ff9a2e", "visor", 3, true, "kite", "plate"]],
  ["dragon_scale", ["#2f6a38", "#5aa860", "#183a1e", "#c9a24a", "#ffb42e", "horned", 3, true, "kite", "scale"]],
  ["tower_mail", ["#4a3a62", "#8a74b0", "#221a33", "#e0b84a", "#7dffb0", "crest", 4, true, "tower", "plate"]],
  ["titan_plate", ["#8a5a2a", "#d9a24a", "#3a2412", "#ffd25a", "#ffe14d", "horned", 4, true, "tower", "plate"]],
]);

export type WeaponLook = readonly [string, string, string, number, number, boolean];
export const WEAPON_LOOK: ReadonlyMap<string, WeaponLook> = new Map<string, WeaponLook>([
  ["wooden_sword", ["#7a5230", "#a07848", "#4a3018", 10, 2, false]],
  ["iron_sword", ["#8a90a0", "#c2c8d6", "#5a4630", 12, 2, false]],
  ["steel_blade", ["#aab2c8", "#e4eaf8", "#c9a24a", 13, 2, false]],
  ["runed_blade", ["#8a96b8", "#d0daf8", "#c9a24a", 14, 2, true]],
  ["dragon_fang", ["#d8d2bc", "#fffbe8", "#2f6a38", 15, 3, true]],
  ["tower_blade", ["#d9b44a", "#fff0a8", "#4a3a62", 16, 3, true]],
  ["stormcaller", ["#5a90e0", "#d0f0ff", "#c9a24a", 16, 3, true]],
]);

export const CHARM_COLOURS: ReadonlyMap<string, string> = new Map<string, string>([["lucky_clover", "#4fcf6a"], ["time_amulet", "#4ac8e8"], ["sages_ring", "#b070ff"], ["phoenix_feather", "#ff7a2e"], ["tower_crown", "#ffd25a"], ["chrono_amulet", "#7dffe8"]]);
