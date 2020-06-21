all_quadrants = [0,1,2,3]
left_side = [0,2]
right_side = [1,3]
top_side = [0,1]
bottom_side = [2,3]



def make_room(index, quadrants):
    # this will eventually return a custom class
    assert(type(quadrants) == list)
    assert(type(quadrants[0]) == int)
    quadrants = sorted(quadrants)
    # yes this is broken if you pass in [2, 3] manually or such
    # ...or is it?
    
    if len(quadrants) == 1:
        return [[[index, quadrants[0]]]]

    elif quadrants == all_quadrants:
        return [[[index, 0], [index, 1]], [[index, 2], [index, 3]]]

    elif quadrants == top_side:
        return [[[index, 0], [index, 1]]]

    elif quadrants == bottom_side:
        return [[[index, 2], [index, 3]]]

    elif quadrants == left_side:
        return [[[index, 0]], [[index, 2]]]
    elif quadrants == right_side:
        return [[[index, 1]], [[index, 3]]]

    elif len(quadrants) == 3:
        tri = [[[index, 0], [index, 1]], [[index, 2], [index, 3]]]
        for q in range(0, 4):
            if q not in quadrants:
                tri[q // 2][q % 2] = None
                return tri
    print("WARNING NO VALID QUADS")
    print(quadrants)
    assert(False)

    return [index, quadrants]

region_to_rooms = {
'Hyrule Castle Lobby':make_room(97, all_quadrants),
'Hyrule Castle West Lobby':make_room(96, right_side),
'Hyrule Castle East Lobby':make_room(98, all_quadrants),
'Hyrule Castle East Hall':make_room(82,  left_side),
'Hyrule Castle West Hall':make_room(96, right_side),
'Hyrule Castle Back Hall':make_room(1, top_side),
'Hyrule Castle Throne Room':make_room(81, all_quadrants),

'Hyrule Dungeon Map Room':make_room(114,top_side),
'Hyrule Dungeon North Abyss':make_room(114, bottom_side),
'Hyrule Dungeon North Abyss Catwalk':make_room(114, [2]),
'Hyrule Dungeon South Abyss':make_room(130, all_quadrants),
'Hyrule Dungeon South Abyss Catwalk':make_room(130, [0]),
'Hyrule Dungeon Guardroom':make_room(129, all_quadrants),
'Hyrule Dungeon Armory Main':make_room(113, [2]),
'Hyrule Dungeon Armory Boomerang':make_room(113, [3]),
'Hyrule Dungeon Armory North Branch':make_room(113, [0]),
'Hyrule Dungeon Staircase':make_room(112, [0]),
'Hyrule Dungeon Cellblock':make_room(128, top_side),

'Sewers Behind Tapestry': make_room(65, all_quadrants),
'Sewers Rope Room': make_room(66, top_side),
'Sewers Dark Cross': make_room(50, all_quadrants),
'Sewers Water': make_room(34, bottom_side),
'Sewers Key Rat': make_room(33, bottom_side),
'Sewers Secret Room Blocked Path': make_room(17, [1]), # I think?!
'Sewers Rat Path': make_room(17, right_side),
'Sewers Secret Room': make_room(17, right_side),

'Sewers Yet More Rats': make_room(2, top_side),
'Sewers Pull Switch': make_room(2, bottom_side),
'Sanctuary': make_room(18, all_quadrants),

'Eastern Lobby':make_room(201, bottom_side),
'Eastern Lobby Bridge':make_room(201, top_side),
'Eastern Lobby Left Ledge':make_room(201, [0]),
'Eastern Lobby Right Ledge':make_room(201, [1]),
'Eastern Cannonball':make_room(185, all_quadrants),
'Eastern Cannonball Ledge':make_room(185, top_side), #???
'Eastern Courtyard Ledge':make_room(169, bottom_side),
'Eastern East Wing':make_room(170, left_side),
'Eastern Pot Switch':make_room(170, [1]),
'Eastern Map Balcony':make_room(170, [3]),
'Eastern Map Room':make_room(170, [3]),
'Eastern West Wing':make_room(168, right_side),
'Eastern Stalfos Spawn':make_room(168, [0]),
'Eastern Compass Room':make_room(168, [2]),
'Eastern Hint Tile':make_room(168, right_side),
'Eastern Hint Tile Blocked Path':make_room(168, right_side),
'Eastern Courtyard':make_room(169, all_quadrants),
'Eastern Fairies':make_room(137, top_side),
'Eastern Map Valley':make_room(170, left_side),
'Eastern Dark Square':make_room(186, [0]),
'Eastern Dark Pots':make_room(186, [1]),
'Eastern Big Key':make_room(184, right_side),
'Eastern Darkness':make_room(153, bottom_side),
'Eastern Rupees':make_room(153, [1]),
'Eastern Attic Start':make_room(218, [2]),
'Eastern False Switches':make_room(217, [3]),
'Eastern Cannonball Hell':make_room(217, [2]),
'Eastern Single Eyegore':make_room(216, [3]),
'Eastern Duo Eyegores':make_room(216, [1]),
'Eastern Boss':make_room(200, [3]),

        # Desert Palace
'Desert Main Lobby':make_room(132, top_side),
'Desert Left Alcove':make_room(132, [0]),
'Desert Right Alcove':make_room(132, [1]),
'Desert Dead End':make_room(116, bottom_side), # ????
'Desert East Lobby':make_room(133, [3]),
'Desert East Wing':make_room(133, left_side),
'Desert Compass Room':make_room(133, [1]), # ???
'Desert Cannonball':make_room(117, right_side),
'Desert Arrow Pot Corner':make_room(117, [2]),
'Desert Trap Room':make_room(117, [0]),
'Desert North Hall':make_room(116, bottom_side), #????
'Desert Map Room':make_room(116, top_side),
'Desert Sandworm Corner':make_room(115, [3]),
'Desert Bonk Torch':make_room(115, [1]),
'Desert Circle of Pots':make_room(115, [2]),
'Desert Big Chest Room':make_room(115, [0]),
'Desert West Wing':make_room(131, right_side),
'Desert West Lobby':make_room(131, [2]),
'Desert Fairy Fountain':make_room(131, [3]),
'Desert Back Lobby':make_room(99, [2]),
'Desert Tiles 1':make_room(99, [0]),
'Desert Bridge':make_room(83, [0]),
'Desert Four Statues':make_room(83, [2]),
'Desert Beamos Hall':make_room(83, right_side),
'Desert Tiles 2':make_room(67, [3]),
'Desert Wall Slide':make_room(67, top_side),
'Desert Boss':make_room(51, [2]),

        # Hera
'Hera Lobby':make_room(119, all_quadrants),
'Hera Basement Cage':make_room(135, [2]),
'Hera Tile Room':make_room(135, [0]),
'Hera Tridorm':make_room(135, [1]),
'Hera Torches':make_room(135, [3]),
'Hera Beetles':make_room(49, [3]),
'Hera Startile Corner':make_room(49, [2]),
'Hera Startile Wide':make_room(49, top_side),
'Hera 4F':make_room(39, all_quadrants),
'Hera Big Chest Landing':make_room(39, top_side),
'Hera 5F':make_room(23, all_quadrants),
'Hera Fairies':make_room(167, [0]),
'Hera Boss':make_room(7, all_quadrants),

        # AgaTower
'Tower Lobby':make_room(224, [2]),
'Tower Gold Knights':make_room(224, [0]),
'Tower Room 03':make_room(224, [1]),
'Tower Lone Statue':make_room(208, [1]),
'Tower Dark Maze':make_room(208, left_side),
'Tower Dark Chargers':make_room(208, [3]),
'Tower Dual Statues':make_room(192, [3]),
'Tower Dark Pits':make_room(192, left_side),
'Tower Dark Archers':make_room(192, [1]),
'Tower Red Spears':make_room(176, [1]),
'Tower Red Guards':make_room(176, [0]),
'Tower Circle of Pots':make_room(176, [2]),
'Tower Pacifist Run':make_room(176, [3]),
'Tower Push Statue':make_room(64, [3]),
'Tower Catwalk':make_room(64, left_side),
'Tower Antechamber':make_room(48, [2]),
'Tower Altar':make_room(48, [0]),
'Tower Agahnim 1':make_room(32, [2]),

        # pod
'PoD Lobby':make_room(74, bottom_side),
'PoD Left Cage':make_room(74, [0]),
'PoD Middle Cage':make_room(74, [1]), # close enough???
'PoD Shooter Room':make_room(9, [0]),
'PoD Pit Room':make_room(58, all_quadrants),
'PoD Pit Room Blocked':make_room(58, [1]),
'PoD Arena Main':make_room(42, all_quadrants), #uuugh
'PoD Arena North':make_room(42, top_side),
'PoD Arena Crystal':make_room(42, all_quadrants),
'PoD Arena Bridge':make_room(42, top_side),
'PoD Arena Ledge':make_room(42, [3]),
'PoD Sexy Statue':make_room(43, left_side),
'PoD Map Balcony':make_room(43, [2]),
'PoD Conveyor':make_room(59, left_side),
'PoD Mimics 1':make_room(75, [0]),
'PoD Jelly Hall':make_room(75, bottom_side),
'PoD Warp Hint':make_room(75, [1]),
'PoD Warp Room':make_room(9, [1]), # ??
'PoD Stalfos Basement':make_room(10, top_side), # close enough??
'PoD Basement Ledge':make_room(0, [0]), #same? 
'PoD Big Key Landing':make_room(58, top_side),
'PoD Falling Bridge Ledge':make_room(26, [0]),
'PoD Falling Bridge':make_room(26, left_side),
'PoD Dark Maze':make_room(25, right_side),
'PoD Big Chest Balcony':make_room(26, left_side),
'PoD Compass Room':make_room(26, [1]),
'PoD Dark Basement': make_room(106, right_side),
'PoD Harmless Hellway':make_room(26, [3]),
'PoD Mimics 2':make_room(27, [2]),
'PoD Bow Statue':make_room(27, top_side),
'PoD Dark Pegs':make_room(11, [1]),
'PoD Lonely Turtle':make_room(11, [0]),
'PoD Turtle Party':make_room(11, [2]),
'PoD Dark Alley':make_room(11, [3]), #???
'PoD Callback':make_room(106, right_side),
'PoD Boss':make_room(90, [3]),

        # swamp
'Swamp Lobby':make_room(40, bottom_side), #sure
'Swamp Entrance':make_room(40, all_quadrants), # sure
'Swamp Pot Row':make_room(56, left_side),
'Swamp Map Ledge':make_room(55, [1]),
'Swamp Trench 1 Approach':make_room(55, all_quadrants), #fuckit - I'm going to remove merge these things anyhow
'Swamp Trench 1 Nexus':make_room(55, all_quadrants),
'Swamp Trench 1 Alcove':make_room(55, all_quadrants),
'Swamp Trench 1 Key Ledge':make_room(55, all_quadrants),
'Swamp Trench 1 Departure':make_room(55, all_quadrants),
'Swamp Hammer Switch':make_room(55, [0]),
'Swamp Hub':make_room(54, all_quadrants),
'Swamp Hub Dead Ledge':make_room(54, [1]),
'Swamp Hub North Ledge':make_room(54, top_side),
'Swamp Donut Top':make_room(70, top_side),
'Swamp Donut Bottom':make_room(70, bottom_side),
'Swamp Compass Donut':make_room(70, [0]),
'Swamp Crystal Switch':make_room(53, [1]),
'Swamp Shortcut':make_room(53, [3]),
'Swamp Trench 2 Pots':make_room(53, [3]),
'Swamp Trench 2 Blocks':make_room(53, [2]),
'Swamp Trench 2 Alcove':make_room(53, top_side),
'Swamp Trench 2 Departure':make_room(53, [2]),
'Swamp Big Key Ledge':make_room(53, [0]),
'Swamp West Shallows':make_room(52, all_quadrants),
'Swamp West Block Path':make_room(52, [2]),
'Swamp West Ledge':make_room(52, [3]),
'Swamp Barrier Ledge':make_room(52, [1]), # maybe
'Swamp Barrier':make_room(52, [1]),
'Swamp Attic':make_room(84, all_quadrants),
'Swamp Push Statue':make_room(38, bottom_side),
'Swamp Shooters':make_room(38, [0]),
'Swamp Left Elbow':make_room(38, [1]),
'Swamp Right Elbow':make_room(38, [1]),
'Swamp Drain Left':make_room(118, [0]),
'Swamp Drain Right':make_room(118, [0]),
        # This is intentionally odd so I don't have to treat the WS door in the Flooded Room oddly (because of how it works when going backward):make_room(118, all_quadrants),
'Swamp Flooded Room':make_room(118, [3]),
'Swamp Flooded Spot':make_room(118, [3]),
'Swamp Basement Shallows':make_room(118, left_side),
'Swamp Waterfall Room':make_room(102, bottom_side),
'Swamp Refill':make_room(102, [0]),
'Swamp Behind Waterfall':make_room(102, [1]),
'Swamp C':make_room(22, [1]),
'Swamp Waterway':make_room(22, bottom_side),
'Swamp I':make_room(22, top_side),
'Swamp T':make_room(22, [0]),
'Swamp Boss':make_room(6, [2]),

        # sw
'Skull 1 Lobby':make_room(88, [2]),
'Skull Map Room':make_room(88, [3]),
'Skull Pot Circle':make_room(88, [1]),
'Skull Pull Switch':make_room(88, [0]),
'Skull Big Chest':make_room(88, [2]),
'Skull Pinball':make_room(104, all_quadrants),
'Skull Compass Room':make_room(103, right_side), #????
'Skull Left Drop':make_room(103, left_side), #???
'Skull Pot Prison':make_room(87, [3]),
'Skull 2 East Lobby':make_room(87, [2]),
'Skull Big Key':make_room(87, [0]),
'Skull Lone Pot':make_room(87, [1]),
'Skull Small Hall':make_room(86, [3]), #???
'Skull Back Drop':make_room(86, right_side),
'Skull 2 West Lobby':make_room(86, [2]),
'Skull X Room':make_room(86, [0]),
'Skull 3 Lobby':make_room(89, left_side),
'Skull East Bridge':make_room(89, right_side),
'Skull West Bridge Nook':make_room(89, [2]),
'Skull Star Pits':make_room(73, [2]),
'Skull Torch Room':make_room(73, right_side),
'Skull Vines':make_room(73, [0]),
'Skull Spike Corner':make_room(57, [2]),
'Skull Final Drop':make_room(57, [3]),
'Skull Boss':make_room(41, [3]),

        # tt
'Thieves Lobby':make_room(219, all_quadrants), #probably
'Thieves Ambush':make_room(203, all_quadrants),
'Thieves Rail Ledge':make_room(204, left_side),
'Thieves BK Corner':make_room(204, all_quadrants),
'Thieves Compass Room':make_room(220, all_quadrants), #probably??
'Thieves Big Chest Nook':make_room(219, [3]),
'Thieves Hallway':make_room(188, right_side),
'Thieves Boss':make_room(172, [3]),
'Thieves Pot Alcove Mid':make_room(188, [2]),
'Thieves Pot Alcove Bottom':make_room(188, [2]),
'Thieves Pot Alcove Top':make_room(188, [2]),
'Thieves Conveyor Maze':make_room(188, [0]),
'Thieves Spike Track':make_room(187, [3]),
'Thieves Hellway':make_room(187, left_side),
'Thieves Hellway N Crystal':make_room(187, [0]),
'Thieves Hellway S Crystal':make_room(187, [2]),
'Thieves Triple Bypass':make_room(187, [1]),
'Thieves Spike Switch':make_room(171, [2]),
'Thieves Attic':make_room(100, [2]),
'Thieves Cricket Hall Left':make_room(100, [3]),
'Thieves Cricket Hall Right':make_room(101, [2]),
'Thieves Attic Window':make_room(101, [3]),
'Thieves Basement Block':make_room(69, [0]),
'Thieves Blocked Entry':make_room(69, [0]),
'Thieves Lonely Zazak':make_room(69, [2]),
'Thieves Blind\'s Cell':make_room(69, right_side),
'Thieves Conveyor Bridge':make_room(68, right_side),
'Thieves Conveyor Block':make_room(68, [1]),
'Thieves Big Chest Room':make_room(68, [2]),
'Thieves Trap':make_room(68, [0]),

        # ice
'Ice Lobby':make_room(14, [3]),
'Ice Jelly Key':make_room(14, [2]),
'Ice Floor Switch':make_room(30, [2]),
'Ice Cross Left':make_room(30, [3]),
'Ice Cross Bottom':make_room(30, [3]),
'Ice Cross Right':make_room(30, [3]),
'Ice Cross Top':make_room(30, [3]),
'Ice Compass Room':make_room(46, [1]),
'Ice Pengator Switch':make_room(31, [2]),
'Ice Dead End':make_room(31, [3]),
'Ice Big Key':make_room(31, [3]),
'Ice Bomb Drop':make_room(30, [1]),
'Ice Stalfos Hint':make_room(62, [1]),
'Ice Conveyor':make_room(62, bottom_side),
'Ice Bomb Jump Ledge':make_room(78, [0]),
'Ice Bomb Jump Catwalk':make_room(78, [0]),
'Ice Narrow Corridor':make_room(78, [1]),
'Ice Pengator Trap':make_room(110, [1]),
'Ice Spike Cross':make_room(94, [3]),
'Ice Firebar':make_room(94, [2]),
'Ice Falling Square':make_room(94, [1]),
'Ice Spike Room':make_room(95, [2]), #????
'Ice Hammer Block':make_room(63, [2]),
'Ice Tongue Pull':make_room(63, [3]),
'Ice Freezors':make_room(126, [2]),
'Ice Freezors Ledge':make_room(126, [2]),
'Ice Tall Hint':make_room(126, right_side),
'Ice Hookshot Ledge':make_room(127, [0]),
'Ice Hookshot Balcony':make_room(127, [0]),
'Ice Spikeball':make_room(127, [2]),
'Ice Lonely Freezor':make_room(142, [1]),
'Iced T':make_room(174, [1]),
'Ice Catwalk':make_room(175, [0]),
'Ice Many Pots':make_room(159, [2]),
'Ice Crystal Right':make_room(158, [3]),
'Ice Crystal Left':make_room(158, [3]),
'Ice Crystal Block':make_room(158, [3]),
'Ice Big Chest View':make_room(158, [2]),
'Ice Big Chest Landing':make_room(158, [2]),
'Ice Backwards Room':make_room(158, [1]), #???
'Ice Anti-Fairy':make_room(190, [1]),#???
'Ice Switch Room':make_room(190, [3]),
'Ice Refill':make_room(191, [2]),
'Ice Fairy':make_room(191, [1]),
'Ice Antechamber':make_room(206, [1]),
'Ice Boss':make_room(222, [1]),

        # mire
'Mire Lobby':make_room(152, bottom_side),
'Mire Post-Gap':make_room(152, [3]),
'Mire 2':make_room(210, right_side),
'Mire Hub':make_room(194, all_quadrants),
'Mire Hub Right':make_room(194, [1]),
'Mire Hub Top':make_room(194, top_side),
'Mire Hub Switch':make_room(194, [0]),
'Mire Lone Shooter':make_room(195, [2]),
'Mire Failure Bridge':make_room(195, left_side),
'Mire Falling Bridge':make_room(195, right_side),
'Mire Map Spike Side':make_room(195, [0]),
'Mire Map Spot':make_room(195, [0]),
'Mire Crystal Dead End':make_room(195, [0]),
'Mire Hidden Shooters':make_room(178, [3]),
'Mire Hidden Shooters Blocked':make_room(178, [3]),
'Mire Cross':make_room(178, [2]),
'Mire Minibridge':make_room(178, [1]),
'Mire BK Door Room':make_room(178, top_side),
'Mire Spikes':make_room(179, [2]),
'Mire Ledgehop':make_room(179, [0]),
'Mire Bent Bridge':make_room(163, left_side),
'Mire Over Bridge':make_room(162, all_quadrants),
'Mire Right Bridge':make_room(163, right_side),
'Mire Left Bridge':make_room(163, all_quadrants),
'Mire Fishbone':make_room(161, [0,1,3]),
'Mire South Fish':make_room(161, [3]),
'Mire Spike Barrier':make_room(177, right_side),
'Mire Square Rail':make_room(177, [2]),
'Mire Lone Warp':make_room(177, [0]),
'Mire Wizzrobe Bypass':make_room(193, [1]),
'Mire Conveyor Crystal':make_room(193, [3]),
'Mire Tile Room':make_room(193, [2]),
'Mire Compass Room':make_room(193, [0]),
'Mire Compass Chest':make_room(193, [0]),
'Mire Neglected Room':make_room(209, [1]),
'Mire Chest View':make_room(209, [3]),
'Mire Conveyor Barrier':make_room(209, [0]),
'Mire BK Chest Ledge':make_room(209, [3]),
'Mire Warping Pool':make_room(209, [2]),
'Mire Torches Top':make_room(151, [0]),
'Mire Torches Bottom':make_room(151, [2]),
'Mire Attic Hint':make_room(151, right_side),
'Mire Dark Shooters':make_room(147, top_side),
'Mire Key Rupees':make_room(147, [3]),
'Mire Block X':make_room(147, [2]),
'Mire Tall Dark and Roomy':make_room(146, right_side),
'Mire Crystal Right':make_room(146, [2]),
'Mire Crystal Mid':make_room(146, [2]),
'Mire Crystal Left':make_room(146, [2]),
'Mire Crystal Top':make_room(146, [0]),
'Mire Shooter Rupees':make_room(146, [0]),
'Mire Falling Foes':make_room(145, right_side),
'Mire Firesnake Skip':make_room(160, [1]),
'Mire Antechamber':make_room(160, [0]),
'Mire Boss':make_room(144, [2]),

        # tr
'TR Main Lobby':make_room(214, right_side),
'TR Lobby Ledge':make_room(214, [0]),
'TR Compass Room':make_room(214, left_side),
'TR Hub':make_room(198, all_quadrants),
'TR Torches Ledge':make_room(198, [2]),
'TR Torches':make_room(199, all_quadrants),
'TR Roller Room':make_room(183, left_side),
'TR Tile Room':make_room(182, [3]),
'TR Refill':make_room(182, [1]),
'TR Pokey 1':make_room(182, [2]),
'TR Chain Chomps':make_room(182, [0]),
'TR Pipe Pit':make_room(21, all_quadrants),
'TR Pipe Ledge':make_room(21, [1]),
'TR Lava Dual Pipes':make_room(20, all_quadrants),
'TR Lava Island':make_room(20, all_quadrants),
'TR Lava Escape':make_room(20, all_quadrants), #not even going to try
'TR Pokey 2':make_room(19, right_side),
'TR Twin Pokeys':make_room(36, [0]),
'TR Hallway':make_room(36, [2]),
'TR Dodgers':make_room(36, [1]),
'TR Big View':make_room(36, [3]),
'TR Big Chest':make_room(36, [3]),
'TR Big Chest Entrance':make_room(36, [3]),
'TR Lazy Eyes':make_room(35, [3]),
'TR Dash Room':make_room(4, [2]),
'TR Tongue Pull':make_room(4, [3]),
'TR Rupees':make_room(4, [1]),
'TR Crystaroller':make_room(4, [0]),
'TR Dark Ride':make_room(181, all_quadrants),
'TR Dash Bridge':make_room(197, left_side),
'TR Eye Bridge':make_room(213, left_side),

'TR Crystal Maze':make_room(196, all_quadrants),
'TR Crystal Maze End':make_room(196, top_side),
'TR Final Abyss':make_room(180, all_quadrants),
'TR Boss':make_room(164, [2]),

        # gt
'GT Lobby':make_room(12, all_quadrants),
'GT Bob\'s Torch':make_room(140, [0]),
'GT Hope Room':make_room(140, [1]),
'GT Big Chest':make_room(140, [2]),
'GT Blocked Stairs':make_room(140, [2]),
'GT Bob\'s Room':make_room(140, [3]),
'GT Tile Room':make_room(141, [0]),
'GT Speed Torch':make_room(141, right_side),
'GT Speed Torch Upper':make_room(141, [1]),
'GT Pots n Blocks':make_room(141, [2]),
'GT Crystal Conveyor':make_room(157,[1]),
'GT Compass Room':make_room(157, [0]),

#'GT Invisible Bridges':make_room(156, all_quadrants), #???
#'GT Invisible Catwalk':make_room(157, bottom_side),
'GT Invisible Catwalk':make_room(156, all_quadrants), #???
'GT Invisible Bridges':make_room(157, bottom_side),

'GT Conveyor Cross':make_room(139, [1]),
'GT Hookshot East Platform':make_room(139, [0]),
'GT Hookshot North Platform':make_room(139, [0]),
'GT Hookshot South Platform':make_room(139, [2]),
'GT Hookshot South Entry':make_room(139, [2]),
'GT Map Room':make_room(139, [3]),
'GT Double Switch Entry':make_room(155, [0]),
'GT Double Switch Switches':make_room(155, [0]),
'GT Double Switch Transition':make_room(155, [0]),
'GT Double Switch Key Spot':make_room(155, [0]),
'GT Double Switch Exit':make_room(155, [0]),
'GT Spike Crystals':make_room(155, [1]),
'GT Warp Maze - Left Section':make_room(155, bottom_side),
'GT Warp Maze - Mid Section':make_room(155, bottom_side),
'GT Warp Maze - Right Section':make_room(155, bottom_side),
'GT Warp Maze - Pit Section':make_room(155, bottom_side),
'GT Warp Maze - Pit Exit Warp Spot':make_room(155, bottom_side),
'GT Warp Maze Exit Section':make_room(155, bottom_side),
'GT Firesnake Room':make_room(125, top_side),
'GT Firesnake Room Ledge':make_room(125, top_side),
'GT Warp Maze - Rail Choice':make_room(125, [2]), #ugh. Need to attach this together
'GT Warp Maze - Rando Rail':make_room(125, [2]), 
'GT Warp Maze - Main Rails':make_room(125, [2]),
'GT Warp Maze - Pot Rail':make_room(125, [2]),
'GT Petting Zoo':make_room(125, [3]),
'GT Conveyor Star Pits':make_room(123, top_side),
'GT Hidden Star':make_room(123, [3]),
'GT DMs Room':make_room(123, [2]),
'GT Falling Bridge':make_room(124, left_side),
'GT Randomizer Room':make_room(124, right_side),
'GT Ice Armos':make_room(28, [3]),
'GT Big Key Room':make_room(28, [1]),
'GT Four Torches':make_room(28, [2]),
'GT Fairy Abyss':make_room(28, [0]),
'GT Crystal Paths':make_room(107, [0]),
'GT Mimics 1':make_room(107, [2]),
'GT Mimics 2':make_room(107, [3]),
'GT Dash Hall':make_room(107, [1]),
'GT Hidden Spikes':make_room(91, right_side),
'GT Cannonball Bridge':make_room(92, top_side),
'GT Refill':make_room(92, [3]),
'GT Gauntlet 1':make_room(93, [1]),
'GT Gauntlet 2':make_room(93, [0]),
'GT Gauntlet 3':make_room(93, [2]),
'GT Gauntlet 4':make_room(109, [0]),
'GT Gauntlet 5':make_room(109, [2]),
'GT Beam Dash':make_room(108, [3]),
'GT Lanmolas 2':make_room(108, [2]),
'GT Quad Pot':make_room(108, [1]),
'GT Wizzrobes 1':make_room(165, all_quadrants),
'GT Dashing Bridge':make_room(165, all_quadrants),
'GT Wizzrobes 2':make_room(165, all_quadrants),
'GT Conveyor Bridge':make_room(149, right_side),
'GT Torch Cross':make_room(150, left_side),
'GT Staredown':make_room(150, [3]),
'GT Falling Torches':make_room(61, [3]),
'GT Mini Helmasaur Room':make_room(61, [1]),
'GT Bomb Conveyor':make_room(61, [0]),
'GT Crystal Circles':make_room(61, [2]),
'GT Left Moldorm Ledge':make_room(77, [0]),
'GT Right Moldorm Ledge':make_room(77, [1]),
'GT Moldorm':make_room(77, all_quadrants),
'GT Moldorm Pit':make_room(166, all_quadrants),
'GT Validation':make_room(77, bottom_side),
'GT Validation Door':make_room(77, [2]),
'GT Frozen Over':make_room(76, right_side),
'GT Brightly Lit Hall':make_room(29, top_side),
'GT Agahnim 2':make_room(13, [2]),
}