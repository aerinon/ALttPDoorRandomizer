import RaceRandom as random
import collections
import itertools
import logging
import math
from contextlib import suppress

from BaseClasses import CollectionState, FillError, LocationType
from Items import ItemFactory
from Regions import shop_to_location_table, retro_shops
from source.item.FillUtil import filter_locations, classify_major_items, replace_trash_item, vanilla_fallback
from source.item.FillUtil import filter_pot_locations, valid_pot_items


def get_dungeon_item_pool(world):
    return [item for dungeon in world.dungeons for item in dungeon.all_items if item.location is None]


def promote_dungeon_items(world):
    world.itempool += get_dungeon_item_pool(world)

    for item in world.get_items():
        if item.smallkey or item.bigkey:
            item.advancement = True
        elif item.map or item.compass:
            item.priority = True


def dungeon_tracking(world):
    for dungeon in world.dungeons:
        layout = world.dungeon_layouts[dungeon.player][dungeon.name]
        layout.dungeon_items = len([i for i in dungeon.all_items if i.is_inside_dungeon_item(world)])
        layout.free_items = layout.location_cnt - layout.dungeon_items


def fill_dungeons_restrictive(world, shuffled_locations):

    # with shuffled dungeon items they are distributed as part of the normal item pool
    for item in world.get_items():
        if ((item.smallkey and world.keyshuffle[item.player] != 'none')
           or (item.bigkey and world.bigkeyshuffle[item.player])):
            item.advancement = True
        elif (item.map and world.mapshuffle[item.player]) or (item.compass and world.compassshuffle[item.player]):
            item.priority = True

    dungeon_items = [item for item in get_dungeon_item_pool(world) if item.is_inside_dungeon_item(world)]
    bigs, smalls, others = [], [], []
    for i in dungeon_items:
        (bigs if i.bigkey else smalls if i.smallkey else others).append(i)
    unplaced_smalls = list(smalls)
    for i in world.itempool:
        if i.smallkey and world.keyshuffle[i.player] != 'none':
            unplaced_smalls.append(i)

    def fill(base_state, items, key_pool):
        fill_restrictive(world, base_state, shuffled_locations, items, key_pool, True)

    all_state_base = world.get_all_state()
    big_state_base = all_state_base.copy()
    for x in smalls + others:
        big_state_base.collect(x, True)
    fill(big_state_base, bigs, unplaced_smalls)
    random.shuffle(shuffled_locations)
    small_state_base = all_state_base.copy()
    for x in others:
        small_state_base.collect(x, True)
    fill(small_state_base, smalls, unplaced_smalls)
    random.shuffle(shuffled_locations)
    fill(all_state_base, others, None)


def fill_restrictive(world, base_state, locations, itempool, key_pool=None, single_player_placement=False,
                     vanilla=False):
    def sweep_from_pool(placing_item=None):
        new_state = base_state.copy()
        for item in itempool:
            new_state.collect(item, True)
        new_state.placing_item = placing_item
        new_state.sweep_for_events()
        new_state.placing_item = None
        return new_state

    unplaced_items = []

    no_access_checks = {}
    reachable_items = {}
    for item in itempool:
        if world.accessibility[item.player] == 'none':
            no_access_checks.setdefault(item.player, []).append(item)
        else:
            reachable_items.setdefault(item.player, []).append(item)

    for player_items in [no_access_checks, reachable_items]:
        while any(player_items.values()) and locations:
            items_to_place = [[itempool.remove(items[-1]), items.pop()][-1] for items in player_items.values() if items]

            maximum_exploration_state = sweep_from_pool(placing_item=items_to_place[0])
            has_beaten_game = world.has_beaten_game(maximum_exploration_state)

            for item_to_place in items_to_place:
                perform_access_check = True
                if world.accessibility[item_to_place.player] == 'none':
                    perform_access_check = not world.has_beaten_game(maximum_exploration_state, item_to_place.player) if single_player_placement else not has_beaten_game

                spot_to_fill = None

                item_locations = filter_locations(item_to_place, locations, world, vanilla)
                verify(item_to_place, item_locations, maximum_exploration_state, single_player_placement,
                       perform_access_check, key_pool, world)
                for location in item_locations:
                    spot_to_fill = verify_spot_to_fill(location, item_to_place, maximum_exploration_state,
                                                       single_player_placement, perform_access_check, key_pool, world)
                    if spot_to_fill:
                        break
                if spot_to_fill is None:
                    if vanilla:
                        unplaced_items.insert(0, item_to_place)
                        continue
                    spot_to_fill = recovery_placement(item_to_place, locations, world, maximum_exploration_state,
                                                      base_state, itempool, perform_access_check, item_locations,
                                                      key_pool, single_player_placement)
                    if spot_to_fill is None:
                        # we filled all reachable spots. Maybe the game can be beaten anyway?
                        unplaced_items.insert(0, item_to_place)
                        if world.can_beat_game():
                            if world.accessibility[item_to_place.player] != 'none':
                                logging.getLogger('').warning('Not all items placed. Game beatable anyway.'
                                                              f' (Could not place {item_to_place})')
                            continue
                        raise FillError('No more spots to place %s' % item_to_place)

                world.push_item(spot_to_fill, item_to_place, False)
                track_outside_keys(item_to_place, spot_to_fill, world)
                track_dungeon_items(item_to_place, spot_to_fill, world)
                locations.remove(spot_to_fill)
                spot_to_fill.event = True

    itempool.extend(unplaced_items)


def verify_spot_to_fill(location, item_to_place, max_exp_state, single_player_placement, perform_access_check,
                        key_pool, world):
    if item_to_place.smallkey or item_to_place.bigkey:  # a better test to see if a key can go there
        location.item = item_to_place
        location.event = True
        if item_to_place.smallkey:
            with suppress(ValueError):
                key_pool.remove(item_to_place)
        test_state = max_exp_state.copy()
        test_state.stale[item_to_place.player] = True
    else:
        test_state = max_exp_state
    if not single_player_placement or location.player == item_to_place.player:
        test_state.sweep_for_events()
        if location.can_fill(test_state, item_to_place, perform_access_check):
            if valid_key_placement(item_to_place, location, key_pool, test_state, world):
                if item_to_place.crystal or valid_dungeon_placement(item_to_place, location, world):
                    return location
    if item_to_place.smallkey or item_to_place.bigkey:
        location.item = None
        location.event = False
        if item_to_place.smallkey:
            key_pool.append(item_to_place)
    return None


def valid_key_placement(item, location, key_pool, collection_state, world):
    if not valid_reserved_placement(item, location, world):
        return False
    if ((not item.smallkey and not item.bigkey) or item.player != location.player
       or world.keyshuffle[item.player] == 'universal' or world.logic[item.player] == 'nologic'):
        return True
    dungeon = location.parent_region.dungeon
    if dungeon:
        if dungeon.name not in item.name and (dungeon.name != 'Hyrule Castle' or 'Escape' not in item.name):
            return True
        key_logic = world.key_logic[item.player][dungeon.name]
        unplaced_keys = len([x for x in key_pool if x.name == key_logic.small_key_name and x.player == item.player])
        prize_loc = None
        if key_logic.prize_location:
            prize_loc = world.get_location(key_logic.prize_location, location.player)
        cr_count = world.crystals_needed_for_gt[location.player]
        wild_keys = world.keyshuffle[item.player] != 'none'
        if wild_keys:
            reached_keys = {x for x in collection_state.locations_checked
                            if x.item and x.item.name == key_logic.small_key_name and x.item.player == item.player}
        else:
            reached_keys = set()  # will be calculated using key logic in a moment
        self_locking_keys = sum(1 for d, rule in key_logic.door_rules.items() if rule.allow_small
                                and rule.small_location.item and rule.small_location.item.name == key_logic.small_key_name)
        return key_logic.check_placement(unplaced_keys, wild_keys, reached_keys, self_locking_keys,
                                         location if item.bigkey else None,  prize_loc, cr_count)
    else:
        return not item.is_inside_dungeon_item(world)


def valid_reserved_placement(item, location, world):
    if item.player == location.player and item.is_inside_dungeon_item(world):
        return location.name not in world.item_pool_config.reserved_locations[location.player]
    return True


def valid_dungeon_placement(item, location, world):
    if location.parent_region.dungeon:
        layout = world.dungeon_layouts[location.player][location.parent_region.dungeon.name]
        if not is_dungeon_item(item, world) or item.player != location.player:
            return layout.free_items > 0
        else:
            # the second half probably doesn't matter much - should always return true
            return item.dungeon == location.parent_region.dungeon.name and layout.dungeon_items > 0
    return not is_dungeon_item(item, world)


def track_outside_keys(item, location, world):
    if not item.smallkey:
        return
    item_dungeon = item.dungeon
    if location.player == item.player:
        loc_dungeon = location.parent_region.dungeon
        if loc_dungeon and loc_dungeon.name == item_dungeon:
            return  # this is an inside key
    world.key_logic[item.player][item_dungeon].outside_keys += 1
    world.key_logic[item.player][item_dungeon].outside_keys_locations.add(location)


def track_dungeon_items(item, location, world):
    if location.parent_region.dungeon and not item.crystal:
        layout = world.dungeon_layouts[location.player][location.parent_region.dungeon.name]
        if is_dungeon_item(item, world) and item.player == location.player:
            layout.dungeon_items -= 1
        else:
            layout.free_items -= 1


def is_dungeon_item(item, world):
    return ((item.smallkey and world.keyshuffle[item.player] == 'none')
            or (item.bigkey and not world.bigkeyshuffle[item.player])
            or (item.compass and not world.compassshuffle[item.player])
            or (item.map and not world.mapshuffle[item.player]))


def recovery_placement(item_to_place, locations, world, state, base_state, itempool, perform_access_check, attempted,
                       key_pool=None, single_player_placement=False):
    logging.getLogger('').debug(f'Could not place {item_to_place} attempting recovery')
    if world.algorithm in ['balanced', 'equitable']:
        return last_ditch_placement(item_to_place, locations, world, state, base_state, itempool, key_pool,
                                    single_player_placement)
    elif world.algorithm == 'vanilla_fill':
        if item_to_place.type == 'Crystal':
            possible_swaps = [x for x in state.locations_checked if x.item.type == 'Crystal']
            return try_possible_swaps(possible_swaps, item_to_place, locations, world, base_state, itempool,
                                      key_pool, single_player_placement)
        else:
            i, config = 0, world.item_pool_config
            tried = set(attempted)
            if not item_to_place.is_inside_dungeon_item(world):
                while i < len(config.location_groups[item_to_place.player]):
                    fallback_locations = config.location_groups[item_to_place.player][i].locations
                    other_locs = [x for x in locations if x.name in fallback_locations]
                    for location in other_locs:
                        spot_to_fill = verify_spot_to_fill(location, item_to_place, state, single_player_placement,
                                                           perform_access_check, key_pool, world)
                        if spot_to_fill:
                            return spot_to_fill
                    i += 1
                    tried.update(other_locs)
            else:
               other_locations = vanilla_fallback(item_to_place, locations, world)
               for location in other_locations:
                   spot_to_fill = verify_spot_to_fill(location, item_to_place, state, single_player_placement,
                                                      perform_access_check, key_pool, world)
                   if spot_to_fill:
                       return spot_to_fill
               tried.update(other_locations)
            other_locations = [x for x in locations if x not in tried]
            for location in other_locations:
                spot_to_fill = verify_spot_to_fill(location, item_to_place, state, single_player_placement,
                                                   perform_access_check, key_pool, world)
                if spot_to_fill:
                    return spot_to_fill
            return None
    # explicitly fail these cases
    elif world.algorithm in ['dungeon_only', 'major_only']:
        raise FillError(f'Rare placement for {world.algorithm} detected. {item_to_place} unable to be placed.'
                        f' Try a different seed')
    else:
        other_locations = [x for x in locations if x not in attempted]
        for location in other_locations:
            spot_to_fill = verify_spot_to_fill(location, item_to_place, state, single_player_placement,
                                               perform_access_check, key_pool, world)
            if spot_to_fill:
                return spot_to_fill
    return None


def last_ditch_placement(item_to_place, locations, world, state, base_state, itempool,
                         key_pool=None, single_player_placement=False):
    def location_preference(loc):
        if not loc.item.advancement:
            return 1
        if loc.item.type and loc.item.type != 'Sword':
            if loc.item.type in ['Map', 'Compass']:
                return 2
            else:
                return 3
        return 4

    if item_to_place.type == 'Crystal':
        possible_swaps = [x for x in state.locations_checked if x.item.type == 'Crystal']
    else:
        possible_swaps = [x for x in state.locations_checked
                          if x.item.type not in ['Event', 'Crystal'] and not x.forced_item and not x.locked]
    swap_locations = sorted(possible_swaps, key=location_preference)
    return try_possible_swaps(swap_locations, item_to_place, locations, world, base_state, itempool,
                              key_pool, single_player_placement)


def try_possible_swaps(swap_locations, item_to_place, locations, world, base_state, itempool,
                       key_pool=None, single_player_placement=False):
    for location in swap_locations:
        old_item = location.item
        new_pool = list(itempool) + [old_item]
        new_spot = find_spot_for_item(item_to_place, [location], world, base_state, new_pool,
                                      key_pool, single_player_placement)
        if new_spot:
            restore_item = new_spot.item
            new_spot.item = item_to_place
            swap_spot = find_spot_for_item(old_item, locations, world, base_state, itempool,
                                           key_pool, single_player_placement)
            if swap_spot:
                logging.getLogger('').debug(f'Swapping {old_item} for {item_to_place}')
                world.push_item(swap_spot, old_item, False)
                swap_spot.event = True
                locations.remove(swap_spot)
                locations.append(new_spot)
                return new_spot
            else:
                new_spot.item = restore_item
        else:
            location.item = old_item
    return None


def find_spot_for_item(item_to_place, locations, world, base_state, pool,
                       keys_in_itempool=None, single_player_placement=False):
    def sweep_from_pool():
        new_state = base_state.copy()
        for item in pool:
            new_state.collect(item, True)
        new_state.sweep_for_events()
        return new_state
    for location in locations:
        maximum_exploration_state = sweep_from_pool()
        perform_access_check = True
        old_item = None
        if world.accessibility[item_to_place.player] == 'none':
            perform_access_check = not world.has_beaten_game(maximum_exploration_state, item_to_place.player) if single_player_placement else not world.has_beaten_game(maximum_exploration_state)

        if item_to_place.smallkey or item_to_place.bigkey:  # a better test to see if a key can go there
            old_item = location.item
            location.item = item_to_place
            test_state = maximum_exploration_state.copy()
            test_state.stale[item_to_place.player] = True
        else:
            test_state = maximum_exploration_state
        if (not single_player_placement or location.player == item_to_place.player) \
             and location.can_fill(test_state, item_to_place, perform_access_check) \
             and valid_key_placement(item_to_place, location,
                                     pool if (keys_in_itempool and keys_in_itempool[item_to_place.player]) else world.itempool,
                                     test_state, world):
            return location
        if item_to_place.smallkey or item_to_place.bigkey:
            location.item = old_item
    return None


def distribute_items_restrictive(world, gftower_trash=False, fill_locations=None):
    # If not passed in, then get a shuffled list of locations to fill in
    if not fill_locations:
        fill_locations = world.get_unfilled_locations()
        random.shuffle(fill_locations)

    # get items to distribute
    classify_major_items(world)
    # handle pot shuffle
    pots_used = False
    pot_item_pool = collections.defaultdict(list)
    for item in world.itempool:
        if item.name in ['Chicken', 'Big Magic']:  # can only fill these in that players world
            pot_item_pool[item.player].append(item)
    for player, pot_pool in pot_item_pool.items():
        if pot_pool:
            for pot_item in pot_pool:
                world.itempool.remove(pot_item)
            pot_locations = [location for location in fill_locations
                             if location.type == LocationType.Pot and location.player == player]
            pot_locations = filter_pot_locations(pot_locations, world)
            fast_fill_helper(world, pot_pool, pot_locations)
            pots_used = True
    if pots_used:
        fill_locations = world.get_unfilled_locations()
        random.shuffle(fill_locations)

    random.shuffle(world.itempool)
    config_sort(world)
    progitempool = [item for item in world.itempool if item.advancement]
    prioitempool = [item for item in world.itempool if not item.advancement and item.priority]
    restitempool = [item for item in world.itempool if not item.advancement and not item.priority]

    gftower_trash &= world.algorithm in ['balanced', 'equitable', 'dungeon_only']
    # dungeon only may fill up the dungeon... and push items out into the overworld

    # fill in gtower locations with trash first
    for player in range(1, world.players + 1):
        if (not gftower_trash or not world.ganonstower_vanilla[player]
           or world.logic[player] in ['owglitches', 'nologic']):
            continue
        gt_count, total_count = calc_trash_locations(world, player)
        scale_factor = .75 * (world.crystals_needed_for_gt[player] / 7)
        if world.algorithm == 'dungeon_only':
            reserved_space = sum(1 for i in progitempool+prioitempool if i.player == player)
            max_trash = max(0, min(gt_count, total_count - reserved_space))
        else:
            max_trash = gt_count
        scaled_trash = math.floor(max_trash * scale_factor)
        if world.goal[player] in ['triforcehunt', 'trinity', 'ganonhunt'] or world.algorithm == 'dungeon_only':
            gftower_trash_count = random.randint(scaled_trash, max_trash)
        else:
            gftower_trash_count = random.randint(0, scaled_trash)

        gtower_locations = [location for location in fill_locations if location.parent_region.dungeon
                            and location.parent_region.dungeon.name == 'Ganons Tower' and location.player == player]
        random.shuffle(gtower_locations)
        trashcnt = 0
        while gtower_locations and restitempool and trashcnt < gftower_trash_count:
            spot_to_fill = gtower_locations.pop()
            item_to_place = restitempool.pop()
            world.push_item(spot_to_fill, item_to_place, False)
            fill_locations.remove(spot_to_fill)
            trashcnt += 1

    random.shuffle(fill_locations)
    fill_locations.reverse()

    # Make sure the escape keys ire placed first in standard to prevent running out of spots
    def std_item_sort(item):
        if world.mode[item.player] == 'standard':
            if item.name == 'Small Key (Escape)':
                return 1
            if item.name == 'Big Key (Escape)':
                return 2
        return 0

    progitempool.sort(key=std_item_sort)
    key_pool = [x for x in progitempool if x.smallkey]

    # sort maps and compasses to the back -- this may not be viable in equitable & ambrosia
    progitempool.sort(key=lambda item: 0 if item.map or item.compass else 1)
    if world.algorithm == 'vanilla_fill':
        fill_restrictive(world, world.state, fill_locations, progitempool, key_pool, vanilla=True)
    fill_restrictive(world, world.state, fill_locations, progitempool, key_pool)
    random.shuffle(fill_locations)
    if world.algorithm == 'balanced':
        fast_fill(world, prioitempool, fill_locations)
    elif world.algorithm == 'vanilla_fill':
        fast_vanilla_fill(world, prioitempool, fill_locations)
    elif world.algorithm in ['major_only', 'dungeon_only', 'district']:
        filtered_fill(world, prioitempool, fill_locations)
    else:  # just need to ensure dungeon items still get placed in dungeons
        fast_equitable_fill(world, prioitempool, fill_locations)
    # placeholder work
    if world.algorithm == 'district':
        random.shuffle(fill_locations)
        placeholder_items = [item for item in world.itempool if item.name == 'Rupee (1)']
        num_ph_items = len(placeholder_items)
        if num_ph_items > 0:
            placeholder_locations = filter_locations('Placeholder', fill_locations, world)
            num_ph_locations = len(placeholder_locations)
            if num_ph_items < num_ph_locations < len(fill_locations):
                for _ in range(num_ph_locations - num_ph_items):
                    placeholder_items.append(replace_trash_item(restitempool, 'Rupee (1)'))
            assert len(placeholder_items) == len(placeholder_locations)
            for i in placeholder_items:
                restitempool.remove(i)
            for l in placeholder_locations:
                fill_locations.remove(l)
            filtered_fill(world, placeholder_items, placeholder_locations)

    if world.players > 1:
        fast_fill_pot_for_multiworld(world, restitempool, fill_locations)
    if world.algorithm == 'vanilla_fill':
        fast_vanilla_fill(world, restitempool, fill_locations)
    else:
        fast_fill(world, restitempool, fill_locations)

    unplaced = [item.name for item in prioitempool + restitempool]
    unfilled = [location.name for location in fill_locations]
    if unplaced or unfilled:
        logging.warning('Unplaced items: %s - Unfilled Locations: %s', unplaced, unfilled)
    ensure_good_pots(world)


def config_sort(world):
    if world.item_pool_config.verify:
        config_sort_helper(world, world.item_pool_config.verify)
    elif world.item_pool_config.preferred:
        config_sort_helper(world, world.item_pool_config.preferred)


def config_sort_helper(world, sort_dict):
    pref = list(sort_dict.keys())
    pref_len = len(pref)
    world.itempool.sort(key=lambda i: pref_len - pref.index((i.name, i.player))
                        if (i.name, i.player) in sort_dict else 0)


def calc_trash_locations(world, player):
    total_count, gt_count = 0, 0
    for loc in world.get_locations():
        if (loc.player == player and loc.item is None
           and (loc.type not in {LocationType.Pot, LocationType.Drop, LocationType.Normal} or not loc.forced_item)
           and (loc.type != LocationType.Shop or world.shopsanity[player])
           and loc.parent_region.dungeon):
                total_count += 1
                if loc.parent_region.dungeon.name == 'Ganons Tower':
                    gt_count += 1
    return gt_count, total_count


def ensure_good_pots(world, write_skips=False):
    for loc in world.get_locations():
        if loc.item is None:
            loc.item = ItemFactory('Nothing', loc.player)
        # convert Arrows 5 and Nothing when necessary
        if (loc.item.name in {'Arrows (5)', 'Nothing'}
           and (loc.type != LocationType.Pot or loc.item.player != loc.player)):
            loc.item = ItemFactory(invalid_location_replacement[loc.item.name], loc.item.player)
        # can be placed here by multiworld balancing or shop balancing
        # change it to something normal for the player it got swapped to
        elif (loc.item.name in {'Chicken', 'Big Magic'}
              and (loc.type != LocationType.Pot or loc.item.player != loc.player)):
                if loc.type == LocationType.Pot:
                    loc.item.player = loc.player
                else:
                    loc.item = ItemFactory(invalid_location_replacement[loc.item.name], loc.player)
        # do the arrow retro check
        if world.bow_mode[loc.item.player].startswith('retro') and loc.item.name in {'Arrows (5)', 'Arrows (10)'}:
            loc.item = ItemFactory('Rupees (5)', loc.item.player)
        # don't write out all pots to spoiler
        if write_skips:
            if loc.type == LocationType.Pot and loc.item.name in valid_pot_items:
                loc.skip = True


invalid_location_replacement = {'Arrows (5)': 'Arrows (10)', 'Nothing':  'Rupees (5)',
                                'Chicken': 'Rupees (5)', 'Big Magic': 'Small Magic'}


def fast_fill_helper(world, item_pool, fill_locations):
    if world.algorithm == 'vanilla_fill':
        fast_vanilla_fill(world, item_pool, fill_locations)
    else:
        fast_fill(world, item_pool, fill_locations)
    # todo: other fast fill methods?


def fast_fill(world, item_pool, fill_locations):
    config = world.item_pool_config
    fast_pool = [x for x in item_pool if (x.name, x.player) not in config.restricted]
    filtered_pool = [x for x in item_pool if (x.name, x.player) in config.restricted]
    filtered_fill(world, filtered_pool, fill_locations)
    while fast_pool and fill_locations:
        spot_to_fill = fill_locations.pop()
        item_to_place = fast_pool.pop()
        world.push_item(spot_to_fill, item_to_place, False)
    item_pool.clear()
    item_pool.extend(filtered_pool)
    item_pool.extend(fast_pool)


def fast_fill_pot_for_multiworld(world, item_pool, fill_locations):
    pot_item_pool = collections.defaultdict(list)
    pot_fill_locations = collections.defaultdict(list)
    for item in item_pool:
        if item.name in valid_pot_items:
            pot_item_pool[item.player].append(item)
    for loc in fill_locations:
        if loc.type == LocationType.Pot:
            pot_fill_locations[loc.player].append(loc)
    for player in range(1, world.players+1):
        flex = 256 - world.pot_contents[player].multiworld_count
        fill_count = len(pot_fill_locations[player]) - flex
        if fill_count > 0:
            fill_spots = random.sample(pot_fill_locations[player], fill_count)
            fill_items = random.sample(pot_item_pool[player], fill_count)
            for x in fill_items:
                item_pool.remove(x)
            for x in fill_spots:
                fill_locations.remove(x)
            fast_fill(world, fill_items, fill_spots)


def filtered_fill(world, item_pool, fill_locations):
    while item_pool and fill_locations:
        item_to_place = item_pool.pop()
        item_locations = filter_locations(item_to_place, fill_locations, world)
        spot_to_fill = next(iter(item_locations))
        fill_locations.remove(spot_to_fill)
        world.push_item(spot_to_fill, item_to_place, False)

    # sweep once to pick up preplaced items
    world.state.sweep_for_events()


def fast_vanilla_fill(world, item_pool, fill_locations):
    next_item_pool = []
    while item_pool and fill_locations:
        item_to_place = item_pool.pop()
        locations = filter_locations(item_to_place, fill_locations, world, vanilla_skip=True)
        if len(locations):
            spot_to_fill = locations.pop()
            fill_locations.remove(spot_to_fill)
            world.push_item(spot_to_fill, item_to_place, False)
        else:
            next_item_pool.append(item_to_place)
    while next_item_pool and fill_locations:
        item_to_place = next_item_pool.pop()
        spot_to_fill = next(iter(filter_locations(item_to_place, fill_locations, world)))
        fill_locations.remove(spot_to_fill)
        world.push_item(spot_to_fill, item_to_place, False)


def filtered_equitable_fill(world, item_pool, fill_locations):
    while item_pool and fill_locations:
        item_to_place = item_pool.pop()
        item_locations = filter_locations(item_to_place, fill_locations, world)
        spot_to_fill = next(l for l in item_locations if valid_dungeon_placement(item_to_place, l, world))
        fill_locations.remove(spot_to_fill)
        world.push_item(spot_to_fill, item_to_place, False)
        track_dungeon_items(item_to_place, spot_to_fill, world)


def fast_equitable_fill(world, item_pool, fill_locations):
    while item_pool and fill_locations:
        item_to_place = item_pool.pop()
        spot_to_fill = next(l for l in fill_locations if valid_dungeon_placement(item_to_place, l, world))
        fill_locations.remove(spot_to_fill)
        world.push_item(spot_to_fill, item_to_place, False)
        track_dungeon_items(item_to_place, spot_to_fill, world)


def lock_shop_locations(world, player):
    for shop, loc_names in shop_to_location_table.items():
        for loc in loc_names:
            world.get_location(loc, player).locked = True


def sell_potions(world, player):
    loc_choices = []
    for shop in world.shops[player]:
        # potions are excluded from the cap fairy due to visual problem
        if shop.region.name in shop_to_location_table and shop.region.name != 'Capacity Upgrade':
            loc_choices += [world.get_location(loc, player) for loc in shop_to_location_table[shop.region.name]]
    locations = [loc for loc in loc_choices if not loc.item]
    for potion in ['Green Potion', 'Blue Potion', 'Red Potion']:
        location = random.choice(filter_locations(ItemFactory(potion, player), locations, world, potion=True))
        locations.remove(location)
        p_item = next((item for item in world.itempool if item.name == potion and item.player == player), None)
        if p_item:
            world.push_item(location, p_item, collect=False)
            world.itempool.remove(p_item)


def sell_keys(world, player):
    # exclude the old man or take any caves because free keys are too good
    shop_names = {shop.region.name: shop for shop in world.shops[player] if shop.region.name in shop_to_location_table}
    choices = [(world.get_location(loc, player), shop) for shop in shop_names for loc in shop_to_location_table[shop]]
    locations = [l for l, shop in choices]
    locations = filter_locations(ItemFactory('Small Key (Universal)', player), locations, world)
    locations = [(loc, shop) for loc, shop in choices if not loc.item and loc in locations]
    location, shop = random.choice(locations)
    universal_key = next(i for i in world.itempool if i.name == 'Small Key (Universal)' and i.player == player)
    world.push_item(location, universal_key, collect=False)
    idx = shop_to_location_table[shop_names[shop].region.name].index(location.name)
    shop_names[shop].add_inventory(idx, 'Small Key (Universal)', 100)
    world.itempool.remove(universal_key)


def verify(item_to_place, item_locations, state, spp, pac, key_pool, world):
    if world.item_pool_config.verify:
        logger = logging.getLogger('')
        item_name = 'Bottle' if item_to_place.name.startswith('Bottle') else item_to_place.name
        item_player = item_to_place.player
        config = world.item_pool_config
        if (item_name, item_player) in config.verify:
            tests = config.verify[(item_name, item_player)]
            issues = []
            for location in item_locations:
                if location.name in tests:
                    expected = tests[location.name]
                    spot = verify_spot_to_fill(location, item_to_place, state, spp, pac, key_pool, world)
                    if spot and (item_to_place.smallkey or item_to_place.bigkey):
                        location.item = None
                        location.event = False
                        if item_to_place.smallkey:
                            key_pool.append(item_to_place)
                    if (expected and spot) or (not expected and spot is None):
                        logger.debug(f'Placing {item_name} ({item_player}) at {location.name} was {expected}')
                        config.verify_count += 1
                        if config.verify_count >= config.verify_target:
                            exit()
                    else:
                        issues.append((item_name, item_player, location.name, expected))
            if len(issues) > 0:
                for name, player, loc, expected in issues:
                    if expected:
                        logger.error(f'Could not place {name} ({player}) at {loc}')
                    else:
                        logger.error(f'{name} ({player}) should not be allowed at {loc}')
                raise Exception(f'Test failed placing {name}')


def balance_multiworld_progression(world):
    state = CollectionState(world)
    checked_locations = set()
    unchecked_locations = set(world.get_locations())

    reachable_locations_count = {}
    for player in range(1, world.players + 1):
        reachable_locations_count[player] = 0

    def get_sphere_locations(sphere_state, locations):
        sphere_state.sweep_for_events(key_only=True, locations=locations)
        return {loc for loc in locations if sphere_state.can_reach(loc) and sphere_state.not_flooding_a_key(sphere_state.world, loc)}

    while True:
        sphere_locations = get_sphere_locations(state, unchecked_locations)
        for location in sphere_locations:
            unchecked_locations.remove(location)
            reachable_locations_count[location.player] += 1

        if checked_locations:
            threshold = max(reachable_locations_count.values()) - 20

            balancing_players = {player for player, reachables in reachable_locations_count.items() if reachables < threshold}
            if balancing_players:
                balancing_state = state.copy()
                balancing_unchecked_locations = unchecked_locations.copy()
                balancing_reachables = reachable_locations_count.copy()
                balancing_sphere = sphere_locations.copy()
                candidate_items = collections.defaultdict(set)
                while True:
                    for location in balancing_sphere:
                        if location.event and (world.keyshuffle[location.item.player] != 'none' or not location.item.smallkey) and (world.bigkeyshuffle[location.item.player] or not location.item.bigkey):
                            balancing_state.collect(location.item, True, location)
                            player = location.item.player
                            if player in balancing_players and not location.locked and location.player != player:
                                candidate_items[player].add(location)
                    balancing_sphere = get_sphere_locations(balancing_state, balancing_unchecked_locations)
                    for location in balancing_sphere:
                        balancing_unchecked_locations.remove(location)
                        balancing_reachables[location.player] += 1
                    if world.has_beaten_game(balancing_state) or all(reachables >= threshold for reachables in balancing_reachables.values()):
                        break
                    elif not balancing_sphere:
                        raise RuntimeError('Not all required items reachable. Something went terribly wrong here.')

                unlocked_locations = collections.defaultdict(set)
                for l in unchecked_locations:
                    if l not in balancing_unchecked_locations:
                        unlocked_locations[l.player].add(l)
                items_to_replace = []
                for player in balancing_players:
                    locations_to_test = unlocked_locations[player]
                    items_to_test = candidate_items[player]
                    while items_to_test:
                        testing = items_to_test.pop()
                        reducing_state = state.copy()
                        for location in itertools.chain((l for l in items_to_replace if l.item.player == player),
                                                        items_to_test):
                            reducing_state.collect(location.item, True, location)

                        reducing_state.sweep_for_events(locations=locations_to_test)

                        if world.has_beaten_game(balancing_state):
                            if not world.has_beaten_game(reducing_state):
                                items_to_replace.append(testing)
                        else:
                            reduced_sphere = get_sphere_locations(reducing_state, locations_to_test)
                            if reachable_locations_count[player] + len(reduced_sphere) < threshold:
                                items_to_replace.append(testing)

                replaced_items = False
                # sort then shuffle to maintain deterministic behaviour,
                # while allowing use of set for better algorithm growth behaviour elsewhere
                replacement_locations = sorted((l for l in checked_locations if not l.event and not l.locked),
                                               key=lambda loc: (loc.name, loc.player))
                random.shuffle(replacement_locations)
                items_to_replace.sort(key=lambda item: (item.name, item.player))
                random.shuffle(items_to_replace)
                while replacement_locations and items_to_replace:
                    old_location = items_to_replace.pop()
                    for new_location in replacement_locations:
                        if (new_location.can_fill(state, old_location.item, False) and
                           old_location.can_fill(state, new_location.item, False)):
                            replacement_locations.remove(new_location)
                            new_location.item, old_location.item = old_location.item, new_location.item
                            if world.shopsanity[new_location.player]:
                                check_shop_swap(new_location)
                            if world.shopsanity[old_location.player]:
                                check_shop_swap(old_location)
                            new_location.event, old_location.event = True, False
                            logging.debug(f"Progression balancing moved {new_location.item} to {new_location}, "
                                          f"displacing {old_location.item} into {old_location}")
                            state.collect(new_location.item, True, new_location)
                            replaced_items = True
                            break
                    else:
                        logging.warning(f"Could not Progression Balance {old_location.item}")

                if replaced_items:
                    unlocked = {fresh for player in balancing_players for fresh in unlocked_locations[player]}
                    for location in get_sphere_locations(state, unlocked):
                        unchecked_locations.remove(location)
                        reachable_locations_count[location.player] += 1
                        sphere_locations.add(location)

        for location in sphere_locations:
            if location.event and (world.keyshuffle[location.item.player] != 'none' or not location.item.smallkey) and (world.bigkeyshuffle[location.item.player] or not location.item.bigkey):
                state.collect(location.item, True, location)
        checked_locations |= sphere_locations

        if world.has_beaten_game(state):
            break
        elif not sphere_locations:
            raise RuntimeError('Not all required items reachable. Something went terribly wrong here.')


def check_shop_swap(l):
    if l.parent_region.name in shop_to_location_table:
        if l.name in shop_to_location_table[l.parent_region.name]:
            idx = shop_to_location_table[l.parent_region.name].index(l.name)
            inv_slot = l.parent_region.shop.inventory[idx]
            inv_slot['item'] = l.item.name
    elif l.parent_region in retro_shops:
        idx = retro_shops[l.parent_region.name].index(l.name)
        inv_slot = l.parent_region.shop.inventory[idx]
        inv_slot['item'] = l.item.name


def balance_money_progression(world):
    logger = logging.getLogger('')
    state = CollectionState(world)
    unchecked_locations = world.get_locations().copy()
    wallet = {player: 0 for player in range(1, world.players+1)}
    kiki_check = {player: False for player in range(1, world.players+1)}
    kiki_paid = {player: False for player in range(1, world.players+1)}
    rooms_visited = {player: set() for player in range(1, world.players+1)}
    balance_locations = {player: set() for player in range(1, world.players+1)}

    pay_for_locations = {'Bottle Merchant': 100, 'Chest Game': 30, 'Digging Game': 80,
                         'King Zora': 500, 'Blacksmith': 10}
    rupee_chart = {'Rupee (1)': 1, 'Rupees (5)': 5, 'Rupees (20)': 20, 'Rupees (50)': 50,
                   'Rupees (100)': 100, 'Rupees (300)': 300}
    rupee_rooms = {'Eastern Rupees': 90, 'Mire Key Rupees': 45, 'Mire Shooter Rupees': 90,
                   'TR Rupees': 270, 'PoD Dark Basement': 270}
    acceptable_balancers = ['Bombs (3)', 'Arrows (10)', 'Bombs (10)']

    base_value = sum(rupee_rooms.values())
    available_money = {player: base_value for player in range(1, world.players+1)}
    for loc in world.get_locations():
        if loc.item and loc.item.name in rupee_chart:
            available_money[loc.item.player] += rupee_chart[loc.item.name]

    total_price = {player: 0 for player in range(1, world.players+1)}
    for player in range(1, world.players+1):
        for shop, loc_list in shop_to_location_table.items():
            for loc in loc_list:
                loc = world.get_location(loc, player)
                slot = shop_to_location_table[loc.parent_region.name].index(loc.name)
                shop = loc.parent_region.shop
                shop_item = shop.inventory[slot]
                if shop_item:
                    total_price[player] += shop_item['price']
        total_price[player] += 110 + sum(pay_for_locations.values())
    # base needed: 830
    # base available: 765

    for player in range(1, world.players+1):
        logger.debug(f'Money balance for P{player}: Needed: {total_price[player]} Available: {available_money[player]}')

    def get_sphere_locations(sphere_state, locations):
        sphere_state.sweep_for_events(key_only=True, locations=locations)
        return [loc for loc in locations if sphere_state.can_reach(loc) and sphere_state.not_flooding_a_key(sphere_state.world, loc)]

    def interesting_item(location, item, world, player):
        if item.advancement:
            return True
        if item.type is not None or item.name.startswith('Rupee'):
            return True
        if item.name in ['Progressive Armor', 'Blue Mail', 'Red Mail']:
            return True
        if world.keyshuffle[player] == 'universal' and item.name == 'Small Key (Universal)':
            return True
        if world.bow_mode[player].startswith('retro') and item.name == 'Single Arrow':
            return True
        if location.name in pay_for_locations:
            return True
        return False

    def kiki_required(state, location):
        path = state.path[location.parent_region]
        if path:
            while path[1]:
                if path[0] == 'Palace of Darkness':
                    return True
                path = path[1]
        return False

    done = False
    while not done:
        sphere_costs = {player: 0 for player in range(1, world.players+1)}
        locked_by_money = {player: set() for player in range(1, world.players+1)}
        sphere_locations = get_sphere_locations(state, unchecked_locations)
        checked_locations = []
        for player in range(1, world.players+1):
            kiki_payable = state.prog_items[('Moon Pearl', player)] > 0 or world.mode[player] == 'inverted'
            if kiki_payable and world.get_region('East Dark World', player) in state.reachable_regions[player]:
                if not kiki_paid[player]:
                    kiki_check[player] = True
                    sphere_costs[player] += 110
                    locked_by_money[player].add('Kiki')
        for location in sphere_locations:
            location_free, loc_player = True, location.player
            if location.parent_region.name in shop_to_location_table and location.name != 'Potion Shop':
                slot = shop_to_location_table[location.parent_region.name].index(location.name)
                shop = location.parent_region.shop
                shop_item = shop.inventory[slot]
                if location.item and interesting_item(location, location.item, world, location.item.player):
                    if location.item.name.startswith('Rupee') and loc_player == location.item.player:
                        if shop_item['price'] < rupee_chart[location.item.name]:
                            wallet[loc_player] -= shop_item['price']  # will get picked up in the location_free block
                        else:
                            location_free = False
                    else:
                        location_free = False
                        sphere_costs[loc_player] += shop_item['price']
                        locked_by_money[loc_player].add(location)
            elif location.name in pay_for_locations:
                sphere_costs[loc_player] += pay_for_locations[location.name]
                location_free = False
                locked_by_money[loc_player].add(location)
            if kiki_check[loc_player] and not kiki_paid[loc_player] and kiki_required(state, location):
                locked_by_money[loc_player].add(location)
                location_free = False
            if location_free:
                state.collect(location.item, True, location)
                unchecked_locations.remove(location)
                if location.item:
                    if location.item.name.startswith('Rupee'):
                        wallet[location.item.player] += rupee_chart[location.item.name]
                        if location.item.name != 'Rupees (300)':
                            balance_locations[location.item.player].add(location)
                    if interesting_item(location, location.item, world, location.item.player):
                        checked_locations.append(location)
                    elif location.item.name in acceptable_balancers:
                        balance_locations[location.item.player].add(location)
        for room, income in rupee_rooms.items():
            for player in range(1, world.players+1):
                if room not in rooms_visited[player] and world.get_region(room, player) in state.reachable_regions[player]:
                    wallet[player] += income
                    rooms_visited[player].add(room)
        if checked_locations or len(unchecked_locations) == 0:
            if world.has_beaten_game(state):
                done = True
                continue
            # else go to next sphere
        else:
            # check for solvent players
            solvent = set()
            insolvent = set()
            for player in range(1, world.players+1):
                if wallet[player] >= sphere_costs[player] >= 0:
                    solvent.add(player)
                if sphere_costs[player] > 0 and sphere_costs[player] > wallet[player]:
                    insolvent.add(player)
            if len([p for p in solvent if len(locked_by_money[p]) > 0]) == 0:
                if len(insolvent) > 0:
                    target_player = min(insolvent, key=lambda p: sphere_costs[p]-wallet[p])
                    difference = sphere_costs[target_player]-wallet[target_player]
                    logger.debug(f'Money balancing needed: Player {target_player} short {difference}')
                else:
                    difference = 0
                while difference > 0:
                    swap_targets = [x for x in unchecked_locations if x not in sphere_locations and x.item.name.startswith('Rupees') and x.item.player == target_player]
                    if len(swap_targets) == 0:
                        best_swap, best_value = None, 300
                    else:
                        best_swap = max(swap_targets, key=lambda t: rupee_chart[t.item.name])
                        best_value = rupee_chart[best_swap.item.name]
                    increase_targets = [x for x in balance_locations[target_player] if x.item.name in rupee_chart and rupee_chart[x.item.name] < best_value]
                    if len(increase_targets) == 0:
                        increase_targets = [x for x in balance_locations[target_player] if (rupee_chart[x.item.name] if x.item.name in rupee_chart else 0) < best_value]
                    if len(increase_targets) == 0:
                        raise Exception('No early sphere swaps for rupees - money grind would be required - bailing for now')
                    best_target = min(increase_targets, key=lambda t: rupee_chart[t.item.name] if t.item.name in rupee_chart else 0)
                    old_value = rupee_chart[best_target.item.name] if best_target.item.name in rupee_chart else 0
                    if best_swap is None:
                        logger.debug(f'Upgrading {best_target.item.name} @ {best_target.name} for 300 Rupees')
                        best_target.item = ItemFactory('Rupees (300)', best_target.item.player)
                        best_target.item.location = best_target
                        check_shop_swap(best_target.item.location)
                    else:
                        old_item = best_target.item
                        logger.debug(f'Swapping {best_target.item.name} @ {best_target.name} for {best_swap.item.name} @ {best_swap.name}')
                        best_target.item = best_swap.item
                        best_target.item.location = best_target
                        best_swap.item = old_item
                        best_swap.item.location = best_swap
                        check_shop_swap(best_target.item.location)
                        check_shop_swap(best_swap.item.location)
                    increase = best_value - old_value
                    difference -= increase
                    wallet[target_player] += increase
                solvent.add(target_player)
            # apply solvency
            for player in solvent:
                wallet[player] -= sphere_costs[player]
                for location in locked_by_money[player]:
                    if isinstance(location, str) and location == 'Kiki':
                        kiki_paid[player] = True
                    else:
                        state.collect(location.item, True, location)
                        unchecked_locations.remove(location)
                        if location.item and location.item.name.startswith('Rupee'):
                            wallet[location.item.player] += rupee_chart[location.item.name]
