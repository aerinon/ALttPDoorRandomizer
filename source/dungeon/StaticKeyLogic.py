# Entrance randomizer key logic for vanilla dungeons: key_logic_algorithm 'static'.
# Numbers count chest keys only, as the entrance randomizer's has_key does.
from BaseClasses import KeyRuleType
from Dungeons import dungeon_keys, dungeon_bigs
from KeyDoorShuffle import apply_key_rule_specs

GT_RANDOMIZER = ['Ganons Tower - Randomizer Room - Top Left', 'Ganons Tower - Randomizer Room - Top Right',
                 'Ganons Tower - Randomizer Room - Bottom Left', 'Ganons Tower - Randomizer Room - Bottom Right']
GT_COMPASS = ['Ganons Tower - Compass Room - Top Left', 'Ganons Tower - Compass Room - Top Right',
              'Ganons Tower - Compass Room - Bottom Left', 'Ganons Tower - Compass Room - Bottom Right']
TR_EYE_BRIDGE = ['Turtle Rock - Eye Bridge - Bottom Left', 'Turtle Rock - Eye Bridge - Bottom Right',
                 'Turtle Rock - Eye Bridge - Top Left', 'Turtle Rock - Eye Bridge - Top Right']

DOOR_RULES = {
    'Hyrule Castle': {
        'Sewers Secret Room Key Door S': 1, 'Sewers Key Rat NE': 1,
        'Sewers Dark Cross Key Door N': 0, 'Hyrule Dungeon Map Room Key Door S': 0,
        'Hyrule Dungeon Armory Interior Key Door N': 0,
    },
    'Eastern Palace': {'Eastern Dark Square Key Door WN': 0, 'Eastern Darkness Up Stairs': 0},
    'Desert Palace': {
        'Desert East Wing Key Door EN': 1, 'Desert Tiles 1 Up Stairs': 0, 'Desert Beamos Hall NE': 0,
        'Desert Tiles 2 NE': 0,
    },
    'Tower of Hera': {
        'Hera Lobby Key Stairs': {'keys': 1, 'small_key_in': 'Tower of Hera - Big Key Chest', 'with_small_key': 0},
    },
    'Agahnims Tower': {
        'Tower Room 03 Up Stairs': 1, 'Tower Dark Maze ES': 2, 'Tower Dark Archers Up Stairs': 2,
        'Tower Circle of Pots ES': 2,
    },
    'Palace of Darkness': {
        'PoD Middle Cage N': 1, 'PoD Arena Main NW': 4, 'PoD Falling Bridge WN': 6,
        'PoD Basement Ledge Up Stairs': {'keys': 6, 'small_key_in': 'Palace of Darkness - Big Key Chest',
                                         'with_small_key': 3},
        'PoD Compass Room SE': {'keys': 6, 'small_key_in': 'Palace of Darkness - Harmless Hellway',
                                'with_small_key': 4},
        'PoD Dark Pegs WN': 6,
    },
    'Swamp Palace': {
        'Swamp Entrance Down Stairs': 1, 'Swamp Pot Row WS': 0, 'Swamp Trench 1 Key Ledge NW': 0,
        'Swamp Hub WN': 0, 'Swamp Hub North Ledge N': 0, 'Swamp Waterway NW': 0,
    },
    'Skull Woods': {
        'Skull Map Room SE': 1, 'Skull Pinball NE': 1, 'Skull 1 Lobby WS': 2, 'Skull 2 West Lobby NW': 0,
        'Skull 3 Lobby NW': 3, 'Skull Spike Corner ES': 3,
    },
    'Thieves Town': {
        'Thieves Hallway WS': 0, 'Thieves Spike Switch Up Stairs': 1,
        'Thieves Conveyor Bridge WS': {'keys': 1, 'small_key_in': "Thieves' Town - Big Chest", 'with_small_key': 0},
    },
    'Ice Palace': {
        'Ice Jelly Key Down Stairs': 0, 'Ice Conveyor SW': 0,
        # without hookshot the east side is only in logic with the big key over there; 3 keys never exist
        'Ice Spike Cross ES': {'keys': 3, 'big_key_in': ['Ice Palace - Spike Room', 'Ice Palace - Big Key Chest',
                                                          'Ice Palace - Map Chest'], 'with_big_key': 1},
        'Ice Tall Hint SE': 0, 'Ice Backwards Room Down Stairs': 2, 'Ice Switch Room ES': 2,
    },
    'Misery Mire': {
        'Mire Hub WS': {'keys': 3, 'big_key_in': ['Misery Mire - Compass Chest', 'Misery Mire - Big Key Chest'],
                        'with_big_key': 2},
        'Mire Conveyor Crystal WS': {'keys': 3, 'big_key_in': ['Misery Mire - Compass Chest',
                                                                'Misery Mire - Big Key Chest'], 'with_big_key': 2},
        'Mire Hub Right EN': 1, 'Mire Spikes NW': 1, 'Mire Fishbone SE': 0, 'Mire Dark Shooters SE': 0,
    },
    'Turtle Rock': {  # most restrictive case; set_static_key_rules relaxes it by entrance access
        'TR Hub NW': 4, 'TR Pokey 1 NW': 4, 'TR Chain Chomps Down Stairs': 4, 'TR Pokey 2 ES': 4,
        'TR Crystaroller Down Stairs': 3, 'TR Dash Bridge WS': 4,
    },
    'Ganons Tower': {
        'GT Torch EN': 0, 'GT Tile Room EN': 3,
        'GT Hookshot ES': {'keys': 4, 'big_key_in': 'Ganons Tower - Map Chest', 'with_big_key': 3,
                           'small_key_in': 'Ganons Tower - Map Chest', 'with_small_key': 3},
        'GT Double Switch EN': 2, 'GT Firesnake Room SW': 3, 'GT Conveyor Star Pits EN': 3,
        'GT Mini Helmasaur Room WN': 3, 'GT Crystal Circles SW': 4,
    },
}


def static_logic_supported(world, player):
    return (world.doorShuffle[player] == 'vanilla' and world.dropshuffle[player] == 'none'
            and world.pottery[player] in ('none', 'cave'))


def static_door_rules(world, player):
    if not static_logic_supported(world, player):
        raise Exception('static key logic needs vanilla doors, unshuffled key drops and unshuffled key pots')
    specs = {}
    for doors in DOOR_RULES.values():
        for door, spec in doors.items():
            spec = dict(spec) if isinstance(spec, dict) else {'keys': spec}
            if 'big_key_in' in spec and isinstance(spec['big_key_in'], str):
                spec['big_key_in'] = [spec['big_key_in']]
            specs[door] = spec
    apply_key_rule_specs(world, player, specs, chest_counting=True, validate=False)
    # the analysis's own conditionals would let doors open with fewer keys than the table says
    for door_name, spec in specs.items():
        door = world.get_door(door_name, player)
        for d, d_spec in ((door, spec), (door.dest, specs.get(door.dest.name, {}) if door.dest else None)):
            key_logic = next((kl for kl in world.key_logic[player].values() if d and d.name in kl.door_rules), None)
            if key_logic is None or d_spec is None:
                continue
            rule = key_logic.door_rules[d.name]
            if 'big_key_in' not in d_spec:
                rule.new_rules.pop((KeyRuleType.Lock, key_logic.bk_name), None)
                rule.alternate_small_key, rule.alternate_big_key_loc = None, set()
            if 'small_key_in' not in d_spec:
                rule.new_rules.pop(KeyRuleType.AllowSmall, None)
                rule.allow_small, rule.small_location = False, None


def set_static_key_rules(world, player):
    from Rules import set_rule, add_rule, forbid_item, set_always_allow, item_in_locations, item_name

    def keys(dungeon, count):
        return lambda state: state.has_sm_key_strict(dungeon_keys[dungeon], player, count)

    def big_key_in(dungeon, locations):
        return lambda state: item_in_locations(state, dungeon_bigs[dungeon], player, [(x, player) for x in locations])

    def small_key_at(dungeon, location):
        return lambda state: item_name(state, location, player) == (dungeon_keys[dungeon], player)

    def or_rules(*rules):
        return lambda state: any(rule(state) for rule in rules)

    def and_rules(*rules):
        return lambda state: all(rule(state) for rule in rules)

    def loc(name):
        return world.get_location(name, player)

    def allow_small(dungeon, location, extra=None):
        # the fill may put the key here even though the chest is behind its own door
        if world.accessibility[player] != 'locations':
            key = dungeon_keys[dungeon]
            set_always_allow(loc(location), lambda state, item: item.name == key and item.player == player
                             and (extra is None or extra(state)))
        else:
            forbid_item(loc(location), dungeon_keys[dungeon], player)

    if world.mode[player] != 'standard':
        for name in ['Hyrule Castle - Boomerang Chest', "Hyrule Castle - Zelda's Chest"]:
            add_rule(loc(name), keys('Hyrule Castle', 1))
            forbid_item(loc(name), dungeon_keys['Hyrule Castle'], player)

    for name in ['Desert Palace - Boss', 'Desert Palace - Prize']:
        add_rule(loc(name), keys('Desert Palace', 1))
    for name in ['Desert Palace - Boss', 'Desert Palace - Big Key Chest', 'Desert Palace - Compass Chest']:
        forbid_item(loc(name), dungeon_keys['Desert Palace'], player)

    allow_small('Tower of Hera', 'Tower of Hera - Big Key Chest')

    allow_small('Palace of Darkness', 'Palace of Darkness - Big Key Chest', keys('Palace of Darkness', 5))
    allow_small('Palace of Darkness', 'Palace of Darkness - Harmless Hellway', keys('Palace of Darkness', 5))

    allow_small('Thieves Town', "Thieves' Town - Big Chest", lambda state: state.has('Hammer', player))
    for name in ["Thieves' Town - Attic", "Thieves' Town - Boss"]:
        forbid_item(loc(name), dungeon_keys['Thieves Town'], player)

    forbid_item(loc('Skull Woods - Boss'), dungeon_keys['Skull Woods'], player)

    # Kholdstare: 2 keys, or Somaria and 1
    somaria = and_rules(lambda state: state.has('Cane of Somaria', player), keys('Ice Palace', 1))
    for name in ['Ice Backwards Room Down Stairs', 'Ice Switch Room ES', 'Ice Refill WS']:
        add_rule(world.get_entrance(name, player), somaria, 'or')

    set_turtle_rock_rules(world, player, keys, big_key_in, small_key_at, or_rules, allow_small, forbid_item,
                          set_rule, item_name, loc)

    gt = 'Ganons Tower'
    add_rule(loc('Ganons Tower - Firesnake Room'), or_rules(
        keys(gt, 3), and_rules(or_rules(big_key_in(gt, GT_RANDOMIZER),
                                        small_key_at(gt, 'Ganons Tower - Firesnake Room')), keys(gt, 2))))
    for name in GT_RANDOMIZER:
        add_rule(loc(name), or_rules(keys(gt, 4), and_rules(big_key_in(gt, GT_RANDOMIZER), keys(gt, 3))))
    for name in GT_COMPASS:
        add_rule(loc(name), or_rules(keys(gt, 4), and_rules(big_key_in(gt, GT_COMPASS), keys(gt, 3))))
    allow_small(gt, 'Ganons Tower - Map Chest', keys(gt, 3))


def set_door_number(world, player, door_name, number):
    key_logic = world.key_logic[player]['Turtle Rock']
    door = world.get_door(door_name, player)
    for d in (door, key_logic.sm_doors.get(door)):
        rule = key_logic.door_rules.get(d.name) if d else None
        if rule:
            rule.small_key_num = number
            rule.new_rules[KeyRuleType.WorstCase] = number
            for rule_type in list(rule.new_rules.keys()):
                if rule_type != KeyRuleType.WorstCase and rule.new_rules[rule_type] >= number:
                    del rule.new_rules[rule_type]


def set_turtle_rock_rules(world, player, keys, big_key_in, small_key_at, or_rules, allow_small, forbid_item,
                          set_rule, item_name, loc):
    tr, chest = 'Turtle Rock', 'Turtle Rock - Big Key Chest'
    # everything but this dungeon's small keys, so its key doors stay shut
    from BaseClasses import CollectionState
    full = world.get_all_state(keys=False)
    state = CollectionState(world)
    state.prog_items = full.prog_items.copy()
    state.prog_items[(dungeon_keys[tr], player)] = 0

    def reachable(region):
        return world.get_region(region, player).can_reach(state)

    back, front = reachable('TR Eye Bridge'), reachable('TR Main Lobby')
    middle, big_chest = reachable('TR Lazy Eyes'), reachable('TR Big Chest Entrance')

    def chest_keys_needed(state):
        item = item_name(state, chest, player)
        if item == (dungeon_keys[tr], player):
            return 0
        if item == (dungeon_bigs[tr], player):
            return 2
        return 4

    no_big_key = ['Turtle Rock - Big Chest', 'Turtle Rock - Boss']
    if back:
        set_rule(loc(chest), or_rules(keys(tr, 4), small_key_at(tr, chest)))
        set_door_number(world, player, 'TR Crystaroller Down Stairs', 4)
        allow_small(tr, chest)
    elif front and middle:
        set_rule(loc(chest), lambda state: state.has_sm_key_strict(dungeon_keys[tr], player, chest_keys_needed(state)))
        allow_small(tr, chest)
        no_big_key += ['Turtle Rock - Crystaroller Room'] + TR_EYE_BRIDGE
    elif front:
        for door in ['TR Chain Chomps Down Stairs', 'TR Pokey 2 ES']:
            set_door_number(world, player, door, 2)
        for door in ['TR Hub NW', 'TR Pokey 1 NW']:
            set_door_number(world, player, door, 1)
        set_rule(loc(chest), lambda state: state.has_sm_key_strict(dungeon_keys[tr], player, chest_keys_needed(state)))
        allow_small(tr, chest, keys(tr, 2))
    elif big_chest:
        # the doors back into the first section: 2 keys if the big key is in the first section, else 4
        first_section = ['Turtle Rock - Compass Chest', 'Turtle Rock - Roller Room - Left', 'Turtle Rock - Roller Room - Right']
        for door in ['TR Chain Chomps SW', 'TR Pokey 1 SW']:
            rule = world.key_logic[player][tr].door_rules.get(door)
            if rule:
                rule.alternate_big_key_loc = {loc(x) for x in first_section}
                rule.new_rules[(KeyRuleType.Lock, dungeon_bigs[tr])] = 2
                rule.alternate_small_key = 2
        set_rule(loc(chest), or_rules(keys(tr, 4), small_key_at(tr, chest)))
        allow_small(tr, chest)
        no_big_key += ['Turtle Rock - Crystaroller Room'] + TR_EYE_BRIDGE
        if not world.bigkeyshuffle[player]:
            no_big_key.append(chest)
    for name in no_big_key:
        forbid_item(loc(name), dungeon_bigs[tr], player)
