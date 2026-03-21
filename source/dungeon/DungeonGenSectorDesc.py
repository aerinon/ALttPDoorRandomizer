from collections import defaultdict, deque, Counter

from BaseClasses import Direction, RegionType, CrystalBarrier, DoorType, flooded_keys
from BaseClasses import hook_from_door
from Regions import dungeon_events, flooded_keys_reverse
from Utils import append_to_yaml, clear_file
from source.dungeon.DungeonGenerationCommon import hanger_from_door
from source.dungeon.DungeonGenerationCommon import GenerationException, is_boss_trap
from source.dungeon.DungeonStitcher import ExplorableDoor


def create_sector_descriptors(sector_list, world, player):
    clear_file(['data', 'gen', 'proposed_test.yaml'])
    v_trap_flag = world.trap_door_mode[player] == 'vanilla'
    # custom intensity could be here
    for sector in sector_list:
        descript = SectorDescriptor(sector, v_trap_flag)
        sector.descriptor = descript
        append_to_yaml(['data', 'gen', 'proposed_test.yaml'], descript.to_yaml())


class SectorDescriptor:
    def __init__(self, sector, v_trap_flag):
        self.sector = sector
        sector.sector_key()
        self.degree = len(sector.outstanding_doors)
        self.name = min(sector.region_set(), key=len)

        # this should include
        #   number of outstanding doors by direction (n1s2e4w5sp3)
        #   special mods like:
        #       _b (blue crystal req, no switch)
        #       _o (orange crystal req, no switch)
        #       _p (path through sector restricted)
        #   consistent suffix to help uniquely identify

        self.reachability = defaultdict(list)
        self.blue_reachability = defaultdict(list)
        self.orange_reachability = defaultdict(list)
        self.state_cache = {}
        self.crystal_switch_doors = []
        self.constraints = {}  # disjunction of optional constraints, indexed by Hooks consumed
        self.parity_id = ''
        self.init_parity_id()

        self.dead_end = False
        self.must_enter_reqs = []
        self.special_reqs = []
        self.crystal_reqs = []
        self.is_neutral = False

        self.shape_construct = {}
        self.analyze_sector(v_trap_flag)

        self.joined_constraints = []
        # self.joined_constraints = [self.constraints]

    def init_parity_id(self):
        dir_map = defaultdict(int)
        for door in self.sector.outstanding_doors:
            dir_map[door.direction] += 1
        for ind, keys in {'n': [Direction.North], 's': [Direction.South], 'e': [Direction.East],
                          'w': [Direction.West], 'sp': [Direction.Up, Direction.Down]}.items():
            amt = sum(dir_map[x] for x in keys)
            if amt:
                self.parity_id += f'{ind}{amt}'

    def analyze_sector(self, v_trap_flag):
        self.reachability.clear()
        skip_doors = set()
        if self.sector.portals and any(not p.destination for p in self.sector.portals):
            for p in self.sector.portals:
                if not p.destination:
                    state = SimpleExplorationState(v_trap_flag)
                    state.extend_reachable_state(p.door, cs_override=CrystalBarrier.Orange)
                    self.state_cache[p.door] = state
                    for explorable in state.unattached_doors:
                        if explorable.door == DoorType.Logical or explorable.door not in self.sector.outstanding_doors:
                                continue
                        self.reachability[p.door].append((explorable.door, explorable.crystal, explorable.flag))
                    # self.reachability[None].append((p.door, CrystalBarrier.Orange, CrystalBarrier.Null))
                    skip_doors.add(p.door)
            # todo: dependent portals
        # which outstanding doors are reachable from which outstanding doors
        for door in self.sector.outstanding_doors:
            # these types you cannot enter from
            if door.type in [DoorType.Warp, DoorType.Hole] or door in skip_doors:
                continue
            state = SimpleExplorationState(v_trap_flag)
            state.extend_reachable_state(door)
            if state.visited_map[door.entrance.parent_region][0] == CrystalBarrier.Either:
                self.crystal_switch_doors.append(door)
            else:
                self.blue_reachability[door].extend([region for region, crystal in state.visited_map.items() if crystal[0] in [CrystalBarrier.Null, CrystalBarrier.Blue, CrystalBarrier.Both]])
                self.orange_reachability[door].extend([region for region, crystal in state.visited_map.items() if crystal[0] in [CrystalBarrier.Null, CrystalBarrier.Orange, CrystalBarrier.Both]])
            for explorable in state.unattached_doors:
                # skip sanc mirror route in this calc and doors reached via overworld
                if explorable.door == DoorType.Logical or explorable.door not in self.sector.outstanding_doors:
                    continue
                # crystal = self.resolve_crystal_prop(explorable.crystal, state.visited_map[explorable.door.entrance.parent_region])
                self.reachability[door].append((explorable.door, explorable.crystal, explorable.flag))
            self.state_cache[door] = state

        for door, reach_list in self.reachability.items():
            ctr = Counter([(hook_from_door(d), number, flag) for d, number, flag in reach_list if hook_from_door(d) is not None])
            valid_portal = door.portalAble and not (door.blocked or is_boss_trap(door))
            has_portal = 'test' if self.sector.portals else 'no'
            if has_portal == 'test':
                has_portal = 'src' if all(not p.destination for p in self.sector.portals) else 'dest'
            self.shape_construct[door] = (valid_portal,has_portal) + tuple(sorted((ctr.items())))

        self.classify()

    def classify(self):
        total_needed = len(self.sector.outstanding_doors)
        unreached = set(self.sector.outstanding_doors)
        if total_needed == 1 and not self.sector.portals:
            self.dead_end = True
        else: #elif not self.sector.portals or all(p.destination for p in self.sector.portals):
            if 'Ice Cross Left' in self.sector.r_name_set and any('Ice Cross ' in d.name for d in self.reachability):
                specials = []
                for source, dest_list in self.reachability.items():
                    if any('Ice Cross ' in d.name for d, c, f in dest_list):
                        specials.append(source)
                self.special_reqs.append(tuple(specials))
            elif any(len(reach_list) < total_needed for source, reach_list in self.reachability.items()):
                # there is no full access
                reversed_reachability = defaultdict(list)
                for source, reach_list in self.reachability.items():
                    for reach in reach_list:
                        reversed_reachability[reach[0]].append(source)
                must_access = [dest for dest, source_list in reversed_reachability.items() if len(source_list) == 1]
                reached = set()
                for dest in must_access:
                    self.must_enter_reqs.append(dest)
                    reached.update([d for d, c, f in self.reachability[dest]])
                unreached.difference_update(reached)
                if len(unreached) > 0:
                    covers_all = []
                    for source, dest_list in self.reachability.items():
                        door_set = set(d for d, c, f in dest_list if d in unreached)
                        if len(door_set) == len(unreached):
                            covers_all.append(source)
                    if not covers_all:
                        raise GenerationException("Some edge case where you need to separate door to cover all: " + self.sector)
                    if len(covers_all) == 1:
                        d = next(iter(covers_all))
                        self.must_enter_reqs.insert(0, d)
                    else:
                        self.must_enter_reqs.insert(0, tuple(covers_all))

        if all(len(reach_list) == total_needed for source, reach_list in self.reachability.items()):
            if self.is_sector_neutral():
                self.is_neutral = True
        if all(portal.destination for portal in self.sector.portals):
            self.classify_crystals_new()

    def classify_crystals_new(self):
        blue_region_set = {r for d, state in self.state_cache.items() for r, reqs in state.visited_map.items() if reqs[1] == CrystalBarrier.Blue}
        if blue_region_set:
            reqs = {}
            for region in blue_region_set:
                need_color, can_reach = set(), set()
                for d, state in self.state_cache.items():
                    if region in state.visited_map:
                        (need_color if state.visited_map[region][1] != CrystalBarrier.Null else can_reach).add(d)
                reqs[region] = (need_color, can_reach)
            reduced_reqs = self.reduce_region_requirements(reqs)
            region_reqs = self.reduce_again(reduced_reqs)
            if len(region_reqs) > 0:
                constraint = CrystalConstraint()
                if len(region_reqs) > 1 and all(len(opt[1]) == 0 for opt in region_reqs.values()):
                    constraint.type = 'all'
                for regions, option in region_reqs.items():
                    if option[0]:
                        constraint.must_have_color_access.append(tuple(option[0]))
                    if option[1]:
                        constraint.must_enter_reqs.append(tuple(option[1]))
                self.crystal_reqs.append(constraint)

        orange_region_set = {r for d, state in self.state_cache.items() for r, reqs in state.visited_map.items() if reqs[1] == CrystalBarrier.Orange}
        if orange_region_set:
            reqs = {}
            for region in orange_region_set:
                need_color, can_reach = set(), set()
                for d, state in self.state_cache.items():
                    if region in state.visited_map:
                        (need_color if state.visited_map[region][1] != CrystalBarrier.Null else can_reach).add(d)
                reqs[region] = (need_color, can_reach)
            reduced_reqs = self.reduce_region_requirements(reqs)
            region_reqs = self.reduce_again(reduced_reqs)
            if len(region_reqs) > 0:
                constraint = CrystalConstraint()
                constraint.color = 'orange'
                if len(region_reqs) > 1 and all(len(opt[1]) == 0 for opt in region_reqs.values()):
                    constraint.type = 'all'
                for regions, option in region_reqs.items():
                    if option[0]:
                        constraint.must_have_color_access.append(tuple(option[0]))
                    if option[1]:
                        constraint.must_enter_reqs.append(tuple(option[1]))
                self.crystal_reqs.append(constraint)


    def reduce_region_requirements(self, reqs):
        region_reqs = {}
        for need, options in reqs.items():
            need_color, can_reach = options
            is_subset = False
            for need2, options2 in region_reqs.items():
                need_color2, can_reach2 = options2
                if set(need_color) <= set(need_color2) and set(can_reach) <= set(can_reach2):
                    is_subset = True
                    new_key = (need2 + (need,) if isinstance(need2, tuple) else (need2, need))
                    region_reqs[new_key] = options
                    del region_reqs[need2]
                    break
                if set(need_color2) <= set(need_color) and set(can_reach2) <= set(can_reach):
                    is_subset = True
                    break
            if not is_subset:
                region_reqs[need] = options
        region_reqs = {k: v for k, v in region_reqs.items() if len(v) > 0}
        return region_reqs

    def reduce_again(self, reqs):
        if all(len(opt[1]) == 0 for opt in reqs.values()):
            return reqs
        region_reqs = {}
        for need, options in reqs.items():
            need_color, can_reach = options
            is_subset = False
            for need2, options2 in region_reqs.items():
                need_color2, can_reach2 = options2
                if can_reach.union(can_reach2) <= need_color.union(need_color2):
                    is_subset = True
                    new_key = (need2 + (need,) if isinstance(need2, tuple) else (need2, need))
                    region_reqs[new_key] = (need_color.union(need_color2), set())
                    del region_reqs[need2]
                    break
            if not is_subset:
                region_reqs[need] = options
        region_reqs = {k: v for k, v in region_reqs.items() if len(v) > 0}
        return region_reqs


    def classify_crystals_old_option(self):
        # check for crystal options
        blue_crystal_needed = {ext.parent_region for r in self.sector.regions for ext in r.exits if ext.door and ext.door.crystal == CrystalBarrier.Blue}
        if blue_crystal_needed:
            doors_to_check = []
            if self.must_enter_reqs:
                for req in self.must_enter_reqs:
                    if not isinstance(req, tuple):
                        req = (req,)
                    if any(d not in self.crystal_switch_doors for d in req):
                        doors_to_check.append(req)
            else:
                doors_to_check.append(tuple(self.sector.outstanding_doors))

            crystal_needs = [tuple(d for d in s if d not in self.crystal_switch_doors) for s in doors_to_check
                             if any(d not in self.crystal_switch_doors for d in s)]
            honorary_cs_doors = [d for s in doors_to_check for d in s if
                                 all(r in self.state_cache[d].visited_map
                                     and self.state_cache[d].visited_map[r][0] in {CrystalBarrier.Either, CrystalBarrier.Both} for r in blue_crystal_needed)]
            if crystal_needs:
                constraint = CrystalConstraint()
                constraint.must_enter_reqs = [tuple(d for d in s if d in self.crystal_switch_doors or d in honorary_cs_doors) for s in doors_to_check
                                              if any(d in self.crystal_switch_doors or d in honorary_cs_doors for d in s)]

                reqs = {r: [k for k, v in self.blue_reachability.items() if r in v and k not in honorary_cs_doors] for r in blue_crystal_needed}
                reqs = {k: v for k, v in reqs.items() if len(v) > 0}
                region_reqs = {}
                for need, options in reqs.items():
                    is_subset = False
                    for need2, options2 in region_reqs.items():
                        if set(options) <= set(options2):
                            is_subset = True
                            new_key = (need2 + (need,) if isinstance(need2, tuple) else (need2, need))
                            region_reqs[new_key] = options2
                            del region_reqs[need2]
                            break
                    if not is_subset:
                        region_reqs[need] = options
                region_reqs = {k: v for k, v in region_reqs.items() if len(v) > 0}

                if len(region_reqs) > 0:  # Hera pits doesn't need a constraint
                    if len(region_reqs) > 1 and len(constraint.must_enter_reqs) == 0:
                        constraint.type = 'all'
                    for regions, doors in region_reqs.items():
                        constraint.must_have_color_access.append(tuple(doors))
                    self.crystal_reqs.append(constraint)

        orange_crystal_needed = {ext.parent_region for r in self.sector.regions for ext in r.exits
                                 if ext.door and ext.door.crystal == CrystalBarrier.Orange and ext.door.name != 'Sanctuary Mirror Route'}
        if orange_crystal_needed:
            doors_to_check = []
            if self.must_enter_reqs:
                for req in self.must_enter_reqs:
                    if not isinstance(req, tuple):
                        req = (req,)
                    if any(d not in self.crystal_switch_doors for d in req):
                        doors_to_check.append(req)
            else:
                doors_to_check.append(tuple(self.sector.outstanding_doors))
            crystal_needs = [tuple(d for d in s if d not in self.crystal_switch_doors) for s in doors_to_check
                             if any(d not in self.crystal_switch_doors for d in s)]
            honorary_cs_doors = [d for s in doors_to_check for d in s if
                                 all(r in self.state_cache[d].visited_map
                                     and self.state_cache[d].visited_map[r][0] in {CrystalBarrier.Either, CrystalBarrier.Both} for r in orange_crystal_needed)]
            if crystal_needs:
                constraint = CrystalConstraint()
                constraint.color = 'orange'
                constraint.must_enter_reqs = [tuple(d for d in s if d in self.crystal_switch_doors or d in honorary_cs_doors) for s in doors_to_check
                                              if any(d in self.crystal_switch_doors or d in honorary_cs_doors for d in s)]
                reqs = {r: [k for k, v in self.orange_reachability.items() if r in v and k not in honorary_cs_doors] for r in orange_crystal_needed}
                reqs = {k: v for k, v in reqs.items() if len(v) > 0}
                region_reqs = {}
                for need, options in reqs.items():
                    is_subset = False
                    for need2, options2 in region_reqs.items():
                        if set(options) <= set(options2):
                            is_subset = True
                            new_key = (need2 + (need,) if isinstance(need2, tuple) else (need2, need))
                            region_reqs[new_key] = options2
                            del region_reqs[need2]
                            break
                    if not is_subset:
                        region_reqs[need] = options
                region_reqs = {k: v for k, v in region_reqs.items() if len(v) > 0}

                if len(region_reqs) > 0:  # Hera pits doesn't need a constraint
                    if len(region_reqs) > 1 and len(constraint.must_enter_reqs) == 0:
                        constraint.type = 'all'
                    for regions, doors in region_reqs.items():
                        constraint.must_have_color_access.append(tuple(doors))
                    self.crystal_reqs.append(constraint)



    def is_sector_neutral(self):
        if len(self.sector.outstanding_doors) == 2:
            d1, d2 = self.sector.outstanding_doors[0], self.sector.outstanding_doors[1]
            if hanger_from_door(d1) == hook_from_door(d2):
                reachability = self.reachability
                if len(reachability[d1]) == 2 and len(reachability[d2]) == 2:
                    return (all(access[1] == CrystalBarrier.Null for access in reachability[d1]) and
                            all(access[1] == CrystalBarrier.Null for access in reachability[d2]))
        return False

    def __str__(self):
        return f'{self.name}:{self.parity_id}'

    def to_yaml(self):
        return {self.sector.sector_key(): [[c.to_yaml() for c in cm.values()] for cm in self.joined_constraints]}


class CrystalConstraint:
    def __init__(self):
        self.type = 'any'  # vs all
        self.must_enter_reqs = []
        self.must_have_color_access = []
        self.color = 'blue'  # vs orange (unsure if needed to support)

    def constains_door(self, door_to_check):
        for req in self.must_enter_reqs:
            if door_to_check in req:
                return True
        for req in self.must_have_color_access:
            if door_to_check in req:
                return True
        return False

    def contains_color_access(self, door_to_check):
        for req in self.must_have_color_access:
            if door_to_check in req:
                return True
        return False


class SectorConstraint:
    def __init__(self, hanger=None, crystal_needed=False, join_method=None, children=None):
        self.join_method = join_method  # either conjoint or disjoint or none
        self.children = children

        self.hanger = hanger  # door Hook(s) consumed - could be a frozenset (hopefully we never need to move to Counter)
        self.candidate_hangers = set()  # door options
        self.crystal_needed = crystal_needed  # is a crystal needed or not
        self.benefits = defaultdict(int)  # Hook -> number of type reached
        self.accessible_doors = {}  # dict of doors to crystal state
        self.assumed_connections = {} # dict of paired doors, key leads to value (reverse is true in non-decoupled)

    def benefit_count(self):
        if self.join_method:
            if self.join_method == 'conjoint':
                return sum(x.benefit_count() for x in self.children)
            elif self.join_method == 'disjoint':
                return max(x.benefit_count() for x in self.children)
        return sum(y for x, y in self.benefits.items())

    def to_yaml(self):
        if self.join_method:
            return {'children': [x.to_yaml() for x in self.children],
                    'join': 'and' if self.join_method == 'conjoint' else 'or'}
        return {
            'cost': self.hanger.name if self.hanger else 'None',
            'candidates': [(x.name if x else 'Entrance') for x in self.candidate_hangers],
            'crystal': self.crystal_needed,
            'benefits': {x.name: y for x, y in self.benefits.items() if y > 0},
            'reachable': {d.name: crystal_map[c] for d, c in self.accessible_doors.items()},
            'assumptions': {k.name: v.name for k, v in self.assumed_connections.items()}
        }

    def combined_key(self):
        if self.join_method:
            ctr = Counter()
            ctr.update(x.combined_key() for x in self.children)
            return frozenset(ctr.items())
        else:
            return self.hanger


crystal_map = {
    CrystalBarrier.Null: 'None',
    CrystalBarrier.Orange: 'Orange',
    CrystalBarrier.Blue: 'Blue',
    CrystalBarrier.Either: 'Switch',
    CrystalBarrier.Both: 'Both'
}


class SimpleExplorationState:
    def __init__(self, respect_traps):
        self.respect_traps = respect_traps

        self.avail_doors = []
        self.unattached_doors = []
        self.event_doors = []

        self.visited_map = {}
        self.events = set()
        self.crystal = CrystalBarrier.Null
        self.crystal_forced = CrystalBarrier.Null

        self.found_locations = []

    def extend_reachable_state(self, start_door, cs_override=None):
        start_region = start_door.entrance.parent_region
        self.append_door_to_list(start_door, self.unattached_doors, cs_override=cs_override)  # always counts for oneself
        self.visit_region(start_region)
        while len(self.avail_doors) > 0:
            explorable_door = self.next_avail_door()
            connect_region = explorable_door.door.entrance.connected_region
            self.crystal = explorable_door.crystal
            self.crystal_forced = explorable_door.flag
            # going to exclude outdoors from this exploration
            if connect_region is not None and not self.visited(connect_region) and connect_region.type == RegionType.Dungeon:
                self.visit_region(connect_region)

    def next_avail_door(self):
        exp_door = self.avail_doors.pop(0)
        self.crystal = exp_door.crystal
        return exp_door

    def visit_region(self, region):
        if region.crystal_switch:
            self.crystal = CrystalBarrier.Either
        if region not in self.visited_map or self.crystal == CrystalBarrier.Either:
            self.visited_map[region] = self.crystal, self.crystal_forced
        elif self.crystal == CrystalBarrier.Null or self.visited_map[region][0] == CrystalBarrier.Null:
            self.visited_map[region] = CrystalBarrier.Null, self.crystal_forced
        elif self.crystal != self.visited_map[region][0]:
            self.crystal = CrystalBarrier.Both
            if self.crystal_forced != self.visited_map[region][1]:
                self.crystal_forced = CrystalBarrier.Null
            self.visited_map[region] = self.crystal, self.crystal_forced  # both blue and orange visited
        else:
            self.visited_map[region] = self.crystal, self.crystal_forced  # we're visiting as a specific color, not sure this is reachable
        if region.type == RegionType.Dungeon:
            for location in region.locations:
                if location not in self.found_locations:
                    self.found_locations.append(location)
                if location.name in dungeon_events and location.name not in self.events:
                    if self.flooded_key_check(location):
                        self.perform_event(location.name)
                if location.name in flooded_keys_reverse.keys() and self.location_found(
                        flooded_keys_reverse[location.name]):
                    self.perform_event(flooded_keys_reverse[location.name])
        for ext in region.exits:
            door = ext.door
            if door is not None:
                if not door.blocked if self.respect_traps else self.can_traverse_ignore_traps(door):
                    if door.controller is not None:
                        door = door.controller
                        connect_region = door.entrance.parent_region
                        if connect_region is not None and not self.visited(connect_region):
                            self.visit_region(connect_region)
                        self.append_door_to_list(door, self.avail_doors, False)
                    if door.dest is None and door.name != 'Sanctuary Mirror Route':
                        self.append_door_to_list(door, self.unattached_doors)
                    elif door.req_event is not None and door.req_event not in self.events:
                        self.append_door_to_list(door, self.event_doors)
                    else:
                        self.append_door_to_list(door, self.avail_doors, False)

    # Visited Truth Table
    # Note: self.crystal or state.crystal should never be "Both", this indicates a forcing thing
    # Prev/State Null    Blue    Orange  Both   Either
    # Null       T       T       T       ?      f
    # Blue       T       T       f       ?      f
    # Orange     T       f       T       ?      f
    # Both       T       T       T       ?      f
    # Either     T       T       T       ?      T

    def visited(self, region):
        if region not in self.visited_map:
            return False
        prev_visit, forced_crystal = self.visited_map[region]
        if forced_crystal != CrystalBarrier.Null and self.crystal_forced == CrystalBarrier.Null:
            return False
        if prev_visit == CrystalBarrier.Either:
            return True
        if prev_visit == self.crystal:
            return True
        if self.crystal == CrystalBarrier.Null:
            return True
        if self.crystal == CrystalBarrier.Either:
            return False
        if prev_visit == CrystalBarrier.Both:
            return True
        return prev_visit == CrystalBarrier.Null

    def flooded_key_check(self, location):
        if location.name not in flooded_keys.keys():
            return True
        return flooded_keys[location.name] in [x.name for x in self.found_locations]

    def location_found(self, location_name):
        for l in self.found_locations:
            if l.name == location_name:
                return True
        return False

    def perform_event(self, location_name):
        self.events.add(location_name)
        queue = deque(self.event_doors)
        while len(queue) > 0:
            exp_door = queue.popleft()
            if exp_door.door.req_event == location_name:
                self.avail_doors.append(exp_door)
                self.event_doors.remove(exp_door)

    def can_traverse(self, door, exception=None):
        if door.blocked:
            return exception(door) if exception else False
        return True

    def can_traverse_ignore_traps(self, door):
        if door.blocked and door.trapFlag == 0:
            return False
        return True

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

    def append_door_to_list(self, door, door_list, collapse=True, cs_override=None):
        existing_exp_door = self.find_door_in_list(door, door_list)
        existing_exp_doors = [d for d in door_list if d.door == door]
        if len(existing_exp_doors) > 1 and collapse:
            raise Exception('append_door_to_list in DungeonGenSectorDesc needs a refactor')
        if existing_exp_door is None or not collapse:
            if door.crystal != CrystalBarrier.Null:
                if door.crystal == CrystalBarrier.Either:
                    door_list.append(ExplorableDoor(door, door.crystal, self.crystal_forced))
                elif self.crystal == CrystalBarrier.Either:
                    door_list.append(ExplorableDoor(door, door.crystal, self.crystal_forced))
                elif self.crystal == CrystalBarrier.Both:
                    if self.crystal_forced == CrystalBarrier.Null:
                        door_list.append(ExplorableDoor(door, door.crystal, door.crystal))
                    else:
                        door_list.append(ExplorableDoor(door, door.crystal, self.crystal_forced))
                elif self.crystal in [CrystalBarrier.Null, CrystalBarrier.Both]:
                    door_list.append(ExplorableDoor(door, door.crystal, door.crystal))
                elif self.crystal == door.crystal:
                    door_list.append(ExplorableDoor(door, door.crystal, self.crystal_forced))
                # otherwise we can't go through this door this way
            else:  # nothing forcing
                if cs_override:
                    door_list.append(ExplorableDoor(door, cs_override, cs_override))
                else:
                    door_list.append(ExplorableDoor(door, self.crystal, self.crystal_forced))
        else:
            # door must not specify and the crystal must be different
            if door.crystal == CrystalBarrier.Null and existing_exp_door.crystal != self.crystal:
                crystal_adj = CrystalBarrier.Null
                force_adj = existing_exp_door.flag
                if self.crystal == CrystalBarrier.Either:
                    crystal_adj = CrystalBarrier.Either
                    force_adj = self.crystal_forced
                elif existing_exp_door.crystal != CrystalBarrier.Null and self.crystal != CrystalBarrier.Null:
                    crystal_adj = CrystalBarrier.Both
                    force_adj = CrystalBarrier.Null
                existing_exp_door.crystal = crystal_adj
                existing_exp_door.flag = force_adj
            if existing_exp_door.flag in [CrystalBarrier.Blue, CrystalBarrier.Orange]:
                if self.crystal == CrystalBarrier.Either:
                    existing_exp_door.flag = self.crystal_forced
                elif existing_exp_door.crystal == door.crystal:
                    existing_exp_door.flag = self.crystal_forced
                if self.crystal_forced == CrystalBarrier.Null:
                    existing_exp_door.flag = CrystalBarrier.Null
