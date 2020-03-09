from collections import namedtuple
import logging
import random

from BaseClasses import Region, RegionType, Shop, ShopType, Location
from Bosses import place_bosses
from Dungeons import get_dungeon_item_pool
from EntranceShuffle import connect_entrance
from Fill import FillError, fill_restrictive
from Items import ItemFactory

import classes.constants as CONST


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
                         'triforcehunt', 'triforce_pieces_required', 'retro',
                         'extras', 'progressive_sword_limit', 'progressive_shield_limit',
                         'progressive_armor_limit', 'progressive_bottle_limit',
                         'progressive_bow_limit', 'heart_piece_limit', 'boss_heart_container_limit'])

total_items_to_place = 153

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
        triforcehunt = ['Triforce Piece'] * 30,
        triforce_pieces_required = 20,
        retro = ['Small Key (Universal)'] * 18 + ['Rupees (20)'] * 10,
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
        triforcehunt = ['Triforce Piece'] * 30,
        triforce_pieces_required = 20,
        retro = ['Small Key (Universal)'] * 13 + ['Rupees (5)'] * 15,
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
        triforcehunt = ['Triforce Piece'] * 30,
        triforce_pieces_required = 20,
        retro = ['Small Key (Universal)'] * 13 + ['Rupees (5)'] * 15,
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
    if (world.difficulty[player] not in ['normal', 'hard', 'expert'] or world.goal[player] not in ['ganon', 'pedestal', 'dungeons', 'triforcehunt', 'crystals']
            or world.mode[player] not in ['open', 'standard', 'inverted'] or world.timer not in ['none', 'display', 'timed', 'timed-ohko', 'ohko', 'timed-countdown'] or world.progressive not in ['on', 'off', 'random']):
        raise NotImplementedError('Not supported yet')

    if world.timer in ['ohko', 'timed-ohko']:
        world.can_take_damage = False

    if world.goal[player] in ['pedestal', 'triforcehunt']:
        world.push_item(world.get_location('Ganon', player), ItemFactory('Nothing', player), False)
    else:
        world.push_item(world.get_location('Ganon', player), ItemFactory('Triforce', player), False)

    if world.goal[player] in ['triforcehunt']:
        region = world.get_region('Light World',player)

        loc = Location(player, "Murahdahla", parent=region)
        loc.access_rule = lambda state: state.item_count('Triforce Piece', player) + state.item_count('Power Star', player) > state.world.treasure_hunt_count[player]
        region.locations.append(loc)
        world.dynamic_locations.append(loc)

        world.clear_location_cache()

        world.push_item(loc, ItemFactory('Triforce', player), False)
        loc.event = True
        loc.locked = True

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
    if world.mode[player] == 'standard':
        world.push_item(world.get_location('Zelda Pickup', player), ItemFactory('Zelda Herself', player), False)
        world.get_location('Zelda Pickup', player).event = True
        world.get_location('Zelda Pickup', player).locked = True
        world.push_item(world.get_location('Zelda Drop Off', player), ItemFactory('Zelda Delivered', player), False)
        world.get_location('Zelda Drop Off', player).event = True
        world.get_location('Zelda Drop Off', player).locked = True

    # set up item pool
    if world.custom:
        (pool, placed_items, precollected_items, clock_mode, treasure_hunt_count, treasure_hunt_icon, lamps_needed_for_dark_rooms) = make_custom_item_pool(world.progressive, world.shuffle[player], world.difficulty[player], world.timer, world.goal[player], world.mode[player], world.swords[player], world.retro[player], world.customitemarray)
        world.rupoor_cost = min(world.customitemarray["rupoorcost"], 9999)
    else:
        (pool, placed_items, precollected_items, clock_mode, treasure_hunt_count, treasure_hunt_icon, lamps_needed_for_dark_rooms) = get_pool_core(world.progressive, world.shuffle[player], world.difficulty[player], world.timer, world.goal[player], world.mode[player], world.swords[player], world.retro[player], world.doorShuffle[player], world.logic[player])

    if player in world.pool_adjustment.keys():
        amt = world.pool_adjustment[player]
        if amt < 0:
            for i in range(0, amt):
                pool.remove('Rupees (20)')
        elif amt > 0:
            for i in range(0, amt):
                pool.append('Rupees (20)')

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
                if item in ['Progressive Bow', 'Bow'] and not found_bow:
                    found_bow = True
                    possible_weapons.append(item)
                if item in ['Hammer', 'Bombs (10)', 'Fire Rod', 'Cane of Somaria', 'Cane of Byrna']:
                    if item not in possible_weapons:
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

    items = ItemFactory(pool, player)

    world.lamps_needed_for_dark_rooms = lamps_needed_for_dark_rooms

    if clock_mode is not None:
        world.clock_mode = clock_mode

    if treasure_hunt_count is not None:
        world.treasure_hunt_count[player] = treasure_hunt_count
    if treasure_hunt_icon is not None:
        world.treasure_hunt_icon[player] = treasure_hunt_icon

    world.itempool.extend([item for item in get_dungeon_item_pool(world) if item.player == player
                           and ((item.smallkey and world.keyshuffle[player])
                                or (item.bigkey and world.bigkeyshuffle[player])
                                or (item.map and world.mapshuffle[player])
                                or (item.compass and world.compassshuffle[player]))])

    # logic has some branches where having 4 hearts is one possible requirement (of several alternatives)
    # rather than making all hearts/heart pieces progression items (which slows down generation considerably)
    # We mark one random heart container as an advancement item (or 4 heart pieces in expert mode)
    if world.difficulty[player] in ['normal', 'hard'] and not (world.custom and world.customitemarray["heartcontainer"] == 0):
        [item for item in items if item.name == 'Boss Heart Container'][0].advancement = True
    elif world.difficulty[player] in ['expert'] and not (world.custom and world.customitemarray["heartpiece"] < 4):
        adv_heart_pieces = [item for item in items if item.name == 'Piece of Heart'][0:4]
        for hp in adv_heart_pieces:
            hp.advancement = True

    beeweights = {0: {None: 100},
                  1: {None: 75, 'trap': 25},
                  2: {None: 40, 'trap': 40, 'bee': 20},
                  3: {'trap': 50, 'bee': 50},
                  4: {'trap': 100}}
    def beemizer(item):
        if world.beemizer[item.player] and not item.advancement and not item.priority and not item.type:
            choice = random.choices(list(beeweights[world.beemizer[item.player]].keys()), weights=list(beeweights[world.beemizer[item.player]].values()))[0]
            return item if not choice else ItemFactory("Bee Trap", player) if choice == 'trap' else ItemFactory("Bee", player)
        return item

    world.itempool += [beemizer(item) for item in items]

    # shuffle medallions
    mm_medallion = ['Ether', 'Quake', 'Bombos'][random.randint(0, 2)]
    tr_medallion = ['Ether', 'Quake', 'Bombos'][random.randint(0, 2)]
    world.required_medallions[player] = (mm_medallion, tr_medallion)

    place_bosses(world, player)
    set_up_shops(world, player)

    if world.retro[player]:
        set_up_take_anys(world, player)

    create_dynamic_shop_locations(world, player)

take_any_locations = [
    'Snitch Lady (East)', 'Snitch Lady (West)', 'Bush Covered House', 'Light World Bomb Hut',
    'Fortune Teller (Light)', 'Lake Hylia Fortune Teller', 'Lumberjack House', 'Bonk Fairy (Light)',
    'Bonk Fairy (Dark)', 'Lake Hylia Healer Fairy', 'Swamp Healer Fairy', 'Desert Healer Fairy',
    'Dark Lake Hylia Healer Fairy', 'Dark Lake Hylia Ledge Healer Fairy', 'Dark Desert Healer Fairy',
    'Dark Death Mountain Healer Fairy', 'Long Fairy Cave', 'Good Bee Cave', '20 Rupee Cave',
    'Kakariko Gamble Game', '50 Rupee Cave', 'Lost Woods Gamble', 'Hookshot Fairy',
    'Palace of Darkness Hint', 'East Dark World Hint', 'Archery Game', 'Dark Lake Hylia Ledge Hint',
    'Dark Lake Hylia Ledge Spike Cave', 'Fortune Teller (Dark)', 'Dark Sanctuary Hint', 'Dark Desert Hint']

def set_up_take_anys(world, player):
    if world.mode[player] == 'inverted' and 'Dark Sanctuary Hint' in take_any_locations:
        take_any_locations.remove('Dark Sanctuary Hint')

    regions = random.sample(take_any_locations, 5)

    old_man_take_any = Region("Old Man Sword Cave", RegionType.Cave, 'the sword cave', player)
    world.regions.append(old_man_take_any)
    world.dynamic_regions.append(old_man_take_any)

    reg = regions.pop()
    entrance = world.get_region(reg, player).entrances[0]
    connect_entrance(world, entrance, old_man_take_any, player)
    entrance.target = 0x58
    old_man_take_any.shop = Shop(old_man_take_any, 0x0112, ShopType.TakeAny, 0xE2, True, True)
    world.shops.append(old_man_take_any.shop)

    swords = [item for item in world.itempool if item.type == 'Sword' and item.player == player]
    if swords:
        sword = random.choice(swords)
        world.itempool.remove(sword)
        world.itempool.append(ItemFactory('Rupees (20)', player))
        old_man_take_any.shop.add_inventory(0, sword.name, 0, 0, create_location=True)
    else:
        old_man_take_any.shop.add_inventory(0, 'Rupees (300)', 0, 0)

    for num in range(4):
        take_any = Region("Take-Any #{}".format(num+1), RegionType.Cave, 'a cave of choice', player)
        world.regions.append(take_any)
        world.dynamic_regions.append(take_any)

        target, room_id = random.choice([(0x58, 0x0112), (0x60, 0x010F), (0x46, 0x011F)])
        reg = regions.pop()
        entrance = world.get_region(reg, player).entrances[0]
        connect_entrance(world, entrance, take_any, player)
        entrance.target = target
        take_any.shop = Shop(take_any, room_id, ShopType.TakeAny, 0xE3, True, True)
        world.shops.append(take_any.shop)
        take_any.shop.add_inventory(0, 'Blue Potion', 0, 0)
        take_any.shop.add_inventory(1, 'Boss Heart Container', 0, 0)

    world.initialize_regions()


def create_dynamic_shop_locations(world, player):
    for shop in world.shops:
        if shop.region.player == player:
            for i, item in enumerate(shop.inventory):
                if item is None:
                    continue
                if item['create_location']:
                    loc = Location(player, "{} Item {}".format(shop.region.name, i+1), parent=shop.region)
                    shop.region.locations.append(loc)
                    world.dynamic_locations.append(loc)

                    world.clear_location_cache()

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
                fill_restrictive(world, all_state, prize_locs, prizepool, True)
            except FillError as e:
                logging.getLogger('').info("Failed to place dungeon prizes (%s). Will retry %s more times", e, attempts - attempt - 1)
                for location in empty_crystal_locations:
                    location.item = None
                continue
            break
        else:
            raise FillError('Unable to place dungeon prizes')


def set_up_shops(world, player):
    # TODO: move hard+ mode changes for sheilds here, utilizing the new shops

    if world.retro[player]:
        rss = world.get_region('Red Shield Shop', player).shop
        if not rss.locked:
            rss.custom = True
            rss.add_inventory(2, 'Single Arrow', 80)
        for shop in random.sample([s for s in world.shops if not s.locked and s.region.player == player], 5):
            shop.custom = True
            shop.locked = True
            shop.add_inventory(0, 'Single Arrow', 80)
            shop.add_inventory(1, 'Small Key (Universal)', 100)
            shop.add_inventory(2, 'Bombs (10)', 50)
        rss.locked = True


def get_pool_core(progressive, shuffle, difficulty, timer, goal, mode, swords, retro, door_shuffle, logic):
    pool = []
    placed_items = {}
    precollected_items = []
    clock_mode = None
    treasure_hunt_count = None
    treasure_hunt_icon = None

    pool.extend(alwaysitems)

    def place_item(loc, item):
        assert loc not in placed_items
        placed_items[loc] = item

    def want_progressives():
        return random.choice([True, False]) if progressive == 'random' else progressive == 'on'

    # provide boots to major glitch dependent seeds
    if logic in ['owglitches', 'nologic']:
        precollected_items.append('Pegasus Boots')
        pool.remove('Pegasus Boots')
        pool.extend(['Rupees (20)'])

    if want_progressives():
        pool.extend(progressivegloves)
    else:
        pool.extend(basicgloves)

    lamps_needed_for_dark_rooms = 1

    # insanity shuffle doesn't have fake LW/DW logic so for now guaranteed Mirror and Moon Pearl at the start
    if  shuffle == 'insanity_legacy':
        place_item('Link\'s House', 'Magic Mirror')
        place_item('Sanctuary', 'Moon Pearl')
    else:
        pool.extend(['Magic Mirror', 'Moon Pearl'])

    if timer == 'display':
        clock_mode = 'stopwatch'
    elif timer == 'ohko':
        clock_mode = 'ohko'

    diff = difficulties[difficulty]
    pool.extend(diff.baseitems)

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

    if want_progressives():
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
        if goal != 'pedestal':
            place_item('Master Sword Pedestal', swords_to_use.pop())
        else:
            place_item('Master Sword Pedestal', 'Triforce')
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

    extraitems = total_items_to_place - len(pool) - len(placed_items)

    if timer in ['timed', 'timed-countdown']:
        pool.extend(diff.timedother)
        extraitems -= len(diff.timedother)
        clock_mode = 'stopwatch' if timer == 'timed' else 'countdown'
    elif timer == 'timed-ohko':
        pool.extend(diff.timedohko)
        extraitems -= len(diff.timedohko)
        clock_mode = 'countdown-ohko'
    if goal == 'triforcehunt':
        pool.extend(diff.triforcehunt)
        extraitems -= len(diff.triforcehunt)
        treasure_hunt_count = diff.triforce_pieces_required
        treasure_hunt_icon = 'Triforce Piece'

    for extra in diff.extras:
        if extraitems > 0:
            pool.extend(extra)
            extraitems -= len(extra)

    if goal == 'pedestal' and swords != 'vanilla':
        place_item('Master Sword Pedestal', 'Triforce')
    if retro:
        pool = [item.replace('Single Arrow','Rupees (5)') for item in pool]
        pool = [item.replace('Arrows (10)','Rupees (5)') for item in pool]
        pool = [item.replace('Arrow Upgrade (+5)','Rupees (5)') for item in pool]
        pool = [item.replace('Arrow Upgrade (+10)','Rupees (5)') for item in pool]
        pool.extend(diff.retro)
        if mode == 'standard':
            if door_shuffle == 'vanilla':
                key_location = random.choice(['Secret Passage', 'Hyrule Castle - Boomerang Chest', 'Hyrule Castle - Map Chest', 'Hyrule Castle - Zelda\'s Chest', 'Sewers - Dark Cross'])
                place_item(key_location, 'Small Key (Universal)')
            else:
                pool.extend(['Small Key (Universal)'])
        else:
            pool.extend(['Small Key (Universal)'])
    return (pool, placed_items, precollected_items, clock_mode, treasure_hunt_count, treasure_hunt_icon, lamps_needed_for_dark_rooms)

def make_custom_item_pool(progressive, shuffle, difficulty, timer, goal, mode, swords, retro, customitemarray):
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
        treasure_hunt_count = max(min(customitemarray["triforcepiecesgoal"], 99), 1) #To display, count must be between 1 and 99.
        treasure_hunt_icon = 'Triforce Piece'
        # Ensure game is always possible to complete here, force sufficient pieces if the player is unwilling.
        if (customitemarray["triforcepieces"] < treasure_hunt_count) and (goal == 'triforcehunt') and (customitemarray["triforce"] == 0):
            extrapieces = treasure_hunt_count - customitemarray["triforcepieces"]
            pool.extend(['Triforce Piece'] * extrapieces)
            itemtotal = itemtotal + extrapieces

    if timer in ['display', 'timed', 'timed-countdown']:
        clock_mode = 'countdown' if timer == 'timed-countdown' else 'stopwatch'
    elif timer == 'timed-ohko':
        clock_mode = 'countdown-ohko'
    elif timer == 'ohko':
        clock_mode = 'ohko'

    if goal == 'pedestal':
        place_item('Master Sword Pedestal', 'Triforce')
        itemtotal = itemtotal + 1

    if mode == 'standard':
        if retro:
            key_location = random.choice(['Secret Passage', 'Hyrule Castle - Boomerang Chest', 'Hyrule Castle - Map Chest', 'Hyrule Castle - Zelda\'s Chest', 'Sewers - Dark Cross'])
            place_item(key_location, 'Small Key (Universal)')
            pool.extend(['Small Key (Universal)'] * max((customitemarray["generickeys"] - 1), 0))
        else:
            pool.extend(['Small Key (Universal)'] * customitemarray["generickeys"])
    else:
        pool.extend(['Small Key (Universal)'] * customitemarray["generickeys"])

    pool.extend(['Fighter Sword'] * customitemarray["sword1"])
    pool.extend(['Progressive Sword'] * customitemarray["progressivesword"])

    if shuffle == 'insanity_legacy':
        place_item('Link\'s House', 'Magic Mirror')
        place_item('Sanctuary', 'Moon Pearl')
        pool.extend(['Magic Mirror'] * max((customitemarray["mirror"] -1 ), 0))
        pool.extend(['Moon Pearl'] * max((customitemarray["pearl"] - 1), 0))
    else:
        pool.extend(['Magic Mirror'] * customitemarray["mirror"])
        pool.extend(['Moon Pearl'] * customitemarray["pearl"])

    if retro:
        itemtotal = itemtotal - 28 # Corrects for small keys not being in item pool in Retro Mode
    if itemtotal < total_items_to_place:
        nothings = total_items_to_place - itemtotal
        print("Placing " + str(nothings) + " Nothings")
        pool.extend(['Nothing'] * nothings)

    return (pool, placed_items, precollected_items, clock_mode, treasure_hunt_count, treasure_hunt_icon, lamps_needed_for_dark_rooms)

# A quick test to ensure all combinations generate the correct amount of items.
def test():
    for difficulty in ['normal', 'hard', 'expert']:
        for goal in ['ganon', 'triforcehunt', 'pedestal']:
            for timer in ['none', 'display', 'timed', 'timed-ohko', 'ohko', 'timed-countdown']:
                for mode in ['open', 'standard', 'inverted']:
                    for swords in ['random', 'assured', 'swordless', 'vanilla']:
                        for progressive in ['on', 'off']:
                            for shuffle in ['full', 'insanity_legacy']:
                                for retro in [True, False]:
                                    for doorshuffle in ['vanilla', 'basic', 'crossed']:
                                        for logic in ['noglitches', 'owglitches']:
                                            out = get_pool_core(progressive, shuffle, difficulty, timer, goal, mode, swords, retro, doorshuffle, logic)
                                            count = len(out[0]) + len(out[1])

                                            correct_count = total_items_to_place
                                            if goal == 'pedestal' and swords != 'vanilla':
                                                # pedestal goals generate one extra item
                                                correct_count += 1
                                            if retro:
                                                correct_count += 28
                                            try:
                                                assert count == correct_count, "expected {0} items but found {1} items for {2}".format(correct_count, count, (progressive, shuffle, difficulty, timer, goal, mode, swords, retro, doorshuffle, logic))
                                            except AssertionError as e:
                                                print(e)

if __name__ == '__main__':
    test()
