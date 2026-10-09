"""Exhaustive solver for small sector sets, independent of Transitivity's search and pruning.

A set is solvable when some sequence of connections reaches every outstanding door from the start portals and the
doors left unpaired can still be paired among themselves: each connection attaches an unreached door (hanger) onto a
reached one (hook), and entering a door reaches what the sector descriptor says it reaches. Crystals are ignored, so
callers only use crystal-free sectors.
"""
from source.dungeon.DungeonGenerationCommon import can_connect
from source.dungeon.DungeonGenTransitivity import valid_portal


class _Budget(Exception):
    pass


def crystal_free(sector):
    desc = sector.descriptor
    return (not desc.crystal_reqs and not desc.crystal_switch_doors and not desc.special_reqs
            and not any(d.crystal for d in sector.outstanding_doors))


def pairable(doors):
    """Whether the doors can be perfectly paired by type (the precondition Balance gives Transitivity's callers)."""
    pool = list(doors)
    while pool:
        d = pool.pop()
        partner = next((p for p in pool if can_connect(d, p) or can_connect(p, d)), None)
        if partner is None:
            return False
        pool.remove(partner)
    return True


def start_doors(sector_list):
    starts = set()
    for s in sector_list:
        for p in s.portals:
            # a dependent portal only opens once its enabling portal's sector is entered
            if not p.destination and not p.dependent and p.door in s.descriptor.reachability:
                starts.update(d for d, c, f in s.descriptor.reachability[p.door])
    return starts


def oracle_solvable(sector_list, c_info, max_nodes=200_000):
    """True/False, or None when the node budget runs out. c_info supplies the portal (lobby) rules."""
    plan = oracle_plan(sector_list, c_info, max_nodes)
    return plan if plan is None else plan is not False


def oracle_plan(sector_list, c_info, max_nodes=200_000):
    """A list of (hanger, hook) connections that solves the set, False if none exists, None if the budget runs out."""
    door_sector = {d: s for s in sector_list for d in s.outstanding_doors}
    all_doors = frozenset(door_sector)
    counter = [0]
    visited = set()

    def allowed(hanger, hook):
        if not can_connect(hanger, hook):
            return False
        if hook.traversal_only:
            return not hanger.traversal_only and valid_portal(hanger, hook, c_info)
        if hanger.traversal_only:
            return valid_portal(hook, hanger, c_info)
        return True

    def enter(reached, door):
        return reached | {d for d, c, f in door_sector[door].descriptor.reachability.get(door, [])} | {door}

    big_key = c_info.big_key  # where big keys matter, a location must be reachable before any big key door

    def leftover_pairings(left, cmap):
        """Every complete pairing of the doors left over once all doors are reached."""
        if not left:
            yield dict(cmap)
            return
        a = left[0]
        for b in left[1:]:
            if allowed(a, b) or allowed(b, a):
                cmap[a], cmap[b] = b, a
                yield from leftover_pairings([x for x in left if x is not a and x is not b], cmap)
                del cmap[a], cmap[b]

    def complete(conns, used):
        left = sorted(all_doors - used, key=lambda d: d.name)
        if big_key is None:
            return pairable(left)
        cmap = {d: p for hanger, hook in conns for d, p in ((hanger, hook), (hook, hanger))}
        return any(big_key.satisfied(full) for full in leftover_pairings(left, cmap))

    def search(reached, used, conns):
        key = (reached, used, frozenset(conns) if big_key is not None else None)
        if key in visited:
            return None
        visited.add(key)
        counter[0] += 1
        if counter[0] > max_nodes:
            raise _Budget()
        if reached >= all_doors:
            return [] if complete(conns, used) else None
        for hook in sorted(reached - used, key=lambda d: d.name):
            # connecting to an already-reached door adds nothing: reachability only grows
            for hanger in sorted(all_doors - reached, key=lambda d: d.name):
                if allowed(hanger, hook):
                    rest = search(enter(reached, hanger), used | {hook, hanger}, conns + ((hanger, hook),))
                    if rest is not None:
                        return [(hanger, hook)] + rest
        return None

    try:
        plan = search(frozenset(start_doors(sector_list)), frozenset(), ())
        return False if plan is None else plan
    except _Budget:
        return None
