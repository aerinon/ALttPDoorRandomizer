from collections import defaultdict, deque

from BaseClasses import Direction, RegionType, CrystalBarrier, flooded_keys
from Regions import dungeon_events, flooded_keys_reverse
from source.dungeon.DungeonStitcher import ExplorableDoor


class SectorDescriptor:
    def __init__(self, sector):
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
        self.constraints = []  # conjunction of constraints needed
        self.parity_id = ''
        self.init_parity_id()

    def init_parity_id(self):
        dir_map = defaultdict(int)
        for door in self.sector.outstanding_doors:
            dir_map[door.direction] += 1
        for ind, keys in {'n': [Direction.North], 's': [Direction.South], 'e': [Direction.East],
                          'w': [Direction.West], 'sp': [Direction.Up, Direction.Down]}.items():
            amt = sum(dir_map[x] for x in keys)
            if amt:
                self.parity_id += f'{ind}{amt}'

        # constraints - could memoize likely key would be frozenset of door names?
        # todo: vanilla traps
        # which outstanding doors are reachable from which outstanding doors
        for door in self.sector.outstanding_doors:
            state = SimpleExplorationState()
            state.extend_reachable_state(door)
            for explorable in state.unattached_doors:
                restrict = "Blue" if explorable.crystal == CrystalBarrier.Blue else "None"
                self.reachability[door.name].append((explorable.door.name, restrict))
        # create constraints
        reverse_reachability = defaultdict(list)
        for door in self.sector.outstanding_doors:
            for source, reachables in self.reachability.items():
                for reachable, restriction in reachables:
                    if reachable == door.name:
                        reverse_reachability[door.name].append((source, restriction))
        complete_doors = {k: v for k, v in self.reachability.items() if len(v) == self.degree}
        if len(complete_doors) == self.degree:  # all doors reach
            unrestricted = [k for k, v in self.reachability.items() if all(x[1] == 'None' for x in v)]
            if len(unrestricted) != self.degree: # otherwise, no constraint needed
                if len(unrestricted) > 0:  # not all doors reach without blue
                    self.create_constraint(unrestricted)
                else:
                    self.create_constraint(self.reachability.keys(), True)
        elif len(complete_doors) > 0:  # some doors reach all
            unrestricted = [k for k, v in complete_doors.items() if all(y[1] == 'None' for y in v)]
            if len(unrestricted) > 0:  # those that reach all without constraint
                self.create_constraint(unrestricted)
            else:  # they all require blue
                self.create_constraint(complete_doors.keys(), True)
        else:
            # todo: Ice Cross
            # the case where there's no door that reaches everything
            most_doors = sorted([(k, v) for k, v in self.reachability.items()], key=lambda x: len(x[1]))
            chosen_door_pair_list = [most_doors.pop()]
            chosen_set = {x[0] for k, v in chosen_door_pair_list for x in v}
            total_set = {x.name for x in self.sector.outstanding_doors}
            while len(chosen_set) < len(total_set):
                if len(most_doors) == 0:
                    sector_doors = ', '.join([x.name for x in self.sector.outstanding_doors])
                    raise Exception(f'Problem with determining constraints for a sector: {sector_doors}')
                lacking_set = total_set.difference(chosen_set)
                choices = {}
                best_choice, best_amt = -1, len(lacking_set)
                # reverse may be more efficient?
                for idx, door_pair in enumerate(most_doors):
                    candidate_set = {x[0] for x in door_pair[1]}
                    choices[idx] = candidate_set
                    reduction = len(lacking_set.difference(candidate_set))
                    if reduction < best_amt:
                        best_amt = reduction
                        best_choice = idx
                if best_choice == -1:
                    best_choice = len(most_doors) - 1
                    next = most_doors.pop()
                else:
                    next = most_doors.pop(best_choice)
                chosen_door_pair_list.append(next)
                chosen_set.update(choices[best_choice])
            for d, c in chosen_door_pair_list:
                self.create_constraint(d, c != 'None')

    def create_constraint(self, door_crystal_pair_list, constrained=False):
        constraint = SectorConstraint(constrained)
        constraint.doors.extend(x[0] for x in door_crystal_pair_list)
        self.constraints.append(constraint)

    def __str__(self):
        return f'{self.name}:{self.parity_id}'


class SectorConstraint:
    def __init__(self, crystal_needed=False):
        self.doors = []  # disjunction of doors, any door will do
        self.crystal_needed = crystal_needed



class SimpleExplorationState:
    def __init__(self):
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
            self.crystal = explorable_door.crystal
            connect_region = explorable_door.door.entrance.connected_region
            if connect_region is not None and not self.visited(connect_region):
                self.visit_region(connect_region)

    def next_avail_door(self):
        exp_door = self.avail_doors.pop()
        self.crystal = exp_door.crystal
        return exp_door

    def visit_region(self, region):
        if region.crystal_switch and self.crystal == CrystalBarrier.Null:
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
                if self.can_traverse_ignore_traps(door):
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
        else:
            door_list.append(ExplorableDoor(door, door.crystal, flag))
