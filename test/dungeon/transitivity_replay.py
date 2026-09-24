"""Drives Transitivity along a known-valid (vanilla) connection path instead of searching.

The first step Transitivity rejects, or cannot take, points at the check responsible for a false negative.
"""
import linecache
import sys
from dataclasses import dataclass, field

from BaseClasses import DoorType, Direction
from DoorShuffle import (default_door_connections, default_one_way_connections, ladders, open_edges,
                         spiral_staircases, straight_staircases)
from source.dungeon.DungeonGenerationCommon import hanger_from_door, hook_from_door
from source.dungeon.DungeonGenTransitivity import ConstraintInfo, ConstraintType, Transitivity
from test.dungeon.transitivity_harness import make_builder

ONE_WAY = (DoorType.Hole, DoorType.Warp)


@dataclass
class ReplayResult:
    ok: bool
    step: int = 0
    failed_pair: tuple = None
    reason: str = ''
    pruned_by: str = ''
    notes: list = field(default_factory=list)

    def describe(self):
        if self.ok:
            return 'ok'
        pair = ' -> '.join(d.name for d in self.failed_pair) if self.failed_pair else '-'
        return f'step {self.step}: {self.reason} [{pair}] {self.pruned_by}'.rstrip()


def vanilla_partners(sector_list):
    """Maps each outstanding door to its vanilla partner. Holes/Warps map to their group's Terminal."""
    doors = {d.name: d for s in sector_list for d in s.outstanding_doors}
    partners = {}
    tables = default_door_connections + open_edges + straight_staircases + spiral_staircases + ladders
    for a, b in tables + default_one_way_connections:
        if a in doors and b in doors:
            partners[doors[a]] = doors[b]
            partners[doors[b]] = doors[a]
    for d in doors.values():
        if d.type in ONE_WAY and d.group in doors:
            partners[d] = doors[d.group]
    for s in sector_list:
        for p in s.portals:
            if p.door in partners or p.door is None or p.door.name not in doors:
                continue
            lobby = p.default_door
            if lobby is not None and lobby.name in doors and lobby is not p.door:
                partners[p.door] = lobby
                partners[lobby] = p.door
    missing = sorted(d.name for d in doors.values() if d not in partners and d.type != DoorType.Terminal)
    return partners, missing


def why_impossible(state, c_info, visited):
    """Calls now_impossible and reports which return statement fired, as 'line N: source'."""
    code = Transitivity.now_impossible.__code__
    info = {}

    def local(frame, event, arg):
        if event == 'return':
            info['line'] = frame.f_lineno
        return local

    def tracer(frame, event, arg):
        return local if frame.f_code is code else None

    sys.settrace(tracer)
    try:
        result = state.now_impossible(c_info, visited)
    finally:
        sys.settrace(None)
    line = info.get('line')
    src = linecache.getline(code.co_filename, line).strip() if line else ''
    # a 'return True' inside a helper call shows up as the caller's line: `if self.helper(...): return True`
    prev = linecache.getline(code.co_filename, line - 1).strip() if line else ''
    return result, f'line {line}: {prev} / {src}' if prev.startswith('if ') else f'line {line}: {src}'


def _setup(name, sector_list, flags):
    """Mirrors the setup in do_transitivity_check_main."""
    all_outstanding = [d for s in sector_list for d in s.outstanding_doors]
    c_info = ConstraintInfo(make_builder(name), sector_list, [], flags)
    for c in [x for x in c_info.constraints if x.type == ConstraintType.Neutral]:
        if any(d.portalAble or (not d.portalAble and d.direction == Direction.South) for d in c.doors):
            continue
        all_outstanding = [x for x in all_outstanding if x not in c.doors]
        c_info.door_matches = {o: m for o, m in c_info.door_matches.items() if o not in c.doors}
        for o, m in c_info.door_matches.items():
            c_info.door_matches[o] = [x for x in m if x not in c.doors]
    unsatisfied = [x for x in c_info.constraints if x.type != ConstraintType.Neutral]
    t = Transitivity(all_outstanding, unsatisfied, [])
    for sector in c_info.init_portals:
        t.append_sector_free(sector, c_info)
    return t, c_info


def _orient(reached, partner):
    """Returns (hanger, hook): the new door is attached onto the reached one (pits included)."""
    return partner, reached


def splice_removed(partners, considered, sector_list):
    """Transitivity drops neutral sectors before searching; follow vanilla chains through them.

    Returns (effective partners among considered doors, notes on chains that could not be followed).
    """
    door_sector = {d: s for s in sector_list for d in s.outstanding_doors}
    effective, notes = {}, []
    for door in considered:
        partner, hops = partners.get(door), 0
        while partner is not None and partner not in considered and hops < 50:
            others = [d for d in door_sector[partner].outstanding_doors if d is not partner]
            if len(others) != 1:
                notes.append(f'{door.name}: vanilla path enters removed sector {door_sector[partner].sector_key()} '
                             f'with {len(others) + 1} doors')
                partner = None
                break
            partner, hops = partners.get(others[0]), hops + 1
        if partner is not None and partner in considered:
            effective[door] = partner
    return effective, notes


def replay_vanilla(name, sector_list, flags):
    raw_partners, missing = vanilla_partners(sector_list)
    t, c_info = _setup(name, sector_list, flags)
    considered = set(t.remaining_doors) | set(t.unconnected_doors)
    partners, splice_notes = splice_removed(raw_partners, considered, sector_list)
    result = ReplayResult(ok=False)
    if missing:
        result.notes.append(f'no vanilla partner: {missing}')
    result.notes.extend(splice_notes)
    visited = set()
    step = 0
    while t.unsatisfied_constraints or t.remaining_doors:
        step += 1
        candidates = sorted(((d, partners[d]) for d in t.unconnected_doors
                             if d in partners and d not in t.connection_map and partners[d] not in t.connection_map),
                            key=lambda pair: pair[0].name)
        if not candidates:
            result.step, result.reason = step, 'stuck'
            result.pruned_by = (f'remaining={sorted(d.name for d in t.remaining_doors)} '
                                f'unsatisfied={[(c.type.name, [d.name for d in c.doors]) for c in t.unsatisfied_constraints]}')
            return result
        reached, partner = candidates[0]
        connection = _orient(reached, partner)
        offered = t.find_connectable_doors(c_info, init=(step == 1))
        if connection not in offered:
            result.notes.append(f'step {step}: {connection[0].name} -> {connection[1].name} not offered '
                                f'(may be winnowed as equivalent; offered {len(offered)})')
        new_t = t.connect_door(connection, c_info)
        impossible, where = why_impossible(new_t, c_info, visited)
        if impossible:
            result.step, result.failed_pair, result.reason, result.pruned_by = step, connection, 'pruned', where
            return result
        visited.add(frozenset(new_t.connection_map.items()))
        t = new_t
    result.ok, result.step = True, step
    return result
