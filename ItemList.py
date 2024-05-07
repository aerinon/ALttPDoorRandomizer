from collections import namedtuple, defaultdict
import logging
import math
import RaceRandom as random

from BaseClasses import Region, RegionType, Shop, ShopType, Location, CollectionState, PotItem
from EntranceShuffle import connect_entrance
from Regions import shop_to_location_table, retro_shops, shop_table_by_location, valid_pot_location
from Fill import FillError, fill_restrictive, get_dungeon_item_pool, track_dungeon_items, track_outside_keys
from PotShuffle import vanilla_pots
from Items import ItemFactory

from source.dungeon.EnemyList import add_drop_contents
from source.item.FillUtil import trash_items, pot_items

import source.classes.constants as CONST


#This file sets the item pools for various modes. Timed modes and triforce hunt are enforced first, and then extra items are specified per mode to fill in the remaining space.
#Some basic items that various modes require are placed here, including pendants and crystals. Medallion requirements for the two relevant entrances are also decided.

alwaysitems = ['Bombos', 'Book of Mudora', 'Cane of Somaria', 'Ether', 'Fire Rod', 'Flippers', 'Ocarina', 'Hammer', 'Hookshot', 'Ice Rod', 'Lamp',
               'Cape', 'Magic Powder', 'Mushroom', 'Pegasus Boots', 'Quake', 'Shovel', 'Bug Catching Net', 'Cane of Byrna', 'Blue Boomerang', 'Red Boomerang']
progressivegloves = ['Progressive Glove'] * 2
basicgloves = ['Power Glove', 'Titans Mitts']

normalbottles = ['Bottle', 'Bottle (Red Potion)', 'Bottle (Green Potion)', 'Bottle (Blue Potion)', 'Bottle (Fairy)', 'Bottle (Bee)', 'Bottle (Good Bee)']
hardbottles = ['Bottle', 'Bottle (Red Potion)', 'Bottle (Green Potion)', 'Bottle (Blue Potion)', 'Bottle (Bee)', 'Bottle (Good Bee)']

normalbaseitems = (['Magic Upgrade (1/2)', 'Single Arrow', 'Sanctuary Heart Container', 'Arrows (10)', 'Bombs (10)'] +
                   ['Rupees (300)'] * 4 + ['Boss Heart Container'] * 10 + ['Piece of Heart'] * 24)
normalfirst15extra = ['Rupees (100)', 'Rupees (300)', 'Rupees (50)'] + ['Arrows (10)'] * 6 + ['Bombs (3)'] * 6
normalsecond15extra = ['Bombs (3)'] * 10 + ['Rupees (50)'] * 2 + ['Arrows (10)'] * 2 + ['Rupee (1)']
normalthird10extra = ['Rupees (50)'] * 4 + ['Rupees (20)'] * 3 + ['Arrows (10)', 'Rupee (1)', 'Rupees (5)']
normalfourth5extra = ['Arrows (10)'] * 2 + ['Rupees (20)'] * 2 + ['Rupees (5)']
normalfinal25extra = ['Rupees (20)'] * 23 + ['Rupees (5)'] * 2

Difficulty = namedtuple('Difficulty',
                        ['baseitems', 'bottles', 'bottle_count', 'same_bottle', 'progressiveshield',
                         'basicshield', 'progressivearmor', 'basicarmor', 'swordless',
                         'progressivesword', 'basicsword', 'basicbow', 'timedohko', 'timedother',
                         'retro', 'bombbag',
                         'extras', 'progressive_sword_limit', 'progressive_shield_limit',
                         'progressive_armor_limit', 'progressive_bottle_limit',
                         'progressive_bow_limit', 'heart_piece_limit', 'boss_heart_container_limit'])

total_items_to_place = 153
max_goal = 850

difficulties = {
    'normal': Difficulty(
        baseitems = normalbaseitems,
        bottles = normalbottles,
        bottle_count = 4,
        same_bottle = False,
        progressiveshield = ['Progressive Shield'] * 3,
        basicshield = ['Blue Shield', 'Red Shield', 'Mirror Shield'],
        progressivearmor = ['Progressive Armor'] * 2,
        basicarmor = ['Blue Mail', 'Red Mail'],
        swordless = ['Rupees (20)'] * 4,
        progressivesword = ['Progressive Sword'] * 4,
        basicsword = ['Fighter Sword', 'Master Sword', 'Tempered Sword', 'Golden Sword'],
        basicbow = ['Bow', 'Silver Arrows'],
        timedohko = ['Green Clock'] * 25,
        timedother = ['Green Clock'] * 20 + ['Blue Clock'] * 10 + ['Red Clock'] * 10,
        retro = ['Small Key (Universal)'] * 18 + ['Rupees (20)'] * 10,
        bombbag = ['Bomb Upgrade (+10)'] * 2,
        extras = [normalfirst15extra, normalsecond15extra, normalthird10extra, normalfourth5extra, normalfinal25extra],
        progressive_sword_limit = 4,
        progressive_shield_limit = 3,
        progressive_armor_limit = 2,
        progressive_bow_limit = 2,
        progressive_bottle_limit = 4,
        boss_heart_container_limit = 255,
        heart_piece_limit = 255,
    ),
    'hard': Difficulty(
        baseitems = normalbaseitems,
        bottles = hardbottles,
        bottle_count = 4,
        same_bottle = False,
        progressiveshield = ['Progressive Shield'] * 3,
        basicshield = ['Blue Shield', 'Red Shield', 'Red Shield'],
        progressivearmor = ['Progressive Armor'] * 2,
        basicarmor = ['Progressive Armor'] * 2, # neither will count
        swordless =  ['Rupees (20)'] * 4,
        progressivesword =  ['Progressive Sword'] * 4,
        basicsword = ['Fighter Sword', 'Master Sword', 'Master Sword', 'Tempered Sword'],
        basicbow = ['Bow'] * 2,
        timedohko = ['Green Clock'] * 25,
        timedother = ['Green Clock'] * 20 + ['Blue Clock'] * 10 + ['Red Clock'] * 10,
        retro = ['Small Key (Universal)'] * 13 + ['Rupees (5)'] * 15,
        bombbag = ['Bomb Upgrade (+10)'] * 2,
        extras = [normalfirst15extra, normalsecond15extra, normalthird10extra, normalfourth5extra, normalfinal25extra],
        progressive_sword_limit = 3,
        progressive_shield_limit = 2,
        progressive_armor_limit = 0,
        progressive_bow_limit = 1,
        progressive_bottle_limit = 4,
        boss_heart_container_limit = 6,
        heart_piece_limit = 16,
    ),
    'expert': Difficulty(
        baseitems = normalbaseitems,
        bottles = hardbottles,
        bottle_count = 4,
        same_bottle = False,
        progressiveshield = ['Progressive Shield'] * 3,
        basicshield = ['Progressive Shield'] * 3,  #only the first one will upgrade, making this equivalent to two blue shields
        progressivearmor = ['Progressive Armor'] * 2, # neither will count
        basicarmor = ['Progressive Armor'] * 2, # neither will count
        swordless = ['Rupees (20)'] * 4,
        progressivesword = ['Progressive Sword'] * 4,
        basicsword = ['Fighter Sword', 'Fighter Sword', 'Master Sword', 'Master Sword'],
        basicbow = ['Bow'] * 2,
        timedohko = ['Green Clock'] * 20 + ['Red Clock'] * 5,
        timedother = ['Green Clock'] * 20 + ['Blue Clock'] * 10 + ['Red Clock'] * 10,
        retro = ['Small Key (Universal)'] * 13 + ['Rupees (5)'] * 15,
        bombbag = ['Bomb Upgrade (+10)'] * 2,
        extras = [normalfirst15extra, normalsecond15extra, normalthird10extra, normalfourth5extra, normalfinal25extra],
        progressive_sword_limit = 2,
        progressive_shield_limit = 1,
        progressive_armor_limit = 0,
        progressive_bow_limit = 1,
        progressive_bottle_limit = 4,
        boss_heart_container_limit = 2,
        heart_piece_limit = 8,
    ),
}

# Translate between Mike's label array and YAML/JSON keys
def get_custom_array_key(item):
  label_switcher = {
    "silverarrow": "silversupgrade",
    "blueboomerang": "boomerang",
    "redboomerang": "redmerang",
    "ocarina": "flute",
    "bugcatchingnet": "bugnet",
    "bookofmudora": "book",
    "pegasusboots": "boots",
    "titansmitts": "titansmitt",
    "pieceofheart": "heartpiece",
    "bossheartcontainer": "heartcontainer",
    "sanctuaryheartcontainer": "sancheart",
    "mastersword": "sword2",
    "temperedsword": "sword3",
    "goldensword": "sword4",
    "blueshield": "shield1",
    "redshield": "shield2",
    "mirrorshield": "shield3",
    "bluemail": "mail2",
    "redmail": "mail3",
    "progressivearmor": "progressivemail",
    "splus12": "halfmagic",
    "splus14": "quartermagic",
    "singlearrow": "arrow1",
    "singlebomb": "bomb1",
    "triforcepiece": "triforcepieces"
  }
  key = item.lower()
  trans = {
    " ": "",
    '(': "",
    '/': "",
    ')': "",
    '+': "",
    "magic": "",
    "caneof": "",
    "upgrade": "splus",
    "arrows": "arrow",
    "arrowplus": "arrowsplus",
    "bombs": "bomb",
    "bombplus": "bombsplus",
    "rupees": "rupee"
  }
  for check in trans:
      repl = trans[check]
      key = key.replace(check,repl)
  if key in label_switcher:
      key = label_switcher.get(key)
  return key


def generate_itempool(world, player):
    if (world.difficulty[player] not in ['normal', 'hard', 'expert']
       or world.goal[player] not in ['ganon', 'pedestal', 'dungeons', 'triforcehunt', 'trinity', 'crystals',
                                     'ganonhunt', 'completionist']
       or world.mode[player] not in ['open', 'standard', 'inverted']
       or world.timer not in ['none', 'display', 'timed', 'timed-ohko', 'ohko', 'timed-countdown']
       or world.progressive not in ['on', 'off', 'random']):
        raise NotImplementedError('Not supported yet')

    if world.timer in ['ohko', 'timed-ohko']:
        world.can_take_damage = False

    if world.goal[player] in ['pedestal', 'triforcehunt']:
        world.push_item(world.get_location('Ganon', player), ItemFactory('Nothing', player), False)
    else:
        world.push_item(world.get_location('Ganon', player), ItemFactory('Triforce', player), False)

    if world.goal[player] in ['triforcehunt', 'trinity']:
        region = world.get_region('Hyrule Castle Courtyard', player)
        loc = Location(player, "Murahdahla", parent=region)
        region.locations.append(loc)
        world.dynamic_locations.append(loc)

        world.clear_location_cache()

        world.push_item(loc, ItemFactory('Triforce', player), False)
        loc.event = True
        loc.locked = True
        loc.forced_item = loc.item

    world.get_location('Ganon', player).event = True
    world.get_location('Ganon', player).locked = True
    world.push_item(world.get_location('Agahnim 1', player), ItemFactory('Beat Agahnim 1', player), False)
    world.get_location('Agahnim 1', player).event = True
    world.get_location('Agahnim 1', player).locked = True
    world.push_item(world.get_location('Agahnim 2', player), ItemFactory('Beat Agahnim 2', player), False)
    world.get_location('Agahnim 2', player).event = True
    world.get_location('Agahnim 2', player).locked = True
    world.push_item(world.get_location('Dark Blacksmith Ruins', player), ItemFactory('Pick Up Purple Chest', player), False)
    world.get_location('Dark Blacksmith Ruins', player).event = True
    world.get_location('Dark Blacksmith Ruins', player).locked = True
    world.push_item(world.get_location('Frog', player), ItemFactory('Get Frog', player), False)
    world.get_location('Frog', player).event = True
    world.get_location('Frog', player).locked = True
    world.push_item(world.get_location('Missing Smith', player), ItemFactory('Return Smith', player), False)
    world.get_location('Missing Smith', player).event = True
    world.get_location('Missing Smith', player).locked = True
    world.push_item(world.get_location('Floodgate', player), ItemFactory('Open Floodgate', player), False)
    world.get_location('Floodgate', player).event = True
    world.get_location('Floodgate', player).locked = True
    world.push_item(world.get_location('Trench 1 Switch', player), ItemFactory('Trench 1 Filled', player), False)
    world.get_location('Trench 1 Switch', player).event = True
    world.get_location('Trench 1 Switch', player).locked = True
    world.push_item(world.get_location('Trench 2 Switch', player), ItemFactory('Trench 2 Filled', player), False)
    world.get_location('Trench 2 Switch', player).event = True
    world.get_location('Trench 2 Switch', player).locked = True
    world.push_item(world.get_location('Swamp Drain', player), ItemFactory('Drained Swamp', player), False)
    world.get_location('Swamp Drain', player).event = True
    world.get_location('Swamp Drain', player).locked = True
    world.push_item(world.get_location('Attic Cracked Floor', player), ItemFactory('Shining Light', player), False)
    world.get_location('Attic Cracked Floor', player).event = True
    world.get_location('Attic Cracked Floor', player).locked = True
    world.push_item(world.get_location('Suspicious Maiden', player), ItemFactory('Maiden Rescued', player), False)
    world.get_location('Suspicious Maiden', player).event = True
    world.get_location('Suspicious Maiden', player).locked = True
    world.push_item(world.get_location('Revealing Light', player), ItemFactory('Maiden Unmasked', player), False)
    world.get_location('Revealing Light', player).event = True
    world.get_location('Revealing Light', player).locked = True
    world.push_item(world.get_location('Ice Block Drop', player), ItemFactory('Convenient Block', player), False)
    world.get_location('Ice Block Drop', player).event = True
    world.get_location('Ice Block Drop', player).locked = True
    world.push_item(world.get_location('Skull Star Tile', player), ItemFactory('Hidden Pits', player), False)
    world.get_location('Skull Star Tile', player).event = True
    world.get_location('Skull Star Tile', player).locked = True
    if world.mode[player] == 'standard':
        world.push_item(world.get_location('Zelda Pickup', player), ItemFactory('Zelda Herself', player), False)
        world.get_location('Zelda Pickup', player).event = True
        world.get_location('Zelda Pickup', player).locked = True
        world.push_item(world.get_location('Zelda Drop Off', player), ItemFactory('Zelda Delivered', player), False)
        world.get_location('Zelda Drop Off', player).event = True
        world.get_location('Zelda Drop Off', player).locked = True

    # set up item pool
    skip_pool_adjustments = False
    if world.customizer and world.customizer.get_item_pool() and player in world.customizer.get_item_pool():
        (pool, placed_items, precollected_items, clock_mode, lamps_needed_for_dark_rooms) = make_customizer_pool(world, player)
        skip_pool_adjustments = True
    elif world.custom:
        (pool, placed_items, precollected_items, clock_mode, treasure_hunt_count, treasure_hunt_icon, lamps_needed_for_dark_rooms) = make_custom_item_pool(world, player, world.progressive, world.shuffle[player], world.difficulty[player], world.timer, world.goal[player], world.mode[player], world.swords[player], world.bombbag[player], world.customitemarray)
        world.rupoor_cost = min(world.customitemarray[player]["rupoorcost"], 9999)
    else:
        (pool, placed_items, precollected_items, clock_mode, lamps_needed_for_dark_rooms) = get_pool_core(world, player, world.progressive, world.shuffle[player], world.difficulty[player], world.treasure_hunt_total[player], world.timer, world.goal[player], world.mode[player], world.swords[player], world.bombbag[player], world.doorShuffle[player], world.logic[player], world.flute_mode[player] == 'active')

    if player in world.pool_adjustment.keys() and not skip_pool_adjustments:
        amt = world.pool_adjustment[player]
        if amt < 0:
            trash_options = [x for x in pool if x in trash_items]
            random.shuffle(trash_options)
            trash_options = sorted(trash_options, key=lambda x: trash_items[x], reverse=True)
            while amt > 0 and len(trash_options) > 0:
                pool.remove(trash_options.pop())
                amt -= 1
        elif amt > 0:
            for _ in range(0, amt):
                pool.append('Rupees (20)')

    if world.logic[player] == 'hybridglitches' and world.pottery[player] not in ['none', 'cave']:
        # In HMG force swamp smalls in pots to allow getting out of swamp palace
        placed_items['Swamp Palace - Trench 1 Pot Key'] = 'Small Key (Swamp Palace)'
        placed_items['Swamp Palace - Pot Row Pot Key'] = 'Small Key (Swamp Palace)'
        pool.remove('Small Key (Swamp Palace)')
        pool.remove('Small Key (Swamp Palace)')

    start_inventory = list(world.precollected_items)
    for item in precollected_items:
        world.push_precollected(ItemFactory(item, player))

    if world.mode[player] == 'standard' and not world.state.has_blunt_weapon(player):
        if "Link's Uncle" not in placed_items:
            found_sword = False
            found_bow = False
            possible_weapons = []
            for item in pool:
                if item in ['Progressive Sword', 'Fighter Sword', 'Master Sword', 'Tempered Sword', 'Golden Sword']:
                    if not found_sword and world.swords[player] != 'swordless':
                        found_sword = True
                        possible_weapons.append(item)
                if world.algorithm == 'vanilla_fill':  # skip other possibilities
                    continue
                if (item in ['Progressive Bow', 'Bow'] and not found_bow
                   and not world.bow_mode[player].startswith('retro')):
                    found_bow = True
                    possible_weapons.append(item)
                if item in ['Hammer', 'Fire Rod', 'Cane of Somaria', 'Cane of Byrna']:
                    if item not in possible_weapons:
                        possible_weapons.append(item)
                if not world.bombbag[player] and item in ['Bombs (10)']:
                    if item not in possible_weapons and world.doorShuffle[player] != 'crossed':
                        possible_weapons.append(item)
            starting_weapon = random.choice(possible_weapons)
            placed_items["Link's Uncle"] = starting_weapon
            pool.remove(starting_weapon)
        if placed_items["Link's Uncle"] in ['Bow', 'Progressive Bow', 'Bombs (10)', 'Cane of Somaria', 'Cane of Byrna'] and world.enemy_health[player] not in ['default', 'easy']:
            world.escape_assist[player].append('bombs')

    for (location, item) in placed_items.items():
        world.push_item(world.get_location(location, player), ItemFactory(item, player), False)
        world.get_location(location, player).event = True
        world.get_location(location, player).locked = True

    if world.shopsanity[player] and not skip_pool_adjustments:
        for shop in world.shops[player]:
            if shop.region.name in shop_to_location_table:
                for index, slot in enumerate(shop.inventory):
                    if slot:
                        item = slot['item']
                        if shop.region.name == 'Capacity Upgrade' and world.difficulty[player] != 'normal':
                            pool.append('Rupees (20)')
                        else:
                            pool.append(item)

    items = ItemFactory(pool, player)
    if world.shopsanity[player]:
        for potion in ['Green Potion', 'Blue Potion', 'Red Potion']:
            p_item = next(item for item in items if item.name == potion and item.player == player)
            p_item.priority = True  # don't beemize one of each potion

    if world.bombbag[player]:
        for item in items:
            if item.name == 'Bomb Upgrade (+10)' and item.player == player:
                item.advancement = True

    world.lamps_needed_for_dark_rooms = lamps_needed_for_dark_rooms

    if clock_mode is not None:
        world.clock_mode = clock_mode

    goal = world.goal[player]
    if goal in ['triforcehunt', 'trinity', 'ganonhunt']:
        g, t = set_default_triforce(goal, world.treasure_hunt_count[player], world.treasure_hunt_total[player])
        world.treasure_hunt_count[player], world.treasure_hunt_total[player] = g, t
        world.treasure_hunt_icon[player] = 'Triforce Piece'

    world.itempool.extend([item for item in get_dungeon_item_pool(world) if item.player == player
                           and ((item.smallkey and world.keyshuffle[player] != 'none')
                                or (item.bigkey and world.bigkeyshuffle[player])
                                or (item.map and world.mapshuffle[player])
                                or (item.compass and world.compassshuffle[player]))])

    # logic has some branches where having 4 hearts is one possible requirement (of several alternatives)
    # rather than making all hearts/heart pieces progression items (which slows down generation considerably)
    # We mark one random heart container as an advancement item (or 4 heart pieces in expert mode)
    if world.difficulty[player] in ['normal', 'hard'] and not (world.custom and world.customitemarray[player]["heartcontainer"] == 0):
        container = next((item for item in items if item.name == 'Boss Heart Container'), None)
        if container:
            container.advancement = True
    elif world.difficulty[player] in ['expert'] and not (world.custom and world.customitemarray[player]["heartpiece"] < 4):
        adv_heart_pieces = (item for item in items if item.name == 'Piece of Heart')
        for i in range(4):
            next(adv_heart_pieces).advancement = True

    world.itempool += items

    # shuffle medallions
    mm_medallion, tr_medallion = None, None
    if world.customizer and world.customizer.get_medallions() and player in world.customizer.get_medallions():
        medal_map = world.customizer.get_medallions()
        if player in medal_map:
            custom_medallions = medal_map[player]
            if 'Misery Mire' in custom_medallions:
                mm_medallion = custom_medallions['Misery Mire']
                if isinstance(mm_medallion, dict):
                    mm_medallion = random.choices(list(mm_medallion.keys()), list(mm_medallion.values()), k=1)[0]
                if mm_medallion == 'Random':
                    mm_medallion = None
            if 'Turtle Rock' in custom_medallions:
                tr_medallion = custom_medallions['Turtle Rock']
                if isinstance(tr_medallion, dict):
                    tr_medallion = random.choices(list(tr_medallion.keys()), list(tr_medallion.values()), k=1)[0]
                if tr_medallion == 'Random':
                    tr_medallion = None
    if not mm_medallion:
        if world.algorithm == 'vanilla_fill':
            mm_medallion = 'Ether'
        else:
            mm_medallion = ['Ether', 'Quake', 'Bombos'][random.randint(0, 2)]
    if not tr_medallion:
        if world.algorithm == 'vanilla_fill':
            tr_medallion = 'Quake'
        else:
            tr_medallion = ['Ether', 'Quake', 'Bombos'][random.randint(0, 2)]
    world.required_medallions[player] = (mm_medallion, tr_medallion)

    # shuffle bottle refills
    if world.difficulty[player] in ['hard', 'expert']:
        waterfall_bottle = hardbottles[random.randint(0, 5)]
        pyramid_bottle = hardbottles[random.randint(0, 5)]
    else:
        waterfall_bottle = normalbottles[random.randint(0, 6)]
        pyramid_bottle = normalbottles[random.randint(0, 6)]
    world.bottle_refills[player] = (waterfall_bottle, pyramid_bottle)

    set_up_shops(world, player)

    if world.take_any[player] != 'none':
        set_up_take_anys(world, player, skip_pool_adjustments)
    if world.keyshuffle[player] == 'universal':
        if world.dropshuffle[player] != 'none' and not skip_pool_adjustments:
            world.itempool += [ItemFactory('Small Key (Universal)', player)] * 13
        if world.pottery[player] not in ['none', 'cave'] and not skip_pool_adjustments:
            world.itempool += [ItemFactory('Small Key (Universal)', player)] * 19

    create_dynamic_shop_locations(world, player)

    if world.pottery[player] not in ['none', 'keys'] and not skip_pool_adjustments:
        add_pot_contents(world, player)

    if world.dropshuffle[player] == 'underworld' and not skip_pool_adjustments:
        add_drop_contents(world, player)

    # modfiy based on start inventory, if any
    modify_pool_for_start_inventory(start_inventory, world, player)

    beeweights = {'0': {None: 100},
                  '1': {None: 75, 'trap': 25},
                  '2': {None: 40, 'trap': 40, 'bee': 20},
                  '3': {'trap': 50, 'bee': 50},
                  '4': {'trap': 100}}
    def beemizer(item):
        if world.beemizer[item.player] and not item.advancement and not item.priority and not item.type:
            choice = random.choices(list(beeweights[world.beemizer[item.player]].keys()), weights=list(beeweights[world.beemizer[item.player]].values()))[0]
            return item if not choice else ItemFactory("Bee Trap", player) if choice == 'trap' else ItemFactory("Bee", player)
        return item

    if not skip_pool_adjustments:
        world.itempool = [beemizer(item) for item in world.itempool]

    # increase pool if not enough items
    ttl_locations = sum(1 for x in world.get_unfilled_locations(player) if '- Prize' not in x.name)
    pool_size = count_player_dungeon_item_pool(world, player)
    pool_size += sum(1 for x in world.itempool if x.player == player)

    if pool_size < ttl_locations:
        retro_bow = world.bow_mode[player].startswith('retro')
        amount_to_add = ttl_locations - pool_size
        filler_additions = random.choices(list(filler_items.keys()), filler_items.values(), k=amount_to_add)
        for item in filler_additions:
            item_name = 'Rupees (5)' if retro_bow and item == 'Arrows (10)' else item
            world.itempool.append(ItemFactory(item_name, player))




take_any_locations = [
    'Snitch Lady (East)', 'Snitch Lady (West)', 'Bush Covered House', 'Light World Bomb Hut',
    'Fortune Teller (Light)', 'Lake Hylia Fortune Teller', 'Lumberjack House', 'Bonk Fairy (Light)',
    'Bonk Fairy (Dark)', 'Lake Hylia Healer Fairy', 'Light Hype Fairy', 'Desert Healer Fairy',
    'Dark Lake Hylia Healer Fairy', 'Dark Lake Hylia Ledge Healer Fairy', 'Mire Healer Fairy',
    'Dark Death Mountain Healer Fairy', 'Long Fairy Cave', 'Good Bee Cave', '20 Rupee Cave',
    'Kakariko Gamble Game', '50 Rupee Cave', 'Lost Woods Gamble', 'Hookshot Fairy',
    'Palace of Darkness Hint', 'East Dark World Hint', 'Archery Game', 'Dark Lake Hylia Ledge Hint',
    'Dark Lake Hylia Ledge Spike Cave', 'Fortune Teller (Dark)', 'Dark Sanctuary Hint', 'Mire Hint']

fixed_take_anys = [
    'Desert Healer Fairy', 'Light Hype Fairy', 'Dark Death Mountain Healer Fairy',
    'Dark Lake Hylia Ledge Healer Fairy', 'Bonk Fairy (Dark)']


def set_up_take_anys(world, player, skip_adjustments=False):
    if world.mode[player] == 'inverted':
        if 'Dark Sanctuary Hint' in take_any_locations:
            take_any_locations.remove('Dark Sanctuary Hint')
        if 'Archery Game' in take_any_locations:
            take_any_locations.remove('Archery Game')

    if world.take_any[player] == 'random':
        take_any_candidates = [x for x in take_any_locations if len(world.get_region(x, player).locations) == 0]
        regions = random.sample(take_any_candidates, 5)
    elif world.take_any[player] == 'fixed':
        regions = list(fixed_take_anys)
        random.shuffle(regions)

    old_man_take_any = Region("Old Man Sword Cave", RegionType.Cave, 'the sword cave', player)
    world.regions.append(old_man_take_any)
    world.dynamic_regions.append(old_man_take_any)

    reg = regions.pop()
    entrance = world.get_region(reg, player).entrances[0]
    connect_entrance(world, entrance, old_man_take_any, player)
    entrance.target = 0x58
    old_man_take_any.shop = Shop(old_man_take_any, 0x0112, ShopType.TakeAny, 0xE2, True, not world.shopsanity[player], 32)
    world.shops[player].append(old_man_take_any.shop)

    sword = next((item for item in world.itempool if item.type == 'Sword' and item.player == player), None)
    if sword:
        if not skip_adjustments:
            world.itempool.append(ItemFactory('Rupees (20)', player))
            if not world.shopsanity[player]:
                world.itempool.remove(sword)
        old_man_take_any.shop.add_inventory(0, sword.name, 0, 0, create_location=True)
    else:
        if world.shopsanity[player] and not skip_adjustments:
            world.itempool.append(ItemFactory('Rupees (300)', player))
        old_man_take_any.shop.add_inventory(0, 'Rupees (300)', 0, 0, create_location=True)

    take_any_type = ShopType.Shop if world.shopsanity[player] else ShopType.TakeAny
    for num in range(4):
        take_any = Region("Take-Any #{}".format(num+1), RegionType.Cave, 'a cave of choice', player)
        world.regions.append(take_any)
        world.dynamic_regions.append(take_any)
        target, room_id = random.choice([(0x58, 0x0112), (0x60, 0x010F), (0x46, 0x011F)])
        reg = regions.pop()
        entrance = next((ent for ent in world.get_region(reg, player).entrances if ent.parent_region.is_outdoors()), None)
        if entrance is None:
            raise Exception(f'No outside entrance found for {reg}')
        connect_entrance(world, entrance, take_any, player)
        entrance.target = target
        take_any.shop = Shop(take_any, room_id, take_any_type, 0xE3, True, not world.shopsanity[player], 33 + num*2)
        world.shops[player].append(take_any.shop)
        take_any.shop.add_inventory(0, 'Blue Potion', 0, 0, create_location=world.shopsanity[player])
        take_any.shop.add_inventory(1, 'Boss Heart Container', 0, 0, create_location=True)
        if world.shopsanity[player] and not skip_adjustments:
            world.itempool.append(ItemFactory('Blue Potion', player))
            world.itempool.append(ItemFactory('Boss Heart Container', player))

    world.initialize_regions()


def create_dynamic_shop_locations(world, player):
    for shop in world.shops[player]:
        if shop.region.player == player:
            for i, item in enumerate(shop.inventory):
                if item is None:
                    continue
                if item['create_location']:
                    slot_name = "{} Item {}".format(shop.region.name, i+1)
                    address = shop_table_by_location[slot_name] if world.shopsanity[player] else None
                    loc = Location(player, slot_name, address=address,
                                   parent=shop.region, hint_text='in an old-fashioned cave')
                    shop.region.locations.append(loc)
                    world.dynamic_locations.append(loc)

                    world.clear_location_cache()

                    if not world.shopsanity[player]:
                        world.push_item(loc, ItemFactory(item['item'], player), False)
                        loc.event = True
                        loc.locked = True


def fill_prizes(world, attempts=15):
    all_state = world.get_all_state(keys=True)
    for player in range(1, world.players + 1):
        crystals = ItemFactory(['Red Pendant', 'Blue Pendant', 'Green Pendant', 'Crystal 1', 'Crystal 2', 'Crystal 3', 'Crystal 4', 'Crystal 7', 'Crystal 5', 'Crystal 6'], player)
        crystal_locations = [world.get_location('Turtle Rock - Prize', player), world.get_location('Eastern Palace - Prize', player), world.get_location('Desert Palace - Prize', player), world.get_location('Tower of Hera - Prize', player), world.get_location('Palace of Darkness - Prize', player),
                             world.get_location('Thieves\' Town - Prize', player), world.get_location('Skull Woods - Prize', player), world.get_location('Swamp Palace - Prize', player), world.get_location('Ice Palace - Prize', player),
                             world.get_location('Misery Mire - Prize', player)]
        placed_prizes = [loc.item.name for loc in crystal_locations if loc.item is not None]
        unplaced_prizes = [crystal for crystal in crystals if crystal.name not in placed_prizes]
        empty_crystal_locations = [loc for loc in crystal_locations if loc.item is None]

        for attempt in range(attempts):
            try:
                prizepool = list(unplaced_prizes)
                prize_locs = list(empty_crystal_locations)
                random.shuffle(prizepool)
                random.shuffle(prize_locs)
                fill_restrictive(world, all_state, prize_locs, prizepool, single_player_placement=True)
            except FillError as e:
                logging.getLogger('').info("Failed to place dungeon prizes (%s). Will retry %s more times", e, attempts - attempt - 1)
                for location in empty_crystal_locations:
                    location.item = None
                continue
            break
        else:
            raise FillError(f'Unable to place dungeon prizes {", ".join(list(map(lambda d: d.hint_text, prize_locs)))}')


def set_up_shops(world, player):
    retro_bow = world.bow_mode[player].startswith('retro')
    universal_keys = world.keyshuffle[player] == 'universal'
    if retro_bow or universal_keys:
        if world.shopsanity[player]:
            removals = []
            if retro_bow:
                removals = [next(item for item in world.itempool if item.name == 'Arrows (10)' and item.player == player)]
                removals.extend([item for item in world.itempool if item.name == 'Arrow Upgrade (+5)' and item.player == player])
                shields_n_hearts = [item for item in world.itempool if item.name in ['Blue Shield', 'Small Heart'] and item.player == player]
                removals.extend(random.sample(shields_n_hearts, 5))
            if universal_keys:
                red_pots = [item for item in world.itempool if item.name == 'Red Potion' and item.player == player][:5]
                removals.extend(red_pots)
            for remove in removals:
                world.itempool.remove(remove)
            if retro_bow:
                for i in range(6):  # replace the Arrows (10) and randomly selected hearts/blue shield
                    arrow_item = ItemFactory('Single Arrow', player)
                    arrow_item.advancement = True
                    world.itempool.append(arrow_item)
                world.itempool.append(ItemFactory('Rupees (50)', player))  # replaces the arrow upgrade
            if universal_keys:
                for i in range(5):  # replace the red potions
                    world.itempool.append(ItemFactory('Small Key (Universal)', player))
        # TODO: move hard+ mode changes for shields here, utilizing the new shops
        else:
            if retro_bow:
                rss = world.get_region('Red Shield Shop', player).shop
                if not rss.locked:
                    rss.custom = True
                    rss.add_inventory(2, 'Single Arrow', 80)
                rss.locked = True
                cap_shop = world.get_region('Capacity Upgrade', player).shop
                cap_shop.inventory[1] = None  # remove arrow capacity upgrades in retro
            for shop in random.sample([s for s in world.shops[player] if not s.locked and s.region.player == player], 5):
                shop.custom = True
                shop.locked = True
                if retro_bow:
                    shop.add_inventory(0, 'Single Arrow', 80)
                if universal_keys:
                    shop.add_inventory(1, 'Small Key (Universal)', 100)
    if world.bombbag[player]:
        if world.shopsanity[player]:
            removals = [item for item in world.itempool if item.name == 'Bomb Upgrade (+5)' and item.player == player]
            for remove in removals:
                world.itempool.remove(remove)
            world.itempool.append(ItemFactory('Rupees (50)', player))  # replace the bomb upgrade
        else:
            cap_shop = world.get_region('Capacity Upgrade', player).shop
            cap_shop.inventory[0] = cap_shop.inventory[1]  # remove bomb capacity upgrades in bombbag
            cap_shop.inventory[1] = None


def customize_shops(world, player):
    retro_bow = world.bow_mode[player].startswith('retro')
    found_bomb_upgrade, found_arrow_upgrade = False, retro_bow
    possible_replacements = []
    shops_to_customize = shop_to_location_table.copy()
    if world.take_any[player] != 'none':
        shops_to_customize.update(retro_shops)
    for shop_name, loc_list in shops_to_customize.items():
        shop = world.get_region(shop_name, player).shop
        shop.custom = True
        shop.clear_inventory()
        for idx, loc in enumerate(loc_list):
            location = world.get_location(loc, player)
            item = location.item
            max_repeat = 1
            if shop_name not in retro_shops:
                if item.name in repeatable_shop_items and item.player == player:
                    max_repeat = 0
                if item.name in ['Bomb Upgrade (+5)', 'Arrow Upgrade (+5)'] and item.player == player:
                    if item.name == 'Bomb Upgrade (+5)':
                        found_bomb_upgrade = True
                    if item.name == 'Arrow Upgrade (+5)':
                        found_arrow_upgrade = True
                    max_repeat = 7
            if shop_name in retro_shops:
                price = 0
            else:
                price = 120 if shop_name == 'Potion Shop' and item.name == 'Red Potion' else item.price
                if retro_bow and item.name == 'Single Arrow':
                    price = 80
            # randomize price
            shop.add_inventory(idx, item.name, randomize_price(price), max_repeat, player=item.player)
            if item.name in cap_replacements and shop_name not in retro_shops and item.player == player:
                possible_replacements.append((shop, idx, location, item))
        # randomize shopkeeper
        if shop_name != 'Capacity Upgrade':
            shopkeeper = random.choice([0xC1, 0xA0, 0xE2, 0xE3])
            shop.shopkeeper_config = shopkeeper
    # handle capacity upgrades - randomly choose a bomb bunch or arrow bunch to become capacity upgrades
    if world.difficulty[player] == 'normal':
        if not found_bomb_upgrade and len(possible_replacements) > 0 and not world.bombbag[player]:
            choices = []
            for shop, idx, loc, item in possible_replacements:
                if item.name in ['Bombs (3)', 'Bombs (10)']:
                    choices.append((shop, idx, loc, item))
            if len(choices) > 0:
                shop, idx, loc, item = random.choice(choices)
                upgrade = ItemFactory('Bomb Upgrade (+5)', player)
                shop.add_inventory(idx, upgrade.name, randomize_price(upgrade.price), 6,
                                   item.name, randomize_price(item.price), player=item.player)
                loc.item = upgrade
                upgrade.location = loc
        if not found_arrow_upgrade and len(possible_replacements) > 0:
            choices = []
            for shop, idx, loc, item in possible_replacements:
                if item.name == 'Arrows (10)' or (item.name == 'Single Arrow' and not retro_bow):
                    choices.append((shop, idx, loc, item))
            if len(choices) > 0:
                shop, idx, loc, item = random.choice(choices)
                upgrade = ItemFactory('Arrow Upgrade (+5)', player)
                shop.add_inventory(idx, upgrade.name, randomize_price(upgrade.price), 6,
                                   item.name, randomize_price(item.price), player=item.player)
                loc.item = upgrade
                upgrade.location = loc
    change_shop_items_to_rupees(world, player, shops_to_customize)
    balance_prices(world, player)
    check_hints(world, player)


def randomize_price(price):
    half_price = price // 2
    max_price = price - half_price
    if max_price % 5 == 0:
        max_price //= 5
        return random.randint(0, max_price) * 5 + half_price
    else:
        if price <= 10:
            return price
        else:
            half_price = int(math.ceil(half_price / 5.0)) * 5
            max_price = price - half_price
            max_price //= 5
            return random.randint(0, max_price) * 5 + half_price


def change_shop_items_to_rupees(world, player, shops):
    locations = world.get_filled_locations(player)
    for location in locations:
        if location.item.name in shop_transfer.keys() and (location.parent_region.name not in shops or location.name == 'Potion Shop'):
            new_item = ItemFactory(shop_transfer[location.item.name], location.item.player)
            location.item = new_item
        if location.parent_region.name == 'Capacity Upgrade' and location.item.name in cap_blacklist:
            new_item = ItemFactory('Rupees (300)', location.item.player)
            location.item = new_item
            shop = world.get_region('Capacity Upgrade', player).shop
            slot = shop_to_location_table['Capacity Upgrade'].index(location.name)
            shop.add_inventory(slot, new_item.name, randomize_price(new_item.price), 1, player=new_item.player)


def balance_prices(world, player):
    available_money = 765   # this base just counts the main rupee rooms. Could up it for houlihan by 225
    needed_money = 830  # this base is the pay for
    for loc in world.get_filled_locations(player):
        if loc.item.name in rupee_chart:
            available_money += rupee_chart[loc.item.name]  # rupee at locations
    shop_locations = []
    for shop, loc_list in shop_to_location_table.items():
        for loc in loc_list:
            loc = world.get_location(loc, player)
            shop_locations.append(loc)
            slot = shop_to_location_table[loc.parent_region.name].index(loc.name)
            needed_money += loc.parent_region.shop.inventory[slot]['price']

    target = available_money - needed_money
    # remove the first set of shops from consideration (or used them for discounting)
    state, done = CollectionState(world), False
    unchecked_locations = world.get_locations().copy()
    while not done:
        state.sweep_for_events(key_only=True, locations=unchecked_locations)
        sphere_loc = [l for l in unchecked_locations if state.can_reach(l) and state.not_flooding_a_key(state.world, l)]
        if any(l in shop_locations for l in sphere_loc):
            if target >= 0:
                shop_locations = [l for l in shop_locations if l not in sphere_loc]
            else:
                shop_locations = [l for l in sphere_loc if l in shop_locations]
            done = True
        else:
            for l in sphere_loc:
                state.collect(l.item, True, l)
                unchecked_locations.remove(l)

    while len(shop_locations) > 0:
        adjustment = target // len(shop_locations)
        adjustment = 5 * (adjustment // 5)
        more_adjustment = []
        for loc in shop_locations:
            slot = shop_to_location_table[loc.parent_region.name].index(loc.name)
            price_max = loc.item.price * 2
            inventory = loc.parent_region.shop.inventory[slot]
            flex = price_max - inventory['price']
            if flex <= adjustment:
                inventory['price'] = price_max
                target -= flex
            elif adjustment <= 0:
                old_price = inventory['price']
                new_price = max(0, inventory['price'] + adjustment)
                inventory['price'] = new_price
                target += (old_price - new_price)
            else:
                more_adjustment.append(loc)
        if len(shop_locations) == len(more_adjustment):
            for loc in shop_locations:
                slot = shop_to_location_table[loc.parent_region.name].index(loc.name)
                inventory = loc.parent_region.shop.inventory[slot]
                new_price = inventory['price'] + adjustment
                new_price = min(500, max(0, new_price))  # cap prices between 0--twice base price
                inventory['price'] = new_price
                target -= adjustment
            more_adjustment = []
        shop_locations = more_adjustment
    logging.getLogger('').debug(f'Price target is off by by {target} rupees')

    # for loc in shop_locations:
    #     slot = shop_to_location_table[loc.parent_region.name].index(loc.name)
    #     new_price = loc.parent_region.shop.inventory[slot]['price'] + adjustment
    #
    #     new_price = min(500, max(0, new_price))  # cap prices between 0--twice base price
    #     loc.parent_region.shop.inventory[slot]['price'] = new_price


def check_hints(world, player):
    if world.shuffle[player] in ['simple', 'restricted', 'full', 'lite', 'lean', 'swapped', 'crossed', 'insanity']:
        for shop, location_list in  shop_to_location_table.items():
            if shop in ['Capacity Upgrade', 'Paradox Shop', 'Potion Shop']:
                continue  # near the queen, near potions, and near 7 chests are fine
            for loc_name in location_list:  # other shops are indistinguishable in ER
                world.get_location(loc_name, player).hint_text = f'for sale'


repeatable_shop_items = ['Single Arrow', 'Arrows (10)', 'Bombs (3)', 'Bombs (10)', 'Red Potion', 'Small Heart',
                         'Blue Shield', 'Red Shield', 'Bee', 'Small Key (Universal)', 'Blue Potion', 'Green Potion']


cap_replacements = ['Single Arrow', 'Arrows (10)', 'Bombs (3)', 'Bombs (10)']


cap_blacklist = ['Green Potion', 'Red Potion', 'Blue Potion']

shop_transfer = {'Red Potion': 'Rupees (50)', 'Bee': 'Rupees (5)', 'Blue Potion': 'Rupees (50)',
                 'Green Potion': 'Rupees (50)',
                 # money seems a bit too generous with these on
                 # 'Blue Shield': 'Rupees (50)', 'Red Shield': 'Rupees (300)',
                 }

rupee_chart = {'Rupee (1)': 1, 'Rupees (5)': 5, 'Rupees (20)': 20, 'Rupees (50)': 50,
               'Rupees (100)': 100, 'Rupees (300)': 300}


def add_pot_contents(world, player):
    retro_bow = world.bow_mode[player].startswith('retro')
    for super_tile, pot_list in vanilla_pots.items():
        for pot in pot_list:
            if pot.item not in [PotItem.Hole, PotItem.Key, PotItem.Switch]:
                if valid_pot_location(pot, world.pot_pool[player], world, player):
                    item = ('Rupees (5)' if retro_bow and pot_items[pot.item] == 'Arrows (5)'
                            else pot_items[pot.item])
                    world.itempool.append(ItemFactory(item, player))


def get_pool_core(world, player, progressive, shuffle, difficulty, treasure_hunt_total, timer, goal, mode, swords,
                  bombbag, door_shuffle, logic, flute_activated):
    pool = []
    placed_items = {}
    precollected_items = []
    clock_mode = None
    if goal in ['triforcehunt', 'trinity', 'ganonhunt']:
        if treasure_hunt_total == 0:
            treasure_hunt_total = 30 if goal in ['triforcehunt', 'ganonhunt'] else 10
    # triforce pieces max out
    triforcepool = ['Triforce Piece'] * min(treasure_hunt_total, max_goal)

    pool.extend(alwaysitems)

    if flute_activated:
        pool.remove('Ocarina')
        pool.append('Ocarina (Activated)')

    def place_item(loc, item):
        assert loc not in placed_items
        placed_items[loc] = item

    def want_progressives():
        return random.choice([True, False]) if progressive == 'random' else progressive == 'on'

    # provide boots to boots glitch dependent modes
    if logic in ['owglitches', 'hybridglitches', 'nologic']:
        precollected_items.append('Pegasus Boots')
        pool.remove('Pegasus Boots')
        pool.extend(['Rupees (20)'])

    if want_progressives():
        pool.extend(progressivegloves)
    else:
        pool.extend(basicgloves)

    lamps_needed_for_dark_rooms = 1

    # old insanity shuffle didn't have fake LW/DW logic so this used to be conditional
    pool.extend(['Magic Mirror', 'Moon Pearl'])

    if timer == 'display':
        clock_mode = 'stopwatch'
    elif timer == 'ohko':
        clock_mode = 'ohko'

    diff = difficulties[difficulty]
    pool.extend(diff.baseitems)

    if bombbag:
        pool = [item.replace('Bomb Upgrade (+5)','Rupees (5)') for item in pool]
        pool = [item.replace('Bomb Upgrade (+10)','Rupees (5)') for item in pool]
        pool.extend(diff.bombbag)

    # expert+ difficulties produce the same contents for
    # all bottles, since only one bottle is available
    if diff.same_bottle:
        thisbottle = random.choice(diff.bottles)
    for _ in range(diff.bottle_count):
        if not diff.same_bottle:
            thisbottle = random.choice(diff.bottles)
        pool.append(thisbottle)

    if want_progressives():
        pool.extend(diff.progressiveshield)
    else:
        pool.extend(diff.basicshield)

    if want_progressives():
        pool.extend(diff.progressivearmor)
    else:
        pool.extend(diff.basicarmor)

    if 'silvers' not in world.bow_mode[player]:
        pool.extend(['Progressive Bow'] * 2)
    elif swords != 'swordless':
        pool.extend(diff.basicbow)
    else:
        pool.extend(['Bow', 'Silver Arrows'])

    if swords == 'swordless':
        pool.extend(diff.swordless)
    elif swords == 'vanilla':
        swords_to_use = diff.progressivesword.copy() if want_progressives() else diff.basicsword.copy()
        random.shuffle(swords_to_use)

        place_item('Link\'s Uncle', swords_to_use.pop())
        place_item('Blacksmith', swords_to_use.pop())
        place_item('Pyramid Fairy - Left', swords_to_use.pop())
        if goal not in ['pedestal', 'trinity']:
            place_item('Master Sword Pedestal', swords_to_use.pop())
        else:
            place_item('Master Sword Pedestal', 'Triforce')
            pool.append(swords_to_use.pop())
    else:
        pool.extend(diff.progressivesword if want_progressives() else diff.basicsword)
        if swords == 'assured':
            if want_progressives():
                precollected_items.append('Progressive Sword')
                pool.remove('Progressive Sword')
            else:
                precollected_items.append('Fighter Sword')
                pool.remove('Fighter Sword')
            pool.extend(['Rupees (50)'])

    if timer in ['timed', 'timed-countdown']:
        pool.extend(diff.timedother)
        clock_mode = 'stopwatch' if timer == 'timed' else 'countdown'
    elif timer == 'timed-ohko':
        pool.extend(diff.timedohko)
        clock_mode = 'countdown-ohko'
    if goal in ['triforcehunt', 'trinity', 'ganonhunt']:
        pool.extend(triforcepool)

    for extra in diff.extras:
        pool.extend(extra)

    # note: massage item pool now handles shrinking the pool appropriately

    if goal in ['pedestal', 'trinity'] and swords != 'vanilla':
        place_item('Master Sword Pedestal', 'Triforce')
    if world.bow_mode[player].startswith('retro'):
        pool = [item.replace('Single Arrow', 'Rupees (5)') for item in pool]
        pool = [item.replace('Arrows (10)', 'Rupees (5)') for item in pool]
        pool = [item.replace('Arrow Upgrade (+5)', 'Rupees (5)') for item in pool]
        pool = [item.replace('Arrow Upgrade (+10)', 'Rupees (5)') for item in pool]
    if world.keyshuffle[player] == 'universal':
        pool.extend(diff.retro)
        if door_shuffle != 'vanilla':  # door shuffle needs more keys for universal keys
            pool.extend(['Small Key (Universal)'] * 5)  # reduce to 5 for now
        if mode == 'standard':
            if door_shuffle == 'vanilla':
                key_location = random.choice(['Secret Passage', 'Hyrule Castle - Boomerang Chest', 'Hyrule Castle - Map Chest', 'Hyrule Castle - Zelda\'s Chest', 'Sewers - Dark Cross'])
                place_item(key_location, 'Small Key (Universal)')
            else:
                pool.extend(['Small Key (Universal)'])
        else:
            pool.extend(['Small Key (Universal)'])
    return (pool, placed_items, precollected_items, clock_mode, lamps_needed_for_dark_rooms)


item_alternates = {
    # Bows
    'Progressive Bow (Alt)': ('Progressive Bow', 1),
    'Bow': ('Progressive Bow', 1),
    'Silver Arrows': ('Progressive Bow', 2),
    # Gloves
    'Power Glove': ('Progressive Glove', 1),
    'Titans Mitts': ('Progressive Glove', 2),
    # Swords
    'Sword and Shield': ('Progressive Sword', 1), # could find a way to also remove a shield, but mostly not impactful
    'Fighter Sword': ('Progressive Sword', 1),
    'Master Sword': ('Progressive Sword', 2),
    'Tempered Sword': ('Progressive Sword', 3),
    'Golden Sword': ('Progressive Sword', 4),
    # Shields
    'Blue Shield': ('Progressive Shield', 1),
    'Red Shield': ('Progressive Shield', 2),
    'Mirror Shield': ('Progressive Shield', 3),
    # Armors
    'Blue Mail': ('Progressive Armor', 1),
    'Red Mail': ('Progressive Armor', 2),

    'Magic Upgrade (1/4)': ('Magic Upgrade (1/2)', 2),
    'Ocarina': ('Ocarina (Activated)', 1),
    'Ocarina (Activated)': ('Ocarina', 1),
    'Boss Heart Container': ('Sanctuary Heart Container', 1),
    'Sanctuary Heart Container': ('Boss Heart Container', 1),
    'Power Star': ('Triforce Piece', 1)
}


def modify_pool_for_start_inventory(start_inventory, world, player):
    if (world.customizer and world.customizer.get_item_pool()) or world.custom:
        # custom item pools only adjust in dungeon items
        for item in start_inventory:
            if item.dungeon:
                d = world.get_dungeon(item.dungeon, item.player)
                match = next((i for i in d.all_items if i.name == item.name), None)
                if match:
                    if match.map or match.compass:
                        d.dungeon_items.remove(match)
                    elif match.smallkey:
                        d.small_keys.remove(match)
                    elif match.bigkey and d.big_key == match:
                        d.big_key = None
        return
    for item in start_inventory:
        if item.player == player:
            if item in world.itempool:
                world.itempool.remove(item)
            elif item.name in item_alternates:
                alt = item_alternates[item.name]
                i = alt[1]
                while i > 0:
                    alt_item = ItemFactory([alt[0]], player)[0]
                    if alt_item in world.itempool:
                        world.itempool.remove(alt_item)
                    i = i-1
            elif 'Bottle' in item.name:
                bottle_item = next((x for x in world.itempool if 'Bottle' in item.name and x.player == player), None)
                if bottle_item is not None:
                    world.itempool.remove(bottle_item)
            if item.dungeon:
                d = world.get_dungeon(item.dungeon, item.player)
                match = next((i for i in d.all_items if i.name == item.name), None)
                if match:
                    if match.map or match.compass:
                        d.dungeon_items.remove(match)
                    elif match.smallkey:
                        d.small_keys.remove(match)
                    elif match.bigkey and d.big_key == match:
                        d.big_key = None


def make_custom_item_pool(world, player, progressive, shuffle, difficulty, timer, goal, mode, swords, bombbag, customitemarray):
    if isinstance(customitemarray,dict) and 1 in customitemarray:
        customitemarray = customitemarray[1]
    pool = []
    placed_items = {}
    precollected_items = []
    clock_mode = None
    treasure_hunt_count = None
    treasure_hunt_icon = None

    def place_item(loc, item):
        assert loc not in placed_items
        placed_items[loc] = item

    # Correct for insanely oversized item counts and take initial steps to handle undersized pools.
    # Bow to Silver Arrows Upgrade, including Generic Keys & Rupoors
    for x in [*range(0, 66 + 1), 68, 69]:
        key = CONST.CUSTOMITEMS[x]
        if customitemarray[key] > total_items_to_place:
            customitemarray[key] = total_items_to_place

    # Triforce
    if customitemarray["triforce"] > total_items_to_place:
        customitemarray["triforce"] = total_items_to_place

    # Triforce Pieces
    if goal in ['triforcehunt', 'trinity', 'ganonhunt']:
        g, t = set_default_triforce(goal, customitemarray["triforcepiecesgoal"], customitemarray["triforcepieces"])
        customitemarray["triforcepiecesgoal"], customitemarray["triforcepieces"] = g, t

    itemtotal = 0
    # Bow to Silver Arrows Upgrade, including Generic Keys & Rupoors
    for x in [*range(0, 66 + 1), 68, 69]:
        key = CONST.CUSTOMITEMS[x]
        itemtotal = itemtotal + customitemarray[key]
    # Triforce
    itemtotal = itemtotal + customitemarray["triforce"]
    # Generic Keys
    itemtotal = itemtotal + customitemarray["generickeys"]

    customitems = [
      "Bow", "Silver Arrows", "Blue Boomerang", "Red Boomerang", "Hookshot", "Mushroom", "Magic Powder", "Fire Rod", "Ice Rod", "Bombos", "Ether", "Quake", "Lamp", "Hammer", "Shovel", "Ocarina", "Bug Catching Net", "Book of Mudora", "Cane of Somaria", "Cane of Byrna", "Cape", "Pegasus Boots", "Power Glove", "Titans Mitts", "Progressive Glove", "Flippers", "Piece of Heart", "Boss Heart Container", "Sanctuary Heart Container", "Master Sword", "Tempered Sword", "Golden Sword", "Blue Shield", "Red Shield", "Mirror Shield", "Progressive Shield", "Blue Mail", "Red Mail", "Progressive Armor", "Magic Upgrade (1/2)", "Magic Upgrade (1/4)", "Bomb Upgrade (+5)", "Bomb Upgrade (+10)", "Arrow Upgrade (+5)", "Arrow Upgrade (+10)", "Single Arrow", "Arrows (10)", "Single Bomb", "Bombs (3)", "Rupee (1)", "Rupees (5)", "Rupees (20)", "Rupees (50)", "Rupees (100)", "Rupees (300)", "Rupoor", "Blue Clock", "Green Clock", "Red Clock", "Progressive Bow", "Bombs (10)", "Triforce Piece", "Triforce"
    ]
    for customitem in customitems:
        pool.extend([customitem] * customitemarray[get_custom_array_key(customitem)])

    diff = difficulties[difficulty]

    lamps_needed_for_dark_rooms = 1

    # expert+ difficulties produce the same contents for
    # all bottles, since only one bottle is available
    if diff.same_bottle:
        thisbottle = random.choice(diff.bottles)
    for _ in range(customitemarray["bottle"]):
        if not diff.same_bottle:
            thisbottle = random.choice(diff.bottles)
        pool.append(thisbottle)

    if customitemarray["triforcepieces"] > 0 or customitemarray["triforcepiecesgoal"] > 0:
        # Location pool doesn't support larger values
        treasure_hunt_count = max(min(customitemarray["triforcepiecesgoal"], max_goal), 1)
        treasure_hunt_icon = 'Triforce Piece'
        # Ensure game is always possible to complete here, force sufficient pieces if the player is unwilling.
        if ((customitemarray["triforcepieces"] < treasure_hunt_count)
           and (goal in ['triforcehunt', 'trinity', 'ganonhunt']) and (customitemarray["triforce"] == 0)):
            extrapieces = treasure_hunt_count - customitemarray["triforcepieces"]
            pool.extend(['Triforce Piece'] * extrapieces)
            itemtotal = itemtotal + extrapieces

    if timer in ['display', 'timed', 'timed-countdown']:
        clock_mode = 'countdown' if timer == 'timed-countdown' else 'stopwatch'
    elif timer == 'timed-ohko':
        clock_mode = 'countdown-ohko'
    elif timer == 'ohko':
        clock_mode = 'ohko'

    if goal in ['pedestal', 'trinity']:
        place_item('Master Sword Pedestal', 'Triforce')
        itemtotal = itemtotal + 1

    if mode == 'standard':
        if world.keyshuffle[player] == 'universal':
            key_location = random.choice(['Secret Passage', 'Hyrule Castle - Boomerang Chest', 'Hyrule Castle - Map Chest', 'Hyrule Castle - Zelda\'s Chest', 'Sewers - Dark Cross'])
            place_item(key_location, 'Small Key (Universal)')
            pool.extend(['Small Key (Universal)'] * max((customitemarray["generickeys"] - 1), 0))
        else:
            pool.extend(['Small Key (Universal)'] * customitemarray["generickeys"])
    else:
        pool.extend(['Small Key (Universal)'] * customitemarray["generickeys"])

    pool.extend(['Fighter Sword'] * customitemarray["sword1"])
    pool.extend(['Progressive Sword'] * customitemarray["progressivesword"])
    pool.extend(['Magic Mirror'] * customitemarray["mirror"])
    pool.extend(['Moon Pearl'] * customitemarray["pearl"])

    if world.keyshuffle[player] == 'universal':
        itemtotal = itemtotal - 28 # Corrects for small keys not being in item pool in Retro Mode
    if itemtotal < total_items_to_place:
        nothings = total_items_to_place - itemtotal
#        print("Placing " + str(nothings) + " Nothings")
        pool.extend(['Nothing'] * nothings)

    start_inventory = [x for x in world.precollected_items if x.player == player]
    if world.logic[player] in ['owglitches', 'hybridglitches', 'nologic'] and all(x.name != 'Pegasus Boots' for x in start_inventory):
        precollected_items.append('Pegasus Boots')
        if 'Pegasus Boots' in pool:
            pool.remove('Pegasus Boots')
            pool.append('Rupees (20)')
    if world.swords[player] == 'assured' and all(' Sword' not in x.name for x in start_inventory):
        precollected_items.append('Progressive Sword')
        if 'Progressive Sword' in pool:
            pool.remove('Progressive Sword')
            pool.append('Rupees (50)')
        elif 'Fighter Sword' in pool:
            pool.remove('Fighter Sword')
            pool.append('Rupees (50)')

    return (pool, placed_items, precollected_items, clock_mode, treasure_hunt_count, treasure_hunt_icon, lamps_needed_for_dark_rooms)


def make_customizer_pool(world, player):
    pool = []
    placed_items = {}
    precollected_items = []
    clock_mode = None

    def place_item(loc, item):
        assert loc not in placed_items
        placed_items[loc] = item

    dungeon_locations, dungeon_count = defaultdict(set), defaultdict(int)
    for l in world.get_unfilled_locations(player):
        if l.parent_region.dungeon:
            dungeon = l.parent_region.dungeon
            dungeon_locations[dungeon.name].add(l)
            if dungeon.name not in dungeon_count:
                d_count = 1 if dungeon.big_key else 0
                d_count += len(dungeon.small_keys) + len(dungeon.dungeon_items)
                dungeon_count[dungeon.name] = d_count

    diff = difficulties[world.difficulty[player]]
    for item_name, amount in world.customizer.get_item_pool()[player].items():
        if isinstance(amount, int):
            if item_name == 'Bottle (Random)':
                for _ in range(amount):
                    pool.append(random.choice(diff.bottles))
            elif item_name.startswith('Small Key') and item_name != 'Small Key (Universal)':
                d_item = ItemFactory(item_name, player)
                if world.keyshuffle[player] == 'none':
                    d_name = d_item.dungeon
                    dungeon = world.get_dungeon(d_name, player)
                    target_amount = max(amount, len(dungeon.small_keys))
                    additional_amount = target_amount - len(dungeon.small_keys)
                    possible_fit = min(additional_amount, len(dungeon_locations[d_name])-dungeon_count[d_name])
                    if possible_fit > 0:
                        dungeon_count[d_name] += possible_fit
                        dungeon.small_keys.extend([d_item] * amount)
                        additional_amount -= possible_fit
                    if additional_amount > 0:
                        pool.extend([item_name] * amount)
                else:
                    dungeon = world.get_dungeon(d_item.dungeon, player)
                    target_amount = max(amount, len(dungeon.small_keys))
                    additional_amount = target_amount - len(dungeon.small_keys)
                    dungeon.small_keys.extend([d_item] * additional_amount)
            elif item_name.startswith('Big Key') or item_name.startswith('Map') or item_name.startswith('Compass'):
                d_item = ItemFactory(item_name, player)
                if ((d_item.bigkey and not world.bigkeyshuffle[player])
                   or (d_item.compass and not world.compassshuffle[player])
                   or (d_item.map and not world.mapshuffle[player])):
                    d_name = d_item.dungeon
                    dungeon = world.get_dungeon(d_name, player)
                    current_amount = 1 if d_item == dungeon.big_key or d_item in dungeon.dungeon_items else 0
                    additional_amount = amount - current_amount
                    possible_fit = min(additional_amount, len(dungeon_locations[d_name])-dungeon_count[d_name])
                    if possible_fit > 0:
                        dungeon_count[d_name] += possible_fit
                        dungeon.dungeon_items.extend([d_item] * amount)
                        additional_amount -= possible_fit
                    if additional_amount > 0:
                        pool.extend([item_name] * amount)
                else:
                    dungeon = world.get_dungeon(d_item.dungeon, player)
                    current_amount = 1 if d_item == dungeon.big_key or d_item in dungeon.dungeon_items else 0
                    additional_amount = amount - current_amount
                    dungeon.dungeon_items.extend([d_item] * additional_amount)
            else:
                pool.extend([item_name] * amount)

    timer = world.timer[player]
    if timer in ['display', 'timed', 'timed-countdown']:
        clock_mode = 'countdown' if timer == 'timed-countdown' else 'stopwatch'
    elif timer == 'timed-ohko':
        clock_mode = 'countdown-ohko'
    elif timer == 'ohko':
        clock_mode = 'ohko'

    if world.goal[player] in ['pedestal', 'trinity']:
        place_item('Master Sword Pedestal', 'Triforce')

    guaranteed_items = alwaysitems + ['Magic Mirror', 'Moon Pearl']
    if world.flute_mode[player] == 'active':
        guaranteed_items.remove('Ocarina')
        guaranteed_items.append('Ocarina (Activated)')
    missing_items = []
    if world.shopsanity[player]:
        guaranteed_items.extend(['Blue Potion', 'Green Potion', 'Red Potion'])
        if world.keyshuffle[player] == 'universal':
            guaranteed_items.append('Small Key (Universal)')
    for item in guaranteed_items:
        if item not in pool:
            missing_items.append(item)

    glove_count = sum(1 for i in pool if i == 'Progressive Glove')
    glove_count = 2 if next((i for i in pool if i == 'Titans Glove'), None) is not None else glove_count
    for i in range(glove_count, 2):
        missing_items.append('Progressive Glove')

    if world.bombbag[player]:
        if 'Bomb Upgrade (+10)' not in pool:
            missing_items.append('Bomb Upgrade (+10)')

    if world.swords[player] != 'swordless':
        beam_swords = {'Master Sword', 'Tempered Sword', 'Golden Sword'}
        sword_count = sum(1 for i in pool if i in 'Progressive Sword')
        sword_count = 2 if next((i for i in pool if i in beam_swords), None) is not None else sword_count
        for i in range(sword_count, 2):
            missing_items.append('Progressive Sword')

    bow_found = next((i for i in pool if i in {'Bow', 'Progressive Bow'}), None)
    if not bow_found:
        missing_items.append('Progressive Bow')
    if missing_items:
        logging.getLogger('').warning(f'The following items are not in the custom item pool {", ".join(missing_items)}')

    g, t = set_default_triforce(world.goal[player], world.treasure_hunt_count[player],
                                world.treasure_hunt_total[player])
    if t != 0:
        pieces = sum(1 for i in pool if i == 'Triforce Piece')
        if pieces < t:
            pool.extend(['Triforce Piece'] * (t - pieces))

    sphere_0 = world.customizer.get_start_inventory()
    no_start_inventory = not sphere_0 or not sphere_0[player]
    init_equip = [] if no_start_inventory else sphere_0[player]
    if (world.logic[player] in ['owglitches', 'hybridglitches', 'nologic']
       and (no_start_inventory or all(x != 'Pegasus Boots' for x in init_equip))):
        precollected_items.append('Pegasus Boots')
        if 'Pegasus Boots' in pool:
            pool.remove('Pegasus Boots')
            pool.append('Rupees (20)')
    if world.swords[player] == 'assured' and (no_start_inventory or all(' Sword' not in x for x in init_equip)):
        precollected_items.append('Progressive Sword')
        if 'Progressive Sword' in pool:
            pool.remove('Progressive Sword')
            pool.append('Rupees (50)')
        elif 'Fighter Sword' in pool:
            pool.remove('Fighter Sword')
            pool.append('Rupees (50)')

    return pool, placed_items, precollected_items, clock_mode, 1


filler_items = {
    'Arrows (10)': 12,
    'Bombs (3)': 16,
    'Rupees (300)': 5,
    'Rupees (100)': 1,
    'Rupees (50)': 7,
    'Rupees (20)': 28,
    'Rupees (5)': 4,
}


def count_player_dungeon_item_pool(world, player):
    return sum(1 for dungeon in world.dungeons for item in dungeon.all_items
               if dungeon.player == player and item.location is None and is_dungeon_item(item.name, world, player))


# location pool doesn't support larger values at this time
def set_default_triforce(goal, custom_goal, custom_total):
    triforce_goal, triforce_total = 0, 0
    if goal in ['triforcehunt', 'ganonhunt']:
        triforce_goal, triforce_total = 20, 30
    elif goal == 'trinity':
        triforce_goal, triforce_total = 8, 10
    if custom_goal > 0:
        triforce_goal = max(min(custom_goal, max_goal), 1)
    if custom_total > 0:
        triforce_total = max(min(custom_total, max_goal), triforce_goal)
    return triforce_goal, triforce_total


# A quick test to ensure all combinations generate the correct amount of items.
# def test():
#     for difficulty in ['normal', 'hard', 'expert']:
#         for goal in ['ganon', 'triforcehunt', 'pedestal', 'trinity']:
#             for timer in ['none', 'display', 'timed', 'timed-ohko', 'ohko', 'timed-countdown']:
#                 for mode in ['open', 'standard', 'inverted', 'retro']:
#                     for swords in ['random', 'assured', 'swordless', 'vanilla']:
#                         for progressive in ['on', 'off']:
#                             for shuffle in ['full']:
#                                 for logic in ['noglitches', 'minorglitches', 'owglitches', 'nologic']:
#                                     for retro in [True, False]:
#                                         for bombbag in [True, False]:
#                                             for door_shuffle in ['basic', 'crossed', 'vanilla']:
#                                                 out = get_pool_core(progressive, shuffle, difficulty, 30, timer, goal, mode, swords, retro, bombbag, door_shuffle, logic)
#                                                 count = len(out[0]) + len(out[1])
#
#                                                 correct_count = total_items_to_place
#                                                 if goal in ['pedestal', 'trinity'] and swords != 'vanilla':
#                                                     # pedestal goals generate one extra item
#                                                     correct_count += 1
#                                                 if retro:
#                                                     correct_count += 28
#                                                 try:
#                                                     assert count == correct_count, "expected {0} items but found {1} items for {2}".format(correct_count, count, (progressive, shuffle, difficulty, timer, goal, mode, swords, retro, bombbag))
#                                                 except AssertionError as e:
#                                                     print(e)
#
# if __name__ == '__main__':
#     test()


def fill_specific_items(world):
    if world.customizer:
        placements = world.customizer.get_placements()
        dungeon_pool = get_dungeon_item_pool(world)
        prize_pool = []
        prize_set = {'Red Pendant', 'Blue Pendant', 'Green Pendant', 'Crystal 1', 'Crystal 2',
                     'Crystal 3', 'Crystal 4', 'Crystal 7', 'Crystal 5', 'Crystal 6'}
        for p in range(1, world.players + 1):
            prize_pool.extend(prize_set)
        if placements:
            for player, placement_list in placements.items():
                for location, item in placement_list.items():
                    loc = world.get_location(location, player)
                    item_to_place, event_flag = get_item_and_event_flag(item, world, player,
                                                                        dungeon_pool, prize_set, prize_pool)
                    if item_to_place:
                        world.push_item(loc, item_to_place, False)
                        loc.locked = True
                        track_outside_keys(item_to_place, loc, world)
                        track_dungeon_items(item_to_place, loc, world)
                        loc.event = (event_flag or item_to_place.advancement
                                     or item_to_place.bigkey or item_to_place.smallkey)
                    else:
                        raise Exception(f'Did not find "{item}" in item pool to place at "{location}"')
        advanced_placements = world.customizer.get_advanced_placements()
        if advanced_placements:
            for player, placement_list in advanced_placements.items():
                for placement in placement_list:
                    if placement['type'] == 'LocationGroup':
                        item = placement['item']
                        item_to_place, event_flag = get_item_and_event_flag(item, world, player,
                                                                            dungeon_pool, prize_set, prize_pool)
                        if not item_to_place:
                            raise Exception(f'Did not find "{item}" in item pool to place for a LocationGroup"')
                        locations = placement['locations']
                        handled = False
                        while not handled:
                            if isinstance(locations, dict):
                                chosen_loc = random.choices(list(locations.keys()), list(locations.values()), k=1)[0]
                            else:  # if isinstance(locations, list):
                                chosen_loc = random.choice(locations)
                            if chosen_loc == 'Random':
                                if is_dungeon_item(item_to_place.name, world, item_to_place.player):
                                    dungeon_pool.append(item_to_place)
                                elif item_to_place.name in prize_set:
                                    prize_pool.append(item_to_place.name)
                                else:
                                    world.itempool.append(item_to_place)
                            else:
                                loc = world.get_location(chosen_loc, player)
                                if loc.item:
                                    continue
                                world.push_item(loc, item_to_place, False)
                                loc.locked = True
                                track_outside_keys(item_to_place, loc, world)
                                track_dungeon_items(item_to_place, loc, world)
                                loc.event = (event_flag or item_to_place.advancement
                                             or item_to_place.bigkey or item_to_place.smallkey)
                            handled = True
                    elif placement['type'] == 'NotLocationGroup':
                        item = placement['item']
                        item_parts = item.split('#')
                        item_player = player if len(item_parts) < 2 else int(item_parts[1])
                        item_name = item_parts[0]
                        world.item_pool_config.restricted[(item_name, item_player)] = placement['locations']
                    elif placement['type'] == 'PreferredLocationGroup':
                        item = placement['item']
                        item_parts = item.split('#')
                        item_player = player if len(item_parts) < 2 else int(item_parts[1])
                        item_name = item_parts[0]
                        world.item_pool_config.preferred[(item_name, item_player)] = placement['locations']
                    elif placement['type'] == 'Verification':
                        item = placement['item']
                        item_parts = item.split('#')
                        item_player = player if len(item_parts) < 2 else int(item_parts[1])
                        item_name = item_parts[0]
                        world.item_pool_config.verify[(item_name, item_player)] = placement['locations']
                        world.item_pool_config.verify_target += len(placement['locations'])


def get_item_and_event_flag(item, world, player, dungeon_pool, prize_set, prize_pool):
    item_parts = item.split('#')
    item_player = player if len(item_parts) < 2 else int(item_parts[1])
    item_name = item_parts[0]
    event_flag = False
    if is_dungeon_item(item_name, world, item_player):
        item_to_place = next(x for x in dungeon_pool
                             if x.name == item_name and x.player == item_player)
        dungeon_pool.remove(item_to_place)
        event_flag = True
    elif item_name in prize_set:
        item_player = player  # prizes must be for that player
        item_to_place = ItemFactory(item_name, item_player)
        prize_pool.remove(item_name)
        event_flag = True
    else:
        matcher = lambda x: x.name == item_name and x.player == item_player
        if item_name == 'Bottle':
            matcher = lambda x: x.name.startswith(item_name) and x.player == item_player
        item_to_place = next((x for x in world.itempool if matcher(x)), None)
        if item_to_place is None:
            return None, event_flag
        else:
            world.itempool.remove(item_to_place)
    return item_to_place, event_flag


def is_dungeon_item(item, world, player):
    return ((item.startswith('Small Key') and world.keyshuffle[player] == 'none')
            or (item.startswith('Big Key') and not world.bigkeyshuffle[player])
            or (item.startswith('Compass') and not world.compassshuffle[player])
            or (item.startswith('Map') and not world.mapshuffle[player]))

