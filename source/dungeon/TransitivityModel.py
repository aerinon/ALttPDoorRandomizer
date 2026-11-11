"""The final say on a Transitivity check the search could not finish: an order-free model of the same check, solved
with clingo. Anything the model leaves out is relaxed toward feasibility, so unsat proves there is no solution; a sat
wiring is replayed through the engine, which must accept it. Used only when the search hits its cap."""
from BaseClasses import CrystalBarrier
from source.dungeon.DungeonGenerationCommon import GenerationException, hanger_from_door, hook_from_door, crystal_allows
from source.dungeon.DungeonGenerationCommon import pit_barrier

try:
    import clingo
except ImportError:  # optional: without it a capped check fails the attempt as before
    clingo = None

# conflicts, not seconds, so a seed decides the same way on any machine; satisfiable checks take a few hundred and the
# slowest proofs seen about 90k
SOLVE_LIMIT = 150000

COLOR = {CrystalBarrier.Blue: ['blue'], CrystalBarrier.Orange: ['orange'], CrystalBarrier.Null: ['orange'],
         CrystalBarrier.Either: ['blue', 'orange'], CrystalBarrier.Both: ['blue', 'orange']}


def _engine():
    from source.dungeon import DungeonGenTransitivity
    return DungeonGenTransitivity


def available():
    return clingo is not None


def decide(t0, c_info, pins):
    """The engine state of a valid wiring the model finds, or None when the model proves there is none or the engine
    rejects the model's wiring. A model that reaches its conflict limit decides nothing, and the attempt fails."""
    facts, names = export(t0, c_info, pins)
    ctl = clingo.Control(['--models=1', '--warn=none', f'--solve-limit={SOLVE_LIMIT}'])
    ctl.add('base', [], RULES + '\n'.join(facts))
    ctl.ground([('base', [])])
    found = []
    result = ctl.solve(on_model=lambda m: found.append([(str(a.arguments[0]), str(a.arguments[1]))
                                                       for a in m.symbols(shown=True)]))
    if not found:
        if result.unknown:
            raise GenerationException(f'Transitivity model reached its limit of {SOLVE_LIMIT} conflicts.')
        return None
    state = replay(t0, c_info, [(names[a], names[b]) for a, b in found[0]])
    return state if state is not None and state.is_complete(c_info) else None


def tag(c):
    return {CrystalBarrier.Blue: 'blue', CrystalBarrier.Orange: 'orange', CrystalBarrier.Either: 'both',
            CrystalBarrier.Both: 'both'}.get(c, 'none')


def may_hang(h, k, c_info):
    """Every hanging the search could ever make, loosened where it depends on state."""
    hanger_type = hanger_from_door(h)
    if hanger_type is None or h == k:
        return False
    if k in c_info.free_hooks:
        return c_info.free_hook_may_land(h)
    if k.traversal_only:
        return any(_engine().valid_portal(h, k, c_info, init) for init in (True, False))
    if h.traversal_only:
        return any(_engine().valid_portal(k, h, c_info, init) for init in (True, False))
    return hook_from_door(k) == hanger_type


def export(t0, c_info, pins):
    doors = sorted(set(t0.remaining_doors) | set(t0.unconnected_doors) | set(t0.connection_map), key=lambda d: d.name)
    ids = {d: f'd{i}' for i, d in enumerate(doors)}
    facts = [f'door({ids[d]}).' for d in doors]
    for h in doors:
        for k in doors:
            if may_hang(h, k, c_info):
                facts.append(f'hang({ids[h]},{ids[k]}).')
    for d, c in t0.unconnected_doors.items():
        facts += [f'start({ids[d]},{x}).' for x in COLOR.get(c, ['blue', 'orange'])]
    for d, c in t0.door_states.items():
        if d in ids:
            facts += [f'start({ids[d]},{x}).' for x in COLOR.get(c, ['blue', 'orange'])]
    for a, b in t0.connection_map.items():
        facts.append(f'pin({ids[a]},{ids[b]}).')
    for si, s in enumerate(c_info.sector_list):
        for d in s.outstanding_doors:
            if d in ids:
                facts.append(f'sector({ids[d]},s{si}).')
                for x, arr, req in s.descriptor.reachability.get(d, []):
                    if x in ids:  # a door reaching itself is a switch room left the way it was entered
                        r = tag(req) if req in (CrystalBarrier.Blue, CrystalBarrier.Orange) else 'none'
                        facts.append(f'walk({ids[d]},{ids[x]},{tag(arr)},{r}).')
        for p in s.portals:
            for e in c_info.dependent_lookup.get(p.door, []):
                if e in ids:
                    facts.append(f'enables(s{si},{ids[e]}).')
    for d in doors:
        if _engine().is_one_way(d):
            facts.append(f'oneway({ids[d]}).')
            pb = pit_barrier(d)
            for c in ('blue', 'orange'):
                state = CrystalBarrier.Blue if c == 'blue' else CrystalBarrier.Orange
                if crystal_allows(pb, state):
                    outs = [tag(pb)] if pb in (CrystalBarrier.Blue, CrystalBarrier.Orange) else (
                        ['blue', 'orange'] if pb in (CrystalBarrier.Either, CrystalBarrier.Both) else [c])
                    facts += [f'fall({ids[d]},{c},{o}).' for o in outs]
    for a, b in pins:
        if a in ids and b in ids:
            facts.append(f'pin({ids[a]},{ids[b]}).')
    for i, k in enumerate(t0.unsatisfied_constraints):
        if k.type == _engine().ConstraintType.Crystal:
            facts.append(f'crystal(c{i},{k.constraint.color}).')
            for d in k.doors:
                if d in ids:
                    kind = 'crystal_access' if k.constraint.contains_color_access(d) else 'crystal_enter'
                    facts.append(f'{kind}(c{i},{ids[d]}).')
        elif k.type != _engine().ConstraintType.Neutral:
            facts.append(f'must(c{i}).')
            facts += [f'must_door(c{i},{ids[d]}).' for d in k.doors if d in ids]
    facts += export_escape(c_info, ids)
    facts += export_primary(c_info, ids)
    facts += export_big_key(c_info, ids)
    return facts, {v: k for k, v in ids.items()}


def vtag(c):
    return 'blue' if c == CrystalBarrier.Blue else 'orange' if c == CrystalBarrier.Orange else 'any'


def etag(c):
    return {CrystalBarrier.Blue: 'blue', CrystalBarrier.Orange: 'orange', CrystalBarrier.Either: 'either'}.get(c, 'none')


def export_escape(c_info, ids):
    esc = c_info.escape
    if esc is None:
        return []
    regions = {}

    def rid(r):
        return regions.setdefault(r, f'g{len(regions)}')
    facts = ['escape.', f'cellblock_region({rid(esc.cellblock)}).', f'throne_region({rid(esc.throne_room)}).']
    for root, name in ((esc.cellblock, 'cellblock'), (esc.throne_room, 'throne')):
        visited_map, reach = esc.start_states[root]
        facts += [f'root_visit({name},{rid(g)},{vtag(v[0])}).' for g, v in visited_map.items()]
        for door, new_color, required in reach:
            if door in ids:
                r = etag(required) if required in (CrystalBarrier.Blue, CrystalBarrier.Orange) else 'none'
                facts.append(f'esc_start({name},{ids[door]},{etag(new_color)},{r}).')
    for door, i in ids.items():
        if door.traversal_only:
            continue
        facts.append(f'region_of({i},{rid(door.entrance.parent_region)}).')
        sector = esc.sector_of.get(door.entrance.parent_region)
        state = sector.descriptor.state_cache.get(door) if sector else None
        if state is None:
            continue
        facts.append(f'enterable({i}).')
        facts += [f'visit({i},{rid(g)},{vtag(v[0])}).' for g, v in state.visited_map.items()]
        for x, new_color, required in sector.descriptor.reachability.get(door, []):
            if x in ids:
                r = etag(required) if required in (CrystalBarrier.Blue, CrystalBarrier.Orange) else 'none'
                facts.append(f'esc_walk({i},{ids[x]},{etag(new_color)},{r}).')
    portal_door = esc.portal.door
    if portal_door.traversal_only:
        if portal_door in ids:
            facts.append(f'lobby_door({ids[portal_door]}).')
    else:
        facts.append(f'lobby_fixed({rid(portal_door.entrance.parent_region)}).')
    return facts


def export_primary(c_info, ids):
    """The primary portal takes a door that is not a dead end."""
    if not c_info.primary_portal_required:
        return []
    facts = ['primary_required.']
    facts += [f'primary_door({ids[p]}).' for p in c_info.primary_portal_doors if p in ids]
    facts += [f'deadend({i}).' for d, i in ids.items() if d.deadEnd]
    return facts


def export_big_key(c_info, ids):
    """Regions reached from the entrances without crossing a big key door must hold a possible big key location.
    Relaxed: gated holes count as open, and a blind boss location counts as available."""
    bk = c_info.big_key
    if bk is None:
        return []
    from source.dungeon.DungeonStitcherV2 import reserved_location, prize_or_event
    facts = ['bk_check.']

    def good(regions):
        locations = [loc for r in regions for loc in r.locations]
        if bk.special:
            return any(loc.forced_big_key() for loc in locations)
        return any('- Big Chest' not in loc.name and not loc.forced_item and not reserved_location(loc, bk.world, bk.player)
                   and not prize_or_event(loc) for loc in locations)
    for d, i in ids.items():
        if d.traversal_only or d.entrance is None or d.entrance.parent_region not in bk.sector_of:
            continue
        visited, reach = bk.explore(d)
        facts.append(f'bk_enterable({i}).')
        if good(visited):
            facts.append(f'bk_good({i}).')
        facts += [f'bk_walk({i},{ids[x]}).' for x in reach if x in ids]
    for n, p in enumerate(bk.portals):
        if p.door.traversal_only:
            if p.door in ids:
                facts.append(f'bk_portal({ids[p.door]}).')
        elif p.door in ids:
            facts.append(f'bk_start({ids[p.door]}).')
        elif p.door.entrance is not None and p.door.entrance.parent_region in bk.sector_of:
            # a lobby already fixed to its portal is not an outstanding door: walk from it all the same
            visited, reach = bk.explore(p.door)
            facts += [f'bk_start(lobby{n}).', f'bk_enterable(lobby{n}).']
            if good(visited):
                facts.append(f'bk_good(lobby{n}).')
            facts += [f'bk_walk(lobby{n},{ids[x]}).' for x in reach if x in ids]
    for fall in bk.drop_starts + [f for f, _ in bk.gated_drops]:
        if fall in ids:
            facts.append(f'bk_start({ids[fall]}).')
    return facts


def replay(t0, c_info, wiring):
    """Connects the wiring in a reachable order through the engine, ignoring prunes; None when it gets stuck."""
    pairs = {frozenset(p) for p in wiring if p[0] not in t0.connection_map}
    t = t0.copy()
    while pairs:
        ready = sorted((p for p in pairs if any(d in t.unconnected_doors for d in p)), key=lambda q: sorted(d.name for d in q))
        if not ready:
            return None
        p = ready[0]
        pairs.discard(p)
        a, b = sorted(p, key=lambda d: d.name)
        hook, hanger = (a, b) if a in t.unconnected_doors else (b, a)
        t = t.connect_door((hanger, hook), c_info)
    return t


RULES = """
% Order-free relaxation of the Transitivity check. Anything not modeled exactly is relaxed toward feasibility, so
% UNSAT proves the check has no solution. Facts come from tools/cap_model.py.
color(blue;orange).

% pairing: every door takes at most one partner from the allowed directed hangings hang(Hanger, Hook)
cand(A,B) :- hang(A,B).
cand(A,B) :- hang(B,A).
{ pair(A,B) : cand(A,B) } <= 1 :- door(A).
pair(B,A) :- pair(A,B).
:- pair(A,B), not cand(A,B).
:- pin(A,B), not pair(A,B).

% reachability over (door, color)
reach(D,C) :- start(D,C).
% inside a sector: from D in color C to X; Req gates, Arr fixes the arrival color
reach(X,C2) :- reach(D,C), walk(D,X,Arr,Req), ok(Req,C), arrive(Arr,C,C2).
ok(none,C) :- color(C).
ok(blue,blue).
ok(orange,orange).
arrive(none,C,C) :- color(C).
arrive(blue,C,blue) :- color(C).
arrive(orange,C,orange) :- color(C).
arrive(both,C,C2) :- color(C), color(C2).
% across a connection: a hook reached in C lets the hanger in; a pit source gates on and sets its barrier color
reach(H,C2) :- reach(K,C), pair(K,H), hang(H,K), not oneway(K), C2 = C.
reach(H,C2) :- reach(K,C), pair(K,H), hang(H,K), oneway(K), fall(K,C,C2).
% two-way doors also lead back
reach(K,C) :- reach(H,C), pair(K,H), hang(H,K), not oneway(K), not oneway(H).
% a dependent portal opens once its enabler sector is reached
reach(E,orange) :- reach(D,_), sector(D,S), enables(S,E).

reached(D) :- reach(D,_).
:- door(D), not reached(D).
paired(D) :- pair(D,_).

% constraints, relaxed: entered through means paired; crystal access means the needed color reaches an access door
:- must(I), not met(I).
met(I) :- must_door(I,D), paired(D).
:- crystal(I,Col), not cmet(I).
cmet(I) :- crystal_access(I,D), reach(D,Col), crystal(I,Col).
cmet(I) :- crystal_enter(I,D), reached(D).

#show pair/2.

% standard escape (EscapeCheck): walks start in orange from Cellblock and Throne Room; on crossing, Both keeps the
% walking color and Either may be either (relaxed). Cellblock reaches the lobby and Throne Room; Throne Room reaches
% the lobby or Cellblock. The lobby is the region paired with the south portal door, or fixed.
escarr(blue,C,blue) :- color(C).
escarr(orange,C,orange) :- color(C).
escarr(none,C,C) :- color(C).
escarr(both,C,C) :- color(C).
escarr(either,C,C2) :- color(C), color(C2).
escreach(R,E,C2) :- esc_start(R,D,Arr,Req), ok(Req,orange), escarr(Arr,orange,C2), pair(D,E), enterable(E).
escreach(R,E2,C2) :- escreach(R,E,C), esc_walk(E,D,Arr,Req), ok(Req,C), escarr(Arr,C,C2), pair(D,E2), enterable(E2).
visok(any,C) :- color(C).
visok(C,C) :- color(C).
escfound(R,G) :- root_visit(R,G,V), visok(V,orange).
escfound(R,G) :- escreach(R,E,C), visit(E,G,V), visok(V,C).
lobby(G) :- lobby_fixed(G).
lobby(G) :- lobby_door(P), pair(P,X), region_of(X,G).
cb_lobby :- escfound(cellblock,G), lobby(G).
tr_ok :- escfound(throne,G), lobby(G).
tr_ok :- escfound(throne,G), cellblock_region(G).
:- escape, not cb_lobby.
:- escape, not escfound(cellblock,G), throne_region(G).
:- escape, not tr_ok.

% primary portal: some primary-capable portal door takes a door that is not a dead end
primary_ok :- primary_door(P), pair(P,X), not deadend(X).
:- primary_required, not primary_ok.

% big key: walking from the entrances without crossing a big key door reaches a possible big key location
bkreach(D) :- bk_start(D), bk_enterable(D).
bkreach(X) :- bk_portal(P), pair(P,X), bk_enterable(X).
bkreach(E) :- bkreach(D), bk_walk(D,X), pair(X,E), bk_enterable(E).
bk_ok :- bkreach(D), bk_good(D).
:- bk_check, not bk_ok.
"""
