from collections import deque

from BaseClasses import DoorType
from KeyDoorShuffle import cid, create_key_counters, dungeon_bigs, dungeon_keys, find_counter_hint
from Regions import dungeon_events

# events that matter outside their own rooms: Blind needs them
blind_events = {'Attic Cracked Floor', 'Suspicious Maiden'}


def find_keylock(key_layout, world, player):
    """Search every order a player can open this dungeon's key doors in, with its keys where fill put them. Returns a
    description of a state where no door can be opened and item locations are still out of reach, or None."""
    if world.keyshuffle[player] == 'universal' or world.accessibility[player] == 'none':
        return None
    if key_layout.key_counters is None:
        key_layout.key_counters = create_key_counters(key_layout, world, player)
    counters = key_layout.key_counters
    small_key, big_key = dungeon_keys[key_layout.sector.name], dungeon_bigs[key_layout.sector.name]

    def locations_of(counter):
        return set(counter.free_locations) | set(counter.key_only_locations) | set(counter.other_locations)

    def holds(location, name):
        return location.item is not None and location.item.name == name and location.item.player == player

    inside = set().union(*(locations_of(c) for c in counters.values()))
    outside_keys = sum(1 for l in world.get_locations() if holds(l, small_key) and l not in inside)
    outside_keys += sum(1 for i in world.precollected_items if i.player == player and i.name == small_key)
    big_outside = (any(holds(l, big_key) and l not in inside for l in world.get_locations())
                   or any(i.player == player and i.name == big_key for i in world.precollected_items))

    def keys_held(counter):
        found = locations_of(counter)
        big = big_outside or any(holds(l, big_key) for l in found)  # a big chest may hold its own big key
        smalls = outside_keys + sum(1 for l in found if holds(l, small_key) and (big or '- Big Chest' not in l.name))
        return smalls, big

    pairs = {}
    for door in key_layout.proposal:
        if isinstance(door, tuple):
            pairs[door[0]], pairs[door[1]] = door[1], door[0]
    queue = deque(c for c in counters.values()
                  if c.used_keys == 0 and not c.big_key_opened and not c.prize_doors_opened)
    seen = set()
    while queue:
        counter = queue.popleft()
        code = cid(counter, key_layout)
        if code in seen:
            continue
        seen.add(code)
        smalls, big = keys_held(counter)
        moves = []
        for door in counter.child_doors:
            opened = dict(counter.open_doors)
            if door.bigKey or door in key_layout.key_logic.bk_doors:
                if counter.big_key_opened or not big:
                    continue
                child = find_counter_hint(opened, True, key_layout, counter.prize_doors_opened)
            elif door in key_layout.flat_prop:
                if smalls <= counter.used_keys:
                    continue
                opened[door] = None
                if door.dest in key_layout.flat_prop and door.type != DoorType.SpiralStairs:
                    opened[door.dest] = None
                if door in pairs:
                    opened[pairs[door]] = None
                child = find_counter_hint(opened, counter.big_key_opened, key_layout, counter.prize_doors_opened)
            else:  # a prize door: the prize comes eventually
                child = find_counter_hint(opened, counter.big_key_opened, key_layout, True)
            if child is not None and child is not counter:
                moves.append(child)
        if not moves:
            lost = [l for l in inside - locations_of(counter)
                    if l.item is not None and not holds(l, small_key) and not holds(l, big_key)
                    and not l.item.name.startswith('Small Key')
                    and (l.name not in dungeon_events or l.name in blind_events)]
            if lost:
                return (f'{len(counter.open_doors)} key doors open, {smalls} keys found, '
                        f'cut off: {", ".join(sorted(l.name for l in lost))}')
        queue.extend(moves)
    return None
