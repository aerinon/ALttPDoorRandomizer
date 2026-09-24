"""Independent validation of the connection map behind a True Transitivity verdict.

Pairing and pit-group rules are checked directly. Reachability walks the world region graph with the same crystal
rules as CollectionState.traverse_world, ignoring keys and item requirements.
"""
from collections import deque

from BaseClasses import CollectionState, CrystalBarrier, DoorType, RegionType
from source.dungeon.DungeonGenerationCommon import hanger_from_door, hook_from_door

ONE_WAY = (DoorType.Hole, DoorType.Warp)


def _compatible(a, b):
    return hanger_from_door(a) == hook_from_door(b) or hanger_from_door(b) == hook_from_door(a)


def check_pairings(cmap, considered):
    """Returns (problems, group_terminal)."""
    problems = []
    group_terminal, terminal_group = {}, {}
    for a, b in cmap.items():
        if cmap.get(b) is not a:
            problems.append(f'asymmetric: {a.name} -> {b.name}')
        if not _compatible(a, b):
            problems.append(f'incompatible: {a.name} <-> {b.name}')
        if a.type in ONE_WAY:
            if b.type != DoorType.Terminal:
                problems.append(f'one-way to non-terminal: {a.name} -> {b.name}')
                continue
            prev = group_terminal.setdefault(a.group, b)
            if prev is not b:
                problems.append(f'split group {a.group}: {prev.name} and {b.name}')
            prev_group = terminal_group.setdefault(b, a.group)
            if prev_group != a.group:
                problems.append(f'terminal {b.name} shared by {prev_group} and {a.group}')

    # completion: groups without a terminal must match free terminals one-to-one
    leftover_groups = {d.group for d in considered if d.type in ONE_WAY} - set(group_terminal)
    leftover_terminals = [d for d in considered if d.type == DoorType.Terminal and d not in cmap]
    if len(leftover_groups) != len(leftover_terminals):
        problems.append(f'leftover mismatch: groups {sorted(leftover_groups)} vs terminals '
                        f'{sorted(t.name for t in leftover_terminals)}')
    return problems, group_terminal


def _impassable(door, respect_traps):
    """Mirrors SimpleExplorationState: traps only block when trap doors stay vanilla; true one-ways always block."""
    door = door.controller if door.controller is not None else door
    return door.blocked and (respect_traps or door.trapFlag == 0)


def explore(starts, cmap, group_terminal, allowed, respect_traps=True, rrp=None):
    """Region -> crystal states reached, following CollectionState.traverse_world's crystal rules."""
    partner_by_name = {d.name: p for d, p in cmap.items()}
    rrp = {} if rrp is None else rrp
    queue = deque((r, CrystalBarrier.Orange) for r in starts)
    while queue:
        region, state = queue.popleft()
        if region not in allowed:
            continue
        if region in rrp:
            if (rrp[region] & state) == state:
                continue
            state |= rrp[region]
        rrp[region] = state
        for ext in region.exits:
            door = ext.door
            partner = partner_by_name.get(ext.name)
            if partner is not None:
                nxt = partner.entrance.parent_region
            elif ext.connected_region is not None:
                nxt = ext.connected_region  # includes pits/warps already wired when not shuffled
            elif door is not None and door.controller is not None:
                nxt = door.controller.entrance.parent_region  # dependent door (e.g. Ice Cross push blocks), as in SimpleExplorationState
            elif door is not None and door.type in ONE_WAY:
                terminal = group_terminal.get(door.group)
                nxt = terminal.entrance.parent_region if terminal is not None else None
            else:
                nxt = None
            if nxt is None:
                continue
            if door is None:
                queue.append((nxt, state))
                continue
            if _impassable(door, respect_traps) or not CollectionState.valid_crystal(door, state):
                continue
            queue.append((nxt, door.crystal if door.crystal else state))
    return rrp


def start_regions(c_info):
    """Start portals, plus regions entered by an overworld drop (an entrance from outside the dungeon)."""
    starts = []
    for s in c_info.init_portals:
        portal_regions = [r for r in s.regions if r.name.endswith(' Portal')]
        starts.extend(portal_regions or s.regions)
    for s in c_info.sector_list:
        for r in s.regions:
            if r.name.endswith(' Portal'):
                continue
            if any(e.parent_region is not None and e.parent_region.type != RegionType.Dungeon
                   for e in r.entrances):
                starts.append(r)
    return starts


def explore_with_dependents(c_info, cmap, group_terminal, allowed):
    """Entering the sector of an enabling portal makes its dependent portal's door reachable via the overworld."""
    respect_traps = c_info.flags.vanilla_traps
    reached = explore(start_regions(c_info), cmap, group_terminal, allowed, respect_traps)
    changed = True
    while changed:
        changed = False
        for sector in c_info.sector_list:
            if not any(r in reached for r in sector.regions):
                continue
            for p in sector.portals:
                enabled = c_info.dependent_lookup.get(p.door)
                if enabled is not None and enabled.entrance.parent_region not in reached:
                    explore([enabled.entrance.parent_region], cmap, group_terminal, allowed, respect_traps, reached)
                    changed = True
    return reached


def check_witness(solution):
    """Independently validates a TransitivitySolution. Returns a list of problems; empty means valid."""
    cmap = solution.state.connection_map
    considered = solution.considered_doors
    problems, group_terminal = check_pairings(cmap, considered)
    if solution.c_info is None:
        return problems

    considered_set = set(considered)
    must_reach = {r for s in solution.c_info.sector_list
                  if not s.outstanding_doors or any(d in considered_set for d in s.outstanding_doors)
                  for r in s.regions}  # sectors dropped as neutral are spliced in later, not reached
    allowed = {r for s in solution.c_info.sector_list for r in s.regions}
    reached = explore_with_dependents(solution.c_info, cmap, group_terminal, allowed)
    for region in sorted(must_reach - set(reached), key=lambda r: r.name):
        problems.append(f'unreached region: {region.name}')
    return problems
