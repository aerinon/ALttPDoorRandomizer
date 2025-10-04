from collections import deque, defaultdict
from typing import Optional, Deque, Tuple

from BaseClasses import DoorType, Door, CrystalBarrier
from DungeonGenerator import ExplorationState
from KeyDoorShuffle import KeyCounter
from KeyDoorShuffle import find_big_chest_locations, dungeon_table, open_a_door, important_location
from KeyDoorShuffle import find_outside_connection, prize_relevance, expand_key_state, create_key_counters
from Regions import dungeon_events
from dungeon.DungeonStitcherV2 import special_big_key_doors


class NewKeyLogic(object):

    def __init__(self):
        self.bk_regions = set()
        self.bk_locations = set()
        self.bk_restricted = set()

        self.fast_logic = False
        self.region_key_reqs = {}
        self.location_key_reqs = {}

        self.key_spheres = defaultdict(list)   # number of keys to a list of spheres accessible by the amt of keys
        self.sphere_map = {}
        self.door_minimums = []

        # Calculated or cached data
        self.relevant_regions = []
        self.relevant_locations = []
        self.can_reach_cache = {}
        self.crystal_switch_reachable = {}

    def get_relevant_regions_and_locations(self):
        if self.relevant_regions or self.relevant_locations:
            return self.relevant_regions, self.relevant_locations

        # fallback
        self._build_relevant_regions_and_locations()

        return self.relevant_regions, self.relevant_locations

    def _build_relevant_regions_and_locations(self):
        regions = set()
        locations = set()
        for sphere_list in self.key_spheres.values():
            for sphere in sphere_list:
                regions.update(sphere.regions)
                locations.update(sphere.locations)
        self.relevant_regions = list(regions)
        self.relevant_locations = list(locations)

    def build_cache_key(self, state, dungeon_logic, player):
        sk_name = dungeon_logic.small_key_name
        bk_name = dungeon_logic.bk_name
        # parameters from state
        smalls_in_hand = state.prog_items[sk_name, player]
        big_in_hand = True if state.prog_items[bk_name, player] > 0 else False

        # for relevant locations, where are small/big keys
        regions, locations = self.get_relevant_regions_and_locations()
        small_locations, big_location = [], None
        small_loc_name_set, big_loc_name = set(), None
        for loc in locations:
            if loc not in state.locations_checked and loc.item is not None:
                if loc.item.name == sk_name and loc.item.player == player:
                    small_locations.append(loc)
                    small_loc_name_set.add(loc.name)
                if loc.item.name == bk_name and loc.item.player == player:
                    big_location = loc
                    big_loc_name = loc.name
        small_loc_name_set = frozenset(small_loc_name_set)

        # placing a dungeon key or not - the self locking sphere
        placing_dungeon_key = False
        if state.placing_items:
            for item in state.placing_items:
                if item.name == sk_name and item.player == player:
                    placing_dungeon_key = True
                    break


        cache_key = (smalls_in_hand, big_in_hand, small_loc_name_set, big_loc_name, placing_dungeon_key)
        return cache_key, small_locations, big_location

    def can_reach(self, entrance, state, dungeon_logic, player):
        cache_key, small_locations, big_location = self.build_cache_key(state, dungeon_logic, player)
        # given the key, have we calculated this already?
        if cache_key not in self.can_reach_cache:
            self.calculate_reachability(cache_key, small_locations, big_location)
        reachable_regions, reachable_locations = self.can_reach_cache[cache_key]
        # the entrances connected region must be in the reachable regions
        # and it must not be a locked door or they must have at least one key to waste
        # this may not be sufficient consider vanilla GT
        return entrance.connected_region in reachable_regions and (entrance.name not in self.door_minimums or cache_key[0] > 0)

    def can_reach_location(self, location, state, dungeon_logic, player):
        cache_key, small_locations, big_location = self.build_cache_key(state, dungeon_logic, player)
        # given the key, have we calculated this already?
        if cache_key not in self.can_reach_cache:
            self.calculate_reachability(cache_key, small_locations, big_location)
        reachable_regions, reachable_locations = self.can_reach_cache[cache_key]
        return location in reachable_locations

    # notes, smalls_in_hand can include some of the small_locations, small_locations may have been checked already - this affects cache_key
    # perhaps we should always start at the root sphere, skipping ahead can be problematic if you have enough keys, but not the big key to reach those later spheres
    def calculate_reachability(self, cache_key, small_locations, big_location):
        smalls_in_hand, big_in_hand, small_loc_name_set, big_loc_name, placing_dungeon_key = cache_key
        sphere_list = self.key_spheres[0] # start at root sphere
        # filter to those applicable for current big key status
        sphere_list = [s for s in sphere_list if s.key_counter.big_key_opened == big_in_hand
                       or (big_in_hand and not s.bk_child_sphere and not s.key_counter.big_key_opened)]
        terminal_spheres = []
        visited_spheres = {(s, big_in_hand) for s in  sphere_list}
        queue = deque([(s, smalls_in_hand, big_in_hand, small_locations) for s in sphere_list])
        while len(queue) > 0:
            sphere, unspent_keys, current_big, small_locations_left = queue.popleft()
            accessible_locations = sphere.get_accessible_locations(self)
            # check if big key is in an accessible location
            big_key_grabbable = not current_big and big_location is not None and big_location in accessible_locations
            # check if we can traverse to a bk_child_sphere
            big_key_openable = current_big and sphere.bk_child_sphere is not None
            if big_key_grabbable or big_key_openable:
                next_sphere = sphere.bk_child_sphere if sphere.bk_child_sphere else sphere
                if (next_sphere, True) not in visited_spheres:
                    visited_spheres.add((next_sphere, True))
                    queue.append((next_sphere, unspent_keys, True, small_locations_left))
                continue  # even if the sphere is visited, we don't continue processing it
            # check if there are small keys in accessible locations
            # need to account for keys found in previous iteration to not double count keys
            smalls_to_grab = [loc for loc in small_locations_left if loc in accessible_locations]
            can_spend_key = unspent_keys + len(smalls_to_grab) > 0
            if can_spend_key and sphere.child_sphere:
                next_sphere_list = [n for n in sphere.child_sphere
                                    if (n.key_counter.big_key_opened == current_big
                                    or (current_big and not sphere.bk_child_sphere and not n.key_counter.big_key_opened))
                                    and (n, current_big) not in visited_spheres]
                if next_sphere_list:
                    keys_gained = len(smalls_to_grab)
                    keys_spent = 1 if (unspent_keys > 0 or keys_gained > 0) else 0
                    next_unspent_keys = unspent_keys + keys_gained - keys_spent
                    next_small_locs = [loc for loc in small_locations_left if loc not in smalls_to_grab]
                    for next_sphere in next_sphere_list:
                        visited_spheres.add((next_sphere, current_big))
                        queue.append((next_sphere, next_unspent_keys, current_big, next_small_locs))
                continue  # even if no spheres are added, we don't continue processing it

            # if we can't spend a key, possible to place in a self-locking sphere?
            if placing_dungeon_key and unspent_keys == 0:  # we can't do this twice so only we have exactly zero keys
                next_unspent_keys = unspent_keys - 1  # we are "spending" a key we don't have here (can't open up more doors with it)
                valid_spheres = []
                for next_sphere in sphere.self_locking_child_spheres:
                    # Skip if already visited
                    if (next_sphere, current_big) in visited_spheres:
                        continue

                    # Get the unique self-locking location
                    self_locking_locations = next_sphere.locations.difference(sphere.locations)
                    if len(self_locking_locations) != 1:
                        continue

                    self_locking_location = next(iter(self_locking_locations))
                    # Skip if non-small key item has been placed
                    if self_locking_location.item is not None and not self_locking_location.item.smallkey:
                        continue

                    valid_spheres.append(next_sphere)
                if valid_spheres:
                    for next_sphere in valid_spheres:
                        visited_spheres.add((next_sphere, current_big))
                        queue.append((next_sphere, next_unspent_keys, current_big, small_locations_left))
                    continue

            # can't advance - terminal
            terminal_spheres.append(sphere)
        if not terminal_spheres:
            raise Exception('No terminal spheres found - logic failure in NewKeyLogic')

        # collect all reachable regions and locations
        reachable_regions = set(terminal_spheres[0].regions)
        reachable_locations = set(terminal_spheres[0].locations)
        for sphere in terminal_spheres[1:]:
            reachable_regions.intersection_update(sphere.regions)
            reachable_locations.intersection_update(sphere.locations)

        # cache the result
        self.can_reach_cache[cache_key] = (reachable_regions, reachable_locations)

    # analyze crystal switch bypasses
    def detect_crystal_switch_bypass(self, key_layout, world, player):
        # Detect cases where crystal switches can be reached to bypass blue barriers.
        for key_count in range(len(key_layout.proposal) + 1):
            for big_key_state in [False, True]:
                self._analyze_crystal_reachability(key_count, big_key_state, key_layout, world, player)

    # Analyze if crystal switches can bypass blue barriers for a given key count.
    def _analyze_crystal_reachability(self, key_count, big_key_state, key_layout, world, player):

        # Build cache key for this scenario
        crystal_cache_key = (key_count, big_key_state)

        # Get normally reachable regions with this key count
        normal_regions = self._get_reachable_regions_with_keys(key_count, big_key_state)

        # Find crystal switches in reachable regions
        crystal_switches = self._find_crystal_switches_in_regions(normal_regions)

        # if there are cs regions, then there is nothing left to check, crystal switch is reachable
        # or if there are no blue barriers in these regions, then no need to check further
        if crystal_switches or not self._any_blue_barrier_entrances(normal_regions):
            return

        # Find blue barrier islands not currently reachable
        blue_islands = self._find_blue_barrier_islands(normal_regions)

        if blue_islands:
            # todo: Mark these islands as potentially reachable via crystal switch
            self.crystal_switch_reachable[crystal_cache_key] = blue_islands

    # Get regions reachable with a specific number of keys and big key state.
    def _get_reachable_regions_with_keys(self, key_count, big_key_state):
        # Build a cache key similar to normal reachability
        cache_key = (key_count, big_key_state, frozenset(), None, False)

        # Use existing reachability logic but with empty small locations
        self.calculate_reachability(cache_key, [], None)

        reachable_regions, _ = self.can_reach_cache[cache_key]
        return reachable_regions

    @staticmethod
    def _find_crystal_switches_in_regions(regions):
        crystal_switches = []
        for region in regions:
            if region.crystal_switch:
                crystal_switches.append(region)
        return crystal_switches

    @staticmethod
    def _any_blue_barrier_entrances(regions):
        for region in regions:
            if any(ent.door and ent.door.crystal == CrystalBarrier.Blue and ent.parent_region in regions
                   for ent in region.entrances):
                return True
        return False

    # Find regions that are only accessible through blue barriers.
    @staticmethod
    def _find_blue_barrier_islands(reachable_regions):
        blue_islands = [] # list of tuple, the first element is a list of regions, the second is a list of entrances
        candidate_islands = [] # list of tuple, the first element is a list of regions, the second is a list of entrances
        unknown_region_map = defaultdict(list)  # dict of regions list of dependent islands
        island_region_map = {}  # dict of region to island it belongs to
        non_islands_regions = set()
        # for repeatability for now, could test by randomization
        queue = deque(sorted(list(reachable_regions), key=lambda r: r.name))

        while len(queue) > 0:
            region = queue.popleft()
            possible_entrances = [ent for ent in region.entrances if ent.parent_region in reachable_regions]
            # first check if this connects to an overworld region
            if any(ent.parent_region.type.is_overworld for ent in region.entrances):
                non_islands_regions.add(region)
                if region in unknown_region_map:
                    NewKeyLogic.clean_up_islands(candidate_islands, island_region_map, non_islands_regions, region, unknown_region_map)
                continue
            blue_barriers = [ent for ent in possible_entrances if ent.door and ent.door.crystal == CrystalBarrier.Blue]
            connected_regions = [ent.parent_region for ent in possible_entrances if ent not in blue_barriers]  # non-blue
            if any(r in non_islands_regions for r in connected_regions):
                non_islands_regions.add(region)
                if region in unknown_region_map:
                    NewKeyLogic.clean_up_islands(candidate_islands, island_region_map, non_islands_regions, region, unknown_region_map)
                continue
            if len(connected_regions) == 0 and len(blue_barriers) > 0:
                # definitely a blue barrier island region
                new_island = BlueIsland([region], blue_barriers, connected_regions)
                blue_islands.append(new_island)
                continue
            # unknown at this time, could be a blue barrier island or not
            # find all potential islands that could connect to this region
            islands_to_merge = list(unknown_region_map[region])
            more_to_merge = [island_region_map[r] for r in connected_regions if r in island_region_map and island_region_map[r] not in islands_to_merge]
            if more_to_merge:
                islands_to_merge.extend(more_to_merge)
            if not islands_to_merge:
                # if no match create new island
                new_island = BlueIsland([region], blue_barriers, connected_regions)
                candidate_islands.append(new_island)
                for r in connected_regions:
                    unknown_region_map[r].append(new_island)
                island_region_map[region] = new_island
            else:
                del unknown_region_map[region]
                region_set = {region}
                barrier_set = set(blue_barriers)
                unknown_set = set(connected_regions)
                for island in islands_to_merge:
                    region_set.update(island.regions)
                    unknown_set.difference_update(island.regions)
                    barrier_set.update(island.blue_barriers)
                    unknown_refs = [r for r in island.unknown_regions if r != region and r not in islands_to_merge]
                    unknown_set.update(unknown_refs)
                    candidate_islands.remove(island)
                    for r in unknown_refs:
                        unknown_region_map[r].remove(island)
                new_island = BlueIsland(list(region_set), list(barrier_set), list(unknown_set))
                candidate_islands.append(new_island)
                for r in region_set:
                    island_region_map[r] = new_island
                for r in unknown_set:
                    unknown_region_map[r].append(new_island)

        blue_islands.extend(candidate_islands) # what is left must be real islands
        return blue_islands

    @staticmethod
    def clean_up_islands(candidate_islands, island_region_map, non_islands_regions, region, unknown_region_map):
        for island in unknown_region_map[region]:
            non_islands_regions.update(island.regions)
            for r in island.regions:
                del island_region_map[r]
            for r in island.unknown_regions:
                unknown_region_map[r].remove(island)
            candidate_islands.remove(island)  # island is invalid


class BlueIsland(object):

    def __init__(self, regions, blue_barriers, open_list):
        self.regions = regions
        self.blue_barriers = blue_barriers
        self.unknown_regions = open_list


class KeySphere(object):

    def __init__(self, code):
        self.code = code
        self.regions = set()
        self.locations = set()
        self.segment_set = set()  # segments that make up this sphere, their codes
        self.key_counter = None
        self.child_sphere = []
        self.bk_child_sphere = None

        self.self_locking_child_spheres = []

        self.accessible_locations = None

    def get_accessible_locations(self, key_logic):
        if self.accessible_locations is None:
            self.accessible_locations = list(self.locations)
        return self.accessible_locations


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

        # Analyze crystal switch bypass opportunities after exhaustive key spheres are built
        key_logic.new_logic.detect_crystal_switch_bypass(key_layout, world, player)


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
    new_logic.fast_logic = True
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
    new_logic.door_minimums = [door.name for door in key_layout.flat_prop]
    complete_region_set = set()
    complete_location_set = set()
    self_locking_doors = set()

    code, root = next((code, key_counter) for code, key_counter in key_layout.key_counters.items()
                       if key_counter.used_keys == 0 and not key_counter.big_key_opened)
    queue: Deque[Tuple[str, KeyCounter, Optional[KeySphere]]] = deque([(code, root, None)])
    while len(queue) > 0:
        code, key_counter, parent_sphere = queue.popleft()

        if code in new_logic.sphere_map:
            sphere = new_logic.sphere_map[code]
            if world.accessibility[player] != 'locations':
                self_locking_doors.update(detect_self_locks(sphere, parent_sphere, key_layout))
        else:
            sphere = KeySphere(code)
            sphere.key_counter = key_counter

            sphere_regions = set(key_counter.state_ref.visited_orange + key_counter.state_ref.visited_blue)
            sphere.regions = sphere_regions
            sphere.locations = {loc for region in sphere_regions for loc in region.locations}

            new_logic.sphere_map[code] = sphere
            new_logic.key_spheres[key_counter.used_keys].append(sphere)
            complete_region_set.update(sphere_regions)
            complete_location_set.update(sphere.locations)

            if world.accessibility[player] != 'locations':
                self_locking_doors.update(detect_self_locks(sphere, parent_sphere, key_layout))

            # bk_restricted zones, obviously only important if both big and small keys aren't shuffled
            possible_key_locs = set(sphere.locations)
            potential_doors = 0
            for door_pair in key_layout.proposal:
                if isinstance(door_pair, tuple):
                    if (door_pair[0] in key_counter.child_doors or door_pair[1] in key_counter.child_doors
                            or door_pair[0] in key_counter.open_doors or door_pair[1] in key_counter.open_doors):
                        potential_doors += 1
                elif door_pair in key_counter.child_doors or door_pair in key_counter.open_doors:
                    potential_doors += 1
            extras = calc_extras(potential_doors, key_layout.key_logic.dungeon, world, player)
            key_locs_sans_bk = possible_key_locs.difference(new_logic.bk_locations)
            big_chests_in_range = len(possible_key_locs.intersection(new_logic.bk_locations)) > 0
            big_doors_accessible = any(d for d in key_counter.open_doors if d.bigKey or d.name in special_big_key_doors)
            if not big_doors_accessible and len(key_locs_sans_bk) + big_chests_in_range <= potential_doors + extras:
                new_logic.bk_restricted.update(sphere.locations)

        skip = False
        if parent_sphere:
            if not parent_sphere.key_counter.big_key_opened and key_counter.big_key_opened:
                parent_sphere.bk_child_sphere = sphere
            elif parent_sphere.key_counter.used_keys < key_counter.used_keys:
                if sphere in parent_sphere.child_sphere:  # unsure if I should de-dudup logically equivalent spheres here or not
                    skip = True
                else:
                    parent_sphere.child_sphere.append(sphere)

        if skip:
            continue
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
                small_code = sphere_id(key_counter.big_key_opened, child_open_set, key_layout.flat_prop)
                if small_code in counters:
                    queue.append((small_code, counters[small_code], sphere))
            # prize doors? - ignore for now I guess

    new_logic.relevant_regions = list(complete_region_set)
    new_logic.relevant_locations = list(complete_location_set)
    new_logic.door_minimums = [d for d in new_logic.door_minimums if all(d != self_locking.name for self_locking in self_locking_doors)]


def detect_self_locks(sphere, parent_sphere, key_layout):
    self_locking_doors = []
    # detect self-locking spheres
    if not parent_sphere:
        return self_locking_doors
    child_door_diff = [d for d in sphere.key_counter.child_doors if d not in parent_sphere.key_counter.child_doors]
    if len(child_door_diff) == 0:
        child_only_locs = sphere.locations.difference(parent_sphere.locations)
        other_locations = set(sphere.key_counter.other_locations.keys()).difference(parent_sphere.key_counter.other_locations.keys())
        if len(other_locations) > 0:
            # if the child sphere has other locations, it can't be self-locking
            return self_locking_doors
        child_only_locs = {loc for loc in child_only_locs if loc.forced_item is None}
        if len(child_only_locs) == 1:
            # must only be one door small key door difference
            door_diff = [s for s in sphere.key_counter.open_doors if s not in parent_sphere.key_counter.open_doors]
            door_diff_cnt = sum(1 for dp in key_layout.proposal
                                if (isinstance(dp, tuple) and (dp[0] in door_diff or dp[1] in door_diff)
                                    or (isinstance(dp, Door) and dp in door_diff)))
            if door_diff_cnt == 1 and sphere not in parent_sphere.self_locking_child_spheres:
                parent_sphere.self_locking_child_spheres.append(sphere)
                self_locking_doors.extend(door_diff)
    return self_locking_doors


def sphere_id(bk_flag, open_door_set, flat_proposal, use_prize=False, prize_flag=False):
    s_id = '1' if bk_flag else '0'
    for d in flat_proposal:
        s_id += '1' if d in open_door_set else '0'
    if use_prize:
        s_id += '1' if prize_flag else '0'
    return s_id





