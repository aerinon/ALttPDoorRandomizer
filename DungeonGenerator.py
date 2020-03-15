import random
import collections
import itertools
from collections import defaultdict, deque
from enum import Enum, unique
import logging
from functools import reduce
import operator as op
from typing import List

from BaseClasses import DoorType, Direction, CrystalBarrier, RegionType, Polarity, Sector, PolSlot, flooded_keys
from Regions import key_only_locations, dungeon_events, flooded_keys_reverse
from Dungeons import dungeon_regions


@unique
class Hook(Enum):
    North = 0
    West = 1
    South = 2
    East = 3
    Stairs = 4
    NEdge = 5
    SEdge = 6
    WEdge = 7
    EEdge = 8


class GraphPiece:

    def __init__(self):
        self.hanger_info = None
        self.hanger_crystal = None
        self.hooks = {}
        self.visited_regions = set()
        self.possible_bk_locations = set()


# Turtle Rock shouldn't be generated until the Big Chest entrance is reachable
def validate_tr(builder, entrance_region_names, world, player):
    entrance_regions = convert_regions(entrance_region_names, world, player)
    proposed_map = {}
    doors_to_connect = {}
    all_regions = set()
    bk_needed = False
    bk_special = False
    for sector in builder.sectors:
        for door in sector.outstanding_doors:
            doors_to_connect[door.name] = door
        all_regions.update(sector.regions)
        bk_needed = bk_needed or determine_if_bk_needed(sector, False, world, player)
        bk_special = bk_special or check_for_special(sector)
    dungeon, hangers, hooks = gen_dungeon_info(builder.name, builder.sectors, entrance_regions, proposed_map,
                                               doors_to_connect, bk_needed, bk_special, world, player)
    return check_valid(dungeon, hangers, hooks, proposed_map, doors_to_connect, all_regions, bk_needed, False)


def generate_dungeon(builder, entrance_region_names, split_dungeon, world, player):
    stonewall = check_for_stonewall(builder)
    sector = generate_dungeon_main(builder, entrance_region_names, split_dungeon, world, player)
    if stonewall and not stonewall_valid(stonewall):
        builder.pre_open_stonewall = stonewall
    return sector


def check_for_stonewall(builder):
    for sector in builder.sectors:
        for door in sector.outstanding_doors:
            if door.stonewall:
                return door
    return None


def generate_dungeon_main(builder, entrance_region_names, split_dungeon, world, player):
    logger = logging.getLogger('')
    name = builder.name
    entrance_regions = convert_regions(entrance_region_names, world, player)
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
    finished = False
    # flag if standard and this is hyrule castle
    std_flag = world.mode[player] == 'standard' and bk_special
    while not finished:
        # what are my choices?
        itr += 1
        if itr > 5000:
            raise Exception('Generation taking too long. Ref %s' % name)
        if depth not in dungeon_cache.keys():
            dungeon, hangers, hooks = gen_dungeon_info(name, builder.sectors, entrance_regions, proposed_map,
                                                       doors_to_connect, bk_needed, bk_special, world, player)
            dungeon_cache[depth] = dungeon, hangers, hooks
            valid = check_valid(dungeon, hangers, hooks, proposed_map, doors_to_connect, all_regions, bk_needed, std_flag)
        else:
            dungeon, hangers, hooks = dungeon_cache[depth]
            valid = True
        if valid:
            if len(proposed_map) == len(doors_to_connect):
                finished = True
                continue
            prev_choices = choices_master[depth]
            # make a choice
            hanger, hook = make_a_choice(dungeon, hangers, hooks, prev_choices)
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
                raise Exception('Invalid dungeon. Ref %s' % name)
            a, b = choices_master[depth][-1]
            logger.debug(' ' * depth + "%d: Rescinding %s, %s", depth, a.name, b.name)
            proposed_map.pop(a, None)
            proposed_map.pop(b, None)
    queue = collections.deque(proposed_map.items())
    while len(queue) > 0:
        a, b = queue.pop()
        connect_doors(a, b)
        queue.remove((b, a))
    available_sectors = list(builder.sectors)
    master_sector = available_sectors.pop()
    for sub_sector in available_sectors:
        master_sector.regions.extend(sub_sector.regions)
    master_sector.outstanding_doors.clear()
    master_sector.r_name_set = None
    return master_sector


def determine_if_bk_needed(sector, split_dungeon, world, player):
    if not split_dungeon:
        for region in sector.regions:
            for ext in region.exits:
                door = world.check_for_door(ext.name, player)
                if door is not None and door.bigKey:
                    return True
    return False


def check_for_special(sector):
    return 'Hyrule Dungeon Cellblock' in sector.region_set()


def gen_dungeon_info(name, available_sectors, entrance_regions, proposed_map, valid_doors, bk_needed, bk_special, world, player):
    # step 1 create dungeon: Dict<DoorName|Origin, GraphPiece>
    dungeon = {}
    start = ExplorationState(dungeon=name)
    start.big_key_special = bk_special
    original_state = extend_reachable_state_improved(entrance_regions, start, proposed_map,
                                                     valid_doors, bk_needed, world, player)
    dungeon['Origin'] = create_graph_piece_from_state(None, original_state, original_state, proposed_map)
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
            if not door.stonewall and door not in proposed_map.keys():
                hanger_set.add(door)
                parent = door.entrance.parent_region
                crystal_start = CrystalBarrier.Either if parent.crystal_switch else init_crystal
                init_state = ExplorationState(crystal_start, dungeon=name)
                init_state.big_key_special = start.big_key_special
                o_state = extend_reachable_state_improved([parent], init_state, proposed_map,
                                                          valid_doors, False, world, player)
                o_state_cache[door.name] = o_state
                piece = create_graph_piece_from_state(door, o_state, o_state, proposed_map)
                dungeon[door.name] = piece
    check_blue_states(hanger_set, dungeon, o_state_cache, proposed_map, valid_doors, world, player)

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


def check_blue_states(hanger_set, dungeon, o_state_cache, proposed_map, valid_doors, world, player):
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
                explore_blue_state(door, dungeon, o_state_cache[door.name], proposed_map, valid_doors, world, player)
                doors_to_check.add(door)
        not_blue.difference_update(doors_to_check)


def explore_blue_state(door, dungeon, o_state, proposed_map, valid_doors, world, player):
    parent = door.entrance.parent_region
    blue_start = ExplorationState(CrystalBarrier.Blue, o_state.dungeon)
    blue_start.big_key_special = o_state.big_key_special
    b_state = extend_reachable_state_improved([parent], blue_start, proposed_map, valid_doors, False, world, player)
    dungeon[door.name] = create_graph_piece_from_state(door, o_state, b_state, proposed_map)


def make_a_choice(dungeon, hangers, avail_hooks, prev_choices):
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
        c_hang = queue.pop()
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
        else:
            return None, None

    return next_hanger, hook


def filter_choices(next_hanger, door, orig_hang, prev_choices, hook_candidates):
    if (next_hanger, door) in prev_choices or (door, next_hanger) in prev_choices:
        return False
    return next_hanger != door and orig_hang != next_hanger and door not in hook_candidates


def check_valid(dungeon, hangers, hooks, proposed_map, doors_to_connect, all_regions, bk_needed, std_flag):
    # evaluate if everything is still plausible

    # only origin is left in the dungeon and not everything is connected
    if len(dungeon.keys()) <= 1 and len(proposed_map.keys()) < len(doors_to_connect):
        return False
    # origin has no more hooks, but not all doors have been proposed
    possible_bks = len(dungeon['Origin'].possible_bk_locations)
    true_origin_hooks = [x for x in dungeon['Origin'].hooks.keys() if not x.bigKey or possible_bks > 0 or not bk_needed]
    if len(true_origin_hooks) == 0 and len(proposed_map.keys()) < len(doors_to_connect):
        return False
    if len(true_origin_hooks) == 0 and bk_needed and possible_bks == 0 and len(proposed_map.keys()) == len(
         doors_to_connect):
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
    bk_possible = not bk_needed
    for piece in dungeon.values():
        all_visited.update(piece.visited_regions)
        if not bk_possible and len(piece.possible_bk_locations) > 0:
            bk_possible = True
    if len(all_regions.difference(all_visited)) > 0:
        return False
    if not bk_possible:
        return False
    if std_flag and not cellblock_valid(doors_to_connect, all_regions, proposed_map):
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


def cellblock_valid(valid_doors, all_regions, proposed_map):
    cellblock = None
    for region in all_regions:
        if 'Hyrule Dungeon Cellblock' == region.name:
            cellblock = region
            break
    queue = deque([cellblock])
    visited = {cellblock}
    while len(queue) > 0:
        region = queue.popleft()
        if region.name == 'Sanctuary':
            return True
        for ext in region.exits:
            connect = ext.connected_region
            if connect is None and ext.name in valid_doors:
                door = valid_doors[ext.name]
                if not door.blocked:
                    if door in proposed_map:
                        new_region = proposed_map[door].entrance.parent_region
                        if new_region not in visited:
                            visited.add(new_region)
                            queue.append(new_region)
                    else:
                        return True  # outstanding connection possible
            elif connect is not None:
                door = ext.door
                if door is not None and not door.blocked and connect not in visited:
                    visited.add(connect)
                    queue.append(connect)
    return False  # couldn't find an outstanding door or the sanctuary


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
                if door is not None and door != stonewall and not door.blocked and parent not in visited:
                    visited.add(parent)
                    queue.append(parent)
    # we didn't find anything bad
    return True


def create_graph_piece_from_state(door, o_state, b_state, proposed_map):
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
        if (door is None or d != door) and not d.blocked and d not in proposed_map.keys():
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
    return graph_piece


def filter_for_potential_bk_locations(locations):
    return [x for x in locations if
            '- Big Chest' not in x.name and '- Prize' not in x.name and x.name not in dungeon_events
            and x.name not in key_only_locations.keys() and x.name not in ['Agahnim 1', 'Agahnim 2']]


def opposite_h_type(h_type):
    type_map = {
        Hook.Stairs: Hook.Stairs,
        Hook.North: Hook.South,
        Hook.South: Hook.North,
        Hook.West: Hook.East,
        Hook.East: Hook.West,
        Hook.NEdge: Hook.SEdge,
        Hook.SEdge: Hook.NEdge,
        Hook.EEdge: Hook.WEdge,
        Hook.WEdge: Hook.EEdge,
    }
    return type_map[h_type]


edge_map = {
    Direction.North: Hook.NEdge,
    Direction.South: Hook.SEdge,
    Direction.West: Hook.WEdge,
    Direction.East: Hook.EEdge,
}

edge_map_back = {
    Direction.North: Hook.SEdge,
    Direction.South: Hook.NEdge,
    Direction.West: Hook.EEdge,
    Direction.East: Hook.WEdge,
}


def hook_from_door(door):
    if door.type == DoorType.SpiralStairs:
        return Hook.Stairs
    if door.type == DoorType.Normal:
        dir = {
            Direction.North: Hook.North,
            Direction.South: Hook.South,
            Direction.West: Hook.West,
            Direction.East: Hook.East,
        }
        return dir[door.direction]
    if door.type == DoorType.Open:
        return edge_map[door.direction]
    return None


def hanger_from_door(door):
    if door.type == DoorType.SpiralStairs:
        return Hook.Stairs
    if door.type == DoorType.Normal:
        dir = {
            Direction.North: Hook.South,
            Direction.South: Hook.North,
            Direction.West: Hook.East,
            Direction.East: Hook.West,
        }
        return dir[door.direction]
    if door.type == DoorType.Open:
        return edge_map_back[door.direction]
    return None


def connect_doors(a, b):
    # Return on unsupported types.
    if a.type in [DoorType.StraightStairs, DoorType.Hole, DoorType.Warp, DoorType.Ladder,
                  DoorType.Interior, DoorType.Logical]:
        return
    # Connect supported types
    if a.type == DoorType.Normal or a.type == DoorType.SpiralStairs or a.type == DoorType.Open:
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
                    if location.name in key_only_locations and 'Small Key' in location.item.name:
                        self.key_locations += 1
                    if location.name not in dungeon_events and '- Prize' not in location.name and location.name not in ['Agahnim 1', 'Agahnim 2']:
                        self.ttl_locations += 1
                if location not in self.found_locations:
                    self.found_locations.append(location)
                    if not bk_Flag:
                        self.bk_found.add(location)
                if location.name in dungeon_events and location.name not in self.events:
                    if self.flooded_key_check(location):
                        self.perform_event(location.name, key_region)
                if location.name in flooded_keys_reverse.keys() and self.location_found(
                     flooded_keys_reverse[location.name]):
                    self.perform_event(flooded_keys_reverse[location.name], key_region)
        if key_checks and region.name == 'Hyrule Dungeon Cellblock' and not self.big_key_opened:
            self.big_key_opened = True
            self.avail_doors.extend(self.big_doors)
            self.big_doors.clear()

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
            exp_door = queue.pop()
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
                if door.dest is None and not self.in_door_list_ic(door, self.unattached_doors):
                    self.append_door_to_list(door, self.unattached_doors)
                elif door.req_event is not None and door.req_event not in self.events and not self.in_door_list(door,
                                                                                                                self.event_doors):
                    self.append_door_to_list(door, self.event_doors)
                elif not self.in_door_list(door, self.avail_doors):
                    self.append_door_to_list(door, self.avail_doors)

    def add_all_doors_check_proposed(self, region, proposed_map, valid_doors, flag, world, player):
        for door in get_doors(world, region, player):
            if self.can_traverse(door):
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
                elif door.bigKey and not self.big_key_opened:
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

    def can_traverse(self, door):
        if door.blocked:
            return False
        if door.crystal not in [CrystalBarrier.Null, CrystalBarrier.Either]:
            return self.crystal == CrystalBarrier.Either or door.crystal == self.crystal
        return True

    def can_traverse_bk_check(self, door, isOrigin):
        if door.blocked:
            return False
        if door.crystal not in [CrystalBarrier.Null, CrystalBarrier.Either]:
            return self.crystal == CrystalBarrier.Either or door.crystal == self.crystal
        return not isOrigin or not door.bigKey or self.count_locations_exclude_specials() > 0
        # return not door.bigKey or len([x for x in self.found_locations if '- Prize' not in x.name]) > 0

    def count_locations_exclude_specials(self):
        cnt = 0
        for loc in self.found_locations:
            if '- Big Chest' not in loc.name and '- Prize' not in loc.name and loc.name not in dungeon_events and loc.name not in key_only_locations.keys():
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


# todo: delete this
def extend_reachable_state(search_regions, state, world, player):
    local_state = state.copy()
    for region in search_regions:
        local_state.visit_region(region)
        local_state.add_all_doors_check_unattached(region, world, player)
    while len(local_state.avail_doors) > 0:
        explorable_door = local_state.next_avail_door()
        connect_region = world.get_entrance(explorable_door.door.name, player).connected_region
        if connect_region is not None:
            if valid_region_to_explore(connect_region, local_state.dungeon, world, player) and not local_state.visited(
                 connect_region):
                local_state.visit_region(connect_region)
                local_state.add_all_doors_check_unattached(connect_region, world, player)
    return local_state


def extend_reachable_state_improved(search_regions, state, proposed_map, valid_doors, isOrigin, world, player):
    local_state = state.copy()
    for region in search_regions:
        local_state.visit_region(region)
        local_state.add_all_doors_check_proposed(region, proposed_map, valid_doors, False, world, player)
    while len(local_state.avail_doors) > 0:
        explorable_door = local_state.next_avail_door()
        if explorable_door.door.bigKey:
            if isOrigin:
                big_not_found = not special_big_key_found(local_state, world, player) if local_state.big_key_special else local_state.count_locations_exclude_specials() == 0
                if big_not_found:
                    continue  # we can't open this door
        if explorable_door.door in proposed_map:
            connect_region = world.get_entrance(proposed_map[explorable_door.door].name, player).parent_region
        else:
            connect_region = world.get_entrance(explorable_door.door.name, player).connected_region
        if connect_region is not None:
            if valid_region_to_explore(connect_region, local_state.dungeon, world, player) and not local_state.visited(
                 connect_region):
                flag = explorable_door.flag or explorable_door.door.bigKey
                local_state.visit_region(connect_region, bk_Flag=flag)
                local_state.add_all_doors_check_proposed(connect_region, proposed_map, valid_doors, flag, world, player)
    return local_state


def special_big_key_found(state, world, player):
    cellblock = world.get_region('Hyrule Dungeon Cellblock', player)
    return state.visited(cellblock)


# cross-utility methods
def valid_region_to_explore(region, name, world, player):
    if region is None:
        return False
    return (region.type == RegionType.Dungeon and region.dungeon.name in name) or region.name in world.inaccessible_regions[player]


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
        self.dead_ends = 0
        self.branches = 0
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

        self.pre_open_stonewall = None  # used by stonewall system

        self.candidates = None
        self.key_doors_num = None
        self.combo_size = None
        self.flex = 0
        self.key_door_proposal = None

        if name in dungeon_dead_end_allowance.keys():
            self.allowance = dungeon_dead_end_allowance[name]
        elif 'Stonewall' in name:
            self.allowance = 1
        elif 'Prewall' in name:
            orig_name = name[:-8]
            if orig_name in dungeon_dead_end_allowance.keys():
                self.allowance = dungeon_dead_end_allowance[orig_name]
        if self.allowance is None:
            self.allowance = 1

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


def simple_dungeon_builder(name, sector_list):
    define_sector_features(sector_list)
    builder = DungeonBuilder(name)
    dummy_pool = dict.fromkeys(sector_list)
    global_pole = GlobalPolarity(dummy_pool)
    for sector in sector_list:
        assign_sector(sector, builder, dummy_pool, global_pole)
    return builder


def create_dungeon_builders(all_sectors, world, player, dungeon_entrances=None):
    logger = logging.getLogger('')
    logger.info('Shuffling Dungeon Sectors')
    if dungeon_entrances is None:
        dungeon_entrances = default_dungeon_entrances
    define_sector_features(all_sectors)
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
                assign_sector(find_sector(r_name, candidate_sectors), current_dungeon, candidate_sectors, global_pole)
    for key in dungeon_entrances.keys():
        current_dungeon = dungeon_map[key]
        current_dungeon.all_entrances = dungeon_entrances[key]
        for r_name in current_dungeon.all_entrances:
            assign_sector(find_sector(r_name, candidate_sectors), current_dungeon, candidate_sectors, global_pole)
    # categorize sectors

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
    logger.info('-Assigning Chest Locations')
    assign_location_sectors(dungeon_map, free_location_sectors, global_pole)
    logger.info('-Assigning Crystal Switches and Barriers')
    leftover = assign_crystal_switch_sectors(dungeon_map, crystal_switches, global_pole)
    for sector in leftover:
        if sector.polarity().is_neutral():
            neutral_sectors[sector] = None
        else:
            polarized_sectors[sector] = None
    # blue barriers
    assign_crystal_barrier_sectors(dungeon_map, crystal_barriers, global_pole)
    # polarity:
    if not global_pole.is_valid(dungeon_map):
        raise NeutralizingException('Either free location/crystal assignment is already globally invalid - lazy dev check this earlier!')
    logger.info('-Balancing Doors')
    assign_polarized_sectors(dungeon_map, polarized_sectors, global_pole, logger)
    # the rest
    assign_the_rest(dungeon_map, neutral_sectors, global_pole)
    return dungeon_map


def define_sector_features(sectors):
    for sector in sectors:
        if 'Hyrule Dungeon Cellblock' in sector.region_set():
            sector.bk_provided = True
        if 'Thieves Blind\'s Cell' in sector.region_set():
            sector.bk_required = True
        for region in sector.regions:
            for loc in region.locations:
                if '- Prize' in loc.name or loc.name in ['Agahnim 1', 'Agahnim 2', 'Hyrule Castle - Big Key Drop']:
                    pass
                elif loc.event and 'Small Key' in loc.item.name:
                    sector.key_only_locations += 1
                elif loc.name not in dungeon_events:
                    sector.chest_locations += 1
                    if '- Big Chest' in loc.name:
                        sector.bk_required = True
                        sector.big_chest_present = True
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
    if sector is not None:
        del candidate_sectors[sector]
        dungeon.sectors.append(sector)
        global_pole.consume(sector)
        dungeon.location_cnt += sector.chest_locations
        dungeon.key_drop_cnt += sector.key_only_locations
        if sector.c_switch:
            dungeon.c_switch_present = True
        if sector.blue_barrier:
            dungeon.c_switch_required = True
        if sector.bk_required:
            dungeon.bk_required = True
        if sector.bk_provided:
            dungeon.bk_provided = True
        count_conn_needed_supplied(sector, dungeon.conn_needed, dungeon.conn_supplied)
        dungeon.dead_ends += sector.dead_ends()
        dungeon.branches += sector.branches()


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
            if totals[idx] < minimal_locations(d_name):
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


def minimal_locations(dungeon_name):
    # bump to 5 if maps do something useful for all these dungeons
    if dungeon_name == 'Hyrule Castle':
        return 4  # bk + compass + 2 others
    if dungeon_name == 'Agahnims Tower':
        return 4
    if dungeon_name == 'Ganons Tower':
        return 4
    # reduce gt to 4 once compasses work
    return 5


def assign_crystal_switch_sectors(dungeon_map, crystal_switches, global_pole, assign_one=False):
    population = []
    some_c_switches_present = False
    for name, builder in dungeon_map.items():
        if builder.c_switch_required and not builder.c_switch_present:
            population.append(name)
        if builder.c_switch_present:
            some_c_switches_present = True
    if len(population) == 0:  # nothing needs a switch
        if assign_one and not some_c_switches_present:  # something should have one
            valid, builder_choice, switch_choice = False, None, None
            switch_candidates = list(crystal_switches)
            switch_choice = random.choice(switch_candidates)
            switch_candidates.remove(switch_choice)
            builder_candidates = list(dungeon_map.keys())
            while not valid:
                if len(builder_candidates) == 0:
                    if len(switch_candidates) == 0:
                        raise Exception('No where to assign crystal switch. Ref %s' % next(iter(dungeon_map.keys())))
                    switch_choice = random.choice(switch_candidates)
                    switch_candidates.remove(switch_choice)
                    builder_candidates = list(dungeon_map.keys())
                choice = random.choice(builder_candidates)
                builder_candidates.remove(choice)
                builder_choice = dungeon_map[choice]
                valid = global_pole.is_valid_choice(dungeon_map, builder_choice, [switch_choice])
            assign_sector(switch_choice, builder_choice, crystal_switches, global_pole)
        return crystal_switches
    sector_list = list(crystal_switches)
    choices = random.sample(sector_list, k=len(population))
    for i, choice in enumerate(choices):
        builder = dungeon_map[population[i]]
        assign_sector(choice, builder, crystal_switches, global_pole)
    return crystal_switches


def assign_crystal_barrier_sectors(dungeon_map, crystal_barriers, global_pole):
    population = []
    for name, builder in dungeon_map.items():
        if builder.c_switch_present:
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
        if len(builder.sectors) == 1:
            continue
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
    return unconnected_builders


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
        if builder.dead_ends > builder.branches + builder.allowance:
            problem_builders[name] = builder
        for h_type in Hook:
            lack = builder.conn_balance[h_type] = builder.conn_supplied[h_type] - builder.conn_needed[h_type]
            if lack < 0:
                builder.total_conn_lack += -lack
                problem_builders[name] = builder
    return problem_builders


def is_entrance_sector(builder, sector):
    for entrance in builder.all_entrances:
        r_set = sector.region_set()
        if entrance in r_set:
            return True
    return False


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
    result = [0, 0, 0]
    for sector in sector_list:
        vector = sector.magnitude()
        for i in range(len(result)):
            result[i] = result[i] + vector[i]
    return result


def sum_polarity(sector_list):
    pol = Polarity()
    for sector in sector_list:
        pol += sector.polarity()
    return pol


def assign_polarized_sectors(dungeon_map, polarized_sectors, global_pole, logger):
    # step 1: fix polarity connection issues
    logger.info('--Basic Traversal')
    unconnected_builders = identify_polarity_issues(dungeon_map)
    while len(unconnected_builders) > 0:
        for name, builder in unconnected_builders.items():
            candidates = find_connection_candidates(builder.mag_needed, polarized_sectors)
            valid, sector = False, None
            while not valid:
                if len(candidates) == 0:
                    raise Exception('Cross Dungeon Builder: Cannot find a candidate for connectedness. %s' % name)
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
            biggest = max(charges) + 1
            weights = [biggest-x for x in charges]
            valid, choice = False, None
            while not valid:
                if len(candidates) == 0:
                    raise Exception('Cross Dungeon Builder: Simple branch problems: %s' % name)
                choice = random.choices(candidates, weights)[0]
                i = candidates.index(choice)
                candidates.pop(i)
                weights.pop(i)
                valid = global_pole.is_valid_choice(dungeon_map, builder, [choice]) and valid_connected_assignment(builder, [choice])
            assign_sector(choice, builder, polarized_sectors, global_pole)
            builder.total_conn_lack = 0
            builder.conn_balance.clear()
        problem_builders = identify_simple_branching_issues(problem_builders)

    # step 3: fix neutrality issues
    polarity_step_3(dungeon_map, polarized_sectors, global_pole, logger)

    # step 4: fix dead ends again
    neutral_choices: List[List] = neutralize_the_rest(polarized_sectors)
    problem_builders = identify_branching_issues_2(dungeon_map)
    while len(problem_builders) > 0:
        for name, builder in problem_builders.items():
            candidates = find_branching_candidates(builder, neutral_choices)
            # if len(candidates) <= 0:
            #     problem_builders = {}
            #     continue
            choice = random.choice(candidates)
            if valid_polarized_assignment(builder, choice):
                neutral_choices.remove(choice)
                for sector in choice:
                    assign_sector(sector, builder, polarized_sectors, global_pole)
            builder.unfulfilled.clear()
        problem_builders = identify_branching_issues_2(problem_builders)

    # step 5: assign randomly until gone - must maintain connectedness, neutral polarity, branching, lack, etc.
    comb_w_replace = len(dungeon_map) ** len(neutral_choices)
    combinations = None
    if comb_w_replace <= 1000:
        combinations = list(itertools.product(dungeon_map.keys(), repeat=len(neutral_choices)))
        random.shuffle(combinations)
    tries = 0
    while len(polarized_sectors) > 0:
        if tries > 1000 or (combinations and tries >= len(combinations)):
            raise Exception('No valid assignment found. Ref: %s' % next(iter(dungeon_map.keys())))
        if combinations:
            choices = combinations[tries]
        else:
            choices = random.choices(list(dungeon_map.keys()), k=len(neutral_choices))
        chosen_sectors = defaultdict(list)
        for i, choice in enumerate(choices):
            chosen_sectors[choice].extend(neutral_choices[i])
        all_valid = True
        for name, sector_list in chosen_sectors.items():
            if not valid_assignment(dungeon_map[name], sector_list):
                all_valid = False
                break
        if all_valid:
            for i, choice in enumerate(choices):
                builder = dungeon_map[choice]
                for sector in neutral_choices[i]:
                    assign_sector(sector, builder, polarized_sectors, global_pole)
        tries += 1


def polarity_step_3(dungeon_map, polarized_sectors, global_pole, logger):
    builder_order = list(dungeon_map.values())
    random.shuffle(builder_order)
    for builder in builder_order:
        logger.info('--Balancing %s', builder.name)
        while not builder.polarity().is_neutral():
            candidates = find_neutralizing_candidates(builder, polarized_sectors)
            valid, sectors = False, None
            while not valid:
                if len(candidates) == 0:
                    raise NeutralizingException('Unable to find a globally valid neutralizer: %s' % builder.name)
                sectors = random.choice(candidates)
                candidates.remove(sectors)
                valid = global_pole.is_valid_choice(dungeon_map, builder, sectors)
            for sector in sectors:
                assign_sector(sector, builder, polarized_sectors, global_pole)


class GlobalPolarity:

    def __init__(self, candidate_sectors):
        self.positives = [0, 0, 0]
        self.negatives = [0, 0, 0]
        for sector in candidate_sectors:
            pol = sector.polarity()
            for slot in PolSlot:
                if pol.vector[slot.value] < 0:
                    self.negatives[slot.value] += -pol.vector[slot.value]
                elif pol.vector[slot.value] > 0:
                    self.positives[slot.value] += pol.vector[slot.value]

    def copy(self):
        gp = GlobalPolarity([])
        gp.positives = self.positives.copy()
        gp.negatives = self.negatives.copy()
        return gp

    def is_valid(self, dungeon_map):
        polarities = [x.polarity() for x in dungeon_map.values()]
        return self._is_valid_polarities(polarities)

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
        for slot in PolSlot:
            if polarity[slot.value] > 0 and slot != PolSlot.Stairs:
                if self.positives[slot.value] >= polarity[slot.value]:
                    self.positives[slot.value] -= polarity[slot.value]
                else:
                    raise Exception('Invalid assignment of %s' % sector.name)
            elif polarity[slot.value] < 0 and slot != PolSlot.Stairs:
                if self.negatives[slot.value] >= -polarity[slot.value]:
                    self.negatives[slot.value] += polarity[slot.value]
                else:
                    raise Exception('Invalid assignment of %s' % sector.name)
            elif slot == PolSlot.Stairs:
                if self.positives[slot.value] >= polarity[slot.value]:
                    self.positives[slot.value] -= polarity[slot.value]
                else:
                    raise Exception('Invalid assignment of %s' % sector.name)

    def is_valid_choice(self, dungeon_map, builder, sectors):
        proposal = self.copy()
        non_neutral_polarities = [x.polarity() for x in dungeon_map.values() if not x.polarity().is_neutral() and x != builder]
        current_polarity = builder.polarity() + sum_polarity(sectors)
        non_neutral_polarities.append(current_polarity)
        for sector in sectors:
            proposal.consume(sector)
        return proposal._is_valid_polarities(non_neutral_polarities)


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
    outflow_needed = builder.dead_ends > builder.branches + builder.allowance
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
        if ttl_lack < original_lack or original_lack >= 0:
            candidates[ttl_lack].append(sector)
            charges[ttl_lack].append((builder.polarity()+sector.polarity()).charge())
            if ttl_lack < best_lack:
                best_lack = ttl_lack
    if best_lack == original_lack and not outflow_needed:
        raise Exception('These candidates may not help at all')
    if len(candidates[best_lack]) <= 0:
        raise Exception('Nothing can fix the simple branching issue. Panic ensues.')
    return candidates[best_lack], charges[best_lack]


def calc_sector_balance(sector):  # todo: move to base class?
    if sector.conn_balance is None:
        sector.conn_balance = defaultdict(int)
        for door in sector.outstanding_doors:
            if door.blocked or door.dead or sector.branching_factor() <= 1:
                sector.conn_balance[hook_from_door(door)] -= 1
            else:
                sector.conn_balance[hanger_from_door(door)] += 1


def find_neutralizing_candidates(builder, sector_pool):
    polarity = builder.polarity()
    candidates = defaultdict(list)
    original_charge = polarity.charge()
    best_charge = original_charge
    main_pool = list(sector_pool)
    last_r = 0
    while len(candidates) == 0:
        r_range = range(last_r + 1, last_r + 3)
        for r in r_range:
            if r > len(main_pool):
                if len(candidates) == 0:
                    raise NeutralizingException('Cross Dungeon Builder: No possible neutralizers left %s' % builder.name)
                else:
                    continue
            last_r = r
            combinations = ncr(len(main_pool), r)
            for i in range(0, combinations):
                choice = kth_combination(i, main_pool, r)
                p_charge = (polarity + sum_polarity(choice)).charge()
                if p_charge < original_charge and p_charge <= best_charge:
                    candidates[p_charge].append(choice)
                    if p_charge < best_charge:
                        best_charge = p_charge

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
            if ttl_balance >= 0 and builder.dead_ends + ttl_deads <= builder.branches + ttl_branches + builder.allowance:
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


def find_branching_candidates(builder, neutral_choices):
    candidates = []
    for choice in neutral_choices:
        door_match = False
        flow_match = False
        for sector in choice:
            if sector.adj_outflow() >= 2:
                flow_match = True
            for door in sector.outstanding_doors:
                if builder.unfulfilled[hanger_from_door(door)] > 0:
                    door_match = True
        if door_match and flow_match:
            candidates.append(choice)
    if len(candidates) == 0:
        raise Exception('Cross Dungeon Builder: No more branching candidates! %s' % builder.name)
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
            raise Exception("Cross Dungeon Builder: no more neutral pairings possible")
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


def valid_assignment(builder, sector_list):
    if not valid_polarized_assignment(builder, sector_list):
        return False
    return len(resolve_equations(builder, sector_list)) == 0


def valid_connected_assignment(builder, sector_list):
    full_list = sector_list + builder.sectors
    for sector in full_list:
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


def valid_polarized_assignment(builder, sector_list):
    if not valid_connected_assignment(builder, sector_list):
        return False
    return (sum_polarity(sector_list) + sum_polarity(builder.sectors)).is_neutral()


def assign_the_rest(dungeon_map, neutral_sectors, global_pole):
    while len(neutral_sectors) > 0:
        sector_list = list(neutral_sectors)
        choices = random.choices(list(dungeon_map.keys()), k=len(sector_list))
        for i, choice in enumerate(choices):
            builder = dungeon_map[choice]
            if valid_polarized_assignment(builder, [sector_list[i]]):
                assign_sector(sector_list[i], builder, neutral_sectors, global_pole)


def split_dungeon_builder(builder, split_list):
    logger = logging.getLogger('')
    logger.info('Splitting Up Desert/Skull')
    candidate_sectors = dict.fromkeys(builder.sectors)
    global_pole = GlobalPolarity(candidate_sectors)

    dungeon_map = {}
    for name, split_entrances in split_list.items():
        key = builder.name + ' ' + name
        dungeon_map[key] = sub_builder = DungeonBuilder(key)
        sub_builder.all_entrances = split_entrances
        for r_name in split_entrances:
            assign_sector(find_sector(r_name, candidate_sectors), sub_builder, candidate_sectors, global_pole)
    return balance_split(candidate_sectors, dungeon_map, global_pole)


def balance_split(candidate_sectors, dungeon_map, global_pole):
    logger = logging.getLogger('')
    # categorize sectors
    crystal_switches, crystal_barriers, neutral_sectors, polarized_sectors = categorize_sectors(candidate_sectors)
    leftover = assign_crystal_switch_sectors(dungeon_map, crystal_switches, global_pole, len(crystal_barriers) > 0)
    for sector in leftover:
        if sector.polarity().is_neutral():
            neutral_sectors[sector] = None
        else:
            polarized_sectors[sector] = None
    # blue barriers
    assign_crystal_barrier_sectors(dungeon_map, crystal_barriers, global_pole)
    # polarity:
    logger.info('-Re-balancing ' + next(iter(dungeon_map.keys())) + ' et al')
    assign_polarized_sectors(dungeon_map, polarized_sectors, global_pole, logger)
    # the rest
    assign_the_rest(dungeon_map, neutral_sectors, global_pole)
    return dungeon_map


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


class DoorEquation:

    def __init__(self, door):
        self.door = door
        self.cost = defaultdict(list)
        self.benefit = defaultdict(list)
        self.required = False

    def copy(self):
        eq = DoorEquation(self.door)
        for key, doors in self.cost.items():
            eq.cost[key] = doors.copy()
        for key, doors in self.benefit.items():
            eq.benefit[key] = doors.copy()
        eq.required = self.required
        return eq

    def total_cost(self):
        ttl = 0
        for key, door_list in self.cost.items():
            ttl += len(door_list)
        return ttl

    def profit(self):
        ttl = 0
        for key, door_list in self.benefit.items():
            ttl += len(door_list)
        return ttl - self.total_cost()

    def neutral(self):
        for key in Hook:
            if len(self.cost[key]) != len(self.benefit[key]):
                return False
        return True

    def can_cover_cost(self, current_access):
        for key, door_list in self.cost.items():
            if len(door_list) > current_access[key]:
                return False
        return True


def identify_branching_issues_2(dungeon_map):
    unconnected_builders = {}
    for name, builder in dungeon_map.items():
        unreached_doors = resolve_equations(builder, [])
        if len(unreached_doors) > 0:
            unconnected_builders[name] = builder
            for hook, door_list in unreached_doors.items():
                builder.unfulfilled[hook] += len(door_list)
    return unconnected_builders


def resolve_equations(builder, sector_list):
    unreached_doors = defaultdict(list)
    equations = copy_door_equations(builder, sector_list)
    current_access = defaultdict(int)
    reached_doors = set()
    # resolve all that provide more access
    free_sector, eq_list, free_eq = find_free_equation(equations)
    while free_eq is not None:
        resolve_equation(free_eq, eq_list, free_sector, current_access, reached_doors, equations)
        free_sector, eq_list, free_eq = find_free_equation(equations)
    while len(equations) > 0:
        eq, eq_list, sector = find_priority_equation(equations, current_access)
        if eq is not None:
            resolve_equation(eq, eq_list, sector, current_access, reached_doors, equations)
        else:
            for sector, eq_list in equations.items():
                for eq in eq_list:
                    unreached_doors[hook_from_door(eq.door)].append(eq.door)
            return unreached_doors
    return unreached_doors


# an equations with no change to access (check)
# the highest benefit equations, that can be paid for (check)
# 0-benefit required transforms
# 0-benefit transforms (how to pick between these?)
# negative benefit transforms (dead end)
def find_priority_equation(equations, current_access):
    flex = calc_flex(equations, current_access)
    required = calc_required(equations, current_access)
    best_profit = None
    triplet_candidates = []
    local_profit_map = {}
    for sector, eq_list in equations.items():
        eq_list.sort(key=lambda eq: eq.profit(), reverse=True)
        best_local_profit = None
        for eq in eq_list:
            profit = eq.profit()
            if best_local_profit is None or profit > best_local_profit:
                best_local_profit = profit
            if eq.can_cover_cost(current_access):
                if eq.neutral():
                    return eq, eq_list, sector  # don't need to compare
                if best_profit is None or profit >= best_profit:
                    if best_profit is None or profit > best_profit:
                        triplet_candidates = [(eq, eq_list, sector)]
                        best_profit = profit
                    else:
                        triplet_candidates.append((eq, eq_list, sector))
        local_profit_map[sector] = best_local_profit
    filtered_candidates = filter_requirements(triplet_candidates, equations, required, current_access)
    if len(filtered_candidates) == 0:
        filtered_candidates = triplet_candidates
    if len(filtered_candidates) == 0:
        return None, None, None  # can't pay for anything
    if len(filtered_candidates) == 1:
        return filtered_candidates[0]

    required_candidates = [x for x in filtered_candidates if x[0].required]
    if len(required_candidates) == 0:
        required_candidates = filtered_candidates
    if len(required_candidates) == 1:
        return required_candidates[0]

    flexible_candidates = [x for x in required_candidates if x[0].can_cover_cost(flex)]
    if len(flexible_candidates) == 0:
        flexible_candidates = required_candidates
    if len(flexible_candidates) == 1:
        return flexible_candidates[0]

    good_local_candidates = [x for x in flexible_candidates if local_profit_map[x[2]] == x[0].profit()]
    if len(good_local_candidates) == 0:
        good_local_candidates = flexible_candidates
    return good_local_candidates[0]  # just pick one I guess


def calc_required(equations, current_access):
    ttl = 0
    for num in current_access.values():
        ttl += num
    local_profit_map = {}
    for sector, eq_list in equations.items():
        best_local_profit = None
        for eq in eq_list:
            profit = eq.profit()
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
                    if eq.profit() < local_profit_map[sector]:
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
                for key, door_list in eq.cost.items():
                    required_costs[key] += len(door_list)
                for key, door_list in eq.benefit.items():
                    required_benefits[key] += len(door_list)
    return required_costs, required_benefits


def calc_flex(equations, current_access):
    flex_spending = defaultdict(int)
    required_costs = defaultdict(int)
    for sector, eq_list in equations.items():
        for eq in eq_list:
            if eq.required:
                for key, door_list in eq.cost.items():
                    required_costs[key] += len(door_list)
    for key in Hook:
        flex_spending[key] = max(0, current_access[key]-required_costs[key])
    return flex_spending


def filter_requirements(triplet_candidates, equations, required, current_access):
    r_costs, r_exits = required
    valid_candidates = []
    for cand, cand_list, cand_sector in triplet_candidates:
        valid = True
        if not cand.required:
            potential_benefit = defaultdict(int)
            potential_costs = defaultdict(int)
            for h_type, benefit in current_access.items():
                cur_cost = len(cand.cost[h_type])
                if benefit - cur_cost > 0:
                    potential_benefit[h_type] += benefit - cur_cost
            for h_type, benefit_list in cand.benefit.items():
                potential_benefit[h_type] += len(benefit_list)
            for sector, eq_list in equations.items():
                if sector == cand_sector:
                    affected_doors = [d for x in cand.benefit.values() for d in x] + [d for x in cand.cost.values() for d in x]
                    adj_list = [x for x in eq_list if x.door not in affected_doors]
                else:
                    adj_list = eq_list
                for eq in adj_list:
                    for h_type, benefit_list in eq.benefit.items():
                        potential_benefit[h_type] += len(benefit_list)
                    for h_type, cost_list in eq.cost.items():
                        potential_costs[h_type] += len(cost_list)
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


def resolve_equation(equation, eq_list, sector, current_access, reached_doors, equations):
    for key, door_list in equation.cost.items():
        if current_access[key] - len(door_list) < 0:
            raise Exception('Cannot pay for this connection')
        current_access[key] -= len(door_list)
        for door in door_list:
            reached_doors.add(door)
    for key, door_list in equation.benefit.items():
        current_access[key] += len(door_list)
        for door in door_list:
            reached_doors.add(door)
    eq_list.remove(equation)
    removing = [x for x in eq_list if x.door in reached_doors]
    for r_eq in removing:
        all_benefits_met = True
        for key in Hook:
            fringe_list = [x for x in r_eq.benefit[key] if x not in reached_doors]
            if len(fringe_list) > 0:
                all_benefits_met = False
                r_eq.benefit[key] = fringe_list
        if all_benefits_met:
            eq_list.remove(r_eq)
    if len(eq_list) == 0:
        del equations[sector]


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
            #todo: sort equations?
            sector.equations = calc_sector_equations(sector, builder)
        curr_list = equations[sector] = []
        for equation in sector.equations:
            curr_list.append(equation.copy())
    return equations


def calc_sector_equations(sector, builder):
    equations = []
    is_entrance = is_entrance_sector(builder, sector)
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
            return eq, flag
    eq = DoorEquation(door)
    eq.required = door.blocked or door.dead
    eq.cost[hanger_from_door(door)].append(door)
    if not door.stonewall:
        start_region = door.entrance.parent_region
        visited = {start_region}
        queue = deque([start_region])
        found_events = set()
        event_doors = set()
        while len(queue) > 0:
            region = queue.popleft()
            for loc in region.locations:
                if loc.name in dungeon_events:
                    found_events.add(loc.name)
                    for d in event_doors:
                        if loc.name == d.req_event:
                            connect = d.entrance.connected_region
                            if connect is not None and connect.type == RegionType.Dungeon and connect not in visited:
                                visited.add(connect)
                                queue.append(connect)
            for ext in region.exits:
                d = ext.door
                if d is not None:
                    if d.controller is not None:
                        d = d.controller
                    if d is not door and d in sector.outstanding_doors and not d.blocked:
                        eq_list = eq.benefit[hook_from_door(d)]
                        if d not in eq_list:
                            eq_list.append(d)
                    if d.req_event is not None and d.req_event not in found_events:
                        event_doors.add(d)
                    else:
                        connect = ext.connected_region
                        if connect is not None and connect.type == RegionType.Dungeon and connect not in visited:
                            visited.add(connect)
                            queue.append(connect)
    if len(eq.benefit) == 0:
        eq.required = True
    return eq, False


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
    'Skull Woods 1': 2,
    'Skull Woods 2': 0,
    'Skull Woods 3': 1,
}
