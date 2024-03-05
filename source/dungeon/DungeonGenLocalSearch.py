import RaceRandom as random
import logging
import os
from collections import defaultdict


from BaseClasses import Direction, RegionType, CrystalBarrier, DoorType, Door
from Utils import clear_file
from source.dungeon.DungeonGenerationCommon import DungeonBuilder, define_sector_features, dungeon_portals
from source.dungeon.DungeonGenerationCommon import GlobalPolarity, find_sector, assign_sector_helper, hanger_from_door, hook_from_door
from source.dungeon.DungeonGen3 import create_sector_descriptors

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

    # ??? do we want a sector map?
    # sector_map = {}
    # for sector in sector_pool:
    #     for door in sector.outstanding_doors:
    #         sector_map[door.name] = sector

    dungeon_map = {}
    dungeon_proposal = defaultdict(list)
    if 'Skull Woods' in dungeon_pool and len(portal_assignments['Skull Woods']) > 1:
        dungeon_pool.append('Skull Woods Back')
        dungeon_pool.append('Skull Woods Front')
        dungeon_pool.remove('Skull Woods')
        assignments = portal_assignments['Skull Woods']
        # get skull 3 portal assignment if present, else a random 1
        skull3 = find_sector('Skull 3 Portal', assignments)
        if skull3 is not None:
            portal_assignments['Skull Woods Back'].append(skull3)
            assignments.remove(skull3)
        else:
            some_portal = random.choice(assignments)
            portal_assignments['Skull Woods Back'].append(some_portal)
            assignments.remove(some_portal)
        # the rest go in front
        for portal in assignments:
            portal_assignments['Skull Woods Front'].append(portal)
    if 'Desert Palace' in dungeon_pool:  # a strict split will prevent this from being a cross-world connector inadvertantly
        dungeon_pool.append('Desert Palace Back')
        dungeon_pool.append('Desert Palace Front')
        dungeon_pool.remove('Desert Palace')
        assignments = portal_assignments['Desert Palace']
        # get desert back portal assignment if present, else a random 1
        back_portal = find_sector('Desert Back Portal', assignments)
        if back_portal is not None:
            portal_assignments['Desert Palace Back'].append(back_portal)
            assignments.remove(back_portal)
        else:
            some_portal = random.choice(assignments)
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

    possible_builders = list(dungeon_map.keys())

    choices = random.choices(possible_builders, k=len(info.sector_pool))
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
            iterations += 1
            balance_move_sector(unbalanced, balance_map, info)
            # swap something
            continue
        done = len(unbalanced) == 0
    info.gen_log.info(f'Performed {iterations} moves to achieve balance')
    # check_dead_ends_branches(info)
    for d_name, sector_list in info.proposal.items():
        for sector in sector_list:
            assign_sector_helper(sector, dungeon_map[d_name])
    return dungeon_map


def propose_sector(builder, new_sector, info, lock=False):
    info.proposal[builder.name].append(new_sector)
    if lock:
        new_sector.locked = True
        del info.sector_pool[new_sector]
        info.gen_log.info(f'{new_sector.sector_key()} locked to {builder.name}')
    else:
        info.gen_log.info(f'{new_sector.sector_key()} assigned to {builder.name}')


def proposal_balance(info):
    balance_map = {}
    for dungeon, sector_list in info.proposal.items():
        dungeon_balance = Balance(info.flags)
        for sector in sector_list:
            sector.pol = Balance(info.flags, sector)
            dungeon_balance.append(sector)
        balance_map[dungeon] = dungeon_balance
    return balance_map


def is_balanced(balance_info):
    polarity, branching, needy = balance_info
    return polarity.balanced() and branching >= 0 and needy == 0


def balance_move_sector(unbalanced, balance_map, info):
    # crystal first
    target = next((dungeon for dungeon, balance in balance_map.items() if balance.need_crystal()), None)
    if target is not None:
        fix_crystal_balance(target, balance_map, info)
        return

    # portal number next
    # todo: certain portals can't be used with other portals
    target = next((dungeon for dungeon, balance in balance_map.items() if not balance.portal_balanced()), None)
    if target is not None:
        fix_portal_balance(target, balance_map, info)
        return

    # dead ends next
    target = next((dungeon for dungeon, balance in balance_map.items() if balance.need_branches()), None)
    if target is not None:
        fix_branching_balance(target, balance_map, info)
        return

    # transitivity
    target = next((dungeon for dungeon, balance in balance_map.items() if not balance.transitive()), None)
    if target is not None:
        fix_transitivity(target, balance_map, info)
        return

    # polarity last
    most_imbalanced, best = find_most_imbalanced(unbalanced, info)
    target, best_charge = None, None
    for other in unbalanced:
        if other == most_imbalanced:
            continue
        curr_charge = unbalanced[other].charge()
        pol = Balance(info.flags)
        pol.extend(info.proposal[other])
        pol.append(best)
        charge_diff = curr_charge - pol.charge()
        if target is None or charge_diff > best_charge:
            target = other
            best_charge = charge_diff
    # do the move
    info.proposal[most_imbalanced].remove(best)
    info.proposal[target].append(best)
    info.gen_log.info(f'Moved {best.sector_key()} from {most_imbalanced} to {target} for polarity balance')


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
            if sector.locked or not sector.c_switch:
                continue
            bal = Balance(info.flags)
            bal.extend([x for x in info.proposal[provider] if x != sector])
            charge = bal.charge()
            if best is None or charge < best_charge:
                best = sector
                best_charge = charge
    if best is not None:
        # do the move
        info.proposal[provider].remove(best)
        info.proposal[target].append(best)
        info.gen_log.info(f'Moved {best.sector_key()} from {provider} to {target} for crystal balance')
        return
    # if none, then need to move the crystal needed elsewhere
    candidate_sector = next(sector for sector in info.proposal[target] if not sector.locked and sector.blue_barrier)
    possible_benefactors = [dungeon for dungeon, balance in balance_map.items() if balance.crystal_provided > 0]
    for benefactor in possible_benefactors:
        bal = Balance(info.flags)
        bal.extend([x for x in info.proposal[benefactor]])
        bal.append(candidate_sector)
        charge = bal.charge()
        if best is None or charge < best_charge:
            best = benefactor
            best_charge = charge
    info.proposal[target].remove(candidate_sector)
    info.proposal[best].append(candidate_sector)
    info.gen_log.info(f'Moved {candidate_sector.sector_key()} from {target} to {best} because no crystal switches available')


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
            if sector.locked or not criteria(sector):
                continue
            bal = Balance(info.flags)
            bal.extend([x for x in info.proposal[provider] if x != sector])
            charge = bal.charge()
            if best is None or charge < best_charge:
                best = sector
                best_charge = charge
    info.proposal[provider].remove(best)
    info.proposal[target].append(best)
    info.gen_log.info(f'Moved {best.sector_key()} from {provider} to {target} for portal balance')


def fix_branching_balance(target, balance_map, info):
    unlocked_cnt = {id: sum(1 for sector in info.proposal[id] if not sector.locked) for id in balance_map}
    candidates = sorted(list(balance_map.items()), key=lambda item: (item[1].branches, unlocked_cnt[item[0]]))
    provider, best = find_min_charge_sector(candidates, info)
    info.proposal[provider].remove(best)
    info.proposal[target].append(best)
    info.gen_log.info(f'Moved {best.sector_key()} from {provider} to {target} for branching balance')


def fix_transitivity(target, balance_map, info):
    unlocked_cnt = {id: sum(1 for sector in info.proposal[id] if not sector.locked) for id in balance_map}
    candidates = sorted(list(balance_map.items()), key=lambda item: unlocked_cnt[item[0]])

    provider, best, best_charge = None, None, None
    while best is None:
        provider, balance_info = candidates.pop()
        if provider == target:
            continue
        for sector in info.proposal[provider]:
            if sector.locked:
                continue
            target_balance = Balance(info.flags)
            target_balance.extend([x for x in info.proposal[target]])
            target_balance.append(sector)
            if not target_balance.transitive():
                continue
            bal = Balance(info.flags)
            bal.extend([x for x in info.proposal[provider] if x != sector])
            charge = bal.charge()
            if best is None or charge < best_charge:
                best = sector
                best_charge = charge

    info.proposal[provider].remove(best)
    info.proposal[target].append(best)
    info.gen_log.info(f'Moved {best.sector_key()} from {provider} to {target} for transitivity')


def find_most_imbalanced(unbalanced, info):
    unlocked_cnt = {id: sum(1 for sector in info.proposal[id] if not sector.locked) for id in unbalanced}
    candidates = sorted(list(unbalanced.items()), key=lambda item: (item[1].charge(), unlocked_cnt[item[0]]))
    return find_min_charge_sector(candidates, info)


# losing the sector that will cause the least amt of harm
def find_min_charge_sector(candidates, info):
    provider, best_choices, best_charge = None, [], None
    while len(best_choices) == 0:
        provider, balance_info = candidates.pop()
        for sector in info.proposal[provider]:
            if sector.locked:
                continue
            bal = Balance(info.flags)
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


# ------------------------------ #
#         Verification
# ------------------------------ #
# todo: verification?


# ------------------------------ #
#         Initialization
# ------------------------------ #


def create_portal_door(world, player, entName):
    entrance = world.get_entrance(entName, player)
    d = Door(player, entName, DoorType.Normal, entrance)
    d.direction = Direction.North
    world.doors.append(d)
    return d


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
        if world.intensity[player] >=3:
            self.lobbies = True
        return self


class Balance:
    def __init__(self, flags, sector=None):
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
        self.passable_portals = 0  # equal to destination
        self.portal_options = 0  # total available

        self.sectors = []
        self.transitive_flag = False
        self.transitive_init = False

        self.flags = flags
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
            branches = len(sector.outstanding_doors) - 2  # negative number represents dead ends
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
        if self.north != self.south:
            return False
        if self.east != self.west:
            return False
        if self.landings < self.one_ways:
            return False
        if not self.stair_balanced():
            return False
        if self.branches < self.dead_ends:
            return False
        if self.crystal_needed > 0 and self.crystal_provided == 0:
            return False
        if not self.portal_balanced():
            return False
        return True

    def need_crystal(self):
        return self.crystal_needed > 0 and self.crystal_provided == 0

    def need_branches(self):
        return self.branches < self.dead_ends

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
        if self.passable_portals < self.destination_portals:
            return False
        return self.portal_needed <= self.portal_options

    def transitive(self):
        if self.transitive_init:
            return self.transitive_flag
        starting_points = {d: s for s in self.sectors for d in s.outstanding_doors if d.portalAble}
        transitivity = False
        for door, sector in starting_points.items():
            if transitivity:
                break
            explored_sectors = [sector]
            explored_doors = {d for d, c in sector.descriptor.reachability[door]}
            reached_types = {hanger_from_door(d) for d in explored_doors}
            while len(explored_sectors) < len(self.sectors):
                s_list = [s for s in self.sectors if s not in explored_sectors]
                explorable_sectors = {d: s for s in s_list for d in s.outstanding_doors if hook_from_door(d) in reached_types}
                if len(explorable_sectors) == 0:
                    break  # nothing left to explore
                for d, s in explorable_sectors.items():
                    if s not in explored_sectors:
                        explored_sectors.append(s)
                    reached_types.update({hanger_from_door(d) for d, c in s.descriptor.reachability[d]})
            if len(explored_sectors) == len(self.sectors):
                transitivity = True
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
        charge += 0 if self.transitive() else 1
        return charge


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
