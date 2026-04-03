import RaceRandom as random, logging, copy
from collections import OrderedDict, defaultdict
from DungeonGenerator import GenerationException
from BaseClasses import OWEdge, WorldType, RegionType, Direction, Terrain, PolSlot, Entrance
from Regions import mark_light_dark_world_regions
from source.overworld.EntranceShuffle2 import connect_simple
from source.overworld.FluteShuffle import shuffle_flute_spots, default_flute_connections, flute_data
from OWEdges import OWTileRegions, OWEdgeGroups, OWEdgeGroupsTerrain, OWExitTypes, OpenStd, parallel_links, IsParallel
from OverworldGlitchRules import create_owg_connections
from Utils import bidict

version_number = '0.7.1.0'
# branch indicator is intentionally different across branches
version_branch = '-u'

__version__ = '%s%s' % (version_number, version_branch)

parallel_links_new = None # needs to be globally available, reset every new generation/player

def link_overworld(world, player):
    global parallel_links_new

    # setup mandatory connections
    for exitname, regionname in mandatory_connections:
        connect_simple(world, exitname, regionname, player)

    def performSwap(groups, swaps):
        def getParallel(edgename):
            if edgename in parallel_links_new:
                return parallel_links_new[edgename]
            else:
                raise Exception('No parallel edge found for edge %s', edgename)
        
        def getNewSets(all_set, other_set):
            new_all_set = list(map(getParallel, all_set))
            if not all(edge in orig_swaps for edge in new_all_set):
                raise Exception('Cannot move a parallel edge without the other')
            else:
                for edge in new_all_set:
                    swaps.remove(edge)
            new_other_set = getNewSet(other_set)
            return (new_all_set, new_other_set)
        
        def getNewSet(edge_set):
            new_set = []
            for edge in edge_set:
                if edge in orig_swaps:
                    new_edge = getParallel(edge)
                    if new_edge not in orig_swaps:
                        raise Exception('Cannot move a parallel edge without the other')
                    new_set.append(new_edge)
                    swaps.remove(new_edge)
                else:
                    new_set.append(edge)
            return new_set
        
        # swaps edges from one pool to another
        orig_swaps = copy.deepcopy(swaps)
        new_groups = {}
        for group in groups.keys():
            new_groups[group] = ([],[])
        
        for group in groups.keys():
            (mode, wrld, dir, terrain, parallel, count, custom) = group
            for (forward_set, back_set) in zip(groups[group][0], groups[group][1]):
                anyF = any(edge in orig_swaps for edge in forward_set)
                anyB = any(edge in orig_swaps for edge in back_set)
                allF = all(edge in orig_swaps for edge in forward_set)
                allB = all(edge in orig_swaps for edge in back_set)
                if not (anyF or anyB):
                    # no change
                    new_groups[group][0].append(forward_set)
                    new_groups[group][1].append(back_set)
                elif allF and allB:
                    # move both sets
                    if parallel == IsParallel.Yes and not (all(edge in orig_swaps for edge in map(getParallel, forward_set)) and all(edge in orig_swaps for edge in map(getParallel, back_set))):
                        raise Exception('Cannot move a parallel edge without the other')
                    new_mode = OpenStd.Open
                    if tuple((OpenStd.Open, WorldType((int(wrld) + 1) % 2), dir, terrain, parallel, count, custom)) not in new_groups.keys():
                        # when Links House tile is flipped, the DW edges need to get put into existing Standard group
                        new_mode = OpenStd.Standard
                    new_groups[(new_mode, WorldType((int(wrld) + 1) % 2), dir, terrain, parallel, count, custom)][0].append(forward_set)
                    new_groups[(new_mode, WorldType((int(wrld) + 1) % 2), dir, terrain, parallel, count, custom)][1].append(back_set)
                    for edge in forward_set:
                        swaps.remove(edge)
                    for edge in back_set:
                        swaps.remove(edge)
                elif anyF or anyB:
                    if parallel == IsParallel.Yes:
                        if allF or allB:
                            # move one set
                            if allF and not (world.owKeepSimilar[player] and anyB):
                                (new_forward_set, new_back_set) = getNewSets(forward_set, back_set)
                            elif allB and not (world.owKeepSimilar[player] and anyF):
                                (new_back_set, new_forward_set) = getNewSets(back_set, forward_set)
                            else:
                                raise Exception('Cannot move an edge out of a Similar group')
                            new_groups[group][0].append(new_forward_set)
                            new_groups[group][1].append(new_back_set)
                        else:
                            # move individual edges
                            if not world.owKeepSimilar[player]:
                                new_groups[group][0].append(getNewSet(forward_set) if anyF else forward_set)
                                new_groups[group][1].append(getNewSet(back_set) if anyB else back_set)
                            else:
                                raise Exception('Cannot move an edge out of a Similar group')
                    else:
                        raise NotImplementedError('Cannot move one side of a non-parallel connection')
                else:
                    raise NotImplementedError('Invalid OW Edge flip scenario')
        return new_groups

    trimmed_groups = copy.deepcopy(OWEdgeGroupsTerrain if world.owTerrain[player] else OWEdgeGroups)
    swapped_edges = list()

    # restructure Maze Race/Suburb/Frog/Dig Game manually due to NP/P relationship
    parallel_links_new = bidict(parallel_links) # shallow copy is enough (deep copy is broken)
    if world.owLayout[player] != 'grid':
        if world.owKeepSimilar[player]:
            del parallel_links_new['Maze Race ES']
            del parallel_links_new['Kakariko Suburb WS']
            for group in trimmed_groups.keys():
                (std, region, axis, terrain, parallel, _, custom) = group
                if parallel == IsParallel.Yes:
                    (forward_edges, back_edges) = trimmed_groups[group]
                    if ['Maze Race ES'] in forward_edges:
                        forward_edges.remove(['Maze Race ES'])
                        trimmed_groups[(std, region, axis, terrain, IsParallel.No, 1, custom)][0].append(['Maze Race ES'])
                    if ['Kakariko Suburb WS'] in back_edges:
                        back_edges.remove(['Kakariko Suburb WS'])
                        trimmed_groups[(std, region, axis, terrain, IsParallel.No, 1, custom)][1].append(['Kakariko Suburb WS'])
                    trimmed_groups[group] = (forward_edges, back_edges)
        else:
            for group in trimmed_groups.keys():
                (std, region, axis, terrain, _, _, custom) = group
                (forward_edges, back_edges) = trimmed_groups[group]
                if ['Dig Game EC', 'Dig Game ES'] in forward_edges:
                    forward_edges.remove(['Dig Game EC', 'Dig Game ES'])
                    trimmed_groups[(std, region, axis, terrain, IsParallel.Yes, 1, custom)][0].append(['Dig Game ES'])
                    trimmed_groups[(std, region, axis, terrain, IsParallel.No, 1, custom)][0].append(['Dig Game EC'])
                if ['Frog WC', 'Frog WS'] in back_edges:
                    back_edges.remove(['Frog WC', 'Frog WS'])
                    trimmed_groups[(std, region, axis, terrain, IsParallel.Yes, 1, custom)][1].append(['Frog WS'])
                    trimmed_groups[(std, region, axis, terrain, IsParallel.No, 1, custom)][1].append(['Frog WC'])
                trimmed_groups[group] = (forward_edges, back_edges)
    parallel_links_new = {**dict(parallel_links_new), **dict({e:p[0] for e, p in parallel_links_new.inverse.items()})}

    connected_edges = []
    if world.owLayout[player] != 'vanilla':
        trimmed_groups = remove_reserved(world, trimmed_groups, connected_edges, player)
        trimmed_groups = reorganize_groups(world, trimmed_groups, player)

    # tile shuffle
    logging.getLogger('').debug('Flipping overworld tiles')
    if world.owMixed[player]:
        tile_groups, force_flipped, force_nonflipped, undefined_chance, allow_flip_sanc = define_tile_groups(world, False, player)
        world.allow_flip_sanc[player] = allow_flip_sanc
        swapped_edges = shuffle_tiles(world, tile_groups, world.owswaps[player], False, (force_flipped, force_nonflipped, undefined_chance), player)
        
        update_world_regions(world, player)

        # update spoiler
        s = list(map(lambda x: ' ' if x not in world.owswaps[player][0] else 'S', [i for i in range(0x40, 0x82)]))
        text_output = tile_swap_spoiler_table.replace('s', '%s') % (                         s[0x02],                                s[0x07],
                                                                                 s[0x00],                s[0x03],        s[0x05],
            s[0x00],        s[0x02],s[0x03],        s[0x05],        s[0x07],                 s[0x0a],                                s[0x0f],
                            s[0x0a],                                s[0x0f],
            s[0x10],s[0x11],s[0x12],s[0x13],s[0x14],s[0x15],s[0x16],s[0x17], s[0x10],s[0x11],s[0x12],s[0x13],s[0x14],s[0x15],s[0x16],s[0x17],
            s[0x18],        s[0x1a],s[0x1b],        s[0x1d],s[0x1e],
                            s[0x22],                s[0x25],                                 s[0x1a],                s[0x1d],
            s[0x28],s[0x29],s[0x2a],s[0x2b],s[0x2c],s[0x2d],s[0x2e],s[0x2f],     s[0x18],                s[0x1b],                s[0x1e],
            s[0x30],        s[0x32],s[0x33],s[0x34],s[0x35],        s[0x37],                 s[0x22],                s[0x25],
                            s[0x3a],s[0x3b],s[0x3c],                s[0x3f],
                                                                             s[0x28],s[0x29],s[0x2a],s[0x2b],s[0x2c],s[0x2d],s[0x2e],s[0x2f],
                                                                    s[0x40],                 s[0x32],s[0x33],s[0x34],                s[0x37],
                                                                                 s[0x30],                                s[0x35],
                                                                    s[0x41],                 s[0x3a],s[0x3b],s[0x3c],                s[0x3f])
        world.spoiler.set_map('swaps', text_output, world.owswaps[player][0], player)
    
    # apply tile logical connections
    if not world.is_bombshop_start(player):
        connect_simple(world, 'Links House S&Q', 'Links House', player)
    else:
        connect_simple(world, 'Links House S&Q', 'Big Bomb Shop', player)
    
    if not world.is_dark_chapel_start(player):
        connect_simple(world, 'Sanctuary S&Q', 'Sanctuary', player)
    else:
        connect_simple(world, 'Sanctuary S&Q', 'Dark Sanctuary Hint', player)

    if not world.is_tile_swapped(0x1b, player):
        connect_simple(world, 'Other World S&Q', 'Pyramid Area', player)
    else:
        connect_simple(world, 'Other World S&Q', 'Hyrule Castle Ledge', player)

    for owid in ow_connections.keys():
        if not world.is_tile_swapped(owid, player):
            for (exitname, regionname) in ow_connections[owid][0]:
                connect_simple(world, exitname, regionname, player)
        else:
            for (exitname, regionname) in ow_connections[owid][1]:
                connect_simple(world, exitname, regionname, player)

    categorize_world_regions(world, player)
    create_dynamic_mirror_exits(world, player)

    if world.logic[player] in ('owglitches', 'hybridglitches', 'nologic'):
        create_owg_connections(world, player)
    
    # crossed shuffle
    logging.getLogger('').debug('Crossing overworld edges')

    # customizer setup
    force_crossed = set()
    force_noncrossed = set()
    count_crossed = 0
    limited_crossed = -1
    undefined_chance = 50
    if world.customizer:
        custom_crossed = world.customizer.get_owcrossed()
        if custom_crossed and player in custom_crossed:
            custom_crossed = custom_crossed[player]
            if 'force_crossed' in custom_crossed and len(custom_crossed['force_crossed']) > 0:
                for edgename in custom_crossed['force_crossed']:
                    edge = world.get_owedge(edgename, player)
                    force_crossed.add(edge.name)
            if 'force_noncrossed' in custom_crossed and len(custom_crossed['force_noncrossed']) > 0:
                for edgename in custom_crossed['force_noncrossed']:
                    edge = world.get_owedge(edgename, player)
                    force_noncrossed.add(edge.name)
            if 'limit_crossed' in custom_crossed:
                if world.owCrossed[player] == 'unrestricted':
                    limited_crossed = custom_crossed['limit_crossed']
            if 'undefined_chance' in custom_crossed:
                undefined_chance = custom_crossed['undefined_chance']

    if limited_crossed > -1 and world.owLayout[player] != 'grid':
        # connect forced crossed non-parallel edges based on previously determined tile flips
        for edge in swapped_edges:
            if edge not in parallel_links_new:
                world.owcrossededges[player].append(edge)
                count_crossed = count_crossed + 1

    if world.owCrossed[player] == 'grouped':
        # the idea is to XOR the new flips with the ones from Mixed so that non-parallel edges still work
        # Polar corresponds to Grouped with no flips in ow_crossed_tiles_mask
        ow_crossed_tiles_mask = [[],[],[]]
        tile_groups, force_flipped, force_nonflipped, undefined_chance, _ = define_tile_groups(world, True, player)
        world.owcrossededges[player] = shuffle_tiles(world, tile_groups, ow_crossed_tiles_mask, True, (force_flipped, force_nonflipped, undefined_chance), player)
        ow_crossed_tiles = [i for i in range(0x82) if (i in world.owswaps[player][0]) != (i in ow_crossed_tiles_mask[0])]

        # update spoiler
        s = list(map(lambda x: 'O' if x not in ow_crossed_tiles else 'X', [i for i in range(0x40, 0x82)]))
        text_output = tile_swap_spoiler_table.replace('s', '%s') % (                         s[0x02],                                s[0x07],
                                                                                    s[0x00],                s[0x03],        s[0x05],
            s[0x00],        s[0x02],s[0x03],        s[0x05],        s[0x07],                 s[0x0a],                                s[0x0f],
                            s[0x0a],                                s[0x0f],
            s[0x10],s[0x11],s[0x12],s[0x13],s[0x14],s[0x15],s[0x16],s[0x17], s[0x10],s[0x11],s[0x12],s[0x13],s[0x14],s[0x15],s[0x16],s[0x17],
            s[0x18],        s[0x1a],s[0x1b],        s[0x1d],s[0x1e],
                            s[0x22],                s[0x25],                                 s[0x1a],                s[0x1d],
            s[0x28],s[0x29],s[0x2a],s[0x2b],s[0x2c],s[0x2d],s[0x2e],s[0x2f],     s[0x18],                s[0x1b],                s[0x1e],
            s[0x30],        s[0x32],s[0x33],s[0x34],s[0x35],        s[0x37],                 s[0x22],                s[0x25],
                            s[0x3a],s[0x3b],s[0x3c],                s[0x3f],
                                                                                s[0x28],s[0x29],s[0x2a],s[0x2b],s[0x2c],s[0x2d],s[0x2e],s[0x2f],
                                                                    s[0x40],                 s[0x32],s[0x33],s[0x34],                s[0x37],
                                                                                s[0x30],                                s[0x35],
                                                                    s[0x41],                 s[0x3a],s[0x3b],s[0x3c],                s[0x3f])
        world.spoiler.set_map('groups', text_output, ow_crossed_tiles, player)
    elif (limited_crossed > -1 and world.owLayout[player] != 'grid') or (world.owLayout[player] == 'vanilla' and world.owCrossed[player] == 'unrestricted'):
        crossed_candidates = list()
        for group in trimmed_groups.keys():
            (mode, wrld, _, terrain, parallel, _, _) = group
            if wrld == WorldType.Light and mode != OpenStd.Standard:
                for (forward_set, back_set) in zip(trimmed_groups[group][0], trimmed_groups[group][1]):
                    if forward_set[0] in parallel_links_new:
                        forward_parallel = [parallel_links_new[e] for e in forward_set]
                        back_parallel = [parallel_links_new[e] for e in back_set]
                        forward_combine = forward_set+forward_parallel
                        back_combine = back_set+back_parallel
                        combine_set = forward_combine+back_combine
                        
                        skip_forward = False
                        if world.owLayout[player] == 'vanilla':
                            if any(edge in force_crossed for edge in combine_set):
                                if not any(edge in force_noncrossed for edge in combine_set):
                                    if any(edge in force_crossed for edge in forward_combine):
                                        world.owcrossededges[player].extend(forward_set)
                                        count_crossed = count_crossed + 1
                                        continue
                                    else:
                                        world.owcrossededges[player].extend(back_set)
                                        count_crossed = count_crossed + 1
                                        continue
                                else:
                                    raise GenerationException('Conflict detected in force_crossed and force_noncrossed')
                            if any(edge in list(force_noncrossed)+world.owcrossededges[player] for edge in combine_set):
                                continue
                        else:
                            skip_back = False
                            if any(edge in force_crossed for edge in forward_combine):
                                if not any(edge in force_noncrossed for edge in forward_combine):
                                    world.owcrossededges[player].extend(forward_set)
                                    count_crossed = count_crossed + 1
                                    skip_forward = True
                                else:
                                    raise GenerationException('Conflict detected in force_crossed and force_noncrossed')
                            if any(edge in force_crossed for edge in back_combine):
                                if not any(edge in force_noncrossed for edge in back_combine):
                                    world.owcrossededges[player].extend(back_set)
                                    count_crossed = count_crossed + 1
                                    skip_back = True
                                else:
                                    raise GenerationException('Conflict detected in force_crossed and force_noncrossed')
                            if any(edge in list(force_noncrossed)+world.owcrossededges[player] for edge in forward_combine):
                                skip_forward = True
                            if any(edge in list(force_noncrossed)+world.owcrossededges[player] for edge in back_combine):
                                skip_back = True
                            if not skip_back:
                                if limited_crossed > -1:
                                    crossed_candidates.append(back_set)
                                elif random.randint(1, 100) <= undefined_chance:
                                    world.owcrossededges[player].extend(back_set)
                                    count_crossed = count_crossed + 1
                        if not skip_forward:
                            if limited_crossed > -1:
                                crossed_candidates.append(forward_set)
                            elif random.randint(1, 100) <= undefined_chance:
                                world.owcrossededges[player].extend(forward_set)
                                count_crossed = count_crossed + 1
        assert len(world.owcrossededges[player]) == len(set(world.owcrossededges[player])), "Same edge added to crossed edges"

        if limited_crossed > -1:
            limit = limited_crossed - count_crossed
            if limit > 1:
                random.shuffle(crossed_candidates)
                for edge_set in crossed_candidates[:limit]:
                    world.owcrossededges[player].extend(edge_set)
        assert len(world.owcrossededges[player]) == len(set(world.owcrossededges[player])), "Same edge candidate added to crossed edges"

        # TODO: Someday don't force parallels also? Keeping for now to ensure full reachability
        for edge in copy.deepcopy(world.owcrossededges[player]):
            if edge in parallel_links_new:
                if parallel_links_new[edge] not in world.owcrossededges[player]:
                    world.owcrossededges[player].append(parallel_links_new[edge])

    # after tile flip and crossed, determine edges that need to flip
    edges_to_swap = [e for e in swapped_edges+world.owcrossededges[player] if (e not in swapped_edges) or (e not in world.owcrossededges[player])]

    # whirlpool shuffle
    logging.getLogger('').debug('Shuffling whirlpools')

    if not world.owWhirlpoolShuffle[player]:
        for (_, from_whirlpool, from_region), (_, to_whirlpool, to_region) in default_whirlpool_connections:
            connect_simple(world, from_whirlpool, to_region, player)
            connect_simple(world, to_whirlpool, from_region, player)
    else:
        def connect_whirlpool(from_whirlpool, to_whirlpool):
            (from_owid, from_name, from_region) = from_whirlpool
            (to_owid, to_name, to_region) = to_whirlpool
            connect_simple(world, from_name, to_region, player)
            connect_simple(world, to_name, from_region, player)
            world.owwhirlpools[player][next(i for i, v in enumerate(whirlpool_map) if v == to_owid)] = from_owid
            world.owwhirlpools[player][next(i for i, v in enumerate(whirlpool_map) if v == from_owid)] = to_owid
            connected_whirlpools.append(tuple((from_name, to_name)))
            world.spoiler.set_whirlpool(from_name, to_name, 'both', player)

        whirlpool_map = [ 0x35, 0x0f, 0x15, 0x33, 0x12, 0x3f, 0x55, 0x7f ]
        whirlpool_candidates = [[],[]]
        connected_whirlpools = []
        world.owwhirlpools[player] = [None] * 8
        for (from_owid, from_whirlpool, from_region), (to_owid, to_whirlpool, to_region) in default_whirlpool_connections:
            if world.owCrossed[player] == 'polar' and world.owMixed[player] and from_owid == 0x55:
                # connect the 2 DW whirlpools in Polar Mixed
                connect_whirlpool((from_owid, from_whirlpool, from_region), (to_owid, to_whirlpool, to_region))
            else:
                if ((world.owCrossed[player] == 'none' or (world.owCrossed[player] == 'polar' and not world.owMixed[player])) and (world.get_region(from_region, player).type == RegionType.LightWorld)) \
                        or world.owCrossed[player] not in ['none', 'polar', 'grouped'] \
                        or (world.owCrossed[player] == 'grouped' and ((world.get_region(from_region, player).type == RegionType.LightWorld) == (from_owid not in ow_crossed_tiles))):
                    whirlpool_candidates[0].append(tuple((from_owid, from_whirlpool, from_region)))
                else:
                    whirlpool_candidates[1].append(tuple((from_owid, from_whirlpool, from_region)))
                
                if ((world.owCrossed[player] == 'none' or (world.owCrossed[player] == 'polar' and not world.owMixed[player])) and (world.get_region(to_region, player).type == RegionType.LightWorld)) \
                        or world.owCrossed[player] not in ['none', 'polar', 'grouped'] \
                        or (world.owCrossed[player] == 'grouped' and ((world.get_region(to_region, player).type == RegionType.LightWorld) == (to_owid not in ow_crossed_tiles))):
                    whirlpool_candidates[0].append(tuple((to_owid, to_whirlpool, to_region)))
                else:
                    whirlpool_candidates[1].append(tuple((to_owid, to_whirlpool, to_region)))

        # shuffle happens here
        if world.customizer:
            custom_whirlpools = world.customizer.get_whirlpools()
            if custom_whirlpools and player in custom_whirlpools:
                custom_whirlpools = custom_whirlpools[player]
                if 'two-way' in custom_whirlpools and len(custom_whirlpools['two-way']) > 0:
                    for whirlpools in whirlpool_candidates:
                        for whirlname1, whirlname2 in custom_whirlpools['two-way'].items():
                            whirl1 = next((w for w in whirlpools if w[1] == whirlname1), None)
                            whirl2 = next((w for w in whirlpools if w[1] == whirlname2), None)
                            if whirl1 and whirl2:
                                whirlpools.remove(whirl1)
                                whirlpools.remove(whirl2)
                                connect_whirlpool(whirl1, whirl2)
                            elif whirl1 != whirl2:
                                raise GenerationException('Attempting to connect whirlpools not in same pool: \'%s\' <-> \'%s\'', whirlname1, whirlname2)
                            elif any(w for w in connected_whirlpools if (whirlname1 in w) != (whirlname2 in w)):
                                raise GenerationException('Attempting to connect whirlpools already connected: \'%s\' <-> \'%s\'', whirlname1, whirlname2)
        for whirlpools in whirlpool_candidates:
            random.shuffle(whirlpools)
            while len(whirlpools):
                if len(whirlpools) % 2 == 1:
                    x=0
                connect_whirlpool(whirlpools.pop(), whirlpools.pop())

    # layout shuffle
    logging.getLogger('').debug('Shuffling overworld layout')

    if world.owLayout[player] == 'vanilla':
        # apply outstanding flips
        trimmed_groups = performSwap(trimmed_groups, edges_to_swap)
        assert len(edges_to_swap) == 0, 'Not all edges were flipped successfully: ' + ', '.join(edges_to_swap)
        
        # vanilla transitions
        groups = list(trimmed_groups.values())
        for (forward_edge_sets, back_edge_sets) in groups:
            assert len(forward_edge_sets) == len(back_edge_sets)
            for (forward_set, back_set) in zip(forward_edge_sets, back_edge_sets):
                assert len(forward_set) == len(back_set)
                for (forward_edge, back_edge) in zip(forward_set, back_set):
                    connect_two_way(world, forward_edge, back_edge, player, connected_edges)
    elif world.owLayout[player] == 'grid':
        from source.overworld.LayoutGenerator import generate_random_grid_layout

        for exitname, destname in special_screen_connections:
            connect_two_way(world, exitname, destname, player, connected_edges)

        generate_random_grid_layout(world, player, connected_edges, ow_crossed_tiles if world.owCrossed[player] == 'grouped' else [], force_noncrossed, force_crossed, limited_crossed, undefined_chance / 100)
    else:
        if world.owKeepSimilar[player] and world.owParallel[player]:
            for exitname, destname in parallelsimilar_connections:
                connect_two_way(world, exitname, destname, player, connected_edges)

        #TODO: Remove, just for testing
        for exitname, destname in test_connections:
            connect_two_way(world, exitname, destname, player, connected_edges)

        # layout shuffle
        groups = adjust_edge_groups(world, trimmed_groups, edges_to_swap, player)

        connect_custom(world, connected_edges, groups, (force_crossed, force_noncrossed), player)
        
        tries = 100
        valid_layout = False
        connected_edge_cache = connected_edges.copy()
        groups_cache = copy.deepcopy(groups)
        while not valid_layout and tries > 0:
            def remove_connected(forward_sets, back_sets):
                deleted_edges = []
                def remove_from_sets(sets):
                    s = 0
                    while s < len(sets):
                        if sets[s][0] in connected_edges:
                            deleted_edges.extend(sets[s])
                            del sets[s]
                            continue
                        s += 1
                remove_from_sets(forward_sets)
                remove_from_sets(back_sets)
                if len(forward_sets) != len(back_sets):
                    x=', '.join(deleted_edges)
                    x=0
                assert len(forward_sets) == len(back_sets), "OW edge pool is uneven due to prior connections: " + ', '.join(deleted_edges)
            
            def connect_set(forward_set, back_set, connected_edges):
                if forward_set is not None and back_set is not None:
                    assert len(forward_set) == len(back_set)
                    for (forward_edge, back_edge) in zip(forward_set, back_set):
                        connect_two_way(world, forward_edge, back_edge, player, connected_edges)
                elif forward_set is not None:
                    logging.getLogger('').warning("Edge '%s' could not find a valid connection" % forward_set[0])
                elif back_set is not None:
                    logging.getLogger('').warning("Edge '%s' could not find a valid connection" % back_set[0])
        
            connected_edges = connected_edge_cache.copy()
            groups = copy.deepcopy(groups_cache)
            groupKeys = list(groups.keys())

            if world.mode[player] == 'standard':
                subset = groupKeys[2:]
                random.shuffle(subset) # keep first 2 groups (Standard) first
                groupKeys[2:] = subset
            else:
                random.shuffle(groupKeys)

            for key in groupKeys:
                (mode, wrld, dir, terrain, parallel, count, _) = key
                (forward_edge_sets, back_edge_sets) = groups[key]
                remove_connected(forward_edge_sets, back_edge_sets)
                random.shuffle(forward_edge_sets)
                random.shuffle(back_edge_sets)

                if wrld is None and len(force_crossed) + len(force_noncrossed) > 0:
                    # divide forward/back sets into LW/DW
                    forward_lw_sets, forward_dw_sets = [], []
                    back_lw_sets, back_dw_sets = [], []
                    forward_parallel_lw_sets, forward_parallel_dw_sets = [], []
                    back_parallel_lw_sets, back_parallel_dw_sets = [], []
                    
                    def add_edgeset_to_worldsets(edge_set, sets, parallel_sets):
                        sets.append(edge_set)
                        if parallel == IsParallel.Yes:
                            parallel_sets.append([parallel_links_new[e] for e in edge_set])
                    for edge_set in forward_edge_sets:
                        if world.get_owedge(edge_set[0], player).is_lw(world):
                            add_edgeset_to_worldsets(edge_set, forward_lw_sets, forward_parallel_lw_sets)
                        else:
                            add_edgeset_to_worldsets(edge_set, forward_dw_sets, forward_parallel_dw_sets)
                    for edge_set in back_edge_sets:
                        if world.get_owedge(edge_set[0], player).is_lw(world):
                            add_edgeset_to_worldsets(edge_set, back_lw_sets, back_parallel_lw_sets)
                        else:
                            add_edgeset_to_worldsets(edge_set, back_dw_sets, back_parallel_dw_sets)
                    
                    crossed_sets = []
                    noncrossed_sets = []
                    def add_to_crossed_sets(sets, parallel_sets):
                        for i in range(0, len(sets)):
                            affected_edges = set(sets[i]+(parallel_sets[i] if parallel == IsParallel.Yes else []))
                            if sets[i] not in crossed_sets and len(set.intersection(set(force_crossed), affected_edges)) > 0:
                                crossed_sets.append(sets[i])
                            if sets[i] not in noncrossed_sets and len(set.intersection(set(force_noncrossed), affected_edges)) > 0:
                                noncrossed_sets.append(sets[i])
                            if sets[i] in crossed_sets and sets[i] in noncrossed_sets:
                                raise GenerationException('Conflict in force crossed/non-crossed definition')
                    add_to_crossed_sets(forward_lw_sets, forward_parallel_lw_sets)
                    add_to_crossed_sets(forward_dw_sets, forward_parallel_dw_sets)
                    add_to_crossed_sets(back_lw_sets, back_parallel_lw_sets)
                    add_to_crossed_sets(back_dw_sets, back_parallel_dw_sets)

                    # random connect forced crossed/noncrossed
                    def connect_forced(forced_sets, is_crossed, opposite_sets=[]):
                        c = 0
                        while c < len(forced_sets):
                            if forced_sets[c] in forward_edge_sets:
                                forward_set = forced_sets[c]
                                if (forward_set in forward_lw_sets) != is_crossed:
                                    back_set = next(s for s in back_lw_sets if s in back_edge_sets and s not in opposite_sets)
                                else:
                                    back_set = next(s for s in back_dw_sets if s in back_edge_sets and s not in opposite_sets)
                            elif forced_sets[c] in back_edge_sets:
                                back_set = forced_sets[c]
                                if (back_set in back_lw_sets) != is_crossed:
                                    forward_set = next(s for s in forward_lw_sets if s in forward_edge_sets and s not in opposite_sets)
                                else:
                                    forward_set = next(s for s in forward_dw_sets if s in forward_edge_sets and s not in opposite_sets)
                            else:
                                c = c + 1
                                continue
                            connect_set(forward_set, back_set, connected_edges)
                            remove_connected(forward_edge_sets, back_edge_sets)
                            c = c + 1
                    connect_forced(noncrossed_sets, False, crossed_sets)
                    connect_forced(crossed_sets, True)
                
                while len(forward_edge_sets) > 0 and len(back_edge_sets) > 0:
                    connect_set(forward_edge_sets[0], back_edge_sets[0], connected_edges)
                    remove_connected(forward_edge_sets, back_edge_sets)
            assert len(connected_edges) == len(default_connections) * 2, connected_edges

            valid_layout = world.accessibility[player] == 'none' or validate_layout(world, player)

            tries -= 1
        assert valid_layout, 'Could not find a valid OW layout'

    world.owsectors[player] = build_sectors(world, player)

    # flute shuffle
    logging.getLogger('').debug('Shuffling flute spots')
    shuffle_flute_spots(world, player)


def connect_custom(world, connected_edges, groups, forced, player):
    forced_crossed, forced_noncrossed = forced
    def remove_pair_from_pool(edgename1, edgename2, is_crossed):
        def add_to_unresolved(forward_set, back_set):
            if len(forward_set) > 1:
                if edgename1 in forward_set:
                    forward_set.remove(edgename1)
                    back_set.remove(edgename2)
                else:
                    back_set.remove(edgename1)
                    forward_set.remove(edgename2)
                unresolved_similars.append(tuple((forward_set, back_set, is_crossed)))
        for forward_pool, back_pool in groups.values():
            if not len(forward_pool):
                continue
            if len(forward_pool[0]) == 1:
                if [edgename1] in forward_pool:
                    if [edgename2] in back_pool:
                        forward_pool.remove([edgename1])
                        back_pool.remove([edgename2])
                        return
                    else:
                        break
                elif [edgename1] in back_pool:
                    if [edgename2] in forward_pool:
                        back_pool.remove([edgename1])
                        forward_pool.remove([edgename2])
                        return
                    else:
                        break
            else:
                forward_similar = next((x for x in forward_pool if edgename1 in x), None)
                if forward_similar:
                    back_similar = next((x for x in back_pool if edgename2 in x), None)
                    if back_similar:
                        forward_pool.remove(forward_similar)
                        back_pool.remove(back_similar)
                        add_to_unresolved(forward_similar, back_similar)
                        return
                    else:
                        break
                else:
                    back_similar = next((x for x in back_pool if edgename1 in x), None)
                    if back_similar:
                        forward_similar = next((x for x in forward_pool if edgename2 in x), None)
                        if forward_similar:
                            back_pool.remove(forward_similar)
                            forward_pool.remove(back_similar)
                            add_to_unresolved(forward_similar, back_similar)
                            return
                        else:
                            break
        for pair in unresolved_similars:
            forward_set, back_set, _ = pair
            if edgename1 in forward_set:
                if edgename2 in back_set:
                    unresolved_similars.remove(pair)
                    add_to_unresolved(forward_set, back_set)
                    return
                else:
                    break
            else:
                if edgename1 in back_set:
                    if edgename2 in forward_set:
                        unresolved_similars.remove(pair)
                        add_to_unresolved(forward_set, back_set)
                        return
                    else:
                        break
        raise GenerationException('Could not find both OW edges in same pool: \'%s\' <-> \'%s\'', edgename1, edgename2)

    if world.customizer:
        custom_edges = world.customizer.get_owedges()
        if custom_edges and player in custom_edges:
            custom_edges = custom_edges[player]
            if 'two-way' in custom_edges:
                unresolved_similars = []
                def validate_crossed_allowed(edge1, edge2, is_crossed):
                    return not ((not is_crossed and (edge1 in forced_crossed or edge2 in forced_crossed))
                            or (is_crossed and (edge1 in forced_noncrossed or edge2 in forced_noncrossed)))
                for edgename1, edgename2 in custom_edges['two-way'].items():
                    edge1 = world.get_owedge(edgename1, player)
                    edge2 = world.get_owedge(edgename2, player)
                    is_crossed = edge1.is_lw(world) != edge2.is_lw(world)
                    if not validate_crossed_allowed(edge1.name, edge2.name, is_crossed):
                        if edgename2[-1] == '*':
                            edge2 = world.get_owedge(edge2.name + '*', player)
                            is_crossed = not is_crossed
                        else:
                            raise GenerationException('Violation of force crossed rules: \'%s\' <-> \'%s\'', edgename1, edgename2)
                    if edge1.name not in connected_edges and edge2.name not in connected_edges:
                        # attempt connection
                        remove_pair_from_pool(edge1.name, edge2.name, is_crossed)
                        connect_two_way(world, edge1.name, edge2.name, player, connected_edges)
                        # resolve parallel
                        if world.owParallel[player] and edge1.name in parallel_links_new:
                            parallel_forward_edge = parallel_links_new[edge1.name]
                            parallel_back_edge = parallel_links_new[edge2.name]
                            if validate_crossed_allowed(parallel_forward_edge, parallel_back_edge, is_crossed):
                                remove_pair_from_pool(parallel_forward_edge, parallel_back_edge, is_crossed)
                            else:
                                raise GenerationException('Violation of force crossed rules on parallel connection: \'%s\' <-> \'%s\'', edgename1, edgename2)
                    elif not edge1.dest or not edge2.dest or edge1.dest.name != edge2.name or edge2.dest.name != edge1.name:
                        raise GenerationException('OW Edge already connected: \'%s\' <-> \'%s\'', edgename1, edgename2)
                # connect leftover similars
                for forward_pool, back_pool, is_crossed in unresolved_similars:
                    for (forward_edge, back_edge) in zip(forward_pool, back_pool):
                        if validate_crossed_allowed(forward_edge, back_edge, is_crossed):
                            connect_two_way(world, forward_edge, back_edge, player, connected_edges)
                        else:
                            raise GenerationException('Violation of force crossed rules on unresolved similars: \'%s\' <-> \'%s\'', forward_edge, back_edge)
                        if world.owParallel[player] and forward_edge in parallel_links_new:
                            parallel_forward_edge = parallel_links_new[forward_edge]
                            parallel_back_edge = parallel_links_new[back_edge]
                            if not validate_crossed_allowed(parallel_forward_edge, parallel_back_edge, is_crossed):
                                raise GenerationException('Violation of force crossed rules on parallel unresolved similars: \'%s\' <-> \'%s\'', forward_edge, back_edge)

def connect_two_way(world, edgename1, edgename2, player, connected_edges=None, set_spoiler=True):
    edge1 = world.get_entrance(edgename1, player)
    edge2 = world.get_entrance(edgename2, player)
    x = world.get_owedge(edgename1, player)
    y = world.get_owedge(edgename2, player)
    
    if connected_edges is not None:
        if edgename1 in connected_edges or edgename2 in connected_edges:
            if (x.dest and x.dest.name == edgename2) and (y.dest and y.dest.name == edgename1):
                return
            else:
                raise Exception('Edges \'%s\' and \'%s\' already connected elsewhere', edgename1, edgename2)
    
    # if these were already connected somewhere, remove the backreference
    if edge1.connected_region is not None:
        edge1.connected_region.entrances.remove(edge1)
    if edge2.connected_region is not None:
        edge2.connected_region.entrances.remove(edge2)

    edge1.connect(edge2.parent_region)
    edge2.connect(edge1.parent_region)
    x.dest = y
    y.dest = x

    if set_spoiler and (world.owLayout[player] != 'vanilla' or world.owMixed[player] or world.owCrossed[player] != 'none'):
        world.spoiler.set_overworld(edgename2, edgename1, 'both', player)

    if connected_edges is not None:
        connected_edges.append(edgename1)
        connected_edges.append(edgename2)
    
        # connecting parallel connections
        if world.owLayout[player] == 'vanilla' or world.owParallel[player]:
            if edgename1 in parallel_links_new:
                try:
                    parallel_forward_edge = parallel_links_new[edgename1]
                    parallel_back_edge = parallel_links_new[edgename2]
                    if not (parallel_forward_edge in connected_edges) and not (parallel_back_edge in connected_edges):
                        connect_two_way(world, parallel_forward_edge, parallel_back_edge, player, connected_edges)
                except KeyError:
                    raise KeyError('No parallel edge for edge %s' % edgename2)

def determine_forced_flips(world, tile_ow_groups, do_grouped, player):
    undefined_chance = 50
    allow_flip_sanc = do_grouped
    flipped_groups = list()
    nonflipped_groups = list()
    merged_owids = list()
    if world.customizer:
        if do_grouped:
            custom_flips = world.customizer.get_owcrossed()
        else:
            custom_flips = world.customizer.get_owtileflips()
        if custom_flips and player in custom_flips:
            custom_flips = custom_flips[player]
            forced_flips = list()
            forced_nonflips = list()
            if 'undefined_chance' in custom_flips:
                undefined_chance = custom_flips['undefined_chance']
            if not do_grouped and 'always_allow_flipped_sanctuary' in custom_flips:
                allow_flip_sanc = custom_flips['always_allow_flipped_sanctuary'] in [1, True, "True", "true"]
            if 'force_flip' in custom_flips:
                forced_flips = custom_flips['force_flip']
            if 'force_no_flip' in custom_flips:
                forced_nonflips = custom_flips['force_no_flip']
            if 'force_together' in custom_flips:
                merged_owids = list(custom_flips['force_together'].values())

            for group in tile_ow_groups:
                if any(owid in group for owid in forced_nonflips):
                    nonflipped_groups.append(group)
                if any(owid in group for owid in forced_flips):
                    flipped_groups.append(group)
            
            if undefined_chance == 0:
                nonflipped_groups.extend([g for g in tile_ow_groups if g not in flipped_groups + nonflipped_groups])
        
        # ensure any customized connections don't end up crossworld
        if world.owCrossed[player] == 'none':
            def should_merge_group(s1_owid, s2_owid):
                flip_together = (s1_owid & 0x40) == (s2_owid & 0x40)
                s1_nonflipped = any(g for g in nonflipped_groups if s1_owid in g)
                s1_flipped = any(g for g in flipped_groups if s1_owid in g)
                if s1_nonflipped or s1_flipped:
                    group = next(g for g in tile_ow_groups if s2_owid in g)
                    if s1_nonflipped == flip_together:
                        nonflipped_groups.append(group)
                    else:
                        flipped_groups.append(group)
                else:
                    s2_nonflipped = any(g for g in nonflipped_groups if s2_owid in g)
                    s2_flipped = any(g for g in flipped_groups if s2_owid in g)
                    if s2_nonflipped or s2_flipped:
                        group = next(g for g in tile_ow_groups if s1_owid in g)
                        if s2_nonflipped == flip_together:
                            nonflipped_groups.append(group)
                        else:
                            flipped_groups.append(group)
                    else:
                        s1_group = next(g for g in tile_ow_groups if s1_owid in g)
                        s2_group = next(g for g in tile_ow_groups if s2_owid in g)
                        if not flip_together:
                            if random.randint(0, 1) > 0:
                                nonflipped_groups.append(s1_group)
                                flipped_groups.append(s2_group)
                            else:
                                flipped_groups.append(s1_group)
                                nonflipped_groups.append(s2_group)
                        else:
                            return True
                return False
            if world.owWhirlpoolShuffle[player]:
                custom_whirlpools = world.customizer.get_whirlpools()
                if custom_whirlpools and player in custom_whirlpools:
                    custom_whirlpools = custom_whirlpools[player]
                    if 'two-way' in custom_whirlpools and len(custom_whirlpools['two-way']) > 0:
                        custom_whirlpools = custom_whirlpools['two-way']
                        whirlpool_map = {name:owid for wc in default_whirlpool_connections for (owid, name, _) in wc}
                        for whirl1, whirl2 in custom_whirlpools.items():
                            if [whirlpool_map[whirl1], whirlpool_map[whirl2]] not in merged_owids and should_merge_group(whirlpool_map[whirl1], whirlpool_map[whirl2]):
                                merged_owids.append([whirlpool_map[whirl1], whirlpool_map[whirl2]])
            if world.owLayout[player] != 'vanilla':
                custom_edges = world.customizer.get_owedges()
                if custom_edges and player in custom_edges:
                    custom_edges = custom_edges[player]
                    if 'two-way' in custom_edges and len(custom_edges['two-way']) > 0:
                        custom_edges = custom_edges['two-way']
                        for edgename1, edgename2 in custom_edges.items():
                            if edgename1[-1] != '*' and edgename2[-1] != '*':
                                edge1 = world.get_owedge(edgename1, player)
                                edge2 = world.get_owedge(edgename2, player)
                                if [edge1.owIndex, edge2.owIndex] not in merged_owids and should_merge_group(edge1.owIndex, edge2.owIndex):
                                    merged_owids.append([edge1.owIndex, edge2.owIndex])
    # Check if there are any groups that appear in both sets
    if any(group in flipped_groups for group in nonflipped_groups):
        raise GenerationException('Conflict found when flipping tiles')
    return flipped_groups, nonflipped_groups, undefined_chance, allow_flip_sanc, merged_owids

def shuffle_tiles(world, groups, result_list, do_grouped, forced_flips, player):
    (flipped_groups, nonflipped_groups, undefined_chance) = forced_flips
    swapped_edges = list()
    group_parity = {}
    for group_data in groups:
        group = group_data[0]
        parity = [0, 0, 0, 0, 0, 0]
        # 0: vertical
        if 0x00 in group:
            parity[0] += 1
        if 0x0f in group:
            parity[0] += 1
        if 0x80 in group:
            parity[0] -= 1
        if 0x81 in group:
            parity[0] -= 1
        # 1: horizontal land single
        if 0x1a in group:
            parity[1] -= 1
        if 0x1b in group:
            parity[1] += 1
        if 0x28 in group:
            parity[1] -= 1
        if 0x29 in group:
            parity[1] += 1
        # 2: horizontal land double
        if 0x28 in group:
            parity[2] += 1
        if 0x29 in group:
            parity[2] -= 1
        if 0x30 in group:
            parity[2] -= 1
        if 0x3a in group:
            parity[2] += 1
        # 3: horizontal water
        if 0x2d in group:
            parity[3] += 1
        if 0x80 in group:
            parity[3] -= 1
        # 4: whirlpool
        if 0x0f in group:
            parity[4] += 1
        if 0x12 in group:
            parity[4] += 1
        if 0x33 in group:
            parity[4] += 1
        if 0x35 in group:
            parity[4] += 1
        # 5: dropdown exit
        for id in [0x00, 0x02, 0x13, 0x15, 0x18, 0x22]:
            if id in group:
                parity[5] += 1
        if 0x1b in group and world.mode[player] != 'standard':
            parity[5] += 1
        if 0x1b in group and world.shuffle_ganon[player]:
            parity[5] -= 1
        group_parity[group[0]] = parity

    attempts = 1
    if 0 < undefined_chance < 100:
        # do roughly 1000 attempts at a full list
        attempts = len(groups) - len(nonflipped_groups)
        attempts = (attempts ** 1.9) + (attempts * 10) + 1
    while True:
        if attempts == 0: # expected to only occur with custom flips
            raise GenerationException('Could not find valid tile flips')

        # tile shuffle happens here
        removed = []
        for group in groups:
            if group[0] in nonflipped_groups:
                removed.append(group)
            else:
                if group[0] in flipped_groups or undefined_chance >= 100:
                    continue
                if undefined_chance == 0 or random.randint(1, 100) > undefined_chance:
                    removed.append(group)

        # save shuffled tiles to list
        new_results = [[],[],[]]
        for group in groups:
            if group not in removed:
                (owids, lw_regions, dw_regions) = group
                (exist_owids, exist_lw_regions, exist_dw_regions) = new_results
                exist_owids.extend(owids)
                exist_lw_regions.extend(lw_regions)
                exist_dw_regions.extend(dw_regions)

        parity = [sum(group_parity[group[0][0]][i] for group in groups if group not in removed) for i in range(6)]
        if world.owLayout[player] == 'grid':
            parity[1] = 0
            parity[2] = 0
        if not world.owKeepSimilar[player]:
            parity[1] += 2*parity[2]
            parity[2] = 0
        if world.owTerrain[player]:
            parity[1] += parity[3]
            parity[3] = 0
        parity[4] %= 2 # actual parity
        if (world.owCrossed[player] == 'none' or do_grouped) and parity[:5] != [0, 0, 0, 0, 0]:
            attempts -= 1
            continue
        # ensure sanc can be placed in LW in certain modes
        if not do_grouped and world.shuffle[player] in ['simple', 'restricted', 'full', 'district'] and not world.is_dark_chapel_start(player) and (world.doorShuffle[player] != 'crossed' or world.intensity[player] < 3 or world.mode[player] == 'standard'):
            free_dw_drops = parity[5] + (1 if world.shuffle_ganon[player] else 0)
            free_drops = 6 + (1 if world.mode[player] != 'standard' else 0) + (1 if world.shuffle_ganon[player] else 0)
            if free_dw_drops == free_drops:
                attempts -= 1
                continue
        break

    (exist_owids, exist_lw_regions, exist_dw_regions) = result_list
    exist_owids.extend(new_results[0])
    exist_lw_regions.extend(new_results[1])
    exist_dw_regions.extend(new_results[2])

    # replace LW edges with DW
    if world.owCrossed[player] == 'none' or do_grouped:
        # in polar, the actual edge connections remain vanilla
        def getSwappedEdges(world, lst, player):
            for regionname in lst:
                region = world.get_region(regionname, player)
                for exit in region.exits:
                    if exit.spot_type == 'OWEdge':
                        swapped_edges.append(exit.name)

        getSwappedEdges(world, result_list[1], player)
        getSwappedEdges(world, result_list[2], player)

    return swapped_edges

def define_tile_groups(world, do_grouped, player):
    groups = [[i, i + 0x40] for i in range(0x40)]

    def get_group(id):
        for group in groups:
            if id in group:
                return group

    def merge_groups(tile_links):
        for link in tile_links:
            merged_group = []
            for id in link:
                if id not in merged_group:
                    group = get_group(id)
                    groups.remove(group)
                    merged_group += group
            groups.append(merged_group)

    def can_shuffle_group(group):
        # escape sequence should stay normal in standard
        if world.mode[player] == 'standard' and (0x1b in group or 0x2b in group or 0x2c in group):
            return False
        
        # sanctuary/chapel should not be flipped if S+Q guaranteed to output on that screen
        if 0x13 in group and not allow_flip_sanc and ((world.shuffle[player] in ['vanilla', 'dungeonssimple', 'dungeonsfull', 'district'] \
                    and (world.mode[player] in ['standard', 'inverted'] or world.doorShuffle[player] not in ['partitioned', 'crossed'] \
                        or world.intensity[player] < 3)) or (world.shuffle[player] in ['lite', 'lean'] and world.is_dark_chapel_start(player))):
            return False
        
        return True

    for i in [0x00, 0x03, 0x05, 0x18, 0x1b, 0x1e, 0x30, 0x35]:
        groups.remove(get_group(i + 1))
        groups.remove(get_group(i + 8))
        groups.remove(get_group(i + 9))
    groups.append([0x80])
    groups.append([0x81])

    # hyrule castle and sanctuary connector
    if world.shuffle[player] in ['vanilla', 'district'] or (world.mode[player] == 'standard' and world.shuffle[player] in ['dungeonssimple', 'dungeonsfull']):
        merge_groups([[0x13, 0x14, 0x1b]])

    # sanctuary and grave connector
    if world.shuffle[player] in ['dungeonssimple', 'dungeonsfull', 'simple', 'restricted', 'full', 'lite', 'district']:
        merge_groups([[0x13, 0x14]])

    # cross-screen connector
    if world.shuffle[player] in ['vanilla', 'dungeonssimple', 'dungeonsfull', 'simple', 'district']:
        merge_groups([[0x03, 0x0a], [0x28, 0x29]])

    # turtle rock connector
    if world.shuffle[player] in ['vanilla', 'dungeonssimple', 'simple', 'restricted', 'district']:
        merge_groups([[0x05, 0x07]])

    # special screens
    if world.owLayout[player] != 'wild' and (world.owCrossed[player] == 'none' or do_grouped):
        merge_groups([[0x00, 0x2d, 0x80], [0x0f, 0x81]])

    # remaining non-parallel edges
    if world.owLayout[player] == 'vanilla' and (world.owCrossed[player] == 'none' or do_grouped):
        merge_groups([[0x1a, 0x1b], [0x28, 0x29], [0x30, 0x3a]])

    # special case: non-parallel keep similar
    if world.owLayout[player] == 'wild' and world.owParallel[player] and world.owKeepSimilar[player] and (world.owCrossed[player] == 'none' or do_grouped):
        merge_groups([[0x28, 0x29]])

    # whirlpool screens
    if not world.owWhirlpoolShuffle[player] and (world.owCrossed[player] == 'none' or do_grouped):
        merge_groups([[0x0f, 0x35], [0x12, 0x15, 0x33, 0x3f]])

    # customizer adjustments
    flipped_groups, nonflipped_groups, undefined_chance, allow_flip_sanc, merged_owids = determine_forced_flips(world, groups, do_grouped, player)
    for owids in merged_owids:
        merge_groups([owids])

    tile_groups = []
    for group in groups:
        if can_shuffle_group(group):
            lw_regions = []
            dw_regions = []
            for id in group:
                (lw_regions if id < 0x40 or id >= 0x80 else dw_regions).extend(OWTileRegions.inverse[id])
            tile_groups.append((group, lw_regions, dw_regions))

    random.shuffle(tile_groups)
    return tile_groups, flipped_groups, nonflipped_groups, undefined_chance, allow_flip_sanc

def remove_reserved(world, groupedlist, connected_edges, player):
    new_grouping = {}
    for group in groupedlist.keys():
        new_grouping[group] = ([], [])

    for group in groupedlist.keys():
        (forward_edges, back_edges) = groupedlist[group]

        # remove edges already connected (thru plando and other forced connections)
        for edge in connected_edges:
            forward_edges = list(list(filter((edge).__ne__, i)) for i in forward_edges)
            back_edges = list(list(filter((edge).__ne__, i)) for i in back_edges)

        forward_edges = list(filter(([]).__ne__, forward_edges))
        back_edges = list(filter(([]).__ne__, back_edges))

        (exist_forward_edges, exist_back_edges) = new_grouping[group]
        exist_forward_edges.extend(forward_edges)
        exist_back_edges.extend(back_edges)
        if len(exist_forward_edges) > 0:
            new_grouping[group] = (exist_forward_edges, exist_back_edges)

    return new_grouping

def reorganize_groups(world, groups, player):
    def get_group_key(group):
        #(std, region, axis, terrain, parallel, count) = group
        new_group = list(group)
        if world.mode[player] != "standard":
            new_group[0] = None
        if world.owTerrain[player]:
            new_group[3] = None
        if not world.owParallel[player]:
            new_group[4] = None
        if not world.owKeepSimilar[player]:
            new_group[5] = None
        return tuple(new_group)

    # predefined shuffle groups get reorganized here
    # this restructures the candidate pool based on the chosen settings
    for grouping in (groups,):
        new_grouping = {}

        for group in grouping.keys():
            new_grouping[get_group_key(group)] = ([], [])
        
        for group in grouping.keys():
            new_group = get_group_key(group)
            (forward_edges, back_edges) = grouping[group]
            if not world.owKeepSimilar[player]:
                forward_edges = [[i] for l in forward_edges for i in l]
                back_edges = [[i] for l in back_edges for i in l]
            (exist_forward_edges, exist_back_edges) = new_grouping[new_group]
            exist_forward_edges.extend(forward_edges)
            exist_back_edges.extend(back_edges)
            new_grouping[new_group] = (exist_forward_edges, exist_back_edges)

        return new_grouping

def adjust_edge_groups(world, trimmed_groups, edges_to_swap, player):
    groups = defaultdict(lambda: ([],[]))
    limited_crossed = False
    custom_groups = dict()
    if world.customizer:
        custom_crossed = world.customizer.get_owcrossed()
        limited_crossed = custom_crossed and (player in custom_crossed) and ('limit_crossed' in custom_crossed[player])
        limited_crossed = limited_crossed and world.owCrossed[player] == 'unrestricted'
        custom_edge_groups = world.customizer.get_owedges()
        if custom_edge_groups and player in custom_edge_groups:
            custom_edge_groups = custom_edge_groups[player]
            if 'groups' in custom_edge_groups:
                custom_groups = dict(custom_edge_groups['groups'])
                for name, edges in custom_groups.items():
                    custom_groups[name] = [world.get_owedge(e, player).name if e[-1] == '*' else e for e in edges]
    for (key, group) in trimmed_groups.items():
        (mode, wrld, dir, terrain, parallel, count, custom) = key
        if mode == OpenStd.Standard:
            groups[key] = group
        else:
            if world.owCrossed[player] == 'unrestricted' and not limited_crossed:
                groups[(mode, None, dir, terrain, parallel, count, custom)][0].extend(group[0])
                groups[(mode, None, dir, terrain, parallel, count, custom)][1].extend(group[1])
            else:
                for i in range(2):
                    for edge_set in group[i]:
                        new_world = int(wrld)
                        if edge_set[0] in edges_to_swap:
                            new_world += 1
                        groups[(mode, WorldType(new_world % 2), dir, terrain, parallel, count, custom)][i].append(edge_set)
    for (key, group) in groups.copy().items():
        (mode, wrld, dir, terrain, parallel, count, custom) = key
        if mode != OpenStd.Standard:
            for group_name, edges in custom_groups.items():
                for i in range(0, 2):
                    matches = [s for s in groups[key][i] if any(e in s for e in edges)]
                    if len(matches) > 0:
                        for m in matches:
                            groups[key][i].remove(m)
                        groups[(mode, wrld, dir, terrain, parallel, count, group_name)][i].extend(matches)
    return groups

def get_mirror_exit_name(from_region, to_region):
    if from_region in mirror_connections and to_region in mirror_connections[from_region]:
        if len(mirror_connections[from_region]) == 1:
            return f'Mirror From {from_region}'
        else:
            return f'Mirror To {to_region}'
    return None

def get_mirror_edges(world, region, player):
    mirror_exits = list()
    if (world.mode[player] != 'inverted') == (region.type == RegionType.DarkWorld):
        # get mirror edges leaving the region
        if region.name in mirror_connections:
            for dest_region_name in mirror_connections[region.name]:
                mirror_exits.append(tuple([get_mirror_exit_name(region.name, dest_region_name), dest_region_name]))
    else:
        # get mirror edges leading into the region
        owid = OWTileRegions[region.name]
        for other_world_region_name in OWTileRegions.inverse[(owid + 0x40) % 0x80]:
            if other_world_region_name in mirror_connections:
                for dest_region_name in mirror_connections[other_world_region_name]:
                    if dest_region_name == region.name:
                        mirror_exits.append(tuple([get_mirror_exit_name(other_world_region_name, region.name), region.name]))
    return mirror_exits

def create_dynamic_mirror_exits(world, player):
    mirror_exits = set()
    for region in (r for r in world.regions if r.player == player and r.name not in ['Zoras Domain', 'Master Sword Meadow', 'Hobo Bridge']):
        if region.type == (RegionType.DarkWorld if world.mode[player] != 'inverted' else RegionType.LightWorld):
            if region.name in mirror_connections:
                for region_dest_name in mirror_connections[region.name]:
                    exitname = get_mirror_exit_name(region.name, region_dest_name)
                    
                    assert exitname not in mirror_exits, f'Mirror Exit with name already exists: {exitname}'

                    exit = Entrance(region.player, exitname, region)
                    exit.spot_type = 'Mirror'
                    to_region = world.get_region(region_dest_name, player)
                    if region.terrain == Terrain.Water or to_region.terrain == Terrain.Water:
                        exit.access_rule = lambda state: state.has('Flippers', player) and state.has_Pearl(player) and state.has_Mirror(player)
                    else:
                        exit.access_rule = lambda state: state.has_Mirror(player)
                    exit.connect(to_region)
                    region.exits.append(exit)

                    mirror_exits.add(exitname)
    world.initialize_regions()

def categorize_world_regions(world, player):
    for type in OWExitTypes:
        for exitname in OWExitTypes[type]:
            world.get_entrance(exitname, player).spot_type = type
    
    mark_light_dark_world_regions(world, player)

def update_world_regions(world, player):
    if world.owMixed[player]:
        for name in world.owswaps[player][1]:
            world.get_region(name, player).type = RegionType.DarkWorld
        for name in world.owswaps[player][2]:
            world.get_region(name, player).type = RegionType.LightWorld

def can_reach_smith(world, player):
    from Items import ItemFactory
    from BaseClasses import CollectionState
    
    def explore_region(region_name, region=None):
        nonlocal found
        explored_regions.append(region_name)
        if not found:
            if not region:
                region = world.get_region(region_name, player)
            for exit in region.exits:
                if not found and exit.connected_region is not None:
                    if starting_flute and exit.spot_type == 'Flute':
                        for flutespot in exit.connected_region.exits:
                            if flutespot.connected_region and flutespot.connected_region.name not in explored_regions:
                                explore_region(flutespot.connected_region.name, flutespot.connected_region)
                    elif exit.connected_region.name == 'Blacksmiths Hut' and exit.access_rule(blank_state):
                        found = True
                        return
                    elif exit.connected_region.name not in explored_regions and exit.name != "Dig Game To Ledge Drop":
                        if (region.type == RegionType.Dungeon and exit.connected_region.name.endswith(' Portal')) \
                            or (exit.connected_region.type in [RegionType.LightWorld, RegionType.DarkWorld] \
                                and exit.access_rule(blank_state)):
                            explore_region(exit.connected_region.name, exit.connected_region)
    
    blank_state = CollectionState(world)
    if world.mode[player] == 'standard':
        blank_state.collect(ItemFactory('Zelda Delivered', player), True)
    if world.logic[player] in ['noglitches', 'minorglitches'] and not world.is_tile_swapped(0x29, player):
        blank_state.collect(ItemFactory('Titans Mitts', player), True)
        blank_state.collect(ItemFactory('Moon Pearl', player), True)
    if not world.bombbag[player]:
        blank_state.collect(ItemFactory('Farmable Bombs', player), True)
    blank_state.collect(ItemFactory('Farmable Rupees', player), True)
    
    found = False
    explored_regions = list()
    starting_flute = any(map(lambda i: i.name == 'Ocarina (Activated)' and i.player == player, world.precollected_items))
    if not world.is_bombshop_start(player):
        start_region = 'Links House'
    else:
        start_region = 'Big Bomb Shop'
    explore_region(start_region)
    if not found:
        if not world.is_dark_chapel_start(player):
            if world.intensity[player] >= 3 and world.doorShuffle[player] != 'vanilla':
                sanc_mirror = world.get_entrance('Sanctuary Mirror Route', player)
                explore_region(sanc_mirror.connected_region.name, sanc_mirror.connected_region)
            else:
                explore_region('Sanctuary')
        else:
            explore_region('Dark Sanctuary Hint')
    return found

def build_sectors(world, player):
    from Main import copy_world_premature
    from OWEdges import OWTileRegions
    
    # perform accessibility check on duplicate world
    for p in range(1, world.players + 1):
        world.key_logic[p] = {}
    base_world = copy_world_premature(world, player, create_flute_exits=False)
    
    # build lists of contiguous regions accessible with full inventory (excl portals/mirror/flute/entrances)
    regions = list(OWTileRegions.copy().keys())
    sectors = list()
    while(len(regions) > 0):
        explored_regions = build_accessible_region_list(base_world, regions[0], player, False, False, False, False)
        regions = [r for r in regions if r not in explored_regions]
        unique_regions = [_ for i in range(len(sectors)) for _ in sectors[i]]
        if (any(r in unique_regions for r in explored_regions)):
            for s in range(len(sectors)):
                if (any(r in sectors[s] for r in explored_regions)):
                    sectors[s] = list(dict.fromkeys(list(sectors[s]) + list(explored_regions)))
                    break
        else:
            sectors.append(explored_regions)
    
    # remove water regions if Flippers not in starting inventory
    if not any(map(lambda i: i.name == 'Flippers', world.precollected_items)):
        for s in range(len(sectors)):
            terrains = list()
            for regionname in sectors[s]:
                region = world.get_region(regionname, player)
                if region.terrain == Terrain.Land:
                    terrains.append(regionname)
            sectors[s] = terrains
    
    # within each group, split into contiguous regions accessible only with starting inventory
    for s in range(len(sectors)):
        regions = list(sectors[s]).copy()
        sectors2 = list()
        while(len(regions) > 0):
            explored_regions = build_accessible_region_list(base_world, regions[0], player, False, False, True, False)
            regions = [r for r in regions if r not in explored_regions]
            unique_regions = [_ for i in range(len(sectors2)) for _ in sectors2[i]]
            if (any(r in unique_regions for r in explored_regions)):
                for s2 in range(len(sectors2)):
                    if (any(r in sectors2[s2] for r in explored_regions)):
                        sectors2[s2] = list(dict.fromkeys(sectors2[s2] + explored_regions))
                        break
            else:
                sectors2.append(explored_regions)
        sectors[s] = sectors2
    
    return sectors

def build_accessible_region_list(world, start_region, player, build_copy_world=False, cross_world=False, region_rules=True, ignore_ledges=False, restrictive_follower=False):
    from BaseClasses import CollectionState
    from Main import copy_world_premature
    from Items import ItemFactory
    from Utils import stack_size3a
    
    def explore_region(region_name, region=None):
        if stack_size3a() > 500:
            raise GenerationException(f'Infinite loop detected for "{start_region}" located at \'build_accessible_region_list\'')

        explored_regions.append(region_name)
        if not region:
            region = base_world.get_region(region_name, player)
        for exit in region.exits:
            if exit.connected_region is not None:
                if starting_flute and exit.spot_type == 'Flute':
                    fluteregion = exit.connected_region
                    for flutespot in fluteregion.exits:
                        if flutespot.connected_region and flutespot.connected_region.name not in explored_regions:
                            explore_region(flutespot.connected_region.name, flutespot.connected_region)
                elif exit.connected_region.name not in explored_regions \
                        and (exit.connected_region.type == region.type or exit.name in OWExitTypes['OWEdge'] 
                            or (cross_world and exit.name in (OWExitTypes['Portal'] + OWExitTypes['Mirror']))) \
                        and (not region_rules or exit.access_rule(blank_state)) \
                        and (not restrictive_follower or exit.spot_type != 'OWG') \
                        and (not ignore_ledges or not (exit.spot_type == 'OWG' or exit.name in OWExitTypes['Ledge'])):
                    explore_region(exit.connected_region.name, exit.connected_region)
    
    if build_copy_world:
        for p in range(1, world.players + 1):
            world.key_logic[p] = {}
        base_world = copy_world_premature(world, player, create_flute_exits=True)
        base_world.override_bomb_check = True
    else:
        base_world = world
    
    connect_simple(base_world, 'Links House S&Q', start_region, player)
    blank_state = CollectionState(base_world)
    if base_world.mode[player] == 'standard':
        blank_state.collect(ItemFactory('Zelda Delivered', player), True)
    explored_regions = list()
    starting_flute = any(map(lambda i: i.name == 'Ocarina (Activated)' and i.player == player, base_world.precollected_items))
    explore_region(start_region)

    return explored_regions

def validate_layout(world, player):
    entrance_connectors = {
        'East Death Mountain (Bottom)':       ['East Death Mountain (Top East)'],
        'Kakariko Suburb Area':               ['Maze Race Ledge'],
        'Maze Race Ledge':                    ['Kakariko Suburb Area'],
        'Desert Area':                        ['Desert Ledge', 'Desert Mouth'],
        'East Dark Death Mountain (Top)':     ['Dark Death Mountain Floating Island'],
        'East Dark Death Mountain (Bottom)':  ['East Dark Death Mountain (Top)'],
        'Turtle Rock Area':                   ['Dark Death Mountain Ledge',
                                               'Dark Death Mountain Isolated Ledge'],
        'Dark Death Mountain Ledge':          ['Turtle Rock Area'],
        'Dark Death Mountain Isolated Ledge': ['Turtle Rock Area'],
        'Mountain Pass Entry':                ['West Death Mountain (Bottom)'],
        'Mountain Pass Ledge':                ['West Death Mountain (Bottom)'],
        'West Death Mountain (Bottom)':       ['Mountain Pass Ledge'],
        'Bumper Cave Entry':                  ['Bumper Cave Ledge']
    }
    sane_connectors = {
        # guaranteed dungeon access
        'Skull Woods Forest':                 ['Skull Woods Forest (West)'],
        'Skull Woods Forest (West)':          ['Skull Woods Forest'],
        # guaranteed dropdown access
        'Graveyard Area':                     ['Sanctuary Area'],
        'Pyramid Area':                       ['Pyramid Exit Ledge']
    }

    # TODO: Find a better source for the below lists, original sourced was deprecated
    from source.overworld.EntranceData import default_dungeon_connections, default_connector_connections, default_item_connections, default_shop_connections, default_drop_connections, default_dropexit_connections

    dungeon_entrances = list(zip(*default_dungeon_connections + [('Ganons Tower', '')]))[0]
    connector_entrances = list(zip(*default_connector_connections))[0]
    item_entrances = list(zip(*default_item_connections))[0]
    shop_entrances = list(zip(*default_shop_connections))[0]
    drop_entrances = list(zip(*default_drop_connections + default_dropexit_connections))[0]
    flute_in_pool = True if player not in world.customitemarray else any(i for i, n in world.customitemarray[player].items() if i == 'flute' and n > 0)

    def explore_region(region_name, region=None):
        if region_name in explored_regions:
            return
        explored_regions.add(region_name)
        if not region:
            region = world.get_region(region_name, player)
        for exit in region.exits:
            if exit.connected_region is not None and exit.connected_region.name not in explored_regions \
                    and exit.connected_region.type in [RegionType.LightWorld, RegionType.DarkWorld]:
                explore_region(exit.connected_region.name, exit.connected_region)
        if world.shuffle[player] in ['vanilla', 'dungeonssimple', 'dungeonsfull', 'simple'] \
                and region_name in entrance_connectors:
            for dest_region in entrance_connectors[region_name]:
                if dest_region not in explored_regions:
                    explore_region(dest_region)
        if world.shuffle[player] not in ['district', 'insanity'] and region_name in sane_connectors:
            for dest_region in sane_connectors[region_name]:
                if dest_region not in explored_regions:
                    explore_region(dest_region)

    explored_regions = set()

    if world.shuffle[player] in ['vanilla', 'dungeonssimple', 'dungeonsfull'] or not world.shufflelinks[player]:
        if not world.is_bombshop_start(player):
            start_region = 'Links House Area'
        else:
            start_region = 'Big Bomb Shop Area'
        explore_region(start_region)

    if world.shuffle[player] in ['vanilla', 'dungeonssimple', 'dungeonsfull', 'lite', 'lean'] and world.is_dark_chapel_start(player):
        start_region = 'Dark Chapel Area'
        explore_region(start_region)

    if flute_in_pool:
        if not world.is_tile_swapped(0x30, player):
            start_region = 'Desert Teleporter Ledge'
        else:
            start_region = 'Mire Teleporter Ledge'
        explore_region(start_region)
    
    if not world.is_tile_swapped(0x1b, player):
        start_region = 'Pyramid Area'
    else:
        start_region = 'Hyrule Castle Ledge'
    explore_region(start_region)

    unreachable_regions = {}
    unreachable_count = -1
    while unreachable_count != len(unreachable_regions):
        # find unreachable regions
        unreachable_regions = {}
        for region_name in list(OWTileRegions.keys()):
            if region_name not in explored_regions and region_name not in isolated_regions:
                region = world.get_region(region_name, player)
                unreachable_regions[region_name] = region
        
        # loop thru unreachable regions to check if some can be excluded
        unreachable_count = len(unreachable_regions)
        for region_name in reversed(unreachable_regions):
            # check if can be accessed flute
            if flute_in_pool and unreachable_regions[region_name].type == (RegionType.LightWorld if world.mode[player] != 'inverted' else RegionType.DarkWorld):
                owid = OWTileRegions[region_name]
                if owid < 0x80 and owid % 0x40 in flute_data and region_name in flute_data[owid % 0x40][0]:
                    if world.owFluteShuffle[player] != 'vanilla' or owid % 0x40 in default_flute_connections:
                        unreachable_regions.pop(region_name)
                        explore_region(region_name)
                        break
            # check if entrances in region could be used to access region
            if world.shuffle[player] != 'vanilla':
                # TODO: For District ER, we need to check if there is a dropdown or connector that is able to connect
                for entrance in [e for e in unreachable_regions[region_name].exits if e.spot_type == 'Entrance']:
                    if (entrance.name == 'Links House' and ((not world.is_bombshop_start(player) and not world.shufflelinks[player]) or world.shuffle[player] in ['dungeonssimple', 'dungeonsfull', 'lite', 'lean'])) \
                            or (entrance.name == 'Big Bomb Shop' and ((world.is_bombshop_start(player) and not world.shufflelinks[player]) or world.shuffle[player] in ['dungeonssimple', 'dungeonsfull', 'lite', 'lean'])) \
                            or (entrance.name == 'Ganons Tower' and (not world.is_atgt_swapped(player) and not world.shuffle_ganon[player])) \
                            or (entrance.name == 'Agahnims Tower' and (world.is_atgt_swapped(player) and not world.shuffle_ganon[player])) \
                            or (entrance.name in ['Skull Woods First Section Door', 'Skull Woods Second Section Door (East)', 'Skull Woods Second Section Door (West)'] and world.shuffle[player] not in ['district', 'insanity']) \
                            or (entrance.name == 'Tavern North' and not world.shuffletavern[player]):
                        continue # these are fixed entrances and cannot be used for gaining access to region
                    if entrance.name not in drop_entrances \
                            and ((entrance.name in dungeon_entrances and world.shuffle[player] not in ['dungeonssimple', 'simple', 'restricted']) \
                                or (entrance.name in connector_entrances and world.shuffle[player] not in ['dungeonssimple', 'dungeonsfull', 'simple']) \
                                or (entrance.name in item_entrances + (tuple() if world.shopsanity[player] else shop_entrances) and world.shuffle[player] not in ['dungeonssimple', 'dungeonsfull', 'lite', 'lean'])):
                        unreachable_regions.pop(region_name)
                        explore_region(region_name)
                        break
                if unreachable_count != len(unreachable_regions):
                    break

    if not flute_in_pool:
        unreachable_regions.pop('Desert Teleporter Ledge')
        unreachable_regions.pop('Mire Teleporter Ledge')

    if len(unreachable_regions):
        return False

    return True

def get_separate_ow_areas(world, player):
    """
    Returns a list of separated areas in the overworld layout.
    It looks at the distinct connected components when only considering
    OW edge and whirlpool connections (no entrances, portals, mirror, or flute).
    Uses Union-Find to handle directed edges properly (treats them as undirected).
    """
    parent = {}

    def find(x):
        if x not in parent:
            parent[x] = x
        if parent[x] != x:
            parent[x] = find(parent[x]) # Path compression
        return parent[x]

    def union(x, y):
        root_x = find(x)
        root_y = find(y)
        if root_x != root_y:
            parent[root_y] = root_x

    all_regions = set(OWTileRegions.keys()) - set(isolated_regions)
    considered_exit_spot_types = set(['OpenTerrain', 'OWTerrain', 'Ledge', 'OWEdge', 'Whirlpool'])

    # Initialize all regions in Union-Find
    for region_name in all_regions:
        find(region_name)

    # Build connections by examining all edges (treating directed as undirected)
    for region_name in all_regions:
        region = world.get_region(region_name, player)
        for exit in region.exits:
            if exit.spot_type in considered_exit_spot_types and exit.connected_region is not None and exit.connected_region.name in all_regions:
                union(region_name, exit.connected_region.name)

    # Group regions by their root
    areas = {}
    for region_name in all_regions:
        root = find(region_name)
        if root not in areas:
            areas[root] = []
        areas[root].append(region_name)

    return list(areas.values())

test_connections = [
                    #('Links House ES', 'Octoballoon WS'),
                    #('Links House NE', 'Lost Woods Pass SW')
                    ]

# these are connections that cannot be shuffled and always exist. They link together separate parts of the world we need to divide into regions
mandatory_connections = [
    ('Old Man S&Q', 'Old Man House'),

    # Intra-tile OW Connections
    ('Lost Woods Bush (West)', 'Lost Woods East Area'), #pearl
    ('Lost Woods Bush (East)', 'Lost Woods West Area'), #pearl
    ('West Death Mountain Drop', 'West Death Mountain (Bottom)'),
    ('Spectacle Rock Ledge Drop', 'West Death Mountain (Top)'),
    ('Old Man Drop Off', 'Old Man Drop Off'),
    ('DM Hammer Bridge (West)', 'East Death Mountain (Top East)'), #hammer
    ('DM Hammer Bridge (East)', 'East Death Mountain (Top West)'), #hammer
    ('EDM To Spiral Ledge Drop', 'Spiral Cave Ledge'),
    ('EDM Ledge Drop', 'East Death Mountain (Bottom)'),
    ('Spiral Ledge Drop', 'East Death Mountain (Bottom)'),
    ('Fairy Ascension Ledge Drop', 'Fairy Ascension Plateau'),
    ('Fairy Ascension Plateau Ledge Drop', 'East Death Mountain (Bottom)'),
    ('Fairy Ascension Rocks (Inner)', 'East Death Mountain (Bottom)'), #mitts
    ('Fairy Ascension Rocks (Outer)', 'Fairy Ascension Plateau'), #mitts
    ('DM Broken Bridge (West)', 'East Death Mountain (Bottom)'), #hookshot
    ('DM Broken Bridge (East)', 'East Death Mountain (Bottom Left)'), #hookshot
    ('TR Pegs Ledge Entry', 'Death Mountain TR Pegs Ledge'), #mitts
    ('TR Pegs Ledge Leave', 'Death Mountain TR Pegs Area'), #mitts
    ('Mountain Pass Rock (Outer)', 'Mountain Pass Entry'), #glove
    ('Mountain Pass Rock (Inner)', 'Mountain Pass Area'), #glove
    ('Mountain Pass Entry Ledge Drop', 'Mountain Pass Area'),
    ('Mountain Pass Ledge Drop', 'Mountain Pass Area'),
    ('Zora Waterfall Landing', 'Zora Waterfall Area'),
    ('Zora Waterfall Water Drop', 'Zora Waterfall Water'), #flippers
    ('Zora Waterfall Water Entry', 'Zora Waterfall Water'), #flippers
    ('Zora Waterfall Approach', 'Zora Waterfall Entryway'), #flippers
    ('Lost Woods Pass Hammer (North)', 'Lost Woods Pass Portal Area'), #hammer
    ('Lost Woods Pass Hammer (South)', 'Lost Woods Pass East Top Area'), #hammer
    ('Lost Woods Pass Rock (North)', 'Lost Woods Pass East Bottom Area'), #mitts
    ('Lost Woods Pass Rock (South)', 'Lost Woods Pass Portal Area'), #mitts
    ('Bonk Rock Ledge Drop', 'Sanctuary Area'),
    ('Graveyard Ledge Drop', 'Graveyard Area'),
    ('Kings Grave Rocks (Outer)', 'Kings Grave Area'), #mitts
    ('Kings Grave Rocks (Inner)', 'Graveyard Area'), #mitts
    ('River Bend Water Drop', 'River Bend Water'), #flippers
    ('River Bend East Water Drop', 'River Bend Water'), #flippers
    ('River Bend West Pier', 'River Bend Area'),
    ('River Bend East Pier', 'River Bend East Bank'),
    ('Potion Shop Water Drop', 'Potion Shop Water'), #flippers
    ('Potion Shop Northeast Water Drop', 'Potion Shop Water'), #flippers
    ('Potion Shop Rock (South)', 'Potion Shop Northeast'), #glove
    ('Potion Shop Rock (North)', 'Potion Shop Area'), #glove
    ('Zora Approach Water Drop', 'Zora Approach Water'), #flippers
    ('Zora Approach Rocks (West)', 'Zora Approach Ledge'), #mitts/boots
    ('Zora Approach Rocks (East)', 'Zora Approach Area'), #mitts/boots
    ('Zora Approach Bottom Ledge Drop', 'Zora Approach Ledge'),
    ('Zora Approach Ledge Drop', 'Zora Approach Area'),
    ('Kakariko Southwest Bush (North)', 'Kakariko Southwest'), #pearl
    ('Kakariko Southwest Bush (South)', 'Kakariko Village'), #pearl
    ('Kakariko Yard Bush (South)', 'Kakariko Bush Yard'), #pearl
    ('Kakariko Yard Bush (North)', 'Kakariko Village'), #pearl
    ('Hyrule Castle Southwest Bush (North)', 'Hyrule Castle Southwest'), #pearl
    ('Hyrule Castle Southwest Bush (South)', 'Hyrule Castle Area'), #pearl
    ('Hyrule Castle Courtyard Bush (North)', 'Hyrule Castle Courtyard'), #pearl
    ('Hyrule Castle Courtyard Bush (South)', 'Hyrule Castle Courtyard Northeast'), #pearl
    ('Hyrule Castle Main Gate (South)', 'Hyrule Castle Courtyard'), #aga+mirror
    ('Hyrule Castle Main Gate (North)', 'Hyrule Castle Area'), #aga+mirror
    ('Hyrule Castle Ledge Drop', 'Hyrule Castle Area'),
    ('Hyrule Castle Ledge Courtyard Drop', 'Hyrule Castle Courtyard'),
    ('Hyrule Castle East Rock (Inner)', 'Hyrule Castle East Entry'), #glove
    ('Hyrule Castle East Rock (Outer)', 'Hyrule Castle Area'), #glove
    ('Wooden Bridge Bush (South)', 'Wooden Bridge Northeast'), #pearl
    ('Wooden Bridge Bush (North)', 'Wooden Bridge Area'), #pearl
    ('Wooden Bridge Water Drop', 'Wooden Bridge Water'), #flippers
    ('Wooden Bridge Northeast Water Drop', 'Wooden Bridge Water'), #flippers
    ('Blacksmith Ledge Peg (West)', 'Blacksmith Ledge'), #hammer
    ('Blacksmith Ledge Peg (East)', 'Blacksmith Area'), #hammer
    ('Maze Race Game', 'Maze Race Prize'), #pearl
    ('Maze Race Ledge Drop', 'Maze Race Area'),
    ('Stone Bridge (Southbound)', 'Stone Bridge South Area'),
    ('Stone Bridge (Northbound)', 'Stone Bridge North Area'),
    ('Desert Statue Move', 'Desert Stairs'), #book
    ('Desert Ledge Drop', 'Desert Area'),
    ('Desert Ledge Rocks (Outer)', 'Desert Ledge Keep'), #glove
    ('Desert Ledge Rocks (Inner)', 'Desert Ledge'), #glove
    ('Checkerboard Ledge Drop', 'Desert Area'),
    ('Desert Mouth Drop', 'Desert Area'),
    ('Desert Teleporter Drop', 'Desert Area'),
    ('Bombos Tablet Drop', 'Desert Area'),
    ('Flute Boy Bush (North)', 'Flute Boy Approach Area'), #pearl
    ('Flute Boy Bush (South)', 'Flute Boy Bush Entry'), #pearl
    ('C Whirlpool Water Entry', 'C Whirlpool Water'), #flippers
    ('C Whirlpool Landing', 'C Whirlpool Area'),
    ('C Whirlpool Rock (Bottom)', 'C Whirlpool Outer Area'), #glove
    ('C Whirlpool Rock (Top)', 'C Whirlpool Area'), #glove
    ('C Whirlpool Pegs (Outer)', 'C Whirlpool Portal Area'), #hammer
    ('C Whirlpool Pegs (Inner)', 'C Whirlpool Area'), #hammer
    ('Statues Water Entry', 'Statues Water'), #flippers
    ('Statues Landing', 'Statues Area'),
    ('Lake Hylia Water Drop', 'Lake Hylia Water'), #flippers
    ('Lake Hylia South Water Drop', 'Lake Hylia Water'), #flippers
    ('Lake Hylia Northeast Water Drop', 'Lake Hylia Water'), #flippers
    ('Lake Hylia Central Water Drop', 'Lake Hylia Water'), #flippers
    ('Lake Hylia Island Water Drop', 'Lake Hylia Water'), #flippers
    ('Lake Hylia Central Island Pier', 'Lake Hylia Central Island'),
    ('Lake Hylia West Pier', 'Lake Hylia Northwest Bank'),
    ('Lake Hylia East Pier', 'Lake Hylia Northeast Bank'),
    ('Lake Hylia Water D Approach', 'Lake Hylia Water D'),
    ('Lake Hylia Water D Leave', 'Lake Hylia Water'), #flippers
    ('Ice Cave Water Drop', 'Ice Cave Water'), #flippers
    ('Ice Cave Pier', 'Ice Cave Area'),
    ('Desert Pass Ledge Drop', 'Desert Pass Area'),
    ('Desert Pass Rocks (North)', 'Desert Pass Southeast'), #glove
    ('Desert Pass Rocks (South)', 'Desert Pass Area'), #glove
    ('Middle Aged Man', 'Middle Aged Man'),
    ('Octoballoon Water Drop', 'Octoballoon Water'), #flippers
    ('Octoballoon Waterfall Water Drop', 'Octoballoon Water'), #flippers
    ('Octoballoon Pier', 'Octoballoon Area'),

    ('Skull Woods Rock (West)', 'Skull Woods Forest'), #glove
    ('Skull Woods Rock (East)', 'Skull Woods Portal Entry'), #glove
    ('Skull Woods Forgotten Bush (West)', 'Skull Woods Forgotten Path (Northeast)'), #pearl
    ('Skull Woods Forgotten Bush (East)', 'Skull Woods Forgotten Path (Southwest)'), #pearl
    ('West Dark Death Mountain Drop', 'West Dark Death Mountain (Bottom)'),
    ('GT Approach', 'GT Stairs'),
    ('GT Leave', 'West Dark Death Mountain (Top)'),
    ('Floating Island Drop', 'East Dark Death Mountain (Top)'),
    ('East Dark Death Mountain Drop', 'East Dark Death Mountain (Bottom)'),
    ('East Dark Death Mountain Bushes', 'East Dark Death Mountain (Bushes)'),
    ('Turtle Rock Ledge Drop', 'Turtle Rock Area'),
    ('Bumper Cave Rock (Outer)', 'Bumper Cave Entry'), #glove
    ('Bumper Cave Rock (Inner)', 'Bumper Cave Area'), #glove
    ('Bumper Cave Ledge Drop', 'Bumper Cave Area'),
    ('Bumper Cave Entry Drop', 'Bumper Cave Area'),
    ('Skull Woods Pass Bush Row (West)', 'Skull Woods Pass East Top Area'), #pearl
    ('Skull Woods Pass Bush Row (East)', 'Skull Woods Pass West Area'), #pearl
    ('Skull Woods Pass Bush (North)', 'Skull Woods Pass Portal Area'), #pearl
    ('Skull Woods Pass Bush (South)', 'Skull Woods Pass East Top Area'), #pearl
    ('Skull Woods Pass Rock (North)', 'Skull Woods Pass East Bottom Area'), #mitts
    ('Skull Woods Pass Rock (South)', 'Skull Woods Pass Portal Area'), #mitts
    ('Dark Graveyard Bush (South)', 'Dark Graveyard North'), #pearl
    ('Dark Graveyard Bush (North)', 'Dark Graveyard Area'), #pearl
    ('Qirn Jump Water Drop', 'Qirn Jump Water'), #flippers
    ('Qirn Jump East Water Drop', 'Qirn Jump Water'), #flippers
    ('Qirn Jump Pier', 'Qirn Jump East Bank'),
    ('Dark Witch Water Drop', 'Dark Witch Water'), #flippers
    ('Dark Witch Northeast Water Drop', 'Dark Witch Water'), #flippers
    ('Dark Witch Rock (North)', 'Dark Witch Area'), #glove
    ('Dark Witch Rock (South)', 'Dark Witch Northeast'), #glove
    ('Catfish Approach Water Drop', 'Catfish Approach Water'), #flippers
    ('Catfish Approach Rocks (West)', 'Catfish Approach Ledge'), #mitts/boots
    ('Catfish Approach Rocks (East)', 'Catfish Approach Area'), #mitts/boots
    ('Catfish Approach Bottom Ledge Drop', 'Catfish Approach Ledge'),
    ('Catfish Approach Ledge Drop', 'Catfish Approach Area'),
    ('Bush Yard Pegs (Outer)', 'Village of Outcasts Bush Yard'), #hammer
    ('Bush Yard Pegs (Inner)', 'Village of Outcasts'), #hammer
    ('Shield Shop Fence Drop (Outer)', 'Shield Shop Fence'),
    ('Shield Shop Fence Drop (Inner)', 'Shield Shop Area'),
    ('Pyramid Exit Ledge Drop', 'Pyramid Area'),
    ('Pyramid Crack', 'Pyramid Crack'),
    ('Broken Bridge Hammer Rock (South)', 'Broken Bridge Northeast'), #hammer/glove
    ('Broken Bridge Hammer Rock (North)', 'Broken Bridge Area'), #hammer/glove
    ('Broken Bridge Hookshot Gap', 'Broken Bridge West'), #hookshot
    ('Broken Bridge Water Drop', 'Broken Bridge Water'), #flippers
    ('Broken Bridge Northeast Water Drop', 'Broken Bridge Water'), #flippers
    ('Broken Bridge West Water Drop', 'Broken Bridge Water'), #flippers
    ('Kiki Assistance', 'Dark Palace Button'),
    ('Peg Area Rocks (West)', 'Hammer Pegs Area'), #mitts
    ('Peg Area Rocks (East)', 'Hammer Pegs Entry'), #mitts
    ('Dig Game To Ledge Drop', 'Dig Game Ledge'), #mitts
    ('Dig Game Ledge Drop', 'Dig Game Area'),
    ('Frog Ledge Drop', 'Archery Game Area'),
    ('Frog Rock (Inner)', 'Frog Area'), #mitts
    ('Frog Rock (Outer)', 'Frog Prison'), #mitts
    ('Archery Game Rock (North)', 'Archery Game Area'), #mitts
    ('Archery Game Rock (South)', 'Frog Area'), #mitts
    ('Hammer Bridge Pegs (North)', 'Hammer Bridge South Area'), #hammer
    ('Hammer Bridge Pegs (South)', 'Hammer Bridge North Area'), #hammer
    ('Hammer Bridge Water Drop', 'Hammer Bridge Water'), #flippers
    ('Hammer Bridge Pier', 'Hammer Bridge North Area'),
    ('Mire Teleporter Ledge Drop', 'Mire Area'),
    ('Stumpy Approach Bush (North)', 'Stumpy Approach Area'), #pearl
    ('Stumpy Approach Bush (South)', 'Stumpy Approach Bush Entry'), #pearl
    ('Dark C Whirlpool Water Entry', 'Dark C Whirlpool Water'), #flippers
    ('Dark C Whirlpool Landing', 'Dark C Whirlpool Area'),
    ('Dark C Whirlpool Rock (Bottom)', 'Dark C Whirlpool Outer Area'), #glove
    ('Dark C Whirlpool Rock (Top)', 'Dark C Whirlpool Area'), #glove
    ('Dark C Whirlpool Pegs (Outer)', 'Dark C Whirlpool Portal Area'), #hammer
    ('Dark C Whirlpool Pegs (Inner)', 'Dark C Whirlpool Area'), #hammer
    ('Hype Cave Water Entry', 'Hype Cave Water'), #flippers
    ('Hype Cave Landing', 'Hype Cave Area'),
    ('Ice Lake Water Drop', 'Ice Lake Water'), #flippers
    ('Ice Lake Northeast Water Drop', 'Ice Lake Water'), #flippers
    ('Ice Lake Southwest Water Drop', 'Ice Lake Water'), #flippers
    ('Ice Lake Southeast Water Drop', 'Ice Lake Water'), #flippers
    ('Ice Lake Iceberg Water Entry', 'Ice Lake Water'), #flippers
    ('Ice Lake Northeast Pier', 'Ice Lake Northeast Bank'),
    ('Shopping Mall Water Drop', 'Shopping Mall Water'), #flippers
    ('Shopping Mall Pier', 'Shopping Mall Area'),
    ('Bomber Corner Water Drop', 'Bomber Corner Water'), #flippers
    ('Bomber Corner Waterfall Water Drop', 'Bomber Corner Water'), #flippers
    ('Bomber Corner Pier', 'Bomber Corner Area'),

    # OWG In-Bounds Connections
    ('Ice Lake Northeast Pier Hop', 'Ice Lake Northeast Bank'),
    ('Ice Lake Iceberg Bomb Jump', 'Ice Lake Iceberg')
]

default_whirlpool_connections = [
    ((0x33, 'C Whirlpool', 'C Whirlpool Water'),              (0x15, 'River Bend Whirlpool', 'River Bend Water')),
    ((0x35, 'Lake Hylia Whirlpool', 'Lake Hylia Water'),      (0x0f, 'Zora Whirlpool', 'Zora Waterfall Water')),
    ((0x12, 'Kakariko Pond Whirlpool', 'Kakariko Pond Area'), (0x3f, 'Octoballoon Whirlpool', 'Octoballoon Water')),
    ((0x55, 'Qirn Jump Whirlpool', 'Qirn Jump Water'),        (0x7f, 'Bomber Corner Whirlpool', 'Bomber Corner Water'))
]

ow_connections = {
    0x03: ([
            ('West Death Mountain Teleporter', 'West Dark Death Mountain (Bottom)')
        ], [
            ('Spectacle Rock Leave', 'West Death Mountain (Top)'),
            ('Spectacle Rock Approach', 'Spectacle Rock Ledge'),
            ('Dark Death Mountain Teleporter (West)', 'West Death Mountain (Bottom)')
        ]),
    0x05: ([
            ('EDM To Fairy Ledge Drop', 'Fairy Ascension Ledge'),
            ('East Death Mountain Teleporter', 'East Dark Death Mountain (Bottom)')
        ], [
            ('Floating Island Bridge (West)', 'East Death Mountain (Top East)'),
            ('Floating Island Bridge (East)', 'Death Mountain Floating Island'),
            ('EDM To Mimic Ledge Drop', 'Mimic Cave Ledge'),
            ('Spiral Mimic Bridge (West)', 'Spiral Mimic Ledge Extend'),
            ('Spiral Mimic Bridge (East)', 'Spiral Mimic Ledge Extend'),
            ('Spiral Ledge Approach', 'Spiral Cave Ledge'),
            ('Mimic Ledge Approach', 'Mimic Cave Ledge'),
            ('Spiral Mimic Ledge Drop', 'Fairy Ascension Ledge'),
            ('East Dark Death Mountain Teleporter', 'East Death Mountain (Bottom)')
        ]),
    0x07: ([
            ('TR Pegs Teleporter', 'Turtle Rock Ledge'),
            ('TR Pegs Ledge Drop', 'Death Mountain TR Pegs Area')
        ], [
            ('Turtle Rock Tail Ledge Drop', 'Turtle Rock Ledge'),
            ('Turtle Rock Teleporter', 'Death Mountain TR Pegs Ledge')
        ]),
    0x10: ([
            ('Kakariko Teleporter', 'Skull Woods Pass Portal Area')
        ], [
            ('West Dark World Teleporter', 'Lost Woods Pass Portal Area')
        ]),
    0x14: ([
            
        ], [
            ('Graveyard Ladder (Top)', 'Graveyard Area'),
            ('Graveyard Ladder (Bottom)', 'Graveyard Ledge')
        ]),
    0x1b: ([
            ('Castle Gate Teleporter', 'Pyramid Area'),
            ('Castle Gate Teleporter (Inner)', 'Pyramid Area')
        ], [
            ('Post Aga Teleporter', 'Hyrule Castle Area')
        ]),
    0x1e: ([
            ('Eastern Palace Cliff Ledge Drop', 'Eastern Palace Area'), # OWG
            ('Palace of Darkness Cliff Ledge Drop', 'Palace of Darkness Area') # OWG
        ], [
            ('Eastern Palace Cliff Ledge Drop', 'Palace of Darkness Area'), # OWG
            ('Palace of Darkness Cliff Ledge Drop', 'Eastern Palace Area') # OWG
        ]),
    0x25: ([
            ('Sand Dunes Cliff Ledge Drop', 'Sand Dunes Area'), # OWG
            ('Dark Dunes Cliff Ledge Drop', 'Dark Dunes Area') # OWG
        ], [
            ('Sand Dunes Cliff Ledge Drop', 'Dark Dunes Area'), # OWG
            ('Dark Dunes Cliff Ledge Drop', 'Sand Dunes Area') # OWG
        ]),
    0x29: ([
            ('Suburb Cliff Ledge Drop', 'Kakariko Suburb Area'), # OWG
            ('Archery Game Cliff Ledge Drop', 'Archery Game Area') # OWG
        ], [
            ('Suburb Cliff Ledge Drop', 'Archery Game Area'), # OWG
            ('Archery Game Cliff Ledge Drop', 'Kakariko Suburb Area') # OWG
        ]),
    0x2b: ([
            ('Central Bonk Rocks Cliff Ledge Drop', 'Central Bonk Rocks Area'), # OWG
            ('Dark Bonk Rocks Cliff Ledge Drop', 'Dark Bonk Rocks Area') # OWG
        ], [
            ('Central Bonk Rocks Cliff Ledge Drop', 'Dark Bonk Rocks Area'), # OWG
            ('Dark Bonk Rocks Cliff Ledge Drop', 'Central Bonk Rocks Area') # OWG
        ]),
    0x2c: ([
            ('Links House Cliff Ledge Drop', 'Links House Area'), # OWG
            ('Bomb Shop Cliff Ledge Drop', 'Big Bomb Shop Area') # OWG
        ], [
            ('Links House Cliff Ledge Drop', 'Big Bomb Shop Area'), # OWG
            ('Bomb Shop Cliff Ledge Drop', 'Links House Area') # OWG
        ]),
    0x2d: ([
            ('Stone Bridge East Cliff Ledge Drop', 'Stone Bridge North Area'), # OWG
            ('Hammer Bridge North Cliff Ledge Drop', 'Hammer Bridge North Area'), # OWG
            ('Stone Bridge Cliff Ledge Drop', 'Stone Bridge South Area'), # OWG
            ('Hammer Bridge South Cliff Ledge Drop', 'Hammer Bridge South Area'), # OWG
            ('Stone Bridge EC Cliff Water Drop', 'Stone Bridge Water'), # fake flipper
            ('Hammer Bridge EC Cliff Water Drop', 'Hammer Bridge Water'), # fake flipper
            ('Tree Line WC Cliff Water Drop', 'Tree Line Water'), # fake flipper
            ('Dark Tree Line WC Cliff Water Drop', 'Dark Tree Line Water') # fake flipper
        ], [
            ('Stone Bridge East Cliff Ledge Drop', 'Hammer Bridge North Area'), # OWG
            ('Hammer Bridge North Cliff Ledge Drop', 'Stone Bridge North Area'), # OWG
            ('Stone Bridge Cliff Ledge Drop', 'Hammer Bridge South Area'), # OWG
            ('Hammer Bridge South Cliff Ledge Drop', 'Stone Bridge South Area'), # OWG
            ('Stone Bridge EC Cliff Water Drop', 'Hammer Bridge Water'), # fake flipper
            ('Hammer Bridge EC Cliff Water Drop', 'Stone Bridge Water'), # fake flipper
            ('Tree Line WC Cliff Water Drop', 'Dark Tree Line Water'), # fake flipper
            ('Dark Tree Line WC Cliff Water Drop', 'Tree Line Water') # fake flipper
        ]),
    0x2e: ([
            ('Tree Line Cliff Ledge Drop', 'Tree Line Area'), # OWG
            ('Dark Tree Line Cliff Ledge Drop', 'Dark Tree Line Area') # OWG
        ], [
            ('Tree Line Cliff Ledge Drop', 'Dark Tree Line Area'), # OWG
            ('Dark Tree Line Cliff Ledge Drop', 'Tree Line Area') # OWG
        ]),
    0x2f: ([
            ('East Hyrule Teleporter', 'Darkness Nook Area')
        ], [
            ('East Dark World Teleporter', 'Eastern Nook Area')
        ]),
    0x30: ([
            ('Mirror To Bombos Tablet Ledge', 'Bombos Tablet Ledge'), # OWG
            ('Desert Teleporter', 'Mire Teleporter Ledge'),
            ('Mire Cliff Ledge Drop', 'Mire Area'), # OWG
            ('Checkerboard Cliff Ledge Drop', 'Desert Checkerboard Ledge') # OWG
        ], [
            ('Checkerboard Ledge Approach', 'Desert Checkerboard Ledge'),
            ('Checkerboard Ledge Leave', 'Desert Area'),
            ('Mire Teleporter', 'Desert Teleporter Ledge'),
            ('Mire Cliff Ledge Drop', 'Desert Ledge Keep'), # OWG
            ('Dark Checkerboard Cliff Ledge Drop', 'Desert Checkerboard Ledge') # OWG
        ]),
    0x32: ([
            ('Cave 45 Ledge Drop', 'Flute Boy Approach Area'),
            ('Cave 45 Cliff Ledge Drop', 'Cave 45 Ledge'), # OWG
            ('Stumpy Approach Cliff Ledge Drop', 'Stumpy Approach Area') # OWG
        ], [
            ('Cave 45 Leave', 'Flute Boy Approach Area'),
            ('Cave 45 Approach', 'Cave 45 Ledge'),
            ('Cave 45 Cliff Ledge Drop', 'Stumpy Approach Area'), # OWG
            ('Stumpy Approach Cliff Ledge Drop', 'Cave 45 Ledge') # OWG
        ]),
    0x33: ([
            ('South Hyrule Teleporter', 'Dark C Whirlpool Portal Area'),
            ('C Whirlpool Cliff Ledge Drop', 'C Whirlpool Area'), # OWG
            ('Dark C Whirlpool Cliff Ledge Drop', 'Dark C Whirlpool Area'), # OWG
            ('C Whirlpool Outer Cliff Ledge Drop', 'C Whirlpool Outer Area'), # OWG
            ('Dark C Whirlpool Outer Cliff Ledge Drop', 'Dark C Whirlpool Outer Area'), # OWG
            ('C Whirlpool Portal Cliff Ledge Drop', 'C Whirlpool Portal Area'), #OWG
            ('Dark C Whirlpool Portal Cliff Ledge Drop', 'Dark C Whirlpool Portal Area'), #OWG
            ('Desert C Whirlpool Cliff Ledge Drop', 'C Whirlpool Outer Area'), # OWG
            ('Mire C Whirlpool Cliff Ledge Drop', 'Dark C Whirlpool Outer Area') # OWG
        ], [
            ('South Dark World Teleporter', 'C Whirlpool Portal Area'),
            ('C Whirlpool Cliff Ledge Drop', 'Dark C Whirlpool Area'), # OWG
            ('Dark C Whirlpool Cliff Ledge Drop', 'C Whirlpool Area'), # OWG
            ('C Whirlpool Outer Cliff Ledge Drop', 'Dark C Whirlpool Outer Area'), # OWG
            ('Dark C Whirlpool Outer Cliff Ledge Drop', 'C Whirlpool Outer Area'), # OWG
            ('C Whirlpool Portal Cliff Ledge Drop', 'Dark C Whirlpool Portal Area'), #OWG
            ('Dark C Whirlpool Portal Cliff Ledge Drop', 'C Whirlpool Portal Area'), #OWG
            ('Desert C Whirlpool Cliff Ledge Drop', 'Dark C Whirlpool Outer Area'), # OWG
            ('Mire C Whirlpool Cliff Ledge Drop', 'C Whirlpool Outer Area') # OWG
        ]),
    0x34: ([
            ('Statues Cliff Ledge Drop', 'Statues Area'), # OWG
            ('Hype Cliff Ledge Drop', 'Hype Cave Area') # OWG
        ], [
            ('Statues Cliff Ledge Drop', 'Hype Cave Area'), # OWG
            ('Hype Cliff Ledge Drop', 'Statues Area') # OWG
        ]),
    0x35: ([
            ('Lake Hylia Teleporter', 'Ice Palace Area'),
            ('Lake Hylia Northwest Cliff Ledge Drop', 'Lake Hylia Northwest Bank'), # OWG
            ('Ice Lake Northwest Cliff Ledge Drop', 'Ice Lake Northwest Bank'), # OWG
            ('Lake Hylia Island FAWT Ledge Drop', 'Lake Hylia Island'), # OWG
            ('Ice Palace Island FAWT Ledge Drop', 'Ice Lake Iceberg') # OWG
        ], [
            ('Lake Hylia Island Pier', 'Lake Hylia Island'),
            ('Ice Lake Teleporter', 'Lake Hylia Water D'),
            ('Lake Hylia Northwest Cliff Ledge Drop', 'Ice Lake Northwest Bank'), # OWG
            ('Ice Lake Northwest Cliff Ledge Drop', 'Lake Hylia Northwest Bank'), # OWG
            ('Lake Hylia Island FAWT Ledge Drop', 'Ice Lake Iceberg'), # OWG
            ('Ice Palace Island FAWT Ledge Drop', 'Lake Hylia Island') # OWG
        ]),
    0x3a: ([
            ('Desert Pass Cliff Ledge Drop', 'Desert Pass Area'), # OWG
            ('Swamp Nook Cliff Ledge Drop', 'Swamp Nook Area') # OWG
        ], [
            ('Desert Pass Ladder (North)', 'Desert Pass Area'),
            ('Desert Pass Ladder (South)', 'Desert Pass Ledge'),
            ('Desert Pass Cliff Ledge Drop', 'Swamp Nook Area'), # OWG
            ('Swamp Nook Cliff Ledge Drop', 'Desert Pass Area') # OWG
        ]),
    0x3b: ([
            ('Dam Cliff Ledge Drop', 'Dam Area'), # OWG
            ('Swamp Cliff Ledge Drop', 'Swamp Area') # OWG
        ], [
            ('Dam Cliff Ledge Drop', 'Swamp Area'), # OWG
            ('Swamp Cliff Ledge Drop', 'Dam Area') # OWG
        ])
}

mirror_connections = {
    'Skull Woods Forest': ['Lost Woods East Area'],
    'Skull Woods Portal Entry': ['Lost Woods West Area'],
    'Skull Woods Forest (West)': ['Lost Woods West Area'],
    'Skull Woods Forgotten Path (Southwest)': ['Lost Woods West Area'],
    'Skull Woods Forgotten Path (Northeast)': ['Lost Woods East Area', 'Lost Woods West Area'],

    'Dark Lumberjack Area': ['Lumberjack Area'],

    'West Dark Death Mountain (Top)': ['West Death Mountain (Top)'],
    'West Dark Death Mountain (Bottom)': ['Spectacle Rock Ledge'],

    'Dark Death Mountain Floating Island': ['Death Mountain Floating Island'],
    'East Dark Death Mountain (Top)': ['East Death Mountain (Top West)', 'East Death Mountain (Top East)'],
    'Dark Death Mountain Ledge': ['Spiral Cave Ledge', 'Mimic Cave Ledge'],
    'Dark Death Mountain Isolated Ledge': ['Fairy Ascension Ledge'],
    'East Dark Death Mountain (Bushes)': ['Fairy Ascension Plateau'],
    'East Dark Death Mountain (Bottom Left)': ['East Death Mountain (Bottom Left)'],

    'Turtle Rock Area': ['Death Mountain TR Pegs Area'],

    'Bumper Cave Area': ['Mountain Pass Area'],
    'Bumper Cave Entry': ['Mountain Pass Entry'],
    'Bumper Cave Ledge': ['Mountain Pass Ledge'],

    'Catfish Area': ['Zora Waterfall Area'],

    'Skull Woods Pass West Area': ['Lost Woods Pass West Area'],
    'Skull Woods Pass East Top Area': ['Lost Woods Pass East Top Area'],
    'Skull Woods Pass Portal Area': ['Lost Woods Pass Portal Area'],
    'Skull Woods Pass East Bottom Area': ['Lost Woods Pass East Bottom Area'],

    'Dark Fortune Area': ['Kakariko Fortune Area'],

    'Outcast Pond Area': ['Kakariko Pond Area'],

    'Dark Chapel Area': ['Sanctuary Area', 'Bonk Rock Ledge'],

    'Dark Graveyard Area': ['Graveyard Area'],
    'Dark Graveyard North': ['Graveyard Ledge', 'Kings Grave Area'],

    'Qirn Jump Area': ['River Bend Area'],
    'Qirn Jump East Bank': ['River Bend East Bank'],

    'Dark Witch Area': ['Potion Shop Area'],
    'Dark Witch Northeast': ['Potion Shop Northeast'],

    'Catfish Approach Area': ['Zora Approach Area'],
    'Catfish Approach Ledge': ['Zora Approach Ledge'],

    'Village of Outcasts': ['Kakariko Village'],
    'Village of Outcasts Bush Yard': ['Kakariko Village'],

    'Shield Shop Area': ['Forgotten Forest Area'],
    'Shield Shop Fence': ['Forgotten Forest Area'],

    'Pyramid Area': ['Hyrule Castle Ledge', 'Hyrule Castle Courtyard', 'Hyrule Castle Area', 'Hyrule Castle East Entry'],
    'Pyramid Exit Ledge': ['Hyrule Castle Courtyard'],
    'Pyramid Pass': ['Hyrule Castle Area'],

    'Broken Bridge Area': ['Wooden Bridge Area'],
    'Broken Bridge Northeast': ['Wooden Bridge Area'],
    'Broken Bridge West': ['Wooden Bridge Area'],

    'Palace of Darkness Area': ['Eastern Palace Area'],

    'Hammer Pegs Area': ['Blacksmith Area', 'Blacksmith Ledge'],
    'Hammer Pegs Entry': ['Blacksmith Area'],

    'Dark Dunes Area': ['Sand Dunes Area'],

    'Dig Game Area': ['Maze Race Ledge'],
    'Dig Game Ledge': ['Maze Race Ledge'],

    'Frog Area': ['Kakariko Suburb Area'],
    'Archery Game Area': ['Kakariko Suburb Area'],

    'Stumpy Area': ['Flute Boy Area'],
    'Stumpy Pass': ['Flute Boy Pass'],

    'Dark Bonk Rocks Area': ['Central Bonk Rocks Area'],

    'Big Bomb Shop Area': ['Links House Area'],

    'Hammer Bridge North Area': ['Stone Bridge North Area'],
    'Hammer Bridge South Area': ['Stone Bridge South Area'],
    'Hammer Bridge Water': ['Stone Bridge Water'],

    'Dark Tree Line Area': ['Tree Line Area'],

    'Darkness Nook Area': ['Eastern Nook Area'],

    'Mire Area': ['Desert Area', 'Desert Ledge', 'Desert Checkerboard Ledge', 'Desert Stairs', 'Desert Ledge Keep'],

    'Stumpy Approach Area': ['Cave 45 Ledge'],
    'Stumpy Approach Bush Entry': ['Flute Boy Bush Entry'],

    'Dark C Whirlpool Area': ['C Whirlpool Area'],
    'Dark C Whirlpool Outer Area': ['C Whirlpool Outer Area'],

    'Hype Cave Area': ['Statues Area'],

    'Ice Lake Northwest Bank': ['Lake Hylia Northwest Bank'],
    'Ice Lake Northeast Bank': ['Lake Hylia Northeast Bank'],
    'Ice Lake Southwest Ledge': ['Lake Hylia South Shore'],
    'Ice Lake Southeast Ledge': ['Lake Hylia South Shore'],
    'Ice Lake Water': ['Lake Hylia Island'],
    'Ice Palace Area': ['Lake Hylia Central Island'],
    'Ice Lake Iceberg': ['Lake Hylia Water', 'Lake Hylia Water D'], #first one needs flippers

    'Shopping Mall Area': ['Ice Cave Area'],

    'Swamp Nook Area': ['Desert Pass Area', 'Desert Pass Ledge'],

    'Swamp Area': ['Dam Area'],

    'Dark South Pass Area': ['South Pass Area'],

    'Bomber Corner Area': ['Octoballoon Area'],


    'Lost Woods West Area': ['Skull Woods Forest (West)', 'Skull Woods Forgotten Path (Southwest)', 'Skull Woods Portal Entry'],
    #'Lost Woods West Area': ['Skull Woods Forgotten Path (Northeast)'], # technically yes, but we dont need it
    'Lost Woods East Area': ['Skull Woods Forgotten Path (Northeast)', 'Skull Woods Forest'],

    'Lumberjack Area': ['Dark Lumberjack Area'],

    'West Death Mountain (Top)': ['West Dark Death Mountain (Top)'],
    'Spectacle Rock Ledge': ['West Dark Death Mountain (Bottom)'],
    'West Death Mountain (Bottom)': ['West Dark Death Mountain (Bottom)'],

    'East Death Mountain (Top West)': ['East Dark Death Mountain (Top)'],
    'East Death Mountain (Top East)': ['East Dark Death Mountain (Top)'],
    'Spiral Cave Ledge': ['Dark Death Mountain Ledge'],
    'Mimic Cave Ledge': ['Dark Death Mountain Ledge'],
    'Fairy Ascension Ledge': ['Dark Death Mountain Isolated Ledge'],
    'Fairy Ascension Plateau': ['East Dark Death Mountain (Bottom)'],
    'East Death Mountain (Bottom Left)': ['East Dark Death Mountain (Bottom Left)'],
    'East Death Mountain (Bottom)': ['East Dark Death Mountain (Bottom)'],
    'Death Mountain Floating Island': ['Dark Death Mountain Floating Island'],

    'Death Mountain TR Pegs Area': ['Turtle Rock Area'],
    'Death Mountain TR Pegs Ledge': ['Turtle Rock Ledge'],

    'Mountain Pass Area': ['Bumper Cave Area'],
    'Mountain Pass Entry': ['Bumper Cave Entry'],
    'Mountain Pass Ledge': ['Bumper Cave Ledge'],

    'Zora Waterfall Area': ['Catfish Area'],

    'Lost Woods Pass West Area': ['Skull Woods Pass West Area'],
    'Lost Woods Pass East Top Area': ['Skull Woods Pass East Top Area'],
    'Lost Woods Pass Portal Area': ['Skull Woods Pass Portal Area'],
    'Lost Woods Pass East Bottom Area': ['Skull Woods Pass East Bottom Area'],

    'Kakariko Fortune Area': ['Dark Fortune Area'],

    'Kakariko Pond Area': ['Outcast Pond Area'],

    'Sanctuary Area': ['Dark Chapel Area'],
    'Bonk Rock Ledge': ['Dark Chapel Area'],

    'Graveyard Area': ['Dark Graveyard Area'],
    'Graveyard Ledge': ['Dark Graveyard Area'],
    'Kings Grave Area': ['Dark Graveyard Area'],

    'River Bend Area': ['Qirn Jump Area'],
    'River Bend East Bank': ['Qirn Jump East Bank'],

    'Potion Shop Area': ['Dark Witch Area'],
    'Potion Shop Northeast': ['Dark Witch Northeast'],

    'Zora Approach Area': ['Catfish Approach Area'],
    'Zora Approach Ledge': ['Catfish Approach Ledge'],

    'Kakariko Village': ['Village of Outcasts'],
    'Kakariko Southwest': ['Village of Outcasts'],
    'Kakariko Bush Yard': ['Village of Outcasts Bush Yard'],

    'Forgotten Forest Area': ['Shield Shop Area'],

    'Hyrule Castle Area': ['Pyramid Area', 'Pyramid Pass'],
    'Hyrule Castle Southwest': ['Pyramid Pass'],
    'Hyrule Castle Courtyard': ['Pyramid Area'],
    'Hyrule Castle Courtyard Northeast': ['Pyramid Area'],
    'Hyrule Castle Ledge': ['Pyramid Area'],
    'Hyrule Castle East Entry': ['Pyramid Area'],

    'Wooden Bridge Area': ['Broken Bridge Area', 'Broken Bridge West'],
    'Wooden Bridge Northeast': ['Broken Bridge Northeast'],

    'Eastern Palace Area': ['Palace of Darkness Area'],

    'Blacksmith Area': ['Hammer Pegs Area', 'Hammer Pegs Entry'],

    'Sand Dunes Area': ['Dark Dunes Area'],

    'Maze Race Area': ['Dig Game Area'],
    'Maze Race Ledge': ['Dig Game Ledge'],

    'Kakariko Suburb Area': ['Frog Area', 'Frog Prison', 'Archery Game Area'],

    'Flute Boy Area': ['Stumpy Area'],
    'Flute Boy Pass': ['Stumpy Pass'],

    'Central Bonk Rocks Area': ['Dark Bonk Rocks Area'],

    'Links House Area': ['Big Bomb Shop Area'],

    'Stone Bridge North Area': ['Hammer Bridge North Area'],
    'Stone Bridge South Area': ['Hammer Bridge South Area'],
    'Stone Bridge Water': ['Hammer Bridge Water'],

    'Tree Line Area': ['Dark Tree Line Area'],

    'Eastern Nook Area': ['Darkness Nook Area'],

    'Desert Area': ['Mire Area'],
    'Desert Ledge': ['Mire Area'],
    'Desert Ledge Keep': ['Mire Area'],
    'Desert Checkerboard Ledge': ['Mire Area'],
    'Desert Stairs': ['Mire Area'],

    'Flute Boy Approach Area': ['Stumpy Approach Area'],
    'Cave 45 Ledge': ['Stumpy Approach Area'],
    'Flute Boy Bush Entry': ['Stumpy Approach Bush Entry'],

    'C Whirlpool Area': ['Dark C Whirlpool Area'],
    'C Whirlpool Outer Area': ['Dark C Whirlpool Outer Area'],

    'Statues Area': ['Hype Cave Area'],

    'Lake Hylia Northwest Bank': ['Ice Lake Northwest Bank'],
    'Lake Hylia South Shore': ['Ice Lake Southwest Ledge', 'Ice Lake Southeast Ledge'],
    'Lake Hylia Northeast Bank': ['Ice Lake Northeast Bank'],
    'Lake Hylia Central Island': ['Ice Palace Area'],
    'Lake Hylia Water D': ['Ice Lake Iceberg'],

    'Ice Cave Area': ['Shopping Mall Area'],

    'Desert Pass Area': ['Swamp Nook Area'],
    'Desert Pass Southeast': ['Swamp Nook Area'],
    'Desert Pass Ledge': ['Swamp Nook Area'],

    'Dam Area': ['Swamp Area'],

    'South Pass Area': ['Dark South Pass Area'],

    'Octoballoon Area': ['Bomber Corner Area']
}

parallelsimilar_connections = [('Maze Race ES', 'Kakariko Suburb WS'),
                               ('Dig Game EC', 'Frog WC'),
                               ('Dig Game ES', 'Frog WS')
                            ]

special_screen_connections = [('Lost Woods NW', 'Master Sword Meadow SC'),
                               ('Stone Bridge WC', 'Hobo EC'),
                               ('Zora Waterfall NE', 'Zoras Domain SW')
                            ]

# non shuffled overworld
default_connections = [('Lost Woods NW', 'Master Sword Meadow SC'),
                        ('Lost Woods SW', 'Lost Woods Pass NW'),
                        ('Lost Woods SC', 'Lost Woods Pass NE'),
                        ('Lost Woods SE', 'Kakariko Fortune NE'),
                        ('Lost Woods EN', 'Lumberjack WN'),
                        ('Lumberjack SW', 'Mountain Pass NW'),
                        ('Mountain Pass SE', 'Kakariko Pond NE'),
                        ('Zora Waterfall NE', 'Zoras Domain SW'),
                        ('Lost Woods Pass SW', 'Kakariko NW'),
                        ('Lost Woods Pass SE', 'Kakariko NC'),
                        ('Kakariko Fortune SC', 'Kakariko NE'),
                        ('Kakariko Fortune EN', 'Kakariko Pond WN'),
                        ('Kakariko Fortune ES', 'Kakariko Pond WS'),
                        ('Kakariko Pond SW', 'Forgotten Forest NW'),
                        ('Kakariko Pond SE', 'Forgotten Forest NE'),
                        ('Kakariko Pond EN', 'Sanctuary WN'),
                        ('Kakariko Pond ES', 'Sanctuary WS'),
                        ('Forgotten Forest ES', 'Hyrule Castle WN'),
                        ('Sanctuary EC', 'Graveyard WC'),
                        ('Graveyard EC', 'River Bend WC'),
                        ('River Bend SW', 'Wooden Bridge NW'),
                        ('River Bend SC', 'Wooden Bridge NC'),
                        ('River Bend SE', 'Wooden Bridge NE'),
                        ('River Bend EN', 'Potion Shop WN'),
                        ('River Bend EC', 'Potion Shop WC'),
                        ('River Bend ES', 'Potion Shop WS'),
                        ('Potion Shop EN', 'Zora Approach WN'),
                        ('Potion Shop EC', 'Zora Approach WC'),
                        ('Zora Approach NE', 'Zora Waterfall SE'),
                        ('Kakariko SE', 'Kakariko Suburb NE'),
                        ('Kakariko ES', 'Blacksmith WS'),
                        ('Hyrule Castle SW', 'Central Bonk Rocks NW'),
                        ('Hyrule Castle SE', 'Links House NE'),
                        ('Hyrule Castle ES', 'Sand Dunes WN'),
                        ('Wooden Bridge SW', 'Sand Dunes NW'),
                        ('Sand Dunes SC', 'Stone Bridge NC'),
                        ('Eastern Palace SW', 'Tree Line NW'),
                        ('Eastern Palace SE', 'Eastern Nook NE'),
                        ('Maze Race ES', 'Kakariko Suburb WS'),
                        ('Kakariko Suburb ES', 'Flute Boy WS'),
                        ('Flute Boy SW', 'Flute Boy Approach NW'),
                        ('Flute Boy SC', 'Flute Boy Approach NC'),
                        ('Flute Boy Approach EC', 'C Whirlpool WC'),
                        ('C Whirlpool NW', 'Central Bonk Rocks SW'),
                        ('C Whirlpool SC', 'Dam NC'),
                        ('C Whirlpool EN', 'Statues WN'),
                        ('C Whirlpool EC', 'Statues WC'),
                        ('C Whirlpool ES', 'Statues WS'),
                        ('Central Bonk Rocks EN', 'Links House WN'),
                        ('Central Bonk Rocks EC', 'Links House WC'),
                        ('Central Bonk Rocks ES', 'Links House WS'),
                        ('Links House SC', 'Statues NC'),
                        ('Links House ES', 'Stone Bridge WS'),
                        ('Stone Bridge SC', 'Lake Hylia NW'),
                        ('Stone Bridge EN', 'Tree Line WN'),
                        ('Stone Bridge EC', 'Tree Line WC'),
                        ('Stone Bridge WC', 'Hobo EC'),
                        ('Tree Line SC', 'Lake Hylia NC'),
                        ('Tree Line SE', 'Lake Hylia NE'),
                        ('Desert EC', 'Desert Pass WC'),
                        ('Desert ES', 'Desert Pass WS'),
                        ('Desert Pass EC', 'Dam WC'),
                        ('Desert Pass ES', 'Dam WS'),
                        ('Dam EC', 'South Pass WC'),
                        ('Statues SC', 'South Pass NC'),
                        ('South Pass ES', 'Lake Hylia WS'),
                        ('Lake Hylia EC', 'Octoballoon WC'),
                        ('Lake Hylia ES', 'Octoballoon WS'),
                        ('Octoballoon NW', 'Ice Cave SW'),
                        ('Octoballoon NE', 'Ice Cave SE'),
                        ('West Death Mountain EN', 'East Death Mountain WN'),
                        ('West Death Mountain ES', 'East Death Mountain WS'),
                        ('East Death Mountain EN', 'Death Mountain TR Pegs WN'),

                        ('Skull Woods SW', 'Skull Woods Pass NW'),
                        ('Skull Woods SC', 'Skull Woods Pass NE'),
                        ('Skull Woods SE', 'Dark Fortune NE'),
                        ('Skull Woods EN', 'Dark Lumberjack WN'),
                        ('Dark Lumberjack SW', 'Bumper Cave NW'),
                        ('Bumper Cave SE', 'Outcast Pond NE'),
                        ('Skull Woods Pass SW', 'Village of Outcasts NW'),
                        ('Skull Woods Pass SE', 'Village of Outcasts NC'),
                        ('Dark Fortune SC', 'Village of Outcasts NE'),
                        ('Dark Fortune EN', 'Outcast Pond WN'),
                        ('Dark Fortune ES', 'Outcast Pond WS'),
                        ('Outcast Pond SW', 'Shield Shop NW'),
                        ('Outcast Pond SE', 'Shield Shop NE'),
                        ('Outcast Pond EN', 'Dark Chapel WN'),
                        ('Outcast Pond ES', 'Dark Chapel WS'),
                        ('Dark Chapel EC', 'Dark Graveyard WC'),
                        ('Dark Graveyard EC', 'Qirn Jump WC'),
                        ('Qirn Jump SW', 'Broken Bridge NW'),
                        ('Qirn Jump SC', 'Broken Bridge NC'),
                        ('Qirn Jump SE', 'Broken Bridge NE'),
                        ('Qirn Jump EN', 'Dark Witch WN'),
                        ('Qirn Jump EC', 'Dark Witch WC'),
                        ('Qirn Jump ES', 'Dark Witch WS'),
                        ('Dark Witch EN', 'Catfish Approach WN'),
                        ('Dark Witch EC', 'Catfish Approach WC'),
                        ('Catfish Approach NE', 'Catfish SE'),
                        ('Village of Outcasts SE', 'Frog NE'),
                        ('Village of Outcasts ES', 'Hammer Pegs WS'),
                        ('Pyramid SW', 'Dark Bonk Rocks NW'),
                        ('Pyramid SE', 'Big Bomb Shop NE'),
                        ('Pyramid ES', 'Dark Dunes WN'),
                        ('Broken Bridge SW', 'Dark Dunes NW'),
                        ('Dark Dunes SC', 'Hammer Bridge NC'),
                        ('Palace of Darkness SW', 'Dark Tree Line NW'),
                        ('Palace of Darkness SE', 'Palace of Darkness Nook NE'),
                        ('Dig Game EC', 'Frog WC'),
                        ('Dig Game ES', 'Frog WS'),
                        ('Frog ES', 'Stumpy WS'),
                        ('Stumpy SW', 'Stumpy Approach NW'),
                        ('Stumpy SC', 'Stumpy Approach NC'),
                        ('Stumpy Approach EC', 'Dark C Whirlpool WC'),
                        ('Dark C Whirlpool NW', 'Dark Bonk Rocks SW'),
                        ('Dark C Whirlpool SC', 'Swamp NC'),
                        ('Dark C Whirlpool EN', 'Hype Cave WN'),
                        ('Dark C Whirlpool EC', 'Hype Cave WC'),
                        ('Dark C Whirlpool ES', 'Hype Cave WS'),
                        ('Dark Bonk Rocks EN', 'Big Bomb Shop WN'),
                        ('Dark Bonk Rocks EC', 'Big Bomb Shop WC'),
                        ('Dark Bonk Rocks ES', 'Big Bomb Shop WS'),
                        ('Big Bomb Shop SC', 'Hype Cave NC'),
                        ('Big Bomb Shop ES', 'Hammer Bridge WS'),
                        ('Hammer Bridge SC', 'Ice Lake NW'),
                        ('Hammer Bridge EN', 'Dark Tree Line WN'),
                        ('Hammer Bridge EC', 'Dark Tree Line WC'),
                        ('Dark Tree Line SC', 'Ice Lake NC'),
                        ('Dark Tree Line SE', 'Ice Lake NE'),
                        ('Swamp Nook EC', 'Swamp WC'),
                        ('Swamp Nook ES', 'Swamp WS'),
                        ('Swamp EC', 'Dark South Pass WC'),
                        ('Hype Cave SC', 'Dark South Pass NC'),
                        ('Dark South Pass ES', 'Ice Lake WS'),
                        ('Ice Lake EC', 'Bomber Corner WC'),
                        ('Ice Lake ES', 'Bomber Corner WS'),
                        ('Bomber Corner NW', 'Shopping Mall SW'),
                        ('Bomber Corner NE', 'Shopping Mall SE'),
                        ('West Dark Death Mountain EN', 'East Dark Death Mountain WN'),
                        ('West Dark Death Mountain ES', 'East Dark Death Mountain WS'),
                        ('East Dark Death Mountain EN', 'Turtle Rock WN')
                        ]

one_way_ledges = {
    'West Death Mountain (Bottom)':      {'West Death Mountain (Top)',
                                          'Spectacle Rock Ledge'},
    'East Death Mountain (Bottom)':      {'East Death Mountain (Top East)',
                                          'Spiral Cave Ledge'},
    'Fairy Ascension Plateau':           {'Fairy Ascension Ledge'},
    'Mountain Pass Area':                {'Mountain Pass Ledge'},
    'Sanctuary Area':                    {'Bonk Rock Ledge'},
    'Graveyard Area':                    {'Graveyard Ledge'},
    'Potion Shop Water':                 {'Potion Shop Area',
                                          'Potion Shop Northeast'},
    'Zora Approach Water':               {'Zora Approach Area'},
    'Hyrule Castle Area':                {'Hyrule Castle Ledge'},
    'Hyrule Castle Courtyard':           {'Hyrule Castle Ledge'},
    'Wooden Bridge Water':               {'Wooden Bridge Area',
                                          'Wooden Bridge Northeast'},
    'Maze Race Area':                    {'Maze Race Ledge',
                                          'Maze Race Prize'},
    'Flute Boy Approach Area':           {'Cave 45 Ledge'},
    'Desert Area':                       {'Desert Ledge',
                                          'Desert Checkerboard Ledge',
                                          'Desert Mouth',
                                          'Bombos Tablet Ledge',
                                          'Desert Teleporter Ledge'},
    'Desert Pass Area':                  {'Desert Pass Ledge'},
    'Lake Hylia Water':                  {'Lake Hylia South Shore',
                                          'Lake Hylia Island'},
    'West Dark Death Mountain (Bottom)': {'West Dark Death Mountain (Top)'},
    'East Dark Death Mountain (Top)':    {'Dark Death Mountain Floating Island'},
    'East Dark Death Mountain (Bottom)': {'East Dark Death Mountain (Top)'},
    'Turtle Rock Area':                  {'Turtle Rock Ledge'},
    'Bumper Cave Area':                  {'Bumper Cave Ledge'},
    'Qirn Jump Water':                   {'Qirn Jump Area'},
    'Dark Witch Water':                  {'Dark Witch Area',
                                          'Dark Witch Northeast'},
    'Catfish Approach Water':            {'Catfish Approach Area'},
    'Pyramid Area':                      {'Pyramid Exit Ledge'},
    'Broken Bridge Water':               {'Broken Bridge West',
                                          'Broken Bridge Area',
                                          'Broken Bridge Northeast'},
    'Mire Area':                         {'Mire Teleporter Ledge'},
    'Ice Lake Water':                    {'Ice Lake Northwest Bank',
                                          'Ice Lake Southwest Ledge',
                                          'Ice Lake Southeast Ledge'}
}

isolated_regions = [
    'Death Mountain Floating Island',
    'Mimic Cave Ledge',
    'Spiral Mimic Ledge Extend',
    'Mountain Pass Ledge',
    'Maze Race Prize',
    'Maze Race Ledge',
    'Desert Ledge',
    'Desert Ledge Keep',
    'Desert Mouth',
    'Dark Death Mountain Floating Island',
    'Dark Death Mountain Ledge',
    'Dark Death Mountain Isolated Ledge',
    'Bumper Cave Ledge',
    'Pyramid Exit Ledge',
    'Hyrule Castle Water',
    'Pyramid Water'
]

ow_loc_prize_table = {
    'Master Sword Pedestal': (0x06d, 0x070),
    'Hobo': (0xb80, 0xb90),
    'Mushroom': (0x180, 0x140),
    'Lost Woods Hideout Tree': (0x200, 0x320),
    'Ether Tablet': (0x728, 0x017),
    'Spectacle Rock': (0x7F8, 0x128),
    'Old Man': (0x6A8, 0x3FF),
    'Floating Island': (0xD38, 0x038),
    'Death Mountain Bonk Rocks': (0xD48, 0x107),
    'Mountain Pass Pull Tree': (0x4E0, 0x380),
    'Mountain Pass Southeast Tree': (0x5A0, 0x3FF),
    'Lost Woods Pass West Tree': (0x080, 0x540),
    'Kakariko Portal Tree': (0x190, 0x540),
    'Fortune Bonk Rocks': (0x288, 0x558),
    'Bonk Rocks Tree': (0x680, 0x520),
    'Sanctuary Tree': (0x788, 0x594),
    'River Bend West Tree': (0xA38, 0x5FF),
    'River Bend East Tree': (0xB88, 0x558),
    'Bottle Merchant': (0x178, 0x7E8),
    'Blinds Hideout Tree': (0x118, 0x6F7),
    'Kakariko Welcome Tree': (0x358, 0x988),
    'Hyrule Castle Tree': (0x730, 0x780),
    'Wooden Bridge Tree': (0xA78, 0x6F0),
    'Eastern Palace Tree': (0xEC0, 0x968),
    'Maze Race': (0x0C0, 0xB00),
    'Flute Spot': (0x480, 0xAC0),
    'Flute Boy East Tree': (0x540, 0xB80),
    'Flute Boy South Tree': (0x540, 0xB80),
    'Central Bonk Rocks Tree': (0x768, 0xB37),
    'Tree Line Tree 2': (0xCD8, 0xB00),
    'Tree Line Tree 4': (0xCD8, 0xB00),
    'Desert Ledge': (0x018, 0xE88),
    'Bombos Tablet': (0x3E8, 0xEF8),
    'Flute Boy Approach North Tree': (0x588, 0xD07),
    'Flute Boy Approach South Tree': (0x588, 0xD07),
    'Lake Hylia Island': (0xB98, 0xD88),
    'Purple Chest': (0x588, 0xE96),
    'Sunken Treasure': (0x6F8, 0xF48),

    'Dark Lumberjack Tree': (0x438, 0x1F7),
    'Bumper Cave Ledge': (0x538, 0x277),
    'Catfish': (0xE80, 0x368),
    'Dark Fortune Bonk Rocks (Drop 1)': (0x288, 0x558),
    'Dark Fortune Bonk Rocks (Drop 2)': (0x288, 0x558),
    'Dark Graveyard West Bonk Rocks': (0x900, 0x580),
    'Dark Graveyard North Bonk Rocks': (0x900, 0x580),
    'Dark Graveyard Tomb Bonk Rocks': (0x900, 0x580),
    'Qirn Jump West Tree': (0xA98, 0x5FF),
    'Qirn Jump East Tree': (0xB88, 0x558),
    'Dark Witch Tree': (0xC28, 0x558),
    'Pyramid': (0x998, 0x778),
    'Pyramid Tree': (0x738, 0x908),
    'Palace of Darkness Tree': (0xEC0, 0x968),
    'Digging Game': (0x0C0, 0xB00),
    'Dark Tree Line Tree 2': (0xCD8, 0xB00),
    'Dark Tree Line Tree 3': (0xCD8, 0xB00),
    'Dark Tree Line Tree 4': (0xCD8, 0xB00),
    'Hype Cave Statue': (0x900, 0xDB0)
}

tile_swap_spoiler_table = \
"""                       0 1 2 3 4 5 6 7
                      +---+-+---+---+-+
      01234567   A(00)|   |s|   |   |s|
     +--------+       | s +-+ s | s +-+
A(00)|s ss s s|  B(08)|   |s|   |   |s|
B(08)|  s    s|       +-+-+-+-+-+-+-+-+
C(10)|ssssssss|  C(10)|s|s|s|s|s|s|s|s|
D(18)|s ss ss |       +-+-+-+-+-+-+-+-+
E(20)|  s  s  |  D(18)|   |s|   |s|   |
F(28)|ssssssss|       | s +-+ s +-+ s |
G(30)|s ssss s|  E(20)|   |s|   |s|   |
H(38)|  sss  s|       +-+-+-+-+-+-+-+-+
     +--------+  F(28)|s|s|s|s|s|s|s|s|
            +-+       +-+-+-+-+-+-+-+-+
  Ped/Hobo: |s|  G(30)|   |s|s|s|   |s|
            +-+       | s +-+-+-+ s +-+
      Zora: |s|  H(38)|   |s|s|s|   |s|
            +-+       +---+-+-+-+---+-+"""
