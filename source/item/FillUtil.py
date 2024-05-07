import RaceRandom as random
import logging
from collections import defaultdict

from source.item.District import resolve_districts
from BaseClasses import PotItem, PotFlags, LocationType
from DoorShuffle import validate_vanilla_reservation
from Dungeons import dungeon_table
from Items import item_table, ItemFactory
from PotShuffle import vanilla_pots


class ItemPoolConfig(object):

    def __init__(self):
        self.location_groups = None
        self.static_placement = None
        self.item_pool = None
        self.placeholders = None
        self.reserved_locations = defaultdict(set)
        self.restricted = {}
        self.preferred = {}
        self.verify = {}
        self.verify_count = 0
        self.verify_target = 0

        self.recorded_choices = []


class LocationGroup(object):
    def __init__(self, name):
        self.name = name
        self.locations = []

        # flags
        self.keyshuffle = False
        self.shopsanity = False
        self.retro = False

    def locs(self, locs):
        self.locations = list(locs)
        return self

    def flags(self, k, s=False, r=False):
        self.keyshuffle = k
        self.shopsanity = s
        self.retro = r
        return self


def create_item_pool_config(world):
    world.item_pool_config = config = ItemPoolConfig()
    player_set = set()
    for player in range(1, world.players+1):
        if world.restrict_boss_items[player] != 'none':
            player_set.add(player)
        if world.restrict_boss_items[player] == 'dungeon':
            for dungeon, info in dungeon_table.items():
                if info.prize:
                    d_name = "Thieves' Town" if dungeon.startswith('Thieves') else dungeon
                    config.reserved_locations[player].add(f'{d_name} - Boss')
    for dungeon in world.dungeons:
        if world.restrict_boss_items[dungeon.player] != 'none':
            for item in dungeon.all_items:
                if item.map or item.compass:
                    item.advancement = True
    if world.algorithm == 'vanilla_fill':
        config.static_placement = {}
        config.location_groups = {}
        for player in range(1, world.players + 1):
            config.static_placement[player] = defaultdict(list)
            config.static_placement[player].update(vanilla_mapping)
            if world.dropshuffle[player] != 'none':
                for item, locs in keydrop_vanilla_mapping.items():
                    config.static_placement[player][item].extend(locs)
            if world.pottery[player] not in ['none', 'cave']:
                for item, locs in potkeys_vanilla_mapping.items():
                    config.static_placement[player][item].extend(locs)
            if world.pottery[player] in ['lottery', 'cave', 'dungeon']:
                for super_tile, pot_list in vanilla_pots.items():
                    for pot_index, pot in enumerate(pot_list):
                        if pot.item not in [PotItem.Key, PotItem.Hole, PotItem.Switch]:
                            item = pot_items[pot.item]
                            descriptor = 'Large Block' if pot.flags & PotFlags.Block else f'Pot #{pot_index+1}'
                            loc = f'{pot.room} {descriptor}'
                            config.static_placement[player][item].append(loc)
            if world.shopsanity[player]:
                for item, locs in shop_vanilla_mapping.items():
                    config.static_placement[player][item].extend(locs)
            if world.take_any[player] != 'none':
                for item, locs in retro_vanilla_mapping.items():
                    config.static_placement[player][item].extend(locs)
                # universal keys
            if world.keyshuffle[player] == 'universal':
                universal_key_locations = []
                for item, locs in vanilla_mapping.items():
                    if 'Small Key' in item:
                        universal_key_locations.extend(locs)
                if world.dropshuffle[player] != 'none':
                    for item, locs in keydrop_vanilla_mapping.items():
                        if 'Small Key' in item:
                            universal_key_locations.extend(locs)
                if world.pottery[player] not in ['none', 'cave']:
                    for item, locs in potkeys_vanilla_mapping.items():
                        universal_key_locations.extend(locs)
                if world.shopsanity[player]:
                    universal_key_locations.extend(shop_vanilla_mapping['Small Heart'])
                    universal_key_locations.extend(shop_vanilla_mapping['Blue Shield'])
                config.static_placement[player]['Small Key (Universal)'] = universal_key_locations
            if world.bow_mode[player].startswith('retro') and world.shopsanity[player]:
                single_arrow_placement = list(shop_vanilla_mapping['Red Potion'])
                single_arrow_placement.append('Red Shield Shop - Right')
                config.static_placement[player]['Single Arrow'] = single_arrow_placement
            config.location_groups[player] = [
                LocationGroup('Major').locs(mode_grouping['Overworld Major'] + mode_grouping['Big Chests'] + mode_grouping['Heart Containers']),
                LocationGroup('bkhp').locs(mode_grouping['Heart Pieces']),
                LocationGroup('bktrash').locs(mode_grouping['Overworld Trash'] + mode_grouping['Dungeon Trash']),
                LocationGroup('bkgt').locs(mode_grouping['GT Trash'])]
            for loc_name in mode_grouping['Big Chests'] + mode_grouping['Heart Containers']:
                config.reserved_locations[player].add(loc_name)
    elif world.algorithm == 'major_only':
        config.location_groups = [
            LocationGroup('MajorItems'),
            LocationGroup('Backup')
        ]
        config.item_pool = {}
        init_set = mode_grouping['Overworld Major'] + mode_grouping['Big Chests'] + mode_grouping['Heart Containers']
        for player in range(1, world.players + 1):
            groups = LocationGroup('Major').locs(init_set)
            if world.bigkeyshuffle[player]:
                groups.locations.extend(mode_grouping['Big Keys'])
                if world.dropshuffle[player] != 'none':
                    groups.locations.extend(mode_grouping['Big Key Drops'])
            if world.keyshuffle[player] != 'none':
                groups.locations.extend(mode_grouping['Small Keys'])
                if world.dropshuffle[player] != 'none':
                    groups.locations.extend(mode_grouping['Key Drops'])
                if world.pottery[player] not in ['none', 'cave']:
                    groups.locations.extend(mode_grouping['Pot Keys'])
            if world.compassshuffle[player]:
                groups.locations.extend(mode_grouping['Compasses'])
            if world.mapshuffle[player]:
                groups.locations.extend(mode_grouping['Maps'])
            if world.shopsanity[player]:
                groups.locations.append('Capacity Upgrade - Left')
                groups.locations.append('Capacity Upgrade - Right')
            if world.take_any[player] != 'none':
                if world.shopsanity[player]:
                    groups.locations.extend(retro_vanilla_mapping['Heart Container'])
                    groups.locations.append('Old Man Sword Cave Item 1')
            config.item_pool[player] = determine_major_items(world, player)
            config.location_groups[0].locations = set(groups.locations)
            config.reserved_locations[player].update(groups.locations)
    elif world.algorithm == 'dungeon_only':
        config.location_groups = [
            LocationGroup('Dungeons'),
            LocationGroup('Backup')
        ]
        config.item_pool = {}
        dungeon_set = (mode_grouping['Big Chests'] + mode_grouping['Dungeon Trash'] + mode_grouping['Big Keys'] +
                       mode_grouping['Heart Containers'] + mode_grouping['GT Trash'] + mode_grouping['Small Keys'] +
                       mode_grouping['Compasses'] + mode_grouping['Maps'] + mode_grouping['Key Drops'] +
                       mode_grouping['Pot Keys'] + mode_grouping['Big Key Drops'])
        dungeon_set = set(dungeon_set)
        for loc in world.get_locations():
            if loc.parent_region.dungeon and loc.type in [LocationType.Pot, LocationType.Drop]:
                dungeon_set.add(loc.name)
        for player in range(1, world.players + 1):
            config.item_pool[player] = determine_major_items(world, player)
            config.location_groups[0].locations = set(dungeon_set)


def district_item_pool_config(world):
    resolve_districts(world)
    if world.algorithm == 'district':
        config = world.item_pool_config
        config.location_groups = [
            LocationGroup('Districts'),
        ]
        item_cnt = 0
        config.item_pool = {}
        for player in range(1, world.players + 1):
            config.item_pool[player] = determine_major_items(world, player)
            item_cnt += count_major_items(config, world, player)
        # set district choices
        district_choices = {}
        for p in range(1, world.players + 1):
            for name, district in world.districts[p].items():
                adjustment = 0
                if district.dungeon:
                    adjustment = len([i for i in world.get_dungeon(name, p).all_items
                                      if i.is_inside_dungeon_item(world)])
                dist_adj = adjustment
                if name not in district_choices:
                    district_choices[name] = (district.sphere_one, dist_adj)
                else:
                    so, amt = district_choices[name]
                    district_choices[name] = (so or district.sphere_one, amt + dist_adj)

        chosen_locations = defaultdict(set)
        adjustment_cnt = 0

        # choose a sphere one district
        sphere_one_choices = [d for d, info in district_choices.items() if info[0]]
        sphere_one = random.choice(sphere_one_choices)
        so, adj = district_choices[sphere_one]
        for player in range(1, world.players + 1):
            for location in world.districts[player][sphere_one].locations:
                chosen_locations[location].add(player)
        del district_choices[sphere_one]
        config.recorded_choices.append(sphere_one)
        adjustment_cnt += adj
        location_cnt = len(chosen_locations) - adjustment_cnt

        scale_factors = defaultdict(int)
        scale_total = 0
        for p in range(1, world.players + 1):
            ent = 'Agahnims Tower' if world.is_atgt_swapped(p) else 'Ganons Tower'
            dungeon = world.get_entrance(ent, p).connected_region.dungeon
            if dungeon:
                scale = world.crystals_needed_for_gt[p]
                if scale > 0:
                    scale_total += scale
                    scale_factors[dungeon.name] += scale
        scale_total = max(1, scale_total)
        scale_divisors = defaultdict(lambda: 1)
        scale_divisors.update(scale_factors)

        while location_cnt < item_cnt:
            weights = [scale_total / scale_divisors[d] for d in district_choices.keys()]
            choice = random.choices(list(district_choices.keys()), weights=weights, k=1)[0]
            so, adj = district_choices[choice]

            for player in range(1, world.players + 1):
                for location in world.districts[player][choice].locations:
                    chosen_locations[location].add(player)
            del district_choices[choice]
            config.recorded_choices.append(choice)
            adjustment_cnt += adj
            location_cnt = len(chosen_locations) - adjustment_cnt
        config.placeholders = location_cnt - item_cnt
        config.location_groups[0].locations = chosen_locations


def location_prefilled(location, world, player):
    if world.swords[player] == 'vanilla':
        return location in vanilla_swords
    if world.goal[player] == 'pedestal':
        return location == 'Master Sword Pedestal'
    return False


def previously_reserved(location, world, player):
    if '- Boss' in location.name:
        if world.restrict_boss_items[player] == 'mapcompass' and (not world.compassshuffle[player]
                                                                  or not world.mapshuffle[player]):
            return True
        if world.restrict_boss_items[player] == 'dungeon' and (not world.compassshuffle[player]
                                                               or not world.mapshuffle[player]
                                                               or not world.bigkeyshuffle[player]
                                                               or world.keyshuffle[player] == 'none'):
            return True
    return False


def massage_item_pool(world):
    player_pool = defaultdict(list)
    for item in world.itempool:
        player_pool[item.player].append(item)
    for dungeon in world.dungeons:
        for item in dungeon.all_items:
            if item.is_inside_dungeon_item(world):
                player_pool[item.player].append(item)
    player_locations = defaultdict(list)
    for player in player_pool:
        player_locations[player] = [x for x in world.get_unfilled_locations(player) if '- Prize' not in x.name]
        discrepancy = len(player_pool[player]) - len(player_locations[player])
        if discrepancy:
            trash_options = [x for x in player_pool[player] if x.name in trash_items]
            random.shuffle(trash_options)
            trash_options = sorted(trash_options, key=lambda x: trash_items[x.name], reverse=True)
            while discrepancy > 0 and len(trash_options) > 0:
                deleted = trash_options.pop()
                world.itempool.remove(deleted)
                discrepancy -= 1
            if discrepancy > 0:
                raise Exception(f'Too many required items in pool, {discrepancy} items cannot be placed')
    if world.item_pool_config.placeholders is not None:
        removed = 0
        single_rupees = [item for item in world.itempool if item.name == 'Rupee (1)']
        removed += len(single_rupees)
        for x in single_rupees:
            world.itempool.remove(x)
        if removed < world.item_pool_config.placeholders:
            trash_options = [x for x in world.itempool if x.name in trash_items]
            random.shuffle(trash_options)
            trash_options = sorted(trash_options, key=lambda x: trash_items[x.name], reverse=True)
            while removed < world.item_pool_config.placeholders:
                if len(trash_options) == 0:
                    logging.getLogger('').warning(f'Too many good items in pool, not enough room for placeholders')
                deleted = trash_options.pop()
                world.itempool.remove(deleted)
                removed += 1
        if world.item_pool_config.placeholders > len(single_rupees):
            for _ in range(world.item_pool_config.placeholders-len(single_rupees)):
                single_rupees.append(ItemFactory('Rupee (1)', random.randint(1, world.players)))
        placeholders = random.sample(single_rupees, world.item_pool_config.placeholders)
        world.itempool += placeholders
        removed -= len(placeholders)
        for _ in range(removed):
            world.itempool.append(ItemFactory('Rupees (5)', random.randint(1, world.players)))


def replace_trash_item(item_pool, replacement):
    trash_options = [x for x in item_pool if x.name in trash_items]
    random.shuffle(trash_options)
    trash_options = sorted(trash_options, key=lambda x: trash_items[x.name], reverse=True)
    if len(trash_options) == 0:
        logging.getLogger('').warning(f'Too many good items in pool, not enough room for placeholders')
    deleted = trash_options.pop()
    item_pool.remove(deleted)
    replace_item = ItemFactory(replacement, deleted.player)
    item_pool.append(replace_item)
    return replace_item


def validate_reservation(location, dungeon, world, player):
    world.item_pool_config.reserved_locations[player].add(location.name)
    if world.doorShuffle[player] != 'vanilla':
        return True  # we can generate the dungeon somehow most likely
    if validate_vanilla_reservation(dungeon, world, player):
        return True
    world.item_pool_config.reserved_locations[player].remove(location.name)
    return False


def count_major_items(config, world, player):
    return sum(1 for x in world.itempool if x.name in config.item_pool[player] and x.player == player)


def determine_major_items(world, player):
    major_item_set = set(major_items)
    if world.progressive == 'off':
        pass  # now what?
    if world.bigkeyshuffle[player]:
        major_item_set.update({x for x, y in item_table.items() if y[2] == 'BigKey'})
    if world.keyshuffle[player] != 'none':
        major_item_set.update({x for x, y in item_table.items() if y[2] == 'SmallKey'})
    if world.compassshuffle[player]:
        major_item_set.update({x for x, y in item_table.items() if y[2] == 'Compass'})
    if world.mapshuffle[player]:
        major_item_set.update({x for x, y in item_table.items() if y[2] == 'Map'})
    if world.shopsanity[player]:
        major_item_set.add('Bomb Upgrade (+5)')
        major_item_set.add('Arrow Upgrade (+5)')
    if world.bow_mode[player].startswith('retro'):
        major_item_set.add('Single Arrow')
    if world.keyshuffle[player] == 'universal':
        major_item_set.add('Small Key (Universal)')
    if world.goal[player] in {'triforcehunt', 'ganonhunt', 'trinity'}:
        major_item_set.add('Triforce Piece')
    if world.bombbag[player]:
        major_item_set.add('Bomb Upgrade (+10)')
    return major_item_set


def classify_major_items(world):
    if world.algorithm in ['major_only', 'dungeon_only', 'district']:
        config = world.item_pool_config
        for item in world.itempool:
            if item.name in config.item_pool[item.player]:
                if not item.advancement and not item.priority:
                    if item.smallkey or item.bigkey:
                        item.advancement = True
                    else:
                        item.priority = True
            else:
                if item.priority:
                    item.priority = False


def vanilla_fallback(item_to_place, locations, world):
    if item_to_place.is_inside_dungeon_item(world):
        return [x for x in locations if x.name in vanilla_fallback_dungeon_set
                and x.parent_region.dungeon and x.parent_region.dungeon.name == item_to_place.dungeon]
    return []


def filter_locations(item_to_place, locations, world, vanilla_skip=False, potion=False):
    config = world.item_pool_config
    if not isinstance(item_to_place, str):
        item_name = 'Bottle' if item_to_place.name.startswith('Bottle') else item_to_place.name
    else:
        item_name = item_to_place
    if world.algorithm == 'vanilla_fill':
        filtered = []
        item_name = 'Bottle' if item_to_place.name.startswith('Bottle') else item_to_place.name
        if item_name in config.static_placement[item_to_place.player]:
            restricted = config.static_placement[item_to_place.player][item_name]
            filtered = [l for l in locations if l.player == item_to_place.player and l.name in restricted]
        if vanilla_skip and len(filtered) == 0:
            return filtered
        i = 0
        while len(filtered) <= 0:
            if i >= len(config.location_groups[item_to_place.player]):
                return locations
            restricted = config.location_groups[item_to_place.player][i].locations
            filtered = [l for l in locations if l.player == item_to_place.player and l.name in restricted]
            i += 1
        return filtered
    if world.algorithm in ['major_only', 'dungeon_only']:
        config = world.item_pool_config
        if item_to_place.name in config.item_pool[item_to_place.player]:
            restricted = config.location_groups[0].locations
            filtered = [l for l in locations if l.name in restricted]
            return filtered
    if world.algorithm == 'district':
        config = world.item_pool_config
        if ((isinstance(item_to_place, str) and item_to_place == 'Placeholder')
           or item_to_place.name in config.item_pool[item_to_place.player]):
            restricted = config.location_groups[0].locations
            filtered = [l for l in locations if l.name in restricted and l.player in restricted[l.name]]
            return filtered
        elif potion:
            restricted = config.location_groups[0].locations
            filtered = [l for l in locations if l.name not in restricted or l.player not in restricted[l.name]]
            if len(filtered) == 0:
                raise RuntimeError('Can\'t sell potion of a certain type due to district restriction')
            return filtered
    if (item_name, item_to_place.player) in config.restricted:
        locs = config.restricted[(item_name, item_to_place.player)]
        return sorted(locations, key=lambda l: 1 if l.name in locs else 0)
    if (item_name, item_to_place.player) in config.preferred:
        locs = config.preferred[(item_name, item_to_place.player)]
        return sorted(locations, key=lambda l: 0 if l.name in locs else 1)
    if (item_name, item_to_place.player) in config.verify:
        locs = config.verify[(item_name, item_to_place.player)].keys()
        return sorted(locations, key=lambda l: 0 if l.name in locs else 1)
    return locations




def filter_special_locations(locations, world, vanilla_matcher):
    if world.algorithm == 'district':
        config = world.item_pool_config
        restricted = config.location_groups[0].locations
        filtered = [l for l in locations if l.name not in restricted or l.player not in restricted[l.name]]
        return filtered if len(filtered) > 0 else locations
    if world.algorithm == 'vanilla_fill':
        filtered = [l for l in locations if vanilla_matcher(l)]
        return filtered if len(filtered) > 0 else locations
    return locations


vanilla_mapping = {
    'Green Pendant': ['Eastern Palace - Prize'],
    'Red Pendant': ['Desert Palace - Prize', 'Tower of Hera - Prize'],
    'Blue Pendant': ['Desert Palace - Prize', 'Tower of Hera - Prize'],
    'Crystal 1': ['Palace of Darkness - Prize', 'Swamp Palace - Prize', 'Thieves\' Town - Prize',
                  'Skull Woods - Prize', 'Turtle Rock - Prize'],
    'Crystal 2': ['Palace of Darkness - Prize', 'Swamp Palace - Prize', 'Thieves\' Town - Prize',
                  'Skull Woods - Prize', 'Turtle Rock - Prize'],
    'Crystal 3': ['Palace of Darkness - Prize', 'Swamp Palace - Prize', 'Thieves\' Town - Prize',
                  'Skull Woods - Prize', 'Turtle Rock - Prize'],
    'Crystal 4': ['Palace of Darkness - Prize', 'Swamp Palace - Prize', 'Thieves\' Town - Prize',
                  'Skull Woods - Prize', 'Turtle Rock - Prize'],
    'Crystal 7': ['Palace of Darkness - Prize', 'Swamp Palace - Prize', 'Thieves\' Town - Prize',
                  'Skull Woods - Prize', 'Turtle Rock - Prize'],
    'Crystal 5': ['Ice Palace - Prize', 'Misery Mire - Prize'],
    'Crystal 6': ['Ice Palace - Prize', 'Misery Mire - Prize'],
    'Bow': ['Eastern Palace - Big Chest'],
    'Progressive Bow': ['Eastern Palace - Big Chest', 'Pyramid Fairy - Right'],
    'Book of Mudora': ['Library'],
    'Hammer': ['Palace of Darkness - Big Chest'],
    'Hookshot': ['Swamp Palace - Big Chest'],
    'Magic Mirror': ['Old Man'],
    'Ocarina': ['Flute Spot'],
    'Ocarina (Activated)': ['Flute Spot'],
    'Pegasus Boots': ['Sahasrahla'],
    'Power Glove': ['Desert Palace - Big Chest'],
    'Cape': ["King's Tomb"],
    'Mushroom': ['Mushroom'],
    'Shovel': ['Stumpy'],
    'Lamp': ["Link's House"],
    'Magic Powder': ['Potion Shop'],
    'Moon Pearl': ['Tower of Hera - Big Chest'],
    'Cane of Somaria': ['Misery Mire - Big Chest'],
    'Fire Rod': ['Skull Woods - Big Chest'],
    'Flippers': ['King Zora'],
    'Ice Rod': ['Ice Rod Cave'],
    'Titans Mitts': ["Thieves' Town - Big Chest"],
    'Bombos': ['Bombos Tablet'],
    'Ether': ['Ether Tablet'],
    'Quake': ['Catfish'],
    'Bottle': ['Bottle Merchant', 'Kakariko Tavern', 'Purple Chest', 'Hobo'],
    'Master Sword': ['Master Sword Pedestal'],
    'Tempered Sword': ['Blacksmith'],
    'Fighter Sword': ["Link's Uncle"],
    'Golden Sword': ['Pyramid Fairy - Left'],
    'Progressive Sword': ["Link's Uncle", 'Blacksmith', 'Master Sword Pedestal', 'Pyramid Fairy - Left'],
    'Progressive Glove': ['Desert Palace - Big Chest', "Thieves' Town - Big Chest"],
    'Silver Arrows': ['Pyramid Fairy - Right'],
    'Single Arrow': ['Palace of Darkness - Dark Basement - Left'],
    'Arrows (10)': ['Chicken House', 'Mini Moldorm Cave - Far Right', 'Sewers - Secret Room - Right',
                    'Paradox Cave Upper - Right', 'Mire Shed - Right', 'Ganons Tower - Hope Room - Left',
                    'Ganons Tower - Compass Room - Bottom Right', 'Ganons Tower - DMs Room - Top Right',
                    'Ganons Tower - Randomizer Room - Top Left', 'Ganons Tower - Randomizer Room - Top Right',
                    "Ganons Tower - Bob's Chest", 'Ganons Tower - Big Key Room - Left'],
    'Bombs (3)': ['Floodgate Chest', "Sahasrahla's Hut - Middle", 'Kakariko Well - Bottom', 'Superbunny Cave - Top',
                  'Mini Moldorm Cave - Far Left', 'Sewers - Secret Room - Left', 'Paradox Cave Upper - Left',
                  "Thieves' Town - Attic", 'Ice Palace - Freezor Chest', 'Palace of Darkness - Dark Maze - Top',
                  'Ganons Tower - Hope Room - Right', 'Ganons Tower - DMs Room - Top Left',
                  'Ganons Tower - Randomizer Room - Bottom Left', 'Ganons Tower - Randomizer Room - Bottom Right',
                  'Ganons Tower - Big Key Room - Right', 'Ganons Tower - Mini Helmasaur Room - Left',
                  'Ganons Tower - Mini Helmasaur Room - Right'],
    'Blue Mail': ['Ice Palace - Big Chest'],
    'Red Mail': ['Ganons Tower - Big Chest'],
    'Progressive Armor': ['Ice Palace - Big Chest', 'Ganons Tower - Big Chest'],
    'Blue Boomerang': ['Hyrule Castle - Boomerang Chest'],
    'Red Boomerang': ['Waterfall Fairy - Left'],
    'Blue Shield': ['Secret Passage'],
    'Red Shield': ['Waterfall Fairy - Right'],
    'Mirror Shield': ['Turtle Rock - Big Chest'],
    'Progressive Shield': ['Secret Passage', 'Waterfall Fairy - Right', 'Turtle Rock - Big Chest'],
    'Bug Catching Net': ['Sick Kid'],
    'Cane of Byrna': ['Spike Cave'],
    'Boss Heart Container': ['Desert Palace - Boss', 'Eastern Palace - Boss', 'Tower of Hera - Boss',
                             'Swamp Palace - Boss', "Thieves' Town - Boss", 'Skull Woods - Boss', 'Ice Palace - Boss',
                             'Misery Mire - Boss', 'Turtle Rock - Boss', 'Palace of Darkness - Boss'],
    'Sanctuary Heart Container': ['Sanctuary'],
    'Piece of Heart': ['Sunken Treasure', "Blind's Hideout - Top", "Zora's Ledge", "Aginah's Cave", 'Maze Race',
                       'Kakariko Well - Top', 'Lost Woods Hideout', 'Lumberjack Tree', 'Cave 45', 'Graveyard Cave',
                       'Checkerboard Cave', 'Bonk Rock Cave', 'Lake Hylia Island', 'Desert Ledge', 'Spectacle Rock',
                       'Spectacle Rock Cave', 'Pyramid', 'Digging Game', 'Peg Cave', 'Chest Game', 'Bumper Cave Ledge',
                       'Mire Shed - Left', 'Floating Island', 'Mimic Cave'],
    'Rupee (1)': ['Turtle Rock - Eye Bridge - Top Right', 'Ganons Tower - Compass Room - Top Right'],
    'Rupees (5)': ["Hyrule Castle - Zelda's Chest", 'Turtle Rock - Eye Bridge - Top Left',
                   # 'Palace of Darkness - Harmless Hellway',
                   'Palace of Darkness - Dark Maze - Bottom',
                   'Ganons Tower - Validation Chest'],
    'Rupees (20)': ["Blind's Hideout - Left", "Blind's Hideout - Right", "Blind's Hideout - Far Left",
                    "Blind's Hideout - Far Right", 'Kakariko Well - Left', 'Kakariko Well - Middle',
                    'Kakariko Well - Right', 'Mini Moldorm Cave - Left', 'Mini Moldorm Cave - Right',
                    'Paradox Cave Lower - Far Left', 'Paradox Cave Lower - Left', 'Paradox Cave Lower - Right',
                    'Paradox Cave Lower - Far Right', 'Paradox Cave Lower - Middle', 'Hype Cave - Top',
                    'Hype Cave - Middle Right', 'Hype Cave - Middle Left', 'Hype Cave - Bottom',
                    'Swamp Palace - West Chest', 'Swamp Palace - Flooded Room - Left', 'Swamp Palace - Waterfall Room',
                    'Swamp Palace - Flooded Room - Right', "Thieves' Town - Ambush Chest",
                    'Turtle Rock - Eye Bridge - Bottom Right', 'Ganons Tower - Compass Room - Bottom Left',
                    'Swamp Palace - Flooded Room - Right', "Thieves' Town - Ambush Chest",
                    'Ganons Tower - DMs Room - Bottom Left', 'Ganons Tower - DMs Room - Bottom Right'],
    'Rupees (50)': ["Sahasrahla's Hut - Left", "Sahasrahla's Hut - Right", 'Spiral Cave', 'Superbunny Cave - Bottom',
                    'Hookshot Cave - Top Right', 'Hookshot Cave - Top Left', 'Hookshot Cave - Bottom Right',
                    'Hookshot Cave - Bottom Left'],
    'Rupees (100)': ['Eastern Palace - Cannonball Chest'],
    'Rupees (300)': ['Mini Moldorm Cave - Generous Guy', 'Sewers - Secret Room - Middle', 'Hype Cave - Generous Guy',
                     'Brewery', 'C-Shaped House'],
    'Magic Upgrade (1/2)': ['Magic Bat'],
    'Big Key (Eastern Palace)': ['Eastern Palace - Big Key Chest'],
    'Compass (Eastern Palace)': ['Eastern Palace - Compass Chest'],
    'Map (Eastern Palace)': ['Eastern Palace - Map Chest'],
    'Small Key (Desert Palace)': ['Desert Palace - Torch'],
    'Big Key (Desert Palace)': ['Desert Palace - Big Key Chest'],
    'Compass (Desert Palace)': ['Desert Palace - Compass Chest'],
    'Map (Desert Palace)': ['Desert Palace - Map Chest'],
    'Small Key (Tower of Hera)': ['Tower of Hera - Basement Cage'],
    'Big Key (Tower of Hera)': ['Tower of Hera - Big Key Chest'],
    'Compass (Tower of Hera)': ['Tower of Hera - Compass Chest'],
    'Map (Tower of Hera)': ['Tower of Hera - Map Chest'],
    'Small Key (Escape)': ['Sewers - Dark Cross'],
    'Map (Escape)': ['Hyrule Castle - Map Chest'],
    'Small Key (Agahnims Tower)': ['Castle Tower - Room 03', 'Castle Tower - Dark Maze'],
    'Small Key (Palace of Darkness)': ['Palace of Darkness - Shooter Room', 'Palace of Darkness - The Arena - Bridge',
                                       'Palace of Darkness - Stalfos Basement',
                                       'Palace of Darkness - The Arena - Ledge',
                                       'Palace of Darkness - Dark Basement - Right',
                                       'Palace of Darkness - Harmless Hellway'],
                                       # 'Palace of Darkness - Dark Maze - Bottom'],
    'Big Key (Palace of Darkness)': ['Palace of Darkness - Big Key Chest'],
    'Compass (Palace of Darkness)': ['Palace of Darkness - Compass Chest'],
    'Map (Palace of Darkness)': ['Palace of Darkness - Map Chest'],
    'Small Key (Thieves Town)': ["Thieves' Town - Blind's Cell"],
    'Big Key (Thieves Town)': ["Thieves' Town - Big Key Chest"],
    'Compass (Thieves Town)': ["Thieves' Town - Compass Chest"],
    'Map (Thieves Town)': ["Thieves' Town - Map Chest"],
    'Small Key (Skull Woods)': ['Skull Woods - Pot Prison', 'Skull Woods - Pinball Room', 'Skull Woods - Bridge Room'],
    'Big Key (Skull Woods)': ['Skull Woods - Big Key Chest'],
    'Compass (Skull Woods)': ['Skull Woods - Compass Chest'],
    'Map (Skull Woods)': ['Skull Woods - Map Chest'],
    'Small Key (Swamp Palace)': ['Swamp Palace - Entrance'],
    'Big Key (Swamp Palace)': ['Swamp Palace - Big Key Chest'],
    'Compass (Swamp Palace)': ['Swamp Palace - Compass Chest'],
    'Map (Swamp Palace)': ['Swamp Palace - Map Chest'],
    'Small Key (Ice Palace)': ['Ice Palace - Iced T Room', 'Ice Palace - Spike Room'],
    'Big Key (Ice Palace)': ['Ice Palace - Big Key Chest'],
    'Compass (Ice Palace)': ['Ice Palace - Compass Chest'],
    'Map (Ice Palace)': ['Ice Palace - Map Chest'],
    'Small Key (Misery Mire)': ['Misery Mire - Main Lobby', 'Misery Mire - Bridge Chest', 'Misery Mire - Spike Chest'],
    'Big Key (Misery Mire)': ['Misery Mire - Big Key Chest'],
    'Compass (Misery Mire)': ['Misery Mire - Compass Chest'],
    'Map (Misery Mire)': ['Misery Mire - Map Chest'],
    'Small Key (Turtle Rock)': ['Turtle Rock - Roller Room - Right', 'Turtle Rock - Chain Chomps',
                                'Turtle Rock - Crystaroller Room', 'Turtle Rock - Eye Bridge - Bottom Left'],
    'Big Key (Turtle Rock)': ['Turtle Rock - Big Key Chest'],
    'Compass (Turtle Rock)': ['Turtle Rock - Compass Chest'],
    'Map (Turtle Rock)': ['Turtle Rock - Roller Room - Left'],
    'Small Key (Ganons Tower)': ["Ganons Tower - Bob's Torch", 'Ganons Tower - Tile Room',
                                 'Ganons Tower - Firesnake Room', 'Ganons Tower - Pre-Moldorm Chest'],
    'Big Key (Ganons Tower)': ['Ganons Tower - Big Key Chest'],
    'Compass (Ganons Tower)': ['Ganons Tower - Compass Room - Top Left'],
    'Map (Ganons Tower)': ['Ganons Tower - Map Chest']
}


keydrop_vanilla_mapping = {
    'Small Key (Eastern Palace)': ['Eastern Palace - Dark Eyegore Key Drop'],
    'Small Key (Escape)': ['Hyrule Castle - Map Guard Key Drop', 'Hyrule Castle - Boomerang Guard Key Drop',
                           'Hyrule Castle - Key Rat Key Drop'],
    'Big Key (Escape)': ['Hyrule Castle - Big Key Drop'],
    'Small Key (Agahnims Tower)': ['Castle Tower - Dark Archer Key Drop', 'Castle Tower - Circle of Pots Key Drop'],
    'Small Key (Skull Woods)': ['Skull Woods - Spike Corner Key Drop'],
    'Small Key (Ice Palace)': ['Ice Palace - Jelly Key Drop', 'Ice Palace - Conveyor Key Drop'],
    'Small Key (Misery Mire)': ['Misery Mire - Conveyor Crystal Key Drop'],
    'Small Key (Turtle Rock)': ['Turtle Rock - Pokey 1 Key Drop', 'Turtle Rock - Pokey 2 Key Drop'],
    'Small Key (Ganons Tower)': ['Ganons Tower - Mini Helmasaur Key Drop'],
}

potkeys_vanilla_mapping = {
    'Small Key (Desert Palace)': ['Desert Palace - Desert Tiles 1 Pot Key',
                                  'Desert Palace - Beamos Hall Pot Key', 'Desert Palace - Desert Tiles 2 Pot Key'],
    'Small Key (Eastern Palace)': ['Eastern Palace - Dark Square Pot Key'],
    'Small Key (Thieves Town)': ["Thieves' Town - Hallway Pot Key", "Thieves' Town - Spike Switch Pot Key"],
    'Small Key (Skull Woods)': ['Skull Woods - West Lobby Pot Key'],
    'Small Key (Swamp Palace)': ['Swamp Palace - Pot Row Pot Key', 'Swamp Palace - Trench 1 Pot Key',
                                 'Swamp Palace - Hookshot Pot Key', 'Swamp Palace - Trench 2 Pot Key',
                                 'Swamp Palace - Waterway Pot Key'],
    'Small Key (Ice Palace)': ['Ice Palace - Hammer Block Key Drop', 'Ice Palace - Many Pots Pot Key'],
    'Small Key (Misery Mire)': ['Misery Mire - Spikes Pot Key', 'Misery Mire - Fishbone Pot Key'],
    'Small Key (Ganons Tower)': ['Ganons Tower - Conveyor Cross Pot Key', 'Ganons Tower - Double Switch Pot Key',
                                 'Ganons Tower - Conveyor Star Pits Pot Key'],
}

shop_vanilla_mapping = {
    'Red Potion': ['Dark Death Mountain Shop - Left', 'Dark Lake Hylia Shop - Left', 'Dark Lumberjack Shop - Left',
                   'Village of Outcasts Shop - Left', 'Dark Potion Shop - Left', 'Paradox Shop - Left',
                   'Kakariko Shop - Left', 'Lake Hylia Shop - Left', 'Potion Shop - Left'],
    'Small Heart': ['Dark Death Mountain Shop - Middle', 'Paradox Shop - Middle', 'Kakariko Shop - Middle',
                    'Lake Hylia Shop - Middle'],
    'Bombs (10)': ['Dark Death Mountain Shop - Right', 'Dark Lake Hylia Shop - Right', 'Dark Lumberjack Shop - Right',
                   'Village of Outcasts Shop - Right', 'Dark Potion Shop - Right', 'Paradox Shop - Right',
                   'Kakariko Shop - Right', 'Lake Hylia Shop - Right'],
    'Blue Shield': ['Dark Lake Hylia Shop - Middle', 'Dark Lumberjack Shop - Middle',
                    'Village of Outcasts Shop - Middle', 'Dark Potion Shop - Middle'],
    'Red Shield': ['Red Shield Shop - Left'],
    'Bee': ['Red Shield Shop - Middle'],
    'Arrows (10)': ['Red Shield Shop - Right'],
    'Bomb Upgrade (+5)': ['Capacity Upgrade - Left'],
    'Arrow Upgrade (+5)': ['Capacity Upgrade - Right'],
    'Blue Potion': ['Potion Shop - Right'],
    'Green Potion': ['Potion Shop - Middle'],
}

retro_vanilla_mapping = {
    'Heart Container': ['Take-Any #1 Item 1', 'Take-Any #2 Item 1', 'Take-Any #3 Item 1', 'Take-Any #4 Item 1'],
    'Blue Potion': ['Take-Any #1 Item 2', 'Take-Any #2 Item 2', 'Take-Any #3 Item 2', 'Take-Any #4 Item 2'],
    'Progressive Sword': ['Old Man Sword Cave Item 1']
}

mode_grouping = {
    'Overworld Major': [
        "Link's Uncle", 'King Zora', "Link's House", 'Sahasrahla', 'Ice Rod Cave', 'Library',
        'Master Sword Pedestal', 'Old Man', 'Ether Tablet', 'Catfish', 'Stumpy', 'Bombos Tablet', 'Mushroom',
        'Bottle Merchant', 'Kakariko Tavern', 'Secret Passage', 'Flute Spot', 'Purple Chest',
        'Waterfall Fairy - Left', 'Waterfall Fairy - Right', 'Blacksmith', 'Magic Bat', 'Sick Kid', 'Hobo',
        'Potion Shop', 'Spike Cave', 'Pyramid Fairy - Left', 'Pyramid Fairy - Right', "King's Tomb",
    ],
    'Big Chests': ['Eastern Palace - Big Chest','Desert Palace - Big Chest', 'Tower of Hera - Big Chest',
                   'Palace of Darkness - Big Chest', 'Swamp Palace - Big Chest', 'Skull Woods - Big Chest',
                   "Thieves' Town - Big Chest", 'Misery Mire - Big Chest', 'Hyrule Castle - Boomerang Chest',
                   'Ice Palace - Big Chest', 'Turtle Rock - Big Chest', 'Ganons Tower - Big Chest'],
    'Heart Containers': ['Sanctuary', 'Eastern Palace - Boss','Desert Palace - Boss', 'Tower of Hera - Boss',
                         'Palace of Darkness - Boss', 'Swamp Palace - Boss', 'Skull Woods - Boss',
                         "Thieves' Town - Boss", 'Ice Palace - Boss', 'Misery Mire - Boss', 'Turtle Rock - Boss'],
    'Heart Pieces': [
        'Bumper Cave Ledge', 'Desert Ledge', 'Lake Hylia Island', 'Floating Island',
        'Maze Race', 'Spectacle Rock', 'Pyramid', "Zora's Ledge", 'Lumberjack Tree',
        'Sunken Treasure', 'Spectacle Rock Cave', 'Lost Woods Hideout', 'Checkerboard Cave', 'Peg Cave', 'Cave 45',
        'Graveyard Cave', 'Kakariko Well - Top', "Blind's Hideout - Top", 'Bonk Rock Cave', "Aginah's Cave",
        'Chest Game', 'Digging Game', 'Mire Shed - Left', 'Mimic Cave'
    ],
    'Big Keys': [
        'Eastern Palace - Big Key Chest', 'Ganons Tower - Big Key Chest',
        'Desert Palace - Big Key Chest', 'Tower of Hera - Big Key Chest', 'Palace of Darkness - Big Key Chest',
        'Swamp Palace - Big Key Chest', "Thieves' Town - Big Key Chest", 'Skull Woods - Big Key Chest',
        'Ice Palace - Big Key Chest', 'Misery Mire - Big Key Chest', 'Turtle Rock - Big Key Chest',
    ],
    'Compasses': [
        'Eastern Palace - Compass Chest', 'Desert Palace - Compass Chest', 'Tower of Hera - Compass Chest',
        'Palace of Darkness - Compass Chest', 'Swamp Palace - Compass Chest', 'Skull Woods - Compass Chest',
        "Thieves' Town - Compass Chest", 'Ice Palace - Compass Chest', 'Misery Mire - Compass Chest',
        'Turtle Rock - Compass Chest', 'Ganons Tower - Compass Room - Top Left'
    ],
    'Maps': [
        'Hyrule Castle - Map Chest', 'Eastern Palace - Map Chest', 'Desert Palace - Map Chest',
        'Tower of Hera - Map Chest', 'Palace of Darkness - Map Chest', 'Swamp Palace - Map Chest',
        'Skull Woods - Map Chest', "Thieves' Town - Map Chest", 'Ice Palace - Map Chest', 'Misery Mire - Map Chest',
        'Turtle Rock - Roller Room - Left', 'Ganons Tower - Map Chest'
    ],
    'Small Keys': [
        'Sewers - Dark Cross', 'Desert Palace - Torch', 'Tower of Hera - Basement Cage',
        'Castle Tower - Room 03', 'Castle Tower - Dark Maze',
        'Palace of Darkness - Stalfos Basement',  'Palace of Darkness - Dark Basement - Right',
        'Palace of Darkness - Harmless Hellway', 'Palace of Darkness - Shooter Room',
        'Palace of Darkness - The Arena - Bridge',  'Palace of Darkness - The Arena - Ledge',
        "Thieves' Town - Blind's Cell",  'Skull Woods - Bridge Room', 'Ice Palace - Spike Room',
        'Skull Woods - Pot Prison', 'Skull Woods - Pinball Room', 'Misery Mire - Spike Chest',
        'Ice Palace - Iced T Room', 'Misery Mire - Main Lobby', 'Misery Mire - Bridge Chest', 'Swamp Palace - Entrance',
        'Turtle Rock - Chain Chomps', 'Turtle Rock - Crystaroller Room', 'Turtle Rock - Roller Room - Right',
        'Turtle Rock - Eye Bridge - Bottom Left', "Ganons Tower - Bob's Torch", 'Ganons Tower - Tile Room',
        'Ganons Tower - Firesnake Room', 'Ganons Tower - Pre-Moldorm Chest'
    ],
    'Dungeon Trash': [
        'Sewers - Secret Room - Right', 'Sewers - Secret Room - Left', 'Sewers - Secret Room - Middle',
        "Hyrule Castle - Zelda's Chest", 'Eastern Palace - Cannonball Chest', "Thieves' Town - Ambush Chest",
        "Thieves' Town - Attic", 'Ice Palace - Freezor Chest', 'Palace of Darkness - Dark Basement - Left',
        'Palace of Darkness - Dark Maze - Bottom', 'Palace of Darkness - Dark Maze - Top',
        'Swamp Palace - Flooded Room - Left', 'Swamp Palace - Flooded Room - Right', 'Swamp Palace - Waterfall Room',
        'Turtle Rock - Eye Bridge - Bottom Right', 'Turtle Rock - Eye Bridge - Top Left',
        'Turtle Rock - Eye Bridge - Top Right', 'Swamp Palace - West Chest',
    ],
    'Overworld Trash': [
        "Blind's Hideout - Left", "Blind's Hideout - Right", "Blind's Hideout - Far Left",
        "Blind's Hideout - Far Right", 'Kakariko Well - Left', 'Kakariko Well - Middle', 'Kakariko Well - Right',
        'Kakariko Well - Bottom', 'Chicken House', 'Floodgate Chest', 'Mini Moldorm Cave - Left',
        'Mini Moldorm Cave - Right', 'Mini Moldorm Cave - Generous Guy', 'Mini Moldorm Cave - Far Left',
        'Mini Moldorm Cave - Far Right', "Sahasrahla's Hut - Left", "Sahasrahla's Hut - Right",
        "Sahasrahla's Hut - Middle", 'Paradox Cave Lower - Far Left', 'Paradox Cave Lower - Left',
        'Paradox Cave Lower - Right', 'Paradox Cave Lower - Far Right', 'Paradox Cave Lower - Middle',
        'Paradox Cave Upper - Left', 'Paradox Cave Upper - Right', 'Spiral Cave', 'Brewery', 'C-Shaped House',
        'Hype Cave - Top', 'Hype Cave - Middle Right', 'Hype Cave - Middle Left', 'Hype Cave - Bottom',
        'Hype Cave - Generous Guy', 'Superbunny Cave - Bottom', 'Superbunny Cave - Top', 'Hookshot Cave - Top Right',
        'Hookshot Cave - Top Left', 'Hookshot Cave - Bottom Right', 'Hookshot Cave - Bottom Left', 'Mire Shed - Right'
    ],
    'GT Trash': [
        'Ganons Tower - DMs Room - Top Right', 'Ganons Tower - DMs Room - Top Left',
        'Ganons Tower - DMs Room - Bottom Left', 'Ganons Tower - DMs Room - Bottom Right',
        'Ganons Tower - Compass Room - Top Right', 'Ganons Tower - Compass Room - Bottom Right',
        'Ganons Tower - Compass Room - Bottom Left', 'Ganons Tower - Hope Room - Left',
        'Ganons Tower - Hope Room - Right', 'Ganons Tower - Randomizer Room - Top Left',
        'Ganons Tower - Randomizer Room - Top Right', 'Ganons Tower - Randomizer Room - Bottom Right',
        'Ganons Tower - Randomizer Room - Bottom Left', "Ganons Tower - Bob's Chest",
        'Ganons Tower - Big Key Room - Left', 'Ganons Tower - Big Key Room - Right',
        'Ganons Tower - Mini Helmasaur Room - Left', 'Ganons Tower - Mini Helmasaur Room - Right',
        'Ganons Tower - Validation Chest',
    ],
    'Key Drops': [
        'Hyrule Castle - Map Guard Key Drop', 'Hyrule Castle - Boomerang Guard Key Drop',
        'Hyrule Castle - Key Rat Key Drop', 'Eastern Palace - Dark Eyegore Key Drop',
        'Castle Tower - Dark Archer Key Drop', 'Castle Tower - Circle of Pots Key Drop',
        'Skull Woods - Spike Corner Key Drop',  'Ice Palace - Jelly Key Drop', 'Ice Palace - Conveyor Key Drop',
        'Misery Mire - Conveyor Crystal Key Drop', 'Turtle Rock - Pokey 1 Key Drop',
        'Turtle Rock - Pokey 2 Key Drop', 'Ganons Tower - Mini Helmasuar Key Drop',
    ],
    'Pot Keys': [
        'Eastern Palace - Dark Square Pot Key', 'Desert Palace - Desert Tiles 1 Pot Key',
        'Desert Palace - Beamos Hall Pot Key', 'Desert Palace - Desert Tiles 2 Pot Key',
        'Swamp Palace - Pot Row Pot Key', 'Swamp Palace - Trench 1 Pot Key', 'Swamp Palace - Hookshot Pot Key',
        'Swamp Palace - Trench 2 Pot Key', 'Swamp Palace - Waterway Pot Key', 'Skull Woods - West Lobby Pot Key',
        "Thieves' Town - Hallway Pot Key", "Thieves' Town - Spike Switch Pot Key",
        'Ice Palace - Hammer Block Key Drop', 'Ice Palace - Many Pots Pot Key', 'Misery Mire - Spikes Pot Key',
        'Misery Mire - Fishbone Pot Key', 'Ganons Tower - Conveyor Cross Pot Key',
        'Ganons Tower - Double Switch Pot Key', 'Ganons Tower - Conveyor Star Pits Pot Key',

    ],
    'Big Key Drops': ['Hyrule Castle - Big Key Drop'],
    'Shops': [
        'Dark Death Mountain Shop - Left', 'Dark Death Mountain Shop - Middle', 'Dark Death Mountain Shop - Right',
        'Red Shield Shop - Left', 'Red Shield Shop - Middle', 'Red Shield Shop - Right', 'Dark Lake Hylia Shop - Left',
        'Dark Lake Hylia Shop - Middle', 'Dark Lake Hylia Shop - Right', 'Dark Lumberjack Shop - Left',
        'Dark Lumberjack Shop - Middle', 'Dark Lumberjack Shop - Right', 'Village of Outcasts Shop - Left',
        'Village of Outcasts Shop - Middle', 'Village of Outcasts Shop - Right', 'Dark Potion Shop - Left',
        'Dark Potion Shop - Middle', 'Dark Potion Shop - Right', 'Paradox Shop - Left', 'Paradox Shop - Middle',
        'Paradox Shop - Right', 'Kakariko Shop - Left', 'Kakariko Shop - Middle', 'Kakariko Shop - Right',
        'Lake Hylia Shop - Left', 'Lake Hylia Shop - Middle', 'Lake Hylia Shop - Right', 'Capacity Upgrade - Left',
        'Capacity Upgrade - Right'
    ],
    'RetroShops': [
        'Old Man Sword Cave Item 1', 'Take-Any #1 Item 1', 'Take-Any #1 Item 2', 'Take-Any #2 Item 1',
        'Take-Any #2 Item 2', 'Take-Any #3 Item 1', 'Take-Any #3 Item 2','Take-Any #4 Item 1', 'Take-Any #4 Item 2'
    ]
}

vanilla_fallback_dungeon_set = set(mode_grouping['Dungeon Trash'] + mode_grouping['Big Keys'] +
                                   mode_grouping['GT Trash'] + mode_grouping['Small Keys'] +
                                   mode_grouping['Compasses'] + mode_grouping['Maps'] + mode_grouping['Key Drops'] +
                                   mode_grouping['Big Key Drops'])


major_items = {'Bombos', 'Book of Mudora', 'Cane of Somaria', 'Ether', 'Fire Rod', 'Flippers', 'Ocarina', 'Hammer',
               'Hookshot', 'Ice Rod', 'Lamp', 'Cape', 'Magic Powder', 'Mushroom', 'Pegasus Boots', 'Quake', 'Shovel',
               'Bug Catching Net', 'Cane of Byrna', 'Blue Boomerang', 'Red Boomerang', 'Progressive Glove',
               'Power Glove', 'Titans Mitts', 'Bottle', 'Bottle (Red Potion)', 'Bottle (Green Potion)', 'Magic Mirror',
               'Bottle (Blue Potion)', 'Bottle (Fairy)', 'Bottle (Bee)', 'Bottle (Good Bee)', 'Magic Upgrade (1/2)',
               'Sanctuary Heart Container', 'Boss Heart Container', 'Progressive Shield', 'Ocarina (Activated)',
               'Mirror Shield', 'Progressive Armor', 'Blue Mail', 'Red Mail', 'Progressive Sword', 'Fighter Sword',
               'Master Sword', 'Tempered Sword', 'Golden Sword', 'Bow', 'Silver Arrows', 'Triforce Piece', 'Moon Pearl',
               'Progressive Bow', 'Progressive Bow (Alt)'}

vanilla_swords = {"Link's Uncle", 'Master Sword Pedestal', 'Blacksmith', 'Pyramid Fairy - Left'}

trash_items = {
    'Nothing': -1,
    'Bee Trap': 0,
    'Rupee (1)': 1, 'Rupees (5)': 1, 'Small Heart': 1, 'Bee': 1, 'Arrows (5)': 1, 'Chicken': 1,  'Single Bomb': 1,
    'Rupees (20)': 2,  'Small Magic': 2,
    'Bombs (3)': 3, 'Arrows (10)': 3, 'Bombs (10)': 3,
    'Big Magic': 4, 'Red Potion': 4, 'Blue Shield': 4, 'Rupees (50)': 4, 'Rupees (100)': 4,
    'Rupees (300)': 5,
    'Piece of Heart': 17
}

pot_items = {
    PotItem.Nothing: 'Nothing',
    PotItem.Bomb: 'Single Bomb',
    PotItem.FiveArrows: 'Arrows (5)',  # convert to 10
    PotItem.OneRupee: 'Rupee (1)',
    PotItem.FiveRupees: 'Rupees (5)',
    PotItem.Heart: 'Small Heart',
    PotItem.BigMagic: 'Big Magic',  # fast fill
    PotItem.SmallMagic: 'Small Magic',
    PotItem.Chicken: 'Chicken'   # fast fill
}

valid_pot_items = {y: x for x, y in pot_items.items()}


if __name__ == '__main__':
    import yaml
    from yaml.representer import Representer
    advanced_placements = {'advanced_placements': {}}
    player_map = advanced_placements['advanced_placements']
    placement_list = []
    player_map[1] = placement_list
    for item, location_list in vanilla_mapping.items():
        for location in location_list:
            placement = {}
            placement['type'] = 'LocationGroup'
            placement['item'] = item
            locations = placement['locations'] = []
            locations.append(location)
            locations.append('Random')
            placement_list.append(placement)
    yaml.add_representer(defaultdict, Representer.represent_dict)
    with open('fillgen.yaml', 'w') as file:
        yaml.dump(advanced_placements, file)


