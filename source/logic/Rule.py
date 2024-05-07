import itertools

from collections import OrderedDict
try:
    from fast_enum import FastEnum
except ImportError:
    from enum import IntFlag as FastEnum

from BaseClasses import CrystalBarrier, KeyRuleType
from Dungeons import dungeon_keys


class RuleType(FastEnum):
    Conjunction = 0
    Disjunction = 1
    Item = 2
    Glitch = 3
    Reachability = 4
    Static = 5
    Bottle = 6
    Crystal = 7
    Barrier = 8
    Hearts = 9
    Unlimited = 10
    ExtendMagic = 11
    Boss = 12
    Negate = 13
    LocationCheck = 14
    SmallKeyDoor = 15


class Rule(object):

    def __init__(self, rule_type):
        self.rule_type = rule_type
        self.sub_rules = []
        self.principal = None
        self.player = 0
        self.resolution_hint = None
        self.barrier = None
        self.flag = None
        self.locations = []
        self.count = 1

        self.std_req = None

        self.rule_lambda = lambda state: True

    def eval(self, state):
        return self.rule_lambda(state)

    def get_requirements(self, progressive_flag=True):
        if not self.std_req:
            reqs = rule_requirements[self.rule_type](self, progressive_flag)
            self.std_req = standardize_requirements(reqs, progressive_flag)
        return self.std_req

    def __str__(self):
        return str(self.__unicode__())

    def __unicode__(self):
        return rule_prints[self.rule_type](self)


rule_prints = {
    RuleType.Conjunction: lambda self: f'({" and ".join([str(x) for x in self.sub_rules])})',
    RuleType.Disjunction: lambda self: f'({" or ".join([str(x) for x in self.sub_rules])})',
    RuleType.Item: lambda self: f'has {self.principal}' if self.count == 1 else f'has {self.count} {self.principal}(s)',
    RuleType.Reachability: lambda self: f'canReach {self.principal}',
    RuleType.Static: lambda self: f'{self.principal}',
    RuleType.Crystal: lambda self: f'has {self.principal} crystals',
    RuleType.Barrier: lambda self: f'{self.barrier} @ {self.principal}',
    RuleType.Hearts: lambda self: f'has {self.principal} hearts',
    RuleType.Unlimited: lambda self: f'canBuyUnlimited {self.principal}',
    RuleType.ExtendMagic: lambda self: f'magicNeeded {self.principal}',
    RuleType.Boss: lambda self: f'canDefeat({self.principal.defeat_rule})',
    RuleType.Negate: lambda self: f'not ({self.sub_rules[0]})',
    RuleType.LocationCheck: lambda self: f'{self.principal} in [{", ".join(self.locations)}]',
    RuleType.SmallKeyDoor: lambda self: f'doorOpen {self.principal[0]}:{self.principal[1]}'
}


def or_rule(rule1, rule2):
    return lambda state: rule1(state) or rule2(state)


def and_rule(rule1, rule2):
    return lambda state: rule1(state) and rule2(state)


class RuleFactory(object):

    @staticmethod
    def static_rule(boolean):
        rule = Rule(RuleType.Static)
        rule.principal = boolean
        rule.rule_lambda = lambda state: boolean
        return rule

    @staticmethod
    def conj(rules):
        if len(rules) == 1:
            return rules[0]
        rule = Rule(RuleType.Conjunction)
        rule_lambda = None
        for r in rules:
            if r is None:
                continue
            if r.rule_type == RuleType.Conjunction:
                rule.sub_rules.extend(r.sub_rules)  # todo: this extension for the lambda calc
            elif r.rule_type == RuleType.Static and r.principal:  # remove static flag if unnecessary
                continue
            elif r.rule_type == RuleType.Static and not r.principal:  # always evaluates to false
                return r
            else:
                rule.sub_rules.append(r)
            if not rule_lambda:
                rule_lambda = r.rule_lambda
            else:
                rule_lambda = and_rule(rule_lambda, r.rule_lambda)
        rule.rule_lambda = rule_lambda if rule_lambda else lambda state: True
        return rule

    @staticmethod
    def disj(rules):
        if len(rules) == 1:
            return rules[0]
        rule = Rule(RuleType.Disjunction)
        rule_lambda = None
        for r in rules:
            if r is None:
                continue
            if r.rule_type == RuleType.Disjunction:
                rule.sub_rules.extend(r.sub_rules)   # todo: this extension for the lambda calc
            elif r.rule_type == RuleType.Static and not r.principal:  # remove static flag if unnecessary
                continue
            elif r.rule_type == RuleType.Static and r.principal:  # always evaluates to true
                return r
            else:
                rule.sub_rules.append(r)
            if not rule_lambda:
                rule_lambda = r.rule_lambda
            else:
                rule_lambda = or_rule(rule_lambda, r.rule_lambda)
        rule.rule_lambda = rule_lambda if rule_lambda else lambda state: True
        return rule

    @staticmethod
    def item(item, player, count=1):
        rule = Rule(RuleType.Item)
        rule.principal = item
        rule.player = player
        rule.count = count
        rule.rule_lambda = lambda state: state.has(item, player, count)
        return rule

    @staticmethod
    def bottle(player):
        rule = Rule(RuleType.Bottle)
        rule.player = player
        rule.rule_lambda = lambda state: state.has_bottle(player)
        return rule

    @staticmethod
    def crystals(number, player):
        rule = Rule(RuleType.Crystal)
        rule.principal = number
        rule.player = player
        rule.rule_lambda = lambda state: state.has_crystals(number, player)
        return rule

    @staticmethod
    def barrier(region, player, barrier):
        rule = Rule(RuleType.Barrier)
        rule.principal = region
        rule.player = player
        rule.barrier = barrier
        rule.rule_lambda = lambda state: state.can_cross_barrier(region, player, barrier)
        return rule

    @staticmethod
    def hearts(number, player):
        rule = Rule(RuleType.Hearts)
        rule.principal = number
        rule.player = player
        rule.rule_lambda = lambda state: state.has_hearts(number, player)
        return rule

    @staticmethod
    def unlimited(item, player, shop_regions):
        rule = Rule(RuleType.Unlimited)
        rule.principal = item
        rule.player = player
        rule.locations = shop_regions  # list of regions where said item can be bought
        rule.rule_lambda = lambda state: state.can_buy_unlimited(item, player)
        return rule

    @staticmethod
    def extend_magic(player, magic, difficulty, magic_potion_regions, flag):
        rule = Rule(RuleType.ExtendMagic)
        rule.principal = magic
        rule.player = player
        rule.resolution_hint = difficulty  # world difficulty setting
        rule.locations = magic_potion_regions  # list of regions where blue/green can be bought
        rule.flag = flag
        rule.rule_lambda = lambda state: state.can_extend_magic(player, magic, flag)
        return rule

    @staticmethod
    def boss(boss):
        rule = Rule(RuleType.Boss)
        rule.principal = boss
        rule.rule_lambda = lambda state: boss.defeat_rule.eval(state)
        return rule

    @staticmethod
    def neg(orig):
        rule = Rule(RuleType.Negate)
        rule.sub_rules.append(orig)
        rule.rule_lambda = lambda state: not orig.rule_lambda(state)
        return rule

    @staticmethod
    def check_location(item, location, player):
        rule = Rule(RuleType.LocationCheck)
        rule.principal = item
        rule.location = location
        rule.player = player
        rule.rule_lambda = eval_location(item, location, player)
        return rule

    @staticmethod
    def small_key_door(door_name, dungeon, player, door_rules):
        rule = Rule(RuleType.SmallKeyDoor)
        rule.principal = (door_name, dungeon)
        rule.player = player
        rule.resolution_hint = door_rules  # door_rule object from KeyDoorShuffle
        rule.rule_lambda = eval_small_key_door(door_name, dungeon, player)
        return rule


def eval_location(item, location, player):
    return lambda state: eval_location_main(item, location, player, state)


def eval_location_main(item, location, player, state):
    location = state.world.get_location(location, player)
    return location.item and location.item.name == item and location.player == player


def eval_small_key_door_main(state, door_name, dungeon, player):
    if state.is_door_open(door_name, player):
        return True
    key_logic = state.world.key_logic[player][dungeon]
    door_rule = key_logic.door_rules[door_name]
    door_openable = False
    for ruleType, number in door_rule.new_rules.items():
        if door_openable:
            return True
        if ruleType == KeyRuleType.WorstCase:
            door_openable |= state.has_sm_key(key_logic.small_key_name, player, number)
        elif ruleType == KeyRuleType.AllowSmall:
            if (door_rule.small_location.item and door_rule.small_location.item.name == key_logic.small_key_name
                 and door_rule.small_location.item.player == player):
                return True  # always okay if allow small is on
        elif isinstance(ruleType, tuple):
            lock, lock_item = ruleType
            # this doesn't track logical locks yet, i.e. hammer locks the item and hammer is there, but the item isn't
            for loc in door_rule.alternate_big_key_loc:
                spot = state.world.get_location(loc, player)
                if spot.item and spot.item.name == lock_item:
                    door_openable |= state.has_sm_key(key_logic.small_key_name, player, number)
                    break
    return door_openable


def eval_small_key_door(door_name, dungeon, player):
    return lambda state: eval_small_key_door_main(state, door_name, dungeon, player)


def conjunction_requirements(rule, f):
    combined = [ReqSet()]
    for r in rule.sub_rules:
        result = r.get_requirements(f)
        combined = merge_requirements(combined, result)
    return combined


def disjunction_requirements(rule, f):
    results = []
    for r in rule.sub_rules:
        result = r.get_requirements(f)
        results.extend(result)
    return results


rule_requirements = {
    RuleType.Conjunction: conjunction_requirements,
    RuleType.Disjunction: disjunction_requirements,
    RuleType.Item: lambda rule, f: [ReqSet([Requirement(ReqType.Item, rule.principal, rule.player, rule, rule.count)])],
    RuleType.Reachability: lambda rule, f: [ReqSet([Requirement(ReqType.Reachable, rule.principal, rule.player, rule)])],
    RuleType.Static: lambda rule, f: static_req(rule),
    RuleType.Crystal: lambda rule, f: crystal_requirements(rule),
    RuleType.Bottle: lambda rule, f: [ReqSet([Requirement(ReqType.Item, 'Bottle', rule.player, rule, 1)])],
    RuleType.Barrier: lambda rule, f: barrier_req(rule),
    RuleType.Hearts: lambda rule, f: empty_req(),  # todo: the one heart container
    RuleType.Unlimited: lambda rule, f: unlimited_buys(rule),
    RuleType.ExtendMagic: lambda rule, f: magic_requirements(rule),
    RuleType.Boss: lambda rule, f: rule.principal.defeat_rule.get_requirements(f),
    RuleType.Negate: lambda rule, f: empty_req(),  # ignore these and just don't flood the key too early
    RuleType.LocationCheck: lambda rule, f: location_check(rule),
    RuleType.SmallKeyDoor: lambda rule, f: small_key_reqs(rule)
}


avail_crystals = ['Crystal 1', 'Crystal 2', 'Crystal 3', 'Crystal 4', 'Crystal 5', 'Crystal 6', 'Crystal 7']


def crystal_requirements(rule):
    crystal_rules = map(lambda c: Requirement(ReqType.Item, c, rule.player, rule), avail_crystals)
    combinations = itertools.combinations(crystal_rules, rule.principal)
    counter_list = []
    for combo in combinations:
        counter_list.append(ReqSet(combo))
    return counter_list


# todo: 1/4 magic
def magic_requirements(rule):
    if rule.principal <= 8:
        return [set()]
    bottle_val = 1.0
    if rule.resolution_hint == 'expert' and not rule.flag:
        bottle_val = 0.25
    elif rule.resolution_hint == 'hard' and not rule.flag:
        bottle_val = 0.5
    base, min_bot, reqs = 8, None, []
    for i in range(1, 5):
        if base + bottle_val*base*i >= rule.principal:
            min_bot = i
            break
    if min_bot:
        for region in rule.locations:
            reqs.append(ReqSet([Requirement(ReqType.Item, 'Bottle', rule.player, rule, min_bot),
                                Requirement(ReqType.Reachable, region, rule.player, rule)]))
    if rule.principal <= 16:
        reqs.append(ReqSet([Requirement(ReqType.Item, 'Magic Upgrade (1/2)', rule.player, rule, 1)]))
        return reqs
    else:
        base, min_bot = 16, 4
        for i in range(1, 5):
            if base + bottle_val*base*i >= rule.principal:
                min_bot = i
                break
        if min_bot:
            for region in rule.locations:
                reqs.append(ReqSet([Requirement(ReqType.Item, 'Magic Upgrade (1/2)', rule.player, rule, 1),
                                    Requirement(ReqType.Item, 'Bottle', rule.player, rule, min_bot),
                                    Requirement(ReqType.Reachable, region, rule.player, rule)]))
        return reqs


def static_req(rule):
    return [ReqSet()] if rule.principal else [ReqSet([Requirement(ReqType.Item, 'Impossible', rule.player, rule)])]


def barrier_req(rule):
    return [ReqSet([Requirement(ReqType.Reachable, rule.principal, rule.player, rule, crystal=rule.barrier)])]


def empty_req():
    return [ReqSet()]


def location_check(rule):
    return [ReqSet([Requirement(ReqType.Placement, rule.principal, rule.player, rule, locations=rule.locations)])]


def unlimited_buys(rule):
    requirements = []
    for region in rule.locations:
        requirements.append(ReqSet([Requirement(ReqType.Reachable, region, rule.player, rule)]))
    return requirements


def small_key_reqs(rule):
    requirements = []
    door_name, dungeon = rule.principal
    key_name = dungeon_keys[dungeon]
    for rule_type, number in rule.resolution_hint.new_rules.items():
        if rule_type == KeyRuleType.WorstCase:
            requirements.append(ReqSet([Requirement(ReqType.Item, key_name, rule.player, rule, number)]))
        elif rule_type == KeyRuleType.AllowSmall:
            small_loc = rule.resolution_hint.small_location.name
            requirements.append(ReqSet([
                Requirement(ReqType.Placement, key_name, rule.player, rule, locations=[small_loc]),
                Requirement(ReqType.Item, key_name, rule.player, rule, number)]))
        elif isinstance(rule_type, tuple):
            lock, lock_item = rule_type
            locs = [x.name for x in rule.resolution_hint.alternate_big_key_loc]
            requirements.append(ReqSet([
                Requirement(ReqType.Placement, lock_item, rule.player, rule, locations=locs),
                Requirement(ReqType.Item, key_name, rule.player, rule, number)]))
    return requirements


class ReqType(FastEnum):
    Item = 0
    Placement = 2


class ReqSet(object):

    def __init__(self, requirements=None):
        if requirements is None:
            requirements = []
        self.keyed = OrderedDict()
        for r in requirements:
            self.keyed[r.simple_key()] = r

    def append(self, req):
        self.keyed[req.simple_key()] = req

    def get_values(self):
        return self.keyed.values()

    def merge(self, other):
        new_set = ReqSet(self.get_values())
        for r in other.get_values():
            key = r.simple_key()
            if key in new_set.keyed:
                new_set.keyed[key] = max(r, new_set.keyed[key], key=lambda r: r.amount)
            else:
                new_set.keyed[key] = r
        return new_set

    def redundant(self, other):
        for k, req in other.keyed.items():
            if k not in self.keyed:
                return False
            elif self.keyed[k].amount < req.amount:
                return False
        return True

    def different(self, other):
        for key in self.keyed.keys():
            if key not in other.keyed:
                return True
            if key in other.keyed and self.keyed[key].amount > other.keyed[key].amount:
                return True
        return False

    def find_item(self, item_name):
        for key, req in self.keyed.items():
            if req.req_type == ReqType.Item and req.item == item_name:
                return req
        return None

    def __eq__(self, other):
        for key, req in self.keyed.items():
            if key not in other.keyed:
                return False
            if req.amount != other.keyed[key].amount:
                return False
        for key in other.keyed:
            if key not in self.keyed:
                return False
        return True

    def __str__(self):
        return str(self.__unicode__())

    def __unicode__(self):
        return " and ".join([str(x) for x in self.keyed.values()])


class Requirement(object):

    def __init__(self, req_type, item, player, rule, amount=1, crystal=CrystalBarrier.Null, locations=()):
        self.req_type = req_type
        self.item = item
        self.player = player
        self.rule = rule
        self.amount = amount
        self.crystal = crystal
        self.locations = tuple(locations)

    def simple_key(self):
        return self.req_type, self.item, self.player, self.crystal, self.locations

    def key(self):
        return self.req_type, self.item, self.player, self.amount, self.crystal, self.locations

    def __eq__(self, other):
        if isinstance(other, Requirement):
            return self.key() == other.key()
        return NotImplemented

    def __hash__(self):
        return hash(self.key())

    def __str__(self):
        return str(self.__unicode__())

    def __unicode__(self):
        if self.req_type == ReqType.Item:
            return f'has {self.item}' if self.amount == 1 else f'has {self.amount} {self.item}(s)'
        elif self.req_type == ReqType.Placement:
            return f'{self.item} located @ {",".join(self.locations)}'


# requirement utility methods
def merge_requirements(starting_requirements, new_requirements):
    merge = []
    for req in starting_requirements:
        for new_r in new_requirements:
            merge.append(req.merge(new_r))
    return reduce_requirements(merge)


only_one = {'Moon Pearl', 'Hammer', 'Blue Boomerang', 'Red Boomerang', 'Hookshot', 'Mushroom', 'Powder',
            'Fire Rod', 'Ice Rod', 'Bombos', 'Ether', 'Quake', 'Lamp', 'Shovel', 'Ocarina', 'Bug Catching Net',
            'Book of Mudora', 'Magic Mirror', 'Cape', 'Cane of Somaria', 'Cane of Byrna', 'Flippers', 'Pegasus Boots'}


def standardize_requirements(requirements, progressive_flag):
    assert isinstance(requirements, list)
    for req in requirements:
        for thing in req.get_values():
            if thing.item in only_one and thing.amount > 1:
                thing.amount = 1
        if progressive_flag:
            substitute_progressive(req)
    return reduce_requirements(requirements)


def reduce_requirements(requirements):
    removals = []
    reduced = list(requirements)
    # subset manip
    ttl = len(reduced)
    for i in range(0, ttl - 1):
        for j in range(i + 1, ttl):
            req, other_req = reduced[i], reduced[j]
            if req.redundant(other_req):
                removals.append(req)
            elif other_req.redundant(req):
                removals.append(other_req)
    for removal in removals:
        if removal in reduced:
            reduced.remove(removal)
    assert len(reduced) != 0
    return reduced


progress_sub = {
    'Fighter Sword': ('Progressive Sword', 1),
    'Master Sword': ('Progressive Sword', 2),
    'Tempered Sword': ('Progressive Sword', 3),
    'Golden Sword': ('Progressive Sword', 4),
    'Power Glove': ('Progressive Glove', 1),
    'Titans Mitts': ('Progressive Glove', 2),
    'Bow': ('Progressive Bow', 1),
    'Silver Arrows': ('Progressive Bow', 2),
    'Blue Mail': ('Progressive Armor', 1),
    'Red Mail': ('Progressive Armor', 2),
    'Blue Shield': ('Progressive Shield', 1),
    'Red Shield': ('Progressive Shield', 2),
    'Mirror Shield': ('Progressive Shield', 3),
}


def substitute_progressive(req):
    for item in req.get_values():
        if item.item in progress_sub.keys():
            item.item, item.amount = progress_sub[item.item]
