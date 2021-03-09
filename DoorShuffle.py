import random
from collections import defaultdict, deque
import logging
import operator as op
import time
from enum import unique, Flag
from typing import DefaultDict, Dict, List

from functools import reduce
from BaseClasses import RegionType, Region, Door, DoorType, Direction, Sector, CrystalBarrier, DungeonInfo
from Dungeons import dungeon_regions, region_starts, standard_starts, split_region_starts
from Dungeons import dungeon_bigs, dungeon_keys, dungeon_hints
from Items import ItemFactory
from RoomData import DoorKind, PairedDoor
from DungeonGenerator import ExplorationState, convert_regions, generate_dungeon, pre_validate, determine_required_paths, drop_entrances
from DungeonGenerator import create_dungeon_builders, split_dungeon_builder, simple_dungeon_builder, default_dungeon_entrances
from DungeonGenerator import dungeon_portals, dungeon_drops
from KeyDoorShuffle import analyze_dungeon, validate_vanilla_key_logic, build_key_layout, validate_key_layout


def link_doors(world, player):

    # Drop-down connections & push blocks
    for exitName, regionName in logical_connections:
        connect_simple_door(world, exitName, regionName, player)
    # These should all be connected for now as normal connections
    for edge_a, edge_b in interior_doors:
        connect_interior_doors(edge_a, edge_b, world, player)

    # These connections are here because they are currently unable to be shuffled
    for exitName, regionName in falldown_pits:
        connect_simple_door(world, exitName, regionName, player)
    for exitName, regionName in dungeon_warps:
        connect_simple_door(world, exitName, regionName, player)
    for ent, ext in ladders:
        connect_two_way(world, ent, ext, player)

    if world.intensity[player] < 2:
        for entrance, ext in open_edges:
            connect_two_way(world, entrance, ext, player)
        for entrance, ext in straight_staircases:
            connect_two_way(world, entrance, ext, player)

    if world.intensity[player] < 3 or world.doorShuffle == 'vanilla':
        mirror_route = world.get_entrance('Sanctuary Mirror Route', player)
        mr_door = mirror_route.door
        sanctuary = mirror_route.parent_region
        sanctuary.exits.remove(mirror_route)
        world.remove_entrance(mirror_route, player)
        world.remove_door(mr_door, player)

    connect_custom(world, player)

    find_inaccessible_regions(world, player)

    if world.intensity[player] >= 3 and world.doorShuffle[player] in ['basic', 'crossed']:
        choose_portals(world, player)
    else:
        if world.shuffle[player] == 'vanilla':
            if world.mode[player] == 'standard':
                world.get_portal('Sanctuary', player).destination = True
            world.get_portal('Desert East', player).destination = True
            if world.mode[player] == 'inverted':
                world.get_portal('Desert West', player).destination = True
            if world.mode[player] == 'open':
                world.get_portal('Skull 2 West', player).destination = True
                world.get_portal('Turtle Rock Lazy Eyes', player).destination = True
                world.get_portal('Turtle Rock Eye Bridge', player).destination = True
        else:
            analyze_portals(world, player)
        for portal in world.dungeon_portals[player]:
            connect_portal(portal, world, player)

    if world.doorShuffle[player] == 'vanilla':
        for entrance, ext in open_edges:
            connect_two_way(world, entrance, ext, player)
        for entrance, ext in straight_staircases:
            connect_two_way(world, entrance, ext, player)
        for exitName, regionName in vanilla_logical_connections:
            connect_simple_door(world, exitName, regionName, player)
        for entrance, ext in spiral_staircases:
            connect_two_way(world, entrance, ext, player)
        for entrance, ext in default_door_connections:
            connect_two_way(world, entrance, ext, player)
        for ent, ext in default_one_way_connections:
            connect_one_way(world, ent, ext, player)
        vanilla_key_logic(world, player)
    elif world.doorShuffle[player] == 'basic':
        within_dungeon(world, player)
    elif world.doorShuffle[player] == 'crossed':
        cross_dungeon(world, player)
    else:
        logging.getLogger('').error('Invalid door shuffle setting: %s' % world.doorShuffle[player])
        raise Exception('Invalid door shuffle setting: %s' % world.doorShuffle[player])

    if world.doorShuffle[player] != 'vanilla':
        create_door_spoiler(world, player)


# todo: I think this function is not necessary
def mark_regions(world, player):
    # traverse dungeons and make sure dungeon property is assigned
    player_dungeons = [dungeon for dungeon in world.dungeons if dungeon.player == player]
    for dungeon in player_dungeons:
        queue = deque(dungeon.regions)
        while len(queue) > 0:
            region = world.get_region(queue.popleft(), player)
            if region.name not in dungeon.regions:
                dungeon.regions.append(region.name)
                region.dungeon = dungeon
            for ext in region.exits:
                d = world.check_for_door(ext.name, player)
                connected = ext.connected_region
                if d is not None and connected is not None:
                    if d.dest is not None and connected.name not in dungeon.regions and connected.type == RegionType.Dungeon and connected.name not in queue:
                        queue.append(connected)  # needs to be added
                elif connected is not None and connected.name not in dungeon.regions and connected.type == RegionType.Dungeon and connected.name not in queue:
                    queue.append(connected)  # needs to be added


def create_door_spoiler(world, player):
    logger = logging.getLogger('')

    queue = deque(world.dungeon_layouts[player].values())
    while len(queue) > 0:
        builder = queue.popleft()
        done = set()
        start_regions = set(convert_regions(builder.layout_starts, world, player))  # todo: set all_entrances for basic
        reg_queue = deque(start_regions)
        visited = set(start_regions)
        while len(reg_queue) > 0:
            next = reg_queue.pop()
            for ext in next.exits:
                door_a = ext.door
                connect = ext.connected_region
                if door_a and door_a.type in [DoorType.Normal, DoorType.SpiralStairs, DoorType.Open,
                                              DoorType.StraightStairs] and door_a not in done:
                    done.add(door_a)
                    door_b = door_a.dest
                    if door_b and not isinstance(door_b, Region):
                        done.add(door_b)
                        if not door_a.blocked and not door_b.blocked:
                            world.spoiler.set_door(door_a.name, door_b.name, 'both', player, builder.name)
                        elif door_a.blocked:
                            world.spoiler.set_door(door_b.name, door_a.name, 'entrance', player, builder.name)
                        elif door_b.blocked:
                            world.spoiler.set_door(door_a.name, door_b.name, 'entrance', player, builder.name)
                        else:
                            logger.warning('This is a bug during door spoiler')
                    elif not isinstance(door_b, Region):
                        logger.warning('Door not connected: %s', door_a.name)
                if connect and connect.type == RegionType.Dungeon and connect not in visited:
                    visited.add(connect)
                    reg_queue.append(connect)


def vanilla_key_logic(world, player):
    builders = []
    world.dungeon_layouts[player] = {}
    for dungeon in [dungeon for dungeon in world.dungeons if dungeon.player == player]:
        sector = Sector()
        sector.name = dungeon.name
        sector.regions.extend(convert_regions(dungeon.regions, world, player))
        builder = simple_dungeon_builder(sector.name, [sector])
        builder.master_sector = sector
        builders.append(builder)
        world.dungeon_layouts[player][builder.name] = builder

    add_inaccessible_doors(world, player)
    for builder in builders:
        origin_list = find_accessible_entrances(world, player, builder)
        start_regions = convert_regions(origin_list, world, player)
        doors = convert_key_doors(default_small_key_doors[builder.name], world, player)
        key_layout = build_key_layout(builder, start_regions, doors, world, player)
        valid = validate_key_layout(key_layout, world, player)
        if not valid:
            logging.getLogger('').warning('Vanilla key layout not valid %s', builder.name)
        builder.key_door_proposal = doors
        if player not in world.key_logic.keys():
            world.key_logic[player] = {}
        analyze_dungeon(key_layout, world, player)
        world.key_logic[player][builder.name] = key_layout.key_logic
        log_key_logic(builder.name, key_layout.key_logic)
    if world.shuffle[player] == 'vanilla' and world.accessibility[player] == 'items' and not world.retro[player] and not world.keydropshuffle[player]:
        validate_vanilla_key_logic(world, player)


# some useful functions
oppositemap = {
    Direction.South: Direction.North,
    Direction.North: Direction.South,
    Direction.West: Direction.East,
    Direction.East: Direction.West,
    Direction.Up: Direction.Down,
    Direction.Down: Direction.Up,
}


def switch_dir(direction):
    return oppositemap[direction]


def convert_key_doors(k_doors, world, player):
    result = []
    for d in k_doors:
        if type(d) is tuple:
            result.append((world.get_door(d[0], player), world.get_door(d[1], player)))
        else:
            result.append(world.get_door(d, player))
    return result


def connect_custom(world, player):
    if hasattr(world, 'custom_doors') and world.custom_doors[player]:
        for entrance, ext in world.custom_doors[player]:
            connect_two_way(world, entrance, ext, player)


def connect_simple_door(world, exit_name, region_name, player):
    region = world.get_region(region_name, player)
    world.get_entrance(exit_name, player).connect(region)
    d = world.check_for_door(exit_name, player)
    if d is not None:
        d.dest = region


def connect_door_only(world, exit_name, region, player):
    d = world.check_for_door(exit_name, player)
    if d is not None:
        d.dest = region


def connect_interior_doors(a, b, world, player):
    door_a = world.get_door(a, player)
    door_b = world.get_door(b, player)
    if door_a.blocked:
        connect_one_way(world, b, a, player)
    elif door_b.blocked:
        connect_one_way(world, a, b, player)
    else:
        connect_two_way(world, a, b, player)


def connect_two_way(world, entrancename, exitname, player):
    entrance = world.get_entrance(entrancename, player)
    ext = world.get_entrance(exitname, player)

    # if these were already connected somewhere, remove the backreference
    if entrance.connected_region is not None:
        entrance.connected_region.entrances.remove(entrance)
    if ext.connected_region is not None:
        ext.connected_region.entrances.remove(ext)

    entrance.connect(ext.parent_region)
    ext.connect(entrance.parent_region)
    if entrance.parent_region.dungeon:
        ext.parent_region.dungeon = entrance.parent_region.dungeon
    x = world.check_for_door(entrancename, player)
    y = world.check_for_door(exitname, player)
    if x is not None:
        x.dest = y
    if y is not None:
        y.dest = x


def connect_one_way(world, entrancename, exitname, player):
    entrance = world.get_entrance(entrancename, player)
    ext = world.get_entrance(exitname, player)

    # if these were already connected somewhere, remove the backreference
    if entrance.connected_region is not None:
        entrance.connected_region.entrances.remove(entrance)
    if ext.connected_region is not None:
        ext.connected_region.entrances.remove(ext)

    entrance.connect(ext.parent_region)
    if entrance.parent_region.dungeon:
        ext.parent_region.dungeon = entrance.parent_region.dungeon
    x = world.check_for_door(entrancename, player)
    y = world.check_for_door(exitname, player)
    if x is not None:
        x.dest = y
    if y is not None:
        y.dest = x


def fix_big_key_doors_with_ugly_smalls(world, player):
    remove_ugly_small_key_doors(world, player)
    unpair_big_key_doors(world, player)


def remove_ugly_small_key_doors(world, player):
    for d in ['Eastern Hint Tile Blocked Path SE', 'Eastern Darkness S', 'Thieves Hallway SE', 'Mire Left Bridge S',
              'TR Lava Escape SE', 'GT Hidden Spikes SE']:
        door = world.get_door(d, player)
        room = world.get_room(door.roomIndex, player)
        if not door.entranceFlag:
            room.change(door.doorListPos, DoorKind.Normal)
        door.smallKey = False
        door.ugly = False


def unpair_big_key_doors(world, player):
    problematic_bk_doors = ['Eastern Courtyard N', 'Eastern Big Key NE', 'Thieves BK Corner NE', 'Mire BK Door Room N',
                            'TR Dodgers NE', 'GT Dash Hall NE']
    for paired_door in world.paired_doors[player]:
        if paired_door.door_a in problematic_bk_doors or paired_door.door_b in problematic_bk_doors:
            paired_door.pair = False


def pair_existing_key_doors(world, player, door_a, door_b):
    already_paired = False
    door_names = [door_a.name, door_b.name]
    for pd in world.paired_doors[player]:
        if pd.door_a in door_names and pd.door_b in door_names:
            already_paired = True
            break
    if already_paired:
        return
    for paired_door in world.paired_doors[player]:
        if paired_door.door_a in door_names or paired_door.door_b in door_names:
            paired_door.pair = False
    world.paired_doors[player].append(PairedDoor(door_a, door_b))


def choose_portals(world, player):

    if world.doorShuffle[player] in ['basic', 'crossed']:
        cross_flag = world.doorShuffle[player] == 'crossed'
        bk_shuffle = world.bigkeyshuffle[player]
        # roast incognito doors
        world.get_room(0x60, player).delete(5)
        world.get_room(0x60, player).change(2, DoorKind.DungeonEntrance)
        world.get_room(0x62, player).delete(5)
        world.get_room(0x62, player).change(1, DoorKind.DungeonEntrance)

        info_map = {}
        for dungeon, portal_list in dungeon_portals.items():
            info = DungeonInfo(dungeon)
            region_map = defaultdict(list)
            reachable_portals = []
            inaccessible_portals = []
            for portal in portal_list:
                placeholder = world.get_region(portal + ' Portal', player)
                portal_region = placeholder.exits[0].connected_region
                name = portal_region.name
                if portal_region.type == RegionType.LightWorld:
                    world.get_portal(portal, player).light_world = True
                if name in world.inaccessible_regions[player]:
                    name_key = 'Desert Ledge' if name == 'Desert Palace Entrance (North) Spot' else name
                    region_map[name_key].append(portal)
                    inaccessible_portals.append(portal)
                else:
                    reachable_portals.append(portal)
            info.total = len(portal_list)
            info.required_passage = region_map
            if len(reachable_portals) == 0:
                if len(inaccessible_portals) == 1:
                    info.sole_entrance = inaccessible_portals[0]
                    info.required_passage.clear()
                else:
                    raise Exception('please inspect this case')
            if len(reachable_portals) == 1:
                info.sole_entrance = reachable_portals[0]
            info_map[dungeon] = info

        master_door_list = [x for x in world.doors if x.player == player and x.portalAble]
        portal_assignment = defaultdict(list)
        for dungeon, info in info_map.items():
            outstanding_portals = list(dungeon_portals[dungeon])
            if dungeon == 'Hyrule Castle' and world.mode[player] == 'standard':
                sanc = world.get_portal('Sanctuary', player)
                sanc.destination = True
                clean_up_portal_assignment(portal_assignment, dungeon, sanc, master_door_list, outstanding_portals)
                for target_region, possible_portals in info.required_passage.items():
                    info.required_passage[target_region] = [x for x in possible_portals if x != sanc.name]
                info.required_passage = {x: y for x, y in info.required_passage.items() if len(y) > 0}
            for target_region, possible_portals in info.required_passage.items():
                candidates = find_portal_candidates(master_door_list, dungeon, need_passage=True, crossed=cross_flag,
                                                    bk_shuffle=bk_shuffle)
                choice, portal = assign_portal(candidates, possible_portals, world, player)
                portal.destination = True
                clean_up_portal_assignment(portal_assignment, dungeon, portal, master_door_list, outstanding_portals)
            dead_end_choices = info.total - 1 - len(portal_assignment[dungeon])
            for i in range(0, dead_end_choices):
                candidates = find_portal_candidates(master_door_list, dungeon, dead_end_allowed=True,
                                                    crossed=cross_flag, bk_shuffle=bk_shuffle)
                possible_portals = outstanding_portals if not info.sole_entrance else [x for x in outstanding_portals if x != info.sole_entrance]
                choice, portal = assign_portal(candidates, possible_portals, world, player)
                if choice.deadEnd:
                    portal.deadEnd = True
                clean_up_portal_assignment(portal_assignment, dungeon, portal, master_door_list, outstanding_portals)
            the_rest = info.total - len(portal_assignment[dungeon])
            for i in range(0, the_rest):
                candidates = find_portal_candidates(master_door_list, dungeon, crossed=cross_flag,
                                                    bk_shuffle=bk_shuffle)
                choice, portal = assign_portal(candidates, outstanding_portals, world, player)
                clean_up_portal_assignment(portal_assignment, dungeon, portal, master_door_list, outstanding_portals)

    for portal in world.dungeon_portals[player]:
        connect_portal(portal, world, player)

    hc_south = world.get_door('Hyrule Castle Lobby S', player)
    if not hc_south.entranceFlag:
        world.get_room(0x61, player).delete(6)
        world.get_room(0x61, player).change(4, DoorKind.NormalLow)
    sanctuary_door = world.get_door('Sanctuary S', player)
    if not sanctuary_door.entranceFlag:
        world.get_room(0x12, player).delete(3)
        world.get_room(0x12, player).change(2, DoorKind.NormalLow)
    hera_door = world.get_door('Hera Lobby S', player)
    if not hera_door.entranceFlag:
        world.get_room(0x77, player).change(0, DoorKind.NormalLow2)

    # tr rock bomb entrances
    for portal in world.dungeon_portals[player]:
        if not portal.destination and not portal.deadEnd:
            if portal.door.name == 'TR Lazy Eyes SE':
                world.get_room(0x23, player).change(0, DoorKind.DungeonEntrance)
            if portal.door.name == 'TR Eye Bridge SW':
                world.get_room(0xd5, player).change(0, DoorKind.DungeonEntrance)

    if not world.swamp_patch_required[player]:
        swamp_region = world.get_entrance('Swamp Palace', player).connected_region
        if swamp_region.name != 'Swamp Lobby':
            world.swamp_patch_required[player] = True


def analyze_portals(world, player):
    info_map = {}
    for dungeon, portal_list in dungeon_portals.items():
        info = DungeonInfo(dungeon)
        region_map = defaultdict(list)
        reachable_portals = []
        inaccessible_portals = []
        for portal in portal_list:
            placeholder = world.get_region(portal + ' Portal', player)
            portal_region = placeholder.exits[0].connected_region
            name = portal_region.name
            if portal_region.type == RegionType.LightWorld:
                world.get_portal(portal, player).light_world = True
            if name in world.inaccessible_regions[player]:
                name_key = 'Desert Ledge' if name == 'Desert Palace Entrance (North) Spot' else name
                region_map[name_key].append(portal)
                inaccessible_portals.append(portal)
            else:
                reachable_portals.append(portal)
        info.total = len(portal_list)
        info.required_passage = region_map
        if len(reachable_portals) == 0:
            if len(inaccessible_portals) == 1:
                info.sole_entrance = inaccessible_portals[0]
                info.required_passage.clear()
            else:
                raise Exception('please inspect this case')
        if len(reachable_portals) == 1:
            info.sole_entrance = reachable_portals[0]
        info_map[dungeon] = info

    for dungeon, info in info_map.items():
        if dungeon == 'Hyrule Castle' and world.mode[player] == 'standard':
            sanc = world.get_portal('Sanctuary', player)
            sanc.destination = True
        for target_region, possible_portals in info.required_passage.items():
            if len(possible_portals) == 1:
                world.get_portal(possible_portals[0], player).destination = True
            elif len(possible_portals) > 1:
                dest_portal = random.choice(possible_portals)
                access_portal = world.get_portal(dest_portal, player)
                access_portal.destination = True
                for other_portal in possible_portals:
                    if other_portal != dest_portal:
                        world.get_portal(dest_portal, player).dependent = access_portal


def connect_portal(portal, world, player):
    ent, ext, entrance_name = portal_map[portal.name]
    if world.mode[player] == 'inverted' and portal.name in ['Ganons Tower', 'Agahnims Tower']:
        ext = 'Inverted ' + ext
        # ent = 'Inverted ' + ent
    portal_entrance = world.get_entrance(portal.door.entrance.name, player)  # ensures I get the right one for copying
    target_exit = world.get_entrance(ext, player)
    portal_entrance.connected_region = target_exit.parent_region
    portal_region = world.get_region(portal.name + ' Portal', player)
    portal_region.entrances.append(portal_entrance)
    edit_entrance = world.get_entrance(entrance_name, player)
    edit_entrance.connected_region = portal_entrance.parent_region
    chosen_door = world.get_door(portal_entrance.name, player)
    chosen_door.blocked = False
    connect_door_only(world, chosen_door, portal_region, player)
    portal_entrance.parent_region.entrances.append(edit_entrance)


#  todo: remove this?
def connect_portal_copy(portal, world, player):
    ent, ext, entrance_name = portal_map[portal.name]
    if world.mode[player] == 'inverted' and portal.name in ['Ganons Tower', 'Agahnims Tower']:
        ext = 'Inverted ' + ext
    portal_entrance = world.get_entrance(portal.door.entrance.name, player)  # ensures I get the right one for copying
    target_exit = world.get_entrance(ext, player)
    portal_entrance.connected_region = target_exit.parent_region
    portal_region = world.get_region(portal.name + ' Portal', player)
    portal_region.entrances.append(portal_entrance)
    edit_entrance = world.get_entrance(entrance_name, player)
    edit_entrance.connected_region = portal_entrance.parent_region
    chosen_door = world.get_door(portal_entrance.name, player)
    chosen_door.blocked = False
    connect_door_only(world, chosen_door, portal_region, player)
    portal_entrance.parent_region.entrances.append(edit_entrance)


def find_portal_candidates(door_list, dungeon, need_passage=False, dead_end_allowed=False, crossed=False, bk_shuffle=False):
    filter_list = [x for x in door_list if bk_shuffle or not x.bk_shuffle_req]
    if need_passage:
        if crossed:
            return [x for x in filter_list if x.passage and (x.dungeonLink is None or x.entrance.parent_region.dungeon.name == dungeon)]
        else:
            return [x for x in filter_list if x.passage and x.entrance.parent_region.dungeon.name == dungeon]
    elif dead_end_allowed:
        if crossed:
            return [x for x in filter_list if x.dungeonLink is None or x.entrance.parent_region.dungeon.name == dungeon]
        else:
            return [x for x in filter_list if x.entrance.parent_region.dungeon.name == dungeon]
    else:
        if crossed:
            return [x for x in filter_list if (not x.dungeonLink or x.entrance.parent_region.dungeon.name == dungeon) and not x.deadEnd]
        else:
            return [x for x in filter_list if x.entrance.parent_region.dungeon.name == dungeon and not x.deadEnd]


def assign_portal(candidates, possible_portals, world, player):
    candidate = random.choice(candidates)
    portal_choice = random.choice(possible_portals)
    portal = world.get_portal(portal_choice, player)
    if candidate != portal.door:
        if candidate.entranceFlag:
            for other_portal in world.dungeon_portals[player]:
                if other_portal.door == candidate:
                    other_portal.door = None
                    break
        old_door = portal.door
        if old_door:
            old_door.entranceFlag = False
            if old_door.name not in ['Hyrule Castle Lobby S', 'Sanctuary S', 'Hera Lobby S']:
                old_door_kind = DoorKind.NormalLow if old_door.layer or old_door.pseudo_bg else DoorKind.Normal
                world.get_room(old_door.roomIndex, player).change(old_door.doorListPos, old_door_kind)
        portal.change_door(candidate)
        if candidate.name not in ['Hyrule Castle Lobby S', 'Sanctuary S']:
            new_door_kind = DoorKind.DungeonEntranceLow if candidate.layer or candidate.pseudo_bg else DoorKind.DungeonEntrance
            world.get_room(candidate.roomIndex, player).change(candidate.doorListPos, new_door_kind)
        candidate.entranceFlag = True
    return candidate, portal


def clean_up_portal_assignment(portal_assignment, dungeon, portal, master_door_list, outstanding_portals):
    portal_assignment[dungeon].append(portal)
    master_door_list[:] = [x for x in master_door_list if x.roomIndex != portal.door.roomIndex]
    if portal.door.dungeonLink and portal.door.dungeonLink.startswith('link'):
        match_link = portal.door.dungeonLink
        for door in master_door_list:
            if door.dungeonLink == match_link:
                door.dungeonLink = dungeon
    outstanding_portals.remove(portal.name)


def create_dungeon_entrances(world, player):
    entrance_map = defaultdict(list)
    split_map: DefaultDict[str, DefaultDict[str, List]] = defaultdict(lambda: defaultdict(list))
    originating: DefaultDict[str, DefaultDict[str, Dict]] = defaultdict(lambda: defaultdict(dict))
    for key, portal_list in dungeon_portals.items():
        if key in dungeon_drops.keys():
            entrance_map[key].extend(dungeon_drops[key])
        if key in split_portals.keys():
            dead_ends = []
            destinations = []
            the_rest = []
            for portal_name in portal_list:
                portal = world.get_portal(portal_name, player)
                entrance_map[key].append(portal.door.entrance.parent_region.name)
                if portal.deadEnd:
                    dead_ends.append(portal)
                elif portal.destination:
                    destinations.append(portal)
                else:
                    the_rest.append(portal)
            choices = list(split_portals[key])
            for portal in dead_ends:
                choice = random.choice(choices)
                choices.remove(choice)
                r_name = portal.door.entrance.parent_region.name
                split_map[key][choice].append(r_name)
            for portal in the_rest:
                if len(choices) == 0:
                    choices.append('Extra')
                choice = random.choice(choices)
                p_entrance = portal.door.entrance
                r_name = p_entrance.parent_region.name
                split_map[key][choice].append(r_name)
                entrance_region = find_entrance_region(portal)
                originating[key][choice][entrance_region.name] = None
            dest_choices = [x for x in choices if len(split_map[key][x]) > 0]
            for portal in destinations:
                entrance_region = find_entrance_region(portal)
                restricted = entrance_region.name in world.inaccessible_regions[player]
                if restricted:
                    filtered_choices = [x for x in choices if any(y not in world.inaccessible_regions[player] for y in originating[key][x].keys())]
                else:
                    filtered_choices = dest_choices
                if len(filtered_choices) == 0:
                    raise Exception('No valid destinations')
                choice = random.choice(filtered_choices)
                r_name = portal.door.entrance.parent_region.name
                split_map[key][choice].append(r_name)
        else:
            for portal_name in portal_list:
                portal = world.get_portal(portal_name, player)
                r_name = portal.door.entrance.parent_region.name
                entrance_map[key].append(r_name)
    return entrance_map, split_map


def find_entrance_region(portal):
    for entrance in portal.door.entrance.connected_region.entrances:
        if entrance.parent_region.type != RegionType.Dungeon:
            return entrance.parent_region
    return None


# def unpair_all_doors(world, player):
#     for paired_door in world.paired_doors[player]:
#         paired_door.pair = False

def within_dungeon(world, player):
    fix_big_key_doors_with_ugly_smalls(world, player)
    add_inaccessible_doors(world, player)
    entrances_map, potentials, connections = determine_entrance_list(world, player)
    connections_tuple = (entrances_map, potentials, connections)

    dungeon_builders = {}
    for key in dungeon_regions.keys():
        sector_list = convert_to_sectors(dungeon_regions[key], world, player)
        dungeon_builders[key] = simple_dungeon_builder(key, sector_list)
        dungeon_builders[key].entrance_list = list(entrances_map[key])
    recombinant_builders = {}
    entrances, splits = create_dungeon_entrances(world, player)
    builder_info = entrances, splits, connections_tuple, world, player
    handle_split_dungeons(dungeon_builders, recombinant_builders, entrances_map, builder_info)
    main_dungeon_generation(dungeon_builders, recombinant_builders, connections_tuple, world, player)

    paths = determine_required_paths(world, player)
    check_required_paths(paths, world, player)

    # shuffle_key_doors for dungeons
    logging.getLogger('').info(world.fish.translate("cli", "cli", "shuffling.keydoors"))
    start = time.process_time()
    for builder in world.dungeon_layouts[player].values():
        shuffle_key_doors(builder, world, player)
    logging.getLogger('').info('%s: %s', world.fish.translate("cli", "cli", "keydoor.shuffle.time"), time.process_time()-start)
    smooth_door_pairs(world, player)

    if world.intensity[player] >= 3:
        portal = world.get_portal('Sanctuary', player)
        target = portal.door.entrance.parent_region
        connect_simple_door(world, 'Sanctuary Mirror Route', target, player)

    refine_boss_exits(world, player)


def handle_split_dungeons(dungeon_builders, recombinant_builders, entrances_map, builder_info):
    dungeon_entrances, split_dungeon_entrances, c_tuple, world, player = builder_info
    if dungeon_entrances is None:
        dungeon_entrances = default_dungeon_entrances
    if split_dungeon_entrances is None:
        split_dungeon_entrances = split_region_starts
    builder_info = dungeon_entrances, split_dungeon_entrances, c_tuple, world, player

    for name, split_list in split_dungeon_entrances.items():
        builder = dungeon_builders.pop(name)
        recombinant_builders[name] = builder

        split_builders = split_dungeon_builder(builder, split_list, builder_info)
        dungeon_builders.update(split_builders)
        for sub_name, split_entrances in split_list.items():
            key = name+' '+sub_name
            if key not in dungeon_builders:
                continue
            sub_builder = dungeon_builders[key]
            sub_builder.split_flag = True
            entrance_list = list(split_entrances)
            for ent in entrances_map[name]:
                add_shuffled_entrances(sub_builder.sectors, ent, entrance_list)
            filtered_entrance_list = [x for x in entrance_list if x in entrances_map[name]]
            sub_builder.entrance_list = filtered_entrance_list


def main_dungeon_generation(dungeon_builders, recombinant_builders, connections_tuple, world, player):
    entrances_map, potentials, connections = connections_tuple
    enabled_entrances = {}
    sector_queue = deque(dungeon_builders.values())
    last_key, loops = None, 0
    logging.getLogger('').info(world.fish.translate("cli", "cli", "generating.dungeon"))
    while len(sector_queue) > 0:
        builder = sector_queue.popleft()
        split_dungeon = builder.name.startswith('Desert Palace') or builder.name.startswith('Skull Woods')
        name = builder.name
        if split_dungeon:
            name = ' '.join(builder.name.split(' ')[:-1])
            if len(builder.sectors) == 0:
                del dungeon_builders[builder.name]
                continue
        origin_list = list(builder.entrance_list)
        find_enabled_origins(builder.sectors, enabled_entrances, origin_list, entrances_map, name)
        if len(origin_list) <= 0 or not pre_validate(builder, origin_list, split_dungeon, world, player):
            if last_key == builder.name or loops > 1000:
                origin_name = world.get_region(origin_list[0], player).entrances[0].parent_region.name if len(origin_list) > 0 else 'no origin'
                raise Exception('Infinite loop detected for "%s" located at %s' % (builder.name, origin_name))
            sector_queue.append(builder)
            last_key = builder.name
            loops += 1
        else:
            ds = generate_dungeon(builder, origin_list, split_dungeon, world, player)
            find_new_entrances(ds, entrances_map, connections, potentials, enabled_entrances, world, player)
            ds.name = name
            builder.master_sector = ds
            builder.layout_starts = origin_list if len(builder.entrance_list) <= 0 else builder.entrance_list
            last_key = None
    combine_layouts(recombinant_builders, dungeon_builders, entrances_map)
    world.dungeon_layouts[player] = {}
    for builder in dungeon_builders.values():
        builder.entrance_list = builder.layout_starts = builder.path_entrances = find_accessible_entrances(world, player, builder)
    world.dungeon_layouts[player] = dungeon_builders


def determine_entrance_list_vanilla(world, player):
    entrance_map = {}
    potential_entrances = {}
    connections = {}
    for key, r_names in region_starts.items():
        entrance_map[key] = []
        if world.mode[player] == 'standard' and key in standard_starts.keys():
            r_names = ['Hyrule Castle Lobby']
        for region_name in r_names:
            region = world.get_region(region_name, player)
            for ent in region.entrances:
                parent = ent.parent_region
                if (parent.type != RegionType.Dungeon and parent.name != 'Menu') or parent.name == 'Sewer Drop':
                    if parent.name not in world.inaccessible_regions[player]:
                        entrance_map[key].append(region_name)
                    else:
                        if ent.parent_region not in potential_entrances.keys():
                            potential_entrances[parent] = []
                        potential_entrances[parent].append(region_name)
                        connections[region_name] = parent
    return entrance_map, potential_entrances, connections


def determine_entrance_list(world, player):
    entrance_map = {}
    potential_entrances = {}
    connections = {}
    for key, portal_list in dungeon_portals.items():
        entrance_map[key] = []
        r_names = {}
        if key in dungeon_drops.keys():
            for drop in dungeon_drops[key]:
                r_names[drop] = None
        for portal_name in portal_list:
            portal = world.get_portal(portal_name, player)
            r_names[portal.door.entrance.parent_region.name] = portal
        for region_name, portal in r_names.items():
            if portal:
                region = world.get_region(portal.name + ' Portal', player)
            else:
                region = world.get_region(region_name, player)
            for ent in region.entrances:
                parent = ent.parent_region
                if (parent.type != RegionType.Dungeon and parent.name != 'Menu') or parent.name == 'Sewer Drop':
                    std_inaccessible = is_standard_inaccessible(key, portal, world, player)
                    if parent.name not in world.inaccessible_regions[player] and not std_inaccessible:
                        entrance_map[key].append(region_name)
                    else:
                        if parent not in potential_entrances.keys():
                            potential_entrances[parent] = []
                        if region_name not in potential_entrances[parent]:
                            potential_entrances[parent].append(region_name)
                        connections[region_name] = parent
    return entrance_map, potential_entrances, connections


def is_standard_inaccessible(key, portal, world, player):
    return world.mode[player] == 'standard' and key in standard_starts and (not portal or portal.name not in standard_starts[key])


def add_shuffled_entrances(sectors, region_list, entrance_list):
    for sector in sectors:
        for region in sector.regions:
            if region.name in region_list and region.name not in entrance_list:
                entrance_list.append(region.name)


def find_enabled_origins(sectors, enabled, entrance_list, entrance_map, key):
    for sector in sectors:
        for region in sector.regions:
            if region.name in enabled.keys() and region.name not in entrance_list:
                entrance_list.append(region.name)
                origin_reg, origin_dungeon = enabled[region.name]
                if origin_reg != region.name and origin_dungeon != region.dungeon:
                    if key not in entrance_map.keys():
                        key = ' '.join(key.split(' ')[:-1])
                    entrance_map[key].append(region.name)


def find_new_entrances(sector, entrances_map, connections, potentials, enabled, world, player):
    for region in sector.regions:
        if region.name in connections.keys() and (connections[region.name] in potentials.keys() or connections[region.name].name in world.inaccessible_regions[player]):
            enable_new_entrances(region, connections, potentials, enabled, world, player, region)
    inverted_aga_check(entrances_map, connections, potentials, enabled, world, player)


def enable_new_entrances(region, connections, potentials, enabled, world, player, region_enabler):
    new_region = connections[region.name]
    if new_region in potentials.keys():
        for potential in potentials.pop(new_region):
            enabled[potential] = (region_enabler.name, region_enabler.dungeon)
    # see if this unexplored region connects elsewhere
    queue = deque(new_region.exits)
    visited = set()
    while len(queue) > 0:
        ext = queue.popleft()
        visited.add(ext)
        region_name = ext.connected_region.name
        if region_name in connections.keys() and connections[region_name] in potentials.keys():
            for potential in potentials.pop(connections[region_name]):
                enabled[potential] = (region.name, region.dungeon)
        if ext.connected_region.name in world.inaccessible_regions[player] or ext.connected_region.name.endswith(' Portal'):
            for new_exit in ext.connected_region.exits:
                if new_exit not in visited:
                    queue.append(new_exit)


def inverted_aga_check(entrances_map, connections, potentials, enabled, world, player):
    if world.mode[player] == 'inverted':
        if 'Agahnims Tower' in entrances_map.keys() or aga_tower_enabled(enabled):
            for region in list(potentials.keys()):
                if region.name == 'Hyrule Castle Ledge':
                    enabler = world.get_region('Tower Agahnim 1', player)
                    for r_name in potentials[region]:
                        new_region = world.get_region(r_name, player)
                        enable_new_entrances(new_region, connections, potentials, enabled, world, player, enabler)


def aga_tower_enabled(enabled):
    for region_name, enabled_tuple in enabled.items():
        entrance, dungeon = enabled_tuple
        if dungeon.name == 'Agahnims Tower':
            return True
    return False


# goals:
# 1. have enough chests to be interesting (2 more than dungeon items)
# 2. have a balanced amount of regions added (check)
# 3. prevent soft locks due to key usage (algorithm written)
# 4. rules in place to affect item placement (lamp, keys, etc. -- in rules)
# 5. to be complete -- all doors linked (check, somewhat)
# 6. avoid deadlocks/dead end dungeon (check)
# 7. certain paths through dungeon must be possible - be able to reach goals (check)


def cross_dungeon(world, player):
    fix_big_key_doors_with_ugly_smalls(world, player)
    add_inaccessible_doors(world, player)
    entrances_map, potentials, connections = determine_entrance_list(world, player)
    connections_tuple = (entrances_map, potentials, connections)

    all_sectors, all_regions = [], []
    for key in dungeon_regions.keys():
        all_regions += dungeon_regions[key]
    all_sectors.extend(convert_to_sectors(all_regions, world, player))
    merge_sectors(all_sectors, world, player)
    entrances, splits = create_dungeon_entrances(world, player)
    dungeon_builders = create_dungeon_builders(all_sectors, connections_tuple, world, player, entrances, splits)
    for builder in dungeon_builders.values():
        builder.entrance_list = list(entrances_map[builder.name])
        dungeon_obj = world.get_dungeon(builder.name, player)
        for sector in builder.sectors:
            for region in sector.regions:
                region.dungeon = dungeon_obj
                for loc in region.locations:
                    if loc.forced_item:
                        key_name = dungeon_keys[builder.name] if loc.name != 'Hyrule Castle - Big Key Drop' else dungeon_bigs[builder.name]
                        loc.forced_item = loc.item = ItemFactory(key_name, player)
    recombinant_builders = {}
    builder_info = entrances, splits, connections_tuple, world, player
    handle_split_dungeons(dungeon_builders, recombinant_builders, entrances_map, builder_info)

    main_dungeon_generation(dungeon_builders, recombinant_builders, connections_tuple, world, player)

    paths = determine_required_paths(world, player)
    check_required_paths(paths, world, player)

    hc = world.get_dungeon('Hyrule Castle', player)
    hc.dungeon_items.append(ItemFactory('Compass (Escape)', player))
    at = world.get_dungeon('Agahnims Tower', player)
    at.dungeon_items.append(ItemFactory('Compass (Agahnims Tower)', player))
    at.dungeon_items.append(ItemFactory('Map (Agahnims Tower)', player))

    assign_cross_keys(dungeon_builders, world, player)
    all_dungeon_items_cnt = len(list(y for x in world.dungeons if x.player == player for y in x.all_items))
    if world.keydropshuffle[player]:
        target_items = 35 if world.retro[player] else 96
    else:
        target_items = 34 if world.retro[player] else 63
    d_items = target_items - all_dungeon_items_cnt
    world.pool_adjustment[player] = d_items
    smooth_door_pairs(world, player)

    # Re-assign dungeon bosses
    gt = world.get_dungeon('Ganons Tower', player)
    for name, builder in dungeon_builders.items():
        reassign_boss('GT Ice Armos', 'bottom', builder, gt, world, player)
        reassign_boss('GT Lanmolas 2', 'middle', builder, gt, world, player)
        reassign_boss('GT Moldorm', 'top', builder, gt, world, player)

    sanctuary = world.get_region('Sanctuary', player)
    d_name = sanctuary.dungeon.name
    if d_name != 'Hyrule Castle':
        possible_portals = []
        for portal_name in dungeon_portals[d_name]:
            portal = world.get_portal(portal_name, player)
            if portal.door.name == 'Sanctuary S':
                possible_portals.clear()
                possible_portals.append(portal)
                break
            if not portal.destination and not portal.deadEnd:
                possible_portals.append(portal)
        if len(possible_portals) == 1:
            world.sanc_portal[player] = possible_portals[0]
        else:
            reachable_portals = []
            for portal in possible_portals:
                start_area = portal.door.entrance.parent_region
                state = ExplorationState(dungeon=d_name)
                state.visit_region(start_area)
                state.add_all_doors_check_unattached(start_area, world, player)
                explore_state(state, world, player)
                if state.visited_at_all(sanctuary):
                    reachable_portals.append(portal)
            world.sanc_portal[player] = random.choice(reachable_portals)
    if world.intensity[player] >= 3:
        if player in world.sanc_portal:
            portal = world.sanc_portal[player]
        else:
            portal = world.get_portal('Sanctuary', player)
        target = portal.door.entrance.parent_region
        connect_simple_door(world, 'Sanctuary Mirror Route', target, player)

    check_entrance_fixes(world, player)

    if world.standardize_palettes[player] == 'standardize':
        palette_assignment(world, player)

    refine_hints(dungeon_builders)
    refine_boss_exits(world, player)


def assign_cross_keys(dungeon_builders, world, player):
    logging.getLogger('').info(world.fish.translate("cli", "cli", "shuffling.keydoors"))
    start = time.process_time()
    if world.retro[player]:
        remaining = 61 if world.keydropshuffle[player] else 29
    else:
        remaining = len(list(x for dgn in world.dungeons if dgn.player == player for x in dgn.small_keys))
    total_keys = remaining
    total_candidates = 0
    start_regions_map = {}
    # Step 1: Find Small Key Door Candidates
    for name, builder in dungeon_builders.items():
        dungeon = world.get_dungeon(name, player)
        if not builder.bk_required or builder.bk_provided:
            dungeon.big_key = None
        elif builder.bk_required and not builder.bk_provided:
            dungeon.big_key = ItemFactory(dungeon_bigs[name], player)
        start_regions = convert_regions(builder.path_entrances, world, player)
        find_small_key_door_candidates(builder, start_regions, world, player)
        builder.key_doors_num = max(0, len(builder.candidates) - builder.key_drop_cnt)
        total_candidates += builder.key_doors_num
        start_regions_map[name] = start_regions


    # Step 2: Initial Key Number Assignment & Calculate Flexibility
    for name, builder in dungeon_builders.items():
        calculated = int(round(builder.key_doors_num*total_keys/total_candidates))
        max_keys = builder.location_cnt - calc_used_dungeon_items(builder)
        cand_len = max(0, len(builder.candidates) - builder.key_drop_cnt)
        limit = min(max_keys, cand_len)
        suggested = min(calculated, limit)
        combo_size = ncr(len(builder.candidates), suggested + builder.key_drop_cnt)
        while combo_size > 500000 and suggested > 0:
            suggested -= 1
            combo_size = ncr(len(builder.candidates), suggested + builder.key_drop_cnt)
        builder.key_doors_num = suggested + builder.key_drop_cnt
        remaining -= suggested
        builder.combo_size = combo_size
        if suggested < limit:
            builder.flex = limit - suggested

    # Step 3: Initial valid combination find - reduce flex if needed
    for name, builder in dungeon_builders.items():
        suggested = builder.key_doors_num - builder.key_drop_cnt
        find_valid_combination(builder, start_regions_map[name], world, player)
        actual_chest_keys = builder.key_doors_num - builder.key_drop_cnt
        if actual_chest_keys < suggested:
            remaining += suggested - actual_chest_keys
            builder.flex = 0

    # Step 4: Try to assign remaining keys
    builder_order = [x for x in dungeon_builders.values() if x.flex > 0]
    builder_order.sort(key=lambda b: b.combo_size)
    queue = deque(builder_order)
    logger = logging.getLogger('')
    while len(queue) > 0 and remaining > 0:
        builder = queue.popleft()
        name = builder.name
        logger.debug('Cross Dungeon: Increasing key count by 1 for %s', name)
        builder.key_doors_num += 1
        result = find_valid_combination(builder, start_regions_map[name], world, player, drop_keys=False)
        if result:
            remaining -= 1
            builder.flex -= 1
            if builder.flex > 0:
                builder.combo_size = ncr(len(builder.candidates), builder.key_doors_num)
                queue.append(builder)
                queue = deque(sorted(queue, key=lambda b: b.combo_size))
        else:
            logger.debug('Cross Dungeon: Increase failed for %s', name)
            builder.key_doors_num -= 1
            builder.flex = 0
    logger.debug('Cross Dungeon: Keys unable to assign in pool %s', remaining)

    # Last Step: Adjust Small Key Dungeon Pool
    if not world.retro[player]:
        for name, builder in dungeon_builders.items():
            reassign_key_doors(builder, world, player)
            log_key_logic(builder.name, world.key_logic[player][builder.name])
            actual_chest_keys = max(builder.key_doors_num - builder.key_drop_cnt, 0)
            dungeon = world.get_dungeon(name, player)
            if actual_chest_keys == 0:
                dungeon.small_keys = []
            else:
                dungeon.small_keys = [ItemFactory(dungeon_keys[name], player)] * actual_chest_keys
    logger.info(f'{world.fish.translate("cli", "cli", "keydoor.shuffle.time.crossed")}: {time.process_time()-start}')


def reassign_boss(boss_region, boss_key, builder, gt, world, player):
    if boss_region in builder.master_sector.region_set():
        new_dungeon = world.get_dungeon(builder.name, player)
        if new_dungeon != gt:
            gt_boss = gt.bosses.pop(boss_key)
            new_dungeon.bosses[boss_key] = gt_boss


def check_entrance_fixes(world, player):
    # I believe these modes will be fine
    if world.shuffle[player] not in ['insanity', 'insanity_legacy', 'madness_legacy']:
        checks = {
            'Palace of Darkness': 'pod',
            'Skull Woods Final Section': 'sw',
            'Turtle Rock': 'tr',
            'Ganons Tower': 'gt',
        }
        if world.mode[player] == 'inverted':
            del checks['Ganons Tower']
        for ent_name, key in checks.items():
            entrance = world.get_entrance(ent_name, player)
            dungeon = entrance.connected_region.dungeon
            if dungeon:
                layout = world.dungeon_layouts[player][dungeon.name]
                if 'Sanctuary' in layout.master_sector.region_set() or dungeon.name in ['Hyrule Castle', 'Desert Palace', 'Skull Woods', 'Turtle Rock']:
                    portal = None
                    for portal_name in dungeon_portals[dungeon.name]:
                        test_portal = world.get_portal(portal_name, player)
                        if entrance.connected_region == test_portal.door.entrance.connected_region:
                            portal = test_portal
                            break
                    world.force_fix[player][key] = portal


def palette_assignment(world, player):
    for portal in world.dungeon_portals[player]:
        if portal.door.roomIndex >= 0:
            room = world.get_room(portal.door.roomIndex, player)
            if room.palette is None:
                name = portal.door.entrance.parent_region.dungeon.name
                room.palette = palette_map[name][0]

    for name, builder in world.dungeon_layouts[player].items():
        for region in builder.master_sector.regions:
            for ext in region.exits:
                if ext.door and ext.door.roomIndex >= 0 and ext.door.name not in palette_non_influencers:
                    room = world.get_room(ext.door.roomIndex, player)
                    if room.palette is None:
                        room.palette = palette_map[name][0]

    for name, tuple in palette_map.items():
        if tuple[1] is not None:
            door_name = boss_indicator[name][1]
            door = world.get_door(door_name, player)
            room = world.get_room(door.roomIndex, player)
            room.palette = tuple[1]
            if tuple[2]:
                leading_door = world.get_door(tuple[2], player)
                ent = next(iter(leading_door.entrance.parent_region.entrances))
                if ent.door and door.roomIndex:
                    room = world.get_room(door.roomIndex, player)
                    room.palette = tuple[1]


    rat_path = world.get_region('Sewers Rat Path', player)
    visited_rooms = set()
    visited_regions = {rat_path}
    queue = deque([(rat_path, 0)])
    while len(queue) > 0:
        region, dist = queue.popleft()
        if dist > 5:
            continue
        for ext in region.exits:
            if ext.door and ext.door.roomIndex >= 0 and ext.door.name not in palette_non_influencers:
                room_idx = ext.door.roomIndex
                if room_idx not in visited_rooms:
                    room = world.get_room(room_idx, player)
                    room.palette = 0x1
                    visited_rooms.add(room_idx)
            if ext.door and ext.door.type in [DoorType.SpiralStairs, DoorType.Ladder]:
                if ext.door.dest and ext.door.dest.roomIndex:
                    visited_rooms.add(ext.door.dest.roomIndex)
                    if ext.connected_region:
                        visited_regions.add(ext.connected_region)
            elif ext.connected_region and ext.connected_region.type == RegionType.Dungeon and ext.connected_region not in visited_regions:
                queue.append((ext.connected_region, dist+1))
                visited_regions.add(ext.connected_region)

    sanc = world.get_region('Sanctuary', player)
    if sanc.dungeon.name == 'Hyrule Castle':
        room = world.get_room(0x12, player)
        room.palette = 0x1d
    for connection in ['Sanctuary S', 'Sanctuary N']:
        adjacent = world.get_entrance(connection, player)
        adj_dest = adjacent.door.dest
        if adj_dest and isinstance(adj_dest, Door) and adj_dest.entrance.parent_region.type == RegionType.Dungeon:
            if adjacent.door and adjacent.door.dest and adjacent.door.dest.roomIndex >= 0:
                room = world.get_room(adjacent.door.dest.roomIndex, player)
                room.palette = 0x1d

    eastfairies = world.get_room(0x89, player)
    eastfairies.palette = palette_map[world.get_region('Eastern Courtyard', player).dungeon.name][0]
    # other ones that could use programmatic treatment:  Skull Boss x29, Hera Fairies xa7, Ice Boss xde (Ice Fairies!)


def refine_hints(dungeon_builders):
    for name, builder in dungeon_builders.items():
        for region in builder.master_sector.regions:
            for location in region.locations:
                if not location.event and '- Boss' not in location.name and '- Prize' not in location.name and location.name != 'Sanctuary':
                    location.hint_text = dungeon_hints[name]


def refine_boss_exits(world, player):
    for d_name, d_boss in {'Desert Palace': 'Desert Boss',
                           'Skull Woods': 'Skull Boss',
                           'Turtle Rock': 'TR Boss'}.items():
        possible_portals = []
        current_boss = None
        for portal_name in dungeon_portals[d_name]:
            portal = world.get_portal(portal_name, player)
            if not portal.destination:
                possible_portals.append(portal)
            if portal.boss_exit_idx > -1:
                current_boss = portal
        if len(possible_portals) == 1:
            if possible_portals[0] != current_boss:
                possible_portals[0].change_boss_exit(current_boss.boss_exit_idx)
                current_boss.change_boss_exit(-1)
        else:
            reachable_portals = []
            for portal in possible_portals:
                start_area = portal.door.entrance.parent_region
                state = ExplorationState(dungeon=d_name)
                state.visit_region(start_area)
                state.add_all_doors_check_unattached(start_area, world, player)
                explore_state_not_inaccessible(state, world, player)
                if state.visited_at_all(world.get_region(d_boss, player)):
                    reachable_portals.append(portal)
            if len(reachable_portals) == 0:
                reachable_portals = possible_portals
            unreachable = world.inaccessible_regions[player]
            filtered = [x for x in reachable_portals if x.door.entrance.connected_region.name not in unreachable]
            if 0 < len(filtered) < len(reachable_portals):
                reachable_portals = filtered
            chosen_one = random.choice(reachable_portals) if len(reachable_portals) > 1 else reachable_portals[0]
            if chosen_one != current_boss:
                chosen_one.change_boss_exit(current_boss.boss_exit_idx)
                current_boss.change_boss_exit(-1)


def convert_to_sectors(region_names, world, player):
    region_list = convert_regions(region_names, world, player)
    sectors = []
    while len(region_list) > 0:
        region = region_list.pop()
        new_sector = True
        region_chunk = [region]
        exits = []
        exits.extend(region.exits)
        outstanding_doors = []
        matching_sectors = []
        while len(exits) > 0:
            ext = exits.pop()
            door = ext.door
            if ext.connected_region is not None or door is not None and door.controller is not None:
                if door is not None and door.controller is not None:
                    connect_region = world.get_entrance(door.controller.name, player).parent_region
                else:
                    connect_region = ext.connected_region
                if connect_region not in region_chunk and connect_region in region_list:
                    region_list.remove(connect_region)
                    region_chunk.append(connect_region)
                    exits.extend(connect_region.exits)
                if connect_region not in region_chunk:
                    for existing in sectors:
                        if connect_region in existing.regions:
                            new_sector = False
                            if existing not in matching_sectors:
                                matching_sectors.append(existing)
            else:
                if door and not door.controller and not door.dest and not door.entranceFlag and door.type != DoorType.Logical:
                    outstanding_doors.append(door)
        sector = Sector()
        if not new_sector:
            for match in matching_sectors:
                sector.regions.extend(match.regions)
                sector.outstanding_doors.extend(match.outstanding_doors)
                sectors.remove(match)
        sector.regions.extend(region_chunk)
        sector.outstanding_doors.extend(outstanding_doors)
        sectors.append(sector)
    return sectors


def merge_sectors(all_sectors, world, player):
    if world.mixed_travel[player] == 'force':
        sectors_to_remove = {}
        merge_sectors = {}
        for sector in all_sectors:
            r_set = sector.region_set()
            if 'PoD Arena Ledge' in r_set:
                sectors_to_remove['Arenahover'] = sector
            elif 'PoD Big Chest Balcony' in r_set:
                sectors_to_remove['Hammerjump'] = sector
            elif 'Mire Chest View' in r_set:
                sectors_to_remove['Mire BJ'] = sector
            elif 'PoD Falling Bridge Ledge' in r_set:
                merge_sectors['Hammerjump'] = sector
            elif 'PoD Arena Bridge' in r_set:
                merge_sectors['Arenahover'] = sector
            elif 'Mire BK Chest Ledge' in r_set:
                merge_sectors['Mire BJ'] = sector
        for key, old_sector in sectors_to_remove.items():
            merge_sectors[key].regions.extend(old_sector.regions)
            merge_sectors[key].outstanding_doors.extend(old_sector.outstanding_doors)
            all_sectors.remove(old_sector)


# those with split region starts like Desert/Skull combine for key layouts
def combine_layouts(recombinant_builders, dungeon_builders, entrances_map):
    for recombine in recombinant_builders.values():
        queue = deque(dungeon_builders.values())
        while len(queue) > 0:
            builder = queue.pop()
            if builder.name.startswith(recombine.name):
                del dungeon_builders[builder.name]
                if recombine.master_sector is None:
                    recombine.master_sector = builder.master_sector
                    recombine.master_sector.name = recombine.name
                    recombine.pre_open_stonewall = builder.pre_open_stonewall
                else:
                    recombine.master_sector.regions.extend(builder.master_sector.regions)
                    if builder.pre_open_stonewall:
                        recombine.pre_open_stonewall = builder.pre_open_stonewall
        recombine.layout_starts = list(entrances_map[recombine.name])
        dungeon_builders[recombine.name] = recombine


def valid_region_to_explore(region, world, player):
    return region and (region.type == RegionType.Dungeon
                       or region.name in world.inaccessible_regions[player]
                       or (region.name == 'Hyrule Castle Ledge' and world.mode[player] == 'standard'))


def shuffle_key_doors(builder, world, player):
    start_regions = convert_regions(builder.path_entrances, world, player)
    # count number of key doors - this could be a table?
    num_key_doors = 0
    skips = []
    for region in builder.master_sector.regions:
        for ext in region.exits:
            d = world.check_for_door(ext.name, player)
            if d is not None and d.smallKey:
                if d not in skips:
                    if d.type == DoorType.Interior:
                        skips.append(d.dest)
                    if d.type == DoorType.Normal:
                        for dp in world.paired_doors[player]:
                            if d.name == dp.door_a:
                                skips.append(world.get_door(dp.door_b, player))
                                break
                            elif d.name == dp.door_b:
                                skips.append(world.get_door(dp.door_a, player))
                                break
                    num_key_doors += 1
    builder.key_doors_num = num_key_doors
    find_small_key_door_candidates(builder, start_regions, world, player)
    find_valid_combination(builder, start_regions, world, player)
    reassign_key_doors(builder, world, player)
    log_key_logic(builder.name, world.key_logic[player][builder.name])


def find_current_key_doors(builder):
    current_doors = []
    for region in builder.master_sector.regions:
        for ext in region.exits:
            d = ext.door
            if d and d.smallKey:
                current_doors.append(d)
    return current_doors


def find_small_key_door_candidates(builder, start_regions, world, player):
    # traverse dungeon and find candidates
    candidates = []
    checked_doors = set()
    for region in start_regions:
        possible, checked = find_key_door_candidates(region, checked_doors, world, player)
        candidates.extend([x for x in possible if x not in candidates])
        checked_doors.update(checked)
    flat_candidates = []
    for candidate in candidates:
        # not valid if: Normal and Pair in is Checked and Pair is not in Candidates
        if candidate.type != DoorType.Normal or candidate.dest not in checked_doors or candidate.dest in candidates:
            flat_candidates.append(candidate)

    paired_candidates = build_pair_list(flat_candidates)
    builder.candidates = paired_candidates


def calc_used_dungeon_items(builder):
    base = 4
    if builder.bk_required and not builder.bk_provided:
        base += 1
    # if builder.name == 'Hyrule Castle':
    #     base -= 1  # Missing compass/map
    # if builder.name == 'Agahnims Tower':
    #     base -= 2  # Missing both compass/map
    # gt can lose map once compasses work
    return base


def find_valid_combination(builder, start_regions, world, player, drop_keys=True):
    logger = logging.getLogger('')
    # find valid combination of candidates
    if len(builder.candidates) < builder.key_doors_num:
        if not drop_keys:
            logger.info('No valid layouts for %s with %s doors', builder.name, builder.key_doors_num)
            return False
        builder.key_doors_num = len(builder.candidates)  # reduce number of key doors
        logger.info('%s: %s', world.fish.translate("cli","cli","lowering.keys.candidates"), builder.name)
    combinations = ncr(len(builder.candidates), builder.key_doors_num)
    itr = 0
    start = time.process_time()
    sample_list = list(range(0, int(combinations)))
    random.shuffle(sample_list)
    proposal = kth_combination(sample_list[itr], builder.candidates, builder.key_doors_num)

    key_layout = build_key_layout(builder, start_regions, proposal, world, player)
    while not validate_key_layout(key_layout, world, player):
        itr += 1
        stop_early = False
        if itr % 1000 == 0:
            mark = time.process_time()-start
            if (mark > 10 and itr*100/combinations > 50) or (mark > 20 and itr*100/combinations > 25) or mark > 30:
                stop_early = True
        if itr >= combinations or stop_early:
            if not drop_keys:
                logger.info('No valid layouts for %s with %s doors', builder.name, builder.key_doors_num)
                return False
            logger.info('%s: %s', world.fish.translate("cli","cli","lowering.keys.layouts"), builder.name)
            builder.key_doors_num -= 1
            if builder.key_doors_num < 0:
                raise Exception('Bad dungeon %s - 0 key doors not valid' % builder.name)
            combinations = ncr(len(builder.candidates), builder.key_doors_num)
            sample_list = list(range(0, int(combinations)))
            random.shuffle(sample_list)
            itr = 0
            start = time.process_time()  # reset time since itr reset
        proposal = kth_combination(sample_list[itr], builder.candidates, builder.key_doors_num)
        key_layout.reset(proposal, builder, world, player)
        if (itr+1) % 1000 == 0:
            mark = time.process_time()-start
            logger.info('%s time elapsed. %s iterations/s', mark, itr/mark)
    # make changes
    if player not in world.key_logic.keys():
        world.key_logic[player] = {}
    analyze_dungeon(key_layout, world, player)
    builder.key_door_proposal = proposal
    world.key_logic[player][builder.name] = key_layout.key_logic
    world.key_layout[player][builder.name] = key_layout
    return True


def log_key_logic(d_name, key_logic):
    logger = logging.getLogger('')
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug('Key Logic for %s', d_name)
        if len(key_logic.bk_restricted) > 0:
            logger.debug('-BK Restrictions')
            for restriction in key_logic.bk_restricted:
                logger.debug(restriction)
        if len(key_logic.sm_restricted) > 0:
            logger.debug('-Small Restrictions')
            for restriction in key_logic.sm_restricted:
                logger.debug(restriction)
        for key in key_logic.door_rules.keys():
            rule = key_logic.door_rules[key]
            logger.debug('--Rule for %s: Nrm:%s Allow:%s Loc:%s Alt:%s', key, rule.small_key_num, rule.allow_small, rule.small_location, rule.alternate_small_key)
            if rule.alternate_small_key is not None:
                for loc in rule.alternate_big_key_loc:
                    logger.debug('---BK Loc %s', loc.name)
        logger.debug('Placement rules for %s', d_name)
        for rule in key_logic.placement_rules:
            logger.debug('*Rule for %s:', rule.door_reference)
            if rule.bk_conditional_set:
                logger.debug('**BK Checks %s', ','.join([x.name for x in rule.bk_conditional_set]))
                logger.debug('**BK Blocked (%s) : %s', rule.needed_keys_wo_bk, ','.join([x.name for x in rule.check_locations_wo_bk]))
            if rule.needed_keys_w_bk:
                logger.debug('**BK Available (%s) : %s', rule.needed_keys_w_bk, ','.join([x.name for x in rule.check_locations_w_bk]))


def build_pair_list(flat_list):
    paired_list = []
    queue = deque(flat_list)
    while len(queue) > 0:
        d = queue.pop()
        if d.dest in queue and d.type != DoorType.SpiralStairs:
            paired_list.append((d, d.dest))
            queue.remove(d.dest)
        else:
            paired_list.append(d)
    return paired_list


def flatten_pair_list(paired_list):
    flat_list = []
    for d in paired_list:
        if type(d) is tuple:
            flat_list.append(d[0])
            flat_list.append(d[1])
        else:
            flat_list.append(d)
    return flat_list


okay_normals = [DoorKind.Normal, DoorKind.SmallKey, DoorKind.Bombable, DoorKind.Dashable, DoorKind.DungeonChanger]


def find_key_door_candidates(region, checked, world, player):
    dungeon = region.dungeon
    candidates = []
    checked_doors = list(checked)
    queue = deque([(region, None, None)])
    while len(queue) > 0:
        current, last_door, last_region = queue.pop()
        for ext in current.exits:
            d = ext.door
            if d and d.controller:
                d = d.controller
            if d and not d.blocked and not d.entranceFlag and d.dest is not last_door and d.dest is not last_region and d not in checked_doors:
                valid = False
                if 0 <= d.doorListPos < 4 and d.type in [DoorType.Interior, DoorType.Normal, DoorType.SpiralStairs]:
                    room = world.get_room(d.roomIndex, player)
                    position, kind = room.doorList[d.doorListPos]

                    if d.type == DoorType.Interior:
                        valid = kind in [DoorKind.Normal, DoorKind.SmallKey, DoorKind.Bombable, DoorKind.Dashable]
                    elif d.type == DoorType.SpiralStairs:
                        valid = kind in [DoorKind.StairKey, DoorKind.StairKey2, DoorKind.StairKeyLow]
                    elif d.type == DoorType.Normal:
                        d2 = d.dest
                        if d2 not in candidates:
                            if d2.type == DoorType.Normal:
                                room_b = world.get_room(d2.roomIndex, player)
                                pos_b, kind_b = room_b.doorList[d2.doorListPos]
                                valid = kind in okay_normals and kind_b in okay_normals
                            else:
                                valid = kind in okay_normals
                            if valid and 0 <= d2.doorListPos < 4:
                                candidates.append(d2)
                        else:
                            valid = True
                if valid and d not in candidates:
                    candidates.append(d)
                connected = ext.connected_region
                if connected and (connected.type != RegionType.Dungeon or connected.dungeon == dungeon):
                    queue.append((ext.connected_region, d, current))
                if d is not None:
                    checked_doors.append(d)
    return candidates, checked_doors


def kth_combination(k, l, r):
    if r == 0:
        return []
    elif len(l) == r:
        return l
    else:
        i = ncr(len(l)-1, r-1)
        if k < i:
            return l[0:1] + kth_combination(k, l[1:], r-1)
        else:
            return kth_combination(k-i, l[1:], r)


def ncr(n, r):
    if r == 0:
        return 1
    r = min(r, n-r)
    numerator = reduce(op.mul, range(n, n-r, -1), 1)
    denominator = reduce(op.mul, range(1, r+1), 1)
    return numerator / denominator


def reassign_key_doors(builder, world, player):
    logger = logging.getLogger('')
    logger.debug('Key doors for %s', builder.name)
    proposal = builder.key_door_proposal
    flat_proposal = flatten_pair_list(proposal)
    queue = deque(find_current_key_doors(builder))
    while len(queue) > 0:
        d = queue.pop()
        if d.type is DoorType.SpiralStairs and d not in proposal:
            room = world.get_room(d.roomIndex, player)
            if room.doorList[d.doorListPos][1] == DoorKind.StairKeyLow:
                room.delete(d.doorListPos)
            else:
                if len(room.doorList) > 1:
                    room.mirror(d.doorListPos)  # I think this works for crossed now
                else:
                    room.delete(d.doorListPos)
            d.smallKey = False
        elif d.type is DoorType.Interior and d not in flat_proposal and d.dest not in flat_proposal and not d.entranceFlag:
            world.get_room(d.roomIndex, player).change(d.doorListPos, DoorKind.Normal)
            d.smallKey = False
            d.dest.smallKey = False
            queue.remove(d.dest)
        elif d.type is DoorType.Normal and d not in flat_proposal and not d.entranceFlag:
            world.get_room(d.roomIndex, player).change(d.doorListPos, DoorKind.Normal)
            d.smallKey = False
            for dp in world.paired_doors[player]:
                if dp.door_a == d.name or dp.door_b == d.name:
                    dp.pair = False
    for obj in proposal:
        if type(obj) is tuple:
            d1 = obj[0]
            d2 = obj[1]
            if d1.type is DoorType.Interior:
                change_door_to_small_key(d1, world, player)
                d2.smallKey = True  # ensure flag is set
            else:
                names = [d1.name, d2.name]
                found = False
                for dp in world.paired_doors[player]:
                    if dp.door_a in names and dp.door_b in names:
                        dp.pair = True
                        found = True
                    elif dp.door_a in names:
                        dp.pair = False
                    elif dp.door_b in names:
                        dp.pair = False
                if not found:
                    world.paired_doors[player].append(PairedDoor(d1.name, d2.name))
                change_door_to_small_key(d1, world, player)
                change_door_to_small_key(d2, world, player)
            world.spoiler.set_door_type(d1.name+' <-> '+d2.name, 'Key Door', player)
            logger.debug('Key Door: %s', d1.name+' <-> '+d2.name)
        else:
            d = obj
            if d.type is DoorType.Interior:
                change_door_to_small_key(d, world, player)
                d.dest.smallKey = True  # ensure flag is set
            elif d.type is DoorType.SpiralStairs:
                pass  # we don't have spiral stairs candidates yet that aren't already key doors
            elif d.type is DoorType.Normal:
                change_door_to_small_key(d, world, player)
            world.spoiler.set_door_type(d.name, 'Key Door', player)
            logger.debug('Key Door: %s', d.name)


def change_door_to_small_key(d, world, player):
    d.smallKey = True
    room = world.get_room(d.roomIndex, player)
    if room.doorList[d.doorListPos][1] != DoorKind.SmallKey:
        room.change(d.doorListPos, DoorKind.SmallKey)


def smooth_door_pairs(world, player):
    all_doors = [x for x in world.doors if x.player == player]
    skip = set()
    bd_candidates, dashable_counts, bombable_counts = defaultdict(list), defaultdict(int), defaultdict(int)
    for door in all_doors:
        if door.type in [DoorType.Normal, DoorType.Interior] and door not in skip and not door.entranceFlag:
            partner = door.dest
            skip.add(partner)
            room_a = world.get_room(door.roomIndex, player)
            type_a = room_a.kind(door)
            if partner.type in [DoorType.Normal, DoorType.Interior]:
                room_b = world.get_room(partner.roomIndex, player)
                type_b = room_b.kind(partner)
                valid_pair = stateful_door(door, type_a) and stateful_door(partner, type_b)
            else:
                valid_pair, room_b, type_b = False, None, None
            if door.type == DoorType.Normal:
                if type_a == DoorKind.SmallKey or type_b == DoorKind.SmallKey:
                    if valid_pair:
                        if type_a != DoorKind.SmallKey:
                            room_a.change(door.doorListPos, DoorKind.SmallKey)
                        if type_b != DoorKind.SmallKey:
                            room_b.change(partner.doorListPos, DoorKind.SmallKey)
                        add_pair(door, partner, world, player)
                    else:
                        if type_a == DoorKind.SmallKey:
                            remove_pair(door, world, player)
                        if type_b == DoorKind.SmallKey:
                            remove_pair(door, world, player)
                elif type_a in [DoorKind.Bombable, DoorKind.Dashable] or type_b in [DoorKind.Bombable, DoorKind.Dashable]:
                    if valid_pair:
                        new_type = type_a
                        if type_a != type_b:
                            new_type = DoorKind.Dashable if type_a == DoorKind.Dashable or type_b == DoorKind.Dashable else DoorKind.Bombable
                            if type_a != new_type:
                                room_a.change(door.doorListPos, new_type)
                            if type_b != new_type:
                                room_b.change(partner.doorListPos, new_type)
                        add_pair(door, partner, world, player)
                        spoiler_type = 'Bomb Door' if new_type == DoorKind.Bombable else 'Dash Door'
                        world.spoiler.set_door_type(door.name + ' <-> ' + partner.name, spoiler_type, player)
                        counter = bombable_counts if new_type == DoorKind.Bombable else dashable_counts
                        counter[door.entrance.parent_region.dungeon] += 1
                    else:
                        if type_a in [DoorKind.Bombable, DoorKind.Dashable]:
                            room_a.change(door.doorListPos, DoorKind.Normal)
                            remove_pair(door, world, player)
                        elif type_b in [DoorKind.Bombable, DoorKind.Dashable]:
                            room_b.change(partner.doorListPos, DoorKind.Normal)
                            remove_pair(partner, world, player)
            elif valid_pair and type_a != DoorKind.SmallKey and type_b != DoorKind.SmallKey:
                bd_candidates[door.entrance.parent_region.dungeon].append(door)
    shuffle_bombable_dashable(bd_candidates, bombable_counts, dashable_counts, world, player)
    world.paired_doors[player] = [x for x in world.paired_doors[player] if x.pair or x.original]


def add_pair(door_a, door_b, world, player):
    pair_a, pair_b = None, None
    for paired_door in world.paired_doors[player]:
        if paired_door.door_a == door_a.name and paired_door.door_b == door_b.name:
            paired_door.pair = True
            return
        if paired_door.door_a == door_b.name and paired_door.door_b == door_a.name:
            paired_door.pair = True
            return
        if paired_door.door_a == door_a.name or paired_door.door_b == door_a.name:
            pair_a = paired_door
        if paired_door.door_a == door_b.name or paired_door.door_b == door_b.name:
            pair_b = paired_door
    if pair_a:
        pair_a.pair = False
    if pair_b:
        pair_b.pair = False
    world.paired_doors[player].append(PairedDoor(door_a, door_b))


def remove_pair(door, world, player):
    for paired_door in world.paired_doors[player]:
        if paired_door.door_a == door.name or paired_door.door_b == door.name:
            paired_door.pair = False
            break


def stateful_door(door, kind):
    if 0 <= door.doorListPos < 4:
        return kind in [DoorKind.Normal, DoorKind.SmallKey, DoorKind.Bombable, DoorKind.Dashable]  #, DoorKind.BigKey]
    return False


def shuffle_bombable_dashable(bd_candidates, bombable_counts, dashable_counts, world, player):
    if world.doorShuffle[player] == 'basic':
        for dungeon, candidates in bd_candidates.items():
            diff = bomb_dash_counts[dungeon.name][1] - dashable_counts[dungeon]
            if diff > 0:
                for chosen in random.sample(candidates, min(diff, len(candidates))):
                    change_pair_type(chosen, DoorKind.Dashable, world, player)
                    candidates.remove(chosen)
            diff = bomb_dash_counts[dungeon.name][0] - bombable_counts[dungeon]
            if diff > 0:
                for chosen in random.sample(candidates, min(diff, len(candidates))):
                    change_pair_type(chosen, DoorKind.Bombable, world, player)
                    candidates.remove(chosen)
            for excluded in candidates:
                remove_pair_type_if_present(excluded, world, player)
    elif world.doorShuffle[player] == 'crossed':
        all_candidates = sum(bd_candidates.values(), [])
        all_bomb_counts = sum(bombable_counts.values())
        all_dash_counts = sum(dashable_counts.values())
        if all_dash_counts < 8:
            for chosen in random.sample(all_candidates, min(8 - all_dash_counts, len(all_candidates))):
                change_pair_type(chosen, DoorKind.Dashable, world, player)
                all_candidates.remove(chosen)
        if all_bomb_counts < 12:
            for chosen in random.sample(all_candidates, min(12 - all_bomb_counts, len(all_candidates))):
                change_pair_type(chosen, DoorKind.Bombable, world, player)
                all_candidates.remove(chosen)
        for excluded in all_candidates:
            remove_pair_type_if_present(excluded, world, player)


def change_pair_type(door, new_type, world, player):
    room_a = world.get_room(door.roomIndex, player)
    room_a.change(door.doorListPos, new_type)
    if door.type != DoorType.Interior:
        room_b = world.get_room(door.dest.roomIndex, player)
        room_b.change(door.dest.doorListPos, new_type)
        add_pair(door, door.dest, world, player)
    spoiler_type = 'Bomb Door' if new_type == DoorKind.Bombable else 'Dash Door'
    world.spoiler.set_door_type(door.name + ' <-> ' + door.dest.name, spoiler_type, player)


def remove_pair_type_if_present(door, world, player):
    room_a = world.get_room(door.roomIndex, player)
    if room_a.kind(door) in [DoorKind.Bombable, DoorKind.Dashable]:
        room_a.change(door.doorListPos, DoorKind.Normal)
        if door.type != DoorType.Interior:
            remove_pair(door, world, player)
    if door.type != DoorType.Interior:
        room_b = world.get_room(door.dest.roomIndex, player)
        if room_b.kind(door.dest) in [DoorKind.Bombable, DoorKind.Dashable]:
            room_b.change(door.dest.doorListPos, DoorKind.Normal)
            remove_pair(door.dest, world, player)


def find_inaccessible_regions(world, player):
    world.inaccessible_regions[player] = []
    if world.mode[player] != 'inverted':
        start_regions = ['Links House', 'Sanctuary']
    else:
        start_regions = ['Inverted Links House', 'Inverted Dark Sanctuary']
    regs = convert_regions(start_regions, world, player)
    all_regions = set([r for r in world.regions if r.player == player and r.type is not RegionType.Dungeon])
    visited_regions = set()
    queue = deque(regs)
    while len(queue) > 0:
        next_region = queue.popleft()
        visited_regions.add(next_region)
        if next_region.name == 'Inverted Dark Sanctuary':  # special spawn point in cave
            for ent in next_region.entrances:
                parent = ent.parent_region
                if parent and parent.type is not RegionType.Dungeon and parent not in queue and parent not in visited_regions:
                    queue.append(parent)
        for ext in next_region.exits:
            connect = ext.connected_region
            if connect and connect not in queue and connect not in visited_regions:
                if connect.type is not RegionType.Dungeon or connect.name.endswith(' Portal'):
                    queue.append(connect)
    world.inaccessible_regions[player].extend([r.name for r in all_regions.difference(visited_regions) if valid_inaccessible_region(r)])
    logger = logging.getLogger('')
    logger.debug('Inaccessible Regions:')
    for r in world.inaccessible_regions[player]:
        logger.debug('%s', r)


def find_accessible_entrances(world, player, builder):
    entrances = [region.name for region in (portal.door.entrance.parent_region for portal in world.dungeon_portals[player]) if region.dungeon.name == builder.name]
    entrances.extend(drop_entrances[builder.name])

    if world.mode[player] == 'standard' and builder.name == 'Hyrule Castle':
        start_regions = ['Hyrule Castle Courtyard']
    elif world.mode[player] != 'inverted':
        start_regions = ['Links House', 'Sanctuary']
    else:
        start_regions = ['Inverted Links House', 'Inverted Dark Sanctuary']
    regs = convert_regions(start_regions, world, player)
    visited_regions = set()
    visited_entrances = []

    # Add Sanctuary as an additional entrance in open mode, since you can save and quit to there
    if world.mode[player] == 'open' and world.get_region('Sanctuary', player).dungeon.name == builder.name and 'Sanctuary' not in entrances:
        entrances.append('Sanctuary')
        visited_entrances.append('Sanctuary')
        regs.remove(world.get_region('Sanctuary', player))

    queue = deque(regs)
    while len(queue) > 0:
        next_region = queue.popleft()
        visited_regions.add(next_region)
        if world.mode[player] == 'inverted' and next_region.name == 'Tower Agahnim 1':
            connect = world.get_region('Hyrule Castle Ledge', player)
            if connect not in queue and connect not in visited_regions:
                queue.append(connect)
        for ext in next_region.exits:
            connect = ext.connected_region
            if connect is None or ext.door and ext.door.blocked:
                continue
            if connect.name in entrances and connect not in visited_entrances:
                visited_entrances.append(connect.name)
            elif connect and connect not in queue and connect not in visited_regions:
                queue.append(connect)
    return visited_entrances


def valid_inaccessible_region(r):
    return r.type is not RegionType.Cave or (len(r.exits) > 0 and r.name not in ['Links House', 'Chris Houlihan Room'])


def add_inaccessible_doors(world, player):
    if world.mode[player] == 'standard':
        create_doors_for_inaccessible_region('Hyrule Castle Ledge', world, player)
    # todo: ignore standard mode hyrule castle ledge?
    for inaccessible_region in world.inaccessible_regions[player]:
        create_doors_for_inaccessible_region(inaccessible_region, world, player)


def create_doors_for_inaccessible_region(inaccessible_region, world, player):
    region = world.get_region(inaccessible_region, player)
    for ext in region.exits:
        create_door(world, player, ext.name, region.name)
        if ext.connected_region.name.endswith(' Portal'):
            for more_exts in ext.connected_region.exits:
                create_door(world, player, more_exts.name, ext.connected_region.name)


def create_door(world, player, entName, region_name):
    entrance = world.get_entrance(entName, player)
    connect = entrance.connected_region
    for ext in connect.exits:
        if ext.connected_region is not None and ext.connected_region.name == region_name:
            d = Door(player, ext.name, DoorType.Logical, ext),
            world.doors += d
            connect_door_only(world, ext.name, ext.connected_region, player)
    d = Door(player, entName, DoorType.Logical, entrance),
    world.doors += d
    connect_door_only(world, entName, connect, player)


def check_required_paths(paths, world, player):
    for dungeon_name in paths.keys():
        if dungeon_name in world.dungeon_layouts[player].keys():
            builder = world.dungeon_layouts[player][dungeon_name]
            if len(paths[dungeon_name]) > 0:
                states_to_explore = defaultdict(list)
                for path in paths[dungeon_name]:
                    if type(path) is tuple:
                        states_to_explore[tuple([path[0]])] = path[1]
                    else:
                        states_to_explore[tuple(builder.path_entrances)].append(path)
                cached_initial_state = None
                for start_regs, dest_regs in states_to_explore.items():
                    if type(dest_regs) is not list:
                        dest_regs = [dest_regs]
                    check_paths = convert_regions(dest_regs, world, player)
                    start_regions = convert_regions(start_regs, world, player)
                    initial = start_regs == tuple(builder.path_entrances)
                    if not initial or cached_initial_state is None:
                        init = determine_init_crystal(initial, cached_initial_state, start_regions)
                        state = ExplorationState(init, dungeon_name)
                        for region in start_regions:
                            state.visit_region(region)
                            state.add_all_doors_check_unattached(region, world, player)
                        explore_state(state, world, player)
                        if initial and cached_initial_state is None:
                            cached_initial_state = state
                    else:
                        state = cached_initial_state
                    valid, bad_region = check_if_regions_visited(state, check_paths)
                    if not valid:
                        if check_for_pinball_fix(state, bad_region, world, player):
                            explore_state(state, world, player)
                            valid, bad_region = check_if_regions_visited(state, check_paths)
                    if not valid:
                        raise Exception('%s cannot reach %s' % (dungeon_name, bad_region.name))


def determine_init_crystal(initial, state, start_regions):
    if initial or state is None:
        return CrystalBarrier.Orange
    if len(start_regions) > 1:
        raise NotImplementedError('Path checking for multiple start regions (not the entrances) not implemented, use more paths instead')
    start_region = start_regions[0]
    if start_region in state.visited_blue and start_region in state.visited_orange:
        return CrystalBarrier.Either
    elif start_region in state.visited_blue:
        return CrystalBarrier.Blue
    elif start_region in state.visited_orange:
        return CrystalBarrier.Orange
    else:
        raise Exception(f'Can\'t get to {start_region.name} from initial state')
#        raise Exception(f'Can\'t get to {start_region.name} from initial state\n{state.dungeon}\n{state.found_locations}')


def explore_state(state, world, player):
    while len(state.avail_doors) > 0:
        door = state.next_avail_door().door
        connect_region = world.get_entrance(door.name, player).connected_region
        if state.can_traverse(door) and not state.visited(connect_region) and valid_region_to_explore(connect_region, world, player):
            state.visit_region(connect_region)
            state.add_all_doors_check_unattached(connect_region, world, player)


def explore_state_not_inaccessible(state, world, player):
    while len(state.avail_doors) > 0:
        door = state.next_avail_door().door
        connect_region = world.get_entrance(door.name, player).connected_region
        if state.can_traverse(door) and not state.visited(connect_region) and connect_region.type == RegionType.Dungeon:
            state.visit_region(connect_region)
            state.add_all_doors_check_unattached(connect_region, world, player)


def check_if_regions_visited(state, check_paths):
    valid = False
    breaking_region = None
    for region_target in check_paths:
        if state.visited_at_all(region_target):
            valid = True
            break
        elif not breaking_region:
            breaking_region = region_target
    return valid, breaking_region


def check_for_pinball_fix(state, bad_region, world, player):
    pinball_region = world.get_region('Skull Pinball', player)
    # todo: lobby shuffle
    if bad_region.name == 'Skull 2 West Lobby' and state.visited_at_all(pinball_region):  # revisit this for entrance shuffle
        door = world.get_door('Skull Pinball WS', player)
        room = world.get_room(door.roomIndex, player)
        if room.doorList[door.doorListPos][1] == DoorKind.Trap:
            room.change(door.doorListPos, DoorKind.Normal)
            door.trapFlag = 0x0
            door.blocked = False
            connect_two_way(world, door.name, door.dest.name, player)
            state.add_all_doors_check_unattached(pinball_region, world, player)
            return True
    return False


@unique
class DROptions(Flag):
    NoOptions = 0x00
    Eternal_Mini_Bosses = 0x01  # If on, GT minibosses marked as defeated when they try to spawn a heart
    Town_Portal = 0x02  # If on, Players will start with mirror scroll
    Map_Info = 0x04
    Debug = 0x08
    Rails = 0x10  # If on, draws rails
    OriginalPalettes = 0x20
    Reserved = 0x40  # Reserved for PoD sliding wall?
    Open_Desert_Wall = 0x80  # If on, pre opens the desert wall, no fire required


# DATA GOES DOWN HERE
logical_connections = [
    ('Hyrule Dungeon North Abyss Catwalk Dropdown', 'Hyrule Dungeon North Abyss'),
    ('Hyrule Dungeon Cellblock Door', 'Hyrule Dungeon Cell'),
    ('Hyrule Dungeon Cell Exit', 'Hyrule Dungeon Cellblock'),
    ('Hyrule Castle Throne Room Tapestry', 'Hyrule Castle Behind Tapestry'),
    ('Hyrule Castle Tapestry Backwards', 'Hyrule Castle Throne Room'),
    ('Sewers Secret Room Push Block', 'Sewers Secret Room Blocked Path'),
    ('Eastern Hint Tile Push Block', 'Eastern Hint Tile'),
    ('Eastern Map Balcony Hook Path', 'Eastern Map Room'),
    ('Eastern Map Room Drop Down', 'Eastern Map Balcony'),
    ('Desert Main Lobby Left Path', 'Desert Left Alcove'),
    ('Desert Main Lobby Right Path', 'Desert Right Alcove'),
    ('Desert Left Alcove Path', 'Desert Main Lobby'),
    ('Desert Right Alcove Path', 'Desert Main Lobby'),

    ('Hera Lobby to Front Barrier - Blue', 'Hera Front'),
    ('Hera Front to Lobby Barrier - Blue', 'Hera Lobby'),
    ('Hera Lobby to Crystal', 'Hera Lobby Crystal'),
    ('Hera Lobby Crystal Exit', 'Hera Lobby'),
    ('Hera Front to Crystal', 'Hera Front Crystal'),
    ('Hera Front Crystal Exit', 'Hera Front'),
    ('Hera Front to Down Stairs Barrier - Blue', 'Hera Down Stairs Landing'),
    ('Hera Front to Up Stairs Barrier - Orange', 'Hera Up Stairs Landing'),
    ('Hera Front to Back Barrier - Orange', 'Hera Back'),
    ('Hera Down Stairs to Front Barrier - Blue', 'Hera Front'),
    ('Hera Down Stairs Landing to Ranged Crystal', 'Hera Down Stairs Landing - Ranged Crystal'),
    ('Hera Down Stairs Landing Ranged Crystal Exit', 'Hera Down Stairs Landing'),
    ('Hera Up Stairs to Front Barrier - Orange', 'Hera Front'),
    ('Hera Up Stairs Landing to Ranged Crystal', 'Hera Up Stairs Landing - Ranged Crystal'),
    ('Hera Up Stairs Landing Ranged Crystal Exit', 'Hera Up Stairs Landing'),
    ('Hera Back to Front Barrier - Orange', 'Hera Front'),
    ('Hera Back to Ranged Crystal', 'Hera Back - Ranged Crystal'),
    ('Hera Back Ranged Crystal Exit', 'Hera Back'),
    ('Hera Big Chest Hook Path', 'Hera Big Chest Landing'),
    ('Hera Big Chest Landing Exit', 'Hera 4F'),

    ('PoD Pit Room Block Path N', 'PoD Pit Room Blocked'),
    ('PoD Pit Room Block Path S', 'PoD Pit Room'),
    ('PoD Arena Landing Bonk Path', 'PoD Arena Bridge'),
    ('PoD Arena North Drop Down', 'PoD Arena Main'),
    ('PoD Arena Bridge Drop Down', 'PoD Arena Main'),
    ('PoD Arena North to Landing Barrier - Orange', 'PoD Arena Landing'),
    ('PoD Arena Main to Ranged Crystal', 'PoD Arena Main - Ranged Crystal'),
    ('PoD Arena Main to Landing Barrier - Blue', 'PoD Arena Landing'),
    ('PoD Arena Main to North Ranged Barrier - Orange', 'PoD Arena North'),
    ('PoD Arena Main Ranged Crystal Exit', 'PoD Arena Main'),
    ('PoD Arena Bridge to Ranged Crystal', 'PoD Arena Bridge - Ranged Crystal'),
    ('PoD Arena Bridge Ranged Crystal Exit', 'PoD Arena Bridge'),
    ('PoD Arena Landing to Main Barrier - Blue', 'PoD Arena Main'),
    ('PoD Arena Landing to Right Barrier - Blue', 'PoD Arena Right'),
    ('PoD Arena Landing to North Barrier - Orange', 'PoD Arena North'),
    ('PoD Arena Landing to Ranged Crystal', 'PoD Arena Landing - Ranged Crystal'),
    ('PoD Arena Landing Ranged Crystal Exit', 'PoD Arena Landing'),
    ('PoD Arena Right to Landing Barrier - Blue', 'PoD Arena Landing'),

    ('PoD Map Balcony Drop Down', 'PoD Sexy Statue'),
    ('PoD Map Balcony to Ranged Crystal', 'PoD Map Balcony - Ranged Crystal'),
    ('PoD Map Balcony Ranged Crystal Exit', 'PoD Map Balcony'),
    ('PoD Basement Ledge Drop Down', 'PoD Stalfos Basement'),
    ('PoD Falling Bridge Path N', 'PoD Falling Bridge Ledge'),
    ('PoD Falling Bridge Path S', 'PoD Falling Bridge'),
    ('PoD Bow Statue Left to Right Barrier - Orange', 'PoD Bow Statue Right'),
    ('PoD Bow Statue Right to Left Barrier - Orange', 'PoD Bow Statue Left'),
    ('PoD Bow Statue Right to Ranged Crystal', 'PoD Bow Statue Right - Ranged Crystal'),
    ('PoD Bow Statue Ranged Crystal Exit', 'PoD Bow Statue Right'),
    ('PoD Dark Pegs Landing to Right', 'PoD Dark Pegs Right'),
    ('PoD Dark Pegs Landing to Ranged Crystal', 'PoD Dark Pegs Landing - Ranged Crystal'),
    ('PoD Dark Pegs Right to Landing', 'PoD Dark Pegs Landing'),
    ('PoD Dark Pegs Right to Middle Barrier - Orange', 'PoD Dark Pegs Middle'),
    ('PoD Dark Pegs Middle to Right Barrier - Orange', 'PoD Dark Pegs Right'),
    ('PoD Dark Pegs Middle to Left Barrier - Blue', 'PoD Dark Pegs Left'),
    ('PoD Dark Pegs Middle to Ranged Crystal', 'PoD Dark Pegs Middle - Ranged Crystal'),
    ('PoD Dark Pegs Left to Middle Barrier - Blue', 'PoD Dark Pegs Middle'),
    ('PoD Dark Pegs Left to Ranged Crystal', 'PoD Dark Pegs Left - Ranged Crystal'),
    ('PoD Dark Pegs Landing Ranged Crystal Exit', 'PoD Dark Pegs Landing'),
    ('PoD Dark Pegs Middle Ranged Crystal Exit', 'PoD Dark Pegs Middle'),
    ('PoD Dark Pegs Left Ranged Crystal Exit', 'PoD Dark Pegs Left'),
    ('Swamp Lobby Moat', 'Swamp Entrance'),
    ('Swamp Entrance Moat', 'Swamp Lobby'),
    ('Swamp Trench 1 Approach Dry', 'Swamp Trench 1 Nexus'),
    ('Swamp Trench 1 Approach Key', 'Swamp Trench 1 Key Ledge'),
    ('Swamp Trench 1 Approach Swim Depart', 'Swamp Trench 1 Departure'),
    ('Swamp Trench 1 Nexus Approach', 'Swamp Trench 1 Approach'),
    ('Swamp Trench 1 Nexus Key', 'Swamp Trench 1 Key Ledge'),
    ('Swamp Trench 1 Key Ledge Dry', 'Swamp Trench 1 Nexus'),
    ('Swamp Trench 1 Key Approach', 'Swamp Trench 1 Approach'),
    ('Swamp Trench 1 Key Ledge Depart', 'Swamp Trench 1 Departure'),
    ('Swamp Trench 1 Departure Dry', 'Swamp Trench 1 Nexus'),
    ('Swamp Trench 1 Departure Approach', 'Swamp Trench 1 Approach'),
    ('Swamp Trench 1 Departure Key', 'Swamp Trench 1 Key Ledge'),
    ('Swamp Hub Hook Path', 'Swamp Hub North Ledge'),
    ('Swamp Hub North Ledge Drop Down', 'Swamp Hub'),
    ('Swamp Compass Donut Push Block', 'Swamp Donut Top'),
    ('Swamp Shortcut Blue Barrier', 'Swamp Trench 2 Pots'),
    ('Swamp Trench 2 Pots Blue Barrier', 'Swamp Shortcut'),
    ('Swamp Trench 2 Pots Dry', 'Swamp Trench 2 Blocks'),
    ('Swamp Trench 2 Pots Wet', 'Swamp Trench 2 Departure'),
    ('Swamp Trench 2 Blocks Pots', 'Swamp Trench 2 Pots'),
    ('Swamp Trench 2 Departure Wet', 'Swamp Trench 2 Pots'),
    ('Swamp West Shallows Push Blocks', 'Swamp West Block Path'),
    ('Swamp West Block Path Drop Down', 'Swamp West Shallows'),
    ('Swamp West Ledge Drop Down', 'Swamp West Shallows'),
    ('Swamp West Ledge Hook Path', 'Swamp Barrier Ledge'),
    ('Swamp Barrier Ledge Drop Down', 'Swamp West Shallows'),
    ('Swamp Barrier Ledge - Orange', 'Swamp Barrier'),
    ('Swamp Barrier - Orange', 'Swamp Barrier Ledge'),
    ('Swamp Barrier Ledge Hook Path', 'Swamp West Ledge'),
    ('Swamp Drain Right Switch', 'Swamp Drain Left'),
    ('Swamp Flooded Spot Ladder', 'Swamp Flooded Room'),
    ('Swamp Flooded Room Ladder', 'Swamp Flooded Spot'),
    ('Skull Pot Circle Star Path', 'Skull Map Room'),
    ('Skull Big Chest Hookpath', 'Skull 1 Lobby'),
    ('Skull Back Drop Star Path', 'Skull Small Hall'),
    ('Thieves Rail Ledge Drop Down', 'Thieves BK Corner'),
    ('Thieves Hellway Orange Barrier', 'Thieves Hellway S Crystal'),
    ('Thieves Hellway Crystal Orange Barrier', 'Thieves Hellway'),
    ('Thieves Hellway Blue Barrier', 'Thieves Hellway N Crystal'),
    ('Thieves Hellway Crystal Blue Barrier', 'Thieves Hellway'),
    ('Thieves Attic Orange Barrier', 'Thieves Attic Hint'),
    ('Thieves Attic Hint Orange Barrier', 'Thieves Attic'),
    ('Thieves Basement Block Path', 'Thieves Blocked Entry'),
    ('Thieves Blocked Entry Path', 'Thieves Basement Block'),
    ('Thieves Conveyor Bridge Block Path', 'Thieves Conveyor Block'),
    ('Thieves Conveyor Block Path', 'Thieves Conveyor Bridge'),
    ("Thieves Blind's Cell Door", "Thieves Blind's Cell Interior"),
    ("Thieves Blind's Cell Exit", "Thieves Blind's Cell"),
    ('Ice Cross Bottom Push Block Left', 'Ice Floor Switch'),
    ('Ice Cross Right Push Block Top', 'Ice Bomb Drop'),
    ('Ice Big Key Push Block', 'Ice Dead End'),
    ('Ice Bomb Jump Ledge Orange Barrier', 'Ice Bomb Jump Catwalk'),
    ('Ice Bomb Jump Catwalk Orange Barrier', 'Ice Bomb Jump Ledge'),
    ('Ice Hookshot Ledge Path', 'Ice Hookshot Balcony'),
    ('Ice Hookshot Balcony Path', 'Ice Hookshot Ledge'),
    ('Ice Crystal Right Orange Barrier', 'Ice Crystal Left'),
    ('Ice Crystal Left Orange Barrier', 'Ice Crystal Right'),
    ('Ice Crystal Left Blue Barrier', 'Ice Crystal Block'),
    ('Ice Crystal Block Exit', 'Ice Crystal Left'),
    ('Ice Big Chest Landing Push Blocks', 'Ice Big Chest View'),
    ('Mire Lobby Gap', 'Mire Post-Gap'),
    ('Mire Post-Gap Gap', 'Mire Lobby'),
    ('Mire Hub Upper Blue Barrier', 'Mire Hub Switch'),
    ('Mire Hub Lower Blue Barrier', 'Mire Hub Right'),
    ('Mire Hub Right Blue Barrier', 'Mire Hub'),
    ('Mire Hub Top Blue Barrier', 'Mire Hub Switch'),
    ('Mire Hub Switch Blue Barrier N', 'Mire Hub Top'),
    ('Mire Hub Switch Blue Barrier S', 'Mire Hub'),
    ('Mire Map Spike Side Drop Down', 'Mire Lone Shooter'),
    ('Mire Map Spike Side Blue Barrier', 'Mire Crystal Dead End'),
    ('Mire Map Spot Blue Barrier', 'Mire Crystal Dead End'),
    ('Mire Crystal Dead End Left Barrier', 'Mire Map Spot'),
    ('Mire Crystal Dead End Right Barrier', 'Mire Map Spike Side'),
    ('Mire Hidden Shooters Block Path S', 'Mire Hidden Shooters'),
    ('Mire Hidden Shooters Block Path N', 'Mire Hidden Shooters Blocked'),
    ('Mire Left Bridge Hook Path', 'Mire Right Bridge'),
    ('Mire Tall Dark and Roomy to Ranged Crystal', 'Mire Tall Dark and Roomy - Ranged Crystal'),
    ('Mire Tall Dark and Roomy Ranged Crystal Exit', 'Mire Tall Dark and Roomy'),
    ('Mire Crystal Right Orange Barrier', 'Mire Crystal Mid'),
    ('Mire Crystal Mid Orange Barrier', 'Mire Crystal Right'),
    ('Mire Crystal Mid Blue Barrier', 'Mire Crystal Left'),
    ('Mire Crystal Left Blue Barrier', 'Mire Crystal Mid'),
    ('Mire Firesnake Skip Orange Barrier', 'Mire Antechamber'),
    ('Mire Antechamber Orange Barrier', 'Mire Firesnake Skip'),
    ('Mire Compass Blue Barrier', 'Mire Compass Chest'),
    ('Mire Compass Chest Exit', 'Mire Compass Room'),
    ('Mire South Fish Blue Barrier', 'Mire Fishbone'),
    ('Mire Fishbone Blue Barrier', 'Mire South Fish'),
    ('TR Main Lobby Gap', 'TR Lobby Ledge'),
    ('TR Lobby Ledge Gap', 'TR Main Lobby'),
    ('TR Pipe Ledge Drop Down', 'TR Pipe Pit'),
    ('TR Big Chest Gap', 'TR Big Chest Entrance'),
    ('TR Big Chest Entrance Gap', 'TR Big Chest'),
    ('TR Chain Chomps Top to Bottom Barrier - Orange', 'TR Chain Chomps Bottom'),
    ('TR Chain Chomps Bottom to Top Barrier - Orange', 'TR Chain Chomps Top'),
    ('TR Chain Chomps Bottom to Ranged Crystal', 'TR Chain Chomps Bottom - Ranged Crystal'),
    ('TR Chain Chomps Bottom Ranged Crystal Exit', 'TR Chain Chomps Bottom'),
    ('TR Pokey 2 Top to Bottom Barrier - Blue', 'TR Pokey 2 Bottom'),
    ('TR Pokey 2 Bottom to Top Barrier - Blue', 'TR Pokey 2 Top'),
    ('TR Pokey 2 Bottom to Ranged Crystal', 'TR Pokey 2 Bottom - Ranged Crystal'),
    ('TR Pokey 2 Bottom Ranged Crystal Exit', 'TR Pokey 2 Bottom'),
    ('TR Crystaroller Bottom to Middle Barrier - Orange', 'TR Crystaroller Middle'),
    ('TR Crystaroller Bottom to Ranged Crystal', 'TR Crystaroller Bottom - Ranged Crystal'),
    ('TR Crystaroller Middle to Bottom Barrier - Orange', 'TR Crystaroller Bottom'),
    ('TR Crystaroller Middle to Chest Barrier - Blue', 'TR Crystaroller Chest'),
    ('TR Crystaroller Middle to Top Barrier - Orange', 'TR Crystaroller Top'),
    ('TR Crystaroller Middle to Ranged Crystal', 'TR Crystaroller Middle - Ranged Crystal'),
    ('TR Crystaroller Top to Middle Barrier - Orange', 'TR Crystaroller Middle'),
    ('TR Crystaroller Chest to Middle Barrier - Blue', 'TR Crystaroller Middle'),
    ('TR Crystaroller Middle Ranged Crystal Exit', 'TR Crystaroller Middle'),
    ('TR Crystaroller Bottom Ranged Crystal Exit', 'TR Crystaroller Bottom'),
    ('TR Crystal Maze Start to Interior Barrier - Blue', 'TR Crystal Maze Interior'),
    ('TR Crystal Maze Interior to End Barrier - Blue', 'TR Crystal Maze End'),
    ('TR Crystal Maze Interior to Start Barrier - Blue', 'TR Crystal Maze Start'),
    ('TR Crystal Maze End to Interior Barrier - Blue', 'TR Crystal Maze Interior'),
    ('TR Crystal Maze End to Ranged Crystal', 'TR Crystal Maze End - Ranged Crystal'),
    ('TR Crystal Maze End Ranged Crystal Exit', 'TR Crystal Maze End'),

    ('GT Blocked Stairs Block Path', 'GT Big Chest'),
    ('GT Speed Torch South Path', 'GT Speed Torch'),
    ('GT Speed Torch North Path', 'GT Speed Torch Upper'),
    ('GT Hookshot East-North Path', 'GT Hookshot North Platform'),
    ('GT Hookshot East-South Path', 'GT Hookshot South Platform'),
    ('GT Hookshot North-East Path', 'GT Hookshot East Platform'),
    ('GT Hookshot North-South Path', 'GT Hookshot South Platform'),
    ('GT Hookshot South-East Path', 'GT Hookshot East Platform'),
    ('GT Hookshot South-North Path', 'GT Hookshot North Platform'),
    ('GT Hookshot Platform Blue Barrier', 'GT Hookshot South Entry'),
    ('GT Hookshot Entry Blue Barrier', 'GT Hookshot South Platform'),
    ('GT Hookshot South Entry to Ranged Crystal',  'GT Hookshot South Entry - Ranged Crystal'),
    ('GT HookShot South Entry Ranged Crystal Exit', 'GT Hookshot South Entry'),
    ('GT Double Switch to Pot Corners Barrier - Orange', 'GT Double Switch Pot Corners'),
    ('GT Double Switch Pot Corners to Barrier - Orange', 'GT Double Switch Entry'),
    ('GT Double Switch Pot Corners to Barrier - Blue', 'GT Double Switch Exit'),
    ('GT Double Switch Pot Corners to Ranged Switches', 'GT Double Switch Pot Corners - Ranged Switches'),
    ('GT Double Switch Pot Corners Ranged Switches Exit', 'GT Double Switch Pot Corners'),
    ('GT Double Switch Exit to Blue Barrier', 'GT Double Switch Pot Corners'),
    ('GT Warp Maze - Pit Section Warp Spot', 'GT Warp Maze - Pit Exit Warp Spot'),
    ('GT Warp Maze Exit Section Warp Spot', 'GT Warp Maze - Pit Exit Warp Spot'),
    ('GT Firesnake Room Hook Path', 'GT Firesnake Room Ledge'),

    ('GT Crystal Conveyor to Corner Barrier - Blue', 'GT Crystal Conveyor Corner'),
    ('GT Crystal Conveyor to Ranged Crystal', 'GT Crystal Conveyor - Ranged Crystal'),
    ('GT Crystal Conveyor to Left Bypass', 'GT Crystal Conveyor Left'),
    ('GT Crystal Conveyor Corner to Barrier - Blue', 'GT Crystal Conveyor Left'),
    ('GT Crystal Conveyor Corner to Barrier - Orange', 'GT Crystal Conveyor'),
    ('GT Crystal Conveyor Corner to Ranged Crystal', 'GT Crystal Conveyor Corner - Ranged Crystal'),
    ('GT Crystal Conveyor Left to Corner Barrier - Orange', 'GT Crystal Conveyor Corner'),
    ('GT Crystal Conveyor Ranged Crystal Exit', 'GT Crystal Conveyor'),
    ('GT Crystal Conveyor Corner Ranged Crystal Exit', 'GT Crystal Conveyor Corner'),

    ('GT Left Moldorm Ledge Drop Down', 'GT Moldorm'),
    ('GT Right Moldorm Ledge Drop Down', 'GT Moldorm'),
    ('GT Crystal Circles Barrier - Orange', 'GT Crystal Inner Circle'),
    ('GT Crystal Circles to Ranged Crystal', 'GT Crystal Circles - Ranged Crystal'),
    ('GT Crystal Inner Circle Barrier - Orange', 'GT Crystal Circles'),
    ('GT Crystal Circles Ranged Crystal Exit', 'GT Crystal Circles'),
    ('GT Moldorm Gap', 'GT Validation'),
    ('GT Validation Block Path', 'GT Validation Door')
]

vanilla_logical_connections = [
    ('Ice Cross Left Push Block', 'Ice Compass Room'),
    ('Ice Cross Right Push Block Bottom', 'Ice Compass Room'),
    ('Ice Cross Bottom Push Block Right', 'Ice Pengator Switch'),
    ('Ice Cross Top Push Block Right', 'Ice Pengator Switch'),
]

spiral_staircases = [
    ('Hyrule Castle Back Hall Down Stairs', 'Hyrule Dungeon Map Room Up Stairs'),
    ('Hyrule Dungeon Armory Down Stairs', 'Hyrule Dungeon Staircase Up Stairs'),
    ('Hyrule Dungeon Staircase Down Stairs', 'Hyrule Dungeon Cellblock Up Stairs'),
    ('Sewers Behind Tapestry Down Stairs', 'Sewers Rope Room Up Stairs'),
    ('Sewers Secret Room Up Stairs', 'Sewers Pull Switch Down Stairs'),
    ('Eastern Darkness Up Stairs', 'Eastern Attic Start Down Stairs'),
    ('Desert Tiles 1 Up Stairs', 'Desert Bridge Down Stairs'),
    ('Hera Lobby Down Stairs', 'Hera Basement Cage Up Stairs'),
    ('Hera Lobby Key Stairs', 'Hera Tile Room Up Stairs'),
    ('Hera Lobby Up Stairs', 'Hera Beetles Down Stairs'),
    ('Hera Startile Wide Up Stairs', 'Hera 4F Down Stairs'),
    ('Hera 4F Up Stairs', 'Hera 5F Down Stairs'),
    ('Hera 5F Up Stairs', 'Hera Boss Down Stairs'),
    ('Tower Room 03 Up Stairs', 'Tower Lone Statue Down Stairs'),
    ('Tower Dark Chargers Up Stairs', 'Tower Dual Statues Down Stairs'),
    ('Tower Dark Archers Up Stairs', 'Tower Red Spears Down Stairs'),
    ('Tower Pacifist Run Up Stairs', 'Tower Push Statue Down Stairs'),
    ('PoD Left Cage Down Stairs', 'PoD Shooter Room Up Stairs'),
    ('PoD Middle Cage Down Stairs', 'PoD Warp Room Up Stairs'),
    ('PoD Basement Ledge Up Stairs', 'PoD Big Key Landing Down Stairs'),
    ('PoD Compass Room W Down Stairs', 'PoD Dark Basement W Up Stairs'),
    ('PoD Compass Room E Down Stairs', 'PoD Dark Basement E Up Stairs'),
    ('Swamp Entrance Down Stairs', 'Swamp Pot Row Up Stairs'),
    ('Swamp West Block Path Up Stairs', 'Swamp Attic Down Stairs'),
    ('Swamp Push Statue Down Stairs', 'Swamp Flooded Room Up Stairs'),
    ('Swamp Left Elbow Down Stairs', 'Swamp Drain Left Up Stairs'),
    ('Swamp Right Elbow Down Stairs', 'Swamp Drain Right Up Stairs'),
    ('Swamp Behind Waterfall Up Stairs', 'Swamp C Down Stairs'),
    ('Thieves Spike Switch Up Stairs', 'Thieves Attic Down Stairs'),
    ('Thieves Conveyor Maze Down Stairs', 'Thieves Basement Block Up Stairs'),
    ('Ice Jelly Key Down Stairs', 'Ice Floor Switch Up Stairs'),
    ('Ice Narrow Corridor Down Stairs', 'Ice Pengator Trap Up Stairs'),
    ('Ice Spike Room Up Stairs', 'Ice Hammer Block Down Stairs'),
    ('Ice Spike Room Down Stairs', 'Ice Spikeball Up Stairs'),
    ('Ice Lonely Freezor Down Stairs', 'Iced T Up Stairs'),
    ('Ice Backwards Room Down Stairs', 'Ice Anti-Fairy Up Stairs'),
    ('Mire Post-Gap Down Stairs', 'Mire 2 Up Stairs'),
    ('Mire Left Bridge Down Stairs', 'Mire Dark Shooters Up Stairs'),
    ('Mire Conveyor Barrier Up Stairs', 'Mire Torches Top Down Stairs'),
    ('Mire Falling Foes Up Stairs', 'Mire Firesnake Skip Down Stairs'),
    ('TR Chain Chomps Down Stairs', 'TR Pipe Pit Up Stairs'),
    ('TR Crystaroller Down Stairs', 'TR Dark Ride Up Stairs'),
    ('GT Lobby Left Down Stairs', 'GT Torch Up Stairs'),
    ('GT Lobby Up Stairs', 'GT Crystal Paths Down Stairs'),
    ('GT Lobby Right Down Stairs', 'GT Hope Room Up Stairs'),
    ('GT Blocked Stairs Down Stairs', 'GT Four Torches Up Stairs'),
    ('GT Cannonball Bridge Up Stairs', 'GT Gauntlet 1 Down Stairs'),
    ('GT Quad Pot Up Stairs', 'GT Wizzrobes 1 Down Stairs'),
    ('GT Moldorm Pit Up Stairs', 'GT Right Moldorm Ledge Down Stairs'),
    ('GT Frozen Over Up Stairs', 'GT Brightly Lit Hall Down Stairs')
]

straight_staircases = [
    ('Hyrule Castle Lobby North Stairs', 'Hyrule Castle Throne Room South Stairs'),
    ('Sewers Rope Room North Stairs', 'Sewers Dark Cross South Stairs'),
    ('Tower Catwalk North Stairs', 'Tower Antechamber South Stairs'),
    ('PoD Conveyor North Stairs', 'PoD Map Balcony South Stairs'),
    ('TR Crystal Maze North Stairs', 'TR Final Abyss South Stairs')
]

open_edges = [
    ('Hyrule Dungeon North Abyss South Edge', 'Hyrule Dungeon South Abyss North Edge'),
    ('Hyrule Dungeon North Abyss Catwalk Edge', 'Hyrule Dungeon South Abyss Catwalk North Edge'),
    ('Hyrule Dungeon South Abyss West Edge', 'Hyrule Dungeon Guardroom Abyss Edge'),
    ('Hyrule Dungeon South Abyss Catwalk West Edge', 'Hyrule Dungeon Guardroom Catwalk Edge'),
    ('Desert Main Lobby NW Edge', 'Desert North Hall SW Edge'),
    ('Desert Main Lobby N Edge', 'Desert Dead End Edge'),
    ('Desert Main Lobby NE Edge', 'Desert North Hall SE Edge'),
    ('Desert Main Lobby E Edge', 'Desert East Wing W Edge'),
    ('Desert East Wing N Edge', 'Desert Arrow Pot Corner S Edge'),
    ('Desert Arrow Pot Corner W Edge', 'Desert North Hall E Edge'),
    ('Desert West Wing N Edge', 'Desert Sandworm Corner S Edge'),
    ('Desert Sandworm Corner E Edge', 'Desert North Hall W Edge'),
    ('Thieves Lobby N Edge', 'Thieves Ambush S Edge'),
    ('Thieves Lobby NE Edge', 'Thieves Ambush SE Edge'),
    ('Thieves Ambush ES Edge', 'Thieves BK Corner WS Edge'),
    ('Thieves Ambush EN Edge', 'Thieves BK Corner WN Edge'),
    ('Thieves BK Corner S Edge', 'Thieves Compass Room N Edge'),
    ('Thieves BK Corner SW Edge', 'Thieves Compass Room NW Edge'),
    ('Thieves Compass Room WS Edge', 'Thieves Big Chest Nook ES Edge'),
    ('Thieves Cricket Hall Left Edge', 'Thieves Cricket Hall Right Edge')
]

falldown_pits = [
    ('Eastern Courtyard Potholes', 'Eastern Fairies'),
    ('Hera Beetles Holes Front', 'Hera Front'),
    ('Hera Beetles Holes Landing', 'Hera Up Stairs Landing'),
    ('Hera Startile Corner Holes Front', 'Hera Front'),
    ('Hera Startile Corner Holes Landing', 'Hera Down Stairs Landing'),
    ('Hera Startile Wide Holes', 'Hera Back'),
    ('Hera 4F Holes', 'Hera Back'),  # failed bomb jump
    ('Hera Big Chest Landing Holes', 'Hera Startile Wide'),  # the other holes near big chest
    ('Hera 5F Star Hole', 'Hera Big Chest Landing'),
    ('Hera 5F Pothole Chain', 'Hera Fairies'),
    ('Hera 5F Normal Holes', 'Hera 4F'),
    ('Hera Boss Outer Hole', 'Hera 5F'),
    ('Hera Boss Inner Hole', 'Hera 4F'),
    ('PoD Pit Room Freefall', 'PoD Stalfos Basement'),
    ('PoD Pit Room Bomb Hole', 'PoD Basement Ledge'),
    ('PoD Big Key Landing Hole', 'PoD Stalfos Basement'),
    ('Swamp Attic Right Pit', 'Swamp Barrier Ledge'),
    ('Swamp Attic Left Pit', 'Swamp West Ledge'),
    ('Skull Final Drop Hole', 'Skull Boss'),
    ('Ice Bomb Drop Hole', 'Ice Stalfos Hint'),
    ('Ice Falling Square Hole', 'Ice Tall Hint'),
    ('Ice Freezors Hole', 'Ice Big Chest View'),
    ('Ice Freezors Ledge Hole', 'Ice Big Chest View'),
    ('Ice Freezors Bomb Hole', 'Ice Big Chest Landing'),
    ('Ice Crystal Block Hole', 'Ice Switch Room'),
    ('Ice Crystal Right Blue Hole', 'Ice Switch Room'),
    ('Ice Backwards Room Hole', 'Ice Fairy'),
    ('Ice Antechamber Hole', 'Ice Boss'),
    ('Mire Attic Hint Hole', 'Mire BK Chest Ledge'),
    ('Mire Torches Top Holes', 'Mire Conveyor Barrier'),
    ('Mire Torches Bottom Holes', 'Mire Warping Pool'),
    ('GT Bob\'s Room Hole', 'GT Ice Armos'),
    ('GT Falling Torches Hole', 'GT Staredown'),
    ('GT Moldorm Hole', 'GT Moldorm Pit')
]

dungeon_warps = [
    ('Eastern Fairies\' Warp', 'Eastern Courtyard'),
    ('Hera Fairies\' Warp', 'Hera 5F'),
    ('PoD Warp Hint Warp', 'PoD Warp Room'),
    ('PoD Warp Room Warp', 'PoD Warp Hint'),
    ('PoD Stalfos Basement Warp', 'PoD Warp Room'),
    ('PoD Callback Warp', 'PoD Dark Alley'),
    ('Ice Fairy Warp', 'Ice Anti-Fairy'),
    ('Mire Lone Warp Warp', 'Mire BK Door Room'),
    ('Mire Warping Pool Warp', 'Mire Square Rail'),
    ('GT Compass Room Warp', 'GT Conveyor Star Pits'),
    ('GT Spike Crystals Warp', 'GT Firesnake Room'),
    ('GT Warp Maze - Left Section Warp', 'GT Warp Maze - Rando Rail'),
    ('GT Warp Maze - Mid Section Left Warp', 'GT Warp Maze - Main Rails'),
    ('GT Warp Maze - Mid Section Right Warp', 'GT Warp Maze - Main Rails'),
    ('GT Warp Maze - Right Section Warp', 'GT Warp Maze - Main Rails'),
    ('GT Warp Maze - Pit Exit Warp', 'GT Warp Maze - Pot Rail'),
    ('GT Warp Maze - Rail Choice Left Warp', 'GT Warp Maze - Left Section'),
    ('GT Warp Maze - Rail Choice Right Warp', 'GT Warp Maze - Mid Section'),
    ('GT Warp Maze - Rando Rail Warp', 'GT Warp Maze - Mid Section'),
    ('GT Warp Maze - Main Rails Best Warp', 'GT Warp Maze - Pit Section'),
    ('GT Warp Maze - Main Rails Mid Left Warp', 'GT Warp Maze - Mid Section'),
    ('GT Warp Maze - Main Rails Mid Right Warp', 'GT Warp Maze - Mid Section'),
    ('GT Warp Maze - Main Rails Right Top Warp', 'GT Warp Maze - Right Section'),
    ('GT Warp Maze - Main Rails Right Mid Warp', 'GT Warp Maze - Right Section'),
    ('GT Warp Maze - Pot Rail Warp', 'GT Warp Maze Exit Section'),
    ('GT Hidden Star Warp', 'GT Invisible Bridges')
]

ladders = [
    ('PoD Bow Statue Down Ladder', 'PoD Dark Pegs Up Ladder'),
    ('Ice Big Key Down Ladder', 'Ice Tongue Pull Up Ladder'),
    ('Ice Firebar Down Ladder', 'Ice Freezors Up Ladder'),
    ('GT Staredown Up Ladder', 'GT Falling Torches Down Ladder')
]

interior_doors = [
    ('Hyrule Dungeon Armory Interior Key Door S', 'Hyrule Dungeon Armory Interior Key Door N'),
    ('Hyrule Dungeon Armory ES', 'Hyrule Dungeon Armory Boomerang WS'),
    ('Hyrule Dungeon Map Room Key Door S', 'Hyrule Dungeon North Abyss Key Door N'),
    ('Sewers Rat Path WS', 'Sewers Secret Room ES'),
    ('Sewers Rat Path WN', 'Sewers Secret Room EN'),
    ('Sewers Yet More Rats S', 'Sewers Pull Switch N'),
    ('Eastern Lobby N', 'Eastern Lobby Bridge S'),
    ('Eastern Lobby NW', 'Eastern Lobby Left Ledge SW'),
    ('Eastern Lobby NE', 'Eastern Lobby Right Ledge SE'),
    ('Eastern East Wing EN', 'Eastern Pot Switch WN'),
    ('Eastern East Wing ES', 'Eastern Map Balcony WS'),
    ('Eastern Pot Switch SE', 'Eastern Map Room NE'),
    ('Eastern West Wing WS', 'Eastern Stalfos Spawn ES'),
    ('Eastern Stalfos Spawn NW', 'Eastern Compass Room SW'),
    ('Eastern Compass Room EN', 'Eastern Hint Tile WN'),
    ('Eastern Dark Square EN', 'Eastern Dark Pots WN'),
    ('Eastern Darkness NE', 'Eastern Rupees SE'),
    ('Eastern False Switches WS', 'Eastern Cannonball Hell ES'),
    ('Eastern Single Eyegore NE', 'Eastern Duo Eyegores SE'),
    ('Desert East Lobby WS', 'Desert East Wing ES'),
    ('Desert East Wing Key Door EN', 'Desert Compass Key Door WN'),
    ('Desert North Hall NW', 'Desert Map SW'),
    ('Desert North Hall NE', 'Desert Map SE'),
    ('Desert Arrow Pot Corner NW', 'Desert Trap Room SW'),
    ('Desert Sandworm Corner NE', 'Desert Bonk Torch SE'),
    ('Desert Sandworm Corner WS', 'Desert Circle of Pots ES'),
    ('Desert Circle of Pots NW', 'Desert Big Chest SW'),
    ('Desert West Wing WS', 'Desert West Lobby ES'),
    ('Desert Fairy Fountain SW', 'Desert West Lobby NW'),
    ('Desert Back Lobby NW', 'Desert Tiles 1 SW'),
    ('Desert Bridge SW', 'Desert Four Statues NW'),
    ('Desert Four Statues ES', 'Desert Beamos Hall WS'),
    ('Desert Tiles 2 NE', 'Desert Wall Slide SE'),
    ('Hera Tile Room EN', 'Hera Tridorm WN'),
    ('Hera Tridorm SE', 'Hera Torches NE'),
    ('Hera Beetles WS', 'Hera Startile Corner ES'),
    ('Hera Startile Corner NW', 'Hera Startile Wide SW'),
    ('Tower Lobby NW', 'Tower Gold Knights SW'),
    ('Tower Gold Knights EN', 'Tower Room 03 WN'),
    ('Tower Lone Statue WN', 'Tower Dark Maze EN'),
    ('Tower Dark Maze ES', 'Tower Dark Chargers WS'),
    ('Tower Dual Statues WS', 'Tower Dark Pits ES'),
    ('Tower Dark Pits EN', 'Tower Dark Archers WN'),
    ('Tower Red Spears WN', 'Tower Red Guards EN'),
    ('Tower Red Guards SW', 'Tower Circle of Pots NW'),
    ('Tower Circle of Pots ES', 'Tower Pacifist Run WS'),
    ('Tower Push Statue WS', 'Tower Catwalk ES'),
    ('Tower Antechamber NW', 'Tower Altar SW'),
    ('PoD Lobby N', 'PoD Middle Cage S'),
    ('PoD Lobby NW', 'PoD Left Cage SW'),
    ('PoD Lobby NE', 'PoD Middle Cage SE'),
    ('PoD Warp Hint SE', 'PoD Jelly Hall NE'),
    ('PoD Jelly Hall NW', 'PoD Mimics 1 SW'),
    ('PoD Falling Bridge EN', 'PoD Compass Room WN'),
    ('PoD Compass Room SE', 'PoD Harmless Hellway NE'),
    ('PoD Mimics 2 NW', 'PoD Bow Statue SW'),
    ('PoD Dark Pegs WN', 'PoD Lonely Turtle EN'),
    ('PoD Lonely Turtle SW', 'PoD Turtle Party NW'),
    ('PoD Turtle Party ES', 'PoD Callback WS'),
    ('Swamp Trench 1 Nexus N', 'Swamp Trench 1 Alcove S'),
    ('Swamp Trench 1 Key Ledge NW', 'Swamp Hammer Switch SW'),
    ('Swamp Donut Top SE', 'Swamp Donut Bottom NE'),
    ('Swamp Donut Bottom NW', 'Swamp Compass Donut SW'),
    ('Swamp Crystal Switch SE', 'Swamp Shortcut NE'),
    ('Swamp Trench 2 Blocks N', 'Swamp Trench 2 Alcove S'),
    ('Swamp Push Statue NW', 'Swamp Shooters SW'),
    ('Swamp Push Statue NE', 'Swamp Right Elbow SE'),
    ('Swamp Shooters EN', 'Swamp Left Elbow WN'),
    ('Swamp Drain WN', 'Swamp Basement Shallows EN'),
    ('Swamp Flooded Room WS', 'Swamp Basement Shallows ES'),
    ('Swamp Waterfall Room NW', 'Swamp Refill SW'),
    ('Swamp Waterfall Room NE', 'Swamp Behind Waterfall SE'),
    ('Swamp C SE', 'Swamp Waterway NE'),
    ('Swamp Waterway N', 'Swamp I S'),
    ('Swamp Waterway NW', 'Swamp T SW'),
    ('Skull 1 Lobby ES', 'Skull Map Room WS'),
    ('Skull Pot Circle WN', 'Skull Pull Switch EN'),
    ('Skull Pull Switch S', 'Skull Big Chest N'),
    ('Skull Left Drop ES', 'Skull Compass Room WS'),
    ('Skull 2 East Lobby NW', 'Skull Big Key SW'),
    ('Skull Big Key WN', 'Skull Lone Pot EN'),
    ('Skull Small Hall WS', 'Skull 2 West Lobby ES'),
    ('Skull 2 West Lobby NW', 'Skull X Room SW'),
    ('Skull 3 Lobby EN', 'Skull East Bridge WN'),
    ('Skull East Bridge WS', 'Skull West Bridge Nook ES'),
    ('Skull Star Pits ES', 'Skull Torch Room WS'),
    ('Skull Torch Room WN', 'Skull Vines EN'),
    ('Skull Spike Corner ES', 'Skull Final Drop WS'),
    ('Thieves Hallway WS', 'Thieves Pot Alcove Mid ES'),
    ('Thieves Conveyor Maze SW', 'Thieves Pot Alcove Top NW'),
    ('Thieves Conveyor Maze EN', 'Thieves Hallway WN'),
    ('Thieves Spike Track NE', 'Thieves Triple Bypass SE'),
    ('Thieves Spike Track WS', 'Thieves Hellway Crystal ES'),
    ('Thieves Hellway Crystal EN', 'Thieves Triple Bypass WN'),
    ('Thieves Attic ES', 'Thieves Cricket Hall Left WS'),
    ('Thieves Cricket Hall Right ES', 'Thieves Attic Window WS'),
    ('Thieves Blocked Entry SW', 'Thieves Lonely Zazak NW'),
    ('Thieves Lonely Zazak ES', 'Thieves Blind\'s Cell WS'),
    ('Thieves Conveyor Bridge WS', 'Thieves Big Chest Room ES'),
    ('Thieves Conveyor Block WN', 'Thieves Trap EN'),
    ('Ice Lobby WS', 'Ice Jelly Key ES'),
    ('Ice Floor Switch ES', 'Ice Cross Left WS'),
    ('Ice Cross Top NE', 'Ice Bomb Drop SE'),
    ('Ice Pengator Switch ES', 'Ice Dead End WS'),
    ('Ice Stalfos Hint SE', 'Ice Conveyor NE'),
    ('Ice Bomb Jump EN', 'Ice Narrow Corridor WN'),
    ('Ice Spike Cross WS', 'Ice Firebar ES'),
    ('Ice Spike Cross NE', 'Ice Falling Square SE'),
    ('Ice Hammer Block ES', 'Ice Tongue Pull WS'),
    ('Ice Freezors Ledge ES', 'Ice Tall Hint WS'),
    ('Ice Hookshot Balcony SW', 'Ice Spikeball NW'),
    ('Ice Crystal Right NE', 'Ice Backwards Room SE'),
    ('Ice Crystal Left WS', 'Ice Big Chest View ES'),
    ('Ice Anti-Fairy SE', 'Ice Switch Room NE'),
    ('Mire Lone Shooter ES', 'Mire Falling Bridge WS'),  # technically one-way
    ('Mire Falling Bridge W', 'Mire Failure Bridge E'),  # technically one-way
    ('Mire Falling Bridge WN', 'Mire Map Spike Side EN'),  # technically one-way
    ('Mire Hidden Shooters WS', 'Mire Cross ES'),  # technically one-way
    ('Mire Hidden Shooters NE', 'Mire Minibridge SE'),
    ('Mire Spikes NW', 'Mire Ledgehop SW'),
    ('Mire Spike Barrier ES', 'Mire Square Rail WS'),
    ('Mire Square Rail NW', 'Mire Lone Warp SW'),
    ('Mire Wizzrobe Bypass WN', 'Mire Compass Room EN'),  # technically one-way
    ('Mire Conveyor Crystal WS', 'Mire Tile Room ES'),
    ('Mire Tile Room NW', 'Mire Compass Room SW'),
    ('Mire Neglected Room SE', 'Mire Chest View NE'),
    ('Mire BK Chest Ledge WS', 'Mire Warping Pool ES'),  # technically one-way
    ('Mire Torches Top SW', 'Mire Torches Bottom NW'),
    ('Mire Torches Bottom WS', 'Mire Attic Hint ES'),
    ('Mire Dark Shooters SE', 'Mire Key Rupees NE'),
    ('Mire Dark Shooters SW', 'Mire Block X NW'),
    ('Mire Tall Dark and Roomy WS', 'Mire Crystal Right ES'),
    ('Mire Tall Dark and Roomy WN', 'Mire Shooter Rupees EN'),
    ('Mire Crystal Mid NW', 'Mire Crystal Top SW'),
    ('TR Tile Room NE', 'TR Refill SE'),
    ('TR Pokey 1 NW', 'TR Chain Chomps SW'),
    ('TR Twin Pokeys EN', 'TR Dodgers WN'),
    ('TR Twin Pokeys SW', 'TR Hallway NW'),
    ('TR Hallway ES', 'TR Big View WS'),
    ('TR Big Chest NE', 'TR Dodgers SE'),
    ('TR Dash Room ES', 'TR Tongue Pull WS'),
    ('TR Dash Room NW', 'TR Crystaroller SW'),
    ('TR Tongue Pull NE', 'TR Rupees SE'),
    ('GT Torch EN', 'GT Hope Room WN'),
    ('GT Torch SW', 'GT Big Chest NW'),
    ('GT Tile Room EN', 'GT Speed Torch WN'),
    ('GT Speed Torch WS', 'GT Pots n Blocks ES'),
    ('GT Crystal Conveyor WN', 'GT Compass Room EN'),
    ('GT Conveyor Cross WN', 'GT Hookshot EN'),
    ('GT Hookshot ES', 'GT Map Room WS'),
    ('GT Double Switch EN', 'GT Spike Crystals WN'),
    ('GT Firesnake Room SW', 'GT Warp Maze (Rails) NW'),
    ('GT Ice Armos NE', 'GT Big Key Room SE'),
    ('GT Ice Armos WS', 'GT Four Torches ES'),
    ('GT Four Torches NW', 'GT Fairy Abyss SW'),
    ('GT Crystal Paths SW', 'GT Mimics 1 NW'),
    ('GT Mimics 1 ES', 'GT Mimics 2 WS'),
    ('GT Mimics 2 NE', 'GT Dash Hall SE'),
    ('GT Cannonball Bridge SE', 'GT Refill NE'),
    ('GT Gauntlet 1 WN', 'GT Gauntlet 2 EN'),
    ('GT Gauntlet 2 SW', 'GT Gauntlet 3 NW'),
    ('GT Gauntlet 4 SW', 'GT Gauntlet 5 NW'),
    ('GT Beam Dash WS', 'GT Lanmolas 2 ES'),
    ('GT Lanmolas 2 NW', 'GT Quad Pot SW'),
    ('GT Wizzrobes 1 SW', 'GT Dashing Bridge NW'),
    ('GT Dashing Bridge NE', 'GT Wizzrobes 2 SE'),
    ('GT Torch Cross ES', 'GT Staredown WS'),
    ('GT Falling Torches NE', 'GT Mini Helmasaur Room SE'),
    ('GT Mini Helmasaur Room WN', 'GT Bomb Conveyor EN'),
    ('GT Bomb Conveyor SW', 'GT Crystal Circles NW')
]

key_doors = [
    ('Sewers Key Rat Key Door N', 'Sewers Secret Room Key Door S'),
    ('Sewers Dark Cross Key Door N', 'Sewers Water S'),
    ('Eastern Dark Square Key Door WN', 'Eastern Cannonball Ledge Key Door EN'),
    ('Eastern Darkness Up Stairs', 'Eastern Attic Start Down Stairs'),
    ('Eastern Big Key NE', 'Eastern Hint Tile Blocked Path SE'),
    ('Eastern Darkness S', 'Eastern Courtyard N'),
    ('Desert East Wing Key Door EN', 'Desert Compass Key Door WN'),
    ('Desert Tiles 1 Up Stairs', 'Desert Bridge Down Stairs'),
    ('Desert Beamos Hall NE', 'Desert Tiles 2 SE'),
    ('Desert Tiles 2 NE', 'Desert Wall Slide SE'),
    ('Desert Wall Slide NW', 'Desert Boss SW'),
    ('Hera Lobby Key Stairs', 'Hera Tile Room Up Stairs'),
    ('Hera Startile Corner NW', 'Hera Startile Wide SW'),
    ('PoD Middle Cage N', 'PoD Pit Room S'),
    ('PoD Arena Main NW', 'PoD Falling Bridge SW'),
    ('PoD Falling Bridge WN', 'PoD Dark Maze EN'),
]

default_small_key_doors = {
    'Hyrule Castle': [
        ('Sewers Key Rat Key Door N', 'Sewers Secret Room Key Door S'),
        ('Sewers Dark Cross Key Door N', 'Sewers Water S'),
        ('Hyrule Dungeon Map Room Key Door S', 'Hyrule Dungeon North Abyss Key Door N'),
        ('Hyrule Dungeon Armory Interior Key Door N', 'Hyrule Dungeon Armory Interior Key Door S')
    ],
    'Eastern Palace': [
        ('Eastern Dark Square Key Door WN', 'Eastern Cannonball Ledge Key Door EN'),
        'Eastern Darkness Up Stairs',
    ],
    'Desert Palace': [
        ('Desert East Wing Key Door EN', 'Desert Compass Key Door WN'),
        'Desert Tiles 1 Up Stairs',
        ('Desert Beamos Hall NE', 'Desert Tiles 2 SE'),
        ('Desert Tiles 2 NE', 'Desert Wall Slide SE'),
    ],
    'Tower of Hera': [
        'Hera Lobby Key Stairs'
    ],
    'Agahnims Tower': [
        'Tower Room 03 Up Stairs',
        ('Tower Dark Maze ES', 'Tower Dark Chargers WS'),
        'Tower Dark Archers Up Stairs',
        ('Tower Circle of Pots ES', 'Tower Pacifist Run WS'),
    ],
    'Palace of Darkness': [
        ('PoD Middle Cage N', 'PoD Pit Room S'),
        ('PoD Arena Main NW', 'PoD Falling Bridge SW'),
        ('PoD Falling Bridge WN', 'PoD Dark Maze EN'),
        'PoD Basement Ledge Up Stairs',
        ('PoD Compass Room SE', 'PoD Harmless Hellway NE'),
        ('PoD Dark Pegs WN', 'PoD Lonely Turtle EN')
    ],
    'Swamp Palace': [
        'Swamp Entrance Down Stairs',
        ('Swamp Pot Row WS', 'Swamp Trench 1 Approach ES'),
        ('Swamp Trench 1 Key Ledge NW', 'Swamp Hammer Switch SW'),
        ('Swamp Hub WN', 'Swamp Crystal Switch EN'),
        ('Swamp Hub North Ledge N', 'Swamp Push Statue S'),
        ('Swamp Waterway NW', 'Swamp T SW')
    ],
    'Skull Woods': [
        ('Skull 1 Lobby WS', 'Skull Pot Prison ES'),
        ('Skull Map Room SE', 'Skull Pinball NE'),
        ('Skull 2 West Lobby NW', 'Skull X Room SW'),
        ('Skull 3 Lobby NW', 'Skull Star Pits SW'),
        ('Skull Spike Corner ES', 'Skull Final Drop WS')
    ],
    'Thieves Town': [
        ('Thieves Hallway WS', 'Thieves Pot Alcove Mid ES'),
        'Thieves Spike Switch Up Stairs',
        ('Thieves Conveyor Bridge WS', 'Thieves Big Chest Room ES')
    ],
    'Ice Palace': [
        'Ice Jelly Key Down Stairs',
        ('Ice Conveyor SW', 'Ice Bomb Jump NW'),
        ('Ice Spike Cross ES', 'Ice Spike Room WS'),
        ('Ice Tall Hint SE', 'Ice Lonely Freezor NE'),
        'Ice Backwards Room Down Stairs',
        ('Ice Switch Room ES', 'Ice Refill WS')
    ],
    'Misery Mire': [
        ('Mire Hub WS', 'Mire Conveyor Crystal ES'),
        ('Mire Hub Right EN', 'Mire Map Spot WN'),
        ('Mire Spikes NW', 'Mire Ledgehop SW'),
        ('Mire Fishbone SE', 'Mire Spike Barrier NE'),
        ('Mire Conveyor Crystal WS', 'Mire Tile Room ES'),
        ('Mire Dark Shooters SE', 'Mire Key Rupees NE')
    ],
    'Turtle Rock': [
        ('TR Hub NW', 'TR Pokey 1 SW'),
        ('TR Pokey 1 NW', 'TR Chain Chomps SW'),
        'TR Chain Chomps Down Stairs',
        ('TR Pokey 2 ES', 'TR Lava Island WS'),
        'TR Crystaroller Down Stairs',
        ('TR Dash Bridge WS', 'TR Crystal Maze ES')
    ],
    'Ganons Tower': [
        ('GT Torch EN', 'GT Hope Room WN'),
        ('GT Tile Room EN', 'GT Speed Torch WN'),
        ('GT Hookshot ES', 'GT Map Room WS'),
        ('GT Double Switch EN', 'GT Spike Crystals WN'),
        ('GT Firesnake Room SW', 'GT Warp Maze (Rails) NW'),
        ('GT Conveyor Star Pits EN', 'GT Falling Bridge WN'),
        ('GT Mini Helmasaur Room WN', 'GT Bomb Conveyor EN'),
        ('GT Crystal Circles SW', 'GT Left Moldorm Ledge NW')
    ]
}

default_door_connections = [
    ('Hyrule Castle Lobby W', 'Hyrule Castle West Lobby E'),
    ('Hyrule Castle Lobby E', 'Hyrule Castle East Lobby W'),
    ('Hyrule Castle Lobby WN', 'Hyrule Castle West Lobby EN'),
    ('Hyrule Castle West Lobby N', 'Hyrule Castle West Hall S'),
    ('Hyrule Castle East Lobby N', 'Hyrule Castle East Hall S'),
    ('Hyrule Castle East Lobby NW', 'Hyrule Castle East Hall SW'),
    ('Hyrule Castle East Hall W', 'Hyrule Castle Back Hall E'),
    ('Hyrule Castle West Hall E', 'Hyrule Castle Back Hall W'),
    ('Hyrule Castle Throne Room N', 'Sewers Behind Tapestry S'),
    ('Hyrule Dungeon Guardroom N', 'Hyrule Dungeon Armory S'),
    ('Sewers Dark Cross Key Door N', 'Sewers Water S'),
    ('Sewers Water W', 'Sewers Key Rat E'),
    ('Sewers Key Rat Key Door N', 'Sewers Secret Room Key Door S'),
    ('Eastern Lobby Bridge N', 'Eastern Cannonball S'),
    ('Eastern Cannonball N', 'Eastern Courtyard Ledge S'),
    ('Eastern Cannonball Ledge WN', 'Eastern Big Key EN'),
    ('Eastern Cannonball Ledge Key Door EN', 'Eastern Dark Square Key Door WN'),
    ('Eastern Courtyard Ledge W', 'Eastern West Wing E'),
    ('Eastern Courtyard Ledge E', 'Eastern East Wing W'),
    ('Eastern Hint Tile EN', 'Eastern Courtyard WN'),
    ('Eastern Big Key NE', 'Eastern Hint Tile Blocked Path SE'),
    ('Eastern Courtyard EN', 'Eastern Map Valley WN'),
    ('Eastern Courtyard N', 'Eastern Darkness S'),
    ('Eastern Map Valley SW', 'Eastern Dark Square NW'),
    ('Eastern Attic Start WS', 'Eastern False Switches ES'),
    ('Eastern Cannonball Hell WS', 'Eastern Single Eyegore ES'),
    ('Desert Compass NW', 'Desert Cannonball S'),
    ('Desert Beamos Hall NE', 'Desert Tiles 2 SE'),
    ('PoD Middle Cage N', 'PoD Pit Room S'),
    ('PoD Pit Room NW', 'PoD Arena Main SW'),
    ('PoD Pit Room NE', 'PoD Arena Bridge SE'),
    ('PoD Arena Main NW', 'PoD Falling Bridge SW'),
    ('PoD Arena Crystals E', 'PoD Sexy Statue W'),
    ('PoD Mimics 1 NW', 'PoD Conveyor SW'),
    ('PoD Map Balcony WS', 'PoD Arena Ledge ES'),
    ('PoD Falling Bridge WN', 'PoD Dark Maze EN'),
    ('PoD Dark Maze E', 'PoD Big Chest Balcony W'),
    ('PoD Sexy Statue NW', 'PoD Mimics 2 SW'),
    ('Swamp Pot Row WN', 'Swamp Map Ledge EN'),
    ('Swamp Pot Row WS', 'Swamp Trench 1 Approach ES'),
    ('Swamp Trench 1 Departure WS', 'Swamp Hub ES'),
    ('Swamp Hammer Switch WN', 'Swamp Hub Dead Ledge EN'),
    ('Swamp Hub S', 'Swamp Donut Top N'),
    ('Swamp Hub WS', 'Swamp Trench 2 Pots ES'),
    ('Swamp Hub WN', 'Swamp Crystal Switch EN'),
    ('Swamp Hub North Ledge N', 'Swamp Push Statue S'),
    ('Swamp Trench 2 Departure WS', 'Swamp West Shallows ES'),
    ('Swamp Big Key Ledge WN', 'Swamp Barrier EN'),
    ('Swamp Basement Shallows NW', 'Swamp Waterfall Room SW'),
    ('Skull 1 Lobby WS', 'Skull Pot Prison ES'),
    ('Skull Map Room SE', 'Skull Pinball NE'),
    ('Skull Pinball WS', 'Skull Compass Room ES'),
    ('Skull Compass Room NE', 'Skull Pot Prison SE'),
    ('Skull 2 East Lobby WS', 'Skull Small Hall ES'),
    ('Skull 3 Lobby NW', 'Skull Star Pits SW'),
    ('Skull Vines NW', 'Skull Spike Corner SW'),
    ('Thieves Lobby E', 'Thieves Compass Room W'),
    ('Thieves Ambush E', 'Thieves Rail Ledge W'),
    ('Thieves Rail Ledge NW', 'Thieves Pot Alcove Bottom SW'),
    ('Thieves BK Corner NE', 'Thieves Hallway SE'),
    ('Thieves Pot Alcove Mid WS', 'Thieves Spike Track ES'),
    ('Thieves Hellway NW', 'Thieves Spike Switch SW'),
    ('Thieves Triple Bypass EN', 'Thieves Conveyor Maze WN'),
    ('Thieves Basement Block WN', 'Thieves Conveyor Bridge EN'),
    ('Thieves Lonely Zazak WS', 'Thieves Conveyor Bridge ES'),
    ('Ice Cross Bottom SE', 'Ice Compass Room NE'),
    ('Ice Cross Right ES', 'Ice Pengator Switch WS'),
    ('Ice Conveyor SW', 'Ice Bomb Jump NW'),
    ('Ice Pengator Trap NE', 'Ice Spike Cross SE'),
    ('Ice Spike Cross ES', 'Ice Spike Room WS'),
    ('Ice Tall Hint SE', 'Ice Lonely Freezor NE'),
    ('Ice Tall Hint EN', 'Ice Hookshot Ledge WN'),
    ('Iced T EN', 'Ice Catwalk WN'),
    ('Ice Catwalk NW', 'Ice Many Pots SW'),
    ('Ice Many Pots WS', 'Ice Crystal Right ES'),
    ('Ice Switch Room ES', 'Ice Refill WS'),
    ('Ice Switch Room SE', 'Ice Antechamber NE'),
    ('Mire 2 NE', 'Mire Hub SE'),
    ('Mire Hub ES', 'Mire Lone Shooter WS'),
    ('Mire Hub E', 'Mire Failure Bridge W'),
    ('Mire Hub NE', 'Mire Hidden Shooters SE'),
    ('Mire Hub WN', 'Mire Wizzrobe Bypass EN'),
    ('Mire Hub WS', 'Mire Conveyor Crystal ES'),
    ('Mire Hub Right EN', 'Mire Map Spot WN'),
    ('Mire Hub Top NW', 'Mire Cross SW'),
    ('Mire Hidden Shooters ES', 'Mire Spikes WS'),
    ('Mire Minibridge NE', 'Mire Right Bridge SE'),
    ('Mire BK Door Room EN', 'Mire Ledgehop WN'),
    ('Mire BK Door Room N', 'Mire Left Bridge S'),
    ('Mire Spikes SW', 'Mire Crystal Dead End NW'),
    ('Mire Ledgehop NW', 'Mire Bent Bridge SW'),
    ('Mire Bent Bridge W', 'Mire Over Bridge E'),
    ('Mire Over Bridge W', 'Mire Fishbone E'),
    ('Mire Fishbone SE', 'Mire Spike Barrier NE'),
    ('Mire Spike Barrier SE', 'Mire Wizzrobe Bypass NE'),
    ('Mire Conveyor Crystal SE', 'Mire Neglected Room NE'),
    ('Mire Tile Room SW', 'Mire Conveyor Barrier NW'),
    ('Mire Block X WS', 'Mire Tall Dark and Roomy ES'),
    ('Mire Crystal Left WS', 'Mire Falling Foes ES'),
    ('TR Lobby Ledge NE', 'TR Hub SE'),
    ('TR Compass Room NW', 'TR Hub SW'),
    ('TR Hub ES', 'TR Torches Ledge WS'),
    ('TR Hub EN', 'TR Torches WN'),
    ('TR Hub NW', 'TR Pokey 1 SW'),
    ('TR Hub NE', 'TR Tile Room SE'),
    ('TR Torches NW', 'TR Roller Room SW'),
    ('TR Pipe Pit WN', 'TR Lava Dual Pipes EN'),
    ('TR Lava Island ES', 'TR Pipe Ledge WS'),
    ('TR Lava Dual Pipes SW', 'TR Twin Pokeys NW'),
    ('TR Lava Dual Pipes WN', 'TR Pokey 2 EN'),
    ('TR Pokey 2 ES', 'TR Lava Island WS'),
    ('TR Dodgers NE', 'TR Lava Escape SE'),
    ('TR Lava Escape NW', 'TR Dash Room SW'),
    ('TR Hallway WS', 'TR Lazy Eyes ES'),
    ('TR Dark Ride SW', 'TR Dash Bridge NW'),
    ('TR Dash Bridge SW', 'TR Eye Bridge NW'),
    ('TR Dash Bridge WS', 'TR Crystal Maze ES'),
    ('GT Torch WN', 'GT Conveyor Cross EN'),
    ('GT Hope Room EN', 'GT Tile Room WN'),
    ('GT Big Chest SW', 'GT Invisible Catwalk NW'),
    ('GT Bob\'s Room SE', 'GT Invisible Catwalk NE'),
    ('GT Speed Torch NE', 'GT Petting Zoo SE'),
    ('GT Speed Torch SE', 'GT Crystal Conveyor NE'),
    ('GT Warp Maze (Pits) ES', 'GT Invisible Catwalk WS'),
    ('GT Hookshot NW', 'GT DMs Room SW'),
    ('GT Hookshot SW', 'GT Double Switch NW'),
    ('GT Warp Maze (Rails) WS', 'GT Randomizer Room ES'),
    ('GT Conveyor Star Pits EN', 'GT Falling Bridge WN'),
    ('GT Falling Bridge WS', 'GT Hidden Star ES'),
    ('GT Dash Hall NE', 'GT Hidden Spikes SE'),
    ('GT Hidden Spikes EN', 'GT Cannonball Bridge WN'),
    ('GT Gauntlet 3 SW', 'GT Gauntlet 4 NW'),
    ('GT Gauntlet 5 WS', 'GT Beam Dash ES'),
    ('GT Wizzrobes 2 NE', 'GT Conveyor Bridge SE'),
    ('GT Conveyor Bridge EN', 'GT Torch Cross WN'),
    ('GT Crystal Circles SW', 'GT Left Moldorm Ledge NW')
]

default_one_way_connections = [
    ('Sewers Pull Switch S', 'Sanctuary N'),
    ('Eastern Duo Eyegores NE', 'Eastern Boss SE'),
    ('Desert Wall Slide NW', 'Desert Boss SW'),
    ('Tower Altar NW', 'Tower Agahnim 1 SW'),
    ('PoD Harmless Hellway SE', 'PoD Arena Main NE'),
    ('PoD Dark Alley NE', 'PoD Boss SE'),
    ('Swamp T NW', 'Swamp Boss SW'),
    ('Thieves Hallway NE', 'Thieves Boss SE'),
    ('Mire Antechamber NW', 'Mire Boss SW'),
    ('TR Final Abyss NW', 'TR Boss SW'),
    ('GT Invisible Bridges WS', 'GT Invisible Catwalk ES'),
    ('GT Validation WS', 'GT Frozen Over ES'),
    ('GT Brightly Lit Hall NW', 'GT Agahnim 2 SW')
]

# For crossed
# offset from 0x122e17, sram storage, write offset from compass_w_addr, 0 = jmp or # of nops, dungeon_id
compass_data = {
    'Hyrule Castle': (0x1, 0xc0, 0x16, 0, 0x02),
    'Eastern Palace': (0x1C, 0xc1, 0x28, 0, 0x04),
    'Desert Palace': (0x35, 0xc2, 0x4a, 0, 0x06),
    'Agahnims Tower': (0x51, 0xc3, 0x5c, 0, 0x08),
    'Swamp Palace': (0x6A, 0xc4, 0x7e, 0, 0x0a),
    'Palace of Darkness': (0x83, 0xc5, 0xa4, 0, 0x0c),
    'Misery Mire': (0x9C, 0xc6, 0xca, 0, 0x0e),
    'Skull Woods': (0xB5, 0xc7, 0xf0, 0, 0x10),
    'Ice Palace': (0xD0, 0xc8, 0x102, 0, 0x12),
    'Tower of Hera': (0xEB, 0xc9, 0x114, 0, 0x14),
    'Thieves Town': (0x106, 0xca, 0x138, 0, 0x16),
    'Turtle Rock': (0x11F, 0xcb, 0x15e, 0, 0x18),
    'Ganons Tower': (0x13A, 0xcc, 0x170, 2, 0x1a)
}

# For compass boss indicator
boss_indicator = {
    'Eastern Palace': (0x04, 'Eastern Boss SE'),
    'Desert Palace': (0x06, 'Desert Boss SW'),
    'Agahnims Tower': (0x08, 'Tower Agahnim 1 SW'),
    'Swamp Palace': (0x0a, 'Swamp Boss SW'),
    'Palace of Darkness': (0x0c, 'PoD Boss SE'),
    'Misery Mire': (0x0e, 'Mire Boss SW'),
    'Skull Woods': (0x10, 'Skull Spike Corner SW'),
    'Ice Palace': (0x12, 'Ice Antechamber NE'),
    'Tower of Hera': (0x14, 'Hera Boss Down Stairs'),
    'Thieves Town': (0x16, 'Thieves Boss SE'),
    'Turtle Rock': (0x18, 'TR Boss SW'),
    'Ganons Tower': (0x1a, 'GT Agahnim 2 SW')
}

# tuples: (non-boss, boss)
# see Utils for other notes
palette_map = {
    'Hyrule Castle': (0x0, None),
    'Eastern Palace': (0xb, None),
    'Desert Palace': (0x9, 0x4, 'Desert Boss SW'),
    'Agahnims Tower': (0x0, 0xc, 'Tower Agahnim 1 SW'),  # ancillary 0x26 for F1, F4
    'Swamp Palace': (0xa, 0x8, 'Swamp Boss SW'),
    'Palace of Darkness': (0xf, 0x10, 'PoD Boss SE'),
    'Misery Mire': (0x11, 0x12, 'Mire Boss SW'),
    'Skull Woods': (0xd, 0xe, 'Skull Spike Corner SW'),
    'Ice Palace': (0x13, 0x14, 'Ice Antechamber NE'),
    'Tower of Hera': (0x6, None),
    'Thieves Town': (0x17, None),  # the attic uses 0x23
    'Turtle Rock': (0x18, 0x19, 'TR Boss SW'),
    'Ganons Tower': (0x28, 0x1b, 'GT Agahnim 2 SW'),  # other palettes: 0x1a (other) 0x24 (Gauntlet - Lanmo) 0x25 (conveyor-torch-wizzrode moldorm pit f5?)
}

# implications:
# pipe room -> where lava chest is
# dark alley -> where pod basement is
# conveyor star or hidden star -> where DMs room is
# falling bridge -> where Rando room is
# petting zoo -> where firesnake is
# basement cage -> where tile room is
# bob's room -> where big chest/hope/torch are
# invis bridges -> compass room

palette_non_influencers = {
    'PoD Shooter Room Up Stairs', 'TR Lava Dual Pipes EN', 'TR Lava Dual Pipes WN', 'TR Lava Dual Pipes SW',
    'TR Lava Escape SE', 'TR Lava Escape NW', 'PoD Arena Ledge ES', 'Swamp Big Key Ledge WN', 'Swamp Hub Dead Ledge EN',
    'Swamp Map Ledge EN', 'Skull Pot Prison ES', 'Skull Pot Prison SE', 'PoD Dark Alley NE', 'GT Conveyor Star Pits EN',
    'GT Hidden Star ES', 'GT Falling Bridge WN', 'GT Falling Bridge WS', 'GT Petting Zoo SE',
    'Hera Basement Cage Up Stairs', "GT Bob's Room SE", 'GT Warp Maze (Pits) ES', 'GT Invisible Bridges WS',
    'Mire Over Bridge E', 'Mire Over Bridge W', 'Eastern Courtyard Ledge S', 'Eastern Courtyard Ledge W',
    'Eastern Courtyard Ledge E', 'Eastern Map Valley WN', 'Eastern Map Valley SW', 'Mire BK Door Room EN',
    'Mire BK Door Room N', 'TR Tile Room SE', 'TR Tile Room NE', 'TR Refill SE', 'Eastern Cannonball Ledge WN',
    'Eastern Cannonball Ledge Key Door EN', 'Mire Neglected Room SE', 'Mire Neglected Room NE', 'Mire Chest View NE',
    'TR Compass Room NW', 'Desert Dead End Edge', 'Hyrule Dungeon South Abyss Catwalk North Edge',
    'Hyrule Dungeon South Abyss Catwalk West Edge'
}


portal_map = {
    'Sanctuary': ('Sanctuary', 'Sanctuary Exit', 'Enter HC (Sanc)'),
    'Hyrule Castle West': ('Hyrule Castle Entrance (West)', 'Hyrule Castle Exit (West)', 'Enter HC (West)'),
    'Hyrule Castle South': ('Hyrule Castle Entrance (South)', 'Hyrule Castle Exit (South)', 'Enter HC (South)'),
    'Hyrule Castle East': ('Hyrule Castle Entrance (East)', 'Hyrule Castle Exit (East)', 'Enter HC (East)'),
    'Eastern': ('Eastern Palace', 'Eastern Palace Exit', 'Enter Eastern Palace'),
    'Desert West': ('Desert Palace Entrance (West)', 'Desert Palace Exit (West)', 'Enter Desert (West)'),
    'Desert South': ('Desert Palace Entrance (South)', 'Desert Palace Exit (South)', 'Enter Desert (South)'),
    'Desert East': ('Desert Palace Entrance (East)', 'Desert Palace Exit (East)', 'Enter Desert (East)'),
    'Desert Back': ('Desert Palace Entrance (North)', 'Desert Palace Exit (North)', 'Enter Desert (North)'),
    'Turtle Rock Lazy Eyes': ('Dark Death Mountain Ledge (West)', 'Turtle Rock Ledge Exit (West)', 'Enter Turtle Rock (Lazy Eyes)'),
    'Turtle Rock Eye Bridge': ('Turtle Rock Isolated Ledge Entrance', 'Turtle Rock Isolated Ledge Exit', 'Enter Turtle Rock (Laser Bridge)'),
    'Turtle Rock Chest': ('Dark Death Mountain Ledge (East)', 'Turtle Rock Ledge Exit (East)', 'Enter Turtle Rock (Chest)'),
    'Agahnims Tower': ('Agahnims Tower', 'Agahnims Tower Exit', 'Enter Agahnims Tower'),
    'Swamp': ('Swamp Palace', 'Swamp Palace Exit', 'Enter Swamp'),
    'Palace of Darkness': ('Palace of Darkness', 'Palace of Darkness Exit', 'Enter Palace of Darkness'),
    'Mire': ('Misery Mire', 'Misery Mire Exit', 'Enter Misery Mire'),
    'Skull 2 West': ('Skull Woods Second Section Door (West)', 'Skull Woods Second Section Exit (West)', 'Enter Skull Woods 2 (West)'),
    'Skull 2 East': ('Skull Woods Second Section Door (East)', 'Skull Woods Second Section Exit (East)', 'Enter Skull Woods 2 (East)'),
    'Skull 1': ('Skull Woods First Section Door', 'Skull Woods First Section Exit', 'Enter Skull Woods 1'),
    'Skull 3': ('Skull Woods Final Section', 'Skull Woods Final Section Exit', 'Enter Skull Woods 3'),
    'Ice': ('Ice Palace', 'Ice Palace Exit', 'Enter Ice Palace'),
    'Hera': ('Tower of Hera', 'Tower of Hera Exit', 'Enter Hera'),
    'Thieves Town': ('Thieves Town', 'Thieves Town Exit', 'Enter Thieves Town'),
    'Turtle Rock Main': ('Turtle Rock', 'Turtle Rock Exit (Front)', 'Enter Turtle Rock (Main)'),
    'Ganons Tower': ('Ganons Tower', 'Ganons Tower Exit', 'Enter Ganons Tower'),
}

split_portals = {
    'Desert Palace': ['Back', 'Main'],
    'Skull Woods': ['1', '2', '3']
}

split_portal_defaults = {
    'Desert Palace': {
        'Desert Back Lobby': 'Back',
        'Desert Main Lobby': 'Main',
        'Desert West Lobby': 'Main',
        'Desert East Lobby': 'Main'
    },
    'Skull Woods': {
        'Skull 1 Lobby': '1',
        'Skull 2 East Lobby': '2',
        'Skull 2 West Lobby': '2',
        'Skull 3 Lobby': '3'
    }
}

bomb_dash_counts = {
    'Hyrule Castle': (0, 2),
    'Eastern Palace': (0, 0),
    'Desert Palace': (0, 0),
    'Agahnims Tower': (0, 0),
    'Swamp Palace': (2, 0),
    'Palace of Darkness': (3, 2),
    'Misery Mire': (2, 0),
    'Skull Woods': (2, 0),
    'Ice Palace': (0, 0),
    'Tower of Hera': (0, 0),
    'Thieves Town': (1, 1),
    'Turtle Rock': (0, 2),  # 2 bombs kind of for entrances
    'Ganons Tower': (2, 1)
}


