import RaceRandom as random
from collections import defaultdict, deque
import logging
import time
from enum import unique, Flag
from typing import DefaultDict, Dict, List
from itertools import chain

from BaseClasses import RegionType, Region, Door, DoorType, Sector, CrystalBarrier, DungeonInfo, dungeon_keys
from BaseClasses import PotFlags, LocationType, Direction, KeyRuleType
from Doors import reset_portals
from Dungeons import dungeon_regions, region_starts, standard_starts, split_region_starts
from Dungeons import dungeon_bigs, dungeon_hints
from Items import ItemFactory
from RoomData import DoorKind, PairedDoor, reset_rooms
from source.dungeon.DungeonStitcher import GenerationException, generate_dungeon
from source.dungeon.DungeonStitcher import ExplorationState as ExplorationState2
from DungeonGenerator import ExplorationState, convert_regions, determine_required_paths, drop_entrances
from DungeonGenerator import create_dungeon_builders, split_dungeon_builder, simple_dungeon_builder, default_dungeon_entrances
from DungeonGenerator import dungeon_portals, dungeon_drops, connect_doors, count_reserved_locations
from DungeonGenerator import valid_region_to_explore
from KeyDoorShuffle import analyze_dungeon, build_key_layout, validate_key_layout, determine_prize_lock
from KeyDoorShuffle import validate_bk_layout, DoorRules
from Utils import ncr, kth_combination


def link_doors(world, player):
    orig_swamp_patch = world.swamp_patch_required[player]
    attempt, valid = 1, False
    while not valid:
        try:
            link_doors_main(world, player)
            valid = True
        except GenerationException as e:
            logging.getLogger('').debug(f'Irreconcilable generation. {str(e)} Starting a new attempt.')
            attempt += 1
            if attempt > 10:
                raise Exception('Could not create world in 10 attempts. Generation algorithms need more work', e)
            for door in world.doors:
                if door.player == player:
                    door.dest = None
                    door.entranceFlag = False
                    ent = door.entrance
                    if (door.type != DoorType.Logical or door.controller) and ent.connected_region is not None:
                        ent.connected_region.entrances = [x for x in ent.connected_region.entrances if x != ent]
                        ent.connected_region = None
            for portal in world.dungeon_portals[player]:
                disconnect_portal(portal, world, player)
            reset_portals(world, player)
            reset_rooms(world, player)
            world.get_door("Skull Pinball WS", player).no_exit()
            world.swamp_patch_required[player] = orig_swamp_patch
            link_doors_prep(world, player)


def link_doors_prep(world, player):
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

    if world.intensity[player] < 2:
        for entrance, ext in open_edges:
            connect_two_way(world, entrance, ext, player)
        for entrance, ext in straight_staircases:
            connect_two_way(world, entrance, ext, player)
        for entrance, ext in ladders:
            connect_two_way(world, entrance, ext, player)

    if world.intensity[player] < 3 or world.doorShuffle[player] == 'vanilla':
        mirror_route = world.get_entrance('Sanctuary Mirror Route', player)
        mr_door = mirror_route.door
        sanctuary = mirror_route.parent_region
        if mirror_route in sanctuary.exits:
            sanctuary.exits.remove(mirror_route)
        world.remove_entrance(mirror_route, player)
        world.remove_door(mr_door, player)

    connect_custom(world, player)

    find_inaccessible_regions(world, player)

    create_dungeon_pool(world, player)
    if world.intensity[player] >= 3 and world.doorShuffle[player] != 'vanilla':
        choose_portals(world, player)
    else:
        if world.shuffle[player] == 'vanilla':
            if world.mode[player] == 'standard':
                world.get_portal('Sanctuary', player).destination = True
            world.get_portal('Desert East', player).destination = True
            if world.mode[player] == 'inverted':
                world.get_portal('Desert West', player).destination = True
            else:
                world.get_portal('Skull 2 West', player).destination = True
                world.get_portal('Turtle Rock Lazy Eyes', player).destination = True
                world.get_portal('Turtle Rock Eye Bridge', player).destination = True
        else:
            analyze_portals(world, player)
        for portal in world.dungeon_portals[player]:
            connect_portal(portal, world, player)

    if not world.doorShuffle[player] == 'vanilla':
        fix_big_key_doors_with_ugly_smalls(world, player)
    else:
        unmark_ugly_smalls(world, player)
    if world.doorShuffle[player] == 'vanilla':
        for entrance, ext in open_edges:
            connect_two_way(world, entrance, ext, player)
        for entrance, ext in straight_staircases:
            connect_two_way(world, entrance, ext, player)
        for exitName, regionName in vanilla_logical_connections:
            connect_simple_door(world, exitName, regionName, player)
        for entrance, ext in spiral_staircases:
            connect_two_way(world, entrance, ext, player)
        for entrance, ext in ladders:
            connect_two_way(world, entrance, ext, player)
        for entrance, ext in default_door_connections:
            connect_two_way(world, entrance, ext, player)
        for ent, ext in default_one_way_connections:
            connect_one_way(world, ent, ext, player)
        vanilla_key_logic(world, player)


def create_dungeon_pool(world, player):
    pool = None
    if world.doorShuffle[player] == 'basic':
        pool = [([name], regions) for name, regions in dungeon_regions.items()]
    elif world.doorShuffle[player] == 'paired':
        dungeon_pool = list(dungeon_regions.keys())
        groups = []
        while dungeon_pool:
            if len(dungeon_pool) == 3:
                groups.append(list(dungeon_pool))
                dungeon_pool.clear()
            else:
                choice_a = random.choice(dungeon_pool)
                dungeon_pool.remove(choice_a)
                choice_b = random.choice(dungeon_pool)
                dungeon_pool.remove(choice_b)
                groups.append([choice_a, choice_b])
        pool = [(group, list(chain.from_iterable([dungeon_regions[d] for d in group]))) for group in groups]
    elif world.doorShuffle[player] == 'partitioned':
        groups = [['Hyrule Castle', 'Eastern Palace', 'Desert Palace', 'Tower of Hera', 'Agahnims Tower'],
                  ['Palace of Darkness', 'Swamp Palace', 'Skull Woods', 'Thieves Town'],
                  ['Ice Palace', 'Misery Mire', 'Turtle Rock', 'Ganons Tower']]
        pool = [(group, list(chain.from_iterable([dungeon_regions[d] for d in group]))) for group in groups]
    elif world.doorShuffle[player] == 'crossed':
        pool = [(list(dungeon_regions.keys()), sum((r for r in dungeon_regions.values()), []))]
    elif world.doorShuffle[player] != 'vanilla':
        logging.getLogger('').error('Invalid door shuffle setting: %s' % world.doorShuffle[player])
        raise Exception('Invalid door shuffle setting: %s' % world.doorShuffle[player])
    world.dungeon_pool[player] = pool


def link_doors_main(world, player):
    pool = world.dungeon_pool[player]
    if pool:
        main_dungeon_pool(pool, world, player)
    if world.doorShuffle[player] != 'vanilla':
        create_door_spoiler(world, player)


def create_door_spoiler(world, player):
    logger = logging.getLogger('')
    shuffled_door_types = [DoorType.Normal, DoorType.SpiralStairs]
    if world.intensity[player] > 1:
        shuffled_door_types += [DoorType.Open, DoorType.StraightStairs, DoorType.Ladder]

    queue = deque(world.dungeon_layouts[player].values())
    while len(queue) > 0:
        builder = queue.popleft()
        std_flag = world.mode[player] == 'standard' and builder.name == 'Hyrule Castle' and world.shuffle[player] == 'vanilla'
        done = set()
        start_regions = set(convert_regions(builder.layout_starts, world, player))  # todo: set all_entrances for basic
        reg_queue = deque(start_regions)
        visited = set(start_regions)
        while len(reg_queue) > 0:
            next = reg_queue.pop()
            for ext in next.exits:
                door_a = ext.door
                connect = ext.connected_region
                if door_a and door_a.type in shuffled_door_types and door_a not in done:
                    done.add(door_a)

                    door_b = door_a.dest
                    if door_b and not isinstance(door_b, Region):
                        if world.decoupledoors[player]:
                            world.spoiler.set_door(door_a.name, door_b.name, 'entrance', player, builder.name)
                        else:
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
                if valid_connection(connect, std_flag, world, player) and connect not in visited:
                    visited.add(connect)
                    reg_queue.append(connect)


def valid_connection(region, std_flag, world, player):
    return region and (region.type == RegionType.Dungeon or region.name in world.inaccessible_regions[player] or
                      (std_flag and region.name == 'Hyrule Castle Ledge'))


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
    entrances_map, potentials, connections = determine_entrance_list(world, player)
    enabled_entrances = world.enabled_entrances[player] = {}
    builder_queue = deque(builders)
    last_key, loops = None, 0
    while len(builder_queue) > 0:
        builder = builder_queue.popleft()
        origin_list = entrances_map[builder.name]
        find_enabled_origins(builder.sectors, enabled_entrances, origin_list, entrances_map, builder.name)
        if len(origin_list) <= 0:
            if last_key == builder.name or loops > 1000:
                origin_name = (world.get_region(origin_list[0], player).entrances[0].parent_region.name
                               if len(origin_list) > 0 else 'no origin')
                raise GenerationException(f'Infinite loop detected for "{builder.name}" located at {origin_name}')
            builder_queue.append(builder)
            last_key = builder.name
            loops += 1
        else:
            find_new_entrances(builder.master_sector, entrances_map, connections, potentials,
                               enabled_entrances, world, player)
            start_regions = convert_regions(origin_list, world, player)
            doors = convert_key_doors(default_small_key_doors[builder.name], world, player)
            key_layout = build_key_layout(builder, start_regions, doors, {}, world, player)
            valid = validate_key_layout(key_layout, world, player)
            if not valid:
                logging.getLogger('').info('Vanilla key layout not valid %s', builder.name)
            builder.key_door_proposal = doors
            if player not in world.key_logic.keys():
                world.key_logic[player] = {}
            analyze_dungeon(key_layout, world, player)
            world.key_logic[player][builder.name] = key_layout.key_logic
            world.key_layout[player][builder.name] = key_layout
            log_key_logic(builder.name, key_layout.key_logic)
    # special adjustments for vanilla
    if world.keyshuffle[player] != 'universal':
        if world.mode[player] != 'standard' and world.dropshuffle[player] == 'none':
            # adjust hc doors
            def adjust_hc_door(door_rule):
                if door_rule.new_rules[KeyRuleType.WorstCase] == 3:
                    door_rule.new_rules[KeyRuleType.WorstCase] = 2
                    door_rule.small_key_num = 2

            rules = world.key_logic[player]['Hyrule Castle'].door_rules
            adjust_hc_door(rules['Sewers Secret Room Key Door S'])
            adjust_hc_door(rules['Hyrule Dungeon Map Room Key Door S'])
            adjust_hc_door(rules['Sewers Dark Cross Key Door N'])
        # adjust pod front door
        pod_front = world.key_logic[player]['Palace of Darkness'].door_rules['PoD Middle Cage N']
        if pod_front.new_rules[KeyRuleType.WorstCase] == 6:
            pod_front.new_rules[KeyRuleType.WorstCase] = 1
            pod_front.small_key_num = 1
        # adjust mire key logic - this currently cannot be done dynamically
        create_alternative_door_rules('Mire Hub Upper Blue Barrier', 2, 'Misery Mire', world, player)
        create_alternative_door_rules('Mire Hub Lower Blue Barrier', 2, 'Misery Mire', world, player)
        create_alternative_door_rules('Mire Hub Right Blue Barrier', 2, 'Misery Mire', world, player)
        create_alternative_door_rules('Mire Hub Top Blue Barrier', 2, 'Misery Mire', world, player)
        create_alternative_door_rules('Mire Hub Switch Blue Barrier N', 2, 'Misery Mire', world, player)
        create_alternative_door_rules('Mire Hub Switch Blue Barrier S', 2, 'Misery Mire', world, player)
        create_alternative_door_rules('Mire Map Spot Blue Barrier', 2, 'Misery Mire', world, player)
        create_alternative_door_rules('Mire Map Spike Side Blue Barrier', 2, 'Misery Mire', world, player)
        create_alternative_door_rules('Mire Crystal Dead End Left Barrier', 2, 'Misery Mire', world, player)
        create_alternative_door_rules('Mire Crystal Dead End Right Barrier', 2, 'Misery Mire', world, player)
        # gt logic? I'm unsure it needs adjusting


def create_alternative_door_rules(door, amount, dungeon, world, player):
    rules = DoorRules(0, True)
    world.key_logic[player][dungeon].door_rules[door] = rules
    rules.new_rules[KeyRuleType.CrystalAlternative] = amount
    world.get_door(door, player).alternative_crystal_rule = True



def validate_vanilla_reservation(dungeon, world, player):
    return validate_key_layout(world.key_layout[player][dungeon.name], world, player)


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
    if world.customizer and world.customizer.get_doors():
        custom_doors = world.customizer.get_doors()
        if player not in custom_doors:
            return
        custom_doors = custom_doors[player]
        if 'doors' not in custom_doors:
            return
        for door, dest in custom_doors['doors'].items():
            d = world.get_door(door, player)
            if d.type not in [DoorType.Interior, DoorType.Logical]:
                if isinstance(dest, str):
                    connect_two_way(world, door, dest, player)
                elif 'dest' in dest:
                    if 'one-way' in dest and dest['one-way']:
                        connect_one_way(world, door, dest['dest'], player)
                    else:
                        connect_two_way(world, door, dest['dest'], player)


def connect_simple_door(world, exit_name, region_name, player):
    region = world.get_region(region_name, player)
    world.get_entrance(exit_name, player).connect(region)
    d = world.check_for_door(exit_name, player)
    if d is not None:
        d.dest = region


def connect_simple_door_to_region(exit_door, region):
    exit_door.entrance.connect(region)
    exit_door.dest = region


def connect_door_only(world, exit_name, region, player):
    d = world.check_for_door(exit_name, player)
    if d is not None:
        d.dest = region


def connect_interior_doors(a, b, world, player):
    door_a = world.get_door(a, player)
    door_b = world.get_door(b, player)
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
    if x.dependents:
        for dep in x.dependents:
            connect_simple_door_to_region(dep, ext.parent_region)
    if y.dependents:
        for dep in y.dependents:
            connect_simple_door_to_region(dep, entrance.parent_region)


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
    if x.dependents:
        for dep in x.dependents:
            connect_simple_door_to_region(dep, ext.parent_region)

def unmark_ugly_smalls(world, player):
    for d in ['Eastern Hint Tile Blocked Path SE', 'Eastern Darkness S', 'Thieves Hallway SE', 'Mire Left Bridge S',
              'TR Lava Escape SE', 'GT Hidden Spikes SE']:
        door = world.get_door(d, player)
        door.smallKey = False


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
    if world.doorShuffle[player] != ['vanilla']:
        shuffle_flag = world.doorShuffle[player] != 'basic'
        allowed = {name: set(group[0]) for group in world.dungeon_pool[player] for name in group[0]}

        # key drops allow the big key in the right place in Desert Tiles 2
        bk_shuffle = world.bigkeyshuffle[player] or world.pottery[player] not in ['none', 'cave']
        std_flag = world.mode[player] == 'standard'
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
            hc_flag = std_flag and dungeon == 'Hyrule Castle'
            for portal in portal_list:
                placeholder = world.get_region(portal + ' Portal', player)
                portal_region = placeholder.exits[0].connected_region
                name = portal_region.name
                if portal_region.type == RegionType.LightWorld:
                    world.get_portal(portal, player).light_world = True
                if name in world.inaccessible_regions[player] or (hc_flag and portal != 'Hyrule Castle South'):
                    name_key = 'Desert Ledge' if name == 'Desert Ledge Keep' else name
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
                    raise Exception(f'No reachable entrances for {dungeon}')
            if len(reachable_portals) == 1:
                info.sole_entrance = reachable_portals[0]
            info_map[dungeon] = info

        master_door_list = [x for x in world.doors if x.player == player and x.portalAble]
        portal_assignment = defaultdict(list)
        shuffled_info = list(info_map.items())

        custom = customizer_portals(master_door_list, world, player)

        if shuffle_flag:
            random.shuffle(shuffled_info)
        for dungeon, info in shuffled_info:
            outstanding_portals = list(dungeon_portals[dungeon])
            hc_flag = std_flag and dungeon == 'Hyrule Castle'
            rupee_bow_flag = hc_flag and world.bow_mode[player].startswith('retro')  # rupee bow
            if hc_flag:
                sanc = world.get_portal('Sanctuary', player)
                sanc.destination = True
                clean_up_portal_assignment(portal_assignment, dungeon, sanc, master_door_list, outstanding_portals)
                for target_region, possible_portals in info.required_passage.items():
                    info.required_passage[target_region] = [x for x in possible_portals if x != sanc.name]
                info.required_passage = {x: y for x, y in info.required_passage.items() if len(y) > 0}
            for target_region, possible_portals in info.required_passage.items():
                candidates = find_portal_candidates(master_door_list, dungeon, custom, allowed, need_passage=True,
                                                    bk_shuffle=bk_shuffle, standard=std_flag, rupee_bow=rupee_bow_flag)
                choice, portal = assign_portal(candidates, possible_portals, custom, world, player)
                portal.destination = True
                clean_up_portal_assignment(portal_assignment, dungeon, portal, master_door_list, outstanding_portals)
            dead_end_choices = info.total - 1 - len(portal_assignment[dungeon])
            for i in range(0, dead_end_choices):
                candidates = find_portal_candidates(master_door_list, dungeon, custom, allowed, dead_end_allowed=True,
                                                    bk_shuffle=bk_shuffle, standard=std_flag, rupee_bow=rupee_bow_flag)
                possible_portals = outstanding_portals if not info.sole_entrance else [x for x in outstanding_portals if x != info.sole_entrance]
                choice, portal = assign_portal(candidates, possible_portals, custom, world, player)
                if choice.deadEnd:
                    if choice.passage:
                        portal.destination = True
                    else:
                        portal.deadEnd = True
                clean_up_portal_assignment(portal_assignment, dungeon, portal, master_door_list, outstanding_portals)
            the_rest = info.total - len(portal_assignment[dungeon])
            for i in range(0, the_rest):
                candidates = find_portal_candidates(master_door_list, dungeon, custom, allowed,
                                                    bk_shuffle=bk_shuffle, standard=hc_flag, rupee_bow=rupee_bow_flag)
                choice, portal = assign_portal(candidates, outstanding_portals, custom, world, player)
                clean_up_portal_assignment(portal_assignment, dungeon, portal, master_door_list, outstanding_portals)

    for portal in world.dungeon_portals[player]:
        connect_portal(portal, world, player)

    hc_south = world.get_door('Hyrule Castle Lobby S', player)
    if not hc_south.entranceFlag:
        world.get_room(0x61, player).delete(6)
        world.get_room(0x61, player).change(4, DoorKind.NormalLow)
    else:
        world.get_room(0x61, player).change(4, DoorKind.DungeonEntrance)
        world.get_room(0x61, player).change(6, DoorKind.CaveEntranceLow)
    sanctuary_door = world.get_door('Sanctuary S', player)
    if not sanctuary_door.entranceFlag:
        world.get_room(0x12, player).delete(3)
        world.get_room(0x12, player).change(2, DoorKind.NormalLow)
    else:
        world.get_room(0x12, player).change(2, DoorKind.DungeonEntrance)
        world.get_room(0x12, player).change(3, DoorKind.CaveEntranceLow)
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
        swamp_portal = world.get_portal('Swamp', player)
        if swamp_portal.door.name != 'Swamp Lobby S':
            world.swamp_patch_required[player] = True


def customizer_portals(master_door_list, world, player):
    custom_portals = {}
    assigned_doors = set()
    if world.customizer and world.customizer.get_doors():
        custom_doors = world.customizer.get_doors()[player]
        if custom_doors and 'lobbies' in custom_doors:
            for portal, assigned_door in custom_doors['lobbies'].items():
                door = next((x for x in master_door_list if x.name == assigned_door), None)
                if door is None:
                    raise Exception(f'{assigned_door} not found. Check for typos')
                custom_portals[portal] = door
                assigned_doors.add(door)
        if custom_doors and 'doors' in custom_doors:
            for src_door, dest in custom_doors['doors'].items():
                door = world.get_door(src_door, player)
                assigned_doors.add(door)
                if isinstance(dest, str):
                    door = world.get_door(dest, player)
                    assigned_doors.add(door)
                elif 'dest' in dest:
                    door = world.get_door(dest['dest'], player)
                    assigned_doors.add(door)
    # restricts connected doors to the customized portals
    if assigned_doors:
        pool = world.dungeon_pool[player]
        if pool:
            pool_map = {}
            for pool, region_list in pool:
                sector_pool = convert_to_sectors(region_list, world, player)
                merge_sectors(sector_pool, world, player)
                for p in pool:
                    pool_map[p] = sector_pool
            for portal, assigned_door in custom_portals.items():
                portal_region = world.get_door(assigned_door, player).entrance.parent_region
                portal_dungeon = world.get_region(f'{portal} Portal', player).dungeon.name
                sector_pool = pool_map[portal_dungeon]
                sector = next((s for s in sector_pool if portal_region in s.regions), None)
                for door in sector.outstanding_doors:
                    if door.portalAble:
                        door.dungeonLink = portal_dungeon
    return custom_portals, assigned_doors


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
                name_key = 'Desert Ledge' if name == 'Desert Ledge Keep' else name
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
                raise Exception(f'No reachable entrances for {dungeon}')
        if len(reachable_portals) == 1:
            info.sole_entrance = reachable_portals[0]
        if world.intensity[player] < 2 and world.doorShuffle[player] == 'basic' and dungeon == 'Desert Palace':
            if len(inaccessible_portals) == 1 and inaccessible_portals[0] == 'Desert Back':
                info.required_passage.clear()  # can't make a passage at this intensity level, something else must exit
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


def disconnect_portal(portal, world, player):
    ent, ext, entrance_name = portal_map[portal.name]
    portal_entrance = world.get_entrance(portal.door.entrance.name, player)
    # portal_region = world.get_region(portal.name + ' Portal', player)
    edit_entrance = world.get_entrance(entrance_name, player)
    chosen_door = world.get_door(portal_entrance.name, player)

    # reverse work
    if edit_entrance in portal_entrance.parent_region.entrances:
        portal_entrance.parent_region.entrances.remove(edit_entrance)
    chosen_door.blocked = chosen_door.blocked_orig
    chosen_door.entranceFlag = False


def find_portal_candidates(door_list, dungeon, custom, allowed, need_passage=False, dead_end_allowed=False,
                           bk_shuffle=False, standard=False, rupee_bow=False):
    custom_portals, assigned_doors = custom
    if assigned_doors:
        ret = [x for x in door_list if x not in assigned_doors]
    else:
        ret = door_list
    ret = [x for x in ret if bk_shuffle or not x.bk_shuffle_req]
    ret = [x for x in ret if not x.dungeonLink or x.dungeonLink == dungeon or x.dungeonLink.startswith('link')]
    ret = [x for x in ret if x.entrance.parent_region.dungeon.name in allowed[dungeon]]
    if need_passage:
        ret = [x for x in ret if x.passage]
    if not dead_end_allowed:
        ret = [x for x in ret if not x.deadEnd]
    if standard:
        ret = [x for x in ret if not x.standard_restricted]
    if rupee_bow:
        ret = [x for x in ret if not x.rupee_bow_restricted]
    return ret


def assign_portal(candidates, possible_portals, custom, world, player):
    custom_portals, assigned_doors = custom
    portal_choice = random.choice(possible_portals)
    if portal_choice in custom_portals:
        candidate = custom_portals[portal_choice]
    else:
        candidate = random.choice(candidates)
    portal = world.get_portal(portal_choice, player)
    while candidate.lw_restricted and not portal.light_world:
        candidates.remove(candidate)
        candidate = random.choice(candidates)
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
            if candidate.name == 'Swamp Hub S':
                new_door_kind = DoorKind.CaveEntranceLow
            elif candidate.layer or candidate.pseudo_bg:
                new_door_kind = DoorKind.DungeonEntranceLow
            else:
                new_door_kind = DoorKind.DungeonEntrance
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
        elif key == 'Hyrule Castle' and world.mode[player] == 'standard':
            for portal_name in portal_list:
                portal = world.get_portal(portal_name, player)
                choice = 'Sewers' if portal_name == 'Sanctuary' else 'Dungeon'
                r_name = portal.door.entrance.parent_region.name
                split_map[key][choice].append(r_name)
                entrance_map[key].append(r_name)
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


# each dungeon_pool members is a pair of lists: dungeon names and regions in those dungeons
def main_dungeon_pool(dungeon_pool, world, player):
    add_inaccessible_doors(world, player)
    entrances_map, potentials, connections = determine_entrance_list(world, player)
    connections_tuple = (entrances_map, potentials, connections)
    entrances, splits = create_dungeon_entrances(world, player)

    dungeon_builders = {}
    door_type_pools = []
    for pool, region_list in dungeon_pool:
        if len(pool) == 1:
            dungeon_key = next(iter(pool))
            sector_pool = convert_to_sectors(region_list, world, player)
            merge_sectors(sector_pool, world, player)
            dungeon_builders[dungeon_key] = simple_dungeon_builder(dungeon_key, sector_pool)
            dungeon_builders[dungeon_key].entrance_list = list(entrances_map[dungeon_key])
        else:
            if 'Hyrule Castle' in pool:
                hc = world.get_dungeon('Hyrule Castle', player)
                hc_compass = ItemFactory('Compass (Escape)', player)
                hc_compass.advancement = world.restrict_boss_items[player] != 'none'
                if hc.dungeon_items.count(hc_compass) < 1:
                    hc.dungeon_items.append(hc_compass)
            if 'Agahnims Tower' in pool:
                at = world.get_dungeon('Agahnims Tower', player)
                at_compass = ItemFactory('Compass (Agahnims Tower)', player)
                at_compass.advancement = world.restrict_boss_items[player] != 'none'
                if at.dungeon_items.count(at_compass) < 1:
                    at.dungeon_items.append(at_compass)
                at_map = ItemFactory('Map (Agahnims Tower)', player)
                at_map.advancement = world.restrict_boss_items[player] != 'none'
                if at.dungeon_items.count(at_map) < 1:
                    at.dungeon_items.append(at_map)
            sector_pool = convert_to_sectors(region_list, world, player)
            merge_sectors(sector_pool, world, player)
            # todo: which dungeon to create
            dungeon_builders.update(create_dungeon_builders(sector_pool, connections_tuple,
                                                            world, player, pool, entrances, splits))
        door_type_pools.append((pool, DoorTypePool(pool, world, player)))

    update_forced_keys(dungeon_builders, entrances_map, world, player)
    recombinant_builders = {}
    builder_info = entrances, splits, connections_tuple, world, player
    handle_split_dungeons(dungeon_builders, recombinant_builders, entrances_map, builder_info)

    main_dungeon_generation(dungeon_builders, recombinant_builders, connections_tuple, world, player)

    setup_custom_door_types(world, player)
    paths = determine_required_paths(world, player)
    shuffle_door_types(door_type_pools, paths, world, player)

    check_required_paths(paths, world, player)

    for pool, door_type_pool in door_type_pools:
        for name in pool:
            builder = world.dungeon_layouts[player][name]
            region_set = builder.master_sector.region_set()
            builder.bk_required = (builder.bk_door_proposal or any(x in region_set for x in special_bk_regions)
                                   or len(world.key_logic[player][name].bk_chests) > 0)
            dungeon = world.get_dungeon(name, player)
            if not builder.bk_required or builder.bk_provided:
                dungeon.big_key = None
            elif builder.bk_required and not builder.bk_provided:
                dungeon.big_key = ItemFactory(dungeon_bigs[name], player)

    all_dungeon_items_cnt = len(list(y for x in world.dungeons if x.player == player for y in x.all_items))
    target_items = 34
    if world.keyshuffle[player] == 'universal':
        target_items += 1 if world.dropshuffle[player] != 'none' else 0  # the hc big key
    else:
        target_items += 29  # small keys in chests
        if world.dropshuffle[player] != 'none':
            target_items += 14  # 13 dropped smalls + 1 big
        if world.pottery[player] not in ['none', 'cave']:
            target_items += 19  # 19 pot keys
    d_items = target_items - all_dungeon_items_cnt
    world.pool_adjustment[player] = d_items
    cross_dungeon_clean_up(world, player)


special_bk_regions = ['Hyrule Dungeon Cellblock', "Thieves Blind's Cell"]


def cross_dungeon_clean_up(world, player):
    # Re-assign dungeon bosses
    gt = world.get_dungeon('Ganons Tower', player)
    for name, builder in world.dungeon_layouts[player].items():
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

    if world.standardize_palettes[player] == 'standardize' and world.doorShuffle[player] != 'basic':
        palette_assignment(world, player)

    refine_hints(world.dungeon_layouts[player])
    refine_boss_exits(world, player)


def update_forced_keys(dungeon_builders, entrances_map, world, player):
    for builder in dungeon_builders.values():
        builder.entrance_list = list(entrances_map[builder.name])
        dungeon_obj = world.get_dungeon(builder.name, player)
        for sector in builder.sectors:
            for region in sector.regions:
                region.dungeon = dungeon_obj
                for loc in region.locations:
                    if loc.forced_item:
                        key_name = (dungeon_keys[builder.name] if loc.name != 'Hyrule Castle - Big Key Drop'
                                    else dungeon_bigs[builder.name])
                        loc.forced_item = loc.item = ItemFactory(key_name, player)


def finish_up_work(world, player):
    dungeon_builders = world.dungeon_layouts[player]
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

    if world.standardize_palettes[player] == 'standardize' and world.doorShuffle[player] not in ['basic']:
        palette_assignment(world, player)

    refine_hints(dungeon_builders)
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
    enabled_entrances = world.enabled_entrances[player] = {}
    sector_queue = deque(dungeon_builders.values())
    last_key, loops = None, 0
    logging.getLogger('').info(world.fish.translate("cli", "cli", "generating.dungeon"))
    while len(sector_queue) > 0:
        builder = sector_queue.popleft()
        split_dungeon = (builder.name.startswith('Desert Palace') or builder.name.startswith('Skull Woods')
                         or (builder.name.startswith('Hyrule Castle') and world.mode[player] == 'standard'))
        name = builder.name
        if split_dungeon:
            name = ' '.join(builder.name.split(' ')[:-1])
            if len(builder.sectors) == 0:
                del dungeon_builders[builder.name]
                continue
        origin_list = list(builder.entrance_list)
        find_standard_origins(builder, recombinant_builders, origin_list)
        find_enabled_origins(builder.sectors, enabled_entrances, origin_list, entrances_map, name)
        split_dungeon = treat_split_as_whole_dungeon(split_dungeon, name, origin_list, world, player)
        # todo: figure out pre-validate, ensure all needed origins are enabled?
        if len(origin_list) <= 0:  # or not pre_validate(builder, origin_list, split_dungeon, world, player):
            if last_key == builder.name or loops > 1000:
                origin_name = world.get_region(origin_list[0], player).entrances[0].parent_region.name if len(origin_list) > 0 else 'no origin'
                raise GenerationException(f'Infinite loop detected for "{builder.name}" located at {origin_name}')
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
    combine_layouts(recombinant_builders, dungeon_builders, entrances_map, world, player)
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
        r_names = []
        if key in dungeon_drops.keys():
            for drop in dungeon_drops[key]:
                r_names.append((drop, None))
        for portal_name in portal_list:
            portal = world.get_portal(portal_name, player)
            r_names.append((portal.door.entrance.parent_region.name, portal))
        for region_name, portal in r_names:
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


def find_standard_origins(builder, recomb_builders, origin_list):
    if builder.name == 'Hyrule Castle Sewers':
        throne_door = recomb_builders['Hyrule Castle'].throne_door
        sewer_entrance = throne_door.entrance.parent_region.name
        if sewer_entrance not in origin_list:
            origin_list.append(sewer_entrance)


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
        if ext.connected_region is None:
            continue
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


def treat_split_as_whole_dungeon(split_dungeon, name, origin_list, world, player):
    # what about ER dungeons? - find an example? (bad key doors 0 keys not valid)
    if split_dungeon and name in multiple_portal_map:
        possible_entrances = []
        for portal_name in multiple_portal_map[name]:
            portal = world.get_portal(portal_name, player)
            portal_entrance = world.get_entrance(portal_map[portal_name][0], player)
            if not portal.destination and portal_entrance.parent_region.name not in world.inaccessible_regions[player]:
                possible_entrances.append(portal)
        if len(possible_entrances) == 1:
            single_portal = possible_entrances[0]
            if single_portal.door.entrance.parent_region.name in origin_list and len(origin_list) == 1:
                return False
    return split_dungeon


# goals:
# 1. have enough chests to be interesting (2 more than dungeon items)
# 2. have a balanced amount of regions added (check)
# 3. prevent soft locks due to key usage (algorithm written)
# 4. rules in place to affect item placement (lamp, keys, etc. -- in rules)
# 5. to be complete -- all doors linked (check, somewhat)
# 6. avoid deadlocks/dead end dungeon (check)
# 7. certain paths through dungeon must be possible - be able to reach goals (check)


def cross_dungeon(world, player):
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

    hc_compass = ItemFactory('Compass (Escape)', player)
    at_compass = ItemFactory('Compass (Agahnims Tower)', player)
    at_map = ItemFactory('Map (Agahnims Tower)', player)
    if world.restrict_boss_items[player] != 'none':
        hc_compass.advancement = at_compass.advancement = at_map.advancement = True
    hc = world.get_dungeon('Hyrule Castle', player)
    if hc.dungeon_items.count(hc_compass) < 1:
        hc.dungeon_items.append(hc_compass)
    at = world.get_dungeon('Agahnims Tower', player)
    if at.dungeon_items.count(at_compass) < 1:
        at.dungeon_items.append(at_compass)
    if at.dungeon_items.count(at_map) < 1:
        at.dungeon_items.append(at_map)

    setup_custom_door_types(world, player)
    assign_cross_keys(dungeon_builders, world, player)
    all_dungeon_items_cnt = len(list(y for x in world.dungeons if x.player == player for y in x.all_items))
    target_items = 34
    if world.keyshuffle[player] == 'universal':
        target_items += 1 if world.dropshuffle[player] != 'none' else 0  # the hc big key
    else:
        target_items += 29  # small keys in chests
        if world.dropshuffle[player] != 'none':
            target_items += 14  # 13 dropped smalls + 1 big
        if world.pottery[player] not in ['none', 'cave']:
            target_items += 19  # 19 pot keys
    d_items = target_items - all_dungeon_items_cnt
    world.pool_adjustment[player] = d_items
    if not world.decoupledoors[player]:
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


def filter_key_door_pool(pool, selected_custom):
    new_pool = []
    for cand in pool:
        found = False
        for custom in selected_custom:
            if isinstance(cand, Door):
                if isinstance(custom, Door):
                    found = cand.name == custom.name
                else:
                    found = cand.name == custom[0].name or cand.name == custom[1].name
            else:
                if isinstance(custom, Door):
                    found = cand[0].name == custom.name or cand[1].name == custom.name
                else:
                    found = (cand[0].name == custom[0].name or cand[0].name == custom[1].name
                             or cand[1].name == custom[0].name or cand[1].name == custom[1].name)
            if found:
                break
        if not found:
            new_pool.append(cand)
    return new_pool


def assign_cross_keys(dungeon_builders, world, player):
    logging.getLogger('').info(world.fish.translate("cli", "cli", "shuffling.keydoors"))
    start = time.process_time()
    if world.keyshuffle[player] == 'universal':
        remaining = 29
        if world.dropshuffle[player] != 'none':
            remaining += 13
        if world.pottery[player] not in ['none', 'cave']:
            remaining += 19
    else:
        remaining = len(list(x for dgn in world.dungeons if dgn.player == player for x in dgn.small_keys))
    total_candidates = 0
    start_regions_map = {}
    if player in world.custom_door_types:
        custom_key_doors = world.custom_door_types[player]['Key Door']
    else:
        custom_key_doors = defaultdict(list)
    key_door_pool, key_doors_assigned = {}, {}
    # Step 1: Find Small Key Door Candidates
    for name, builder in dungeon_builders.items():
        dungeon = world.get_dungeon(name, player)
        if not builder.bk_required or builder.bk_provided:
            dungeon.big_key = None
        elif builder.bk_required and not builder.bk_provided:
            dungeon.big_key = ItemFactory(dungeon_bigs[name], player)
        start_regions = convert_regions(builder.path_entrances, world, player)
        find_small_key_door_candidates(builder, start_regions, world, player)
        key_door_pool[name] = list(builder.candidates)
        if custom_key_doors[name]:
            key_door_pool[name] = filter_key_door_pool(key_door_pool[name], custom_key_doors[name])
            remaining -= len(custom_key_doors[name])
        builder.key_doors_num = max(0, len(key_door_pool[name]) - builder.key_drop_cnt)
        total_candidates += builder.key_doors_num
        start_regions_map[name] = start_regions
    total_keys = remaining

    # Step 2: Initial Key Number Assignment & Calculate Flexibility
    for name, builder in dungeon_builders.items():
        calculated = int(round(builder.key_doors_num*total_keys/total_candidates))
        max_keys = max(0, builder.location_cnt - calc_used_dungeon_items(builder, world, player))
        cand_len = max(0, len(key_door_pool[name]) - builder.key_drop_cnt)
        limit = min(max_keys, cand_len)
        suggested = min(calculated, limit)
        combo_size = ncr(len(key_door_pool[name]), suggested + builder.key_drop_cnt)
        while combo_size > 500000 and suggested > 0:
            suggested -= 1
            combo_size = ncr(len(key_door_pool[name]), suggested + builder.key_drop_cnt)
        builder.key_doors_num = suggested + builder.key_drop_cnt + len(custom_key_doors[name])
        remaining -= suggested
        builder.combo_size = combo_size
        if suggested < limit:
            builder.flex = limit - suggested

    # Step 3: Initial valid combination find - reduce flex if needed
    for name, builder in dungeon_builders.items():
        suggested = builder.key_doors_num - builder.key_drop_cnt - len(custom_key_doors[name])
        builder.total_keys = builder.key_doors_num
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
        builder.total_keys = builder.key_doors_num
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
    for name, builder in dungeon_builders.items():
        reassign_key_doors(builder, world, player)
        if world.keyshuffle[player] != 'universal':
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
    if world.shuffle[player] not in ['insanity']:
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
                    if location.type == LocationType.Pot and location.pot:
                        hint_text = ('under a block' if location.pot.flags & PotFlags.Block else 'in a pot')
                        location.hint_text = f'{hint_text} {dungeon_hints[name]}'
                    elif location.type == LocationType.Drop:
                        location.hint_text = f'dropped {dungeon_hints[name]}'
                    else:
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
            filtered = []
            for reachable in reachable_portals:
                for entrance in reachable.door.entrance.connected_region.entrances:
                    parent = entrance.parent_region
                    if parent.type != RegionType.Dungeon and parent.name not in unreachable:
                        filtered.append(reachable)
            if 0 < len(filtered) < len(reachable_portals):
                reachable_portals = filtered
            chosen_one = random.choice(reachable_portals) if len(reachable_portals) > 1 else reachable_portals[0]
            chosen_one.chosen = True
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
def combine_layouts(recombinant_builders, dungeon_builders, entrances_map, world, player):
    for recombine in recombinant_builders.values():
        queue = deque(dungeon_builders.values())
        while len(queue) > 0:
            builder = queue.pop()
            if builder.name.startswith(recombine.name):
                del dungeon_builders[builder.name]
                if recombine.master_sector is None:
                    recombine.master_sector = builder.master_sector
                    recombine.master_sector.name = recombine.name
                else:
                    recombine.master_sector.regions.extend(builder.master_sector.regions)
        if recombine.name == 'Hyrule Castle':
            recombine.master_sector.regions.extend(recombine.throne_sector.regions)
            throne_n = world.get_door('Hyrule Castle Throne Room N', player)
            connect_doors(throne_n, recombine.throne_door)
        recombine.layout_starts = list(entrances_map[recombine.name])
        dungeon_builders[recombine.name] = recombine


def setup_custom_door_types(world, player):
    if not hasattr(world, 'custom_door_types'):
        world.custom_door_types = defaultdict(dict)
    if world.customizer and world.customizer.get_doors():
        # type_conv = {'Bomb Door': DoorKind.Bombable , 'Dash Door', DoorKind.Dashable, 'Key Door', DoorKind.SmallKey}
        custom_doors = world.customizer.get_doors()
        if player not in custom_doors:
            return
        custom_doors = custom_doors[player]
        if 'doors' not in custom_doors:
            return
        customizeable_types = ['Key Door', 'Dash Door', 'Bomb Door', 'Trap Door', 'Big Key Door']
        world.custom_door_types[player] = type_map = {x: defaultdict(list) for x in customizeable_types}
        for door, dest in custom_doors['doors'].items():
            if isinstance(dest, dict):
                if 'type' in dest:
                    door_kind = dest['type']
                    d = world.get_door(door, player)
                    dungeon = d.entrance.parent_region.dungeon
                    if d.type == DoorType.SpiralStairs:
                        type_map[door_kind][dungeon.name].append(d)
                    else:
                        # check if the dest is paired
                        if d.dest and d.dest.type in [DoorType.Interior, DoorType.Normal] and door_kind != 'Trap Door':
                            type_map[door_kind][dungeon.name].append((d, d.dest))
                        else:
                            type_map[door_kind][dungeon.name].append(d)


class DoorTypePool:
    def __init__(self, pool, world, player):
        self.smalls = 0
        self.bombable = 0
        self.dashable = 0
        self.bigs = 0
        self.traps = 0
        self.tricky = 0
        self.hidden = 0
        # todo: custom pools?
        for dungeon in pool:
            counts = door_type_counts[dungeon]
            if world.door_type_mode[player] == 'chaos':
                counts = self.chaos_shuffle(counts)
            self.smalls += counts[0]
            self.bigs += counts[1]
            self.traps += counts[2]
            self.bombable += counts[3]
            self.dashable += counts[4]
            self.hidden += counts[5]
            self.tricky += counts[6]

    def chaos_shuffle(self, counts):
        weights = [1, 2, 4, 3, 2]
        return [random.choices(self.get_choices(counts[i]), weights=weights)[0] for i, c in enumerate(counts)]

    @staticmethod
    def get_choices(number):
        return [max(number+i, 0) for i in range(-1, 4)]


class BuilderDoorCandidates:
    def __init__(self):
        self.small = []
        self.big = []
        self.trap = []
        self.bomb_dash = []


def shuffle_door_types(door_type_pools, paths, world, player):
    start_regions_map = {}
    for name, builder in world.dungeon_layouts[player].items():
        start_regions = convert_regions(find_possible_entrances(world, player, builder), world, player)
        start_regions_map[name] = start_regions
        builder.candidates = BuilderDoorCandidates()

    all_custom = defaultdict(list)
    if player in world.custom_door_types:
        for custom_dict in world.custom_door_types[player].values():
            for dungeon, doors in custom_dict.items():
                all_custom[dungeon].extend(doors)

    for pd in world.paired_doors[player]:
        pd.pair = False
    used_doors = shuffle_trap_doors(door_type_pools, paths, start_regions_map, all_custom, world, player)
    # big keys
    used_doors = shuffle_big_key_doors(door_type_pools, used_doors, start_regions_map, all_custom, world, player)
    # small keys
    used_doors = shuffle_small_key_doors(door_type_pools, used_doors, start_regions_map, all_custom, world, player)
    # bombable / dashable
    used_doors = shuffle_bomb_dash_doors(door_type_pools, used_doors, start_regions_map, all_custom, world, player)
    # handle paired list


def shuffle_trap_doors(door_type_pools, paths, start_regions_map, all_custom, world, player):
    used_doors = set()
    for pool, door_type_pool in door_type_pools:
        if world.trap_door_mode[player] != 'oneway':
            ttl = 0
            suggestion_map, trap_map, flex_map = {}, {}, {}
            remaining = door_type_pool.traps
            if player in world.custom_door_types and 'Trap Door' in world.custom_door_types[player]:
                custom_trap_doors = world.custom_door_types[player]['Trap Door']
            else:
                custom_trap_doors = defaultdict(list)
            for dungeon in pool:
                builder = world.dungeon_layouts[player][dungeon]
                if 'Mire Warping Pool' in builder.master_sector.region_set():
                    custom_trap_doors[dungeon].append(world.get_door('Mire Warping Pool ES', player))
                    world.custom_door_types[player]['Trap Door'] = custom_trap_doors
                find_trappable_candidates(builder, world, player)
                if all_custom[dungeon]:
                    builder.candidates.trap = filter_key_door_pool(builder.candidates.trap, all_custom[dungeon])
                    remaining -= len(custom_trap_doors[dungeon])
                ttl += len(builder.candidates.trap)
            if ttl == 0 and all(len(custom_trap_doors[dungeon]) == 0 for dungeon in pool):
                continue
            for dungeon in pool:
                builder = world.dungeon_layouts[player][dungeon]
                proportion = len(builder.candidates.trap)
                calc = 0 if ttl == 0 else int(round(proportion * door_type_pool.traps/ttl))
                suggested = min(proportion, calc)
                remaining -= suggested
                suggestion_map[dungeon] = suggested
                flex_map[dungeon] = (proportion - suggested) if suggested < proportion else 0
            for dungeon in pool:
                builder = world.dungeon_layouts[player][dungeon]
                valid_traps, trap_number = find_valid_trap_combination(builder, suggestion_map[dungeon],
                                                                       start_regions_map[dungeon], paths, world, player,
                                                                       drop=True)
                trap_map[dungeon] = valid_traps
                if trap_number < suggestion_map[dungeon]:
                    flex_map[dungeon] = 0
                    remaining += suggestion_map[dungeon] - trap_number
                suggestion_map[dungeon] = trap_number
            builder_order = [x for x in pool if flex_map[x] > 0]
            random.shuffle(builder_order)
            queue = deque(builder_order)
            while len(queue) > 0 and remaining > 0:
                dungeon = queue.popleft()
                builder = world.dungeon_layouts[player][dungeon]
                increased = suggestion_map[dungeon] + 1
                valid_traps, trap_number = find_valid_trap_combination(builder, increased, start_regions_map[dungeon],
                                                                       paths, world, player)
                if valid_traps:
                    trap_map[dungeon] = valid_traps
                    remaining -= 1
                    suggestion_map[dungeon] = increased
                    flex_map[dungeon] -= 1
                    if flex_map[dungeon] > 0:
                        queue.append(dungeon)
            # time to re-assign
        else:
            trap_map = {dungeon: [] for dungeon in pool}
            for dungeon in pool:
                builder = world.dungeon_layouts[player][dungeon]
                if 'Mire Warping Pool' in builder.master_sector.region_set():
                    trap_map[dungeon].append(world.get_door('Mire Warping Pool ES', player))
        reassign_trap_doors(trap_map, world, player)
        for name, traps in trap_map.items():
            used_doors.update(traps)
    return used_doors


def shuffle_big_key_doors(door_type_pools, used_doors, start_regions_map, all_custom, world, player):
    for pool, door_type_pool in door_type_pools:
        ttl = 0
        suggestion_map, bk_map, flex_map = {}, {}, {}
        remaining = door_type_pool.bigs
        if player in world.custom_door_types and 'Big Key Door' in world.custom_door_types[player]:
            custom_bk_doors = world.custom_door_types[player]['Big Key Door']
        else:
            custom_bk_doors = defaultdict(list)

        for dungeon in pool:
            builder = world.dungeon_layouts[player][dungeon]
            find_big_key_candidates(builder, start_regions_map[dungeon], used_doors, world, player)
            if all_custom[dungeon]:
                builder.candidates.big = filter_key_door_pool(builder.candidates.big, all_custom[dungeon])
                remaining -= len(custom_bk_doors[dungeon])
            ttl += len(builder.candidates.big)
        if ttl == 0:
            continue
        remaining = max(0, remaining)
        for dungeon in pool:
            builder = world.dungeon_layouts[player][dungeon]
            proportion = len(builder.candidates.big)
            calc = int(round(proportion * remaining/ttl))
            suggested = min(proportion, calc)
            remaining -= suggested
            suggestion_map[dungeon] = suggested
            flex_map[dungeon] = (proportion - suggested) if suggested < proportion else 0
        for dungeon in pool:
            builder = world.dungeon_layouts[player][dungeon]
            valid_doors, bk_number = find_valid_bk_combination(builder, suggestion_map[dungeon],
                                                               start_regions_map[dungeon], world, player, True)
            bk_map[dungeon] = valid_doors
            if bk_number < suggestion_map[dungeon]:
                flex_map[dungeon] = 0
                remaining += suggestion_map[dungeon] - bk_number
            suggestion_map[dungeon] = bk_number
        builder_order = [x for x in pool if flex_map[x] > 0]
        random.shuffle(builder_order)
        queue = deque(builder_order)
        while len(queue) > 0 and remaining > 0:
            dungeon = queue.popleft()
            builder = world.dungeon_layouts[player][dungeon]
            increased = suggestion_map[dungeon] + 1
            valid_doors, bk_number = find_valid_bk_combination(builder, increased, start_regions_map[dungeon],
                                                               world, player)
            if valid_doors:
                bk_map[dungeon] = valid_doors
                remaining -= 1
                suggestion_map[dungeon] = increased
                flex_map[dungeon] -= 1
                if flex_map[dungeon] > 0:
                    queue.append(dungeon)
        # time to re-assign
        reassign_big_key_doors(bk_map, used_doors, world, player)
        for name, big_list in bk_map.items():
            used_doors.update(flatten_pair_list(big_list))
    return used_doors


def shuffle_small_key_doors(door_type_pools, used_doors, start_regions_map, all_custom, world, player):
    max_computation = 11  # this is around 6 billion worse case factorial don't want to exceed this much
    for pool, door_type_pool in door_type_pools:
        ttl = 0
        suggestion_map, small_map, flex_map = {}, {}, {}
        remaining = door_type_pool.smalls
        total_keys = remaining
        if player in world.custom_door_types and 'Key Door' in world.custom_door_types[player]:
            custom_key_doors = world.custom_door_types[player]['Key Door']
        else:
            custom_key_doors = defaultdict(list)
        total_adjustable = len(pool) > 1
        for dungeon in pool:
            builder = world.dungeon_layouts[player][dungeon]
            if not total_adjustable:
                builder.total_keys = total_keys
            find_small_key_door_candidates(builder, start_regions_map[dungeon], used_doors, world, player)
            custom_doors = 0
            if all_custom[dungeon]:
                builder.candidates.small = filter_key_door_pool(builder.candidates.small, all_custom[dungeon])
                custom_doors = len(custom_key_doors[dungeon])
                remaining -= custom_doors
            builder.key_doors_num = max(0, len(builder.candidates.small) - builder.key_drop_cnt) + custom_doors
            total_keys -= builder.key_drop_cnt
            ttl += builder.key_doors_num
        remaining = max(0, remaining)
        for dungeon in pool:
            builder = world.dungeon_layouts[player][dungeon]
            if ttl == 0:
                calculated = 0
            else:
                calculated = int(round(builder.key_doors_num*total_keys/ttl))
            max_keys = max(0, builder.location_cnt - calc_used_dungeon_items(builder, world, player))
            cand_len = max(0, len(builder.candidates.small) - builder.key_drop_cnt)
            limit = min(max_keys, cand_len, max_computation)
            suggested = min(calculated, limit)
            key_door_num = min(suggested + builder.key_drop_cnt, max_computation)
            combo_size = ncr(len(builder.candidates.small), key_door_num)
            suggestion_map[dungeon] = builder.key_doors_num = key_door_num
            remaining -= key_door_num + builder.key_drop_cnt
            builder.combo_size = combo_size
            flex_map[dungeon] = (limit - key_door_num) if key_door_num < limit else 0
        for dungeon in pool:
            builder = world.dungeon_layouts[player][dungeon]
            if total_adjustable:
                builder.total_keys = max(suggestion_map[dungeon], builder.key_drop_cnt)
            valid_doors, small_number = find_valid_combination(builder, suggestion_map[dungeon],
                                                               start_regions_map[dungeon], world, player)
            small_map[dungeon] = valid_doors
            actual_chest_keys = small_number - builder.key_drop_cnt
            if actual_chest_keys < suggestion_map[dungeon]:
                if total_adjustable:
                    builder.total_keys = actual_chest_keys + builder.key_drop_cnt
                flex_map[dungeon] = 0
                remaining += suggestion_map[dungeon] - actual_chest_keys
            suggestion_map[dungeon] = small_number
        builder_order = [world.dungeon_layouts[player][x] for x in pool if flex_map[x] > 0]
        builder_order.sort(key=lambda b: b.combo_size)
        queue = deque(builder_order)
        while len(queue) > 0 and remaining > 0:
            builder = queue.popleft()
            dungeon = builder.name
            increased = suggestion_map[dungeon] + 1
            if increased > max_computation:
                continue
            builder.key_doors_num = increased
            valid_doors, small_number = find_valid_combination(builder, increased, start_regions_map[dungeon],
                                                               world, player)
            if valid_doors:
                small_map[dungeon] = valid_doors
                remaining -= 1
                suggestion_map[dungeon] = increased
                flex_map[dungeon] -= 1
                if total_adjustable:
                    builder.total_keys = max(increased, builder.key_drop_cnt)
                if flex_map[dungeon] > 0:
                    builder.combo_size = ncr(len(builder.candidates.small), builder.key_doors_num)
                    queue.append(builder)
                    queue = deque(sorted(queue, key=lambda b: b.combo_size))
            else:
                builder.key_doors_num -= 1
        # time to re-assign
        reassign_key_doors(small_map, used_doors, world, player)
        for dungeon_name in pool:
            if world.keyshuffle[player] != 'universal':
                builder = world.dungeon_layouts[player][dungeon_name]
                log_key_logic(builder.name, world.key_logic[player][builder.name])
                if world.doorShuffle[player] != 'basic':
                    actual_chest_keys = max(builder.key_doors_num - builder.key_drop_cnt, 0)
                    dungeon = world.get_dungeon(dungeon_name, player)
                    if actual_chest_keys == 0:
                        dungeon.small_keys = []
                    else:
                        dungeon.small_keys = [ItemFactory(dungeon_keys[dungeon_name], player)] * actual_chest_keys

        for name, small_list in small_map.items():
            used_doors.update(flatten_pair_list(small_list))
    return used_doors


def shuffle_bomb_dash_doors(door_type_pools, used_doors, start_regions_map, all_custom, world, player):
    for pool, door_type_pool in door_type_pools:
        ttl = 0
        suggestion_map, bd_map = {}, {}
        remaining_bomb = door_type_pool.bombable
        remaining_dash = door_type_pool.dashable

        if player in world.custom_door_types and 'Bomb Door' in world.custom_door_types[player]:
            custom_bomb_doors = world.custom_door_types[player]['Bomb Door']
            custom_dash_doors = world.custom_door_types[player]['Dash Door']
        else:
            custom_bomb_doors = defaultdict(list)
            custom_dash_doors = defaultdict(list)

        for dungeon in pool:
            builder = world.dungeon_layouts[player][dungeon]
            find_bd_candidates(builder, start_regions_map[dungeon], used_doors, world, player)
            if all_custom[dungeon]:
                builder.candidates.bomb_dash = filter_key_door_pool(builder.candidates.bomb_dash, all_custom[dungeon])
                remaining_bomb -= len(custom_bomb_doors[dungeon])
                remaining_dash -= len(custom_dash_doors[dungeon])
            ttl += len(builder.candidates.bomb_dash)
        if ttl == 0:
            continue
        for dungeon in pool:
            builder = world.dungeon_layouts[player][dungeon]
            proportion = len(builder.candidates.bomb_dash)
            calc = int(round(proportion * door_type_pool.bombable/ttl))
            suggested_bomb = min(proportion, calc)
            remaining_bomb -= suggested_bomb
            calc = int(round(proportion * door_type_pool.dashable/ttl))
            suggested_dash = min(proportion, calc)
            remaining_dash -= suggested_dash
            suggestion_map[dungeon] = suggested_bomb, suggested_dash
        for dungeon in pool:
            builder = world.dungeon_layouts[player][dungeon]
            bomb_doors, dash_doors, bd_number = find_valid_bd_combination(builder, suggestion_map[dungeon], world, player)
            bd_map[dungeon] = (bomb_doors, dash_doors)
            if bd_number < suggestion_map[dungeon][0] + suggestion_map[dungeon][1]:
                remaining_bomb += suggestion_map[dungeon][0] - len(bomb_doors)
                remaining_dash += suggestion_map[dungeon][1] - len(dash_doors)
            suggestion_map[dungeon] = len(bomb_doors), len(dash_doors)
        builder_order = [x for x in pool]
        random.shuffle(builder_order)
        queue = deque(builder_order)
        while len(queue) > 0 and (remaining_bomb > 0 or remaining_dash > 0):
            dungeon = queue.popleft()
            builder = world.dungeon_layouts[player][dungeon]
            type_pool = []
            if remaining_bomb > 0:
                type_pool.append('bomb')
            if remaining_dash > 0:
                type_pool.append('dash')
            type_choice = random.choice(type_pool)
            pair = suggestion_map[dungeon]
            pair = pair[0] + (1 if type_choice == 'bomb' else 0), pair[1] + (1 if type_choice == 'dash' else 0)
            bomb_doors, dash_doors, bd_number = find_valid_bd_combination(builder, pair, world, player)
            if bomb_doors and dash_doors:
                bd_map[dungeon] = (bomb_doors, dash_doors)
                remaining_bomb -= (1 if type_choice == 'bomb' else 0)
                remaining_dash -= (1 if type_choice == 'dash' else 0)
                suggestion_map[dungeon] = pair
                queue.append(dungeon)
        # time to re-assign
        reassign_bd_doors(bd_map, used_doors, world, player)
        for name, pair in bd_map.items():
            used_doors.update(flatten_pair_list(pair[0]))
            used_doors.update(flatten_pair_list(pair[1]))
    return used_doors


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
    builder.key_doors_num = builder.total_keys = num_key_doors
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


def find_trappable_candidates(builder, world, player):
    if world.door_type_mode[player] not in ['original', 'big']:  # all, chaos
        r_set = builder.master_sector.region_set()
        filtered_doors = [ext.door for r in r_set for ext in world.get_region(r, player).exits
                          if ext.door and ext.door.type in [DoorType.Interior, DoorType.Normal]]
        for d in filtered_doors:
            # I only support the first 3 due to the trapFlag right now
            if 0 <= d.doorListPos < 3 and not d.entranceFlag and d.name != 'Skull Small Hall WS':
                room = world.get_room(d.roomIndex, player)
                kind = room.kind(d)
                if d.type == DoorType.Interior:
                    if (kind in [DoorKind.Normal, DoorKind.SmallKey, DoorKind.Bombable, DoorKind.Dashable,
                                DoorKind.BigKey]
                       or (d.blocked and d.trapFlag != 0 and 'Boss' not in d.name and 'Agahnim' not in d.name)
                       or (kind == DoorKind.TrapTriggerable and d.direction in [Direction.South, Direction.East])
                       or (kind == DoorKind.Trap2 and d.direction in [Direction.North, Direction.West])):
                        builder.candidates.trap.append(d)
                elif d.type == DoorType.Normal:
                    if (kind in [DoorKind.Normal, DoorKind.SmallKey, DoorKind.Bombable, DoorKind.Dashable,
                                 DoorKind.BigKey]
                       or (d.blocked and d.trapFlag != 0 and 'Boss' not in d.name and 'Agahnim' not in d.name)):
                        builder.candidates.trap.append(d)
    else:
        r_set = builder.master_sector.region_set()
        for r in r_set:
            for ext in world.get_region(r, player).exits:
                if ext.door:
                    d = ext.door
                    if d.blocked and d.trapFlag != 0 and exclude_boss_traps(d):
                        builder.candidates.trap.append(d)


def find_valid_trap_combination(builder, suggested, start_regions, paths, world, player, drop=True):
    trap_door_pool = builder.candidates.trap
    trap_doors_needed = suggested
    if player in world.custom_door_types and 'Trap Door' in world.custom_door_types[player]:
        custom_trap_doors = world.custom_door_types[player]['Trap Door'][builder.name]
    else:
        custom_trap_doors = []
    if custom_trap_doors:
        trap_door_pool = filter_key_door_pool(trap_door_pool, custom_trap_doors)
        trap_doors_needed -= len(custom_trap_doors)
        trap_doors_needed = max(0, trap_doors_needed)
    if len(trap_door_pool) < trap_doors_needed:
        if not drop:
            return None, 0
        trap_doors_needed = len(trap_door_pool)
    combinations = ncr(len(trap_door_pool), trap_doors_needed)
    itr = 0
    sample_list = build_sample_list(combinations, 1000)
    proposal = kth_combination(sample_list[itr], trap_door_pool, trap_doors_needed)
    proposal.extend(custom_trap_doors)
    filtered_proposal = [x for x in proposal if x.name not in trap_door_exceptions]

    start_regions, event_starts = filter_start_regions(builder, start_regions, world, player)
    while not validate_trap_layout(filtered_proposal, builder, start_regions, paths, world, player):
        itr += 1
        if itr >= len(sample_list):
            if not drop:
                return None, 0
            trap_doors_needed -= 1
            if trap_doors_needed < 0:
                raise Exception(f'Bad dungeon {builder.name} - maybe custom trap doors are bad')
            combinations = ncr(len(trap_door_pool), trap_doors_needed)
            sample_list = build_sample_list(combinations, 1000)
            itr = 0
        proposal = kth_combination(sample_list[itr], trap_door_pool, trap_doors_needed)
        proposal.extend(custom_trap_doors)
        filtered_proposal = [x for x in proposal if x.name not in trap_door_exceptions]
    builder.trap_door_proposal = proposal
    return proposal, trap_doors_needed


# eliminate start region if portal marked as destination
def filter_start_regions(builder, start_regions, world, player):
    std_flag = world.mode[player] == 'standard' and builder.name == 'Hyrule Castle'
    excluded = {}   # todo: drop lobbies, might be better to white list instead (two entrances per region)
    event_doors = {}
    for region in start_regions:
        portal = next((x for x in world.dungeon_portals[player] if x.door.entrance.parent_region == region), None)
        if portal and portal.destination:
            # make sure that a drop is not accessible for this "destination"
            drop_region = next((x.parent_region for x in region.entrances
                                if x.parent_region.type in [RegionType.LightWorld, RegionType.DarkWorld]
                                or x.parent_region.name == 'Sewer Drop'), None)
            if not drop_region:
                excluded[region] = None
        if portal and not portal.destination:
            portal_entrance_region = portal.door.entrance.parent_region.name
            if portal_entrance_region not in builder.path_entrances:
                excluded[region] = None
        if not portal:
            drop_region = next((x.parent_region for x in region.entrances
                                if x.parent_region.type in [RegionType.LightWorld, RegionType.DarkWorld]
                                or x.parent_region.name == 'Sewer Drop'), None)
            if drop_region and drop_region.name in world.inaccessible_regions[player]:
                excluded[region] = None
        if std_flag and (not portal or portal.find_portal_entrance().parent_region.name != 'Hyrule Castle Courtyard'):
            excluded[region] = None
            if portal is None:
                entrance = next((x for x in region.entrances
                                 if x.parent_region.type in [RegionType.LightWorld, RegionType.DarkWorld]
                                 or x.parent_region.name == 'Sewer Drop'), None)
                event_doors[entrance] = None
            else:
                event_doors[portal.find_portal_entrance()] = None

    return [x for x in start_regions if x not in excluded.keys()], event_doors


def validate_trap_layout(proposal, builder, start_regions, paths, world, player):
    flag, state = check_required_paths_with_traps(paths, proposal, builder.name, start_regions, world, player)
    if not flag:
        return False
    bk_special_loc = find_bk_special_location(builder, world, player)
    if bk_special_loc:
        if not state.found_forced_bk():
            return False
    if world.accessibility[player] != 'beatable':
        all_locations = [l for r in builder.master_sector.region_set() for l in world.get_region(r, player).locations]
        if any(l not in state.found_locations for l in all_locations):
            return False
    return True


def find_bk_special_location(builder, world, player):
    for r_name in builder.master_sector.region_set():
        region = world.get_region(r_name, player)
        for loc in region.locations:
            if loc.forced_big_key():
                return loc
    return None


def check_required_paths_with_traps(paths, proposal, dungeon_name, start_regions, world, player):
    cached_initial_state = None
    if len(paths[dungeon_name]) > 0:
        common_starts = tuple(start_regions)
        states_to_explore = {common_starts: ([], 'all')}
        for path in paths[dungeon_name]:
            if type(path) is tuple:
                states_to_explore[tuple([path[0]])] = (path[1], 'any')
            else:
                # if common_starts not in states_to_explore:
                #     states_to_explore[common_starts] = ([], 'all')
                states_to_explore[common_starts][0].append(path)
        for start_regs, info in states_to_explore.items():
            dest_regs, path_type = info
            if type(dest_regs) is not list:
                dest_regs = [dest_regs]
            check_paths = convert_regions(dest_regs, world, player)
            start_regions = convert_regions(start_regs, world, player)
            initial = start_regs == common_starts
            if not initial or cached_initial_state is None:
                if cached_initial_state and any(not cached_initial_state.visited_at_all(r) for r in start_regions):
                    return False, None  # can't start processing the initial state because start regs aren't reachable
                init = determine_init_crystal(initial, cached_initial_state, start_regions)
                state = ExplorationState2(init, dungeon_name)
                for region in start_regions:
                    state.visit_region(region)
                    state.add_all_doors_check_proposed_traps(region, proposal, world, player)
                explore_state_proposed_traps(state, proposal, world, player)
                if initial and cached_initial_state is None:
                    cached_initial_state = state
            else:
                state = cached_initial_state
            if path_type == 'any':
                valid, bad_region = check_if_any_regions_visited(state, check_paths)
            else:
                valid, bad_region = check_if_all_regions_visited(state, check_paths)
            if not valid:
                return False, None
    return True, cached_initial_state


def reassign_trap_doors(trap_map, world, player):
    logger = logging.getLogger('')
    for name, traps in trap_map.items():
        builder = world.dungeon_layouts[player][name]
        queue = deque(find_current_trap_doors(builder, world, player))
        while len(queue) > 0:
            d = queue.pop()
            if d.type is DoorType.Interior and d not in traps:
                room = world.get_room(d.roomIndex, player)
                kind = room.kind(d)
                if kind == DoorKind.Trap:
                    new_type = (DoorKind.TrapTriggerable if d.direction in [Direction.South, Direction.East] else
                                DoorKind.Trap2)
                    room.change(d.doorListPos, new_type)
                elif kind in [DoorKind.Trap2, DoorKind.TrapTriggerable]:
                    room.change(d.doorListPos, DoorKind.Normal)
                d.blocked = False
                d.trapped = False
                # connect_one_way(world, d.name, d.dest.name, player)
            elif d.type is DoorType.Normal and d not in traps:
                world.get_room(d.roomIndex, player).change(d.doorListPos, DoorKind.Normal)
                d.blocked = False
                d.trapped = False
        for d in traps:
            change_door_to_trap(d, world, player)
            world.spoiler.set_door_type(f'{d.name} ({d.dungeon_name()})', 'Trap Door', player)
            logger.debug(f'Trap Door: {d.name} ({d.dungeon_name()})')


def exclude_boss_traps(d):
    return ' Boss ' not in d.name and ' Agahnim ' not in d.name and d.name not in ['Skull Spike Corner SW']


def find_current_trap_doors(builder, world, player):
    checker = exclude_boss_traps if world.trap_door_mode[player] in ['vanilla', 'optional'] else (lambda x: True)
    current_doors = []
    for region in builder.master_sector.regions:
        for ext in region.exits:
            d = ext.door
            if d and d.blocked and d.trapFlag != 0 and checker(d):
                current_doors.append(d)
    return current_doors


def change_door_to_trap(d, world, player):
    room = world.get_room(d.roomIndex, player)
    if d.type is DoorType.Interior:
        kind = room.kind(d)
        new_kind = None
        if kind == DoorKind.Trap:
            new_kind = DoorKind.Trap
        elif kind == DoorKind.TrapTriggerable and d.direction in [Direction.South, Direction.East]:
            new_kind = DoorKind.Trap
        elif kind == DoorKind.Trap2 and d.direction in [Direction.North, Direction.West]:
            new_kind = DoorKind.Trap
        elif d.direction in [Direction.South, Direction.East]:
            new_kind = DoorKind.Trap2
        elif d.direction in [Direction.North, Direction.West]:
            new_kind = DoorKind.TrapTriggerable
        if new_kind:
            d.blocked = is_trap_door_blocked(d)
            d.trapped = True
            pos = 3 if d.type == DoorType.Normal else 4
            verify_door_list_pos(d, room, world, player, pos)
            d.trapFlag = {0: 0x4, 1: 0x2, 2: 0x1, 3: 0x8}[d.doorListPos]
            room.change(d.doorListPos, new_kind)
            if d.entrance.connected_region is not None and d.blocked:
                d.entrance.connected_region.entrances.remove(d.entrance)
                d.entrance.connected_region = None
    elif d.type is DoorType.Normal:
        d.blocked = is_trap_door_blocked(d)
        d.trapped = True
        verify_door_list_pos(d, room, world, player, pos=3)
        d.trapFlag = {0: 0x4, 1: 0x2, 2: 0x1}[d.doorListPos]
        room.change(d.doorListPos, DoorKind.Trap)
        if d.entrance.connected_region is not None and d.blocked:
            d.entrance.connected_region.entrances.remove(d.entrance)
            d.entrance.connected_region = None
            if d.dependents:
                for dep in d.dependents:
                    if dep.entrance.connected_region is not None:
                        dep.entrance.connected_region.remove(dep.entrance)
                        dep.entrance.connected_region = None


trap_door_exceptions = {
    'PoD Mimics 2 SW', 'TR Twin Pokeys NW', 'Thieves Blocked Entry SW', 'Hyrule Dungeon Armory Interior Key Door N',
    'Desert Compass Key Door WN', 'TR Tile Room SE', 'Mire Cross SW', 'Tower Circle of Pots ES',
    'PoD Mimics 1 SW', 'Eastern Single Eyegore ES', 'Eastern Duo Eyegores SE', 'Swamp Push Statue S',
    'Skull 2 East Lobby WS', 'GT Hope Room WN', 'Eastern Courtyard Ledge S', 'Ice Lobby SE', 'GT Speed Torch WN',
    'Ice Switch Room ES', 'Ice Switch Room NE', 'Skull Torch Room WS', 'GT Speed Torch NE', 'GT Speed Torch WS',
    'GT Torch Cross WN', 'Mire Tile Room SW', 'Mire Tile Room ES', 'TR Torches WN', 'PoD Lobby N', 'PoD Middle Cage S',
    'Ice Bomb Jump NW', 'GT Hidden Spikes SE', 'Ice Tall Hint EN', 'Ice Tall Hint SE', 'Eastern Pot Switch WN',
    'Thieves Conveyor Maze WN', 'Thieves Conveyor Maze SW', 'Eastern Dark Square Key Door WN', 'Eastern Lobby NW',
    'Eastern Lobby NE', 'Ice Cross Bottom SE', 'Ice Cross Right ES', 'Desert Back Lobby S', 'Desert West S',
    'Desert West Lobby ES', 'Mire Hidden Shooters SE', 'Mire Hidden Shooters ES', 'Mire Hidden Shooters WS',
    'Tower Dark Pits EN', 'Tower Dark Maze ES', 'TR Tongue Pull WS', 'GT Conveyor Cross EN',
}


def is_trap_door_blocked(door):
    return door.name not in trap_door_exceptions


def find_big_key_candidates(builder, start_regions, used, world, player):
    if world.door_type_mode[player] != 'original':  # big, all, chaos
        # traverse dungeon and find candidates
        candidates = []
        checked_doors = set()
        for region in start_regions:
            possible, checked = find_big_key_door_candidates(region, checked_doors, used, world, player)
            candidates.extend([x for x in possible if x not in candidates])
            checked_doors.update(checked)
        flat_candidates = []
        for candidate in candidates:
            # not valid if: Normal Coupled and Pair in is Checked and Pair is not in Candidates
            if (world.decoupledoors[player] or candidate.type != DoorType.Normal
               or candidate.dest not in checked_doors or candidate.dest in candidates):
                flat_candidates.append(candidate)

        paired_candidates = build_pair_list(flat_candidates)
        builder.candidates.big = paired_candidates
    else:
        r_set = builder.master_sector.region_set()
        for r in r_set:
            for ext in world.get_region(r, player).exits:
                if ext.door:
                    d = ext.door
                    if d.bigKey and d.type in [DoorType.Normal, DoorType.Interior]:
                        builder.candidates.big.append(d)


def find_big_key_door_candidates(region, checked, used, world, player):
    decoupled = world.decoupledoors[player]
    dungeon_name = region.dungeon.name
    candidates = []
    checked_doors = list(checked)
    queue = deque([(region, None, None)])
    while len(queue) > 0:
        current, last_door, last_region = queue.pop()
        for ext in current.exits:
            d = ext.door
            controlled = d
            if d and d.controller:
                d = d.controller
            if (d and not d.blocked and d.dest is not last_door and d.dest is not last_region
               and d not in checked_doors):
                valid = False
                if (0 <= d.doorListPos < 4 and d.type in [DoorType.Interior, DoorType.Normal]
                     and not d.entranceFlag and d.direction in [Direction.North, Direction.South] and d not in used):
                    room = world.get_room(d.roomIndex, player)
                    position, kind = room.doorList[d.doorListPos]
                    if d.type == DoorType.Interior:
                        valid = kind in okay_interiors
                        if valid and d.dest not in candidates:  # interior doors are not separable yet
                            candidates.append(d.dest)
                    elif d.type == DoorType.Normal:
                        valid = kind in okay_normals
                        if valid and not decoupled:
                            d2 = d.dest
                            if d2 not in candidates and d2 not in used:
                                if d2.type == DoorType.Normal:
                                    room_b = world.get_room(d2.roomIndex, player)
                                    pos_b, kind_b = room_b.doorList[d2.doorListPos]
                                    valid &= kind_b in okay_normals and valid_key_door_pair(d, d2)
                                if valid and 0 <= d2.doorListPos < 4:
                                    candidates.append(d2)
                if valid and d not in candidates:
                    candidates.append(d)
                connected = ext.connected_region
                if valid_region_to_explore(connected, dungeon_name, world, player):
                    queue.append((ext.connected_region, controlled, current))
                if d is not None:
                    checked_doors.append(d)
    return candidates, checked_doors


def find_valid_bk_combination(builder, suggested, start_regions, world, player, drop=True):
    bk_door_pool = builder.candidates.big
    bk_doors_needed = suggested
    if player in world.custom_door_types and 'Big Key Door' in world.custom_door_types[player]:
        custom_bk_doors = world.custom_door_types[player]['Big Key Door'][builder.name]
    else:
        custom_bk_doors = []
    if custom_bk_doors:
        bk_door_pool = filter_key_door_pool(bk_door_pool, custom_bk_doors)
        bk_doors_needed -= len(custom_bk_doors)
        bk_doors_needed = max(0, bk_doors_needed)
    if len(bk_door_pool) < bk_doors_needed:
        if not drop:
            return None, 0
        bk_doors_needed = len(bk_door_pool)
    combinations = ncr(len(bk_door_pool), bk_doors_needed)
    itr = 0
    sample_list = build_sample_list(combinations, 10000)
    proposal = kth_combination(sample_list[itr], bk_door_pool, bk_doors_needed)
    proposal.extend(custom_bk_doors)

    start_regions, event_starts = filter_start_regions(builder, start_regions, world, player)
    while not validate_bk_layout(proposal, builder, start_regions, world, player):
        itr += 1
        if itr >= len(sample_list):
            if not drop:
                return None, 0
            bk_doors_needed -= 1
            if bk_doors_needed < 0:
                raise Exception(f'Bad dungeon {builder.name} - maybe custom bk doors are bad')
            combinations = ncr(len(bk_door_pool), bk_doors_needed)
            sample_list = build_sample_list(combinations, 10000)
            itr = 0
        proposal = kth_combination(sample_list[itr], bk_door_pool, bk_doors_needed)
        proposal.extend(custom_bk_doors)
    builder.bk_door_proposal = proposal
    return proposal, bk_doors_needed


def find_current_bk_doors(builder):
    current_doors = []
    for region in builder.master_sector.regions:
        for ext in region.exits:
            d = ext.door
            if d and d.type != DoorType.Logical and d.bigKey:
                current_doors.append(d)
    return current_doors


def reassign_big_key_doors(bk_map, used_doors, world, player):
    logger = logging.getLogger('')
    for name, big_doors in bk_map.items():
        flat_proposal = flatten_pair_list(big_doors)
        builder = world.dungeon_layouts[player][name]
        queue = deque(find_current_bk_doors(builder))
        while len(queue) > 0:
            d = queue.pop()
            if d.type is DoorType.Interior and d not in flat_proposal and d.dest not in flat_proposal:
                if not d.entranceFlag and d not in used_doors and d.dest not in used_doors:
                    world.get_room(d.roomIndex, player).change(d.doorListPos, DoorKind.Normal)
                d.bigKey = False
            elif d.type is DoorType.Normal and d not in flat_proposal :
                if not d.entranceFlag and d not in used_doors:
                    world.get_room(d.roomIndex, player).change(d.doorListPos, DoorKind.Normal)
                d.bigKey = False
        for obj in big_doors:
            if type(obj) is tuple:
                d1 = obj[0]
                d2 = obj[1]
                if d1.type is DoorType.Interior:
                    change_door_to_big_key(d1, world, player)
                    d2.bigKey = True  # ensure flag is set
                    if d2.smallKey:
                        d2.smallKey = False
                else:
                    world.paired_doors[player].append(PairedDoor(d1.name, d2.name))
                    change_door_to_big_key(d1, world, player)
                    change_door_to_big_key(d2, world, player)
                world.spoiler.set_door_type(f'{d1.name} <-> {d2.name} ({d1.dungeon_name()})', 'Big Key Door', player)
                logger.debug(f'Big Key Door: {d1.name} <-> {d2.name} ({d1.dungeon_name()})')
            else:
                d = obj
                if d.type is DoorType.Interior:
                    change_door_to_big_key(d, world, player)
                    if world.door_type_mode[player] != 'original':
                        d.dest.bigKey = True  # ensure flag is set when bk doors are double sided
                elif d.type is DoorType.SpiralStairs:
                    pass  # we don't have spiral stairs candidates yet that aren't already key doors
                elif d.type is DoorType.Normal:
                    change_door_to_big_key(d, world, player)
                    if not world.decoupledoors[player] and d.dest and world.door_type_mode[player] != 'original':
                        if d.dest.type in [DoorType.Normal]:
                            dest_room = world.get_room(d.dest.roomIndex, player)
                            if stateful_door(d.dest, dest_room.kind(d.dest)):
                                change_door_to_big_key(d.dest, world, player)
                                add_pair(d, d.dest, world, player)
                world.spoiler.set_door_type(f'{d.name} ({d.dungeon_name()})', 'Big Key Door', player)
                logger.debug(f'Big Key Door: {d.name} ({d.dungeon_name()})')


def change_door_to_big_key(d, world, player):
    d.bigKey = True
    if d.smallKey:
        d.smallKey = False
    room = world.get_room(d.roomIndex, player)
    if room.doorList[d.doorListPos][1] != DoorKind.BigKey:
        verify_door_list_pos(d, room, world, player)
        room.change(d.doorListPos, DoorKind.BigKey)


def find_small_key_door_candidates(builder, start_regions, used, world, player):
    # traverse dungeon and find candidates
    candidates = []
    checked_doors = set()
    for region in start_regions:
        possible, checked = find_key_door_candidates(region, checked_doors, used, world, player)
        candidates.extend([x for x in possible if x not in candidates])
        checked_doors.update(checked)
    flat_candidates = []
    for candidate in candidates:
        # not valid if: Normal Coupled and Pair in is Checked and Pair is not in Candidates
        if (world.decoupledoors[player] or candidate.type != DoorType.Normal
             or candidate.dest not in checked_doors or candidate.dest in candidates):
            flat_candidates.append(candidate)

    paired_candidates = build_pair_list(flat_candidates)
    builder.candidates.small = paired_candidates


def calc_used_dungeon_items(builder, world, player):
    basic_flag = world.doorShuffle[player] == 'basic'
    base = 0 if basic_flag else 2  # at least 2 items per dungeon, except in basic
    base = max(count_reserved_locations(world, player, builder.location_set), base)
    if not world.bigkeyshuffle[player]:
        if builder.bk_required and not builder.bk_provided:
            base += 1
    if not world.compassshuffle[player] and (builder.name not in ['Hyrule Castle', 'Agahnims Tower'] or not basic_flag):
        base += 1
    if not world.mapshuffle[player] and (builder.name != 'Agahnims Tower' or not basic_flag):
        base += 1
    return base


def find_valid_combination(builder, target, start_regions, world, player, drop_keys=True):
    logger = logging.getLogger('')
    key_door_pool = list(builder.candidates.small)
    key_doors_needed = target
    if player in world.custom_door_types and 'Key Door' in world.custom_door_types[player]:
        custom_key_doors = world.custom_door_types[player]['Key Door'][builder.name]
    else:
        custom_key_doors = []
    if custom_key_doors:  # could validate that each custom item is in the candidates
        key_door_pool = filter_key_door_pool(key_door_pool, custom_key_doors)
        key_doors_needed -= len(custom_key_doors)
        key_doors_needed = max(0, key_doors_needed)
    # find valid combination of candidates
    if len(key_door_pool) < key_doors_needed:
        if not drop_keys:
            logger.info('No valid layouts for %s with %s doors', builder.name, builder.key_doors_num)
            return None, 0
        builder.key_doors_num -= key_doors_needed - len(key_door_pool)  # reduce number of key doors
        key_doors_needed = len(key_door_pool)
        logger.info('%s: %s', world.fish.translate("cli", "cli", "lowering.keys.candidates"), builder.name)
    combinations = ncr(len(key_door_pool), key_doors_needed)
    itr = 0
    start = time.process_time()
    sample_list = build_sample_list(combinations)
    proposal = kth_combination(sample_list[itr], key_door_pool, key_doors_needed)
    proposal.extend(custom_key_doors)
    builder.key_doors_num = len(proposal)
    start_regions, event_starts = filter_start_regions(builder, start_regions, world, player)

    key_layout = build_key_layout(builder, start_regions, proposal, event_starts, world, player)
    determine_prize_lock(key_layout, world, player)
    while not validate_key_layout(key_layout, world, player):
        itr += 1
        if itr >= len(sample_list):
            if not drop_keys:
                logger.info('No valid layouts for %s with %s doors', builder.name, builder.key_doors_num)
                return None, 0
            logger.info('%s: %s', world.fish.translate("cli","cli","lowering.keys.layouts"), builder.name)
            builder.key_doors_num -= 1
            key_doors_needed -= 1
            if key_doors_needed < 0:
                raise Exception(f'Bad dungeon {builder.name} - less than 0 key doors or invalid custom key door')
            combinations = ncr(len(key_door_pool), max(0, key_doors_needed))
            sample_list = build_sample_list(combinations)
            itr = 0
            start = time.process_time()  # reset time since itr reset
        proposal = kth_combination(sample_list[itr], key_door_pool, key_doors_needed)
        proposal.extend(custom_key_doors)
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
    return builder.key_door_proposal, key_doors_needed + len(custom_key_doors)


def find_bd_candidates(builder, start_regions, used, world, player):
    # traverse dungeon and find candidates
    candidates = []
    checked_doors = set()
    for region in start_regions:
        possible, checked = find_bd_door_candidates(region, checked_doors, used, world, player)
        candidates.extend([x for x in possible if x not in candidates])
        checked_doors.update(checked)
    flat_candidates = []
    for candidate in candidates:
        # not valid if: Normal Coupled and Pair in is Checked and Pair is not in Candidates
        if (world.decoupledoors[player] or candidate.type != DoorType.Normal
             or candidate.dest not in checked_doors or candidate.dest in candidates):
            flat_candidates.append(candidate)
    builder.candidates.bomb_dash = build_pair_list(flat_candidates)


def find_bd_door_candidates(region, checked, used, world, player):
    decoupled = world.decoupledoors[player]
    dungeon_name = region.dungeon.name
    candidates = []
    checked_doors = list(checked)
    queue = deque([(region, None, None)])
    while len(queue) > 0:
        current, last_door, last_region = queue.pop()
        for ext in current.exits:
            d = ext.door
            controlled = d
            if d and d.controller:
                d = d.controller
            if (d and not d.blocked and d.dest is not last_door and d.dest is not last_region
                 and d not in checked_doors):
                valid = False
                if (0 <= d.doorListPos < 4 and d.type in [DoorType.Interior, DoorType.Normal] and not d.entranceFlag
                   and d not in used):
                    room = world.get_room(d.roomIndex, player)
                    position, kind = room.doorList[d.doorListPos]
                    if d.type == DoorType.Interior:
                        # interior doors are not separable yet
                        valid = kind in okay_interiors and d.dest not in used
                        if valid and d.dest not in candidates:
                            candidates.append(d.dest)
                    elif d.type == DoorType.Normal:
                        valid = kind in okay_normals
                        if valid and not decoupled:
                            d2 = d.dest
                            if d2 not in candidates and d2 not in used:
                                if d2.type == DoorType.Normal:
                                    room_b = world.get_room(d2.roomIndex, player)
                                    pos_b, kind_b = room_b.doorList[d2.doorListPos]
                                    valid &= kind_b in okay_normals and valid_key_door_pair(d, d2)
                                if valid and 0 <= d2.doorListPos < 4:
                                    candidates.append(d2)
                if valid and d not in candidates:
                    candidates.append(d)
                connected = ext.connected_region
                if valid_region_to_explore(connected, dungeon_name, world, player):
                    queue.append((ext.connected_region, controlled, current))
                if d is not None:
                    checked_doors.append(d)
    return candidates, checked_doors


def find_valid_bd_combination(builder, suggested, world, player):
    # bombable/dashable doors could be excluded in escape in standard until we can guarantee bomb access
    # if world.mode[player] == 'standard' and builder.name == 'Hyrule Castle':
    #     return None, None, 0
    bd_door_pool = builder.candidates.bomb_dash
    bomb_doors_needed, dash_doors_needed = suggested
    ttl_needed = bomb_doors_needed + dash_doors_needed
    if player in world.custom_door_types and 'Bomb Door' in world.custom_door_types[player]:
        custom_bomb_doors = world.custom_door_types[player]['Bomb Door'][builder.name]
        custom_dash_doors = world.custom_door_types[player]['Dash Door'][builder.name]
    else:
        custom_bomb_doors = []
        custom_dash_doors = []
    if custom_bomb_doors:
        bd_door_pool = filter_key_door_pool(bd_door_pool, custom_bomb_doors)
        bomb_doors_needed -= len(custom_bomb_doors)
    if custom_dash_doors:
        bd_door_pool = filter_key_door_pool(bd_door_pool, custom_dash_doors)
        dash_doors_needed -= len(custom_dash_doors)
    while len(bd_door_pool) < bomb_doors_needed + dash_doors_needed:
        test = random.choice([True, False])
        if test:
            bomb_doors_needed -= 1
            if bomb_doors_needed < 0:
                bomb_doors_needed = 0
        else:
            dash_doors_needed -= 1
            if dash_doors_needed < 0:
                dash_doors_needed = 0
    bomb_proposal = random.sample(bd_door_pool, k=bomb_doors_needed)
    bomb_proposal.extend(custom_bomb_doors)
    dash_pool = [x for x in bd_door_pool if x not in bomb_proposal]
    dash_proposal = random.sample(dash_pool, k=dash_doors_needed)
    dash_proposal.extend(custom_dash_doors)
    return bomb_proposal, dash_proposal, ttl_needed


def reassign_bd_doors(bd_map, used_doors, world, player):
    for name, pair in bd_map.items():
        flat_bomb_proposal = flatten_pair_list(pair[0])
        flat_dash_proposal = flatten_pair_list(pair[1])

        def not_in_proposal(door):
            return (door not in flat_bomb_proposal and door.dest not in flat_bomb_proposal and
                    door not in flat_dash_proposal and door.dest not in flat_bomb_proposal)

        builder = world.dungeon_layouts[player][name]
        queue = deque(find_current_bd_doors(builder, world))
        while len(queue) > 0:
            d = queue.pop()
            if d.type is DoorType.Interior and not_in_proposal(d) and d not in used_doors and d.dest not in used_doors:
                if not d.entranceFlag:
                    world.get_room(d.roomIndex, player).change(d.doorListPos, DoorKind.Normal)
            elif d.type is DoorType.Normal and not_in_proposal(d) and d not in used_doors:
                if not d.entranceFlag:
                    world.get_room(d.roomIndex, player).change(d.doorListPos, DoorKind.Normal)
        do_bombable_dashable(pair[0], DoorKind.Bombable, world, player)
        do_bombable_dashable(pair[1], DoorKind.Dashable, world, player)


def do_bombable_dashable(proposal, kind, world, player):
    for obj in proposal:
        if type(obj) is tuple:
            d1 = obj[0]
            d2 = obj[1]
            if d1.type is DoorType.Interior:
                change_door_to_kind(d1, kind, world, player)
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
                change_door_to_kind(d1, kind, world, player)
                change_door_to_kind(d2, kind, world, player)
            spoiler_type = 'Bomb Door' if kind == DoorKind.Bombable else 'Dash Door'
            world.spoiler.set_door_type(f'{d1.name} <-> {d2.name} ({d1.dungeon_name()})', spoiler_type, player)
        else:
            d = obj
            if d.type is DoorType.Interior:
                change_door_to_kind(d, kind, world, player)
            elif d.type is DoorType.Normal:
                change_door_to_kind(d, kind, world, player)
                if not world.decoupledoors[player] and d.dest:
                    if d.dest.type in okay_normals and not std_forbidden(d.dest, world, player):
                        dest_room = world.get_room(d.dest.roomIndex, player)
                        if stateful_door(d.dest, dest_room.kind(d.dest)):
                            change_door_to_kind(d.dest, kind, world, player)
                            add_pair(d, d.dest, world, player)
            spoiler_type = 'Bomb Door' if kind == DoorKind.Bombable else 'Dash Door'
            world.spoiler.set_door_type(f'{d.name} ({d.dungeon_name()})', spoiler_type, player)


def find_current_bd_doors(builder, world):
    current_doors = []
    for region in builder.master_sector.regions:
        for ext in region.exits:
            d = ext.door
            if d and d.type in [DoorType.Interior, DoorType.Normal]:
                kind = d.kind(world)
                if kind in [DoorKind.Dashable, DoorKind.Bombable]:
                    current_doors.append(d)
    return current_doors


def change_door_to_kind(d, kind, world, player):
    room = world.get_room(d.roomIndex, player)
    if room.doorList[d.doorListPos][1] != kind:
        verify_door_list_pos(d, room, world, player)
        room.change(d.doorListPos, kind)


def build_sample_list(combinations, max_combinations=10000):
    if combinations <= max_combinations:
        sample_list = list(range(0, int(combinations)))
    else:
        num_set = set()
        while len(num_set) < max_combinations:
            num_set.add(random.randint(0, combinations))
        sample_list = list(num_set)
        sample_list.sort()
    random.shuffle(sample_list)
    return sample_list


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
        paired = d.dest.dest == d
        if d.dest in queue and d.type != DoorType.SpiralStairs and paired:
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


okay_normals = [DoorKind.Normal, DoorKind.SmallKey, DoorKind.Bombable, DoorKind.Dashable,
                DoorKind.DungeonChanger, DoorKind.BigKey]

okay_interiors = [DoorKind.Normal, DoorKind.SmallKey, DoorKind.Bombable, DoorKind.Dashable, DoorKind.BigKey]


def find_key_door_candidates(region, checked, used, world, player):
    decoupled = world.decoupledoors[player]
    dungeon_name = region.dungeon.name
    candidates = []
    checked_doors = list(checked)
    queue = deque([(region, None, None)])
    while len(queue) > 0:
        current, last_door, last_region = queue.pop()
        for ext in current.exits:
            d = ext.door
            controlled = d
            if d and d.controller:
                d = d.controller
            if (d and not d.blocked and d.dest is not last_door and d.dest is not last_region
                and d not in checked_doors):
                valid = False
                if (0 <= d.doorListPos < 4 and d.type in [DoorType.Interior, DoorType.Normal, DoorType.SpiralStairs]
                     and not d.entranceFlag and d not in used):
                    room = world.get_room(d.roomIndex, player)
                    position, kind = room.doorList[d.doorListPos]
                    if d.type == DoorType.Interior:
                        valid = kind in okay_interiors and d.dest not in used
                        # interior doors are not separable yet
                        if valid and d.dest not in candidates:
                            candidates.append(d.dest)
                    elif d.type == DoorType.SpiralStairs:
                        valid = kind in [DoorKind.StairKey, DoorKind.StairKey2, DoorKind.StairKeyLow]
                    elif d.type == DoorType.Normal:
                        valid = kind in okay_normals
                        if valid and not decoupled:
                            d2 = d.dest
                            if d2 not in candidates and d2 not in used:
                                if d2.type == DoorType.Normal:
                                    room_b = world.get_room(d2.roomIndex, player)
                                    pos_b, kind_b = room_b.doorList[d2.doorListPos]
                                    valid &= kind_b in okay_normals and valid_key_door_pair(d, d2)
                                if valid and 0 <= d2.doorListPos < 4:
                                    candidates.append(d2)
                if valid and d not in candidates:
                    candidates.append(d)
                connected = ext.connected_region
                if valid_region_to_explore(connected, dungeon_name, world, player):
                    queue.append((ext.connected_region, controlled, current))
                if d is not None:
                    checked_doors.append(d)
    return candidates, checked_doors


def valid_key_door_pair(door1, door2):
    if door1.roomIndex != door2.roomIndex:
        return True
    return len(door1.entrance.parent_region.exits) <= 1 or len(door2.entrance.parent_region.exits) <= 1


def reassign_key_doors(small_map, used_doors, world, player):
    logger = logging.getLogger('')
    for name, small_doors in small_map.items():
        logger.debug(f'Key doors for {name}')
        builder = world.dungeon_layouts[player][name]
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
            elif d.type is DoorType.Interior and d not in flat_proposal and d.dest not in flat_proposal:
                if not d.entranceFlag and d not in used_doors and d.dest not in used_doors:
                    world.get_room(d.roomIndex, player).change(d.doorListPos, DoorKind.Normal)
                d.smallKey = False
                d.dest.smallKey = False
                queue.remove(d.dest)
            elif d.type is DoorType.Normal and d not in flat_proposal:
                if not d.entranceFlag and d not in used_doors:
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
                world.spoiler.set_door_type(f'{d1.name} <-> {d2.name} ({d1.dungeon_name()})', 'Key Door', player)
                logger.debug(f'Key Door: {d1.name} <-> {d2.name} ({d1.dungeon_name()})')
            else:
                d = obj
                if d.type is DoorType.Interior:
                    change_door_to_small_key(d, world, player)
                    d.dest.smallKey = True  # ensure flag is set
                elif d.type is DoorType.SpiralStairs:
                    pass  # we don't have spiral stairs candidates yet that aren't already key doors
                elif d.type is DoorType.Normal:
                    change_door_to_small_key(d, world, player)
                    if not world.decoupledoors[player] and d.dest:
                        if d.dest.type in [DoorType.Normal]:
                            dest_room = world.get_room(d.dest.roomIndex, player)
                            if stateful_door(d.dest, dest_room.kind(d.dest)):
                                change_door_to_small_key(d.dest, world, player)
                                add_pair(d, d.dest, world, player)
                world.spoiler.set_door_type(f'{d.name} ({d.dungeon_name()})', 'Key Door', player)
                logger.debug(f'Key Door: {d.name} ({d.dungeon_name()})')


def change_door_to_small_key(d, world, player):
    d.smallKey = True
    room = world.get_room(d.roomIndex, player)
    if room.doorList[d.doorListPos][1] != DoorKind.SmallKey:
        verify_door_list_pos(d, room, world, player)
        room.change(d.doorListPos, DoorKind.SmallKey)


def verify_door_list_pos(d, room, world, player, pos=4):
    if d.doorListPos >= pos:
        new_index = room.next_free(pos)
        if new_index is not None:
            room.swap(new_index, d.doorListPos)
            other = next(x for x in world.doors if x.player == player and x.roomIndex == d.roomIndex
                         and x.doorListPos == new_index)
            other.doorListPos = d.doorListPos
            d.doorListPos = new_index
        else:
            raise Exception(f'Invalid stateful door: {d.name}. Only {pos} stateful doors per supertile')


def smooth_door_pairs(world, player):
    all_doors = [x for x in world.doors if x.player == player]
    skip = set()
    bd_candidates = defaultdict(list)
    for door in all_doors:
        if door.type in [DoorType.Normal, DoorType.Interior] and door not in skip and not door.entranceFlag:
            if not door.dest:
                continue
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
                else:
                    if valid_pair and not std_forbidden(door, world, player):
                        bd_candidates[door.entrance.parent_region.dungeon].append(door)
                    elif type_a in [DoorKind.Bombable, DoorKind.Dashable] or type_b in [DoorKind.Bombable, DoorKind.Dashable]:
                        if type_a in [DoorKind.Bombable, DoorKind.Dashable]:
                            room_a.change(door.doorListPos, DoorKind.Normal)
                            remove_pair(door, world, player)
                        else:
                            room_b.change(partner.doorListPos, DoorKind.Normal)
                            remove_pair(partner, world, player)
            elif (valid_pair and type_a != DoorKind.SmallKey and type_b != DoorKind.SmallKey
                  and not std_forbidden(door, world, player)):
                bd_candidates[door.entrance.parent_region.dungeon].append(door)
    shuffle_bombable_dashable(bd_candidates, world, player)
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
        return kind in [DoorKind.Normal, DoorKind.SmallKey, DoorKind.Bombable, DoorKind.Dashable, DoorKind.BigKey]
    return False


def std_forbidden(door, world, player):
    return (world.mode[player] == 'standard' and door.entrance.parent_region.dungeon.name == 'Hyrule Castle' and
            'Hyrule Castle Throne Room N' in [door.name, door.dest.name])


def custom_door_kind(custom_key, kind, bd_candidates, counts, world, player):
    if custom_key in world.custom_door_types[player]:
        for door_a, door_b in world.custom_door_types[player][custom_key]:
            change_pair_type(door_a, kind, world, player)
            d_name = door_a.entrance.parent_region.dungeon.name
            bd_list = next(bd_list for dungeon, bd_list in bd_candidates.items() if dungeon.name == d_name)
            if door_a in bd_list:
                bd_list.remove(door_a)
            if door_b in bd_list:
                bd_list.remove(door_b)
            counts[d_name] += 1


dashable_forbidden = {
    'Swamp Trench 1 Key Ledge NW', 'Swamp Left Elbow WN', 'Swamp Right Elbow SE', 'Mire Hub WN', 'Mire Hub WS',
    'Mire Hub Top NW', 'Mire Hub NE', 'Ice Dead End WS'
}

ohko_forbidden = {
    'GT Invisible Catwalk NE', 'GT Falling Bridge WN', 'GT Falling Bridge WS', 'GT Hidden Star ES', 'GT Hookshot EN',
    'GT Torch Cross WN', 'TR Torches WN', 'Mire Falling Bridge WS', 'Mire Falling Bridge W', 'Ice Hookshot Balcony SW',
    'Ice Catwalk WN', 'Ice Catwalk NW', 'Ice Bomb Jump NW', 'GT Cannonball Bridge SE'
}


def filter_dashable_candidates(candidates, world):
    forbidden_set = dashable_forbidden
    if world.timer in ['ohko', 'timed-ohko']:
        forbidden_set = ohko_forbidden.union(dashable_forbidden)
    return [x for x in candidates if x.name not in forbidden_set and x.dest.name not in forbidden_set]


def shuffle_bombable_dashable(bd_candidates, world, player):
    dash_counts = defaultdict(int)
    bomb_counts = defaultdict(int)
    if world.custom_door_types[player]:
        custom_door_kind('Dash Door', DoorKind.Dashable, bd_candidates, dash_counts, world, player)
        custom_door_kind('Bomb Door', DoorKind.Bombable, bd_candidates, bomb_counts, world, player)
    if world.doorShuffle[player] == 'basic':
        for dungeon, candidates in bd_candidates.items():
            diff = bomb_dash_counts[dungeon.name][1] - dash_counts[dungeon.name]
            if diff > 0:
                dash_candidates = filter_dashable_candidates(candidates, world)
                for chosen in random.sample(dash_candidates, min(diff, len(candidates))):
                    change_pair_type(chosen, DoorKind.Dashable, world, player)
                    candidates.remove(chosen)
            diff = bomb_dash_counts[dungeon.name][0] - bomb_counts[dungeon.name]
            if diff > 0:
                for chosen in random.sample(candidates, min(diff, len(candidates))):
                    change_pair_type(chosen, DoorKind.Bombable, world, player)
                    candidates.remove(chosen)
            for excluded in candidates:
                remove_pair_type_if_present(excluded, world, player)
    elif world.doorShuffle[player] == 'crossed':
        all_candidates = sum(bd_candidates.values(), [])
        desired_dashables = 8 - sum(dash_counts.values(), 0)
        desired_bombables = 12 - sum(bomb_counts.values(), 0)
        if desired_dashables > 0:
            dash_candidates = filter_dashable_candidates(all_candidates, world)
            for chosen in random.sample(dash_candidates, min(desired_dashables, len(all_candidates))):
                change_pair_type(chosen, DoorKind.Dashable, world, player)
                all_candidates.remove(chosen)
        if desired_bombables > 0:
            for chosen in random.sample(all_candidates, min(desired_bombables, len(all_candidates))):
                change_pair_type(chosen, DoorKind.Bombable, world, player)
                all_candidates.remove(chosen)
        for excluded in all_candidates:
            remove_pair_type_if_present(excluded, world, player)


def change_pair_type(door, new_type, world, player):
    room_a = world.get_room(door.roomIndex, player)
    verify_door_list_pos(door, room_a, world, player)
    room_a.change(door.doorListPos, new_type)
    if door.type != DoorType.Interior:
        room_b = world.get_room(door.dest.roomIndex, player)
        verify_door_list_pos(door.dest, room_b, world, player)
        room_b.change(door.dest.doorListPos, new_type)
        add_pair(door, door.dest, world, player)
    spoiler_type = 'Bomb Door' if new_type == DoorKind.Bombable else 'Dash Door'
    world.spoiler.set_door_type(f'{door.name} <-> {door.dest.name} ({door.dungeon_name()})', spoiler_type, player)


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
        start_regions = ['Links House', 'Dark Sanctuary Hint']
    regs = convert_regions(start_regions, world, player)
    all_regions = set([r for r in world.regions if r.player == player and r.type is not RegionType.Dungeon])
    visited_regions = set()
    queue = deque(regs)
    while len(queue) > 0:
        next_region = queue.popleft()
        visited_regions.add(next_region)
        if world.mode[player] == 'inverted' and next_region.name == 'Dark Sanctuary Hint':  # special spawn point in cave
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
    if world.mode[player] == 'inverted':
        ledge = world.get_region('Hyrule Castle Ledge', player)
        if any(x for x in ledge.exits if x.connected_region.name == 'Agahnims Tower Portal'):
            world.inaccessible_regions[player].append('Hyrule Castle Ledge')
    # this should be considered as part of the inaccessible regions, dungeonssimple?
    if world.mode[player] == 'standard' and world.shuffle[player] == 'vanilla':
        world.inaccessible_regions[player].append('Hyrule Castle Ledge')
    logger = logging.getLogger('')
    logger.debug('Inaccessible Regions:')
    for r in world.inaccessible_regions[player]:
        logger.debug('%s', r)


def find_accessible_entrances(world, player, builder):
    entrances = [region.name for region in (portal.door.entrance.parent_region for portal in world.dungeon_portals[player]) if region.dungeon.name == builder.name]
    entrances.extend(drop_entrances[builder.name])
    hc_std = False

    if world.mode[player] == 'standard' and builder.name == 'Hyrule Castle':
        hc_std = True
        start_regions = ['Hyrule Castle Courtyard']
    elif world.mode[player] != 'inverted':
        start_regions = ['Links House', 'Sanctuary', 'Pyramid Area']
    else:
        start_regions = ['Links House', 'Dark Sanctuary Hint', 'Hyrule Castle Ledge']
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
            if hc_std and ext.name in ['Hyrule Castle Main Gate (North)', 'Castle Gate Teleporter (Inner)', 'Hyrule Castle Ledge Drop']:  # just skip it
                continue
            connect = ext.connected_region
            if connect is None or ext.door and ext.door.blocked:
                continue
            if connect.name in entrances and connect not in visited_entrances:
                visited_entrances.append(connect.name)
            elif connect and connect not in queue and connect not in visited_regions:
                queue.append(connect)
    return visited_entrances


def find_possible_entrances(world, player, builder):
    entrances = [region.name for region in
                 (portal.door.entrance.parent_region for portal in world.dungeon_portals[player])
                 if region.dungeon.name == builder.name]
    entrances.extend(drop_entrances[builder.name])
    return entrances


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
        if ext.connected_region and ext.connected_region.name.endswith(' Portal'):
            for more_exts in ext.connected_region.exits:
                create_door(world, player, more_exts.name, ext.connected_region.name)


def create_door(world, player, entName, region_name):
    entrance = world.get_entrance(entName, player)
    connect = entrance.connected_region
    if connect is not None:
        for ext in connect.exits:
            if ext.connected_region and ext.connected_region.name == region_name:
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
                states_to_explore = {}
                for path in paths[dungeon_name]:
                    if type(path) is tuple:
                        states_to_explore[tuple([path[0]])] = (path[1], 'any')
                    else:
                        common_starts = tuple(builder.path_entrances)
                        if common_starts not in states_to_explore:
                            states_to_explore[common_starts] = ([], 'all')
                        states_to_explore[common_starts][0].append(path)
                cached_initial_state = None
                for start_regs, info in states_to_explore.items():
                    dest_regs, path_type = info
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
                    if path_type == 'any':
                        valid, bad_region = check_if_any_regions_visited(state, check_paths)
                    else:
                        valid, bad_region = check_if_all_regions_visited(state, check_paths)
                    if not valid:
                        if check_for_pinball_fix(state, bad_region, world, player):
                            explore_state(state, world, player)
                            if path_type == 'any':
                                valid, bad_region = check_if_any_regions_visited(state, check_paths)
                            else:
                                valid, bad_region = check_if_all_regions_visited(state, check_paths)
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
        if (state.can_traverse(door) and not state.visited(connect_region)
           and valid_region_to_explore(connect_region, state.dungeon, world, player)):
            state.visit_region(connect_region)
            state.add_all_doors_check_unattached(connect_region, world, player)


def explore_state_proposed_traps(state, proposed_traps, world, player):
    while len(state.avail_doors) > 0:
        door = state.next_avail_door().door
        connect_region = world.get_entrance(door.name, player).connected_region
        if (not state.visited(connect_region)
           and valid_region_to_explore(connect_region, state.dungeon, world, player)):
            state.visit_region(connect_region)
            state.add_all_doors_check_proposed_traps(connect_region, proposed_traps, world, player)


def explore_state_not_inaccessible(state, world, player):
    while len(state.avail_doors) > 0:
        door = state.next_avail_door().door
        connect_region = world.get_entrance(door.name, player).connected_region
        if state.can_traverse(door) and not state.visited(connect_region) and connect_region.type == RegionType.Dungeon:
            state.visit_region(connect_region)
            state.add_all_doors_check_unattached(connect_region, world, player)


def check_if_any_regions_visited(state, check_paths):
    valid = False
    breaking_region = None
    for region_target in check_paths:
        if state.visited_at_all(region_target):
            valid = True
            break
        elif not breaking_region:
            breaking_region = region_target
    return valid, breaking_region


def check_if_all_regions_visited(state, check_paths):
    for region_target in check_paths:
        if not state.visited_at_all(region_target):
            return False, region_target
    return True, None


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
    Fix_EG = 0x10  # used to be Rails = 0x10  # Unused bit now
    OriginalPalettes = 0x20
    # Open_PoD_Wall = 0x40  # No longer pre-opening pod wall - unused
    # Open_Desert_Wall = 0x80  # No longer pre-opening desert wall - unused
    Hide_Total = 0x100
    DarkWorld_Spawns = 0x200
    BigKeyDoor_Shuffle = 0x400
    EnemyDropIndicator = 0x800  # if on, enemy drop indicator show, else it doesn't


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
    ('Hera Lobby to Crystal', 'Hera Lobby - Crystal'),
    ('Hera Lobby Crystal Exit', 'Hera Lobby'),
    ('Hera Front to Crystal', 'Hera Front - Crystal'),
    ('Hera Front to Back Bypass', 'Hera Back'),
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
    ('Hera Basement Cage to Crystal', 'Hera Basement Cage - Crystal'),
    ('Hera Basement Cage Crystal Exit', 'Hera Basement Cage'),
    ('Hera Tridorm to Crystal', 'Hera Tridorm - Crystal'),
    ('Hera Tridorm Crystal Exit', 'Hera Tridorm'),
    ('Hera Startile Wide to Crystal', 'Hera Startile Wide - Crystal'),
    ('Hera Startile Wide Crystal Exit', 'Hera Startile Wide'),
    ('Hera Big Chest Hook Path', 'Hera Big Chest Landing'),
    ('Hera Big Chest Landing Exit', 'Hera 4F'),
    ('Hera 5F Orange Path', 'Hera 5F Pot Block'),

    ('PoD Pit Room Block Path N', 'PoD Pit Room Blocked'),
    ('PoD Pit Room Block Path S', 'PoD Pit Room'),
    ('PoD Arena Landing Bonk Path', 'PoD Arena Bridge'),
    ('PoD Arena North Drop Down', 'PoD Arena Main'),
    ('PoD Arena Bridge Drop Down', 'PoD Arena Main'),
    ('PoD Arena North to Landing Barrier - Orange', 'PoD Arena Landing'),
    ('PoD Arena Main to Ranged Crystal', 'PoD Arena Main - Ranged Crystal'),
    ('PoD Arena Main to Landing Barrier - Blue', 'PoD Arena Landing'),
    ('PoD Arena Main to Landing Bypass', 'PoD Arena Landing'),
    ('PoD Arena Main to Right Bypass', 'PoD Arena Right'),
    ('PoD Arena Main Ranged Crystal Exit', 'PoD Arena Main'),
    ('PoD Arena Bridge to Ranged Crystal', 'PoD Arena Bridge - Ranged Crystal'),
    ('PoD Arena Bridge Ranged Crystal Exit', 'PoD Arena Bridge'),
    ('PoD Arena Landing to Main Barrier - Blue', 'PoD Arena Main'),
    ('PoD Arena Landing to Right Barrier - Blue', 'PoD Arena Right'),
    ('PoD Arena Landing to North Barrier - Orange', 'PoD Arena North'),
    ('PoD Arena Right to Landing Barrier - Blue', 'PoD Arena Landing'),
    ('PoD Arena Right to Ranged Crystal', 'PoD Arena Right - Ranged Crystal'),
    ('PoD Arena Right Ranged Crystal Exit', 'PoD Arena Right'),
    ('PoD Arena Ledge to Ranged Crystal', 'PoD Arena Ledge - Ranged Crystal'),
    ('PoD Arena Ledge Ranged Crystal Exit', 'PoD Arena Ledge'),
    ('PoD Map Balcony Drop Down', 'PoD Sexy Statue'),
    ('PoD Map Balcony to Ranged Crystal', 'PoD Map Balcony - Ranged Crystal'),
    ('PoD Map Balcony Ranged Crystal Exit', 'PoD Map Balcony'),
    ('PoD Basement Ledge Drop Down', 'PoD Stalfos Basement'),
    ('PoD Falling Bridge Path N', 'PoD Falling Bridge Mid'),
    ('PoD Falling Bridge Path S', 'PoD Falling Bridge Mid'),
    ('PoD Falling Bridge Mid Path S', 'PoD Falling Bridge'),
    ('PoD Falling Bridge Mid Path N', 'PoD Falling Bridge Ledge'),
    ('PoD Bow Statue Left to Right Barrier - Orange', 'PoD Bow Statue Right'),
    ('PoD Bow Statue Left to Right Bypass', 'PoD Bow Statue Right'),
    ('PoD Bow Statue Left to Crystal', 'PoD Bow Statue Left - Crystal'),
    ('PoD Bow Statue Left Crystal Exit', 'PoD Bow Statue Left'),
    ('PoD Bow Statue Right to Left Barrier - Orange', 'PoD Bow Statue Left'),
    ('PoD Bow Statue Right to Ranged Crystal', 'PoD Bow Statue Right - Ranged Crystal'),
    ('PoD Bow Statue Ranged Crystal Exit', 'PoD Bow Statue Right'),
    ('PoD Dark Pegs Landing to Right', 'PoD Dark Pegs Right'),
    ('PoD Dark Pegs Landing to Ranged Crystal', 'PoD Dark Pegs Landing - Ranged Crystal'),
    ('PoD Dark Pegs Right to Landing', 'PoD Dark Pegs Landing'),
    ('PoD Dark Pegs Right to Middle Barrier - Orange', 'PoD Dark Pegs Middle'),
    ('PoD Dark Pegs Right to Middle Bypass', 'PoD Dark Pegs Middle'),
    ('PoD Dark Pegs Middle to Right Barrier - Orange', 'PoD Dark Pegs Right'),
    ('PoD Dark Pegs Middle to Left Barrier - Blue', 'PoD Dark Pegs Left'),
    ('PoD Dark Pegs Middle to Ranged Crystal', 'PoD Dark Pegs Middle - Ranged Crystal'),
    ('PoD Dark Pegs Left to Middle Barrier - Blue', 'PoD Dark Pegs Middle'),
    ('PoD Dark Pegs Left to Ranged Crystal', 'PoD Dark Pegs Left - Ranged Crystal'),
    ('PoD Dark Pegs Landing Ranged Crystal Exit', 'PoD Dark Pegs Landing'),
    ('PoD Dark Pegs Middle Ranged Crystal Exit', 'PoD Dark Pegs Middle'),
    ('PoD Dark Pegs Middle to Left Bypass', 'PoD Dark Pegs Left'),
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
    ('Swamp Hub Side Hook Path', 'Swamp Hub Side Ledges'),
    ('Swamp Hub North Ledge Drop Down', 'Swamp Hub'),
    ('Swamp Crystal Switch Outer to Inner Barrier - Blue', 'Swamp Crystal Switch Inner'),
    ('Swamp Crystal Switch Outer to Ranged Crystal', 'Swamp Crystal Switch Outer - Ranged Crystal'),
    ('Swamp Crystal Switch Outer to Inner Bypass', 'Swamp Crystal Switch Inner'),
    ('Swamp Crystal Switch Outer Ranged Crystal Exit', 'Swamp Crystal Switch Outer'),
    ('Swamp Crystal Switch Inner to Outer Barrier - Blue', 'Swamp Crystal Switch Outer'),
    ('Swamp Crystal Switch Inner to Outer Bypass', 'Swamp Crystal Switch Outer'),
    ('Swamp Crystal Switch Inner to Crystal', 'Swamp Crystal Switch Inner - Crystal'),
    ('Swamp Crystal Switch Inner Crystal Exit', 'Swamp Crystal Switch Inner'),
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
    ('Skull 2 West Lobby Pits', 'Skull 2 West Lobby Ledge'),
    ('Skull 2 West Lobby Ledge Pits', 'Skull 2 West Lobby'),
    ('Thieves Rail Ledge Drop Down', 'Thieves BK Corner'),
    ('Thieves Hellway Orange Barrier', 'Thieves Hellway S Crystal'),
    ('Thieves Hellway Crystal Orange Barrier', 'Thieves Hellway'),
    ('Thieves Hellway Blue Barrier', 'Thieves Hellway N Crystal'),
    ('Thieves Hellway Crystal Blue Barrier', 'Thieves Hellway'),
    ('Thieves Attic Orange Barrier', 'Thieves Attic Hint'),
    ('Thieves Attic Blue Barrier', 'Thieves Attic Switch'),
    ('Thieves Attic Hint Orange Barrier', 'Thieves Attic'),
    ('Thieves Attic Switch Blue Barrier', 'Thieves Attic'),
    ('Thieves Basement Block Path', 'Thieves Blocked Entry'),
    ('Thieves Blocked Entry Path', 'Thieves Basement Block'),
    ('Thieves Conveyor Bridge Block Path', 'Thieves Conveyor Block'),
    ('Thieves Conveyor Block Path', 'Thieves Conveyor Bridge'),
    ("Thieves Blind's Cell Door", "Thieves Blind's Cell Interior"),
    ("Thieves Blind's Cell Exit", "Thieves Blind's Cell"),

    ('Ice Cross Bottom Push Block Left', 'Ice Floor Switch'),
    ('Ice Cross Right Push Block Top', 'Ice Bomb Drop'),
    ('Ice Bomb Drop Path', 'Ice Bomb Drop - Top'),
    ('Ice Conveyor to Crystal', 'Ice Conveyor - Crystal'),
    ('Ice Conveyor Crystal Exit', 'Ice Conveyor'),
    ('Ice Big Key Push Block', 'Ice Dead End'),
    ('Ice Bomb Jump Ledge Orange Barrier', 'Ice Bomb Jump Catwalk'),
    ('Ice Bomb Jump Catwalk Orange Barrier', 'Ice Bomb Jump Ledge'),
    ('Ice Right H Path', 'Ice Hammer Block'),
    ('Ice Hammer Block Path', 'Ice Right H'),
    ('Ice Hookshot Ledge Path', 'Ice Hookshot Balcony'),
    ('Ice Hookshot Balcony Path', 'Ice Hookshot Ledge'),
    ('Ice Crystal Right Orange Barrier', 'Ice Crystal Left'),
    ('Ice Crystal Left Orange Barrier', 'Ice Crystal Right'),
    ('Ice Crystal Left Blue Barrier', 'Ice Crystal Block'),
    ('Ice Crystal Block Exit', 'Ice Crystal Left'),
    ('Ice Big Chest Landing Push Blocks', 'Ice Big Chest View'),
    ('Ice Refill to Crystal', 'Ice Refill - Crystal'),
    ('Ice Refill Crystal Exit', 'Ice Refill'),

    ('Mire Lobby Gap', 'Mire Post-Gap'),
    ('Mire Post-Gap Gap', 'Mire Lobby'),
    ('Mire Hub Upper Blue Barrier', 'Mire Hub Switch'),
    ('Mire Hub Lower Blue Barrier', 'Mire Hub Right'),
    ('Mire Hub Right Blue Barrier', 'Mire Hub'),
    ('Mire Hub Top Blue Barrier', 'Mire Hub Switch'),
    ('Mire Hub Switch Blue Barrier N', 'Mire Hub Top'),
    ('Mire Hub Switch Blue Barrier S', 'Mire Hub'),
    ('Mire Falling Bridge Hook Path', 'Mire Falling Bridge - Chest'),
    ('Mire Falling Bridge Hook Only Path', 'Mire Falling Bridge - Chest'),
    ('Mire Falling Bridge Failure Path', 'Mire Falling Bridge - Failure'),
    ('Mire Map Spike Side Drop Down', 'Mire Lone Shooter'),
    ('Mire Map Spike Side Blue Barrier', 'Mire Crystal Dead End'),
    ('Mire Map Spot Blue Barrier', 'Mire Crystal Dead End'),
    ('Mire Crystal Dead End Left Barrier', 'Mire Map Spot'),
    ('Mire Crystal Dead End Right Barrier', 'Mire Map Spike Side'),
    ('Mire Hidden Shooters Block Path S', 'Mire Hidden Shooters'),
    ('Mire Hidden Shooters Block Path N', 'Mire Hidden Shooters Blocked'),
    ('Mire Conveyor to Crystal', 'Mire Conveyor - Crystal'),
    ('Mire Conveyor Crystal Exit', 'Mire Conveyor Crystal'),
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
    ('Mire Fishbone Blue Barrier Bypass', 'Mire South Fish'),

    ('TR Main Lobby Gap', 'TR Lobby Ledge'),
    ('TR Lobby Ledge Gap', 'TR Main Lobby'),
    ('TR Hub Path', 'TR Hub Ledges'),
    ('TR Hub Ledges Path', 'TR Hub'),
    ('TR Pipe Ledge Drop Down', 'TR Pipe Pit'),
    ('TR Big Chest Gap', 'TR Big Chest Entrance'),
    ('TR Big Chest Entrance Gap', 'TR Big Chest'),
    ('TR Chain Chomps Top to Bottom Barrier - Orange', 'TR Chain Chomps Bottom'),
    ('TR Chain Chomps Top to Crystal', 'TR Chain Chomps Top - Crystal'),
    ('TR Chain Chomps Top Crystal Exit', 'TR Chain Chomps Top'),
    ('TR Chain Chomps Bottom to Top Barrier - Orange', 'TR Chain Chomps Top'),
    ('TR Chain Chomps Bottom to Ranged Crystal', 'TR Chain Chomps Bottom - Ranged Crystal'),
    ('TR Chain Chomps Bottom Ranged Crystal Exit', 'TR Chain Chomps Bottom'),
    ('TR Pokey 2 Top to Bottom Barrier - Blue', 'TR Pokey 2 Bottom'),
    ('TR Pokey 2 Top to Crystal', 'TR Pokey 2 Top - Crystal'),
    ('TR Pokey 2 Top Crystal Exit', 'TR Pokey 2 Top'),
    ('TR Pokey 2 Bottom to Top Barrier - Blue', 'TR Pokey 2 Top'),
    ('TR Pokey 2 Bottom to Ranged Crystal', 'TR Pokey 2 Bottom - Ranged Crystal'),
    ('TR Pokey 2 Bottom Ranged Crystal Exit', 'TR Pokey 2 Bottom'),
    ('TR Crystaroller Bottom to Middle Barrier - Orange', 'TR Crystaroller Middle'),
    ('TR Crystaroller Bottom to Ranged Crystal', 'TR Crystaroller Bottom - Ranged Crystal'),
    ('TR Crystaroller Middle to Bottom Barrier - Orange', 'TR Crystaroller Bottom'),
    ('TR Crystaroller Middle to Bottom Bypass', 'TR Crystaroller Bottom'),
    ('TR Crystaroller Middle to Chest Barrier - Blue', 'TR Crystaroller Chest'),
    ('TR Crystaroller Middle to Top Barrier - Orange', 'TR Crystaroller Top'),
    ('TR Crystaroller Middle to Ranged Crystal', 'TR Crystaroller Middle - Ranged Crystal'),
    ('TR Crystaroller Top to Middle Barrier - Orange', 'TR Crystaroller Middle'),
    ('TR Crystaroller Top to Crystal', 'TR Crystaroller Top - Crystal'),
    ('TR Crystaroller Top Crystal Exit', 'TR Crystaroller Top'),
    ('TR Crystaroller Chest to Middle Barrier - Blue', 'TR Crystaroller Middle'),
    ('TR Crystaroller Middle Ranged Crystal Exit', 'TR Crystaroller Middle'),
    ('TR Crystaroller Bottom Ranged Crystal Exit', 'TR Crystaroller Bottom'),
    ('TR Dark Ride Path', 'TR Dark Ride Ledges'),
    ('TR Dark Ride Ledges Path', 'TR Dark Ride'),
    ('TR Crystal Maze Start to Interior Barrier - Blue', 'TR Crystal Maze Interior'),
    ('TR Crystal Maze Start to Crystal', 'TR Crystal Maze Start - Crystal'),
    ('TR Crystal Maze Start Crystal Exit', 'TR Crystal Maze Start'),
    ('TR Crystal Maze Interior to End Barrier - Blue', 'TR Crystal Maze End'),
    ('TR Crystal Maze Interior to Start Barrier - Blue', 'TR Crystal Maze Start'),
    ('TR Crystal Maze Interior to End Bypass', 'TR Crystal Maze End'),
    ('TR Crystal Maze Interior to Start Bypass', 'TR Crystal Maze Start'),
    ('TR Crystal Maze End to Interior Barrier - Blue', 'TR Crystal Maze Interior'),
    ('TR Crystal Maze End to Ranged Crystal', 'TR Crystal Maze End - Ranged Crystal'),
    ('TR Crystal Maze End Ranged Crystal Exit', 'TR Crystal Maze End'),
    ('TR Final Abyss Balcony Path', 'TR Final Abyss Ledge'),
    ('TR Final Abyss Ledge Path', 'TR Final Abyss Balcony'),

    ('GT Blocked Stairs Block Path', 'GT Big Chest'),
    ('GT Speed Torch South Path', 'GT Speed Torch'),
    ('GT Speed Torch North Path', 'GT Speed Torch Upper'),
    ('GT Conveyor Cross Hammer Path', 'GT Conveyor Cross Across Pits'),
    ('GT Conveyor Cross Hookshot Path', 'GT Conveyor Cross'),
    ('GT Hookshot East-Mid Path', 'GT Hookshot Mid Platform'),
    ('GT Hookshot Mid-East Path', 'GT Hookshot East Platform'),
    ('GT Hookshot North-Mid Path', 'GT Hookshot Mid Platform'),
    ('GT Hookshot Mid-North Path', 'GT Hookshot North Platform'),
    ('GT Hookshot South-Mid Path', 'GT Hookshot Mid Platform'),
    ('GT Hookshot Mid-South Path', 'GT Hookshot South Platform'),
    ('GT Hookshot Platform Blue Barrier', 'GT Hookshot South Entry'),
    ('GT Hookshot Platform Barrier Bypass', 'GT Hookshot South Entry'),
    ('GT Hookshot Entry Blue Barrier', 'GT Hookshot South Platform'),
    ('GT Hookshot South Entry to Ranged Crystal',  'GT Hookshot South Entry - Ranged Crystal'),
    ('GT HookShot South Entry Ranged Crystal Exit', 'GT Hookshot South Entry'),
    ('GT Double Switch Entry to Pot Corners Barrier - Orange', 'GT Double Switch Pot Corners'),
    ('GT Double Switch Entry to Left Barrier - Orange', 'GT Double Switch Left'),
    ('GT Double Switch Entry to Ranged Switches', 'GT Double Switch Entry - Ranged Switches'),
    ('GT Double Switch Entry Ranged Switches Exit', 'GT Double Switch Entry'),
    ('GT Double Switch Left to Crystal', 'GT Double Switch Left - Crystal'),
    ('GT Double Switch Left Crystal Exit', 'GT Double Switch Left'),
    ('GT Double Switch Left to Entry Barrier - Orange', 'GT Double Switch Entry'),
    ('GT Double Switch Left to Entry Bypass', 'GT Double Switch Entry'),
    ('GT Double Switch Left to Pot Corners Bypass', 'GT Double Switch Pot Corners'),
    ('GT Double Switch Left to Exit Bypass', 'GT Double Switch Exit'),
    ('GT Double Switch Pot Corners to Entry Barrier - Orange', 'GT Double Switch Entry'),
    ('GT Double Switch Pot Corners to Exit Barrier - Blue', 'GT Double Switch Exit'),
    ('GT Double Switch Pot Corners to Ranged Switches', 'GT Double Switch Pot Corners - Ranged Switches'),
    ('GT Double Switch Pot Corners Ranged Switches Exit', 'GT Double Switch Pot Corners'),
    ('GT Double Switch Exit to Blue Barrier', 'GT Double Switch Pot Corners'),
    ('GT Spike Crystal Left to Right Barrier - Orange', 'GT Spike Crystal Right'),
    ('GT Spike Crystal Right to Left Barrier - Orange', 'GT Spike Crystal Left'),
    ('GT Spike Crystal Left to Right Bypass', 'GT Spike Crystal Right'),
    ('GT Warp Maze - Pit Section Warp Spot', 'GT Warp Maze - Pit Exit Warp Spot'),
    ('GT Warp Maze Exit Section Warp Spot', 'GT Warp Maze - Pit Exit Warp Spot'),
    ('GT Firesnake Room Hook Path', 'GT Firesnake Room Ledge'),

    ('GT Crystal Conveyor to Corner Barrier - Blue', 'GT Crystal Conveyor Corner'),
    ('GT Crystal Conveyor to Ranged Crystal', 'GT Crystal Conveyor - Ranged Crystal'),
    ('GT Crystal Conveyor Corner to Left Bypass', 'GT Crystal Conveyor Left'),
    ('GT Crystal Conveyor Corner to Barrier - Blue', 'GT Crystal Conveyor'),
    ('GT Crystal Conveyor Corner to Barrier - Orange', 'GT Crystal Conveyor Left'),
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
    ('Mire Falling Bridge Primary Path', 'Mire Lone Shooter'),
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
    ('Sewers Dark Aquabats N', 'Sewers Key Rat S'),
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
    ('PoD Map Balcony ES', 'PoD Fairy Pool WS'),
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
    ('Skull Big Key EN', 'Skull Lone Pot WN'),
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
    ('Mire Torches Bottom ES', 'Mire Attic Hint WS'),
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
    ('Sewers Key Rat NE', 'Sewers Secret Room Key Door S'),
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
        ('Sewers Key Rat NE', 'Sewers Secret Room Key Door S'),
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
    ('Sewers Water W', 'Sewers Dark Aquabats ES'),
    ('Sewers Key Rat NE', 'Sewers Secret Room Key Door S'),
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
    ('Desert Compass NE', 'Desert Cannonball S'),
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
    'Ganons Tower': (0x28, 0x1b, 'GT Agahnim 2 SW'),
    # other palettes: 0x1a (other) 0x24 (Gauntlet - Lanmo) 0x25 (conveyor-torch-wizzrobe moldorm pit f5?)
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


multiple_portal_map = {
    'Hyrule Castle': ['Sanctuary', 'Hyrule Castle West', 'Hyrule Castle South', 'Hyrule Castle East'],
    'Desert Palace': ['Desert West', 'Desert South', 'Desert East', 'Desert Back'],
    'Skull Woods': ['Skull 1', 'Skull 2 West', 'Skull 2 East', 'Skull 3'],
    'Turtle Rock': ['Turtle Rock Lazy Eyes', 'Turtle Rock Eye Bridge', 'Turtle Rock Chest', 'Turtle Rock Main'],
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

# small, big, trap, bomb, dash, hidden, tricky
door_type_counts = {
    'Hyrule Castle': (4, 0, 1, 0, 2, 0, 0),
    'Eastern Palace': (2, 2, 0, 0, 0, 0, 0),
    'Desert Palace': (4, 1, 0, 0, 0, 0, 0),
    'Agahnims Tower': (4, 0, 1, 0, 0, 1, 0),
    'Swamp Palace': (6, 0, 0, 2, 0, 0, 0),
    'Palace of Darkness': (6, 1, 1, 3, 2, 0, 0),
    'Misery Mire': (6, 3, 5, 2, 0, 0, 0),
    'Skull Woods': (5, 0, 1, 2, 0, 1, 0),
    'Ice Palace': (6, 1, 3, 0, 0, 0, 0),
    'Tower of Hera': (1, 1, 0, 0, 0, 0, 0),
    'Thieves Town': (3, 1, 2, 1, 1, 0, 0),
    'Turtle Rock': (6, 2, 2, 0, 2, 0, 1),  # 2 bombs kind of for entrances, but I put 0 here
    'Ganons Tower': (8, 2, 5, 2, 1, 0, 0)
}


