from collections import deque, defaultdict
from typing import Optional, Deque, Tuple

from BaseClasses import DoorType
from DungeonGenerator import ExplorationState
from KeyDoorShuffle import KeyCounter
from KeyDoorShuffle import find_big_chest_locations, dungeon_table, open_a_door, important_location
from KeyDoorShuffle import find_outside_connection, prize_relevance, expand_key_state, create_key_counters
from Regions import dungeon_events
from Rules import check_is_dark_world
from dungeon.DungeonStitcherV2 import special_big_key_doors


class NewKeyLogic(object):

    def __init__(self):
        self.bk_regions = set()
        self.bk_locations = set()
        self.bk_restricted = set()
        self.region_key_reqs = {}
        self.location_key_reqs = {}

        self.key_spheres = defaultdict(list)   # number of keys to a list of spheres accessible by the amt of keys
        self.sphere_map = {}
        self.segment_map = {}   # segment id to segment object

class KeySphere(object):

    def __init__(self, code):
        self.code = code
        self.segment_set = set()  # segments that make up this sphere, their codes
        self.key_counter = None
        self.child_sphere = []
        self.bk_child_sphere = None

class KeySegment(object):
    def __init__(self, id):
        self.id = id  # segment id
        self.regions = []  # regions in this segment
        self.locations = []  # locations in this segment


def analyze_dungeon(key_layout, world, player):
    key_layout.key_logic.reset()
    key_logic = key_layout.key_logic
    key_logic.new_logic = NewKeyLogic()
    for door in key_layout.proposal:
        if isinstance(door, tuple):
            key_logic.sm_doors[door[0]] = door[1]
            key_logic.sm_doors[door[1]] = door[0]
        else:
            if door.dest and door.type != DoorType.SpiralStairs:
                key_logic.sm_doors[door] = door.dest
                key_logic.sm_doors[door.dest] = door
            else:
                key_logic.sm_doors[door] = None

    key_logic.prize_location = dungeon_table[key_layout.sector.name].prize
    start_state = determine_big_key_logic(key_layout, world, player)
    if world.keyshuffle[player] == 'universal' and world.mode[player] != 'standard':
        return

    if world.key_logic_algorithm[player] == 'strict' or len(key_layout.proposal) > 8:
        determine_small_key_logic_fast(key_layout, start_state, world, player)

    else:
        # this is more granular and accurate - for lower key counts
        determine_small_key_logic_exhaustive(key_layout, world, player)


def determine_big_key_logic(key_layout, world, player):
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
            key_layout.key_logic.new_logic.bk_regions.add(region)
            for loc in region.locations:
                key_layout.key_logic.new_logic.bk_locations.add(loc)
                if important_location(loc, world, player):
                    big_chest_allowed_big_key = False
    if not big_chest_allowed_big_key:
        key_layout.key_logic.new_logic.bk_locations.update(find_big_chest_locations(key_layout.all_chest_locations))
    return start_state


def determine_small_key_logic_fast(key_layout, start_state, world, player):
    state = start_state.copy()
    key_value = len(key_layout.proposal)

    # expand the state without opening small key doors
    while len(state.big_doors) > 0:
        exp_door = state.big_doors.pop()
        open_a_door(exp_door.door, state, key_layout.flat_prop, world, player)
        expand_key_state(state, key_layout.flat_prop, world, player)

    # determine which regions & locations are locked by small keys
    new_logic = key_layout.key_logic.new_logic
    for region in key_layout.sector.regions:
        if not state.visited_at_all(region):
            new_logic.region_key_reqs[region] = key_value
            for loc in region.locations:
                new_logic.location_key_reqs[loc] = key_value
    possible_key_locs = set(key_layout.all_chest_locations).difference(set(new_logic.location_key_reqs))
    extras = calc_extras(key_value, key_layout.key_logic.dungeon, world, player)
    key_locs_sans_bk = possible_key_locs.difference(new_logic.bk_locations)
    if len(key_locs_sans_bk) < key_value + extras:
       new_logic.bk_restricted.update(new_logic.location_key_reqs.keys())
    elif len(possible_key_locs) == len(key_layout.proposal):
        new_logic.bk_restricted.update(possible_key_locs)


def calc_extras(amount_needed, dungeon_name, world, player):
    extras = 0
    if ('Hyrule Castle' in dungeon_name and world.mode[player] == 'standard'
            and world.doorShuffle[player] not in ['vanilla', 'basic']):
        extras = amount_needed // 5
    return extras


def determine_small_key_logic_exhaustive(key_layout, world, player):
    if key_layout.key_counters is None:
        key_layout.key_counters = create_key_counters(key_layout, world, player)
    counters = key_layout.key_counters
    key_logic = key_layout.key_logic
    new_logic = key_logic.new_logic
    seg_id_gen = letter_generator()
    visited_region_dict = {}
    code, root = next((code, key_counter) for code, key_counter in key_layout.key_counters.items()
                       if key_counter.used_keys == 0 and not key_counter.big_key_opened)
    queue: Deque[Tuple[str, KeyCounter, Optional[KeySphere]]] = deque([(code, root, None)])
    # build key segments
    while len(queue) > 0:
        code, key_counter, parent_sphere = queue.popleft()
        # child spheres?
        segment_regions = set(key_counter.state_ref.visited_orange + key_counter.state_ref.visited_blue)
        if parent_sphere:
            parent_regions = {region for seg_code in parent_sphere.segment_set for region in new_logic.segment_map[seg_code].regions}
            segment_regions.difference_update(parent_regions)
        seg_regions = frozenset(segment_regions)
        if len(seg_regions) <= 0:
            segment = None
        elif seg_regions in visited_region_dict:
            segment = visited_region_dict[seg_regions]
        else:
            segment = KeySegment(next(seg_id_gen))
            segment.locations = [loc for region in segment_regions for loc in region.locations]
            segment.regions = list(segment_regions)
            new_logic.segment_map[segment.id] = segment
            visited_region_dict[seg_regions] = segment

        if code in new_logic.sphere_map:
            sphere = new_logic.sphere_map[code]
        else:
            sphere = KeySphere(code)
            sphere.key_counter = key_counter
            segment_set = set() if segment is None else {segment.id}
            if parent_sphere:
                segment_set.update(parent_sphere.segment_set)
            sphere.segment_set = segment_set
            new_logic.sphere_map[code] = sphere
            new_logic.key_spheres[key_counter.used_keys].append(sphere)

        if parent_sphere:
            if not parent_sphere.key_counter.big_key_opened and key_counter.big_key_opened:
                parent_sphere.bk_child_sphere = sphere
            elif parent_sphere.key_counter.used_keys < key_counter.used_keys:
                parent_sphere.child_sphere.append(sphere)

        bk_checked = key_counter.big_key_opened
        open_door_set = set(key_counter.open_doors)
        for child_door in key_counter.child_doors:
            if not bk_checked and (child_door.bigKey or child_door.name in special_big_key_doors):
                bk_code = '1' + code[1:]
                if bk_code in counters:
                    bk_checked = True
                    queue.append((bk_code, counters[bk_code], sphere))
            elif child_door.smallKey:
                if child_door.dest in key_layout.flat_prop and child_door.type != DoorType.SpiralStairs:
                    child_open_set = open_door_set.union({child_door, child_door.dest})
                else:
                    child_open_set = open_door_set.union({child_door})
                small_code = segment_id(key_counter.big_key_opened, child_open_set, key_layout.flat_prop)
                if small_code in counters:
                    queue.append((small_code, counters[small_code], sphere))
            # prize doors? - ignore for now I guess

def segment_id(bk_flag, open_door_set, flat_proposal, use_prize=False, prize_flag=False):
    s_id = '1' if bk_flag else '0'
    for d in flat_proposal:
        s_id += '1' if d in open_door_set else '0'
    if use_prize:
        s_id += '1' if prize_flag else '0'
    return s_id


def letter_generator():
    current = ord('A')
    while current <= ord('Z'):
        yield chr(current)
        current += 1
    yield 'Z'





