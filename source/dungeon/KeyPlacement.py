import itertools

from KeyDoorShuffle import PlacementRule


def create_exhaustive_placement_rules(key_layout, bk_restrictions, world, player):
    key_logic = key_layout.key_logic
    max_ctr = find_max_counter(key_layout)
    if max_ctr is None:
        return False
    for code, key_counter in key_layout.key_counters.items():
        if skip_key_counter_due_to_prize(key_layout, key_counter):
            continue  # we have the prize, we are not concerned about this case
        accessible_loc = set()
        accessible_loc.update(key_counter.free_locations)
        accessible_loc.update(key_counter.key_only_locations)
        accessible_loc.update([l for l in key_counter.important_locations if l.forced_big_key()])
        blocked_loc = key_layout.item_locations.difference(accessible_loc)
        valid_rule = True
        # Only add 1 if there are small key doors that need to be opened
        has_small_key_doors = any(door in key_layout.flat_prop for door in key_counter.child_doors)
        min_keys = key_counter.used_keys + (1 if has_small_key_doors else 0)
        if len(blocked_loc) > 0:
            rule = PlacementRule()
            rule.door_reference = code
            rule.small_key = key_logic.small_key_name
            if key_counter.big_key_opened or not big_key_progress(key_counter):
                rule.needed_keys_w_bk = min_keys
                rule.bk_relevant = key_counter.big_key_opened
                placement_self_lock_adjustment(rule, max_ctr, blocked_loc, key_counter, world, player)
                rule.check_locations_w_bk = accessible_loc
                if key_layout.big_key_special:
                    rule.special_bk_avail = forced_big_key_avail(key_counter.important_locations) is not None
                    # check_sm_restriction_needed(key_layout, max_ctr, rule, blocked_loc)
            else:
                if big_key_progress(key_counter) and only_sm_doors(key_counter):
                    create_inclusive_rule(key_layout, max_ctr, code, key_counter, blocked_loc, accessible_loc, min_keys, world, player)
                conditional_set = blocked_loc.difference(bk_restrictions)
                if len(conditional_set) == 0:
                    valid_rule = False  # the big key can't be blocked at this point
                rule.bk_conditional_set = conditional_set
                rule.needed_keys_wo_bk = min_keys
                rule.check_locations_wo_bk = set(filter_big_chest(accessible_loc))
                rule.prize_relevance = key_layout.prize_relevant if rule_prize_relevant(key_counter) else None
            if valid_rule:
                key_logic.placement_rules.append(rule)
                adjust_locations_rules(key_logic, rule, accessible_loc, key_layout, key_counter, max_ctr)
    refine_placement_rules(key_layout, bk_restrictions)
    return True


def skip_key_counter_due_to_prize(key_layout, key_counter):
    return key_layout.prize_relevant and key_counter.prize_received and not key_counter.prize_doors_opened


def find_counter_hint(opened_doors, bk_hint, key_layout, prize_flag):
    cid = counter_id(opened_doors, bk_hint, key_layout.flat_prop, key_layout.prize_relevant, prize_flag)
    if cid in key_layout.key_counters.keys():
        return cid, key_layout.key_counters[cid]
    if not bk_hint:
        cid = counter_id(opened_doors, True, key_layout.flat_prop, key_layout.prize_relevant, prize_flag)
        if cid in key_layout.key_counters.keys():
            return cid, key_layout.key_counters[cid]
    return None, None


def find_max_counter(key_layout):
    max_cid, max_counter = find_counter_hint(dict.fromkeys(key_layout.flat_prop), False, key_layout, True)
    if max_counter is None:
        return None
    if len(max_counter.child_doors) > 0:
        max_cid, max_counter = find_counter_hint(dict.fromkeys(key_layout.flat_prop), True, key_layout, True)
    if max_cid and not all(c == '1' for c in max_cid[1:]):
        raise Exception(f'Max counter ID is not all 1s: {max_cid}')
        # logging.getLogger('').warning(f'Max counter ID is not all 1s: {max_cid}')
    return max_counter

def counter_id(opened_doors, bk_unlocked, flat_proposal, prize_relevant, prize_flag):
    s_id = '1' if bk_unlocked else '0'
    for d in flat_proposal:
        s_id += '1' if d in opened_doors.keys() else '0'
    if prize_relevant:
        s_id += '1' if prize_flag else '0'
    return s_id

def big_key_progress(key_counter):
    return not only_sm_doors(key_counter) or exist_big_chest(key_counter)

def only_sm_doors(key_counter):
    for door in key_counter.child_doors:
        if door.bigKey:
            return False
    return True

def exist_big_chest(key_counter):
    for loc in key_counter.free_locations:
        if '- Big Chest' in loc.name:
            return True
    return False

def placement_self_lock_adjustment(rule, max_ctr, blocked_loc, ctr, world, player):
    if len(blocked_loc) == 1 and world.accessibility[player] != 'locations':
        blocked_others = set(max_ctr.other_locations).difference(set(ctr.other_locations))
        important_found = False
        for loc in blocked_others:
            if important_location(loc, world, player):
                important_found = True
                break
        if not important_found:
            rule.needed_keys_w_bk -= 1

def important_location(loc, world, player):
    return '- Prize' in loc.name or loc.name in imp_locations_factory(world, player) or (loc.forced_big_key())

imp_locations = None

def imp_locations_factory(world, player):
    global imp_locations
    if imp_locations:
        return imp_locations
    imp_locations = ['Agahnim 1', 'Agahnim 2', 'Attic Cracked Floor', 'Suspicious Maiden']
    if world.mode[player] == 'standard':
        imp_locations.append('Zelda Pickup')
        imp_locations.append('Zelda Drop Off')
    return imp_locations

def forced_big_key_avail(locations):
    for loc in locations:
        if loc.forced_big_key:
            return loc
    return None

def filter_big_chest(locations):
    return [x for x in locations if '- Big Chest' not in x.name]

def rule_prize_relevant(key_counter):
    return not key_counter.prize_doors_opened and not key_counter.prize_received

def create_inclusive_rule(key_layout, max_ctr, code, key_counter, blocked_loc, accessible_loc, min_keys, world, player):
    key_logic = key_layout.key_logic
    rule = PlacementRule()
    rule.door_reference = code
    rule.small_key = key_logic.small_key_name
    rule.needed_keys_w_bk = min_keys
    if key_counter.big_key_opened and rule.needed_keys_w_bk + 1 > len(accessible_loc):
        key_logic.bk_restricted.update(set(accessible_loc).difference(max_ctr.key_only_locations))
    else:
        placement_self_lock_adjustment(rule, max_ctr, blocked_loc, key_counter, world, player)
        rule.check_locations_w_bk = accessible_loc
        rule.special_bk_avail = forced_big_key_avail(key_counter.important_locations) is not None
        key_logic.placement_rules.append(rule)
        adjust_locations_rules(key_logic, rule, accessible_loc, key_layout, key_counter, max_ctr)

def adjust_locations_rules(key_logic, rule, accessible_loc, key_layout, key_counter, max_ctr):
    if rule.bk_conditional_set:
        test_set = (rule.bk_conditional_set - key_logic.bk_locked) - set(max_ctr.key_only_locations.keys())
        needed = rule.needed_keys_wo_bk if test_set else 0
    else:
        test_set = None
        needed = rule.needed_keys_w_bk
    if needed > 0:
        all_accessible = set(accessible_loc)
        all_accessible.update(key_counter.other_locations)
        blocked_loc = key_layout.all_locations-all_accessible
        for location in blocked_loc:
            if location not in key_logic.location_rules.keys():
                loc_rule = LocationRule()
                key_logic.location_rules[location] = loc_rule
            else:
                loc_rule = key_logic.location_rules[location]
            if test_set:
                if location not in key_logic.bk_locked:
                    cond_rule = None
                    for other in loc_rule.conditional_sets:
                        if other.conditional_set == test_set:
                            cond_rule = other
                            break
                    if not cond_rule:
                        cond_rule = ConditionalLocationRule(test_set)
                        loc_rule.conditional_sets.append(cond_rule)
                    cond_rule.small_key_num = max(needed, cond_rule.small_key_num)
            else:
                loc_rule.small_key_num = max(needed, loc_rule.small_key_num)

class LocationRule(object):
    def __init__(self):
        self.small_key_num = 0
        self.conditional_sets = []

class ConditionalLocationRule(object):
    def __init__(self, conditional_set):
        self.conditional_set = conditional_set
        self.small_key_num = 0

def refine_placement_rules(key_layout, bk_restrictions):
    key_logic = key_layout.key_logic
    max_keys = key_layout.max_chests + key_layout.max_drops
    changed = True
    while changed:
        changed = False
        rules_to_remove = {}
        for rule in key_logic.placement_rules:
            if rule.check_locations_w_bk:
                rule.check_locations_w_bk.difference_update(key_logic.sm_restricted)
            if rule.bk_conditional_set:
                rule.bk_conditional_set.difference_update(key_logic.bk_restricted)
            if rule.check_locations_wo_bk:
                rule.check_locations_wo_bk.difference_update(key_logic.sm_restricted)
        should_continue = changed = detect_more_small_key_restrictions(key_logic, max_keys, key_layout.all_chest_locations)
        if should_continue:
            continue
        for rule_a, rule_b in itertools.combinations([x for x in key_logic.placement_rules if x not in rules_to_remove], 2):
            if rule_b.bk_conditional_set and rule_a.check_locations_w_bk:
                rule_a, rule_b = rule_b, rule_a  # swap for next check
            if rule_a.bk_conditional_set and rule_b.check_locations_w_bk:
                common_needed = min(rule_a.needed_keys_wo_bk, rule_b.needed_keys_w_bk)
                common_locs = len(rule_b.check_locations_w_bk & rule_a.check_locations_wo_bk)
                if (common_needed - common_locs) * 2 > key_layout.max_chests:
                    bk_restrictions.update(rule_a.bk_conditional_set)
                    rules_to_remove[rule_a] = None
                    changed = True
                    break
        equivalent_rules = []
        for rule in key_logic.placement_rules:
            for rule2 in key_logic.placement_rules:
                if rule != rule2 and rule not in rules_to_remove and rule2 not in rules_to_remove:
                    if rule.check_locations_w_bk and rule2.check_locations_w_bk:
                        if rule2.check_locations_w_bk == rule.check_locations_w_bk and rule2.needed_keys_w_bk > rule.needed_keys_w_bk:
                            rules_to_remove[rule] = None
                        elif rule2.needed_keys_w_bk == rule.needed_keys_w_bk and rule2.check_locations_w_bk < rule.check_locations_w_bk:
                            rules_to_remove[rule] = None
                        elif rule2.check_locations_w_bk == rule.check_locations_w_bk and rule2.needed_keys_w_bk == rule.needed_keys_w_bk:
                            equivalent_rules.append((rule, rule2))
                    if rule.check_locations_wo_bk and rule2.check_locations_wo_bk and rule.bk_conditional_set == rule2.bk_conditional_set:
                        if rule2.check_locations_wo_bk == rule.check_locations_wo_bk and rule2.needed_keys_wo_bk > rule.needed_keys_wo_bk:
                            rules_to_remove[rule] = None
                        elif rule2.needed_keys_wo_bk == rule.needed_keys_wo_bk and rule2.check_locations_wo_bk < rule.check_locations_wo_bk:
                            rules_to_remove[rule] = None
                        elif rule2.check_locations_wo_bk == rule.check_locations_wo_bk and rule2.needed_keys_wo_bk == rule.needed_keys_wo_bk:
                            equivalent_rules.append((rule, rule2))
        if len(rules_to_remove) > 0:
            key_logic.placement_rules = [x for x in key_logic.placement_rules if x not in rules_to_remove]
            equivalent_rules = [x for x in equivalent_rules if x[0] not in rules_to_remove and x[1] not in rules_to_remove]
        if len(equivalent_rules) > 0:
            removed_rules = {}
            for r1, r2 in equivalent_rules:
                if r1 in removed_rules.keys():
                    r1 = removed_rules[r1]
                if r2 in removed_rules.keys():
                    r2 = removed_rules[r2]
                if r1 != r2:
                    r1.door_reference += ','+r2.door_reference
                    key_logic.placement_rules.remove(r2)
                    removed_rules[r2] = r1

def detect_more_small_key_restrictions(key_logic, max_keys, chest_locations):
    continue_flag = False
    for rule in key_logic.placement_rules:
        if not rule.bk_conditional_set and rule.needed_keys_w_bk == max_keys:
            excluded_chests = {loc for loc in chest_locations if loc not in rule.check_locations_w_bk}
            original_size = len(key_logic.sm_restricted)
            key_logic.sm_restricted.update(excluded_chests)
            continue_flag = original_size < len(key_logic.sm_restricted)
    return continue_flag