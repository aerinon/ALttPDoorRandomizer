from BaseClasses import RegionType, Terrain, Entrance
from Utils import bidict
import logging

def link_overworld(world, player):
    # setup mandatory connections
    for exitname, regionname in mandatory_connections:
        connect_simple(world, exitname, regionname, player)

    # apply tile logical connections
    if not world.mode[player] == 'inverted':
        for exitname, regionname in open_mandatory_connections:
            connect_simple(world, exitname, regionname, player)
    else:
        for exitname, regionname in inverted_mandatory_connections:
            connect_simple(world, exitname, regionname, player)

    for forward_edge, back_edge in default_connections:
        connect_two_way(world, forward_edge, back_edge, player)


def connect_simple(world, exitname, regionname, player):
    world.get_entrance(exitname, player).connect(world.get_region(regionname, player))

def connect_two_way(world, edgename1, edgename2, player):
    edge1 = world.get_entrance(edgename1, player)
    edge2 = world.get_entrance(edgename2, player)
    edge1.connect(edge2.parent_region)
    edge2.connect(edge1.parent_region)

def create_flute_exits(world, player):
    for region in (r for r in world.regions if r.player == player and r.terrain == Terrain.Land and r.name not in ['Zoras Domain', 'Master Sword Meadow', 'Hobo Bridge']):
        if region.type == (RegionType.LightWorld if world.mode[player] != 'inverted' else RegionType.DarkWorld):
            exitname = 'Flute From ' + region.name
            exit = Entrance(region.player, exitname, region)
            exit.spot_type = 'Flute'
            exit.connect(world.get_region('Flute Sky', player))
            region.exits.append(exit)

def get_mirror_exit_name(from_region, to_region):
    if from_region in mirror_connections and to_region in mirror_connections[from_region]:
        if len(mirror_connections[from_region]) == 1:
            return f'Mirror From {from_region}'
        else:
            return f'Mirror To {to_region}'
    return None

def create_mirror_exits(world, player):
    mirror_exits = set()
    for region in (r for r in world.regions if r.player == player and r.name not in ['Zoras Domain', 'Master Sword Meadow', 'Hobo Bridge']):
        if region.type == (RegionType.DarkWorld if world.mode[player] != 'inverted' else RegionType.LightWorld):
            if region.name in mirror_connections:
                for region_dest_name in mirror_connections[region.name]:
                    exitname = get_mirror_exit_name(region.name, region_dest_name)
                    
                    assert exitname not in mirror_exits, f'Mirror Exit with name already exists: {exitname}'

                    exit = Entrance(region.player, exitname, region)
                    exit.spot_type = 'Mirror'
                    to_region = world.get_region(region_dest_name, player)
                    if region.terrain == Terrain.Water or to_region.terrain == Terrain.Water:
                        exit.access_rule = lambda state: state.has('Flippers', player) and state.has_Pearl(player) and state.has_Mirror(player)
                    else:
                        exit.access_rule = lambda state: state.has_Mirror(player)
                    exit.connect(to_region)
                    region.exits.append(exit)

                    mirror_exits.add(exitname)

def create_dynamic_exits(world, player):
    create_flute_exits(world, player)
    create_mirror_exits(world, player)
    world.initialize_regions()


# these are connections that cannot be shuffled and always exist. They link together separate parts of the world we need to divide into regions
mandatory_connections = [
    ('Links House S&Q', 'Links House'),

    # Intra-tile OW Connections
    ('Lost Woods Bush (West)', 'Lost Woods East Area'), #pearl
    ('Lost Woods Bush (East)', 'Lost Woods West Area'), #pearl
    ('West Death Mountain Drop', 'West Death Mountain (Bottom)'),
    ('Spectacle Rock Ledge Drop', 'West Death Mountain (Top)'),
    ('DM Hammer Bridge (West)', 'East Death Mountain (Top East)'), #hammer
    ('DM Hammer Bridge (East)', 'East Death Mountain (Top West)'), #hammer
    ('EDM To Spiral Ledge Drop', 'Spiral Cave Ledge'),
    ('EDM To Fairy Ledge Drop', 'Fairy Ascension Ledge'),
    ('EDM Ledge Drop', 'East Death Mountain (Bottom)'),
    ('Spiral Ledge Drop', 'East Death Mountain (Bottom)'),
    ('Fairy Ascension Ledge Drop', 'Fairy Ascension Plateau'),
    ('Fairy Ascension Plateau Ledge Drop', 'East Death Mountain (Bottom)'),
    ('Fairy Ascension Rocks (Inner)', 'East Death Mountain (Bottom)'), #mitts
    ('Fairy Ascension Rocks (Outer)', 'Fairy Ascension Plateau'), #mitts
    ('DM Broken Bridge (West)', 'East Death Mountain (Bottom)'), #hookshot
    ('DM Broken Bridge (East)', 'East Death Mountain (Bottom Left)'), #hookshot
    ('TR Pegs Ledge Entry', 'Death Mountain TR Pegs Ledge'), #mitts
    ('TR Pegs Ledge Leave', 'Death Mountain TR Pegs Area'), #mitts
    ('TR Pegs Ledge Drop', 'Death Mountain TR Pegs Area'),
    ('Mountain Pass Rock (Outer)', 'Mountain Pass Entry'), #glove
    ('Mountain Pass Rock (Inner)', 'Mountain Pass Area'), #glove
    ('Mountain Pass Entry Ledge Drop', 'Mountain Pass Area'),
    ('Mountain Pass Ledge Drop', 'Mountain Pass Area'),
    ('Zora Waterfall Landing', 'Zora Waterfall Area'),
    ('Zora Waterfall Water Drop', 'Zora Waterfall Water'), #flippers
    ('Zora Waterfall Water Entry', 'Zora Waterfall Water'), #flippers
    ('Zora Waterfall Approach', 'Zora Waterfall Entryway'), #flippers
    ('Lost Woods Pass Hammer (North)', 'Lost Woods Pass Portal Area'), #hammer
    ('Lost Woods Pass Hammer (South)', 'Lost Woods Pass East Top Area'), #hammer
    ('Lost Woods Pass Rock (North)', 'Lost Woods Pass East Bottom Area'), #mitts
    ('Lost Woods Pass Rock (South)', 'Lost Woods Pass Portal Area'), #mitts
    ('Bonk Rock Ledge Drop', 'Sanctuary Area'),
    ('Graveyard Ledge Drop', 'Graveyard Area'),
    ('Kings Grave Rocks (Outer)', 'Kings Grave Area'), #mitts
    ('Kings Grave Rocks (Inner)', 'Graveyard Area'), #mitts
    ('River Bend Water Drop', 'River Bend Water'), #flippers
    ('River Bend East Water Drop', 'River Bend Water'), #flippers
    ('River Bend West Pier', 'River Bend Area'),
    ('River Bend East Pier', 'River Bend East Bank'),
    ('Potion Shop Water Drop', 'Potion Shop Water'), #flippers
    ('Potion Shop Northeast Water Drop', 'Potion Shop Water'), #flippers
    ('Potion Shop Rock (South)', 'Potion Shop Northeast'), #glove
    ('Potion Shop Rock (North)', 'Potion Shop Area'), #glove
    ('Zora Approach Water Drop', 'Zora Approach Water'), #flippers
    ('Zora Approach Rocks (West)', 'Zora Approach Ledge'), #mitts/boots
    ('Zora Approach Rocks (East)', 'Zora Approach Area'), #mitts/boots
    ('Zora Approach Bottom Ledge Drop', 'Zora Approach Ledge'),
    ('Zora Approach Ledge Drop', 'Zora Approach Area'),
    ('Kakariko Southwest Bush (North)', 'Kakariko Southwest'), #pearl
    ('Kakariko Southwest Bush (South)', 'Kakariko Village'), #pearl
    ('Kakariko Yard Bush (South)', 'Kakariko Bush Yard'), #pearl
    ('Kakariko Yard Bush (North)', 'Kakariko Village'), #pearl
    ('Hyrule Castle Southwest Bush (North)', 'Hyrule Castle Southwest'), #pearl
    ('Hyrule Castle Southwest Bush (South)', 'Hyrule Castle Area'), #pearl
    ('Hyrule Castle Courtyard Bush (North)', 'Hyrule Castle Courtyard'), #pearl
    ('Hyrule Castle Courtyard Bush (South)', 'Hyrule Castle Courtyard Northeast'), #pearl
    ('Hyrule Castle Main Gate (South)', 'Hyrule Castle Courtyard'), #aga+mirror
    ('Hyrule Castle Main Gate (North)', 'Hyrule Castle Area'), #aga+mirror
    ('Hyrule Castle Ledge Drop', 'Hyrule Castle Area'),
    ('Hyrule Castle Ledge Courtyard Drop', 'Hyrule Castle Courtyard'),
    ('Hyrule Castle East Rock (Inner)', 'Hyrule Castle East Entry'), #glove
    ('Hyrule Castle East Rock (Outer)', 'Hyrule Castle Area'), #glove
    ('Wooden Bridge Bush (South)', 'Wooden Bridge Northeast'), #pearl
    ('Wooden Bridge Bush (North)', 'Wooden Bridge Area'), #pearl
    ('Wooden Bridge Water Drop', 'Wooden Bridge Water'), #flippers
    ('Wooden Bridge Northeast Water Drop', 'Wooden Bridge Water'), #flippers
    ('Blacksmith Ledge Peg (West)', 'Blacksmith Ledge'), #hammer
    ('Blacksmith Ledge Peg (East)', 'Blacksmith Area'), #hammer
    ('Maze Race Game', 'Maze Race Prize'), #pearl
    ('Maze Race Ledge Drop', 'Maze Race Area'),
    ('Stone Bridge (Southbound)', 'Stone Bridge South Area'),
    ('Stone Bridge (Northbound)', 'Stone Bridge North Area'),
    ('Desert Statue Move', 'Desert Stairs'), #book
    ('Desert Ledge Drop', 'Desert Area'),
    ('Desert Ledge Rocks (Outer)', 'Desert Ledge Keep'), #glove
    ('Desert Ledge Rocks (Inner)', 'Desert Ledge'), #glove
    ('Checkerboard Ledge Drop', 'Desert Area'),
    ('Desert Mouth Drop', 'Desert Area'),
    ('Desert Teleporter Drop', 'Desert Area'),
    ('Bombos Tablet Drop', 'Desert Area'),
    ('Flute Boy Bush (North)', 'Flute Boy Approach Area'), #pearl
    ('Flute Boy Bush (South)', 'Flute Boy Bush Entry'), #pearl
    ('Cave 45 Ledge Drop', 'Flute Boy Approach Area'),
    ('C Whirlpool Water Entry', 'C Whirlpool Water'), #flippers
    ('C Whirlpool Landing', 'C Whirlpool Area'),
    ('C Whirlpool Rock (Bottom)', 'C Whirlpool Outer Area'), #glove
    ('C Whirlpool Rock (Top)', 'C Whirlpool Area'), #glove
    ('C Whirlpool Pegs (Outer)', 'C Whirlpool Portal Area'), #hammer
    ('C Whirlpool Pegs (Inner)', 'C Whirlpool Area'), #hammer
    ('Statues Water Entry', 'Statues Water'), #flippers
    ('Statues Landing', 'Statues Area'),
    ('Lake Hylia Water Drop', 'Lake Hylia Water'), #flippers
    ('Lake Hylia South Water Drop', 'Lake Hylia Water'), #flippers
    ('Lake Hylia Northeast Water Drop', 'Lake Hylia Water'), #flippers
    ('Lake Hylia Central Water Drop', 'Lake Hylia Water'), #flippers
    ('Lake Hylia Island Water Drop', 'Lake Hylia Water'), #flippers
    ('Lake Hylia Central Island Pier', 'Lake Hylia Central Island'),
    ('Lake Hylia West Pier', 'Lake Hylia Northwest Bank'),
    ('Lake Hylia East Pier', 'Lake Hylia Northeast Bank'),
    ('Lake Hylia Water D Approach', 'Lake Hylia Water D'),
    ('Lake Hylia Water D Leave', 'Lake Hylia Water'), #flippers
    ('Ice Cave Water Drop', 'Ice Cave Water'), #flippers
    ('Ice Cave Pier', 'Ice Cave Area'),
    ('Desert Pass Ledge Drop', 'Desert Pass Area'),
    ('Desert Pass Rocks (North)', 'Desert Pass Southeast'), #glove
    ('Desert Pass Rocks (South)', 'Desert Pass Area'), #glove
    ('Octoballoon Water Drop', 'Octoballoon Water'), #flippers
    ('Octoballoon Waterfall Water Drop', 'Octoballoon Water'), #flippers
    ('Octoballoon Pier', 'Octoballoon Area'),

    ('Skull Woods Rock (West)', 'Skull Woods Forest'), #glove
    ('Skull Woods Rock (East)', 'Skull Woods Portal Entry'), #glove
    ('Skull Woods Forgotten Bush (West)', 'Skull Woods Forgotten Path (Northeast)'), #pearl
    ('Skull Woods Forgotten Bush (East)', 'Skull Woods Forgotten Path (Southwest)'), #pearl
    ('West Dark Death Mountain Drop', 'West Dark Death Mountain (Bottom)'),
    ('GT Approach', 'GT Stairs'),
    ('GT Leave', 'West Dark Death Mountain (Top)'),
    ('Floating Island Drop', 'East Dark Death Mountain (Top)'),
    ('East Dark Death Mountain Drop', 'East Dark Death Mountain (Bottom)'),
    ('East Dark Death Mountain Bushes', 'East Dark Death Mountain (Bushes)'),
    ('Turtle Rock Ledge Drop', 'Turtle Rock Area'),
    ('Bumper Cave Rock (Outer)', 'Bumper Cave Entry'), #glove
    ('Bumper Cave Rock (Inner)', 'Bumper Cave Area'), #glove
    ('Bumper Cave Ledge Drop', 'Bumper Cave Area'),
    ('Bumper Cave Entry Drop', 'Bumper Cave Area'),
    ('Skull Woods Pass Bush Row (West)', 'Skull Woods Pass East Top Area'), #pearl
    ('Skull Woods Pass Bush Row (East)', 'Skull Woods Pass West Area'), #pearl
    ('Skull Woods Pass Bush (North)', 'Skull Woods Pass Portal Area'), #pearl
    ('Skull Woods Pass Bush (South)', 'Skull Woods Pass East Top Area'), #pearl
    ('Skull Woods Pass Rock (North)', 'Skull Woods Pass East Bottom Area'), #mitts
    ('Skull Woods Pass Rock (South)', 'Skull Woods Pass Portal Area'), #mitts
    ('Dark Graveyard Bush (South)', 'Dark Graveyard North'), #pearl
    ('Dark Graveyard Bush (North)', 'Dark Graveyard Area'), #pearl
    ('Qirn Jump Water Drop', 'Qirn Jump Water'), #flippers
    ('Qirn Jump East Water Drop', 'Qirn Jump Water'), #flippers
    ('Qirn Jump Pier', 'Qirn Jump East Bank'),
    ('Dark Witch Water Drop', 'Dark Witch Water'), #flippers
    ('Dark Witch Northeast Water Drop', 'Dark Witch Water'), #flippers
    ('Dark Witch Rock (North)', 'Dark Witch Area'), #glove
    ('Dark Witch Rock (South)', 'Dark Witch Northeast'), #glove
    ('Catfish Approach Water Drop', 'Catfish Approach Water'), #flippers
    ('Catfish Approach Rocks (West)', 'Catfish Approach Ledge'), #mitts/boots
    ('Catfish Approach Rocks (East)', 'Catfish Approach Area'), #mitts/boots
    ('Catfish Approach Bottom Ledge Drop', 'Catfish Approach Ledge'),
    ('Catfish Approach Ledge Drop', 'Catfish Approach Area'),
    ('Bush Yard Pegs (Outer)', 'Village of Outcasts Bush Yard'), #hammer
    ('Bush Yard Pegs (Inner)', 'Village of Outcasts'), #hammer
    ('Shield Shop Fence Drop (Outer)', 'Shield Shop Fence'),
    ('Shield Shop Fence Drop (Inner)', 'Shield Shop Area'),
    ('Pyramid Exit Ledge Drop', 'Pyramid Area'),
    ('Broken Bridge Hammer Rock (South)', 'Broken Bridge Northeast'), #hammer/glove
    ('Broken Bridge Hammer Rock (North)', 'Broken Bridge Area'), #hammer/glove
    ('Broken Bridge Hookshot Gap', 'Broken Bridge West'), #hookshot
    ('Broken Bridge Water Drop', 'Broken Bridge Water'), #flippers
    ('Broken Bridge Northeast Water Drop', 'Broken Bridge Water'), #flippers
    ('Broken Bridge West Water Drop', 'Broken Bridge Water'), #flippers
    ('Peg Area Rocks (West)', 'Hammer Pegs Area'), #mitts
    ('Peg Area Rocks (East)', 'Hammer Pegs Entry'), #mitts
    ('Dig Game To Ledge Drop', 'Dig Game Ledge'), #mitts
    ('Dig Game Ledge Drop', 'Dig Game Area'),
    ('Frog Ledge Drop', 'Archery Game Area'),
    ('Frog Rock (Inner)', 'Frog Area'), #mitts
    ('Frog Rock (Outer)', 'Frog Prison'), #mitts
    ('Archery Game Rock (North)', 'Archery Game Area'), #mitts
    ('Archery Game Rock (South)', 'Frog Area'), #mitts
    ('Hammer Bridge Pegs (North)', 'Hammer Bridge South Area'), #hammer
    ('Hammer Bridge Pegs (South)', 'Hammer Bridge North Area'), #hammer
    ('Hammer Bridge Water Drop', 'Hammer Bridge Water'), #flippers
    ('Hammer Bridge Pier', 'Hammer Bridge North Area'),
    ('Mire Teleporter Ledge Drop', 'Mire Area'),
    ('Stumpy Approach Bush (North)', 'Stumpy Approach Area'), #pearl
    ('Stumpy Approach Bush (South)', 'Stumpy Approach Bush Entry'), #pearl
    ('Dark C Whirlpool Water Entry', 'Dark C Whirlpool Water'), #flippers
    ('Dark C Whirlpool Landing', 'Dark C Whirlpool Area'),
    ('Dark C Whirlpool Rock (Bottom)', 'Dark C Whirlpool Outer Area'), #glove
    ('Dark C Whirlpool Rock (Top)', 'Dark C Whirlpool Area'), #glove
    ('Dark C Whirlpool Pegs (Outer)', 'Dark C Whirlpool Portal Area'), #hammer
    ('Dark C Whirlpool Pegs (Inner)', 'Dark C Whirlpool Area'), #hammer
    ('Hype Cave Water Entry', 'Hype Cave Water'), #flippers
    ('Hype Cave Landing', 'Hype Cave Area'),
    ('Ice Lake Water Drop', 'Ice Lake Water'), #flippers
    ('Ice Lake Northeast Water Drop', 'Ice Lake Water'), #flippers
    ('Ice Lake Southwest Water Drop', 'Ice Lake Water'), #flippers
    ('Ice Lake Southeast Water Drop', 'Ice Lake Water'), #flippers
    ('Ice Lake Iceberg Water Entry', 'Ice Lake Water'), #flippers
    ('Ice Lake Northeast Pier', 'Ice Lake Northeast Bank'),
    ('Shopping Mall Water Drop', 'Shopping Mall Water'), #flippers
    ('Shopping Mall Pier', 'Shopping Mall Area'),
    ('Bomber Corner Water Drop', 'Bomber Corner Water'), #flippers
    ('Bomber Corner Waterfall Water Drop', 'Bomber Corner Water'), #flippers
    ('Bomber Corner Pier', 'Bomber Corner Area'),

    # OWG In-Bounds Connections
    ('Ice Lake Northeast Pier Hop', 'Ice Lake Northeast Bank'),
    ('Ice Lake Iceberg Bomb Jump', 'Ice Lake Iceberg'),

    # OWG Connections
    ('Lake Hylia Island FAWT Ledge Drop', 'Lake Hylia Island'),
    ('Stone Bridge EC Cliff Water Drop', 'Stone Bridge Water'), #fake flipper
    ('C Whirlpool Portal Cliff Ledge Drop', 'C Whirlpool Portal Area'),
    ('Checkerboard Cliff Ledge Drop', 'Desert Checkerboard Ledge'),
    ('Cave 45 Cliff Ledge Drop', 'Cave 45 Ledge'),

    ('Ice Lake Iceberg FAWT Ledge Drop', 'Ice Lake Iceberg'),
    ('Hammer Bridge EC Cliff Water Drop', 'Hammer Bridge Water'), #fake flipper
    ('Dark C Whirlpool Portal Cliff Ledge Drop', 'Dark C Whirlpool Portal Area'),
    ('Mire Cliff Ledge Drop', 'Mire Area'),
    ('Stumpy Approach Cliff Ledge Drop', 'Stumpy Approach Area')
]

open_mandatory_connections = [
    ('Sanctuary S&Q', 'Sanctuary'),
    ('Old Man S&Q', 'Old Man House'),
    ('Other World S&Q', 'Pyramid Area'),

    # flute
    ('Flute Spot 1', 'West Death Mountain (Bottom)'),
    ('Flute Spot 2', 'Potion Shop Area'),
    ('Flute Spot 3', 'Kakariko Village'),
    ('Flute Spot 4', 'Links House Area'),
    ('Flute Spot 5', 'Eastern Nook Area'),
    ('Flute Spot 6', 'Desert Teleporter Ledge'),
    ('Flute Spot 7', 'Dam Area'),
    ('Flute Spot 8', 'Octoballoon Area'),

    # portals
    ('West Death Mountain Teleporter', 'West Dark Death Mountain (Bottom)'),
    ('East Death Mountain Teleporter', 'East Dark Death Mountain (Bottom)'),
    ('TR Pegs Teleporter', 'Turtle Rock Ledge'),
    ('Kakariko Teleporter', 'Skull Woods Pass Portal Area'),
    ('Castle Gate Teleporter', 'Pyramid Area'),
    ('Castle Gate Teleporter (Inner)', 'Pyramid Area'),
    ('East Hyrule Teleporter', 'Darkness Nook Area'),
    ('South Hyrule Teleporter', 'Dark C Whirlpool Portal Area'),
    ('Desert Teleporter', 'Mire Teleporter Ledge'),
    ('Lake Hylia Teleporter', 'Ice Palace Area'),

    # OWG connections
    ('Mirror To Bombos Tablet Ledge', 'Bombos Tablet Ledge')
]

inverted_mandatory_connections = [
    ('Sanctuary S&Q', 'Dark Sanctuary Hint'),
    ('Old Man S&Q', 'West Dark Death Mountain (Bottom)'),
    ('Other World S&Q', 'Hyrule Castle Ledge'),

    # flute
    ('Flute Spot 1', 'West Dark Death Mountain (Bottom)'),
    ('Flute Spot 2', 'Dark Witch Area'),
    ('Flute Spot 3', 'Village of Outcasts'),
    ('Flute Spot 4', 'Big Bomb Shop Area'),
    ('Flute Spot 5', 'Darkness Nook Area'),
    ('Flute Spot 6', 'Mire Teleporter Ledge'),
    ('Flute Spot 7', 'Swamp Area'),
    ('Flute Spot 8', 'Bomber Corner Area'),

    # modified terrain
    ('Spectacle Rock Approach', 'Spectacle Rock Ledge'),
    ('Spectacle Rock Leave', 'West Death Mountain (Top)'),
    ('Floating Island Bridge (West)', 'East Death Mountain (Top East)'),
    ('Floating Island Bridge (East)', 'Death Mountain Floating Island'),
    ('Graveyard Ladder (Top)', 'Graveyard Area'),
    ('Graveyard Ladder (Bottom)', 'Graveyard Ledge'),
    ('EDM To Mimic Ledge Drop', 'Mimic Cave Ledge'),
    ('Mimic Ledge Drop', 'East Death Mountain (Bottom)'),
    ('Checkerboard Ledge Approach', 'Desert Checkerboard Ledge'),
    ('Checkerboard Ledge Leave', 'Desert Area'),
    ('Cave 45 Approach', 'Cave 45 Ledge'),
    ('Cave 45 Leave', 'Flute Boy Approach Area'),
    ('Lake Hylia Island Pier', 'Lake Hylia Island'),
    ('Desert Pass Ladder (North)', 'Desert Pass Area'),
    ('Desert Pass Ladder (South)', 'Desert Pass Ledge'),
    ('Dark Death Mountain Ladder (Top)', 'West Dark Death Mountain (Bottom)'),
    ('Dark Death Mountain Ladder (Bottom)', 'West Dark Death Mountain (Top)'),
    ('Turtle Rock Tail Ledge Drop', 'Turtle Rock Ledge'),
    ('Ice Palace Approach', 'Ice Palace Area'),
    ('Ice Palace Leave', 'Ice Lake Iceberg'),

    # portals
    ('Dark Death Mountain Teleporter (West)', 'West Death Mountain (Bottom)'),
    ('East Dark Death Mountain Teleporter', 'East Death Mountain (Bottom)'),
    ('Turtle Rock Teleporter', 'Death Mountain TR Pegs Ledge'),
    ('West Dark World Teleporter', 'Lost Woods Pass Portal Area'),
    ('Post Aga Teleporter', 'Hyrule Castle Area'),
    ('East Dark World Teleporter', 'Eastern Nook Area'),
    ('South Dark World Teleporter', 'C Whirlpool Portal Area'),
    ('Mire Teleporter', 'Desert Teleporter Ledge'),
    ('Ice Lake Teleporter', 'Lake Hylia Central Island')
]

# non shuffled overworld
default_connections = [
    ('Lost Woods NW', 'Master Sword Meadow SC'),
    ('Lost Woods SW', 'Lost Woods Pass NW'),
    ('Lost Woods SC', 'Lost Woods Pass NE'),
    ('Lost Woods SE', 'Kakariko Fortune NE'),
    ('Lost Woods EN', 'Lumberjack WN'),
    ('Lumberjack SW', 'Mountain Pass NW'),
    ('Mountain Pass SE', 'Kakariko Pond NE'),
    ('Zora Waterfall NE', 'Zoras Domain SW'),
    ('Lost Woods Pass SW', 'Kakariko NW'),
    ('Lost Woods Pass SE', 'Kakariko NC'),
    ('Kakariko Fortune SC', 'Kakariko NE'),
    ('Kakariko Fortune EN', 'Kakariko Pond WN'),
    ('Kakariko Fortune ES', 'Kakariko Pond WS'),
    ('Kakariko Pond SW', 'Forgotten Forest NW'),
    ('Kakariko Pond SE', 'Forgotten Forest NE'),
    ('Kakariko Pond EN', 'Sanctuary WN'),
    ('Kakariko Pond ES', 'Sanctuary WS'),
    ('Forgotten Forest ES', 'Hyrule Castle WN'),
    ('Sanctuary EC', 'Graveyard WC'),
    ('Graveyard EC', 'River Bend WC'),
    ('River Bend SW', 'Wooden Bridge NW'),
    ('River Bend SC', 'Wooden Bridge NC'),
    ('River Bend SE', 'Wooden Bridge NE'),
    ('River Bend EN', 'Potion Shop WN'),
    ('River Bend EC', 'Potion Shop WC'),
    ('River Bend ES', 'Potion Shop WS'),
    ('Potion Shop EN', 'Zora Approach WN'),
    ('Potion Shop EC', 'Zora Approach WC'),
    ('Zora Approach NE', 'Zora Waterfall SE'),
    ('Kakariko SE', 'Kakariko Suburb NE'),
    ('Kakariko ES', 'Blacksmith WS'),
    ('Hyrule Castle SW', 'Central Bonk Rocks NW'),
    ('Hyrule Castle SE', 'Links House NE'),
    ('Hyrule Castle ES', 'Sand Dunes WN'),
    ('Wooden Bridge SW', 'Sand Dunes NW'),
    ('Sand Dunes SC', 'Stone Bridge NC'),
    ('Eastern Palace SW', 'Tree Line NW'),
    ('Eastern Palace SE', 'Eastern Nook NE'),
    ('Maze Race ES', 'Kakariko Suburb WS'),
    ('Kakariko Suburb ES', 'Flute Boy WS'),
    ('Flute Boy SW', 'Flute Boy Pass NW'),
    ('Flute Boy SC', 'Flute Boy Pass NC'),
    ('Flute Boy Pass EC', 'C Whirlpool WC'),
    ('C Whirlpool NW', 'Central Bonk Rocks SW'),
    ('C Whirlpool SC', 'Dam NC'),
    ('C Whirlpool EN', 'Statues WN'),
    ('C Whirlpool EC', 'Statues WC'),
    ('C Whirlpool ES', 'Statues WS'),
    ('Central Bonk Rocks EN', 'Links House WN'),
    ('Central Bonk Rocks EC', 'Links House WC'),
    ('Central Bonk Rocks ES', 'Links House WS'),
    ('Links House SC', 'Statues NC'),
    ('Links House ES', 'Stone Bridge WS'),
    ('Stone Bridge SC', 'Lake Hylia NW'),
    ('Stone Bridge EN', 'Tree Line WN'),
    ('Stone Bridge EC', 'Tree Line WC'),
    ('Stone Bridge WC', 'Hobo EC'),
    ('Tree Line SC', 'Lake Hylia NC'),
    ('Tree Line SE', 'Lake Hylia NE'),
    ('Desert EC', 'Desert Pass WC'),
    ('Desert ES', 'Desert Pass WS'),
    ('Desert Pass EC', 'Dam WC'),
    ('Desert Pass ES', 'Dam WS'),
    ('Dam EC', 'South Pass WC'),
    ('Statues SC', 'South Pass NC'),
    ('South Pass ES', 'Lake Hylia WS'),
    ('Lake Hylia EC', 'Octoballoon WC'),
    ('Lake Hylia ES', 'Octoballoon WS'),
    ('Octoballoon NW', 'Ice Cave SW'),
    ('Octoballoon NE', 'Ice Cave SE'),
    ('West Death Mountain EN', 'East Death Mountain WN'),
    ('West Death Mountain ES', 'East Death Mountain WS'),
    ('East Death Mountain EN', 'Death Mountain TR Pegs WN'),

    ('Skull Woods SW', 'Skull Woods Pass NW'),
    ('Skull Woods SC', 'Skull Woods Pass NE'),
    ('Skull Woods SE', 'Dark Fortune NE'),
    ('Skull Woods EN', 'Dark Lumberjack WN'),
    ('Dark Lumberjack SW', 'Bumper Cave NW'),
    ('Bumper Cave SE', 'Outcast Pond NE'),
    ('Skull Woods Pass SW', 'Village of Outcasts NW'),
    ('Skull Woods Pass SE', 'Village of Outcasts NC'),
    ('Dark Fortune SC', 'Village of Outcasts NE'),
    ('Dark Fortune EN', 'Outcast Pond WN'),
    ('Dark Fortune ES', 'Outcast Pond WS'),
    ('Outcast Pond SW', 'Shield Shop NW'),
    ('Outcast Pond SE', 'Shield Shop NE'),
    ('Outcast Pond EN', 'Dark Chapel WN'),
    ('Outcast Pond ES', 'Dark Chapel WS'),
    ('Dark Chapel EC', 'Dark Graveyard WC'),
    ('Dark Graveyard EC', 'Qirn Jump WC'),
    ('Qirn Jump SW', 'Broken Bridge NW'),
    ('Qirn Jump SC', 'Broken Bridge NC'),
    ('Qirn Jump SE', 'Broken Bridge NE'),
    ('Qirn Jump EN', 'Dark Witch WN'),
    ('Qirn Jump EC', 'Dark Witch WC'),
    ('Qirn Jump ES', 'Dark Witch WS'),
    ('Dark Witch EN', 'Catfish Approach WN'),
    ('Dark Witch EC', 'Catfish Approach WC'),
    ('Catfish Approach NE', 'Catfish SE'),
    ('Village of Outcasts SE', 'Frog NE'),
    ('Village of Outcasts ES', 'Hammer Pegs WS'),
    ('Pyramid SW', 'Dark Bonk Rocks NW'),
    ('Pyramid SE', 'Big Bomb Shop NE'),
    ('Pyramid ES', 'Dark Dunes WN'),
    ('Broken Bridge SW', 'Dark Dunes NW'),
    ('Dark Dunes SC', 'Hammer Bridge NC'),
    ('Palace of Darkness SW', 'Dark Tree Line NW'),
    ('Palace of Darkness SE', 'Palace of Darkness Nook NE'),
    ('Dig Game EC', 'Frog WC'),
    ('Dig Game ES', 'Frog WS'),
    ('Frog ES', 'Stumpy WS'),
    ('Stumpy SW', 'Stumpy Approach NW'),
    ('Stumpy SC', 'Stumpy Approach NC'),
    ('Stumpy Approach EC', 'Dark C Whirlpool WC'),
    ('Dark C Whirlpool NW', 'Dark Bonk Rocks SW'),
    ('Dark C Whirlpool SC', 'Swamp NC'),
    ('Dark C Whirlpool EN', 'Hype Cave WN'),
    ('Dark C Whirlpool EC', 'Hype Cave WC'),
    ('Dark C Whirlpool ES', 'Hype Cave WS'),
    ('Dark Bonk Rocks EN', 'Big Bomb Shop WN'),
    ('Dark Bonk Rocks EC', 'Big Bomb Shop WC'),
    ('Dark Bonk Rocks ES', 'Big Bomb Shop WS'),
    ('Big Bomb Shop SC', 'Hype Cave NC'),
    ('Big Bomb Shop ES', 'Hammer Bridge WS'),
    ('Hammer Bridge SC', 'Ice Lake NW'),
    ('Hammer Bridge EN', 'Dark Tree Line WN'),
    ('Hammer Bridge EC', 'Dark Tree Line WC'),
    ('Dark Tree Line SC', 'Ice Lake NC'),
    ('Dark Tree Line SE', 'Ice Lake NE'),
    ('Swamp Nook EC', 'Swamp WC'),
    ('Swamp Nook ES', 'Swamp WS'),
    ('Swamp EC', 'Dark South Pass WC'),
    ('Hype Cave SC', 'Dark South Pass NC'),
    ('Dark South Pass ES', 'Ice Lake WS'),
    ('Ice Lake EC', 'Bomber Corner WC'),
    ('Ice Lake ES', 'Bomber Corner WS'),
    ('Bomber Corner NW', 'Shopping Mall SW'),
    ('Bomber Corner NE', 'Shopping Mall SE'),
    ('West Dark Death Mountain EN', 'East Dark Death Mountain WN'),
    ('West Dark Death Mountain ES', 'East Dark Death Mountain WS'),
    ('East Dark Death Mountain EN', 'Turtle Rock WN'),

    # whirlpool connections
    ('C Whirlpool', 'River Bend Whirlpool'),
    ('Lake Hylia Whirlpool', 'Zora Whirlpool'),
    ('Kakariko Pond Whirlpool', 'Octoballoon Whirlpool'),
    ('Qirn Jump Whirlpool', 'Bomber Corner Whirlpool')
]

mirror_connections = {
    'Skull Woods Forest': ['Lost Woods East Area'],
    'Skull Woods Portal Entry': ['Lost Woods West Area'],
    'Skull Woods Forest (West)': ['Lost Woods West Area'],
    'Skull Woods Forgotten Path (Southwest)': ['Lost Woods West Area'],
    'Skull Woods Forgotten Path (Northeast)': ['Lost Woods East Area', 'Lost Woods West Area'],

    'Dark Lumberjack Area': ['Lumberjack Area'],

    'West Dark Death Mountain (Top)': ['West Death Mountain (Top)'],
    'West Dark Death Mountain (Bottom)': ['Spectacle Rock Ledge'],

    'Dark Death Mountain Floating Island': ['Death Mountain Floating Island'],
    'East Dark Death Mountain (Top)': ['East Death Mountain (Top West)', 'East Death Mountain (Top East)'],
    'Dark Death Mountain Ledge': ['Spiral Cave Ledge', 'Mimic Cave Ledge'],
    'Dark Death Mountain Isolated Ledge': ['Fairy Ascension Ledge'],
    'East Dark Death Mountain (Bushes)': ['Fairy Ascension Plateau'],
    'East Dark Death Mountain (Bottom Left)': ['East Death Mountain (Bottom Left)'],

    'Turtle Rock Area': ['Death Mountain TR Pegs Area'],

    'Bumper Cave Area': ['Mountain Pass Area'],
    'Bumper Cave Entry': ['Mountain Pass Entry'],
    'Bumper Cave Ledge': ['Mountain Pass Ledge'],

    'Catfish Area': ['Zora Waterfall Area'],

    'Skull Woods Pass West Area': ['Lost Woods Pass West Area'],
    'Skull Woods Pass East Top Area': ['Lost Woods Pass East Top Area'],
    'Skull Woods Pass Portal Area': ['Lost Woods Pass Portal Area'],
    'Skull Woods Pass East Bottom Area': ['Lost Woods Pass East Bottom Area'],

    'Dark Fortune Area': ['Kakariko Fortune Area'],

    'Outcast Pond Area': ['Kakariko Pond Area'],

    'Dark Chapel Area': ['Sanctuary Area', 'Bonk Rock Ledge'],

    'Dark Graveyard Area': ['Graveyard Area'],
    'Dark Graveyard North': ['Graveyard Ledge', 'Kings Grave Area'],

    'Qirn Jump Area': ['River Bend Area'],
    'Qirn Jump East Bank': ['River Bend East Bank'],

    'Dark Witch Area': ['Potion Shop Area'],
    'Dark Witch Northeast': ['Potion Shop Northeast'],

    'Catfish Approach Area': ['Zora Approach Area'],
    'Catfish Approach Ledge': ['Zora Approach Ledge'],

    'Village of Outcasts': ['Kakariko Village'],
    'Village of Outcasts Bush Yard': ['Kakariko Village'],

    'Shield Shop Area': ['Forgotten Forest Area'],
    'Shield Shop Fence': ['Forgotten Forest Area'],

    'Pyramid Area': ['Hyrule Castle Ledge', 'Hyrule Castle Courtyard', 'Hyrule Castle Area', 'Hyrule Castle East Entry'],
    'Pyramid Exit Ledge': ['Hyrule Castle Courtyard'],
    'Pyramid Pass': ['Hyrule Castle Area'],

    'Broken Bridge Area': ['Wooden Bridge Area'],
    'Broken Bridge Northeast': ['Wooden Bridge Area'],
    'Broken Bridge West': ['Wooden Bridge Area'],

    'Palace of Darkness Area': ['Eastern Palace Area'],

    'Hammer Pegs Area': ['Blacksmith Area', 'Blacksmith Ledge'],
    'Hammer Pegs Entry': ['Blacksmith Area'],

    'Dark Dunes Area': ['Sand Dunes Area'],

    'Dig Game Area': ['Maze Race Ledge'],
    'Dig Game Ledge': ['Maze Race Ledge'],

    'Frog Area': ['Kakariko Suburb Area'],
    'Archery Game Area': ['Kakariko Suburb Area'],

    'Stumpy Area': ['Flute Boy Area'],
    'Stumpy Pass': ['Flute Boy Pass'],

    'Dark Bonk Rocks Area': ['Central Bonk Rocks Area'],

    'Big Bomb Shop Area': ['Links House Area'],

    'Hammer Bridge North Area': ['Stone Bridge North Area'],
    'Hammer Bridge South Area': ['Stone Bridge South Area'],
    'Hammer Bridge Water': ['Stone Bridge Water'],

    'Dark Tree Line Area': ['Tree Line Area'],

    'Darkness Nook Area': ['Eastern Nook Area'],

    'Mire Area': ['Desert Area', 'Desert Ledge', 'Desert Checkerboard Ledge', 'Desert Stairs', 'Desert Ledge Keep'],

    'Stumpy Approach Area': ['Cave 45 Ledge'],
    'Stumpy Approach Bush Entry': ['Flute Boy Bush Entry'],

    'Dark C Whirlpool Area': ['C Whirlpool Area'],
    'Dark C Whirlpool Outer Area': ['C Whirlpool Outer Area'],

    'Hype Cave Area': ['Statues Area'],

    'Ice Lake Northwest Bank': ['Lake Hylia Northwest Bank'],
    'Ice Lake Northeast Bank': ['Lake Hylia Northeast Bank'],
    'Ice Lake Southwest Ledge': ['Lake Hylia South Shore'],
    'Ice Lake Southeast Ledge': ['Lake Hylia South Shore'],
    'Ice Lake Water': ['Lake Hylia Island'],
    'Ice Palace Area': ['Lake Hylia Central Island'],
    'Ice Lake Iceberg': ['Lake Hylia Water', 'Lake Hylia Water D'], #first one needs flippers

    'Shopping Mall Area': ['Ice Cave Area'],

    'Swamp Nook Area': ['Desert Pass Area', 'Desert Pass Ledge'],

    'Swamp Area': ['Dam Area'],

    'Dark South Pass Area': ['South Pass Area'],

    'Bomber Corner Area': ['Octoballoon Area'],


    'Lost Woods West Area': ['Skull Woods Forest (West)', 'Skull Woods Forgotten Path (Southwest)', 'Skull Woods Portal Entry'],
    #'Lost Woods West Area': ['Skull Woods Forgotten Path (Northeast)'], # technically yes, but we dont need it
    'Lost Woods East Area': ['Skull Woods Forgotten Path (Northeast)', 'Skull Woods Forest'],

    'Lumberjack Area': ['Dark Lumberjack Area'],

    'West Death Mountain (Top)': ['West Dark Death Mountain (Top)'],
    'Spectacle Rock Ledge': ['West Dark Death Mountain (Bottom)'],
    'West Death Mountain (Bottom)': ['West Dark Death Mountain (Bottom)'],

    'East Death Mountain (Top West)': ['East Dark Death Mountain (Top)'],
    'East Death Mountain (Top East)': ['East Dark Death Mountain (Top)'],
    'Spiral Cave Ledge': ['Dark Death Mountain Ledge'],
    'Mimic Cave Ledge': ['Dark Death Mountain Ledge'],
    'Fairy Ascension Ledge': ['Dark Death Mountain Isolated Ledge'],
    'Fairy Ascension Plateau': ['East Dark Death Mountain (Bottom)'],
    'East Death Mountain (Bottom Left)': ['East Dark Death Mountain (Bottom Left)'],
    'East Death Mountain (Bottom)': ['East Dark Death Mountain (Bottom)'],
    'Death Mountain Floating Island': ['Dark Death Mountain Floating Island'],

    'Death Mountain TR Pegs Area': ['Turtle Rock Area'],
    'Death Mountain TR Pegs Ledge': ['Turtle Rock Ledge'],

    'Mountain Pass Area': ['Bumper Cave Area'],
    'Mountain Pass Entry': ['Bumper Cave Entry'],
    'Mountain Pass Ledge': ['Bumper Cave Ledge'],

    'Zora Waterfall Area': ['Catfish Area'],

    'Lost Woods Pass West Area': ['Skull Woods Pass West Area'],
    'Lost Woods Pass East Top Area': ['Skull Woods Pass East Top Area'],
    'Lost Woods Pass Portal Area': ['Skull Woods Pass Portal Area'],
    'Lost Woods Pass East Bottom Area': ['Skull Woods Pass East Bottom Area'],

    'Kakariko Fortune Area': ['Dark Fortune Area'],

    'Kakariko Pond Area': ['Outcast Pond Area'],

    'Sanctuary Area': ['Dark Chapel Area'],
    'Bonk Rock Ledge': ['Dark Chapel Area'],

    'Graveyard Area': ['Dark Graveyard Area'],
    'Graveyard Ledge': ['Dark Graveyard Area'],
    'Kings Grave Area': ['Dark Graveyard Area'],

    'River Bend Area': ['Qirn Jump Area'],
    'River Bend East Bank': ['Qirn Jump East Bank'],

    'Potion Shop Area': ['Dark Witch Area'],
    'Potion Shop Northeast': ['Dark Witch Northeast'],

    'Zora Approach Area': ['Catfish Approach Area'],
    'Zora Approach Ledge': ['Catfish Approach Ledge'],

    'Kakariko Village': ['Village of Outcasts'],
    'Kakariko Southwest': ['Village of Outcasts'],
    'Kakariko Bush Yard': ['Village of Outcasts Bush Yard'],

    'Forgotten Forest Area': ['Shield Shop Area'],

    'Hyrule Castle Area': ['Pyramid Area', 'Pyramid Pass'],
    'Hyrule Castle Southwest': ['Pyramid Pass'],
    'Hyrule Castle Courtyard': ['Pyramid Area'],
    'Hyrule Castle Courtyard Northeast': ['Pyramid Area'],
    'Hyrule Castle Ledge': ['Pyramid Area'],
    'Hyrule Castle East Entry': ['Pyramid Area'],

    'Wooden Bridge Area': ['Broken Bridge Area', 'Broken Bridge West'],
    'Wooden Bridge Northeast': ['Broken Bridge Northeast'],

    'Eastern Palace Area': ['Palace of Darkness Area'],

    'Blacksmith Area': ['Hammer Pegs Area', 'Hammer Pegs Entry'],

    'Sand Dunes Area': ['Dark Dunes Area'],

    'Maze Race Area': ['Dig Game Area'],
    'Maze Race Ledge': ['Dig Game Ledge'],

    'Kakariko Suburb Area': ['Frog Area', 'Frog Prison', 'Archery Game Area'],

    'Flute Boy Area': ['Stumpy Area'],
    'Flute Boy Pass': ['Stumpy Pass'],

    'Central Bonk Rocks Area': ['Dark Bonk Rocks Area'],

    'Links House Area': ['Big Bomb Shop Area'],

    'Stone Bridge North Area': ['Hammer Bridge North Area'],
    'Stone Bridge South Area': ['Hammer Bridge South Area'],
    'Stone Bridge Water': ['Hammer Bridge Water'],

    'Tree Line Area': ['Dark Tree Line Area'],

    'Eastern Nook Area': ['Darkness Nook Area'],

    'Desert Area': ['Mire Area'],
    'Desert Ledge': ['Mire Area'],
    'Desert Ledge Keep': ['Mire Area'],
    'Desert Checkerboard Ledge': ['Mire Area'],
    'Desert Stairs': ['Mire Area'],

    'Flute Boy Approach Area': ['Stumpy Approach Area'],
    'Cave 45 Ledge': ['Stumpy Approach Area'],
    'Flute Boy Bush Entry': ['Stumpy Approach Bush Entry'],

    'C Whirlpool Area': ['Dark C Whirlpool Area'],
    'C Whirlpool Outer Area': ['Dark C Whirlpool Outer Area'],

    'Statues Area': ['Hype Cave Area'],

    'Lake Hylia Northwest Bank': ['Ice Lake Northwest Bank'],
    'Lake Hylia South Shore': ['Ice Lake Southwest Ledge', 'Ice Lake Southeast Ledge'],
    'Lake Hylia Northeast Bank': ['Ice Lake Northeast Bank'],
    'Lake Hylia Central Island': ['Ice Palace Area'],
    'Lake Hylia Water D': ['Ice Lake Iceberg'],

    'Ice Cave Area': ['Shopping Mall Area'],

    'Desert Pass Area': ['Swamp Nook Area'],
    'Desert Pass Southeast': ['Swamp Nook Area'],
    'Desert Pass Ledge': ['Swamp Nook Area'],

    'Dam Area': ['Swamp Area'],

    'South Pass Area': ['Dark South Pass Area'],

    'Octoballoon Area': ['Bomber Corner Area']
}

OWTileRegions = bidict({
    'Lost Woods West Area': 0x00,
    'Lost Woods East Area': 0x00,

    'Lumberjack Area': 0x02,

    'West Death Mountain (Top)': 0x03,
    'Spectacle Rock Ledge': 0x03,
    'West Death Mountain (Bottom)': 0x03,

    'East Death Mountain (Top West)': 0x05,
    'East Death Mountain (Top East)': 0x05,
    'Spiral Cave Ledge': 0x05,
    'Mimic Cave Ledge': 0x05,
    'Fairy Ascension Ledge': 0x05,
    'Fairy Ascension Plateau': 0x05,
    'East Death Mountain (Bottom Left)': 0x05,
    'East Death Mountain (Bottom)': 0x05,
    'Death Mountain Floating Island': 0x05,

    'Death Mountain TR Pegs Area': 0x07,
    'Death Mountain TR Pegs Ledge': 0x07,

    'Mountain Pass Area': 0x0a,
    'Mountain Pass Entry': 0x0a,
    'Mountain Pass Ledge': 0x0a,

    'Zora Waterfall Area': 0x0f,
    'Zora Waterfall Water': 0x0f,
    'Zora Waterfall Entryway': 0x0f,

    'Lost Woods Pass West Area': 0x10,
    'Lost Woods Pass East Top Area': 0x10,
    'Lost Woods Pass Portal Area': 0x10,
    'Lost Woods Pass East Bottom Area': 0x10,

    'Kakariko Fortune Area': 0x11,

    'Kakariko Pond Area': 0x12,

    'Sanctuary Area': 0x13,
    'Bonk Rock Ledge': 0x13,

    'Graveyard Area': 0x14,
    'Graveyard Ledge': 0x14,
    'Kings Grave Area': 0x14,

    'River Bend Area': 0x15,
    'River Bend East Bank': 0x15,
    'River Bend Water': 0x15,

    'Potion Shop Area': 0x16,
    'Potion Shop Northeast': 0x16,
    'Potion Shop Water': 0x16,

    'Zora Approach Area': 0x17,
    'Zora Approach Ledge': 0x17,
    'Zora Approach Water': 0x17,

    'Kakariko Village': 0x18,
    'Kakariko Southwest': 0x18,
    'Kakariko Bush Yard': 0x18,

    'Forgotten Forest Area': 0x1a,

    'Hyrule Castle Area': 0x1b,
    'Hyrule Castle Southwest': 0x1b,
    'Hyrule Castle Courtyard': 0x1b,
    'Hyrule Castle Courtyard Northeast': 0x1b,
    'Hyrule Castle Ledge': 0x1b,
    'Hyrule Castle East Entry': 0x1b,
    'Hyrule Castle Water': 0x1b,

    'Wooden Bridge Area': 0x1d,
    'Wooden Bridge Northeast': 0x1d,
    'Wooden Bridge Water': 0x1d,

    'Eastern Palace Area': 0x1e,

    'Blacksmith Area': 0x22,
    'Blacksmith Ledge': 0x22,

    'Sand Dunes Area': 0x25,

    'Maze Race Area': 0x28,
    'Maze Race Ledge': 0x28,
    'Maze Race Prize': 0x28,

    'Kakariko Suburb Area': 0x29,

    'Flute Boy Area': 0x2a,
    'Flute Boy Pass': 0x2a,

    'Central Bonk Rocks Area': 0x2b,

    'Links House Area': 0x2c,

    'Stone Bridge North Area': 0x2d,
    'Stone Bridge South Area': 0x2d,
    'Stone Bridge Water': 0x2d,

    'Tree Line Area': 0x2e,
    'Tree Line Water': 0x2e,

    'Eastern Nook Area': 0x2f,

    'Desert Area': 0x30,
    'Desert Ledge': 0x30,
    'Desert Ledge Keep': 0x30,
    'Desert Checkerboard Ledge': 0x30,
    'Desert Stairs': 0x30,
    'Desert Mouth': 0x30,
    'Desert Teleporter Ledge': 0x30,
    'Bombos Tablet Ledge': 0x30,

    'Flute Boy Approach Area': 0x32,
    'Flute Boy Bush Entry': 0x32,
    'Cave 45 Ledge': 0x32,

    'C Whirlpool Area': 0x33,
    'C Whirlpool Portal Area': 0x33,
    'C Whirlpool Water': 0x33,
    'C Whirlpool Outer Area': 0x33,

    'Statues Area': 0x34,
    'Statues Water': 0x34,

    'Lake Hylia Northwest Bank': 0x35,
    'Lake Hylia Northeast Bank': 0x35,
    'Lake Hylia South Shore': 0x35,
    'Lake Hylia Central Island': 0x35,
    'Lake Hylia Island': 0x35,
    'Lake Hylia Water': 0x35,
    'Lake Hylia Water D': 0x35,

    'Ice Cave Area': 0x37,
    'Ice Cave Water': 0x37,

    'Desert Pass Area': 0x3a,
    'Desert Pass Southeast': 0x3a,
    'Desert Pass Ledge': 0x3a,

    'Dam Area': 0x3b,

    'South Pass Area': 0x3c,

    'Octoballoon Area': 0x3f,
    'Octoballoon Water': 0x3f,
    'Octoballoon Water Ledge': 0x3f,

    'Skull Woods Forest': 0x40,
    'Skull Woods Portal Entry': 0x40,
    'Skull Woods Forest (West)': 0x40,
    'Skull Woods Forgotten Path (Southwest)': 0x40,
    'Skull Woods Forgotten Path (Northeast)': 0x40,

    'Dark Lumberjack Area': 0x42,

    'West Dark Death Mountain (Top)': 0x43,
    'GT Stairs': 0x43,
    'West Dark Death Mountain (Bottom)': 0x43,

    'East Dark Death Mountain (Top)': 0x45,
    'East Dark Death Mountain (Bottom Left)': 0x45,
    'East Dark Death Mountain (Bottom)': 0x45,
    'East Dark Death Mountain (Bushes)': 0x45,
    'Dark Death Mountain Ledge': 0x45,
    'Dark Death Mountain Isolated Ledge': 0x45,
    'Dark Death Mountain Floating Island': 0x45,

    'Turtle Rock Area': 0x47,
    'Turtle Rock Ledge': 0x47,

    'Bumper Cave Area': 0x4a,
    'Bumper Cave Entry': 0x4a,
    'Bumper Cave Ledge': 0x4a,

    'Catfish Area': 0x4f,

    'Skull Woods Pass West Area': 0x50,
    'Skull Woods Pass East Top Area': 0x50,
    'Skull Woods Pass Portal Area': 0x50,
    'Skull Woods Pass East Bottom Area': 0x50,

    'Dark Fortune Area': 0x51,

    'Outcast Pond Area': 0x52,

    'Dark Chapel Area': 0x53,

    'Dark Graveyard Area': 0x54,
    'Dark Graveyard North': 0x54,

    'Qirn Jump Area': 0x55,
    'Qirn Jump East Bank': 0x55,
    'Qirn Jump Water': 0x55,

    'Dark Witch Area': 0x56,
    'Dark Witch Northeast': 0x56,
    'Dark Witch Water': 0x56,

    'Catfish Approach Area': 0x57,
    'Catfish Approach Ledge': 0x57,
    'Catfish Approach Water': 0x57,

    'Village of Outcasts': 0x58,
    'Village of Outcasts Bush Yard': 0x58,

    'Shield Shop Area': 0x5a,
    'Shield Shop Fence': 0x5a,

    'Pyramid Area': 0x5b,
    'Pyramid Exit Ledge': 0x5b,
    'Pyramid Pass': 0x5b,
    'Pyramid Water': 0x5b,

    'Broken Bridge Area': 0x5d,
    'Broken Bridge Northeast': 0x5d,
    'Broken Bridge West': 0x5d,
    'Broken Bridge Water': 0x5d,

    'Palace of Darkness Area': 0x5e,

    'Hammer Pegs Area': 0x62,
    'Hammer Pegs Entry': 0x62,

    'Dark Dunes Area': 0x65,

    'Dig Game Area': 0x68,
    'Dig Game Ledge': 0x68,

    'Frog Area': 0x69,
    'Frog Prison': 0x69,
    'Archery Game Area': 0x69,

    'Stumpy Area': 0x6a,
    'Stumpy Pass': 0x6a,

    'Dark Bonk Rocks Area': 0x6b,

    'Big Bomb Shop Area': 0x6c,

    'Hammer Bridge North Area': 0x6d,
    'Hammer Bridge South Area': 0x6d,
    'Hammer Bridge Water': 0x6d,

    'Dark Tree Line Area': 0x6e,
    'Dark Tree Line Water': 0x6e,

    'Darkness Nook Area': 0x6f,

    'Mire Area': 0x70,
    'Mire Teleporter Ledge': 0x70,

    'Stumpy Approach Area': 0x72,
    'Stumpy Approach Bush Entry': 0x72,

    'Dark C Whirlpool Area': 0x73,
    'Dark C Whirlpool Portal Area': 0x73,
    'Dark C Whirlpool Water': 0x73,
    'Dark C Whirlpool Outer Area': 0x73,

    'Hype Cave Area': 0x74,
    'Hype Cave Water': 0x74,

    'Ice Lake Northwest Bank': 0x75,
    'Ice Lake Northeast Bank': 0x75,
    'Ice Lake Southwest Ledge': 0x75,
    'Ice Lake Southeast Ledge': 0x75,
    'Ice Lake Water': 0x75,
    'Ice Lake Iceberg': 0x75,
    'Ice Palace Area': 0x75,

    'Shopping Mall Area': 0x77,
    'Shopping Mall Water': 0x77,

    'Swamp Nook Area': 0x7a,

    'Swamp Area': 0x7b,

    'Dark South Pass Area': 0x7c,

    'Bomber Corner Area': 0x7f,
    'Bomber Corner Water': 0x7f,
    'Bomber Corner Water Ledge': 0x7f,

    'Master Sword Meadow': 0x80,
    'Hobo Bridge': 0x80,

    'Zoras Domain': 0x81
})