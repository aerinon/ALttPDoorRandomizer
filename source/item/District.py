from collections import deque

from BaseClasses import CollectionState, RegionType
from Dungeons import dungeon_table


class District(object):

    def __init__(self, name, locations, entrances=None, dungeon=None):
        self.name = name
        self.dungeon = dungeon
        self.locations = locations
        self.entrances = entrances if entrances else []
        self.sphere_one = False

        self.dungeons = set()
        self.access_points = set()


def create_districts(world):
    world.districts = {}
    for p in range(1, world.players + 1):
        create_district_helper(world, p)


def create_district_helper(world, player):
    inverted = world.mode[player] == 'inverted'
    districts = {}
    kak_locations = {'Bottle Merchant', 'Kakariko Tavern', 'Maze Race'}
    nw_lw_locations = {'Mushroom', 'Master Sword Pedestal'}
    central_lw_locations = {'Sunken Treasure', 'Flute Spot'}
    desert_locations = {'Purple Chest', 'Desert Ledge', 'Bombos Tablet'}
    lake_locations = {'Hobo', 'Lake Hylia Island'}
    east_lw_locations = {"Zora's Ledge", 'King Zora'}
    lw_dm_locations = {'Old Man', 'Spectacle Rock', 'Ether Tablet', 'Floating Island'}
    east_dw_locations = {'Pyramid', 'Catfish'}
    south_dw_locations = {'Stumpy', 'Digging Game'}
    voo_north_locations = {'Bumper Cave Ledge'}
    ddm_locations = set()

    kak_entrances = ['Kakariko Well Cave', 'Bat Cave Cave', 'Elder House (East)', 'Elder House (West)',
                     'Two Brothers House (East)', 'Two Brothers House (West)', 'Blinds Hideout', 'Chicken House',
                     'Blacksmiths Hut', 'Sick Kids House', 'Snitch Lady (East)', 'Snitch Lady (West)',
                     'Bush Covered House', 'Tavern (Front)', 'Light World Bomb Hut', 'Kakariko Shop', 'Library',
                     'Kakariko Gamble Game', 'Kakariko Well Drop', 'Bat Cave Drop', 'Tavern North']
    nw_lw_entrances = ['North Fairy Cave', 'Lost Woods Hideout Stump', 'Lumberjack Tree Cave', 'Sanctuary',
                       'Old Man Cave (West)', 'Death Mountain Return Cave (West)', 'Kings Grave', 'Lost Woods Gamble',
                       'Fortune Teller (Light)', 'Bonk Rock Cave', 'Lumberjack House', 'North Fairy Cave Drop',
                       'Lost Woods Hideout Drop', 'Lumberjack Tree Tree', 'Sanctuary Grave', 'Graveyard Cave']
    central_lw_entrances = ['Links House', 'Hyrule Castle Entrance (South)', 'Hyrule Castle Entrance (West)',
                            'Hyrule Castle Entrance (East)', 'Agahnims Tower', 'Hyrule Castle Secret Entrance Stairs',
                            'Dam', 'Bonk Fairy (Light)', 'Light Hype Fairy', 'Hyrule Castle Secret Entrance Drop',
                            'Cave 45']
    desert_entrances = ['Desert Palace Entrance (South)', 'Desert Palace Entrance (West)',
                        'Desert Palace Entrance (North)', 'Desert Palace Entrance (East)', 'Desert Fairy',
                        'Aginahs Cave', '50 Rupee Cave', 'Checkerboard Cave']
    lake_entrances = ['Capacity Upgrade', 'Mini Moldorm Cave', 'Good Bee Cave', '20 Rupee Cave', 'Ice Rod Cave',
                      'Lake Hylia Shop', 'Lake Hylia Fortune Teller']
    east_lw_entrances = ['Eastern Palace', 'Waterfall of Wishing', 'Lake Hylia Fairy', 'Sahasrahlas Hut',
                         'Long Fairy Cave', 'Potion Shop']
    lw_dm_entrances = ['Tower of Hera', 'Old Man Cave (East)', 'Old Man House (Bottom)', 'Old Man House (Top)',
                       'Death Mountain Return Cave (East)', 'Spectacle Rock Cave Peak', 'Spectacle Rock Cave',
                       'Spectacle Rock Cave (Bottom)', 'Paradox Cave (Bottom)', 'Paradox Cave (Middle)',
                       'Paradox Cave (Top)', 'Fairy Ascension Cave (Bottom)', 'Fairy Ascension Cave (Top)',
                       'Spiral Cave', 'Spiral Cave (Bottom)', 'Hookshot Fairy', 'Mimic Cave']
    east_dw_entrances = ['Palace of Darkness', 'Pyramid Entrance', 'Pyramid Fairy', 'East Dark World Hint',
                         'Palace of Darkness Hint', 'Dark Lake Hylia Fairy', 'Dark Potion Shop', 'Pyramid Hole']
    south_dw_entrances = ['Ice Palace', 'Swamp Palace', 'Dark Lake Hylia Ledge Fairy',
                          'Dark Lake Hylia Ledge Spike Cave', 'Dark Lake Hylia Ledge Hint', 'Hype Cave',
                          'Bonk Fairy (Dark)', 'Archery Game', 'Big Bomb Shop', 'Dark Lake Hylia Shop', ]
    voo_north_entrances = ['Thieves Town', 'Skull Woods First Section Door', 'Skull Woods Second Section Door (East)',
                           'Skull Woods Second Section Door (West)', 'Skull Woods Final Section',
                           'Bumper Cave (Bottom)', 'Bumper Cave (Top)', 'Brewery', 'C-Shaped House', 'Chest Game',
                           'Hammer Peg Cave', 'Red Shield Shop', 'Dark Sanctuary Hint',
                           'Fortune Teller (Dark)', 'Dark World Shop', 'Dark Lumberjack Shop',
                           'Skull Woods First Section Hole (West)', 'Skull Woods First Section Hole (East)',
                           'Skull Woods First Section Hole (North)', 'Skull Woods Second Section Hole']
    mire_entrances = ['Misery Mire', 'Mire Shed', 'Mire Hint', 'Mire Fairy']
    ddm_entrances = ['Turtle Rock', 'Dark Death Mountain Ledge (West)', 'Dark Death Mountain Ledge (East)',
                     'Turtle Rock Isolated Ledge Entrance', 'Superbunny Cave (Top)', 'Superbunny Cave (Bottom)',
                     'Hookshot Cave', 'Hookshot Cave Back Entrance', 'Ganons Tower', 'Spike Cave',
                     'Dark Death Mountain Shop', 'Dark Death Mountain Fairy']

    if inverted:
        east_dw_entrances.remove('Pyramid Entrance')
        central_lw_entrances.append('Inverted Pyramid Entrance')
        east_dw_entrances.remove('Pyramid Hole')
        central_lw_entrances.append('Inverted Pyramid Hole')

    districts['Kakariko'] = District('Kakariko', kak_locations, entrances=kak_entrances)
    districts['Northwest Hyrule'] = District('Northwest Hyrule', nw_lw_locations, entrances=nw_lw_entrances)
    districts['Central Hyrule'] = District('Central Hyrule', central_lw_locations, entrances=central_lw_entrances)
    districts['The Desert Area'] = District('Desert', desert_locations, entrances=desert_entrances)
    districts['Lake Hylia'] = District('Lake Hylia', lake_locations, entrances=lake_entrances)
    districts['Eastern Hyrule'] = District('Eastern Hyrule', east_lw_locations, entrances=east_lw_entrances)
    districts['Death Mountain'] = District('Death Mountain', lw_dm_locations, entrances=lw_dm_entrances)
    districts['East Dark World'] = District('East Dark World', east_dw_locations, entrances=east_dw_entrances)
    districts['South Dark World'] = District('South Dark World', south_dw_locations, entrances=south_dw_entrances)
    districts['Northwest Dark World'] = District('Northwest Dark World', voo_north_locations,
                                                 entrances=voo_north_entrances)
    districts['The Mire Area'] = District('The Mire', set(), entrances=mire_entrances)
    districts['Dark Death Mountain'] = District('Dark Death Mountain', ddm_locations, entrances=ddm_entrances)
    districts.update({x: District(x, set(), dungeon=x) for x in dungeon_table.keys()})

    world.districts[player] = districts


def resolve_districts(world):
    create_districts(world)
    state = CollectionState(world)
    state.sweep_for_events()
    for player in range(1, world.players + 1):
        # these are not static for OWR - but still important
        inaccessible = inaccessible_regions_inv if world.mode[player] == 'inverted' else inaccessible_regions_std
        check_set = find_reachable_locations(state, player)
        for name, district in world.districts[player].items():
            if district.dungeon:
                layout = world.dungeon_layouts[player][district.dungeon]
                district.locations.update([l.name for r in layout.master_sector.regions
                                           for l in r.locations if not l.item and l.real])
            else:
                for entrance in district.entrances:
                    ent = world.get_entrance(entrance, player)
                    queue = deque([ent.connected_region])
                    visited = set()
                    while len(queue) > 0:
                        region = queue.pop()
                        visited.add(region)
                        if region.type == RegionType.Cave:
                            for location in region.locations:
                                if not location.item and location.real:
                                    district.locations.add(location.name)
                            for ext in region.exits:
                                if ext.connected_region and ext.connected_region not in visited:
                                    queue.appendleft(ext.connected_region)
                        elif region.type == RegionType.Dungeon and region.dungeon:
                            district.dungeons.add(region.dungeon.name)
                        elif region.name in inaccessible:
                            district.access_points.add(region)

            district.sphere_one = len(check_set.intersection(district.locations)) > 0


def find_reachable_locations(state, player):
    check_set = set()
    for region in state.reachable_regions[player]:
        for location in region.locations:
            if location.can_reach(state) and not location.forced_item and location.real:
                check_set.add(location.name)
    return check_set


inaccessible_regions_std = {'Desert Mouth', 'Bumper Cave Ledge', 'Skull Woods Forest (West)',
                            'Dark Death Mountain Ledge', 'Dark Death Mountain Isolated Ledge',
                            'Dark Death Mountain Floating Island'}


inaccessible_regions_inv = {'Desert Mouth', 'Maze Race Ledge', 'Desert Ledge',
                            'Desert Ledge Keep', 'Hyrule Castle Ledge', 'Mountain Pass Ledge'}
