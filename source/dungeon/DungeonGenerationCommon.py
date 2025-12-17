from collections import defaultdict

import RaceRandom as random

from BaseClasses import CrystalBarrier, Polarity, PolSlot, DoorType, Hook, Direction, hook_from_door
from Regions import dungeon_events

# ------------------------------ #
#      Main Helper Functions
# ------------------------------ #

def define_sector_features(sectors):
    for sector in sectors:
        for region in sector.regions:
            for loc in region.locations:
                if '- Prize' in loc.name or loc.name in ['Agahnim 1', 'Agahnim 2']:
                    pass
                elif loc.forced_item and 'Small Key' in loc.item.name:
                    sector.key_only_locations += 1
                elif loc.forced_item and loc.forced_item.bigkey:
                    sector.bk_provided = True
                elif loc.name not in dungeon_events and not loc.forced_item:
                    sector.chest_locations += 1
                    sector.chest_location_set.add(loc.name)
                    if '- Big Chest' in loc.name or loc.name in ["Hyrule Castle - Zelda's Chest",
                                                                 "Thieves' Town - Blind's Cell"]:
                        sector.bk_required = True
            for ext in region.exits:
                door = ext.door
                if door is not None and not door.blocked:
                    if door.crystal == CrystalBarrier.Either:
                        sector.c_switch = True
                    elif door.crystal == CrystalBarrier.Orange:
                        sector.orange_barrier = True
                    elif door.crystal == CrystalBarrier.Blue:
                        sector.blue_barrier = True
                    if door.bigKey:
                        sector.bk_required = True
            if region.name in ['PoD Mimics 2', 'PoD Bow Statue Right', 'PoD Mimics 1', 'GT Mimics 1', 'GT Mimics 2',
                               'Eastern Single Eyegore', 'Eastern Duo Eyegores']:
                sector.item_logic.add('Bow')
            if region.name in ['Swamp Lobby', 'Swamp Entrance']:
                sector.item_logic.add('Open Floodgate')
            # these are not exhaustive right now, just ones that matter for sector pruning
            if region.name in ['TR Final Abyss Ledge', 'TR Dark Ride Ledges', 'TR Hub', 'TR Torches',
                               'Mire Dark Shooters', 'TR Main Lobby']:
                sector.item_logic.add('Somaria')
            if region.name in ['Ice Hookshot Balcony', 'Mire Lobby']:
                sector.item_logic.add('Hookshot')
            if region.name in ['Skull Torch Room']:
                sector.item_logic.add('Fire Rod')
            if region.name in ['Sewers Water', 'Sewers Rope Room']:
                sector.item_logic.add('Lamp')
            if region.name in ['GT Lanmolas 2']:
                sector.item_logic.add('Boss')
        for door in sector.outstanding_doors:
            if door.portalAble:
                if len(sector.outstanding_doors) == 1 and not is_boss_trap(door):
                    door.dead_end()
                elif len(sector.outstanding_doors) == 1 and is_boss_trap(door) and door.deadEnd:
                    door.deadEnd = False


def handle_special_sectors(all_sectors, candidate_sectors, global_pole, dungeon_pool, connections_tuple,
                           dungeon_entrances, world, player):

    entrances_map, potentials, connections = connections_tuple

    dungeon_map = {}
    for key in dungeon_pool:
        current_dungeon = dungeon_map[key] = DungeonBuilder(key)
        for r_name in dungeon_boss_sectors[key]:
            assign_sector(find_sector(r_name, candidate_sectors), current_dungeon, candidate_sectors, global_pole)
        if key == 'Hyrule Castle' and world.mode[player] == 'standard':
            for r_name in ['Hyrule Dungeon Cellblock', 'Sanctuary', 'Hyrule Castle Throne Room']:  # need to deliver zelda
                assign_sector(find_sector(r_name, candidate_sectors), current_dungeon,
                              candidate_sectors, global_pole)
        if key == 'Thieves Town' and world.get_dungeon("Thieves Town", player).boss.enemizer_name == 'Blind':
            assign_sector(find_sector("Thieves Blind's Cell", candidate_sectors), current_dungeon,
                          candidate_sectors, global_pole)
    accessible_sectors, reverse_d_map = set(), {}
    for key in dungeon_pool:
        current_dungeon = dungeon_map[key]
        current_dungeon.all_entrances = dungeon_entrances[key]
        for r_name in current_dungeon.all_entrances:
            sector = find_sector(r_name, candidate_sectors)
            assign_sector(sector, current_dungeon, candidate_sectors, global_pole)
            if r_name in entrances_map[key]:
                if sector:
                    accessible_sectors.add(sector)
            else:
                if not sector:
                    sector = find_sector(r_name, all_sectors)
                reverse_d_map[sector] = key
    return dungeon_map, accessible_sectors, reverse_d_map


def assign_sector(sector, dungeon, candidate_sectors, global_pole):
    if sector:
        del candidate_sectors[sector]
        global_pole.consume(sector)
        assign_sector_helper(sector, dungeon)


def assign_sector_helper(sector, builder):
    builder.sectors.append(sector)
    builder.location_cnt += sector.chest_locations
    builder.key_drop_cnt += sector.key_only_locations
    builder.location_set.update(sector.chest_location_set)
    if sector.c_switch:
        builder.c_switch_present = True
    if sector.blue_barrier:
        builder.c_switch_required = True
    if sector.bk_required:
        builder.bk_required = True
    if sector.bk_provided:
        builder.bk_provided = True
    count_conn_needed_supplied(sector, builder.conn_needed, builder.conn_supplied)
    builder.dead_ends += sector.dead_ends()
    builder.branches += sector.branches()
    if sector in builder.exception_list:
        builder.exception_list.remove(sector)
    else:
        if builder.split_dungeon_map:
            builder.split_dungeon_map = None
        if builder.valid_proposal:
            builder.valid_proposal = None


def count_conn_needed_supplied(sector, conn_needed, conn_supplied):
    for door in sector.outstanding_doors:
        # todo: destination sectors like skull 2 west should be
        if (door.blocked or door.dead or sector.adj_outflow() <= 1) and not sector.is_entrance_sector():
            conn_needed[hook_from_door(door)] += 1
        # todo: stonewall
        else:  # todo: dungeons that need connections... skull, tr, hc, desert (when edges are done)
            conn_supplied[hanger_from_door(door)] += 1


def find_sector(r_name, sectors):
    for s in sectors:
        if r_name in s.region_set():
            return s
    return None


def standard_stair_check(dungeon_map, dungeon, candidate_sectors, global_pole):
    # this is because there must be at least one non-dead stairway in hc to get out
    # this check may not be necessary
    filtered_sectors = [x for x in candidate_sectors if 'Open Floodgate' not in x.item_logic and
                        any(y for y in x.outstanding_doors if not y.dead and y.type == DoorType.SpiralStairs)]
    valid = False
    while not valid:
        chosen_sector = random.choice(filtered_sectors)
        filtered_sectors.remove(chosen_sector)
        valid = global_pole.is_valid_choice(dungeon_map, dungeon, [chosen_sector])
        if valid:
            assign_sector(chosen_sector, dungeon, candidate_sectors, global_pole)


def identify_destination_sectors(accessible_sectors, reverse_d_map, dungeon_map, connections, dungeon_entrances, split_dungeon_entrances):
    accessible_overworld, found_connections, explored = set(), set(), False

    while not explored:
        explored = True
        for ent_name, region in connections.items():
            if ent_name in found_connections:
                continue
            sector = find_sector(ent_name, reverse_d_map.keys())
            if sector is None:
                continue
            if sector in accessible_sectors:
                found_connections.add(ent_name)
                accessible_overworld.add(region)  # todo: drops don't give ow access
                explored = False
            elif region in accessible_overworld:
                found_connections.add(ent_name)
                accessible_sectors.add(sector)
                explored = False
            else:
                d_name = reverse_d_map[sector]
                if d_name not in dungeon_map:
                    return
                if d_name not in split_dungeon_entrances:
                    for r_name in dungeon_entrances[d_name]:
                        ent_sector = find_sector(r_name, dungeon_map[d_name].sectors)
                        if ent_sector in accessible_sectors and ent_name not in dead_entrances:
                            sector.destination_entrance = True
                            found_connections.add(ent_name)
                            accessible_sectors.add(sector)
                            accessible_overworld.add(region)
                            explored = False
                            break
                elif d_name in split_dungeon_entrances.keys():
                    split_section = None
                    for split_name, split_list in split_dungeon_entrances[d_name].items():
                        if ent_name in split_list:
                            split_section = split_name
                            break
                    if split_section:
                        for r_name in split_dungeon_entrances[d_name][split_section]:
                            ent_sector = find_sector(r_name, dungeon_map[d_name].sectors)
                            if ent_sector in accessible_sectors and ent_name not in dead_entrances:
                                sector.destination_entrance = True
                                found_connections.add(ent_name)
                                accessible_sectors.add(sector)
                                accessible_overworld.add(region)
                                explored = False
                                break


# todo: split version that adds allowance for potential entrances
def calc_allowance_and_dead_ends(builder, connections_tuple, world, player):
    portals = world.dungeon_portals[player]
    entrances_map, potentials, connections = connections_tuple
    name = builder.name if not builder.split_flag else builder.name.rsplit(' ', 1)[0]
    needed_connections = [x for x in builder.all_entrances if x not in entrances_map[name]]
    starting_allowance = 0
    used_sectors = set()
    destination_entrances = [x.door.entrance.parent_region.name for x in portals if x.destination]
    dead_ends = [x.door.entrance.parent_region.name for x in portals if x.deadEnd]
    for entrance in entrances_map[name]:
        sector = find_sector(entrance, builder.sectors)
        if sector:
            outflow_target = 0 if entrance not in drop_entrances_allowance else 1
            if sector not in used_sectors and (sector.adj_outflow() > outflow_target or entrance in dead_ends):
                if entrance not in destination_entrances:
                    starting_allowance += 1
                else:
                    builder.branches -= 1
                used_sectors.add(sector)
            elif sector not in used_sectors:
                if entrance in destination_entrances and sector.branches() > 0:
                    builder.branches -= 1
                if entrance not in drop_entrances_allowance:
                    needed_connections.append(entrance)
    if builder.sewers_access:
        starting_allowance += 1
    builder.allowance = starting_allowance
    for entrance in needed_connections:
        sector = find_sector(entrance, builder.sectors)
        if sector and sector not in used_sectors:  # ignore things on same sector
            is_destination = entrance in destination_entrances
            connect_able = False
            if entrance in connections.keys():
                enabling_region = connections[entrance]
                check_list = list(potentials[enabling_region])
                if enabling_region.name in ['Desert Ledge', 'Desert Ledge Keep']:
                    alternate = 'Desert Ledge Keep' if enabling_region.name == 'Desert Ledge' else 'Desert Ledge'
                    if world.get_region(alternate, player) in potentials:
                        check_list.extend(potentials[world.get_region(alternate, player)])
                connecting_entrances = [x for x in check_list if x != entrance and x not in dead_entrances and x not in drop_entrances_allowance]
                connect_able = len(connecting_entrances) > 0
            if is_destination and sector.branches() == 0:  #
                builder.dead_ends += 1
            if is_destination and sector.branches() > 0:
                builder.branches -= 1
            if connect_able and not is_destination:
                builder.allowance += 1
            used_sectors.add(sector)


def handle_non_crossworld_sanctuary(candidate_sectors, dungeon_map, dungeon_pool, global_pole, world, player):
    # todo: figure out non-crossworld better, using mode_def from ES2, probably
    if world.mode[player] == 'open' and world.shuffle[player] not in ['crossed', 'insanity', 'lean', 'swapped']:
        sanc = find_sector('Sanctuary', candidate_sectors)
        if sanc:  # only run if sanc if a candidate
            lw_builders = []
            for name in dungeon_pool:
                for portal_name in dungeon_portals[name]:
                    if world.get_portal(portal_name, player).light_world:
                        lw_builders.append(dungeon_map[name])
                        break
            # portals only - not drops for mirror stuff
            sanc_builder = random.choice(lw_builders)
            assign_sector(sanc, sanc_builder, candidate_sectors, global_pole)


def assign_non_hc_sectors(dungeon_map, non_hc_sectors, global_pole):
    sector_list = list(non_hc_sectors)
    random.shuffle(sector_list)
    population = []
    for name in dungeon_map:
        if name != 'Hyrule Castle':
            population.append(name)
    choices = random.choices(population, k=len(sector_list))
    for i, choice in enumerate(choices):
        builder = dungeon_map[choice]
        assign_sector(sector_list[i], builder, non_hc_sectors, global_pole)


hang_dir_map = {
    Direction.North: Hook.South,
    Direction.South: Hook.North,
    Direction.West: Hook.East,
    Direction.East: Hook.West,
}


def hanger_from_door(door):
    if door.type == DoorType.SpiralStairs:
        return Hook.Stairs
    if door.type in [DoorType.Normal, DoorType.Open, DoorType.StraightStairs, DoorType.Ladder]:
        return hang_dir_map[door.direction]
    return None

# ------------------------------ #
#       Generation Classes
# ------------------------------ #

class DungeonBuilder(object):

    def __init__(self, name):
        self.name = name
        self.sectors = []
        self.location_cnt = 0
        self.location_set = set()
        self.key_drop_cnt = 0
        self.dungeon_items = None  # during fill how many dungeon items are left
        self.free_items = None  # during fill how many dungeon items are left
        self.bk_required = False
        self.bk_provided = False
        self.c_switch_required = False
        self.c_switch_present = False
        self.c_locked = False
        self.dead_ends = 0
        self.branches = 0
        self.forced_loops = 0
        self.total_conn_lack = 0
        self.conn_needed = defaultdict(int)
        self.conn_supplied = defaultdict(int)
        self.conn_balance = defaultdict(int)
        self.mag_needed = {}
        self.unfulfilled = defaultdict(int)
        self.all_entrances = None  # used for sector segregation/branching
        self.entrance_list = None  # used for overworld accessibility
        self.layout_starts = None  # used for overworld accessibility
        self.master_sector = None
        self.path_entrances = None  # used for pathing/key doors, I think
        self.split_flag = False

        self.candidates = None
        self.total_keys = None
        self.key_doors_num = None
        self.combo_size = None
        self.flex = 0
        self.key_door_proposal = None
        self.bk_door_proposal = None
        self.trap_door_proposal = None

        self.allowance = 1

        self.valid_proposal = None
        self.split_dungeon_map = None
        self.exception_list = []

        self.throne_door = None
        self.throne_sector = None
        self.chosen_lobby = None
        self.sewers_access = None

    def polarity_complement(self):
        pol = Polarity()
        for sector in self.sectors:
            pol += sector.polarity()
        return pol.complement()

    def polarity(self):
        pol = Polarity()
        for sector in self.sectors:
            pol += sector.polarity()
        return pol

    def __str__(self):
        return str(self.__unicode__())

    def __unicode__(self):
        return '%s' % self.name

def sum_polarity(sector_list):
    pol = Polarity()
    for sector in sector_list:
        pol += sector.polarity()
    return pol


class GlobalPolarity:

    def __init__(self, candidate_sectors):
        self.positives = [0, 0, 0]
        self.negatives = [0, 0, 0]
        self.evens = 0
        self.odds = 0
        for sector in candidate_sectors:
            pol = sector.polarity()
            if pol.charge() % 2 == 0:
                self.evens += 1
            else:
                self.odds += 1
            for slot in PolSlot:
                if pol.vector[slot.value] < 0:
                    self.negatives[slot.value] += -pol.vector[slot.value]
                elif pol.vector[slot.value] > 0:
                    self.positives[slot.value] += pol.vector[slot.value]

    def copy(self):
        gp = GlobalPolarity([])
        gp.positives = self.positives.copy()
        gp.negatives = self.negatives.copy()
        gp.evens = self.evens
        gp.odds = self.odds
        return gp

    def is_valid(self, dungeon_map):
        polarities = [x.polarity() for x in dungeon_map.values()]
        return self._check_parity(polarities) and self._is_valid_polarities(polarities)

    def _check_parity(self, polarities):
        local_evens = 0
        local_odds = 0
        for pol in polarities:
            if pol.charge() % 2 == 0:
                local_evens += 1
            else:
                local_odds += 1
        if local_odds > self.odds:
            return False
        return True

    def _is_valid_polarities(self, polarities):
        positives = self.positives.copy()
        negatives = self.negatives.copy()
        for polarity in polarities:
            for slot in PolSlot:
                if polarity[slot.value] > 0 and slot != PolSlot.Stairs:
                    if negatives[slot.value] >= polarity[slot.value]:
                        negatives[slot.value] -= polarity[slot.value]
                    else:
                        return False
                elif polarity[slot.value] < 0 and slot != PolSlot.Stairs:
                    if positives[slot.value] >= -polarity[slot.value]:
                        positives[slot.value] += polarity[slot.value]
                    else:
                        return False
                elif slot == PolSlot.Stairs:
                    if positives[slot.value] >= polarity[slot.value]:
                        positives[slot.value] -= polarity[slot.value]
                    else:
                        return False
        return True

    def consume(self, sector):
        polarity = sector.polarity()
        if polarity.charge() % 2 == 0:
            self.evens -= 1
        else:
            self.odds -= 1
        for slot in PolSlot:
            if polarity[slot.value] > 0 and slot != PolSlot.Stairs:
                if self.positives[slot.value] >= polarity[slot.value]:
                    self.positives[slot.value] -= polarity[slot.value]
                else:
                    raise GenerationException('Invalid assignment of %s' % sector.name)
            elif polarity[slot.value] < 0 and slot != PolSlot.Stairs:
                if self.negatives[slot.value] >= -polarity[slot.value]:
                    self.negatives[slot.value] += polarity[slot.value]
                else:
                    raise GenerationException('Invalid assignment of %s' % sector.name)
            elif slot == PolSlot.Stairs:
                if self.positives[slot.value] >= polarity[slot.value]:
                    self.positives[slot.value] -= polarity[slot.value]
                else:
                    raise GenerationException('Invalid assignment of %s' % sector.name)

    def is_valid_choice(self, dungeon_map, builder, sectors):
        proposal = self.copy()
        non_neutral_polarities = [x.polarity() for x in dungeon_map.values() if not x.polarity().is_neutral() and x != builder]
        current_polarity = builder.polarity() + sum_polarity(sectors)
        non_neutral_polarities.append(current_polarity)
        for sector in sectors:
            proposal.consume(sector)
        return proposal._check_parity(non_neutral_polarities) and proposal._is_valid_polarities(non_neutral_polarities)

    def is_valid_multi_choice(self, dungeon_map, builders, sector_lists):
        proposal = self.copy()
        non_neutral_polarities = [x.polarity() for x in dungeon_map.values() if not x.polarity().is_neutral()
                                  and x not in builders]
        for i, sectors in enumerate(sector_lists):
            builder = builders[i]
            current_polarity = builder.polarity() + sum_polarity(sectors)
            non_neutral_polarities.append(current_polarity)
            for sector in sectors:
                proposal.consume(sector)
        return proposal._check_parity(non_neutral_polarities) and proposal._is_valid_polarities(non_neutral_polarities)

    def is_valid_multi_choice_2(self, dungeon_map, builders, sector_dict):
        proposal = self.copy()
        non_neutral_polarities = [x.polarity() for x in dungeon_map.values() if not x.polarity().is_neutral()
                                  and x not in builders]
        for builder, sectors in sector_dict.items():
            current_polarity = builder.polarity() + sum_polarity(sectors)
            non_neutral_polarities.append(current_polarity)
            for sector in sectors:
                proposal.consume(sector)
        return proposal._check_parity(non_neutral_polarities) and proposal._is_valid_polarities(non_neutral_polarities)

    # def check_odd_polarities(self, candidate_sectors, dungeon_map):
    #     odd_candidates = [x for x in candidate_sectors if x.polarity().charge() % 2 != 0]
    #     odd_map = {n: x for (n, x) in dungeon_map.items() if sum_polarity(x.sectors).charge() % 2 != 0}
    #     gp = GlobalPolarity(odd_candidates)
    #     return gp.is_valid(odd_map)


# ugly hack for now
def is_boss_trap(d):
    return ' Boss ' in d.name or ' Agahnim ' in d.name or d.name in ['Skull Spike Corner SW']

class NeutralizingException(Exception):
    pass


class GenerationException(Exception):
    pass

# ------------------------------ #
#         Data Section
# ------------------------------ #

dungeon_boss_sectors = {
    'Hyrule Castle': [],
    'Eastern Palace': ['Eastern Boss'],
    'Desert Palace': ['Desert Boss'],
    'Tower of Hera': ['Hera Boss'],
    'Agahnims Tower': ['Tower Agahnim 1'],
    'Palace of Darkness': ['PoD Boss'],
    'Swamp Palace': ['Swamp Boss'],
    'Skull Woods': ['Skull Boss'],
    'Thieves Town': ['Thieves Boss'],
    'Ice Palace': ['Ice Boss'],
    'Misery Mire': ['Mire Boss'],
    'Turtle Rock': ['TR Boss'],
    'Ganons Tower': ['GT Agahnim 2']
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

drop_entrances_allowance = [
    'Sewers Rat Path', 'Skull Pinball', 'Skull Left Drop', 'Skull Pot Circle', 'Skull Back Drop'
]

dead_entrances = [
    'TR Big Chest Entrance'
]

dungeon_portals = {
    'Hyrule Castle': ['Hyrule Castle South', 'Hyrule Castle West', 'Hyrule Castle East', 'Sanctuary'],
    'Eastern Palace': ['Eastern'],
    'Desert Palace': ['Desert Back', 'Desert South', 'Desert West', 'Desert East'],
    'Tower of Hera': ['Hera'],
    'Agahnims Tower': ['Agahnims Tower'],
    'Palace of Darkness': ['Palace of Darkness'],
    'Swamp Palace': ['Swamp'],
    'Skull Woods': ['Skull 1', 'Skull 2 East', 'Skull 2 West', 'Skull 3'],
    'Thieves Town': ['Thieves Town'],
    'Ice Palace': ['Ice'],
    'Misery Mire': ['Mire'],
    'Turtle Rock': ['Turtle Rock Main', 'Turtle Rock Lazy Eyes', 'Turtle Rock Chest', 'Turtle Rock Eye Bridge'],
    'Ganons Tower': ['Ganons Tower']
}

special_bk_regions = ['Hyrule Dungeon Cellblock', "Thieves Blind's Cell"]
