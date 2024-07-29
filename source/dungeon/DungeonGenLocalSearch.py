import RaceRandom as random
import logging
import os
from collections import defaultdict, deque


from BaseClasses import Direction, RegionType, CrystalBarrier, DoorType, Door, Hook, Entrance
from Utils import clear_file
from source.dungeon.DungeonGenerationCommon import DungeonBuilder, GenerationException, define_sector_features, dungeon_portals
from source.dungeon.DungeonGenerationCommon import GlobalPolarity, find_sector, assign_sector_helper, hanger_from_door, hook_from_door
from source.dungeon.DungeonGen3 import create_sector_descriptors
# from source.dungeon.DungeonGenTransitivity import do_transitivity_check as do_transitivity_check_new
from source.dungeon.DungeonGenTransitivity2 import do_transitivity_check as do_transitivity_check_new

# ------------------------------ #
#         Main Algorithm
# ------------------------------ #


def create_dungeon_builders_prototype(dungeon_pool, sector_pool, portal_pool, world, player):
    generation_log_name = ['data', 'gen', 'gen.log.txt']
    clear_file(generation_log_name)
    logger = logging.getLogger('GenerationLog')
    handler = logging.FileHandler(os.path.join(*generation_log_name))
    logger.addHandler(handler)
    gen_log = logging
    dungeons = main_dungeon_builders(dungeon_pool, sector_pool, portal_pool, gen_log, world, player)
    return dungeons


def main_dungeon_builders(pool, sector_pool, portal_pool, gen_log, world, player):
    dungeon_pool = list(pool)
    flags = DoorFlags().from_world(world, player)
    portal_assignments = defaultdict(list)

    # vanilla assignment
    for key in dungeon_pool:
        portal_list = dungeon_portals[key]
        for portal in portal_list:
            region_name = portal + ' Portal'
            portal_sector = next(p for p in portal_pool if region_name in p.region_set())
            region = world.get_region(region_name, player)
            door = create_portal_door(world, player, next(e.name for e in region.exits if e.name.startswith('Enter ')))
            portal_sector.outstanding_doors.append(door)
            portal_sector.portal = world.get_portal(portal, player)
            portal_sector.portal.door = door  # assign placeholder door
            portal_assignments[key].append(portal_sector)


    define_sector_features(sector_pool)
    create_sector_descriptors(sector_pool + portal_pool, world, player)

    dungeon_map = {}
    if 'Skull Woods' in dungeon_pool and len(portal_assignments['Skull Woods']) > 1:
        dungeon_pool.append('Skull Woods Back')
        dungeon_pool.append('Skull Woods Front')
        dungeon_pool.remove('Skull Woods')
        assignments = portal_assignments['Skull Woods']
        # todo: feels like the back portal should always not be chosen as the destination ones, see todo saying (analyze not based on inaccessible regions)
        # get skull 3 portal assignment if present, else a random 1
        skull3 = find_sector('Skull 3 Portal', assignments)
        if skull3 is not None and not skull3.portal.destination:
            portal_assignments['Skull Woods Back'].append(skull3)
            assignments.remove(skull3)
        else:
            candidates = [x for x in assignments if not x.portal.destination]
            some_portal = random.choice(candidates)
            portal_assignments['Skull Woods Back'].append(some_portal)
            assignments.remove(some_portal)
        # the rest go in front
        for portal in assignments:
            portal_assignments['Skull Woods Front'].append(portal)
    if 'Desert Palace' in dungeon_pool:  # a strict split will prevent this from being a cross-world connector inadvertently
        dungeon_pool.append('Desert Palace Back')
        dungeon_pool.append('Desert Palace Front')
        dungeon_pool.remove('Desert Palace')
        assignments = portal_assignments['Desert Palace']
        # get desert back portal assignment if present, else a random 1
        back_portal = find_sector('Desert Back Portal', assignments)
        if back_portal is not None and not back_portal.portal.destination:
            portal_assignments['Desert Palace Back'].append(back_portal)
            assignments.remove(back_portal)
        else:
            candidates = [x for x in assignments if not x.portal.destination]
            some_portal = random.choice(candidates)
            portal_assignments['Desert Palace Back'].append(some_portal)
            assignments.remove(some_portal)
        # the rest go in front
        for portal in assignments:
            portal_assignments['Desert Palace Front'].append(portal)
    if 'Hyrule Castle' in dungeon_pool and world.mode[player] == 'standard':
        # todo: special edits for throne room, sewer "portal" sector
        dungeon_pool.append('Hyrule Castle Dungeon')
        dungeon_pool.append('Hyrule Castle Sewers')
        dungeon_pool.remove('Hyrule Castle')

    all_sectors = sector_pool + portal_pool
    info = DungeonGenInfo(gen_log, all_sectors, flags)

    for key in dungeon_pool:
        current_dungeon = dungeon_map[key] = DungeonBuilder(key)
        # handle special assignments
        for sector in portal_assignments[key]:
            propose_sector(current_dungeon, sector, info, True)
        # handle special sectors:
        if key == 'Hyrule Castle Dungeon':  # builder doesn't exist except in standard
            for r_name in ['Hyrule Dungeon Cellblock', 'Hyrule Castle Throne Room']:  # need to deliver zelda
                propose_sector(current_dungeon, find_sector(r_name, sector_pool), info, True)
        elif key == 'Hyrule Castle Sewers':  # builder doesn't exist except in standard
            propose_sector(current_dungeon, find_sector('Sanctuary', sector_pool), info, True)
        elif key == 'Thieves Town' and world.get_dungeon("Thieves Town", player).boss.enemizer_name == 'Blind':
            propose_sector(current_dungeon, find_sector("Thieves Blind's Cell", sector_pool), info, True)

    def lock_down_default_sectors(definition):
        for key, builder_list in definition.items():
            sector = find_sector(key, sector_pool)
            if sector:
                candidate_builders = [d for d in dungeon_map if d in builder_list]
                if len(candidate_builders) == 1:
                    chosen_builder = next(iter(candidate_builders))
                else:
                    chosen_builder = random.choice(candidate_builders)
                propose_sector(dungeon_map[chosen_builder], sector, info, True)

    # this handles boss sectors
    lock_down_default_sectors(dungeon_boss_regions)

    # handles drop down lobbies - lock down for now - technically can move to a different
    if not info.flags.warps_pits or not info.flags.lobbies:
        lock_down_default_sectors(default_lobby_drops)

    if not info.flags.lobbies:
        # todo: lock lobbies for intensity 2 or less - can technically assign portals at this point too
        pass
    else:
        # randomly choose which portal will not be portalAble for this seed
        for dungeon, choices_list in portal_choices.items():
            # only needed if crossing, could restore later if they happen to be in the same dungeon
            if dungeon in pool and len(pool) > 1:
                for needed_choice in choices_list:
                    choice = random.choice(needed_choice)
                    world.get_door(choice, player).portalAble = False

    possible_builders = list(dungeon_map.keys())
    weights = [weight_map[builder] for builder in possible_builders]
    choices = random.choices(possible_builders, weights, k=len(info.sector_pool))
    for idx, sector in enumerate(info.sector_pool):
        propose_sector(dungeon_map[choices[idx]], sector, info)
    done = False
    iterations = 0
    while not done:
        if iterations > 1000:
            raise Exception(f'1k iterations seems high, probably should investigate the algorithm')
        balance_map = proposal_balance(info)
        unbalanced = {dungeon: balance for dungeon, balance in balance_map.items() if not balance.balanced()}
        if len(unbalanced) > 0:
            balance_move_sector(unbalanced, balance_map, info)
            iterations += 1
            # swap something
            continue
        done = len(unbalanced) == 0
    info.gen_log.info(f'Performed {iterations} moves to achieve balance')
    # check_dead_ends_branches(info)
    for d_name, sector_list in info.proposal.items():
        info.gen_log.debug(f'{d_name}: {", ".join([str(s) for s in sector_list])}')
        for sector in sector_list:
            assign_sector_helper(sector, dungeon_map[d_name])
    return dungeon_map


def propose_sector(builder, new_sector, info, lock=False):
    info.proposal[builder.name].append(new_sector)
    if lock:
        new_sector.locked = True
        del info.sector_pool[new_sector]
        info.gen_log.debug(f'{new_sector.sector_key()} locked to {builder.name}')
    else:
        info.gen_log.debug(f'{new_sector.sector_key()} assigned to {builder.name}')


def proposal_balance(info):
    balance_map = {}
    for dungeon, sector_list in info.proposal.items():
        dungeon_balance = Balance(dungeon, info)
        dungeon_balance.extend(sector_list)
        balance_map[dungeon] = dungeon_balance
    return balance_map


def is_balanced(balance_info):
    polarity, branching, needy = balance_info
    return polarity.balanced() and branching >= 0 and needy == 0


def balance_move_sector(unbalanced, balance_map, info):
    # crystal first
    crystal_problems = [dungeon for dungeon, balance in balance_map.items() if balance.need_crystal()]
    if crystal_problems:
        target = random.choice(crystal_problems)
        fix_crystal_balance(target, balance_map, info)
        return

    # portal number next
    # todo: certain portals can't be used with other portals
    portal_needs = [dungeon for dungeon, balance in balance_map.items() if not balance.portal_balanced()]
    if portal_needs:
        target = random.choice(portal_needs)
        fix_portal_balance(target, balance_map, info)
        return

    # dead ends next
    branching_needs = [dungeon for dungeon, balance in balance_map.items() if balance.need_branches()]
    if branching_needs:
        target = random.choice(branching_needs)
        fix_branching_balance(target, balance_map, info)
        return

    # parity next
    parity_needs = [dungeon for dungeon, balance in balance_map.items() if balance.need_parity()]
    if len(parity_needs):
        target = random.choice(parity_needs)
        fix_parity_balance(target, balance_map, info)
        return

    # polarity next
    polarity_problems = [dungeon for dungeon, balance in unbalanced.items() if not balance.polarity_balanced()]
    if polarity_problems:
        best_choices = []
        while len(best_choices) == 0:
            if len(polarity_problems) == 0:
                raise GenerationException('A More serious generation error has occured, no valid moves for polarity')
            weights = [unbalanced[d].charge() for d in polarity_problems]
            target = random.choices(polarity_problems, weights, k=1)[0]
            polarity_problems.remove(target)
            unlocked_cnt = {id: sum(1 for sector in info.proposal[id] if not sector.locked) for id in balance_map}
            candidates = {k: v for k, v in unbalanced.items() if not v.polarity_balanced() and k != target}
            candidates = sorted(list(candidates.items()), key=lambda item: (item[1].branches, unlocked_cnt[item[0]]))

            provider, best_choices, best_charge = None, [], None
            while len(best_choices) == 0 and len(candidates) > 0:
                provider, balance_info = candidates.pop()
                best_choices, best_charge = find_a_good_polarity_shift(provider, target, unbalanced, info)
                swap_choices, swap_charge = find_a_good_polarity_shift(target, provider, unbalanced, info)
                if swap_charge is not None and (best_charge is None or swap_charge > best_charge):
                    best_choices = swap_choices
                    provider, target = target, provider
        best = random.choice(best_choices)
        # do the move
        perform_move(info, best, provider, target)
        info.gen_log.debug(f'Moved {best.sector_key()} from {provider} to {target} for polarity balance')
        return

    # transitivity last
    transitivity_problems = [dungeon for dungeon, balance in balance_map.items() if not balance.transitive()]
    if transitivity_problems:
        target = random.choice(transitivity_problems)
        fix_transitivity(target, balance_map, info)
        # return


def find_a_good_polarity_shift(provider, target, unbalanced, info):
    best_choices, best_charge = [], None
    for sector in info.proposal[provider]:
        if not valid_for_move(sector, info) or is_sector_neutral(sector):
            continue
        target_charge = unbalanced[target].charge()
        target_balance = Balance(target, info)
        target_balance.extend([x for x in info.proposal[target]])
        target_balance.append(sector)
        target_change = target_charge - target_balance.charge()
        # if not target_balance.need_parity():
        curr_charge = unbalanced[provider].charge()
        provider_balance = Balance(provider, info)
        provider_balance.extend([x for x in info.proposal[provider] if x != sector])
        provider_change = curr_charge - provider_balance.charge()
        charge_diff = provider_change + target_change
        if len(best_choices) == 0 or charge_diff > best_charge:
            best_choices.clear()
            best_choices.append(sector)
            best_charge = charge_diff
        elif charge_diff == best_charge:
            best_choices.append(sector)
    return best_choices, best_charge


def fix_crystal_balance(target, balance_map, info):
    # find a crystal provider
    unlocked_cnt = {id: sum(1 for sector in info.proposal[id] if not sector.locked) for id in balance_map}
    candidates = sorted(list(balance_map.items()), key=lambda item: (item[1].crystal_provided, unlocked_cnt[item[0]]))
    provider, best, best_charge = None, None, None
    while best is None and len(candidates) > 0:
        provider, balance_info = candidates.pop()
        if balance_info.crystal_provided == 0 or (balance_info.crystal_provided == 1 and balance_info.crystal_needed > 0):
            continue
        for sector in info.proposal[provider]:
            if not valid_for_move(sector, info) or not sector.c_switch:
                continue
            bal = Balance(provider, info)
            bal.extend([x for x in info.proposal[provider] if x != sector])
            charge = bal.charge()
            if best is None or charge < best_charge:
                best = sector
                best_charge = charge
    if best is not None:
        # do the move
        info.proposal[provider].remove(best)
        info.proposal[target].append(best)
        info.gen_log.debug(f'Moved {best.sector_key()} from {provider} to {target} for crystal balance')
        return
    # if none, then need to move the crystal needed elsewhere
    candidate_sector = next(sector for sector in info.proposal[target] if not sector.locked and sector.blue_barrier)
    possible_benefactors = [dungeon for dungeon, balance in balance_map.items() if balance.crystal_provided > 0]
    for benefactor in possible_benefactors:
        bal = Balance(benefactor, info)
        bal.extend([x for x in info.proposal[benefactor]])
        bal.append(candidate_sector)
        charge = bal.charge()
        if best is None or charge < best_charge:
            best = benefactor
            best_charge = charge
    perform_move(info, candidate_sector, target, best)
    info.gen_log.debug(f'Moved {candidate_sector.sector_key()} from {target} to {best} because no crystal switches available')


def fix_portal_balance(target, balance_map, info):
    unlocked_cnt = {id: sum(1 for sector in info.proposal[id] if not sector.locked) for id in balance_map}
    candidates = sorted(list(balance_map.items()), key=lambda item: (item[1].portal_options, unlocked_cnt[item[0]]))
    # best criteria for issue caused
    if balance_map[target].non_dead_end_portals == 0:
        def criteria(sector):
            return any(d.portalAble and not d.deadEnd for d in sector.outstanding_doors)
    elif balance_map[target].passable_portals < balance_map[target].destination_portals:
        def criteria(sector):
            return any(d.portalAble and d.passage for d in sector.outstanding_doors)
    else:
        def criteria(sector):
            return any(d.portalAble for d in sector.outstanding_doors)
    provider, best, best_charge = None, None, None
    while best is None:
        provider, balance_info = candidates.pop()
        for sector in info.proposal[provider]:
            if not valid_for_move(sector, info) or not criteria(sector):
                continue
            bal = Balance(provider, info)
            bal.extend([x for x in info.proposal[provider] if x != sector])
            charge = bal.charge()
            if best is None or charge < best_charge:
                best = sector
                best_charge = charge
    perform_move(info, best, provider, target)
    best.locked = True
    info.gen_log.debug(f'Moved and locked {best.sector_key()} from {provider} to {target} for portal balance')


def fix_branching_balance(target, balance_map, info):
    unlocked_cnt = {id: sum(1 for sector in info.proposal[id] if valid_for_move(sector, info)) for id in balance_map}
    candidates = sorted(list(balance_map.items()), key=lambda item: (item[1].branches, unlocked_cnt[item[0]]))
    provider, best = find_min_charge_sector(candidates, info)
    perform_move(info, best, provider, target)
    info.gen_log.debug(f'Moved {best.sector_key()} from {provider} to {target} for branching balance')


def fix_parity_balance(target, balance_map, info):
    unlocked_cnt = {id: sum(1 for sector in info.proposal[id] if not sector.locked) for id in balance_map}
    candidates = {k: v for k, v in balance_map.items() if v.need_parity() and k != target}
    candidates = sorted(list(candidates.items()), key=lambda item: (item[1].branches, unlocked_cnt[item[0]]))
    provider, best, best_charge = None, None, None
    while best is None:
        if len(candidates) == 0:
            parity_needs = [dungeon for dungeon, balance in balance_map.items() if balance.need_parity() and dungeon != target]
            target = random.choice(parity_needs)
            candidates = {k: v for k, v in balance_map.items() if v.need_parity() and k != target}
            candidates = sorted(list(candidates.items()), key=lambda item: (item[1].branches, unlocked_cnt[item[0]]))
        provider, balance_info = candidates.pop()
        for sector in info.proposal[provider]:
            if not valid_for_move(sector, info):
                continue
            bal = Balance(provider, info)
            bal.extend([x for x in info.proposal[provider] if x != sector])
            if not bal.need_parity():
                bal2 = Balance(target, info)
                bal2.extend(info.proposal[target])
                bal2.append(sector)
                if not bal2.need_parity():
                    charge = bal.charge()
                    if best is None or charge < best_charge:
                        best_charge = charge
                        best = sector
    perform_move(info, best, provider, target)
    info.gen_log.debug(f'Moved {best.sector_key()} from {provider} to {target} for parity')


def fix_transitivity(target, balance_map, info):
    unlocked_cnt = {id: sum(1 for sector in info.proposal[id] if not sector.locked) for id in balance_map}
    candidates = sorted(list(balance_map.items()), key=lambda item: unlocked_cnt[item[0]])

    provider, best, best_charge = None, None, None
    while best is None:
        provider, balance_info = candidates.pop()
        if provider == target:
            continue
        for sector in info.proposal[provider]:
            if not valid_for_move(sector, info):
                continue
            target_balance = Balance(target, info)
            target_balance.extend([x for x in info.proposal[target]])
            target_balance.append(sector)
            if not target_balance.transitive():
                continue
            bal = Balance(provider, info)
            bal.extend([x for x in info.proposal[provider] if x != sector])
            charge = bal.charge()
            if best is None or charge < best_charge:
                best = sector
                best_charge = charge

    perform_move(info, best, provider, target)
    info.gen_log.debug(f'Moved {best.sector_key()} from {provider} to {target} for transitivity')


# losing the sector that will cause the least amt of harm
def find_min_charge_sector(candidates, info):
    provider, best_choices, best_charge = None, [], None
    while len(best_choices) == 0:
        provider, balance_info = candidates.pop()
        for sector in info.proposal[provider]:
            if not valid_for_move(sector, info):
                continue
            bal = Balance(provider, info)
            bal.extend([x for x in info.proposal[provider] if x != sector])
            charge = bal.charge()
            if len(best_choices) == 0 or charge < best_charge:
                best_choices.clear()
                best_choices.append(sector)
                best_charge = charge
            elif charge == best_charge:
                best_choices.append(sector)
    best = random.choice(best_choices)
    return provider, best


def valid_for_move(sector, info):
    return not sector.locked and sector not in info.recent_moves


def perform_move(info, sector, provider, target):
    info.proposal[provider].remove(sector)
    info.proposal[target].append(sector)
    info.recent_moves.append(sector)


# ------------------------------ #
#         Initialization
# ------------------------------ #


def create_portal_door(world, player, entName):
    entrance = world.get_entrance(entName, player)
    d = Door(player, entName, DoorType.Normal, entrance)
    d.direction = Direction.North
    d.traversal_only = True
    world.doors.append(d)
    return d


def create_bridge_door(world, player, bridge_name, region_name, target_region):
    region = world.get_region(region_name, player)
    ent = Entrance(player, bridge_name, region)
    region.exits.append(ent)
    # d = Door(player, bridge_name, DoorType.Logical, ent)
    ent.connect(world.get_region(target_region, player))
    return ent


# ------------------------------ #
#         Utility
# ------------------------------ #

class DungeonGenInfo:

    def __init__(self, gen_log, all_sectors, flags):
        self.proposal = defaultdict(list)
        self.gen_log = gen_log
        self.global_pole = GlobalPolarity(all_sectors)
        self.sector_pool = dict.fromkeys(all_sectors)
        self.flags = flags
        self.transitive_db = {}
        self.recent_moves = deque(maxlen=2)


class DoorFlags:
    def __init__(self):
        self.normal = False
        self.spiral = False
        self.straight = False
        self.ladder = False
        self.edges = False
        self.lobbies = False
        self.vanilla_traps = False
        self.stair_loops = False
        self.decoupled = False
        self.warps_pits = False  # NotYetImplemented
        self.cave_interiors = False  # NotYetImplemented
        self.intratile = False   # NotYetImplemented

    def from_world(self, world, player):
        self.vanilla_traps = world.trap_door_mode[player] == 'vanilla'
        self.stair_loops = world.door_self_loops[player]
        self.decoupled = world.decoupledoors[player]
        if world.intensity[player] >= 1:
            self.normal = True
            self.spiral = True
        if world.intensity[player] >= 2:
            self.straight = True
            self.ladder = True
            self.edges = True
        if world.intensity[player] >= 3:
            self.lobbies = True
        return self


def score_door(item):
    door, sector = item
    longest = max(len(l) for d, l in sector.descriptor.reachability.items())
    score = len(sector.descriptor.reachability[door])
    if score == longest:
        score += 100
    return score


class Balance:
    def __init__(self, name, info, sector=None):
        self.name = name
        self.north = 0
        self.south = 0
        self.east = 0
        self.west = 0
        self.ttl_stairs = 0
        self.dead_stairs = 0
        self.one_ways = 0
        self.landings = 0

        self.dead_ends = 0
        self.branches = 0

        self.crystal_provided = 0
        self.crystal_needed = 0

        self.portal_needed = 0  # total needed
        self.destination_portals = 0  # not deadEnd or passage

        self.non_dead_end_portals = 0  # always at least one
        self.passable_portals = 0  # equal to destination portals + 1 (primary portal)
        self.portal_options = 0  # total available

        self.sectors = []
        self.transitive_flag = False
        self.transitive_init = False

        self.info = info
        self.flags = info.flags
        if sector is not None:
            self.append(sector)

    def append(self, sector):
        self.transitive_init = False
        self.sectors.append(sector)
        if sector.portal:
            self.portal_needed += 1
            if sector.portal.destination:
                self.destination_portals += 1

        if sector.portal and not sector.portal.destination:
            self.branches += 1  # non-destination portals represent a new branch
        else:
            best_access = max(len(access) for d, access in sector.descriptor.reachability.items())
            missing_doors = len(sector.outstanding_doors) - best_access
            branches = best_access - 2 - missing_doors  # negative number represents dead ends
            if branches > 0:
                self.branches += branches
            elif branches < 0:
                self.dead_ends -= branches

        if sector.blue_barrier and not sector.c_switch:
            self.crystal_needed += 1
        if sector.c_switch:
            self.crystal_provided += 1

        marked = []  # only one counted per super
        for d in sector.outstanding_doors:
            if d.portalAble and d.roomIndex not in marked:
                self.portal_options += 1
                marked.append(d.roomIndex)
                if d.passage:
                    self.passable_portals += 1
                if not d.deadEnd:
                    self.non_dead_end_portals += 1

            if d.direction == Direction.North:
                self.north += 1
            elif d.direction == Direction.South:
                self.south += 1
            elif d.direction == Direction.East:
                self.east += 1
            elif d.direction == Direction.West:
                self.west += 1
            elif d.direction in [Direction.Up, Direction.Down]:
                self.ttl_stairs += 1
                if len(sector.outstanding_doors) == 1:
                    self.dead_stairs += 1
            elif d.type in [DoorType.Warp, DoorType.Hole]:
                self.one_ways += 1
            # todo: landing types

    def extend(self, sector_list):
        for s in sector_list:
            self.append(s)

    def balanced(self):
        if not self.polarity_balanced():
            return False
        if self.branches < self.dead_ends:
            return False
        if self.crystal_needed > 0 and self.crystal_provided == 0:
            return False
        if not self.portal_balanced():
            return False
        if not self.transitive():
            return False
        return True

    def pol_sum(self):
        return (self.north - self.south, self.east - self.west, 0 if self.stair_balanced() else 1)

    def polarity_balanced(self):
        if self.north != self.south:
            return False
        if self.east != self.west:
            return False
        if self.landings < self.one_ways:
            return False
        if not self.stair_balanced():
            return False
        return True

    def need_crystal(self):
        return self.crystal_needed > 0 and self.crystal_provided == 0

    def need_branches(self):
        return self.branches < self.dead_ends

    def need_parity(self):
        return sum(x for x in self.pol_sum()) % 2 == 1

    def stair_balanced(self):
        if self.flags.stair_loops:
            if self.flags.decoupled:
                return self.ttl_stairs > self.dead_stairs
            else:
                return self.ttl_stairs - self.dead_stairs >= self.dead_stairs
        else:
            return self.ttl_stairs % 2 == 0

    def portal_balanced(self):
        if self.non_dead_end_portals == 0:
            return False
        if self.passable_portals <= self.destination_portals:  # we need 1 + destination passable portals
            return False
        return self.portal_needed <= self.portal_options

    def transitive(self):
        if self.transitive_init:
            return self.transitive_flag
        neutral_sectors = [s for s in self.sectors if is_sector_neutral(s)]
        non_neutral_sectors = [s for s in self.sectors if s not in neutral_sectors]
        db_key = frozenset([str(s) for s in non_neutral_sectors])
        if db_key in self.info.transitive_db:
            self.transitive_flag = self.info.transitive_db[db_key]
            self.transitive_init = True
            return self.transitive_flag
        # new transitivity calc
        transitivity = do_transitivity_check_new(self.sectors)
        self.info.transitive_db[db_key] = transitivity
        self.transitive_flag = transitivity
        self.transitive_init = True
        return transitivity

    def charge(self):
        charge = abs(self.north - self.south)
        charge += abs(self.east - self.west)
        charge += max(self.one_ways - self.landings, 0)
        charge += 0 if self.stair_balanced() else 1
        charge += 0 if self.crystal_needed == 0 or self.crystal_provided > 0 else self.crystal_needed
        charge += 0 if self.branches >= self.dead_ends else self.dead_ends
        charge += 0 if self.portal_balanced() else 1
        charge += 0 if not self.need_parity() else 1  # penalty for disturbing parity
        # only run the transitivity check here if everything else is already good
        # otherwise it's likely not going to work
        charge += 0 if charge == 0 and self.transitive() else 1
        return charge


def do_transitivity_check(sectors, starting_point_list):
    door_sector_map = {d: s for s in sectors for d in s.outstanding_doors}
    trans_calc = Transitivity()
    for s in sectors:
        if s.portal and not s.portal.destination:
            trans_calc.append_sector_free(s)
        # todo: some drop downs are free - need to figure out reachability from drop down

    door_info_map = {}
    for s in sectors:
        for d in s.outstanding_doors:
            info = DoorInfo(d, s)
            door_info_map[d] = info
            if len(s.outstanding_doors) == 1:
                info.needs_hook = True
            else:
                access = sum(1 for source, reach_list in s.descriptor.reachability.items() for reach in reach_list if d == reach[0])
                if access == 1:
                    info.needs_hook = True

    visited = {trans_calc.id()}
    starting_points = {d: door_sector_map[d] for d in starting_point_list}
    start_priority = sorted(starting_points.items(), key=score_door)
    init_queue = []
    for starting_point, sector in start_priority:
        t_state = trans_calc.copy()
        t_state.append_door(starting_point, sector)
        id = t_state.id()
        if id not in visited:
            init_queue.append(t_state)
            visited.add(t_state.id())

    neutral_sectors = [s for s in sectors if is_sector_neutral(s)]
    sectors = [s for s in sectors if s not in neutral_sectors]
    queue = deque(init_queue)
    iterations = 0
    while len(queue) > 0:
        iterations += 1
        if iterations > 10000:
            raise GenerationException('Slow transitivity check. 10k or more: time to investigate')
        curr_t_state = queue.pop()
        potential_doors = {d: s for s in sectors for d in s.outstanding_doors if d not in curr_t_state.explored_doors}
        if len(potential_doors) == 0:
            return all(all(any(hanger_from_door(d) == hook_from_door(ex) for ex in curr_t_state.explored_doors) for d in s.outstanding_doors) for s in neutral_sectors)
        availability = figure_out_forced_doors(sectors, curr_t_state, door_info_map)
        if any(v < 0 for hook, v in availability.items()):
            continue  # this path is not viable
        # elminate doors that can't hook
        potential_doors = {d: s for d, s in potential_doors.items() if curr_t_state.can_hook(d)}
        # eliminate doors that would break must-enter doors
        potential_doors = {d: s for d, s in potential_doors.items() if door_info_map[d].needs_hook or availability[hanger_from_door(d)] > 0}
        priority_doors = sorted(potential_doors.items(), key=score_door)
        for door, sector in priority_doors:
            t_state = curr_t_state.copy()
            t_state.append_door(door, sector)
            id = t_state.id()
            if id not in visited:
                queue.append(t_state)
                visited.add(id)
    return False


def figure_out_forced_doors(sectors, curr_t_state, door_info_map):
    available = defaultdict(int)
    for k, v in curr_t_state.current_hooks.items():
        if v > 0:
            available[k] = v
    for s in sectors:
        for d in s.outstanding_doors:
            if d not in curr_t_state.explored_doors:
                if door_info_map[d].needs_hook:  # these eat hooks
                    available[hanger_from_door(d)] -= 1
                else:
                    available[hook_from_door(d)] += 1
    return available


def is_sector_neutral(sector):
    if len(sector.outstanding_doors) == 2:
        d1, d2 = sector.outstanding_doors[0], sector.outstanding_doors[1]
        if hanger_from_door(d1) == hook_from_door(d2):
            reachability = sector.descriptor.reachability
            if len(reachability[d1]) == 2 and len(reachability[d2]) == 2:
                return (all(access[1] == CrystalBarrier.Null for access in reachability[d1]) and
                       all(access[1] == CrystalBarrier.Null for access in reachability[d2]))
    return False


class Transitivity:

    def __init__(self):
        self.explored_doors = set()
        self.current_hooks = defaultdict(int)  # hook -> number
        self.door_path = []

    def copy(self):
        copy = Transitivity()
        copy.explored_doors.update(self.explored_doors)
        copy.current_hooks.update(self.current_hooks)
        copy.door_path.extend(self.door_path)
        return copy

    def id(self):
        return tuple([frozenset(self.explored_doors), tuple(sorted(self.current_hooks.items()))])

    def append_sector_free(self, sector):
        for d in sector.outstanding_doors:
            self.explored_doors.add(d)
            self.door_path.append(d)
            self.current_hooks[Hook.NormalPortal] += 1

    def append_door(self, door, sector):
        self.door_path.append(door)
        if door.portalAble and self.current_hooks[Hook.NormalPortal] > 0:
            hook_to_use = Hook.NormalPortal
        else:
            hook_to_use = hanger_from_door(door)
        self.current_hooks[hook_to_use] -= 1
        self.explored_doors.add(door)
        # todo: I think decoupled doors has diff logic here
        new_doors = {d for d, c in sector.descriptor.reachability[door] if d != door and d not in self.explored_doors}
        self.explored_doors.update(new_doors)
        for d in new_doors:
            if d.type != DoorType.Logical:
                self.current_hooks[hook_from_door(d)] += 1

    def can_hook(self, door):
        if door.portalAble and self.current_hooks[Hook.NormalPortal] > 0:
            return True
        return self.current_hooks[hanger_from_door(door)] > 0


class DoorInfo:

    def __init__(self, door, sector):
        self.door = door
        self.sector = sector
        self.needs_hook = False
# ------------------------------ #
#         Data Section
# ------------------------------ #

dungeon_boss_regions = {
    'Eastern Boss': ['Eastern Palace'],
    'Desert Boss': ['Desert Palace', 'Desert Palace Back', 'Desert Palace Front'],
    'Hera Boss': ['Tower of Hera'],
    'Tower Agahnim 1': ['Agahnims Tower'],
    'PoD Boss': ['Palace of Darkness'],
    'Swamp Boss': ['Swamp Palace'],
    'Skull Boss': ['Skull Woods', 'Skull Woods Back', 'Skull Woods Front'],
    'Thieves Boss': ['Thieves Town'],
    'Ice Boss': ['Ice Palace'],
    'Mire Boss': ['Misery Mire'],
    'TR Boss': ['Turtle Rock'],
    'GT Agahnim 2': ['Ganons Tower'],
}


default_dungeon_entrances = {
    'Hyrule Castle': ['Hyrule Castle Lobby', 'Hyrule Castle West Lobby', 'Hyrule Castle East Lobby', 'Sewers Rat Path',
                      'Sanctuary'],
    'Eastern Palace': ['Eastern Lobby'],
    'Desert Palace': ['Desert Back Lobby', 'Desert Main Lobby', 'Desert West Lobby', 'Desert East Lobby'],
    'Tower of Hera': ['Hera Lobby'],
    'Agahnims Tower': ['Tower Lobby'],
    'Palace of Darkness': ['PoD Lobby'],
    'Swamp Palace': ['Swamp Lobby'],
    'Skull Woods': ['Skull 1 Lobby', 'Skull Pinball', 'Skull Left Drop', 'Skull Pot Circle', 'Skull 2 East Lobby',
                    'Skull 2 West Lobby', 'Skull Back Drop', 'Skull 3 Lobby'],
    'Thieves Town': ['Thieves Lobby'],
    'Ice Palace': ['Ice Lobby'],
    'Misery Mire': ['Mire Lobby'],
    'Turtle Rock': ['TR Main Lobby', 'TR Eye Bridge', 'TR Big Chest Entrance', 'TR Lazy Eyes'],
    'Ganons Tower': ['GT Lobby']
}

default_lobby_drops = {
    'Sewers Rat Path': ['Hyrule Castle Sewers', 'Hyrule Castle'],
    'Skull Pinball': ['Skull Woods', 'Skull Woods Back', 'Skull Woods Front'],
    'Skull Left Drop': ['Skull Woods', 'Skull Woods Back', 'Skull Woods Front'],
    'Skull Pot Circle': ['Skull Woods', 'Skull Woods Back', 'Skull Woods Front'],
    'Skull Back Drop': ['Skull Woods', 'Skull Woods Back', 'Skull Woods Front'],
}

portal_choices = {
    'Skull Woods': [['Skull Pot Prison SE', 'Skull 2 East Lobby SW']],
    'Thieves Town': [['Thieves Hallway SE', 'Thieves Pot Alcove Bottom SW']],
    'Turtle Rock': [['TR Lava Dual Pipes SW', 'TR Lava Escape SE'], ['TR Pokey 1 SW', 'TR Tile Room SE']],
    'Ganons Tower': [['GT Bob\'s Room SE', 'GT Big Chest SW']]
}

full_dungeon_weight = 2
half_dungeon_weight = 1

weight_map = {
    'Hyrule Castle': full_dungeon_weight,
    'Eastern Palace': full_dungeon_weight,
    'Desert Palace': full_dungeon_weight,
    'Tower of Hera': full_dungeon_weight,
    'Agahnims Tower': full_dungeon_weight,
    'Palace of Darkness': full_dungeon_weight,
    'Swamp Palace': full_dungeon_weight,
    'Skull Woods': full_dungeon_weight,
    'Thieves Town': full_dungeon_weight,
    'Ice Palace': full_dungeon_weight,
    'Misery Mire': full_dungeon_weight,
    'Turtle Rock': full_dungeon_weight,
    'Ganons Tower': full_dungeon_weight,
    'Desert Palace Back': half_dungeon_weight,
    'Desert Palace Front': half_dungeon_weight,
    'Skull Woods Front': half_dungeon_weight,
    'Skull Woods Back': half_dungeon_weight,
    # todo: standard
}
