import RaceRandom as random
import collections
import logging
import time

from BaseClasses import CrystalBarrier, DoorType, Hook, RegionType, Sector
from BaseClasses import hook_from_door, flooded_keys
from Regions import dungeon_events, flooded_keys_reverse


def pre_validate(builder, entrance_region_names, split_dungeon, world, player):
    pass
    # todo: determine the part of check_valid that are necessary here


def generate_dungeon(builder, entrance_region_names, split_dungeon, world, player):
    if builder.valid_proposal:  # we made this earlier in gen, just use it
        proposed_map = builder.valid_proposal
    else:
        proposed_map = generate_dungeon_find_proposal(builder, entrance_region_names, split_dungeon, world, player)
        builder.valid_proposal = proposed_map
    queue = collections.deque(proposed_map.items())
    while len(queue) > 0:
        a, b = queue.popleft()
        if a == b or world.decoupledoors[player]:
            connect_doors_one_way(a, b)
        else:
            connect_doors(a, b)
            queue.remove((b, a))
    if len(builder.sectors) == 0:
        return Sector()
    available_sectors = list(builder.sectors)
    master_sector = available_sectors.pop()
    for sub_sector in available_sectors:
        master_sector.regions.extend(sub_sector.regions)
    master_sector.outstanding_doors.clear()
    master_sector.r_name_set = None
    return master_sector


def generate_dungeon_find_proposal(builder, entrance_region_names, split_dungeon, world, player):
    logger = logging.getLogger('')
    name = builder.name
    logger.debug(f'Generating Dungeon: {name}')
    entrance_regions = convert_regions(entrance_region_names, world, player)
    excluded = {}
    for region in entrance_regions:
        portal = next((x for x in world.dungeon_portals[player] if x.door.entrance.parent_region == region), None)
        if portal:
            if portal.destination:
                excluded[region] = None
            elif len(entrance_regions) > 1:
                p_region = portal.door.entrance.connected_region
                access_region = next(x.parent_region for x in p_region.entrances
                                     if x.parent_region.type in [RegionType.LightWorld, RegionType.DarkWorld])
                if (access_region.name in world.inaccessible_regions[player] and
                     region.name not in world.enabled_entrances[player]):
                    excluded[region] = None
        elif split_dungeon and builder.sewers_access and builder.sewers_access.entrance.parent_region == region:
            continue
        drop_region = next((x.parent_region for x in region.entrances
                           if x.parent_region.type in [RegionType.LightWorld, RegionType.DarkWorld]
                           or x.parent_region.name == 'Sewer Drop'), None)
        if drop_region:  # for holes
            if drop_region.name == 'Sewer Drop':
                drop_region = next(x.parent_region for x in drop_region.entrances)
            if (drop_region.name in world.inaccessible_regions[player] and
               region.name not in world.enabled_entrances[player]):
                excluded[region] = None
            elif region in excluded:
                del excluded[region]
    entrance_regions = [x for x in entrance_regions if x not in excluded.keys()]
    doors_to_connect, idx = {}, 0
    all_regions = set()
    bk_special = False
    for sector in builder.sectors:
        for door in sector.outstanding_doors:
            doors_to_connect[door.name] = door, idx
            idx += 1
        all_regions.update(sector.regions)
        bk_special |= check_for_special(sector.regions)
    finished = False
    # flag if standard and this is hyrule castle
    paths = determine_paths_for_dungeon(world, player, all_regions, name)
    proposed_map = create_random_proposal(doors_to_connect, world, player)
    itr = 0
    hash_code = proposal_hash(doors_to_connect, proposed_map)
    hash_code_set = set()
    start = time.time()
    while not finished:
        if itr > 1000:
            elasped = time.time() - start
            raise GenerationException(f'Generation taking too long. {elasped}. Ref {name}')
        if hash_code in hash_code_set:
            proposed_map = create_random_proposal(doors_to_connect, world, player)
            hash_code = proposal_hash(doors_to_connect, proposed_map)
        if hash_code not in hash_code_set:
            hash_code_set.add(hash_code)
            explored_state = explore_proposal(name, entrance_regions, all_regions, proposed_map, doors_to_connect,
                                              bk_special, world, player)
            if check_valid(name, explored_state, proposed_map, doors_to_connect, all_regions,
                           paths, entrance_regions, bk_special, world, player):
                finished = True
            else:
                proposed_map, hash_code = modify_proposal(proposed_map, explored_state, doors_to_connect,
                                                          hash_code_set, world, player)
        itr += 1
    return proposed_map


def create_random_proposal(doors_to_connect, world, player):
    logger = logging.getLogger('')
    hooks = [Hook.North, Hook.South, Hook.East, Hook.West, Hook.Stairs]
    primary_bucket = collections.defaultdict(list)
    secondary_bucket = collections.defaultdict(list)
    for name, door in doors_to_connect.items():
        door, idx = door
        primary_bucket[hook_from_door(door)].append(door)
        secondary_bucket[hook_from_door(door)].append(door)
    proposal = {}
    while True:
        hooks_left, left = [], 0
        for hook in hooks:
            hook_len = len(primary_bucket[hook])
            if hook_len > 0:
                hooks_left.append(hook)
                left += hook_len
        if left == 0:
            return proposal
        next_hook = random.choice(hooks_left)
        primary_door = random.choice(primary_bucket[next_hook])
        opp_hook, secondary_door = type_map[next_hook], None
        while (secondary_door is None or (secondary_door == primary_door and not world.door_self_loops[player])
               or decouple_check(primary_bucket[next_hook], secondary_bucket[opp_hook],
                                 primary_door, secondary_door, world, player)):
            secondary_door = random.choice(secondary_bucket[opp_hook])
        proposal[primary_door] = secondary_door
        primary_bucket[next_hook].remove(primary_door)
        secondary_bucket[opp_hook].remove(secondary_door)
        if primary_door != secondary_door and not world.decoupledoors[player]:
            proposal[secondary_door] = primary_door
            primary_bucket[opp_hook].remove(secondary_door)
            secondary_bucket[next_hook].remove(primary_door)
            logger.debug(f'  Linking {primary_door.name} <-> {secondary_door.name}')
        else:
            logger.debug(f'  Linking {primary_door.name} -> {secondary_door.name}')


def decouple_check(primary_list, secondary_list, primary_door, secondary_door, world, player):
    if world.decoupledoors[player] and len(primary_list) == 2 and len(secondary_list) == 2:
        primary_alone = next(d for d in primary_list if d != primary_door)
        secondary_alone = next(d for d in secondary_list if d != secondary_door)
        return primary_alone == secondary_alone
    return False


def proposal_hash(doors_to_connect, proposed_map):
    hash_code = ''
    for name, door_pair in doors_to_connect.items():
        door, idx = door_pair
        hash_code += str(idx) + str(doors_to_connect[proposed_map[door].name][1])
    return hash_code


def modify_proposal(proposed_map, explored_state, doors_to_connect, hash_code_set, world, player):
    logger = logging.getLogger('')
    hash_code, itr = None, 0
    while hash_code is None or hash_code in hash_code_set:
        if itr > 10:
            proposed_map = create_random_proposal(doors_to_connect, world, player)
            hash_code = proposal_hash(doors_to_connect, proposed_map)
            return proposed_map, hash_code
        visited_bucket = collections.defaultdict(list)
        unvisted_bucket = collections.defaultdict(list)
        visited_choices = []
        unvisted_count = 0
        for door_one, door_two in proposed_map.items():
            if door_one in explored_state.visited_doors:
                visited_bucket[hook_from_door(door_one)].append(door_one)
                visited_choices.append(door_one)
            else:
                unvisted_bucket[hook_from_door(door_one)].append(door_one)
                unvisted_count += 1
        if unvisted_count == 0:
            # something is wrong beyond connectedness, crystal switch puzzle or bk layout - reshuffle
            proposed_map = create_random_proposal(doors_to_connect, world, player)
            hash_code = proposal_hash(doors_to_connect, proposed_map)
            return proposed_map, hash_code

        attempt, opp_hook = None, None
        opp_hook_len, possible_swaps = 0, list(visited_choices)
        while opp_hook_len == 0:
            if len(possible_swaps) == 0:
                break
            attempt = random.choice(possible_swaps)
            possible_swaps.remove(attempt)
            opp_hook = type_map[hook_from_door(attempt)]
            opp_hook_len = len(unvisted_bucket[opp_hook])
        if opp_hook_len == 0:
            itr += 1
            continue
        unvisted_bucket[opp_hook].sort(key=lambda d: d.name)
        new_door = random.choice(unvisted_bucket[opp_hook])
        old_target = proposed_map[attempt]
        if not world.decoupledoors[player]:
            old_attempt = proposed_map[new_door]
        else:
            old_attempt = next(x for x in proposed_map if proposed_map[x] == new_door)
        # ensure nothing gets messed up when something loops with itself
        if attempt == old_target and old_attempt == new_door:
            old_attempt = new_door
            old_target = attempt
        elif attempt == old_target:
            old_target = old_attempt
        elif old_attempt == new_door:
            old_attempt = old_target
        proposed_map[attempt] = new_door
        proposed_map[old_attempt] = old_target
        if not world.decoupledoors[player]:
            proposed_map[old_target] = old_attempt
            proposed_map[new_door] = attempt
        hash_code = proposal_hash(doors_to_connect, proposed_map)
        itr += 1

    if not world.decoupledoors[player]:
        logger.debug(f'   Re-linking {attempt.name} <-> {new_door.name}')
        logger.debug(f'   Re-linking {old_attempt.name} <-> {old_target.name}')
    else:
        logger.debug(f'   Re-Linking {attempt.name} -> {new_door.name}')
        logger.debug(f'   Re-Linking {old_attempt.name} -> {old_target.name}')
    return proposed_map, hash_code


def explore_proposal(name, entrance_regions, all_regions, proposed_map, valid_doors, bk_special, world, player):
    start = ExplorationState(dungeon=name)
    bk_relevant = (world.door_type_mode[player] == 'original' and not world.bigkeyshuffle[player]) or bk_special
    start.big_key_special = bk_special
    original_state = extend_reachable_state_lenient(entrance_regions, start, proposed_map,
                                                    all_regions, valid_doors, bk_relevant, world, player)
    return original_state


def check_valid(name, exploration_state, proposed_map, doors_to_connect, all_regions,
                paths, entrance_regions, bk_special, world, player):
    all_visited = set()
    all_visited.update(exploration_state.visited_blue)
    all_visited.update(exploration_state.visited_orange)
    if len(all_regions.difference(all_visited)) > 0:
        return False
    if not valid_paths(name, paths, entrance_regions, doors_to_connect, all_regions, proposed_map,
                       bk_special, world, player):
        return False
    return True


def determine_if_bk_needed(sector, split_dungeon, bk_special, world, player):
    if not split_dungeon or bk_special:
        for region in sector.regions:
            for ext in region.exits:
                door = world.check_for_door(ext.name, player)
                if door is not None and door.bigKey:
                    return True
    return False


def check_for_special(regions):
    for region in regions:
        for loc in region.locations:
            if loc.forced_big_key():
                return True
    return False


def valid_paths(name, paths, entrance_regions, valid_doors, all_regions, proposed_map, bk_special, world, player):
    for path in paths:
        if type(path) is tuple:
            target = path[1]
            start_regions = []
            for region in all_regions:
                if path[0] == region.name:
                    start_regions.append(region)
                    break
        else:
            target = path
            start_regions = entrance_regions
        if not valid_path(name, start_regions, target, valid_doors, proposed_map, all_regions,
                          bk_special, world, player):
            return False
    return True


def valid_path(name, starting_regions, target, valid_doors, proposed_map, all_regions, bk_special, world, player):
    target_regions = set()
    if type(target) is not list:
        for region in all_regions:
            if target == region.name:
                target_regions.add(region)
                break
    else:
        for region in all_regions:
            if region.name in target:
                target_regions.add(region)

    start = ExplorationState(dungeon=name)
    bk_relevant = (world.door_type_mode[player] == 'original' and not world.bigkeyshuffle[player]) or bk_special
    start.big_key_special = bk_special
    original_state = extend_reachable_state_lenient(starting_regions, start, proposed_map, all_regions,
                                                    valid_doors, bk_relevant, world, player)

    for exp_door in original_state.unattached_doors:
        if not exp_door.door.blocked or exp_door.door.trapFlag != 0:
            return True  # outstanding connection possible
    for target in target_regions:
        if original_state.visited_at_all(target):
            return True
    return False  # couldn't find an outstanding door or the target


boss_path_checks = ['Eastern Boss', 'Desert Boss', 'Hera Boss', 'Tower Agahnim 1', 'PoD Boss', 'Swamp Boss',
                    'Skull Boss', 'Ice Boss', 'Mire Boss', 'TR Boss', 'GT Agahnim 2']

# pinball is allowed to orphan you
drop_path_checks = ['Skull Pot Circle', 'Skull Left Drop', 'Skull Back Drop', 'Sewers Rat Path']


def determine_paths_for_dungeon(world, player, all_regions, name):
    all_r_names = set(x.name for x in all_regions)
    paths = []
    non_hole_portals = []
    for portal in world.dungeon_portals[player]:
        if portal.door.entrance.parent_region in all_regions:
            non_hole_portals.append(portal.door.entrance.parent_region.name)
            if portal.destination:
                paths.append(portal.door.entrance.parent_region.name)
    if world.mode[player] == 'standard' and name == 'Hyrule Castle Dungeon':
        paths.append('Hyrule Dungeon Cellblock')
        paths.append(('Hyrule Dungeon Cellblock', 'Hyrule Castle Throne Room'))
        entrance = next(x for x in world.dungeon_portals[player] if x.name == 'Hyrule Castle South')
        # todo: in non-er, we can use the other portals too
        paths.append(('Hyrule Dungeon Cellblock', entrance.door.entrance.parent_region.name))
        paths.append(('Hyrule Castle Throne Room', [entrance.door.entrance.parent_region.name,
                                                    'Hyrule Dungeon Cellblock']))
    if world.doorShuffle[player] in ['basic'] and name == 'Thieves Town':
        paths.append('Thieves Attic Window')
    elif 'Thieves Attic Window' in all_r_names:
        paths.append('Thieves Attic Window')
    for boss in boss_path_checks:
        if boss in all_r_names:
            paths.append(boss)
    if 'Thieves Boss' in all_r_names:
        paths.append('Thieves Boss')
        if world.get_dungeon("Thieves Town", player).boss.enemizer_name == 'Blind':
            paths.append(('Thieves Blind\'s Cell', 'Thieves Boss'))
    for drop_check in drop_path_checks:
        if drop_check in all_r_names:
            paths.append((drop_check, non_hole_portals))
    return paths


def convert_regions(region_names, world, player):
    region_list = []
    for name in region_names:
        region_list.append(world.get_region(name, player))
    return region_list


type_map = {
    Hook.Stairs: Hook.Stairs,
    Hook.North: Hook.South,
    Hook.South: Hook.North,
    Hook.West: Hook.East,
    Hook.East: Hook.West
}


def connect_doors(a, b):
    # Return on unsupported types.
    if a.type in [DoorType.Hole, DoorType.Warp, DoorType.Interior, DoorType.Logical]:
        return
    # Connect supported types
    if a.type in [DoorType.Normal, DoorType.SpiralStairs, DoorType.Open, DoorType.StraightStairs, DoorType.Ladder]:
        connect_two_way(a.entrance, b.entrance)
        dep_doors, target = [], None
        if len(a.dependents) > 0:
            dep_doors, target = a.dependents, b
        elif len(b.dependents) > 0:
            dep_doors, target = b.dependents, a
        if target is not None:
            target_region = target.entrance.parent_region
            for dep in dep_doors:
                connect_simple_door(dep, target_region)
        return
    # If we failed to account for a type, panic
    raise RuntimeError('Unknown door type ' + a.type.name)


def connect_doors_one_way(a, b):
    # Return on unsupported types.
    if a.type in [DoorType.Hole, DoorType.Warp, DoorType.Interior, DoorType.Logical]:
        return
    # Connect supported types
    if a.type in [DoorType.Normal, DoorType.SpiralStairs, DoorType.Open, DoorType.StraightStairs, DoorType.Ladder]:
        connect_one_way(a.entrance, b.entrance)
        dep_doors, target = [], None
        if len(a.dependents) > 0:
            dep_doors, target = a.dependents, b
        if target is not None:
            target_region = target.entrance.parent_region
            for dep in dep_doors:
                connect_simple_door(dep, target_region)
        return
    # If we failed to account for a type, panic
    raise RuntimeError('Unknown door type ' + a.type.name)


def connect_two_way(entrance, ext):

    # if these were already connected somewhere, remove the backreference
    if entrance.connected_region is not None:
        entrance.connected_region.entrances.remove(entrance)
    if ext.connected_region is not None:
        ext.connected_region.entrances.remove(ext)

    entrance.connect(ext.parent_region)
    ext.connect(entrance.parent_region)
    if entrance.parent_region.dungeon:
        ext.parent_region.dungeon = entrance.parent_region.dungeon
    x = entrance.door
    y = ext.door
    if x is not None:
        x.dest = y
    if y is not None:
        y.dest = x


def connect_one_way(entrance, ext):

    # if these were already connected somewhere, remove the backreference
    if entrance.connected_region is not None:
        entrance.connected_region.entrances.remove(entrance)

    entrance.connect(ext.parent_region)
    if entrance.parent_region.dungeon:
        ext.parent_region.dungeon = entrance.parent_region.dungeon
    x = entrance.door
    if x is not None:
        x.dest = ext.door


def connect_simple_door(exit_door, region):
    exit_door.entrance.connect(region)
    exit_door.dest = region


special_big_key_doors = ['Hyrule Dungeon Cellblock Door', "Thieves Blind's Cell Door"]
std_special_big_key_doors = ['Hyrule Castle Throne Room Tapestry'] + special_big_key_doors


def get_special_big_key_doors(world, player):
    if world.mode[player] == 'standard':
        return std_special_big_key_doors
    return special_big_key_doors


class ExplorationState(object):

    def __init__(self, init_crystal=CrystalBarrier.Orange, dungeon=None):

        self.unattached_doors = []
        self.avail_doors = []
        self.event_doors = []

        self.visited_orange = []
        self.visited_blue = []
        self.visited_doors = set()
        self.events = set()
        self.crystal = init_crystal

        # key region stuff
        self.door_krs = {}

        # key validation stuff
        self.small_doors = []
        self.big_doors = []
        self.opened_doors = []
        self.big_key_opened = False
        self.big_key_special = False

        self.found_locations = []
        self.ttl_locations = 0
        self.used_locations = 0
        self.key_locations = 0
        self.used_smalls = 0
        self.bk_found = set()

        self.non_door_entrances = []
        self.dungeon = dungeon
        self.pinball_used = False

        self.prize_door_set = {}
        self.prize_doors = []
        self.prize_doors_opened = False

    def copy(self):
        ret = ExplorationState(dungeon=self.dungeon)
        ret.unattached_doors = list(self.unattached_doors)
        ret.avail_doors = list(self.avail_doors)
        ret.event_doors = list(self.event_doors)
        ret.visited_orange = list(self.visited_orange)
        ret.visited_blue = list(self.visited_blue)
        ret.events = set(self.events)
        ret.crystal = self.crystal
        ret.door_krs = self.door_krs.copy()

        ret.small_doors = list(self.small_doors)
        ret.big_doors = list(self.big_doors)
        ret.opened_doors = list(self.opened_doors)
        ret.big_key_opened = self.big_key_opened
        ret.big_key_special = self.big_key_special
        ret.ttl_locations = self.ttl_locations
        ret.key_locations = self.key_locations
        ret.used_locations = self.used_locations
        ret.used_smalls = self.used_smalls
        ret.found_locations = list(self.found_locations)
        ret.bk_found = set(self.bk_found)

        ret.non_door_entrances = list(self.non_door_entrances)
        ret.dungeon = self.dungeon
        ret.pinball_used = self.pinball_used

        ret.prize_door_set = dict(self.prize_door_set)
        ret.prize_doors = list(self.prize_doors)
        ret.prize_doors_opened = self.prize_doors_opened
        return ret

    def next_avail_door(self):
        self.avail_doors.sort(key=lambda x: 0 if x.flag else 1 if x.door.bigKey else 2)
        exp_door = self.avail_doors.pop()
        self.crystal = exp_door.crystal
        return exp_door

    def visit_region(self, region, key_region=None, key_checks=False, bk_relevant=False):
        if region.type != RegionType.Dungeon:
            self.crystal = CrystalBarrier.Orange
        if self.crystal == CrystalBarrier.Either:
            if region not in self.visited_blue:
                self.visited_blue.append(region)
            if region not in self.visited_orange:
                self.visited_orange.append(region)
        elif self.crystal == CrystalBarrier.Orange:
            self.visited_orange.append(region)
        elif self.crystal == CrystalBarrier.Blue:
            self.visited_blue.append(region)
        if region.type == RegionType.Dungeon:
            for location in region.locations:
                if key_checks and location not in self.found_locations:
                    if location.forced_item and 'Small Key' in location.item.name:
                        self.key_locations += 1
                    if location.name not in dungeon_events and '- Prize' not in location.name and location.name not in ['Agahnim 1', 'Agahnim 2']:
                        self.ttl_locations += 1
                if location not in self.found_locations:
                    self.found_locations.append(location)
                    if bk_relevant:
                        if self.big_key_special:
                            if special_big_key_found(self):
                                self.bk_found.add(location)
                                self.re_add_big_key_doors()
                        else:
                            self.bk_found.add(location)
                            self.re_add_big_key_doors()
                if location.name in dungeon_events and location.name not in self.events:
                    if self.flooded_key_check(location):
                        self.perform_event(location.name, key_region)
                if location.name in flooded_keys_reverse.keys() and self.location_found(
                     flooded_keys_reverse[location.name]):
                    self.perform_event(flooded_keys_reverse[location.name], key_region)
                if '- Prize' in location.name:
                    self.prize_received = True

    def flooded_key_check(self, location):
        if location.name not in flooded_keys.keys():
            return True
        return flooded_keys[location.name] in [x.name for x in self.found_locations]

    def location_found(self, location_name):
        for l in self.found_locations:
            if l.name == location_name:
                return True
        return False

    def re_add_big_key_doors(self):
        self.big_key_opened = True
        queue = collections.deque(self.big_doors)
        while len(queue) > 0:
            exp_door = queue.popleft()
            self.avail_doors.append(exp_door)
            self.big_doors.remove(exp_door)

    def perform_event(self, location_name, key_region):
        self.events.add(location_name)
        queue = collections.deque(self.event_doors)
        while len(queue) > 0:
            exp_door = queue.popleft()
            if exp_door.door.req_event == location_name:
                self.avail_doors.append(exp_door)
                self.event_doors.remove(exp_door)
                if key_region is not None:
                    d_name = exp_door.door.name
                    if d_name not in self.door_krs.keys():
                        self.door_krs[d_name] = key_region

    def add_all_entrance_doors_check_unattached(self, region, world, player):
        door_list = [x for x in get_doors(world, region, player) if x.type in [DoorType.Normal, DoorType.SpiralStairs]]
        door_list.extend(get_entrance_doors(world, region, player))
        for door in door_list:
            if self.can_traverse(door):
                if door.dest is None and not self.in_door_list_ic(door, self.unattached_doors):
                    self.append_door_to_list(door, self.unattached_doors)
                elif door.req_event is not None and door.req_event not in self.events and not self.in_door_list(door,
                                                                                                                self.event_doors):
                    self.append_door_to_list(door, self.event_doors)
                elif not self.in_door_list(door, self.avail_doors):
                    self.append_door_to_list(door, self.avail_doors)
        for entrance in region.entrances:
            door = world.check_for_door(entrance.name, player)
            if door is None:
                self.non_door_entrances.append(entrance)

    def add_all_doors_check_unattached(self, region, world, player):
        for door in get_doors(world, region, player):
            if self.can_traverse(door):
                if door.controller is not None:
                    door = door.controller
                if door.dest is None and not self.in_door_list_ic(door, self.unattached_doors):
                    self.append_door_to_list(door, self.unattached_doors)
                elif door.req_event is not None and door.req_event not in self.events and not self.in_door_list(door,
                                                                                                                self.event_doors):
                    self.append_door_to_list(door, self.event_doors)
                elif not self.in_door_list(door, self.avail_doors):
                    self.append_door_to_list(door, self.avail_doors)

    def add_all_doors_check_proposed(self, region, proposed_map, valid_doors, flag, world, player, exception):
        for door in get_doors(world, region, player):
            if door in proposed_map and door.name in valid_doors:
                self.visited_doors.add(door)
            if door.blocked and exception(door):
                self.pinball_used = True
            if self.can_traverse(door, exception):
                if door.controller is not None:
                    door = door.controller
                if door.dest is None and door not in proposed_map.keys() and door.name in valid_doors:
                    if not self.in_door_list_ic(door, self.unattached_doors):
                        self.append_door_to_list(door, self.unattached_doors, flag)
                    else:
                        other = self.find_door_in_list(door, self.unattached_doors)
                        if self.crystal != other.crystal:
                            other.crystal = CrystalBarrier.Either
                elif door.req_event is not None and door.req_event not in self.events and not self.in_door_list(door,
                                                                                                                self.event_doors):
                    self.append_door_to_list(door, self.event_doors, flag)
                elif not self.in_door_list(door, self.avail_doors):
                    self.append_door_to_list(door, self.avail_doors, flag)

    # same as above but traps are ignored, and flag is not used
    def add_all_doors_check_proposed_2(self, region, proposed_map, valid_doors, bk_relevant, world, player):
        for door in get_doors(world, region, player):
            if door in proposed_map and door.name in valid_doors:
                self.visited_doors.add(door)
            if self.can_traverse_ignore_traps(door):
                if door.controller is not None:
                    door = door.controller
                if door.dest is None and door not in proposed_map.keys() and door.name in valid_doors:
                    if not self.in_door_list_ic(door, self.unattached_doors):
                        self.append_door_to_list(door, self.unattached_doors)
                    else:
                        other = self.find_door_in_list(door, self.unattached_doors)
                        if self.crystal != other.crystal:
                            other.crystal = CrystalBarrier.Either
                elif (door.req_event is not None and door.req_event not in self.events
                      and not self.in_door_list(door, self.event_doors)):
                    self.append_door_to_list(door, self.event_doors)
                elif (bk_relevant and (door.bigKey or door.name in get_special_big_key_doors(world, player))
                                       and not self.big_key_opened):
                    if not self.in_door_list(door, self.big_doors):
                        self.append_door_to_list(door, self.big_doors)
                elif not self.in_door_list(door, self.avail_doors):
                    self.append_door_to_list(door, self.avail_doors)

    # same as above but traps are checked for
    def add_all_doors_check_proposed_3(self, region, proposed_map, valid_doors, bk_relevant, world, player):
        for door in get_doors(world, region, player):
            if door in proposed_map and door.name in valid_doors:
                self.visited_doors.add(door)
            if self.can_traverse(door):
                if door.controller is not None:
                    door = door.controller
                if door.dest is None and door not in proposed_map.keys() and door.name in valid_doors:
                    if not self.in_door_list_ic(door, self.unattached_doors):
                        self.append_door_to_list(door, self.unattached_doors)
                    else:
                        other = self.find_door_in_list(door, self.unattached_doors)
                        if self.crystal != other.crystal:
                            other.crystal = CrystalBarrier.Either
                elif (door.req_event is not None and door.req_event not in self.events
                      and not self.in_door_list(door, self.event_doors)):
                    self.append_door_to_list(door, self.event_doors)
                elif (bk_relevant and (door.bigKey or door.name in get_special_big_key_doors(world, player))
                      and not self.big_key_opened):
                    if not self.in_door_list(door, self.big_doors):
                        self.append_door_to_list(door, self.big_doors)
                elif not self.in_door_list(door, self.avail_doors):
                    self.append_door_to_list(door, self.avail_doors)

    def add_all_doors_check_proposed_traps(self, region, proposed_traps, world, player):
        for door in get_doors(world, region, player):
            if self.can_traverse_ignore_traps(door) and door not in proposed_traps:
                if door.controller is not None:
                    door = door.controller
                if door.req_event is not None and door.req_event not in self.events and not self.in_door_list(door,
                                                                                                                self.event_doors):
                    self.append_door_to_list(door, self.event_doors, False)
                elif not self.in_door_list(door, self.avail_doors):
                    self.append_door_to_list(door, self.avail_doors, False)

    def add_all_doors_check_key_region(self, region, key_region, world, player):
        for door in get_doors(world, region, player):
            if self.can_traverse(door):
                if door.req_event is not None and door.req_event not in self.events and not self.in_door_list(door,
                                                                                                              self.event_doors):
                    self.append_door_to_list(door, self.event_doors)
                elif not self.in_door_list(door, self.avail_doors):
                    self.append_door_to_list(door, self.avail_doors)
                    if door.name not in self.door_krs.keys():
                        self.door_krs[door.name] = key_region
            else:
                if door.name not in self.door_krs.keys():
                    self.door_krs[door.name] = key_region

    def add_all_doors_check_keys(self, region, key_door_proposal, world, player):
        for door in get_doors(world, region, player):
            if self.can_traverse(door):
                if door.controller:
                    door = door.controller
                if door in key_door_proposal and door not in self.opened_doors:
                    if not self.in_door_list(door, self.small_doors):
                        self.append_door_to_list(door, self.small_doors)
                elif (door.bigKey or door.name in get_special_big_key_doors(world, player)) and not self.big_key_opened:
                    if not self.in_door_list(door, self.big_doors):
                        self.append_door_to_list(door, self.big_doors)
                elif door.req_event is not None and door.req_event not in self.events:
                    if not self.in_door_list(door, self.event_doors):
                        self.append_door_to_list(door, self.event_doors)
                elif not self.in_door_list(door, self.avail_doors):
                    self.append_door_to_list(door, self.avail_doors)

    def visited(self, region):
        if self.crystal == CrystalBarrier.Either:
            return region in self.visited_blue and region in self.visited_orange
        elif self.crystal == CrystalBarrier.Orange:
            return region in self.visited_orange
        elif self.crystal == CrystalBarrier.Blue:
            return region in self.visited_blue
        return False

    def visited_at_all(self, region):
        return region in self.visited_blue or region in self.visited_orange

    def found_forced_bk(self):
        for location in self.found_locations:
            if location.forced_big_key():
                return True
        return False

    def can_traverse(self, door, exception=None):
        if door.blocked:
            return exception(door) if exception else False
        if door.crystal not in [CrystalBarrier.Null, CrystalBarrier.Either]:
            return self.crystal == CrystalBarrier.Either or door.crystal == self.crystal
        return True

    def can_traverse_ignore_traps(self, door):
        if door.blocked and door.trapFlag == 0:
            return False
        if door.crystal not in [CrystalBarrier.Null, CrystalBarrier.Either]:
            return self.crystal == CrystalBarrier.Either or door.crystal == self.crystal
        return True

    def count_locations_exclude_specials(self, world, player):
        return count_locations_exclude_big_chest(self.found_locations, world, player)

    def validate(self, door, region, world, player):
        return self.can_traverse(door) and not self.visited(region) and valid_region_to_explore(region, self.dungeon,
                                                                                                world, player)

    def in_door_list(self, door, door_list):
        for d in door_list:
            if d.door == door and d.crystal == self.crystal:
                return True
        return False

    @staticmethod
    def in_door_list_ic(door, door_list):
        for d in door_list:
            if d.door == door:
                return True
        return False

    @staticmethod
    def find_door_in_list(door, door_list):
        for d in door_list:
            if d.door == door:
                return d
        return None

    def append_door_to_list(self, door, door_list, flag=False):
        if door.crystal == CrystalBarrier.Null:
            door_list.append(ExplorableDoor(door, self.crystal, flag))
        else:
            door_list.append(ExplorableDoor(door, door.crystal, flag))

    def key_door_sort(self, d):
        if d.door.smallKey:
            if d.door in self.opened_doors:
                return 1
            else:
                return 0
        return 2


def count_locations_exclude_big_chest(locations, world, player):
    cnt = 0
    for loc in locations:
        if ('- Big Chest' not in loc.name and not loc.forced_item and not reserved_location(loc, world, player)
             and not prize_or_event(loc) and not blind_boss_unavail(loc, locations, world, player)):
            cnt += 1
    return cnt


def prize_or_event(loc):
    return loc.name in dungeon_events or '- Prize' in loc.name or loc.name in ['Agahnim 1', 'Agahnim 2']


def reserved_location(loc, world, player):
    return hasattr(world, 'item_pool_config') and loc.name in world.item_pool_config.reserved_locations[player]


def blind_boss_unavail(loc, locations, world, player):
    if loc.name == "Thieves' Town - Boss":
        return (loc.parent_region.dungeon.boss.name == 'Blind' and
                (not any(x for x in locations if x.name == 'Suspicious Maiden') or
                 (world.get_region('Thieves Attic Window', player).dungeon.name == 'Thieves Town' and
                  not any(x for x in locations if x.name == 'Attic Cracked Floor'))))
    return False


class ExplorableDoor(object):

    def __init__(self, door, crystal, flag):
        self.door = door
        self.crystal = crystal
        self.flag = flag

    def __str__(self):
        return str(self.__unicode__())

    def __unicode__(self):
        return '%s (%s)' % (self.door.name, self.crystal.name)


def extend_reachable_state_improved(search_regions, state, proposed_map, all_regions, valid_doors, bk_flag, world, player, exception):
    local_state = state.copy()
    for region in search_regions:
        local_state.visit_region(region)
        local_state.add_all_doors_check_proposed(region, proposed_map, valid_doors, False, world, player, exception)
    while len(local_state.avail_doors) > 0:
        explorable_door = local_state.next_avail_door()
        if explorable_door.door.bigKey:
            if bk_flag:
                big_not_found = (not special_big_key_found(local_state) if local_state.big_key_special
                                 else local_state.count_locations_exclude_specials(world, player) == 0)
                if big_not_found:
                    continue  # we can't open this door
        if explorable_door.door in proposed_map:
            connect_region = world.get_entrance(proposed_map[explorable_door.door].name, player).parent_region
        else:
            connect_region = world.get_entrance(explorable_door.door.name, player).connected_region
        if connect_region is not None:
            if valid_region_to_explore_in_regions(connect_region, all_regions, world, player) and not local_state.visited(
                 connect_region):
                flag = explorable_door.flag or explorable_door.door.bigKey
                local_state.visit_region(connect_region, bk_flag=flag)
                local_state.add_all_doors_check_proposed(connect_region, proposed_map, valid_doors, flag, world, player, exception)
    return local_state


# bk_relevant means the big key doors need to be checks
def extend_reachable_state_lenient(search_regions, state, proposed_map, all_regions, valid_doors, bk_relevant,
                                   world, player):
    local_state = state.copy()
    for region in search_regions:
        local_state.visit_region(region, bk_relevant=bk_relevant)
        if world.trap_door_mode[player] == 'vanilla':
            local_state.add_all_doors_check_proposed_3(region, proposed_map, valid_doors, bk_relevant, world, player)
        else:
            local_state.add_all_doors_check_proposed_2(region, proposed_map, valid_doors, bk_relevant, world, player)
    while len(local_state.avail_doors) > 0:
        explorable_door = local_state.next_avail_door()
        if explorable_door.door.bigKey:
            if bk_relevant and (not special_big_key_found(local_state) if local_state.big_key_special
                                else local_state.count_locations_exclude_specials(world, player) == 0):
                continue
        if explorable_door.door in proposed_map:
            connect_region = world.get_entrance(proposed_map[explorable_door.door].name, player).parent_region
        else:
            connect_region = world.get_entrance(explorable_door.door.name, player).connected_region
        if connect_region is not None:
            if (valid_region_to_explore_in_regions(connect_region, all_regions, world, player)
               and not local_state.visited(connect_region)):
                local_state.visit_region(connect_region, bk_relevant=bk_relevant)
                if world.trap_door_mode[player] == 'vanilla':
                    local_state.add_all_doors_check_proposed_3(connect_region, proposed_map, valid_doors,
                                                               bk_relevant, world, player)
                else:
                    local_state.add_all_doors_check_proposed_2(connect_region, proposed_map, valid_doors,
                                                               bk_relevant, world, player)
    return local_state


def special_big_key_found(state):
    for location in state.found_locations:
        if location.forced_item and location.forced_item.bigkey:
            return True
    return False


def valid_region_to_explore_in_regions(region, all_regions, world, player):
    if region is None:
        return False
    return ((region.type == RegionType.Dungeon and region in all_regions)
            or region.name in world.inaccessible_regions[player]
            or (region.name == 'Hyrule Castle Ledge' and world.mode[player] == 'standard'))


def valid_region_to_explore(region, name, world, player):
    if region is None:
        return False
    return ((region.type == RegionType.Dungeon and region.dungeon and region.dungeon.name in name)
            or region.name in world.inaccessible_regions[player]
            or (region.name == 'Hyrule Castle Ledge' and world.mode[player] == 'standard'))


def get_doors(world, region, player):
    res = []
    for ext in region.exits:
        door = world.check_for_door(ext.name, player)
        if door is not None:
            res.append(door)
    return res


def get_entrance_doors(world, region, player):
    res = []
    for ext in region.entrances:
        door = world.check_for_door(ext.name, player)
        if door is not None:
            res.append(door)
    return res


class GenerationException(Exception):
    pass


