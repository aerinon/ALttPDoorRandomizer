import RaceRandom as random
import logging
import os
from collections import defaultdict, deque, Counter


from BaseClasses import Direction, RegionType, CrystalBarrier, DoorType, Door, flooded_keys
from Utils import append_to_yaml, clear_file
from source.dungeon.DungeonGenerationCommon import DungeonBuilder, define_sector_features, dungeon_portals
from source.dungeon.DungeonGenerationCommon import GlobalPolarity, find_sector

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
    # try:
    dungeons = main_dungeon_builders(dungeon_pool, sector_pool, portal_pool, gen_log, world, player)
    # append_to_yaml(generation_log_name, gen_log)
    return dungeons
    # except Exception as e:
    #     append_to_yaml(generation_log_name, gen_log)
    #     raise e


def main_dungeon_builders(dungeon_pool, sector_pool, portal_pool, gen_log, world, player):
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

    # ??? do we want a sector map?
    # sector_map = {}
    # for sector in sector_pool:
    #     for door in sector.outstanding_doors:
    #         sector_map[door.name] = sector

    # todo: distribute portals for split dungeons
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
        polarity_map = proposal_polarity(info)
        unbalanced = {dungeon: pol for dungeon, pol in polarity_map.items() if not pol.balanced()}
        if len(unbalanced) > 0:
            iterations += 1
            balance_move_sector(unbalanced, info)
            # swap something
            continue
        done = len(unbalanced) == 0
    info.gen_log.info(f'Performed {iterations} moves to achieve balance')
    return dungeon_map


def propose_sector(builder, new_sector, info, lock=False):
    info.proposal[builder.name].append(new_sector)
    if lock:
        new_sector.locked = True
        del info.sector_pool[new_sector]
        info.gen_log.info(f'{new_sector.sector_key()} locked to {builder.name}')
    else:
        info.gen_log.info(f'{new_sector.sector_key()} assigned to {builder.name}')


def proposal_polarity(info):
    polarity_map = {}
    for dungeon, sector_list in info.proposal.items():
        dungeon_polarity = Polarity(info.flags)
        polarity_map[dungeon] = dungeon_polarity
        for sector in sector_list:
            sector.pol = Polarity(info.flags, sector)
            dungeon_polarity.append(sector)
    return polarity_map


def balance_move_sector(unbalanced, info):
    most_imbalanced, best = find_most_imbalanced(unbalanced, info)
    target, best_charge = None, None
    for other in unbalanced:
        if other == most_imbalanced:
            continue
        curr_charge = unbalanced[other].charge()
        pol = Polarity(info.flags)
        pol.extend(info.proposal[other])
        pol.append(best)
        charge_diff = curr_charge - pol.charge()
        if target is None or charge_diff > best_charge:
            target = other
            best_charge = charge_diff
    # do the move
    info.proposal[most_imbalanced].remove(best)
    info.proposal[target].append(best)
    info.gen_log.info(f'Moved {best.sector_key()} from {most_imbalanced} to {target}')

def find_most_imbalanced(unbalanced, info):
    unlocked_cnt = {id: sum(1 for sector in info.proposal[id] if not sector.locked) for id in unbalanced}
    candidates = sorted(list(unbalanced.items()), key=lambda item: (item[1].charge(), unlocked_cnt[item[0]]))
    most_imbalanced, best, best_charge = None, None, None
    while best is None:
        most_imbalanced, polarity = candidates.pop()
        for sector in info.proposal[most_imbalanced]:
            if sector.locked:
                continue
            pol = Polarity(info.flags)
            pol.extend([x for x in info.proposal[most_imbalanced] if x != sector])
            charge = pol.charge()
            if best is None or charge < best_charge:
                best = sector
                best_charge = charge
    return most_imbalanced, best

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


class Polarity:
    def __init__(self, flags, sector=None):
        self.north = 0
        self.south = 0
        self.east = 0
        self.west = 0
        self.ttl_stairs = 0
        self.dead_stairs = 0
        self.one_ways = 0
        self.landings = 0
        self.flags = flags
        if sector is not None:
            self.append(sector)

    def append(self, sector):
        for d in sector.outstanding_doors:
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
        return self.stair_balanced()

    def stair_balanced(self):
        if self.flags.stair_loops:
            if self.flags.decoupled:
                return self.ttl_stairs > self.dead_stairs
            else:
                return self.ttl_stairs - self.dead_stairs >= self.dead_stairs
        else:
            return self.ttl_stairs % 2 == 0

    def charge(self):
        charge = abs(self.north - self.south)
        charge += abs(self.east - self.west)
        charge += max(self.one_ways - self.landings, 0)
        charge += 0 if self.stair_balanced() else 1
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
