"""
Helper functions to deliver entrance/exit/region sets to OWG rules.
"""

from BaseClasses import Entrance

# Cave regions that superbunny can get through - but only with a sword.
sword_required_superbunny_mirror_regions = ["Spiral Cave (Top)"]

# Cave regions that superbunny can get through - but only with boots.
boots_required_superbunny_mirror_regions = ["Two Brothers House"]

# Cave locations that superbunny can access - but only with boots.
boots_required_superbunny_mirror_locations = [
    "Sahasrahla's Hut - Left",
    "Sahasrahla's Hut - Middle",
    "Sahasrahla's Hut - Right",
]

# Entrances that can't be superbunny-mirrored into.
invalid_mirror_bunny_entrances = [
    "Hype Cave",
    "Bonk Fairy (Dark)",
    "Thieves Town",
    "Hammer Peg Cave",
    "Brewery",
    "Hookshot Cave",
    "Dark Lake Hylia Ledge Fairy",
    "Dark Lake Hylia Ledge Spike Cave",
    "Palace of Darkness",
    "Misery Mire",
    "Turtle Rock",
    "Bonk Rock Cave",
    "Bonk Fairy (Light)",
    "50 Rupee Cave",
    "20 Rupee Cave",
    "Checkerboard Cave",
    "Light Hype Fairy",
    "Waterfall of Wishing",
    "Light World Bomb Hut",
    "Mini Moldorm Cave",
    "Ice Rod Cave",
    "Sanctuary Grave",
    "Kings Grave",
    "Sanctuary Grave",
    "Hyrule Castle Secret Entrance Drop",
    "Skull Woods Second Section Hole",
    "Skull Woods First Section Hole (North)",
]

# Interior locations that can be accessed with superbunny state.
superbunny_accessible_locations = [
    "Waterfall of Wishing - Left",
    "Waterfall of Wishing - Right",
    "King's Tomb",
    "Floodgate",
    "Floodgate Chest",
    "Cave 45",
    "Bonk Rock Cave",
    "Brewery",
    "C-Shaped House",
    "Chest Game",
    "Mire Shed - Left",
    "Mire Shed - Right",
    "Secret Passage",
    "Ice Rod Cave",
    "Pyramid Fairy - Left",
    "Pyramid Fairy - Right",
    "Superbunny Cave - Top",
    "Superbunny Cave - Bottom",
    "Blind's Hideout - Left",
    "Blind's Hideout - Right",
    "Blind's Hideout - Far Left",
    "Blind's Hideout - Far Right",
    "Kakariko Well - Left",
    "Kakariko Well - Middle",
    "Kakariko Well - Right",
    "Kakariko Well - Bottom",
    "Kakariko Tavern",
    "Library",
    "Spiral Cave",
] + boots_required_superbunny_mirror_locations


# Entrances that can be reached with full equipment using overworld glitches and don't need to be an exit.
# The following are still be mandatory exits:
# Open:
# Turtle Rock Isolated Ledge Entrance
# Skull Woods Second Section Door (West) (or Skull Woods Final Section)
# Inverted:
# Two Brothers House (West)
# Desert Palace Entrance (East)


non_mandatory_exits = [
    "Bumper Cave (Top)",
    "Death Mountain Return Cave (West)",
    "Hookshot Cave Back Entrance",
]

inverted_non_mandatory_exits = [
    "Desert Palace Entrance (North)",
    "Desert Palace Entrance (West)",
    "Agahnims Tower",
    "Hyrule Castle Entrance (West)",
    "Hyrule Castle Entrance (East)",
] + non_mandatory_exits

open_non_mandatory_exits = [
    "Dark Death Mountain Ledge (West)",
    "Dark Death Mountain Ledge (East)",
    "Mimic Cave",
    "Desert Palace Entrance (East)",
] + non_mandatory_exits


# Special Light World region exits that require boots clips.
boots_clip_exits_lw = [
    ('Lumberjack DMA Clip', 'Lumberjack Area', 'West Death Mountain (Bottom)'),
    ('Spectacle Rock Clip', 'West Death Mountain (Top)', 'Spectacle Rock Ledge'),
    ('Hera Ascent Clip', 'West Death Mountain (Bottom)', 'West Death Mountain (Top)'),
    ('Death Mountain Glitched Bridge Clip', 'West Death Mountain (Bottom)', 'East Death Mountain (Top East)'),
    ('Sanctuary DMD Clip', 'West Death Mountain (Bottom)', 'Sanctuary Area'),
    ('Graveyard Ledge Clip', 'West Death Mountain (Bottom)', 'Graveyard Ledge'),
    ('Kings Grave Clip', 'West Death Mountain (Bottom)', 'Kings Grave Area'),
    ('Floating Island Clip', 'East Death Mountain (Top East)', 'Death Mountain Floating Island'),
    ('Zora DMD Clip', 'Death Mountain TR Pegs Area', 'Zoras Domain'),
    ('TR Pegs Ledge Clip', 'Death Mountain TR Pegs Area', 'Death Mountain TR Pegs Ledge'),
    ('Mountain Pass Ledge Clip', 'Mountain Pass Area', 'Mountain Pass Ledge'),
    ('Mountain Pass Entry Clip', 'Kakariko Pond Area', 'Mountain Pass Entry'),
    ('Bat Cave River Clip', 'Blacksmith Area', 'Blacksmith Ledge'),
    ('Desert Keep Clip', 'Maze Race Area', 'Desert Ledge Keep'),
    ('Desert Ledge Clip', 'Maze Race Area', 'Desert Ledge'),
    ('Maze Race Prize Clip', 'Maze Race Area', 'Maze Race Prize'),
    ('Stone Bridge To Cliff Clip', 'Stone Bridge South Area', 'Central Cliffs'),
    ('Hobo Clip', 'Stone Bridge South Area', 'Stone Bridge Water'),
    ('Bombos Tablet Clip', 'Desert Area', 'Bombos Tablet Ledge'),
    ('Desert Teleporter Clip', 'Desert Area', 'Desert Teleporter Ledge'),
    ('Cave 45 Clip', 'Flute Boy Approach Area', 'Cave 45 Ledge'),
    ('Desert Northern Cliffs Clip', 'Flute Boy Approach Area', 'Desert Northern Cliffs')
]

# Special Dark World region exits that require boots clips.
boots_clip_exits_dw = [
    ('Dark World DMA Clip', 'Dark Lumberjack Area', 'West Dark Death Mountain (Bottom)'),
    ('Dark Death Mountain Descent', 'West Dark Death Mountain (Bottom)', 'Dark Chapel Area'),
    ('Ganons Tower Ascent', 'West Dark Death Mountain (Bottom)', 'GT Stairs'),  # This only gets you to the GT entrance
    ('Dark Death Mountain Glitched Bridge', 'West Dark Death Mountain (Bottom)', 'East Dark Death Mountain (Top)'),
    ('DW Floating Island Clip', 'East Dark Death Mountain (Bottom)', 'Dark Death Mountain Floating Island'),
    ('Turtle Rock (Top) Clip', 'Turtle Rock Area', 'Turtle Rock Ledge'),
    ('Catfish DMD', 'Turtle Rock Area', 'Catfish Area'),
    ('Bumper Cave Ledge Clip', 'Bumper Cave Area', 'Bumper Cave Ledge'),
    ('Bumper Cave Entry Clip', 'Outcast Pond Area', 'Bumper Cave Entry'),
    ('Broken Bridge Hammer Rock Skip Clip', 'Qirn Jump East Bank', 'Broken Bridge Area'),
    ('Dark Witch Rock Skip Clip', 'Dark Witch Area', 'Dark Witch Northeast'),
    ('Hammer Pegs River Clip', 'Dark Dunes Area', 'Hammer Pegs Area'),
    ('Hammer Bridge To Cliff Clip', 'Hammer Bridge South Area', 'Dark Central Cliffs'),
    ('Mire Cliffs Clip', 'Stumpy Approach Area', 'Mire Northern Cliffs'),
    ('Dark Lake Hylia Ledge Clip', 'Darkness Nook Area', 'Shopping Mall Area'),
    ('Mire Teleporter Clip', 'Mire Area', 'Mire Teleporter Ledge')
]


# Dark World drop-down ledges that require glitched speed.
glitched_speed_drops_dw = [
    ('Dark Death Mountain Ledge Clip', 'East Dark Death Mountain (Top)', 'Dark Death Mountain Ledge')
]


# Out of bounds transitions using the mirror
mirror_clip_spots_dw = [
    ('Bunny DMD Mirror Spot', 'West Dark Death Mountain (Bottom)', 'Qirn Jump Area'),
    (
        'Dark Death Mountain Bunny Mirror To East Jump',
        'West Dark Death Mountain (Bottom)',
        'East Dark Death Mountain (Bottom)',
    ),
    ('Desert East Mirror Clip', 'Mire Area', 'Desert Mouth'),
]

# Mirror shenanigans placing a mirror portal with a broken camera
mirror_offset_spots_dw = [('Dark Death Mountain Offset Mirror', 'West Dark Death Mountain (Bottom)', 'Pyramid Area')]

# Mirror shenanigans placing a mirror portal with a broken camera
mirror_offset_spots_lw = [
    ('Death Mountain Offset Mirror', 'West Death Mountain (Bottom)', 'Hyrule Castle Area'),
    ('Death Mountain Uncle Offset Mirror', 'West Death Mountain (Bottom)', 'Hyrule Castle Courtyard Northeast'),
    ('Death Mountain Castle Ledge Offset Mirror', 'West Death Mountain (Bottom)', 'Hyrule Castle Ledge'),
]


def create_owg_connections(world, player):
    """
    Add OWG transitions to player's world without logic
    """
    if world.mode[player] == "inverted":
        connections = (
            boots_clip_exits_dw
            + boots_clip_exits_lw
            + glitched_speed_drops_dw
            + mirror_offset_spots_lw
        )
    else:
        connections = (
            boots_clip_exits_dw
            + boots_clip_exits_lw
            + glitched_speed_drops_dw
            + mirror_clip_spots_dw
            + mirror_offset_spots_dw
        )
    create_no_logic_connections(player, world, connections)


def overworld_glitches_rules(world, player):
    inverted = world.mode[player] == "inverted"

    # Boots-accessible locations.
    set_owg_rules(
        player,
        world,
        boots_clip_exits_lw,
        lambda state: state.can_boots_clip_lw(player),
    )
    set_owg_rules(
        player,
        world,
        boots_clip_exits_dw,
        lambda state: state.can_boots_clip_dw(player),
    )
    # Glitched speed drops.
    set_owg_rules(
        player,
        world,
        glitched_speed_drops_dw,
        lambda state: state.can_get_glitched_speed_dw(player),
    )
    # Dark Death Mountain Ledge Clip also accessible with mirror.
    if not inverted:
        add_alternate_rule(
            world.get_entrance('Dark Death Mountain Ledge Clip', player), lambda state: state.has_Mirror(player)
        )

    # Mirror clip spots.
    if inverted:
        set_owg_rules(
            player,
            world,
            mirror_offset_spots_lw,
            lambda state: state.has_Mirror(player) and state.can_boots_clip_dw(player),
        )
    else:
        set_owg_rules(player, world, mirror_clip_spots_dw, lambda state: state.has_Mirror(player))
        set_owg_rules(
            player,
            world,
            mirror_offset_spots_dw,
            lambda state: state.has_Mirror(player) and state.can_boots_clip_lw(player),
        )
        
    # Regions that require the boots and some other stuff.
    if not inverted:
        add_alternate_rule(
            world.get_entrance('Zora Waterfall Approach', player),
            lambda state: state.has_Pearl(player) or state.has_Boots(player),
        )  # assumes access to Waterwalk ability (boots case)
    else:
        add_alternate_rule(
            world.get_entrance('Zora Waterfall Approach', player),
            lambda state: state.has_Pearl(player)
        )

    add_alternate_rule(
        world.get_location("Zora's Ledge", player), lambda state: state.can_boots_clip_lw(player)
    )  # assumes access to Waterwalk ability

    # Bunny pocket
    if not inverted:
        add_alternate_rule(world.get_entrance("Skull Woods Final Section", player), lambda state: state.can_bunny_pocket(player) and state.has("Fire Rod", player))
        add_alternate_rule(world.get_entrance("Dark World Shop", player), lambda state: state.can_bunny_pocket(player) and state.has("Hammer", player))
    

def add_alternate_rule(entrance, rule):
    old_rule = entrance.access_rule
    entrance.access_rule = lambda state: old_rule(state) or rule(state)


def create_no_logic_connections(player, world, connections):
    for entrance, parent_region, target_region, *rule_override in connections:
        parent = world.get_region(parent_region, player)
        target = world.get_region(target_region, player)
        connection = Entrance(player, entrance, parent)
        parent.exits.append(connection)
        connection.connect(target)


def set_owg_rules(player, world, connections, default_rule):
    for entrance, parent_region, target_region, *rule_override in connections:
        connection = world.get_entrance(entrance, player)
        rule = rule_override[0] if len(rule_override) > 0 else default_rule
        connection.access_rule = rule
