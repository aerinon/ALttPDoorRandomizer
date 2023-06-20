from BaseClasses import RegionType, Entrance

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
                    # if region.terrain == Terrain.Water or to_region.terrain == Terrain.Water:
                    if region.name == 'Dark Lake Hylia Water': # TODO: Uncomment line above when Terrain type is modeled
                        exit.access_rule = lambda state: state.has('Flippers', player) and state.has_Pearl(player) and state.has_Mirror(player)
                    else:
                        exit.access_rule = lambda state: state.has_Mirror(player)
                    exit.connect(to_region)
                    region.exits.append(exit)

                    mirror_exits.add(exitname)

def create_dynamic_exits(world, player):
    create_mirror_exits(world, player)
    world.initialize_regions()


mirror_connections = {
    'Skull Woods Forest (West)': ['Light World'],

    'West Dark Death Mountain (Bottom)': ['Spectacle Rock'],
    'Dark Death Mountain (Top)': ['East Death Mountain (Top)'],

    'Dark Death Mountain Floating Island': ['Death Mountain Floating Island'],
    'Dark Death Mountain Ledge': ['Spiral Cave Ledge', 'Mimic Cave Ledge'],
    'Dark Death Mountain Isolated Ledge': ['Fairy Ascension Ledge'],
    'East Dark Death Mountain (Bushes)': ['Fairy Ascension Plateau'],
    'East Dark Death Mountain (Bottom)': ['East Death Mountain (Bottom)'],
    
    'Dark Graveyard North': ['Graveyard Ledge', 'Kings Grave Area'],

    'Bumper Cave Ledge': ['Death Mountain Return Ledge'],
    'Bumper Cave Entrance': ['Death Mountain Entrance'],

    'Northeast Dark World': ['Potion Shop Area'],

    'Dark Grassy Lawn': ['Bush Covered Lawn'],

    'Hammer Peg Area': ['Bat Cave Ledge'],

    'East Dark World': ['Hyrule Castle Ledge', 'Hyrule Castle Courtyard'],

    'Dark Desert': ['Desert Ledge', 'Desert Checkerboard Ledge', 'Desert Palace Stairs', 'Desert Palace Entrance (North) Spot'],

    'South Dark World': ['Maze Race Ledge', 'Cave 45 Ledge', 'Bombos Tablet Ledge'],

    'Dark Lake Hylia Water': ['Lake Hylia Island'],
    'Dark Lake Hylia Central Island': ['Lake Hylia Central Island'],

    'Southeast Dark World': ['Light World'],


    'Light World': ['Skull Woods Forest (West)', 'West Dark World', 'Hammer Peg Area', 'East Dark World', 'South Dark World', 'Dark Desert', 'Southeast Dark World'],

    'West Death Mountain (Top)': ['Dark Death Mountain (Top)'],
    'West Death Mountain (Bottom)': ['West Dark Death Mountain (Bottom)'],

    'East Death Mountain (Top)': ['Dark Death Mountain (Top)'],
    'Death Mountain Floating Island': ['Dark Death Mountain Floating Island'],
    'Spiral Cave Ledge': ['Dark Death Mountain Ledge'],
    'Mimic Cave Ledge': ['Dark Death Mountain Ledge'],
    'Fairy Ascension Ledge': ['Dark Death Mountain Isolated Ledge'],
    'East Death Mountain (Bottom)': ['East Dark Death Mountain (Bottom)'],

    'Death Mountain Return Ledge': ['Bumper Cave Ledge'],
    'Death Mountain Entrance': ['Bumper Cave Entrance'],

    'Northeast Light World': ['Catfish Area'],

    'Graveyard Ledge': ['West Dark World'],
    'Kings Grave Area': ['West Dark World'],

    'Potion Shop Area': ['Northeast Dark World'],

    'Bush Covered Lawn': ['Dark Grassy Lawn'],
    'Bomb Hut Area': ['West Dark World'],

    'Hyrule Castle Secret Entrance Area': ['East Dark World'],

    'Maze Race Ledge': ['South Dark World'],

    'Cave 45 Ledge': ['South Dark World'],

    'Desert Palace Stairs': ['Dark Desert'],
    'Desert Ledge': ['Dark Desert'],
    'Desert Palace Entrance (North) Spot': ['Dark Desert'],
    'Desert Checkerboard Ledge': ['Dark Desert'],

    'Lake Hylia Central Island': ['Dark Lake Hylia Central Island']
}