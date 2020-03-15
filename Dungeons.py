import random

from BaseClasses import Dungeon
from Bosses import BossFactory
from Fill import fill_restrictive
from Items import ItemFactory


def create_dungeons(world, player):
    def make_dungeon(name, default_boss, dungeon_regions, big_key, small_keys, dungeon_items):
        dungeon = Dungeon(name, dungeon_regions, big_key, [] if world.retro[player] else small_keys, dungeon_items, player)
        dungeon.boss = BossFactory(default_boss, player)
        for region in dungeon.regions:
            world.get_region(region, player).dungeon = dungeon
            dungeon.world = world
        return dungeon

    ES = make_dungeon('Hyrule Castle', None, hyrule_castle_regions, None, [ItemFactory('Small Key (Escape)', player)], [ItemFactory('Map (Escape)', player)])
    EP = make_dungeon('Eastern Palace', 'Armos Knights', eastern_regions, ItemFactory('Big Key (Eastern Palace)', player), [], ItemFactory(['Map (Eastern Palace)', 'Compass (Eastern Palace)'], player))
    DP = make_dungeon('Desert Palace', 'Lanmolas', desert_regions, ItemFactory('Big Key (Desert Palace)', player), [ItemFactory('Small Key (Desert Palace)', player)], ItemFactory(['Map (Desert Palace)', 'Compass (Desert Palace)'], player))
    ToH = make_dungeon('Tower of Hera', 'Moldorm', hera_regions, ItemFactory('Big Key (Tower of Hera)', player), [ItemFactory('Small Key (Tower of Hera)', player)], ItemFactory(['Map (Tower of Hera)', 'Compass (Tower of Hera)'], player))
    PoD = make_dungeon('Palace of Darkness', 'Helmasaur King', pod_regions, ItemFactory('Big Key (Palace of Darkness)', player), ItemFactory(['Small Key (Palace of Darkness)'] * 6, player), ItemFactory(['Map (Palace of Darkness)', 'Compass (Palace of Darkness)'], player))
    TT = make_dungeon('Thieves Town', 'Blind', thieves_regions, ItemFactory('Big Key (Thieves Town)', player), [ItemFactory('Small Key (Thieves Town)', player)], ItemFactory(['Map (Thieves Town)', 'Compass (Thieves Town)'], player))
    SW = make_dungeon('Skull Woods', 'Mothula', skull_regions, ItemFactory('Big Key (Skull Woods)', player), ItemFactory(['Small Key (Skull Woods)'] * 3, player), ItemFactory(['Map (Skull Woods)', 'Compass (Skull Woods)'], player))
    SP = make_dungeon('Swamp Palace', 'Arrghus', swamp_regions, ItemFactory('Big Key (Swamp Palace)', player), [ItemFactory('Small Key (Swamp Palace)', player)], ItemFactory(['Map (Swamp Palace)', 'Compass (Swamp Palace)'], player))
    IP = make_dungeon('Ice Palace', 'Kholdstare', ice_regions, ItemFactory('Big Key (Ice Palace)', player), ItemFactory(['Small Key (Ice Palace)'] * 2, player), ItemFactory(['Map (Ice Palace)', 'Compass (Ice Palace)'], player))
    MM = make_dungeon('Misery Mire', 'Vitreous', mire_regions, ItemFactory('Big Key (Misery Mire)', player), ItemFactory(['Small Key (Misery Mire)'] * 3, player), ItemFactory(['Map (Misery Mire)', 'Compass (Misery Mire)'], player))
    TR = make_dungeon('Turtle Rock', 'Trinexx', tr_regions, ItemFactory('Big Key (Turtle Rock)', player), ItemFactory(['Small Key (Turtle Rock)'] * 4, player), ItemFactory(['Map (Turtle Rock)', 'Compass (Turtle Rock)'], player))
    AT = make_dungeon('Agahnims Tower', 'Agahnim', tower_regions, None, ItemFactory(['Small Key (Agahnims Tower)'] * 2, player), [])
    GT = make_dungeon('Ganons Tower', 'Agahnim2', gt_regions, ItemFactory('Big Key (Ganons Tower)', player), ItemFactory(['Small Key (Ganons Tower)'] * 4, player), ItemFactory(['Map (Ganons Tower)', 'Compass (Ganons Tower)'], player))

    GT.bosses['bottom'] = BossFactory('Armos Knights', player)
    GT.bosses['middle'] = BossFactory('Lanmolas', player)
    GT.bosses['top'] = BossFactory('Moldorm', player)

    world.dungeons += [ES, EP, DP, ToH, AT, PoD, TT, SW, SP, IP, MM, TR, GT]

def fill_dungeons(world):
    freebes = ['Ganons Tower - Map Chest', 'Palace of Darkness - Harmless Hellway', 'Palace of Darkness - Big Key Chest', 'Turtle Rock - Big Key Chest']

    all_state_base = world.get_all_state()

    for player in range(1, world.players + 1):
        pinball_room = world.get_location('Skull Woods - Pinball Room', player)
        if world.retro[player]:
            world.push_item(pinball_room, ItemFactory('Small Key (Universal)', player), False)
        else:
            world.push_item(pinball_room, ItemFactory('Small Key (Skull Woods)', player), False)
        pinball_room.event = True
        pinball_room.locked = True

    dungeons = [(list(dungeon.regions), dungeon.big_key, list(dungeon.small_keys), list(dungeon.dungeon_items)) for dungeon in world.dungeons]

    loopcnt = 0
    while dungeons:
        loopcnt += 1
        dungeon_regions, big_key, small_keys, dungeon_items = dungeons.pop(0)
        # this is what we need to fill
        dungeon_locations = [location for location in world.get_unfilled_locations() if location.parent_region.name in dungeon_regions]
        random.shuffle(dungeon_locations)

        all_state = all_state_base.copy()

        # first place big key
        if big_key is not None:
            bk_location = None
            for location in dungeon_locations:
                if location.item_rule(big_key):
                    bk_location = location
                    break

            if bk_location is None:
                raise RuntimeError('No suitable location for %s' % big_key)

            world.push_item(bk_location, big_key, False)
            bk_location.event = True
            bk_location.locked = True
            dungeon_locations.remove(bk_location)
            big_key = None

        # next place small keys
        while small_keys:
            small_key = small_keys.pop()
            all_state.sweep_for_events()
            sk_location = None
            for location in dungeon_locations:
                if location.name in freebes or (location.can_reach(all_state) and location.item_rule(small_key)):
                    sk_location = location
                    break

            if sk_location is None:
                # need to retry this later
                small_keys.append(small_key)
                dungeons.append((dungeon_regions, big_key, small_keys, dungeon_items))
                # infinite regression protection
                if loopcnt < (30 * world.players):
                    break
                else:
                    raise RuntimeError('No suitable location for %s' % small_key)

            world.push_item(sk_location, small_key, False)
            sk_location.event = True
            sk_location.locked = True
            dungeon_locations.remove(sk_location)

        if small_keys:
            # key placement not finished, loop again
            continue

        # next place dungeon items
        for dungeon_item in dungeon_items:
            di_location = dungeon_locations.pop()
            world.push_item(di_location, dungeon_item, False)


def get_dungeon_item_pool(world):
    return [item for dungeon in world.dungeons for item in dungeon.all_items]

def fill_dungeons_restrictive(world, shuffled_locations):
    all_state_base = world.get_all_state()

    # for player in range(1, world.players + 1):
    #     pinball_room = world.get_location('Skull Woods - Pinball Room', player)
    #     if world.retro[player]:
    #         world.push_item(pinball_room, ItemFactory('Small Key (Universal)', player), False)
    #     else:
    #         world.push_item(pinball_room, ItemFactory('Small Key (Skull Woods)', player), False)
    #     pinball_room.event = True
    #     pinball_room.locked = True
    #     shuffled_locations.remove(pinball_room)

    # with shuffled dungeon items they are distributed as part of the normal item pool
    for item in world.get_items():
        if (item.smallkey and world.keyshuffle[item.player]) or (item.bigkey and world.bigkeyshuffle[item.player]):
            item.advancement = True
        elif (item.map and world.mapshuffle[item.player]) or (item.compass and world.compassshuffle[item.player]):
            item.priority = True

    dungeon_items = [item for item in get_dungeon_item_pool(world) if ((item.smallkey and not world.keyshuffle[item.player])
                                                                       or (item.bigkey and not world.bigkeyshuffle[item.player])
                                                                       or (item.map and not world.mapshuffle[item.player])
                                                                       or (item.compass and not world.compassshuffle[item.player]))]

    # sort in the order Big Key, Small Key, Other before placing dungeon items
    sort_order = {"BigKey": 3, "SmallKey": 2}
    dungeon_items.sort(key=lambda item: sort_order.get(item.type, 1))

    fill_restrictive(world, all_state_base, shuffled_locations, dungeon_items,
                     keys_in_itempool={player: not world.keyshuffle[player] for player in range(1, world.players+1)}, single_player_placement=True)


dungeon_music_addresses = {'Eastern Palace - Prize': [0x1559A],
                           'Desert Palace - Prize': [0x1559B, 0x1559C, 0x1559D, 0x1559E],
                           'Tower of Hera - Prize': [0x155C5, 0x1107A, 0x10B8C],
                           'Palace of Darkness - Prize': [0x155B8],
                           'Swamp Palace - Prize': [0x155B7],
                           'Thieves\' Town - Prize': [0x155C6],
                           'Skull Woods - Prize': [0x155BA, 0x155BB, 0x155BC, 0x155BD, 0x15608, 0x15609, 0x1560A, 0x1560B],
                           'Ice Palace - Prize': [0x155BF],
                           'Misery Mire - Prize': [0x155B9],
                           'Turtle Rock - Prize': [0x155C7, 0x155A7, 0x155AA, 0x155AB]}

hyrule_castle_regions = [
    'Hyrule Castle Lobby', 'Hyrule Castle West Lobby', 'Hyrule Castle East Lobby', 'Hyrule Castle East Hall',
    'Hyrule Castle West Hall', 'Hyrule Castle Back Hall', 'Hyrule Castle Throne Room', 'Hyrule Dungeon Map Room',
    'Hyrule Dungeon North Abyss', 'Hyrule Dungeon North Abyss Catwalk', 'Hyrule Dungeon South Abyss',
    'Hyrule Dungeon South Abyss Catwalk', 'Hyrule Dungeon Guardroom', 'Hyrule Dungeon Armory Main',
    'Hyrule Dungeon Armory Boomerang',  'Hyrule Dungeon Armory North Branch', 'Hyrule Dungeon Staircase',
    'Hyrule Dungeon Cellblock', 'Sewers Behind Tapestry', 'Sewers Rope Room', 'Sewers Dark Cross', 'Sewers Water',
    'Sewers Key Rat', 'Sewers Rat Path', 'Sewers Secret Room Blocked Path', 'Sewers Secret Room',
    'Sewers Yet More Rats', 'Sewers Pull Switch', 'Sanctuary'
]

eastern_regions = [
    'Eastern Lobby', 'Eastern Lobby Bridge', 'Eastern Lobby Left Ledge', 'Eastern Lobby Right Ledge',
    'Eastern Cannonball', 'Eastern Cannonball Ledge', 'Eastern Courtyard Ledge', 'Eastern East Wing',
    'Eastern Pot Switch', 'Eastern Map Balcony', 'Eastern Map Room', 'Eastern West Wing', 'Eastern Stalfos Spawn',
    'Eastern Compass Room', 'Eastern Hint Tile', 'Eastern Hint Tile Blocked Path', 'Eastern Courtyard',
    'Eastern Fairies', 'Eastern Map Valley', 'Eastern Dark Square', 'Eastern Dark Pots', 'Eastern Big Key',
    'Eastern Darkness', 'Eastern Rupees', 'Eastern Attic Start', 'Eastern False Switches', 'Eastern Cannonball Hell',
    'Eastern Single Eyegore', 'Eastern Duo Eyegores', 'Eastern Boss'
]

desert_regions = [
    'Desert Main Lobby', 'Desert Left Alcove', 'Desert Right Alcove', 'Desert Dead End', 'Desert East Lobby',
    'Desert East Wing', 'Desert Compass Room', 'Desert Cannonball', 'Desert Arrow Pot Corner', 'Desert Trap Room',
    'Desert North Hall', 'Desert Map Room', 'Desert Sandworm Corner', 'Desert Bonk Torch', 'Desert Circle of Pots',
    'Desert Big Chest Room', 'Desert West Wing', 'Desert West Lobby', 'Desert Fairy Fountain', 'Desert Back Lobby',
    'Desert Tiles 1', 'Desert Bridge', 'Desert Four Statues', 'Desert Beamos Hall', 'Desert Tiles 2',
    'Desert Wall Slide', 'Desert Boss'
]

hera_regions = [
    'Hera Lobby', 'Hera Basement Cage', 'Hera Tile Room', 'Hera Tridorm', 'Hera Torches', 'Hera Beetles',
    'Hera Startile Corner', 'Hera Startile Wide', 'Hera 4F', 'Hera Big Chest Landing', 'Hera 5F',
    'Hera Fairies', 'Hera Boss'
]

tower_regions = [
    'Tower Lobby', 'Tower Gold Knights', 'Tower Room 03', 'Tower Lone Statue', 'Tower Dark Maze', 'Tower Dark Chargers',
    'Tower Dual Statues', 'Tower Dark Pits', 'Tower Dark Archers', 'Tower Red Spears', 'Tower Red Guards',
    'Tower Circle of Pots', 'Tower Pacifist Run', 'Tower Push Statue', 'Tower Catwalk', 'Tower Antechamber',
    'Tower Altar', 'Tower Agahnim 1'
]

pod_regions = [
    'PoD Lobby', 'PoD Left Cage', 'PoD Middle Cage', 'PoD Shooter Room', 'PoD Pit Room', 'PoD Pit Room Blocked',
    'PoD Arena Main', 'PoD Arena North', 'PoD Arena Crystal', 'PoD Arena Bridge', 'PoD Arena Ledge', 'PoD Sexy Statue',
    'PoD Map Balcony', 'PoD Conveyor', 'PoD Mimics 1', 'PoD Jelly Hall', 'PoD Warp Hint', 'PoD Warp Room',
    'PoD Stalfos Basement', 'PoD Basement Ledge', 'PoD Big Key Landing', 'PoD Falling Bridge',
    'PoD Falling Bridge Ledge', 'PoD Dark Maze', 'PoD Big Chest Balcony', 'PoD Compass Room', 'PoD Dark Basement',
    'PoD Harmless Hellway', 'PoD Mimics 2', 'PoD Bow Statue', 'PoD Dark Pegs', 'PoD Lonely Turtle', 'PoD Turtle Party',
    'PoD Dark Alley', 'PoD Callback', 'PoD Boss'
]

swamp_regions = [
    'Swamp Lobby', 'Swamp Entrance', 'Swamp Pot Row', 'Swamp Map Ledge', 'Swamp Trench 1 Approach',
    'Swamp Trench 1 Nexus', 'Swamp Trench 1 Alcove', 'Swamp Trench 1 Key Ledge', 'Swamp Trench 1 Departure',
    'Swamp Hammer Switch', 'Swamp Hub', 'Swamp Hub Dead Ledge', 'Swamp Hub North Ledge', 'Swamp Donut Top',
    'Swamp Donut Bottom', 'Swamp Compass Donut', 'Swamp Crystal Switch', 'Swamp Shortcut', 'Swamp Trench 2 Pots',
    'Swamp Trench 2 Blocks', 'Swamp Trench 2 Alcove', 'Swamp Trench 2 Departure', 'Swamp Big Key Ledge',
    'Swamp West Shallows', 'Swamp West Block Path', 'Swamp West Ledge', 'Swamp Barrier Ledge', 'Swamp Barrier',
    'Swamp Attic', 'Swamp Push Statue', 'Swamp Shooters', 'Swamp Left Elbow', 'Swamp Right Elbow', 'Swamp Drain Left',
    'Swamp Drain Right', 'Swamp Flooded Room', 'Swamp Flooded Spot', 'Swamp Basement Shallows', 'Swamp Waterfall Room',
    'Swamp Refill', 'Swamp Behind Waterfall', 'Swamp C', 'Swamp Waterway', 'Swamp I', 'Swamp T', 'Swamp Boss'
]

skull_regions = [
    'Skull 1 Lobby', 'Skull Map Room', 'Skull Pot Circle', 'Skull Pull Switch', 'Skull Big Chest', 'Skull Pinball',
    'Skull Pot Prison', 'Skull Compass Room', 'Skull Left Drop', 'Skull 2 East Lobby', 'Skull Big Key',
    'Skull Lone Pot', 'Skull Small Hall', 'Skull Back Drop', 'Skull 2 West Lobby', 'Skull X Room', 'Skull 3 Lobby',
    'Skull East Bridge', 'Skull West Bridge Nook', 'Skull Star Pits', 'Skull Torch Room', 'Skull Vines',
    'Skull Spike Corner', 'Skull Final Drop', 'Skull Boss'
]

thieves_regions = [
    'Thieves Lobby', 'Thieves Ambush', 'Thieves BK Corner', 'Thieves Rail Ledge', 'Thieves Compass Room',
    'Thieves Big Chest Nook', 'Thieves Hallway', 'Thieves Boss', 'Thieves Pot Alcove Mid', 'Thieves Pot Alcove Bottom',
    'Thieves Pot Alcove Top', 'Thieves Conveyor Maze', 'Thieves Spike Track', 'Thieves Hellway',
    'Thieves Hellway N Crystal', 'Thieves Hellway S Crystal', 'Thieves Triple Bypass', 'Thieves Spike Switch',
    'Thieves Attic', 'Thieves Cricket Hall Left', 'Thieves Cricket Hall Right', 'Thieves Attic Window',
    'Thieves Basement Block', 'Thieves Blocked Entry', 'Thieves Lonely Zazak', 'Thieves Blind\'s Cell',
    'Thieves Conveyor Bridge', 'Thieves Conveyor Block', 'Thieves Big Chest Room', 'Thieves Trap'
]

ice_regions = [
    'Ice Lobby', 'Ice Jelly Key', 'Ice Floor Switch', 'Ice Cross Left', 'Ice Cross Bottom', 'Ice Cross Right',
    'Ice Cross Top', 'Ice Compass Room', 'Ice Pengator Switch', 'Ice Dead End', 'Ice Big Key', 'Ice Bomb Drop',
    'Ice Stalfos Hint', 'Ice Conveyor', 'Ice Bomb Jump Ledge', 'Ice Bomb Jump Catwalk', 'Ice Narrow Corridor',
    'Ice Pengator Trap', 'Ice Spike Cross', 'Ice Firebar', 'Ice Falling Square', 'Ice Spike Room', 'Ice Hammer Block',
    'Ice Tongue Pull', 'Ice Freezors', 'Ice Freezors Ledge', 'Ice Tall Hint', 'Ice Hookshot Ledge',
    'Ice Hookshot Balcony', 'Ice Spikeball', 'Ice Lonely Freezor', 'Iced T', 'Ice Catwalk', 'Ice Many Pots',
    'Ice Crystal Right', 'Ice Crystal Left', 'Ice Crystal Block', 'Ice Big Chest View', 'Ice Big Chest Landing',
    'Ice Backwards Room', 'Ice Anti-Fairy', 'Ice Switch Room', 'Ice Refill', 'Ice Fairy', 'Ice Antechamber', 'Ice Boss'
]

mire_regions = [
    'Mire Lobby', 'Mire Post-Gap', 'Mire 2', 'Mire Hub', 'Mire Hub Right', 'Mire Hub Top', 'Mire Lone Shooter',
    'Mire Failure Bridge', 'Mire Falling Bridge', 'Mire Map Spike Side', 'Mire Map Spot', 'Mire Crystal Dead End',
    'Mire Hidden Shooters', 'Mire Hidden Shooters Blocked', 'Mire Cross', 'Mire Minibridge', 'Mire BK Door Room',
    'Mire Spikes', 'Mire Ledgehop', 'Mire Bent Bridge', 'Mire Over Bridge', 'Mire Right Bridge', 'Mire Left Bridge',
    'Mire Fishbone', 'Mire South Fish', 'Mire Spike Barrier', 'Mire Square Rail', 'Mire Lone Warp',
    'Mire Wizzrobe Bypass', 'Mire Conveyor Crystal', 'Mire Tile Room', 'Mire Compass Room', 'Mire Compass Chest',
    'Mire Neglected Room', 'Mire Chest View', 'Mire Conveyor Barrier', 'Mire BK Chest Ledge', 'Mire Warping Pool',
    'Mire Torches Top', 'Mire Torches Bottom', 'Mire Attic Hint', 'Mire Dark Shooters', 'Mire Key Rupees',
    'Mire Block X', 'Mire Tall Dark and Roomy', 'Mire Crystal Right', 'Mire Crystal Mid', 'Mire Crystal Left',
    'Mire Crystal Top', 'Mire Shooter Rupees', 'Mire Falling Foes', 'Mire Firesnake Skip', 'Mire Antechamber',
    'Mire Boss'
]

tr_regions = [
    'TR Main Lobby', 'TR Lobby Ledge', 'TR Compass Room', 'TR Hub', 'TR Torches Ledge', 'TR Torches', 'TR Roller Room',
    'TR Tile Room', 'TR Refill', 'TR Pokey 1', 'TR Chain Chomps', 'TR Pipe Pit', 'TR Pipe Ledge', 'TR Lava Dual Pipes',
    'TR Lava Island', 'TR Lava Escape', 'TR Pokey 2', 'TR Twin Pokeys', 'TR Hallway', 'TR Dodgers', 'TR Big View',
    'TR Big Chest', 'TR Big Chest Entrance', 'TR Lazy Eyes', 'TR Dash Room', 'TR Tongue Pull', 'TR Rupees',
    'TR Crystaroller', 'TR Dark Ride', 'TR Dash Bridge', 'TR Eye Bridge', 'TR Crystal Maze', 'TR Crystal Maze End',
    'TR Final Abyss', 'TR Boss'
]

gt_regions = [
    'GT Lobby', 'GT Bob\'s Torch', 'GT Hope Room', 'GT Big Chest', 'GT Blocked Stairs', 'GT Bob\'s Room',
    'GT Tile Room', 'GT Speed Torch', 'GT Speed Torch Upper', 'GT Pots n Blocks', 'GT Crystal Conveyor',
    'GT Compass Room', 'GT Invisible Bridges', 'GT Invisible Catwalk', 'GT Conveyor Cross', 'GT Hookshot East Platform',
    'GT Hookshot North Platform', 'GT Hookshot South Platform', 'GT Hookshot South Entry', 'GT Map Room',
    'GT Double Switch Entry', 'GT Double Switch Switches', 'GT Double Switch Transition', 'GT Double Switch Key Spot',
    'GT Double Switch Exit', 'GT Spike Crystals', 'GT Warp Maze - Left Section', 'GT Warp Maze - Mid Section',
    'GT Warp Maze - Right Section', 'GT Warp Maze - Pit Section', 'GT Warp Maze - Pit Exit Warp Spot',
    'GT Warp Maze Exit Section', 'GT Firesnake Room', 'GT Firesnake Room Ledge', 'GT Warp Maze - Rail Choice',
    'GT Warp Maze - Rando Rail', 'GT Warp Maze - Main Rails', 'GT Warp Maze - Pot Rail', 'GT Petting Zoo',
    'GT Conveyor Star Pits', 'GT Hidden Star', 'GT DMs Room', 'GT Falling Bridge', 'GT Randomizer Room', 'GT Ice Armos',
    'GT Big Key Room', 'GT Four Torches', 'GT Fairy Abyss', 'GT Crystal Paths', 'GT Mimics 1', 'GT Mimics 2',
    'GT Dash Hall', 'GT Hidden Spikes', 'GT Cannonball Bridge', 'GT Refill', 'GT Gauntlet 1', 'GT Gauntlet 2',
    'GT Gauntlet 3', 'GT Gauntlet 4', 'GT Gauntlet 5', 'GT Beam Dash', 'GT Lanmolas 2', 'GT Quad Pot', 'GT Wizzrobes 1',
    'GT Dashing Bridge', 'GT Wizzrobes 2', 'GT Conveyor Bridge', 'GT Torch Cross', 'GT Staredown', 'GT Falling Torches',
    'GT Mini Helmasaur Room', 'GT Bomb Conveyor', 'GT Crystal Circles', 'GT Left Moldorm Ledge',
    'GT Right Moldorm Ledge', 'GT Moldorm', 'GT Moldorm Pit', 'GT Validation', 'GT Validation Door', 'GT Frozen Over',
    'GT Brightly Lit Hall', 'GT Agahnim 2'
]


dungeon_regions = {
    'Hyrule Castle': hyrule_castle_regions,
    'Eastern Palace': eastern_regions,
    'Desert Palace': desert_regions,
    'Tower of Hera': hera_regions,
    'Agahnims Tower': tower_regions,
    'Palace of Darkness': pod_regions,
    'Swamp Palace': swamp_regions,
    'Skull Woods': skull_regions,
    'Thieves Town': thieves_regions,
    'Ice Palace': ice_regions,
    'Misery Mire': mire_regions,
    'Turtle Rock': tr_regions,
    'Ganons Tower': gt_regions
}

region_starts = {
    'Hyrule Castle': ['Hyrule Castle Lobby', 'Hyrule Castle West Lobby', 'Hyrule Castle East Lobby', 'Sewers Rat Path', 'Sanctuary'],
    'Eastern Palace': ['Eastern Lobby'],
    'Desert Palace': ['Desert Back Lobby', 'Desert Main Lobby', 'Desert West Lobby', 'Desert East Lobby'],
    'Tower of Hera': ['Hera Lobby'],
    'Agahnims Tower': ['Tower Lobby'],
    'Palace of Darkness': ['PoD Lobby'],
    'Swamp Palace': ['Swamp Lobby'],
    'Skull Woods': ['Skull 1 Lobby', 'Skull 2 East Lobby', 'Skull 2 West Lobby', 'Skull 3 Lobby', 'Skull Pot Circle',
                    'Skull Pinball', 'Skull Left Drop', 'Skull Back Drop'],
    'Thieves Town': ['Thieves Lobby'],
    'Ice Palace': ['Ice Lobby'],
    'Misery Mire': ['Mire Lobby'],
    'Turtle Rock': ['TR Main Lobby', 'TR Lazy Eyes', 'TR Big Chest Entrance', 'TR Eye Bridge'],
    'Ganons Tower': ['GT Lobby']
}

split_region_starts = {
    'Desert Palace': {
        'Back': ['Desert Back Lobby'],
        'Main': ['Desert Main Lobby', 'Desert West Lobby', 'Desert East Lobby']
    },
    'Skull Woods': {
        '1': ['Skull 1 Lobby', 'Skull Pot Circle'],
        '2': ['Skull 2 West Lobby', 'Skull 2 East Lobby', 'Skull Back Drop'],
        '3': ['Skull 3 Lobby']
    }
}

flexible_starts = {
    'Skull Woods': ['Skull Left Drop', 'Skull Pinball']
}

drop_entrances = [
    'Sewers Rat Path', 'Skull Pinball', 'Skull Left Drop', 'Sanctuary'  # Pot circle, Back drop have unique access
]

dungeon_keys = {
    'Hyrule Castle': 'Small Key (Escape)',
    'Eastern Palace': 'Small Key (Eastern Palace)',
    'Desert Palace': 'Small Key (Desert Palace)',
    'Tower of Hera': 'Small Key (Tower of Hera)',
    'Agahnims Tower': 'Small Key (Agahnims Tower)',
    'Palace of Darkness': 'Small Key (Palace of Darkness)',
    'Swamp Palace': 'Small Key (Swamp Palace)',
    'Skull Woods': 'Small Key (Skull Woods)',
    'Thieves Town': 'Small Key (Thieves Town)',
    'Ice Palace': 'Small Key (Ice Palace)',
    'Misery Mire': 'Small Key (Misery Mire)',
    'Turtle Rock': 'Small Key (Turtle Rock)',
    'Ganons Tower': 'Small Key (Ganons Tower)'
}

dungeon_bigs = {
    'Hyrule Castle': 'Big Key (Escape)',
    'Eastern Palace': 'Big Key (Eastern Palace)',
    'Desert Palace': 'Big Key (Desert Palace)',
    'Tower of Hera': 'Big Key (Tower of Hera)',
    'Agahnims Tower': 'Big Key (Agahnims Tower)',
    'Palace of Darkness': 'Big Key (Palace of Darkness)',
    'Swamp Palace': 'Big Key (Swamp Palace)',
    'Skull Woods': 'Big Key (Skull Woods)',
    'Thieves Town': 'Big Key (Thieves Town)',
    'Ice Palace': 'Big Key (Ice Palace)',
    'Misery Mire': 'Big Key (Misery Mire)',
    'Turtle Rock': 'Big Key (Turtle Rock)',
    'Ganons Tower': 'Big Key (Ganons Tower)'
}

dungeon_hints = {
    'Hyrule Castle': 'in Hyrule Castle',
    'Eastern Palace': 'in Eastern Palace',
    'Desert Palace': 'in Desert Palace',
    'Tower of Hera': 'in Tower of Hera',
    'Agahnims Tower': 'in Castle Tower',
    'Palace of Darkness': 'in Palace of Darkness',
    'Swamp Palace': 'in Swamp Palace)',
    'Skull Woods': 'in Skull Woods',
    'Thieves Town': 'in Thieves\' Town)',
    'Ice Palace': 'in Ice Palace',
    'Misery Mire': 'in Misery Mire',
    'Turtle Rock': 'in Turtle Rock',
    'Ganons Tower': 'in Ganon\'s Tower'
}

