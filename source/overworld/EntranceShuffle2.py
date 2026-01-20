import RaceRandom as random
import logging
import copy

from collections import defaultdict, OrderedDict
from BaseClasses import RegionType

from source.overworld.EntranceData import door_addresses


class EntrancePool(object):
    def __init__(self, world, player):
        self.entrances = set()
        self.exits = set()
        self.inverted = False
        self.coupled = True
        self.swapped = False
        self.assumed_loose_caves = False
        self.keep_drops_together = True
        self.default_map = {}
        self.one_way_map = {}
        self.combine_map = {}
        self.skull_handled = False
        self.links_on_mountain = False
        self.decoupled_entrances = []
        self.decoupled_exits = []
        self.original_entrances = set()
        self.original_exits = set()
        self.same_world_restricted = {}

        self.world = world
        self.player = player

    def is_standard(self):
        return self.world.mode[self.player] == 'standard'

    def is_sanc_forced_in_hc(self):
        return self.is_standard() or self.world.doorShuffle[self.player] in ['vanilla', 'basic'] or self.world.intensity[self.player] < 3


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

    from OverworldShuffle import build_sectors
    if not world.owsectors[player] and world.shuffle[player] != 'vanilla':
        world.owsectors[player] = build_sectors(world, player)

    avail_pool.entrances = set(i_drop_map.keys()).union(i_entrance_map.keys()).union(i_single_ent_map.keys())
    avail_pool.exits = set(i_entrance_map.values()).union(i_drop_map.values()).union(i_single_ent_map.values())
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
    if avail_pool.world.is_atgt_swapped(avail_pool.player):
        default_map['Ganons Tower'] = 'Agahnims Tower Exit'
        default_map['Agahnims Tower'] = 'Ganons Tower Exit'
    avail_pool.default_map = default_map
    avail_pool.one_way_map = one_way_map
    avail_pool.combine_map = {**default_map, **one_way_map}

    global LW_Entrances, DW_Entrances
    LW_Entrances = []
    DW_Entrances = []
    for e in [e for e in avail_pool.entrances if e not in drop_map]:
        region = world.get_entrance(e, player).parent_region
        if region.type == RegionType.LightWorld:
            LW_Entrances.append(e)
        else:
            DW_Entrances.append(e)

    # setup mandatory connections
    for exit_name, region_name in mandatory_connections:
        connect_simple(world, exit_name, region_name, player)
    
    connect_custom(avail_pool, world, player)

    if world.shuffle[player] == 'vanilla':
        do_vanilla_connections(avail_pool)
    else:
        mode = world.shuffle[player]
        if mode not in modes:
            raise RuntimeError(f'Shuffle mode {mode} is not yet supported')
        mode_cfg = copy.deepcopy(modes[mode])

        if world.linked_drops[player] != 'unset':
            mode_cfg['keep_drops_together'] = 'on' if world.linked_drops[player] == 'linked' else 'off'

        avail_pool.swapped = mode_cfg['undefined'] == 'swap'
        avail_pool.keep_drops_together = mode_cfg['keep_drops_together'] == 'on' if 'keep_drops_together' in mode_cfg else True
        avail_pool.assumed_loose_caves = not avail_pool.keep_drops_together and world.shuffle[player] == 'district'
        avail_pool.coupled = mode_cfg['decoupled'] != 'on' if 'decoupled' in mode_cfg else True
        if avail_pool.is_standard():
            do_standard_connections(avail_pool)
        pool_list = mode_cfg['pools'] if 'pools' in mode_cfg else {}
        for pool_name, pool in pool_list.items():
            special_shuffle = pool['special'] if 'special' in pool else None
            if special_shuffle == 'drops':
                handle_skull_woods_drops(avail_pool, pool['entrances'], mode_cfg)
            elif special_shuffle == 'normal_drops':
                cross_world = mode_cfg['cross_world'] == 'on' if 'cross_world' in mode_cfg else False
                do_holes_and_linked_drops(set(avail_pool.entrances), set(avail_pool.exits), avail_pool, cross_world)
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
            elif special_shuffle == 'limited':
                do_limited_shuffle(pool, avail_pool)
            elif special_shuffle == 'limited_lw':
                do_limited_shuffle_exclude_drops(pool, avail_pool)
            elif special_shuffle == 'limited_dw':
                do_limited_shuffle_exclude_drops(pool, avail_pool, False)
            elif special_shuffle == 'vanilla':
                do_vanilla_connect(pool, avail_pool)
            elif special_shuffle == 'district':
                drops = []
                world_limiter = LW_Entrances if pool['condition'] == 'lightworld' else DW_Entrances
                entrances = [e for e in pool['entrances'] if e in world_limiter]
                if 'drops' in pool:
                    drops = [e for e in pool['drops'] if combine_linked_drop_map[e] in world_limiter]
                entrances, exits = find_entrances_and_exits(avail_pool, entrances+drops)
                do_main_shuffle(entrances, exits, avail_pool, mode_cfg)
            elif special_shuffle == 'skull':
                handle_skull_woods_entrances(avail_pool, pool['entrances'])
            else:
                entrances, exits = find_entrances_and_exits(avail_pool, pool['entrances'])
                do_main_shuffle(entrances, exits, avail_pool, mode_cfg)
        undefined_behavior = mode_cfg['undefined']
        if undefined_behavior == 'vanilla':
            do_vanilla_connections(avail_pool)
        elif undefined_behavior in ['shuffle', 'swap']:
            do_main_shuffle(set(avail_pool.entrances), set(avail_pool.exits), avail_pool, mode_cfg)
        elif undefined_behavior == 'error':
            assert len(avail_pool.entrances)+len(avail_pool.exits) == 0, 'Not all entrances were placed in their districts'

    # afterward

    # connect houlihan
    if not world.get_entrance('Chris Houlihan Room Exit', player).connected_region:
        lh = 'Big Bomb Shop' if world.is_bombshop_start(player) else 'Links House'
        lh = world.get_region(lh, player).entrances[1].name
        connect_exit('Chris Houlihan Room Exit', lh, avail_pool)

    # check for swamp palace fix
    if (world.get_entrance('Dam', player).connected_region.name != 'Dam'
       or world.get_entrance('Swamp Palace', player).connected_region.name != 'Swamp Portal'):
        world.swamp_patch_required[player] = True

    # check for potion shop location
    if world.get_entrance('Potion Shop', player).connected_region.name != 'Potion Shop':
        world.powder_patch_required[player] = True

    # check for ganon location
    pyramid_hole = 'Inverted Pyramid Hole' if avail_pool.world.is_tile_swapped(0x1b, avail_pool.player) else 'Pyramid Hole'
    if world.get_entrance(pyramid_hole, player).connected_region.name != 'Pyramid':
        world.ganon_at_pyramid[player] = False

    # check for Ganon's Tower location
    gt = 'Agahnims Tower' if avail_pool.world.is_atgt_swapped(avail_pool.player) else 'Ganons Tower'
    if world.get_entrance(gt, player).connected_region.name != 'Ganons Tower Portal':
        world.ganonstower_vanilla[player] = False


def do_vanilla_connections(avail_pool):
    for ent in list(avail_pool.entrances):
        if ent in avail_pool.default_map and avail_pool.default_map[ent] in avail_pool.exits:
            connect_vanilla_two_way(ent, avail_pool.default_map[ent], avail_pool)
        if ent in avail_pool.one_way_map and avail_pool.one_way_map[ent] in avail_pool.exits:
            connect_vanilla(ent, avail_pool.one_way_map[ent], avail_pool)
        if avail_pool.world.is_bombshop_start(avail_pool.player):
            ext = avail_pool.world.get_entrance('Big Bomb Shop Exit', avail_pool.player)
            ext.connect(avail_pool.world.get_region('Big Bomb Shop Area', avail_pool.player))
        if avail_pool.world.is_dark_chapel_start(avail_pool.player):
            ext = avail_pool.world.get_entrance('Dark Sanctuary Hint Exit', avail_pool.player)
            ext.connect(avail_pool.world.get_region('Dark Chapel Area', avail_pool.player))


def do_main_shuffle(entrances, exits, avail, mode_def):
    cross_world = mode_def['cross_world'] == 'on' if 'cross_world' in mode_def else False
    # drops and holes
    do_holes_and_linked_drops(entrances, exits, avail, cross_world)

    if not avail.coupled:
        avail.decoupled_entrances.extend(entrances)
        avail.decoupled_exits.extend(exits)

    if not avail.world.shuffle_ganon[avail.player]:
        if avail.world.is_atgt_swapped(avail.player):
            if 'Agahnims Tower' in entrances:
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

    # inverted sanc
    do_dark_sanc(entrances, exits, avail)

    # links house
    do_links_house(entrances, exits, avail, cross_world)

    # mandatory exits
    rem_entrances, rem_exits = set(), set()
    if not cross_world:
        determine_dungeon_restrictions(avail)
        mand_exits = figure_out_must_exits_same_world(entrances, exits, avail)
        must_exit_lw, must_exit_dw, lw_entrances, dw_entrances, multi_exit_caves = mand_exits
        
        def do_world_mandatory(world_entrances, world_must_exits, restriction):
            nonlocal multi_exit_caves
            candidates = filter_restricted_caves(multi_exit_caves, restriction, avail)
            other_candidates = [x for x in multi_exit_caves if x not in candidates]  # remember those not passed in
            do_mandatory_connections(avail, world_entrances, candidates, world_must_exits)
            multi_exit_caves = (other_candidates + candidates) if other_candidates else candidates  # rebuild list from the candidates and those not passed
        
        if not avail.inverted:
            do_world_mandatory(lw_entrances, must_exit_lw, 'LightWorld')
        else:
            do_world_mandatory(dw_entrances, must_exit_dw, 'DarkWorld')

        new_mec = []
        for cave_option in multi_exit_caves:
            # remove old man house as connector - not valid for dw must_exit if it is a spawn point
            # remove HC exits as connector if sanc is guaranteed in HC
            if any('Old Man House' in cave for cave in cave_option) \
                    or (avail.is_sanc_forced_in_hc() and any('Hyrule Castle' in cave for cave in cave_option)):
                rem_exits.update([item for item in cave_option])
            else:
                new_mec.append(cave_option)
        multi_exit_caves = new_mec

        if not avail.inverted:
            do_world_mandatory(dw_entrances, must_exit_dw, 'DarkWorld')
        else:
            do_world_mandatory(lw_entrances, must_exit_lw, 'LightWorld')
        rem_entrances.update(lw_entrances)
        rem_entrances.update(dw_entrances)
    else:
        # cross world mandatory
        entrance_list = list(entrances)
        if avail.swapped:
            forbidden = [e for e in Forbidden_Swap_Entrances if e in entrance_list]
            entrance_list = [e for e in entrance_list if e not in forbidden]
        must_exit, multi_exit_caves = figure_out_must_exits_cross_world(entrances, exits, avail)
        do_mandatory_connections(avail, entrance_list, multi_exit_caves, must_exit)
        rem_entrances.update(entrance_list)
        if avail.swapped:
            rem_entrances.update(forbidden)

    rem_exits.update([x for item in multi_exit_caves for x in item if x in avail.exits])
    rem_exits.update(exits)
    if avail.swapped:
        rem_exits = [x for x in rem_exits if x in avail.exits]

    # old man cave
    do_old_man_cave_exit(rem_entrances, rem_exits, avail, cross_world)

    # blacksmith
    do_blacksmith(rem_entrances, rem_exits, avail)

    # bomb shop
    if not avail.world.is_bombshop_start(avail.player):
        bomb_shop = 'Big Bomb Shop'
        if bomb_shop in rem_exits:
            bomb_shop_forbidden = []
            if avail.world.logic[avail.player] in ['noglitches', 'minorglitches']:
                bomb_shop_forbidden.append('Pyramid Fairy')
            if avail.world.is_tile_swapped(0x03, avail.player):
                bomb_shop_forbidden.extend(['Spectacle Rock Cave', 'Spectacle Rock Cave (Bottom)'])
            bomb_shop_options = [x for x in rem_entrances if x not in bomb_shop_forbidden]
            if avail.swapped and len(bomb_shop_options) > 1:
                bomb_shop_options = [x for x in bomb_shop_options if x != 'Big Bomb Shop']

            bomb_shop_choice = random.choice(bomb_shop_options)
            connect_entrance(bomb_shop_choice, bomb_shop, avail)
            rem_entrances.remove(bomb_shop_choice)
            if avail.swapped and bomb_shop_choice != 'Big Bomb Shop':
                swap_ent, swap_ext = connect_swap(bomb_shop_choice, bomb_shop, avail)
                rem_exits.remove(swap_ext)
                rem_entrances.remove(swap_ent)
            if not avail.coupled:
                avail.decoupled_exits.remove(bomb_shop)
            rem_exits.remove(bomb_shop)

    # old man S&Q cave
    if not cross_world and not avail.assumed_loose_caves:
        #TODO: Add Swapped ER support for this
        # OM Cave entrance in lw/dw if cross_world off
        if 'Old Man Cave Exit (West)' in rem_exits:
            world_limiter = DW_Entrances if avail.inverted else LW_Entrances
            om_cave_options = sorted([x for x in rem_entrances if x in world_limiter and bonk_fairy_exception(avail, x)])
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
        for ext in om_house:
            if ext in rem_exits:
                world_limiter = DW_Entrances if avail.inverted else LW_Entrances
                om_house_options = [x for x in rem_entrances if x in world_limiter and bonk_fairy_exception(avail, x)]
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
            if bonk_fairy_exception(avail, x):
                lw_entrances.append(x) if x in LW_Entrances else dw_entrances.append(x)
        do_same_world_connectors(lw_entrances, dw_entrances, multi_exit_caves, avail)
        if avail.world.doorShuffle[avail.player] != 'vanilla':
            determine_dungeon_restrictions(avail)
            possibles = figure_out_possible_exits(rem_exits)
            do_same_world_possible_connectors(lw_entrances, dw_entrances, possibles, avail)
        unused_entrances.update(lw_entrances)
        unused_entrances.update(dw_entrances)
    else:
        entrance_list = sorted([x for x in rem_entrances if bonk_fairy_exception(avail, x)])
        do_cross_world_connectors(entrance_list, multi_exit_caves, avail)
        unused_entrances.update(entrance_list)

    if avail.is_standard() and 'Bonk Fairy (Light)' in rem_entrances:
        rem_entrances = list(unused_entrances) + ['Bonk Fairy (Light)']
    else:
        rem_entrances = list(unused_entrances)
    rem_entrances.sort()
    rem_exits = list(rem_exits if avail.coupled else avail.decoupled_exits)
    if avail.swapped:
        rem_exits = [x for x in rem_exits if x in avail.exits]
    rem_exits.sort()
    random.shuffle(rem_entrances)
    random.shuffle(rem_exits)
    placing = min(len(rem_entrances), len(rem_exits))
    if avail.swapped:
        connect_swapped(rem_entrances, rem_exits, avail)
    else:
        for door, target in zip(rem_entrances, rem_exits):
            connect_entrance(door, target, avail)
    rem_entrances[:] = rem_entrances[placing:]
    rem_exits[:] = rem_exits[placing:]
    if rem_entrances or rem_exits:
        logging.getLogger('').warning(f'Unplaced entrances/exits: {", ".join(rem_entrances + rem_exits)}')


def do_old_man_cave_exit(entrances, exits, avail, cross_world):
    if 'Old Man Cave Exit (East)' in exits:
        from OverworldShuffle import build_accessible_region_list
        if not avail.world.is_tile_swapped(0x03, avail.player) or avail.world.shuffle[avail.player] == 'district':
            region_name = 'West Death Mountain (Top)'
        else:
            region_name = 'West Dark Death Mountain (Top)'
        om_cave_options = list(get_accessible_entrances(region_name, avail, [], cross_world, True, True, True, True))
        om_cave_options = [e for e in om_cave_options if e in avail.entrances]
        if avail.swapped:
            om_cave_options = [e for e in om_cave_options if e not in Forbidden_Swap_Entrances]
        assert len(om_cave_options), 'No available entrances left to place Old Man Cave'
        random.shuffle(om_cave_options)
        om_cave_choice = None
        while not om_cave_choice:
            if not len(om_cave_options) and 'Old Man Cave (East)' in entrances:
                om_cave_choice = 'Old Man Cave (East)'
            else:
                om_cave_choice = om_cave_options.pop()
            choice_region = avail.world.get_entrance(om_cave_choice, avail.player).parent_region.name
            if 'West Death Mountain (Bottom)' not in build_accessible_region_list(avail.world, choice_region, avail.player, True, True):
                om_cave_choice = None
        if not avail.coupled:
            connect_exit('Old Man Cave Exit (East)', om_cave_choice, avail)
            avail.decoupled_entrances.remove(om_cave_choice)
        else:
            connect_two_way(om_cave_choice, 'Old Man Cave Exit (East)', avail)
            entrances.remove(om_cave_choice)
            if avail.swapped and om_cave_choice != 'Old Man Cave (East)':
                swap_ent, swap_ext = connect_swap(om_cave_choice, 'Old Man Cave Exit (East)', avail)
                entrances.remove(swap_ent)
                exits.remove(swap_ext)
        exits.remove('Old Man Cave Exit (East)')


def do_blacksmith(entrances, exits, avail):
    if 'Blacksmiths Hut' in exits:
        assumed_inventory = list()
        if avail.world.logic[avail.player] in ['noglitches', 'minorglitches'] and (avail.world.is_tile_swapped(0x29, avail.player) == avail.inverted):
            assumed_inventory.append('Titans Mitts')
        
        blacksmith_options = list()
        if not avail.world.is_bombshop_start(avail.player):
            links_region = avail.world.get_entrance('Links House Exit', avail.player).connected_region
        else:
            links_region = avail.world.get_entrance('Big Bomb Shop Exit', avail.player).connected_region
        if links_region is not None:
            links_region = links_region.name
            blacksmith_options = list(get_accessible_entrances(links_region, avail, assumed_inventory, False, True, True))
        
        if avail.world.is_dark_chapel_start(avail.player):
            dark_sanc = avail.world.get_entrance('Dark Sanctuary Hint Exit', avail.player).connected_region.name
            blacksmith_options = list(OrderedDict.fromkeys(blacksmith_options + list(get_accessible_entrances(dark_sanc, avail, assumed_inventory, False, True, True))))
        elif avail.is_sanc_forced_in_hc():
            sanc_region = avail.world.get_entrance('Sanctuary Exit', avail.player).connected_region
            if sanc_region:
                blacksmith_options = list(OrderedDict.fromkeys(blacksmith_options + list(get_accessible_entrances(sanc_region.name, avail, assumed_inventory, False, True, True))))
            else:
                logging.getLogger('').warning('Blacksmith is unable to use Sanctuary S&Q as initial accessibility because Sanctuary Exit has not been placed yet')
        
        if avail.swapped:
            blacksmith_options = [e for e in blacksmith_options if e not in Forbidden_Swap_Entrances]
        blacksmith_options = [x for x in blacksmith_options if x in entrances]

        if avail.world.shuffle[avail.player] == 'district' and not len(blacksmith_options):
            blacksmith_options = [e for e in entrances if e not in Forbidden_Swap_Entrances or not avail.swapped]

        assert len(blacksmith_options), 'No available entrances left to place Blacksmith'
        blacksmith_choice = random.choice(blacksmith_options)
        connect_entrance(blacksmith_choice, 'Blacksmiths Hut', avail)
        entrances.remove(blacksmith_choice)
        if avail.swapped and blacksmith_choice != 'Blacksmiths Hut':
            swap_ent, swap_ext = connect_swap(blacksmith_choice, 'Blacksmiths Hut', avail)
            entrances.remove(swap_ent)
            exits.remove(swap_ext)
        if not avail.coupled:
            avail.decoupled_exits.remove('Blacksmiths Hut')
        exits.remove('Blacksmiths Hut')


def do_standard_connections(avail):
    std_exits = ['Hyrule Castle Exit (South)', 'Hyrule Castle Secret Entrance Exit']
    if not avail.keep_drops_together:
        random.shuffle(std_exits)
    connect_two_way('Links House', 'Links House Exit', avail)
    connect_entrance('Hyrule Castle Secret Entrance Drop', 'Hyrule Castle Secret Entrance', avail)
    if avail.coupled:
        connect_two_way('Hyrule Castle Entrance (South)', std_exits[0], avail)
        # cannot move uncle cave
        connect_two_way('Hyrule Castle Secret Entrance Stairs', std_exits[1], avail)
    else:
        connect_entrance('Hyrule Castle Entrance (South)', std_exits[0], avail)
        connect_entrance('Hyrule Castle Secret Entrance Stairs', std_exits[1], avail)
        random.shuffle(std_exits)
        connect_exit(std_exits[0], 'Hyrule Castle Entrance (South)', avail)
        connect_exit(std_exits[1], 'Hyrule Castle Secret Entrance Stairs', avail)


def remove_from_list(t_list, removals):
    for r in removals:
        t_list.remove(r)


def do_holes_and_linked_drops(entrances, exits, avail, cross_world):
    holes_to_shuffle = [x for x in entrances if x in drop_map]

    if not avail.world.shuffle_ganon[avail.player]:
        if avail.world.is_tile_swapped(0x1b, avail.player) and 'Inverted Pyramid Hole' in holes_to_shuffle:
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

    if not avail.keep_drops_together:
        targets = [avail.one_way_map[x] for x in holes_to_shuffle]
        if avail.swapped:
            connect_swapped(holes_to_shuffle, targets, avail)
        else:
            connect_random(holes_to_shuffle, targets, avail)
        remove_from_list(entrances, holes_to_shuffle)
        remove_from_list(exits, targets)
        return  # we're done here

    hole_entrances, hole_targets = [], []
    leftover_hole_entrances, leftover_hole_targets = [], []
    for hole in drop_map:
        if hole in avail.original_entrances and hole in linked_drop_map:
            linked_entrance = linked_drop_map[hole]
            if hole in entrances and linked_entrance in entrances:
                hole_entrances.append((linked_entrance, hole))
            target_exit = avail.default_map[linked_entrance]
            target_drop = avail.one_way_map[hole]
            if target_exit in exits and target_drop in exits:
                hole_targets.append((target_exit, target_drop))
        else:
            if hole in avail.original_entrances and hole in entrances:
                leftover_hole_entrances.append(hole)
            if drop_map[hole] in exits:
                leftover_hole_targets.append(drop_map[hole])

    random.shuffle(hole_entrances)
    if not cross_world:
        if 'Sanctuary Grave' in holes_to_shuffle:
            hc = avail.world.get_entrance('Hyrule Castle Exit (South)', avail.player)
            is_hc_in_opp_world = avail.inverted
            if hc.connected_region:
                opp_world = RegionType.LightWorld if avail.inverted else RegionType.DarkWorld
                is_hc_in_opp_world = hc.connected_region.type == opp_world
            start_world_entrances = DW_Entrances if avail.inverted else LW_Entrances
            opp_world_entrances = LW_Entrances if avail.inverted else DW_Entrances
            chosen_entrance = None
            if is_hc_in_opp_world:
                if avail.swapped:
                    chosen_entrance = next(e for e in hole_entrances if e[0] in opp_world_entrances and e[0] != 'Sanctuary')
                if not chosen_entrance:
                    chosen_entrance = next((e for e in hole_entrances if e[0] in opp_world_entrances), None)
            if not chosen_entrance:
                if avail.swapped:
                    chosen_entrance = next(e for e in hole_entrances if e[0] in start_world_entrances and e[0] != 'Sanctuary')
                if not chosen_entrance:
                    chosen_entrance = next(e for e in hole_entrances if e[0] in start_world_entrances)

            if chosen_entrance:
                connect_hole_via_interior(chosen_entrance, 'Sanctuary Exit', hole_entrances, hole_targets, entrances, exits, avail)
                
        sw_world_entrances = DW_Entrances if not avail.world.is_tile_swapped(0x00, avail.player) else LW_Entrances
        if 'Skull Woods First Section Hole (North)' in holes_to_shuffle:
            chosen_entrance = next(e for e in hole_entrances if e[0] in sw_world_entrances)
            connect_hole_via_interior(chosen_entrance, 'Skull Woods First Section Exit', hole_entrances, hole_targets, entrances, exits, avail)
        if 'Skull Woods Second Section Hole' in holes_to_shuffle:
            chosen_entrance = next(e for e in hole_entrances if e[0] in sw_world_entrances)
            connect_hole_via_interior(chosen_entrance, 'Skull Woods Second Section Exit (East)', hole_entrances, hole_targets, entrances, exits, avail)

    random.shuffle(hole_targets)
    while len(hole_entrances):
        entrance, drop = hole_entrances.pop()
        if avail.swapped and len(hole_targets) > 1:
            ext, target = next((x, t) for x, t in hole_targets if x != entrance_map[entrance])
            hole_targets.remove((ext, target))
        else:
            ext, target = hole_targets.pop()
        connect_two_way(entrance, ext, avail)
        connect_entrance(drop, target, avail)
        remove_from_list(entrances, [entrance, drop])
        remove_from_list(exits, [ext, target])
        if avail.swapped and drop_map[drop] != target:
            swap_ent, swap_ext = connect_swap(entrance, ext, avail)
            swap_drop, swap_tgt = connect_swap(drop, target, avail)
            hole_entrances.remove((swap_ent, swap_drop))
            hole_targets.remove((swap_ext, swap_tgt))
            remove_from_list(entrances, [swap_ent, swap_drop])
            remove_from_list(exits, [swap_ext, swap_tgt])

    if leftover_hole_entrances and leftover_hole_targets:
        remove_from_list(entrances, leftover_hole_entrances)
        remove_from_list(exits, leftover_hole_targets)
        if avail.swapped:
            connect_swapped(leftover_hole_entrances, leftover_hole_targets, avail)
        else:
            connect_random(leftover_hole_entrances, leftover_hole_targets, avail)


def connect_hole_via_interior(chosen_entrance, interior, hole_entrances, hole_targets, entrances, exits, avail):
    hole_entrances.remove(chosen_entrance)
    interior = next(target for target in hole_targets if target[0] == interior)
    hole_targets.remove(interior)
    connect_two_way(chosen_entrance[0], interior[0], avail)
    connect_entrance(chosen_entrance[1], interior[1], avail)
    remove_from_list(entrances, [chosen_entrance[0], chosen_entrance[1]])
    remove_from_list(exits, [interior[0], interior[1]])
    if avail.swapped and drop_map[chosen_entrance[1]] != interior[1]:
        swap_ent, swap_ext = connect_swap(chosen_entrance[0], interior[0], avail)
        swap_drop, swap_tgt = connect_swap(chosen_entrance[1], interior[1], avail)
        hole_entrances.remove((swap_ent, swap_drop))
        hole_targets.remove((swap_ext, swap_tgt))
        remove_from_list(entrances, [swap_ent, swap_drop])
        remove_from_list(exits, [swap_ext, swap_tgt])


def do_dark_sanc(entrances, exits, avail):
    if avail.world.is_dark_chapel_start(avail.player):
        ext = avail.world.get_entrance('Dark Sanctuary Hint Exit', avail.player)
        if 'Dark Sanctuary Hint' in exits:
            forbidden = list(Isolated_LH_Doors)
            if not avail.world.is_tile_swapped(0x05, avail.player):
                forbidden.append('Mimic Cave')
            if avail.swapped:
                forbidden.append('Dark Sanctuary Hint')
                forbidden.extend(Forbidden_Swap_Entrances)
                if not avail.world.is_bombshop_start(avail.player):
                    forbidden.append('Links House')
                else:
                    forbidden.append('Big Bomb Shop')
            if avail.world.owLayout[avail.player] == 'vanilla':
                choices = [e for e in avail.world.districts[avail.player]['Northwest Dark World'].entrances if e not in forbidden and e in entrances]
            else:
                choices = [e for e in get_starting_entrances(avail) if e not in forbidden and e in entrances]
            
            choice = random.choice(choices)
            entrances.remove(choice)
            exits.remove('Dark Sanctuary Hint')
            connect_entrance(choice, 'Dark Sanctuary Hint', avail)
            if not avail.coupled:
                avail.decoupled_entrances.remove(choice)
            if avail.swapped and choice != 'Dark Sanctuary Hint':
                swap_ent, swap_ext = connect_swap(choice, 'Dark Sanctuary Hint', avail)
                entrances.remove(swap_ent)
                exits.remove(swap_ext)
        elif not ext.connected_region:
            raise Exception('Dark Sanctuary Hint was placed earlier but its exit not properly connected')


def do_links_house(entrances, exits, avail, cross_world):
    lh_exit = 'Big Bomb Shop' if avail.world.is_bombshop_start(avail.player) else 'Links House Exit'
    if lh_exit in exits:
        links_house_vanilla = 'Big Bomb Shop' if avail.world.is_bombshop_start(avail.player) else 'Links House'
        if not avail.world.shufflelinks[avail.player]:
            links_house = links_house_vanilla
        else:
            entrance_pool = entrances if avail.coupled else avail.decoupled_entrances

            forbidden = list(Isolated_LH_Doors)
            if not avail.world.is_tile_swapped(0x05, avail.player):
                forbidden.append('Mimic Cave')
            if avail.world.is_bombshop_start(avail.player) and (avail.inverted == avail.world.is_tile_swapped(0x03, avail.player)):
                forbidden.extend(['Spectacle Rock Cave', 'Spectacle Rock Cave (Bottom)'])
            if avail.world.is_dark_chapel_start(avail.player) and avail.world.shuffle[avail.player] != 'district':
                dark_sanc_region = avail.world.get_entrance('Dark Sanctuary Hint Exit', avail.player).connected_region.name
                forbidden.extend(get_nearby_entrances(avail, dark_sanc_region))
            else:
                if (avail.world.doorShuffle[avail.player] != 'vanilla' and avail.world.intensity[avail.player] > 2
                        and not avail.world.is_tile_swapped(0x1b, avail.player)):
                    forbidden.append('Hyrule Castle Entrance (South)')
            if avail.swapped:
                forbidden.append(links_house_vanilla)
                forbidden.extend(Forbidden_Swap_Entrances)
            shuffle_mode = avail.world.shuffle[avail.player]
            if avail.world.owLayout[avail.player] == 'vanilla':
                # simple shuffle -
                if shuffle_mode == 'simple':
                    avail.links_on_mountain = True  # taken care of by the logic below
                    if avail.world.is_tile_swapped(0x03, avail.player):  # in inverted, links house cannot be on the mountain
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
                if shuffle_mode == 'restricted' and avail.world.is_tile_swapped(0x03, avail.player):
                    avail.links_on_mountain = True
                    forbidden.extend(['Spike Cave', 'Dark Death Mountain Fairy'])

                if shuffle_mode in ['lite', 'lean']:
                    forbidden.extend(['Spike Cave', 'Mire Shed'])
                    if avail.world.is_tile_swapped(0x05, avail.player):
                        avail.links_on_mountain = True
                        forbidden.extend(['Dark Death Mountain Shop'])
            else:
                avail.links_on_mountain = True
                
            # lobby shuffle means you ought to keep links house in the same world
            sanc_spawn_can_be_dark = (not avail.world.is_dark_chapel_start(avail.player) and avail.world.doorShuffle[avail.player] in ['partitioned', 'crossed']
                                    and avail.world.intensity[avail.player] >= 3)

            if (cross_world and not sanc_spawn_can_be_dark) or avail.world.shuffle[avail.player] == 'district':
                possible = [e for e in entrance_pool if e not in forbidden]
            else:
                world_list = LW_Entrances if not avail.inverted else DW_Entrances
                possible = [e for e in entrance_pool if e in world_list and e not in forbidden]
            possible.sort()
            links_house = random.choice(possible)
        if not avail.world.is_bombshop_start(avail.player):
            connect_two_way(links_house, lh_exit, avail)
        else:
            connect_entrance(links_house, lh_exit, avail)
        entrances.remove(links_house)
        exits.remove(lh_exit)
        if not avail.coupled:
            avail.decoupled_entrances.remove(links_house)
            avail.decoupled_exits.remove(lh_exit)
        if avail.swapped and links_house != links_house_vanilla:
            swap_ent, swap_ext = connect_swap(links_house, lh_exit, avail)
            entrances.remove(swap_ent)
            exits.remove(swap_ext)

        # links on dm
        dm_spots = LH_DM_Connector_List.union(LH_DM_Exit_Forbidden)
        if links_house in dm_spots and avail.world.owLayout[avail.player] == 'vanilla':
            if avail.links_on_mountain:
                return  # connector is fine
            logging.getLogger('').warning(f'Links House is placed in tight area and is now unhandled. Report any errors that occur from here.')
            return
            if avail.world.shuffle[avail.player] in ['lite', 'lean']:
                rem_exits = [e for e in avail.exits if e in Connector_Exit_Set and e not in Dungeon_Exit_Set]
                multi_exit_caves = figure_out_connectors(rem_exits, avail)
                if cross_world:
                    possible_dm_exits = [e for e in avail.entrances if e not in entrances and e in LH_DM_Connector_List]
                    possible_exits = [e for e in avail.entrances if e not in entrances and e not in dm_spots]
                else:
                    world_list = LW_Entrances if not avail.inverted else DW_Entrances
                    possible_dm_exits = [e for e in avail.entrances if e not in entrances and e in LH_DM_Connector_List and e in world_list]
                    possible_exits = [e for e in avail.entrances if e not in entrances and e not in dm_spots and e in world_list]
            else:
                multi_exit_caves = figure_out_connectors(exits, avail)
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
            chosen_exit_start = chosen_cave.pop(0)
            chosen_exit_end = chosen_cave.pop()
            if avail.coupled:
                connect_two_way(chosen_dm_escape, chosen_exit_start, avail)
                connect_two_way(chosen_landing, chosen_exit_end, avail)
                entrances.remove(chosen_dm_escape)
                entrances.remove(chosen_landing)
            else:
                connect_entrance(chosen_dm_escape, chosen_exit_start, avail)
                connect_exit(chosen_exit_end, chosen_landing, avail)
                entrances.remove(chosen_dm_escape)
                avail.decoupled_exits.remove(chosen_exit_start)
                avail.decoupled_entrances.remove(chosen_landing)
                # chosen cave has already been removed from exits
                exits.add(chosen_exit_start)  # this needs to be added back in
            if len(chosen_cave):
                exits.update([x for x in chosen_cave])
            exits.update([x for item in multi_exit_caves for x in item])


def get_starting_entrances(avail, force_starting_world=True):
    from OWEdges import OWTileRegions
    sector = None
    invalid_sectors = list()
    entrances = list()
    while not len(entrances):
        # find largest walkable sector
        while (sector is None):
            sector = max(avail.world.owsectors[avail.player], key=lambda x: len(x) - (0 if x not in invalid_sectors else 1000))
            if not ((avail.world.owCrossed[avail.player] == 'polar' and avail.world.owMixed[avail.player]) or avail.world.owCrossed[avail.player] not in ['none', 'polar']) \
                    and avail.world.get_region(next(iter(next(iter(sector)))), avail.player).type != (RegionType.DarkWorld if avail.inverted else RegionType.LightWorld):
                invalid_sectors.append(sector)
                sector = None
        regions = max(sector, key=lambda x: len(x))
        
        # get entrances from list of regions
        entrances = list()
        for region_name in regions:
            if avail.world.shuffle[avail.player] == 'simple' and region_name in OWTileRegions.keys() and OWTileRegions[region_name] in [0x03, 0x05, 0x07]:
                continue
            region = avail.world.get_region(region_name, avail.player)
            if not force_starting_world or region.type == (RegionType.DarkWorld if avail.inverted else RegionType.LightWorld):
                for exit in region.exits:
                    if not exit.connected_region and exit.spot_type == 'Entrance':
                        entrances.append(exit.name)
        
        invalid_sectors.append(sector)
        sector = None
    
    return entrances


def get_nearby_entrances(avail, start_region):
    from OverworldShuffle import one_way_ledges
    from OWEdges import OWTileRegions

    # get walkable sector in which initial entrance was placed
    regions = next(s for s in avail.world.owsectors[avail.player] if any(start_region in w for w in s))
    regions = next(w for w in regions if start_region in w)
    
    # eliminate regions surrounding the initial entrance until less than half of the candidate regions remain
    explored_regions = list({start_region})
    was_progress = True
    while was_progress and len(explored_regions) < len(regions) / 2:
        was_progress = False
        new_regions = list()
        for region_name in explored_regions:
            if region_name in one_way_ledges:
                for ledge in one_way_ledges[region_name]:
                    if ledge not in explored_regions + new_regions:
                        new_regions.append(ledge)
                        was_progress = True
            region = avail.world.get_region(region_name, avail.player)
            for exit in region.exits:
                if exit.connected_region and region.type == exit.connected_region.type and exit.connected_region.name in regions and exit.connected_region.name not in explored_regions + new_regions:
                    new_regions.append(exit.connected_region.name)
                    was_progress = True
        explored_regions.extend(new_regions)

    # get entrances from remaining regions
    candidates = list()
    for region_name in [r for r in regions if r in explored_regions]:
        if region_name in OWTileRegions.keys() and OWTileRegions[region_name] in [0x03, 0x05, 0x07]:
            continue
        region = avail.world.get_region(region_name, avail.player)
        for exit in region.exits:
            if not exit.connected_region and exit.spot_type == 'Entrance':
                candidates.append(exit.name)
    
    return candidates


def get_accessible_entrances(start_region, avail, assumed_inventory=[], cross_world=False, region_rules=True, exit_rules=True, include_one_ways=False, restrictive_follower=False):
    from Main import copy_world_premature
    from BaseClasses import CollectionState
    from Items import ItemFactory
    from OverworldShuffle import build_accessible_region_list, one_way_ledges
    
    for p in range(1, avail.world.players + 1):
        avail.world.key_logic[p] = {}
    base_world = copy_world_premature(avail.world, avail.player, create_flute_exits=True)
    base_world.override_bomb_check = True
    
    connect_simple(base_world, 'Links House S&Q', start_region, avail.player)
    blank_state = CollectionState(base_world)
    if base_world.mode[avail.player] == 'standard':
        blank_state.collect(ItemFactory('Zelda Delivered', avail.player), True)
    if base_world.logic[avail.player] in ['owglitches', 'hybridglitches', 'nologic']:
        blank_state.collect(ItemFactory('Pegasus Boots', avail.player), True)
    for item in assumed_inventory:
        blank_state.collect(ItemFactory(item, avail.player), True)

    explored_regions = list(build_accessible_region_list(base_world, start_region, avail.player, False, cross_world, region_rules, False, restrictive_follower))

    if include_one_ways:
        new_regions = list()
        for region_name in explored_regions:
            if region_name in one_way_ledges:
                for ledge in one_way_ledges[region_name]:
                    if ledge not in explored_regions + new_regions:
                        new_regions.append(ledge)
        explored_regions.extend(new_regions)
    
    found_entrances = list()
    for region_name in explored_regions:
        region = base_world.get_region(region_name, avail.player)
        for exit in region.exits:
            if exit.spot_type == 'Entrance' and (not exit_rules or exit.access_rule(blank_state)):
                found_entrances.append(exit.name)

    return found_entrances


def figure_out_connectors(exits, avail, cross_world=True):
    multi_exit_caves = []
    cave_list = list(Connector_List)
    if avail.assumed_loose_caves or (not avail.skull_handled and (cross_world or not avail.world.is_tile_swapped(0x00, avail.player))):
        skull_connector = [x for x in ['Skull Woods Second Section Exit (West)', 'Skull Woods Second Section Exit (East)'] if x in exits]
        if len(skull_connector):
            cave_list.extend([skull_connector])
    if avail.assumed_loose_caves or not avail.keep_drops_together:
        cave_list.extend([[entrance_map[e]] for e in linked_drop_map.values() if 'Inverted ' not in e and 'Skull Woods ' not in e])

    for item in cave_list:
        if all(x in exits for x in item):
            remove_from_list(exits, item)
            multi_exit_caves.append(list(item))
        elif avail.assumed_loose_caves and any(x in exits for x in item):
            remaining = [i for i in item if i in exits]
            remove_from_list(exits, remaining)
            multi_exit_caves.append(list(remaining))
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


def must_exits_helper(avail):
    def find_inacessible_ow_regions():
        from DoorShuffle import find_inaccessible_regions
        nonlocal inaccessible_regions
        find_inaccessible_regions(avail.world, avail.player)
        inaccessible_regions = list(avail.world.inaccessible_regions[avail.player])
        
        # find OW regions that don't have a multi-entrance dungeon exit connected
        glitch_regions = ['Central Cliffs', 'Eastern Cliff', 'Desert Northern Cliffs', 'Hyrule Castle Water',
                          'Dark Central Cliffs', 'Darkness Cliff', 'Mire Northern Cliffs', 'Pyramid Water']
        multi_dungeon_exits = {
            'Hyrule Castle South Portal', 'Hyrule Castle West Portal', 'Hyrule Castle East Portal', 'Sanctuary Portal',
            'Desert South Portal', 'Desert West Portal',
            'Skull 2 East Portal', 'Skull 2 West Portal',
            'Turtle Rock Main Portal', 'Turtle Rock Lazy Eyes Portal', 'Turtle Rock Eye Bridge Portal'
        }
        for region_name in avail.world.inaccessible_regions[avail.player]:
            if (avail.world.logic[avail.player] in ['noglitches', 'minorglitches'] and region_name in glitch_regions) \
                    or (region_name == 'Pyramid Exit Ledge' and (avail.keep_drops_together or avail.world.is_tile_swapped(0x1b, avail.player))) \
                    or (region_name == 'Spiral Mimic Ledge Extend' and not avail.world.is_tile_swapped(0x05, avail.player)):
                # removing irrelevant and resolved regions
                inaccessible_regions.remove(region_name)
                continue
            region = avail.world.get_region(region_name, avail.player)
            if region.type not in [RegionType.LightWorld, RegionType.DarkWorld]:
                inaccessible_regions.remove(region_name)
                continue
            if avail.world.shuffle[avail.player] != 'insanity':
                for exit in region.exits:
                    # because dungeon regions haven't been connected yet, the inaccessibility check won't be able to know it's reachable yet
                    if exit.connected_region and exit.connected_region.name in multi_dungeon_exits:
                        resolved_regions.append(region_name)
                        break

    inaccessible_regions = list()
    resolved_regions = list()
    find_inacessible_ow_regions()

    # keep track of neighboring regions for later consolidation
    must_exit_links = OrderedDict()
    for region_name in inaccessible_regions:
        region = avail.world.get_region(region_name, avail.player)
        must_exit_links[region_name] = [x.connected_region.name for x in region.exits if x.connected_region and x.connected_region.name in inaccessible_regions]

    # group neighboring regions together, separated by one-ways
    def consolidate_group(region):
        processed_regions.append(region)
        must_exit_links_copy.pop(region)
        region_group.append(region)
        for dest_region in must_exit_links[region]:
            if region in must_exit_links[dest_region]:
                if dest_region not in processed_regions:
                    consolidate_group(dest_region)
            else:
                one_ways.append(tuple((region, dest_region)))

    processed_regions = list()
    must_exit_candidates = list()
    one_ways = list()
    must_exit_links_copy = must_exit_links.copy()
    while len(must_exit_links_copy):
        region_group = list()
        region_name = next(iter(must_exit_links_copy))
        consolidate_group(region_name)
        must_exit_candidates.append(region_group)

    # get available entrances in each group
    for regions in must_exit_candidates:
        entrances = list()
        for region_name in regions:
            region = avail.world.get_region(region_name, avail.player)
            entrances = entrances + [x.name for x in region.exits if x.spot_type == 'Entrance' and not x.connected_region]
        must_exit_candidates[must_exit_candidates.index(regions)] = tuple((regions, entrances))

    # necessary for circular relations between region groups, it will pick the last group
    # and fill one of those entrances, and we don't want it to bias the same group
    random.shuffle(must_exit_candidates)

    # remove must exit candidates that would be made accessible thru other region groups
    def find_group(region):
        for group in must_exit_candidates:
            regions, _ = group
            if region in regions:
                return group
        raise Exception(f'Could not find region group for {region}')

    def cascade_ignore(group):
        nonlocal ignored_regions, sector_entrances
        regions, entrances = group
        ignored_regions = ignored_regions + regions
        sector_entrances.update(entrances)
        for from_region, to_region in one_ways:
            if from_region in regions:
                if to_region not in ignored_regions:
                    sector_entrances.update(cascade_ignore(find_group(to_region)))
        return sector_entrances
    
    def build_invalid(entrances):
        # building lists of entrances that cannot fulfill must-exit scenarios
        # this ensures must-exits connect to an area outside of this group
        for e in entrances:
            if not Must_Exit_Invalid_Connections[e]:
                Must_Exit_Invalid_Connections[e] = set()
            Must_Exit_Invalid_Connections[e].update(set(entrances))

    def process_group(group):
        nonlocal processed_regions, ignored_regions, sector_entrances
        regions, entrances = group
        must_exit_candidates_copy.remove(group)
        processed_regions = processed_regions + regions
        if regions[0] not in ignored_regions:
            for from_region, to_region in one_ways:
                if to_region in regions and from_region not in ignored_regions + processed_regions:
                    process_group(find_group(from_region)) # process the parent region group
            if regions[0] not in ignored_regions:
                # this is the top level region
                sector_entrances = set()
                if any(r in resolved_regions for r in regions):
                    cascade_ignore(group)
                    build_invalid(sector_entrances)
                else:
                    if len(entrances):
                        # we will fulfill must exit here and cascade access to children
                        if len(entrances) == 1:
                            entrances = entrances[0]
                        else:
                            entrances = tuple(entrances)
                        must_exit_regions.append(tuple((regions, entrances)))
                        cascade_ignore(group)
                        build_invalid(sector_entrances)
                    else:
                        ignored_regions = ignored_regions + regions

    global Must_Exit_Invalid_Connections
    Must_Exit_Invalid_Connections = defaultdict(set)
    processed_regions = list()
    ignored_regions = list()
    sector_entrances = set()
    must_exit_regions = list()
    must_exit_candidates_copy = must_exit_candidates.copy()
    while len(must_exit_candidates_copy):
        region_group = next(iter(must_exit_candidates_copy))
        process_group(region_group)

    # build final must exit lists
    must_exit_lw = list()
    must_exit_dw = list()
    for regions, entrances in must_exit_regions:
        region = avail.world.get_region(regions[0], avail.player)
        if region.type == RegionType.LightWorld:
            must_exit_lw.append(entrances)
        else:
            must_exit_dw.append(entrances)
    return must_exit_lw, must_exit_dw


def figure_out_possible_exits(exits):
    possible_multi_exit_caves = []
    for item in doors_possible_connectors:
        if item in exits:
            remove_from_list(exits, item)
            possible_multi_exit_caves.append(item)
    return possible_multi_exit_caves


def determine_dungeon_restrictions(avail):
    check_for_hc = (avail.is_standard() or avail.world.doorShuffle[avail.player] != 'vanilla')
    for check in dungeon_restriction_checks:
        dungeon_exits, drop_regions = check
        if check_for_hc and any('Hyrule Castle' in x for x in dungeon_exits):
            avail.same_world_restricted.update({x: 'LightWorld' for x in dungeon_exits})
        else:
            restriction = None
            for x in dungeon_exits:
                ent = avail.world.get_entrance(x, avail.player)
                if ent.connected_region:
                    if ent.connected_region.type == RegionType.LightWorld:
                        restriction = 'LightWorld'
                    elif ent.connected_region.type == RegionType.DarkWorld:
                        restriction = 'DarkWorld'
            # Holes only restrict
            for x in drop_regions:
                region = avail.world.get_region(x, avail.player)
                ent = next((ent for ent in region.entrances if ent.parent_region and ent.parent_region.type in [RegionType.LightWorld, RegionType.DarkWorld]), None)
                if ent:
                    if ent.parent_region.type == RegionType.LightWorld and not avail.inverted:
                        restriction = 'LightWorld'
                    elif ent.parent_region.type == RegionType.DarkWorld and avail.inverted:
                        restriction = 'DarkWorld'
            if restriction:
                avail.same_world_restricted.update({x: restriction for x in dungeon_exits})


def figure_out_must_exits_same_world(entrances, exits, avail):
    lw_entrances, dw_entrances = [], []

    for x in entrances:
        lw_entrances.append(x) if x in LW_Entrances else dw_entrances.append(x)
    multi_exit_caves = figure_out_connectors(exits, avail, False)

    must_exit_lw, must_exit_dw = must_exits_helper(avail)
    must_exit_lw = must_exit_filter(avail, must_exit_lw, lw_entrances)
    must_exit_dw = must_exit_filter(avail, must_exit_dw, dw_entrances)

    return must_exit_lw, must_exit_dw, lw_entrances, dw_entrances, multi_exit_caves


def filter_restricted_caves(multi_exit_caves, restriction, avail):
    candidates = []
    for cave in multi_exit_caves:
        if all(x not in avail.same_world_restricted or avail.same_world_restricted[x] == restriction for x in cave):
            candidates.append(cave)
    return candidates


def flatten(list_to_flatten):
    ret = []
    for item in list_to_flatten:
        if isinstance(item, tuple):
            ret.extend(item)
        else:
            ret.append(item)
    return ret


def figure_out_must_exits_cross_world(entrances, exits, avail):
    multi_exit_caves = figure_out_connectors(exits, avail, True)

    must_exit_lw, must_exit_dw = must_exits_helper(avail)
    must_exit = must_exit_filter(avail, must_exit_lw + must_exit_dw, entrances)

    return must_exit, multi_exit_caves


def do_same_world_connectors(lw_entrances, dw_entrances, caves, avail):
    random.shuffle(lw_entrances)
    random.shuffle(dw_entrances)
    random.shuffle(caves)
    while caves:
        # connect highest-exit-count caves first, prevent issue where we have 2 or 3 exits across worlds left to fill
        cave_candidate = (None, 0)
        for i, cave in enumerate(caves):
            if isinstance(cave, str):
                cave = (cave,)
            if len(cave) > cave_candidate[1]:
                cave_candidate = (i, len(cave))
        cave = caves.pop(cave_candidate[0])

        if isinstance(cave, str):
            cave = (cave,)
        target, restriction = None, None
        if any(x in avail.same_world_restricted for x in cave):
            restriction = next(avail.same_world_restricted[x] for x in cave if x in avail.same_world_restricted)
            target = lw_entrances if restriction == 'LightWorld' else dw_entrances
        if target is None:
            target = lw_entrances if random.randint(0, 1) == 0 else dw_entrances

        # check if we can still fit the cave into our target group
        if len(target) < len(cave):
            if restriction:
                raise Exception('Not enough entrances for restricted cave, algorithm needs revision (main)')
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


def do_same_world_possible_connectors(lw_entrances, dw_entrances, possibles, avail):
    random.shuffle(possibles)
    while possibles:
        possible = possibles.pop()
        target = None
        if possible in avail.same_world_restricted:
            target = lw_entrances if avail.same_world_restricted[possible] == 'LightWorld' else dw_entrances
        if target is None:
            target = lw_entrances if random.randint(0, 1) == 0 else dw_entrances
        connect_two_way(target.pop(), possible, avail)
        determine_dungeon_restrictions(avail)

def do_cross_world_connectors(entrances, caves, avail):
    random.shuffle(entrances)
    random.shuffle(caves)
    while caves:
        cave_candidate = (None, 0)
        for i, cave in enumerate(caves):
            if isinstance(cave, str):
                cave = [cave]
            if len(cave) > cave_candidate[1]:
                cave_candidate = (i, len(cave))
        cave = caves.pop(cave_candidate[0])

        if isinstance(cave, str):
            cave = [cave]

        while len(cave):
            ext = cave.pop()
            if not avail.coupled:
                choice = random.choice(avail.decoupled_entrances)
                connect_exit(ext, choice, avail)
                avail.decoupled_entrances.remove(choice)
            else:
                if avail.swapped and len(entrances) > 1:
                    chosen_entrance = next(e for e in entrances if avail.combine_map[e] != ext)
                    entrances.remove(chosen_entrance)
                else:
                    chosen_entrance = entrances.pop()
                connect_two_way(chosen_entrance, ext, avail)
                if avail.swapped:
                    swap_ent, swap_ext = connect_swap(chosen_entrance, ext, avail)
                    if swap_ent:
                        entrances.remove(swap_ent)
                        if chosen_entrance not in single_entrance_map:
                            if swap_ext in cave:
                                cave.remove(swap_ext)
                            else:
                                for c in caves:
                                    if swap_ext == c:
                                        caves.remove(swap_ext)
                                        break
                                    if not isinstance(c, str) and swap_ext in c:
                                        c.remove(swap_ext)
                                        if len(c) == 0:
                                            caves.remove(c)
                                        break


def handle_skull_woods_drops(avail, pool, mode_cfg):
    skull_woods = avail.world.skullwoods[avail.player]
    if skull_woods in ['restricted', 'loose']:
        for drop in pool:
            target = drop_map[drop]
            connect_entrance(drop, target, avail)
    elif skull_woods == 'original':
        holes, targets = find_entrances_and_targets_drops(avail, pool)
        if avail.swapped:
            connect_swapped(holes, targets, avail)
        else:
            connect_random(holes, targets, avail)
    elif skull_woods == 'followlinked':
        keep_together = mode_cfg['keep_drops_together'] == 'on' if 'keep_drops_together' in mode_cfg else True
        if keep_together:
            for drop in ['Skull Woods First Section Hole (East)', 'Skull Woods First Section Hole (West)']:
                if drop in avail.entrances:
                    target = drop_map[drop]
                    connect_entrance(drop, target, avail)


def handle_skull_woods_entrances(avail, pool):
    skull_woods = avail.world.skullwoods[avail.player]
    if skull_woods in ['restricted', 'original']:
        entrances, exits = find_entrances_and_exits(avail, pool)
        if avail.world.shuffle[avail.player] in ['dungeonssimple', 'simple', 'restricted'] \
                and not avail.world.is_tile_swapped(0x00, avail.player):
            rem_ent = random.choice(['Skull Woods First Section Door', 'Skull Woods Second Section Door (East)'])
            entrances.remove(rem_ent)
            exits.remove('Skull Woods First Section Exit')
            connect_random(entrances, exits, avail, True)
            entrances, exits = [rem_ent], ['Skull Woods First Section Exit']
        if avail.swapped:
            connect_swapped(entrances, exits, avail, True)
        else:
            connect_random(entrances, exits, avail, True)
        avail.skull_handled = True


def do_fixed_shuffle(avail, entrance_list):
    max_size = 0
    options = {}
    for i, entrance_set in enumerate(entrance_list):
        entrances, targets = find_entrances_and_exits(avail, entrance_set)
        size = min(len(entrances), len(targets))
        max_size = max(max_size, size)
        rules = Restrictions()
        rules.size = size
        if ('Hyrule Castle Entrance (South)' in entrances and avail.is_sanc_forced_in_hc()):
            rules.must_exit_to_lw = True
        if (avail.world.is_atgt_swapped(avail.player) and 'Agahnims Tower' in entrances and
           not avail.world.shuffle_ganon[avail.player]):
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
            lw_exits = set()
            for e, x in avail.combine_map.items():
                if x in avail.exits:
                    region = avail.world.get_entrance(e, avail.player).parent_region
                    if region.type == RegionType.LightWorld:
                        new_x = x
                        if avail.world.is_atgt_swapped(avail.player):
                            if x == 'Ganons Tower Exit':
                                new_x = 'Agahnims Tower Exit'
                            elif x == 'Agahnims Tower Exit':
                                new_x = 'Ganons Tower Exit'
                        if avail.world.is_bombshop_start(avail.player):
                            if x == 'Links House Exit':
                                new_x = 'Big Bomb Shop'
                            elif x == 'Big Bomb Shop':
                                new_x = 'Links House Exit'
                        lw_exits.add(new_x)
            filtered_choices = {i: opt for i, opt in choices.items() if all(t in lw_exits for t in opt[2])}
            _, choice = random.choice(list(filtered_choices.items()))
        else:
            _, choice = random.choice(list(choices.items()))
        del choices[choice[0]]
        for t, entrance in enumerate(entrances):
            target = choice[2][t]
            connect_two_way(entrance, target, avail)


def do_same_world_shuffle(avail, pool_def):
    single_exit = pool_def['entrances']
    multi_exit = pool_def['connectors']
    # complete_entrance_set = set()
    lw_entrances, dw_entrances, multi_exits_caves, other_exits = [], [], [], []

    single_entrances, single_exits = find_entrances_and_exits(avail, single_exit)
    other_exits.extend(single_exits)
    for x in single_entrances:
        (dw_entrances, lw_entrances)[x in LW_Entrances].append(x)
    # complete_entrance_set.update(single_entrances)
    for option in multi_exit:
        multi_entrances, multi_exits = find_entrances_and_exits(avail, option)
        # complete_entrance_set.update(multi_entrances)
        if multi_exits:
            multi_exits_caves.append(multi_exits)
        for x in multi_entrances:
            (dw_entrances, lw_entrances)[x in LW_Entrances].append(x)

    must_exit_lw, must_exit_dw = must_exits_helper(avail)
    must_exit_lw = must_exit_filter(avail, must_exit_lw, lw_entrances)
    must_exit_dw = must_exit_filter(avail, must_exit_dw, dw_entrances)

    def do_world_mandatory(world_entrances, world_must_exits, restriction):
        nonlocal multi_exits_caves
        candidates = filter_restricted_caves(multi_exits_caves, restriction, avail)
        other_candidates = [x for x in multi_exits_caves if x not in candidates]  # remember those not passed in
        do_mandatory_connections(avail, world_entrances, candidates, world_must_exits)
        multi_exits_caves = (other_candidates + candidates) if other_candidates else candidates  # rebuild list from the candidates and those not passed

    determine_dungeon_restrictions(avail)
    do_world_mandatory(lw_entrances, must_exit_lw, 'LightWorld')
    do_world_mandatory(dw_entrances, must_exit_dw, 'DarkWorld')

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

        target, restriction = None, None
        if any(x in avail.same_world_restricted for x in cave):
            restriction = next(avail.same_world_restricted[x] for x in cave if x in avail.same_world_restricted)
            target = lw_entrances if restriction == 'LightWorld' else dw_entrances
        if target is None:
            target = lw_entrances if random.randint(0, 1) == 0 else dw_entrances
        if len(target) < len(cave):  # swap because we ran out of entrances in that world
            if restriction:
                raise Exception('Not enough entrances for restricted cave, algorithm needs revision (dungeonsfull)')
            target = lw_entrances if target is dw_entrances else dw_entrances

        for ext in cave:
            connect_two_way(target.pop(), ext, avail)
    # finish the rest
    connect_random(lw_entrances+dw_entrances, single_exits, avail, True)


def do_connector_shuffle(avail, pool_def):
    directional_list = pool_def['directional']
    connector_list = pool_def['connectors']
    option_list = pool_def['options']

    for connector in directional_list:
        chosen_option = random.choice(option_list)
        _, chosen_exits = find_entrances_and_exits(avail, chosen_option)
        if not chosen_exits:
            continue  # nothing available
        # this shuffle ensures directionality
        shuffle_connector_exits(chosen_exits)
        connector_ent, _ = find_entrances_and_exits(avail, connector)
        for i, ent in enumerate(connector_ent):
            connect_two_way(ent, chosen_exits[i], avail)
        option_list.remove(chosen_option)

    for connector in connector_list:
        chosen_option = random.choice(option_list)
        _, chosen_exits = find_entrances_and_exits(avail, chosen_option)
        # directionality need not be preserved
        random.shuffle(chosen_exits)
        connector_ent, _ = find_entrances_and_exits(avail, connector)
        for i, ent in enumerate(connector_ent):
            connect_two_way(ent, chosen_exits[i], avail)
        option_list.remove(chosen_option)


def do_limited_shuffle(pool_def, avail):
    entrance_pool, _ = find_entrances_and_exits(avail, pool_def['entrances'])
    exit_pool = [x for x in pool_def['options'] if x in avail.exits]
    random.shuffle(exit_pool)
    for entrance in entrance_pool:
        chosen_exit = exit_pool.pop()
        connect_two_way(entrance, chosen_exit, avail)


def do_limited_shuffle_exclude_drops(pool_def, avail, lw=True):
    if avail.inverted:
        lw = not lw
    _, exits = find_entrances_and_exits(avail, pool_def['entrances'])
    reserved_drops = set(linked_drop_map.values())
    must_exit_lw, must_exit_dw = must_exits_helper(avail)
    must_exit_lw = must_exit_filter(avail, must_exit_lw, LW_Entrances)
    must_exit_dw = must_exit_filter(avail, must_exit_dw, DW_Entrances)
    must_exit = set(must_exit_lw if lw else must_exit_dw)
    base_set = LW_Entrances if lw else DW_Entrances
    entrance_pool = [x for x in base_set if x in avail.entrances and x not in reserved_drops]
    if not avail.world.shuffle_ganon[avail.player]:
        if avail.world.is_atgt_swapped(avail.player):
            if 'Agahnims Tower' in entrance_pool:
                connect_two_way('Agahnims Tower', 'Ganons Tower Exit', avail)
                entrance_pool.remove('Agahnims Tower')
                exits.remove('Ganons Tower Exit')
                if not avail.coupled:
                    avail.decoupled_entrances.remove('Agahnims Tower')
                    avail.decoupled_exits.remove('Ganons Tower Exit')
        elif 'Ganons Tower' in entrance_pool:
            connect_two_way('Ganons Tower', 'Ganons Tower Exit', avail)
            entrance_pool.remove('Ganons Tower')
            exits.remove('Ganons Tower Exit')
            if not avail.coupled:
                avail.decoupled_entrances.remove('Ganons Tower')
                avail.decoupled_exits.remove('Ganons Tower Exit')
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
    if 'shopsanity' in pool_def['condition']:
        if avail.world.shopsanity[avail.player]:
            return
    if 'pottery' in pool_def['condition']:  # this condition involves whether caves with pots are shuffled or not
        if avail.world.pottery[avail.player] not in ['none', 'keys', 'dungeon']:
            return
    if 'takeany' in pool_def['condition']:
        if avail.world.take_any[avail.player] == 'fixed':
            return
    if 'bonk' in pool_def['condition']:
        if avail.world.shuffle_bonk_drops[avail.player]:
            return
    if 'dropshuffle' in pool_def['condition']:
        if avail.world.dropshuffle[avail.player] not in ['none', 'keys']:
            return
    if 'enemy_drop' in pool_def['condition']:
        if avail.world.dropshuffle[avail.player] not in ['none', 'keys'] and avail.world.enemy_shuffle[avail.player] != 'none':
            return
    defaults = {**default_connections, **(inverted_default_connections if avail.inverted != avail.world.is_tile_swapped(0x1b, avail.player) else open_default_connections)}
    for entrance in pool_def['entrances']:
        if entrance in avail.entrances:
            target = defaults[entrance]
            if entrance in avail.default_map:
                connect_vanilla_two_way(entrance, avail.default_map[entrance], avail)
            else:
                connect_simple(avail.world, entrance, target, avail.player)
                avail.entrances.remove(entrance)
                avail.exits.remove(target)

def bonk_fairy_exception(avail, x):  # (Bonk Fairy not eligible in standard)
    return not avail.is_standard() or x != 'Bonk Fairy (Light)'

def do_mandatory_connections(avail, entrances, cave_options, must_exit):
    if len(must_exit) == 0:
        return
    if not avail.coupled:
        do_mandatory_connections_decoupled(avail, cave_options, must_exit)
        return

    invalid_connections = Must_Exit_Invalid_Connections.copy()
    invalid_cave_connections = defaultdict(set)

    if avail.world.logic[avail.player] in ['owglitches', 'hybridglitches', 'nologic']:
        import OverworldGlitchRules
        for entrance in OverworldGlitchRules.get_non_mandatory_exits(avail.world, avail.player):
            invalid_connections[entrance] = set()
            if entrance in must_exit:
                must_exit.remove(entrance)
                if entrance not in entrances:
                    entrances.append(entrance)
    if avail.swapped:
        swap_forbidden = [e for e in entrances if avail.combine_map[e] in must_exit]
        for e in swap_forbidden:
            entrances.remove(e)
    entrances.sort()  # sort these for consistency
    random.shuffle(entrances)
    random.shuffle(cave_options)

    if avail.world.is_tile_swapped(0x1b, avail.player):
        for entrance in invalid_connections:
            region = avail.world.get_entrance(entrance, avail.player).connected_region
            if region and region.name == 'Agahnims Tower Portal':
                for ext in invalid_connections[entrance]:
                    invalid_connections[ext] = invalid_connections[ext].union({'Agahnims Tower', 'Hyrule Castle Entrance (West)', 'Hyrule Castle Entrance (East)'})
                break

    def connect_cave_swap(entrance, exit, current_cave):
        swap_entrance, swap_exit = connect_swap(entrance, exit, avail)
        if swap_entrance and entrance not in single_entrance_map:
            for option in cave_options:
                if swap_exit in option and option == current_cave:
                    x=0
                if swap_exit in option and option != current_cave:
                    option.remove(swap_exit)
                    if len(option) == 0:
                        cave_options.remove(option)
                    break
        return swap_entrance, swap_exit

    used_caves = []
    required_entrances = 0  # Number of entrances reserved for used_caves
    while must_exit:
        exit = must_exit.pop()
        # find multi exit cave
        candidates = []
        for candidate in cave_options:
            allow_single = avail.assumed_loose_caves or len(candidate) > 1
            if not isinstance(candidate, str) and allow_single and (candidate in used_caves
                                                   or len(candidate) < len(entrances) - required_entrances):
                if not avail.swapped or (avail.combine_map[exit] not in candidate and not any(e for e in must_exit if avail.combine_map[e] in candidate)): #maybe someday allow these, but we need to disallow mutual locks in Swapped
                    candidates.append(candidate)
        cave = random.choice(candidates)

        if avail.swapped and len(candidates) > 1 and not avail.world.is_tile_swapped(0x03, avail.player):
            DM_Connector_Prefixes = ['Spectacle Rock Cave', 'Old Man House', 'Death Mountain Return']
            if any(p for p in DM_Connector_Prefixes if p in cave[0]):  # if chosen cave is a DM connector
                remain = [p for p in DM_Connector_Prefixes if len([e for e in entrances if p in e]) > 0]  # gets remaining DM caves left in pool
                if len(remain) == 1:  # guarantee that old man rescue cave can still be placed
                    candidates.remove(cave)
                    cave = random.choice(candidates)

        if cave is None:
            raise RuntimeError('No more caves left. Should not happen!')

        # all caves are sorted so that the last exit is always reachable
        rnd_cave = list(cave)
        shuffle_connector_exits(rnd_cave)  # should be the same as unbiasing some entrances...
        if avail.swapped and exit in swap_forbidden:
            swap_forbidden.remove(exit)
        else:
            entrances.remove(exit)
        connect_two_way(exit, rnd_cave[-1], avail)
        if avail.swapped:
            swap_ent, _ = connect_cave_swap(exit, rnd_cave[-1], cave)
            entrances.remove(swap_ent)
        if len(cave) == 2:
            entrance = next(e for e in entrances[::-1] if e not in invalid_connections[exit]
                            and e not in invalid_cave_connections[tuple(cave)] and e not in must_exit
                            and (not avail.swapped or rnd_cave[0] != avail.combine_map[e])
                            and bonk_fairy_exception(avail, e))
            entrances.remove(entrance)
            connect_two_way(entrance, rnd_cave[0], avail)
            if avail.swapped and avail.combine_map[entrance] != rnd_cave[0]:
                swap_ent, _ = connect_cave_swap(entrance, rnd_cave[0], cave)
                entrances.remove(swap_ent)
            if cave in used_caves:
                required_entrances -= 2
                used_caves.remove(cave)
            if entrance in invalid_connections:
                for exit2 in invalid_connections[entrance]:
                    invalid_connections[exit2] = invalid_connections[exit2].union(invalid_connections[exit]).union(invalid_cave_connections[tuple(cave)])
        elif len(cave) == 1 and avail.assumed_loose_caves:
            #TODO: keep track of caves we use for must exits that are unaccounted here
            # the other exits of the cave should NOT be used to satisfy must-exit later
            pass
        elif cave[-1] == 'Spectacle Rock Cave Exit':  # Spectacle rock only has one exit
            cave_entrances = []
            for cave_exit in rnd_cave[:-1]:
                if avail.swapped and cave_exit not in avail.exits:
                    entrance = avail.world.get_entrance(cave_exit, avail.player)
                    entrance = next((e for e in entrance.parent_region.entrances if e.parent_region.type in [RegionType.LightWorld, RegionType.DarkWorld])).name
                    cave_entrances.append(entrance)
                else:
                    entrance = next(e for e in entrances[::-1] if e not in invalid_connections[exit] and e not in must_exit
                                    and (not avail.swapped or cave_exit != avail.combine_map[e]) and bonk_fairy_exception(avail, e))
                    cave_entrances.append(entrance)
                    entrances.remove(entrance)
                    connect_two_way(entrance, cave_exit, avail)
                    if avail.swapped and avail.combine_map[entrance] != cave_exit:
                        swap_ent, _ = connect_cave_swap(entrance, cave_exit, cave)
                        entrances.remove(swap_ent)
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
                if avail.swapped and cave_exit not in avail.exits:
                    continue
                else:
                    entrance = next(e for e in entrances[::-1] if e not in invalid_cave_connections[tuple(cave)]
                                    and (not avail.swapped or cave_exit != avail.combine_map[e]) and bonk_fairy_exception(avail, e))
                    invalid_cave_connections[tuple(cave)] = set()
                    entrances.remove(entrance)
                    connect_two_way(entrance, cave_exit, avail)
                    if avail.swapped and avail.combine_map[entrance] != cave_exit:
                        swap_ent, _ = connect_cave_swap(entrance, cave_exit, cave)
                        entrances.remove(swap_ent)
            cave_options.remove(cave)
    if avail.swapped:
        entrances.extend(swap_forbidden)


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
        if item in avail_pool.default_map and avail_pool.default_map[item] in avail_pool.exits:
            targets.append(avail_pool.default_map[item])
        elif item in avail_pool.one_way_map and avail_pool.one_way_map[item] in avail_pool.exits:
            targets.append(avail_pool.one_way_map[item])
    return entrances, targets


inverted_sub_table = {
    'Pyramid Hole': 'Inverted Pyramid Hole',
    'Pyramid Entrance': 'Inverted Pyramid Entrance'
}

inverted_exit_sub_table = { }


def inverted_substitution(avail_pool, collection, is_entrance, is_set=False):
    if avail_pool.world.is_tile_swapped(0x1b, avail_pool.player):
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


def connect_swapped(entrancelist, targetlist, avail, two_way=False):
    random.shuffle(entrancelist)
    sorted_targets = list()
    for ent in entrancelist:
        if ent in avail.combine_map:
            if avail.combine_map[ent] not in targetlist:
                logging.getLogger('').error(f'{avail.combine_map[ent]} not in target list, cannot swap entrance')
                raise Exception(f'{avail.combine_map[ent]} not in target list, cannot swap entrance')
            sorted_targets.append(avail.combine_map[ent])
    if len(sorted_targets):
        targetlist = list(sorted_targets)
    else:
        targetlist = list(targetlist)
    indexlist = list(range(len(targetlist)))
    random.shuffle(indexlist)

    while len(indexlist) > 1:
        index1 = indexlist.pop()
        index2 = indexlist.pop()
        targetlist[index1], targetlist[index2] = targetlist[index2], targetlist[index1]

    for exit, target in zip(entrancelist, targetlist):
        if two_way:
            connect_two_way(exit, target, avail)
        else:
            connect_entrance(exit, target, avail)


def connect_swap(entrance, exit, avail):
    swap_exit = avail.combine_map[entrance]
    if swap_exit != exit:
        swap_entrance = next(e for e, x in avail.combine_map.items() if x == exit)
        if swap_entrance in ['Pyramid Entrance', 'Pyramid Hole'] and avail.world.is_tile_swapped(0x1b, avail.player):
            swap_entrance = 'Inverted ' + swap_entrance
        if swap_exit in entrance_map.values():
            connect_two_way(swap_entrance, swap_exit, avail)
        else:
            connect_entrance(swap_entrance, swap_exit, avail)
        return swap_entrance, swap_exit
    return None, None


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
    if exit_name == 'Big Bomb Shop' and avail.world.is_bombshop_start(avail.player):
        ext = avail.world.get_entrance('Big Bomb Shop Exit', avail.player)
        ext.connect(avail.world.get_entrance(entrancename, avail.player).parent_region)
    if exit_name == 'Dark Sanctuary Hint' and avail.world.is_dark_chapel_start(avail.player):
        ext = avail.world.get_entrance('Dark Sanctuary Hint Exit', avail.player)
        ext.connect(avail.world.get_entrance(entrancename, avail.player).parent_region)
    world.spoiler.set_entrance(entrance.name, exit.name if exit is not None else region.name, 'entrance', player)
    logging.getLogger('').debug(f'Connected (entr) {entrance.name} to {exit.name if exit is not None else region.name}')


def connect_exit(exit_name, entrancename, avail):
    world, player = avail.world, avail.player
    entrance = world.get_entrance(entrancename, player)
    exit = world.get_entrance(exit_name, player)

    # if this was already connected somewhere, remove the backreference
    if exit.connected_region is not None:
        exit.connected_region.entrances.remove(exit)

    dest_region = entrance.parent_region
    if dest_region.name in ['Pyramid Crack', 'GT Stairs']:
        # Needs to logically exit into greater OW area
        dest_region = entrance.parent_region.entrances[0].parent_region

    exit.connect(dest_region, door_addresses[entrance.name][1], exit_ids[exit.name][1])
    if exit_name != 'Chris Houlihan Room Exit':
        if avail.coupled:
            avail.entrances.remove(entrancename)
        avail.exits.remove(exit_name)
    world.spoiler.set_entrance(entrance.name, exit.name, 'exit', player)
    logging.getLogger('').debug(f'Connected (exit) {exit.name} to {entrance.name}')


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
            'skull_layout': {
                'special': 'vanilla',
                'condition': '',
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
                              'Ganons Tower', 'Desert Palace Entrance (North)', 'Dark Death Mountain Ledge (East)'],
                'connectors': [['Hyrule Castle Entrance (South)', 'Hyrule Castle Entrance (East)',
                                'Hyrule Castle Entrance (West)'],
                               ['Desert Palace Entrance (South)', 'Desert Palace Entrance (East)',
                                'Desert Palace Entrance (West)'],
                               ['Turtle Rock', 'Turtle Rock Isolated Ledge Entrance',
                                'Dark Death Mountain Ledge (West)'],
                               ['Skull Woods Second Section Door (East)', 'Skull Woods Second Section Door (West)',
                                'Skull Woods First Section Door']]
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
            'drops': {
                'special': 'normal_drops',
                'entrances': ['Hyrule Castle Secret Entrance Drop', 'Kakariko Well Drop', 'Bat Cave Drop',
                              'North Fairy Cave Drop', 'Lost Woods Hideout Drop', 'Lumberjack Tree Tree',
                              'Sanctuary Grave', 'Pyramid Hole',
                              'Skull Woods First Section Hole (North)', 'Skull Woods Second Section Hole']
            },
            'fixed_non_items': {
                'special': 'vanilla',
                'condition': '',
                'entrances': ['Mire Fairy', 'Archery Game', 'Fortune Teller (Dark)', 'Dark Sanctuary Hint',
                              'Dark Lake Hylia Ledge Hint', 'Dark Lake Hylia Fairy', 'East Dark World Hint',
                              'Kakariko Gamble Game', 'Bush Covered House', 'Fortune Teller (Light)',
                              'Lost Woods Gamble', 'Lake Hylia Fortune Teller', 'Lake Hylia Fairy'],
            },
            'fixed_shops': {
                'special': 'vanilla',
                'condition': 'shopsanity',
                'entrances': ['Dark Death Mountain Shop', 'Dark Potion Shop', 'Dark Lumberjack Shop', 'Dark World Shop',
                              'Red Shield Shop', 'Kakariko Shop', 'Lake Hylia Shop', 'Dark Lake Hylia Shop'],
            },
            'fixed_takeanys': {
                'special': 'vanilla',
                'condition': 'takeany',
                'entrances': ['Desert Fairy', 'Light Hype Fairy', 'Dark Death Mountain Fairy', 'Dark Lake Hylia Ledge Fairy'],
            },
            'fixed_takeanys_enemy_drops_fairies': {
                'special': 'vanilla',
                'condition': ['takeany', 'enemy_drop'],
                'entrances': ['Bonk Fairy (Dark)'],
            },
            'fixed_pottery': {
                'special': 'vanilla',
                'condition': 'pottery',
                'entrances': ['Lumberjack House', 'Snitch Lady (West)', 'Snitch Lady (East)', 'Tavern (Front)',
                              '20 Rupee Cave', '50 Rupee Cave', 'Palace of Darkness Hint',
                              'Dark Lake Hylia Ledge Spike Cave', 'Mire Hint']
            },
            'fixed_enemy_drops_fairies': {
                'special': 'vanilla',
                'condition': 'enemy_drop',
                'entrances': ['Long Fairy Cave', 'Bonk Fairy (Light)']
            },
            'fixed_pots_n_bones_fairies': {
                'special': 'vanilla',
                'condition': ['pottery', 'enemy_drop'],
                'entrances': ['Hookshot Fairy']
            },
            'fixed_pots_n_bones': {
                'special': 'vanilla',
                'condition': ['pottery', 'dropshuffle'],
                'entrances': ['Light World Bomb Hut']
            },
            'fixed_shop_n_bones': {
                'special': 'vanilla',
                'condition': ['shopsanity', 'enemy_drop'],
                'entrances': ['Capacity Upgrade']
            },
            'fixed_bonk': {
                'special': 'vanilla',
                'condition': ['enemy_drop', 'bonk'],
                'entrances': ['Good Bee Cave']
            },
            'item_caves': {  # shuffles shops/pottery if they weren't fixed in the last steps
                'entrances': ['Mimic Cave', 'Spike Cave', 'Mire Shed', 'Hammer Peg Cave', 'Chest Game',
                              'C-Shaped House', 'Brewery', 'Hype Cave', 'Big Bomb Shop', 'Pyramid Fairy',
                              'Ice Rod Cave', 'Dam', 'Bonk Rock Cave', 'Library', 'Potion Shop', 'Mini Moldorm Cave',
                              'Checkerboard Cave', 'Graveyard Cave', 'Cave 45', 'Sick Kids House', 'Blacksmiths Hut',
                              'Sahasrahlas Hut', 'Aginahs Cave', 'Chicken House', 'Kings Grave', 'Blinds Hideout',
                              'Waterfall of Wishing', 'Dark Death Mountain Shop', 'Dark Lake Hylia Shop',
                              'Dark Potion Shop', 'Dark Lumberjack Shop', 'Dark World Shop',
                              'Red Shield Shop', 'Kakariko Shop', 'Capacity Upgrade', 'Lake Hylia Shop',
                              'Lumberjack House', 'Snitch Lady (West)', 'Snitch Lady (East)', 'Tavern (Front)',
                              'Light World Bomb Hut', '20 Rupee Cave', '50 Rupee Cave', 'Hookshot Fairy',
                              'Palace of Darkness Hint', 'Dark Lake Hylia Ledge Spike Cave', 'Desert Fairy',
                              'Light Hype Fairy', 'Dark Death Mountain Fairy', 'Dark Lake Hylia Ledge Fairy',
                              'Bonk Fairy (Dark)', 'Good Bee Cave', 'Long Fairy Cave', 'Bonk Fairy (Light)',
                              'Mire Hint', 'Links House', 'Tavern North']
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
            'drops': {
                'special': 'normal_drops',
                'entrances': ['Hyrule Castle Secret Entrance Drop', 'Kakariko Well Drop', 'Bat Cave Drop',
                              'North Fairy Cave Drop', 'Lost Woods Hideout Drop', 'Lumberjack Tree Tree',
                              'Sanctuary Grave', 'Pyramid Hole',
                              'Skull Woods First Section Hole (North)', 'Skull Woods Second Section Hole']
            },
            'fixed_non_items': {
                'special': 'vanilla',
                'condition': '',
                'entrances': ['Mire Fairy', 'Archery Game', 'Fortune Teller (Dark)', 'Dark Sanctuary Hint',
                              'Dark Lake Hylia Ledge Hint', 'Dark Lake Hylia Fairy', 'East Dark World Hint',
                              'Kakariko Gamble Game', 'Bush Covered House', 'Fortune Teller (Light)',
                              'Lost Woods Gamble', 'Lake Hylia Fortune Teller', 'Lake Hylia Fairy'],
            },
            'fixed_shops': {
                'special': 'vanilla',
                'condition': 'shopsanity',
                'entrances': ['Dark Death Mountain Shop', 'Dark Potion Shop', 'Dark Lumberjack Shop', 'Dark World Shop',
                              'Red Shield Shop', 'Kakariko Shop', 'Lake Hylia Shop', 'Dark Lake Hylia Shop'],
            },
            'fixed_takeanys': {
                'special': 'vanilla',
                'condition': 'takeany',
                'entrances': ['Desert Fairy', 'Light Hype Fairy', 'Dark Death Mountain Fairy', 'Dark Lake Hylia Ledge Fairy'],
            },
            'fixed_takeanys_enemy_drops_fairies': {
                'special': 'vanilla',
                'condition': ['takeany', 'enemy_drop'],
                'entrances': ['Bonk Fairy (Dark)'],
            },
            'fixed_pottery': {
                'special': 'vanilla',
                'condition': 'pottery',
                'entrances': ['Lumberjack House', 'Snitch Lady (West)', 'Snitch Lady (East)', 'Tavern (Front)',
                              '20 Rupee Cave', '50 Rupee Cave', 'Palace of Darkness Hint',
                              'Dark Lake Hylia Ledge Spike Cave', 'Mire Hint']
            },
            'fixed_enemy_drops_fairies': {
                'special': 'vanilla',
                'condition': 'enemy_drop',
                'entrances': ['Long Fairy Cave', 'Bonk Fairy (Light)']
            },
            'fixed_pots_n_bones_fairies': {
                'special': 'vanilla',
                'condition': ['pottery', 'enemy_drop'],
                'entrances': ['Hookshot Fairy']
            },
            'fixed_pots_n_bones': {
                'special': 'vanilla',
                'condition': ['pottery', 'dropshuffle'],
                'entrances': ['Light World Bomb Hut']
            },
            'fixed_shop_n_bones': {
                'special': 'vanilla',
                'condition': ['shopsanity', 'enemy_drop'],
                'entrances': ['Capacity Upgrade']
            },
            'fixed_bonk': {
                'special': 'vanilla',
                'condition': ['enemy_drop', 'bonk'],
                'entrances': ['Good Bee Cave']
            },
            'item_caves': {  # shuffles shops/pottery if they weren't fixed in the last steps
                'entrances': ['Mimic Cave', 'Spike Cave', 'Mire Shed', 'Hammer Peg Cave', 'Chest Game',
                              'C-Shaped House', 'Brewery', 'Hype Cave', 'Big Bomb Shop', 'Pyramid Fairy',
                              'Ice Rod Cave', 'Dam', 'Bonk Rock Cave', 'Library', 'Potion Shop', 'Mini Moldorm Cave',
                              'Checkerboard Cave', 'Graveyard Cave', 'Cave 45', 'Sick Kids House', 'Blacksmiths Hut',
                              'Sahasrahlas Hut', 'Aginahs Cave', 'Chicken House', 'Kings Grave', 'Blinds Hideout',
                              'Waterfall of Wishing', 'Dark Death Mountain Shop', 'Dark Lake Hylia Shop',
                              'Dark Potion Shop', 'Dark Lumberjack Shop', 'Dark World Shop',
                              'Red Shield Shop', 'Kakariko Shop', 'Capacity Upgrade', 'Lake Hylia Shop',
                              'Lumberjack House', 'Snitch Lady (West)', 'Snitch Lady (East)', 'Tavern (Front)',
                              'Light World Bomb Hut', '20 Rupee Cave', '50 Rupee Cave', 'Hookshot Fairy',
                              'Palace of Darkness Hint', 'Dark Lake Hylia Ledge Spike Cave', 'Desert Fairy',
                              'Light Hype Fairy', 'Dark Death Mountain Fairy', 'Dark Lake Hylia Ledge Fairy',
                              'Bonk Fairy (Dark)', 'Good Bee Cave', 'Long Fairy Cave', 'Bonk Fairy (Light)',
                              'Mire Hint', 'Links House', 'Tavern North']
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
            'skull_layout': {
                'special': 'vanilla',
                'condition': '',
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
            'skull_layout': {
                'special': 'vanilla',
                'condition': '',
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
    'district': {
        'undefined': 'error',
        'keep_drops_together': 'off',
        'cross_world': 'off',
        'pools': {
            'northwest_hyrule': {
                'special': 'district',
                'condition': 'lightworld',
                'drops': ['Lost Woods Hideout Drop', 'Lumberjack Tree Tree', 'Sanctuary Grave', 'North Fairy Cave Drop',

                          'Skull Woods First Section Hole (West)', 'Skull Woods First Section Hole (East)',
                          'Skull Woods First Section Hole (North)', 'Skull Woods Second Section Hole'],
                'entrances': ['Lost Woods Hideout Stump', 'Lumberjack Tree Cave', 'Sanctuary', 'North Fairy Cave',
                              'Lost Woods Gamble', 'Lumberjack House', 'Old Man Cave (West)', 'Death Mountain Return Cave (West)',
                              'Fortune Teller (Light)', 'Bonk Rock Cave', 'Graveyard Cave', 'Kings Grave',

                              'Skull Woods First Section Door', 'Skull Woods Second Section Door (East)',
                              'Skull Woods Second Section Door (West)', 'Skull Woods Final Section', 'Dark Lumberjack Shop',
                              'Bumper Cave (Bottom)', 'Bumper Cave (Top)', 'Fortune Teller (Dark)', 'Dark Sanctuary Hint',
                              'Red Shield Shop']
            },
            'northwest_dark_world': {
                'special': 'district',
                'condition': 'darkworld',
                'drops': ['Skull Woods First Section Hole (West)', 'Skull Woods First Section Hole (East)',
                          'Skull Woods First Section Hole (North)', 'Skull Woods Second Section Hole',

                          'Lost Woods Hideout Drop', 'Lumberjack Tree Tree', 'Sanctuary Grave', 'North Fairy Cave Drop',
                          'Kakariko Well Drop', 'Bat Cave Drop'],
                'entrances': ['Skull Woods First Section Door', 'Skull Woods Second Section Door (East)',
                              'Skull Woods Second Section Door (West)', 'Skull Woods Final Section', 'Dark Lumberjack Shop',
                              'Bumper Cave (Bottom)', 'Bumper Cave (Top)', 'Fortune Teller (Dark)', 'Dark Sanctuary Hint',
                              'Chest Game', 'Thieves Town', 'C-Shaped House', 'Dark World Shop', 'Brewery',
                              'Red Shield Shop', 'Hammer Peg Cave',

                              'Lost Woods Hideout Stump', 'Lumberjack Tree Cave', 'Sanctuary', 'North Fairy Cave',
                              'Kakariko Well Cave', 'Bat Cave Cave', 'Lost Woods Gamble', 'Lumberjack House', 'Fortune Teller (Light)',
                              'Old Man Cave (West)', 'Death Mountain Return Cave (West)', 'Bonk Rock Cave', 'Graveyard Cave',
                              'Kings Grave', 'Blinds Hideout', 'Elder House (West)', 'Elder House (East)', 'Snitch Lady (West)',
                              'Snitch Lady (East)', 'Chicken House', 'Sick Kids House', 'Bush Covered House', 'Light World Bomb Hut',
                              'Kakariko Shop', 'Tavern North', 'Tavern (Front)', 'Blacksmiths Hut']
            },
            'central_hyrule': {
                'special': 'district',
                'condition': 'lightworld',
                'drops': ['Hyrule Castle Secret Entrance Drop', 'Inverted Pyramid Hole',

                          'Pyramid Hole'],
                'entrances': ['Hyrule Castle Secret Entrance Stairs', 'Inverted Pyramid Entrance', 'Agahnims Tower',
                              'Hyrule Castle Entrance (West)', 'Hyrule Castle Entrance (East)', 'Hyrule Castle Entrance (South)',
                              'Bonk Fairy (Light)', 'Links House', 'Cave 45', 'Light Hype Fairy', 'Dam',

                              'Pyramid Entrance', 'Pyramid Fairy', 'Bonk Fairy (Dark)', 'Big Bomb Shop', 'Hype Cave', 'Swamp Palace']
            },
            'kakariko': {
                'special': 'district',
                'condition': 'lightworld',
                'drops': ['Kakariko Well Drop', 'Bat Cave Drop'],
                'entrances': ['Kakariko Well Cave', 'Bat Cave Cave', 'Blinds Hideout', 'Elder House (West)', 'Elder House (East)',
                              'Snitch Lady (West)', 'Snitch Lady (East)', 'Chicken House', 'Sick Kids House', 'Bush Covered House',
                              'Light World Bomb Hut', 'Kakariko Shop', 'Tavern North', 'Tavern (Front)', 'Blacksmiths Hut',
                              'Two Brothers House (West)', 'Two Brothers House (East)', 'Library', 'Kakariko Gamble Game',

                              'Chest Game', 'Thieves Town', 'C-Shaped House', 'Dark World Shop', 'Brewery',
                              'Hammer Peg Cave', 'Archery Game']
            },
            'eastern_hyrule': {
                'special': 'district',
                'condition': 'lightworld',
                'entrances': ['Waterfall of Wishing', 'Potion Shop', 'Sahasrahlas Hut', 'Eastern Palace', 'Lake Hylia Fairy',
                              'Long Fairy Cave',

                              'Dark Potion Shop', 'Palace of Darkness Hint', 'Palace of Darkness', 'Dark Lake Hylia Fairy',
                              'East Dark World Hint']
            },
            'lake_hylia': {
                'special': 'district',
                'condition': 'lightworld',
                'entrances': ['Lake Hylia Fortune Teller', 'Lake Hylia Shop', 'Capacity Upgrade', 'Mini Moldorm Cave',
                              'Ice Rod Cave', 'Good Bee Cave', '20 Rupee Cave',

                              'Dark Lake Hylia Shop', 'Ice Palace', 'Dark Lake Hylia Ledge Fairy', 'Dark Lake Hylia Ledge Hint',
                              'Dark Lake Hylia Ledge Spike Cave']
            },
            'desert': {
                'special': 'district',
                'condition': 'lightworld',
                'entrances': ['Desert Palace Entrance (North)', 'Desert Palace Entrance (West)', 'Desert Palace Entrance (South)',
                              'Desert Palace Entrance (East)', 'Checkerboard Cave', 'Aginahs Cave', 'Desert Fairy', '50 Rupee Cave',

                              'Mire Shed', 'Misery Mire', 'Mire Fairy', 'Mire Hint']
            },
            'death_mountain': {
                'special': 'district',
                'condition': 'lightworld',
                'entrances': ['Tower of Hera', 'Spectacle Rock Cave Peak', 'Spectacle Rock Cave (Bottom)', 'Spectacle Rock Cave',
                              'Death Mountain Return Cave (East)', 'Old Man Cave (East)', 'Old Man House (Bottom)', 'Old Man House (Top)',
                              'Spiral Cave', 'Spiral Cave (Bottom)', 'Fairy Ascension Cave (Top)', 'Fairy Ascension Cave (Bottom)',
                              'Mimic Cave', 'Hookshot Fairy', 'Paradox Cave (Top)', 'Paradox Cave (Middle)', 'Paradox Cave (Bottom)',

                              'Ganons Tower', 'Dark Death Mountain Fairy', 'Spike Cave', 'Superbunny Cave (Bottom)', 'Superbunny Cave (Top)',
                              'Dark Death Mountain Shop', 'Hookshot Cave', 'Hookshot Cave Back Entrance',
                              'Dark Death Mountain Ledge (West)', 'Dark Death Mountain Ledge (East)', 'Turtle Rock Isolated Ledge Entrance', 'Turtle Rock']
            },
            'dark_death_mountain': {
                'special': 'district',
                'condition': 'darkworld',
                'entrances': ['Ganons Tower', 'Dark Death Mountain Fairy', 'Spike Cave', 'Superbunny Cave (Bottom)', 'Superbunny Cave (Top)',
                              'Dark Death Mountain Shop', 'Hookshot Cave', 'Hookshot Cave Back Entrance',
                              'Dark Death Mountain Ledge (West)', 'Dark Death Mountain Ledge (East)', 'Turtle Rock Isolated Ledge Entrance', 'Turtle Rock',

                              'Tower of Hera', 'Spectacle Rock Cave Peak', 'Spectacle Rock Cave (Bottom)', 'Spectacle Rock Cave',
                              'Death Mountain Return Cave (East)', 'Old Man Cave (East)', 'Old Man House (Bottom)', 'Old Man House (Top)',
                              'Spiral Cave', 'Spiral Cave (Bottom)', 'Fairy Ascension Cave (Top)', 'Fairy Ascension Cave (Bottom)',
                              'Mimic Cave', 'Hookshot Fairy', 'Paradox Cave (Top)', 'Paradox Cave (Middle)', 'Paradox Cave (Bottom)']
            },
            'south_dark_world': {
                'special': 'district',
                'condition': 'darkworld',
                'entrances': ['Archery Game', 'Bonk Fairy (Dark)', 'Big Bomb Shop', 'Hype Cave', 'Dark Lake Hylia Shop', 'Ice Palace',
                              'Dark Lake Hylia Ledge Fairy', 'Dark Lake Hylia Ledge Hint', 'Dark Lake Hylia Ledge Spike Cave',
                              'Swamp Palace',

                              'Two Brothers House (West)', 'Two Brothers House (East)', 'Library', 'Kakariko Gamble Game',
                              'Bonk Fairy (Light)', 'Links House', 'Cave 45', 'Desert Fairy', '50 Rupee Cave', 'Dam',
                              'Light Hype Fairy', 'Lake Hylia Fortune Teller', 'Lake Hylia Shop', 'Capacity Upgrade',
                              'Mini Moldorm Cave', 'Ice Rod Cave', 'Good Bee Cave', '20 Rupee Cave']
            },
            'east_dark_world': {
                'special': 'district',
                'condition': 'darkworld',
                'drops': ['Pyramid Hole',

                          'Hyrule Castle Secret Entrance Drop', 'Inverted Pyramid Hole'],
                'entrances': ['Pyramid Entrance', 'Pyramid Fairy', 'Dark Potion Shop', 'Palace of Darkness Hint', 'Palace of Darkness',
                              'Dark Lake Hylia Fairy', 'East Dark World Hint',

                              'Hyrule Castle Secret Entrance Stairs', 'Inverted Pyramid Entrance', 'Waterfall of Wishing', 'Potion Shop', 
                              'Agahnims Tower', 'Hyrule Castle Entrance (West)', 'Hyrule Castle Entrance (East)',
                              'Hyrule Castle Entrance (South)', 'Sahasrahlas Hut', 'Eastern Palace', 'Lake Hylia Fairy', 'Long Fairy Cave']
            },
            'mire': {
                'special': 'district',
                'condition': 'darkworld',
                'entrances': ['Mire Shed', 'Misery Mire', 'Mire Fairy', 'Mire Hint',

                              'Desert Palace Entrance (North)', 'Desert Palace Entrance (West)', 'Desert Palace Entrance (South)',
                              'Desert Palace Entrance (East)', 'Checkerboard Cave', 'Aginahs Cave']
            }
        }
    },
    'swapped': {
        'undefined': 'swap',
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
    'Hyrule Castle Secret Entrance Drop': 'Hyrule Castle Secret Entrance Stairs',
    'Kakariko Well Drop': 'Kakariko Well Cave',
    'Bat Cave Drop': 'Bat Cave Cave',
    'North Fairy Cave Drop': 'North Fairy Cave',
    'Lost Woods Hideout Drop': 'Lost Woods Hideout Stump',
    'Lumberjack Tree Tree': 'Lumberjack Tree Cave',
    'Sanctuary Grave': 'Sanctuary',
    'Pyramid Hole': 'Pyramid Entrance',
    'Inverted Pyramid Hole': 'Inverted Pyramid Entrance',

    'Skull Woods First Section Hole (North)': 'Skull Woods First Section Door',
    'Skull Woods Second Section Hole': 'Skull Woods Second Section Door (East)',
}

sw_linked_drop_map = {
    'Skull Woods Second Section Hole': 'Skull Woods Second Section Door (East)',
    'Skull Woods First Section Hole (North)': 'Skull Woods First Section Door',
    'Skull Woods First Section Hole (West)': 'Skull Woods First Section Door',
    'Skull Woods First Section Hole (East)': 'Skull Woods First Section Door'
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


    'Hyrule Castle Secret Entrance Stairs': 'Hyrule Castle Secret Entrance Exit',
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
    'Paradox Cave (Top)': 'Paradox Cave Exit (Top)'
}

single_entrance_map = {
    'Mimic Cave': 'Mimic Cave', 'Dark Death Mountain Fairy': 'Dark Death Mountain Healer Fairy',
    'Dark Death Mountain Shop': 'Dark Death Mountain Shop', 'Spike Cave': 'Spike Cave',
    'Mire Fairy': 'Mire Healer Fairy', 'Mire Hint': 'Mire Hint', 'Mire Shed': 'Mire Shed',
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

combine_linked_drop_map = {**linked_drop_map, **sw_linked_drop_map}

LW_Entrances = []
DW_Entrances = []

Isolated_LH_Doors = ['Kings Grave', 'Waterfall of Wishing', 'Desert Palace Entrance (South)',
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

Dungeon_Exit_Set = {
    'Eastern Palace Exit',
    'Tower of Hera Exit',
    'Agahnims Tower Exit',
    'Palace of Darkness Exit',
    'Swamp Palace Exit', 
    'Skull Woods Final Section Exit',
    'Thieves Town Exit',
    'Ice Palace Exit',
    'Misery Mire Exit',
    'Ganons Tower Exit',
    'Skull Woods First Section Exit', 'Skull Woods Second Section Exit (East)', 'Skull Woods Second Section Exit (West)',
    'Hyrule Castle Exit (South)', 'Hyrule Castle Exit (West)', 'Hyrule Castle Exit (East)',
    'Desert Palace Exit (South)', 'Desert Palace Exit (East)', 'Desert Palace Exit (West)',
    'Turtle Rock Exit (Front)', 'Turtle Rock Isolated Ledge Exit', 'Turtle Rock Ledge Exit (West)'
}

dungeon_restriction_checks = [
    (['Hyrule Castle Exit (South)', 'Hyrule Castle Exit (West)', 'Hyrule Castle Exit (East)', 'Sanctuary Exit'], ['Sewer Drop']),
    (['Desert Palace Exit (South)', 'Desert Palace Exit (East)', 'Desert Palace Exit (West)', 'Desert Palace Exit (North)'], []),
    (['Turtle Rock Exit (Front)', 'Turtle Rock Isolated Ledge Exit', 'Turtle Rock Ledge Exit (West)', 'Turtle Rock Ledge Exit (East)'], []),
    (['Skull Woods First Section Exit', 'Skull Woods Second Section Exit (East)', 'Skull Woods Second Section Exit (West)', 'Skull Woods Final Section Exit'],
     ['Skull Pinball', 'Skull Left Drop', 'Skull Pot Circle', 'Skull Back Drop'])
 ]

doors_possible_connectors = [
    'Sanctuary Exit', 'Desert Palace Exit (North)', 'Skull Woods First Section Exit',
    'Skull Woods Second Section Exit (East)', 'Skull Woods Second Section Exit (West)', 'Skull Woods Final Section Exit'
]

# Entrances that cannot be used to access a must_exit entrance - symmetrical to allow reverse lookups
Must_Exit_Invalid_Connections = defaultdict(set)

Simple_DM_Non_Connectors = {'Old Man Cave Ledge', 'Spiral Cave (Top)', 'Superbunny Cave (Bottom)',
                            'Spectacle Rock Cave (Peak)', 'Spectacle Rock Cave (Top)'}

Forbidden_Swap_Entrances = {'Old Man Cave (East)', 'Blacksmiths Hut', 'Big Bomb Shop'}


# these are connections that cannot be shuffled and always exist.
# They link together underworld regions
mandatory_connections = [('Lost Woods Hideout (top to bottom)', 'Lost Woods Hideout (bottom)'),
                         ('Lumberjack Tree (top to bottom)', 'Lumberjack Tree (bottom)'),
                         ('Death Mountain Return Cave E', 'Death Mountain Return Cave (right)'),
                         ('Death Mountain Return Cave W', 'Death Mountain Return Cave (left)'),
                         ('Old Man Cave Dropdown', 'Old Man Cave (East)'),
                         ('Old Man Cave W', 'Old Man Cave (West)'),
                         ('Old Man Cave E', 'Old Man Cave (East)'),
                         ('Spectacle Rock Cave Drop', 'Spectacle Rock Cave Pool'),
                         ('Spectacle Rock Cave Peak Drop', 'Spectacle Rock Cave Pool'),
                         ('Spectacle Rock Cave West Edge', 'Spectacle Rock Cave (Bottom)'),
                         ('Spectacle Rock Cave East Edge', 'Spectacle Rock Cave Pool'),
                         ('Old Man House Front to Back', 'Old Man House Back'),
                         ('Old Man House Back to Front', 'Old Man House'),
                         ('Spiral Cave (top to bottom)', 'Spiral Cave (Bottom)'),
                         ('Paradox Cave Push Block Reverse', 'Paradox Cave Chest Area'),
                         ('Paradox Cave Push Block', 'Paradox Cave Front'),
                         ('Paradox Cave Chest Area NE', 'Paradox Cave Bomb Area'),
                         ('Paradox Cave Bomb Jump', 'Paradox Cave'),
                         ('Paradox Cave Climb', 'Paradox Cave (Top)'),
                         ('Paradox Cave Descent', 'Paradox Cave'),
                         ('Paradox Cave Drop', 'Paradox Cave Chest Area'),
                         ('Paradox Shop', 'Paradox Shop'),
                         ('Fairy Ascension Cave Climb', 'Fairy Ascension Cave (Top)'),
                         ('Fairy Ascension Cave Pots', 'Fairy Ascension Cave (Bottom)'),
                         ('Fairy Ascension Cave Drop', 'Fairy Ascension Cave (Drop)'),
                         ('Kakariko Well (top to bottom)', 'Kakariko Well (bottom)'),
                         ('Kakariko Well (top to back)', 'Kakariko Well (back)'),
                         ('Blinds Hideout N', 'Blinds Hideout (Top)'),
                         ('Sewer Drop', 'Sewers Rat Path'),
                         ('Missing Smith', 'Missing Smith'),
                         ('Bat Cave Door', 'Bat Cave (left)'),
                         ('Good Bee Cave Front to Back', 'Good Bee Cave (back)'),
                         ('Good Bee Cave Back to Front', 'Good Bee Cave'),
                         ('Capacity Upgrade East', 'Capacity Fairy Pool'),
                         ('Capacity Fairy Pool West', 'Capacity Upgrade'),
                         ('Bonk Fairy (Dark) Pool', 'Bonk Fairy Pool'),
                         ('Bonk Fairy (Light) Pool', 'Bonk Fairy Pool'),
                         
                         ('Hookshot Cave Front to Middle', 'Hookshot Cave (Middle)'),
                         ('Hookshot Cave Middle to Front', 'Hookshot Cave (Front)'),
                         ('Hookshot Cave Middle to Back', 'Hookshot Cave (Back)'),
                         ('Hookshot Cave Back to Middle', 'Hookshot Cave (Middle)'),
                         ('Hookshot Cave Back to Fairy', 'Hookshot Cave (Fairy Pool)'),
                         ('Hookshot Cave Fairy to Back', 'Hookshot Cave (Back)'),
                         ('Hookshot Cave Bonk Path', 'Hookshot Cave (Bonk Islands)'),
                         ('Hookshot Cave Hook Path', 'Hookshot Cave (Hook Islands)'),
                         ('Superbunny Cave Climb', 'Superbunny Cave (Top)'),
                         ('Bumper Cave Bottom to Top', 'Bumper Cave (top)'),
                         ('Bumper Cave Top To Bottom', 'Bumper Cave (bottom)'),
                         ('Ganon Drop', 'Bottom of Pyramid')
                    ]

# non-shuffled entrance links
default_connections = {'Lost Woods Gamble': 'Lost Woods Gamble',
                       'Lost Woods Hideout Drop': 'Lost Woods Hideout (top)',
                       'Lost Woods Hideout Stump': 'Lost Woods Hideout (bottom)',
                       'Lost Woods Hideout Exit': 'Lost Woods East Area',
                       'Lumberjack House': 'Lumberjack House',
                       'Lumberjack Tree Tree': 'Lumberjack Tree (top)',
                       'Lumberjack Tree Cave': 'Lumberjack Tree (bottom)',
                       'Lumberjack Tree Exit': 'Lumberjack Area',
                       'Death Mountain Return Cave (East)': 'Death Mountain Return Cave (right)',
                       'Death Mountain Return Cave Exit (East)': 'West Death Mountain (Bottom)',
                       'Old Man Cave (East)': 'Old Man Cave (East)',
                       'Old Man Cave Exit (East)': 'West Death Mountain (Bottom)',
                       'Spectacle Rock Cave': 'Spectacle Rock Cave (Top)',
                       'Spectacle Rock Cave Exit (Top)': 'West Death Mountain (Bottom)',
                       'Spectacle Rock Cave Peak': 'Spectacle Rock Cave (Peak)',
                       'Spectacle Rock Cave Exit (Peak)': 'West Death Mountain (Bottom)',
                       'Spectacle Rock Cave (Bottom)': 'Spectacle Rock Cave (Bottom)',
                       'Spectacle Rock Cave Exit': 'West Death Mountain (Bottom)',
                       'Old Man House (Bottom)': 'Old Man House',
                       'Old Man House Exit (Bottom)': 'West Death Mountain (Bottom)',
                       'Old Man House (Top)': 'Old Man House Back',
                       'Old Man House Exit (Top)': 'West Death Mountain (Bottom)',
                       'Spiral Cave': 'Spiral Cave (Top)',
                       'Spiral Cave Exit (Top)': 'Spiral Cave Ledge',
                       'Spiral Cave (Bottom)': 'Spiral Cave (Bottom)',
                       'Spiral Cave Exit': 'East Death Mountain (Bottom)',
                       'Mimic Cave': 'Mimic Cave',
                       'Fairy Ascension Cave (Top)': 'Fairy Ascension Cave (Top)',
                       'Fairy Ascension Cave Exit (Top)': 'Fairy Ascension Ledge',
                       'Fairy Ascension Cave (Bottom)': 'Fairy Ascension Cave (Bottom)',
                       'Fairy Ascension Cave Exit (Bottom)': 'Fairy Ascension Plateau',
                       'Hookshot Fairy': 'Hookshot Fairy',
                       'Paradox Cave (Top)': 'Paradox Cave',
                       'Paradox Cave Exit (Top)': 'East Death Mountain (Top East)',
                       'Paradox Cave (Middle)': 'Paradox Cave',
                       'Paradox Cave Exit (Middle)': 'East Death Mountain (Bottom)',
                       'Paradox Cave (Bottom)': 'Paradox Cave Front',
                       'Paradox Cave Exit (Bottom)': 'East Death Mountain (Bottom)',
                       'Death Mountain Return Cave (West)': 'Death Mountain Return Cave (left)',
                       'Death Mountain Return Cave Exit (West)': 'Mountain Pass Ledge',
                       'Old Man Cave (West)': 'Old Man Cave Ledge',
                       'Old Man Cave Exit (West)': 'Mountain Pass Entry',
                       'Waterfall of Wishing': 'Waterfall of Wishing',
                       'Fortune Teller (Light)': 'Fortune Teller (Light)',
                       'Bonk Rock Cave': 'Bonk Rock Cave',
                       'Sanctuary': 'Sanctuary Portal',
                       'Sanctuary Grave': 'Sewer Drop',
                       'Sanctuary Exit': 'Sanctuary Area',
                       'Graveyard Cave': 'Graveyard Cave',
                       'Kings Grave': 'Kings Grave',
                       'North Fairy Cave Drop': 'North Fairy Cave',
                       'North Fairy Cave': 'North Fairy Cave',
                       'North Fairy Cave Exit': 'River Bend Area',
                       'Potion Shop': 'Potion Shop',
                       'Kakariko Well Drop': 'Kakariko Well (top)',
                       'Kakariko Well Cave': 'Kakariko Well (bottom)',
                       'Kakariko Well Exit': 'Kakariko Village',
                       'Blinds Hideout': 'Blinds Hideout',
                       'Elder House (West)': 'Elder House',
                       'Elder House Exit (West)': 'Kakariko Village',
                       'Elder House (East)': 'Elder House',
                       'Elder House Exit (East)': 'Kakariko Village',
                       'Snitch Lady (West)': 'Snitch Lady (West)',
                       'Snitch Lady (East)': 'Snitch Lady (East)',
                       'Chicken House': 'Chicken House',
                       'Sick Kids House': 'Sick Kids House',
                       'Bush Covered House': 'Bush Covered House',
                       'Light World Bomb Hut': 'Light World Bomb Hut',
                       'Kakariko Shop': 'Kakariko Shop',
                       'Tavern North': 'Tavern',
                       'Tavern (Front)': 'Tavern (Front)',
                       'Hyrule Castle Secret Entrance Drop': 'Hyrule Castle Secret Entrance',
                       'Hyrule Castle Secret Entrance Stairs': 'Hyrule Castle Secret Entrance',
                       'Hyrule Castle Secret Entrance Exit': 'Hyrule Castle Courtyard',
                       'Sahasrahlas Hut': 'Sahasrahlas Hut',
                       'Blacksmiths Hut': 'Blacksmiths Hut',
                       'Bat Cave Drop': 'Bat Cave (right)',
                       'Bat Cave Cave': 'Bat Cave (left)',
                       'Bat Cave Exit': 'Blacksmith Area',
                       'Two Brothers House (West)': 'Two Brothers House',
                       'Two Brothers House Exit (West)': 'Maze Race Ledge',
                       'Two Brothers House (East)': 'Two Brothers House',
                       'Two Brothers House Exit (East)': 'Kakariko Suburb Area',
                       'Library': 'Library',
                       'Kakariko Gamble Game': 'Kakariko Gamble Game',
                       'Bonk Fairy (Light)': 'Bonk Fairy (Light)',
                       'Links House': 'Links House',
                       'Links House Exit': 'Links House Area',
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
                       'Dark Death Mountain Fairy': 'Dark Death Mountain Healer Fairy',
                       'Spike Cave': 'Spike Cave',
                       'Hookshot Cave Back Entrance': 'Hookshot Cave (Back)',
                       'Hookshot Cave Back Exit': 'Dark Death Mountain Floating Island',
                       'Hookshot Cave': 'Hookshot Cave (Front)',
                       'Hookshot Cave Front Exit': 'East Dark Death Mountain (Top)',
                       'Superbunny Cave (Top)': 'Superbunny Cave (Top)',
                       'Superbunny Cave Exit (Top)': 'East Dark Death Mountain (Top)',
                       'Superbunny Cave (Bottom)': 'Superbunny Cave (Bottom)',
                       'Superbunny Cave Exit (Bottom)': 'East Dark Death Mountain (Bottom)',
                       'Dark Death Mountain Shop': 'Dark Death Mountain Shop',
                       'Bumper Cave (Top)': 'Bumper Cave (top)',
                       'Bumper Cave Exit (Top)': 'Bumper Cave Ledge',
                       'Bumper Cave (Bottom)': 'Bumper Cave (bottom)',
                       'Bumper Cave Exit (Bottom)': 'Bumper Cave Entry',
                       'Fortune Teller (Dark)': 'Fortune Teller (Dark)',
                       'Dark Sanctuary Hint': 'Dark Sanctuary Hint',
                       'Dark Potion Shop': 'Dark Potion Shop',
                       'Chest Game': 'Chest Game',
                       'C-Shaped House': 'C-Shaped House',
                       'Dark World Shop': 'Village of Outcasts Shop',
                       'Brewery': 'Brewery',
                       'Red Shield Shop': 'Red Shield Shop',
                       'Pyramid Fairy': 'Pyramid Fairy',
                       'Palace of Darkness Hint': 'Palace of Darkness Hint',
                       'Hammer Peg Cave': 'Hammer Peg Cave',
                       'Archery Game': 'Archery Game',
                       'Bonk Fairy (Dark)': 'Bonk Fairy (Dark)',
                       'Big Bomb Shop': 'Big Bomb Shop',
                       'Dark Lake Hylia Fairy': 'Dark Lake Hylia Healer Fairy',
                       'East Dark World Hint': 'East Dark World Hint',
                       'Mire Shed': 'Mire Shed',
                       'Mire Hint': 'Mire Hint',
                       'Mire Fairy': 'Mire Healer Fairy',
                       'Hype Cave': 'Hype Cave',
                       'Dark Lake Hylia Shop': 'Dark Lake Hylia Shop',
                       'Dark Lake Hylia Ledge Fairy': 'Dark Lake Hylia Ledge Healer Fairy',
                       'Dark Lake Hylia Ledge Hint': 'Dark Lake Hylia Ledge Hint',
                       'Dark Lake Hylia Ledge Spike Cave': 'Dark Lake Hylia Ledge Spike Cave'}

open_default_connections = {'Pyramid Hole': 'Pyramid',
                            'Pyramid Exit': 'Pyramid Ledge',
                            'Pyramid Entrance': 'Bottom of Pyramid'}

inverted_default_connections = {'Inverted Pyramid Hole': 'Pyramid',
                                'Pyramid Exit': 'Hyrule Castle Ledge',
                                'Inverted Pyramid Entrance': 'Bottom of Pyramid'}


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
            'Mire Healer Fairy': 0x5E,
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
            'Mire Hint': 0x62,
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
