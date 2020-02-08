import logging
from collections import defaultdict, deque

from BaseClasses import DoorType
from Regions import dungeon_events, key_only_locations
from Dungeons import dungeon_keys, dungeon_bigs
from DungeonGenerator import ExplorationState


class KeyLayout(object):

    def __init__(self, sector, starts, proposal):
        self.sector = sector
        self.start_regions = starts
        self.proposal = proposal
        self.key_logic = KeyLogic(sector.name)

        self.key_counters = None
        self.flat_prop = None
        self.max_chests = None
        self.max_drops = None
        self.all_chest_locations = {}
        self.big_key_special = False

        # bk special?
        # bk required? True if big chests or big doors exists

    def reset(self, proposal, builder, world, player):
        self.proposal = proposal
        self.flat_prop = flatten_pair_list(self.proposal)
        self.key_logic = KeyLogic(self.sector.name)
        self.max_chests = calc_max_chests(builder, self, world, player)


class KeyLogic(object):

    def __init__(self, dungeon_name):
        self.door_rules = {}
        self.bk_restricted = set()
        self.sm_restricted = set()
        self.small_key_name = dungeon_keys[dungeon_name]
        self.bk_name = dungeon_bigs[dungeon_name]
        self.bk_doors = set()
        self.bk_chests = set()
        self.logic_min = {}
        self.logic_max = {}


class DoorRules(object):

    def __init__(self, number, is_valid):
        self.small_key_num = number
        self.is_valid = is_valid
        # allowing a different number if bk is behind this door in a set of locations
        self.alternate_small_key = None
        self.alternate_big_key_loc = set()
        # for a place with only 1 free location/key_only_location behind it ... no goals and locations
        self.allow_small = False
        self.small_location = None


class KeyCounter(object):

    def __init__(self, max_chests):
        self.max_chests = max_chests
        self.free_locations = {}
        self.key_only_locations = {}
        self.child_doors = {}
        self.open_doors = {}
        self.used_keys = 0
        self.big_key_opened = False
        self.important_location = False
        self.other_locations = {}

    def used_smalls_loc(self, reserve=0):
        return max(self.used_keys + reserve - len(self.key_only_locations), 0)

    def copy(self):
        ret = KeyCounter(self.max_chests)
        ret.free_locations.update(self.free_locations)
        ret.key_only_locations.update(self.key_only_locations)
        ret.child_doors.update(self.child_doors)
        ret.used_keys = self.used_keys
        ret.open_doors.update(self.open_doors)
        ret.big_key_opened = self.big_key_opened
        ret.important_location = self.important_location
        return ret


def build_key_layout(builder, start_regions, proposal, world, player):
    key_layout = KeyLayout(builder.master_sector, start_regions, proposal)
    key_layout.flat_prop = flatten_pair_list(key_layout.proposal)
    key_layout.max_drops = count_key_drops(key_layout.sector)
    key_layout.max_chests = calc_max_chests(builder, key_layout, world, player)
    key_layout.big_key_special = 'Hyrule Dungeon Cellblock' in key_layout.sector.region_set()
    return key_layout


def calc_max_chests(builder, key_layout, world, player):
    if world.doorShuffle[player] != 'crossed':
        return len(world.get_dungeon(key_layout.sector.name, player).small_keys)
    return max(0, builder.key_doors_num - key_layout.max_drops)


def analyze_dungeon(key_layout, world, player):
    key_layout.key_counters = create_key_counters(key_layout, world, player)
    key_logic = key_layout.key_logic

    find_bk_locked_sections(key_layout, world)
    key_logic.bk_chests.update(find_big_chest_locations(key_layout.all_chest_locations))

    original_key_counter = find_counter({}, False, key_layout)
    queue = deque([(None, original_key_counter)])
    doors_completed = set()
    visited_cid = set()
    visited_cid.add(cid(original_key_counter, key_layout))

    while len(queue) > 0:
        queue = deque(sorted(queue, key=queue_sorter))
        parent_door, key_counter = queue.popleft()
        chest_keys = available_chest_small_keys(key_counter, world, player)
        raw_avail = chest_keys + len(key_counter.key_only_locations)
        available = raw_avail - key_counter.used_keys
        possible_smalls = count_unique_small_doors(key_counter, key_layout.flat_prop)
        avail_bigs = exist_relevant_big_doors(key_counter, key_layout)
        non_big_locs = count_locations_big_optional(key_counter.free_locations)
        if not key_counter.big_key_opened:
            if chest_keys == non_big_locs and chest_keys > 0 and available <= possible_smalls and not avail_bigs:
                key_logic.bk_restricted.update(filter_big_chest(key_counter.free_locations))
                if not key_counter.big_key_opened and big_chest_in_locations(key_counter.free_locations):
                    key_logic.sm_restricted.update(find_big_chest_locations(key_counter.free_locations))
        # todo: detect forced subsequent keys - see keypuzzles
        # try to relax the rules here? - smallest requirement that doesn't force a softlock
        child_queue = deque()
        smallest_rule = None
        for child in key_counter.child_doors.keys():
            if not child.bigKey or not key_layout.big_key_special or key_counter.big_key_opened:
                odd_counter = create_odd_key_counter(child, key_counter, key_layout, world, player)
                empty_flag = empty_counter(odd_counter)
                child_queue.append((child, odd_counter, empty_flag))
                if child in doors_completed and child in key_logic.door_rules.keys():
                    rule = key_logic.door_rules[child]
                    if smallest_rule is None or rule.small_key_num < smallest_rule:
                        smallest_rule = rule.small_key_num
        while len(child_queue) > 0:
            child, odd_counter, empty_flag = child_queue.popleft()
            if not child.bigKey and child not in doors_completed:
                best_counter = find_best_counter(child, odd_counter, key_counter, key_layout, world, player, False, empty_flag)
                rule = create_rule(best_counter, key_counter, key_layout, world, player)
                # todo: seems to be caused by best_counter not opening the big key door when that's logically required.  Re-evaluate usage of this
                # if not rule.is_valid:
                #     logging.getLogger('').warning('Key logic for door %s requires too many chests.  Seed may be beatable anyway.', child.name)
                if smallest_rule is None or rule.small_key_num < smallest_rule:
                    smallest_rule = rule.small_key_num
                check_for_self_lock_key(rule, child, best_counter, key_layout, world, player)
                bk_restricted_rules(rule, child, odd_counter, empty_flag, key_counter, key_layout, world, player)
                key_logic.door_rules[child.name] = rule
            doors_completed.add(child)
            next_counter = find_next_counter(child, key_counter, key_layout)
            ctr_id = cid(next_counter, key_layout)
            if ctr_id not in visited_cid:
                queue.append((child, next_counter))
                visited_cid.add(ctr_id)
        possible_smalls_collected = len(key_counter.key_only_locations) + non_big_locs
        if not key_counter.big_key_opened:
            if smallest_rule is not None and smallest_rule >= possible_smalls_collected and not avail_bigs:
                key_logic.bk_restricted.update(filter_big_chest(key_counter.free_locations))
                if not key_counter.big_key_opened and big_chest_in_locations(key_counter.free_locations):
                    key_logic.sm_restricted.update(find_big_chest_locations(key_counter.free_locations))
    check_rules(original_key_counter, key_layout, world, player)

    # Flip bk rules if more restrictive, to prevent placing a big key in a softlocking location
    for rule in key_logic.door_rules.values():
        if rule.alternate_small_key is not None and rule.alternate_small_key > rule.small_key_num:
            max_counter = find_max_counter(key_layout)
            rule.alternate_big_key_loc = set(max_counter.free_locations.keys()).difference(rule.alternate_big_key_loc)
            rule.small_key_num, rule.alternate_small_key = rule.alternate_small_key, rule.small_key_num



def count_key_drops(sector):
    cnt = 0
    for region in sector.regions:
        for loc in region.locations:
            if loc.event and 'Small Key' in loc.item.name:
                cnt += 1
    return cnt


def queue_sorter(queue_item):
    door, counter = queue_item
    if door is None:
        return 0
    return 1 if door.bigKey else 0


def queue_sorter_2(queue_item):
    door, counter, key_only = queue_item
    if door is None:
        return 0
    return 1 if door.bigKey else 0


def find_bk_locked_sections(key_layout, world):
    if key_layout.big_key_special:
        return
    key_counters = key_layout.key_counters
    key_logic = key_layout.key_logic

    bk_key_not_required = set()
    big_chest_allowed_big_key = world.accessibility != 'locations'
    for counter in key_counters.values():
        key_layout.all_chest_locations.update(counter.free_locations)
        if counter.big_key_opened and counter.important_location:
            big_chest_allowed_big_key = False
        if not counter.big_key_opened:
            bk_key_not_required.update(counter.free_locations)
    key_logic.bk_restricted.update(dict.fromkeys(set(key_layout.all_chest_locations).difference(bk_key_not_required)))
    if not big_chest_allowed_big_key:
        key_logic.bk_restricted.update(find_big_chest_locations(key_layout.all_chest_locations))


def empty_counter(counter):
    if len(counter.key_only_locations) != 0 or len(counter.free_locations) != 0 or len(counter.child_doors) != 0:
        return False
    return not counter.important_location


def relative_empty_counter(odd_counter, key_counter):
    if len(set(odd_counter.key_only_locations).difference(key_counter.key_only_locations)) > 0:
        return False
    if len(set(odd_counter.free_locations).difference(key_counter.free_locations)) > 0:
        return False
    new_child_door = False
    for child in odd_counter.child_doors:
        if unique_child_door(child, key_counter):
            new_child_door = True
            break
    if new_child_door:
        return False
    return True


def unique_child_door(child, key_counter):
    if child in key_counter.child_doors or child.dest in key_counter.child_doors:
        return False
    if child in key_counter.open_doors or child.dest in key_counter.open_doors:
        return False
    if child.bigKey and key_counter.big_key_opened:
        return False
    return True


def find_best_counter(door, odd_counter, key_counter, key_layout, world, player, skip_bk, empty_flag):  # try to waste as many keys as possible?
    bk_opened = key_counter.big_key_opened

    def score(counter):
        return (counter.used_keys - len(counter.key_only_locations), counter.used_keys, counter.big_key_opened)

    best_counter = max((i for i in key_layout.key_counters.values() if door not in i.open_doors and
                    set(i.open_doors.keys()).issuperset(set(key_counter.open_doors.keys())) and
                    (empty_flag or not relative_empty_counter(odd_counter, i)) and
                    (not skip_bk or bk_opened or not i.big_key_opened) and
                    (skip_bk or i.big_key_opened or len(i.key_only_locations) + available_chest_small_keys(i, world, player) > i.used_keys)), 
                    key=score, default=key_counter)

    return best_counter


def find_potential_open_doors(key_counter, ignored_doors, key_layout, skip_bk):
    small_doors = []
    big_doors = []
    for other in key_counter.child_doors:
        if other not in ignored_doors and other.dest not in ignored_doors:
            if other.bigKey:
                if not skip_bk and (not key_layout.big_key_special or key_counter.big_key_opened):
                    big_doors.append(other)
            elif other.dest not in small_doors:
                small_doors.append(other)
    if key_layout.big_key_special:
        big_key_available = key_counter.big_key_opened
    else:
        big_key_available = len(key_counter.free_locations) - key_counter.used_smalls_loc(1) > 0
    if len(small_doors) == 0 and (not skip_bk and (len(big_doors) == 0 or not big_key_available)):
        return None
    return small_doors + big_doors


def key_wasted(new_door, old_door, old_counter, new_counter, key_layout, world, player):
    if new_door.bigKey:  # big keys are not wastes - it uses up a location
        return True
    chest_keys = available_chest_small_keys(old_counter, world, player)
    old_key_diff = len(old_counter.key_only_locations) - old_counter.used_keys
    old_avail = chest_keys + old_key_diff
    new_chest_keys = available_chest_small_keys(new_counter, world, player)
    new_key_diff = len(new_counter.key_only_locations) - new_counter.used_keys
    new_avail = new_chest_keys + new_key_diff
    if new_key_diff < old_key_diff or new_avail < old_avail:
        return True
    if new_avail >= old_avail:
        wasted_keys = 0
        old_children = old_counter.child_doors.keys()
        new_children = [x for x in new_counter.child_doors.keys() if x != old_door and x.dest != old_door and (not x.bigKey or x not in old_children)]
        current_counter = new_counter
        opened_doors = dict(current_counter.open_doors)
        bk_opened = current_counter.big_key_opened
        for new_child in new_children:
            proposed_doors = {**opened_doors, **dict.fromkeys([new_child, new_child.dest])}
            bk_open = bk_opened or new_door.bigKey
            new_counter = find_counter(proposed_doors, bk_open, key_layout)
            if key_wasted(new_child, old_door, current_counter, new_counter, key_layout, world, player):
                wasted_keys += 1
            if new_avail - wasted_keys < old_avail:
                return True  # waste is possible
    return False


def find_next_counter(new_door, old_counter, key_layout):
    proposed_doors = {**old_counter.open_doors, **dict.fromkeys([new_door, new_door.dest])}
    bk_open = old_counter.big_key_opened or new_door.bigKey
    return find_counter(proposed_doors, bk_open, key_layout)


def check_special_locations(locations):
    for loc in locations:
        if loc.name == 'Hyrule Castle - Zelda\'s Chest':
            return True
    return False


def calc_avail_keys(key_counter, world, player):
    chest_keys = available_chest_small_keys(key_counter, world, player)
    raw_avail = chest_keys + len(key_counter.key_only_locations)
    return raw_avail - key_counter.used_keys


def create_rule(key_counter, prev_counter, key_layout, world, player):
    # prev_chest_keys = available_chest_small_keys(prev_counter, world)
    # prev_avail = prev_chest_keys + len(prev_counter.key_only_locations)
    chest_keys = available_chest_small_keys(key_counter, world, player)
    key_gain = len(key_counter.key_only_locations) - len(prev_counter.key_only_locations)
    # previous method
    # raw_avail = chest_keys + len(key_counter.key_only_locations)
    # available = raw_avail - key_counter.used_keys
    # possible_smalls = count_unique_small_doors(key_counter, key_layout.flat_prop)
    # required_keys = min(available, possible_smalls) + key_counter.used_keys
    required_keys = key_counter.used_keys + 1  # this makes more sense, if key_counter has wasted all keys
    adj_chest_keys = min(chest_keys, required_keys)
    needed_chests = required_keys - len(key_counter.key_only_locations)
    is_valid = needed_chests <= chest_keys
    unneeded_chests = min(key_gain, max(0, adj_chest_keys - needed_chests))
    rule_num = required_keys - unneeded_chests
    return DoorRules(rule_num, is_valid)


def check_for_self_lock_key(rule, door, parent_counter, key_layout, world, player):
    if world.accessibility != 'locations':
        counter = find_inverted_counter(door, parent_counter, key_layout, world, player)
        if not self_lock_possible(counter):
            return
        if len(counter.free_locations) == 1 and len(counter.key_only_locations) == 0 and not counter.important_location:
            rule.allow_small = True
            rule.small_location = next(iter(counter.free_locations))


def find_inverted_counter(door, parent_counter, key_layout, world, player):
    # open all doors in counter
    counter = open_all_counter(parent_counter, key_layout, door=door)
    max_counter = find_max_counter(key_layout)
    # find the difference
    inverted_counter = KeyCounter(key_layout.max_chests)
    inverted_counter.free_locations = dict_difference(max_counter.free_locations, counter.free_locations)
    inverted_counter.key_only_locations = dict_difference(max_counter.key_only_locations, counter.key_only_locations)
    # child doors? used_keys?
    # inverted_counter.child_doors = dict_difference(max_counter.child_doors, counter.child_doors)
    inverted_counter.open_doors = dict_difference(max_counter.open_doors, counter.open_doors)
    inverted_counter.other_locations = dict_difference(max_counter.other_locations, counter.other_locations)
    for loc in inverted_counter.other_locations:
        if important_location(loc, world, player):
            inverted_counter.important_location = True
    return inverted_counter


def open_all_counter(parent_counter, key_layout, door=None, skipBk=False):
    changed = True
    counter = parent_counter
    proposed_doors = dict.fromkeys(parent_counter.open_doors.keys())
    while changed:
        changed = False
        doors_to_open = {}
        for child in counter.child_doors:
            if door is None or (child != door and child != door.dest):
                if skipBk:
                    if not child.bigKey:
                        doors_to_open[child] = None
                elif not child.bigKey or not key_layout.big_key_special or counter.big_key_opened:
                    doors_to_open[child] = None
        if len(doors_to_open.keys()) > 0:
            proposed_doors = {**proposed_doors, **doors_to_open}
            bk_hint = counter.big_key_opened
            for d in doors_to_open.keys():
                bk_hint = bk_hint or d.bigKey
            counter = find_counter(proposed_doors, bk_hint, key_layout)
            changed = True
    return counter


def open_some_counter(parent_counter, key_layout, ignored_doors):
    changed = True
    counter = parent_counter
    proposed_doors = dict.fromkeys(parent_counter.open_doors.keys())
    while changed:
        changed = False
        doors_to_open = {}
        for child in counter.child_doors:
            if child not in ignored_doors:
                if not child.bigKey:
                    doors_to_open[child] = None
        if len(doors_to_open.keys()) > 0:
            proposed_doors = {**proposed_doors, **doors_to_open}
            bk_hint = counter.big_key_opened
            for d in doors_to_open.keys():
                bk_hint = bk_hint or d.bigKey
            counter = find_counter(proposed_doors, bk_hint, key_layout)
            changed = True
    return counter


def self_lock_possible(counter):
    return len(counter.free_locations) <= 1 and len(counter.key_only_locations) == 0 and not counter.important_location


def available_chest_small_keys(key_counter, world, player):
    if not world.keyshuffle[player] and not world.retro[player]:
        cnt = 0
        for loc in key_counter.free_locations:
            if key_counter.big_key_opened or '- Big Chest' not in loc.name:
                cnt += 1
        return min(cnt, key_counter.max_chests)
    else:
        return key_counter.max_chests


def available_chest_small_keys_logic(key_counter, world, player, sm_restricted):
    if not world.keyshuffle[player] and not world.retro[player]:
        cnt = 0
        for loc in key_counter.free_locations:
            if loc not in sm_restricted and (key_counter.big_key_opened or '- Big Chest' not in loc.name):
                cnt += 1
        return min(cnt, key_counter.max_chests)
    else:
        return key_counter.max_chests


def bk_restricted_rules(rule, door, odd_counter, empty_flag, key_counter, key_layout, world, player):
    if key_counter.big_key_opened:
        return
    best_counter = find_best_counter(door, odd_counter, key_counter, key_layout, world, player, True, empty_flag)
    bk_rule = create_rule(best_counter, key_counter, key_layout, world, player)
    if bk_rule.small_key_num >= rule.small_key_num and bk_rule.is_valid:
        return
    door_open = find_next_counter(door, best_counter, key_layout)
    ignored_doors = dict_intersection(best_counter.child_doors, door_open.child_doors)
    dest_ignored = []
    for door in ignored_doors.keys():
        if door.dest not in ignored_doors:
            dest_ignored.append(door.dest)
    ignored_doors = {**ignored_doors, **dict.fromkeys(dest_ignored)}
    post_counter = open_some_counter(door_open, key_layout, ignored_doors.keys())
    unique_loc = dict_difference(post_counter.free_locations, best_counter.free_locations)
    # todo: figure out the intention behind this change - better way to detect the big key is blocking needed key onlys?
    if len(unique_loc) > 0 and bk_rule.is_valid:
        rule.alternate_small_key = bk_rule.small_key_num
        rule.alternate_big_key_loc.update(unique_loc)
    elif not bk_rule.is_valid:
        key_layout.key_logic.bk_restricted.update(unique_loc)


def open_a_door(door, child_state, flat_proposal):
    if door.bigKey:
        child_state.big_key_opened = True
        child_state.avail_doors.extend(child_state.big_doors)
        child_state.opened_doors.extend(set([d.door for d in child_state.big_doors]))
        child_state.big_doors.clear()
    else:
        child_state.opened_doors.append(door)
        doors_to_open = [x for x in child_state.small_doors if x.door == door]
        child_state.small_doors[:] = [x for x in child_state.small_doors if x.door != door]
        child_state.avail_doors.extend(doors_to_open)
        dest_door = door.dest
        if dest_door in flat_proposal and door.type != DoorType.SpiralStairs:
            child_state.opened_doors.append(dest_door)
            if child_state.in_door_list_ic(dest_door, child_state.small_doors):
                now_available = [x for x in child_state.small_doors if x.door == dest_door]
                child_state.small_doors[:] = [x for x in child_state.small_doors if x.door != dest_door]
                child_state.avail_doors.extend(now_available)


# allows dest doors
def unique_doors(doors):
    unique_d_set = []
    for d in doors:
        if d.door not in unique_d_set:
            unique_d_set.append(d.door)
    return unique_d_set


# does not allow dest doors
def count_unique_sm_doors(doors):
    unique_d_set = set()
    for d in doors:
        if d not in unique_d_set and d.dest not in unique_d_set and not d.bigKey:
            unique_d_set.add(d)
    return len(unique_d_set)


# doesn't count dest doors
def count_unique_small_doors(key_counter, proposal):
    cnt = 0
    counted = set()
    for door in key_counter.child_doors:
        if door in proposal and door not in counted:
            cnt += 1
            counted.add(door)
            counted.add(door.dest)
    return cnt


def exist_relevant_big_doors(key_counter, key_layout):
    bk_counter = find_counter(key_counter.open_doors, True, key_layout, False)
    if bk_counter is not None:
        diff = dict_difference(bk_counter.free_locations, key_counter.free_locations)
        if len(diff) > 0:
            return True
        diff = dict_difference(bk_counter.key_only_locations, key_counter.key_only_locations)
        if len(diff) > 0:
            return True
        diff = dict_difference(bk_counter.child_doors, key_counter.child_doors)
        if len(diff) > 0:
            return True
    return False


def count_locations_big_optional(locations, bk=False):
    cnt = 0
    for loc in locations:
        if bk or '- Big Chest' not in loc.name:
            cnt += 1
    return cnt


def filter_big_chest(locations):
    return [x for x in locations if '- Big Chest' not in x.name]


def count_free_locations(state):
    cnt = 0
    for loc in state.found_locations:
        if '- Prize' not in loc.name and loc.name not in dungeon_events and loc.name not in key_only_locations and loc.name not in ['Agahnim 1', 'Agahnim 2', 'Hyrule Castle - Big Key Drop']:
            cnt += 1
    return cnt


def count_locations_exclude_big_chest(state):
    cnt = 0
    for loc in state.found_locations:
        if '- Big Chest' not in loc.name and '- Prize' not in loc.name and loc.name not in dungeon_events and loc.name not in key_only_locations and loc.name not in ['Agahnim 1', 'Agahnim 2', 'Hyrule Castle - Big Key Drop']:
            cnt += 1
    return cnt


def count_key_only_locations(state):
    cnt = 0
    for loc in state.found_locations:
        if loc.name in key_only_locations:
            cnt += 1
    return cnt


def big_chest_in_locations(locations):
    return len(find_big_chest_locations(locations)) > 0


def find_big_chest_locations(locations):
    ret = []
    for loc in locations:
        if 'Big Chest' in loc.name:
            ret.append(loc)
    return ret


def expand_key_state(state, flat_proposal, world, player):
    while len(state.avail_doors) > 0:
        exp_door = state.next_avail_door()
        door = exp_door.door
        connect_region = world.get_entrance(door.name, player).connected_region
        if state.validate(door, connect_region, world, player):
            state.visit_region(connect_region, key_checks=True)
            state.add_all_doors_check_keys(connect_region, flat_proposal, world, player)


def flatten_pair_list(paired_list):
    flat_list = []
    for d in paired_list:
        if type(d) is tuple:
            flat_list.append(d[0])
            flat_list.append(d[1])
        else:
            flat_list.append(d)
    return flat_list


def check_rules(original_counter, key_layout, world, player):
    all_key_only = set()
    key_only_map = {}
    queue = deque([(None, original_counter, original_counter.key_only_locations)])
    completed = set()
    completed.add(cid(original_counter, key_layout))
    while len(queue) > 0:
        queue = deque(sorted(queue, key=queue_sorter_2))
        access_door, counter, key_only_loc = queue.popleft()
        for loc in key_only_loc:
            if loc not in all_key_only:
                all_key_only.add(loc)
                access_rules = []
                key_only_map[loc] = access_rules
            else:
                access_rules = key_only_map[loc]
            if access_door is None or access_door.name not in key_layout.key_logic.door_rules.keys():
                if access_door is None or not access_door.bigKey:
                    access_rules.append(DoorRules(0, True))
            else:
                rule = key_layout.key_logic.door_rules[access_door.name]
                if rule not in access_rules:
                    access_rules.append(rule)
        for child in counter.child_doors.keys():
            if not child.bigKey or not key_layout.big_key_special or counter.big_key_opened:
                next_counter = find_next_counter(child, counter, key_layout)
                c_id = cid(next_counter, key_layout)
                if c_id not in completed:
                    completed.add(c_id)
                    new_key_only = dict_difference(next_counter.key_only_locations, counter.key_only_locations)
                    queue.append((child, next_counter, new_key_only))
    min_rule_bk = defaultdict(list)
    min_rule_non_bk = defaultdict(list)
    check_non_bk = False
    for loc, rule_list in key_only_map.items():
        m_bk = None
        m_nbk = None
        for rule in rule_list:
            if m_bk is None or rule.small_key_num <= m_bk:
                min_rule_bk[loc].append(rule)
                m_bk = rule.small_key_num
            if rule.alternate_small_key is None:
                ask = rule.small_key_num
            else:
                check_non_bk = True
                ask = rule.alternate_small_key
            if m_nbk is None or ask <= m_nbk:
                min_rule_non_bk[loc].append(rule)
                m_nbk = rule.alternate_small_key
    adjust_key_location_mins(key_layout, min_rule_bk, lambda r: r.small_key_num, lambda r, v: setattr(r, 'small_key_num', v))
    if check_non_bk:
        adjust_key_location_mins(key_layout, min_rule_non_bk, lambda r: r.small_key_num if r.alternate_small_key is None else r.alternate_small_key,
                                 lambda r, v: r if r.alternate_small_key is None else setattr(r, 'alternate_small_key', v))
    check_rules_deep(original_counter, key_layout, world, player)


def adjust_key_location_mins(key_layout, min_rules, getter, setter):
    collected_keys = key_layout.max_chests
    collected_locs = set()
    changed = True
    while changed:
        changed = False
        for_removal = []
        for loc, rules in min_rules.items():
            if loc in collected_locs:
                for_removal.append(loc)
            for rule in rules:
                if getter(rule) <= collected_keys and loc not in collected_locs:
                    changed = True
                    collected_keys += 1
                    collected_locs.add(loc)
                    for_removal.append(loc)
        for loc in for_removal:
            del min_rules[loc]
    if len(min_rules) > 0:
        for loc, rules in min_rules.items():
            for rule in rules:
                setter(rule, collected_keys)


def check_rules_deep(original_counter, key_layout, world, player):
    key_logic = key_layout.key_logic
    big_locations = {x for x in key_layout.all_chest_locations if x not in key_logic.bk_restricted}
    queue = deque([original_counter])
    completed = set()
    completed.add(cid(original_counter, key_layout))
    last_counter = None
    bail = 0
    while len(queue) > 0:
        counter = queue.popleft()
        if counter == last_counter:
            bail += 1
            if bail > 10:
                raise Exception('Key logic issue, during deep rule check: %s' % key_layout.sector.name)
        else:
            bail = 0
        last_counter = counter
        chest_keys = available_chest_small_keys_logic(counter, world, player, key_logic.sm_restricted)
        big_avail = counter.big_key_opened
        big_maybe_not_found = not counter.big_key_opened
        if not key_layout.big_key_special and not big_avail:
            for location in counter.free_locations:
                if location not in key_logic.bk_restricted:
                    big_avail = True
                    break
        outstanding_big_locs = {x for x in big_locations if x not in counter.free_locations}
        if big_maybe_not_found:
            if len(outstanding_big_locs) == 0:
                big_maybe_not_found = False
        big_uses_chest = big_avail and not key_layout.big_key_special
        collected_alt = len(counter.key_only_locations) + chest_keys
        if big_uses_chest and chest_keys == count_locations_big_optional(counter.free_locations, counter.big_key_opened):
            chest_keys -= 1
        collected = len(counter.key_only_locations) + chest_keys
        can_progress = len(counter.child_doors) == 0
        smalls_opened = False
        small_rules = []
        for door in counter.child_doors.keys():
            can_open = False
            if door.bigKey and big_avail:
                can_open = True
            elif door.name in key_logic.door_rules.keys():
                rule = key_logic.door_rules[door.name]
                small_rules.append(rule)
                if rule_satisfied(rule, collected, collected_alt, outstanding_big_locs, chest_keys, key_layout):
                    can_open = True
                    smalls_opened = True
            elif not door.bigKey:
                can_open = True
            if can_open:
                can_progress = smalls_opened or not big_maybe_not_found
                next_counter = find_next_counter(door, counter, key_layout)
                c_id = cid(next_counter, key_layout)
                if c_id not in completed:
                    completed.add(c_id)
                    queue.append(next_counter)
        if not can_progress:
            if len(small_rules) > 0:  # zero could be indicative of a problem, but also, the big key is now required
                reduce_rules(small_rules, collected, collected_alt)
                queue.append(counter)  # run it through again
            else:
                raise Exception('Possible problem with generation or bk rules')


def rule_satisfied(rule, collected, collected_alt, outstanding_big_locs, chest_keys, key_layout):
    if collected >= rule.small_key_num:
        return True
    if rule.allow_small and collected >= rule.small_key_num-1 and chest_keys < key_layout.max_chests:
        return True
    rule_diff = outstanding_big_locs.difference(rule.alternate_big_key_loc)
    if rule.alternate_small_key is not None and len(rule_diff) == 0 and collected >= rule.alternate_small_key:
        return True
    if collected_alt > collected:
        if collected_alt >= rule.small_key_num:
            return True
        if rule.allow_small and collected_alt >= rule.small_key_num-1 and chest_keys+1 < key_layout.max_chests:
            return True
        if rule.alternate_small_key is not None and len(rule_diff) == 0 and collected_alt >= rule.alternate_small_key:
            return True
    return False


def reduce_rules(small_rules, collected, collected_alt):
    smallest_rules = []
    min_num = None
    for rule in small_rules:
        if min_num is None or rule.small_key_num <= min_num:
            if min_num is not None and rule.small_key_num < min_num:
                min_num = rule.small_key_num
                smallest_rules.clear()
            elif min_num is None:
                min_num = rule.small_key_num
            smallest_rules.append(rule)
    for rule in smallest_rules:
        if rule.allow_small:  # we are already reducing it
            rule.allow_small = False
        if min_num > collected_alt > collected:
            rule.small_key_num = collected_alt
        else:
            rule.small_key_num = collected


# Soft lock stuff
def validate_key_layout(key_layout, world, player):
    if world.retro[player]:  # retro is all good - don't care how the doors are laid out
        return True
    flat_proposal = key_layout.flat_prop
    state = ExplorationState(dungeon=key_layout.sector.name)
    state.key_locations = key_layout.max_chests
    state.big_key_special = world.get_region('Hyrule Dungeon Cellblock', player) in key_layout.sector.regions
    for region in key_layout.start_regions:
        state.visit_region(region, key_checks=True)
        state.add_all_doors_check_keys(region, flat_proposal, world, player)
    return validate_key_layout_sub_loop(key_layout, state, {}, flat_proposal, None, None, world, player)


def validate_key_layout_sub_loop(key_layout, state, checked_states, flat_proposal, prev_state, prev_avail, world, player):
    expand_key_state(state, flat_proposal, world, player)
    smalls_avail = len(state.small_doors) > 0   # de-dup crystal repeats
    num_bigs = 1 if len(state.big_doors) > 0 else 0  # all or nothing
    if not smalls_avail and num_bigs == 0:
        return True   # I think that's the end
    # todo: fix state to separate out these types
    ttl_locations = count_free_locations(state) if state.big_key_opened else count_locations_exclude_big_chest(state)
    ttl_key_only = count_key_only_locations(state)
    available_small_locations = cnt_avail_small_locations(ttl_locations, ttl_key_only, state, world, player)
    available_big_locations = cnt_avail_big_locations(ttl_locations, state, world, player)
    if invalid_self_locking_key(state, prev_state, prev_avail, world, player):
        return False
    if (not smalls_avail or not enough_small_locations(state, available_small_locations)) and (state.big_key_opened or num_bigs == 0 or available_big_locations == 0):
        return False
    else:
        if smalls_avail and available_small_locations > 0:
            for exp_door in state.small_doors:
                state_copy = state.copy()
                open_a_door(exp_door.door, state_copy, flat_proposal)
                state_copy.used_smalls += 1
                if state_copy.used_smalls > ttl_key_only:
                    state_copy.used_locations += 1
                code = state_id(state_copy, flat_proposal)
                if code not in checked_states.keys():
                    valid = validate_key_layout_sub_loop(key_layout, state_copy, checked_states, flat_proposal,
                                                         state, available_small_locations, world, player)
                    checked_states[code] = valid
                else:
                    valid = checked_states[code]
                if not valid:
                    return False
        if not state.big_key_opened and available_big_locations >= num_bigs > 0:
            state_copy = state.copy()
            open_a_door(state.big_doors[0].door, state_copy, flat_proposal)
            state_copy.used_locations += 1
            code = state_id(state_copy, flat_proposal)
            if code not in checked_states.keys():
                valid = validate_key_layout_sub_loop(key_layout, state_copy, checked_states, flat_proposal,
                                                     state, available_small_locations, world, player)
                checked_states[code] = valid
            else:
                valid = checked_states[code]
            if not valid:
                return False
    return True


def invalid_self_locking_key(state, prev_state, prev_avail, world, player):
    if prev_state is None or state.used_smalls == prev_state.used_smalls:
        return False
    new_locations = set(state.found_locations).difference(set(prev_state.found_locations))
    important_found = False
    for loc in new_locations:
        important_found |= important_location(loc, world, player)
    if not important_found:
        return False
    new_small_doors = set(state.small_doors).difference(set(prev_state.small_doors))
    new_bk_doors = set(state.big_doors).difference(set(prev_state.big_doors))
    if len(new_small_doors) > 0 or len(new_bk_doors) > 0:
        return False
    return prev_avail - 1 == 0


# does not allow dest doors
def count_unique_sm_doors(doors):
    unique_d_set = set()
    for d in doors:
        if d not in unique_d_set and d.dest not in unique_d_set and not d.bigKey:
            unique_d_set.add(d)
    return len(unique_d_set)


def enough_small_locations(state, avail_small_loc):
    unique_d_set = set()
    for exp_door in state.small_doors:
        door = exp_door.door
        if door not in unique_d_set and door.dest not in unique_d_set:
            unique_d_set.add(door)
    return avail_small_loc >= len(unique_d_set)


def cnt_avail_small_locations(free_locations, key_only, state, world, player):
    if not world.keyshuffle[player] and not world.retro[player]:
        bk_adj = 1 if state.big_key_opened and not state.big_key_special else 0
        avail_chest_keys = min(free_locations - bk_adj, state.key_locations - key_only)
        return max(0, avail_chest_keys + key_only - state.used_smalls)
    return state.key_locations - state.used_smalls


def cnt_avail_big_locations(ttl_locations, state, world, player):
    if not world.bigkeyshuffle[player]:
        return max(0, ttl_locations - state.used_locations) if not state.big_key_special else 0
    return 1 if not state.big_key_special else 0


def create_key_counters(key_layout, world, player):
    key_counters = {}
    flat_proposal = key_layout.flat_prop
    state = ExplorationState(dungeon=key_layout.sector.name)
    state.key_locations = len(world.get_dungeon(key_layout.sector.name, player).small_keys)
    state.big_key_special = world.get_region('Hyrule Dungeon Cellblock', player) in key_layout.sector.regions
    for region in key_layout.start_regions:
        state.visit_region(region, key_checks=True)
        state.add_all_doors_check_keys(region, flat_proposal, world, player)
    expand_key_state(state, flat_proposal, world, player)
    code = state_id(state, key_layout.flat_prop)
    key_counters[code] = create_key_counter(state, key_layout, world, player)
    queue = deque([(key_counters[code], state)])
    while len(queue) > 0:
        next_key_counter, parent_state = queue.popleft()
        for door in next_key_counter.child_doors:
            child_state = parent_state.copy()
            if door.bigKey:
                key_layout.key_logic.bk_doors.add(door)
            # open the door, if possible
            if not door.bigKey or not child_state.big_key_special or child_state.big_key_opened:
                open_a_door(door, child_state, flat_proposal)
                expand_key_state(child_state, flat_proposal, world, player)
                code = state_id(child_state, key_layout.flat_prop)
                if code not in key_counters.keys():
                    child_kr = create_key_counter(child_state, key_layout, world, player)
                    key_counters[code] = child_kr
                    queue.append((child_kr, child_state))
    return key_counters


def create_key_counter(state, key_layout, world, player):
    key_counter = KeyCounter(key_layout.max_chests)
    key_counter.child_doors.update(dict.fromkeys(unique_doors(state.small_doors+state.big_doors)))
    for loc in state.found_locations:
        if important_location(loc, world, player):
            key_counter.important_location = True
            key_counter.other_locations[loc] = None
        elif loc.event and 'Small Key' in loc.item.name:
            key_counter.key_only_locations[loc] = None
        elif loc.name not in dungeon_events:
            key_counter.free_locations[loc] = None
        else:
            key_counter.other_locations[loc] = None
    key_counter.open_doors.update(dict.fromkeys(state.opened_doors))
    key_counter.used_keys = count_unique_sm_doors(state.opened_doors)
    if state.big_key_special:
        key_counter.big_key_opened = state.visited(world.get_region('Hyrule Dungeon Cellblock', player))
    else:
        key_counter.big_key_opened = state.big_key_opened
    # if soft_lock_check:
    #     avail_chests = available_chest_small_keys(key_counter, key_counter.big_key_opened, world)
    #     avail_keys = avail_chests + len(key_counter.key_only_locations)
    #     if avail_keys <= key_counter.used_keys and avail_keys < key_layout.max_chests + key_layout.max_drops:
    #         raise SoftLockException()
    return key_counter


def important_location(loc, world, player):
    important_locations = ['Agahnim 1', 'Agahnim 2', 'Attic Cracked Floor', 'Suspicious Maiden']
    if world.mode[player] == 'standard' or world.doorShuffle[player] == 'crossed':
        important_locations.append('Hyrule Dungeon Cellblock')
    return '- Prize' in loc.name or loc.name in important_locations


def create_odd_key_counter(door, parent_counter, key_layout, world, player):
    odd_counter = KeyCounter(key_layout.max_chests)
    next_counter = find_next_counter(door, parent_counter, key_layout)
    odd_counter.free_locations = dict_difference(next_counter.free_locations, parent_counter.free_locations)
    odd_counter.key_only_locations = dict_difference(next_counter.key_only_locations, parent_counter.key_only_locations)
    odd_counter.child_doors = dict_difference(next_counter.child_doors, parent_counter.child_doors)
    odd_counter.other_locations = dict_difference(next_counter.other_locations, parent_counter.other_locations)
    for loc in odd_counter.other_locations:
        if important_location(loc, world, player):
            odd_counter.important_location = True
    return odd_counter


def dict_difference(dict_a, dict_b):
    return dict.fromkeys([x for x in dict_a.keys() if x not in dict_b.keys()])


def dict_intersection(dict_a, dict_b):
    return dict.fromkeys([x for x in dict_a.keys() if x in dict_b.keys()])


def state_id(state, flat_proposal):
    s_id = '1' if state.big_key_opened else '0'
    for d in flat_proposal:
        s_id += '1' if d in state.opened_doors else '0'
    return s_id


def find_counter(opened_doors, bk_hint, key_layout, raise_on_error=True):
    counter = find_counter_hint(opened_doors, bk_hint, key_layout)
    if counter is not None:
        return counter
    more_doors = []
    for door in opened_doors.keys():
        more_doors.append(door)
        if door.dest not in opened_doors.keys():
            more_doors.append(door.dest)
    if len(more_doors) > len(opened_doors.keys()):
        counter = find_counter_hint(dict.fromkeys(more_doors), bk_hint, key_layout)
        if counter is not None:
            return counter
    if raise_on_error:
        raise Exception('Unable to find door permutation. Init CID: %s' % counter_id(opened_doors, bk_hint, key_layout.flat_prop))
    return None


def find_counter_hint(opened_doors, bk_hint, key_layout):
    cid = counter_id(opened_doors, bk_hint, key_layout.flat_prop)
    if cid in key_layout.key_counters.keys():
        return key_layout.key_counters[cid]
    if not bk_hint:
        cid = counter_id(opened_doors, True, key_layout.flat_prop)
        if cid in key_layout.key_counters.keys():
            return key_layout.key_counters[cid]
    return None


def find_max_counter(key_layout):
    max_counter = find_counter_hint(dict.fromkeys(key_layout.flat_prop), False, key_layout)
    if len(max_counter.child_doors) > 0:
        max_counter = find_counter_hint(dict.fromkeys(key_layout.flat_prop), True, key_layout)
    return max_counter


def counter_id(opened_doors, bk_unlocked, flat_proposal):
    s_id = '1' if bk_unlocked else '0'
    for d in flat_proposal:
        s_id += '1' if d in opened_doors.keys() else '0'
    return s_id


def cid(counter, key_layout):
    return counter_id(counter.open_doors, counter.big_key_opened, key_layout.flat_prop)


# class SoftLockException(Exception):
#     pass


# vanilla validation code
def validate_vanilla_key_logic(world, player):
    validators = {
        'Hyrule Castle': val_hyrule,
        'Eastern Palace': val_eastern,
        'Desert Palace': val_desert,
        'Tower of Hera': val_hera,
        'Agahnims Tower': val_tower,
        'Palace of Darkness': val_pod,
        'Swamp Palace': val_swamp,
        'Skull Woods': val_skull,
        'Thieves Town': val_thieves,
        'Ice Palace': val_ice,
        'Misery Mire': val_mire,
        'Turtle Rock': val_turtle,
        'Ganons Tower': val_ganons
    }
    key_logic_dict = world.key_logic[player]
    for key, key_logic in key_logic_dict.items():
        validators[key](key_logic, world, player)


def val_hyrule(key_logic, world, player):
    if world.mode[player] == 'standard':
        val_rule(key_logic.door_rules['Hyrule Dungeon Map Room Key Door S'], 1)
        val_rule(key_logic.door_rules['Hyrule Dungeon Armory Interior Key Door N'], 2)
        val_rule(key_logic.door_rules['Sewers Dark Cross Key Door N'], 3)
        val_rule(key_logic.door_rules['Sewers Key Rat Key Door N'], 4)
    else:
        val_rule(key_logic.door_rules['Sewers Secret Room Key Door S'], 2)
        val_rule(key_logic.door_rules['Sewers Dark Cross Key Door N'], 2)
        val_rule(key_logic.door_rules['Hyrule Dungeon Map Room Key Door S'], 2)
        val_rule(key_logic.door_rules['Hyrule Dungeon Armory Interior Key Door N'], 4)


def val_eastern(key_logic, world, player):
    val_rule(key_logic.door_rules['Eastern Dark Square Key Door WN'], 2, True, 'Eastern Palace - Big Key Chest', 1, {'Eastern Palace - Big Key Chest'})
    val_rule(key_logic.door_rules['Eastern Darkness Up Stairs'], 2)
    assert world.get_location('Eastern Palace - Big Chest', player) in key_logic.bk_restricted
    assert world.get_location('Eastern Palace - Boss', player) in key_logic.bk_restricted
    assert len(key_logic.bk_restricted) == 2


def val_desert(key_logic, world, player):
    val_rule(key_logic.door_rules['Desert East Wing Key Door EN'], 4)
    val_rule(key_logic.door_rules['Desert Tiles 1 Up Stairs'], 2)
    val_rule(key_logic.door_rules['Desert Beamos Hall NE'], 3)
    val_rule(key_logic.door_rules['Desert Tiles 2 NE'], 4)
    assert world.get_location('Desert Palace - Big Chest', player) in key_logic.bk_restricted
    assert world.get_location('Desert Palace - Boss', player) in key_logic.bk_restricted
    assert len(key_logic.bk_restricted) == 2


def val_hera(key_logic, world, player):
    val_rule(key_logic.door_rules['Hera Lobby Key Stairs'], 1, True, 'Tower of Hera - Big Key Chest')
    assert world.get_location('Tower of Hera - Big Chest', player) in key_logic.bk_restricted
    assert world.get_location('Tower of Hera - Compass Chest', player) in key_logic.bk_restricted
    assert world.get_location('Tower of Hera - Boss', player) in key_logic.bk_restricted
    assert len(key_logic.bk_restricted) == 3


def val_tower(key_logic, world, player):
    val_rule(key_logic.door_rules['Tower Room 03 Up Stairs'], 1)
    val_rule(key_logic.door_rules['Tower Dark Maze ES'], 2)
    val_rule(key_logic.door_rules['Tower Dark Archers Up Stairs'], 3)
    val_rule(key_logic.door_rules['Tower Circle of Pots WS'], 4)


def val_pod(key_logic, world, player):
    val_rule(key_logic.door_rules['PoD Arena Main NW'], 4)
    val_rule(key_logic.door_rules['PoD Basement Ledge Up Stairs'], 6, True, 'Palace of Darkness - Big Key Chest')
    val_rule(key_logic.door_rules['PoD Compass Room SE'], 6, True, 'Palace of Darkness - Harmless Hellway')
    val_rule(key_logic.door_rules['PoD Falling Bridge WN'], 6)
    val_rule(key_logic.door_rules['PoD Dark Pegs WN'], 6)
    assert world.get_location('Palace of Darkness - Big Chest', player) in key_logic.bk_restricted
    assert world.get_location('Palace of Darkness - Boss', player) in key_logic.bk_restricted
    assert len(key_logic.bk_restricted) == 2


def val_swamp(key_logic, world, player):
    val_rule(key_logic.door_rules['Swamp Entrance Down Stairs'], 1)
    val_rule(key_logic.door_rules['Swamp Pot Row WS'], 2)
    val_rule(key_logic.door_rules['Swamp Trench 1 Key Ledge NW'], 3)
    val_rule(key_logic.door_rules['Swamp Hub North Ledge N'], 5)
    val_rule(key_logic.door_rules['Swamp Hub WN'], 6)
    val_rule(key_logic.door_rules['Swamp Waterway NW'], 6)
    assert world.get_location('Swamp Palace - Entrance', player) in key_logic.bk_restricted
    assert len(key_logic.bk_restricted) == 1


def val_skull(key_logic, world, player):
    val_rule(key_logic.door_rules['Skull 3 Lobby NW'], 4)
    val_rule(key_logic.door_rules['Skull Spike Corner ES'], 5)


def val_thieves(key_logic, world, player):
    val_rule(key_logic.door_rules['Thieves Hallway WS'], 1)
    val_rule(key_logic.door_rules['Thieves Spike Switch Up Stairs'], 3)
    val_rule(key_logic.door_rules['Thieves Conveyor Bridge WS'], 3, True, 'Thieves\' Town - Big Chest')
    assert world.get_location('Thieves\' Town - Attic', player) in key_logic.bk_restricted
    assert world.get_location('Thieves\' Town - Boss', player) in key_logic.bk_restricted
    assert world.get_location('Thieves\' Town - Blind\'s Cell', player) in key_logic.bk_restricted
    assert world.get_location('Thieves\' Town - Big Chest', player) in key_logic.bk_restricted
    assert len(key_logic.bk_restricted) == 4


def val_ice(key_logic, world, player):
    val_rule(key_logic.door_rules['Ice Jelly Key Down Stairs'], 1)
    val_rule(key_logic.door_rules['Ice Conveyor SW'], 2)
    val_rule(key_logic.door_rules['Ice Backwards Room Down Stairs'], 5)
    assert world.get_location('Ice Palace - Boss', player) in key_logic.bk_restricted
    assert world.get_location('Ice Palace - Big Chest', player) in key_logic.bk_restricted
    assert len(key_logic.bk_restricted) == 2


def val_mire(key_logic, world, player):
    mire_west_wing = {'Misery Mire - Big Key Chest', 'Misery Mire - Compass Chest'}
    val_rule(key_logic.door_rules['Mire Spikes NW'], 3)  # todo: is sometimes 3 or 5? best_counter order matters
    # val_rule(key_logic.door_rules['Mire Spike Barrier NE'], 4)  # kind of a waste mostly
    val_rule(key_logic.door_rules['Mire Hub WS'], 5, False, None, 3, mire_west_wing)
    val_rule(key_logic.door_rules['Mire Conveyor Crystal WS'], 6, False, None, 4, mire_west_wing)
    assert world.get_location('Misery Mire - Boss', player) in key_logic.bk_restricted
    assert world.get_location('Misery Mire - Big Chest', player) in key_logic.bk_restricted
    assert len(key_logic.bk_restricted) == 2


def val_turtle(key_logic, world, player):
    # todo: check vanilla key logic when TR back doors are accessible
    if world.shuffle[player] == 'vanilla' and world.mode[player] != 'inverted':
        val_rule(key_logic.door_rules['TR Hub NW'], 1)
        val_rule(key_logic.door_rules['TR Pokey 1 NW'], 2)
        val_rule(key_logic.door_rules['TR Chain Chomps Down Stairs'], 3)
        val_rule(key_logic.door_rules['TR Pokey 2 ES'], 6, True, 'Turtle Rock - Big Key Chest', 4, {'Turtle Rock - Big Key Chest'})
        val_rule(key_logic.door_rules['TR Crystaroller Down Stairs'], 5)
        val_rule(key_logic.door_rules['TR Dash Bridge WS'], 6)
        assert world.get_location('Turtle Rock - Eye Bridge - Bottom Right', player) in key_logic.bk_restricted
        assert world.get_location('Turtle Rock - Eye Bridge - Top Left', player) in key_logic.bk_restricted
        assert world.get_location('Turtle Rock - Eye Bridge - Top Right', player) in key_logic.bk_restricted
        assert world.get_location('Turtle Rock - Eye Bridge - Bottom Left', player) in key_logic.bk_restricted
        assert world.get_location('Turtle Rock - Boss', player) in key_logic.bk_restricted
        assert world.get_location('Turtle Rock - Crystaroller Room', player) in key_logic.bk_restricted
        assert world.get_location('Turtle Rock - Big Chest', player) in key_logic.bk_restricted
        assert len(key_logic.bk_restricted) == 7


def val_ganons(key_logic, world, player):
    rando_room = {'Ganons Tower - Randomizer Room - Top Left', 'Ganons Tower - Randomizer Room - Top Right', 'Ganons Tower - Randomizer Room - Bottom Left', 'Ganons Tower - Randomizer Room - Bottom Right'}
    compass_room = {'Ganons Tower - Compass Room - Top Left', 'Ganons Tower - Compass Room - Top Right', 'Ganons Tower - Compass Room - Bottom Left', 'Ganons Tower - Compass Room - Bottom Right'}
    gt_middle = {'Ganons Tower - Big Key Room - Left', 'Ganons Tower - Big Key Chest', 'Ganons Tower - Big Key Room - Right', 'Ganons Tower - Bob\'s Chest', 'Ganons Tower - Big Chest'}
    val_rule(key_logic.door_rules['GT Double Switch EN'], 6, False, None, 4, rando_room.union({'Ganons Tower - Firesnake Room'}))
    val_rule(key_logic.door_rules['GT Hookshot ES'], 7, False, 'Ganons Tower - Map Chest', 5, {'Ganons Tower - Map Chest'})
    val_rule(key_logic.door_rules['GT Tile Room EN'], 6, False, None, 5, compass_room)
    val_rule(key_logic.door_rules['GT Firesnake Room SW'], 7, False, None, 5, rando_room)
    val_rule(key_logic.door_rules['GT Conveyor Star Pits EN'], 6, False, None, 5, gt_middle)  # should be 7?
    val_rule(key_logic.door_rules['GT Mini Helmasaur Room WN'], 6)  # not sure about this 6...
    val_rule(key_logic.door_rules['GT Crystal Circles SW'], 8)
    assert world.get_location('Ganons Tower - Mini Helmasaur Room - Left', player) in key_logic.bk_restricted
    assert world.get_location('Ganons Tower - Mini Helmasaur Room - Right', player) in key_logic.bk_restricted
    assert world.get_location('Ganons Tower - Big Chest', player) in key_logic.bk_restricted
    assert world.get_location('Ganons Tower - Pre-Moldorm Chest', player) in key_logic.bk_restricted
    assert world.get_location('Ganons Tower - Validation Chest', player) in key_logic.bk_restricted
    assert len(key_logic.bk_restricted) == 5


def val_rule(rule, skn, allow=False, loc=None, askn=None, setCheck=None):
    if setCheck is None:
        setCheck = set()
    assert rule.small_key_num == skn
    assert rule.allow_small == allow
    assert rule.small_location == loc or rule.small_location.name == loc
    assert rule.alternate_small_key == askn
    assert len(setCheck) == len(rule.alternate_big_key_loc)
    for loc in rule.alternate_big_key_loc:
        assert loc.name in setCheck


# Soft lock stuff
def validate_key_placement(key_layout, world, player):
    if world.retro[player] or world.accessibility[player] == 'none':
        return True  # Can't keylock in retro.  Expected if beatable only.
    max_counter = find_max_counter(key_layout)
    keys_outside = 0
    big_key_outside = False
    dungeon = world.get_dungeon(key_layout.sector.name, player)
    smallkey_name = 'Small Key (%s)' % (key_layout.sector.name if key_layout.sector.name != 'Hyrule Castle' else 'Escape')
    if world.keyshuffle[player]:
        keys_outside = key_layout.max_chests - sum(1 for i in max_counter.free_locations if i.item is not None and i.item.name == smallkey_name and i.item.player == player)
    if world.bigkeyshuffle[player]:
        max_counter = find_max_counter(key_layout)
        big_key_outside = dungeon.big_key not in (l.item for l in max_counter.free_locations)

    for counter in key_layout.key_counters.values():
        if len(counter.child_doors) == 0:
            continue
        big_found = any(i.item == dungeon.big_key for i in counter.free_locations if "- Big Chest" not in i.name) or big_key_outside
        if counter.big_key_opened and not big_found:
            continue  # Can't get to this state
        found_locations = set(i for i in counter.free_locations if big_found or "- Big Chest" not in i.name)
        found_keys = sum(1 for i in found_locations if i.item is not None and i.item.name == smallkey_name and i.item.player == player) + \
                     len(counter.key_only_locations) + keys_outside
        can_progress = (not counter.big_key_opened and big_found and any(d.bigKey for d in counter.child_doors)) or \
                       found_keys > counter.used_keys and any(not d.bigKey for d in counter.child_doors)
        if not can_progress:
            missing_locations = set(max_counter.free_locations.keys()).difference(found_locations)
            missing_items = [l for l in missing_locations if l.item is None or (l.item.name != smallkey_name and l.item != dungeon.big_key) or "- Boss" in l.name]
            # missing_key_only = set(max_counter.key_only_locations.keys()).difference(counter.key_only_locations.keys()) # do freestanding keys matter for locations?
            if len(missing_items) > 0: # world.accessibility[player]=='locations' and (len(missing_locations)>0 or len(missing_key_only) > 0):
                logging.getLogger('').error("Keylock - can't open locations: ")
                for i in missing_locations:
                    logging.getLogger('').error(i)
                return False

    return True

