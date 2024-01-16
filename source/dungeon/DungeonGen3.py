import logging
import typing
from collections import defaultdict, deque, Counter

from BaseClasses import Direction, RegionType, CrystalBarrier, DoorType, flooded_keys
from BaseClasses import hook_from_door
from Regions import dungeon_events, flooded_keys_reverse
from Utils import append_to_yaml
from source.dungeon.DungeonGenerationCommon import DungeonBuilder, define_sector_features, hanger_from_door, dungeon_portals
from source.dungeon.DungeonStitcher import ExplorableDoor


def create_sector_descriptors(sector_list, world, player):
    v_trap_flag = world.trap_door_mode[player] == 'vanilla'
    # custom intensity could be here
    for sector in sector_list:
        descript = SectorDescriptor(sector, v_trap_flag)
        sector.descriptor = descript


class SectorDescriptor:
    def __init__(self, sector, v_trap_flag):
        self.sector = sector
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
        self.constraints = {}  # disjunction of optional constraints, indexed by Hooks consumed
        self.parity_id = ''
        self.init_parity_id()
        self.analyze_sector(v_trap_flag)

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
        # which outstanding doors are reachable from which outstanding doors
        for door in self.sector.outstanding_doors:
            # these types you cannot enter from
            if door.type in [DoorType.Warp, DoorType.Hole]:
                continue
            state = SimpleExplorationState(v_trap_flag)
            state.extend_reachable_state(door)
            for explorable in state.unattached_doors:
                if explorable.door == DoorType.Logical:  # skip sanc mirror route in this calc
                    continue
                restrict = 'Blue' if explorable.crystal == CrystalBarrier.Blue else 'None'
                self.reachability[door].append((explorable.door, restrict))
        for door_hanger, reached_list in self.reachability.items():
            crystal_needed = any(x[1] == 'Blue' for x in reached_list)
            hanger_type = hook_from_door(door_hanger)
            constraint = SectorConstraint(hanger_type, crystal_needed)
            constraint.candidate_hangers.add(door_hanger)
            for door_hook, crystal in reached_list:
                constraint.accessible_doors.add(door_hook)
                # todo: in decoupled, you actually do get the benefit from the hooked door
                if door_hook.name == door_hanger.name:
                    continue
                hook = hook_from_door(door_hook)
                if hook is not None:
                    constraint.benefits[hook] += 1

            # is this constraint helpful?
            bene_count = constraint.benefit_count()
            if hanger_type not in self.constraints:
                self.constraints[hanger_type] = constraint
            else:
                competitor = self.constraints[hanger_type]
                comp_count = competitor.benefit_count()
                if comp_count < bene_count:
                    # replace with the new guy, he's just better
                    self.constraints[hanger_type] = constraint
                elif comp_count == bene_count:
                    if competitor.accessible_doors == constraint.accessible_doors:
                        if competitor.crystal_needed and not constraint.crystal_needed:
                            self.constraints[hanger_type] = constraint  # replace, no crystal requirement is better
                        elif competitor.crystal_needed or not constraint.crystal_needed:
                            self.constraints[hanger_type].candidate_hangers.add(door_hanger)  # new option, cool

                    else:
                        logging.getLogger('').warning(f'You should check {door_hanger.name}, same hook, different access')
                        # probably means we need a slightly different data structure
                # else, this constraint is worse than the previous one

        complete_constraints = {k: c for k, c in self.constraints.items() if len(c.accessible_doors) == self.degree}
        if len(complete_constraints) > 0:
            self.constraints = complete_constraints  # done, let's just use the complete ones
        else:
            self.reduce_constraints()  # if possible

        # check if each constraint satisfies completely the sector, or if a combination is needed
        # priority = sorted([(k, v) for k, v in self.constraints.items()], key=lambda x: x[1].benefit_count(), reverse=True)
        # total_set = {x.name for x in self.sector.outstanding_doors}
        # satisfaction_flag = False
        # chosen_set = set()
        # combined_constraint = None
        # for hanger_type, constraint in priority:
        #     is_complete = len(constraint.accessible_doors) == self.degree
        #     if is_complete:
        #         satisfaction_flag = True
        #     elif satisfaction_flag:  # we're satisfied, we don't need this
        #         del self.constraints[hanger_type]
        #     elif combined_constraint is None:
        #         combined_constraint = SectorConstraint(None, False, 'conjoint', [constraint])
        #         chosen_set.update(x.name for x in constraint.accessible_doors)
        #         del self.constraints[hanger_type]
        #     else:
        #         lacking_set = total_set.difference(chosen_set)
        #         candidate_set = {x.name for x in constraint.accessible_doors}
        #         reduction = len(lacking_set.intersection(candidate_set))
        #         if reduction > 0:
        #             combined_constraint.children.append(constraint)
        #             if reduction == len(lacking_set):
        #                 satisfaction_flag = True
        #         # else, what's the point?
        #         del self.constraints[hanger_type]
        # if combined_constraint is not None:
        #     self.constraints[combined_constraint.combined_key()] = combined_constraint

    def reduce_constraints(self):
        def fewest_remaining(item):
            constr, door = item
            return len(lacking_doors - constr.accessible_doors)

        constraint_options = []
        fully_satisfied = False
        best_length = float('inf')
        total_set = set(self.sector.outstanding_doors)

        constraint_order = sorted([c for c in self.constraints.values()], key=lambda c: c.benefit_count(), reverse=True)

        for constraint in constraint_order:
            done = False
            current_constraint = constraint
            while not done:
                # figure out what is missing
                lacking_doors = total_set - current_constraint.accessible_doors
                # can I hook into any of these?
                connectable = [d for d in lacking_doors if current_constraint.benefits[hanger_from_door(d)] > 0]
                connectable_constraints = []
                for c in connectable:
                    possible = self.constraints[hook_from_door(c)]
                    if c in possible.candidate_hangers:
                        connectable_constraints.append((possible, c))
                if len(connectable_constraints) > 0:
                    cc = sorted(connectable_constraints, key=fewest_remaining)
                    combined_c, door = next(iter(cc))
                    new_constraint = SectorConstraint(current_constraint.hanger, current_constraint.crystal_needed)
                    new_constraint.candidate_hangers.update(constraint.candidate_hangers)
                    new_constraint.benefits.update(current_constraint.benefits)
                    new_constraint.benefits[hanger_from_door(door)] -= 1
                    new_constraint.accessible_doors.update(current_constraint.accessible_doors)
                    used_door = next(d for d in new_constraint.accessible_doors if hook_from_door(d) == hanger_from_door(door))
                    new_constraint.assumed_connections[used_door] = door
                    new_access_doors = lacking_doors.intersection(combined_c.accessible_doors)
                    for new_door in new_access_doors:
                        hook = hook_from_door(new_door)
                        # todo: in decoupled, you actually do get the benefit from the hooked door
                        if new_door.name != door.name and hook is not None:
                            new_constraint.benefits[hook_from_door(new_door)] += 1
                    new_constraint.accessible_doors.update(new_access_doors)
                    if len(new_constraint.accessible_doors) == self.degree:
                        if not fully_satisfied:
                            fully_satisfied = True
                        constraint_options = [o for o in constraint_options if o.join_method is None]
                        constraint_options.append(new_constraint)
                        best_length = 1
                        done = True
                    else:
                        current_constraint = new_constraint
                else:
                    if fully_satisfied or best_length == 1:  # don't bother with these constraints
                        done = True
                        continue
                    # combine with other constraints with and until satisfied_by_multiples?
                    priority = sorted([(k, v) for k, v in self.constraints.items()],
                                      key=lambda x: len(lacking_doors-constraint.accessible_doors))
                    chosen_set = set(constraint.accessible_doors)
                    combined_constraint = SectorConstraint(None, False, 'conjoint', [constraint])
                    while len(chosen_set) < len(total_set):
                        if len(priority) == 0:
                            sector_doors = ', '.join([x.name for x in self.sector.outstanding_doors])
                            raise Exception(f'Problem with determining constraints for a sector: {sector_doors}')
                        k, next_constraint = priority.pop()
                        if len(lacking_doors.intersection(next_constraint.accessible_doors)) > 0:
                            chosen_set.update(next_constraint.accessible_doors)
                            combined_constraint.children.append(next_constraint)
                        if len(combined_constraint.children) > best_length:  # early exit
                            break
                    if len(combined_constraint.children) <= 1:
                        sector_doors = ', '.join([x.name for x in self.sector.outstanding_doors])
                        raise Exception(f'Conjoint constraint should have more than one child: {sector_doors}')
                    child_length = len(combined_constraint.children)
                    if child_length < best_length:
                        best_length = child_length
                        constraint_options = [c for c in constraint_options if len(c.children) <= best_length]
                        constraint_options.append(combined_constraint)
                    elif child_length == best_length:
                        constraint_options.append(combined_constraint)
                    # else, this was worse
                    done = True
        self.constraints = {opt.combined_key(): opt for opt in constraint_options}

    def __str__(self):
        return f'{self.name}:{self.parity_id}'

    def to_yaml(self):
        return {self.sector.sector_key(): [x.to_yaml() for x in self.constraints.values()]}


class SectorConstraint:
    def __init__(self, hanger=None, crystal_needed=False, join_method='conjoint', children=None):
        if hanger is None:
            self.join_method = join_method  # either conjoint or disjoint
            self.children = children
        else:
            self.join_method = None
            self.children = None

        self.hanger = hanger  # door Hook(s) consumed - could be a frozenset (hopefully we never need to move to Counter)
        self.candidate_hangers = set()  # door options
        self.crystal_needed = crystal_needed  # is a crystal needed or not
        self.benefits = defaultdict(int)  # Hook -> number of type reached
        self.accessible_doors = set()
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
            'cost': self.hanger.name,
            'candidates': [x.name for x in self.candidate_hangers],
            'crystal': self.crystal_needed,
            'benefits': {x.name: y for x, y in self.benefits.items()},
            'reachable': [x.name for x in self.accessible_doors],
            'assumptions': {k.name: v.name for k, v in self.assumed_connections.items()}
        }

    def combined_key(self):
        if self.join_method:
            ctr = Counter()
            ctr.update(x.combined_key() for x in self.children)
            return frozenset(ctr.items())
        else:
            return self.hanger


class SimpleExplorationState:
    def __init__(self, respect_traps):
        self.respect_traps = respect_traps

        self.avail_doors = []
        self.unattached_doors = []
        self.event_doors = []

        self.visited_orange = []
        self.visited_blue = []
        self.visited_doors = set()
        self.events = set()
        self.crystal = CrystalBarrier.Null

        self.found_locations = []

    def extend_reachable_state(self, start_door):
        start_region = start_door.entrance.parent_region
        self.append_door_to_list(start_door, self.unattached_doors)  # always counts for oneself
        self.visit_region(start_region)
        while len(self.avail_doors) > 0:
            explorable_door = self.next_avail_door()
            connect_region = explorable_door.door.entrance.connected_region
            if connect_region is not None and not self.visited(connect_region):
                self.visit_region(connect_region)

    def next_avail_door(self):
        exp_door = self.avail_doors.pop()
        self.crystal = exp_door.crystal
        return exp_door

    def visit_region(self, region):
        if region.crystal_switch:
            self.crystal = CrystalBarrier.Either
        if self.crystal == CrystalBarrier.Either:
            if region not in self.visited_blue:
                self.visited_blue.append(region)
            if region not in self.visited_orange:
                self.visited_orange.append(region)
        elif self.crystal in [CrystalBarrier.Orange, CrystalBarrier.Null]:
            self.visited_orange.append(region)
        elif self.crystal == CrystalBarrier.Blue:
            self.visited_blue.append(region)
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
                # if '- Prize' in location.name:
                #     self.prize_received = True
        for ext in region.exits:
            door = ext.door
            if door is not None:
                if not door.blocked if self.respect_traps else self.can_traverse_ignore_traps(door):
                    if door.controller is not None:
                        door = door.controller
                    if door.dest is None:
                        if not self.in_door_list_ic(door, self.unattached_doors):
                            self.append_door_to_list(door, self.unattached_doors)
                    elif (door.req_event is not None and door.req_event not in self.events
                          and not self.in_door_list(door, self.event_doors)):
                        self.append_door_to_list(door, self.event_doors)
                    elif not self.in_door_list(door, self.avail_doors):
                        self.append_door_to_list(door, self.avail_doors)

    def visited(self, region):
        if self.crystal == CrystalBarrier.Either:
            return region in self.visited_blue and region in self.visited_orange
        elif self.crystal in [CrystalBarrier.Orange, CrystalBarrier.Null]:
            return region in self.visited_orange
        elif self.crystal == CrystalBarrier.Blue:
            return region in self.visited_blue
        return False

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

    def append_door_to_list(self, door, door_list, flag=False):
        if door.crystal in [CrystalBarrier.Null, CrystalBarrier.Either]:
            door_list.append(ExplorableDoor(door, self.crystal, flag))
        elif self.crystal == CrystalBarrier.Either:  # if we found a crystal switch, continue
            door_list.append(ExplorableDoor(door, self.crystal, flag))
        elif self.crystal == CrystalBarrier.Null or self.crystal == door.crystal:
            door_list.append(ExplorableDoor(door, door.crystal, flag))
        # otherwise we can't go through this door this way


# ------------------------------ #
#         Main Algorithm
# ------------------------------ #

def create_dungeon_builders_prototype(dungeon_pool, sector_pool, portal_pool, world, player):
    portal_assignments = defaultdict(list)
    # shuffle portals between dungeons at this point?
    # each dungeon needs at least one portal, but no more than four

    # vanilla assignment
    for key in dungeon_pool:
        portal_list = dungeon_portals[key]
        for portal in portal_list:
            portal_sector = next(p for p in portal_pool if portal in p.name)
            portal_assignments[key].append(portal_sector)

    # for



    define_sector_features(sector_pool)
    create_sector_descriptors(sector_pool, world, player)
    sector_map = {}
    for sector in sector_pool:
        for door in sector.outstanding_doors:
            sector_map[door.name] = sector

    dungeon_map = {}
    if 'Skull Woods' in dungeon_pool:
        dungeon_pool.append('Skull Woods Back')
        dungeon_pool.append('Skull Woods Front')
        dungeon_pool.remove('Skull Woods')
    if 'Desert Palace' in dungeon_pool:  # a strict split will prevent
        dungeon_pool.append('Desert Palace Back')
        dungeon_pool.append('Desert Palace Front')
        dungeon_pool.remove('Desert Palace')
    if 'Hyrule Castle' in dungeon_pool and world.mode[player] == 'standard':
        dungeon_pool.append('Hyrule Castle Dungeon')
        dungeon_pool.append('Hyrule Castle Sewers')
        dungeon_pool.remove('Hyrule Castle')
    for key in dungeon_pool:
        current_dungeon = dungeon_map[key] = DungeonBuilder(key)

    # add special portal sectors to sector pool

    for sector in sector_pool:
        append_to_yaml(['data', 'gen', 'proposed.yaml'], sector.descriptor.to_yaml())

    return {}


def merge_sectors_by_two_way_list(sector_pool, sector_map, connection_list, world, player):
    for edge_a, edge_b in connection_list:
        # connect_two_way(world, edge_a, edge_b, player)
        sector_a = sector_map[edge_a]
        sector_b = sector_map[edge_b]
        sector_pool.remove(sector_b)
        merge_sectors(sector_a, sector_b, {world.get_door(edge_a, player), world.get_door(edge_b, player)})


def merge_sectors(sector_a, sector_b, connected_doors):
    sector_a.regions.extend(sector_b.regions)
    sector_a.outstanding_doors = [d for d in sector_a.outstanding_doors if d.name not in connected_doors]
    sector_a.outstanding_doors.extend([d for d in sector_b.outstanding_doors if d.name not in connected_doors])
    sector_a.name = None
    sector_a.r_name_set = None
    sector_a.chest_locations += sector_b.chest_locations
    sector_a.key_only_locations += sector_b.key_only_locations
    sector_a.c_switch |= sector_b.c_switch
    sector_a.orange_barrier |= sector_b.orange_barrier
    sector_a.blue_barrier |= sector_b.blue_barrier
    sector_a.bk_required |= sector_b.bk_required

    # not yet implemented, are they needed?
    # self.conn_balance = None
    # self.branch_factor = None
    # self.dead_end_cnt = None
    # self.entrance_sector = None
    # self.destination_entrance = False

    sector_a.item_logic |= sector_b.item_logic
    sector_a.chest_location_set |= sector_b.chest_location_set
    sector_a.key = None

    sector_a.descriptor.degree = len(sector_a.outstanding_doors)
    sector_a.descriptor.name = min(sector_a.region_set(), key=len)
    sector_a.descriptor.init_parity_id()
    # for door, reached sector_a.descriptor.reachability




# ------------------------------ #
#         Utility
# ------------------------------ #

# hook_map = {
#     Hook.North : 'North',
#     Hook.South : 'South',
#     Hook.West : 'West',
#     Hook.East : 'East',
#     Hook.Stairs : 'Stairs',
#     Hook.PitWarp : 'PitWarp',
# }
# def hook_to_string(hook):
#     return hook_map[hook