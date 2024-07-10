from collections import deque
from enum import Enum

from BaseClasses import CrystalBarrier
from Utils import flatten

from source.dungeon.DungeonGenerationCommon import hanger_from_door, hook_from_door
from source.dungeon.DungeonGen3 import CrystalConstraint


def do_transitivity_check(sector_list):
    all_outstanding_doors = []
    for s in sector_list:
        all_outstanding_doors.extend(s.outstanding_doors)

    # clear out neutral constraints - a n/s neutral might be needed as a portal (todo: could result in a false negative)
    c_info = ConstraintInfo(sector_list)
    neutral_constraints = [x for x in c_info.constraints if x.type == ConstraintType.Neutral]
    neutral_checks = []
    for c in neutral_constraints:
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
    t = Transitivity(all_outstanding_doors, unsatisfied_constraints)
    for sector in c_info.init_portals:
        t.append_sector_free(sector, c_info)
    initial_options = t.find_connectable_doors(c_info)
    queue = deque([(t, conn) for conn in initial_options])
    while queue:
        current, conn = queue.pop()
        new_t = current.connect_door(conn, c_info)
        if new_t.now_impossible():
            continue
        if not new_t.unsatisfied_constraints:
            return True
        new_options = new_t.find_connectable_doors(c_info)
        queue.extend([(new_t, conn) for conn in new_options])
    return False


class ConstraintInfo:
    def __init__(self, sector_list):
        self.constraints = []
        self.switch_doors = []
        self.init_portals = []
        self.door_sector_map = {}
        for s in sector_list:
            if s.portal and not s.portal.destination:
                self.init_portals.append(s)
            for d in s.outstanding_doors:
                self.door_sector_map[d] = s
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
    def __init__(self, door_list, constraint_list):
        self.remaining_doors = list(door_list)
        self.unconnected_doors = {}  # door -> potential crystal state
        self.door_path = []  # door choices made to get to this point
        self.connection_map = {}  # hard connections made
        self.crystal_switch_included = False

        # which constraints are satisfied and remaining?
        self.unsatisfied_constraints = list(constraint_list)
        self.satisfied_constraints = []

    def copy(self):
        copy = Transitivity(self.remaining_doors, self.unsatisfied_constraints)
        copy.unconnected_doors.update(self.unconnected_doors)
        copy.door_path.extend(self.door_path)
        copy.connection_map.update(self.connection_map)
        copy.crystal_switch_included = self.crystal_switch_included
        copy.satisfied_constraints.extend(self.satisfied_constraints)
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
        for d in doors_to_check:
            hanger_type = hanger_from_door(d)
            for available in self.unconnected_doors:
                if available == d:  # might allow self-connecting spirals someday here, not too important for logic though
                    continue
                if available.traversal_only:
                    if d.portalAble:
                        connectable_doors.append((d, available))
                else:
                    if hook_from_door(available) == hanger_type:
                        connectable_doors.append((d, available))
        connectable_doors.sort(key=lambda c: self.score_possible_connection(c, c_info))
        return connectable_doors

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
            return 2
        if constraint.type == ConstraintType.DeadEnd:
            return 1

    def connect_door(self, connection, c_info):
        t = self.copy()
        hanger, hook = connection  # we are attaching the hanger to the hook
        t.door_path.append(hanger)
        t.connection_map[hook] = hanger
        if hanger in c_info.switch_doors:
            t.crystal_switch_included = True

        # deal with reachabile remaining doors/unnconnected doors
        if hanger in t.remaining_doors:
            t.remaining_doors.remove(hanger)
        if hanger in t.unconnected_doors:
            del t.unconnected_doors[hanger]
        crystal_prop = t.unconnected_doors.pop(hook)
        reachability = c_info.door_sector_map[hanger].descriptor.reachability
        for pair in reachability[hanger]:
            reachable, new_crystal = pair
            # todo: decoupled doors? algorithm could be made more flexibile in that case? not sure it matters much
            if reachable != hanger and reachable in t.remaining_doors:  # second condition mean it hasn't been seen yet
                new_crystal = new_crystal if CrystalBarrier.Null != new_crystal else crystal_prop
                t.unconnected_doors[reachable] = new_crystal
                t.remaining_doors.remove(reachable)

        # deal with newly satisfied constraints
        new_unsatisfied_constraints = []
        for constraint in t.unsatisfied_constraints:
            if ConstraintType.Portal == constraint.type and hook in constraint.doors:
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
            else:
                new_unsatisfied_constraints.append(constraint)
        t.unsatisfied_constraints = new_unsatisfied_constraints

        return t

    def now_impossible(self):
        # need to figure out some useful shortcuts here
        return False

    def is_satisfied(self):
        for constraint in self.unsatisfied_constraints:
            if constraint.type != ConstraintType.DeadEnd:
                return False
        return True


