import random
import collections
import itertools
from collections import defaultdict, deque
from functools import reduce
import logging
import math
import operator as op
import time
from typing import List

from BaseClasses import DoorType, Direction, CrystalBarrier, RegionType, Polarity, PolSlot, flooded_keys, Sector
from BaseClasses import Hook, hook_from_door
from Regions import dungeon_events, flooded_keys_reverse
from Dungeons import dungeon_regions, split_region_starts
from RoomData import DoorKind


class GraphPiece:

    def __init__(self):
        self.hanger_info = None
        self.hanger_crystal = None
        self.hooks = {}
        self.visited_regions = set()
        self.possible_bk_locations = set()
        self.pinball_used = False


# Dungeons shouldn't be generated until all entrances are appropriately accessible
def pre_validate(builder, entrance_region_names, split_dungeon, world, player):
    entrance_regions = convert_regions(entrance_region_names, world, player)
    excluded = {}
    for region in entrance_regions:
        portal = next((x for x in world.dungeon_portals[player] if x.door.entrance.parent_region == region), None)
        if portal and portal.destination:
            excluded[region] = None
    entrance_regions = [x for x in entrance_regions if x not in excluded.keys()]
    proposed_map = {}
    doors_to_connect = {}
    all_regions = set()
    bk_needed = False
    bk_special = False
    for sector in builder.sectors:
        for door in sector.outstanding_doors:
            doors_to_connect[door.name] = door
        all_regions.update(sector.regions)
        bk_needed = bk_needed or determine_if_bk_needed(sector, split_dungeon, world, player)
        bk_special = bk_special or check_for_special(sector)
    paths = determine_paths_for_dungeon(world, player, all_regions, builder.name)
    dungeon, hangers, hooks = gen_dungeon_info(builder.name, builder.sectors, entrance_regions, all_regions,
                                               proposed_map, doors_to_connect, bk_needed, bk_special, world, player)
    return check_valid(builder.name, dungeon, hangers, hooks, proposed_map, doors_to_connect, all_regions,
                       bk_needed, bk_special, paths, entrance_regions, world, player)


def generate_dungeon(builder, entrance_region_names, split_dungeon, world, player):
    stonewalls = check_for_stonewalls(builder)
    sector = generate_dungeon_main(builder, entrance_region_names, split_dungeon, world, player)
    for stonewall in stonewalls:
        if not stonewall_valid(stonewall):
            builder.pre_open_stonewalls.add(stonewall)
    return sector


def check_for_stonewalls(builder):
    stonewalls = set()
    for sector in builder.sectors:
        for door in sector.outstanding_doors:
            if door.stonewall:
                stonewalls.add(door)
    return stonewalls


def generate_dungeon_main(builder, entrance_region_names, split_dungeon, world, player):
    if builder.valid_proposal:  # we made this earlier in gen, just use it
        proposed_map = builder.valid_proposal
    else:
        proposed_map = generate_dungeon_find_proposal(builder, entrance_region_names, split_dungeon, world, player)
        builder.valid_proposal = proposed_map
    queue = collections.deque(proposed_map.items())
    while len(queue) > 0:
        a, b = queue.popleft()
        connect_doors(a, b)
        queue.remove((b, a))
    if len(builder.sectors) == 0:
        return Sector()
    available_sectors = list(builder.sectors)
    master_sector = available_sectors.pop()
    for sub_sector in available_sectors:
        master_sector.regions.extend(sub_sector.regions)
    master_sector.outstanding_doors.clear()
    master_sector.r_name_set = None
    return master_sector


def generate_dungeon_find_proposal(builder, entrance_region_names, split_dungeon, world, player):
    logger = logging.getLogger('')
    name = builder.name
    entrance_regions = convert_regions(entrance_region_names, world, player)
    excluded = {}
    for region in entrance_regions:
        portal = next((x for x in world.dungeon_portals[player] if x.door.entrance.parent_region == region), None)
        if portal and portal.destination:
            excluded[region] = None
    entrance_regions = [x for x in entrance_regions if x not in excluded.keys()]
    doors_to_connect = {}
    all_regions = set()
    bk_needed = False
    bk_special = False
    for sector in builder.sectors:
        for door in sector.outstanding_doors:
            doors_to_connect[door.name] = door
        all_regions.update(sector.regions)
        bk_needed = bk_needed or determine_if_bk_needed(sector, split_dungeon, world, player)
        bk_special = bk_special or check_for_special(sector)
    proposed_map = {}
    choices_master = [[]]
    depth = 0
    dungeon_cache = {}
    backtrack = False
    itr = 0
    attempt = 1
    finished = False
    # flag if standard and this is hyrule castle
    paths = determine_paths_for_dungeon(world, player, all_regions, name)
    while not finished:
        # what are my choices?
        itr += 1
        if itr > 1000:
            if attempt > 9:
                raise GenerationException('Generation taking too long. Ref %s' % name)
            proposed_map = {}
            choices_master = [[]]
            depth = 0
            dungeon_cache = {}
            backtrack = False
            itr = 0
            attempt += 1
            logger.debug(f'Starting new attempt {attempt}')
        if depth not in dungeon_cache.keys():
            dungeon, hangers, hooks = gen_dungeon_info(name, builder.sectors, entrance_regions, all_regions, proposed_map,
                                                       doors_to_connect, bk_needed, bk_special, world, player)
            dungeon_cache[depth] = dungeon, hangers, hooks
            valid = check_valid(name, dungeon, hangers, hooks, proposed_map, doors_to_connect, all_regions,
                                bk_needed, bk_special, paths, entrance_regions, world, player)
        else:
            dungeon, hangers, hooks = dungeon_cache[depth]
            valid = True
        if valid:
            if len(proposed_map) == len(doors_to_connect):
                if dungeon['Origin'].pinball_used:
                    door = world.get_door('Skull Pinball WS', player)
                    room = world.get_room(door.roomIndex, player)
                    if room.doorList[door.doorListPos][1] == DoorKind.Trap:
                        room.change(door.doorListPos, DoorKind.Normal)
                        door.trapFlag = 0x0
                        door.blocked = False
                finished = True
                continue
            prev_choices = choices_master[depth]
            # make a choice
            hanger, hook = make_a_choice(dungeon, hangers, hooks, prev_choices, name)
            if hanger is None:
                backtrack = True
            else:
                logger.debug(' ' * depth + "%d: Linking %s to %s", depth, hanger.name, hook.name)
                proposed_map[hanger] = hook
                proposed_map[hook] = hanger
                last_choice = (hanger, hook)
                choices_master[depth].append(last_choice)
                depth += 1
                choices_master.append([])
        else:
            backtrack = True
        if backtrack:
            backtrack = False
            choices_master.pop()
            dungeon_cache.pop(depth, None)
            depth -= 1
            if depth < 0:
                raise GenerationException('Invalid dungeon. Ref %s' % name)
            a, b = choices_master[depth][-1]
            logger.debug(' ' * depth + "%d: Rescinding %s, %s", depth, a.name, b.name)
            proposed_map.pop(a, None)
            proposed_map.pop(b, None)
    return proposed_map


def determine_if_bk_needed(sector, split_dungeon, world, player):
    if not split_dungeon:
        for region in sector.regions:
            for ext in region.exits:
                door = world.check_for_door(ext.name, player)
                if door is not None and door.bigKey:
                    return True
    return False


def check_for_special(sector):
    for region in sector.regions:
        for loc in region.locations:
            if loc.forced_big_key():
                return True
    return False


def gen_dungeon_info(name, available_sectors, entrance_regions, all_regions, proposed_map, valid_doors, bk_needed, bk_special, world, player):
    # step 1 create dungeon: Dict<DoorName|Origin, GraphPiece>
    dungeon = {}
    start = ExplorationState(dungeon=name)
    start.big_key_special = bk_special
    group_flags, door_map = find_bk_groups(name, available_sectors, proposed_map, bk_special)
    bk_flag = False if world.bigkeyshuffle[player] and not bk_special else bk_needed

    def exception(d):
        return name == 'Skull Woods 2' and d.name == 'Skull Pinball WS'
    original_state = extend_reachable_state_improved(entrance_regions, start, proposed_map, all_regions,
                                                     valid_doors, bk_flag, world, player, exception)
    dungeon['Origin'] = create_graph_piece_from_state(None, original_state, original_state, proposed_map, exception)
    either_crystal = True  # if all hooks from the origin are either, explore all bits with either
    for hook, crystal in dungeon['Origin'].hooks.items():
        if crystal != CrystalBarrier.Either:
            either_crystal = False
            break
    init_crystal = CrystalBarrier.Either if either_crystal else CrystalBarrier.Orange
    hanger_set = set()
    o_state_cache = {}
    for sector in available_sectors:
        for door in sector.outstanding_doors:
            if door not in proposed_map.keys():
                hanger_set.add(door)
                bk_flag = group_flags[door_map[door]]
                parent = door.entrance.parent_region
                crystal_start = CrystalBarrier.Either if parent.crystal_switch else init_crystal
                init_state = ExplorationState(crystal_start, dungeon=name)
                init_state.big_key_special = start.big_key_special
                o_state = extend_reachable_state_improved([parent], init_state, proposed_map, all_regions,
                                                          valid_doors, bk_flag, world, player, exception)
                o_state_cache[door.name] = o_state
                piece = create_graph_piece_from_state(door, o_state, o_state, proposed_map, exception)
                dungeon[door.name] = piece
    check_blue_states(hanger_set, dungeon, o_state_cache, proposed_map, all_regions, valid_doors,
                      group_flags, door_map, world, player, exception)

    # catalog hooks: Dict<Hook, List<Door, Crystal, Door>>
    # and hangers: Dict<Hang, List<Door>>
    avail_hooks = defaultdict(list)
    hangers = defaultdict(list)
    for key, piece in dungeon.items():
        door_hang = piece.hanger_info
        if door_hang is not None:
            hanger = hanger_from_door(door_hang)
            hangers[hanger].append(door_hang)
        for door, crystal in piece.hooks.items():
            hook = hook_from_door(door)
            avail_hooks[hook].append((door, crystal, door_hang))

    # thin out invalid hanger
    winnow_hangers(hangers, avail_hooks)
    return dungeon, hangers, avail_hooks


def find_bk_groups(name, available_sectors, proposed_map, bk_special):
    groups = {}
    door_ids = {}
    gid = 1
    for sector in available_sectors:
        if bk_special:
            my_gid = None
            for door in sector.outstanding_doors:
                if door in proposed_map and proposed_map[door] in door_ids:
                    if my_gid:
                        merge_gid = door_ids[proposed_map[door]]
                        for door in door_ids.keys():
                            if door_ids[door] == merge_gid:
                                door_ids[door] = my_gid
                        groups[my_gid] = groups[my_gid] or groups[merge_gid]
                    else:
                        my_gid = door_ids[proposed_map[door]]
            if not my_gid:
                my_gid = gid
                gid += 1
            for door in sector.outstanding_doors:
                door_ids[door] = my_gid
            if my_gid not in groups.keys():
                groups[my_gid] = False
            for region in sector.regions:
                for loc in region.locations:
                    if loc.forced_item and loc.item.bigkey and name in loc.item.name:
                        groups[my_gid] = True
        else:
            for door in sector.outstanding_doors:
                door_ids[door] = gid
            groups[gid] = False
    return groups, door_ids


def check_blue_states(hanger_set, dungeon, o_state_cache, proposed_map, all_regions, valid_doors, group_flags, door_map,
                      world, player, exception):
    not_blue = set()
    not_blue.update(hanger_set)
    doors_to_check = set()
    doors_to_check.update(hanger_set)  # doors to check, check everything on first pass
    blue_hooks = []
    blue_hangers = []
    new_blues = True
    while new_blues:
        new_blues = False
        for door in doors_to_check:
            piece = dungeon[door.name]
            for hook, crystal in piece.hooks.items():
                if crystal != CrystalBarrier.Orange:
                    h_type = hook_from_door(hook)
                    if h_type not in blue_hooks:
                        new_blues = True
                        blue_hooks.append(h_type)
            if piece.hanger_crystal == CrystalBarrier.Either:
                h_type = hanger_from_door(piece.hanger_info)
                if h_type not in blue_hangers:
                    new_blues = True
                    blue_hangers.append(h_type)
        doors_to_check = set()
        for door in not_blue:  # am I now blue?
            hang_type = hanger_from_door(door)  # am I hangable on a hook?
            hook_type = hook_from_door(door)  # am I hookable onto a hanger?
            if (hang_type in blue_hooks and not door.stonewall) or hook_type in blue_hangers:
                bk_flag = group_flags[door_map[door]]
                explore_blue_state(door, dungeon, o_state_cache[door.name], proposed_map, all_regions, valid_doors,
                                   bk_flag, world, player, exception)
                doors_to_check.add(door)
        not_blue.difference_update(doors_to_check)


def explore_blue_state(door, dungeon, o_state, proposed_map, all_regions, valid_doors, bk_flag, world, player, exception):
    parent = door.entrance.parent_region
    blue_start = ExplorationState(CrystalBarrier.Blue, o_state.dungeon)
    blue_start.big_key_special = o_state.big_key_special
    b_state = extend_reachable_state_improved([parent], blue_start, proposed_map, all_regions, valid_doors, bk_flag,
                                              world, player, exception)
    dungeon[door.name] = create_graph_piece_from_state(door, o_state, b_state, proposed_map, exception)


def make_a_choice(dungeon, hangers, avail_hooks, prev_choices, name):
    # choose a hanger
    all_hooks = {}
    origin = dungeon['Origin']
    for key in avail_hooks.keys():
        for hstuff in avail_hooks[key]:
            all_hooks[hstuff[0]] = None
    candidate_hangers = []
    for key in hangers.keys():
        candidate_hangers.extend(hangers[key])
    candidate_hangers.sort(key=lambda x: x.name)  # sorting to create predictable seeds
    random.shuffle(candidate_hangers)  # randomize if equal preference
    stage_2_hangers = []
    if len(prev_choices) > 0:
        prev_hanger = prev_choices[0][0]
        if prev_hanger in candidate_hangers:
            stage_2_hangers.append(prev_hanger)
            candidate_hangers.remove(prev_hanger)
    hookable_hangers = collections.deque()
    queue = collections.deque(candidate_hangers)
    while len(queue) > 0:
        c_hang = queue.popleft()
        if c_hang in all_hooks.keys():
            hookable_hangers.append(c_hang)
        else:
            stage_2_hangers.append(c_hang)  # prefer hangers that are not hooks
    # todo : prefer hangers with fewer hooks at some point? not sure about this
    # this prefer hangers of the fewest type - to catch problems fast
    hookable_hangers = sorted(hookable_hangers, key=lambda door: len(hangers[hanger_from_door(door)]), reverse=True)
    origin_hangers = []
    while len(hookable_hangers) > 0:
        c_hang = hookable_hangers.pop()
        if c_hang in origin.hooks.keys():
            origin_hangers.append(c_hang)
        else:
            stage_2_hangers.append(c_hang)  # prefer hangers that are not hooks on the 'origin'
    stage_2_hangers.extend(origin_hangers)

    hook = None
    next_hanger = None
    while hook is None:
        if len(stage_2_hangers) == 0:
            return None, None
        next_hanger = stage_2_hangers.pop(0)
        next_hanger_type = hanger_from_door(next_hanger)
        hook_candidates = []
        for door, crystal, orig_hang in avail_hooks[next_hanger_type]:
            if filter_choices(next_hanger, door, orig_hang, prev_choices, hook_candidates):
                hook_candidates.append(door)
        if len(hook_candidates) > 0:
            hook_candidates.sort(key=lambda x: x.name)  # sort for deterministic seeds
            hook = random.choice(tuple(hook_candidates))
        elif name == 'Skull Woods 2' and next_hanger.name == 'Skull Pinball WS':
            continue
        else:
            return None, None

    return next_hanger, hook


def filter_choices(next_hanger, door, orig_hang, prev_choices, hook_candidates):
    if (next_hanger, door) in prev_choices or (door, next_hanger) in prev_choices:
        return False
    return next_hanger != door and orig_hang != next_hanger and door not in hook_candidates


def check_valid(name, dungeon, hangers, hooks, proposed_map, doors_to_connect, all_regions,
                bk_needed, bk_special, paths, entrance_regions, world, player):
    # evaluate if everything is still plausible

    # only origin is left in the dungeon and not everything is connected
    if len(dungeon.keys()) <= 1 and len(proposed_map.keys()) < len(doors_to_connect):
        return False
    # origin has no more hooks, but not all doors have been proposed
    if not world.bigkeyshuffle[player]:
        possible_bks = len(dungeon['Origin'].possible_bk_locations)
        true_origin_hooks = [x for x in dungeon['Origin'].hooks.keys() if not x.bigKey or possible_bks > 0 or not bk_needed]
        if len(true_origin_hooks) == 0 and len(proposed_map.keys()) < len(doors_to_connect):
            return False
        if len(true_origin_hooks) == 0 and bk_needed and possible_bks == 0 and len(proposed_map.keys()) == len(doors_to_connect):
            return False
    for key in hangers.keys():
        if len(hooks[key]) > 0 and len(hangers[key]) == 0:
            return False
    # todo: stonewall - check that there's no hook-only that is without a matching hanger
    must_hang = defaultdict(list)
    all_hooks = set()
    for key in hooks.keys():
        for hook in hooks[key]:
            all_hooks.add(hook[0])
    for key in hangers.keys():
        for hanger in hangers[key]:
            if hanger not in all_hooks:
                must_hang[key].append(hanger)
    for key in must_hang.keys():
        if len(must_hang[key]) > len(hooks[key]):
            return False
    outstanding_doors = defaultdict(list)
    for d in doors_to_connect.values():
        if d not in proposed_map.keys():
            outstanding_doors[hook_from_door(d)].append(d)
    for key in outstanding_doors.keys():
        opp_key = opposite_h_type(key)
        if len(outstanding_doors[key]) > 0 and len(hangers[key]) == 0 and len(hooks[opp_key]) == 0:
            return False
    all_visited = set()
    bk_possible = not bk_needed or (world.bigkeyshuffle[player] and not bk_special)
    for piece in dungeon.values():
        all_visited.update(piece.visited_regions)
        if not bk_possible and len(piece.possible_bk_locations) > 0:
            bk_possible = True
    if len(all_regions.difference(all_visited)) > 0:
        return False
    if not bk_possible:
        return False
    if not valid_paths(name, paths, entrance_regions, doors_to_connect, all_regions, proposed_map,
                       bk_needed, bk_special, world, player):
        return False
    new_hangers_found = True
    accessible_hook_types = []
    hanger_matching = set()
    all_hangers = set()
    origin_hooks = set(dungeon['Origin'].hooks.keys())
    for door_hook in origin_hooks:
        h_type = hook_from_door(door_hook)
        if h_type not in accessible_hook_types:
            accessible_hook_types.append(h_type)
    while new_hangers_found:
        new_hangers_found = False
        for hanger_set in hangers.values():
            for hanger in hanger_set:
                all_hangers.add(hanger)
                h_type = hanger_from_door(hanger)
                if (h_type in accessible_hook_types or hanger in origin_hooks) and hanger not in hanger_matching:
                    new_hangers_found = True
                    hanger_matching.add(hanger)
                    matching_hooks = dungeon[hanger.name].hooks.keys()
                    origin_hooks.update(matching_hooks)
                    for door_hook in matching_hooks:
                        new_h_type = hook_from_door(door_hook)
                        if new_h_type not in accessible_hook_types:
                            accessible_hook_types.append(new_h_type)
    return len(all_hangers.difference(hanger_matching)) == 0


def valid_paths(name, paths, entrance_regions, valid_doors, all_regions, proposed_map,
                bk_needed, bk_special, world, player):
    for path in paths:
        if type(path) is tuple:
            target = path[1]
            start_regions = []
            for region in all_regions:
                if path[0] == region.name:
                    start_regions.append(region)
                    break
        else:
            target = path
            start_regions = entrance_regions
        if not valid_path(name, start_regions, target, valid_doors, proposed_map, all_regions,
                          bk_needed, bk_special, world, player):
            return False
    return True


def valid_path(name, starting_regions, target, valid_doors, proposed_map, all_regions,
               bk_needed, bk_special, world, player):
    target_regions = set()
    if type(target) is not list:
        for region in all_regions:
            if target == region.name:
                target_regions.add(region)
                break
    else:
        for region in all_regions:
            if region.name in target:
                target_regions.add(region)

    start = ExplorationState(dungeon=name)
    start.big_key_special = bk_special
    bk_flag = False if world.bigkeyshuffle[player] and not bk_special else bk_needed

    def exception(d):
        return name == 'Skull Woods 2' and d.name == 'Skull Pinball WS'
    original_state = extend_reachable_state_improved(starting_regions, start, proposed_map, all_regions,
                                                     valid_doors, bk_flag, world, player, exception)

    for exp_door in original_state.unattached_doors:
        if not exp_door.door.blocked:
            return True  # outstanding connection possible
    for target in target_regions:
        if original_state.visited_at_all(target):
            return True
    return False  # couldn't find an outstanding door or the target


def determine_required_paths(world, player):
    paths = {}
    for name, builder in world.dungeon_layouts[player].items():
        all_regions = builder.master_sector.regions
        paths[name] = determine_paths_for_dungeon(world, player, all_regions, name)
    return paths


boss_path_checks = ['Eastern Boss', 'Desert Boss', 'Hera Boss', 'Tower Agahnim 1', 'PoD Boss', 'Swamp Boss',
                    'Skull Boss', 'Ice Boss', 'Mire Boss', 'TR Boss', 'GT Agahnim 2']

# pinball is allowed to orphan you
drop_path_checks = ['Skull Pot Circle', 'Skull Left Drop', 'Skull Back Drop', 'Sewers Rat Path']


def determine_paths_for_dungeon(world, player, all_regions, name):
    all_r_names = set(x.name for x in all_regions)
    paths = []
    non_hole_portals = []
    for portal in world.dungeon_portals[player]:
        if portal.door.entrance.parent_region in all_regions:
            non_hole_portals.append(portal.door.entrance.parent_region.name)
            if portal.destination:
                paths.append(portal.door.entrance.parent_region.name)
    if world.mode[player] == 'standard' and name == 'Hyrule Castle':
        paths.append('Hyrule Dungeon Cellblock')
        paths.append(('Hyrule Dungeon Cellblock', 'Sanctuary'))
    if world.doorShuffle[player] in ['basic'] and name == 'Thieves Town':
        paths.append('Thieves Attic Window')
    elif 'Thieves Attic Window' in all_r_names:
        paths.append('Thieves Attic Window')
    for boss in boss_path_checks:
        if boss in all_r_names:
            paths.append(boss)
    if 'Thieves Boss' in all_r_names:
        paths.append('Thieves Boss')
        paths.append(('Thieves Blind\'s Cell', 'Thieves Boss'))
    for drop_check in drop_path_checks:
        if drop_check in all_r_names:
            paths.append((drop_check, non_hole_portals))
    return paths


def winnow_hangers(hangers, hooks):
    removal_info = []
    for hanger, door_set in hangers.items():
        for door in door_set:
            hook_set = hooks[hanger]
            if len(hook_set) == 0:
                removal_info.append((hanger, door))
            else:
                found_valid = False
                for door_hook, crystal, orig_hanger in hook_set:
                    if orig_hanger != door:
                        found_valid = True
                        break
                if not found_valid:
                    removal_info.append((hanger, door))
    for hanger, door in removal_info:
        hangers[hanger].remove(door)


def stonewall_valid(stonewall):
    bad_door = stonewall.dest
    if bad_door.blocked:
        return True  # great we're done with this one
    loop_region = stonewall.entrance.parent_region
    start_regions = [bad_door.entrance.parent_region]
    if bad_door.dependents:
        for dep in bad_door.dependents:
            start_regions.append(dep.entrance.parent_region)
    queue = deque(start_regions)
    visited = set(start_regions)
    while len(queue) > 0:
        region = queue.popleft()
        if region == loop_region:
            return False  # guaranteed loop
        possible_entrances = list(region.entrances)
        for entrance in possible_entrances:
            parent = entrance.parent_region
            if parent.type != RegionType.Dungeon:
                return False  # you can get stuck from an entrance
            else:
                door = entrance.door
                if (door is None or (door != stonewall and not door.blocked)) and parent not in visited:
                    visited.add(parent)
                    queue.append(parent)
    # we didn't find anything bad
    return True


def create_graph_piece_from_state(door, o_state, b_state, proposed_map, exception):
    # todo: info about dungeon events - not sure about that
    graph_piece = GraphPiece()
    all_unattached = {}
    for exp_d in o_state.unattached_doors:
        all_unattached[exp_d.door] = exp_d.crystal
    for exp_d in b_state.unattached_doors:
        d = exp_d.door
        if d in all_unattached.keys():
            if all_unattached[d] != exp_d.crystal:
                if all_unattached[d] == CrystalBarrier.Orange and exp_d.crystal == CrystalBarrier.Blue:
                    all_unattached[d] = CrystalBarrier.Null
                elif all_unattached[d] == CrystalBarrier.Blue and exp_d.crystal == CrystalBarrier.Orange:
                    # the swapping case
                    logging.getLogger('').warning('Mismatched state @ %s (o:%s b:%s)', d.name, all_unattached[d],
                                                  exp_d.crystal)
                elif all_unattached[d] == CrystalBarrier.Either:
                    all_unattached[d] = exp_d.crystal  # pessimism, and if not this, leave it alone
        else:
            all_unattached[exp_d.door] = exp_d.crystal
    h_crystal = door.crystal if door is not None else None
    for d, crystal in all_unattached.items():
        if (door is None or d != door) and (not d.blocked or exception(d))and d not in proposed_map.keys():
            graph_piece.hooks[d] = crystal
        if d == door:
            h_crystal = crystal
    graph_piece.hanger_info = door
    graph_piece.hanger_crystal = h_crystal
    graph_piece.visited_regions.update(o_state.visited_blue)
    graph_piece.visited_regions.update(o_state.visited_orange)
    graph_piece.visited_regions.update(b_state.visited_blue)
    graph_piece.visited_regions.update(b_state.visited_orange)
    graph_piece.possible_bk_locations.update(filter_for_potential_bk_locations(o_state.bk_found))
    graph_piece.possible_bk_locations.update(filter_for_potential_bk_locations(b_state.bk_found))
    graph_piece.pinball_used = o_state.pinball_used or b_state.pinball_used
    return graph_piece


def filter_for_potential_bk_locations(locations):
    return [x for x in locations if
            '- Big Chest' not in x.name and '- Prize' not in x.name and x.name not in dungeon_events
            and  not x.forced_item and x.name not in ['Agahnim 1', 'Agahnim 2']]


type_map = {
    Hook.Stairs: Hook.Stairs,
    Hook.North: Hook.South,
    Hook.South: Hook.North,
    Hook.West: Hook.East,
    Hook.East: Hook.West
}


def opposite_h_type(h_type) -> Hook:
    return type_map[h_type]


hang_dir_map = {
    Direction.North: Hook.South,
    Direction.South: Hook.North,
    Direction.West: Hook.East,
    Direction.East: Hook.West,
}


def hanger_from_door(door):
    if door.type == DoorType.SpiralStairs:
        return Hook.Stairs
    if door.type in [DoorType.Normal, DoorType.Open, DoorType.StraightStairs, DoorType.Ladder]:
        return hang_dir_map[door.direction]
    return None


def connect_doors(a, b):
    # Return on unsupported types.
    if a.type in [DoorType.Hole, DoorType.Warp, DoorType.Interior, DoorType.Logical]:
        return
    # Connect supported types
    if a.type in [DoorType.Normal, DoorType.SpiralStairs, DoorType.Open, DoorType.StraightStairs, DoorType.Ladder]:
        if a.blocked:
            connect_one_way(b.entrance, a.entrance)
        elif b.blocked:
            connect_one_way(a.entrance, b.entrance)
        else:
            connect_two_way(a.entrance, b.entrance)
        dep_doors, target = [], None
        if len(a.dependents) > 0:
            dep_doors, target = a.dependents, b
        elif len(b.dependents) > 0:
            dep_doors, target = b.dependents, a
        if target is not None:
            target_region = target.entrance.parent_region
            for dep in dep_doors:
                connect_simple_door(dep, target_region)
        return
    # If we failed to account for a type, panic
    raise RuntimeError('Unknown door type ' + a.type.name)


def connect_two_way(entrance, ext):

    # if these were already connected somewhere, remove the backreference
    if entrance.connected_region is not None:
        entrance.connected_region.entrances.remove(entrance)
    if ext.connected_region is not None:
        ext.connected_region.entrances.remove(ext)

    entrance.connect(ext.parent_region)
    ext.connect(entrance.parent_region)
    if entrance.parent_region.dungeon:
        ext.parent_region.dungeon = entrance.parent_region.dungeon
    x = entrance.door
    y = ext.door
    if x is not None:
        x.dest = y
    if y is not None:
        y.dest = x


def connect_one_way(entrance, ext):

    # if these were already connected somewhere, remove the backreference
    if entrance.connected_region is not None:
        entrance.connected_region.entrances.remove(entrance)
    if ext.connected_region is not None:
        ext.connected_region.entrances.remove(ext)

    entrance.connect(ext.parent_region)
    if entrance.parent_region.dungeon:
        ext.parent_region.dungeon = entrance.parent_region.dungeon
    x = entrance.door
    y = ext.door
    if x is not None:
        x.dest = y
    if y is not None:
        y.dest = x


def connect_simple_door(exit_door, region):
    exit_door.entrance.connect(region)
    exit_door.dest = region


special_big_key_doors = ['Hyrule Dungeon Cellblock Door', "Thieves Blind's Cell Door"]


class ExplorationState(object):

    def __init__(self, init_crystal=CrystalBarrier.Orange, dungeon=None):

        self.unattached_doors = []
        self.avail_doors = []
        self.event_doors = []

        self.visited_orange = []
        self.visited_blue = []
        self.events = set()
        self.crystal = init_crystal

        # key region stuff
        self.door_krs = {}

        # key validation stuff
        self.small_doors = []
        self.big_doors = []
        self.opened_doors = []
        self.big_key_opened = False
        self.big_key_special = False

        self.found_locations = []
        self.ttl_locations = 0
        self.used_locations = 0
        self.key_locations = 0
        self.used_smalls = 0
        self.bk_found = set()

        self.non_door_entrances = []
        self.dungeon = dungeon
        self.pinball_used = False

    def copy(self):
        ret = ExplorationState(dungeon=self.dungeon)
        ret.unattached_doors = list(self.unattached_doors)
        ret.avail_doors = list(self.avail_doors)
        ret.event_doors = list(self.event_doors)
        ret.visited_orange = list(self.visited_orange)
        ret.visited_blue = list(self.visited_blue)
        ret.events = set(self.events)
        ret.crystal = self.crystal
        ret.door_krs = self.door_krs.copy()

        ret.small_doors = list(self.small_doors)
        ret.big_doors = list(self.big_doors)
        ret.opened_doors = list(self.opened_doors)
        ret.big_key_opened = self.big_key_opened
        ret.big_key_special = self.big_key_special
        ret.ttl_locations = self.ttl_locations
        ret.key_locations = self.key_locations
        ret.used_locations = self.used_locations
        ret.used_smalls = self.used_smalls
        ret.found_locations = list(self.found_locations)
        ret.bk_found = set(self.bk_found)

        ret.non_door_entrances = list(self.non_door_entrances)
        ret.dungeon = self.dungeon
        ret.pinball_used = self.pinball_used
        return ret

    def next_avail_door(self):
        self.avail_doors.sort(key=lambda x: 0 if x.flag else 1 if x.door.bigKey else 2)
        exp_door = self.avail_doors.pop()
        self.crystal = exp_door.crystal
        return exp_door

    def visit_region(self, region, key_region=None, key_checks=False, bk_Flag=False):
        if self.crystal == CrystalBarrier.Either:
            if region not in self.visited_blue:
                self.visited_blue.append(region)
            if region not in self.visited_orange:
                self.visited_orange.append(region)
        elif self.crystal == CrystalBarrier.Orange:
            self.visited_orange.append(region)
        elif self.crystal == CrystalBarrier.Blue:
            self.visited_blue.append(region)
        if region.type == RegionType.Dungeon:
            for location in region.locations:
                if key_checks and location not in self.found_locations:
                    if location.forced_item and 'Small Key' in location.item.name:
                        self.key_locations += 1
                    if location.name not in dungeon_events and '- Prize' not in location.name and location.name not in ['Agahnim 1', 'Agahnim 2']:
                        self.ttl_locations += 1
                if location not in self.found_locations:  # todo: special logic for TT Boss?
                    self.found_locations.append(location)
                    if not bk_Flag:
                        self.bk_found.add(location)
                if location.name in dungeon_events and location.name not in self.events:
                    if self.flooded_key_check(location):
                        self.perform_event(location.name, key_region)
                if location.name in flooded_keys_reverse.keys() and self.location_found(
                     flooded_keys_reverse[location.name]):
                    self.perform_event(flooded_keys_reverse[location.name], key_region)

    def flooded_key_check(self, location):
        if location.name not in flooded_keys.keys():
            return True
        return flooded_keys[location.name] in [x.name for x in self.found_locations]

    def location_found(self, location_name):
        for l in self.found_locations:
            if l.name == location_name:
                return True
        return False

    def perform_event(self, location_name, key_region):
        self.events.add(location_name)
        queue = collections.deque(self.event_doors)
        while len(queue) > 0:
            exp_door = queue.popleft()
            if exp_door.door.req_event == location_name:
                self.avail_doors.append(exp_door)
                self.event_doors.remove(exp_door)
                if key_region is not None:
                    d_name = exp_door.door.name
                    if d_name not in self.door_krs.keys():
                        self.door_krs[d_name] = key_region

    def add_all_entrance_doors_check_unattached(self, region, world, player):
        door_list = [x for x in get_doors(world, region, player) if x.type in [DoorType.Normal, DoorType.SpiralStairs]]
        door_list.extend(get_entrance_doors(world, region, player))
        for door in door_list:
            if self.can_traverse(door):
                if door.dest is None and not self.in_door_list_ic(door, self.unattached_doors):
                    self.append_door_to_list(door, self.unattached_doors)
                elif door.req_event is not None and door.req_event not in self.events and not self.in_door_list(door,
                                                                                                                self.event_doors):
                    self.append_door_to_list(door, self.event_doors)
                elif not self.in_door_list(door, self.avail_doors):
                    self.append_door_to_list(door, self.avail_doors)
        for entrance in region.entrances:
            door = world.check_for_door(entrance.name, player)
            if door is None:
                self.non_door_entrances.append(entrance)

    def add_all_doors_check_unattached(self, region, world, player):
        for door in get_doors(world, region, player):
            if self.can_traverse(door):
                if door.controller is not None:
                    door = door.controller
                if door.dest is None and not self.in_door_list_ic(door, self.unattached_doors):
                    self.append_door_to_list(door, self.unattached_doors)
                elif door.req_event is not None and door.req_event not in self.events and not self.in_door_list(door,
                                                                                                                self.event_doors):
                    self.append_door_to_list(door, self.event_doors)
                elif not self.in_door_list(door, self.avail_doors):
                    self.append_door_to_list(door, self.avail_doors)

    def add_all_doors_check_proposed(self, region, proposed_map, valid_doors, flag, world, player, exception):
        for door in get_doors(world, region, player):
            if door.blocked and exception(door):
                self.pinball_used = True
            if self.can_traverse(door, exception):
                if door.controller is not None:
                    door = door.controller
                if door.dest is None and door not in proposed_map.keys() and door.name in valid_doors.keys():
                    if not self.in_door_list_ic(door, self.unattached_doors):
                        self.append_door_to_list(door, self.unattached_doors, flag)
                    else:
                        other = self.find_door_in_list(door, self.unattached_doors)
                        if self.crystal != other.crystal:
                            other.crystal = CrystalBarrier.Either
                elif door.req_event is not None and door.req_event not in self.events and not self.in_door_list(door,
                                                                                                                self.event_doors):
                    self.append_door_to_list(door, self.event_doors, flag)
                elif not self.in_door_list(door, self.avail_doors):
                    self.append_door_to_list(door, self.avail_doors, flag)

    def add_all_doors_check_key_region(self, region, key_region, world, player):
        for door in get_doors(world, region, player):
            if self.can_traverse(door):
                if door.req_event is not None and door.req_event not in self.events and not self.in_door_list(door,
                                                                                                              self.event_doors):
                    self.append_door_to_list(door, self.event_doors)
                elif not self.in_door_list(door, self.avail_doors):
                    self.append_door_to_list(door, self.avail_doors)
                    if door.name not in self.door_krs.keys():
                        self.door_krs[door.name] = key_region
            else:
                if door.name not in self.door_krs.keys():
                    self.door_krs[door.name] = key_region

    def add_all_doors_check_keys(self, region, key_door_proposal, world, player):
        for door in get_doors(world, region, player):
            if self.can_traverse(door):
                if door.controller:
                    door = door.controller
                if door in key_door_proposal and door not in self.opened_doors:
                    if not self.in_door_list(door, self.small_doors):
                        self.append_door_to_list(door, self.small_doors)
                elif (door.bigKey or door.name in special_big_key_doors) and not self.big_key_opened:
                    if not self.in_door_list(door, self.big_doors):
                        self.append_door_to_list(door, self.big_doors)
                elif door.req_event is not None and door.req_event not in self.events:
                    if not self.in_door_list(door, self.event_doors):
                        self.append_door_to_list(door, self.event_doors)
                elif not self.in_door_list(door, self.avail_doors):
                    self.append_door_to_list(door, self.avail_doors)

    def visited(self, region):
        if self.crystal == CrystalBarrier.Either:
            return region in self.visited_blue and region in self.visited_orange
        elif self.crystal == CrystalBarrier.Orange:
            return region in self.visited_orange
        elif self.crystal == CrystalBarrier.Blue:
            return region in self.visited_blue
        return False

    def visited_at_all(self, region):
        return region in self.visited_blue or region in self.visited_orange

    def found_forced_bk(self):
        for location in self.found_locations:
            if location.forced_big_key():
                return True
        return False

    def can_traverse(self, door, exception=None):
        if door.blocked:
            return exception(door) if exception else False
        if door.crystal not in [CrystalBarrier.Null, CrystalBarrier.Either]:
            return self.crystal == CrystalBarrier.Either or door.crystal == self.crystal
        return True

    def count_locations_exclude_specials(self):
        cnt = 0
        for loc in self.found_locations:
            if '- Big Chest' not in loc.name and '- Prize' not in loc.name and loc.name not in dungeon_events and not loc.forced_item:
                cnt += 1
        return cnt

    def validate(self, door, region, world, player):
        return self.can_traverse(door) and not self.visited(region) and valid_region_to_explore(region, self.dungeon,
                                                                                                world, player)

    def in_door_list(self, door, door_list):
        for d in door_list:
            if d.door == door and d.crystal == self.crystal:
                return True
        return False

    @staticmethod
    def in_door_list_ic(door, door_list):
        for d in door_list:
            if d.door == door:
                return True
        return False

    @staticmethod
    def find_door_in_list(door, door_list):
        for d in door_list:
            if d.door == door:
                return d
        return None

    def append_door_to_list(self, door, door_list, flag=False):
        if door.crystal == CrystalBarrier.Null:
            door_list.append(ExplorableDoor(door, self.crystal, flag))
        else:
            door_list.append(ExplorableDoor(door, door.crystal, flag))

    def key_door_sort(self, d):
        if d.door.smallKey:
            if d.door in self.opened_doors:
                return 1
            else:
                return 0
        return 2


class ExplorableDoor(object):

    def __init__(self, door, crystal, flag):
        self.door = door
        self.crystal = crystal
        self.flag = flag

    def __str__(self):
        return str(self.__unicode__())

    def __unicode__(self):
        return '%s (%s)' % (self.door.name, self.crystal.name)


def extend_reachable_state_improved(search_regions, state, proposed_map, all_regions, valid_doors, bk_flag, world, player, exception):
    local_state = state.copy()
    for region in search_regions:
        local_state.visit_region(region)
        local_state.add_all_doors_check_proposed(region, proposed_map, valid_doors, False, world, player, exception)
    while len(local_state.avail_doors) > 0:
        explorable_door = local_state.next_avail_door()
        if explorable_door.door.bigKey:
            if bk_flag:
                big_not_found = not special_big_key_found(local_state) if local_state.big_key_special else local_state.count_locations_exclude_specials() == 0
                if big_not_found:
                    continue  # we can't open this door
        if explorable_door.door in proposed_map:
            connect_region = world.get_entrance(proposed_map[explorable_door.door].name, player).parent_region
        else:
            connect_region = world.get_entrance(explorable_door.door.name, player).connected_region
        if connect_region is not None:
            if valid_region_to_explore_in_regions(connect_region, all_regions, world, player) and not local_state.visited(
                 connect_region):
                flag = explorable_door.flag or explorable_door.door.bigKey
                local_state.visit_region(connect_region, bk_Flag=flag)
                local_state.add_all_doors_check_proposed(connect_region, proposed_map, valid_doors, flag, world, player, exception)
    return local_state


def special_big_key_found(state):
    for location in state.found_locations:
        if location.forced_item and location.forced_item.bigkey:
            return True
    return False


def valid_region_to_explore_in_regions(region, all_regions, world, player):
    if region is None:
        return False
    return (region.type == RegionType.Dungeon and region in all_regions)\
        or region.name in world.inaccessible_regions[player]\
        or (region.name == 'Hyrule Castle Ledge' and world.mode[player] == 'standard')


# cross-utility methods
def valid_region_to_explore(region, name, world, player):
    if region is None:
        return False
    return (region.type == RegionType.Dungeon and region.dungeon.name in name)\
        or region.name in world.inaccessible_regions[player]\
        or (region.name == 'Hyrule Castle Ledge' and world.mode[player] == 'standard')


def get_doors(world, region, player):
    res = []
    for ext in region.exits:
        door = world.check_for_door(ext.name, player)
        if door is not None:
            res.append(door)
    return res


def get_dungeon_doors(region, world, player):
    res = []
    for ext in region.exits:
        door = world.check_for_door(ext.name, player)
        if door is not None and ext.parent_region.type == RegionType.Dungeon:
            res.append(door)
    return res


def get_entrance_doors(world, region, player):
    res = []
    for ext in region.entrances:
        door = world.check_for_door(ext.name, player)
        if door is not None:
            res.append(door)
    return res


def convert_regions(region_names, world, player):
    region_list = []
    for name in region_names:
        region_list.append(world.get_region(name, player))
    return region_list


# Begin crossed mode sector shuffle

class DungeonBuilder(object):

    def __init__(self, name):
        self.name = name
        self.sectors = []
        self.location_cnt = 0
        self.key_drop_cnt = 0
        self.bk_required = False
        self.bk_provided = False
        self.c_switch_required = False
        self.c_switch_present = False
        self.c_locked = False
        self.dead_ends = 0
        self.branches = 0
        self.forced_loops = 0
        self.total_conn_lack = 0
        self.conn_needed = defaultdict(int)
        self.conn_supplied = defaultdict(int)
        self.conn_balance = defaultdict(int)
        self.mag_needed = {}
        self.unfulfilled = defaultdict(int)
        self.all_entrances = None  # used for sector segregation/branching
        self.entrance_list = None  # used for overworld accessibility
        self.layout_starts = None  # used for overworld accessibility
        self.master_sector = None
        self.path_entrances = None  # used for pathing/key doors, I think
        self.split_flag = False

        self.pre_open_stonewalls = set()  # used by stonewall system

        self.candidates = None
        self.key_doors_num = None
        self.combo_size = None
        self.flex = 0
        self.key_door_proposal = None

        self.allowance = None
        if 'Stonewall' in name:
            self.allowance = 1
        elif 'Prewall' in name:
            orig_name = name[:-8]
            if orig_name in dungeon_dead_end_allowance.keys():
                self.allowance = dungeon_dead_end_allowance[orig_name]
        if self.allowance is None:
            self.allowance = 1

        self.valid_proposal = None
        self.split_dungeon_map = None
        self.exception_list = []

    def polarity_complement(self):
        pol = Polarity()
        for sector in self.sectors:
            pol += sector.polarity()
        return pol.complement()

    def polarity(self):
        pol = Polarity()
        for sector in self.sectors:
            pol += sector.polarity()
        return pol

    def __str__(self):
        return str(self.__unicode__())

    def __unicode__(self):
        return '%s' % self.name


def simple_dungeon_builder(name, sector_list):
    define_sector_features(sector_list)
    builder = DungeonBuilder(name)
    dummy_pool = dict.fromkeys(sector_list)
    global_pole = GlobalPolarity(dummy_pool)
    for sector in sector_list:
        assign_sector(sector, builder, dummy_pool, global_pole)
    return builder


def create_dungeon_builders(all_sectors, connections_tuple, world, player,
                            dungeon_entrances=None, split_dungeon_entrances=None):
    logger = logging.getLogger('')
    logger.info('Shuffling Dungeon Sectors')

    if dungeon_entrances is None:
        dungeon_entrances = default_dungeon_entrances
    if split_dungeon_entrances is None:
        split_dungeon_entrances = split_region_starts
    define_sector_features(all_sectors)
    finished, dungeon_map, attempts = False, {}, 0
    while not finished:
        candidate_sectors = dict.fromkeys(all_sectors)
        global_pole = GlobalPolarity(candidate_sectors)

        dungeon_map = {}
        for key in dungeon_regions.keys():
            dungeon_map[key] = DungeonBuilder(key)
        for key in dungeon_boss_sectors.keys():
            current_dungeon = dungeon_map[key]
            for r_name in dungeon_boss_sectors[key]:
                assign_sector(find_sector(r_name, candidate_sectors), current_dungeon, candidate_sectors, global_pole)
            if key == 'Hyrule Castle' and world.mode[player] == 'standard':
                for r_name in ['Hyrule Dungeon Cellblock', 'Sanctuary']:  # need to deliver zelda
                    assign_sector(find_sector(r_name, candidate_sectors), current_dungeon,
                                  candidate_sectors, global_pole)
                standard_stair_check(dungeon_map, current_dungeon, candidate_sectors, global_pole)
        entrances_map, potentials, connections = connections_tuple
        accessible_sectors, reverse_d_map = set(), {}
        for key in dungeon_entrances.keys():
            current_dungeon = dungeon_map[key]
            current_dungeon.all_entrances = dungeon_entrances[key]
            for r_name in current_dungeon.all_entrances:
                sector = find_sector(r_name, candidate_sectors)
                assign_sector(sector, current_dungeon, candidate_sectors, global_pole)
                if r_name in entrances_map[key]:
                    if sector:
                        accessible_sectors.add(sector)
                else:
                    if not sector:
                        sector = find_sector(r_name, all_sectors)
                    reverse_d_map[sector] = key

        complete_dungeons = {x: y for x, y in dungeon_map.items() if sum(len(sector.outstanding_doors) for sector in y.sectors) <= 0}
        [dungeon_map.pop(key) for key in complete_dungeons.keys()]

        # categorize sectors
        identify_destination_sectors(accessible_sectors, reverse_d_map, dungeon_map, connections,
                                     dungeon_entrances, split_dungeon_entrances)
        for name, builder in dungeon_map.items():
            calc_allowance_and_dead_ends(builder, connections_tuple, world, player)

        if world.mode[player] == 'open' and world.shuffle[player] not in ['crossed', 'insanity']:
            sanc = find_sector('Sanctuary', candidate_sectors)
            if sanc:  # only run if sanc if a candidate
                lw_builders = []
                for name, portal_list in dungeon_portals.items():
                    for portal_name in portal_list:
                        if world.get_portal(portal_name, player).light_world:
                            lw_builders.append(dungeon_map[name])
                            break
                # portals only - not drops for mirror stuff
                sanc_builder = random.choice(lw_builders)
                assign_sector(sanc, sanc_builder, candidate_sectors, global_pole)

        free_location_sectors = {}
        crystal_switches = {}
        crystal_barriers = {}
        polarized_sectors = {}
        neutral_sectors = {}
        for sector in candidate_sectors:
            if sector.chest_locations > 0:
                free_location_sectors[sector] = None
            elif sector.c_switch:
                crystal_switches[sector] = None
            elif sector.blue_barrier:
                crystal_barriers[sector] = None
            elif sector.polarity().is_neutral():
                neutral_sectors[sector] = None
            else:
                polarized_sectors[sector] = None
        assign_location_sectors(dungeon_map, free_location_sectors, global_pole)
        leftover = assign_crystal_switch_sectors(dungeon_map, crystal_switches, crystal_barriers, global_pole)
        ensure_crystal_switches_reachable(dungeon_map, leftover, polarized_sectors, crystal_barriers, global_pole)
        for sector in leftover:
            if sector.polarity().is_neutral():
                neutral_sectors[sector] = None
            else:
                polarized_sectors[sector] = None
        # blue barriers
        assign_crystal_barrier_sectors(dungeon_map, crystal_barriers, global_pole)
        try:
            # polarity:
            if not global_pole.is_valid(dungeon_map):
                # restart
                raise NeutralizingException('Either free location/crystal assignment is already globally invalid')
            logger.info(world.fish.translate("cli", "cli", "balance.doors"))
            builder_info = dungeon_entrances, split_dungeon_entrances, connections_tuple, world, player
            assign_polarized_sectors(dungeon_map, polarized_sectors, global_pole, builder_info)
            # the rest
            assign_the_rest(dungeon_map, neutral_sectors, global_pole, builder_info)
            dungeon_map.update(complete_dungeons)
            finished = True
        except (NeutralizingException, GenerationException) as e:
            attempts += 1
            logger.debug(f'Attempt {attempts} failed with {str(e)}')
            if attempts >= 10:
                raise Exception('Could not find a valid seed quickly, something is likely horribly wrong.', e)
    return dungeon_map


def standard_stair_check(dungeon_map, dungeon, candidate_sectors, global_pole):
    # this is because there must be at least one non-dead stairway in hc to get out
    # this check may not be necessary
    filtered_sectors = [x for x in candidate_sectors if any(y for y in x.outstanding_doors if not y.dead and y.type == DoorType.SpiralStairs)]
    valid = False
    while not valid:
        chosen_sector = random.choice(filtered_sectors)
        filtered_sectors.remove(chosen_sector)
        valid = global_pole.is_valid_choice(dungeon_map, dungeon, [chosen_sector])
        if valid:
            assign_sector(chosen_sector, dungeon, candidate_sectors, global_pole)


def identify_destination_sectors(accessible_sectors, reverse_d_map, dungeon_map, connections, dungeon_entrances, split_dungeon_entrances):
    accessible_overworld, found_connections, explored = set(), set(), False

    while not explored:
        explored = True
        for ent_name, region in connections.items():
            if ent_name in found_connections:
                continue
            sector = find_sector(ent_name, reverse_d_map.keys())
            if sector in accessible_sectors:
                found_connections.add(ent_name)
                accessible_overworld.add(region)  # todo: drops don't give ow access
                explored = False
            elif region in accessible_overworld:
                found_connections.add(ent_name)
                accessible_sectors.add(sector)
                explored = False
            else:
                d_name = reverse_d_map[sector]
                if d_name not in split_dungeon_entrances:
                    for r_name in dungeon_entrances[d_name]:
                        ent_sector = find_sector(r_name, dungeon_map[d_name].sectors)
                        if ent_sector in accessible_sectors and ent_name not in dead_entrances:
                            sector.destination_entrance = True
                            found_connections.add(ent_name)
                            accessible_sectors.add(sector)
                            accessible_overworld.add(region)
                            explored = False
                            break
                elif d_name in split_dungeon_entrances.keys():
                    split_section = None
                    for split_name, split_list in split_dungeon_entrances[d_name].items():
                        if ent_name in split_list:
                            split_section = split_name
                            break
                    if split_section:
                        for r_name in split_dungeon_entrances[d_name][split_section]:
                            ent_sector = find_sector(r_name, dungeon_map[d_name].sectors)
                            if ent_sector in accessible_sectors and ent_name not in dead_entrances:
                                sector.destination_entrance = True
                                found_connections.add(ent_name)
                                accessible_sectors.add(sector)
                                accessible_overworld.add(region)
                                explored = False
                                break


# todo: split version that adds allowance for potential entrances
def calc_allowance_and_dead_ends(builder, connections_tuple, world, player):
    portals = world.dungeon_portals[player]
    entrances_map, potentials, connections = connections_tuple
    name = builder.name if not builder.split_flag else builder.name.rsplit(' ', 1)[0]
    needed_connections = [x for x in builder.all_entrances if x not in entrances_map[name]]
    starting_allowance = 0
    used_sectors = set()
    destination_entrances = [x.door.entrance.parent_region.name for x in portals if x.destination]
    dead_ends = [x.door.entrance.parent_region.name for x in portals if x.deadEnd]
    for entrance in entrances_map[name]:
        sector = find_sector(entrance, builder.sectors)
        if sector:
            outflow_target = 0 if entrance not in drop_entrances_allowance else 1
            if sector not in used_sectors and (sector.adj_outflow() > outflow_target or entrance in dead_ends):
                if entrance not in destination_entrances:
                    starting_allowance += 1
                else:
                    builder.branches -= 1
                used_sectors.add(sector)
            elif sector not in used_sectors:
                if entrance in destination_entrances and sector.branches() > 0:
                    builder.branches -= 1
                if entrance not in drop_entrances_allowance:
                    needed_connections.append(entrance)
    builder.allowance = starting_allowance
    for entrance in needed_connections:
        sector = find_sector(entrance, builder.sectors)
        if sector and sector not in used_sectors:  # ignore things on same sector
            is_destination = entrance in destination_entrances
            connect_able = False
            if entrance in connections.keys():
                enabling_region = connections[entrance]
                check_list = list(potentials[enabling_region])
                if enabling_region.name in ['Desert Ledge', 'Desert Palace Entrance (North) Spot']:
                    alternate = 'Desert Palace Entrance (North) Spot' if enabling_region.name == 'Desert Ledge' else 'Desert Ledge'
                    check_list.extend(potentials[world.get_region(alternate, player)])
                connecting_entrances = [x for x in check_list if x != entrance and x not in dead_entrances and x not in drop_entrances_allowance]
                connect_able = len(connecting_entrances) > 0
            if is_destination and sector.branches() == 0:  #
                builder.dead_ends += 1
            if is_destination and sector.branches() > 0:
                builder.branches -= 1
            if connect_able and not is_destination:
                builder.allowance += 1
            used_sectors.add(sector)


def define_sector_features(sectors):
    for sector in sectors:
        for region in sector.regions:
            for loc in region.locations:
                if '- Prize' in loc.name or loc.name in ['Agahnim 1', 'Agahnim 2']:
                    pass
                elif loc.forced_item and 'Small Key' in loc.item.name:
                    sector.key_only_locations += 1
                elif loc.forced_item and loc.forced_item.bigkey:
                    sector.bk_provided = True
                elif loc.name not in dungeon_events and not loc.forced_item:
                    sector.chest_locations += 1
                    if '- Big Chest' in loc.name or loc.name in ["Hyrule Castle - Zelda's Chest",
                                                                 "Thieves' Town - Blind's Cell"]:
                        sector.bk_required = True
            for ext in region.exits:
                door = ext.door
                if door is not None:
                    if door.crystal == CrystalBarrier.Either:
                        sector.c_switch = True
                    elif door.crystal == CrystalBarrier.Orange:
                        sector.orange_barrier = True
                    elif door.crystal == CrystalBarrier.Blue:
                        sector.blue_barrier = True
                    if door.bigKey:
                        sector.bk_required = True


def assign_sector(sector, dungeon, candidate_sectors, global_pole):
    if sector:
        del candidate_sectors[sector]
        global_pole.consume(sector)
        assign_sector_helper(sector, dungeon)


def assign_sector_helper(sector, builder):
    builder.sectors.append(sector)
    builder.location_cnt += sector.chest_locations
    builder.key_drop_cnt += sector.key_only_locations
    if sector.c_switch:
        builder.c_switch_present = True
    if sector.blue_barrier:
        builder.c_switch_required = True
    if sector.bk_required:
        builder.bk_required = True
    if sector.bk_provided:
        builder.bk_provided = True
    count_conn_needed_supplied(sector, builder.conn_needed, builder.conn_supplied)
    builder.dead_ends += sector.dead_ends()
    builder.branches += sector.branches()
    if sector in builder.exception_list:
        builder.exception_list.remove(sector)
    else:
        if builder.split_dungeon_map:
            builder.split_dungeon_map = None
        if builder.valid_proposal:
            builder.valid_proposal = None


def count_conn_needed_supplied(sector, conn_needed, conn_supplied):
    for door in sector.outstanding_doors:
        # todo: destination sectors like skull 2 west should be
        if (door.blocked or door.dead or sector.adj_outflow() <= 1) and not sector.is_entrance_sector():
            conn_needed[hook_from_door(door)] += 1
        # todo: stonewall
        else:  # todo: dungeons that need connections... skull, tr, hc, desert (when edges are done)
            conn_supplied[hanger_from_door(door)] += 1


def find_sector(r_name, sectors):
    for s in sectors:
        if r_name in s.region_set():
            return s
    return None


def assign_location_sectors(dungeon_map, free_location_sectors, global_pole):
    valid = False
    choices = None
    sector_list = list(free_location_sectors)
    random.shuffle(sector_list)
    while not valid:
        choices, d_idx, totals = weighted_random_locations(dungeon_map, sector_list)
        for i, sector in enumerate(sector_list):
            choice = d_idx[choices[i].name]
            totals[choice] += sector.chest_locations
        valid = True
        for d_name, idx in d_idx.items():
            if totals[idx] < 5:  # min locations for dungeons is 5 (bk exception)
                valid = False
                break
    for i, choice in enumerate(choices):
        builder = dungeon_map[choice.name]
        assign_sector(sector_list[i], builder, free_location_sectors, global_pole)


def weighted_random_locations(dungeon_map, free_location_sectors):
    population = []
    ttl_assigned = 0
    weights = []
    totals = []
    d_idx = {}
    for i, dungeon_builder in enumerate(dungeon_map.values()):
        population.append(dungeon_builder)
        totals.append(dungeon_builder.location_cnt)
        ttl_assigned += dungeon_builder.location_cnt
        weights.append(6.375)
        d_idx[dungeon_builder.name] = i
    average = ttl_assigned / 13
    for i, db in enumerate(population):
        if db.location_cnt < average:
            weights[i] += average - db.location_cnt
        if db.location_cnt > average:
            weights[i] = max(0, weights[i] - db.location_cnt + average)

    choices = random.choices(population, weights, k=len(free_location_sectors))
    return choices, d_idx, totals


def assign_crystal_switch_sectors(dungeon_map, crystal_switches, crystal_barriers, global_pole, assign_one=False):
    population = []
    some_c_switches_present = False
    for name, builder in dungeon_map.items():
        if builder.c_switch_required and not builder.c_switch_present and not builder.c_locked:
            population.append(name)
        if builder.c_switch_present and not builder.c_locked:
            some_c_switches_present = True
    if len(population) == 0:  # nothing needs a switch
        if assign_one and not some_c_switches_present:  # something should have one
            if len(crystal_switches) == 0:
                raise GenerationException('No crystal switches to assign. Ref %s' % next(iter(dungeon_map.keys())))
            valid, builder_choice, switch_choice = False, None, None
            switch_candidates = list(crystal_switches)
            switch_choice = random.choice(switch_candidates)
            switch_candidates.remove(switch_choice)
            builder_candidates = [name for name, builder in dungeon_map.items() if not builder.c_locked]
            while not valid:
                if len(builder_candidates) == 0:
                    if len(switch_candidates) == 0:
                        raise GenerationException('No where to assign crystal switch. Ref %s' % next(iter(dungeon_map.keys())))
                    switch_choice = random.choice(switch_candidates)
                    switch_candidates.remove(switch_choice)
                    builder_candidates = list(dungeon_map.keys())
                choice = random.choice(builder_candidates)
                builder_candidates.remove(choice)
                builder_choice = dungeon_map[choice]
                test_set = [switch_choice]
                test_set.extend(crystal_barriers)
                valid = global_pole.is_valid_choice(dungeon_map, builder_choice, test_set)
            assign_sector(switch_choice, builder_choice, crystal_switches, global_pole)
        return crystal_switches
    if len(crystal_switches) == 0:
        raise GenerationException('No crystal switches to assign')
    sector_list = list(crystal_switches)
    if len(population) > len(sector_list):
        raise GenerationException('Not enough crystal switch sectors for those needed')
    choices = random.sample(sector_list, k=len(population))
    for i, choice in enumerate(choices):
        builder = dungeon_map[population[i]]
        assign_sector(choice, builder, crystal_switches, global_pole)
    return crystal_switches


def ensure_crystal_switches_reachable(dungeon_map, crystal_switches, polarized_sectors, crystal_barriers, global_pole):
    invalid_builders = []
    for name, builder in dungeon_map.items():
        if builder.c_switch_present and builder.c_switch_required and not builder.c_locked:
            invalid_builders.append(builder)
    while len(invalid_builders) > 0:
        valid_builders = []
        for builder in invalid_builders:
            entrance_sectors = []
            reachable_crystals = defaultdict()
            for sector in builder.sectors:
                if sector.equations is None:
                    sector.equations = calc_sector_equations(sector)
                if sector.is_entrance_sector() and not sector.destination_entrance:
                    need_switch = True
                    for region in sector.get_start_regions():
                        if region.crystal_switch:
                            need_switch = False
                            break
                    any_benefit = False
                    for eq in sector.equations:
                        if len(eq.benefit) > 0:
                            any_benefit = True
                            break
                    if need_switch and any_benefit:
                        entrance_sectors.append(sector)
                for eq in sector.equations:
                    if eq.c_switch:
                        reachable_crystals[hook_from_door(eq.door)] = True
            valid_ent_sectors = []
            for entrance_sector in entrance_sectors:
                other_sectors = [x for x in builder.sectors if x != entrance_sector]
                reachable, access = is_c_switch_reachable(entrance_sector, reachable_crystals, other_sectors)
                if reachable:
                    valid_ent_sectors.append(entrance_sector)
                else:
                    candidates = {}
                    for c in find_pol_cand_for_c_switch(access, reachable_crystals, polarized_sectors):
                        candidates[c] = 'Polarized'
                    for c in find_crystal_cand(access, crystal_switches):
                        candidates[c] = 'Crystals'
                    for c in find_pol_cand_for_c_switch(access, reachable_crystals, crystal_barriers):
                        candidates[c] = 'Barriers'
                    valid, sector, which_list = False, None, None
                    while not valid:
                        if len(candidates) <= 0:
                            raise GenerationException(f'need to provide more sophisticated crystal connection for {entrance_sector}')
                        sector, which_list = random.choice(list(candidates.items()))
                        del candidates[sector]
                        valid = global_pole.is_valid_choice(dungeon_map, builder, [sector])
                    if which_list == 'Polarized':
                        assign_sector(sector, builder, polarized_sectors, global_pole)
                    elif which_list == 'Crystals':
                        assign_sector(sector, builder, crystal_switches, global_pole)
                    elif which_list == 'Barriers':
                        assign_sector(sector, builder, crystal_barriers, global_pole)
            entrance_sectors = [x for x in entrance_sectors if x not in valid_ent_sectors]
            if len(entrance_sectors) == 0:
                valid_builders.append(builder)
        invalid_builders = [x for x in invalid_builders if x not in valid_builders]


def is_c_switch_reachable(entrance_sector, reachable_crystals, other_sectors):
    current_access = {}
    for eq in entrance_sector.equations:
        if eq.total_cost() <= 0:
            for key, door_list in eq.benefit.items():
                for door in door_list:
                    if door not in eq.crystal_blocked.keys() or eq.crystal_blocked[door] != CrystalBarrier.Blue:
                        current_access[key] = True
                        break
    for key, flag in current_access.items():
        if opposite_h_type(key) in reachable_crystals.keys():
            return True, {}
    changed = True
    while changed:
        changed = False
        for sector in other_sectors:
            for eq in sector.equations:
                key, cost_door = eq.cost
                if key in current_access.keys() and current_access[key]:
                    for bene_key, door_list in eq.benefit.items():
                        for door in door_list:
                            block_dict = eq.crystal_blocked
                            if door not in block_dict.keys() or block_dict[door] != CrystalBarrier.Blue:
                                if bene_key not in current_access.keys():
                                    current_access[bene_key] = True
                                    changed = True
                                    break
    for key, flag in current_access.items():
        if opposite_h_type(key) in reachable_crystals.keys():
            return True, {}
    return False, current_access


def find_pol_cand_for_c_switch(access, reachable_crystals, polarized_candidates):
    candidates = []
    for sector in polarized_candidates:
        if pol_cand_matches_access_reach(sector, access, reachable_crystals):
            candidates.append(sector)
    return candidates


def pol_cand_matches_access_reach(sector, access, reachable_crystals):
    if sector.equations is None:
        sector.equations = calc_sector_equations(sector)
    for eq in sector.equations:
        key, cost_door = eq.cost
        if key in access.keys() and access[key]:
            for bene_key, door_list in eq.benefit.items():
                for door in door_list:
                    if door not in eq.crystal_blocked.keys() or eq.crystal_blocked[door] != CrystalBarrier.Blue:
                        if opposite_h_type(bene_key) in reachable_crystals.keys():
                            return True
    return False


def find_crystal_cand(access, crystal_switches):
    candidates = []
    for sector in crystal_switches:
        if crystal_cand_matches_access(sector, access):
            candidates.append(sector)
    return candidates


def crystal_cand_matches_access(sector, access):
    if sector.equations is None:
        sector.equations = calc_sector_equations(sector)
    for eq in sector.equations:
        key, cost_door = eq.cost
        if key in access.keys() and access[key] and eq.c_switch and len(sector.outstanding_doors) > 1:
            return True
    return False


def assign_crystal_barrier_sectors(dungeon_map, crystal_barriers, global_pole):
    population = []
    for name, builder in dungeon_map.items():
        if builder.c_switch_present and not builder.c_locked:
            population.append(name)
    sector_list = list(crystal_barriers)
    random.shuffle(sector_list)
    choices = random.choices(population, k=len(sector_list))
    for i, choice in enumerate(choices):
        builder = dungeon_map[choice]
        assign_sector(sector_list[i], builder, crystal_barriers, global_pole)


def identify_polarity_issues(dungeon_map):
    unconnected_builders = {}
    for name, builder in dungeon_map.items():
        identify_polarity_issues_internal(name, builder, unconnected_builders)
    return unconnected_builders


def identify_polarity_issues_internal(name, builder, unconnected_builders):
    if len(builder.sectors) == 1:
        return
    else:
        def sector_filter(x, y):
            return x != y
        # else:
        #     def sector_filter(x, y):
        #         return x != y and (x.outflow() > 1 or is_entrance_sector(builder, x))
    connection_flags = {}
    for slot in PolSlot:
        connection_flags[slot] = {}
        for slot2 in PolSlot:
            connection_flags[slot][slot2] = False
    for sector in builder.sectors:
        others = [x for x in builder.sectors if sector_filter(x, sector)]
        other_mag = sum_magnitude(others)
        sector_mag = sector.magnitude()
        check_flags(sector_mag, connection_flags)
        unconnected_sector = True
        for i in PolSlot:
            if sector_mag[i.value] == 0 or other_mag[i.value] > 0 or self_connecting(sector, i, sector_mag):
                unconnected_sector = False
                break
        if unconnected_sector:
            for i in PolSlot:
                if sector_mag[i.value] > 0 and other_mag[i.value] == 0 and not self_connecting(sector, i, sector_mag):
                    builder.mag_needed[i] = [x for x in PolSlot if other_mag[x.value] > 0]
                    if name not in unconnected_builders.keys():
                        unconnected_builders[name] = builder
    ttl_mag = sum_magnitude(builder.sectors)
    for slot in PolSlot:
        for slot2 in PolSlot:
            if ttl_mag[slot.value] > 0 and ttl_mag[slot2.value] > 0 and not connection_flags[slot][slot2]:
                builder.mag_needed[slot] = [slot2]
                builder.mag_needed[slot2] = [slot]
                if name not in unconnected_builders.keys():
                    unconnected_builders[name] = builder

def self_connecting(sector, slot, magnitude):
    return sector.polarity()[slot.value] == 0 and sum(magnitude) > magnitude[slot.value]


def check_flags(sector_mag, connection_flags):
    for slot in PolSlot:
        for slot2 in PolSlot:
            if sector_mag[slot.value] > 0 and sector_mag[slot2.value] > 0:
                connection_flags[slot][slot2] = True
                if slot != slot2:
                    for check_slot in PolSlot:  # transitivity check
                        if check_slot not in [slot, slot2] and connection_flags[slot2][check_slot]:
                            connection_flags[slot][check_slot] = True
                            connection_flags[check_slot][slot] = True


def identify_simple_branching_issues(dungeon_map):
    problem_builders = {}
    for name, builder in dungeon_map.items():
        if name == 'Skull Woods 2':  # i dislike this special case todo: identify destination entrances
            builder.conn_supplied[Hook.West] += 1
            builder.conn_needed[Hook.East] -= 1
        builder.forced_loops = calc_forced_loops(builder.sectors)
        if builder.dead_ends + builder.forced_loops * 2 > builder.branches + builder.allowance:
            problem_builders[name] = builder
        for h_type in Hook:
            lack = builder.conn_balance[h_type] = builder.conn_supplied[h_type] - builder.conn_needed[h_type]
            if lack < 0:
                builder.total_conn_lack += -lack
                problem_builders[name] = builder
    return problem_builders


def calc_forced_loops(sector_list):
    forced_loops = 0
    for sector in sector_list:
        h_mag = sector.hook_magnitude()
        other_sectors = [x for x in sector_list if x != sector]
        other_mag = sum_hook_magnitude(other_sectors)
        loop_parts = 0
        for hook in Hook:
            opp = opposite_h_type(hook).value
            if h_mag[hook.value] > other_mag[opp] and loop_present(hook, opp, h_mag, other_mag):
                loop_parts += (h_mag[hook.value] - other_mag[opp]) / 2
        forced_loops += math.floor(loop_parts)
    return forced_loops


def loop_present(hook, opp, h_mag, other_mag):
    if hook == Hook.Stairs:
        return h_mag[hook.value] - other_mag[opp] >= 2
    else:
        return h_mag[opp] >= h_mag[hook.value] - other_mag[opp]


def is_satisfied(door_dict_list):
    for door_dict in door_dict_list:
        for door_list in door_dict.values():
            if len(door_list) > 0:
                return False
    return True


# todo: maybe filter by used doors too
# todo: I want the number of door that match is accessible by still
def filter_match_deps(candidate, match_deps):
    return [x for x in match_deps if x != candidate]


def sum_magnitude(sector_list):
    result = [0] * len(PolSlot)
    for sector in sector_list:
        vector = sector.magnitude()
        for i in range(len(result)):
            result[i] = result[i] + vector[i]
    return result


def sum_hook_magnitude(sector_list):
    result = [0] * len(Hook)
    for sector in sector_list:
        vector = sector.hook_magnitude()
        for i in range(len(result)):
            result[i] = result[i] + vector[i]
    return result


def sum_polarity(sector_list):
    pol = Polarity()
    for sector in sector_list:
        pol += sector.polarity()
    return pol


def assign_polarized_sectors(dungeon_map, polarized_sectors, global_pole, builder_info):
    # step 1: fix polarity connection issues
    unconnected_builders = identify_polarity_issues(dungeon_map)
    while len(unconnected_builders) > 0:
        for name, builder in unconnected_builders.items():
            candidates = find_connection_candidates(builder.mag_needed, polarized_sectors)
            valid, sector = False, None
            while not valid:
                if len(candidates) == 0:
                    raise GenerationException('Cross Dungeon Builder: Cannot find a candidate for connectedness. %s' % name)
                sector = random.choice(candidates)
                candidates.remove(sector)
                valid = global_pole.is_valid_choice(dungeon_map, builder, [sector])
            assign_sector(sector, builder, polarized_sectors, global_pole)
            builder.mag_needed = {}
        unconnected_builders = identify_polarity_issues(unconnected_builders)

    # step 2: fix dead ends
    problem_builders = identify_simple_branching_issues(dungeon_map)
    while len(problem_builders) > 0:
        for name, builder in problem_builders.items():
            candidates, charges = find_simple_branching_candidates(builder, polarized_sectors)
            best = min(charges)
            best_candidates = [x for i, x in enumerate(candidates) if charges[i] <= best]
            valid, choice = False, None
            while not valid:
                if len(best_candidates) == 0:
                    if len(candidates) == 0:
                        raise GenerationException('Cross Dungeon Builder: Simple branch problems: %s' % name)
                    best = min(charges)
                    best_candidates = [x for i, x in enumerate(candidates) if charges[i] <= best]
                choice = random.choice(best_candidates)
                best_candidates.remove(choice)
                i = candidates.index(choice)
                candidates.pop(i)
                charges.pop(i)
                valid = global_pole.is_valid_choice(dungeon_map, builder, [choice]) and valid_connected_assignment(builder, [choice])
            assign_sector(choice, builder, polarized_sectors, global_pole)
            builder.total_conn_lack = 0
            builder.conn_balance.clear()
        problem_builders = identify_simple_branching_issues(problem_builders)

    # step 3: fix neutrality issues
    polarity_step_3(dungeon_map, polarized_sectors, global_pole)

    # step 4: fix dead ends again
    neutral_choices: List[List] = neutralize_the_rest(polarized_sectors)
    problem_builders = identify_branching_issues(dungeon_map, builder_info)
    while len(problem_builders) > 0:
        for name, builder in problem_builders.items():
            candidates = find_branching_candidates(builder, neutral_choices, builder_info)
            valid, choice = False, None
            while not valid:
                if len(candidates) <= 0:
                        raise GenerationException('Cross Dungeon Builder: Complex branch problems: %s' % name)
                choice = random.choice(candidates)
                candidates.remove(choice)
                valid = global_pole.is_valid_choice(dungeon_map, builder, choice) and valid_polarized_assignment(builder, choice)
            neutral_choices.remove(choice)
            for sector in choice:
                assign_sector(sector, builder, polarized_sectors, global_pole)
            builder.unfulfilled.clear()
        problem_builders = identify_branching_issues(problem_builders, builder_info)

    # step 5: assign randomly until gone - must maintain connectedness, neutral polarity, branching, lack, etc.
    comb_w_replace = len(dungeon_map) ** len(neutral_choices)
    combinations = None
    if comb_w_replace <= 1000:
        combinations = list(itertools.product(dungeon_map.keys(), repeat=len(neutral_choices)))
        random.shuffle(combinations)
    tries = 0
    while len(polarized_sectors) > 0:
        if tries > 1000 or (combinations and tries >= len(combinations)):
            raise GenerationException('No valid assignment found. Ref: %s' % next(iter(dungeon_map.keys())))
        if combinations:
            choices = combinations[tries]
        else:
            choices = random.choices(list(dungeon_map.keys()), k=len(neutral_choices))
        chosen_sectors = defaultdict(list)
        for i, choice in enumerate(choices):
            chosen_sectors[choice].extend(neutral_choices[i])
        all_valid = True
        for name, sector_list in chosen_sectors.items():
            if not valid_assignment(dungeon_map[name], sector_list, builder_info):
                all_valid = False
                break
        if all_valid:
            for i, choice in enumerate(choices):
                builder = dungeon_map[choice]
                for sector in neutral_choices[i]:
                    assign_sector(sector, builder, polarized_sectors, global_pole)
        tries += 1


def polarity_step_3(dungeon_map, polarized_sectors, global_pole):
    # step 3a: fix odd builders
    odd_builders = [x for x in dungeon_map.values() if sum_polarity(x.sectors).charge() % 2 != 0]
    grouped_choices: List[List] = find_forced_groupings(polarized_sectors, dungeon_map)
    random.shuffle(odd_builders)
    odd_candidates = find_odd_sectors(grouped_choices)
    tries = 0
    while len(odd_builders) > 0:
        if tries > 1000:
            raise GenerationException('Unable to fix dungeon parity. Ref: %s' % next(iter(odd_builders)).name)
        best_choices = None
        best_charge = sum([x.polarity().charge() for x in dungeon_map.values()])
        samples = 0
        combos = ncr(len(odd_candidates), len(odd_builders))
        sample_target = 100 if combos > 10 else combos * 2
        while best_choices is None or samples < sample_target:
            samples += 1
            if len(odd_candidates) < len(odd_builders):
                raise GenerationException(f'Unable to fix dungeon parity - not enough candidates.'
                                          f' Ref: {next(iter(odd_builders)).name}')
            choices = random.sample(odd_candidates, k=len(odd_builders))
            valid = global_pole.is_valid_multi_choice(dungeon_map, odd_builders, choices)
            charge = calc_total_charge(dungeon_map, odd_builders, choices)
            if valid and charge < best_charge:
                best_choices = choices
                best_charge = charge
            if samples > sample_target and best_choices is None:
                best_choices = choices
                best_charge = charge
                samples = 0
        all_valid = True
        for i, candidate_list in enumerate(best_choices):
            test_set = find_forced_connections(dungeon_map, candidate_list, polarized_sectors)
            builder = odd_builders[i]
            if ensure_test_set_connectedness(test_set, builder, polarized_sectors, dungeon_map, global_pole):
                all_valid &= valid_branch_only(builder, candidate_list)
            else:
                all_valid = False
                break
            if not all_valid:
                break
        if all_valid:
            for i, candidate_list in enumerate(best_choices):
                builder = odd_builders[i]
                for sector in candidate_list:
                    assign_sector(sector, builder, polarized_sectors, global_pole)
            odd_builders = [x for x in dungeon_map.values() if sum_polarity(x.sectors).charge() % 2 != 0]
        else:
            tries += 1

    # step 3b: neutralize all builders
    parallel_full_neutralization(dungeon_map, polarized_sectors, global_pole)


def parallel_full_neutralization(dungeon_map, polarized_sectors, global_pole):
    start = time.process_time()
    builders = list(dungeon_map.values())
    finished = all([x.polarity().is_neutral() for x in builders])
    solution_list, current_depth = defaultdict(list), 1
    complete_builders = [x for x in builders if x.polarity().is_neutral()]
    avail_sectors = list(polarized_sectors)
    while not finished:
        builders_to_check = [x for x in builders if not (x.polarity()+sum_polarity(solution_list[x])).is_neutral()]
        candidates, last_depth = find_exact_neutralizing_candidates_parallel_db(builders_to_check, solution_list,
                                                                                avail_sectors, current_depth)
        increment_depth = True
        any_valid = False
        for builder, candidate_list in candidates.items():
            valid, sectors = False, None
            while not valid:
                if len(candidate_list) == 0:
                    increment_depth = False  #need to look again at current level
                    break
                sectors = random.choice(candidate_list)
                candidate_list.remove(sectors)
                proposal = solution_list.copy()
                proposal[builder] = list(proposal[builder])
                proposal[builder].extend(sectors)
                valid = global_pole.is_valid_multi_choice_2(dungeon_map, builders, proposal)
            if valid:
                any_valid = True
                solution_list[builder].extend(sectors)
                for sector in sectors:
                    avail_sectors.remove(sector)
                complete_builders.append(builder)
                for other_builder, other_cand_list in candidates.items():
                    if other_builder not in complete_builders:
                        candidates_to_remove = list()
                        for candidate in other_cand_list:
                            for sector in sectors:
                                if sector in candidate:
                                    candidates_to_remove.append(candidate)
                                    break
                        other_cand_list[:] = [x for x in other_cand_list if x not in candidates_to_remove]
            # remove sectors from other candidate lists
        if not any_valid:
            increment_depth = True
        current_depth = last_depth + 1 if increment_depth else last_depth
        finished = all([(x.polarity()+sum_polarity(solution_list[x])).is_neutral() for x in builders])
    logging.getLogger('').info(f'-Balanced solution found in {time.process_time()-start}')
    for builder, sectors in solution_list.items():
        for sector in sectors:
            assign_sector(sector, builder, polarized_sectors, global_pole)


def find_forced_connections(dungeon_map, candidate_list, polarized_sectors):
    test_set = list(candidate_list)
    other_sectors = [x for x in polarized_sectors if x not in candidate_list]
    dungeon_hooks = defaultdict(int)
    for name, builder in dungeon_map.items():
        d_mag = sum_hook_magnitude(builder.sectors)
        for val in Hook:
            dungeon_hooks[val] += d_mag[val.value]
    queue = deque(candidate_list)
    while queue:
        candidate = queue.popleft()
        c_mag = candidate.hook_magnitude()
        other_candidates = [x for x in candidate_list if x != candidate]
        for val in Hook:
            if c_mag[val.value] > 0:
                opp = opposite_h_type(val)
                o_val = opp.value
                if sum_hook_magnitude(other_candidates)[o_val] == 0 and dungeon_hooks[opp] == 0 and not valid_self(c_mag, val, opp):
                    forced_sector = []
                    for sec in other_sectors:
                        if sec.hook_magnitude()[o_val] > 0:
                            forced_sector.append(sec)
                            if len(forced_sector) > 1:
                                break
                    if len(forced_sector) == 1:
                        test_set.append(forced_sector[0])
    return test_set


def valid_self(c_mag, val, opp):
    if val == Hook.Stairs:
        return c_mag[val.value] > 2
    else:
        return c_mag[opp.value] > 0 and sum(c_mag) > 2


def ensure_test_set_connectedness(test_set, builder, polarized_sectors, dungeon_map, global_pole):
    test_copy = list(test_set)
    while not valid_connected_assignment(builder, test_copy):
        dummy_builder = DungeonBuilder("Dummy Builder for " + builder.name)
        dummy_builder.sectors = builder.sectors + test_copy
        possibles = [x for x in polarized_sectors if x not in test_copy]
        candidates = find_connected_candidates(possibles)
        valid, sector = False, None
        while not valid:
            if len(candidates) == 0:
                return False
            sector = random.choice(candidates)
            candidates.remove(sector)
            t2 = test_copy+[sector]
            valid = global_pole.is_valid_choice(dungeon_map, builder, t2) and valid_branch_only(builder, t2)
        test_copy.append(sector)
        dummy_builder.sectors = builder.sectors + test_copy
    test_set[:] = test_copy
    return True


def calc_total_charge(dungeon_map, builders, sector_lists):
    polarity_list = [x.polarity() for x in dungeon_map.values() if x not in builders]
    for i, sectors in enumerate(sector_lists):
        builder = builders[i]
        polarity = builder.polarity() + sum_polarity(sectors)
        polarity_list.append(polarity)
    return sum([x.charge() for x in polarity_list])


class GlobalPolarity:

    def __init__(self, candidate_sectors):
        self.positives = [0, 0, 0]
        self.negatives = [0, 0, 0]
        self.evens = 0
        self.odds = 0
        for sector in candidate_sectors:
            pol = sector.polarity()
            if pol.charge() % 2 == 0:
                self.evens += 1
            else:
                self.odds += 1
            for slot in PolSlot:
                if pol.vector[slot.value] < 0:
                    self.negatives[slot.value] += -pol.vector[slot.value]
                elif pol.vector[slot.value] > 0:
                    self.positives[slot.value] += pol.vector[slot.value]

    def copy(self):
        gp = GlobalPolarity([])
        gp.positives = self.positives.copy()
        gp.negatives = self.negatives.copy()
        gp.evens = self.evens
        gp.odds = self.odds
        return gp

    def is_valid(self, dungeon_map):
        polarities = [x.polarity() for x in dungeon_map.values()]
        return self._check_parity(polarities) and self._is_valid_polarities(polarities)

    def _check_parity(self, polarities):
        local_evens = 0
        local_odds = 0
        for pol in polarities:
            if pol.charge() % 2 == 0:
                local_evens += 1
            else:
                local_odds += 1
        if local_odds > self.odds:
            return False
        return True

    def _is_valid_polarities(self, polarities):
        positives = self.positives.copy()
        negatives = self.negatives.copy()
        for polarity in polarities:
            for slot in PolSlot:
                if polarity[slot.value] > 0 and slot != PolSlot.Stairs:
                    if negatives[slot.value] >= polarity[slot.value]:
                        negatives[slot.value] -= polarity[slot.value]
                    else:
                        return False
                elif polarity[slot.value] < 0 and slot != PolSlot.Stairs:
                    if positives[slot.value] >= -polarity[slot.value]:
                        positives[slot.value] += polarity[slot.value]
                    else:
                        return False
                elif slot == PolSlot.Stairs:
                    if positives[slot.value] >= polarity[slot.value]:
                        positives[slot.value] -= polarity[slot.value]
                    else:
                        return False
        return True

    def consume(self, sector):
        polarity = sector.polarity()
        if polarity.charge() % 2 == 0:
            self.evens -= 1
        else:
            self.odds -= 1
        for slot in PolSlot:
            if polarity[slot.value] > 0 and slot != PolSlot.Stairs:
                if self.positives[slot.value] >= polarity[slot.value]:
                    self.positives[slot.value] -= polarity[slot.value]
                else:
                    raise GenerationException('Invalid assignment of %s' % sector.name)
            elif polarity[slot.value] < 0 and slot != PolSlot.Stairs:
                if self.negatives[slot.value] >= -polarity[slot.value]:
                    self.negatives[slot.value] += polarity[slot.value]
                else:
                    raise GenerationException('Invalid assignment of %s' % sector.name)
            elif slot == PolSlot.Stairs:
                if self.positives[slot.value] >= polarity[slot.value]:
                    self.positives[slot.value] -= polarity[slot.value]
                else:
                    raise GenerationException('Invalid assignment of %s' % sector.name)

    def is_valid_choice(self, dungeon_map, builder, sectors):
        proposal = self.copy()
        non_neutral_polarities = [x.polarity() for x in dungeon_map.values() if not x.polarity().is_neutral() and x != builder]
        current_polarity = builder.polarity() + sum_polarity(sectors)
        non_neutral_polarities.append(current_polarity)
        for sector in sectors:
            proposal.consume(sector)
        return proposal._check_parity(non_neutral_polarities) and proposal._is_valid_polarities(non_neutral_polarities)

    def is_valid_multi_choice(self, dungeon_map, builders, sector_lists):
        proposal = self.copy()
        non_neutral_polarities = [x.polarity() for x in dungeon_map.values() if not x.polarity().is_neutral()
                                  and x not in builders]
        for i, sectors in enumerate(sector_lists):
            builder = builders[i]
            current_polarity = builder.polarity() + sum_polarity(sectors)
            non_neutral_polarities.append(current_polarity)
            for sector in sectors:
                proposal.consume(sector)
        return proposal._check_parity(non_neutral_polarities) and proposal._is_valid_polarities(non_neutral_polarities)

    def is_valid_multi_choice_2(self, dungeon_map, builders, sector_dict):
        proposal = self.copy()
        non_neutral_polarities = [x.polarity() for x in dungeon_map.values() if not x.polarity().is_neutral()
                                  and x not in builders]
        for builder, sectors in sector_dict.items():
            current_polarity = builder.polarity() + sum_polarity(sectors)
            non_neutral_polarities.append(current_polarity)
            for sector in sectors:
                proposal.consume(sector)
        return proposal._check_parity(non_neutral_polarities) and proposal._is_valid_polarities(non_neutral_polarities)

    # def check_odd_polarities(self, candidate_sectors, dungeon_map):
    #     odd_candidates = [x for x in candidate_sectors if x.polarity().charge() % 2 != 0]
    #     odd_map = {n: x for (n, x) in dungeon_map.items() if sum_polarity(x.sectors).charge() % 2 != 0}
    #     gp = GlobalPolarity(odd_candidates)
    #     return gp.is_valid(odd_map)


def find_connection_candidates(mag_needed, sector_pool):
    candidates = []
    for sector in sector_pool:
        if sector.branching_factor() < 2:
            continue
        mag = sector.magnitude()
        matches = False
        for slot, match_slot in mag_needed.items():
            if mag[slot.value] > 0:
                for i in PolSlot:
                    if i in match_slot and mag[i.value] > 0:
                        matches = True
                        break
        if matches:
            candidates.append(sector)
    return candidates


def find_simple_branching_candidates(builder, sector_pool):
    candidates = defaultdict(list)
    charges = defaultdict(list)
    outflow_needed = builder.dead_ends + builder.forced_loops * 2 > builder.branches + builder.allowance
    total_needed = builder.dead_ends + builder.forced_loops * 2 - builder.branches + builder.allowance
    original_lack = builder.total_conn_lack
    best_lack = original_lack
    for sector in sector_pool:
        if outflow_needed and sector.branching_factor() <= 2:
            continue
        calc_sector_balance(sector)
        ttl_lack = 0
        for hook in Hook:
            lack = builder.conn_balance[hook] + sector.conn_balance[hook]
            if lack < 0:
                ttl_lack += -lack
        forced_loops = calc_forced_loops(builder.sectors + [sector])
        net_outflow = builder.dead_ends + forced_loops * 2 + sector.dead_ends() - builder.branches - builder.allowance - sector.branches()
        valid_branches = net_outflow < total_needed
        if valid_branches and (ttl_lack < original_lack or original_lack >= 0):
            candidates[ttl_lack].append(sector)
            charges[ttl_lack].append((builder.polarity()+sector.polarity()).charge())
            if ttl_lack < best_lack:
                best_lack = ttl_lack
    if best_lack == original_lack and not outflow_needed:
        raise GenerationException('These candidates may not help at all')
    if len(candidates[best_lack]) <= 0:
        raise GenerationException('Nothing can fix the simple branching issue. Panic ensues.')
    return candidates[best_lack], charges[best_lack]


def calc_sector_balance(sector):  # todo: move to base class?
    if sector.conn_balance is None:
        sector.conn_balance = defaultdict(int)
        for door in sector.outstanding_doors:
            if door.blocked or door.dead or sector.branching_factor() <= 1:
                sector.conn_balance[hook_from_door(door)] -= 1
            else:
                sector.conn_balance[hanger_from_door(door)] += 1


def find_odd_sectors(grouped_candidates):
    return [x for x in grouped_candidates if sum_polarity(x).charge() % 2 != 0]


# This is related to the perfect sum problem in CS
# * Best algorithm so far - db for dynamic programming
# * Keeps track of unique deviations from neutral in the index
# * Another assumption is that solutions that take fewer sector are more ideal
# * When attempting to add depth and there are no more possibilities, this raises an Exception
# * Each depth should be checked before asking for another one
# An alterative approach would be to trim the db after deciding the candidate at the current depth will be
# part of the propsoal
def find_exact_neutralizing_candidates_parallel_db(builders, proposal, avail_sectors, current_depth):
    candidate_map = defaultdict(list)
    polarity_map = {}
    for builder in builders:
        polarity_map[builder] = builder.polarity() + sum_polarity(proposal[builder])
    finished = False
    db, index = create_db_for_depth(current_depth, avail_sectors)
    while not finished:
        depth_map = db[current_depth]
        for builder in builders:
            target = polarity_map[builder].complement()
            if target in depth_map.keys():
                finished = True
                candidate_map[builder].extend(depth_map[target].keys())
        if finished:
            for builder in list(candidate_map.keys()):
                try:
                    candidate_map[builder] = weed_candidates(builder, {0: candidate_map[builder]}, 0)
                except NeutralizingException:
                    del candidate_map[builder]
            if len(candidate_map) == 0:
                finished = False
        if not finished:
            current_depth += 1
            add_depth_to_db(db, index, current_depth, avail_sectors)
    return candidate_map, current_depth


def create_db_for_depth(depth, avail_sectors):
    db = {0: {Polarity(): {OrderedFrozenSet(): None}}}
    db_index = {Polarity()}
    for i in range(1, depth+1):
        add_depth_to_db(db, db_index, i, avail_sectors)
    return db, db_index


def add_depth_to_db(db, db_index, i, avail_sectors):
    previous = db[i-1]
    depth_map = defaultdict(dict)
    index_additions = set()
    for sector in avail_sectors:
        sector_set = {sector}
        sector_pol = sector.polarity()
        for polarity, choices in previous.items():
            combo_pol = sector_pol + polarity
            if combo_pol not in db_index:
                index_additions.add(combo_pol)
                for choice in choices:
                    if sector in choice.frozen_set:
                        continue
                    new_set = choice.new_with_element(sector_set)
                    depth_map[combo_pol][new_set] = None
    for addition in index_additions:
        if len(depth_map[addition]) > 0:
            db_index.add(addition)
        else:
            del depth_map[addition]
    if len(depth_map) == 0:
        raise NeutralizingException('There is not a solution for this particular combination. Crystal switch issue?')  # restart required
    db[i] = depth_map


class OrderedFrozenSet:

    def __init__(self):
        self.frozen_set = frozenset()
        self.order = []

    def __eq__(self, other):
        return self.frozen_set == other.frozen_set

    def __hash__(self):
        return hash(self.frozen_set)

    def __iter__(self):
        return self.order.__iter__()

    def __len__(self):
        return len(self.order)

    def new_with_element(self, elements):
        ret = OrderedFrozenSet()
        ret.frozen_set = frozenset(self.frozen_set | elements)
        ret.order = list(self.order)
        ret.order.extend(elements)
        return ret


# this could be re-worked for the more complete solution
# i'm not sure it does a whole lot now
def weed_candidates(builder, candidates, best_charge):
    official_cand = []
    while len(official_cand) == 0:
        if len(candidates.keys()) == 0:
            raise NeutralizingException('Cross Dungeon Builder: Weeded out all candidates %s' % builder.name)
        while best_charge not in candidates.keys():
            best_charge += 1
        candidate_list = candidates.pop(best_charge)
        best_lack = None
        for cand in candidate_list:
            ttl_deads = 0
            ttl_branches = 0
            for sector in cand:
                calc_sector_balance(sector)
                ttl_deads += sector.dead_ends()
                ttl_branches += sector.branches()
            ttl_lack = 0
            ttl_balance = 0
            for hook in Hook:
                bal = 0
                for sector in cand:
                    bal += sector.conn_balance[hook]
                lack = builder.conn_balance[hook] + bal
                ttl_balance += lack
                if lack < 0:
                    ttl_lack += -lack
            forced_loops = calc_forced_loops(builder.sectors + list(cand))
            if ttl_balance >= 0 and builder.dead_ends + ttl_deads + forced_loops * 2 <= builder.branches + ttl_branches + builder.allowance:
                if best_lack is None or ttl_lack < best_lack:
                    best_lack = ttl_lack
                    official_cand = [cand]
                elif ttl_lack == best_lack:
                    official_cand.append(cand)

    # choose from among those that use less
    best_len = None
    cand_len = []
    for cand in official_cand:
        size = len(cand)
        if best_len is None or size < best_len:
            best_len = size
            cand_len = [cand]
        elif size == best_len:
            cand_len.append(cand)
    return cand_len


def find_branching_candidates(builder, neutral_choices, builder_info):
    candidates = []
    for choice in neutral_choices:
        resolved, problem_list = check_for_valid_layout(builder, choice, builder_info)
        if resolved:
            candidates.append(choice)
    return candidates


def find_connected_candidates(sector_pool):
    candidates = []
    for sector in sector_pool:
        if sector.adj_outflow() >= 2:
            candidates.append(sector)
    return candidates


def neutralize_the_rest(sector_pool):
    neutral_choices = []
    main_pool = list(sector_pool)
    failed_pool = []
    r_size = 1
    while len(main_pool) > 0 or len(failed_pool) > 0:
        if len(main_pool) <= r_size:
            main_pool.extend(failed_pool)
            failed_pool.clear()
            r_size += 1
        candidate = random.choice(main_pool)
        main_pool.remove(candidate)
        if r_size > len(main_pool):
            raise GenerationException("Cross Dungeon Builder: no more neutral pairings possible")
        combinations = ncr(len(main_pool), r_size)
        itr = 0
        done = False
        while not done:
            ttl_polarity = candidate.polarity()
            choice_set = kth_combination(itr, main_pool, r_size)
            for choice in choice_set:
                ttl_polarity += choice.polarity()
            if ttl_polarity.is_neutral():
                choice_set.append(candidate)
                neutral_choices.append(choice_set)
                main_pool = [x for x in main_pool if x not in choice_set]
                failed_pool = [x for x in failed_pool if x not in choice_set]
                done = True
            else:
                itr += 1
            if itr >= combinations:
                failed_pool.append(candidate)
                done = True
    return neutral_choices


# doesn't force a grouping when all in the found_list comes from the same sector
def find_forced_groupings(sector_pool, dungeon_map):
    dungeon_hooks = {}
    for name, builder in dungeon_map.items():
        dungeon_hooks[name] = categorize_groupings(builder.sectors)
    groupings = []
    queue = deque(sector_pool)
    skips = set()
    while len(queue) > 0:
        grouping = queue.popleft()
        is_list = isinstance(grouping, List)
        if not is_list and grouping in skips:
            continue
        grouping = grouping if is_list else [grouping]
        hook_categories = categorize_groupings(grouping)
        force_found = False
        for val in Hook:
            if val in hook_categories.keys():
                required_doors, flexible_doors = hook_categories[val]
                if len(required_doors) >= 1:
                    opp = opposite_h_type(val)
                    found_list = []
                    if opp in hook_categories.keys() and len(hook_categories[opp][1]) > 0:
                        found_list.extend(hook_categories[opp][1])
                    for name, hooks in dungeon_hooks.items():
                        if opp in hooks.keys() and len(hooks[opp][1]) > 0:
                            found_list.extend(hooks[opp][1])
                    other_sectors = [x for x in sector_pool if x not in grouping]
                    other_sector_cats = categorize_groupings(other_sectors)
                    if opp in other_sector_cats.keys() and len(other_sector_cats[opp][1]) > 0:
                        found_list.extend(other_sector_cats[opp][1])
                    if len(required_doors) == len(found_list):
                        forced_sectors = []
                        for sec in other_sectors:
                            cats = categorize_groupings([sec])
                            if opp in cats.keys() and len(cats[opp][1]) > 0:
                                forced_sectors.append(sec)
                        if len(forced_sectors) > 0:
                            grouping.extend(forced_sectors)
                            skips.update(forced_sectors)
                            merge_groups = []
                            for group in groupings:
                                for sector in group:
                                    if sector in forced_sectors:
                                        merge_groups.append(group)
                            for merge in merge_groups:
                                grouping = list(set(grouping).union(set(merge)))
                                groupings.remove(merge)
                            queue.append(grouping)
                            force_found = True
                elif len(flexible_doors) == 1:
                    opp = opposite_h_type(val)
                    found_list = []
                    if opp in hook_categories.keys() and (len(hook_categories[opp][0]) > 0 or len(hook_categories[opp][1]) > 0):
                        found_list.extend(hook_categories[opp][0])
                        found_list.extend([x for x in hook_categories[opp][1] if x not in flexible_doors])
                    for name, hooks in dungeon_hooks.items():
                        if opp in hooks.keys() and (len(hooks[opp][0]) > 0 or len(hooks[opp][1]) > 0):
                            found_list.extend(hooks[opp][0])
                            found_list.extend(hooks[opp][1])
                    other_sectors = [x for x in sector_pool if x not in grouping]
                    other_sector_cats = categorize_groupings(other_sectors)
                    if opp in other_sector_cats.keys() and (len(other_sector_cats[opp][0]) > 0 or len(other_sector_cats[opp][1]) > 0):
                        found_list.extend(other_sector_cats[opp][0])
                        found_list.extend(other_sector_cats[opp][1])
                    if len(found_list) == 1:
                        forced_sectors = []
                        for sec in other_sectors:
                            cats = categorize_groupings([sec])
                            if opp in cats.keys() and (len(cats[opp][0]) > 0 or len(cats[opp][1]) > 0):
                                forced_sectors.append(sec)
                        if len(forced_sectors) > 0:
                            grouping.extend(forced_sectors)
                            skips.update(forced_sectors)
                            merge_groups = []
                            for group in groupings:
                                for sector in group:
                                    if sector in forced_sectors:
                                        merge_groups.append(group)
                            for merge in merge_groups:
                                grouping += merge
                                groupings.remove(merge)
                            queue.append(grouping)
                            force_found = True
            if force_found:
                break
        if not force_found:
            groupings.append(grouping)
    return groupings


def categorize_groupings(sectors):
    hook_categories = {}
    for sector in sectors:
        for door in sector.outstanding_doors:
            hook = hook_from_door(door)
            if hook not in hook_categories.keys():
                hook_categories[hook] = ([], [])
            if door.blocked or door.dead:
                hook_categories[hook][0].append(door)
            else:
                hook_categories[hook][1].append(door)
    return hook_categories


def valid_assignment(builder, sector_list, builder_info):
    if not valid_entrance(builder, sector_list, builder_info):
        return False
    if not valid_c_switch(builder, sector_list):
        return False
    if not valid_polarized_assignment(builder, sector_list):
        return False
    resolved, problems = check_for_valid_layout(builder, sector_list, builder_info)
    return resolved


def valid_entrance(builder, sector_list, builder_info):
    is_dead_end = False
    if len(builder.sectors) == 0:
        is_dead_end = True
    else:
        entrances, splits, c_tuple, world, player = builder_info
        if builder.name not in entrances.keys():
            name_parts = builder.name.rsplit(' ', 1)
            entrance_list = splits[name_parts[0]][name_parts[1]]
            entrances = []
            for sector in builder.sectors:
                if sector.is_entrance_sector():
                    sector.region_set()
                    entrances.append(sector)
            all_dead = True
            for sector in entrances:
                for region in entrance_list:
                    if region in sector.region_set():
                        portal = next((x for x in world.dungeon_portals[player] if x.door.entrance.parent_region.name == region), None)
                        if portal and not portal.deadEnd:
                            all_dead = False
                        break
                if not all_dead:
                    break
            is_dead_end = all_dead
    return len(sector_list) == 0 if is_dead_end else True


def valid_c_switch(builder, sector_list):
    if builder.c_switch_present:
        return True
    for sector in sector_list:
        if sector.c_switch:
            return True
    if builder.c_switch_required:
        return False
    for sector in sector_list:
        if sector.blue_barrier:
            return False
    return True


def valid_connected_assignment(builder, sector_list):
    full_list = sector_list + builder.sectors
    if len(full_list) == 1 and sum_magnitude(full_list) == [0, 0, 0]:
        return True
    for sector in full_list:
        if sector.is_entrance_sector():
            continue
        others = [x for x in full_list if x != sector]
        other_mag = sum_magnitude(others)
        sector_mag = sector.magnitude()
        hookable = False
        for i in range(len(sector_mag)):
            if sector_mag[i] > 0 and other_mag[i] > 0:
                hookable = True
        if not hookable:
            return False
    return True


def valid_branch_assignment(builder, sector_list):
    if not valid_connected_assignment(builder, sector_list):
        return False
    return valid_branch_only(builder, sector_list)


def valid_branch_only(builder, sector_list):
    forced_loops = calc_forced_loops(builder.sectors + sector_list)
    ttl_deads = 0
    ttl_branches = 0
    for s in sector_list:
        # calc_sector_balance(sector)  # do I want to check lack here? see weed_candidates
        ttl_deads += s.dead_ends()
        ttl_branches += s.branches()
    return builder.dead_ends + ttl_deads + forced_loops * 2 <= builder.branches + ttl_branches + builder.allowance


def valid_polarized_assignment(builder, sector_list):
    if not valid_branch_assignment(builder, sector_list):
        return False
    return (sum_polarity(sector_list) + sum_polarity(builder.sectors)).is_neutral()


def assign_the_rest(dungeon_map, neutral_sectors, global_pole, builder_info):
    comb_w_replace = len(dungeon_map) ** len(neutral_sectors)
    combinations = None
    if comb_w_replace <= 1000:
        combinations = list(itertools.product(dungeon_map.keys(), repeat=len(neutral_sectors)))
        random.shuffle(combinations)
    tries = 0
    while len(neutral_sectors) > 0:
        if tries > 1000 or (combinations and tries >= len(combinations)):
            raise GenerationException('No valid assignment found for "neutral" sectors. Ref: %s' % next(iter(dungeon_map.keys())))
        # sector_list = list(neutral_sectors)
        if combinations:
            choices = combinations[tries]
        else:
            choices = random.choices(list(dungeon_map.keys()), k=len(neutral_sectors))
        neutral_sector_list = list(neutral_sectors)
        chosen_sectors = defaultdict(list)
        for i, choice in enumerate(choices):
            chosen_sectors[choice].append(neutral_sector_list[i])
        all_valid = True
        for name, sector_list in chosen_sectors.items():
            if not valid_assignment(dungeon_map[name], sector_list, builder_info):
                all_valid = False
                break
        if all_valid:
            for name, sector_list in chosen_sectors.items():
                builder = dungeon_map[name]
                for sector in sector_list:
                    assign_sector(sector, builder, neutral_sectors, global_pole)
        tries += 1


def split_dungeon_builder(builder, split_list, builder_info):
    if builder.split_dungeon_map and len(builder.exception_list) == 0:
        for name, proposal in builder.valid_proposal.items():
            builder.split_dungeon_map[name].valid_proposal = proposal
        return builder.split_dungeon_map  # we made this earlier in gen, just use it

    attempts, comb_w_replace, merge_attempt, merge_limit = 0, None, 0, len(split_list) - 1
    while attempts < 5:  # does not solve coin flips 3% of the time
        try:
            candidate_sectors = dict.fromkeys(builder.sectors)
            global_pole = GlobalPolarity(candidate_sectors)

            dungeon_map, sub_builder, merge_keys = {}, None, []
            if merge_attempt > 0:
                candidates = []
                for name, split_entrances in split_list.items():
                    if len(split_entrances) > 1:
                        candidates.append(name)
                        continue
                    elif len(split_entrances) <= 0:
                        continue
                    ents, splits, c_tuple, world, player = builder_info
                    r_name = split_entrances[0]
                    p = next((x for x in world.dungeon_portals[player] if x.door.entrance.parent_region.name == r_name), None)
                    if p and not p.deadEnd:
                        candidates.append(name)
                merge_keys = random.sample(candidates, merge_attempt+1) if len(candidates) >= merge_attempt+1 else []
            for name, split_entrances in split_list.items():
                key = builder.name + ' ' + name
                if merge_keys and name in merge_keys:
                    other_keys = [builder.name + ' ' + x for x in merge_keys if x != name]
                    other_key = next((x for x in other_keys if x in dungeon_map), None)
                    if other_key:
                        key = other_key
                        sub_builder = dungeon_map[other_key]
                        sub_builder.all_entrances.extend(split_entrances)
                if key not in dungeon_map:
                    dungeon_map[key] = sub_builder = DungeonBuilder(key)
                    sub_builder.split_flag = True
                    sub_builder.all_entrances = list(split_entrances)
                for r_name in split_entrances:
                    assign_sector(find_sector(r_name, candidate_sectors), sub_builder, candidate_sectors, global_pole)
            comb_w_replace = len(dungeon_map) ** len(candidate_sectors)
            return balance_split(candidate_sectors, dungeon_map, global_pole, builder_info)
        except (GenerationException, NeutralizingException):
            if comb_w_replace and comb_w_replace <= 10000:
                attempts += 5  # all the combinations were tried already, no use repeating
            else:
                attempts += 1
        if attempts >= 5 and merge_attempt < merge_limit:
            merge_attempt, attempts = merge_attempt + 1, 0

    raise GenerationException('Unable to resolve in 5 attempts')


def balance_split(candidate_sectors, dungeon_map, global_pole, builder_info):
    dungeon_entrances, split_dungeon_entrances, connections_tuple, world, player = builder_info
    for name, builder in dungeon_map.items():
        calc_allowance_and_dead_ends(builder, connections_tuple, world, player)
    comb_w_replace = len(dungeon_map) ** len(candidate_sectors)
    if comb_w_replace <= 10000:
        combinations = list(itertools.product(dungeon_map.keys(), repeat=len(candidate_sectors)))
        random.shuffle(combinations)
        tries = 0
        while tries < len(combinations):
            choices = combinations[tries]
            main_sector_list = list(candidate_sectors)
            chosen_sectors = defaultdict(list)
            for i, choice in enumerate(choices):
                chosen_sectors[choice].append(main_sector_list[i])
            all_valid = True
            for name, builder in dungeon_map.items():
                if not valid_assignment(builder, chosen_sectors[name], builder_info):
                    all_valid = False
                    break
            if all_valid:
                for name, sector_list in chosen_sectors.items():
                    builder = dungeon_map[name]
                    for sector in sector_list:
                        assign_sector(sector, builder, candidate_sectors, global_pole)
                return dungeon_map
            tries += 1
        raise GenerationException('Split Dungeon Builder: Impossible dungeon. Ref %s' % next(iter(dungeon_map.keys())))

    # categorize sectors
    check_for_forced_dead_ends(dungeon_map, candidate_sectors, global_pole)
    check_for_forced_assignments(dungeon_map, candidate_sectors, global_pole)
    check_for_forced_crystal(dungeon_map, candidate_sectors, global_pole)
    crystal_switches, crystal_barriers, neutral_sectors, polarized_sectors = categorize_sectors(candidate_sectors)
    leftover = assign_crystal_switch_sectors(dungeon_map, crystal_switches, crystal_barriers,
                                             global_pole, len(crystal_barriers) > 0)
    ensure_crystal_switches_reachable(dungeon_map, leftover, polarized_sectors, crystal_barriers, global_pole)
    for sector in leftover:
        if sector.polarity().is_neutral():
            neutral_sectors[sector] = None
        else:
            polarized_sectors[sector] = None
    # blue barriers
    assign_crystal_barrier_sectors(dungeon_map, crystal_barriers, global_pole)
    # polarity:
    assign_polarized_sectors(dungeon_map, polarized_sectors, global_pole, builder_info)
    # the rest
    assign_the_rest(dungeon_map, neutral_sectors, global_pole, builder_info)
    return dungeon_map


def check_for_forced_dead_ends(dungeon_map, candidate_sectors, global_pole):
    dead_end_sectors = [x for x in candidate_sectors if x.branching_factor() <= 1]
    other_sectors = [x for x in candidate_sectors if x not in dead_end_sectors]
    for name, builder in dungeon_map.items():
        other_sectors += builder.sectors
    other_magnitude = sum_hook_magnitude(other_sectors)
    dead_cnt = [0] * len(Hook)
    for sector in dead_end_sectors:
        hook_mag = sector.hook_magnitude()
        for hook in Hook:
            if hook_mag[hook.value] != 0:
                dead_cnt[hook.value] += 1
    for hook in Hook:
        opp = opposite_h_type(hook).value
        if dead_cnt[hook.value] > other_magnitude[opp]:
            raise GenerationException('Impossible to satisfy all these dead ends')
        elif dead_cnt[hook.value] == other_magnitude[opp]:
            candidates = [x for x in dead_end_sectors if x.hook_magnitude()[hook.value] > 0]
            for sector in other_sectors:
                if sector.hook_magnitude()[opp] > 0 and sector.is_entrance_sector() and sector.branching_factor() == 2:
                    builder = None
                    for b in dungeon_map.values():
                        if sector in b.sectors:
                            builder = b
                            break
                    valid, candidate_sector = False, None
                    while not valid:
                        if len(candidates) == 0:
                            raise GenerationException('Split Dungeon Builder: Bad dead end %s' % builder.name)
                        candidate_sector = random.choice(candidates)
                        candidates.remove(candidate_sector)
                        valid = global_pole.is_valid_choice(dungeon_map, builder, [candidate_sector]) and check_crystal(candidate_sector, sector)
                    assign_sector(candidate_sector, builder, candidate_sectors, global_pole)
                    builder.c_locked = True


def check_crystal(dead_end, entrance):
    if dead_end.blue_barrier and not entrance.c_switch and not dead_end.c_switch:
        return False
    if entrance.blue_barrier and not entrance.c_switch and not dead_end.c_switch:
        return False
    return True


def check_for_forced_assignments(dungeon_map, candidate_sectors, global_pole):
    done = False
    while not done:
        done = True
        magnitude = sum_hook_magnitude(candidate_sectors)
        dungeon_hooks = {}
        for name, builder in dungeon_map.items():
            dungeon_hooks[name] = sum_hook_magnitude(builder.sectors)
        for val in Hook:
            if magnitude[val.value] == 1:
                forced_sector = None
                for sec in candidate_sectors:
                    if sec.hook_magnitude()[val.value] > 0:
                        forced_sector = sec
                        break
                opp = opposite_h_type(val).value
                other_sectors = [x for x in candidate_sectors if x != forced_sector]
                if sum_hook_magnitude(other_sectors)[opp] == 0:
                    found_hooks = []
                    for name, hooks in dungeon_hooks.items():
                        if hooks[opp] > 0 and not dungeon_map[name].c_locked:
                            found_hooks.append(name)
                    if len(found_hooks) == 1:
                        done = False
                        assign_sector(forced_sector, dungeon_map[found_hooks[0]], candidate_sectors, global_pole)


def check_for_forced_crystal(dungeon_map, candidate_sectors, global_pole):
    for name, builder in dungeon_map.items():
        if check_for_forced_crystal_single(builder, candidate_sectors):
            builder.c_switch_required = True


def check_for_forced_crystal_single(builder, candidate_sectors):
    builder_doors = defaultdict(dict)
    for sector in builder.sectors:
        for door in sector.outstanding_doors:
            builder_doors[hook_from_door(door)][door] = sector
    if len(builder_doors) == 0:
        return False
    candidate_doors = defaultdict(dict)
    for sector in candidate_sectors:
        for door in sector.outstanding_doors:
            candidate_doors[hook_from_door(door)][door] = sector
    for hook in builder_doors.keys():
        for door in builder_doors[hook].keys():
            opp = opposite_h_type(hook)
            if opp in builder_doors.keys():
                for d, sector in builder_doors[opp].items():
                    if d != door and (not sector.blue_barrier or sector.c_switch):
                        return False
                for d, sector in candidate_doors[opp].items():
                    if not sector.blue_barrier or sector.c_switch:
                        return False
    return True


def categorize_sectors(candidate_sectors):
    crystal_switches = {}
    crystal_barriers = {}
    polarized_sectors = {}
    neutral_sectors = {}
    for sector in candidate_sectors:
        if sector.c_switch:
            crystal_switches[sector] = None
        elif sector.blue_barrier:
            crystal_barriers[sector] = None
        elif sector.polarity().is_neutral():
            neutral_sectors[sector] = None
        else:
            polarized_sectors[sector] = None
    return crystal_switches, crystal_barriers, neutral_sectors, polarized_sectors


class NeutralizingException(Exception):
    pass


class GenerationException(Exception):
    pass


class DoorEquation:

    def __init__(self, door):
        self.door = door
        self.cost = None, None
        self.benefit = defaultdict(list)
        self.required = False
        self.access_id = None
        self.c_switch = False
        self.crystal_blocked = {}
        self.entrance_flag = False

    def copy(self):
        eq = DoorEquation(self.door)
        eq.cost = self.cost
        for key, doors in self.benefit.items():
            eq.benefit[key] = doors.copy()
        eq.required = self.required
        eq.c_switch = self.c_switch
        eq.crystal_blocked = self.crystal_blocked.copy()
        return eq

    def total_cost(self):
        return 0 if self.cost[0] is None else 1

    def gross(self, current_access):
        key, cost_door = self.cost
        if key is None:
            # todo: could just be Orange as well (multiple entrance case)
            crystal_access = current_access.access_door[None]
        else:
            crystal_access = None
            for match_door, crystal in current_access.outstanding_doors.items():
                if hook_from_door(match_door) == key:
                    if crystal_access is None or current_access._better_crystal(crystal_access, crystal):
                        crystal_access = crystal
        ttl = 0
        for key, door_list in self.benefit.items():
            for door in door_list:
                if door in current_access.outstanding_doors.keys() or door in current_access.proposed_connections.keys():
                    continue
                if door in self.crystal_blocked.keys() and not self.c_switch:
                    if crystal_access == CrystalBarrier.Either or crystal_access == self.crystal_blocked[door]:
                        ttl += 1
                else:
                    ttl += 1
        return ttl

    def profit(self, current_access):
        return self.gross(current_access) - self.total_cost()

    def neutral(self):
        key, door = self.cost
        if key is not None and len(self.benefit[key]) <= 0:
            return False
        return True

    def neutral_profit(self):
        key, door = self.cost
        if key is not None:
            if len(self.benefit[key]) < 1:
                return False
            if len(self.benefit[key]) > 1:
                return True
            return False
        else:
            return True

    def can_cover_cost(self, current_access):
        key, door = self.cost
        if key is not None and current_access[key] < 1:
            return False
        return True


class DungeonAccess:

    def __init__(self):
        self.access = defaultdict(int)
        self.door_access = {}  # door -> crystal
        self.door_sector_map = {}  # door -> original sector
        self.outstanding_doors = {}
        self.blocked_doors = {}
        self.door_access[None] = CrystalBarrier.Orange
        self.proposed_connections = {}
        self.reached_doors = set()

    def can_cover_equation(self, equation):
        key, door = equation.cost
        if key is None:
            return True
        return self.access[key] >= 1

    def can_pay(self, key):
        if key is None:
            return True
        return self.access[key] >= 1

    def adjust_for_equation(self, equation, sector):
        if equation.cost[0] is None:
            original_crystal = self.door_access[None]
            for key, door_list in equation.benefit.items():
                self.access[key] += len(door_list)
                for door in door_list:
                    # I can't think of an entrance sector that forces blue
                    crystal_state = CrystalBarrier.Either if equation.c_switch else original_crystal
                    if crystal_state == CrystalBarrier.Either:
                        self.door_access[None] = CrystalBarrier.Either
                    self.door_access[door] = crystal_state
                    self.door_sector_map[door] = sector
                    self.outstanding_doors[door] = crystal_state
                    self.reached_doors.add(door)
        else:
            key, door = equation.cost
            self.access[key] -= 1
            # find the a matching connection
            best_door, best_crystal = None, None
            for match_door, crystal in self.outstanding_doors.items():
                if hook_from_door(match_door) == key:
                    if best_door is None or self._better_crystal(best_crystal, crystal):
                        best_door = match_door
                        best_crystal = crystal
            if best_door is None:
                raise Exception('Something went terribly wrong I think')
                # for match_door, crystal in self.blocked_doors.items():
                #     if hook_from_door(match_door) == key:
                #         if best_door is None or self._better_crystal(best_crystal, crystal):
                #             best_door = match_door
                #             best_crystal = crystal
            self.door_sector_map[door] = sector
            self.door_access[door] = best_crystal
            self.reached_doors.add(door)
            self.proposed_connections[door] = best_door
            self.proposed_connections[best_door] = door
            if best_door in self.outstanding_doors.keys():
                del self.outstanding_doors[best_door]
            elif best_door in self.blocked_doors.keys():
                del self.blocked_doors[best_door]
                self.reached_doors.add(best_door)

            # todo: backpropagate crystal access
            if equation.c_switch or best_crystal == CrystalBarrier.Either:
                # if not equation.door.blocked:
                self.door_access[door] = CrystalBarrier.Either
                self.door_access[best_door] = CrystalBarrier.Either
                queue = deque([best_door, door])
                visited = set()
                while len(queue) > 0:
                    next_door = queue.popleft()
                    visited.add(next_door)
                    curr_sector = self.door_sector_map[next_door]
                    next_eq = None
                    for eq in curr_sector.equations:
                        if eq.door == next_door:
                            next_eq = eq
                            break
                    if next_eq.entrance_flag:
                        crystal_state = self.door_access[next_door]
                        self.door_access[None] = crystal_state
                        for eq in curr_sector.equations:
                            cand_door = eq.door
                            crystal_state = self.door_access[None]
                            if cand_door in next_eq.crystal_blocked.keys():
                                crystal_state = next_eq.crystal_blocked[cand_door]
                            if cand_door not in visited:
                                self.door_access[cand_door] = crystal_state
                                if not cand_door.blocked:
                                    if cand_door in self.outstanding_doors.keys():
                                        self.outstanding_doors[cand_door] = crystal_state
                                    if cand_door in self.proposed_connections.keys():
                                        partner_door = self.proposed_connections[cand_door]
                                        self.door_access[partner_door] = crystal_state
                                        if partner_door in self.outstanding_doors.keys():
                                            self.outstanding_doors[partner_door] = crystal_state
                                        if partner_door not in visited:
                                            queue.append(partner_door)
                    else:
                        for key, door_list in next_eq.benefit.items():
                            for cand_door in door_list:
                                crystal_state = self.door_access[next_door]
                                if cand_door in next_eq.crystal_blocked.keys():
                                    crystal_state = next_eq.crystal_blocked[cand_door]
                                if cand_door in self.blocked_doors.keys():
                                    needed_crystal = self.blocked_doors[cand_door]
                                    if meets_crystal_requirment(crystal_state, needed_crystal):
                                        del self.blocked_doors[cand_door]
                                        if cand_door != door:
                                            self.access[key] += 1
                                            self.outstanding_doors[cand_door] = crystal_state
                                            self.door_access[cand_door] = crystal_state
                                            self.reached_doors.add(cand_door)
                                if cand_door not in visited:
                                    self.door_access[cand_door] = crystal_state
                                    if not cand_door.blocked:
                                        if cand_door in self.outstanding_doors.keys():
                                            self.outstanding_doors[cand_door] = crystal_state
                                        if cand_door in self.proposed_connections.keys():
                                            partner_door = self.proposed_connections[cand_door]
                                            self.door_access[partner_door] = crystal_state
                                            if partner_door in self.outstanding_doors.keys():
                                                self.outstanding_doors[partner_door] = crystal_state
                                            queue.append(cand_door)
                                            queue.append(partner_door)

            for key, door_list in equation.benefit.items():
                for door in door_list:
                    crystal_access = self.door_access[best_door]
                    can_access = True
                    if door in equation.crystal_blocked.keys():
                        if crystal_access == CrystalBarrier.Either or crystal_access == equation.crystal_blocked[door]:
                            crystal_access = equation.crystal_blocked[door]
                        else:
                            self.blocked_doors[door] = equation.crystal_blocked[door]
                            can_access = False
                    self.door_sector_map[door] = sector
                    if can_access and door not in self.reached_doors:
                        self.access[key] += 1
                        self.door_access[door] = crystal_access
                        self.outstanding_doors[door] = crystal_access
                        self.reached_doors.add(door)

    def _better_crystal(self, current_champ, contender):
        if current_champ == CrystalBarrier.Either:
            return False
        elif contender == CrystalBarrier.Either:
            return True
        elif current_champ == CrystalBarrier.Blue:
            return False
        elif contender == CrystalBarrier.Blue:
            return True
        else:
            return False


def identify_branching_issues(dungeon_map, builder_info):
    unconnected_builders = {}
    for name, builder in dungeon_map.items():
        resolved, unreached_doors = check_for_valid_layout(builder, [], builder_info)
        if not resolved:
            unconnected_builders[name] = builder
            for hook, door_list in unreached_doors.items():
                builder.unfulfilled[hook] += len(door_list)
    return unconnected_builders


def check_for_valid_layout(builder, sector_list, builder_info):
    dungeon_entrances, split_dungeon_entrances, c_tuple, world, player = builder_info
    if builder.name in split_dungeon_entrances.keys():
        try:
            temp_builder = DungeonBuilder(builder.name)
            for s in sector_list + builder.sectors:
                assign_sector_helper(s, temp_builder)
            split_list = split_dungeon_entrances[builder.name]
            builder.split_dungeon_map = split_dungeon_builder(temp_builder, split_list, builder_info)
            builder.valid_proposal = {}
            possible_regions = set()
            for portal in world.dungeon_portals[player]:
                if not portal.destination and portal.name in dungeon_portals[builder.name]:
                    possible_regions.add(portal.door.entrance.parent_region.name)
            if builder.name in dungeon_drops.keys():
                possible_regions.update(dungeon_drops[builder.name])
            for name, split_build in builder.split_dungeon_map.items():
                name_bits = name.split(" ")
                orig_name = " ".join(name_bits[:-1])
                entrance_regions = split_dungeon_entrances[orig_name][name_bits[-1]]
                # todo: this is hardcoded information for random entrances
                for sector in split_build.sectors:
                    match_set = set(sector.region_set()).intersection(possible_regions)
                    if len(match_set) > 0:
                        for r_name in match_set:
                            if r_name not in entrance_regions:
                                entrance_regions.append(r_name)
                # entrance_regions = [x for x in entrance_regions if x not in split_check_entrance_invalid]
                proposal = generate_dungeon_find_proposal(split_build, entrance_regions, True, world, player)
                # record split proposals
                builder.valid_proposal[name] = proposal
            builder.exception_list = list(sector_list)
            return True, {}
        except (GenerationException, NeutralizingException):
            builder.split_dungeon_map = None
            builder.valid_proposal = None
        unreached_doors = resolve_equations(builder, sector_list)
        return False, unreached_doors
    else:
        unreached_doors = resolve_equations(builder, sector_list)
        return len(unreached_doors) == 0, unreached_doors


def resolve_equations(builder, sector_list):
    unreached_doors = defaultdict(list)
    equations = {x: y for x, y in copy_door_equations(builder, sector_list).items() if len(y) > 0}
    current_access = {}
    sector_split = {}  # those sectors that belong to a certain sector
    if builder.name in split_region_starts.keys():
        for name, region_list in split_region_starts[builder.name].items():
            current_access[name] = DungeonAccess()
            for r_name in region_list:
                sector = find_sector(r_name, builder.sectors)
                sector_split[sector] = name
    else:
        current_access[builder.name] = DungeonAccess()

    # resolve all that provide more access
    free_sector, eq_list, free_eq = find_free_equation(equations)
    while free_eq is not None:
        if free_sector in sector_split.keys():
            access_id = sector_split[free_sector]
            access = current_access[access_id]
        else:
            access_id = next(iter(current_access.keys()))
            access = current_access[access_id]
        resolve_equation(free_eq, eq_list, free_sector, access_id, access, equations)
        free_sector, eq_list, free_eq = find_free_equation(equations)
    while len(equations) > 0:
        valid_access = next_access(current_access)
        eq, eq_list, sector, access, access_id = None, None, None, None, None
        if len(valid_access) == 1:
            access_id, access = valid_access[0]
            eq, eq_list, sector = find_priority_equation(equations, access_id, access)
        elif len(valid_access) > 1:
            access_id, access = valid_access[0]
            eq, eq_list, sector = find_greedy_equation(equations, access_id, access, sector_split)
        if eq:
            resolve_equation(eq, eq_list, sector, access_id, access, equations)
        else:
            for sector, eq_list in equations.items():
                for eq in eq_list:
                    unreached_doors[hook_from_door(eq.door)].append(eq.door)
            return unreached_doors
    valid_access = next_access(current_access)
    for access_id, dungeon_access in valid_access:
        access = dungeon_access.access
        access[Hook.Stairs] = access[Hook.Stairs] % 2
        ns_leftover = min(access[Hook.North], access[Hook.South])
        access[Hook.North] -= ns_leftover
        access[Hook.South] -= ns_leftover
        ew_leftover = min(access[Hook.West], access[Hook.East])
        access[Hook.East] -= ew_leftover
        access[Hook.West] -= ew_leftover
        if sum(access.values()) > 0:
            for hook, num in access.items():
                for i in range(num):
                    unreached_doors[hook].append('placeholder')
    return unreached_doors


def next_access(current_access):
    valid_ones = [(x, y) for x, y in current_access.items() if sum(y.access.values()) > 0]
    valid_ones.sort(key=lambda x: sum(x[1].access.values()))
    return valid_ones


# an equations with no change to access (check)
# the highest benefit equations, that can be paid for (check)
# 0-benefit required transforms
# 0-benefit transforms (how to pick between these?)
# negative benefit transforms (dead end)
def find_priority_equation(equations, access_id, current_access):
    flex = calc_flex(equations, current_access)
    required = calc_required(equations, current_access)
    wanted_candidates = []
    best_profit = None
    all_candidates = []
    local_profit_map = {}

    for sector, eq_list in equations.items():
        eq_list.sort(key=lambda eq: eq.profit(current_access), reverse=True)
        best_local_profit = None
        for eq in eq_list:
            profit = eq.profit(current_access)
            if current_access.can_cover_equation(eq) and (eq.access_id is None or eq.access_id == access_id):
                # if eq.neutral_profit() or eq.neutral():
                #     return eq, eq_list, sector  # don't need to compare - just use it now
                if best_local_profit is None or profit > best_local_profit:
                    best_local_profit = profit
                all_candidates.append((eq, eq_list, sector))
            elif (best_profit is None or profit >= best_profit) and profit > 0:
                if best_profit is None or profit > best_profit:
                    wanted_candidates = [eq]
                    best_profit = profit
                else:
                    wanted_candidates.append(eq)
        local_profit_map[sector] = best_local_profit
    filtered_candidates = filter_requirements(all_candidates, equations, required, current_access)
    filtered_candidates = [x for x in filtered_candidates if x[0].gross(current_access) > 0]
    if len(filtered_candidates) == 0:
        filtered_candidates = all_candidates  # probably bad things
    if len(filtered_candidates) == 0:
            return None, None, None  # can't pay for anything
    if len(filtered_candidates) == 1:
        return filtered_candidates[0]

    neutral_candidates = [x for x in filtered_candidates if (x[0].neutral_profit() or x[0].neutral()) and x[0].profit(current_access) == local_profit_map[x[2]]]
    if len(neutral_candidates) == 0:
        neutral_candidates = filtered_candidates
    if len(neutral_candidates) == 1:
        return neutral_candidates[0]

    filtered_candidates = filter_requirements(neutral_candidates, equations, required, current_access)
    if len(filtered_candidates) == 0:
        filtered_candidates = neutral_candidates
    if len(filtered_candidates) == 1:
        return filtered_candidates[0]

    triplet_candidates = []
    best_profit = None
    for eq, eq_list, sector in filtered_candidates:
        profit = eq.profit(current_access)
        if best_profit is None or profit >= best_profit:
            if best_profit is None or profit > best_profit:
                triplet_candidates = [(eq, eq_list, sector)]
                best_profit = profit
            else:
                triplet_candidates.append((eq, eq_list, sector))

    filtered_candidates = filter_requirements(triplet_candidates, equations, required, current_access)
    if len(filtered_candidates) == 0:
        filtered_candidates = triplet_candidates
    if len(filtered_candidates) == 1:
        return filtered_candidates[0]

    required_candidates = [x for x in filtered_candidates if x[0].required]
    if len(required_candidates) == 0:
        required_candidates = filtered_candidates
    if len(required_candidates) == 1:
        return required_candidates[0]

    c_switch_candidates = [x for x in required_candidates if x[0].c_switch]
    if len(c_switch_candidates) == 0:
        c_switch_candidates = required_candidates
    if len(c_switch_candidates) == 1:
        return c_switch_candidates[0]

    loop_candidates = find_enabling_switch_connections(current_access)
    if len(loop_candidates) >= 1:
        return loop_candidates[0]  # just pick one

    flexible_candidates = [x for x in c_switch_candidates if x[0].can_cover_cost(flex)]
    if len(flexible_candidates) == 0:
        flexible_candidates = c_switch_candidates
    if len(flexible_candidates) == 1:
        return flexible_candidates[0]

    good_local_candidates = [x for x in flexible_candidates if local_profit_map[x[2]] == x[0].profit(current_access)]
    if len(good_local_candidates) == 0:
        good_local_candidates = flexible_candidates
    if len(good_local_candidates) == 1:
        return good_local_candidates[0]

    leads_to_profit = [x for x in good_local_candidates if can_enable_wanted(x[0], wanted_candidates)]
    if len(leads_to_profit) == 0:
        leads_to_profit = good_local_candidates
    if len(leads_to_profit) == 1:
        return leads_to_profit[0]

    cost_point = {x[0]: find_cost_point(x, current_access) for x in leads_to_profit}
    best_point = max(cost_point.values())
    cost_point_candidates = [x for x in leads_to_profit if cost_point[x[0]] == best_point]
    if len(cost_point_candidates) == 0:
        cost_point_candidates = leads_to_profit
    return cost_point_candidates[0]  # just pick one I guess


def find_enabling_switch_connections(current_access):
    triad_list = []
    # probably should check for loop/branches in builder at some stage
    # - but this could indicate that a loop or branch is necessary
    for cand_door, crystal in current_access.outstanding_doors.items():
        for blocked_door, req_crystal in current_access.blocked_doors.items():
            if hook_from_door(cand_door) == hanger_from_door(blocked_door):
                if crystal == CrystalBarrier.Either or crystal == req_crystal:
                    sector, equation = current_access.door_sector_map[blocked_door], None
                    for eq in sector.equations:
                        if eq.door == blocked_door:
                            equation = eq.copy()
                            break
                    if equation:
                        triad_list.append((equation, [equation], sector))
    return triad_list


def find_cost_point(eq_triplet, access):
    cost_point = 0
    key, cost_door = eq_triplet[0].cost
    if cost_door is not None:
        cost_point += access.access[key] - 1
    return cost_point


def find_greedy_equation(equations, access_id, current_access, sector_split):
    all_candidates = []
    for sector, eq_list in equations.items():
        if sector not in sector_split.keys() or sector_split[sector] == access_id:
            eq_list.sort(key=lambda eq: eq.profit(current_access), reverse=True)
            for eq in eq_list:
                if current_access.can_cover_equation(eq) and (eq.access_id is None or eq.access_id == access_id):
                    all_candidates.append((eq, eq_list, sector))
    if len(all_candidates) == 0:
        return None, None, None  # can't pay for anything
    if len(all_candidates) == 1:
        return all_candidates[0]
    filtered_candidates = [x for x in all_candidates if x[0].profit(current_access) + 2 >= len(x[2].outstanding_doors)]
    if len(filtered_candidates) == 0:
        filtered_candidates = all_candidates  # terrible! ugly dead ends
    if len(filtered_candidates) == 1:
        return filtered_candidates[0]

    triplet_candidates = []
    worst_profit = None
    for eq, eq_list, sector in filtered_candidates:
        profit = eq.profit(current_access)
        if worst_profit is None or profit <= worst_profit:
            if worst_profit is None or profit < worst_profit:
                triplet_candidates = [(eq, eq_list, sector)]
                worst_profit = profit
            else:
                triplet_candidates.append((eq, eq_list, sector))
    if len(triplet_candidates) == 0:
        triplet_candidates = filtered_candidates  # probably bad things
    return triplet_candidates[0]  # just pick one?


def calc_required(equations, current_access):
    ttl = sum(current_access.access.values())
    local_profit_map = {}
    for sector, eq_list in equations.items():
        best_local_profit = None
        for eq in eq_list:
            profit = eq.profit(current_access)
            if best_local_profit is None or profit > best_local_profit:
                best_local_profit = profit
        local_profit_map[sector] = best_local_profit
        ttl += best_local_profit
    if ttl == 0:
        new_lists = {}
        for sector, eq_list in equations.items():
            if len(eq_list) > 1:
                rem_list = []
                for eq in eq_list:
                    if eq.profit(current_access) < local_profit_map[sector]:
                        rem_list.append(eq)
                if len(rem_list) > 0:
                    new_lists[sector] = [x for x in eq_list if x not in rem_list]
        for sector, eq_list in new_lists.items():
            if len(eq_list) <= 1:
                for eq in eq_list:
                    eq.required = True
            equations[sector] = eq_list
    required_costs = defaultdict(int)
    required_benefits = defaultdict(int)
    for sector, eq_list in equations.items():
        for eq in eq_list:
            if eq.required:
                key, door = eq.cost
                required_costs[key] += 1
                for key, door_list in eq.benefit.items():
                    required_benefits[key] += len(door_list)
    return required_costs, required_benefits


def calc_flex(equations, current_access):
    flex_spending = defaultdict(int)
    required_costs = defaultdict(int)
    for sector, eq_list in equations.items():
        for eq in eq_list:
            if eq.required:
                key, door = eq.cost
                required_costs[key] += 1
    for key in Hook:
        flex_spending[key] = max(0, current_access.access[key]-required_costs[key])
    return flex_spending


def filter_requirements(triplet_candidates, equations, required, current_access):
    r_costs, r_exits = required
    valid_candidates = []
    for cand, cand_list, cand_sector in triplet_candidates:
        valid = True
        if not cand.required and not cand.c_switch:
            potential_benefit = defaultdict(int)
            benefit_counted = set()
            potential_costs = defaultdict(int)
            for h_type, benefit in current_access.access.items():
                cur_cost = 1 if cand.cost[0] is not None else 0
                if benefit - cur_cost > 0:
                    potential_benefit[h_type] += benefit - cur_cost
            for h_type, benefit_list in cand.benefit.items():
                potential_benefit[h_type] += len(benefit_list)
            for sector, eq_list in equations.items():
                if sector == cand_sector:
                    affected_doors = [d for x in cand.benefit.values() for d in x] + [cand.cost[1]]
                    adj_list = [x for x in eq_list if x.door not in affected_doors]
                else:
                    adj_list = eq_list
                for eq in adj_list:
                    for h_type, benefit_list in eq.benefit.items():
                        total_benefit = set(benefit_list) - benefit_counted
                        potential_benefit[h_type] += len(total_benefit)
                        benefit_counted.update(benefit_list)
                    h_type, cost_door = eq.cost
                    potential_costs[h_type] += 1
            for h_type, requirement in r_costs.items():
                if requirement > 0 and potential_benefit[h_type] < requirement:
                    valid = False
                    break
            if valid:
                for h_type, requirement in r_exits.items():
                    if requirement > 0 and potential_costs[h_type] < requirement:
                        valid = False
                        break
        if valid:
            valid_candidates.append((cand, cand_list, cand_sector))
    return valid_candidates


def can_enable_wanted(test_eq, wanted_candidates):
    for wanted in wanted_candidates:
        covered = True
        key, cost_door = wanted.cost
        if len(test_eq.benefit[key]) < 1:
            covered = False
        if covered:
            return True
    return False


def resolve_equation(equation, eq_list, sector, access_id, current_access, equations):
    if not current_access.can_pay(equation.cost[0]):
        raise GenerationException('Cannot pay for this connection')
    current_access.adjust_for_equation(equation, sector)
    eq_list.remove(equation)
    reached_doors = set(current_access.reached_doors)
    reached_doors.update(current_access.blocked_doors.keys())
    for r_eq in list(eq_list):
        all_benefits_met = r_eq.door in reached_doors
        for key in Hook:
            fringe_list = [x for x in r_eq.benefit[key] if x not in reached_doors]
            r_eq.benefit[key] = fringe_list
            if len(fringe_list) > 0:
                all_benefits_met = False
        if all_benefits_met:
            eq_list.remove(r_eq)
    if len(eq_list) == 0 and sector in equations.keys():
        del equations[sector]
    else:
        for eq in eq_list:
            eq.access_id = access_id


def find_free_equation(equations):
    for sector, eq_list in equations.items():
        for eq in eq_list:
            if eq.total_cost() <= 0:
                return sector, eq_list, eq
    return None, None, None


def copy_door_equations(builder, sector_list):
    equations = {}
    for sector in builder.sectors + sector_list:
        if sector.equations is None:
            # todo: sort equations?
            sector.equations = calc_sector_equations(sector)
        curr_list = equations[sector] = []
        for equation in sector.equations:
            curr_list.append(equation.copy())
    return equations


def calc_sector_equations(sector):
    equations = []
    is_entrance = sector.is_entrance_sector() and not sector.destination_entrance
    if is_entrance:
        flagged_equations = []
        for door in sector.outstanding_doors:
            equation, flag = calc_door_equation(door, sector, True)
            if flag:
                flagged_equations.append(equation)
            equations.append(equation)
        for flagged_equation in flagged_equations:
            for equation in equations:
                for key, door_list in equation.benefit.items():
                    if flagged_equation.door in door_list and flagged_equation != equation:
                        door_list.remove(flagged_equation.door)
    else:
        for door in sector.outstanding_doors:
            equation, flag = calc_door_equation(door, sector, False)
            equations.append(equation)
    return equations


def calc_door_equation(door, sector, look_for_entrance):
    if look_for_entrance and not door.blocked:
        flag = sector.is_entrance_sector()
        if flag:
            eq = DoorEquation(door)
            eq.benefit[hook_from_door(door)].append(door)
            eq.required = True
            eq.c_switch = door.crystal == CrystalBarrier.Either
            # exceptions for long entrances ???
            # if door.name in ['PoD Dark Alley']:
            eq.entrance_flag = True
            return eq, flag
    eq = DoorEquation(door)
    eq.required = door.blocked or door.dead
    eq.cost = (hanger_from_door(door), door)
    eq.entrance_flag = sector.is_entrance_sector()
    if not door.stonewall:
        start_region = door.entrance.parent_region
        visited = {(start_region, CrystalBarrier.Null)}
        queue = deque([(start_region, CrystalBarrier.Null)])
        found_events = set()
        event_doors = set()
        while len(queue) > 0:
            region, crystal_barrier = queue.popleft()
            if region.crystal_switch and crystal_barrier == CrystalBarrier.Null:
                eq.c_switch = True
                crystal_barrier = CrystalBarrier.Either
            # todo: backtracking from double switch with orange on--
            for loc in region.locations:
                if loc.name in dungeon_events:
                    found_events.add(loc.name)
                    for d in event_doors:
                        if loc.name == d.req_event:
                            connect = d.entrance.connected_region
                            if connect is not None and connect.type == RegionType.Dungeon and valid_crystal(d, crystal_barrier):
                                cb_flag = crystal_barrier if d.crystal == CrystalBarrier.Null else d.crystal
                                cb_flag = CrystalBarrier.Null if cb_flag == CrystalBarrier.Either else cb_flag
                                if (connect, cb_flag) not in visited:
                                    visited.add((connect, cb_flag))
                                    queue.append((connect, cb_flag))
            for ext in region.exits:
                d = ext.door
                if d is not None:
                    if d.controller is not None:
                        d = d.controller
                    if d is not door and d in sector.outstanding_doors and not d.blocked:
                        eq_list = eq.benefit[hook_from_door(d)]
                        if d not in eq_list:
                            eq_list.append(d)
                            crystal_barrier = crystal_barrier if d.crystal == CrystalBarrier.Null else d.crystal
                            if crystal_barrier != CrystalBarrier.Null:
                                if d in eq.crystal_blocked.keys() and eq.crystal_blocked[d] != crystal_barrier:
                                    del eq.crystal_blocked[d]
                                else:
                                    eq.crystal_blocked[d] = crystal_barrier
                        elif d.crystal == CrystalBarrier.Null:
                            if d in eq.crystal_blocked.keys() and eq.crystal_blocked[d] != crystal_barrier:
                                del eq.crystal_blocked[d]
                    if d.req_event is not None and d.req_event not in found_events:
                        event_doors.add(d)
                    else:
                        connect = ext.connected_region if ext.door.controller is None else d.entrance.parent_region
                        if connect is not None and connect.type == RegionType.Dungeon and valid_crystal(d, crystal_barrier):
                            cb_flag = crystal_barrier if d.crystal == CrystalBarrier.Null else d.crystal
                            cb_flag = CrystalBarrier.Null if cb_flag == CrystalBarrier.Either else cb_flag
                            if (connect, cb_flag) not in visited:
                                visited.add((connect, cb_flag))
                                queue.append((connect, cb_flag))
    if len(eq.benefit) == 0:
        eq.required = True
    return eq, False


def meets_crystal_requirment(current_crystal, requirement):
    if current_crystal == CrystalBarrier.Either:
        return True
    return current_crystal == requirement


def valid_crystal(door, current_crystal):
    if door.crystal in [CrystalBarrier.Null, CrystalBarrier.Either]:
        return True
    if current_crystal in [CrystalBarrier.Either, CrystalBarrier.Null]:
        return True
    return door.crystal == current_crystal


# common functions - todo: move to a common place
def kth_combination(k, l, r):
    if r == 0:
        return []
    elif len(l) == r:
        return l
    else:
        i = ncr(len(l) - 1, r - 1)
        if k < i:
            return l[0:1] + kth_combination(k, l[1:], r - 1)
        else:
            return kth_combination(k - i, l[1:], r)


def ncr(n, r):
    if r == 0:
        return 1
    r = min(r, n - r)
    numerator = reduce(op.mul, range(n, n - r, -1), 1)
    denominator = reduce(op.mul, range(1, r + 1), 1)
    return int(numerator / denominator)


dungeon_boss_sectors = {
    'Hyrule Castle': [],
    'Eastern Palace': ['Eastern Boss'],
    'Desert Palace': ['Desert Boss'],
    'Tower of Hera': ['Hera Boss'],
    'Agahnims Tower': ['Tower Agahnim 1'],
    'Palace of Darkness': ['PoD Boss'],
    'Swamp Palace': ['Swamp Boss'],
    'Skull Woods': ['Skull Boss'],
    'Thieves Town': ['Thieves Blind\'s Cell', 'Thieves Boss'],
    'Ice Palace': ['Ice Boss'],
    'Misery Mire': ['Mire Boss'],
    'Turtle Rock': ['TR Boss'],
    'Ganons Tower': ['GT Agahnim 2']
}

default_dungeon_entrances = {
    'Hyrule Castle': ['Hyrule Castle Lobby', 'Hyrule Castle West Lobby', 'Hyrule Castle East Lobby', 'Sewers Rat Path',
                      'Sanctuary'],
    'Eastern Palace': ['Eastern Lobby'],
    'Desert Palace': ['Desert Back Lobby', 'Desert Main Lobby', 'Desert West Lobby', 'Desert East Lobby'],
    'Tower of Hera': ['Hera Lobby'],
    'Agahnims Tower': ['Tower Lobby'],
    'Palace of Darkness': ['PoD Lobby'],
    'Swamp Palace': ['Swamp Lobby'],
    'Skull Woods': ['Skull 1 Lobby', 'Skull Pinball', 'Skull Left Drop', 'Skull Pot Circle', 'Skull 2 East Lobby',
                    'Skull 2 West Lobby', 'Skull Back Drop', 'Skull 3 Lobby'],
    'Thieves Town': ['Thieves Lobby'],
    'Ice Palace': ['Ice Lobby'],
    'Misery Mire': ['Mire Lobby'],
    'Turtle Rock': ['TR Main Lobby', 'TR Eye Bridge', 'TR Big Chest Entrance', 'TR Lazy Eyes'],
    'Ganons Tower': ['GT Lobby']
}

drop_entrances = {
    'Hyrule Castle': ['Sewers Rat Path'],
    'Eastern Palace': [],
    'Desert Palace': [],
    'Tower of Hera': [],
    'Agahnims Tower': [],
    'Palace of Darkness': [],
    'Swamp Palace': [],
    'Skull Woods': ['Skull Pinball', 'Skull Left Drop', 'Skull Pot Circle', 'Skull Back Drop'],
    'Thieves Town': [],
    'Ice Palace': [],
    'Misery Mire': [],
    'Turtle Rock': [],
    'Ganons Tower': []
}


# todo: calculate these for ER - the multi entrance dungeons anyway
dungeon_dead_end_allowance = {
    'Hyrule Castle': 6,
    'Eastern Palace': 1,
    'Desert Palace': 2,
    'Tower of Hera': 1,
    'Agahnims Tower': 1,
    'Palace of Darkness': 1,
    'Swamp Palace': 1,
    'Skull Woods': 3,  # two allowed in skull 1, 1 in skull 3, 0 in skull 2
    'Thieves Town': 1,
    'Ice Palace': 1,
    'Misery Mire': 1,
    'Turtle Rock': 2,  # this assumes one overworld connection
    'Ganons Tower': 1,
    'Desert Palace Back': 1,
    'Desert Palace Main': 1,
    'Skull Woods 1': 0,
    'Skull Woods 2': 0,
    'Skull Woods 3': 1,
}

drop_entrances_allowance = [
    'Sewers Rat Path', 'Skull Pinball', 'Skull Left Drop', 'Skull Pot Circle', 'Skull Back Drop'
]

dead_entrances = [
    'TR Big Chest Entrance'
]

split_check_entrance_invalid = [
    'Desert East Lobby', 'Skull 2 West Lobby'
]

dungeon_portals = {
    'Hyrule Castle': ['Hyrule Castle South', 'Hyrule Castle West', 'Hyrule Castle East', 'Sanctuary'],
    'Eastern Palace': ['Eastern'],
    'Desert Palace': ['Desert Back', 'Desert South', 'Desert West', 'Desert East'],
    'Tower of Hera': ['Hera'],
    'Agahnims Tower': ['Agahnims Tower'],
    'Palace of Darkness': ['Palace of Darkness'],
    'Swamp Palace': ['Swamp'],
    'Skull Woods': ['Skull 1', 'Skull 2 East', 'Skull 2 West', 'Skull 3'],
    'Thieves Town': ['Thieves Town'],
    'Ice Palace': ['Ice'],
    'Misery Mire': ['Mire'],
    'Turtle Rock': ['Turtle Rock Main', 'Turtle Rock Lazy Eyes', 'Turtle Rock Chest', 'Turtle Rock Eye Bridge'],
    'Ganons Tower': ['Ganons Tower']
}

dungeon_drops = {
    'Hyrule Castle': ['Sewers Rat Path'],
    'Skull Woods': ['Skull Pot Circle', 'Skull Pinball', 'Skull Left Drop', 'Skull Back Drop'],
}

