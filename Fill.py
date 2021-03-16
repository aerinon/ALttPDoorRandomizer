import random
import logging

from BaseClasses import CollectionState
from Items import ItemFactory
from Regions import shop_to_location_table


class FillError(RuntimeError):
    pass

def distribute_items_cutoff(world, cutoffrate=0.33):
    # get list of locations to fill in
    fill_locations = world.get_unfilled_locations()
    random.shuffle(fill_locations)

    # get items to distribute
    random.shuffle(world.itempool)
    itempool = world.itempool

    total_advancement_items = len([item for item in itempool if item.advancement])
    placed_advancement_items = 0

    progress_done = False
    advancement_placed = False

    # sweep once to pick up preplaced items
    world.state.sweep_for_events()

    while itempool and fill_locations:
        candidate_item_to_place = None
        item_to_place = None
        for item in itempool:
            if advancement_placed or (progress_done and (item.advancement or item.priority)):
                item_to_place = item
                break
            if item.advancement:
                candidate_item_to_place = item
                if world.unlocks_new_location(item):
                    item_to_place = item
                    placed_advancement_items += 1
                    break

        if item_to_place is None:
            # check if we can reach all locations and that is why we find no new locations to place
            if not progress_done and len(world.get_reachable_locations()) == len(world.get_locations()):
                progress_done = True
                continue
            # check if we have now placed all advancement items
            if progress_done:
                advancement_placed = True
                continue
            # we might be in a situation where all new locations require multiple items to reach. If that is the case, just place any advancement item we've found and continue trying
            if candidate_item_to_place is not None:
                item_to_place = candidate_item_to_place
                placed_advancement_items += 1
            else:
                # we placed all available progress items. Maybe the game can be beaten anyway?
                if world.can_beat_game():
                    logging.getLogger('').warning('Not all locations reachable. Game beatable anyway.')
                    progress_done = True
                    continue
                raise FillError('No more progress items left to place.')

        spot_to_fill = None
        for location in fill_locations if placed_advancement_items / total_advancement_items < cutoffrate else reversed(fill_locations):
            if location.can_fill(world.state, item_to_place):
                spot_to_fill = location
                break

        if spot_to_fill is None:
            # we filled all reachable spots. Maybe the game can be beaten anyway?
            if world.can_beat_game():
                logging.getLogger('').warning('Not all items placed. Game beatable anyway.')
                break
            raise FillError('No more spots to place %s' % item_to_place)

        world.push_item(spot_to_fill, item_to_place, True)
        itempool.remove(item_to_place)
        fill_locations.remove(spot_to_fill)
    unplaced = [item.name for item in itempool]
    unfilled = [location.name for location in fill_locations]
    if unplaced or unfilled:
        logging.warning('Unplaced items: %s - Unfilled Locations: %s', unplaced, unfilled)


def distribute_items_staleness(world):
    # get list of locations to fill in
    fill_locations = world.get_unfilled_locations()
    random.shuffle(fill_locations)

    # get items to distribute
    random.shuffle(world.itempool)
    itempool = world.itempool

    progress_done = False
    advancement_placed = False

    # sweep once to pick up preplaced items
    world.state.sweep_for_events()

    while itempool and fill_locations:
        candidate_item_to_place = None
        item_to_place = None
        for item in itempool:
            if advancement_placed or (progress_done and (item.advancement or item.priority)):
                item_to_place = item
                break
            if item.advancement:
                candidate_item_to_place = item
                if world.unlocks_new_location(item):
                    item_to_place = item
                    break

        if item_to_place is None:
            # check if we can reach all locations and that is why we find no new locations to place
            if not progress_done and len(world.get_reachable_locations()) == len(world.get_locations()):
                progress_done = True
                continue
            # check if we have now placed all advancement items
            if progress_done:
                advancement_placed = True
                continue
            # we might be in a situation where all new locations require multiple items to reach. If that is the case, just place any advancement item we've found and continue trying
            if candidate_item_to_place is not None:
                item_to_place = candidate_item_to_place
            else:
                # we placed all available progress items. Maybe the game can be beaten anyway?
                if world.can_beat_game():
                    logging.getLogger('').warning('Not all locations reachable. Game beatable anyway.')
                    progress_done = True
                    continue
                raise FillError('No more progress items left to place.')

        spot_to_fill = None
        for location in fill_locations:
            # increase likelyhood of skipping a location if it has been found stale
            if not progress_done and random.randint(0, location.staleness_count) > 2:
                continue

            if location.can_fill(world.state, item_to_place):
                spot_to_fill = location
                break
            else:
                location.staleness_count += 1

        # might have skipped too many locations due to potential staleness. Do not check for staleness now to find a candidate
        if spot_to_fill is None:
            for location in fill_locations:
                if location.can_fill(world.state, item_to_place):
                    spot_to_fill = location
                    break

        if spot_to_fill is None:
            # we filled all reachable spots. Maybe the game can be beaten anyway?
            if world.can_beat_game():
                logging.getLogger('').warning('Not all items placed. Game beatable anyway.')
                break
            raise FillError('No more spots to place %s' % item_to_place)

        world.push_item(spot_to_fill, item_to_place, True)
        itempool.remove(item_to_place)
        fill_locations.remove(spot_to_fill)

    unplaced = [item.name for item in itempool]
    unfilled = [location.name for location in fill_locations]
    if unplaced or unfilled:
        logging.warning('Unplaced items: %s - Unfilled Locations: %s', unplaced, unfilled)

def fill_restrictive(world, base_state, locations, itempool, keys_in_itempool = None, single_player_placement = False):
    def sweep_from_pool():
        new_state = base_state.copy()
        for item in itempool:
            new_state.collect(item, True)
        new_state.sweep_for_events()
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

            maximum_exploration_state = sweep_from_pool()
            has_beaten_game = world.has_beaten_game(maximum_exploration_state)

            for item_to_place in items_to_place:
                perform_access_check = True
                if world.accessibility[item_to_place.player] == 'none':
                    perform_access_check = not world.has_beaten_game(maximum_exploration_state, item_to_place.player) if single_player_placement else not has_beaten_game

                spot_to_fill = None

                for location in locations:
                    if item_to_place.smallkey or item_to_place.bigkey:  # a better test to see if a key can go there
                        location.item = item_to_place
                        test_state = maximum_exploration_state.copy()
                        test_state.stale[item_to_place.player] = True
                    else:
                        test_state = maximum_exploration_state
                    if (not single_player_placement or location.player == item_to_place.player)\
                            and location.can_fill(test_state, item_to_place, perform_access_check)\
                            and valid_key_placement(item_to_place, location, itempool if (keys_in_itempool and keys_in_itempool[item_to_place.player]) else world.itempool, world):
                        spot_to_fill = location
                        break
                    elif item_to_place.smallkey or item_to_place.bigkey:
                        location.item = None

                if spot_to_fill is None:
                    # we filled all reachable spots. Maybe the game can be beaten anyway?
                    unplaced_items.insert(0, item_to_place)
                    if world.can_beat_game():
                        if world.accessibility[item_to_place.player] != 'none':
                            logging.getLogger('').warning('Not all items placed. Game beatable anyway. (Could not place %s)' % item_to_place)
                        continue
                    raise FillError('No more spots to place %s' % item_to_place)

                world.push_item(spot_to_fill, item_to_place, False)
                track_outside_keys(item_to_place, spot_to_fill, world)
                locations.remove(spot_to_fill)
                spot_to_fill.event = True

    itempool.extend(unplaced_items)


def valid_key_placement(item, location, itempool, world):
    if (not item.smallkey and not item.bigkey) or item.player != location.player or world.retro[item.player] or world.logic[item.player] == 'nologic':
        return True
    dungeon = location.parent_region.dungeon
    if dungeon:
        if dungeon.name not in item.name and (dungeon.name != 'Hyrule Castle' or 'Escape' not in item.name):
            return True
        key_logic = world.key_logic[item.player][dungeon.name]
        unplaced_keys = len([x for x in itempool if x.name == key_logic.small_key_name and x.player == item.player])
        return key_logic.check_placement(unplaced_keys, location if item.bigkey else None)
    else:
        inside_dungeon_item = ((item.smallkey and not world.keyshuffle[item.player])
                               or (item.bigkey and not world.bigkeyshuffle[item.player]))
        return not inside_dungeon_item


def track_outside_keys(item, location, world):
    if not item.smallkey:
        return
    item_dungeon = item.name.split('(')[1][:-1]
    if item_dungeon == 'Escape':
        item_dungeon = 'Hyrule Castle'
    if location.player == item.player:
        loc_dungeon = location.parent_region.dungeon
        if loc_dungeon and loc_dungeon.name == item_dungeon:
            return  # this is an inside key
    world.key_logic[item.player][item_dungeon].outside_keys += 1


def distribute_items_restrictive(world, gftower_trash=False, fill_locations=None):
    # If not passed in, then get a shuffled list of locations to fill in
    if not fill_locations:
        fill_locations = world.get_unfilled_locations()
        random.shuffle(fill_locations)

    # get items to distribute
    random.shuffle(world.itempool)
    progitempool = [item for item in world.itempool if item.advancement]
    prioitempool = [item for item in world.itempool if not item.advancement and item.priority]
    restitempool = [item for item in world.itempool if not item.advancement and not item.priority]

    # fill in gtower locations with trash first
    for player in range(1, world.players + 1):
        if not gftower_trash or not world.ganonstower_vanilla[player] or world.doorShuffle[player] == 'crossed':
            continue

        gftower_trash_count = (random.randint(15, 50) if world.goal[player] == 'triforcehunt' else random.randint(0, 15))

        gtower_locations = [location for location in fill_locations if 'Ganons Tower' in location.name and location.player == player]
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

    # Make sure the escape small key is placed first in standard with key shuffle to prevent running out of spots
    # todo: crossed
    progitempool.sort(key=lambda item: 1 if item.name == 'Small Key (Escape)' and world.keyshuffle[item.player] and world.mode[item.player] == 'standard' else 0)

    fill_restrictive(world, world.state, fill_locations, progitempool,
                     keys_in_itempool={player: world.keyshuffle[player] for player in range(1, world.players + 1)})

    random.shuffle(fill_locations)

    fast_fill(world, prioitempool, fill_locations)

    fast_fill(world, restitempool, fill_locations)

    unplaced = [item.name for item in prioitempool + restitempool]
    unfilled = [location.name for location in fill_locations]
    if unplaced or unfilled:
        logging.warning('Unplaced items: %s - Unfilled Locations: %s', unplaced, unfilled)

def fast_fill(world, item_pool, fill_locations):
    while item_pool and fill_locations:
        spot_to_fill = fill_locations.pop()
        item_to_place = item_pool.pop()
        world.push_item(spot_to_fill, item_to_place, False)


def flood_items(world):
    # get items to distribute
    random.shuffle(world.itempool)
    itempool = world.itempool
    progress_done = False

    # sweep once to pick up preplaced items
    world.state.sweep_for_events()

    # fill world from top of itempool while we can
    while not progress_done:
        location_list = world.get_unfilled_locations()
        random.shuffle(location_list)
        spot_to_fill = None
        for location in location_list:
            if location.can_fill(world.state, itempool[0]):
                spot_to_fill = location
                break

        if spot_to_fill:
            item = itempool.pop(0)
            world.push_item(spot_to_fill, item, True)
            continue

        # ran out of spots, check if we need to step in and correct things
        if len(world.get_reachable_locations()) == len(world.get_locations()):
            progress_done = True
            continue

        # need to place a progress item instead of an already placed item, find candidate
        item_to_place = None
        candidate_item_to_place = None
        for item in itempool:
            if item.advancement:
                candidate_item_to_place = item
                if world.unlocks_new_location(item):
                    item_to_place = item
                    break

        # we might be in a situation where all new locations require multiple items to reach. If that is the case, just place any advancement item we've found and continue trying
        if item_to_place is None:
            if candidate_item_to_place is not None:
                item_to_place = candidate_item_to_place
            else:
                raise FillError('No more progress items left to place.')

        # find item to replace with progress item
        location_list = world.get_reachable_locations()
        random.shuffle(location_list)
        for location in location_list:
            if location.item is not None and not location.item.advancement and not location.item.priority and not location.item.smallkey and not location.item.bigkey:
                # safe to replace
                replace_item = location.item
                replace_item.location = None
                itempool.append(replace_item)
                world.push_item(location, item_to_place, True)
                itempool.remove(item_to_place)
                break


def lock_shop_locations(world, player):
    for shop, loc_names in shop_to_location_table.items():
        for loc in loc_names:
            world.get_location(loc, player).event = True
            world.get_location(loc, player).locked = True
    # I don't believe these locations exist in non-shopsanity
    # if world.retro[player]:
    #     for shop, loc_names in retro_shops.items():
    #         for loc in loc_names:
    #             world.get_location(loc, player).event = True
    #             world.get_location(loc, player).locked = True


def sell_potions(world, player):
    loc_choices = []
    for shop in world.shops[player]:
        # potions are excluded from the cap fairy due to visual problem
        if shop.region.name in shop_to_location_table and shop.region.name != 'Capacity Upgrade':
            loc_choices += [world.get_location(loc, player) for loc in shop_to_location_table[shop.region.name]]
    locations = [loc for loc in loc_choices if not loc.item]
    for potion in ['Green Potion', 'Blue Potion', 'Red Potion']:
        location = random.choice(locations)
        locations.remove(location)
        p_item = next(item for item in world.itempool if item.name == potion and item.player == player)
        world.push_item(location, p_item, collect=False)
        world.itempool.remove(p_item)


def sell_keys(world, player):
    # exclude the old man or take any caves because free keys are too good
    shop_names = {shop.region.name: shop for shop in world.shops[player] if shop.region.name in shop_to_location_table}
    choices = [(world.get_location(loc, player), shop) for shop in shop_names for loc in shop_to_location_table[shop]]
    locations = [(loc, shop) for loc, shop in choices if not loc.item]
    location, shop = random.choice(locations)
    universal_key = next(i for i in world.itempool if i.name == 'Small Key (Universal)' and i.player == player)
    world.push_item(location, universal_key, collect=False)
    idx = shop_to_location_table[shop_names[shop].region.name].index(location.name)
    shop_names[shop].add_inventory(idx, 'Small Key (Universal)', 100)
    world.itempool.remove(universal_key)


def balance_multiworld_progression(world):
    state = CollectionState(world)
    checked_locations = []
    unchecked_locations = world.get_locations().copy()
    random.shuffle(unchecked_locations)

    reachable_locations_count = {}
    for player in range(1, world.players + 1):
        reachable_locations_count[player] = 0

    def get_sphere_locations(sphere_state, locations):
        sphere_state.sweep_for_events(key_only=True, locations=locations)
        return [loc for loc in locations if sphere_state.can_reach(loc) and sphere_state.not_flooding_a_key(sphere_state.world, loc)]

    while True:
        sphere_locations = get_sphere_locations(state, unchecked_locations)
        for location in sphere_locations:
            unchecked_locations.remove(location)
            reachable_locations_count[location.player] += 1

        if checked_locations:
            threshold = max(reachable_locations_count.values()) - 20

            balancing_players = [player for player, reachables in reachable_locations_count.items() if reachables < threshold]
            if balancing_players is not None and len(balancing_players) > 0:
                balancing_state = state.copy()
                balancing_unchecked_locations = unchecked_locations.copy()
                balancing_reachables = reachable_locations_count.copy()
                balancing_sphere = sphere_locations.copy()
                candidate_items = []
                while True:
                    for location in balancing_sphere:
                        if location.event and (world.keyshuffle[location.item.player] or not location.item.smallkey) and (world.bigkeyshuffle[location.item.player] or not location.item.bigkey):
                            balancing_state.collect(location.item, True, location)
                            if location.item.player in balancing_players and not location.locked:
                                candidate_items.append(location)
                    balancing_sphere = get_sphere_locations(balancing_state, balancing_unchecked_locations)
                    for location in balancing_sphere:
                        balancing_unchecked_locations.remove(location)
                        balancing_reachables[location.player] += 1
                    if world.has_beaten_game(balancing_state) or all([reachables >= threshold for reachables in balancing_reachables.values()]):
                        break
                    elif not balancing_sphere:
                        raise RuntimeError('Not all required items reachable. Something went terribly wrong here.')

                unlocked_locations = [l for l in unchecked_locations if l not in balancing_unchecked_locations]
                items_to_replace = []
                for player in balancing_players:
                    locations_to_test = [l for l in unlocked_locations if l.player == player]
                    # only replace items that end up in another player's world
                    items_to_test = [l for l in candidate_items if l.item.player == player and l.player != player]
                    while items_to_test:
                        testing = items_to_test.pop()
                        reducing_state = state.copy()
                        for location in [*[l for l in items_to_replace if l.item.player == player], *items_to_test]:
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
                replacement_locations = [l for l in checked_locations if not l.event and not l.locked]
                while replacement_locations and items_to_replace:
                    new_location = replacement_locations.pop()
                    old_location = items_to_replace.pop()

                    while not new_location.can_fill(state, old_location.item, False) or (new_location.item and not old_location.can_fill(state, new_location.item, False)):
                        replacement_locations.insert(0, new_location)
                        new_location = replacement_locations.pop()

                    new_location.item, old_location.item = old_location.item, new_location.item
                    new_location.event, old_location.event = True, False
                    state.collect(new_location.item, True, new_location)
                    replaced_items = True
                if replaced_items:
                    for location in get_sphere_locations(state, [l for l in unlocked_locations if l.player in balancing_players]):
                        unchecked_locations.remove(location)
                        reachable_locations_count[location.player] += 1
                        sphere_locations.append(location)

        for location in sphere_locations:
            if location.event and (world.keyshuffle[location.item.player] or not location.item.smallkey) and (world.bigkeyshuffle[location.item.player] or not location.item.bigkey):
                state.collect(location.item, True, location)
        checked_locations.extend(sphere_locations)

        if world.has_beaten_game(state):
            break
        elif not sphere_locations:
            raise RuntimeError('Not all required items reachable. Something went terribly wrong here.')


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
        if world.retro[player] and (item.name in ['Single Arrow', 'Small Key (Universal)']):
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
                if interesting_item(location, location.item, world, location.item.player):
                    sphere_costs[loc_player] += shop_item['price']
                    location_free = False
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
        if checked_locations:
            if world.has_beaten_game(state):
                done = True
                continue
            # else go to next sphere
        else:
            # check for solvent players
            solvent = set()
            insolvent = set()
            for player in range(1, world.players+1):
                if wallet[player] >= sphere_costs[player] > 0:
                    solvent.add(player)
                if sphere_costs[player] > 0 and sphere_costs[player] > wallet[player]:
                    insolvent.add(player)
            if len(solvent) == 0:
                target_player = min(insolvent, key=lambda p: sphere_costs[p]-wallet[p])
                difference = sphere_costs[target_player]-wallet[target_player]
                logger.debug(f'Money balancing needed: Player {target_player} short {difference}')
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
                    else:
                        old_item = best_target.item
                        logger.debug(f'Swapping {best_target.item.name} @ {best_target.name} for {best_swap.item.name} @ {best_swap.name}')
                        best_target.item = best_swap.item
                        best_target.item.location = best_target
                        best_swap.item = old_item
                        best_swap.item.location = best_swap
                    increase = best_value - old_value
                    difference -= increase
                    wallet[target_player] += increase
                solvent.add(target_player)
            # apply solvency
            for player in solvent:
                wallet[player] -= sphere_costs[player]
                for location in locked_by_money[player]:
                    if location == 'Kiki':
                        kiki_paid[player] = True
                    else:
                        state.collect(location.item, True, location)
                        unchecked_locations.remove(location)
                        if location.item.name.startswith('Rupee'):
                            wallet[location.item.player] += rupee_chart[location.item.name]
