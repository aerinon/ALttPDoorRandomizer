from collections import defaultdict, deque

from BaseClasses import Hook, CrystalBarrier, DoorType

from source.dungeon.DungeonGenerationCommon import hanger_from_door, hook_from_door, GenerationException


# 'Ice Portal'

# Dead Ends
# 'Ice Antechamber', 'TR Refill', 'Mire Chest View', 'Ice Compass Room', 'Hera Tile Room', 'PoD Big Chest Balcony'

# Must Enters
# 'GT Big Key Room', 'GT Frozen Over', 'Thieves Lobby'

# Special
# 'Ice Bomb Drop'

# Neutral
# 'TR Lava Escape', 'Skull Star Pits', 'PoD Conveyor', 'Tower Dark Archers', 'Sewers Dark Cross'

# Other
# 'TR Torches', 'Sewers Pull Switch', 'Swamp Left Elbow', 'Ice Spike Room'

# pseudo code

# Categorize into groups (Dead End, Must Enter, Portals, Neutral, Other, Special)
# Find valid starting points (dead ends aren't)
#   Bob's, Ice Cross S, Lava, Skull, PoD Cov, Pull Switch, Swamp Pull Statue
#   Portalable neutrals could be satisfied here without any loss of generality
    # Satisfy: Lava, Skull, Convey, Dark Cross
#   Prefer Must-Exit,Special over Other
#   Bob's -> Ice Cross -> Sewers Pull/Swamp Left Elbow
# Bob's Chosen
#   Satisfy: Tower Dark Archers
# How to Expand. Note Frozen, Lobby needs Torches, Spike connectors. No other options.
# Which do you connect to which? Best option is Spike Room > TT Lobby, but only because of lookahead
    # Recalc reachability?
# Must-enters now Either Ice Spike Stair or TR Torch south

# Choose Ice Spike Stair
# Avail hangers: ice spike stair + either frozen stair or lobby nx2/s
# Poor choice: 2 stairs avail
# Pull Switch or Swamp Left, either gets 1 S
#


def do_transitivity_check(sector_list, starting_point_list):
    door_sector_map = {d: s for s in sector_list for d in s.outstanding_doors}

    init_state = Transitivity(sector_list, starting_point_list)
    init_state.initialize()
    queue = deque([init_state])
    while len(queue) > 0:
        current_state = queue.pop()
        if current_state.next_door is None:
            if len(current_state.sector_list) == 0:  # everything is satisfied
                return True
            # find next doors to explore
            constraints = current_state.find_next_constraints()
            if len(constraints) == 0:
                # no more constraints to fill - check others/neutrals
                changed = True
                available_hooks = {hook_from_door(d) for d in current_state.explored_doors}
                while changed:
                    changed = False
                    satisfied = []
                    for s in current_state.others:
                        if any(hanger_from_door(d) in available_hooks for d in s.outstanding_doors):
                            satisfied.append(s)
                            more_hooks = {hook_from_door(d) for d in s.outstanding_doors}
                            if any(h not in available_hooks for h in more_hooks):
                                available_hooks.update(more_hooks)
                                changed = True
                    for s in satisfied:
                        current_state.others.remove(s)
                        current_state.sector_list.remove(s)
                    satisfied = []
                    for s in current_state.neutrals:
                        if any(hanger_from_door(d) in available_hooks for d in s.outstanding_doors):
                            satisfied.append(s)
                    for s in satisfied:
                        current_state.neutrals.remove(s)
                        current_state.sector_list.remove(s)
                return len(current_state.sector_list) == 0
            for next_door in constraints:
                child_state = current_state.copy()
                child_state.next_door = next_door
                queue.append(child_state)
        else:
            found_paths = current_state.find_possible_hooks()
            for path in found_paths:
                next_state = current_state.copy()
                for idx in range(len(path.sector_path), 0, -1):
                    sector = path.sector_path[idx-1]
                    hooked_door, priority_hangers, the_rest = None, [], []
                    for hanger in path.hangers:
                        if any(hanger == req or (isinstance(req,tuple) and hanger in req) for req in current_state.must_enters):
                            priority_hangers.append(hanger)
                        else:
                            the_rest.append(hanger)
                    for hanger in priority_hangers:
                        hooks = next_state.get_possible_hooks(hanger)
                        if len(hooks) > 0:
                            hooked_door = hanger
                            break
                    if hooked_door is None:
                        for hanger in the_rest:
                            hooks = next_state.get_possible_hooks(hanger)
                            if len(hooks) > 0:
                                hooked_door = hanger
                                break
                    next_state.append_door(hooked_door, sector)

                constrained_sector = door_sector_map[path.origin_door]
                next_state.append_door(path.origin_door, constrained_sector)
                next_state.next_door = None
                queue.append(next_state)


    return False  # no valid transitivity found



# state class
class Transitivity:

    def __init__(self, sector_list=None, starting_points=None):

        # mutable state
        self.explored_doors = set()  # reached doors
        self.current_hooks = defaultdict(list)  # hook -> doors
        self.door_path = []
        self.next_door = None

        self.sector_list = sector_list
        self.starting_points = starting_points
        self.connected_sectors = []
        self.connection_map = {}

        # categories
        self.must_enters = {}  # door -> sector
        self.specials = {}  # tuple of doors -> sector?
        self.crystal_needs = {}  # tuple fo doors -> sector?
        self.dead_ends = {}
        self.sector_reqs = defaultdict(list)  # sector -> constraint list

        self.others = []
        self.neutrals = []

        self.switch_providers = []

    def copy(self):
        copy = Transitivity()
        copy.explored_doors.update(self.explored_doors)
        copy.current_hooks.update({k: list(v) for k, v in self.current_hooks.items()})
        copy.door_path.extend(self.door_path)
        copy.next_door = self.next_door

        copy.sector_list = self.sector_list.copy()
        copy.starting_points = self.starting_points.copy()
        copy.connected_sectors.extend(self.connected_sectors)
        copy.connection_map.update(self.connection_map)

        copy.must_enters.update(self.must_enters)
        copy.specials.update(self.specials)
        copy.crystal_needs.update(self.crystal_needs)
        copy.dead_ends.update(self.dead_ends)
        copy.sector_reqs.update({k: list(v) for k, v in self.sector_reqs.items()})

        copy.others.extend(self.others)
        copy.neutrals.extend(self.neutrals)
        copy.switch_providers.extend(self.switch_providers)
        return copy

    def initialize(self):
        free_portals = []
        for s in self.sector_list:
            if s.portal and not s.portal.destination:  # this doesn't handle dependent sectors, yet
                self.append_sector_free(s)
                free_portals.append(s)
        self.connected_sectors.extend(free_portals)
        self.sector_list = [s for s in self.sector_list if s not in free_portals]
        self.classify_sectors()

    def classify_sectors(self):
        for s in self.sector_list:
            if s.descriptor.dead_end:
                d = next(iter(s.outstanding_doors))
                self.dead_ends[d] = s
                self.sector_reqs[s].append(d)
            else:
                if s.descriptor.must_enter_reqs:
                    for req in s.descriptor.must_enter_reqs:
                        self.must_enters[req] = s
                        self.sector_reqs[s].append(req)
            if s not in self.sector_reqs:
                if s.descriptor.is_neutral:
                    self.neutrals.append(s)
                else:
                    self.others.append(s)
            if s.c_switch:
                self.switch_providers.append(s)

    def append_sector_free(self, sector):
        for d in sector.outstanding_doors:
            self.explored_doors.add(d)
            self.door_path.append(d)
            self.current_hooks[Hook.NormalPortal].append(d)

    def find_next_constraints(self):
        if len(self.must_enters) > 0:
            # order them? hookable now better score than not, also those that provide more hooks
            return list(self.must_enters.keys())
        if len(self.dead_ends) > 0:
            return list(self.dead_ends.keys())
        return []

    def find_possible_hooks(self):
        door_set = self.next_door if isinstance(self.next_door, tuple) else (self.next_door,)
        solutions = []
        for d in door_set:
            if len(self.get_possible_hooks(d)) > 0:
                solutions.append(Path([d], d))
        if solutions:
            return solutions

        # look for intervening sectors using others
        current_depth = 0
        init_paths = []
        for d in door_set:
            init_paths.append(Path([d], d))
        found_paths = deque(init_paths)

        while len(found_paths) > 0:
            path = found_paths.popleft()
            if len(path.sector_path) > current_depth:
                if len(solutions) > 0:
                    return solutions
                else:
                    current_depth = len(path.sector_path)
            if any(len(self.get_possible_hooks(hanger)) for hanger in path.hangers):
                solutions.append(path)
                continue
            candidates = [s for s in self.sector_list if s not in path.sector_path
                          and not s.descriptor.dead_end and not s.descriptor.is_neutral]
            if len(path.sector_path) >= len(candidates):
                continue
            for s in candidates:
                done_hooks = []
                for d in s.outstanding_doors:
                    # don't hook to your self or to a hard must-enter requirement
                    if d == path.origin_door or d in self.must_enters:
                        continue
                    hook = hook_from_door(d)
                    if hook in done_hooks:
                        continue
                    if any(hook == hanger_from_door(h) for h in path.hangers):
                        child_path = path.copy()
                        child_path.sector_path.append(s)
                        child_path.connection_type.append(hook)
                        child_path.hangers = [door for door in s.outstanding_doors if door != d]
                        found_paths.append(child_path)
                        done_hooks.append(hook)
        if len(solutions) > 0:
            return solutions
        return None

    def get_possible_hooks(self, door):
        # non-starting point portals? not sure, I have to worry about that
        if door.portalAble and door in self.starting_points and len(self.current_hooks[Hook.NormalPortal]) > 0:
            return self.current_hooks[Hook.NormalPortal]
        return self.current_hooks[hanger_from_door(door)]

    def append_door(self, door, sector):
        self.door_path.append(door)
        if door.portalAble and len(self.current_hooks[Hook.NormalPortal]):
            hook_to_use = Hook.NormalPortal
        else:
            hook_to_use = hanger_from_door(door)
        used_door = self.current_hooks[hook_to_use].pop()  # shouldn't matter which?
        self.connection_map[used_door] = door
        self.explored_doors.add(door)
        # todo: I think decoupled doors has diff logic here
        new_doors = {d for d, c in sector.descriptor.reachability[door] if d != door and d not in self.explored_doors}
        self.explored_doors.update(new_doors)
        for d in new_doors:
            if d.type != DoorType.Logical:
                self.current_hooks[hook_from_door(d)].append(d)

        # todo: alter specials, crystal_needs, neutral?
        must_enter = self.find_must_enter_by_door(door)
        if must_enter is not None:
            del self.must_enters[must_enter]
        if door in self.dead_ends:
            del self.dead_ends[door]
        if sector in self.sector_reqs:
            req = self.find_sector_req_by_door(sector, door)
            if req is not None:
                self.sector_reqs[sector].remove(req)
                if len(self.sector_reqs[sector]) == 0:
                    del self.sector_reqs[sector]
                    self.connected_sectors.append(sector)
                    self.sector_list.remove(sector)
        else:
            if sector in self.others:
                self.connected_sectors.append(sector)
                self.sector_list.remove(sector)
                self.others.remove(sector)

    def find_must_enter_by_door(self, door):
        for req in self.must_enters:
            if door == req:
                return req
            elif isinstance(req, tuple) and door in req:
                return req
        return None

    def find_sector_req_by_door(self, sector, door):
        for req in self.sector_reqs[sector]:
            if req == door:
                return req
            elif isinstance(req, tuple) and door in req:
                return req
        return None


class Path:

    def __init__(self, hangers, origin=None):
        self.sector_path = []  # tuple of type used + sector at each step
        self.connection_type = []
        self.hangers = hangers
        self.origin_door = origin

    def copy(self):
        path = Path(self.hangers)
        path.sector_path.extend(self.sector_path)
        path.connection_type.extend(self.connection_type)
        path.origin_door = self.origin_door
        return path



# Portal: 'Eastern Portal'
# Dead Ends: 'Eastern Boss', 'TR Roller Room', 'TR Compass Room', 'Thieves Big Chest Nook', 'PoD Shooter Room'
# Must_Enter: 'GT Beam Dash', 'GT Hidden Star', 'GT Compass Room', 'Ice Big Key', 'Eastern Compass Room', 'Tower Altar'
# Other: 'Mire Lobby', 'PoD Bow Statue Left', 'Desert Big Chest Room', 'Desert Compass Room',
#        'Hyrule Castle East Hall', 'TR Torches', 'Ice Hammer Block', 'Ice Lonely Freezor', 'Thieves Compass Room',
#         'Hyrule Dungeon South Abyss'
# Crystal "Must Enter": 'Thieves Attic'
# Neutral:

# Providers: 'GT Compass Room', 'PoD Bow Statue Left'

# Portable must-enters: 'Eastern Compass Room'
# Look for starting points: [TR Roller Room SW, Mire Lobby S, PoD Mimics 2 SW, Desert East Lobby S, Eastern Hint Tile Blocked Path SE, Hyrule Castle East Hall SW, Hyrule Castle East Hall S]
# Eliminate dead-ends [Mire Lobby S, PoD Mimics 2 SW, Desert East Lobby S, Eastern Hint Tile Blocked Path SE, Hyrule Castle East Hall SW, Hyrule Castle East Hall S]

# What are your options that you can satisfy:
# Constraints to satisfy: must_enters, specials (one of several options), crystals, dead-ends, neutrals

# One path: Compass, Hidden, Ice Big, Beam Dash, GT Compass
# 2 E Eastern Compass
# 2 E, 1 S, 1 N pick an E, (Hidden Star) find Thieves Compass Room which has 2 W
# 1W, 1E, 2N open: pick Ice Big Key because open
# 1E, 2W, 1N: pick other E b/c W
# 1 Str, 1W, 1E, 1N: pick S because that's what left' need a S, and any open thing: PoD Bow statue double S works
# 1 Str, 1W, 2E : Must empty gone, crystal PoD Bow -> Thieves Compass -> Beam Dash -> Attic
# 1W, 3E: Nook
# 3E: HC East, Torches, HC South Abyss (Must be this way)
# 2N, 2S: Boss, Roller, Compass
# 1S: Ice Hammer (or Lonely Freezor)
# 1 Str: PoD Shooter
# Lobby + Lonely = either 1S/1N or 2 Str basically neutral
# Tower Altar can fit anywhere


# Crystal notes, getting the crystal provider attached early close to the portal is great
# Could also attach directly or indirectly, but may have lots of variations in the indirect space

# Potential preferences for must-exits:
# Portable and portal available
# Crystal switch provider
# Door type available without any extra sectors
# Those that need to search extra sectors to connect


# Cleanup: ensure the unvisited sectors are neutral



# [Desert Back Portal, Thieves Lobby, PoD Arena Ledge, PoD Left Cage, Eastern Cannonball Ledge, Mire Cross, Mire Ledgehop, Desert Arrow Pot Corner]


# Portal: Desert Back Portal
# Dead Ends: PoD Arena Ledge
# Must_Enter: Thieves Lobby
# Other: PoD Left Cage, Mire Cross, Mire Ledgehop, Desert Arrow Pot Corner
# Crystal "Must Enter": XXX
# Neutral: Eastern Cannonball Ledge

