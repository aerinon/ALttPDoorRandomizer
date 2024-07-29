import heapq
import itertools
import logging
import time

from collections import deque, defaultdict, Counter
from enum import Enum

from BaseClasses import CrystalBarrier
from Utils import flatten

from source.dungeon.DungeonGenerationCommon import hanger_from_door, hook_from_door
from source.dungeon.DungeonGen3 import CrystalConstraint

logger = logging.getLogger('tlogger')
# for handler in logger.handlers[:]:
#     logger.removeHandler(handler)
# handler = logging.FileHandler('transitivity.log')
# handler.setLevel(logging.DEBUG)
# logger.addHandler(handler)

def do_transitivity_check(sector_list, limited_starting_points=None):
    logger.debug("Starting Transitivity Check")
    logger.debug(f"Sector List: {','.join(s.sector_key() for s in sector_list)}")
    start_time = time.process_time()
    if limited_starting_points is None:
        limited_starting_points = []
    all_outstanding_doors = []
    for s in sector_list:
        all_outstanding_doors.extend(s.outstanding_doors)

    # clear out neutral constraints - a n/s neutral might be needed as a portal (todo: could result in a false negative)
    c_info = ConstraintInfo(sector_list)
    neutral_constraints = [x for x in c_info.constraints if x.type == ConstraintType.Neutral]
    neutral_checks = []
    for c in neutral_constraints:
        if any(d.portalAble for d in c.doors):
            continue
        all_outstanding_doors = [x for x in all_outstanding_doors if x not in c.doors]
        neutral_checks.extend(c.doors)
    satisfied = True
    for d in neutral_checks:
        hanger = hanger_from_door(d)
        if all(hanger != hook_from_door(door) for door in all_outstanding_doors):
            satisfied = False
            break
    if not satisfied:
        return False
    unsatisfied_constraints = [x for x in c_info.constraints if x.type != ConstraintType.Neutral]

    # initialize portals
    t = Transitivity(all_outstanding_doors, unsatisfied_constraints, limited_starting_points)
    visited = set()
    for sector in c_info.init_portals:
        t.append_sector_free(sector, c_info)
    initial_options = t.find_connectable_doors(c_info)
    tiebreaker = itertools.count()
    queue = []
    for conn in initial_options:
        init_t = t.connect_door(conn, c_info)
        if not init_t.now_impossible(c_info, visited):
            if not init_t.unsatisfied_constraints:
                return True  # that was easy
            priority = init_t.priority()
            visited.add(frozenset(init_t.connection_map.items()))
            heapq.heappush(queue, (priority, -next(tiebreaker), init_t))
    iterations = 0
    while queue:
        iterations += 1
        priority_prev, ignored, current = heapq.heappop(queue)
        # logger.debug(f'TStats: Iteration {iterations}, Priority {priority_prev}, Depth {len(current.door_path)}, Constraints {len(current.unsatisfied_constraints)}')
        new_options = current.find_connectable_doors(c_info)
        for conn in new_options:
            new_t = current.connect_door(conn, c_info)
            if not new_t.now_impossible(c_info, visited):
                if not new_t.unsatisfied_constraints:
                    if iterations > 10000:
                        logger.warning(f'Transitivity check took {iterations} iterations for true result')
                    logger.debug(f'Finished transitivity check "True" in {time.process_time() - start_time} seconds and {iterations} iterations')
                    return True
                priority = new_t.priority()
                new_t_key = frozenset(new_t.connection_map.items())
                visited.add(new_t_key)
                heapq.heappush(queue, (priority, -next(tiebreaker), new_t))
    if iterations > 10000:
        logger.warning(f'Transitivity check took {iterations} iterations for false result')
    logger.debug(f'Finished transitivity check "False" in {time.process_time() - start_time} seconds and {iterations} iterations')
    return False


class ConstraintInfo:
    def __init__(self, sector_list):
        self.constraints = []
        self.switch_doors = []
        self.init_portals = []
        self.door_sector_map = {}
        self.shape_map = {}
        for s in sector_list:
            if s.portal and not s.portal.destination:
                self.init_portals.append(s)
            for d in s.outstanding_doors:
                self.door_sector_map[d] = s
                self.shape_map[d] = s.descriptor.shape_construct[d]
                if d.traversal_only:
                    self.constraints.append(Constraint(ConstraintType.Portal, [d], None))
                if d in s.descriptor.crystal_switch_doors:
                    self.switch_doors.append(d)
            if s.descriptor.must_enter_reqs:
                for req in s.descriptor.must_enter_reqs:
                    if isinstance(req, tuple):
                        self.constraints.append(Constraint(ConstraintType.MustEnter, list(req), None))
                    else:
                        self.constraints.append(Constraint(ConstraintType.MustEnter, [req], None))
            # special constraint (we can formulate as must enter for now, the trick is for the ice cross - no traps allowed)
            if s.descriptor.special_reqs:
                participants = flatten(s.descriptor.special_reqs)
                self.constraints.append(Constraint(ConstraintType.Special, participants, None))
            if s.descriptor.crystal_reqs:
                c_req = s.descriptor.crystal_reqs
                if c_req.type == 'any':
                    participants = flatten(c_req.must_have_color_access)
                    if c_req.must_enter_reqs:
                        participants += flatten(c_req.must_enter_reqs)
                    self.constraints.append(Constraint(ConstraintType.Crystal, participants, c_req))
                else:
                    for req in c_req.must_have_color_access:
                        new_req = CrystalConstraint()
                        new_req.must_have_color_access.append(req)
                        self.constraints.append(Constraint(ConstraintType.Crystal, flatten(req), new_req))
            if s.descriptor.dead_end and all(not d.traversal_only for d in s.outstanding_doors):
                self.constraints.append(Constraint(ConstraintType.DeadEnd, s.outstanding_doors, None))
            if s.descriptor.is_neutral:
                self.constraints.append(Constraint(ConstraintType.Neutral, s.outstanding_doors, None))

        self.door_constraint_map = defaultdict(list)
        for constraint in self.constraints:
            for d in constraint.doors:
                self.door_constraint_map[d].append(constraint)
        self.door_matches = defaultdict(list)
        for d in self.door_sector_map:
            for potential_match in self.door_sector_map:
                if d == potential_match:
                    continue
                if hanger_from_door(d) != hook_from_door(potential_match):
                    continue
                d_is_dead_end = d in self.door_constraint_map and any(c.type == ConstraintType.DeadEnd for c in self.door_constraint_map[d])
                d_is_must_enter = d in self.door_constraint_map and any(c.type == ConstraintType.MustEnter and d in c.doors and len(c.doors) == 1 for c in self.door_constraint_map[d])
                potential_is_dead_end = potential_match in self.door_constraint_map and any(c.type == ConstraintType.DeadEnd for c in self.door_constraint_map[potential_match])
                potential_is_must_enter = potential_match in self.door_constraint_map and any(c.type == ConstraintType.MustEnter and potential_match in c.doors and len(c.doors) == 1 for c in self.door_constraint_map[potential_match])

                if d.traversal_only:
                    if potential_match.traversal_only or not potential_match.portalAble:
                        continue
                    if self.door_sector_map[d].portal.destination and (potential_is_dead_end or potential_is_must_enter):
                        continue

                if potential_match.traversal_only:
                    if d.traversal_only or not d.portalAble:
                        continue
                    if self.door_sector_map[potential_match].portal.destination and (d_is_dead_end or d_is_must_enter):
                        continue

                # bad cases: dead end to dead end, must enter to must enter, dead end to must enter, must enter to dead end
                if ((d_is_dead_end and potential_is_dead_end)
                   or (d_is_must_enter and potential_is_must_enter)
                   or (d_is_dead_end and potential_is_must_enter)
                   or (d_is_must_enter and potential_is_dead_end)):
                    continue
                self.door_matches[d].append(potential_match)


class ConstraintType(Enum):
    MustEnter = 1
    Special = 2  # used for ice cross for now?
    Crystal = 3
    DeadEnd = 4
    Neutral = 5
    Portal = 6


class Constraint:

    def __init__(self, type, doors, constraint):
        self.type = type
        self.doors = list(doors)
        self.constraint = constraint


class Transitivity:
    def __init__(self, door_list, constraint_list, limited_starting_points):
        self.remaining_doors = list(door_list)
        self.unconnected_doors = {}  # door -> potential crystal state
        self.door_path = []  # door choices made to get to this point
        self.connection_map = {}  # hard connections made
        self.crystal_switch_included = False

        # which constraints are satisfied and remaining?
        self.unsatisfied_constraints = list(constraint_list)
        self.satisfied_constraints = []
        self.limited_starting_points = list(limited_starting_points)
        self.used_starting_points = []

    def copy(self):
        copy = Transitivity(self.remaining_doors, self.unsatisfied_constraints, self.limited_starting_points)
        copy.unconnected_doors.update(self.unconnected_doors)
        copy.door_path.extend(self.door_path)
        copy.connection_map.update(self.connection_map)
        copy.crystal_switch_included = self.crystal_switch_included
        copy.satisfied_constraints.extend(self.satisfied_constraints)
        copy.used_starting_points.extend(self.used_starting_points)
        return copy

    def append_sector_free(self, sector, c_info):
        for d in sector.outstanding_doors:
            self.remaining_doors.remove(d)
            self.unconnected_doors[d] = CrystalBarrier.Orange
            self.door_path.append(d)
            if d in c_info.switch_doors:
                self.crystal_switch_included = True

    # big task here - a lot of doors are "equivalent" logically for what we're checking
    # and so shouldn't be explored independently, not sure how to determine that here
    def find_connectable_doors(self, c_info):
        connectable_doors = []
        doors_to_check = list(self.unconnected_doors.keys()) + self.remaining_doors
        # check for forced doors first?
        for d, possibles in c_info.door_matches.items():
            if d not in self.unconnected_doors:
                continue
            options = [p for p in possibles if p in doors_to_check]
            if len(options) == 1:
                connectable_doors.append((options[0], d))

        if connectable_doors:
            return connectable_doors[:1]

        doors_to_check = self.winnow_doors_to_check(doors_to_check, c_info)
        doors_to_connect = self.get_unique_unconnected_doors(c_info)
        for d in doors_to_check:
            hanger_type = hanger_from_door(d)
            for available in doors_to_connect:
                if available == d:  # might allow self-connecting spirals someday here, not too important for logic though
                    continue
                if available.traversal_only:
                    if d.portalAble and (not self.limited_starting_points or d in self.limited_starting_points):
                        connectable_doors.append((d, available))
                else:
                    if hook_from_door(available) == hanger_type:
                        connectable_doors.append((d, available))
        connectable_doors.sort(key=lambda c: self.score_possible_connection(c, c_info))
        return connectable_doors

    @staticmethod
    def winnow_doors_to_check(doors_to_check, c_info):
        reachability_dict = {}
        for door in doors_to_check:
            # reachability = c_info.door_sector_map[door].descriptor.reachability
            # if door in reachability:
            #     reach_key = tuple(sorted({d.name: c for d, c in reachability[door]}.items()))  # Convert dict to tuple for hashing
            # else:
            #     reach_key = ()
            reach_key = (hanger_from_door(door),) + c_info.shape_map[door]
            reachability_dict[reach_key] = door  # If reachability is the same, the door will be overwritten
        return list(reachability_dict.values())  # Get the doors from the dictionary

    def get_unique_unconnected_doors(self, c_info):
        unique_dict = {}
        for door in self.unconnected_doors:
            reachability = c_info.door_sector_map[door].descriptor.reachability
            if door in reachability:
                reach_key = tuple(sorted({d.name: c for d, c in reachability[door]}.items()))  # Convert dict to tuple for hashing
            else:
                reach_key = ()
            unique_dict[(hook_from_door(door), self.unconnected_doors[door]) + reach_key] = door
        return list(unique_dict.values())

    def score_possible_connection(self, connection, c_info):
        if connection[0] in c_info.switch_doors and not self.crystal_switch_included:
            return 5
        best = 0
        for constraint in self.unsatisfied_constraints:
            if connection[0] in constraint.doors:
                new_score = self.score_against_constraint(connection, constraint)
                if new_score > best:
                    best = new_score
        return best

    def score_against_constraint(self, connection, constraint):
        if constraint.type == ConstraintType.MustEnter:
            return 4
        if constraint.type == ConstraintType.Special:
            return 3
        if constraint.type == ConstraintType.Crystal:
            if constraint.constraint.contains_color_access(connection[0]):
                crystal = self.unconnected_doors[connection[1]]
                if crystal in [CrystalBarrier.Blue, CrystalBarrier.Either, CrystalBarrier.Both]:
                    return 2
                return 0  # if it's not fulfilling a requirement, it's not a high priority
            if constraint.constraint.contains_color_access(connection[1]) and connection[0] in self.unconnected_doors:
                crystal = self.unconnected_doors[connection[0]]
                if crystal in [CrystalBarrier.Blue, CrystalBarrier.Either, CrystalBarrier.Both]:
                    return 2
                return 0
            return 2
        if constraint.type == ConstraintType.DeadEnd:
            return 1
        return 0

    def priority(self):
        # return 0
        # doors_left = len(self.remaining_doors) + len(self.unconnected_doors)
        # number of constraints satisfied per depth
        # extraneous_depth = len(self.door_path) - len(self.satisfied_constraints)
        # efficiency_ratio = len(self.satisfied_constraints) / len(self.door_path)
        # efficiency_score = (-extraneous_depth * 100) + len(self.door_path)  # depth bonus

        unsatisfied_crystal = False
        constraints_score = 0
        for constraint in self.unsatisfied_constraints:
            if constraint.type == ConstraintType.MustEnter:
                constraints_score += 4
            elif constraint.type == ConstraintType.Special:
                constraints_score += 3
            elif constraint.type == ConstraintType.Crystal:
                unsatisfied_crystal = True
                constraints_score += 2
            elif constraint.type in [ConstraintType.DeadEnd, ConstraintType.Portal]:
                constraints_score += 1
            else:
                constraints_score += 0.5
        if unsatisfied_crystal and not self.crystal_switch_included:
            constraints_score += 5
        score = len(self.door_path) / constraints_score  # penalize for unsatisfied constraints
        return -score  # for min-heap, need to negate priority

    def connect_door(self, connection, c_info):
        t = self.copy()
        hanger, hook = connection  # we are attaching the hanger to the hook
        t.door_path.append(hanger)
        t.connection_map[hook] = hanger
        t.connection_map[hanger] = hook
        if hanger in c_info.switch_doors:
            t.crystal_switch_included = True
        if t.limited_starting_points and hanger in t.limited_starting_points:
            t.limited_starting_points.remove(hanger)
            t.used_starting_points.append(hanger)

        # deal with reachabale remaining doors/unnconnected doors
        crystal_prop = t.unconnected_doors.pop(hook)
        backprop_queue = deque([])
        visited = set()
        if hanger in t.remaining_doors:
            t.remaining_doors.remove(hanger)
        if hanger in t.unconnected_doors:
            hanger_cs = t.unconnected_doors.pop(hanger)
            if not hanger.blocked:
                if crystal_prop == CrystalBarrier.Null and hanger_cs != CrystalBarrier.Null:
                    crystal_prop = hanger_cs
                if ((hanger_cs == CrystalBarrier.Blue and crystal_prop == CrystalBarrier.Orange) or
                   (hanger_cs == CrystalBarrier.Orange and crystal_prop == CrystalBarrier.Blue)):
                    crystal_prop = CrystalBarrier.Both
                if hanger_cs in [CrystalBarrier.Either, CrystalBarrier.Both]:
                    crystal_prop = hanger_cs

        # back-propagate crystal state - through queue
        if not hanger.blocked and crystal_prop not in [CrystalBarrier.Either, CrystalBarrier.Both]:
            hook_reach = c_info.door_sector_map[hook].descriptor.reachability
            if hook in hook_reach and hook_reach[hook]:
                self_hook = next((pair for pair in hook_reach[hook] if pair[0] == hook), None)
                if self_hook and self_hook[1] == CrystalBarrier.Either:
                    crystal_prop = self_hook[1]
        reachability = c_info.door_sector_map[hanger].descriptor.reachability
        for pair in reachability[hanger]:
            reachable, new_crystal = pair
            new_crystal = new_crystal if CrystalBarrier.Null != new_crystal else crystal_prop
            # todo: decoupled doors? algorithm could be made more flexibile in that case? not sure it matters much
            if reachable != hanger and reachable in t.remaining_doors:  # second condition mean it hasn't been seen yet
                t.unconnected_doors[reachable] = new_crystal
                t.remaining_doors.remove(reachable)
            if reachable == hanger and new_crystal != CrystalBarrier.Null:
                backprop_queue.append((hook, new_crystal))
                visited.add((hook, new_crystal))

        # special handling for ice cross and similar cases
        if not hanger.blocked:
            reachability = c_info.door_sector_map[hook].descriptor.reachability
            for pair in reachability[hook]:
                reachable, new_crystal = pair
                if reachable != hook and reachable in t.remaining_doors:
                    new_crystal = new_crystal if CrystalBarrier.Null != new_crystal else crystal_prop
                    t.unconnected_doors[reachable] = new_crystal
                    t.remaining_doors.remove(reachable)

        while backprop_queue:
            backprop_door, new_crystal = backprop_queue.pop()
            reachability = c_info.door_sector_map[backprop_door].descriptor.reachability
            for pair in reachability[backprop_door]:
                reachable, c_prop = pair
                if reachable != backprop_door:
                    if reachable in t.unconnected_doors:
                        if t.unconnected_doors[reachable] not in [CrystalBarrier.Either, CrystalBarrier.Both] and new_crystal in [CrystalBarrier.Either, CrystalBarrier.Both]:
                            t.unconnected_doors[reachable] = new_crystal
                    if reachable in t.connection_map:
                        if c_prop == CrystalBarrier.Null:
                            target = t.connection_map[reachable]
                            if (target, new_crystal) not in visited:
                                visited.add((target, new_crystal))
                                backprop_queue.append((target, new_crystal))

        # deal with newly satisfied constraints
        new_unsatisfied_constraints = []
        for constraint in t.unsatisfied_constraints:
            if ConstraintType.Portal == constraint.type and (hook in constraint.doors or hanger in constraint.doors):
                t.satisfied_constraints.append(constraint)
            elif hanger in constraint.doors:
                if constraint.type in [ConstraintType.MustEnter, ConstraintType.Special, ConstraintType.DeadEnd]:
                    t.satisfied_constraints.append(constraint)
                elif constraint.type == ConstraintType.Crystal:
                    if (not constraint.constraint.contains_color_access(hanger)
                            or crystal_prop in [CrystalBarrier.Blue, CrystalBarrier.Either, CrystalBarrier.Both]):
                        t.satisfied_constraints.append(constraint)
                    else:
                        new_unsatisfied_constraints.append(constraint)
                else:
                    new_unsatisfied_constraints.append(constraint)
            # fulfill color required by back propagation
            elif hook in constraint.doors:
                if constraint.type == ConstraintType.Crystal:
                    if (constraint.constraint.contains_color_access(hook)
                            and crystal_prop in [CrystalBarrier.Blue, CrystalBarrier.Either, CrystalBarrier.Both]):
                        t.satisfied_constraints.append(constraint)
                    else:
                        new_unsatisfied_constraints.append(constraint)
            else:
                new_unsatisfied_constraints.append(constraint)
        t.unsatisfied_constraints = new_unsatisfied_constraints

        return t

    def now_impossible(self, c_info, visited_states):
        if frozenset(self.connection_map.items()) in visited_states:
            return True
        if len(self.unconnected_doors) == 0 and self.unsatisfied_constraints:
            return True

        total_needed_per_type = defaultdict(list)
        forced_list = []
        for constraint in self.unsatisfied_constraints:
            if constraint.type == ConstraintType.MustEnter:
                if all(d not in self.remaining_doors and d not in self.unconnected_doors for d in constraint.doors):
                    return True
                if len(constraint.doors) == 1:
                    forced_door = constraint.doors[0]
                    total_needed_per_type[hanger_from_door(forced_door)].append(forced_door)
                    forced_list.append(forced_door)
            elif constraint.type == ConstraintType.Crystal:
                if all(d not in self.remaining_doors and d not in self.unconnected_doors for d in constraint.doors):
                    return True
            elif constraint.type == ConstraintType.DeadEnd:
                forced_door = constraint.doors[0]
                total_needed_per_type[hanger_from_door(forced_door)].append(forced_door)
                forced_list.append(forced_door)
        available_per_type = defaultdict(list)
        for door in self.remaining_doors + list(self.unconnected_doors.keys()):
            if door not in forced_list:
                available_per_type[hook_from_door(door)].append(door)
        for hanger, needed in total_needed_per_type.items():
            if len(available_per_type[hanger]) < len(needed):
                return True
        if self.check_for_forced_connections(available_per_type, total_needed_per_type, c_info):
            return True

        # branches vs dead-ends
        balance = len(self.unconnected_doors)
        sectors_to_check = {c_info.door_sector_map[d] for d in self.remaining_doors}
        for sector in sectors_to_check:
            if sector.portal and not sector.portal.destination:
                balance += 1
            else:
                doors = [d for d in sector.outstanding_doors if d in self.remaining_doors]
                best = max(sum(1 for item in sector.descriptor.reachability[d] if item[0] in self.remaining_doors) for d in doors)
                missing_doors = len(doors) - best
                balance += best - 2 - missing_doors
        if balance < 0:
            return True

        # crystal switch death - self limited
        # if all(d not in self.unconnected_doors and d not in self.remaining_doors for d in c_info.switch_doors):
        #     if all()
        return False

    @staticmethod
    def check_for_forced_connections(available_per_type, total_needed_per_type, c_info):
        def init(t, a):
            new_t = defaultdict(list)
            new_t.update({k: list(v) for k, v in t.items()})
            new_a = defaultdict(list)
            new_a.update({k: list(v) for k, v in a.items()})
            return new_t, new_a

        transformed = True
        new_total_needed, new_available = init(total_needed_per_type, available_per_type)
        while transformed:
            transformed = False
            new_total_needed, new_available = init(new_total_needed, new_available)
            potentially_forced = [hanger for hanger, needed in new_total_needed.items() if len(new_available[hanger]) == len(needed)]
            if potentially_forced:
                hanger = next(iter(potentially_forced))
                removals = []
                new_required, num_satisfied = [], 0
                for d in new_available[hanger]:
                    reachability = c_info.door_sector_map[d].descriptor.reachability[d]
                    if len(reachability) == 2:
                        potentials = [a for a, b in reachability if a != d and (a in new_available[hook_from_door(a)] or a in new_total_needed[hanger_from_door(a)])]
                        if len(potentials) == 1:
                            removals.append((hanger, d))
                            removals.append((hook_from_door(potentials[0]), potentials[0]))
                            new_required.append((hanger_from_door(potentials[0]), potentials[0]))
                            num_satisfied += 1
                if removals:
                    transformed = True
                    for h, r in removals:
                        new_available[h].remove(r)
                    del new_total_needed[hanger][:num_satisfied]
                    for h, r in new_required:
                        if r not in new_total_needed[h]:
                            new_total_needed[h].append(r)
        for hanger, needed in new_total_needed.items():
            if len(new_available[hanger]) < len(needed):
                return True
        return False

    def is_satisfied(self):
        for constraint in self.unsatisfied_constraints:
            if constraint.type != ConstraintType.DeadEnd:
                return False
        return True


