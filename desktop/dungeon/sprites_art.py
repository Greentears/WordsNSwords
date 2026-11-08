"""Hand-drawn 32x32 sprite art (data only).

Each sprite is a list of rows describing the LEFT half, written so that the last
character of a row is the one next to the centre line. Rows may be shorter than
16 characters (they are padded with '.' on the outer side) and the drawing is
bottom-aligned (blank rows are added on top). The right half is the mirror image.
'.' is transparent, 'o' the dark outline, every other letter a palette key.
"""

ART: dict[str, list[str]] = {
    "hero": [
        "o...............", "oo.........ooooo", "ohoo......ohhHHH", ".ohoo....ohHHHHH",
        "..ohoo..ohhHHHHH", "...ohooohhhhhhHH", "....oooohhhhhhhh", ".....ohhhhhhhhhh",
        ".....ohhhhhhhhhh", ".....ohhooeeeeee", ".....ohhhhhhhhhh", ".....ohhhHhhhohh",
        "......ohhhhhhooo", ".....ooohhhhhhHH", "..ooooHHHHhhhKKK", ".oHHHHoHHhhKKKKK",
        "ohHHhhoKKKKKKKgg", "ohhhhhooKKKKKKgg", "oHhhhoooKKKKKKKg", ".ooooorrKKKKKKKK",
        "..orrrrrbbbbbbbb", "..orrrrrbbggbbgg", "..orrrrrKKKKKKKK", "..orrrrohhhhhhhh",
        "..orrrrohhhhhhHH", "...orrroohhhhhhh", "....ooo.ohhhhho.", ".......ohhHhhho.",
        ".......ohhhhhho.", "......obbbbbbbo.", "......ooooooooo.",
    ],
    "slime": [
        "oooooo", "ooGGGGgg", "oGGGgggggg", "oGGggggggggg", "ogggwwggggggg",
        "ogggweggggggg", "oggggggggggggg", "oggggggggggoooo", "ogggggggggggggg",
        "ogggggggggggggg", "oggggggggggggggg", "oooooooooooooooo",
    ],
    "goblin": [
        "ooo......oooooo", "oGgo....oGGGgggg", "ogggoooogggggggg", ".ogggggggggggggg",
        "..oogggeeggggggg", "...ogggggggggggg", "....oggggwgwgggg", "....oogggooooooo",
        "......ooggggggg", "....ooobbbbbbbbb", "...obbbbbbbbbbbb", "..ogbbbbbbbbbbbb",
        "..ogbbbbbbbbyyyy", "..oggbbbbbbbbbbb", "...oggbbbbbbbbbb", "...ooobbbbbbbbbb",
        "....oggggggggo..", "....oggggggggo..", "...oobbbbbbbbo..", "...ooooooooooo..",
    ],
    "skeleton": [
        "........oooooooo", ".......owwwwwwww", "......owwwwwwwww", "......owwwwwwwww",
        "......owwoooowww", "......owwoeeowww", "......owwoooowww", "......owwwwwwwwww"[:16],
        ".......owwwwwwoo", "........owowowow", "........oooooooo", "..........oowwww",
        "...ooooowwwwwwww", "..owwwwowwwwwwoo", "..owdddowdddddoo", "..owwwwowwwwwwoo",
        "...owwwowwwwwwoo", "...owddowdddddoo", "....owwowwwwwooo", ".....oooowwwwooo",
        ".....owwwooowwoo", "....owwo.owwwwwo", "....owo..owwwwwo", "....owo..owdwwwo",
        "....owo...owwwwo", "...oowo...owwwwo", "..owwwo...oowwwo",
    ],
    "dark_knight": [
        ".........ppppppp", "........pppppppp", ".......ppppppppp", "......oooooooooo",
        ".....okkkkkkkkkk", ".....okkKKKKKKKK", ".....okkkkkkkkkk", ".....okkorrrrrrr",
        ".....okkkkkkkkkk", ".....okkkkkkooook", "......ookkkkkkkk", "....oooookkkkkkk",
        "..oKKKKKkkkkkkkk", ".oKKkkkKKkkkkkkk", "ooKkkkkkKkkkkppk", "oKkkkkkkkkkkkkpp",
        "ooKkkkkokkkkkkkk", ".oooooorkkkkkkkk", "..oppppobbbbbbbb", "..oppppokkkkkkkk",
        "..oppppokkkkkkkk", "...opppookkkkkkkk", "....ooo.okkkkko.", ".......okkKkkko.",
        ".......okkkkkko.", "......okkkkkkko.", "......ooooooooo.",
    ],
    "boss": [
        "y...............", "yy..............", "oyy......ooo....", ".oyy....oyyyo...",
        ".oyyoooooyyyoooo", "..oyyooRRRRRRRRR", "...oyoRRRRRRRRRR", "....ooRRrRRRRRRR",
        ".....oRReeRRRRRR", ".....oRRReeRRRRR", ".....oRRRRRRRRRR", ".....oRRwRRwRRRR",
        "......oRwwRwwRww", "......ooRRRRRRRR", ".....ooRRRRRRRRR", "..oooRRRRRrrRRRR",
        ".oRRRRRRRrrrrRRR", "oRRRRRRRrrrrrrrr", "oRRRRRRrrrrrrrrr", "oRRRRRrrrrrrrrrr",
        "oRRRRRrrrrrrrrrr", ".oRRRRrrrrrrrrrr", ".ooRRRrrrrrrrrrr", "..oRRRRrrrrrrrrr",
        "..oRRRRRroooooo.", "..ooRRRRRo......", "...oooooooo.....",
    ],
    "bat": [
        "o...............", "oo......o.....o.", "oPo.....opo..opp", "oPPo....oprooprr"[:16],
        "oPPPo...opwoopww"[:16], "oPPPPo..oppppppp", "oPPPPPooopppppPp", "oPPPPPPPPpppppPp",
        ".oPoPPPPPPpppppp", ".oP.oPPPPpppppp.", "..o..oPPoppppp..", ".....ooo.opppp..",
        "..........ooppp.", "...........oppo.", "............ooo.",
    ],
    "wolf": [
        "o.....o.........", "oo...oGo.....o.o", "oGoooGGgo...oGgo", "oGGGGGggoooooGgg",
        ".oGGgggggggggggg", "..ogggggggggggge", "..oggggggeegggge"[:16], "..ogggggggggggww",
        "...ogggggGGgggww", "...oggggooGGooww", "....oggggoowwwoo", "....ooggGGGggggg",
        "...oogggGGGGgggg", "..ogggggGGGGgggg", "..ogggggggggggog", "..oggggggggggoog",
        "..ogggggggggggg.", "..oggo.oggggggo.", "..ogGo.oggggggo.", "..ooo..ooooooo..",
    ],
    "treant": [
        "..g.g.gG.G.g.gGg", ".gGgGgGgGgGgGgGg", "gGgGgGgGgGgGgGgG", ".ogGgGgGgGgGgGgG",
        "..obbbbbbbbbbbBB", "..obbbbbbbbbBBBB", "..obeebbbbbbbbBB", "..obeebbbbbbbbBB",
        "..obbbbbbbbbbBBB", "..obbbbooooooobb", "...obbbbbbbbbbBB", "..obbbBBbbbbbbBB",
        ".obbbbbBBbbbbbBB", "obbbBbbbBbbbbbBB", "obbBBbbbBBbbbbbB", "obbbBbbbbBbbbbbb",
        ".obbbbbbbbbbBbbb", ".obbbbbbbbbbbbbb", "..obbbbboobbbbbb", "..obbbo..obbbbbb",
        ".obbbo...obbbbbb", ".obbbbo..oobbbbb", ".ooooooo..ooooo.",
    ],
    "witch": [
        "..............oo", ".............opp", "............oppp", "...........opppp",
        "..........oppPPP", ".........opppPPp", "........oppppppp", "...oooooooooooPp",
        "....oooppppppppp", "......ogggggggggg", "......oggeeggggg", "......ogggggggggg",
        ".......oggwwgggg", "......ooogggggggg", ".....oppoooooooo", "....oppppppPPPPP",
        "...opppppppPPPPP", "..oppppPPpppppppp"[:16], "..oppppPPpppppppp"[:16], ".oppppppppppppppp"[:16],
        ".opppppppppppyyp", ".opppppppppyyyyy", ".oppppppppppppyy", "..oppppppppppppp",
        "..ooppppppppppp.", "....oooooooooooo",
    ],
    "golem": [
        "...oooooooooooo", "..oIIIIIIIIiiiii", "..oIIiiiiiiiiiii", "..oIiiiiiiiiiiii",
        "..oiiiieeeiiiiii", "..oiiiieeeiiiiii", "..oiiiiiiiiiiiii", "...oooiiiiooooii",
        ".oooIIIioiiiiiii", "oIIIIIiiiiiibbbb", "oIIIiiiiiibbbbbb", "oIIiiiiibbbbbbbb",
        "oIIiiiibbbbbbbbb", "ooIiiiibbbbbbbbb", ".oiiiiibbbbbbbbb", ".ooiiiiiibbbbbbb",
        "..oiiiiiiibbbbbb", "..oiiiiiiiiibbbb", "..oiiiiiiiiiiibb", "..oiiiiiiiiiiiii",
        "..oiiiioo.oiiiii", "..oiiiio...oiiii", "..oooooo...ooooo",
    ],
    "wraith": [
        "......oooooooooo", ".....occcccccccc", "....occccccccccc", "...occckkkkkkkkk",
        "...occkkkkkkkkkk", "...occkkeeekkkkk", "...occkkeeekkkkk", "...occkkkkkkkkkk",
        "...occckkkkkkkkk", "....occcckkkkkkk", "....occcccccckkk", "...occccCccccccc",
        "..occcccccCccccc", "..occcccCcccccCc", ".occcCccccccCccc", ".occcccccCccccCc",
        "occcccCccccccccc", "occcccccccCccccc", "occCcccccccccccc", ".occcccccCcccccc",
        ".occccCcccccccCc", "..occccccCccccc.", "..ococcccocccoc.", "...o.ooc.oo.o.o.",
    ],
    "dragon": [
        "o...............", "oo....o.........", "ogo..ogo.....oo.", "ogGoogGGo...ogGo",
        ".oggggGGGoooogGg", ".ogggggggggggggg", ".ogeegggggggggge"[:16], ".oggggggggggggww",
        "..ogggggggggwwww", "..oogggggrrrrrrr", "...oggggggrrrrrr", "..oggGGGgggggggg",
        ".ogggGGGGggggggg", "ogGGgGyyyyGGgggg", "ogGGyyyyyyyyGGgg", "ogGyyyyyyyyyyGGg",
        "ogGyyyyyyyyyyGGg", "ogGGyyyyyyyyGGgg", ".ogGGyyyyyyGGggg", ".oggGGGGGGGGggg.",
        "..oggdoooooodogg", "..oddo.....oddog", "..oooo......oooo",
    ],
}
