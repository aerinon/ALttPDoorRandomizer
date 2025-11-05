import itertools
import logging

from functools import reduce

import RaceRandom as random

from collections import defaultdict, deque

from BaseClasses import DoorType, Door, RegionType, dungeon_keys
from DungeonGenerator import valid_region_to_explore, count_reserved_locations, ExplorationState
from Items import ItemFactory
from KeyDoorShuffle import build_key_layout, check_bk_special, count_key_drops, expand_key_state, flatten_pair_list, open_a_door, reduce_rules
from KeyDoorShuffle import find_outside_connection, prize_relevance_sig2, count_free_locations, prize_or_event, reserved_location, blind_boss_unavail
from KeyDoorShuffle import count_small_key_only_locations, cnt_avail_big_locations
from KeyDoorShuffle import create_key_counters, PlacementRule, prize_relevance, find_big_chest_locations
from Regions import dungeon_events
from RoomData import DoorKind, PairedDoor
from Utils import ncr, kth_combination

from source.dungeon.NewKeyLogic import analyze_dungeon, calc_extras

def shuffle_small_key_doors(door_type_pools, used_doors, start_regions_map, all_custom, world, player):
    max_computation = 35  # this is the main limit for the number of key doors
    for pool, door_type_pool in door_type_pools:
        ttl = 0
        suggestion_map, small_map, flex_map = {}, {}, {}
        remaining = door_type_pool.smalls
        total_keys = remaining
        if player in world.custom_door_types and 'Key Door' in world.custom_door_types[player]:
            custom_key_doors = world.custom_door_types[player]['Key Door']
        else:
            custom_key_doors = defaultdict(list)
        total_adjustable = len(pool) > 1
        for dungeon in pool:
            builder = world.dungeon_layouts[player][dungeon]
            if not total_adjustable:
                builder.total_keys = total_keys
            find_small_key_door_candidates(builder, start_regions_map[dungeon], used_doors, world, player)
            custom_doors = 0
            if all_custom[dungeon]:
                builder.candidates.small = filter_key_door_pool(builder.candidates.small, all_custom[dungeon])
                custom_doors = len(custom_key_doors[dungeon])
                remaining -= custom_doors
            builder.key_doors_num = max(0, len(builder.candidates.small) - builder.key_drop_cnt) + custom_doors
            total_keys -= builder.key_drop_cnt
            ttl += builder.key_doors_num
        remaining = max(0, remaining)
        for dungeon in pool:
            builder = world.dungeon_layouts[player][dungeon]
            if ttl == 0:
                calculated = 0
            else:
                calculated = int(round(builder.key_doors_num*total_keys/ttl))
            max_keys = max(0, builder.location_cnt - calc_used_dungeon_items(builder, world, player))
            cand_len = max(0, len(builder.candidates.small) - builder.key_drop_cnt)
            limit = min(max_keys, cand_len, max_computation)
            suggested = min(calculated, limit)
            key_door_num = min(suggested + builder.key_drop_cnt, max_computation)
            combo_size = ncr(len(builder.candidates.small), key_door_num)
            suggestion_map[dungeon] = builder.key_doors_num = key_door_num
            remaining -= key_door_num + builder.key_drop_cnt
            builder.combo_size = combo_size
            flex_map[dungeon] = (limit - key_door_num) if key_door_num < limit else 0
        for dungeon in pool:
            builder = world.dungeon_layouts[player][dungeon]
            if total_adjustable:
                builder.total_keys = max(suggestion_map[dungeon], builder.key_drop_cnt)
            valid_doors, small_number = find_valid_combination(builder, suggestion_map[dungeon],
                                                               start_regions_map[dungeon], world, player)
            small_map[dungeon] = valid_doors
            actual_chest_keys = small_number - builder.key_drop_cnt
            if actual_chest_keys < suggestion_map[dungeon]:
                if total_adjustable:
                    builder.total_keys = actual_chest_keys + builder.key_drop_cnt
                flex_map[dungeon] = 0
                remaining += suggestion_map[dungeon] - actual_chest_keys
            suggestion_map[dungeon] = small_number
        builder_order = [world.dungeon_layouts[player][x] for x in pool if flex_map[x] > 0]
        builder_order.sort(key=lambda b: b.combo_size)
        queue = deque(builder_order)
        while len(queue) > 0 and remaining > 0:
            builder = queue.popleft()
            dungeon = builder.name
            increased = suggestion_map[dungeon] + 1
            if increased > max_computation:
                continue
            builder.key_doors_num = increased
            valid_doors, small_number = find_valid_combination(builder, increased, start_regions_map[dungeon],
                                                               world, player)
            if valid_doors and small_number == increased:
                small_map[dungeon] = valid_doors
                remaining -= 1
                suggestion_map[dungeon] = increased
                flex_map[dungeon] -= 1
                if total_adjustable:
                    builder.total_keys = max(increased, builder.key_drop_cnt)
                if flex_map[dungeon] > 0:
                    builder.combo_size = ncr(len(builder.candidates.small), builder.key_doors_num)
                    queue.append(builder)
                    queue = deque(sorted(queue, key=lambda b: b.combo_size))
            else:
                builder.key_doors_num -= 1
        # time to re-assign
        reassign_key_doors(small_map, used_doors, world, player)
        for dungeon_name in pool:
            if world.keyshuffle[player] != 'universal':
                builder = world.dungeon_layouts[player][dungeon_name]
                log_key_logic(builder.name, world.key_logic[player][builder.name])
                if world.doorShuffle[player] != 'basic':
                    actual_chest_keys = max(builder.key_doors_num - builder.key_drop_cnt, 0)
                    dungeon = world.get_dungeon(dungeon_name, player)
                    if actual_chest_keys == 0:
                        dungeon.small_keys = []
                    else:
                        dungeon.small_keys = [ItemFactory(dungeon_keys[dungeon_name], player) for _ in range(actual_chest_keys)]

        for name, small_list in small_map.items():
            used_doors.update(flatten_pair_list(small_list))
    return used_doors


def find_small_key_door_candidates(builder, start_regions, used, world, player):
    # traverse dungeon and find candidates
    candidates = []
    checked_doors = set()
    for region in start_regions:
        possible, checked = find_key_door_candidates(region, checked_doors, used, world, player)
        candidates.extend([x for x in possible if x not in candidates])
        checked_doors.update(checked)
    flat_candidates = []
    for candidate in candidates:
        # not valid if: Normal Coupled and Pair in is Checked and Pair is not in Candidates
        if (world.decoupledoors[player] or candidate.type != DoorType.Normal
                or candidate.dest not in checked_doors or candidate.dest in candidates):
            flat_candidates.append(candidate)

    paired_candidates = build_pair_list(flat_candidates)
    builder.candidates.small = paired_candidates


def find_key_door_candidates(region, checked, used, world, player):
    decoupled = world.decoupledoors[player]
    dungeon_name = region.dungeon.name
    candidates = []
    checked_doors = list(checked)
    queue = deque([(region, None, None)])
    while len(queue) > 0:
        current, last_door, last_region = queue.pop()
        for ext in current.exits:
            d = ext.door
            controlled = d
            if d and d.controller:
                d = d.controller
            if (d and not d.blocked and d.dest is not last_door and d.dest is not last_region
                    and d not in checked_doors):
                valid = False
                if (0 <= d.doorListPos < 4 and d.type in [DoorType.Interior, DoorType.Normal, DoorType.SpiralStairs]
                        and not d.entranceFlag and d not in used):
                    room = world.get_room(d.roomIndex, player)
                    position, kind = room.doorList[d.doorListPos]
                    if d.type == DoorType.Interior:
                        valid = kind in okay_interiors and d.dest not in used
                        # interior doors are not separable yet
                        if valid and d.dest not in candidates:
                            candidates.append(d.dest)
                    elif d.type == DoorType.SpiralStairs:
                        valid = kind in [DoorKind.StairKey, DoorKind.StairKey2, DoorKind.StairKeyLow]
                    elif d.type == DoorType.Normal:
                        valid = kind in okay_normals
                        if valid and not decoupled:
                            d2 = d.dest
                            if d2 not in candidates and d2 not in used:
                                if d2.type == DoorType.Normal:
                                    room_b = world.get_room(d2.roomIndex, player)
                                    pos_b, kind_b = room_b.doorList[d2.doorListPos]
                                    valid &= kind_b in okay_normals and valid_key_door_pair(d, d2)
                                if valid and 0 <= d2.doorListPos < 4:
                                    candidates.append(d2)
                if valid and d not in candidates:
                    candidates.append(d)
                connected = ext.connected_region
                if valid_region_to_explore(connected, dungeon_name, world, player):
                    queue.append((ext.connected_region, controlled, current))
                if d is not None:
                    checked_doors.append(d)
    return candidates, checked_doors


okay_normals = [DoorKind.Normal, DoorKind.SmallKey, DoorKind.Bombable, DoorKind.Dashable,
                DoorKind.DungeonChanger, DoorKind.BigKey]

okay_interiors = [DoorKind.Normal, DoorKind.SmallKey, DoorKind.Bombable, DoorKind.Dashable, DoorKind.BigKey]


def valid_key_door_pair(door1, door2):
    if door1.roomIndex != door2.roomIndex:
        return True
    return len(door1.entrance.parent_region.exits) <= 1 or len(door2.entrance.parent_region.exits) <= 1


def build_pair_list(flat_list):
    paired_list = []
    queue = deque(flat_list)
    while len(queue) > 0:
        d = queue.pop()
        paired = d.dest.dest == d
        if d.dest in queue and d.type != DoorType.SpiralStairs and paired:
            paired_list.append((d, d.dest))
            queue.remove(d.dest)
        else:
            paired_list.append(d)
    return paired_list


def filter_key_door_pool(pool, selected_custom):
    new_pool = []
    for cand in pool:
        found = False
        for custom in selected_custom:
            if isinstance(cand, Door):
                if isinstance(custom, Door):
                    found = cand.name == custom.name
                else:
                    found = cand.name == custom[0].name or cand.name == custom[1].name
            else:
                if isinstance(custom, Door):
                    found = cand[0].name == custom.name or cand[1].name == custom.name
                else:
                    found = (cand[0].name == custom[0].name or cand[0].name == custom[1].name
                             or cand[1].name == custom[0].name or cand[1].name == custom[1].name)
            if found:
                break
        if not found:
            new_pool.append(cand)
    return new_pool

def calc_used_dungeon_items(builder, world, player):
    basic_flag = world.doorShuffle[player] == 'basic'
    base = count_reserved_locations(world, player, builder.location_set)
    if not world.bigkeyshuffle[player]:
        if builder.bk_required and not builder.bk_provided:
            base += 1
    if not world.compassshuffle[player] and (builder.name not in ['Hyrule Castle', 'Agahnims Tower'] or not basic_flag):
        base += 1
    if not world.mapshuffle[player] and (builder.name != 'Agahnims Tower' or not basic_flag):
        base += 1
    return base

def find_valid_combination(builder, target, start_regions, world, player, drop_keys=True):
    logger = logging.getLogger('')
    key_door_pool = list(builder.candidates.small)
    key_doors_needed = target
    if player in world.custom_door_types and 'Key Door' in world.custom_door_types[player]:
        custom_key_doors = world.custom_door_types[player]['Key Door'][builder.name]
    else:
        custom_key_doors = []
    if custom_key_doors:  # could validate that each custom item is in the candidates
        key_door_pool = filter_key_door_pool(key_door_pool, custom_key_doors)
        key_doors_needed -= len(custom_key_doors)
        key_doors_needed = max(0, key_doors_needed)
    # find valid combination of candidates
    if len(key_door_pool) < key_doors_needed:
        if not drop_keys:
            logger.info('No valid layouts for %s with %s doors', builder.name, builder.key_doors_num)
            return None, 0
        builder.key_doors_num -= key_doors_needed - len(key_door_pool)  # reduce number of key doors
        key_doors_needed = len(key_door_pool)
        logger.info('%s: %s', world.fish.translate("cli", "cli", "lowering.keys.candidates"), builder.name)
    proposal = None
    start_regions, event_starts = filter_start_regions(builder, start_regions, world, player)
    # todo: figure out prize lock issues
    if is_key_layout_agnostic(builder, world, player):
        # in these cases any door combination should be fine
        combinations = ncr(len(key_door_pool), key_doors_needed)
        proposal = kth_combination(random.randint(0, combinations), key_door_pool, key_doors_needed)
        proposal.extend(custom_key_doors)
    elif world.key_logic_algorithm[player] != 'strict' and key_doors_needed <= 8:
        proposal = exhaustive_key_logic_algorithm(builder, key_door_pool, key_doors_needed, start_regions, event_starts, custom_key_doors, world, player)
    else:
        proposal = monte_carlo_algorithm(builder, key_door_pool, key_doors_needed, start_regions, event_starts, custom_key_doors, world, player)
    key_layout = build_key_layout(builder, start_regions, proposal, event_starts, world, player)
    if player not in world.key_logic.keys():
        world.key_logic[player] = {}
    analyze_dungeon(key_layout, world, player)
    builder.key_door_proposal = proposal
    world.key_logic[player][builder.name] = key_layout.key_logic
    world.key_layout[player][builder.name] = key_layout
    return proposal, len(proposal)


def is_key_layout_agnostic(builder, world, player):
    return (world.logic[player] == 'nologic'
            or (world.keyshuffle[player] == 'universal'
                and (world.mode[player] != 'standard' or 'Hyrule Castle' not in builder.name))
            or (world.keyshuffle[player] == 'wild' and world.dropshuffle[player] != 'none' and world.pottery[player] not in ['none', 'cave']))


# eliminate start region if portal marked as destination
def filter_start_regions(builder, start_regions, world, player):
    std_flag = world.mode[player] == 'standard' and builder.name == 'Hyrule Castle'
    excluded = {}   # todo: drop lobbies, might be better to white list instead (two entrances per region)
    event_doors = {}
    for region in start_regions:
        portal = next((x for x in world.dungeon_portals[player] if x.door.entrance.parent_region == region), None)
        if portal and portal.destination:
            # make sure that a drop is not accessible for this "destination"
            drop_region = next((x.parent_region for x in region.entrances
                                if x.parent_region.type in [RegionType.LightWorld, RegionType.DarkWorld]
                                or x.parent_region.name == 'Sewer Drop'), None)
            if not drop_region:
                excluded[region] = None
        if portal and not portal.destination:
            portal_entrance_region = portal.door.entrance.parent_region.name
            if portal_entrance_region not in builder.path_entrances:
                excluded[region] = None
        if not portal:
            drop_region = next((x.parent_region for x in region.entrances
                                if x.parent_region.type in [RegionType.LightWorld, RegionType.DarkWorld]
                                or x.parent_region.name == 'Sewer Drop'), None)
            if drop_region and drop_region.name in world.inaccessible_regions[player]:
                excluded[region] = None
        if std_flag and (not portal or portal.find_portal_entrance().parent_region.name != 'Hyrule Castle Courtyard'):
            excluded[region] = None
            if portal is None:
                entrance = next((x for x in region.entrances
                                 if x.parent_region.type in [RegionType.LightWorld, RegionType.DarkWorld]
                                 or x.parent_region.name == 'Sewer Drop'), None)
                event_doors[entrance] = None
            else:
                event_doors[portal.find_portal_entrance()] = None

    return [x for x in start_regions if x not in excluded.keys()], event_doors


def monte_carlo_algorithm(builder, key_door_pool, key_doors_needed, start_regions, event_starts, custom, world, player):
    # first build exploration init_state for each door in key_door_pool, and eliminate if it can't meet the criteria
    elimination_list = []
    init_state = ExplorationState(dungeon=builder.name)
    init_state.init_zelda_event_doors(event_starts, player)
    init_state.key_locations = key_doors_needed - count_key_drops(builder.master_sector)
    init_state.big_key_special = check_bk_special(builder.master_sector.regions, world, player)

    locations = [world.get_location(loc, player) for loc in builder.location_set]
    all_small_key_only_locations = sum(1 for loc in locations if loc.forced_item and loc.item.smallkey)
    extras = calc_extras(key_doors_needed, builder.name, world, player)

    for candidate in key_door_pool:
        cand_list = flatten_to_list(candidate)
        current_state = init_state.copy()
        initialize_state(current_state, start_regions, builder, cand_list, world, player)
        expand_state_improved(current_state, cand_list, world, player)
        found_smalls = count_small_key_only_locations(current_state)
        ttl_locations = count_free_locations(current_state, world, player)
        if current_state.big_key_opened:
            ttl_locations -= (0 if current_state.big_key_special else 1)
        else:
            locs_sans_big = count_locations_exclude_big_chest(current_state.found_locations, world, player)
            ttl_locations = locs_sans_big if current_state.big_key_special else max(ttl_locations - 1, locs_sans_big)
        if found_smalls < all_small_key_only_locations or ttl_locations <= key_doors_needed + extras:
            elimination_list.append(candidate)
    surviving_pool = [x for x in key_door_pool if x not in elimination_list]
    # now we need to find a valid combination
    combinations = ncr(len(surviving_pool), key_doors_needed)
    sample_list = build_sample_list(combinations, 10000)
    itr = 0
    proposal = kth_combination(sample_list[itr], surviving_pool, key_doors_needed)
    proposal.extend(custom)
    while not validate_key_proposal_large(proposal, init_state, all_small_key_only_locations, builder, start_regions, world, player):
        itr += 1
        if itr >= len(sample_list):
            key_doors_needed -= 1
            if key_doors_needed < 0:
                raise Exception(f'Bad dungeon {builder.name} - less than 0 key doors or invalid custom key door')
            combinations = ncr(len(surviving_pool), max(0, key_doors_needed))
            sample_list = build_sample_list(combinations)
            itr = 0
        proposal = kth_combination(sample_list[itr], surviving_pool, key_doors_needed)
        proposal.extend(custom)
    return proposal


def validate_key_proposal_large(proposal, init_state, all_smalls, builder, start_regions, world, player):
    extras = calc_extras(len(proposal), builder.name, world, player)
    flat_prop = flatten_pair_list(proposal)
    state = init_state.copy()
    initialize_state(state, start_regions, builder, flat_prop, world, player)
    expand_state_improved(state, flat_prop, world, player)
    found_smalls = count_small_key_only_locations(state)
    ttl_locations = count_free_locations(state, world, player)
    if state.big_key_opened:
        ttl_locations -= (0 if state.big_key_special else 1)
    else:
        locs_sans_big = count_locations_exclude_big_chest(state.found_locations, world, player)
        ttl_locations = locs_sans_big if state.big_key_special else max(ttl_locations - 1, locs_sans_big)
    return found_smalls >= all_smalls and (ttl_locations > len(proposal) + extras or len(proposal) == 0)


def build_sample_list(combinations, max_combinations=10000):
    if combinations <= max_combinations:
        sample_list = list(range(0, int(combinations)))
    else:
        num_set = set()
        while len(num_set) < max_combinations:
            num_set.add(random.randint(0, combinations))
        sample_list = list(num_set)
        sample_list.sort()
    random.shuffle(sample_list)
    return sample_list


def expand_state_improved(state, cand_list, world, player):
    changed = True
    while changed:
        changed = False
        expand_key_state(state, cand_list, world, player)
        if state.big_doors and not state.big_key_opened:
            ttl_locations = count_locations_exclude_big_chest(state.found_locations, world, player)
            available_big_locations = cnt_avail_big_locations(ttl_locations, state, world, player)
            if available_big_locations > 0 or state.found_forced_bk():
                state.big_key_opened = True
                state.avail_doors.extend(state.big_doors)
                state.opened_doors.extend(set([d.door for d in state.big_doors]))
                state.big_doors.clear()
                changed = True
        if not state.prize_doors_opened and state.prize_doors and any(l.name.endswith('- Prize') for l in state.found_locations):
            state.prize_doors_opened = True
            state.avail_doors.extend(state.prize_doors)
            state.opened_doors.extend(set([d.door for d in state.prize_doors]))
            state.prize_doors.clear()
            changed = True


def initialize_state(state, start_regions, builder, door_list, world, player):
    for region in start_regions:
        dungeon_entrance, portal_door = find_outside_connection(region)
        prize_relevant_flag = prize_relevance_sig2(start_regions, builder.name, dungeon_entrance, world.is_atgt_swapped(player))
        if prize_relevant_flag:
            state.append_door_to_list(portal_door, state.prize_doors)
            state.prize_door_set[portal_door] = dungeon_entrance
        else:
            state.visit_region(region, key_checks=True)
            state.add_all_doors_check_keys(region, door_list, world, player)


def flatten_to_list(element):
    if isinstance(element, tuple):
        return list(element)
    else:
        return [element]


def count_locations_exclude_big_chest(locations, world, player):
    cnt = 0
    for loc in locations:
        if ('- Big Chest' not in loc.name and not loc.forced_item and not reserved_location(loc, world, player)
                and not prize_or_event(loc) and not blind_boss_unavail(loc, locations, world, player)
                and loc.parent_region.name not in ["Thieves Blind's Cell Interior", 'Hyrule Dungeon Cell']):
            cnt += 1
    return cnt


def reassign_key_doors(small_map, used_doors, world, player):
    logger = logging.getLogger('')
    for name, small_doors in small_map.items():
        logger.debug(f'Key doors for {name}')
        builder = world.dungeon_layouts[player][name]
        proposal = builder.key_door_proposal
        flat_proposal = flatten_pair_list(proposal)
        queue = deque(find_current_key_doors(builder))
        while len(queue) > 0:
            d = queue.pop()
            if d.type is DoorType.SpiralStairs and d not in proposal:
                room = world.get_room(d.roomIndex, player)
                if room.doorList[d.doorListPos][1] == DoorKind.StairKeyLow:
                    room.delete(d.doorListPos)
                else:
                    if len(room.doorList) > 1:
                        room.mirror(d.doorListPos)  # I think this works for crossed now
                    else:
                        room.delete(d.doorListPos)
                d.smallKey = False
            elif d.type is DoorType.Interior and d not in flat_proposal and d.dest not in flat_proposal:
                if not d.entranceFlag and d not in used_doors and d.dest not in used_doors:
                    world.get_room(d.roomIndex, player).change(d.doorListPos, DoorKind.Normal)
                d.smallKey = False
                d.dest.smallKey = False
                queue.remove(d.dest)
            elif d.type is DoorType.Normal and d not in flat_proposal:
                if not d.entranceFlag and d not in used_doors:
                    world.get_room(d.roomIndex, player).change(d.doorListPos, DoorKind.Normal)
                d.smallKey = False
                for dp in world.paired_doors[player]:
                    if dp.door_a == d.name or dp.door_b == d.name:
                        dp.pair = False
        for obj in proposal:
            if type(obj) is tuple:
                d1 = obj[0]
                d2 = obj[1]
                if d1.type is DoorType.Interior:
                    change_door_to_small_key(d1, world, player)
                    d2.smallKey = True  # ensure flag is set
                else:
                    names = [d1.name, d2.name]
                    found = False
                    for dp in world.paired_doors[player]:
                        if dp.door_a in names and dp.door_b in names:
                            dp.pair = True
                            found = True
                        elif dp.door_a in names:
                            dp.pair = False
                        elif dp.door_b in names:
                            dp.pair = False
                    if not found:
                        world.paired_doors[player].append(PairedDoor(d1.name, d2.name))
                    change_door_to_small_key(d1, world, player)
                    change_door_to_small_key(d2, world, player)
                world.spoiler.set_door_type(f'{d1.name} <-> {d2.name} ({d1.dungeon_name()})', 'Key Door', player)
                logger.debug(f'Key Door: {d1.name} <-> {d2.name} ({d1.dungeon_name()})')
            else:
                d = obj
                if d.type is DoorType.Interior:
                    change_door_to_small_key(d, world, player)
                    d.dest.smallKey = True  # ensure flag is set
                elif d.type is DoorType.SpiralStairs:
                    pass  # we don't have spiral stairs candidates yet that aren't already key doors
                elif d.type is DoorType.Normal:
                    change_door_to_small_key(d, world, player)
                    if not world.decoupledoors[player] and d.dest:
                        if d.dest.type in [DoorType.Normal]:
                            dest_room = world.get_room(d.dest.roomIndex, player)
                            if stateful_door(d.dest, dest_room.kind(d.dest)):
                                change_door_to_small_key(d.dest, world, player)
                                add_pair(d, d.dest, world, player)
                world.spoiler.set_door_type(f'{d.name} ({d.dungeon_name()})', 'Key Door', player)
                logger.debug(f'Key Door: {d.name} ({d.dungeon_name()})')


def find_current_key_doors(builder):
    current_doors = []
    for region in builder.master_sector.regions:
        for ext in region.exits:
            d = ext.door
            if d and d.smallKey:
                current_doors.append(d)
    return current_doors


def change_door_to_small_key(d, world, player):
    d.smallKey = True
    room = world.get_room(d.roomIndex, player)
    if room.doorList[d.doorListPos][1] != DoorKind.SmallKey:
        verify_door_list_pos(d, room, world, player)
        room.change(d.doorListPos, DoorKind.SmallKey)


def verify_door_list_pos(d, room, world, player, pos=4):
    if d.doorListPos >= pos:
        new_index = room.next_free(pos)
        if new_index is not None:
            room.swap(new_index, d.doorListPos)
            other = next(x for x in world.doors if x.player == player and x.roomIndex == d.roomIndex
                         and x.doorListPos == new_index)
            other.doorListPos = d.doorListPos
            d.doorListPos = new_index
        else:
            raise Exception(f'Invalid stateful door: {d.name}. Only {pos} stateful doors per supertile')


def add_pair(door_a, door_b, world, player):
    pair_a, pair_b = None, None
    for paired_door in world.paired_doors[player]:
        if paired_door.door_a == door_a.name and paired_door.door_b == door_b.name:
            paired_door.pair = True
            return
        if paired_door.door_a == door_b.name and paired_door.door_b == door_a.name:
            paired_door.pair = True
            return
        if paired_door.door_a == door_a.name or paired_door.door_b == door_a.name:
            pair_a = paired_door
        if paired_door.door_a == door_b.name or paired_door.door_b == door_b.name:
            pair_b = paired_door
    if pair_a:
        pair_a.pair = False
    if pair_b:
        pair_b.pair = False
    world.paired_doors[player].append(PairedDoor(door_a, door_b))


def remove_pair(door, world, player):
    for paired_door in world.paired_doors[player]:
        if paired_door.door_a == door.name or paired_door.door_b == door.name:
            paired_door.pair = False
            break


def stateful_door(door, kind):
    if 0 <= door.doorListPos < 4:
        return kind in [DoorKind.Normal, DoorKind.SmallKey, DoorKind.Bombable, DoorKind.Dashable, DoorKind.BigKey]
    return False


def log_key_logic(d_name, key_logic):
    logger = logging.getLogger('')
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug('Key Logic for %s', d_name)
        if len(key_logic.bk_restricted) > 0:
            logger.debug('-BK Restrictions')
            for restriction in key_logic.bk_restricted:
                logger.debug(restriction)
        if len(key_logic.sm_restricted) > 0:
            logger.debug('-Small Restrictions')
            for restriction in key_logic.sm_restricted:
                logger.debug(restriction)
        for key in key_logic.door_rules.keys():
            rule = key_logic.door_rules[key]
            logger.debug('--Rule for %s: Nrm:%s Allow:%s Loc:%s Alt:%s', key, rule.small_key_num, rule.allow_small, rule.small_location, rule.alternate_small_key)
            if rule.alternate_small_key is not None:
                for loc in rule.alternate_big_key_loc:
                    logger.debug('---BK Loc %s', loc.name)
        log_placement_rules(d_name, key_logic, logger)
        if key_logic.new_logic:
            if key_logic.new_logic.bk_locations:
                logger.debug(f'BK Locked Locations: {",".join([x.name for x in key_logic.new_logic.bk_locations])}')
            if key_logic.new_logic.bk_regions:
                logger.debug(f'BK Locked Regions: {",".join([x.name for x in key_logic.new_logic.bk_regions])}')
            if key_logic.new_logic.location_key_reqs or key_logic.new_logic.region_key_reqs:
                def appending_reduce(x, kv):
                    x[kv[1]].append(kv[0])
                    return x
                reqs = defaultdict(list)
                reduce(appending_reduce, key_logic.new_logic.location_key_reqs.items(), reqs)
                region_reqs = defaultdict(list)
                reduce(appending_reduce, key_logic.new_logic.region_key_reqs.items(), region_reqs)
                all_keys = set(reqs.keys()).union(region_reqs.keys())
                for key_value in sorted(all_keys):
                    locs = reqs[key_value]
                    regions = region_reqs[key_value]
                    if locs:
                        logger.debug(f'Locations with {key_value} keys(s): {",".join([x.name for x in locs])}')
                    if regions:
                        logger.debug(f'Regions with {key_value} keys(s): {",".join([x.name for x in regions])}')


def log_placement_rules(d_name, key_logic, logger):
    if key_logic.placement_rules:
        logger.debug('Placement rules for %s', d_name)
        for rule in key_logic.placement_rules:
            logger.debug('*Rule for %s:', rule.door_reference)
            if rule.bk_conditional_set:
                logger.debug('**BK Checks %s', ','.join([x.name for x in rule.bk_conditional_set]))
                logger.debug('**BK Blocked (%s) : %s', rule.needed_keys_wo_bk, ','.join([x.name for x in rule.check_locations_wo_bk]))
            if rule.needed_keys_w_bk:
                logger.debug(f'**BK Available ({rule.needed_keys_w_bk}) Relevant? ({rule.bk_relevant}) : {",".join([x.name for x in rule.check_locations_w_bk])}')



def exhaustive_key_logic_algorithm(builder, key_door_pool, key_doors_needed, start_regions, event_starts, custom, world, player):
    combinations = ncr(len(key_door_pool), key_doors_needed)
    sample_list = build_sample_list(combinations, 10000)
    itr = 0
    contradiction_exists = True
    proposal = list(custom)  # base case

    bk_restrictions = None

    while contradiction_exists and itr < len(sample_list):
        contradiction_exists = False
        proposal = kth_combination(sample_list[itr], key_door_pool, key_doors_needed)
        proposal.extend(custom)

        key_layout = build_key_layout(builder, start_regions, proposal, event_starts, world, player)
        key_layout.key_logic.reset()
        key_layout.key_counters = create_key_counters(key_layout, world, player)
        for counter in key_layout.key_counters.values():
            key_layout.all_chest_locations.update(counter.free_locations)
            key_layout.item_locations.update(counter.free_locations)
            key_layout.item_locations.update(counter.key_only_locations)
            key_layout.all_locations.update(key_layout.item_locations)
            key_layout.all_locations.update(counter.other_locations)
        if bk_restrictions is None:
            bk_restrictions = determine_big_key_logic(key_layout, world, player)

        create_exhaustive_placement_rules(key_layout, bk_restrictions, world, player)


        # first we can sanity check the rules to ensure one is not always bad
        total_available_keys = key_layout.max_chests + key_layout.max_drops
        for rule in key_layout.key_logic.placement_rules:
            if rule.bk_conditional_set:
                if rule.needed_keys_wo_bk > total_available_keys:
                    contradiction_exists = True
                    break
                # Check rule without big key
                available_keys = min(key_layout.max_chests, sum(1 for loc in rule.check_locations_wo_bk if not loc.forced_item))
                key_drops = sum(1 for loc in rule.check_locations_wo_bk if loc.forced_item and loc.item.smallkey)
                if rule.needed_keys_wo_bk > available_keys + key_drops:
                    bk_restrictions.update(rule.bk_conditional_set)  ## this indicates the big key cannot be in these locations
            else:
                if rule.needed_keys_w_bk > total_available_keys:
                    contradiction_exists = True
                    break
                available_keys = min(key_layout.max_chests, sum(1 for loc in rule.check_locations_w_bk if not loc.forced_item))
                key_drops = sum(1 for loc in rule.check_locations_w_bk if loc.forced_item and loc.item.smallkey)
                if rule.needed_keys_w_bk > available_keys + key_drops:
                    contradiction_exists = True
                    break

        if not contradiction_exists:
            if not is_key_door_layout_satisfiable(key_layout, bk_restrictions):
                contradiction_exists = True
        if not contradiction_exists:
            log_placement_rules(builder.name, key_layout.key_logic, logging.getLogger(''))
        itr += 1  # pre for next iteration if any

    # base case is where we find no cases
    return proposal


def is_key_door_layout_satisfiable(key_layout, bk_restrictions):
    # determine locations the big key could be assigned to, or is it already assigned
    bk_assignment_needed, bk_location = True, None
    possible_bk_locations = []
    if key_layout.big_key_special:
        bk_assignment_needed = False
    elif any(loc.item and loc.item.name == key_layout.key_logic.bk_name for loc in key_layout.item_locations):
        bk_assignment_needed = False
        bk_location = next(loc for loc in key_layout.item_locations if loc.item and loc.item.bigkey)
    else:
        candidates = {loc for loc in key_layout.item_locations if not loc.item}
        possible_bk_locations.extend(candidates.difference(bk_restrictions))
        if len(possible_bk_locations) == 0:
            return False
        # we could try to be more efficient by choosing a smart order here
        possible_bk_locations.sort(key = lambda loc: loc.name)

    looking_for_satisfaction = True
    while looking_for_satisfaction:
        if bk_assignment_needed:
            bk_location = possible_bk_locations.pop()
        rules_to_check = [r for r in key_layout.key_logic.placement_rules if not r.bk_conditional_set or bk_location in r.bk_conditional_set]
        if not rules_to_check:
            logging.getLogger('').debug(f'Potential solution found: Small Keys: Anywhere.'
                                        f' Big Key at {bk_location.name if bk_location else "Special"}')
            return True  # no rules to check, so satisfied
        satisfying_key_set = find_contradiction_in_rules(rules_to_check, key_layout.max_chests)
        if satisfying_key_set is None:
            if not possible_bk_locations:
                looking_for_satisfaction = False  # no more options - fail this layout
        else:

            logging.getLogger('').debug(f'Potential solution found: Small Keys: {", ".join([loc.name for loc in satisfying_key_set]) if satisfying_key_set else "Empty Set"}.'
                                        f' Big Key at {bk_location.name if bk_location else "Special"}')
            return True  # found a satisfying set
    return False


def find_contradiction_in_rules(rules, num_to_choose):
    all_locations = set()
    for r in rules:
        if r.bk_conditional_set:
            all_locations.update(r.check_locations_wo_bk)
        else:
            all_locations.update(r.check_locations_w_bk)
    starter_set = {loc for loc in all_locations if (loc.forced_item and loc.forced_item.smallkey)}
    number_allowed = num_to_choose + len(starter_set)
    already_assigned =  {loc for loc in all_locations if loc.item}
    all_locations.difference_update(already_assigned)
    all_locations = list(all_locations)

    frequency = {loc: 0 for loc in all_locations}
    for r in rules:
        check_set = r.check_locations_wo_bk if r.bk_conditional_set else r.check_locations_w_bk
        for loc in check_set:
            if loc in frequency:
                frequency[loc] += 1

    all_locations = sorted(all_locations, key=lambda loc: frequency[loc], reverse=True)

    def can_satisfy(chosen_set, remaining_set):
        """Check if any extension of mask can satisfy constraints"""
        if len(chosen_set) > number_allowed:
            return False

        for r in rules:
            check_set = r.check_locations_wo_bk if r.bk_conditional_set else r.check_locations_w_bk
            check_amt = r.needed_keys_wo_bk if r.bk_conditional_set else r.needed_keys_w_bk

            # Already satisfied in this constraint
            chosen_met = chosen_set.intersection(check_set)

            # Remaining unassigned locations in this constraint
            remaining_left = remaining_set.intersection(check_set)

            # Can't satisfy this constraint
            if len(chosen_met) + len(remaining_set) < check_amt:
                return False

        return True

    def search(var_idx, chosen_set, left_to_choose):
        if var_idx == len(all_locations):
            # is everything satisfied?
            for r in rules:
                check_set = r.check_locations_wo_bk if r.bk_conditional_set else r.check_locations_w_bk
                check_amt = r.needed_keys_wo_bk if r.bk_conditional_set else r.needed_keys_w_bk
                if len(check_set.intersection(chosen_set)) < check_amt:
                    return None
            return chosen_set

        # pruning step, check if we can still satisfy all rules
        remaining_set = set(all_locations[var_idx:])
        if not can_satisfy(chosen_set, remaining_set):
            return None

        # Prefer fewer chosen locations
        result = search(var_idx + 1, chosen_set, left_to_choose)
        if result is not None:
            return result

        # Try choosing this location if we have any left
        if left_to_choose > 0:
            result = search(var_idx + 1, chosen_set.union({all_locations[var_idx]}), left_to_choose - 1)
            if result is not None:
                return result

        # No solution found
        return None

    return search(0, starter_set, num_to_choose)


def create_exhaustive_placement_rules(key_layout, bk_restrictions, world, player):
    key_logic = key_layout.key_logic
    max_ctr = find_max_counter(key_layout)
    for code, key_counter in key_layout.key_counters.items():
        if skip_key_counter_due_to_prize(key_layout, key_counter):
            continue  # we have the prize, we are not concerned about this case
        accessible_loc = set()
        accessible_loc.update(key_counter.free_locations)
        accessible_loc.update(key_counter.key_only_locations)
        blocked_loc = key_layout.item_locations.difference(accessible_loc)
        valid_rule = True
        # Only add 1 if there are small key doors that need to be opened
        has_small_key_doors = any(door in key_layout.flat_prop for door in key_counter.child_doors)
        min_keys = key_counter.used_keys + (1 if has_small_key_doors else 0)
        if len(blocked_loc) > 0:
            rule = PlacementRule()
            rule.door_reference = code
            rule.small_key = key_logic.small_key_name
            if key_counter.big_key_opened or not big_key_progress(key_counter):
                rule.needed_keys_w_bk = min_keys
                rule.bk_relevant = key_counter.big_key_opened
                placement_self_lock_adjustment(rule, max_ctr, blocked_loc, key_counter, world, player)
                rule.check_locations_w_bk = accessible_loc
                if key_layout.big_key_special:
                    rule.special_bk_avail = forced_big_key_avail(key_counter.important_locations) is not None
                    # check_sm_restriction_needed(key_layout, max_ctr, rule, blocked_loc)
            else:
                if big_key_progress(key_counter) and only_sm_doors(key_counter):
                    create_inclusive_rule(key_layout, max_ctr, code, key_counter, blocked_loc, accessible_loc, min_keys, world, player)
                conditional_set = blocked_loc.difference(bk_restrictions)
                if len(conditional_set) == 0:
                    valid_rule = False  # the big key can't be blocked at this point
                rule.bk_conditional_set = conditional_set
                rule.needed_keys_wo_bk = min_keys
                rule.check_locations_wo_bk = set(filter_big_chest(accessible_loc))
                rule.prize_relevance = key_layout.prize_relevant if rule_prize_relevant(key_counter) else None
            if valid_rule:
                key_logic.placement_rules.append(rule)
                adjust_locations_rules(key_logic, rule, accessible_loc, key_layout, key_counter, max_ctr)
    refine_placement_rules(key_layout, max_ctr)


def skip_key_counter_due_to_prize(key_layout, key_counter):
    return key_layout.prize_relevant and key_counter.prize_received and not key_counter.prize_doors_opened


def find_counter_hint(opened_doors, bk_hint, key_layout, prize_flag):
    cid = counter_id(opened_doors, bk_hint, key_layout.flat_prop, key_layout.prize_relevant, prize_flag)
    if cid in key_layout.key_counters.keys():
        return key_layout.key_counters[cid]
    if not bk_hint:
        cid = counter_id(opened_doors, True, key_layout.flat_prop, key_layout.prize_relevant, prize_flag)
        if cid in key_layout.key_counters.keys():
            return key_layout.key_counters[cid]
    return None


def find_max_counter(key_layout):
    max_counter = find_counter_hint(dict.fromkeys(key_layout.found_doors), False, key_layout, True)
    if max_counter is None:
        raise Exception("Max Counter is none - something is amiss")
    if len(max_counter.child_doors) > 0:
        max_counter = find_counter_hint(dict.fromkeys(key_layout.found_doors), True, key_layout, True)
    return max_counter


def counter_id(opened_doors, bk_unlocked, flat_proposal, prize_relevant, prize_flag):
    s_id = '1' if bk_unlocked else '0'
    for d in flat_proposal:
        s_id += '1' if d in opened_doors.keys() else '0'
    if prize_relevant:
        s_id += '1' if prize_flag else '0'
    return s_id


def big_key_progress(key_counter):
    return not only_sm_doors(key_counter) or exist_big_chest(key_counter)

def only_sm_doors(key_counter):
    for door in key_counter.child_doors:
        if getattr(door, 'bigKey', False):
            return False
    return True

def exist_big_chest(key_counter):
    for loc in getattr(key_counter, 'free_locations', []):
        if '- Big Chest' in getattr(loc, 'name', ''):
            return True
    return False

def placement_self_lock_adjustment(rule, max_ctr, blocked_loc, ctr, world, player):
    if len(blocked_loc) == 1 and world.accessibility[player] != 'locations':
        blocked_others = set(getattr(max_ctr, 'other_locations', {})).difference(set(getattr(ctr, 'other_locations', {})))
        important_found = False
        for loc in blocked_others:
            if important_location(loc, world, player):
                important_found = True
                break
        if not important_found:
            rule.needed_keys_w_bk -= 1

def important_location(loc, world, player):
    return '- Prize' in loc.name or loc.name in imp_locations_factory(world, player) or (loc.forced_big_key())

imp_locations = None

def imp_locations_factory(world, player):
    global imp_locations
    if imp_locations:
        return imp_locations
    imp_locations = ['Agahnim 1', 'Agahnim 2', 'Attic Cracked Floor', 'Suspicious Maiden']
    if world.mode[player] == 'standard':
        imp_locations.append('Zelda Pickup')
        imp_locations.append('Zelda Drop Off')
    return imp_locations

def forced_big_key_avail(locations):
    for loc in locations:
        if getattr(loc, 'forced_big_key', lambda: False)():
            return loc
    return None

def filter_big_chest(locations):
    return [x for x in locations if '- Big Chest' not in getattr(x, 'name', '')]

def rule_prize_relevant(key_counter):
    return not getattr(key_counter, 'prize_doors_opened', False) and not getattr(key_counter, 'prize_received', False)

def create_inclusive_rule(key_layout, max_ctr, code, key_counter, blocked_loc, accessible_loc, min_keys, world, player):
    key_logic = key_layout.key_logic
    rule = PlacementRule()
    rule.door_reference = code
    rule.small_key = key_logic.small_key_name
    rule.needed_keys_w_bk = min_keys
    if key_counter.big_key_opened and rule.needed_keys_w_bk + 1 > len(accessible_loc):
        key_logic.bk_restricted.update(set(accessible_loc).difference(getattr(max_ctr, 'key_only_locations', {})))
    else:
        placement_self_lock_adjustment(rule, max_ctr, blocked_loc, key_counter, world, player)
        rule.check_locations_w_bk = accessible_loc
        rule.special_bk_avail = forced_big_key_avail(getattr(key_counter, 'important_locations', [])) is not None
        key_logic.placement_rules.append(rule)
        adjust_locations_rules(key_logic, rule, accessible_loc, key_layout, key_counter, max_ctr)

def adjust_locations_rules(key_logic, rule, accessible_loc, key_layout, key_counter, max_ctr):
    if rule.bk_conditional_set:
        test_set = (rule.bk_conditional_set - getattr(key_logic, 'bk_locked', set())) - set(getattr(max_ctr, 'key_only_locations', {}))
        needed = rule.needed_keys_wo_bk if test_set else 0
    else:
        test_set = None
        needed = rule.needed_keys_w_bk
    if needed > 0:
        all_accessible = set(accessible_loc)
        all_accessible.update(getattr(key_counter, 'other_locations', {}))
        blocked_loc = getattr(key_layout, 'all_locations', set()) - all_accessible
        for location in blocked_loc:
            if location not in getattr(key_logic, 'location_rules', {}):
                loc_rule = LocationRule()
                key_logic.location_rules[location] = loc_rule
            else:
                loc_rule = key_logic.location_rules[location]
            if test_set:
                if location not in getattr(key_logic, 'bk_locked', set()):
                    cond_rule = None
                    for other in getattr(loc_rule, 'conditional_sets', []):
                        if getattr(other, 'conditional_set', None) == test_set:
                            cond_rule = other
                            break
                    if not cond_rule:
                        cond_rule = ConditionalLocationRule(test_set)
                        loc_rule.conditional_sets.append(cond_rule)
                    cond_rule.small_key_num = max(needed, getattr(cond_rule, 'small_key_num', 0))
            else:
                loc_rule.small_key_num = max(needed, getattr(loc_rule, 'small_key_num', 0))

class LocationRule(object):
    def __init__(self):
        self.small_key_num = 0
        self.conditional_sets = []

class ConditionalLocationRule(object):
    def __init__(self, conditional_set):
        self.conditional_set = conditional_set
        self.small_key_num = 0

def refine_placement_rules(key_layout, max_ctr):
    key_logic = key_layout.key_logic
    changed = True
    while changed:
        changed = False
        rules_to_remove = {}
        for rule in key_logic.placement_rules:
            if rule.check_locations_w_bk:
                rule.check_locations_w_bk.difference_update(getattr(key_logic, 'sm_restricted', set()))
            if rule.bk_conditional_set:
                rule.bk_conditional_set.difference_update(getattr(key_logic, 'bk_restricted', set()))
            if rule.check_locations_wo_bk:
                rule.check_locations_wo_bk.difference_update(getattr(key_logic, 'sm_restricted', set()))
        for rule_a, rule_b in itertools.combinations([x for x in key_logic.placement_rules if x not in rules_to_remove], 2):
            if rule_b.bk_conditional_set and rule_a.check_locations_w_bk:
                temp = rule_a
                rule_a = rule_b
                rule_b = temp
            if rule_a.bk_conditional_set and rule_b.check_locations_w_bk:
                common_needed = min(rule_a.needed_keys_wo_bk, rule_b.needed_keys_w_bk)
                common_locs = len(rule_b.check_locations_w_bk & rule_a.check_locations_wo_bk)
                if (common_needed - common_locs) * 2 > key_layout.max_chests:
                    key_logic.bk_restricted.update(rule_a.bk_conditional_set)
                    rules_to_remove[rule_a] = None
                    changed = True
                    break
        equivalent_rules = []
        for rule in key_logic.placement_rules:
            for rule2 in key_logic.placement_rules:
                if rule != rule2 and rule not in rules_to_remove and rule2 not in rules_to_remove:
                    if rule.check_locations_w_bk and rule2.check_locations_w_bk:
                        if rule2.check_locations_w_bk == rule.check_locations_w_bk and rule2.needed_keys_w_bk > rule.needed_keys_w_bk:
                            rules_to_remove[rule] = None
                        elif rule2.needed_keys_w_bk == rule.needed_keys_w_bk and rule2.check_locations_w_bk < rule.check_locations_w_bk:
                            rules_to_remove[rule] = None
                        elif rule2.check_locations_w_bk == rule.check_locations_w_bk and rule2.needed_keys_w_bk == rule.needed_keys_w_bk:
                            equivalent_rules.append((rule, rule2))
                    if rule.check_locations_wo_bk and rule2.check_locations_wo_bk and rule.bk_conditional_set == rule2.bk_conditional_set:
                        if rule2.check_locations_wo_bk == rule.check_locations_wo_bk and rule2.needed_keys_wo_bk > rule.needed_keys_wo_bk:
                            rules_to_remove[rule] = None
                        elif rule2.needed_keys_wo_bk == rule.needed_keys_wo_bk and rule2.check_locations_wo_bk < rule.check_locations_wo_bk:
                            rules_to_remove[rule] = None
                        elif rule2.check_locations_wo_bk == rule.check_locations_wo_bk and rule2.needed_keys_wo_bk == rule.needed_keys_wo_bk:
                            equivalent_rules.append((rule, rule2))
        if len(rules_to_remove) > 0:
            key_logic.placement_rules = [x for x in key_logic.placement_rules if x not in rules_to_remove]
            equivalent_rules = [x for x in equivalent_rules if x[0] not in rules_to_remove and x[1] not in rules_to_remove]
        if len(equivalent_rules) > 0:
            removed_rules = {}
            for r1, r2 in equivalent_rules:
                if r1 in removed_rules.keys():
                    r1 = removed_rules[r1]
                if r2 in removed_rules.keys():
                    r2 = removed_rules[r2]
                if r1 != r2:
                    r1.door_reference += ','+r2.door_reference
                    key_logic.placement_rules.remove(r2)
                    removed_rules[r2] = r1


def determine_big_key_logic(key_layout, world, player):
    bk_restrictions = set()
    key_layout.found_doors.clear()
    flat_proposal = key_layout.flat_prop
    state = ExplorationState(dungeon=key_layout.sector.name)
    state.init_zelda_event_doors(key_layout.event_starts, player)
    if world.doorShuffle[player] == 'vanilla':
        builder = world.dungeon_layouts[player][key_layout.sector.name]
        state.key_locations = len(builder.key_door_proposal) - builder.key_drop_cnt
    else:
        builder = world.dungeon_layouts[player][key_layout.sector.name]
        state.key_locations = max(0, builder.total_keys - builder.key_drop_cnt)
    state.big_key_special = False
    for region in key_layout.sector.regions:
        for location in region.locations:
            if location.forced_big_key():
                state.big_key_special = True
    for region in key_layout.start_regions:
        dungeon_entrance, portal_door = find_outside_connection(region)
        prize_relevant_flag = prize_relevance(key_layout, dungeon_entrance, world.is_atgt_swapped(player))
        if prize_relevant_flag:
            state.append_door_to_list(portal_door, state.prize_doors)
            state.prize_door_set[portal_door] = dungeon_entrance
            key_layout.prize_relevant = prize_relevant_flag
        else:
            state.visit_region(region, key_checks=True)
            state.add_all_doors_check_keys(region, flat_proposal, world, player)
    expand_key_state(state, flat_proposal, world, player)
    start_state = state.copy()

    # expand the state without opening big key doors
    while len(state.small_doors) > 0:
        door = state.small_doors[-1]  # this is because open_a_door removes it from the list
        open_a_door(door.door, state, flat_proposal, world, player)
        expand_key_state(state, flat_proposal, world, player)

    # determine which regions & locations are locked by the big key
    big_chest_allowed_big_key = world.accessibility[player] != 'locations'
    for region in key_layout.sector.regions:
        key_layout.all_locations.update(region.locations)
        free_locations = {l: None for l in region.locations if not important_location(l, world, player)
                          and not l.forced_item and l.name not in dungeon_events}
        key_layout.all_chest_locations.update(free_locations)
        if not state.visited_at_all(region):
            for loc in region.locations:
                bk_restrictions.add(loc)
                if important_location(loc, world, player):
                    big_chest_allowed_big_key = False
    if not big_chest_allowed_big_key:
        bk_restrictions.update(find_big_chest_locations(key_layout.all_chest_locations))
    return bk_restrictions
