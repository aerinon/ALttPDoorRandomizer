import logging
import RaceRandom as random
from collections import defaultdict, deque, Counter

from BaseClasses import Direction, RegionType, CrystalBarrier, DoorType, Door, flooded_keys
from BaseClasses import hook_from_door
from Regions import dungeon_events, flooded_keys_reverse
from Utils import append_to_yaml, clear_file
from source.dungeon.DungeonGenerationCommon import DungeonBuilder, define_sector_features, hanger_from_door, dungeon_portals
from source.dungeon.DungeonGenerationCommon import GlobalPolarity, find_sector, GenerationException
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
        self.constraints = {}  # disjunction of optional constraints, indexed by Hooks consumed
        self.parity_id = ''
        self.init_parity_id()

        self.dead_end = False
        self.must_enter_reqs = []
        self.special_reqs = []
        self.crystal_reqs = None
        self.is_neutral = False

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
        skip_door = None
        if self.sector.portal and not self.sector.portal.destination:
            self.reachability[None].append((self.sector.portal.door, False))
            skip_door = self.sector.portal.door
            # todo: dependent portals
        # which outstanding doors are reachable from which outstanding doors
        for door in self.sector.outstanding_doors:
            # these types you cannot enter from
            if door.type in [DoorType.Warp, DoorType.Hole] or door == skip_door:
                continue
            state = SimpleExplorationState(v_trap_flag)
            state.extend_reachable_state(door)
            for explorable in state.unattached_doors:
                if explorable.door == DoorType.Logical:  # skip sanc mirror route in this calc
                    continue
                # crystal = self.resolve_crystal_prop(explorable.crystal, state.visited_map[explorable.door.entrance.parent_region])
                self.reachability[door].append((explorable.door, explorable.crystal))

        self.classify()
        # for door_hanger, reached_list in self.reachability.items():
        #     crystal_needed = any(x[1] in {CrystalBarrier.Blue, CrystalBarrier.Both} for x in reached_list)
        #     hanger_type = None if door_hanger is None else hook_from_door(door_hanger)
        #     constraint = SectorConstraint(hanger_type, crystal_needed)
        #     constraint.candidate_hangers.add(door_hanger)
        #     for door_hook, crystal in reached_list:
        #         constraint.accessible_doors[door_hook] = crystal
        #         # todo: in decoupled, you actually do get the benefit from the hooked door
        #         if door_hanger and door_hook.name == door_hanger.name:
        #             continue
        #         hook = hook_from_door(door_hook)
        #         if hook is not None:
        #             constraint.benefits[hook] += 1
        #     # is this constraint helpful?
        #     bene_count = constraint.benefit_count()
        #     if hanger_type not in self.constraints:
        #         self.constraints[hanger_type] = constraint
        #     else:
        #         competitor = self.constraints[hanger_type]
        #         comp_count = competitor.benefit_count()
        #         if comp_count < bene_count:
        #             # replace with the new guy, he's just better
        #             self.constraints[hanger_type] = constraint
        #         elif comp_count == bene_count:
        #             if competitor.accessible_doors == constraint.accessible_doors:
        #                 if competitor.crystal_needed and not constraint.crystal_needed:
        #                     self.constraints[hanger_type] = constraint  # replace, no crystal requirement is better
        #                 elif competitor.crystal_needed or not constraint.crystal_needed:
        #                     self.constraints[hanger_type].candidate_hangers.add(door_hanger)  # new option, cool
        #             else:
        #                 logging.getLogger('').warning(f'You should check {door_hanger.name}, same hook, different access')
        #                 # probably means we need a slightly different data structure
        #         # else, this constraint is worse than the previous one
        #
        # complete_constraints = {k: c for k, c in self.constraints.items() if len(c.accessible_doors) == self.degree}
        # if len(complete_constraints) > 0:
        #     self.constraints = complete_constraints  # done, let's just use the complete ones
        # else:
        #     self.reduce_constraints()  # if possible

    def classify(self):
        total_needed = len(self.sector.outstanding_doors)
        unreached = set(self.sector.outstanding_doors)
        if total_needed == 1:
            self.dead_end = True
        else:
            if 'Ice Cross Left' in self.sector.r_name_set:
                specials = []
                for source, dest_list in self.reachability.items():
                    if any('Ice Cross ' in d.name for d, c in dest_list):
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
                    reached.update([d for d, c in self.reachability[dest]])
                unreached.difference_update(reached)
                if len(unreached) > 0:
                    covers_all = []
                    for source, dest_list in self.reachability.items():
                        door_set = set(d for d, c in dest_list if d in unreached)
                        if len(door_set) == len(unreached):
                            covers_all.append(source)
                    if not covers_all:
                        raise GenerationException("Some edge case where you need to separate door to cover all: " + self.sector)
                    if len(covers_all) == 1:
                        d = next(iter(covers_all))
                        self.must_enter_reqs.insert(0, d)
                    else:
                        self.must_enter_reqs.insert(0, tuple(covers_all))
            # todo: check for crystal options
        if all(len(reach_list) == total_needed for source, reach_list in self.reachability.items()):
            if self.is_sector_neutral():
                self.is_neutral = True

    def is_sector_neutral(self):
        if len(self.sector.outstanding_doors) == 2:
            d1, d2 = self.sector.outstanding_doors[0], self.sector.outstanding_doors[1]
            if hanger_from_door(d1) == hook_from_door(d2):
                reachability = self.reachability
                if len(reachability[d1]) == 2 and len(reachability[d2]) == 2:
                    return (all(access[1] == CrystalBarrier.Null for access in reachability[d1]) and
                            all(access[1] == CrystalBarrier.Null for access in reachability[d2]))
        return False

    # assumptions, state_crystal can't be null and represents the last barrier passed over
    def resolve_crystal_prop(self, state_crystal, region_crystal):
        if state_crystal != CrystalBarrier.Null:
            return state_crystal
        return region_crystal

    def reduce_constraints(self):
        def fewest_remaining(item):
            constr, door = item
            return len(lacking_doors - set(constr.accessible_doors.keys()))

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
                lacking_doors = total_set - set(current_constraint.accessible_doors.keys())
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
                    new_access_doors = {d: combined_c.accessible_doors[d] for d in lacking_doors if d in combined_c.accessible_doors}
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
                                      key=lambda x: len(lacking_doors-set(constraint.accessible_doors.keys())))
                    chosen_set = set(constraint.accessible_doors.keys())
                    combined_constraint = SectorConstraint(None, False, 'conjoint', [constraint])
                    while len(chosen_set) < len(total_set):
                        if len(priority) == 0:
                            sector_doors = ', '.join([x.name for x in self.sector.outstanding_doors])
                            raise Exception(f'Problem with determining constraints for a sector: {sector_doors}')
                        k, next_constraint = priority.pop()
                        if len(lacking_doors.intersection(set(next_constraint.accessible_doors.keys()))) > 0:
                            chosen_set.update(set(next_constraint.accessible_doors.keys()))
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
        return {self.sector.sector_key(): [[c.to_yaml() for c in cm.values()] for cm in self.joined_constraints]}


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

        self.found_locations = []

    def extend_reachable_state(self, start_door):
        start_region = start_door.entrance.parent_region
        self.append_door_to_list(start_door, self.unattached_doors)  # always counts for oneself
        self.visit_region(start_region)
        while len(self.avail_doors) > 0:
            explorable_door = self.next_avail_door()
            connect_region = explorable_door.door.entrance.connected_region
            self.crystal = explorable_door.crystal
            if connect_region is not None and not self.visited(connect_region):
                self.visit_region(connect_region)

    def next_avail_door(self):
        exp_door = self.avail_doors.pop()
        self.crystal = exp_door.crystal
        return exp_door

    def visit_region(self, region):
        if region.crystal_switch:
            self.crystal = CrystalBarrier.Either
        if region not in self.visited_map or self.crystal == CrystalBarrier.Either:
            self.visited_map[region] = self.crystal
        elif self.crystal == CrystalBarrier.Null or self.visited_map[region] == CrystalBarrier.Null:
            self.visited_map[region] = CrystalBarrier.Null
        elif self.crystal != self.visited_map[region]:
            self.visited_map[region] = CrystalBarrier.Both   # both blue and orange visited
        else:
            self.visited_map[region] = self.crystal  # we're visiting as a specific color, not sure this is reachable
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
                    if door.dest is None:
                        self.append_door_to_list(door, self.unattached_doors)
                    elif door.req_event is not None and door.req_event not in self.events:
                        self.append_door_to_list(door, self.event_doors)
                    else:
                        self.append_door_to_list(door, self.avail_doors)

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
        prev_visit = self.visited_map[region]
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

    def append_door_to_list(self, door, door_list, flag=False):
        existing_exp_door = self.find_door_in_list(door, door_list)
        if existing_exp_door is None:
            if door.crystal != CrystalBarrier.Null:
                if door.crystal == CrystalBarrier.Either or self.crystal in {CrystalBarrier.Null, CrystalBarrier.Either} or self.crystal == door.crystal:
                    door_list.append(ExplorableDoor(door, door.crystal, flag))
                # otherwise we can't go through this door this way
            else:  # nothing forcing
                door_list.append(ExplorableDoor(door, self.crystal, flag))
        else:
            # door must not specify and the crystal must be different
            if door.crystal == CrystalBarrier.Null and existing_exp_door.crystal != self.crystal:
                crystal_adj = CrystalBarrier.Null
                if self.crystal == CrystalBarrier.Either:
                    crystal_adj = CrystalBarrier.Either
                elif existing_exp_door.crystal != CrystalBarrier.Null and self.crystal != CrystalBarrier.Null:
                    crystal_adj = CrystalBarrier.Both
                existing_exp_door.crystal = crystal_adj


# ------------------------------ #
#         Main Algorithm
# ------------------------------ #

def create_dungeon_builders_prototype(dungeon_pool, sector_pool, portal_pool, world, player):
    generation_log_name = ['data', 'gen', 'generation.yaml']
    gen_log = []
    try:
        dungeons = main_dungeon_builders(dungeon_pool, sector_pool, portal_pool, gen_log, world, player)
        append_to_yaml(generation_log_name, gen_log)
        return dungeons
    except Exception as e:
        append_to_yaml(generation_log_name, gen_log)
        raise e


def main_dungeon_builders(dungeon_pool, sector_pool, portal_pool, gen_log, world, player):
    flags = DoorFlags().from_world(world, player)
    portal_assignments = defaultdict(list)
    # shuffle portals between dungeons at this point?
    # each dungeon needs at least one portal, but no more than four

    # vanilla assignment
    for key in dungeon_pool:
        portal_list = dungeon_portals[key]
        for portal in portal_list:
            region_name = portal + ' Portal'
            portal_sector = next(p for p in portal_pool if region_name in p.region_set())
            region = world.get_region(region_name, player)
            door = create_portal_door(world, player, next(e.name for e in region.exits if e.name.startswith('Enter ')))
            portal_sector.outstanding_doors.append(door)
            portal_sector.portal = world.get_portal(portal, player)
            portal_sector.portal.door = door  # assign placeholder door
            portal_assignments[key].append(portal_sector)

    define_sector_features(sector_pool)
    create_sector_descriptors(sector_pool + portal_pool, world, player)

    # ??? do we want a sector map?
    # sector_map = {}
    # for sector in sector_pool:
    #     for door in sector.outstanding_doors:
    #         sector_map[door.name] = sector

    # todo: distribute portals for split dungeons
    dungeon_map = {}
    if 'Skull Woods' in dungeon_pool and len(portal_assignments['Skull Woods']) > 1:
        dungeon_pool.append('Skull Woods Back')
        dungeon_pool.append('Skull Woods Front')
        dungeon_pool.remove('Skull Woods')
        assignments = portal_assignments['Skull Woods']
        # get skull 3 portal assignment if present, else a random 1
        # the rest go in front
    if 'Desert Palace' in dungeon_pool:  # a strict split will prevent this from being a cross-world connector inadvertantly
        dungeon_pool.append('Desert Palace Back')
        dungeon_pool.append('Desert Palace Front')
        dungeon_pool.remove('Desert Palace')
    if 'Hyrule Castle' in dungeon_pool and world.mode[player] == 'standard':
        # todo: special edits for throne room, sewer "portal" sector
        dungeon_pool.append('Hyrule Castle Dungeon')
        dungeon_pool.append('Hyrule Castle Sewers')
        dungeon_pool.remove('Hyrule Castle')

    all_sectors = sector_pool + portal_pool
    info = DungeonGenInfo(gen_log, all_sectors, flags)

    for key in dungeon_pool:
        current_dungeon = dungeon_map[key] = DungeonBuilder(key)
        # handle special assignments
        for sector in portal_assignments[key]:
            assign_sector(current_dungeon, sector, info)
        # handle special sectors:
        if key == 'Hyrule Castle Dungeon':  # builder doesn't exist except in standard
            for r_name in ['Hyrule Dungeon Cellblock', 'Hyrule Castle Throne Room']:  # need to deliver zelda
                assign_sector(current_dungeon, find_sector(r_name, sector_pool), info)
        elif key == 'Hyrule Castle Sewers':  # builder doesn't exist except in standard
            assign_sector(current_dungeon, find_sector('Sanctuary', sector_pool), info)
        elif key == 'Thieves Town' and world.get_dungeon("Thieves Town", player).boss.enemizer_name == 'Blind':
            assign_sector(current_dungeon, find_sector("Thieves Blind's Cell", sector_pool), info)

    # this handles boss sectors
    for key, builder_list in dungeon_boss_regions.items():
        boss_sector = find_sector(key, sector_pool)
        if boss_sector:
            candidate_builders = [d for d in dungeon_map if d in builder_list]
            if len(candidate_builders) == 1:
                chosen_builder = next(iter(candidate_builders))
            else:
                chosen_builder = random.choice(candidate_builders)
            assign_sector(dungeon_map[chosen_builder], boss_sector, info)

    if not info.flags.lobbies:
        # todo: lobbies for intensity 2 or less
        pass

    # next step, find sectors with crystal needed
    # find sectors with crystal provided
    # choose and join
    handle_crystal_switch_constraints(dungeon_map, info)  # step 1

    # todo: how necessary is this
    # find sectors without path from switch to crystal needed
    # find possible transition sectors
    # choose and join
    handle_crystal_switch_paths(dungeon_map, info)  # todo: ???

    # find sectors with hardest requirements
    #   dead ends (no benefits) - first - these must be connected to some branch)
    #   connectors with specific transforms (one option, one

    return dungeon_map


def create_portal_door(world, player, entName):
    entrance = world.get_entrance(entName, player)
    d = Door(player, entName, DoorType.Normal, entrance)
    d.direction = Direction.North
    world.doors.append(d)
    return d


# def merge_sectors_by_two_way_list(sector_pool, sector_map, connection_list, world, player):
#     for edge_a, edge_b in connection_list:
#         # connect_two_way(world, edge_a, edge_b, player)
#         sector_a = sector_map[edge_a]
#         sector_b = sector_map[edge_b]
#         sector_pool.remove(sector_b)
#         merge_sectors(sector_a, sector_b, {world.get_door(edge_a, player), world.get_door(edge_b, player)})


def assign_sector(builder, new_sector, info):
    info.global_pole.consume(new_sector)
    del info.sector_pool[new_sector]
    master = builder.master_sector
    if master is None:
        builder.master_sector = new_sector
        return
    merge_sectors(master, new_sector, info)


def merge_sectors(master, new_sector, info):
    # todo: investigate: can we verify global pol before this merge happens? do we need to?
    if new_sector in info.sector_pool:
        del info.sector_pool[new_sector]
    master.regions.extend(new_sector.regions)
    master.outstanding_doors.extend(new_sector.outstanding_doors)
    master.name = None
    master.r_name_set = None
    master.chest_locations += new_sector.chest_locations
    master.key_only_locations += new_sector.key_only_locations
    master.c_switch |= new_sector.c_switch
    master.orange_barrier |= new_sector.orange_barrier
    master.blue_barrier |= new_sector.blue_barrier
    master.bk_required |= new_sector.bk_required

    master.item_logic |= new_sector.item_logic
    master.chest_location_set |= new_sector.chest_location_set
    master.key = None

    master.descriptor.degree = len(master.outstanding_doors)
    master.descriptor.name = min(master.region_set(), key=len)
    master.descriptor.init_parity_id()
    # master.descriptor.analyze_sector(info.flags.vanilla_traps)
    master.descriptor.joined_constraints += new_sector.descriptor.joined_constraints
    info.gen_log.append(master.descriptor.to_yaml())
    return master


def handle_crystal_switch_constraints(dungeon_map, info):
    crystal_needed_sectors = find_crystal_constraints(dungeon_map, info)
    c_switch_sectors = find_crystal_switches(dungeon_map, info)
    for sector, limitation in crystal_needed_sectors.items():
        if limitation:
            candidates = [s for s, limit in c_switch_sectors.items() if limit is None]
        else:
            candidates = list(c_switch_sectors.keys())
        chosen = random.choice(candidates)
        assumptions, extra_sectors = find_crystal_switch_connectivity(sector, chosen)

        # todo: probably need to handle connectability and check global pol before assignment and merge


        if limitation:
            assign_sector(limitation, chosen, info)
            del c_switch_sectors[chosen]
            c_switch_sectors[limitation.master_sector] = limitation
        else:
            if c_switch_sectors[chosen]:
                assign_sector(c_switch_sectors[chosen], sector, info)
            else:
                merge_sectors(chosen, sector, info)

# returns a couple things:
# first: it returns a dict of assumed connections door leads to doors (e.g. crys -> needy)
# second: additional sectors to merge
def find_crystal_switch_connectivity(needy_sector, switch_sector):
    door_options = {door for cl in needy_sector.descriptor.joined_constraints for cons in cl.values()
                    for door in cons.candidate_hangers if cons.crystal_needed}
    provided_doors = {door for cl in switch_sector.descriptor.joined_constraints for cons in cl.values()
                      for door, provided in cons.accessible_doors.items() if provided == CrystalBarrier.Either}
    # find matches
    matches = [{p: d} for d in door_options for p in provided_doors if hanger_from_door(d)==hook_from_door(p)]
    extra_sectors = []
    if len(matches) <= 0:
        pass
        # todo: if no matches, find a connecting sector from dungeon_map/info
        # the candidates may need a branching factor and the doors be accessible
        #     if the switch_sector is dumb like GT Compass and the switch door needs to be hooked anyway
    if len(matches) == 1:
        return next(iter(matches)), extra_sectors
    elif len(matches) > 1:
        assumptions = random.choice(matches)
        # todo: figure out associated extra sectors?
        return assumptions, extra_sectors
    # pick a match, set up the assumed connections? validate the choice, if bad alert upper loop that they need a new switch sector


def find_crystal_constraints(builders, info):
    crystal_needed_sectors = {}
    for b in builders.values():
        if not b.master_sector.c_switch:
            if any(all(c.crystal_needed for c in cl.values()) for cl in b.master_sector.descriptor.joined_constraints):
                crystal_needed_sectors[b.master_sector] = b
    for s in info.sector_pool:
        if not s.c_switch:
            if any(all(c.crystal_needed for c in cl.values()) for cl in s.descriptor.joined_constraints):
                crystal_needed_sectors[s] = None  # free agent
    return crystal_needed_sectors


def find_crystal_switches(builders, info):
    c_switch_sectors = {b.master_sector: b for b in builders.values() if b.master_sector.c_switch}
    c_switch_sectors.update({s: None for s in info.sector_pool if s.c_switch})
    return c_switch_sectors


def handle_crystal_switch_paths(dungeon_map, info):
    crystal_needed_sectors = find_crystal_path_constraints(dungeon_map, info)
    for sector, limitation in crystal_needed_sectors.items():
        pass


def find_crystal_path_constraints(builders, info):
    crystal_needed_sectors = {}
    for b in builders.values():
        if any(all(c.crystal_needed for c in cl.values()) for cl in b.master_sector.descriptor.joined_constraints):
            crystal_needed_sectors[b.master_sector] = b
    for s in info.sector_pool:
        if any(all(c.crystal_needed for c in cl.values()) for cl in s.descriptor.joined_constraints):
            crystal_needed_sectors[s] = None  # free agent
    return crystal_needed_sectors


def handle_directional_constraints(builders, info):
    # todo: master sector issues? exclude bosses?
    # problems is a list of pairs of restricted constraint list to the sector they belong to
    # need limitation thing?
    problems = [(cl, b.master_sector) for b in builders.values() for cl in b.master_sector.descriptor.joined_constraints
                if len(cl) == 1 and next(iter(cl.keys())) is not None]
    problems.extend([(cl, s) for s in info.sector_pool for cl in s.descriptor.joined_constraints if len(cl) == 1])
    sorted(problems, key=lambda prob: sum(next(iter(prob[0].items()))[1].benefits.values()))

    for constraint, sector in problems.items():
        if sum(constraint.benefits.values()) == 0:
            # dead end and needs a branching sector unless boss room?
            pass






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


class DungeonGenInfo:

    def __init__(self, gen_log, all_sectors, flags):
        self.gen_log = gen_log
        self.global_pole = GlobalPolarity(all_sectors)
        self.sector_pool = dict.fromkeys(all_sectors)
        self.flags = flags


class DoorFlags:
    def __init__(self):
        self.normal = False
        self.spiral = False
        self.straight = False
        self.ladder = False
        self.edges = False
        self.lobbies = False
        self.vanilla_traps = False
        self.warps_pits = False  # NotYetImplemented
        self.cave_interiors = False  # NotYetImplemented
        self.intratile = False   # NotYetImplemented

    def from_world(self, world, player):
        self.vanilla_traps = world.trap_door_mode[player] == 'vanilla'
        if world.intensity[player] >= 1:
            self.normal = True
            self.spiral = True
        if world.intensity[player] >= 2:
            self.straight = True
            self.ladder = True
            self.edges = True
        if world.intensity[player] >=3:
            self.lobbies = True
        return self


# ------------------------------ #
#         Data Section
# ------------------------------ #

dungeon_boss_regions = {
    'Eastern Boss': ['Eastern Palace'],
    'Desert Boss': ['Desert Palace', 'Desert Palace Back', 'Desert Palace Front'],
    'Hera Boss': ['Tower of Hera'],
    'Tower Agahnim 1': ['Agahnims Tower'],
    'PoD Boss': ['Palace of Darkness'],
    'Swamp Boss': ['Swamp Palace'],
    'Skull Boss': ['Skull Woods', 'Skull Woods Back', 'Skull Woods Front'],
    'Thieves Boss': ['Thieves Town'],
    'Ice Boss': ['Ice Palace'],
    'Mire Boss': ['Misery Mire'],
    'TR Boss': ['Turtle Rock'],
    'GT Agahnim 2': ['Ganons Tower'],
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