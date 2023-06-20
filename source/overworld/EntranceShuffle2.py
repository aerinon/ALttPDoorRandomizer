import RaceRandom as random
import logging
import copy

from collections import defaultdict


class EntrancePool(object):
    def __init__(self, world, player):
        self.entrances = set()
        self.exits = set()
        self.inverted = False
        self.coupled = True
        self.default_map = {}
        self.one_way_map = {}
        self.skull_handled = False
        self.links_on_mountain = False
        self.decoupled_entrances = []
        self.decoupled_exits = []
        self.original_entrances = set()
        self.original_exits = set()

        self.world = world
        self.player = player

    def is_standard(self):
        return self.world.mode[self.player] == 'standard'


class Restrictions(object):
    def __init__(self):
        self.size = None
        self.must_exit_to_lw = False
        self.fixed = False
        # must_exit_to_dw = False
        # same_world = False


def link_entrances_new(world, player):
    avail_pool = EntrancePool(world, player)
    i_drop_map = {x: y for x, y in drop_map.items() if not x.startswith('Inverted')}
    i_entrance_map = {x: y for x, y in entrance_map.items() if not x.startswith('Inverted')}
    i_single_ent_map = {x: y for x, y in single_entrance_map.items()}

    avail_pool.entrances = set(i_drop_map.keys()).union(i_entrance_map.keys()).union(i_single_ent_map.keys())
    avail_pool.exits = set(i_entrance_map.values()).union(i_drop_map.values()).union(i_single_ent_map.values())
    avail_pool.exits.add('Chris Houlihan Room Exit')
    avail_pool.inverted = world.mode[player] == 'inverted'
    inverted_substitution(avail_pool, avail_pool.entrances, True, True)
    inverted_substitution(avail_pool, avail_pool.exits, False, True)
    avail_pool.original_entrances.update(avail_pool.entrances)
    avail_pool.original_exits.update(avail_pool.exits)
    default_map = {}
    default_map.update(entrance_map)
    one_way_map = {}
    one_way_map.update(drop_map)
    one_way_map.update(single_entrance_map)
    if avail_pool.inverted:
        default_map['Ganons Tower'] = 'Agahnims Tower Exit'
        default_map['Agahnims Tower'] = 'Ganons Tower Exit'
        default_map['Old Man Cave (West)'] = 'Bumper Cave Exit (Bottom)'
        default_map['Death Mountain Return Cave (West)'] = 'Bumper Cave Exit (Top)'
        default_map['Bumper Cave (Bottom)'] = 'Old Man Cave Exit (West)'
        default_map['Dark Death Mountain Fairy'] = 'Old Man Cave Exit (East)'
        del one_way_map['Dark Death Mountain Fairy']
        default_map['Old Man Cave (East)'] = 'Death Mountain Return Cave Exit (West)'
        one_way_map['Bumper Cave (Top)'] = 'Dark Death Mountain Healer Fairy'
        del default_map['Bumper Cave (Top)']
    avail_pool.default_map = default_map
    avail_pool.one_way_map = one_way_map

    # setup mandatory connections
    for exit_name, region_name in mandatory_connections:
        connect_simple(world, exit_name, region_name, player)
    if not avail_pool.inverted:
        for exit_name, region_name in open_mandatory_connections:
            connect_simple(world, exit_name, region_name, player)
    else:
        for exit_name, region_name in inverted_mandatory_connections:
            connect_simple(world, exit_name, region_name, player)

    connect_custom(avail_pool, world, player)

    if world.shuffle[player] == 'vanilla':
        do_vanilla_connections(avail_pool)
    else:
        mode = world.shuffle[player]
        if mode not in modes:
            raise RuntimeError(f'Shuffle mode {mode} is not yet supported')
        mode_cfg = copy.deepcopy(modes[mode])
        if avail_pool.is_standard():
            do_standard_connections(avail_pool)
        pool_list = mode_cfg['pools'] if 'pools' in mode_cfg else {}
        for pool_name, pool in pool_list.items():
            special_shuffle = pool['special'] if 'special' in pool else None
            if special_shuffle == 'drops':
                holes, targets = find_entrances_and_targets_drops(avail_pool, pool['entrances'])
                connect_random(holes, targets, avail_pool)
            elif special_shuffle == 'fixed_shuffle':
                do_fixed_shuffle(avail_pool, pool['entrances'])
            elif special_shuffle == 'same_world':
                do_same_world_shuffle(avail_pool, pool)
            elif special_shuffle == 'simple_connector':
                do_connector_shuffle(avail_pool, pool)
            elif special_shuffle == 'old_man_cave_east':
                exits = [x for x in pool['entrances'] if x in avail_pool.exits]
                cross_world = mode_cfg['cross_world'] == 'on' if 'cross_world' in mode_cfg else False
                do_old_man_cave_exit(set(avail_pool.entrances), exits, avail_pool, cross_world)
            elif special_shuffle == 'inverted_fixed':
                if avail_pool.inverted:
                    connect_two_way(pool['entrance'], pool['exit'], avail_pool)
            elif special_shuffle == 'limited':
                do_limited_shuffle(pool, avail_pool)
            elif special_shuffle == 'limited_lw':
                do_limited_shuffle_exclude_drops(pool, avail_pool)
            elif special_shuffle == 'limited_dw':
                do_limited_shuffle_exclude_drops(pool, avail_pool, False)
            elif special_shuffle == 'vanilla':
                do_vanilla_connect(pool, avail_pool)
            elif special_shuffle == 'skull':
                entrances, exits = find_entrances_and_exits(avail_pool, pool['entrances'])
                connect_random(entrances, exits, avail_pool, True)
                avail_pool.skull_handled = True
            else:
                entrances, exits = find_entrances_and_exits(avail_pool, pool['entrances'])
                do_main_shuffle(entrances, exits, avail_pool, mode_cfg)
        undefined_behavior = mode_cfg['undefined']
        if undefined_behavior == 'vanilla':
            do_vanilla_connections(avail_pool)
        elif undefined_behavior == 'shuffle':
            do_main_shuffle(set(avail_pool.entrances), set(avail_pool.exits), avail_pool, mode_cfg)

    # afterward

    # check for swamp palace fix
    if (world.get_entrance('Dam', player).connected_region.name != 'Dam'
       or world.get_entrance('Swamp Palace', player).connected_region.name != 'Swamp Portal'):
        world.swamp_patch_required[player] = True

    # check for potion shop location
    if world.get_entrance('Potion Shop', player).connected_region.name != 'Potion Shop':
        world.powder_patch_required[player] = True

    # check for ganon location
    pyramid_hole = 'Inverted Pyramid Hole' if avail_pool.inverted else 'Pyramid Hole'
    if world.get_entrance(pyramid_hole, player).connected_region.name != 'Pyramid':
        world.ganon_at_pyramid[player] = False

    # check for Ganon's Tower location
    gt = 'Agahnims Tower' if avail_pool.world.is_atgt_swapped(avail_pool.player) else 'Ganons Tower'
    if world.get_entrance(gt, player).connected_region.name != 'Ganons Tower Portal':
        world.ganonstower_vanilla[player] = False


def do_vanilla_connections(avail_pool):
    if 'Chris Houlihan Room Exit' in avail_pool.exits:
        lh = 'Big Bomb Shop' if avail_pool.inverted else 'Links House'
        connect_exit('Chris Houlihan Room Exit', lh, avail_pool)
    for ent in list(avail_pool.entrances):
        if ent in avail_pool.default_map and avail_pool.default_map[ent] in avail_pool.exits:
            connect_vanilla_two_way(ent, avail_pool.default_map[ent], avail_pool)
        if ent in avail_pool.one_way_map and avail_pool.one_way_map[ent] in avail_pool.exits:
            connect_vanilla(ent, avail_pool.one_way_map[ent], avail_pool)


def do_main_shuffle(entrances, exits, avail, mode_def):
    # drops and holes
    cross_world = mode_def['cross_world'] == 'on' if 'cross_world' in mode_def else False
    keep_together = mode_def['keep_drops_together'] == 'on' if 'keep_drops_together' in mode_def else True
    avail.coupled = mode_def['decoupled'] != 'on' if 'decoupled' in mode_def else True
    do_holes_and_linked_drops(entrances, exits, avail, cross_world, keep_together)

    if not avail.coupled:
        avail.decoupled_entrances.extend(entrances)
        avail.decoupled_exits.extend(exits)

    if not avail.world.shuffle_ganon:
        if avail.world.is_atgt_swapped(avail.player) and 'Agahnims Tower' in entrances:
            connect_two_way('Agahnims Tower', 'Ganons Tower Exit', avail)
            entrances.remove('Agahnims Tower')
            exits.remove('Ganons Tower Exit')
            if not avail.coupled:
                avail.decoupled_entrances.remove('Agahnims Tower')
                avail.decoupled_exits.remove('Ganons Tower Exit')
        elif 'Ganons Tower' in entrances:
            connect_two_way('Ganons Tower', 'Ganons Tower Exit', avail)
            entrances.remove('Ganons Tower')
            exits.remove('Ganons Tower Exit')
            if not avail.coupled:
                avail.decoupled_entrances.remove('Ganons Tower')
                avail.decoupled_exits.remove('Ganons Tower Exit')

    # back of tavern
    if not avail.world.shuffletavern[avail.player] and 'Tavern North' in entrances:
        connect_entrance('Tavern North', 'Tavern', avail)
        entrances.remove('Tavern North')
        exits.remove('Tavern')
        if not avail.coupled:
            avail.decoupled_entrances.remove('Tavern North')

    # links house / houlihan
    do_links_house(entrances, exits, avail, cross_world)

    # inverted sanc
    if avail.inverted and 'Dark Sanctuary Hint' in exits:
        choices = [e for e in Inverted_Dark_Sanctuary_Doors if e in entrances]
        choice = random.choice(choices)
        entrances.remove(choice)
        exits.remove('Dark Sanctuary Hint')
        connect_entrance(choice, 'Dark Sanctuary Hint', avail)
        ext = avail.world.get_entrance('Dark Sanctuary Hint Exit', avail.player)
        ext.connect(avail.world.get_entrance(choice, avail.player).parent_region)
        if not avail.coupled:
            avail.decoupled_entrances.remove(choice)

    # mandatory exits
    rem_entrances, rem_exits = set(), set()
    if not cross_world:
        mand_exits = figure_out_must_exits_same_world(entrances, exits, avail)
        must_exit_lw, must_exit_dw, lw_entrances, dw_entrances, multi_exit_caves, hyrule_forced = mand_exits
        if hyrule_forced:
            do_mandatory_connections(avail, lw_entrances, hyrule_forced, must_exit_lw)
        else:
            do_mandatory_connections(avail, lw_entrances, multi_exit_caves, must_exit_lw)
        # remove old man house as connector - not valid for dw must_exit if it is a spawn point
        if not avail.inverted:
            new_mec = []
            for cave_option in multi_exit_caves:
                if any('Old Man House' in cave for cave in cave_option):
                    rem_exits.update([item for item in cave_option])
                else:
                    new_mec.append(cave_option)
            multi_exit_caves = new_mec
        do_mandatory_connections(avail, dw_entrances, multi_exit_caves, must_exit_dw)
        rem_entrances.update(lw_entrances)
        rem_entrances.update(dw_entrances)
    else:
        # cross world mandantory
        entrance_list = list(entrances)
        must_exit, multi_exit_caves = figure_out_must_exits_cross_world(entrances, exits, avail)
        do_mandatory_connections(avail, entrance_list, multi_exit_caves, must_exit)
        rem_entrances.update(entrance_list)

    rem_exits.update([x for item in multi_exit_caves for x in item])
    rem_exits.update(exits)

    # old man cave
    do_old_man_cave_exit(rem_entrances, rem_exits, avail, cross_world)

    # blacksmith
    if 'Blacksmiths Hut' in rem_exits:
        blacksmith_options = [x for x in Blacksmith_Options if x in rem_entrances]
        blacksmith_choice = random.choice(blacksmith_options)
        connect_entrance(blacksmith_choice, 'Blacksmiths Hut', avail)
        rem_entrances.remove(blacksmith_choice)
        if not avail.coupled:
            avail.decoupled_exits.remove('Blacksmiths Hut')
        rem_exits.remove('Blacksmiths Hut')

    # bomb shop
    bomb_shop = 'Links House' if avail.inverted else 'Big Bomb Shop'
    if bomb_shop in rem_exits:
        bomb_shop_options = Inverted_Bomb_Shop_Options if avail.inverted else Bomb_Shop_Options
        bomb_shop_options = [x for x in bomb_shop_options if x in rem_entrances]
        bomb_shop_choice = random.choice(bomb_shop_options)
        connect_entrance(bomb_shop_choice, bomb_shop, avail)
        rem_entrances.remove(bomb_shop_choice)
        if not avail.coupled:
            avail.decoupled_exits.remove(bomb_shop)
        rem_exits.remove(bomb_shop)

    def bonk_fairy_exception(x):  # (Bonk Fairy not eligible in standard)
        return not avail.is_standard() or x != 'Bonk Fairy (Light)'
    if not cross_world:
        # OM Cave entrance in lw/dw if cross_world off
        if 'Old Man Cave Exit (West)' in rem_exits:
            world_limiter = DW_Entrances if avail.inverted else LW_Entrances
            om_cave_options = sorted([x for x in rem_entrances if x in world_limiter and bonk_fairy_exception(x)])
            om_cave_choice = random.choice(om_cave_options)
            if not avail.coupled:
                connect_exit('Old Man Cave Exit (West)', om_cave_choice, avail)
                avail.decoupled_entrances.remove(om_cave_choice)
            else:
                connect_two_way(om_cave_choice, 'Old Man Cave Exit (West)', avail)
                rem_entrances.remove(om_cave_choice)
            rem_exits.remove('Old Man Cave Exit (West)')
        # OM House in lw/dw if cross_world off
        om_house = ['Old Man House Exit (Bottom)', 'Old Man House Exit (Top)']
        if not avail.inverted:  # we don't really care where this ends up in inverted?
            for ext in om_house:
                if ext in rem_exits:
                    om_house_options = [x for x in rem_entrances if x in LW_Entrances and bonk_fairy_exception(x)]
                    om_house_choice = random.choice(om_house_options)
                    if not avail.coupled:
                        connect_exit(ext, om_house_choice, avail)
                        avail.decoupled_entrances.remove(om_house_choice)
                    else:
                        connect_two_way(om_house_choice, ext, avail)
                        rem_entrances.remove(om_house_choice)
                    rem_exits.remove(ext)

    # the rest of the caves
    multi_exit_caves = figure_out_true_exits(rem_exits, avail)
    unused_entrances = set()
    if not cross_world:
        lw_entrances, dw_entrances = [], []
        left = sorted(rem_entrances)
        for x in left:
            if bonk_fairy_exception(x):
                lw_entrances.append(x) if x in LW_Entrances else dw_entrances.append(x)
        do_same_world_connectors(lw_entrances, dw_entrances, multi_exit_caves, avail)
        unused_entrances.update(lw_entrances)
        unused_entrances.update(dw_entrances)
    else:
        entrance_list = sorted([x for x in rem_entrances if bonk_fairy_exception(x)])
        do_cross_world_connectors(entrance_list, multi_exit_caves, avail)
        unused_entrances.update(entrance_list)

    if avail.is_standard() and 'Bonk Fairy (Light)' in rem_entrances:
        rem_entrances = list(unused_entrances) + ['Bonk Fairy (Light)']
    else:
        rem_entrances = list(unused_entrances)
    rem_entrances.sort()
    rem_exits = list(rem_exits if avail.coupled else avail.decoupled_exits)
    rem_exits.sort()
    random.shuffle(rem_entrances)
    random.shuffle(rem_exits)
    placing = min(len(rem_entrances), len(rem_exits))
    for door, target in zip(rem_entrances, rem_exits):
        connect_entrance(door, target, avail)
    rem_entrances[:] = rem_entrances[placing:]
    rem_exits[:] = rem_exits[placing:]
    if rem_entrances or rem_exits:
        logging.getLogger('').warning(f'Unplaced entrances/exits: {", ".join(rem_entrances + rem_exits)}')


def do_old_man_cave_exit(entrances, exits, avail, cross_world):
    if 'Old Man Cave Exit (East)' in exits:
        om_cave_options = Inverted_Old_Man_Entrances if avail.inverted else Old_Man_Entrances
        if avail.inverted and cross_world:
            om_cave_options = Inverted_Old_Man_Entrances + Old_Man_Entrances
        om_cave_options = [x for x in om_cave_options if x in entrances]
        om_cave_choice = random.choice(om_cave_options)
        if not avail.coupled:
            connect_exit('Old Man Cave Exit (East)', om_cave_choice, avail)
            avail.decoupled_entrances.remove(om_cave_choice)
        else:
            connect_two_way(om_cave_choice, 'Old Man Cave Exit (East)', avail)
            entrances.remove(om_cave_choice)
        exits.remove('Old Man Cave Exit (East)')


def do_standard_connections(avail):
    connect_two_way('Hyrule Castle Entrance (South)', 'Hyrule Castle Exit (South)', avail)
    # cannot move uncle cave
    connect_two_way('Hyrule Castle Secret Entrance Stairs', 'Hyrule Castle Secret Entrance Exit', avail)
    connect_entrance('Hyrule Castle Secret Entrance Drop', 'Hyrule Castle Secret Entrance', avail)
    connect_two_way('Links House', 'Links House Exit', avail)
    connect_exit('Chris Houlihan Room Exit', 'Links House', avail)


def remove_from_list(t_list, removals):
    for r in removals:
        t_list.remove(r)


def do_holes_and_linked_drops(entrances, exits, avail, cross_world, keep_together):
    holes_to_shuffle = [x for x in entrances if x in drop_map]

    if not avail.world.shuffle_ganon:
        if avail.inverted and 'Inverted Pyramid Hole' in holes_to_shuffle:
            connect_entrance('Inverted Pyramid Hole', 'Pyramid', avail)
            connect_two_way('Pyramid Entrance', 'Pyramid Exit', avail)
            holes_to_shuffle.remove('Inverted Pyramid Hole')
            remove_from_list(entrances, ['Inverted Pyramid Hole', 'Pyramid Entrance'])
            remove_from_list(exits, ['Pyramid', 'Pyramid Exit'])
        elif 'Pyramid Hole' in holes_to_shuffle:
            connect_entrance('Pyramid Hole', 'Pyramid', avail)
            connect_two_way('Pyramid Entrance', 'Pyramid Exit', avail)
            holes_to_shuffle.remove('Pyramid Hole')
            remove_from_list(entrances, ['Pyramid Hole', 'Pyramid Entrance'])
            remove_from_list(exits, ['Pyramid', 'Pyramid Exit'])

    if not keep_together:
        targets = [avail.one_way_map[x] for x in holes_to_shuffle]
        connect_random(holes_to_shuffle, targets, avail)
        remove_from_list(entrances, holes_to_shuffle)
        remove_from_list(exits, targets)
        return  # we're done here

    hole_entrances, hole_targets = [], []
    for hole in drop_map:
        if hole in avail.original_entrances and hole in linked_drop_map:
            linked_entrance = linked_drop_map[hole]
            if hole in entrances and linked_entrance in entrances:
                hole_entrances.append((linked_entrance, hole))
            target_exit = avail.default_map[linked_entrance]
            target_drop = avail.one_way_map[hole]
            if target_exit in exits and target_drop in exits:
                hole_targets.append((target_exit, target_drop))

    random.shuffle(hole_entrances)
    if not cross_world and 'Sanctuary Grave' in holes_to_shuffle:
        lw_entrance = next(entrance for entrance in hole_entrances if entrance[0] in LW_Entrances)
        hole_entrances.remove(lw_entrance)
        sanc_interior = next(target for target in hole_targets if target[0] == 'Sanctuary Exit')
        hole_targets.remove(sanc_interior)
        connect_two_way(lw_entrance[0], sanc_interior[0], avail)  # two-way exit
        connect_entrance(lw_entrance[1], sanc_interior[1], avail)  # hole
        remove_from_list(entrances, [lw_entrance[0], lw_entrance[1]])
        remove_from_list(exits, [sanc_interior[0], sanc_interior[1]])

    random.shuffle(hole_targets)
    for entrance, drop in hole_entrances:
        ext, target = hole_targets.pop()
        connect_two_way(entrance, ext, avail)
        connect_entrance(drop, target, avail)
        remove_from_list(entrances, [entrance, drop])
        remove_from_list(exits, [ext, target])


def do_links_house(entrances, exits, avail, cross_world):
    lh_exit = 'Links House Exit'
    if lh_exit in exits:
        if not avail.world.shufflelinks[avail.player]:
            links_house = 'Big Bomb Shop' if avail.inverted else 'Links House'
        else:
            forbidden = list((Isolated_LH_Doors_Inv + Inverted_Dark_Sanctuary_Doors)
                             if avail.inverted else Isolated_LH_Doors_Open)
            shuffle_mode = avail.world.shuffle[avail.player]
            # simple shuffle -
            if shuffle_mode == 'simple':
                avail.links_on_mountain = True  # taken care of by the logic below
                if avail.inverted:  # in inverted, links house cannot be on the mountain
                    forbidden.extend(['Spike Cave', 'Dark Death Mountain Fairy', 'Hookshot Fairy'])
                else:
                    # links house cannot be on dm if there's no way off the mountain
                    ent = avail.world.get_entrance('Death Mountain Return Cave (West)', avail.player)
                    if ent.connected_region.name in Simple_DM_Non_Connectors:
                        forbidden.append('Hookshot Fairy')
                    # other cases it is fine
            # can't have links house on eddm in restricted because Inverted Aga Tower isn't available
            # todo: inverted full may have the same problem if both links house and a mandatory connector is chosen
            # from the 3 inverted options
            if shuffle_mode in ['restricted'] and avail.inverted:
                avail.links_on_mountain = True
                forbidden.extend(['Spike Cave', 'Dark Death Mountain Fairy'])
            if shuffle_mode in ['lite', 'lean']:
                forbidden.extend(['Spike Cave', 'Mire Shed'])
            # lobby shuffle means you ought to keep links house in the same world
            sanc_spawn_can_be_dark = (not avail.inverted and avail.world.doorShuffle[avail.player] in ['partitioned', 'crossed']
                                      and avail.world.intensity[avail.player] >= 3)
            entrance_pool = entrances if avail.coupled else avail.decoupled_entrances
            if cross_world and not sanc_spawn_can_be_dark:
                possible = [e for e in entrance_pool if e not in forbidden]
            else:
                world_list = LW_Entrances if not avail.inverted else DW_Entrances
                possible = [e for e in entrance_pool if e in world_list and e not in forbidden]
            possible.sort()
            links_house = random.choice(possible)
        connect_two_way(links_house, lh_exit, avail)
        entrances.remove(links_house)
        connect_exit('Chris Houlihan Room Exit', links_house, avail)  # should match link's house
        exits.remove(lh_exit)
        exits.remove('Chris Houlihan Room Exit')
        if not avail.coupled:
            avail.decoupled_entrances.remove(links_house)
            avail.decoupled_exits.remove('Links House Exit')
            avail.decoupled_exits.remove('Chris Houlihan Room Exit')
        # links on dm
        dm_spots = LH_DM_Connector_List.union(LH_DM_Exit_Forbidden)
        if links_house in dm_spots:
            if avail.links_on_mountain:
                return  # connector is fine
            multi_exit_caves = figure_out_connectors(exits)
            entrance_pool = entrances if avail.coupled else avail.decoupled_entrances
            if cross_world:
                possible_dm_exits = [e for e in entrances if e in LH_DM_Connector_List]
                possible_exits = [e for e in entrance_pool if e not in dm_spots]
            else:
                world_list = LW_Entrances if not avail.inverted else DW_Entrances
                possible_dm_exits = [e for e in entrances if e in LH_DM_Connector_List and e in world_list]
                possible_exits = [e for e in entrance_pool if e not in dm_spots and e in world_list]
            chosen_cave = random.choice(multi_exit_caves)
            shuffle_connector_exits(chosen_cave)
            possible_dm_exits.sort()
            possible_exits.sort()
            chosen_dm_escape = random.choice(possible_dm_exits)
            chosen_landing = random.choice(possible_exits)
            if avail.coupled:
                connect_two_way(chosen_dm_escape, chosen_cave.pop(0), avail)
                connect_two_way(chosen_landing, chosen_cave.pop(), avail)
                entrances.remove(chosen_dm_escape)
                entrances.remove(chosen_landing)
            else:
                connect_entrance(chosen_dm_escape, chosen_cave.pop(0), avail)
                connect_exit(chosen_cave.pop(), chosen_landing, avail)
                entrances.remove(chosen_dm_escape)
                avail.decoupled_entrances.remove(chosen_landing)
            if len(chosen_cave):
                exits.update([x for x in chosen_cave])
            exits.update([x for item in multi_exit_caves for x in item])


def figure_out_connectors(exits):
    multi_exit_caves = []
    for item in Connector_List:
        if all(x in exits for x in item):
            remove_from_list(exits, item)
            multi_exit_caves.append(list(item))
    return multi_exit_caves


def figure_out_true_exits(exits, avail):
    multi_exit_caves = []
    for item in Connector_List:
        if all(x in exits for x in item):
            remove_from_list(exits, item)
            multi_exit_caves.append(list(item))
    for item in avail.default_map.values():
        if item in exits:
            multi_exit_caves.append(item)
            exits.remove(item)
    return multi_exit_caves


# todo: figure out hyrule forced better
def figure_out_must_exits_same_world(entrances, exits, avail):
    lw_entrances, dw_entrances = [], []
    hyrule_forced = None
    check_for_hc = (avail.is_standard() or avail.world.doorShuffle[avail.player] != 'vanilla')

    for x in entrances:
        lw_entrances.append(x) if x in LW_Entrances else dw_entrances.append(x)
    multi_exit_caves = figure_out_connectors(exits)
    if check_for_hc:
        for option in multi_exit_caves:
            if any(x in option for x in ['Hyrule Castle Exit (South)', 'Hyrule Castle Exit (East)',
                                         'Hyrule Castle Exit (West)']):
                hyrule_forced = [option]
    if hyrule_forced:
        remove_from_list(multi_exit_caves, hyrule_forced)

    must_exit_lw, must_exit_dw = must_exits_helper(avail, lw_entrances, dw_entrances)

    return must_exit_lw, must_exit_dw, lw_entrances, dw_entrances, multi_exit_caves, hyrule_forced


def must_exits_helper(avail, lw_entrances, dw_entrances):
    must_exit_lw = (Inverted_LW_Must_Exit if avail.inverted else LW_Must_Exit).copy()
    must_exit_dw = (Inverted_DW_Must_Exit if avail.inverted else DW_Must_Exit).copy()
    if not avail.inverted and not avail.skull_handled:
        must_exit_dw.append(('Skull Woods Second Section Door (West)', 'Skull Woods Final Section'))
    must_exit_lw = must_exit_filter(avail, must_exit_lw, lw_entrances)
    must_exit_dw = must_exit_filter(avail, must_exit_dw, dw_entrances)
    return must_exit_lw, must_exit_dw


def figure_out_must_exits_cross_world(entrances, exits, avail):
    multi_exit_caves = figure_out_connectors(exits)

    must_exit_lw = (Inverted_LW_Must_Exit if avail.inverted else LW_Must_Exit).copy()
    must_exit_dw = (Inverted_DW_Must_Exit if avail.inverted else DW_Must_Exit).copy()
    if not avail.inverted and not avail.skull_handled:
        must_exit_dw.append(('Skull Woods Second Section Door (West)', 'Skull Woods Final Section'))
    must_exit = must_exit_filter(avail, must_exit_lw + must_exit_dw, entrances)

    return must_exit, multi_exit_caves


def do_same_world_connectors(lw_entrances, dw_entrances, caves, avail):
    random.shuffle(lw_entrances)
    random.shuffle(dw_entrances)
    random.shuffle(caves)
    while caves:
        # connect highest exit count caves first, prevent issue where we have 2 or 3 exits across worlds left to fill
        cave_candidate = (None, 0)
        for i, cave in enumerate(caves):
            if isinstance(cave, str):
                cave = (cave,)
            if len(cave) > cave_candidate[1]:
                cave_candidate = (i, len(cave))
        cave = caves.pop(cave_candidate[0])

        target = lw_entrances if random.randint(0, 1) == 0 else dw_entrances
        if isinstance(cave, str):
            cave = (cave,)

        # check if we can still fit the cave into our target group
        if len(target) < len(cave):
            # need to use other set
            target = lw_entrances if target is dw_entrances else dw_entrances

        for ext in cave:
            # todo: for decoupled, need to split the avail decoupled entrances into lw/dw
            # if decoupled:
            #     choice = random.choice(avail.decoupled_entrances)
            #     connect_exit(ext, choice, avail)
            #     avail.decoupled_entrances.remove()
            # else:
            connect_two_way(target.pop(), ext, avail)


def do_cross_world_connectors(entrances, caves, avail):
    random.shuffle(entrances)
    random.shuffle(caves)
    while caves:
        cave_candidate = (None, 0)
        for i, cave in enumerate(caves):
            if isinstance(cave, str):
                cave = (cave,)
            if len(cave) > cave_candidate[1]:
                cave_candidate = (i, len(cave))
        cave = caves.pop(cave_candidate[0])

        if isinstance(cave, str):
            cave = (cave,)

        for ext in cave:
            if not avail.coupled:
                choice = random.choice(avail.decoupled_entrances)
                connect_exit(ext, choice, avail)
                avail.decoupled_entrances.remove(choice)
            else:
                connect_two_way(entrances.pop(), ext, avail)


def do_fixed_shuffle(avail, entrance_list):
    max_size = 0
    options = {}
    for i, entrance_set in enumerate(entrance_list):
        entrances, targets = find_entrances_and_exits(avail, entrance_set)
        size = min(len(entrances), len(targets))
        max_size = max(max_size, size)
        rules = Restrictions()
        rules.size = size
        if ('Hyrule Castle Entrance (South)' in entrances and
           avail.world.doorShuffle[avail.player] != 'vanilla'):
            rules.must_exit_to_lw = True
        if avail.world.is_atgt_swapped(avail.player) and 'Agahnims Tower' in entrances and not avail.world.shuffle_ganon:
            rules.fixed = True
        option = (i, entrances, targets, rules)
        options[i] = option
    choices = dict(options)
    for i, option in options.items():
        key, entrances, targets, rules = option
        if rules.size and rules.size < max_size:
            choice = choices[i]
        elif rules.fixed:
            choice = choices[i]
        elif rules.must_exit_to_lw:
            lw_exits = set(default_lw)
            lw_exits.update({'Big Bomb Shop', 'Ganons Tower Exit'} if avail.inverted else {'Links House Exit', 'Agahnims Tower Exit'})
            filtered_choices = {i: opt for i, opt in choices.items() if all(t in lw_exits for t in opt[2])}
            index, choice = random.choice(list(filtered_choices.items()))
        else:
            index, choice = random.choice(list(choices.items()))
        del choices[choice[0]]
        for t, entrance in enumerate(entrances):
            target = choice[2][t]
            connect_two_way(entrance, target, avail)


def do_same_world_shuffle(avail, pool_def):
    single_exit = pool_def['entrances']
    multi_exit = pool_def['connectors']
    # complete_entrance_set = set()
    lw_entrances, dw_entrances, multi_exits_caves, other_exits = [], [], [], []
    hyrule_forced = None
    check_for_hc = avail.is_standard() or avail.world.doorShuffle[avail.player] != 'vanilla'

    single_entrances, single_exits = find_entrances_and_exits(avail, single_exit)
    other_exits.extend(single_exits)
    for x in single_entrances:
        (dw_entrances, lw_entrances)[x in LW_Entrances].append(x)
    # complete_entrance_set.update(single_entrances)
    for option in multi_exit:
        multi_entrances, multi_exits = find_entrances_and_exits(avail, option)
        # complete_entrance_set.update(multi_entrances)
        if check_for_hc and any(x in multi_entrances for x in ['Hyrule Castle Entrance (South)',
                                                               'Hyrule Castle Entrance (East)',
                                                               'Hyrule Castle Entrance (West)']):
            hyrule_forced = [multi_exits]
        else:
            multi_exits_caves.append(multi_exits)
        for x in multi_entrances:
            (dw_entrances, lw_entrances)[x in LW_Entrances].append(x)

    must_exit_lw = Inverted_LW_Must_Exit if avail.inverted else LW_Must_Exit
    must_exit_dw = Inverted_DW_Must_Exit if avail.inverted else DW_Must_Exit
    must_exit_lw = must_exit_filter(avail, must_exit_lw, lw_entrances)
    must_exit_dw = must_exit_filter(avail, must_exit_dw, dw_entrances)

    if hyrule_forced:
        do_mandatory_connections(avail, lw_entrances, hyrule_forced, must_exit_lw)
    else:
        do_mandatory_connections(avail, lw_entrances, multi_exits_caves, must_exit_lw)
    do_mandatory_connections(avail, dw_entrances, multi_exits_caves, must_exit_dw)

    # connect caves
    random.shuffle(lw_entrances)
    random.shuffle(dw_entrances)
    random.shuffle(multi_exits_caves)
    while multi_exits_caves:
        cave_candidate = (None, 0)
        for i, cave in enumerate(multi_exits_caves):
            if len(cave) > cave_candidate[1]:
                cave_candidate = (i, len(cave))
        cave = multi_exits_caves.pop(cave_candidate[0])

        target = lw_entrances if random.randint(0, 1) == 0 else dw_entrances
        if len(target) < len(cave):  # swap because we ran out of entrances in that world
            target = lw_entrances if target is dw_entrances else dw_entrances

        for ext in cave:
            connect_two_way(target.pop(), ext, avail)
    # finish the rest
    connect_random(lw_entrances+dw_entrances, single_exits, avail, True)


def do_connector_shuffle(avail, pool_def):
    directional_list = pool_def['directional_inv' if avail.inverted else 'directional']
    connector_list = pool_def['connectors_inv' if avail.inverted else 'connectors']
    option_list = pool_def['options']

    for connector in directional_list:
        chosen_option = random.choice(option_list)
        ignored_ent, chosen_exits = find_entrances_and_exits(avail, chosen_option)
        if not chosen_exits:
            continue  # nothing available
        # this shuffle ensures directionality
        shuffle_connector_exits(chosen_exits)
        connector_ent, ignored_exits = find_entrances_and_exits(avail, connector)
        for i, ent in enumerate(connector_ent):
            connect_two_way(ent, chosen_exits[i], avail)
        option_list.remove(chosen_option)

    for connector in connector_list:
        chosen_option = random.choice(option_list)
        ignored_ent, chosen_exits = find_entrances_and_exits(avail, chosen_option)
        # directionality need not be preserved
        random.shuffle(chosen_exits)
        connector_ent, ignored_exits = find_entrances_and_exits(avail, connector)
        for i, ent in enumerate(connector_ent):
            connect_two_way(ent, chosen_exits[i], avail)
        option_list.remove(chosen_option)


def do_limited_shuffle(pool_def, avail):
    entrance_pool, ignored_exits = find_entrances_and_exits(avail, pool_def['entrances'])
    exit_pool = [x for x in pool_def['options'] if x in avail.exits]
    random.shuffle(exit_pool)
    for entrance in entrance_pool:
        chosen_exit = exit_pool.pop()
        connect_two_way(entrance, chosen_exit, avail)


def do_limited_shuffle_exclude_drops(pool_def, avail, lw=True):
    ignored_entrances, exits = find_entrances_and_exits(avail, pool_def['entrances'])
    reserved_drops = set(linked_drop_map.values())
    must_exit_lw, must_exit_dw = must_exits_helper(avail, LW_Entrances, DW_Entrances)
    must_exit = set(must_exit_lw if lw else must_exit_dw)
    base_set = LW_Entrances if lw else DW_Entrances
    entrance_pool = [x for x in base_set if x in avail.entrances and x not in reserved_drops]
    random.shuffle(entrance_pool)
    for next_exit in exits:
        if next_exit not in Connector_Exit_Set:
            reduced_pool = [x for x in entrance_pool if x not in must_exit]
            chosen_entrance = reduced_pool.pop()
            entrance_pool.remove(chosen_entrance)
        else:
            chosen_entrance = entrance_pool.pop()
        connect_two_way(chosen_entrance, next_exit, avail)


def do_vanilla_connect(pool_def, avail):
    if pool_def['condition'] == 'shopsanity':
        if avail.world.shopsanity[avail.player]:
            return
    elif pool_def['condition'] == 'pottery':  # this condition involves whether caves with pots are shuffled or not
        if avail.world.pottery[avail.player] not in ['none', 'keys', 'dungeon']:
            return
    defaults = {**default_connections, **(inverted_default_connections if avail.inverted else open_default_connections)}
    if avail.inverted:
        if 'Dark Death Mountain Fairy' in pool_def['entrances']:
            pool_def['entrances'].remove('Dark Death Mountain Fairy')
            pool_def['entrances'].append('Bumper Cave (top)')
    for entrance in pool_def['entrances']:
        if entrance in avail.entrances:
            target = defaults[entrance]
            if entrance in avail.default_map:
                connect_vanilla_two_way(entrance, avail.default_map[entrance], avail)
            else:
                connect_simple(avail.world, entrance, target, avail.player)
                avail.entrances.remove(entrance)
                avail.exits.remove(target)


def do_mandatory_connections(avail, entrances, cave_options, must_exit):
    if len(must_exit) == 0:
        return
    if not avail.coupled:
        do_mandatory_connections_decoupled(avail, cave_options, must_exit)
        return

    # Keeps track of entrances that cannot be used to access each exit / cave
    if avail.inverted:
        invalid_connections = Inverted_Must_Exit_Invalid_Connections.copy()
    else:
        invalid_connections = Must_Exit_Invalid_Connections.copy()
    invalid_cave_connections = defaultdict(set)

    if avail.world.logic[avail.player] in ['owglitches', 'nologic']:
        import OverworldGlitchRules
        for entrance in OverworldGlitchRules.get_non_mandatory_exits(avail.inverted):
            invalid_connections[entrance] = set()
            if entrance in must_exit:
                must_exit.remove(entrance)
                entrances.append(entrance)
    entrances.sort()  # sort these for consistency
    random.shuffle(entrances)
    random.shuffle(cave_options)

    if avail.inverted:
        at = avail.world.get_region('Agahnims Tower Portal', avail.player)
        for entrance in invalid_connections:
            if avail.world.get_entrance(entrance, avail.player).connected_region == at:
                for ext in invalid_connections[entrance]:
                    invalid_connections[ext] = invalid_connections[ext].union({'Agahnims Tower', 'Hyrule Castle Entrance (West)', 'Hyrule Castle Entrance (East)'})
                break

    used_caves = []
    required_entrances = 0  # Number of entrances reserved for used_caves
    while must_exit:
        exit = must_exit.pop()
        # find multi exit cave
        candidates = []
        for candidate in cave_options:
            if not isinstance(candidate, str) and (candidate in used_caves
                                                   or len(candidate) < len(entrances) - required_entrances):
                candidates.append(candidate)
        cave = random.choice(candidates)
        if cave is None:
            raise RuntimeError('No more caves left. Should not happen!')

        # all caves are sorted so that the last exit is always reachable
        rnd_cave = list(cave)
        shuffle_connector_exits(rnd_cave)  # should be the same as unbiasing some entrances...
        entrances.remove(exit)
        connect_two_way(exit, rnd_cave[-1], avail)
        if len(cave) == 2:
            entrance = next(e for e in entrances[::-1] if e not in invalid_connections[exit]
                            and e not in invalid_cave_connections[tuple(cave)] and e not in must_exit)
            entrances.remove(entrance)
            connect_two_way(entrance, rnd_cave[0], avail)
            if cave in used_caves:
                required_entrances -= 2
                used_caves.remove(cave)
            if entrance in invalid_connections:
                for exit2 in invalid_connections[entrance]:
                    invalid_connections[exit2] = invalid_connections[exit2].union(invalid_connections[exit]).union(invalid_cave_connections[tuple(cave)])
        elif cave[-1] == 'Spectacle Rock Cave Exit':  # Spectacle rock only has one exit
            cave_entrances = []
            for cave_exit in rnd_cave[:-1]:
                entrance = next(e for e in entrances[::-1] if e not in invalid_connections[exit] and e not in must_exit)
                cave_entrances.append(entrance)
                entrances.remove(entrance)
                connect_two_way(entrance, cave_exit, avail)
                if entrance not in invalid_connections:
                    invalid_connections[exit] = set()
            if all(entrance in invalid_connections for entrance in cave_entrances):
                new_invalid_connections = invalid_connections[cave_entrances[0]].intersection(invalid_connections[cave_entrances[1]])
                for exit2 in new_invalid_connections:
                    invalid_connections[exit2] = invalid_connections[exit2].union(invalid_connections[exit])
        else:  # save for later so we can connect to multiple exits
            if cave in used_caves:
                required_entrances -= 1
                used_caves.remove(cave)
            else:
                required_entrances += len(cave)-1
            cave_options.append(rnd_cave[0:-1])
            random.shuffle(cave_options)
            used_caves.append(rnd_cave[0:-1])
            invalid_cave_connections[tuple(rnd_cave[0:-1])] = invalid_cave_connections[tuple(cave)].union(invalid_connections[exit])
        cave_options.remove(cave)
    for cave in used_caves:
        if cave in cave_options:  # check if we placed multiple entrances from this 3 or 4 exit
            for cave_exit in cave:
                entrance = next(e for e in entrances[::-1] if e not in invalid_cave_connections[tuple(cave)])
                invalid_cave_connections[tuple(cave)] = set()
                entrances.remove(entrance)
                connect_two_way(entrance, cave_exit, avail)
            cave_options.remove(cave)


def do_mandatory_connections_decoupled(avail, cave_options, must_exit):
    for next_entrance in must_exit:
        random.shuffle(cave_options)
        candidate = None
        for cave in cave_options:
            if len(cave) < 2 or (len(cave) == 2 and ('Spectacle Rock Cave Exit (Peak)' in cave
                                                     or 'Turtle Rock Ledge Exit (East)' in cave)):
                continue
            candidate = cave
            break
        if candidate is None:
            raise RuntimeError('No suitable cave.')
        cave_options.remove(candidate)

        # all caves are sorted so that the last exit is always reachable
        shuffle_connector_exits(candidate)  # should be the same as un-biasing some entrances...
        chosen_exit = candidate[-1]
        cave = candidate[:-1]
        connect_exit(chosen_exit, next_entrance, avail)
        cave_options.append(cave)
        avail.decoupled_entrances.remove(next_entrance)


def must_exit_filter(avail, candidates, shuffle_pool):
    filtered_list = []
    for cand in candidates:
        if isinstance(cand, tuple):
            candidates = [x for x in cand if x in avail.entrances and x in shuffle_pool]
            if len(candidates) > 1:
                filtered_list.append(random.choice(candidates))
            elif len(candidates) == 1:
                filtered_list.append(candidates[0])
        elif cand in avail.entrances and cand in shuffle_pool:
            filtered_list.append(cand)
    return filtered_list


def shuffle_connector_exits(connector_choices):
    random.shuffle(connector_choices)
    # the order matter however, because we assume the last choice is exit-able from the other ways to get in
    # the first one is the one where you can assume you access the entire cave from
    if 'Paradox Cave Exit (Bottom)' == connector_choices[0]:  # Paradox bottom is exit only
        i = random.randint(1, len(connector_choices) - 1)
        connector_choices[0], connector_choices[i] = connector_choices[i], connector_choices[0]
    # east ledge can't fulfill a must_exit condition
    if 'Turtle Rock Ledge Exit (East)' in connector_choices and 'Turtle Rock Ledge Exit (East)' != connector_choices[0]:
        i = connector_choices.index('Turtle Rock Ledge Exit (East)')
        connector_choices[0], connector_choices[i] = connector_choices[i], connector_choices[0]
    # these only have one exit (one-way nature)
    if 'Spectacle Rock Cave Exit' in connector_choices and connector_choices[-1] != 'Spectacle Rock Cave Exit':
        i = connector_choices.index('Spectacle Rock Cave Exit')
        connector_choices[-1], connector_choices[i] = connector_choices[i], connector_choices[-1]
    if 'Superbunny Cave Exit (Top)' in connector_choices and connector_choices[-1] != 'Superbunny Cave Exit (Top)':
        connector_choices[-1], connector_choices[0] = connector_choices[0], connector_choices[-1]
    if 'Spiral Cave Exit' in connector_choices and connector_choices[-1] != 'Spiral Cave Exit':
        connector_choices[-1], connector_choices[0] = connector_choices[0], connector_choices[-1]


def find_entrances_and_targets_drops(avail_pool, drop_pool):
    holes, targets = [], []
    inverted_substitution(avail_pool, drop_pool, True)
    for item in drop_pool:
        if item in avail_pool.entrances:
            holes.append(item)
        if drop_map[item] in avail_pool.exits:
            targets.append(drop_map[item])
    return holes, targets


def find_entrances_and_exits(avail_pool, entrance_pool):
    entrances, targets = [], []
    inverted_substitution(avail_pool, entrance_pool, True)
    for item in entrance_pool:
        if item in avail_pool.entrances:
            entrances.append(item)
        if item in entrance_map and entrance_map[item] in avail_pool.exits:
            if entrance_map[item] == 'Links House Exit':
                targets.append('Chris Houlihan Room Exit')
            targets.append(entrance_map[item])
        elif item in single_entrance_map and single_entrance_map[item] in avail_pool.exits:
            targets.append(single_entrance_map[item])
    return entrances, targets


inverted_sub_table = {
    #'Ganons Tower':  'Agahnims Tower',
    #'Agahnims Tower': 'Ganons Tower',
    #'Links House': 'Big Bomb Shop',
    #'Big Bomb Shop': 'Links House',
    'Pyramid Hole': 'Inverted Pyramid Hole',
    'Pyramid Entrance': 'Inverted Pyramid Entrance'
}

inverted_exit_sub_table = {
    #'Ganons Tower Exit': 'Ganons Tower Exit',
    #'Agahnims Tower Exit': 'Agahnims Tower Exit'
}


def inverted_substitution(avail_pool, collection, is_entrance, is_set=False):
    if avail_pool.inverted:
        sub_table = inverted_sub_table if is_entrance else inverted_exit_sub_table
        for area, sub in sub_table.items():
            if is_set:
                if area in collection:
                    collection.remove(area)
                    collection.add(sub)
            else:
                try:
                    idx = collection.index(area)
                    collection[idx] = sub
                except ValueError:
                    pass


def connect_random(exitlist, targetlist, avail, two_way=False):
    targetlist = list(targetlist)
    random.shuffle(targetlist)

    for exit, target in zip(exitlist, targetlist):
        if two_way:
            connect_two_way(exit, target, avail)
        else:
            connect_entrance(exit, target, avail)


def connect_custom(avail_pool, world, player):
    if world.customizer and world.customizer.get_entrances():
        custom_entrances = world.customizer.get_entrances()
        player_key = player
        if 'two-way' in custom_entrances[player_key]:
            for ent_name, exit_name in custom_entrances[player_key]['two-way'].items():
                connect_two_way(ent_name, exit_name, avail_pool)
        if 'entrances' in custom_entrances[player_key]:
            for ent_name, exit_name in custom_entrances[player_key]['entrances'].items():
                connect_entrance(ent_name, exit_name, avail_pool)
        if 'exits' in custom_entrances[player_key]:
            for ent_name, exit_name in custom_entrances[player_key]['exits'].items():
                connect_exit(exit_name, ent_name, avail_pool)


def connect_simple(world, exit_name, region_name, player):
    world.get_entrance(exit_name, player).connect(world.get_region(region_name, player))


def connect_vanilla(exit_name, region_name, avail):
    world, player = avail.world, avail.player
    world.get_entrance(exit_name, player).connect(world.get_region(region_name, player))
    avail.entrances.remove(exit_name)
    avail.exits.remove(region_name)


def connect_vanilla_two_way(entrancename, exit_name, avail):
    world, player = avail.world, avail.player

    entrance = world.get_entrance(entrancename, player)
    exit = world.get_entrance(exit_name, player)

    # if these were already connected somewhere, remove the backreference
    if entrance.connected_region is not None:
        entrance.connected_region.entrances.remove(entrance)
    if exit.connected_region is not None:
        exit.connected_region.entrances.remove(exit)

    entrance.connect(exit.parent_region)
    exit.connect(entrance.parent_region)
    avail.entrances.remove(entrancename)
    avail.exits.remove(exit_name)


def connect_entrance(entrancename, exit_name, avail):
    world, player = avail.world, avail. player
    entrance = world.get_entrance(entrancename, player)
    # check if we got an entrance or a region to connect to
    try:
        region = world.get_region(exit_name, player)
        exit = None
    except RuntimeError:
        exit = world.get_entrance(exit_name, player)
        region = exit.parent_region

    # if this was already connected somewhere, remove the backreference
    if entrance.connected_region is not None:
        entrance.connected_region.entrances.remove(entrance)

    target = exit_ids[exit.name][0] if exit is not None else exit_ids.get(region.name, None)
    addresses = door_addresses[entrance.name][0]

    entrance.connect(region, addresses, target)
    avail.entrances.remove(entrancename)
    if avail.coupled:
        avail.exits.remove(exit_name)
    world.spoiler.set_entrance(entrance.name, exit.name if exit is not None else region.name, 'entrance', player)
    logging.getLogger('').debug(f'Connected (entr) {entrance.name} to {exit.name if exit is not None else region.name}')


def connect_exit(exit_name, entrancename, avail):
    world, player = avail.world, avail. player
    entrance = world.get_entrance(entrancename, player)
    exit = world.get_entrance(exit_name, player)

    # if this was already connected somewhere, remove the backreference
    if exit.connected_region is not None:
        exit.connected_region.entrances.remove(exit)

    exit.connect(entrance.parent_region, door_addresses[entrance.name][1], exit_ids[exit.name][1])
    if exit_name != 'Chris Houlihan Room Exit' and avail.coupled:
        avail.entrances.remove(entrancename)
    avail.exits.remove(exit_name)
    world.spoiler.set_entrance(entrance.name, exit.name, 'exit', player)
    logging.getLogger('').debug(f'Connected (exit) {entrance.name} to {exit.name}')


def connect_two_way(entrancename, exit_name, avail):
    world, player = avail.world, avail.player

    entrance = world.get_entrance(entrancename, player)
    exit = world.get_entrance(exit_name, player)

    # if these were already connected somewhere, remove the backreference
    if entrance.connected_region is not None:
        entrance.connected_region.entrances.remove(entrance)
    if exit.connected_region is not None:
        exit.connected_region.entrances.remove(exit)

    entrance.connect(exit.parent_region, door_addresses[entrance.name][0], exit_ids[exit.name][0])
    exit.connect(entrance.parent_region, door_addresses[entrance.name][1], exit_ids[exit.name][1])
    avail.entrances.remove(entrancename)
    avail.exits.remove(exit_name)
    world.spoiler.set_entrance(entrance.name, exit.name, 'both', player)
    logging.getLogger('').debug(f'Connected (2-way) {entrance.name} to {exit.name}')


modes = {
    'dungeonssimple': {
        'undefined': 'vanilla',
        'pools': {
            'skull_drops': {
                'special': 'drops',
                'entrances': ['Skull Woods First Section Hole (East)', 'Skull Woods First Section Hole (West)',
                              'Skull Woods First Section Hole (North)', 'Skull Woods Second Section Hole']
            },
            'skull_doors': {
                'special': 'skull',
                'entrances': ['Skull Woods First Section Door', 'Skull Woods Second Section Door (East)',
                              'Skull Woods Second Section Door (West)']
            },
            'single_entrance_dungeon': {
                'entrances': ['Eastern Palace', 'Tower of Hera', 'Thieves Town', 'Skull Woods Final Section',
                              'Palace of Darkness', 'Ice Palace', 'Misery Mire', 'Swamp Palace', 'Ganons Tower']
            },
            'multi_entrance_dungeon': {
                'special': 'fixed_shuffle',
                'entrances': [['Hyrule Castle Entrance (South)', 'Hyrule Castle Entrance (East)',
                               'Hyrule Castle Entrance (West)', 'Agahnims Tower'],
                              ['Desert Palace Entrance (South)', 'Desert Palace Entrance (East)',
                              'Desert Palace Entrance (West)', 'Desert Palace Entrance (North)'],
                              ['Turtle Rock', 'Turtle Rock Isolated Ledge Entrance',
                               'Dark Death Mountain Ledge (West)', 'Dark Death Mountain Ledge (East)']]
            },
        }
    },
    'dungeonsfull': {
        'undefined': 'vanilla',
        'pools': {
            'skull_drops': {
                'special': 'drops',
                'entrances': ['Skull Woods First Section Hole (East)', 'Skull Woods First Section Hole (West)',
                              'Skull Woods First Section Hole (North)', 'Skull Woods Second Section Hole']
            },
            'skull_doors': {
                'special': 'skull',
                'entrances': ['Skull Woods First Section Door', 'Skull Woods Second Section Door (East)',
                              'Skull Woods Second Section Door (West)']
            },
            'dungeon': {
                'special': 'same_world',
                'sanc_flag': 'light_world',  # always light world flag
                'entrances': ['Eastern Palace', 'Tower of Hera', 'Thieves Town', 'Skull Woods Final Section',
                              'Agahnims Tower', 'Palace of Darkness', 'Ice Palace', 'Misery Mire', 'Swamp Palace',
                              'Ganons Tower'],
                'connectors': [['Hyrule Castle Entrance (South)', 'Hyrule Castle Entrance (East)',
                                'Hyrule Castle Entrance (West)'],
                               ['Desert Palace Entrance (South)', 'Desert Palace Entrance (East)',
                                'Desert Palace Entrance (West)', 'Desert Palace Entrance (North)'],
                               ['Turtle Rock', 'Turtle Rock Isolated Ledge Entrance',
                                'Dark Death Mountain Ledge (West)', 'Dark Death Mountain Ledge (East)']]
            },
        }
    },
    'lite': {
        'undefined': 'shuffle',
        'keep_drops_together': 'on',
        'cross_world': 'off',
        'pools': {
            'skull_drops': {
                'special': 'drops',
                'entrances': ['Skull Woods First Section Hole (East)', 'Skull Woods First Section Hole (West)',
                              'Skull Woods First Section Hole (North)', 'Skull Woods Second Section Hole']
            },
            'skull_doors': {
                'special': 'skull',
                'entrances': ['Skull Woods First Section Door', 'Skull Woods Second Section Door (East)',
                              'Skull Woods Second Section Door (West)']
            },
            'fixed_non_items': {
                'special': 'vanilla',
                'condition': '',
                'entrances': ['Dark Death Mountain Fairy', 'Dark Desert Fairy', 'Archery Game',
                              'Fortune Teller (Dark)', 'Dark Sanctuary Hint', 'Bonk Fairy (Dark)',
                              'Dark Lake Hylia Ledge Hint', 'Dark Lake Hylia Ledge Fairy', 'Dark Lake Hylia Fairy',
                              'Dark Lake Hylia Shop', 'East Dark World Hint', 'Kakariko Gamble Game', 'Good Bee Cave',
                              'Long Fairy Cave', 'Bush Covered House',  'Fortune Teller (Light)', 'Lost Woods Gamble',
                              'Desert Fairy', 'Light Hype Fairy', 'Lake Hylia Fortune Teller', 'Lake Hylia Fairy',
                              'Bonk Fairy (Light)'],
            },
            'fixed_shops': {
                'special': 'vanilla',
                'condition': 'shopsanity',
                'entrances': ['Dark Death Mountain Shop', 'Dark Potion Shop', 'Dark Lumberjack Shop',
                              'Dark World Shop', 'Red Shield Shop', 'Kakariko Shop', 'Capacity Upgrade',
                              'Lake Hylia Shop'],
            },
            'fixed_pottery': {
                'special': 'vanilla',
                'condition': 'pottery',
                'entrances': ['Lumberjack House', 'Snitch Lady (West)', 'Snitch Lady (East)', 'Tavern (Front)',
                              'Light World Bomb Hut', '20 Rupee Cave', '50 Rupee Cave', 'Hookshot Fairy',
                              'Palace of Darkness Hint', 'Dark Lake Hylia Ledge Spike Cave',
                              'Dark Desert Hint']

            },
            'item_caves': {  # shuffles shops/pottery if they weren't fixed in the last steps
                'entrances': ['Mimic Cave', 'Spike Cave', 'Mire Shed', 'Hammer Peg Cave', 'Chest Game',
                              'C-Shaped House', 'Brewery', 'Hype Cave', 'Big Bomb Shop', 'Pyramid Fairy',
                              'Ice Rod Cave', 'Dam', 'Bonk Rock Cave', 'Library', 'Potion Shop', 'Mini Moldorm Cave',
                              'Checkerboard Cave', 'Graveyard Cave', 'Cave 45', 'Sick Kids House', 'Blacksmiths Hut',
                              'Sahasrahlas Hut', 'Aginahs Cave', 'Chicken House', 'Kings Grave', 'Blinds Hideout',
                              'Waterfall of Wishing', 'Dark Death Mountain Shop',
                              'Dark Potion Shop', 'Dark Lumberjack Shop', 'Dark World Shop',
                              'Red Shield Shop', 'Kakariko Shop', 'Capacity Upgrade', 'Lake Hylia Shop',
                              'Lumberjack House', 'Snitch Lady (West)', 'Snitch Lady (East)', 'Tavern (Front)',
                              'Light World Bomb Hut', '20 Rupee Cave', '50 Rupee Cave', 'Hookshot Fairy',
                              'Palace of Darkness Hint', 'Dark Lake Hylia Ledge Spike Cave',
                              'Dark Desert Hint',
                              'Links House', 'Tavern North']
            },
            'old_man_cave': {  # have to do old man cave first so lw dungeon don't use up everything
                'special': 'old_man_cave_east',
                'entrances': ['Old Man Cave Exit (East)'],
            },
            'lw_dungeons': {
                'special': 'limited_lw',
                'entrances': ['Hyrule Castle Entrance (South)', 'Hyrule Castle Entrance (East)',
                              'Hyrule Castle Entrance (West)', 'Agahnims Tower', 'Eastern Palace', 'Tower of Hera',
                              'Desert Palace Entrance (South)', 'Desert Palace Entrance (East)',
                              'Desert Palace Entrance (West)', 'Desert Palace Entrance (North)'],
            },
            'dw_dungeons': {
                'special': 'limited_dw',
                'entrances': ['Ice Palace', 'Misery Mire', 'Ganons Tower', 'Turtle Rock',
                              'Turtle Rock Isolated Ledge Entrance',
                              'Dark Death Mountain Ledge (West)', 'Dark Death Mountain Ledge (East)'],
            },
        }
    },
    'lean': {
        'undefined': 'shuffle',
        'keep_drops_together': 'on',
        'cross_world': 'on',
        'pools': {
            'skull_drops': {
                'special': 'drops',
                'entrances': ['Skull Woods First Section Hole (East)', 'Skull Woods First Section Hole (West)',
                              'Skull Woods First Section Hole (North)', 'Skull Woods Second Section Hole']
            },
            'skull_doors': {
                'special': 'skull',
                'entrances': ['Skull Woods First Section Door', 'Skull Woods Second Section Door (East)',
                              'Skull Woods Second Section Door (West)']
            },
            'fixed_non_items': {
                'special': 'vanilla',
                'condition': '',
                'entrances': ['Dark Death Mountain Fairy', 'Dark Desert Fairy', 'Archery Game',
                              'Fortune Teller (Dark)', 'Dark Sanctuary Hint', 'Bonk Fairy (Dark)',
                              'Dark Lake Hylia Ledge Hint', 'Dark Lake Hylia Ledge Fairy', 'Dark Lake Hylia Fairy',
                              'Dark Lake Hylia Shop', 'East Dark World Hint', 'Kakariko Gamble Game', 'Good Bee Cave',
                              'Long Fairy Cave', 'Bush Covered House',  'Fortune Teller (Light)', 'Lost Woods Gamble',
                              'Desert Fairy', 'Light Hype Fairy', 'Lake Hylia Fortune Teller', 'Lake Hylia Fairy',
                              'Bonk Fairy (Light)'],
            },
            'fixed_shops': {
                'special': 'vanilla',
                'condition': 'shopsanity',
                'entrances': ['Dark Death Mountain Shop', 'Dark Potion Shop', 'Dark Lumberjack Shop',
                              'Dark World Shop', 'Red Shield Shop', 'Kakariko Shop', 'Capacity Upgrade',
                              'Lake Hylia Shop'],
            },
            'fixed_pottery': {
                'special': 'vanilla',
                'condition': 'pottery',
                'entrances': ['Lumberjack House', 'Snitch Lady (West)', 'Snitch Lady (East)', 'Tavern (Front)',
                              'Light World Bomb Hut', '20 Rupee Cave', '50 Rupee Cave', 'Hookshot Fairy',
                              'Palace of Darkness Hint', 'Dark Lake Hylia Ledge Spike Cave',
                              'Dark Desert Hint']

            },
            'item_caves': {  # shuffles shops/pottery if they weren't fixed in the last steps
                'entrances': ['Mimic Cave', 'Spike Cave', 'Mire Shed', 'Hammer Peg Cave', 'Chest Game',
                              'C-Shaped House', 'Brewery', 'Hype Cave', 'Big Bomb Shop', 'Pyramid Fairy',
                              'Ice Rod Cave', 'Dam', 'Bonk Rock Cave', 'Library', 'Potion Shop', 'Mini Moldorm Cave',
                              'Checkerboard Cave', 'Graveyard Cave', 'Cave 45', 'Sick Kids House', 'Blacksmiths Hut',
                              'Sahasrahlas Hut', 'Aginahs Cave', 'Chicken House', 'Kings Grave', 'Blinds Hideout',
                              'Waterfall of Wishing', 'Dark Death Mountain Shop',
                              'Dark Potion Shop', 'Dark Lumberjack Shop', 'Dark World Shop',
                              'Red Shield Shop', 'Kakariko Shop', 'Capacity Upgrade', 'Lake Hylia Shop',
                              'Lumberjack House', 'Snitch Lady (West)', 'Snitch Lady (East)', 'Tavern (Front)',
                              'Light World Bomb Hut', '20 Rupee Cave', '50 Rupee Cave', 'Hookshot Fairy',
                              'Palace of Darkness Hint', 'Dark Lake Hylia Ledge Spike Cave',
                              'Dark Desert Hint',
                              'Links House', 'Tavern North']  # inverted links house gets substituted
            }
        }
    },
    'simple': {
        'undefined': 'shuffle',
        'keep_drops_together': 'on',
        'cross_world': 'off',
        'pools': {
            'skull_drops': {
                'special': 'drops',
                'entrances': ['Skull Woods First Section Hole (East)', 'Skull Woods First Section Hole (West)',
                              'Skull Woods First Section Hole (North)', 'Skull Woods Second Section Hole']
            },
            'skull_doors': {
                'special': 'skull',
                'entrances': ['Skull Woods First Section Door', 'Skull Woods Second Section Door (East)',
                              'Skull Woods Second Section Door (West)']
            },
            'single_entrance_dungeon': {
                'entrances': ['Eastern Palace', 'Tower of Hera', 'Thieves Town', 'Skull Woods Final Section',
                              'Palace of Darkness', 'Ice Palace', 'Misery Mire', 'Swamp Palace', 'Ganons Tower']
            },
            'multi_entrance_dungeon': {
                'special': 'fixed_shuffle',
                'entrances': [['Hyrule Castle Entrance (South)', 'Hyrule Castle Entrance (East)',
                               'Hyrule Castle Entrance (West)', 'Agahnims Tower'],
                              ['Desert Palace Entrance (South)', 'Desert Palace Entrance (East)',
                               'Desert Palace Entrance (West)', 'Desert Palace Entrance (North)'],
                              ['Turtle Rock', 'Turtle Rock Isolated Ledge Entrance',
                               'Dark Death Mountain Ledge (West)', 'Dark Death Mountain Ledge (East)']]
            },
            'two_way_entrances': {
                'special': 'simple_connector',
                'directional': [
                    ['Bumper Cave (Bottom)', 'Bumper Cave (Top)'],
                    ['Hookshot Cave', 'Hookshot Cave Back Entrance'],
                ],
                'connectors': [
                    ['Elder House (East)', 'Elder House (West)'],
                    ['Two Brothers House (East)', 'Two Brothers House (West)'],
                    ['Superbunny Cave (Bottom)', 'Superbunny Cave (Top)']
                ],
                'directional_inv': [
                    ['Old Man Cave (West)', 'Death Mountain Return Cave (West)'],
                    ['Two Brothers House (East)', 'Two Brothers House (West)'],
                ],
                'connectors_inv': [
                    ['Elder House (East)', 'Elder House (West)'],
                    ['Superbunny Cave (Bottom)', 'Superbunny Cave (Top)'],
                    ['Hookshot Cave', 'Hookshot Cave Back Entrance']
                ],
                'options': [
                    ['Bumper Cave (Bottom)', 'Bumper Cave (Top)'],
                    ['Hookshot Cave', 'Hookshot Cave Back Entrance'],
                    ['Elder House (East)', 'Elder House (West)'],
                    ['Two Brothers House (East)', 'Two Brothers House (West)'],
                    ['Superbunny Cave (Bottom)', 'Superbunny Cave (Top)'],
                    ['Death Mountain Return Cave (West)', 'Death Mountain Return Cave (East)'],
                    ['Fairy Ascension Cave (Bottom)', 'Fairy Ascension Cave (Top)'],
                    ['Spiral Cave (Bottom)', 'Spiral Cave']
                ]
            },
            'old_man_cave': {
                'special': 'old_man_cave_east',
                'entrances': ['Old Man Cave Exit (East)'],
            },
            'old_man_cave_inverted': {
                'special': 'inverted_fixed',
                'entrance': 'Bumper Cave (Bottom)',
                'exit': 'Old Man Cave Exit (West)'
            },
            'light_death_mountain': {
                'special': 'limited',
                'entrances': ['Old Man Cave (West)', 'Old Man Cave (East)', 'Old Man House (Bottom)',
                              'Old Man House (Top)', 'Death Mountain Return Cave (East)',
                              'Death Mountain Return Cave (West)', 'Fairy Ascension Cave (Bottom)',
                              'Fairy Ascension Cave (Top)', 'Spiral Cave', 'Spiral Cave (Bottom)',
                              'Spectacle Rock Cave Peak', 'Spectacle Rock Cave (Bottom)', 'Spectacle Rock Cave',
                              'Paradox Cave (Bottom)', 'Paradox Cave (Middle)', 'Paradox Cave (Top)'],
                'options': ['Elder House Exit (East)', 'Elder House Exit (West)', 'Two Brothers House Exit (East)',
                            'Two Brothers House Exit (West)', 'Old Man Cave Exit (West)', 'Old Man House Exit (Bottom)',
                            'Old Man House Exit (Top)', 'Death Mountain Return Cave Exit (East)',
                            'Death Mountain Return Cave Exit (West)', 'Fairy Ascension Cave Exit (Bottom)',
                            'Fairy Ascension Cave Exit (Top)', 'Spiral Cave Exit (Top)', 'Spiral Cave Exit',
                            'Bumper Cave Exit (Bottom)', 'Bumper Cave Exit (Top)', 'Hookshot Cave Front Exit',
                            'Hookshot Cave Back Exit', 'Superbunny Cave Exit (Top)', 'Superbunny Cave Exit (Bottom)',
                            'Spectacle Rock Cave Exit (Peak)', 'Spectacle Rock Cave Exit',
                            'Spectacle Rock Cave Exit (Top)', 'Paradox Cave Exit (Bottom)',
                            'Paradox Cave Exit (Middle)', 'Paradox Cave Exit (Top)']
            }
        }
    },
    'restricted': {
        'undefined': 'shuffle',
        'keep_drops_together': 'on',
        'cross_world': 'off',
        'pools': {
            'skull_drops': {
                'special': 'drops',
                'entrances': ['Skull Woods First Section Hole (East)', 'Skull Woods First Section Hole (West)',
                              'Skull Woods First Section Hole (North)', 'Skull Woods Second Section Hole']
            },
            'skull_doors': {
                'special': 'skull',
                'entrances': ['Skull Woods First Section Door', 'Skull Woods Second Section Door (East)',
                              'Skull Woods Second Section Door (West)']
            },
            'single_entrance_dungeon': {
                'entrances': ['Eastern Palace', 'Tower of Hera', 'Thieves Town', 'Skull Woods Final Section',
                              'Palace of Darkness', 'Ice Palace', 'Misery Mire', 'Swamp Palace', 'Ganons Tower']
            },
            'multi_entrance_dungeon': {
                'special': 'fixed_shuffle',
                'entrances': [['Hyrule Castle Entrance (South)', 'Hyrule Castle Entrance (East)',
                               'Hyrule Castle Entrance (West)', 'Agahnims Tower'],
                              ['Desert Palace Entrance (South)', 'Desert Palace Entrance (East)',
                               'Desert Palace Entrance (West)', 'Desert Palace Entrance (North)'],
                              ['Turtle Rock', 'Turtle Rock Isolated Ledge Entrance',
                               'Dark Death Mountain Ledge (West)', 'Dark Death Mountain Ledge (East)']]
            },
        }
    },
    'full': {
        'undefined': 'shuffle',
        'keep_drops_together': 'on',
        'cross_world': 'off',
        'pools': {
            'skull_drops': {
                'special': 'drops',
                'entrances': ['Skull Woods First Section Hole (East)', 'Skull Woods First Section Hole (West)',
                              'Skull Woods First Section Hole (North)', 'Skull Woods Second Section Hole']
            },
            'skull_doors': {
                'special': 'skull',
                'entrances': ['Skull Woods First Section Door', 'Skull Woods Second Section Door (East)',
                              'Skull Woods Second Section Door (West)']
            },
        }
    },
    'crossed': {
        'undefined': 'shuffle',
        'keep_drops_together': 'on',
        'cross_world': 'on',
        'pools': {
            'skull_drops': {
                'special': 'drops',
                'entrances': ['Skull Woods First Section Hole (East)', 'Skull Woods First Section Hole (West)',
                              'Skull Woods First Section Hole (North)', 'Skull Woods Second Section Hole']
            },
            'skull_doors': {
                'special': 'skull',
                'entrances': ['Skull Woods First Section Door', 'Skull Woods Second Section Door (East)',
                              'Skull Woods Second Section Door (West)']
            },
        }
    },
    'insanity': {
        'undefined': 'shuffle',
        'keep_drops_together': 'off',
        'cross_world': 'on',
        'decoupled': 'on',
        'pools': {}
    }
}

drop_map = {
    'Skull Woods First Section Hole (East)': 'Skull Pinball',
    'Skull Woods First Section Hole (West)': 'Skull Left Drop',
    'Skull Woods First Section Hole (North)': 'Skull Pot Circle',
    'Skull Woods Second Section Hole': 'Skull Back Drop',

    'Hyrule Castle Secret Entrance Drop':  'Hyrule Castle Secret Entrance',
    'Kakariko Well Drop': 'Kakariko Well (top)',
    'Bat Cave Drop': 'Bat Cave (right)',
    'North Fairy Cave Drop': 'North Fairy Cave',
    'Lost Woods Hideout Drop': 'Lost Woods Hideout (top)',
    'Lumberjack Tree Tree': 'Lumberjack Tree (top)',
    'Sanctuary Grave': 'Sewer Drop',
    'Pyramid Hole': 'Pyramid',
    'Inverted Pyramid Hole': 'Pyramid'
}

linked_drop_map = {
    'Hyrule Castle Secret Entrance Drop':  'Hyrule Castle Secret Entrance Stairs',
    'Kakariko Well Drop': 'Kakariko Well Cave',
    'Bat Cave Drop': 'Bat Cave Cave',
    'North Fairy Cave Drop': 'North Fairy Cave',
    'Lost Woods Hideout Drop': 'Lost Woods Hideout Stump',
    'Lumberjack Tree Tree': 'Lumberjack Tree Cave',
    'Sanctuary Grave': 'Sanctuary',
    'Pyramid Hole': 'Pyramid Entrance',
    'Inverted Pyramid Hole': 'Inverted Pyramid Entrance'
}

entrance_map = {
    'Desert Palace Entrance (South)': 'Desert Palace Exit (South)',
    'Desert Palace Entrance (West)': 'Desert Palace Exit (West)',
    'Desert Palace Entrance (North)': 'Desert Palace Exit (North)',
    'Desert Palace Entrance (East)': 'Desert Palace Exit (East)',
    
    'Eastern Palace': 'Eastern Palace Exit',
    'Tower of Hera': 'Tower of Hera Exit',
    
    'Hyrule Castle Entrance (South)': 'Hyrule Castle Exit (South)',
    'Hyrule Castle Entrance (West)': 'Hyrule Castle Exit (West)',
    'Hyrule Castle Entrance (East)': 'Hyrule Castle Exit (East)',
    'Agahnims Tower': 'Agahnims Tower Exit',

    'Thieves Town': 'Thieves Town Exit',
    'Skull Woods First Section Door': 'Skull Woods First Section Exit',
    'Skull Woods Second Section Door (East)': 'Skull Woods Second Section Exit (East)',
    'Skull Woods Second Section Door (West)': 'Skull Woods Second Section Exit (West)',
    'Skull Woods Final Section': 'Skull Woods Final Section Exit',
    'Ice Palace': 'Ice Palace Exit',
    'Misery Mire': 'Misery Mire Exit',
    'Palace of Darkness': 'Palace of Darkness Exit',
    'Swamp Palace': 'Swamp Palace Exit', 
    
    'Turtle Rock': 'Turtle Rock Exit (Front)',
    'Dark Death Mountain Ledge (West)': 'Turtle Rock Ledge Exit (West)',
    'Dark Death Mountain Ledge (East)': 'Turtle Rock Ledge Exit (East)',
    'Turtle Rock Isolated Ledge Entrance': 'Turtle Rock Isolated Ledge Exit',
    'Ganons Tower': 'Ganons Tower Exit',

    'Links House': 'Links House Exit',


    'Hyrule Castle Secret Entrance Stairs':  'Hyrule Castle Secret Entrance Exit',
    'Kakariko Well Cave': 'Kakariko Well Exit',
    'Bat Cave Cave': 'Bat Cave Exit',
    'North Fairy Cave': 'North Fairy Cave Exit',
    'Lost Woods Hideout Stump': 'Lost Woods Hideout Exit',
    'Lumberjack Tree Cave': 'Lumberjack Tree Exit',
    'Sanctuary': 'Sanctuary Exit',
    'Pyramid Entrance': 'Pyramid Exit',
    'Inverted Pyramid Entrance': 'Pyramid Exit',

    'Elder House (East)': 'Elder House Exit (East)',
    'Elder House (West)': 'Elder House Exit (West)',
    'Two Brothers House (East)': 'Two Brothers House Exit (East)',
    'Two Brothers House (West)': 'Two Brothers House Exit (West)',
    'Old Man Cave (West)': 'Old Man Cave Exit (West)',
    'Old Man Cave (East)': 'Old Man Cave Exit (East)',
    'Old Man House (Bottom)': 'Old Man House Exit (Bottom)',
    'Old Man House (Top)': 'Old Man House Exit (Top)',
    'Death Mountain Return Cave (East)': 'Death Mountain Return Cave Exit (East)',
    'Death Mountain Return Cave (West)': 'Death Mountain Return Cave Exit (West)',
    'Fairy Ascension Cave (Bottom)': 'Fairy Ascension Cave Exit (Bottom)',
    'Fairy Ascension Cave (Top)': 'Fairy Ascension Cave Exit (Top)',
    'Spiral Cave': 'Spiral Cave Exit (Top)',
    'Spiral Cave (Bottom)': 'Spiral Cave Exit',
    'Bumper Cave (Bottom)': 'Bumper Cave Exit (Bottom)',
    'Bumper Cave (Top)': 'Bumper Cave Exit (Top)',
    'Hookshot Cave': 'Hookshot Cave Front Exit',
    'Hookshot Cave Back Entrance': 'Hookshot Cave Back Exit',
    'Superbunny Cave (Top)': 'Superbunny Cave Exit (Top)',
    'Superbunny Cave (Bottom)': 'Superbunny Cave Exit (Bottom)',

    'Spectacle Rock Cave Peak': 'Spectacle Rock Cave Exit (Peak)',
    'Spectacle Rock Cave (Bottom)': 'Spectacle Rock Cave Exit',
    'Spectacle Rock Cave': 'Spectacle Rock Cave Exit (Top)',
    'Paradox Cave (Bottom)': 'Paradox Cave Exit (Bottom)',
    'Paradox Cave (Middle)': 'Paradox Cave Exit (Middle)',
    'Paradox Cave (Top)': 'Paradox Cave Exit (Top)',
}


single_entrance_map = {
    'Mimic Cave': 'Mimic Cave', 'Dark Death Mountain Fairy': 'Dark Death Mountain Healer Fairy',
    'Dark Death Mountain Shop': 'Dark Death Mountain Shop', 'Spike Cave': 'Spike Cave',
    'Dark Desert Fairy': 'Dark Desert Healer Fairy', 'Dark Desert Hint': 'Dark Desert Hint', 'Mire Shed': 'Mire Shed',
    'Archery Game': 'Archery Game', 'Dark Potion Shop': 'Dark Potion Shop',
    'Dark Lumberjack Shop': 'Dark Lumberjack Shop', 'Dark World Shop': 'Village of Outcasts Shop',
    'Fortune Teller (Dark)': 'Fortune Teller (Dark)', 'Dark Sanctuary Hint': 'Dark Sanctuary Hint',
    'Red Shield Shop': 'Red Shield Shop', 'Hammer Peg Cave': 'Hammer Peg Cave',
    'Chest Game': 'Chest Game', 'C-Shaped House': 'C-Shaped House', 'Brewery': 'Brewery',
    'Bonk Fairy (Dark)': 'Bonk Fairy (Dark)', 'Hype Cave': 'Hype Cave',
    'Dark Lake Hylia Ledge Hint': 'Dark Lake Hylia Ledge Hint',
    'Dark Lake Hylia Ledge Spike Cave': 'Dark Lake Hylia Ledge Spike Cave',
    'Dark Lake Hylia Ledge Fairy': 'Dark Lake Hylia Ledge Healer Fairy',
    'Dark Lake Hylia Fairy': 'Dark Lake Hylia Healer Fairy',
    'Dark Lake Hylia Shop': 'Dark Lake Hylia Shop', 'Big Bomb Shop': 'Big Bomb Shop',
    'Palace of Darkness Hint': 'Palace of Darkness Hint', 'East Dark World Hint': 'East Dark World Hint',
    'Pyramid Fairy': 'Pyramid Fairy', 'Hookshot Fairy': 'Hookshot Fairy', '50 Rupee Cave': '50 Rupee Cave',
    'Ice Rod Cave': 'Ice Rod Cave', 'Bonk Rock Cave': 'Bonk Rock Cave', 'Library': 'Library',
    'Kakariko Gamble Game': 'Kakariko Gamble Game', 'Potion Shop': 'Potion Shop', '20 Rupee Cave': '20 Rupee Cave',
    'Good Bee Cave': 'Good Bee Cave', 'Long Fairy Cave': 'Long Fairy Cave', 'Mini Moldorm Cave': 'Mini Moldorm Cave',
    'Checkerboard Cave': 'Checkerboard Cave', 'Graveyard Cave': 'Graveyard Cave', 'Cave 45': 'Cave 45',
    'Kakariko Shop': 'Kakariko Shop', 'Light World Bomb Hut': 'Light World Bomb Hut',
    'Tavern (Front)': 'Tavern (Front)', 'Bush Covered House': 'Bush Covered House',
    'Snitch Lady (West)': 'Snitch Lady (West)', 'Snitch Lady (East)': 'Snitch Lady (East)',
    'Fortune Teller (Light)': 'Fortune Teller (Light)', 'Lost Woods Gamble': 'Lost Woods Gamble',
    'Sick Kids House': 'Sick Kids House', 'Blacksmiths Hut': 'Blacksmiths Hut', 'Capacity Upgrade': 'Capacity Upgrade',
    'Lake Hylia Shop': 'Lake Hylia Shop', 'Sahasrahlas Hut': 'Sahasrahlas Hut',
    'Aginahs Cave': 'Aginahs Cave', 'Chicken House': 'Chicken House', 'Tavern North': 'Tavern',
    'Kings Grave': 'Kings Grave', 'Desert Fairy': 'Desert Healer Fairy', 'Light Hype Fairy': 'Light Hype Fairy',
    'Lake Hylia Fortune Teller': 'Lake Hylia Fortune Teller', 'Lake Hylia Fairy': 'Lake Hylia Healer Fairy',
    'Bonk Fairy (Light)': 'Bonk Fairy (Light)', 'Lumberjack House': 'Lumberjack House', 'Dam': 'Dam',
    'Blinds Hideout': 'Blinds Hideout', 'Waterfall of Wishing': 'Waterfall of Wishing'
}

default_dw = {
    'Thieves Town Exit', 'Skull Woods First Section Exit', 'Skull Woods Second Section Exit (East)',
    'Skull Woods Second Section Exit (West)', 'Skull Woods Final Section Exit', 'Ice Palace Exit', 'Misery Mire Exit',
    'Palace of Darkness Exit', 'Swamp Palace Exit', 'Turtle Rock Exit (Front)', 'Turtle Rock Ledge Exit (West)',
    'Turtle Rock Ledge Exit (East)', 'Turtle Rock Isolated Ledge Exit', 'Bumper Cave Exit (Top)',
    'Bumper Cave Exit (Bottom)', 'Superbunny Cave Exit (Top)', 'Superbunny Cave Exit (Bottom)',
    'Hookshot Cave Front Exit', 'Hookshot Cave Back Exit', 'Ganons Tower Exit', 'Pyramid Exit', 'Bonk Fairy (Dark)',
    'Dark Lake Hylia Healer Fairy', 'Dark Lake Hylia Ledge Healer Fairy', 'Dark Desert Healer Fairy',
    'Dark Death Mountain Healer Fairy', 'Dark Death Mountain Shop', 'Pyramid Fairy', 'East Dark World Hint',
    'Palace of Darkness Hint', 'Village of Outcasts Shop', 'Dark Lake Hylia Shop',
    'Dark Lumberjack Shop', 'Dark Potion Shop', 'Dark Lake Hylia Ledge Spike Cave',
    'Dark Lake Hylia Ledge Hint', 'Hype Cave', 'Brewery', 'C-Shaped House', 'Chest Game', 'Hammer Peg Cave',
    'Red Shield Shop', 'Dark Sanctuary Hint', 'Fortune Teller (Dark)', 'Archery Game', 'Mire Shed', 'Dark Desert Hint',
    'Spike Cave', 'Skull Back Drop', 'Skull Left Drop', 'Skull Pinball', 'Skull Pot Circle', 'Pyramid'
}

default_lw = {
    'Desert Palace Exit (South)', 'Desert Palace Exit (West)', 'Desert Palace Exit (East)',
    'Desert Palace Exit (North)', 'Eastern Palace Exit', 'Tower of Hera Exit', 'Hyrule Castle Exit (South)',
    'Hyrule Castle Exit (West)', 'Hyrule Castle Exit (East)',
    'Hyrule Castle Secret Entrance Exit', 'Kakariko Well Exit', 'Bat Cave Exit', 'Elder House Exit (East)',
    'Elder House Exit (West)', 'North Fairy Cave Exit', 'Lost Woods Hideout Exit', 'Lumberjack Tree Exit',
    'Two Brothers House Exit (East)', 'Two Brothers House Exit (West)', 'Sanctuary Exit', 'Old Man Cave Exit (East)',
    'Old Man Cave Exit (West)', 'Old Man House Exit (Bottom)', 'Old Man House Exit (Top)',
    'Death Mountain Return Cave Exit (West)', 'Death Mountain Return Cave Exit (East)', 'Spectacle Rock Cave Exit',
    'Spectacle Rock Cave Exit (Top)', 'Spectacle Rock Cave Exit (Peak)', 'Paradox Cave Exit (Bottom)',
    'Paradox Cave Exit (Middle)', 'Paradox Cave Exit (Top)', 'Fairy Ascension Cave Exit (Bottom)',
    'Fairy Ascension Cave Exit (Top)', 'Spiral Cave Exit', 'Spiral Cave Exit (Top)', 'Waterfall of Wishing', 'Dam',
    'Blinds Hideout', 'Lumberjack House', 'Bonk Fairy (Light)', 'Lake Hylia Healer Fairy',
    'Swamp Healer Fairy', 'Desert Healer Fairy', 'Fortune Teller (Light)', 'Lake Hylia Fortune Teller', 'Kings Grave', 'Tavern',
    'Chicken House', 'Aginahs Cave', 'Sahasrahlas Hut', 'Cave Shop (Lake Hylia)', 'Capacity Upgrade', 'Blacksmiths Hut',
    'Sick Kids House', 'Lost Woods Gamble', 'Snitch Lady (East)', 'Snitch Lady (West)', 'Bush Covered House',
    'Tavern (Front)', 'Light World Bomb Hut', 'Kakariko Shop', 'Cave 45', 'Graveyard Cave', 'Checkerboard Cave',
    'Mini Moldorm Cave', 'Long Fairy Cave', 'Good Bee Cave', '20 Rupee Cave', '50 Rupee Cave', 'Ice Rod Cave',
    'Bonk Rock Cave', 'Library', 'Kakariko Gamble Game', 'Potion Shop', 'Hookshot Fairy', 'Mimic Cave',
    'Kakariko Well (top)', 'Hyrule Castle Secret Entrance', 'Bat Cave (right)', 'North Fairy Cave',
    'Lost Woods Hideout (top)', 'Lumberjack Tree (top)', 'Sewer Drop'
}

LW_Entrances = ['Elder House (East)', 'Elder House (West)', 'Two Brothers House (East)', 'Two Brothers House (West)',
                'Old Man Cave (West)', 'Old Man House (Bottom)', 'Death Mountain Return Cave (West)',
                'Paradox Cave (Bottom)', 'Paradox Cave (Middle)', 'Paradox Cave (Top)',
                'Fairy Ascension Cave (Bottom)', 'Fairy Ascension Cave (Top)', 'Spiral Cave', 'Spiral Cave (Bottom)',
                'Desert Palace Entrance (South)', 'Desert Palace Entrance (West)', 'Desert Palace Entrance (North)',
                'Desert Palace Entrance (East)', 'Eastern Palace', 'Tower of Hera', 'Hyrule Castle Entrance (West)',
                'Hyrule Castle Entrance (East)', 'Hyrule Castle Entrance (South)', 'Agahnims Tower', 'Blinds Hideout',
                'Lake Hylia Fairy', 'Light Hype Fairy', 'Desert Fairy', 'Tavern North', 'Chicken House', 'Aginahs Cave',
                'Sahasrahlas Hut', 'Lake Hylia Shop', 'Blacksmiths Hut', 'Sick Kids House', 'Lost Woods Gamble',
                'Fortune Teller (Light)', 'Snitch Lady (East)', 'Snitch Lady (West)', 'Bush Covered House',
                'Tavern (Front)', 'Light World Bomb Hut', 'Kakariko Shop', 'Mini Moldorm Cave', 'Long Fairy Cave',
                'Good Bee Cave', '20 Rupee Cave', '50 Rupee Cave', 'Ice Rod Cave', 'Library', 'Potion Shop', 'Dam',
                'Lumberjack House', 'Lake Hylia Fortune Teller', 'Kakariko Gamble Game', 'Waterfall of Wishing',
                'Capacity Upgrade', 'Bonk Rock Cave', 'Graveyard Cave', 'Checkerboard Cave', 'Cave 45', 'Kings Grave',
                'Bonk Fairy (Light)', 'Hookshot Fairy', 'Mimic Cave', 'Links House', 'Old Man Cave (East)',
                'Old Man House (Top)', 'Death Mountain Return Cave (East)', 'Spectacle Rock Cave',
                'Spectacle Rock Cave Peak', 'Spectacle Rock Cave (Bottom)', 'Hyrule Castle Secret Entrance Stairs',
                'Kakariko Well Cave', 'Bat Cave Cave', 'North Fairy Cave', 'Lost Woods Hideout Stump',
                'Lumberjack Tree Cave', 'Sanctuary', 'Inverted Pyramid Entrance']

DW_Entrances = ['Bumper Cave (Bottom)', 'Superbunny Cave (Top)',  'Superbunny Cave (Bottom)', 'Hookshot Cave',
                'Thieves Town', 'Skull Woods Final Section', 'Ice Palace', 'Misery Mire', 'Palace of Darkness',
                'Swamp Palace', 'Turtle Rock', 'Dark Death Mountain Ledge (West)', 'Dark Death Mountain Ledge (East)',
                'Turtle Rock Isolated Ledge Entrance', 'Bumper Cave (Top)', 'Hookshot Cave Back Entrance',
                'Bonk Fairy (Dark)', 'Dark Sanctuary Hint', 'Dark Lake Hylia Fairy', 'C-Shaped House', 'Big Bomb Shop',
                'Dark Death Mountain Fairy', 'Dark Lake Hylia Shop', 'Dark World Shop', 'Red Shield Shop', 'Mire Shed',
                'East Dark World Hint', 'Dark Desert Hint', 'Spike Cave', 'Palace of Darkness Hint',
                'Dark Lake Hylia Ledge Spike Cave', 'Dark Death Mountain Shop', 'Dark Potion Shop',
                'Pyramid Fairy', 'Archery Game', 'Dark Lumberjack Shop', 'Hype Cave', 'Brewery',
                'Dark Lake Hylia Ledge Hint', 'Chest Game', 'Dark Desert Fairy', 'Dark Lake Hylia Ledge Fairy',
                'Fortune Teller (Dark)', 'Hammer Peg Cave', 'Pyramid Entrance',
                'Skull Woods First Section Door', 'Skull Woods Second Section Door (East)',
                'Skull Woods Second Section Door (West)', 'Ganons Tower']

LW_Must_Exit = ['Desert Palace Entrance (East)']

DW_Must_Exit = [('Dark Death Mountain Ledge (East)', 'Dark Death Mountain Ledge (West)'),
                'Turtle Rock Isolated Ledge Entrance', 'Bumper Cave (Top)', 'Hookshot Cave Back Entrance',
                'Pyramid Entrance']

Inverted_LW_Must_Exit = [('Desert Palace Entrance (North)', 'Desert Palace Entrance (West)'),
                         'Desert Palace Entrance (East)', 'Death Mountain Return Cave (West)',
                         'Two Brothers House (West)',
                         ('Hyrule Castle Entrance (West)', 'Hyrule Castle Entrance (East)', 'Agahnims Tower')]

Inverted_DW_Must_Exit = []

Isolated_LH_Doors_Open = ['Mimic Cave', 'Kings Grave', 'Waterfall of Wishing', 'Desert Palace Entrance (South)',
                          'Desert Palace Entrance (North)', 'Capacity Upgrade', 'Ice Palace',
                          'Skull Woods Final Section', 'Skull Woods Second Section Door (West)',
                          'Hammer Peg Cave', 'Turtle Rock Isolated Ledge Entrance',
                          'Dark Death Mountain Ledge (West)', 'Dark Death Mountain Ledge (East)',
                          'Dark World Shop', 'Dark Potion Shop']

Isolated_LH_Doors_Inv = ['Kings Grave', 'Waterfall of Wishing', 'Desert Palace Entrance (South)',
                         'Desert Palace Entrance (North)', 'Capacity Upgrade', 'Ice Palace',
                         'Skull Woods Final Section', 'Skull Woods Second Section Door (West)',
                         'Hammer Peg Cave', 'Turtle Rock Isolated Ledge Entrance',
                         'Dark Death Mountain Ledge (West)', 'Dark Death Mountain Ledge (East)',
                         'Dark World Shop', 'Dark Potion Shop']

# inverted doesn't like really like - Paradox Top or Tower of Hera
LH_DM_Connector_List = {
    'Old Man Cave (East)', 'Old Man House (Bottom)', 'Old Man House (Top)', 'Death Mountain Return Cave (East)',
    'Fairy Ascension Cave (Bottom)', 'Fairy Ascension Cave (Top)', 'Spiral Cave', 'Spiral Cave (Bottom)',
    'Tower of Hera', 'Spectacle Rock Cave Peak', 'Spectacle Rock Cave (Bottom)', 'Spectacle Rock Cave',
    'Paradox Cave (Bottom)', 'Paradox Cave (Middle)', 'Paradox Cave (Top)', 'Hookshot Fairy', 'Spike Cave',
    'Dark Death Mountain Fairy', 'Ganons Tower', 'Superbunny Cave (Top)',  'Superbunny Cave (Bottom)',
    'Hookshot Cave', 'Dark Death Mountain Shop', 'Turtle Rock'}

LH_DM_Exit_Forbidden = {
    'Turtle Rock Isolated Ledge Entrance', 'Mimic Cave', 'Hookshot Cave Back Entrance',
    'Dark Death Mountain Ledge (West)', 'Dark Death Mountain Ledge (East)', 'Desert Palace Entrance (South)',
    'Ice Palace', 'Waterfall of Wishing', 'Kings Grave', 'Hammer Peg Cave', 'Capacity Upgrade',
    'Skull Woods Final Section', 'Skull Woods Second Section Door (West)'
}  # omissions from Isolated Starts: 'Desert Palace Entrance (North)', 'Dark World Shop', 'Dark Potion Shop'

# in inverted we put dark sanctuary in west dark world for now
Inverted_Dark_Sanctuary_Doors = [
    'Dark Sanctuary Hint', 'Fortune Teller (Dark)', 'Brewery', 'C-Shaped House', 'Chest Game',
    'Dark Lumberjack Shop', 'Red Shield Shop', 'Bumper Cave (Bottom)', 'Bumper Cave (Top)', 'Thieves Town'
]

Connector_List = [['Elder House Exit (East)', 'Elder House Exit (West)'],
                  ['Two Brothers House Exit (East)', 'Two Brothers House Exit (West)'],
                  ['Death Mountain Return Cave Exit (West)', 'Death Mountain Return Cave Exit (East)'],
                  ['Fairy Ascension Cave Exit (Bottom)', 'Fairy Ascension Cave Exit (Top)'],
                  ['Bumper Cave Exit (Top)', 'Bumper Cave Exit (Bottom)'],
                  ['Hookshot Cave Back Exit', 'Hookshot Cave Front Exit'],
                  ['Superbunny Cave Exit (Bottom)', 'Superbunny Cave Exit (Top)'],
                  ['Spiral Cave Exit (Top)', 'Spiral Cave Exit'],
                  ['Old Man House Exit (Bottom)', 'Old Man House Exit (Top)'],
                  ['Spectacle Rock Cave Exit (Peak)', 'Spectacle Rock Cave Exit (Top)',
                   'Spectacle Rock Cave Exit'],
                  ['Paradox Cave Exit (Top)', 'Paradox Cave Exit (Middle)', 'Paradox Cave Exit (Bottom)'],
                  ['Hyrule Castle Exit (South)', 'Hyrule Castle Exit (West)',
                   'Hyrule Castle Exit (East)'],
                  ['Desert Palace Exit (South)', 'Desert Palace Exit (East)',
                   'Desert Palace Exit (West)'],
                  ['Turtle Rock Exit (Front)', 'Turtle Rock Isolated Ledge Exit',
                   'Turtle Rock Ledge Exit (West)', 'Turtle Rock Ledge Exit (East)']]

Connector_Exit_Set = {
    'Elder House Exit (East)', 'Elder House Exit (West)', 'Two Brothers House Exit (East)',
    'Two Brothers House Exit (West)', 'Death Mountain Return Cave Exit (West)',
    'Death Mountain Return Cave Exit (East)', 'Fairy Ascension Cave Exit (Bottom)', 'Fairy Ascension Cave Exit (Top)',
    'Bumper Cave Exit (Top)', 'Bumper Cave Exit (Bottom)', 'Hookshot Cave Back Exit', 'Hookshot Cave Front Exit',
    'Superbunny Cave Exit (Top)', 'Spiral Cave Exit', 'Old Man House Exit (Bottom)', 'Old Man House Exit (Top)',
    'Spectacle Rock Cave Exit', 'Paradox Cave Exit (Bottom)',
    'Hyrule Castle Exit (South)', 'Hyrule Castle Exit (West)', 'Hyrule Castle Exit (East)',
    'Desert Palace Exit (South)', 'Desert Palace Exit (East)', 'Desert Palace Exit (West)', 'Turtle Rock Exit (Front)',
    'Turtle Rock Isolated Ledge Exit', 'Turtle Rock Ledge Exit (West)'
}

# Entrances that cannot be used to access a must_exit entrance - symmetrical to allow reverse lookups
Must_Exit_Invalid_Connections = defaultdict(set, {
    'Dark Death Mountain Ledge (East)': {'Dark Death Mountain Ledge (West)', 'Mimic Cave'},
    'Dark Death Mountain Ledge (West)': {'Dark Death Mountain Ledge (East)', 'Mimic Cave'},
    'Mimic Cave': {'Dark Death Mountain Ledge (West)', 'Dark Death Mountain Ledge (East)'},
    'Bumper Cave (Top)': {'Death Mountain Return Cave (West)'},
    'Death Mountain Return Cave (West)': {'Bumper Cave (Top)'},
    'Skull Woods Second Section Door (West)': {'Skull Woods Final Section'},
    'Skull Woods Final Section': {'Skull Woods Second Section Door (West)'},
})
Inverted_Must_Exit_Invalid_Connections = defaultdict(set, {
    'Bumper Cave (Top)': {'Death Mountain Return Cave (West)'},
    'Death Mountain Return Cave (West)': {'Bumper Cave (Top)'},
    'Desert Palace Entrance (North)': {'Desert Palace Entrance (West)'},
    'Desert Palace Entrance (West)': {'Desert Palace Entrance (North)'},
    'Agahnims Tower': {'Hyrule Castle Entrance (West)', 'Hyrule Castle Entrance (East)'},
    'Hyrule Castle Entrance (West)': {'Hyrule Castle Entrance (East)', 'Agahnims Tower'},
    'Hyrule Castle Entrance (East)': {'Hyrule Castle Entrance (West)', 'Agahnims Tower'},
})

Old_Man_Entrances = ['Old Man Cave (East)',
                     'Old Man House (Top)',
                     'Death Mountain Return Cave (East)',
                     'Spectacle Rock Cave',
                     'Spectacle Rock Cave Peak',
                     'Spectacle Rock Cave (Bottom)',
                     'Tower of Hera']

Inverted_Old_Man_Entrances = ['Dark Death Mountain Fairy', 'Spike Cave', 'Ganons Tower']

Simple_DM_Non_Connectors = {'Old Man Cave Ledge', 'Spiral Cave (Top)', 'Superbunny Cave (Bottom)',
                            'Spectacle Rock Cave (Peak)', 'Spectacle Rock Cave (Top)'}

Blacksmith_Options = [
    'Blinds Hideout', 'Lake Hylia Fairy', 'Light Hype Fairy', 'Desert Fairy', 'Tavern North', 'Chicken House',
    'Aginahs Cave', 'Sahasrahlas Hut', 'Lake Hylia Shop', 'Blacksmiths Hut', 'Sick Kids House', 'Lost Woods Gamble',
    'Fortune Teller (Light)', 'Snitch Lady (East)', 'Snitch Lady (West)', 'Bush Covered House', 'Tavern (Front)',
    'Light World Bomb Hut', 'Kakariko Shop', 'Mini Moldorm Cave', 'Long Fairy Cave', 'Good Bee Cave', '20 Rupee Cave',
    '50 Rupee Cave', 'Ice Rod Cave', 'Library', 'Potion Shop', 'Dam', 'Lumberjack House', 'Lake Hylia Fortune Teller',
    'Kakariko Gamble Game', 'Eastern Palace', 'Elder House (East)', 'Elder House (West)', 'Two Brothers House (East)',
    'Old Man Cave (West)', 'Sanctuary', 'Lumberjack Tree Cave', 'Lost Woods Hideout Stump', 'North Fairy Cave',
    'Bat Cave Cave', 'Kakariko Well Cave', 'Links House']

Bomb_Shop_Options = [
    'Waterfall of Wishing', 'Capacity Upgrade', 'Bonk Rock Cave', 'Graveyard Cave', 'Checkerboard Cave', 'Cave 45',
    'Kings Grave', 'Bonk Fairy (Light)', 'Hookshot Fairy', 'East Dark World Hint', 'Palace of Darkness Hint',
    'Dark Lake Hylia Fairy', 'Dark Lake Hylia Ledge Fairy', 'Dark Lake Hylia Ledge Spike Cave',
    'Dark Lake Hylia Ledge Hint', 'Hype Cave', 'Bonk Fairy (Dark)', 'Brewery', 'C-Shaped House', 'Chest Game',
    'Hammer Peg Cave', 'Red Shield Shop', 'Dark Sanctuary Hint', 'Fortune Teller (Dark)', 'Dark World Shop',
    'Dark Lumberjack Shop', 'Dark Potion Shop', 'Archery Game', 'Mire Shed', 'Dark Desert Hint',
    'Dark Desert Fairy', 'Spike Cave', 'Dark Death Mountain Shop', 'Dark Death Mountain Fairy', 'Mimic Cave',
    'Big Bomb Shop', 'Dark Lake Hylia Shop', 'Bumper Cave (Top)', 'Links House',
    'Hyrule Castle Entrance (South)', 'Misery Mire', 'Thieves Town', 'Bumper Cave (Bottom)', 'Swamp Palace',
    'Hyrule Castle Secret Entrance Stairs', 'Skull Woods First Section Door', 'Skull Woods Second Section Door (East)',
    'Skull Woods Second Section Door (West)', 'Skull Woods Final Section', 'Ice Palace', 'Turtle Rock',
    'Dark Death Mountain Ledge (West)', 'Dark Death Mountain Ledge (East)', 'Superbunny Cave (Top)',
    'Superbunny Cave (Bottom)', 'Hookshot Cave', 'Ganons Tower', 'Desert Palace Entrance (South)', 'Tower of Hera',
    'Old Man Cave (East)', 'Old Man House (Bottom)', 'Old Man House (Top)',
    'Death Mountain Return Cave (East)', 'Death Mountain Return Cave (West)', 'Spectacle Rock Cave Peak',
    'Paradox Cave (Bottom)', 'Paradox Cave (Middle)', 'Paradox Cave (Top)', 'Fairy Ascension Cave (Bottom)',
    'Fairy Ascension Cave (Top)', 'Spiral Cave', 'Spiral Cave (Bottom)', 'Palace of Darkness',
    'Hyrule Castle Entrance (West)', 'Hyrule Castle Entrance (East)', 'Agahnims Tower',
    'Desert Palace Entrance (West)', 'Desert Palace Entrance (North)',
    'Spectacle Rock Cave', 'Spectacle Rock Cave (Bottom)', 'Two Brothers House (West)'] + Blacksmith_Options

Inverted_Bomb_Shop_Options = [
    'Waterfall of Wishing', 'Capacity Upgrade', 'Bonk Rock Cave', 'Graveyard Cave', 'Checkerboard Cave', 'Cave 45',
    'Kings Grave', 'Bonk Fairy (Light)', 'Hookshot Fairy', 'East Dark World Hint', 'Palace of Darkness Hint',
    'Dark Lake Hylia Fairy', 'Dark Lake Hylia Ledge Fairy', 'Dark Lake Hylia Ledge Spike Cave',
    'Dark Lake Hylia Ledge Hint', 'Hype Cave', 'Bonk Fairy (Dark)', 'Brewery', 'C-Shaped House', 'Chest Game',
    'Hammer Peg Cave', 'Red Shield Shop', 'Fortune Teller (Dark)', 'Dark World Shop',
    'Dark Lumberjack Shop', 'Dark Potion Shop', 'Archery Game', 'Mire Shed', 'Dark Desert Hint',
    'Dark Desert Fairy', 'Spike Cave', 'Dark Death Mountain Shop', 'Dark Death Mountain Fairy', 'Mimic Cave',
    'Dark Lake Hylia Shop', 'Bumper Cave (Top)',
    'Hyrule Castle Entrance (South)', 'Misery Mire', 'Thieves Town', 'Bumper Cave (Bottom)', 'Swamp Palace',
    'Hyrule Castle Secret Entrance Stairs', 'Skull Woods First Section Door', 'Skull Woods Second Section Door (East)',
    'Skull Woods Second Section Door (West)', 'Skull Woods Final Section', 'Ice Palace', 'Turtle Rock',
    'Dark Death Mountain Ledge (West)', 'Dark Death Mountain Ledge (East)', 'Superbunny Cave (Top)',
    'Superbunny Cave (Bottom)', 'Hookshot Cave', 'Desert Palace Entrance (South)', 'Tower of Hera',
    'Old Man Cave (East)', 'Old Man House (Bottom)', 'Old Man House (Top)',
    'Death Mountain Return Cave (East)', 'Death Mountain Return Cave (West)', 'Spectacle Rock Cave Peak',
    'Paradox Cave (Bottom)', 'Paradox Cave (Middle)', 'Paradox Cave (Top)', 'Fairy Ascension Cave (Bottom)',
    'Fairy Ascension Cave (Top)', 'Spiral Cave', 'Spiral Cave (Bottom)', 'Palace of Darkness',
    'Hyrule Castle Entrance (West)', 'Hyrule Castle Entrance (East)',
    'Desert Palace Entrance (West)', 'Desert Palace Entrance (North)',
    'Agahnims Tower', 'Ganons Tower', 'Dark Sanctuary Hint', 'Big Bomb Shop', 'Links House'] + Blacksmith_Options


# these are connections that cannot be shuffled and always exist.
# They link together separate parts of the world we need to divide into regions
mandatory_connections = [('Links House S&Q', 'Links House'),

                         # underworld
                         ('Lost Woods Hideout (top to bottom)', 'Lost Woods Hideout (bottom)'),
                         ('Lumberjack Tree (top to bottom)', 'Lumberjack Tree (bottom)'),
                         ('Death Mountain Return Cave E', 'Death Mountain Return Cave (right)'),
                         ('Death Mountain Return Cave W', 'Death Mountain Return Cave (left)'),
                         ('Old Man Cave Dropdown', 'Old Man Cave'),
                         ('Spectacle Rock Cave Drop', 'Spectacle Rock Cave (Bottom)'),
                         ('Spectacle Rock Cave Peak Drop', 'Spectacle Rock Cave (Bottom)'),
                         ('Old Man House Front to Back', 'Old Man House Back'),
                         ('Old Man House Back to Front', 'Old Man House'),
                         ('Spiral Cave (top to bottom)', 'Spiral Cave (Bottom)'),
                         ('Paradox Cave Push Block Reverse', 'Paradox Cave Chest Area'),
                         ('Paradox Cave Push Block', 'Paradox Cave Front'),
                         ('Paradox Cave Chest Area NE', 'Paradox Cave Bomb Area'),
                         ('Paradox Cave Bomb Jump', 'Paradox Cave'),
                         ('Paradox Cave Drop', 'Paradox Cave Chest Area'),
                         ('Paradox Shop', 'Paradox Shop'),
                         ('Fairy Ascension Cave Climb', 'Fairy Ascension Cave (Top)'),
                         ('Fairy Ascension Cave Pots', 'Fairy Ascension Cave (Bottom)'),
                         ('Fairy Ascension Cave Drop', 'Fairy Ascension Cave (Drop)'),
                         ('Sewer Drop', 'Sewers Rat Path'),
                         ('Kakariko Well (top to bottom)', 'Kakariko Well (bottom)'),
                         ('Kakariko Well (top to back)', 'Kakariko Well (back)'),
                         ('Blinds Hideout N', 'Blinds Hideout (Top)'),
                         ('Bat Cave Door', 'Bat Cave (left)'),

                         ('Hookshot Cave Front to Middle', 'Hookshot Cave (Middle)'),
                         ('Hookshot Cave Middle to Front', 'Hookshot Cave (Front)'),
                         ('Hookshot Cave Middle to Back', 'Hookshot Cave (Back)'),
                         ('Hookshot Cave Back to Middle', 'Hookshot Cave (Middle)'),
                         ('Hookshot Cave Bonk Path', 'Hookshot Cave (Bonk Islands)'),
                         ('Hookshot Cave Hook Path', 'Hookshot Cave (Hook Islands)'),
                         ('Superbunny Cave Climb', 'Superbunny Cave (Top)'),
                         ('Bumper Cave Bottom to Top', 'Bumper Cave (top)'),
                         ('Bumper Cave Top To Bottom', 'Bumper Cave (bottom)'),
                         ('Ganon Drop', 'Bottom of Pyramid'),

                         # water entry
                         ('Waterfall Fairy Access', 'Zora Waterfall Entryway'),
                         ('Zora Waterfall Water Drop', 'Lake Hylia Water'),
                         ('Light World Water Drop', 'Lake Hylia Water'),
                         ('Potion Shop Water Drop', 'Lake Hylia Water'),
                         ('Northeast Light World Water Drop', 'Lake Hylia Water'),
                         ('Lake Hylia Central Island Water Drop', 'Lake Hylia Water'),

                         ('West Dark World Water Drop', 'Dark Lake Hylia Water'),
                         ('Northeast Dark World Water Drop', 'Dark Lake Hylia Water'),
                         ('Catfish Water Drop', 'Dark Lake Hylia Water'),
                         ('East Dark World Water Drop', 'Dark Lake Hylia Water'),
                         ('South Dark World Water Drop', 'Dark Lake Hylia Water'),
                         ('Southeast Dark World Water Drop', 'Dark Lake Hylia Water'),
                         ('Ice Palace Leave Water Drop', 'Dark Lake Hylia Water'),

                         # water exit
                         ('Light World Pier', 'Light World'), # there are several piers in-game, only one needs to be modeled
                         ('Potion Shop Pier', 'Potion Shop Area'),
                         ('Hobo Pier', 'Hobo Bridge'),
                         ('Lake Hylia Central Island Pier', 'Lake Hylia Central Island'),
                         ('Lake Hylia Whirlpool', 'Northeast Light World'),

                         ('Northeast Dark World Pier', 'Northeast Dark World'),
                         ('East Dark World Pier', 'East Dark World'),
                         ('Southeast Dark World Pier', 'Southeast Dark World'),

                         # terrain
                         ('Master Sword Meadow', 'Master Sword Meadow'),
                         ('DM Hammer Bridge (West)', 'East Death Mountain (Top)'),
                         ('DM Hammer Bridge (East)', 'West Death Mountain (Top)'),
                         ('DM Broken Bridge (West)', 'East Death Mountain (Bottom)'),
                         ('DM Broken Bridge (East)', 'West Death Mountain (Bottom)'),
                         ('Fairy Ascension Rocks', 'Fairy Ascension Plateau'),
                         ('Death Mountain Entrance Rock', 'Death Mountain Entrance'),
                         ('Zoras Domain', 'Zoras Domain'),
                         ('Kings Grave Rocks (Outer)', 'Kings Grave Area'),
                         ('Kings Grave Rocks (Inner)', 'Light World'),
                         ('Potion Shop Rock (South)', 'Northeast Light World'),
                         ('Potion Shop Rock (North)', 'Potion Shop Area'),
                         ('Kakariko Southwest Bush (North)', 'Bomb Hut Area'),
                         ('Kakariko Southwest Bush (South)', 'Light World'),
                         ('Kakariko Yard Bush (North)', 'Light World'),
                         ('Kakariko Yard Bush (South)', 'Bush Covered Lawn'),
                         ('Hyrule Castle Courtyard Bush (North)', 'Hyrule Castle Courtyard'),
                         ('Hyrule Castle Courtyard Bush (South)', 'Hyrule Castle Secret Entrance Area'),
                         ('Hyrule Castle Main Gate', 'Hyrule Castle Courtyard'),
                         ('Hyrule Castle Main Gate (North)', 'Light World'),
                         ('Wooden Bridge Bush (North)', 'Light World'),
                         ('Wooden Bridge Bush (South)', 'Potion Shop Area'),
                         ('Bat Cave Ledge Peg', 'Bat Cave Ledge'),
                         ('Bat Cave Ledge Peg (East)', 'Light World'),
                         ('Desert Statue Move', 'Desert Palace Stairs'),
                         ('Desert Ledge Rocks (Outer)', 'Desert Palace Entrance (North) Spot'),
                         ('Desert Ledge Rocks (Inner)', 'Desert Ledge'),

                         ('Skull Woods Forest', 'Skull Woods Forest'),
                         ('East Dark Death Mountain Bushes', 'East Dark Death Mountain (Bushes)'),
                         ('Bumper Cave Entrance Rock', 'Bumper Cave Entrance'),
                         ('Dark Witch Rock (North)', 'Northeast Dark World'),
                         ('Dark Witch Rock (South)', 'Catfish Area'),
                         ('Grassy Lawn Pegs (Top)', 'West Dark World'),
                         ('Grassy Lawn Pegs (Bottom)', 'Dark Grassy Lawn'),
                         ('West Dark World Gap', 'West Dark World'),
                         ('Dark Graveyard Bush (South)', 'Dark Graveyard North'),
                         ('Dark Graveyard Bush (North)', 'West Dark World'),
                         ('Broken Bridge Pass (Top)', 'East Dark World'),
                         ('Broken Bridge Pass (Bottom)', 'Northeast Dark World'),
                         ('Peg Area Rocks (Left)', 'Hammer Peg Area'),
                         ('Peg Area Rocks (Right)', 'West Dark World'),
                         ('Village of Outcasts Heavy Rock', 'West Dark World'),
                         ('Hammer Bridge Pegs (North)', 'South Dark World'),
                         ('Hammer Bridge Pegs (South)', 'East Dark World'),
                         ('Ice Island To East Pier', 'East Dark World'),

                         # ledge drops
                         ('Spectacle Rock Drop', 'West Death Mountain (Top)'),
                         ('Death Mountain Drop', 'West Death Mountain (Bottom)'),
                         ('Spiral Cave Ledge Access', 'Spiral Cave Ledge'),
                         ('Fairy Ascension Ledge Access', 'Fairy Ascension Ledge'),
                         ('East Death Mountain Drop', 'East Death Mountain (Bottom)'),
                         ('Spiral Cave Ledge Drop', 'East Death Mountain (Bottom)'),
                         ('Fairy Ascension Ledge Drop', 'Fairy Ascension Plateau'),
                         ('Fairy Ascension Drop', 'East Death Mountain (Bottom)'),
                         ('Death Mountain Entrance Drop', 'Light World'),
                         ('Death Mountain Return Ledge Drop', 'Light World'),
                         ('Graveyard Ledge Drop', 'Light World'),
                         ('Hyrule Castle Ledge Courtyard Drop', 'Hyrule Castle Courtyard'),
                         ('Hyrule Castle Ledge Drop', 'Light World'),
                         ('Maze Race Ledge Drop', 'Light World'),
                         ('Desert Ledge Drop', 'Light World'),
                         ('Desert Palace Mouth Drop', 'Light World'),
                         ('Checkerboard Ledge Drop', 'Light World'),
                         ('Desert Teleporter Drop', 'Light World'),
                         ('Cave 45 Ledge Drop', 'Light World'),

                         ('Dark Death Mountain Drop (West)', 'West Dark Death Mountain (Bottom)'),
                         ('Dark Death Mountain Drop (East)', 'East Dark Death Mountain (Bottom)'),
                         ('Floating Island Drop', 'Dark Death Mountain (Top)'),
                         ('Turtle Rock Drop', 'Dark Death Mountain (Top)'),
                         ('Bumper Cave Entrance Drop', 'West Dark World'),
                         ('Bumper Cave Ledge Drop', 'West Dark World'),
                         ('Pyramid Drop', 'East Dark World'),
                         ('Village of Outcasts Drop', 'South Dark World'),
                         ('Dark Desert Drop', 'Dark Desert')
                        ]

open_mandatory_connections = [('Sanctuary S&Q', 'Sanctuary'),
                              ('Old Man S&Q', 'Old Man House'),
                              ('Other World S&Q', 'East Dark World'),

                              # flute
                              ('Flute Spot 1', 'West Death Mountain (Bottom)'),
                              ('Flute Spot 2', 'Potion Shop Area'),
                              ('Flute Spot 3', 'Light World'),
                              ('Flute Spot 4', 'Light World'),
                              ('Flute Spot 5', 'Light World'),
                              ('Flute Spot 6', 'Desert Teleporter Ledge'),
                              ('Flute Spot 7', 'Light World'),
                              ('Flute Spot 8', 'Light World'),
                              ('LW Flute', 'Flute Sky'),
                              ('NWLW Flute', 'Flute Sky'),
                              ('ZLW Flute', 'Flute Sky'),
                              ('DM Flute', 'Flute Sky'),
                              ('EDM Flute', 'Flute Sky'),

                              # portals
                              ('Death Mountain Teleporter', 'West Dark Death Mountain (Bottom)'),
                              ('East Death Mountain Teleporter', 'East Dark Death Mountain (Bottom)'),
                              ('Turtle Rock Teleporter', 'Turtle Rock (Top)'),
                              ('Kakariko Teleporter', 'West Dark World'),
                              ('Castle Gate Teleporter', 'East Dark World'),
                              ('East Hyrule Teleporter', 'East Dark World'),
                              ('South Hyrule Teleporter', 'South Dark World'),
                              ('Desert Teleporter', 'Dark Desert'),
                              ('Lake Hylia Teleporter', 'Dark Lake Hylia Central Island')
                             ]

inverted_mandatory_connections = [('Sanctuary S&Q', 'Dark Sanctuary Hint'),
                                  ('Old Man S&Q', 'West Dark Death Mountain (Bottom)'),
                                  ('Other World S&Q', 'Hyrule Castle Ledge'),

                                  # flute
                                  ('Flute Spot 1', 'West Dark Death Mountain (Bottom)'),
                                  ('Flute Spot 2', 'Northeast Dark World'),
                                  ('Flute Spot 3', 'West Dark World'),
                                  ('Flute Spot 4', 'South Dark World'),
                                  ('Flute Spot 5', 'East Dark World'),
                                  ('Flute Spot 6', 'Dark Desert Ledge'),
                                  ('Flute Spot 7', 'South Dark World'),
                                  ('Flute Spot 8', 'Southeast Dark World'),
                                  ('DDM Flute', 'Flute Sky'),
                                  ('NEDW Flute', 'Flute Sky'),
                                  ('WDW Flute', 'Flute Sky'),
                                  ('SDW Flute', 'Flute Sky'),
                                  ('EDW Flute', 'Flute Sky'),
                                  ('DD Flute', 'Flute Sky'),
                                  ('DLHL Flute', 'Flute Sky'),
                                  ('EDDM Flute', 'Flute Sky'),
                                  ('Dark Grassy Lawn Flute', 'Flute Sky'),
                                  ('Hammer Peg Area Flute', 'Flute Sky'),

                                  # modified terrain
                                  ('Spectacle Rock Approach', 'Spectacle Rock'),
                                  ('Spectacle Rock Leave', 'West Death Mountain (Top)'),
                                  ('Floating Island Bridge (West)', 'East Death Mountain (Top)'),
                                  ('Floating Island Bridge (East)', 'Death Mountain Floating Island'),
                                  ('Graveyard Ladder (Top)', 'Light World'),
                                  ('Graveyard Ladder (Bottom)', 'Graveyard Ledge'),
                                  ('Mimic Cave Ledge Access', 'Mimic Cave Ledge'),
                                  ('Mimic Cave Ledge Drop', 'East Death Mountain (Bottom)'),
                                  ('Checkerboard Ledge Approach', 'Desert Checkerboard Ledge'),
                                  ('Checkerboard Ledge Leave', 'Light World'),
                                  ('Cave 45 Approach', 'Cave 45 Ledge'),
                                  ('Cave 45 Leave', 'Light World'),
                                  ('Lake Hylia Island Pier', 'Lake Hylia Island'),
                                  ('Bombos Tablet Ladder (Top)', 'Light World'),
                                  ('Bombos Tablet Ladder (Bottom)', 'Bombos Tablet Ledge'),
                                  ('Dark Death Mountain Ladder (Top)', 'West Dark Death Mountain (Bottom)'),
                                  ('Dark Death Mountain Ladder (Bottom)', 'Dark Death Mountain (Top)'),
                                  ('Turtle Rock Tail Drop', 'Turtle Rock (Top)'),
                                  ('Ice Palace Approach', 'Dark Lake Hylia Central Island'),

                                  # portals
                                  ('Dark Death Mountain Teleporter (West)', 'West Death Mountain (Bottom)'),
                                  ('East Dark Death Mountain Teleporter (Bottom)', 'East Death Mountain (Bottom)'),
                                  ('East Dark Death Mountain Teleporter (Top)', 'East Death Mountain (Top)'),
                                  ('West Dark World Teleporter', 'Light World'),
                                  ('Post Aga Teleporter', 'Light World'),
                                  ('East Dark World Teleporter', 'Light World'),
                                  ('South Dark World Teleporter', 'Light World'),
                                  ('Dark Desert Teleporter', 'Light World'),
                                  ('Dark Lake Hylia Teleporter', 'Lake Hylia Central Island')
                                 ]

# non-shuffled entrance links
default_connections = {'Lost Woods Gamble': 'Lost Woods Gamble',
                       'Lost Woods Hideout Drop': 'Lost Woods Hideout (top)',
                       'Lost Woods Hideout Stump': 'Lost Woods Hideout (bottom)',
                       'Lost Woods Hideout Exit': 'Light World',
                       'Lumberjack House': 'Lumberjack House',
                       'Lumberjack Tree Tree': 'Lumberjack Tree (top)',
                       'Lumberjack Tree Cave': 'Lumberjack Tree (bottom)',
                       'Lumberjack Tree Exit': 'Light World',
                       'Death Mountain Return Cave (East)': 'Death Mountain Return Cave (right)',
                       'Death Mountain Return Cave Exit (East)': 'West Death Mountain (Bottom)',
                       'Spectacle Rock Cave Peak': 'Spectacle Rock Cave (Peak)',
                       'Spectacle Rock Cave (Bottom)': 'Spectacle Rock Cave (Bottom)',
                       'Spectacle Rock Cave': 'Spectacle Rock Cave (Top)',
                       'Spectacle Rock Cave Exit': 'West Death Mountain (Bottom)',
                       'Spectacle Rock Cave Exit (Top)': 'West Death Mountain (Bottom)',
                       'Spectacle Rock Cave Exit (Peak)': 'West Death Mountain (Bottom)',
                       'Old Man House (Bottom)': 'Old Man House',
                       'Old Man House Exit (Bottom)': 'West Death Mountain (Bottom)',
                       'Old Man House (Top)': 'Old Man House Back',
                       'Old Man House Exit (Top)': 'West Death Mountain (Bottom)',
                       'Spiral Cave': 'Spiral Cave (Top)',
                       'Spiral Cave (Bottom)': 'Spiral Cave (Bottom)',
                       'Spiral Cave Exit': 'East Death Mountain (Bottom)',
                       'Spiral Cave Exit (Top)': 'Spiral Cave Ledge',
                       'Mimic Cave': 'Mimic Cave',
                       'Fairy Ascension Cave (Bottom)': 'Fairy Ascension Cave (Bottom)',
                       'Fairy Ascension Cave (Top)': 'Fairy Ascension Cave (Top)',
                       'Fairy Ascension Cave Exit (Bottom)': 'Fairy Ascension Plateau',
                       'Fairy Ascension Cave Exit (Top)': 'Fairy Ascension Ledge',
                       'Hookshot Fairy': 'Hookshot Fairy',
                       'Paradox Cave (Bottom)': 'Paradox Cave Front',
                       'Paradox Cave (Middle)': 'Paradox Cave',
                       'Paradox Cave (Top)': 'Paradox Cave',
                       'Paradox Cave Exit (Bottom)': 'East Death Mountain (Bottom)',
                       'Paradox Cave Exit (Middle)': 'East Death Mountain (Bottom)',
                       'Paradox Cave Exit (Top)': 'East Death Mountain (Top)',
                       'Waterfall of Wishing': 'Waterfall of Wishing',
                       'Fortune Teller (Light)': 'Fortune Teller (Light)',
                       'Bonk Rock Cave': 'Bonk Rock Cave',
                       'Sanctuary': 'Sanctuary Portal',
                       'Sanctuary Exit': 'Light World',
                       'Sanctuary Grave': 'Sewer Drop',
                       'Graveyard Cave': 'Graveyard Cave',
                       'Kings Grave': 'Kings Grave',
                       'North Fairy Cave Drop': 'North Fairy Cave',
                       'North Fairy Cave': 'North Fairy Cave',
                       'North Fairy Cave Exit': 'Light World',
                       'Potion Shop': 'Potion Shop',
                       'Kakariko Well Drop': 'Kakariko Well (top)',
                       'Kakariko Well Cave': 'Kakariko Well (bottom)',
                       'Kakariko Well Exit': 'Light World',
                       'Blinds Hideout': 'Blinds Hideout',
                       'Elder House (West)': 'Elder House',
                       'Elder House (East)': 'Elder House',
                       'Elder House Exit (West)': 'Light World',
                       'Elder House Exit (East)': 'Light World',
                       'Snitch Lady (West)': 'Snitch Lady (West)',
                       'Snitch Lady (East)': 'Snitch Lady (East)',
                       'Bush Covered House': 'Bush Covered House',
                       'Chicken House': 'Chicken House',
                       'Sick Kids House': 'Sick Kids House',
                       'Light World Bomb Hut': 'Light World Bomb Hut',
                       'Kakariko Shop': 'Kakariko Shop',
                       'Tavern North': 'Tavern',
                       'Tavern (Front)': 'Tavern (Front)',
                       'Hyrule Castle Secret Entrance Drop': 'Hyrule Castle Secret Entrance',
                       'Hyrule Castle Secret Entrance Stairs': 'Hyrule Castle Secret Entrance',
                       'Hyrule Castle Secret Entrance Exit': 'Hyrule Castle Secret Entrance Area',
                       'Sahasrahlas Hut': 'Sahasrahlas Hut',
                       'Blacksmiths Hut': 'Blacksmiths Hut',
                       'Bat Cave Drop': 'Bat Cave (right)',
                       'Bat Cave Cave': 'Bat Cave (left)',
                       'Bat Cave Exit': 'Light World',
                       'Two Brothers House (West)': 'Two Brothers House',
                       'Two Brothers House Exit (West)': 'Maze Race Ledge',
                       'Two Brothers House (East)': 'Two Brothers House',
                       'Two Brothers House Exit (East)': 'Light World',
                       'Library': 'Library',
                       'Kakariko Gamble Game': 'Kakariko Gamble Game',
                       'Bonk Fairy (Light)': 'Bonk Fairy (Light)',
                       'Lake Hylia Fairy': 'Lake Hylia Healer Fairy',
                       'Long Fairy Cave': 'Long Fairy Cave',
                       'Checkerboard Cave': 'Checkerboard Cave',
                       'Aginahs Cave': 'Aginahs Cave',
                       'Cave 45': 'Cave 45',
                       'Light Hype Fairy': 'Light Hype Fairy',
                       'Lake Hylia Fortune Teller': 'Lake Hylia Fortune Teller',
                       'Lake Hylia Shop': 'Lake Hylia Shop',
                       'Capacity Upgrade': 'Capacity Upgrade',
                       'Mini Moldorm Cave': 'Mini Moldorm Cave',
                       'Ice Rod Cave': 'Ice Rod Cave',
                       'Good Bee Cave': 'Good Bee Cave',
                       '20 Rupee Cave': '20 Rupee Cave',
                       'Desert Fairy': 'Desert Healer Fairy',
                       '50 Rupee Cave': '50 Rupee Cave',
                       'Dam': 'Dam',

                       'Dark Lumberjack Shop': 'Dark Lumberjack Shop',
                       'Spike Cave': 'Spike Cave',
                       'Hookshot Cave Back Exit': 'Dark Death Mountain Floating Island',
                       'Hookshot Cave Back Entrance': 'Hookshot Cave (Back)',
                       'Hookshot Cave': 'Hookshot Cave (Front)',
                       'Hookshot Cave Front Exit': 'Dark Death Mountain (Top)',
                       'Superbunny Cave (Top)': 'Superbunny Cave (Top)',
                       'Superbunny Cave Exit (Top)': 'Dark Death Mountain (Top)',
                       'Superbunny Cave (Bottom)': 'Superbunny Cave (Bottom)',
                       'Superbunny Cave Exit (Bottom)': 'East Dark Death Mountain (Bottom)',
                       'Dark Death Mountain Shop': 'Dark Death Mountain Shop',
                       'Fortune Teller (Dark)': 'Fortune Teller (Dark)',
                       'Dark Sanctuary Hint': 'Dark Sanctuary Hint',
                       'Dark Potion Shop': 'Dark Potion Shop',
                       'Chest Game': 'Chest Game',
                       'C-Shaped House': 'C-Shaped House',
                       'Brewery': 'Brewery',
                       'Dark World Shop': 'Village of Outcasts Shop',
                       'Hammer Peg Cave': 'Hammer Peg Cave',
                       'Red Shield Shop': 'Red Shield Shop',
                       'Pyramid Fairy': 'Pyramid Fairy',
                       'Palace of Darkness Hint': 'Palace of Darkness Hint',
                       'Archery Game': 'Archery Game',
                       'Bonk Fairy (Dark)': 'Bonk Fairy (Dark)',
                       'Dark Lake Hylia Fairy': 'Dark Lake Hylia Healer Fairy',
                       'East Dark World Hint': 'East Dark World Hint',
                       'Mire Shed': 'Mire Shed',
                       'Dark Desert Fairy': 'Dark Desert Healer Fairy',
                       'Dark Desert Hint': 'Dark Desert Hint',
                       'Hype Cave': 'Hype Cave',
                       'Dark Lake Hylia Shop': 'Dark Lake Hylia Shop',
                       'Dark Lake Hylia Ledge Fairy': 'Dark Lake Hylia Ledge Healer Fairy',
                       'Dark Lake Hylia Ledge Hint': 'Dark Lake Hylia Ledge Hint',
                       'Dark Lake Hylia Ledge Spike Cave': 'Dark Lake Hylia Ledge Spike Cave'
                      }

open_default_connections = {'Links House': 'Links House',
                            'Links House Exit': 'Light World',
                            'Big Bomb Shop': 'Big Bomb Shop',
                            'Old Man Cave (West)': 'Old Man Cave Ledge',
                            'Old Man Cave (East)': 'Old Man Cave',
                            'Old Man Cave Exit (West)': 'Light World',
                            'Old Man Cave Exit (East)': 'West Death Mountain (Bottom)',
                            'Death Mountain Return Cave (West)': 'Death Mountain Return Cave (left)',
                            'Death Mountain Return Cave Exit (West)': 'Death Mountain Return Ledge',
                            'Bumper Cave (Bottom)': 'Bumper Cave (bottom)',
                            'Bumper Cave (Top)': 'Bumper Cave (top)',
                            'Bumper Cave Exit (Top)': 'Bumper Cave Ledge',
                            'Bumper Cave Exit (Bottom)': 'West Dark World',
                            'Dark Death Mountain Fairy': 'Dark Death Mountain Healer Fairy',
                            'Pyramid Hole': 'Pyramid',
                            'Pyramid Entrance': 'Bottom of Pyramid',
                            'Pyramid Exit': 'Pyramid Exit Ledge'
                           }

inverted_default_connections = {'Links House': 'Big Bomb Shop',
                                'Links House Exit': 'South Dark World',
                                'Big Bomb Shop': 'Links House',
                                'Dark Sanctuary Hint Exit': 'West Dark World',
                                'Old Man Cave (West)': 'Bumper Cave (bottom)',
                                'Old Man Cave (East)': 'Death Mountain Return Cave (left)',
                                'Old Man Cave Exit (West)': 'West Dark World',
                                'Old Man Cave Exit (East)': 'West Dark Death Mountain (Bottom)',
                                'Death Mountain Return Cave (West)': 'Bumper Cave (top)',
                                'Death Mountain Return Cave Exit (West)': 'West Death Mountain (Bottom)',
                                'Bumper Cave (Bottom)': 'Old Man Cave Ledge',
                                'Bumper Cave (Top)': 'Dark Death Mountain Healer Fairy',
                                'Bumper Cave Exit (Top)': 'Death Mountain Return Ledge',
                                'Bumper Cave Exit (Bottom)': 'Light World',
                                'Dark Death Mountain Fairy': 'Old Man Cave',
                                'Inverted Pyramid Hole': 'Pyramid',
                                'Inverted Pyramid Entrance': 'Bottom of Pyramid',
                                'Pyramid Exit': 'Hyrule Castle Courtyard'
                               }

# non shuffled dungeons
default_dungeon_connections = [('Hyrule Castle Entrance (South)', 'Hyrule Castle South Portal'),
                               ('Hyrule Castle Entrance (West)', 'Hyrule Castle West Portal'),
                               ('Hyrule Castle Entrance (East)', 'Hyrule Castle East Portal'),
                               ('Hyrule Castle Exit (South)', 'Hyrule Castle Courtyard'),
                               ('Hyrule Castle Exit (West)', 'Hyrule Castle Ledge'),
                               ('Hyrule Castle Exit (East)', 'Hyrule Castle Ledge'),
                               ('Desert Palace Entrance (South)', 'Desert South Portal'),
                               ('Desert Palace Entrance (West)', 'Desert West Portal'),
                               ('Desert Palace Entrance (North)', 'Desert Back Portal'),
                               ('Desert Palace Entrance (East)', 'Desert East Portal'),
                               ('Desert Palace Exit (South)', 'Desert Palace Stairs'),
                               ('Desert Palace Exit (West)', 'Desert Ledge'),
                               ('Desert Palace Exit (East)', 'Desert Palace Mouth'),
                               ('Desert Palace Exit (North)', 'Desert Palace Entrance (North) Spot'),
                               ('Eastern Palace', 'Eastern Portal'),
                               ('Eastern Palace Exit', 'Light World'),
                               ('Tower of Hera', 'Hera Portal'),
                               ('Tower of Hera Exit', 'West Death Mountain (Top)'),

                               ('Palace of Darkness', 'Palace of Darkness Portal'),
                               ('Palace of Darkness Exit', 'East Dark World'),
                               ('Swamp Palace', 'Swamp Portal'),  # requires additional patch for flooding moat if moved
                               ('Swamp Palace Exit', 'South Dark World'),
                               ('Skull Woods First Section Hole (East)', 'Skull Pinball'),
                               ('Skull Woods First Section Hole (West)', 'Skull Left Drop'),
                               ('Skull Woods First Section Hole (North)', 'Skull Pot Circle'),
                               ('Skull Woods First Section Door', 'Skull 1 Portal'),
                               ('Skull Woods First Section Exit', 'Skull Woods Forest'),
                               ('Skull Woods Second Section Hole', 'Skull Back Drop'),
                               ('Skull Woods Second Section Door (East)', 'Skull 2 East Portal'),
                               ('Skull Woods Second Section Door (West)', 'Skull 2 West Portal'),
                               ('Skull Woods Second Section Exit (East)', 'Skull Woods Forest'),
                               ('Skull Woods Second Section Exit (West)', 'Skull Woods Forest (West)'),
                               ('Skull Woods Final Section', 'Skull 3 Portal'),
                               ('Skull Woods Final Section Exit', 'Skull Woods Forest (West)'),
                               ('Thieves Town', 'Thieves Town Portal'),
                               ('Thieves Town Exit', 'West Dark World'),
                               ('Ice Palace', 'Ice Portal'),
                               ('Ice Palace Exit', 'Dark Lake Hylia Central Island'),
                               ('Misery Mire', 'Mire Portal'),
                               ('Misery Mire Exit', 'Dark Desert'),
                               ('Turtle Rock', 'Turtle Rock Main Portal'),
                               ('Turtle Rock Exit (Front)', 'Dark Death Mountain (Top)'),
                               ('Dark Death Mountain Ledge (West)', 'Turtle Rock Lazy Eyes Portal'),
                               ('Dark Death Mountain Ledge (East)', 'Turtle Rock Chest Portal'),
                               ('Turtle Rock Ledge Exit (West)', 'Dark Death Mountain Ledge'),
                               ('Turtle Rock Ledge Exit (East)', 'Dark Death Mountain Ledge'),
                               ('Turtle Rock Isolated Ledge Entrance', 'Turtle Rock Eye Bridge Portal'),
                               ('Turtle Rock Isolated Ledge Exit', 'Dark Death Mountain Isolated Ledge')
                              ]

open_default_dungeon_connections = [('Agahnims Tower', 'Agahnims Tower Portal'),
                                    ('Agahnims Tower Exit', 'Hyrule Castle Ledge'),
                                    ('Ganons Tower', 'Ganons Tower Portal'),
                                    ('Ganons Tower Exit', 'Dark Death Mountain (Top)')
                                   ]

inverted_default_dungeon_connections = [('Agahnims Tower', 'Ganons Tower Portal'),
                                        ('Agahnims Tower Exit', 'Dark Death Mountain (Top)'),
                                        ('Ganons Tower', 'Agahnims Tower Portal'),
                                        ('Ganons Tower Exit', 'Hyrule Castle Ledge')
                                       ]

indirect_connections = {
    'Turtle Rock (Top)': 'Turtle Rock',
    'East Dark World': 'Pyramid Fairy',
    'Big Bomb Shop': 'Pyramid Fairy',
    'Dark Desert': 'Pyramid Fairy',
    'West Dark World': 'Pyramid Fairy',
    'South Dark World': 'Pyramid Fairy',
    'Light World': 'Pyramid Fairy',
    'Old Man Cave': 'Old Man S&Q'
}
# format:
# Key=Name
# addr = (door_index, exitdata) # multiexit
#       | ([addr], None)  # holes
# exitdata = (room_id, ow_area, vram_loc, scroll_y, scroll_x, link_y, link_x, camera_y, camera_x, unknown_1, unknown_2, door_1, door_2)

# ToDo somehow merge this with creation of the locations
door_addresses = {'Links House': (0x00, (0x0104, 0x2c, 0x0506, 0x0a9a, 0x0832, 0x0ae8, 0x08b8, 0x0b07, 0x08bf, 0x06, 0xfe, 0x0816, 0x0000)),
                  'Desert Palace Entrance (South)': (0x08, (0x0084, 0x30, 0x0314, 0x0c56, 0x00a6, 0x0ca8, 0x0128, 0x0cc3, 0x0133, 0x0a, 0xfa, 0x0000, 0x0000)),
                  'Desert Palace Entrance (West)': (0x0A, (0x0083, 0x30, 0x0280, 0x0c46, 0x0003, 0x0c98, 0x0088, 0x0cb3, 0x0090, 0x0a, 0xfd, 0x0000, 0x0000)),
                  'Desert Palace Entrance (North)': (0x0B, (0x0063, 0x30, 0x0016, 0x0c00, 0x00a2, 0x0c28, 0x0128, 0x0c6d, 0x012f, 0x00, 0x0e, 0x0000, 0x0000)),
                  'Desert Palace Entrance (East)': (0x09, (0x0085, 0x30, 0x02a8, 0x0c4a, 0x0142, 0x0c98, 0x01c8, 0x0cb7, 0x01cf, 0x06, 0xfe, 0x0000, 0x0000)),
                  'Eastern Palace': (0x07, (0x00c9, 0x1e, 0x005a, 0x0600, 0x0ed6, 0x0618, 0x0f50, 0x066d, 0x0f5b, 0x00, 0xfa, 0x0000, 0x0000)),
                  'Tower of Hera': (0x32, (0x0077, 0x03, 0x0050, 0x0014, 0x087c, 0x0068, 0x08f0, 0x0083, 0x08fb, 0x0a, 0xf4, 0x0000, 0x0000)),
                  'Hyrule Castle Entrance (South)': (0x03, (0x0061, 0x1b, 0x0530, 0x0692, 0x0784, 0x06cc, 0x07f8, 0x06ff, 0x0803, 0x0e, 0xfa, 0x0000, 0x87be)),
                  'Hyrule Castle Entrance (West)': (0x02, (0x0060, 0x1b, 0x0016, 0x0600, 0x06ae, 0x0604, 0x0728, 0x066d, 0x0733, 0x00, 0x02, 0x0000, 0x8124)),
                  'Hyrule Castle Entrance (East)': (0x04, (0x0062, 0x1b, 0x004a, 0x0600, 0x0856, 0x0604, 0x08c8, 0x066d, 0x08d3, 0x00, 0xfa, 0x0000, 0x8158)),
                  'Inverted Pyramid Entrance': (0x35, (0x0010, 0x1b, 0x0418, 0x0679, 0x06b4, 0x06c6, 0x0728, 0x06e6, 0x0733, 0x07, 0xf9, 0x0000, 0x0000)),
                  'Agahnims Tower': (0x23, (0x00e0, 0x1b, 0x0032, 0x0600, 0x0784, 0x0634, 0x07f8, 0x066d, 0x0803, 0x00, 0x0a, 0x0000, 0x82be)),
                  'Thieves Town': (0x33, (0x00db, 0x58, 0x0b2e, 0x075a, 0x0176, 0x07a8, 0x01f8, 0x07c7, 0x0203, 0x06, 0xfa, 0x0000, 0x0000)),
                  'Skull Woods First Section Door': (0x29, (0x0058, 0x40, 0x0f4c, 0x01f6, 0x0262, 0x0248, 0x02e8, 0x0263, 0x02ef, 0x0a, 0xfe, 0x0000, 0x0000)),
                  'Skull Woods Second Section Door (East)': (0x28, (0x0057, 0x40, 0x0eb8, 0x01e6, 0x01c2, 0x0238, 0x0248, 0x0253, 0x024f, 0x0a, 0xfe, 0x0000, 0x0000)),
                  'Skull Woods Second Section Door (West)': (0x27, (0x0056, 0x40, 0x0c8e, 0x01a6, 0x0062, 0x01f8, 0x00e8, 0x0213, 0x00ef, 0x0a, 0x0e, 0x0000, 0x0000)),
                  'Skull Woods Final Section': (0x2A, (0x0059, 0x40, 0x0282, 0x0066, 0x0016, 0x00b8, 0x0098, 0x00d3, 0x00a3, 0x0a, 0xfa, 0x0000, 0x0000)),
                  'Ice Palace': (0x2C, (0x000e, 0x75, 0x0bc6, 0x0d6a, 0x0c3e, 0x0db8, 0x0cb8, 0x0dd7, 0x0cc3, 0x06, 0xf2, 0x0000, 0x0000)),
                  'Misery Mire': (0x26, (0x0098, 0x70, 0x0414, 0x0c79, 0x00a6, 0x0cc7, 0x0128, 0x0ce6, 0x0133, 0x07, 0xfa, 0x0000, 0x0000)),
                  'Palace of Darkness': (0x25, (0x004a, 0x5e, 0x005a, 0x0600, 0x0ed6, 0x0628, 0x0f50, 0x066d, 0x0f5b, 0x00, 0xfa, 0x0000, 0x0000)),
                  'Swamp Palace': (0x24, (0x0028, 0x7b, 0x049e, 0x0e8c, 0x06f2, 0x0ed8, 0x0778, 0x0ef9, 0x077f, 0x04, 0xfe, 0x0000, 0x0000)),
                  'Turtle Rock': (0x34, (0x00d6, 0x47, 0x0712, 0x00da, 0x0e96, 0x0128, 0x0f08, 0x0147, 0x0f13, 0x06, 0xfa, 0x0000, 0x0000)),
                  'Dark Death Mountain Ledge (West)': (0x14, (0x0023, 0x45, 0x07ca, 0x0103, 0x0c46, 0x0157, 0x0cb8, 0x0172, 0x0cc3, 0x0b, 0x0a, 0x0000, 0x0000)),
                  'Dark Death Mountain Ledge (East)': (0x18, (0x0024, 0x45, 0x07e0, 0x0103, 0x0d00, 0x0157, 0x0d78, 0x0172, 0x0d7d, 0x0b, 0x00, 0x0000, 0x0000)),
                  'Turtle Rock Isolated Ledge Entrance': (0x17, (0x00d5, 0x45, 0x0ad4, 0x0164, 0x0ca6, 0x01b8, 0x0d18, 0x01d3, 0x0d23, 0x0a, 0xfa, 0x0000, 0x0000)),
                  'Hyrule Castle Secret Entrance Stairs': (0x31, (0x0055, 0x1b, 0x044a, 0x067a, 0x0854, 0x06c8, 0x08c8, 0x06e7, 0x08d3, 0x06, 0xfa, 0x0000, 0x0000)),
                  'Kakariko Well Cave': (0x38, (0x002f, 0x18, 0x0386, 0x0665, 0x0032, 0x06b7, 0x00b8, 0x06d2, 0x00bf, 0x0b, 0xfe, 0x0000, 0x0000)),
                  'Bat Cave Cave': (0x10, (0x00e3, 0x22, 0x0412, 0x087a, 0x048e, 0x08c8, 0x0508, 0x08e7, 0x0513, 0x06, 0x02, 0x0000, 0x0000)),
                  'Elder House (East)': (0x0D, (0x00f3, 0x18, 0x02c4, 0x064a, 0x0222, 0x0698, 0x02a8, 0x06b7, 0x02af, 0x06, 0xfe, 0x05d4, 0x0000)),
                  'Elder House (West)': (0x0C, (0x00f2, 0x18, 0x02bc, 0x064c, 0x01e2, 0x0698, 0x0268, 0x06b9, 0x026f, 0x04, 0xfe, 0x05cc, 0x0000)),
                  'North Fairy Cave': (0x37, (0x0008, 0x15, 0x0088, 0x0400, 0x0a36, 0x0448, 0x0aa8, 0x046f, 0x0ab3, 0x00, 0x0a, 0x0000, 0x0000)),
                  'Lost Woods Hideout Stump': (0x2B, (0x00e1, 0x00, 0x0f4e, 0x01f6, 0x0262, 0x0248, 0x02e8, 0x0263, 0x02ef, 0x0a, 0x0e, 0x0000, 0x0000)),
                  'Lumberjack Tree Cave': (0x11, (0x00e2, 0x02, 0x0118, 0x0015, 0x04c6, 0x0067, 0x0548, 0x0082, 0x0553, 0x0b, 0xfa, 0x0000, 0x0000)),
                  'Two Brothers House (East)': (0x0F, (0x00f5, 0x29, 0x0880, 0x0b07, 0x0200, 0x0b58, 0x0238, 0x0b74, 0x028d, 0x09, 0x00, 0x0b86, 0x0000)),
                  'Two Brothers House (West)': (0x0E, (0x00f4, 0x28, 0x08a0, 0x0b06, 0x0100, 0x0b58, 0x01b8, 0x0b73, 0x018d, 0x0a, 0x00, 0x0bb6, 0x0000)),
                  'Sanctuary': (0x01, (0x0012, 0x13, 0x001c, 0x0400, 0x06de, 0x0414, 0x0758, 0x046d, 0x0763, 0x00, 0x02, 0x0000, 0x01aa)),
                  'Old Man Cave (West)': (0x05, (0x00f0, 0x0a, 0x03a0, 0x0264, 0x0500, 0x02b8, 0x05a8, 0x02d3, 0x058d, 0x0a, 0x00, 0x0000, 0x0000)),
                  'Old Man Cave (East)': (0x06, (0x00f1, 0x03, 0x1402, 0x0294, 0x0604, 0x02e8, 0x0678, 0x0303, 0x0683, 0x0a, 0xfc, 0x0000, 0x0000)),
                  'Old Man House (Bottom)': (0x2F, (0x00e4, 0x03, 0x181a, 0x031e, 0x06b4, 0x03a7, 0x0728, 0x038d, 0x0733, 0x00, 0x0c, 0x0000, 0x0000)),
                  'Old Man House (Top)': (0x30, (0x00e5, 0x03, 0x10c6, 0x0224, 0x0814, 0x0278, 0x0888, 0x0293, 0x0893, 0x0a, 0x0c, 0x0000, 0x0000)),
                  'Death Mountain Return Cave (East)': (0x2E, (0x00e7, 0x03, 0x0d82, 0x01c4, 0x0600, 0x0218, 0x0648, 0x0233, 0x067f, 0x0a, 0x00, 0x0000, 0x0000)),
                  'Death Mountain Return Cave (West)': (0x2D, (0x00e6, 0x0a, 0x00a0, 0x0205, 0x0500, 0x0257, 0x05b8, 0x0272, 0x058d, 0x0b, 0x00, 0x0000, 0x0000)),
                  'Spectacle Rock Cave Peak': (0x22, (0x00ea, 0x03, 0x092c, 0x0133, 0x0754, 0x0187, 0x07c8, 0x01a2, 0x07d3, 0x0b, 0xfc, 0x0000, 0x0000)),
                  'Spectacle Rock Cave': (0x21, (0x00fa, 0x03, 0x0eac, 0x01e3, 0x0754, 0x0237, 0x07c8, 0x0252, 0x07d3, 0x0b, 0xfc, 0x0000, 0x0000)),
                  'Spectacle Rock Cave (Bottom)': (0x20, (0x00f9, 0x03, 0x0d9c, 0x01c3, 0x06d4, 0x0217, 0x0748, 0x0232, 0x0753, 0x0b, 0xfc, 0x0000, 0x0000)),
                  'Paradox Cave (Bottom)': (0x1D, (0x00ff, 0x05, 0x0ee0, 0x01e3, 0x0d00, 0x0237, 0x0da8, 0x0252, 0x0d7d, 0x0b, 0x00, 0x0000, 0x0000)),
                  'Paradox Cave (Middle)': (0x1E, (0x00ef, 0x05, 0x17e0, 0x0304, 0x0d00, 0x0358, 0x0dc8, 0x0373, 0x0d7d, 0x0a, 0x00, 0x0000, 0x0000)),
                  'Paradox Cave (Top)': (0x1F, (0x00df, 0x05, 0x0460, 0x0093, 0x0d00, 0x00e7, 0x0db8, 0x0102, 0x0d7d, 0x0b, 0x00, 0x0000, 0x0000)),
                  'Fairy Ascension Cave (Bottom)': (0x19, (0x00fd, 0x05, 0x0dd4, 0x01c4, 0x0ca6, 0x0218, 0x0d18, 0x0233, 0x0d23, 0x0a, 0xfa, 0x0000, 0x0000)),
                  'Fairy Ascension Cave (Top)': (0x1A, (0x00ed, 0x05, 0x0ad4, 0x0163, 0x0ca6, 0x01b7, 0x0d18, 0x01d2, 0x0d23, 0x0b, 0xfa, 0x0000, 0x0000)),
                  'Spiral Cave': (0x1C, (0x00ee, 0x05, 0x07c8, 0x0108, 0x0c46, 0x0158, 0x0cb8, 0x0177, 0x0cc3, 0x06, 0xfa, 0x0000, 0x0000)),
                  'Spiral Cave (Bottom)': (0x1B, (0x00fe, 0x05, 0x0cca, 0x01a3, 0x0c56, 0x01f7, 0x0cc8, 0x0212, 0x0cd3, 0x0b, 0xfa, 0x0000, 0x0000)),
                  'Bumper Cave (Bottom)': (0x15, (0x00fb, 0x4a, 0x03a0, 0x0263, 0x0500, 0x02b7, 0x05a8, 0x02d2, 0x058d, 0x0b, 0x00, 0x0000, 0x0000)),
                  'Bumper Cave (Top)': (0x16, (0x00eb, 0x4a, 0x00a0, 0x020a, 0x0500, 0x0258, 0x05b8, 0x0277, 0x058d, 0x06, 0x00, 0x0000, 0x0000)),
                  'Superbunny Cave (Top)': (0x13, (0x00e8, 0x45, 0x0460, 0x0093, 0x0d00, 0x00e7, 0x0db8, 0x0102, 0x0d7d, 0x0b, 0x00, 0x0000, 0x0000)),
                  'Superbunny Cave (Bottom)': (0x12, (0x00f8, 0x45, 0x0ee0, 0x01e4, 0x0d00, 0x0238, 0x0d78, 0x0253, 0x0d7d, 0x0a, 0x00, 0x0000, 0x0000)),
                  'Hookshot Cave': (0x39, (0x003c, 0x45, 0x04da, 0x00a3, 0x0cd6, 0x0107, 0x0d48, 0x0112, 0x0d53, 0x0b, 0xfa, 0x0000, 0x0000)),
                  'Hookshot Cave Back Entrance': (0x3A, (0x002c, 0x45, 0x004c, 0x0000, 0x0c56, 0x0038, 0x0cc8, 0x006f, 0x0cd3, 0x00, 0x0a, 0x0000, 0x0000)),
                  'Ganons Tower': (0x36, (0x000c, 0x43, 0x0052, 0x0000, 0x0884, 0x0028, 0x08f8, 0x006f, 0x0903, 0x00, 0xfc, 0x0000, 0x0000)),
                  'Pyramid Entrance': (0x35, (0x0010, 0x5b, 0x0b0e, 0x075a, 0x0674, 0x07a8, 0x06e8, 0x07c7, 0x06f3, 0x06, 0xfa, 0x0000, 0x0000)),
                  'Skull Woods First Section Hole (West)': ([0xDB84D, 0xDB84E], None),
                  'Skull Woods First Section Hole (East)': ([0xDB84F, 0xDB850], None),
                  'Skull Woods First Section Hole (North)': ([0xDB84C], None),
                  'Skull Woods Second Section Hole': ([0xDB851, 0xDB852], None),
                  'Pyramid Hole': ([0xDB854, 0xDB855, 0xDB856], None),
                  'Inverted Pyramid Hole': ([0xDB854, 0xDB855, 0xDB856, 0x180340], None),
                  'Waterfall of Wishing': (0x5B, (0x0114, 0x0f, 0x0080, 0x0200, 0x0e00, 0x0207, 0x0e60, 0x026f, 0x0e7d, 0x00, 0x00, 0x0000, 0x0000)),
                  'Dam': (0x4D, (0x010b, 0x3b, 0x04a0, 0x0e8a, 0x06fa, 0x0ed8, 0x0778, 0x0ef7, 0x077f, 0x06, 0xfa, 0x0000, 0x0000)),
                  'Blinds Hideout': (0x60, (0x0119, 0x18, 0x02b2, 0x064a, 0x0186, 0x0697, 0x0208, 0x06b7, 0x0213, 0x06, 0xfa, 0x0000, 0x0000)),
                  'Hyrule Castle Secret Entrance Drop': ([0xDB858], None),
                  'Bonk Fairy (Light)': (0x76, (0x0126, 0x2b, 0x00a0, 0x0a0a, 0x0700, 0x0a67, 0x0788, 0x0a77, 0x0785, 0x06, 0xfa, 0x0000, 0x0000)),
                  'Lake Hylia Fairy': (0x5D, (0x0115, 0x2e, 0x0016, 0x0a00, 0x0cb6, 0x0a37, 0x0d28, 0x0a6d, 0x0d33, 0x00, 0x00, 0x0000, 0x0000)),
                  'Light Hype Fairy': (0x6B, (0x0115, 0x34, 0x00a0, 0x0c04, 0x0900, 0x0c58, 0x0988, 0x0c73, 0x0985, 0x0a, 0xf6, 0x0000, 0x0000)),
                  'Desert Fairy': (0x71, (0x0115, 0x3a, 0x0000, 0x0e00, 0x0400, 0x0e26, 0x0468, 0x0e6d, 0x0485, 0x00, 0x00, 0x0000, 0x0000)),
                  'Kings Grave': (0x5A, (0x0113, 0x14, 0x0320, 0x0456, 0x0900, 0x04a6, 0x0998, 0x04c3, 0x097d, 0x0a, 0xf6, 0x0000, 0x0000)),
                  'Tavern North': (0x42, (0x0103, 0x18, 0x1440, 0x08a7, 0x0206, 0x091b, 0x0288, 0x0914, 0x0293, 0xf7, 0x09, 0xFFFF, 0x0000)),
                  'Chicken House': (0x4A, (0x0108, 0x18, 0x1120, 0x0837, 0x0106, 0x0888, 0x0188, 0x08a4, 0x0193, 0x07, 0xf9, 0x1530, 0x0000)),
                  'Aginahs Cave': (0x70, (0x010a, 0x30, 0x0656, 0x0cc6, 0x02aa, 0x0d18, 0x0328, 0x0d33, 0x032f, 0x08, 0xf8, 0x0000, 0x0000)),
                  'Sahasrahlas Hut': (0x44, (0x0105, 0x1e, 0x0610, 0x06d4, 0x0c76, 0x0727, 0x0cf0, 0x0743, 0x0cfb, 0x0a, 0xf6, 0x0000, 0x0000)),
                  'Lake Hylia Shop': (0x57, (0x0112, 0x35, 0x0022, 0x0c00, 0x0b1a, 0x0c26, 0x0b98, 0x0c6d, 0x0b9f, 0x00, 0x00, 0x0000, 0x0000)),
                  'Capacity Upgrade': (0x5C, (0x0115, 0x35, 0x0a46, 0x0d36, 0x0c2a, 0x0d88, 0x0ca8, 0x0da3, 0x0caf, 0x0a, 0xf6, 0x0000, 0x0000)),
                  'Kakariko Well Drop': ([0xDB85C, 0xDB85D], None),
                  'Blacksmiths Hut': (0x63, (0x0121, 0x22, 0x010c, 0x081a, 0x0466, 0x0868, 0x04d8, 0x0887, 0x04e3, 0x06, 0xfa, 0x041A, 0x0000)),
                  'Bat Cave Drop': ([0xDB859, 0xDB85A], None),
                  'Sick Kids House': (0x3F, (0x0102, 0x18, 0x10be, 0x0826, 0x01f6, 0x0877, 0x0278, 0x0893, 0x0283, 0x08, 0xf8, 0x14CE, 0x0000)),
                  'North Fairy Cave Drop': ([0xDB857], None),
                  'Lost Woods Gamble': (0x3B, (0x0100, 0x00, 0x004e, 0x0000, 0x0272, 0x0008, 0x02f0, 0x006f, 0x02f7, 0x00, 0x00, 0x0000, 0x0000)),
                  'Fortune Teller (Light)': (0x64, (0x0122, 0x11, 0x060e, 0x04b4, 0x027d, 0x0508, 0x02f8, 0x0523, 0x0302, 0x0a, 0xf6, 0x0000, 0x0000)),
                  'Snitch Lady (East)': (0x3D, (0x0101, 0x18, 0x0ad8, 0x074a, 0x02c6, 0x0798, 0x0348, 0x07b7, 0x0353, 0x06, 0xfa, 0x0DE8, 0x0000)),
                  'Snitch Lady (West)': (0x3E, (0x0101, 0x18, 0x0788, 0x0706, 0x0046, 0x0758, 0x00c8, 0x0773, 0x00d3, 0x08, 0xf8, 0x0B98, 0x0000)),
                  'Bush Covered House': (0x43, (0x0103, 0x18, 0x1156, 0x081a, 0x02b6, 0x0868, 0x0338, 0x0887, 0x0343, 0x06, 0xfa, 0x1466, 0x0000)),
                  'Tavern (Front)': (0x41, (0x0103, 0x18, 0x1842, 0x0916, 0x0206, 0x0967, 0x0288, 0x0983, 0x0293, 0x08, 0xf8, 0x1C50, 0x0000)),
                  'Light World Bomb Hut': (0x49, (0x0107, 0x18, 0x1800, 0x0916, 0x0000, 0x0967, 0x0068, 0x0983, 0x008d, 0x08, 0xf8, 0x9C0C, 0x0000)),
                  'Kakariko Shop': (0x45, (0x011f, 0x18, 0x16a8, 0x08e7, 0x0136, 0x0937, 0x01b8, 0x0954, 0x01c3, 0x07, 0xf9, 0x1AB6, 0x0000)),
                  'Lost Woods Hideout Drop': ([0xDB853], None),
                  'Lumberjack Tree Tree': ([0xDB85B], None),
                  'Cave 45': (0x50, (0x011b, 0x32, 0x0680, 0x0cc9, 0x0400, 0x0d16, 0x0438, 0x0d36, 0x0485, 0x07, 0xf9, 0x0000, 0x0000)),
                  'Graveyard Cave': (0x51, (0x011b, 0x14, 0x0016, 0x0400, 0x08a2, 0x0446, 0x0918, 0x046d, 0x091f, 0x00, 0x00, 0x0000, 0x0000)),
                  'Checkerboard Cave': (0x7D, (0x0126, 0x30, 0x00c8, 0x0c0a, 0x024a, 0x0c67, 0x02c8, 0x0c77, 0x02cf, 0x06, 0xfa, 0x0000, 0x0000)),
                  'Mini Moldorm Cave': (0x7C, (0x0123, 0x35, 0x1480, 0x0e96, 0x0a00, 0x0ee8, 0x0a68, 0x0f03, 0x0a85, 0x08, 0xf8, 0x0000, 0x0000)),
                  'Long Fairy Cave': (0x54, (0x011e, 0x2f, 0x06a0, 0x0aca, 0x0f00, 0x0b18, 0x0fa8, 0x0b37, 0x0f85, 0x06, 0xfa, 0x0000, 0x0000)),
                  'Good Bee Cave': (0x6A, (0x0120, 0x37, 0x0084, 0x0c00, 0x0e26, 0x0c36, 0x0e98, 0x0c6f, 0x0ea3, 0x00, 0x00, 0x0000, 0x0000)),
                  '20 Rupee Cave': (0x7A, (0x0125, 0x37, 0x0200, 0x0c23, 0x0e00, 0x0c86, 0x0e68, 0x0c92, 0x0e7d, 0x0d, 0xf3, 0x0000, 0x0000)),
                  '50 Rupee Cave': (0x78, (0x0124, 0x3a, 0x0790, 0x0eea, 0x047a, 0x0f47, 0x04f8, 0x0f57, 0x04ff, 0x06, 0xfa, 0x0000, 0x0000)),
                  'Ice Rod Cave': (0x7F, (0x0120, 0x37, 0x0080, 0x0c00, 0x0e00, 0x0c37, 0x0e48, 0x0c6f, 0x0e7d, 0x00, 0x00, 0x0000, 0x0000)),
                  'Bonk Rock Cave': (0x79, (0x0124, 0x13, 0x0280, 0x044a, 0x0600, 0x04a7, 0x0638, 0x04b7, 0x067d, 0x06, 0xfa, 0x0000, 0x0000)),
                  'Library': (0x48, (0x0107, 0x29, 0x0100, 0x0a14, 0x0200, 0x0a67, 0x0278, 0x0a83, 0x0285, 0x0a, 0xf6, 0x040E, 0x0000)),
                  'Potion Shop': (0x4B, (0x0109, 0x16, 0x070a, 0x04e6, 0x0c56, 0x0538, 0x0cc8, 0x0553, 0x0cd3, 0x08, 0xf8, 0x0A98, 0x0000)),
                  'Sanctuary Grave': ([0xDB85E], None),
                  'Hookshot Fairy': (0x4F, (0x010c, 0x05, 0x0ee0, 0x01e3, 0x0d00, 0x0236, 0x0d78, 0x0252, 0x0d7d, 0x0b, 0xf5, 0x0000, 0x0000)),
                  'Pyramid Fairy': (0x62, (0x0116, 0x5b, 0x0b1e, 0x0754, 0x06fa, 0x07a7, 0x0778, 0x07c3, 0x077f, 0x0a, 0xf6, 0x0000, 0x0000)),
                  'East Dark World Hint': (0x68, (0x010e, 0x6f, 0x06a0, 0x0aca, 0x0f00, 0x0b18, 0x0fa8, 0x0b37, 0x0f85, 0x06, 0xfa, 0x0000, 0x0000)),
                  'Palace of Darkness Hint': (0x67, (0x011a, 0x5e, 0x0c24, 0x0794, 0x0d12, 0x07e8, 0x0d90, 0x0803, 0x0d97, 0x0a, 0xf6, 0x0000, 0x0000)),
                  'Dark Lake Hylia Fairy': (0x6C, (0x0115, 0x6e, 0x0016, 0x0a00, 0x0cb6, 0x0a36, 0x0d28, 0x0a6d, 0x0d33, 0x00, 0x00, 0x0000, 0x0000)),
                  'Dark Lake Hylia Ledge Fairy': (0x80, (0x0115, 0x77, 0x0080, 0x0c00, 0x0e00, 0x0c37, 0x0e48, 0x0c6f, 0x0e7d, 0x00, 0x00, 0x0000, 0x0000)),
                  'Dark Lake Hylia Ledge Spike Cave': (0x7B, (0x0125, 0x77, 0x0200, 0x0c27, 0x0e00, 0x0c86, 0x0e68, 0x0c96, 0x0e7d, 0x09, 0xf7, 0x0000, 0x0000)),
                  'Dark Lake Hylia Ledge Hint': (0x69, (0x010e, 0x77, 0x0084, 0x0c00, 0x0e26, 0x0c36, 0x0e98, 0x0c6f, 0x0ea3, 0x00, 0x00, 0x0000, 0x0000)),
                  'Hype Cave': (0x3C, (0x011e, 0x74, 0x00a0, 0x0c0a, 0x0900, 0x0c58, 0x0988, 0x0c77, 0x097d, 0x06, 0xfa, 0x0000, 0x0000)),
                  'Bonk Fairy (Dark)': (0x77, (0x0126, 0x6b, 0x00a0, 0x0a05, 0x0700, 0x0a66, 0x0788, 0x0a72, 0x0785, 0x0b, 0xf5, 0x0000, 0x0000)),
                  'Brewery': (0x47, (0x0106, 0x58, 0x16a8, 0x08e4, 0x013e, 0x0938, 0x01b8, 0x0953, 0x01c3, 0x0a, 0xf6, 0x1AB6, 0x0000)),
                  'C-Shaped House': (0x53, (0x011c, 0x58, 0x09d8, 0x0744, 0x02ce, 0x0797, 0x0348, 0x07b3, 0x0353, 0x0a, 0xf6, 0x0DE8, 0x0000)),
                  'Chest Game': (0x46, (0x0106, 0x58, 0x078a, 0x0705, 0x004e, 0x0758, 0x00c8, 0x0774, 0x00d3, 0x09, 0xf7, 0x0B98, 0x0000)),
                  'Hammer Peg Cave': (0x7E, (0x0127, 0x62, 0x0894, 0x091e, 0x0492, 0x09a6, 0x0508, 0x098b, 0x050f, 0x00, 0x00, 0x0000, 0x0000)),
                  'Red Shield Shop': (0x74, (0x0110, 0x5a, 0x079a, 0x06e8, 0x04d6, 0x0738, 0x0548, 0x0755, 0x0553, 0x08, 0xf8, 0x0AA8, 0x0000)),
                  'Dark Sanctuary Hint': (0x59, (0x0112, 0x53, 0x001e, 0x0400, 0x06e2, 0x0446, 0x0758, 0x046d, 0x075f, 0x00, 0x00, 0x0000, 0x0000)),
                  'Fortune Teller (Dark)': (0x65, (0x0122, 0x51, 0x0610, 0x04b4, 0x027e, 0x0507, 0x02f8, 0x0523, 0x0303, 0x0a, 0xf6, 0x091E, 0x0000)),
                  'Dark World Shop': (0x5F, (0x010f, 0x58, 0x1058, 0x0814, 0x02be, 0x0868, 0x0338, 0x0883, 0x0343, 0x0a, 0xf6, 0x0000, 0x0000)),
                  'Dark Lumberjack Shop': (0x56, (0x010f, 0x42, 0x041c, 0x0074, 0x04e2, 0x00c7, 0x0558, 0x00e3, 0x055f, 0x0a, 0xf6, 0x0000, 0x0000)),
                  'Dark Potion Shop': (0x6E, (0x010f, 0x56, 0x080e, 0x04f4, 0x0c66, 0x0548, 0x0cd8, 0x0563, 0x0ce3, 0x0a, 0xf6, 0x0000, 0x0000)),
                  'Archery Game': (0x58, (0x0111, 0x69, 0x069e, 0x0ac4, 0x02ea, 0x0b18, 0x0368, 0x0b33, 0x036f, 0x0a, 0xf6, 0x09AC, 0x0000)),
                  'Mire Shed': (0x5E, (0x010d, 0x70, 0x0384, 0x0c69, 0x001e, 0x0cb6, 0x0098, 0x0cd6, 0x00a3, 0x07, 0xf9, 0x0000, 0x0000)),
                  'Dark Desert Hint': (0x61, (0x0114, 0x70, 0x0654, 0x0cc5, 0x02aa, 0x0d16, 0x0328, 0x0d32, 0x032f, 0x09, 0xf7, 0x0000, 0x0000)),
                  'Dark Desert Fairy': (0x55, (0x0115, 0x70, 0x03a8, 0x0c6a, 0x013a, 0x0cb7, 0x01b8, 0x0cd7, 0x01bf, 0x06, 0xfa, 0x0000, 0x0000)),
                  'Spike Cave': (0x40, (0x0117, 0x43, 0x0ed4, 0x01e4, 0x08aa, 0x0236, 0x0928, 0x0253, 0x092f, 0x0a, 0xf6, 0x0000, 0x0000)),
                  'Dark Death Mountain Shop': (0x6D, (0x0112, 0x45, 0x0ee0, 0x01e3, 0x0d00, 0x0236, 0x0daa, 0x0252, 0x0d7d, 0x0b, 0xf5, 0x0000, 0x0000)),
                  'Dark Death Mountain Fairy': (0x6F, (0x0115, 0x43, 0x1400, 0x0294, 0x0600, 0x02e8, 0x0678, 0x0303, 0x0685, 0x0a, 0xf6, 0x0000, 0x0000)),
                  'Mimic Cave': (0x4E, (0x010c, 0x05, 0x07e0, 0x0103, 0x0d00, 0x0156, 0x0d78, 0x0172, 0x0d7d, 0x0b, 0xf5, 0x0000, 0x0000)),
                  'Big Bomb Shop': (0x52, (0x011c, 0x6c, 0x0506, 0x0a9a, 0x0832, 0x0ae7, 0x08b8, 0x0b07, 0x08bf, 0x06, 0xfa, 0x0816, 0x0000)),
                  'Dark Lake Hylia Shop': (0x73, (0x010f, 0x75, 0x0380, 0x0c6a, 0x0a00, 0x0cb8, 0x0a58, 0x0cd7, 0x0a85, 0x06, 0xfa, 0x0000, 0x0000)),
                  'Lumberjack House': (0x75, (0x011f, 0x02, 0x049c, 0x0088, 0x04e6, 0x00d8, 0x0558, 0x00f7, 0x0563, 0x08, 0xf8, 0x07AA, 0x0000)),
                  'Lake Hylia Fortune Teller': (0x72, (0x0122, 0x35, 0x0380, 0x0c6a, 0x0a00, 0x0cb8, 0x0a58, 0x0cd7, 0x0a85, 0x06, 0xfa, 0x0000, 0x0000)),
                  'Kakariko Gamble Game': (0x66, (0x0118, 0x29, 0x069e, 0x0ac4, 0x02ea, 0x0b18, 0x0368, 0x0b33, 0x036f, 0x0a, 0xf6, 0x09AC, 0x0000))}

# format:
# Key=Name
# value = entrance #
#        | (entrance #, exit #)
exit_ids = {'Links House Exit': (0x01, 0x00),
            'Chris Houlihan Room Exit': (None, 0x3D),
            'Desert Palace Exit (South)': (0x09, 0x0A),
            'Desert Palace Exit (West)': (0x0B, 0x0C),
            'Desert Palace Exit (East)': (0x0A, 0x0B),
            'Desert Palace Exit (North)': (0x0C, 0x0D),
            'Eastern Palace Exit': (0x08, 0x09),
            'Tower of Hera Exit': (0x33, 0x2D),
            'Hyrule Castle Exit (South)': (0x04, 0x03),
            'Hyrule Castle Exit (West)': (0x03, 0x02),
            'Hyrule Castle Exit (East)': (0x05, 0x04),
            'Agahnims Tower Exit': (0x24, 0x25),
            'Thieves Town Exit': (0x34, 0x35),
            'Skull Woods First Section Exit': (0x2A, 0x2B),
            'Skull Woods Second Section Exit (East)': (0x29, 0x2A),
            'Skull Woods Second Section Exit (West)': (0x28, 0x29),
            'Skull Woods Final Section Exit': (0x2B, 0x2C),
            'Ice Palace Exit': (0x2D, 0x2E),
            'Misery Mire Exit': (0x27, 0x28),
            'Palace of Darkness Exit': (0x26, 0x27),
            'Swamp Palace Exit': (0x25, 0x26),
            'Turtle Rock Exit (Front)': (0x35, 0x34),
            'Turtle Rock Ledge Exit (West)': (0x15, 0x16),
            'Turtle Rock Ledge Exit (East)': (0x19, 0x1A),
            'Turtle Rock Isolated Ledge Exit': (0x18, 0x19),
            'Hyrule Castle Secret Entrance Exit': (0x32, 0x33),
            'Kakariko Well Exit': (0x39, 0x3A),
            'Bat Cave Exit': (0x11, 0x12),
            'Elder House Exit (East)': (0x0E, 0x0F),
            'Elder House Exit (West)': (0x0D, 0x0E),
            'North Fairy Cave Exit': (0x38, 0x39),
            'Lost Woods Hideout Exit': (0x2C, 0x36),
            'Lumberjack Tree Exit': (0x12, 0x13),
            'Two Brothers House Exit (East)': (0x10, 0x11),
            'Two Brothers House Exit (West)': (0x0F, 0x10),
            'Sanctuary Exit': (0x02, 0x01),
            'Old Man Cave Exit (East)': (0x07, 0x08),
            'Old Man Cave Exit (West)': (0x06, 0x07),
            'Old Man House Exit (Bottom)': (0x30, 0x31),
            'Old Man House Exit (Top)': (0x31, 0x32),
            'Death Mountain Return Cave Exit (West)': (0x2E, 0x2F),
            'Death Mountain Return Cave Exit (East)': (0x2F, 0x30),
            'Spectacle Rock Cave Exit': (0x21, 0x22),
            'Spectacle Rock Cave Exit (Top)': (0x22, 0x23),
            'Spectacle Rock Cave Exit (Peak)': (0x23, 0x24),
            'Paradox Cave Exit (Bottom)': (0x1E, 0x1F),
            'Paradox Cave Exit (Middle)': (0x1F, 0x20),
            'Paradox Cave Exit (Top)': (0x20, 0x21),
            'Fairy Ascension Cave Exit (Bottom)': (0x1A, 0x1B),
            'Fairy Ascension Cave Exit (Top)': (0x1B, 0x1C),
            'Spiral Cave Exit': (0x1C, 0x1D),
            'Spiral Cave Exit (Top)': (0x1D, 0x1E),
            'Bumper Cave Exit (Top)': (0x17, 0x18),
            'Bumper Cave Exit (Bottom)': (0x16, 0x17),
            'Superbunny Cave Exit (Top)': (0x14, 0x15),
            'Superbunny Cave Exit (Bottom)': (0x13, 0x14),
            'Hookshot Cave Front Exit': (0x3A, 0x3B),
            'Hookshot Cave Back Exit': (0x3B, 0x3C),
            'Ganons Tower Exit': (0x37, 0x38),
            'Pyramid Exit': (0x36, 0x37),
            'Waterfall of Wishing': 0x5C,
            'Dam': 0x4E,
            'Blinds Hideout': 0x61,
            'Lumberjack House': 0x6B,
            'Bonk Fairy (Light)': 0x71,
            'Bonk Fairy (Dark)': 0x71,
            'Lake Hylia Healer Fairy': 0x5E,
            'Light Hype Fairy': 0x5E,
            'Desert Healer Fairy': 0x5E,
            'Dark Lake Hylia Healer Fairy': 0x5E,
            'Dark Lake Hylia Ledge Healer Fairy': 0x5E,
            'Dark Desert Healer Fairy': 0x5E,
            'Dark Death Mountain Healer Fairy': 0x5E,
            'Fortune Teller (Light)': 0x65,
            'Lake Hylia Fortune Teller': 0x65,
            'Kings Grave': 0x5B,
            'Tavern': 0x43,
            'Chicken House': 0x4B,
            'Aginahs Cave': 0x4D,
            'Sahasrahlas Hut': 0x45,
            'Lake Hylia Shop': 0x58,
            'Dark Death Mountain Shop': 0x58,
            'Capacity Upgrade': 0x5D,
            'Blacksmiths Hut': 0x64,
            'Sick Kids House': 0x40,
            'Lost Woods Gamble': 0x3C,
            'Snitch Lady (East)': 0x3E,
            'Snitch Lady (West)': 0x3F,
            'Bush Covered House': 0x44,
            'Tavern (Front)': 0x42,
            'Light World Bomb Hut': 0x4A,
            'Kakariko Shop': 0x46,
            'Cave 45': 0x51,
            'Graveyard Cave': 0x52,
            'Checkerboard Cave': 0x72,
            'Mini Moldorm Cave': 0x6C,
            'Long Fairy Cave': 0x55,
            'Good Bee Cave': 0x56,
            '20 Rupee Cave': 0x6F,
            '50 Rupee Cave': 0x6D,
            'Ice Rod Cave': 0x84,
            'Bonk Rock Cave': 0x6E,
            'Library': 0x49,
            'Kakariko Gamble Game': 0x67,
            'Potion Shop': 0x4C,
            'Hookshot Fairy': 0x50,
            'Pyramid Fairy': 0x63,
            'East Dark World Hint': 0x69,
            'Palace of Darkness Hint': 0x68,
            'Big Bomb Shop': 0x53,
            'Village of Outcasts Shop': 0x60,
            'Dark Lake Hylia Shop': 0x60,
            'Dark Lumberjack Shop': 0x60,
            'Dark Potion Shop': 0x60,
            'Dark Lake Hylia Ledge Spike Cave': 0x70,
            'Dark Lake Hylia Ledge Hint': 0x6A,
            'Hype Cave': 0x3D,
            'Brewery': 0x48,
            'C-Shaped House': 0x54,
            'Chest Game': 0x47,
            'Hammer Peg Cave': 0x83,
            'Red Shield Shop': 0x57,
            'Dark Sanctuary Hint': 0x5A,
            'Fortune Teller (Dark)': 0x66,
            'Archery Game': 0x59,
            'Mire Shed': 0x5F,
            'Dark Desert Hint': 0x62,
            'Spike Cave': 0x41,
            'Mimic Cave': 0x4F,
            'Kakariko Well (top)': 0x80,
            'Hyrule Castle Secret Entrance': 0x7D,
            'Bat Cave (right)': 0x7E,
            'North Fairy Cave': 0x7C,
            'Lost Woods Hideout (top)': 0x7A,
            'Lumberjack Tree (top)': 0x7F,
            'Sewer Drop': 0x81,
            'Skull Back Drop': 0x79,
            'Skull Left Drop': 0x77,
            'Skull Pinball': 0x78,
            'Skull Pot Circle': 0x76,
            'Pyramid': 0x7B}

ow_prize_table = {'Links House': (0x8b1, 0xb2d),
                  'Desert Palace Entrance (South)': (0x108, 0xd70), 'Desert Palace Entrance (West)': (0x031, 0xca0),
                  'Desert Palace Entrance (North)': (0x0e1, 0xba0), 'Desert Palace Entrance (East)': (0x191, 0xca0),
                  'Eastern Palace': (0xf31, 0x620), 'Tower of Hera': (0x8D0, 0x080),
                  'Hyrule Castle Entrance (South)': (0x7b0, 0x730), 'Hyrule Castle Entrance (West)': (0x700, 0x640),
                  'Hyrule Castle Entrance (East)': (0x8a0, 0x640), 'Inverted Pyramid Entrance': (0x720, 0x700),
                  'Agahnims Tower': (0x7e0, 0x640),
                  'Thieves Town': (0x1d0, 0x780), 'Skull Woods First Section Door': (0x240, 0x280),
                  'Skull Woods Second Section Door (East)': (0x1a0, 0x240),
                  'Skull Woods Second Section Door (West)': (0x0c0, 0x1c0), 'Skull Woods Final Section': (0x082, 0x0b0),
                  'Ice Palace': (0xca0, 0xda0),
                  'Misery Mire': (0x100, 0xca0),
                  'Palace of Darkness': (0xf40, 0x620), 'Swamp Palace': (0x759, 0xED0),
                  'Turtle Rock': (0xf11, 0x103),
                  'Dark Death Mountain Ledge (West)': (0xb80, 0x180),
                  'Dark Death Mountain Ledge (East)': (0xc80, 0x180),
                  'Turtle Rock Isolated Ledge Entrance': (0xc00, 0x240),
                  'Hyrule Castle Secret Entrance Stairs': (0x850, 0x700),
                  'Kakariko Well Cave': (0x060, 0x680),
                  'Bat Cave Cave': (0x540, 0x8f0),
                  'Elder House (East)': (0x2b0, 0x6a0),
                  'Elder House (West)': (0x230, 0x6a0),
                  'North Fairy Cave': (0xa80, 0x440),
                  'Lost Woods Hideout Stump': (0x240, 0x280),
                  'Lumberjack Tree Cave': (0x4e0, 0x004),
                  'Two Brothers House (East)': (0x200, 0x0b60),
                  'Two Brothers House (West)': (0x180, 0x0b60),
                  'Sanctuary': (0x720, 0x4a0),
                  'Old Man Cave (West)': (0x580, 0x2c0),
                  'Old Man Cave (East)': (0x620, 0x2c0),
                  'Old Man House (Bottom)': (0x720, 0x320),
                  'Old Man House (Top)': (0x820, 0x220),
                  'Death Mountain Return Cave (East)': (0x600, 0x220),
                  'Death Mountain Return Cave (West)': (0x500, 0x1c0),
                  'Spectacle Rock Cave Peak': (0x720, 0x0a0),
                  'Spectacle Rock Cave': (0x790, 0x1a0),
                  'Spectacle Rock Cave (Bottom)': (0x710, 0x0a0),
                  'Paradox Cave (Bottom)': (0xd80, 0x180),
                  'Paradox Cave (Middle)': (0xd80, 0x380),
                  'Paradox Cave (Top)': (0xd80, 0x020),
                  'Fairy Ascension Cave (Bottom)': (0xcc8, 0x2a0),
                  'Fairy Ascension Cave (Top)': (0xc00, 0x240),
                  'Spiral Cave': (0xb80, 0x180),
                  'Spiral Cave (Bottom)': (0xb80, 0x2c0),
                  'Bumper Cave (Bottom)': (0x580, 0x2c0),
                  'Bumper Cave (Top)': (0x500, 0x1c0),
                  'Superbunny Cave (Top)': (0xd80, 0x020),
                  'Superbunny Cave (Bottom)': (0xd00, 0x180),
                  'Hookshot Cave': (0xc80, 0x0c0),
                  'Hookshot Cave Back Entrance': (0xcf0, 0x004),
                  'Ganons Tower': (0x8D0, 0x080),
                  'Pyramid Entrance': (0x640, 0x7c0),
                  'Skull Woods First Section Hole (West)': None,
                  'Skull Woods First Section Hole (East)': None,
                  'Skull Woods First Section Hole (North)': None,
                  'Skull Woods Second Section Hole': None,
                  'Pyramid Hole': None,
                  'Inverted Pyramid Hole': None,
                  'Waterfall of Wishing': (0xe80, 0x280),
                  'Dam': (0x759, 0xED0),
                  'Blinds Hideout': (0x190, 0x6c0),
                  'Hyrule Castle Secret Entrance Drop': None,
                  'Bonk Fairy (Light)': (0x740, 0xa80),
                  'Lake Hylia Fairy': (0xd40, 0x9f0),
                  'Light Hype Fairy': (0x940, 0xc80),
                  'Desert Fairy': (0x420, 0xe00),
                  'Kings Grave': (0x920, 0x520),
                  'Tavern North': (0x270, 0x900),
                  'Chicken House': (0x120, 0x880),
                  'Aginahs Cave': (0x2e0, 0xd00),
                  'Sahasrahlas Hut': (0xcf0, 0x6c0),
                  'Lake Hylia Shop': (0xbc0, 0xc00),
                  'Capacity Upgrade': (0xca0, 0xda0),
                  'Kakariko Well Drop': None,
                  'Blacksmiths Hut': (0x4a0, 0x880),
                  'Bat Cave Drop': None,
                  'Sick Kids House': (0x220, 0x880),
                  'North Fairy Cave Drop': None,
                  'Lost Woods Gamble': (0x240, 0x080),
                  'Fortune Teller (Light)': (0x2c0, 0x4c0),
                  'Snitch Lady (East)': (0x310, 0x7a0),
                  'Snitch Lady (West)': (0x080, 0x7a0),
                  'Bush Covered House': (0x2e0, 0x880),
                  'Tavern (Front)': (0x270, 0x980),
                  'Light World Bomb Hut': (0x070, 0x980),
                  'Kakariko Shop': (0x170, 0x980),
                  'Lost Woods Hideout Drop': None,
                  'Lumberjack Tree Tree': None,
                  'Cave 45': (0x440, 0xca0), 'Graveyard Cave': (0x8f0, 0x430),
                  'Checkerboard Cave': (0x260, 0xc00),
                  'Mini Moldorm Cave': (0xa40, 0xe80),
                  'Long Fairy Cave': (0xf60, 0xb00),
                  'Good Bee Cave': (0xec0, 0xc00),
                  '20 Rupee Cave': (0xe80, 0xca0),
                  '50 Rupee Cave': (0x4d0, 0xed0),
                  'Ice Rod Cave': (0xe00, 0xc00),
                  'Bonk Rock Cave': (0x5f0, 0x460),
                  'Library': (0x270, 0xaa0),
                  'Potion Shop': (0xc80, 0x4c0),
                  'Sanctuary Grave': None,
                  'Hookshot Fairy': (0xd00, 0x180),
                  'Pyramid Fairy': (0x740, 0x740),
                  'East Dark World Hint': (0xf60, 0xb00),
                  'Palace of Darkness Hint': (0xd60, 0x7c0),
                  'Dark Lake Hylia Fairy': (0xd40, 0x9f0),
                  'Dark Lake Hylia Ledge Fairy': (0xe00, 0xc00),
                  'Dark Lake Hylia Ledge Spike Cave': (0xe80, 0xca0),
                  'Dark Lake Hylia Ledge Hint': (0xec0, 0xc00),
                  'Hype Cave': (0x940, 0xc80),
                  'Bonk Fairy (Dark)': (0x740, 0xa80),
                  'Brewery': (0x170, 0x980), 'C-Shaped House': (0x310, 0x7a0), 'Chest Game': (0x080, 0x7a0),
                  'Hammer Peg Cave': (0x4c0, 0x940),
                  'Red Shield Shop': (0x500, 0x680),
                  'Dark Sanctuary Hint': (0x720, 0x4a0),
                  'Fortune Teller (Dark)': (0x2c0, 0x4c0),
                  'Dark World Shop': (0x2e0, 0x880),
                  'Dark Lumberjack Shop': (0x4e0, 0x0d0),
                  'Dark Potion Shop': (0xc80, 0x4c0),
                  'Archery Game': (0x2f0, 0xaf0),
                  'Mire Shed': (0x060, 0xc90),
                  'Dark Desert Hint': (0x2e0, 0xd00),
                  'Dark Desert Fairy': (0x1c0, 0xc90),
                  'Spike Cave': (0x860, 0x180),
                  'Dark Death Mountain Shop': (0xd80, 0x180),
                  'Dark Death Mountain Fairy': (0x620, 0x2c0),
                  'Mimic Cave': (0xc80, 0x180),
                  'Big Bomb Shop': (0x8b1, 0xb2d),
                  'Dark Lake Hylia Shop': (0xa40, 0xc40),
                  'Lumberjack House': (0x4e0, 0x0d0),
                  'Lake Hylia Fortune Teller': (0xa40, 0xc40),
                  'Kakariko Gamble Game': (0x2f0, 0xaf0)}
