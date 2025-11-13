import RaceRandom as random
import itertools
import logging
import os
from collections import defaultdict, deque


from BaseClasses import Direction, CrystalBarrier, DoorType, Door, Hook, Entrance, Sector
from Regions import create_dungeon_region
from Utils import clear_file
from source.dungeon.DungeonGenerationCommon import DungeonBuilder, GenerationException, define_sector_features, dungeon_portals
from source.dungeon.DungeonGenerationCommon import GlobalPolarity, find_sector, assign_sector_helper, hanger_from_door, hook_from_door, sum_polarity
from source.dungeon.DungeonGenSectorDesc import create_sector_descriptors
from source.dungeon.DungeonGenTransitivity import do_transitivity_check as do_transitivity_check_new

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
            portal_sector = next((p for p in portal_pool if region_name in p.region_set()), None)
            if portal_sector:
                region = world.get_region(region_name, player)
                door = create_portal_door(world, player, next(e.name for e in region.exits if e.name.startswith('Enter ')))
                portal_sector.outstanding_doors.append(door)
                p = world.get_portal(portal, player)
                p.door = door  # assign placeholder door
            else:
                portal_sector = next(p for p in sector_pool if region_name in p.region_set())
                region = world.get_region(region_name, player)
                door = create_portal_door(world, player, next(e.name for e in region.exits if e.name.startswith('Enter ')))
                p = world.get_portal(portal, player)
                if p.assigned:
                    door.dest = p.door
            portal_assignments[key].append(portal_sector)

    if 'Hyrule Castle' in dungeon_pool and world.mode[player] == 'standard':
        sewer_portal = create_dungeon_region(player, 'Sewer Access Portal', 'Hyrule Castle', None, ['Enter HC (Sewers)'])
        world.regions.append(sewer_portal)
        door = create_portal_door(world, player, next(e.name for e in sewer_portal.exits if e.name.startswith('Enter ')))
        sector = Sector()
        sector.regions.append(sewer_portal)
        sector.outstanding_doors.append(door)
        sector_pool.append(sector)
        throne_room = find_sector('Hyrule Castle Throne Room', sector_pool)
        throne_room.outstanding_doors.remove(world.get_door('Hyrule Castle Throne Room N', player))

    define_sector_features(sector_pool)
    cut_empty_sectors(sector_pool, world, player)
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
        if skull3 is not None and any(not p.destination for p in skull3.portals):
            portal_assignments['Skull Woods Back'].append(skull3)
            assignments.remove(skull3)
        else:
            candidates = [x for x in assignments if any(not p.destination for p in x.portals)]
            some_portal = random.choice(candidates)
            portal_assignments['Skull Woods Back'].append(some_portal)
            assignments.remove(some_portal)
        # the rest go in front
        for portal in assignments:
            portal_assignments['Skull Woods Front'].append(portal)
    # a strict split will prevent this from being a cross-world connector inadvertently
    if 'Desert Palace' in dungeon_pool and len(portal_assignments['Desert Palace']) > 1:
        dungeon_pool.append('Desert Palace Back')
        dungeon_pool.append('Desert Palace Front')
        dungeon_pool.remove('Desert Palace')
        assignments = portal_assignments['Desert Palace']
        # get desert back portal assignment if present, else a random 1
        back_portal = find_sector('Desert Back Portal', assignments)
        if back_portal is not None and any(not p.destination for p in back_portal.portals):
            portal_assignments['Desert Palace Back'].append(back_portal)
            assignments.remove(back_portal)
        else:
            candidates = [x for x in assignments if any(not p.destination for p in x.portals)]
            some_portal = random.choice(candidates)
            portal_assignments['Desert Palace Back'].append(some_portal)
            assignments.remove(some_portal)
        # the rest go in front
        for portal in assignments:
            portal_assignments['Desert Palace Front'].append(portal)
    if 'Hyrule Castle' in dungeon_pool and world.mode[player] == 'standard':
        dungeon_pool.append('Hyrule Castle Dungeon')
        dungeon_pool.append('Hyrule Castle Sewers')
        dungeon_pool.remove('Hyrule Castle')
        assignments = portal_assignments['Hyrule Castle']
        sanc_portal = find_sector('Sanctuary Portal', assignments)
        portal_assignments['Hyrule Castle Sewers'].append(sanc_portal)
        assignments.remove(sanc_portal)
        main_portal = find_sector('Hyrule Castle South Portal', assignments)
        portal_assignments['Hyrule Castle Dungeon'].append(main_portal)
        assignments.remove(main_portal)
        # the other two should go together
        paired = random.choice(['Hyrule Castle Dungeon', 'Hyrule Castle Sewers'])
        for portal in assignments:
            portal_assignments[paired].append(portal)

    all_sectors = sector_pool + portal_pool
    info = DungeonGenInfo(gen_log, all_sectors, flags, dungeon_map)

    for key in dungeon_pool:
        current_dungeon = dungeon_map[key] = DungeonBuilder(key)
        current_dungeon.split_flag = key not in dungeon_aliases
        # handle special assignments
        for sector in portal_assignments[key]:
            propose_sector(current_dungeon, sector, info, True)
        # handle special sectors:
        if key == 'Hyrule Castle Dungeon':  # builder doesn't exist except in standard
            for r_name in ['Hyrule Dungeon Cellblock', 'Hyrule Castle Throne Room']:  # need to deliver zelda
                propose_sector(current_dungeon, find_sector(r_name, sector_pool), info, True)
        elif key == 'Hyrule Castle Sewers':  # builder doesn't exist except in standard
            # Sanctuary handled by portals above
            propose_sector(current_dungeon, find_sector('Sewer Access Portal', sector_pool), info, True)
        elif key == 'Thieves Town' and world.get_dungeon("Thieves Town", player).boss.enemizer_name == 'Blind':
            propose_sector(current_dungeon, find_sector("Thieves Blind's Cell", sector_pool), info, True)

    def lock_down_default_sectors(definition):
        for key, builder_list in definition.items():
            sector = find_sector(key, info.sector_pool)
            if sector:
                candidate_builders = [d for d in dungeon_map if d in builder_list]
                if len(candidate_builders) == 1:
                    chosen_builder = next(iter(candidate_builders))
                else:
                    chosen_builder = random.choice(candidate_builders)
                propose_sector(dungeon_map[chosen_builder], sector, info, False, restrict_list=list(builder_list))

    # this handles boss sectors
    lock_down_default_sectors(dungeon_boss_regions)

    # handles drop down lobbies - lock down for now - technically can move to a different
    if not info.flags.warps_pits or not info.flags.lobbies:
        lock_down_default_sectors(default_lobby_drops)

    if world.mode[player] == 'standard':
        exclude_sector(find_sector('Swamp Lobby', info.sector_pool), info, dungeon_aliases['Hyrule Castle'])
        if world.bow_mode[player].startswith('retro'):
            # support more if interior doors happen: 'PoD Bow Statue Right', 'GT Mimics 2', 'Eastern Duo Eyegores'
            for r in ['PoD Mimics 2', 'PoD Mimics 1', 'GT Mimics 1', 'Eastern Single Eyegore']:
                exclude_sector(find_sector(r, info.sector_pool), info, dungeon_aliases['Hyrule Castle'])
    do_custom_sectors(dungeon_map, info, world, player)
    do_custom_exclusions(info, world, player)

    if info.flags.lobbies:
        # randomly choose which portal will not be portalAble for this seed
        for dungeon, choices_list in portal_choices.items():
            # only needed if crossing, could restore later if they happen to be in the same dungeon
            if dungeon in pool:
                for needed_choice in choices_list:
                    needed_choice = [c for c in needed_choice if world.get_door(c, player).dest is None]
                    if len(needed_choice) > 1:
                        choice = random.choice(needed_choice)
                        world.get_door(choice, player).portalAble = False

    possible_builders = list(dungeon_map.keys())
    balance_map = proposal_balance(info)
    possible_builders = [b for b in possible_builders if not balance_map[b].complete()]
    weights = determine_weights(possible_builders, info, world, player)
    choices = random.choices(possible_builders, weights, k=len(info.sector_pool)) if info.sector_pool else []
    for idx, sector in enumerate(info.sector_pool):
        if valid_for_move(sector, choices[idx], info):
            propose_sector(dungeon_map[choices[idx]], sector, info)
        else:
            options = [b for b in possible_builders if valid_for_move(sector, b, info)]
            weights = determine_weights(options, info, world, player)
            choice = random.choices(options, weights, k=1)
            propose_sector(dungeon_map[choice[0]], sector, info)
    if world.dungeon_shuffle_algorithm[player] == 'biased':
        seed_biased_builders(info, world, player)
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


# ------------------------------ #
#     Sector Cutting Utility
# ------------------------------ #
def is_sector_cuttable(sector):
    return (
        all(len(r.locations) == 0 for r in sector.regions)
        and not sector.portals
        # trying to eliminate more sectors
        # and not sector.c_switch
        # and not sector.blue_barrier
        # and not sector.orange_barrier
        # and not sector.item_logic
        and 'Boss' not in sector.item_logic
    )

 #--- Smaller Dungeon Gen: Remove neutral, empty sectors before descriptor creation ---#
def cut_empty_sectors(sector_pool, world, player):
    if world.smaller_dungeon_gen[player]:
        cuttable_sectors = [s for s in sector_pool if is_sector_cuttable(s)]
        removed_sectors = {s for s in cuttable_sectors if s.polarity().is_neutral()}
        cuttable_sectors[:] = [s for s in cuttable_sectors if s not in removed_sectors]
        cuttable_sectors.sort(key=lambda s: s.sector_key())  # sort for consistency in shuffle
        random.shuffle(cuttable_sectors) # randomize order to find different combinations based on seed
        while True:
            # Only consider sectors not already removed
            candidates = [s for s in cuttable_sectors if s not in removed_sectors]
            if not candidates:
                break
            # Try all combinations, smallest first, to find a neutral polarity set
            found = False
            for r in range(2, len(candidates) + 1):
                for combo in itertools.combinations(candidates, r):
                    pol = sum_polarity(combo)
                    if pol.is_neutral():
                        for s in combo:
                            removed_sectors.add(s)
                        found = True
                        break
                if found:
                    break
            if not found:
                break
        # Remove found sectors from sector_pool
        for s in removed_sectors:
            sector_pool.remove(s)


def do_custom_sectors(dungeon_map, info, world, player):
    if world.customizer and world.customizer.get_dungeon_sectors(player):
        for region, dungeons in world.customizer.get_dungeon_sectors(player).items():
            sector = find_sector(region, info.sector_pool)
            if sector:
                if not isinstance(dungeons, list):
                    dungeons = [dungeons]
                builders = []
                restrict_list = []
                for dungeon in dungeons:
                    if dungeon in dungeon_map:
                        builders.append(dungeon_map[dungeon])
                        restrict_list.append(dungeon)
                    else:
                        builders.extend([dungeon_map[d] for d in dungeon_aliases[dungeon] if d in dungeon_map])
                        restrict_list.extend([d for d in dungeon_aliases[dungeon] if d in dungeon_map])
                builder = random.choice(builders)
                propose_sector(builder, sector, info, False, restrict_list=restrict_list)


def do_custom_exclusions(info, world, player):
    if world.customizer and world.customizer.get_dungeon_exclusions(player):
        for region, dungeon_list in world.customizer.get_dungeon_exclusions(player).items():
            sector = find_sector(region, info.sector_pool)
            if sector:
                exclude_sector(sector, info, sum((dungeon_aliases[d] for d in dungeon_list), []))


def determine_weights(builders, info, world, player):
    if world.dungeon_shuffle_algorithm[player] == 'biased':
        bias_present = any(world.dungeon_bias[player] in b for b in builders)
        if bias_present:
            return [(weight_map[builder] if world.dungeon_bias[player] in builder else 0) for builder in builders]
        else:
            balance_map = proposal_balance(info)
            unbalanced = {dungeon: balance for dungeon, balance in balance_map.items() if not balance.balanced()}
            return [(weight_map[builder] if builder in unbalanced else 0) for builder in builders]
    return [weight_map[builder] for builder in builders]


def exclude_sector(sector, info, exclude_list):
    if sector:
        sector.exclude_list = exclude_list
        info.gen_log.debug(f'{sector.sector_key()} excluded from various dungeons (see config)')


def propose_sector(builder, new_sector, info, lock=False, restrict_list=None):
    if new_sector in info.proposal[builder.name]:  # already been assigned
        return
    info.proposal[builder.name].append(new_sector)
    if lock:
        new_sector.locked = True
        del info.sector_pool[new_sector]
        info.gen_log.debug(f'{new_sector.sector_key()} locked to {builder.name}')
    elif restrict_list:
        new_sector.restrict_list = restrict_list
        del info.sector_pool[new_sector]
        info.gen_log.debug(f'{new_sector.sector_key()} restricted to {builder.name}')
    else:
        info.gen_log.debug(f'{new_sector.sector_key()} assigned to {builder.name}')


def proposal_balance(info):
    balance_map = {}
    for dungeon, sector_list in info.proposal.items():
        dungeon_balance = Balance(dungeon, info)
        dungeon_balance.extend(sector_list)
        balance_map[dungeon] = dungeon_balance
    return balance_map


def balance_move_sector(unbalanced, balance_map, info):
    if info.random_moves > 0:
        do_a_random_move(info, unbalanced, balance_map)
        return

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

    # location balance?
    location_needs = [dungeon for dungeon, balance in balance_map.items() if not balance.location_balanced()]
    if location_needs:
        target = random.choice(location_needs)
        fix_location_balance(target, balance_map, info)
        return

    # dead ends next
    branching_needs = [dungeon for dungeon, balance in balance_map.items() if balance.need_branches()]
    if branching_needs:
        target = random.choice(branching_needs)
        fix_branching_balance(target, balance_map, info)
        return

    # parity next
    # parity_needs = [dungeon for dungeon, balance in balance_map.items() if balance.need_parity()]
    # if len(parity_needs):
    #     target = random.choice(parity_needs)
    #     fixed = fix_parity_balance(target, balance_map, info)
    #     if fixed:  # otherwise look at polarity to solve issue
    #         return

    # polarity next
    polarity_problems = [dungeon for dungeon, balance in unbalanced.items() if not balance.polarity_balanced()]
    if polarity_problems:
        best_choices, combo_len = [], 1
        while len(best_choices) == 0:
            if len(polarity_problems) == 0:
                combo_len += 1
                if combo_len > 4:
                    info.random_moves = 10
                    info.gen_log.debug(f'Problem with polarity balance, resorting to random moves')
                    return
                polarity_problems = [dungeon for dungeon, balance in unbalanced.items() if not balance.polarity_balanced()]
            weights = [unbalanced[d].charge(False) for d in polarity_problems]
            target = random.choices(polarity_problems, weights, k=1)[0]
            polarity_problems.remove(target)
            unlocked_cnt = {id: sum(1 for sector in info.proposal[id] if not sector.locked) for id in balance_map}
            candidates = {k: v for k, v in balance_map.items() if k != target}
            candidates = sorted(list(candidates.items()), key=lambda item: ((0 if item[1].polarity_balanced() else 1), item[1].branches, unlocked_cnt[item[0]]))

            provider, best_choices, best_charge = None, [], None
            while len(best_choices) == 0 and len(candidates) > 0:
                provider, balance_info = candidates.pop()
                best_choices, best_charge = find_a_good_polarity_shift(provider, target, balance_map, info, combo_len)
                swap_choices, swap_charge = find_a_good_polarity_shift(target, provider, balance_map, info, combo_len)
                if swap_charge is not None and (best_charge is None or swap_charge > best_charge):
                    best_choices = swap_choices
                    provider, target = target, provider
                if not best_choices and combo_len == 1:
                    trade = find_a_polarity_trade(provider, target, balance_map, info)
                    if trade is not None:
                        move_a, move_b = trade
                        perform_move(info, move_a, provider, target)
                        info.gen_log.debug(f'Traded {move_a.sector_key()} from {provider} to {target} for polarity balance')
                        perform_move(info, move_b, target, provider)
                        info.gen_log.debug(f'Traded {move_b.sector_key()} from {target} to {provider} for polarity balance')
                        return
        best = random.choice(best_choices)
        # do the moves
        for sector in best:
            perform_move(info, sector, provider, target)
            info.gen_log.debug(f'Moved {sector.sector_key()} from {provider} to {target} for polarity balance')
        return

    # transitivity last
    transitivity_problems = [dungeon for dungeon, balance in balance_map.items() if not balance.transitive()]
    if transitivity_problems:
        target = random.choice(transitivity_problems)
        fix_transitivity(target, balance_map, info)
        # return


def do_a_random_move(info, unbalanced, balance_map):
    move_to_unbalanced = random.choice([True, False])
    targets = [dungeon for dungeon, balance in unbalanced.items()]
    target = random.choice(targets)
    provider = random.choice([dungeon for dungeon in balance_map if dungeon != target])
    if move_to_unbalanced:
        possible_moves = [s for s in info.proposal[provider] if valid_for_move(s, target, info) and not is_sector_neutral(s)]
        if len(possible_moves) == 0:
            return  # just skip this time
        move = random.choice(possible_moves)
        perform_move(info, move, provider, target)
        info.gen_log.debug(f'Moved {move.sector_key()} from {provider} to {target} randomly')
    else:
        possible_moves = [s for s in info.proposal[target] if valid_for_move(s, provider, info) and not is_sector_neutral(s)]
        if len(possible_moves) == 0:
            return  # just skip this time
        move = random.choice(possible_moves)
        perform_move(info, move, target, provider)
        info.gen_log.debug(f'Moved {move.sector_key()} from {target} to {provider} randomly')
    info.random_moves -= 1

def find_a_good_polarity_shift(provider, target, balance_map, info, combination_length=1):
    best_choices, best_charge = [], None
    possible_moves = [s for s in info.proposal[provider] if valid_for_move(s, target, info) and not is_sector_neutral(s)]
    for sector_combo in itertools.combinations(possible_moves, combination_length):
        target_charge = balance_map[target].charge(False)
        target_balance = Balance(target, info)
        target_balance.extend([x for x in info.proposal[target]])
        target_balance.extend(sector_combo)
        new_target_charge = target_balance.charge(False)
        target_change = target_charge - new_target_charge
        # calc provider charge
        curr_charge = balance_map[provider].charge(False)
        provider_balance = Balance(provider, info)
        provider_balance.extend([x for x in info.proposal[provider] if x not in sector_combo])
        new_provider_charge = provider_balance.charge(False)
        provider_change = curr_charge - new_provider_charge
        # no progressing change
        if new_target_charge >= target_charge and new_provider_charge >= curr_charge:
            continue
        # if the target is polarity balanced, then we want to maximize the charge difference
        charge_diff = provider_change + target_change
        if len(best_choices) == 0 or charge_diff > best_charge:
            best_choices.clear()
            best_choices.append(sector_combo)
            best_charge = charge_diff
        elif charge_diff == best_charge:
            best_choices.append(sector_combo)
    return best_choices, best_charge


def find_a_polarity_trade(builder_a, builder_b, balance_map, info):
    a_moves = [s for s in info.proposal[builder_a] if not is_sector_neutral(s) and valid_for_move(s, builder_b, info)]
    a_charge_orig = balance_map[builder_a].charge(False)
    b_moves = [s for s in info.proposal[builder_b] if not is_sector_neutral(s) and valid_for_move(s, builder_a, info)]
    b_charge_orig = balance_map[builder_b].charge(False)
    for a_sector, b_sector in itertools.product(range(len(a_moves)), range(len(b_moves))):
        a = a_moves[a_sector]
        b = b_moves[b_sector]
        a_charge = calc_charge_for_trade(b, a, builder_a, info)
        b_charge = calc_charge_for_trade(a, b, builder_b, info)
        if ((a_charge < a_charge_orig and b_charge <= b_charge_orig)
           or (b_charge < b_charge_orig and a_charge <= a_charge_orig)):
            return a, b
    return None


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
            if not valid_for_move(sector, target, info) or not sector.c_switch:
                continue
            bal = Balance(provider, info)
            bal.extend([x for x in info.proposal[provider] if x != sector])
            charge = bal.charge(False)
            if best is None or charge < best_charge:
                best = sector
                best_charge = charge
    if best is not None:
        # do the move
        perform_move(info, best, provider, target)
        info.gen_log.debug(f'Moved {best.sector_key()} from {provider} to {target} for crystal balance')
        return
    # if none, then need to move the crystal needed elsewhere
    candidate_sector = next(sector for sector in info.proposal[target] if not sector.locked and sector.blue_barrier)
    possible_benefactors = [dungeon for dungeon, balance in balance_map.items() if balance.crystal_provided > 0]
    for benefactor in possible_benefactors:
        bal = Balance(benefactor, info)
        bal.extend([x for x in info.proposal[benefactor]])
        bal.append(candidate_sector)
        charge = bal.charge(False)
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
            if not valid_for_move(sector, target, info) or not criteria(sector):
                continue
            bal = Balance(provider, info)
            bal.extend([x for x in info.proposal[provider] if x != sector])
            charge = bal.charge(False)
            if best is None or charge < best_charge:
                best = sector
                best_charge = charge
            if best_charge == 0:
                break
    perform_move(info, best, provider, target)
    info.gen_log.debug(f'Moved {best.sector_key()} from {provider} to {target} for portal balance')


def fix_location_balance(target, balance_map, info):
    candidates = {k: v for k, v in balance_map.items() if k != target and v.non_bk_locations > 1}
    candidates = sorted(list(candidates.items()), key=lambda item: item[1].non_bk_locations)
    provider, best, best_charge = None, None, None
    while best is None:
        provider, balance_info = candidates.pop()
        for sector in info.proposal[provider]:
            if not valid_for_move(sector, target, info) or cnt_non_bk_locations(sector) == 0:
                continue
            bal = Balance(provider, info)
            bal.extend([x for x in info.proposal[provider] if x != sector])
            charge = bal.charge(False)
            if best is None or charge < best_charge:
                best = sector
                best_charge = charge
            if best_charge == 0:
                break
    perform_move(info, best, provider, target)
    info.gen_log.debug(f'Moved {best.sector_key()} from {provider} to {target} for location balance')


def fix_branching_balance(target, balance_map, info):
    unlocked_cnt = {id: sum(1 for sector in info.proposal[id] if valid_for_move(sector, target, info)) for id in balance_map}
    candidates = {k: v for k, v in balance_map.items() if k != target}
    candidates = sorted(list(candidates.items()), key=lambda item: (item[1].branches, unlocked_cnt[item[0]]))
    provider, best, swap = find_branching_solution(target, candidates, balance_map, info)
    if swap:
        perform_move(info, best, target, provider)
        info.gen_log.debug(f'Moved {best.sector_key()} from {target} to {provider} for branching balance')
    else:
        perform_move(info, best, provider, target)
        info.gen_log.debug(f'Moved {best.sector_key()} from {provider} to {target} for branching balance')



def fix_parity_balance(target, balance_map, info):
    unlocked_cnt = {id: sum(1 for sector in info.proposal[id] if not sector.locked) for id in balance_map}
    candidates = {k: v for k, v in balance_map.items() if v.need_parity() and k != target}
    candidates = sorted(list(candidates.items()), key=lambda item: (item[1].branches, unlocked_cnt[item[0]]))
    used_targets, expand_candidates = [], False
    provider, best, best_charge = None, None, None
    while best is None:
        if len(candidates) == 0:
            used_targets.append(target)
            parity_needs = [dungeon for dungeon, balance in balance_map.items() if balance.need_parity() and dungeon not in used_targets]
            if len(parity_needs) == 0:
                if expand_candidates:
                    return False  # unable to fix parity, try polarity swap instead?
                # try to fix parity using other dungeons
                expand_candidates = True
                used_targets.clear()
                parity_needs = [dungeon for dungeon, balance in balance_map.items() if balance.need_parity() and dungeon not in used_targets]
            target = random.choice(parity_needs)
            candidates = {k: v for k, v in balance_map.items() if (v.need_parity() or expand_candidates) and k != target}
            candidates = sorted(list(candidates.items()), key=lambda item: (item[1].branches, unlocked_cnt[item[0]]))
        provider, balance_info = candidates.pop()
        for sector in info.proposal[provider]:
            if not valid_for_move(sector, target, info):
                continue
            bal = Balance(provider, info)
            bal.extend([x for x in info.proposal[provider] if x != sector])
            # expand_candidates allows us to disturb parity of provider dungeon to shake things up
            if not bal.need_parity() or expand_candidates:
                bal2 = Balance(target, info)
                bal2.extend(info.proposal[target])
                bal2.append(sector)
                if not bal2.need_parity():
                    charge = bal.charge(False)
                    if best is None or charge < best_charge:
                        best_charge = charge
                        best = sector
    perform_move(info, best, provider, target)
    info.gen_log.debug(f'Moved {best.sector_key()} from {provider} to {target} for parity')
    return True


def fix_transitivity(target, balance_map, info):
    unlocked_cnt = {id: sum(1 for sector in info.proposal[id] if not sector.locked) for id in balance_map}
    candidates = sorted(list(balance_map.items()), key=lambda item: unlocked_cnt[item[0]])

    provider, best, swap = None, None, False
    while best is None:
        if len(candidates) == 0:
            raise GenerationException(f'No transitivity solution found during fix_transitivity step for "{target}"')
        provider, balance_info = candidates.pop()
        if provider == target:
            continue
        best, swap = find_valid_move_for_trans(provider, target, info)
    if swap:
        provider, target = target, provider
    for s in best:
        perform_move(info, s, provider, target)
        info.gen_log.debug(f'Moved {s.sector_key()} from {provider} to {target} for transitivity')


def find_valid_move_for_trans(provider, target, info):
    max_combination_length = 4

    valid_provider_moves = [sector for sector in info.proposal[provider] if valid_for_move(sector, target, info)]
    valid_target_moves = [sector for sector in info.proposal[target] if valid_for_move(sector, provider, info)]

    best, best_charge, swap = None, None, False
    for length in range(1, max_combination_length + 1):
        for provider_combination in itertools.combinations(valid_provider_moves, length):
            if best_charge == 0:
                break
            if check_combination_balance(provider_combination, info):
                target_balance = Balance(target, info)
                target_balance.extend([x for x in info.proposal[target]])
                target_balance.extend(provider_combination)
                if not target_balance.transitive():
                    continue
                bal = Balance(provider, info)
                bal.extend([x for x in info.proposal[provider] if x not in provider_combination])
                if not bal.transitive():
                    continue
                charge = bal.charge()
                if best is None or charge < best_charge:
                    best = provider_combination
                    best_charge = charge
                    swap = False
        if best is None:
            for target_combination in itertools.combinations(valid_target_moves, length):
                if best_charge == 0:
                    break
                if check_combination_balance(target_combination, info):
                    target_balance = Balance(target, info)
                    target_balance.extend([x for x in info.proposal[target] if x not in target_combination])
                    if not target_balance.transitive():
                        continue
                    bal = Balance(provider, info)
                    bal.extend([x for x in info.proposal[provider]])
                    bal.extend(target_combination)
                    if not bal.transitive():
                        continue
                    charge = bal.charge()
                    if best is None or charge < best_charge:
                        best = target_combination
                        best_charge = charge
                        swap = True
        if best is not None:
            return best, swap
    return None, False


def check_combination_balance(sectors, info):
    bal = Balance('temp', info)
    bal.extend(sectors)
    return bal.polarity_balanced()


def find_branching_solution(target, candidates, balance_map, info):
    provider, best_choices, best_charge = None, [], None
    current_t_charge = balance_map[target].charge(False)
    curr_branch_score = balance_map[target].branch_score()
    while len(best_choices) == 0:
        if len(candidates) == 0:
            raise GenerationException(f'No branching solution found during find_branching_solution step for "{target}"')
        provider, balance_info = candidates.pop()
        charge_to_beat = current_t_charge + balance_map[provider].charge(False)
        for sector in info.proposal[provider]:
            if not valid_for_move(sector, target, info):
                continue
            charge, p_bal, t_bal = calc_combo_charge_for_move(sector, provider, target, info)
            if charge >= charge_to_beat and (t_bal.branch_score() >= curr_branch_score or p_bal.need_branches()):
                continue
            if len(best_choices) == 0 or charge < best_charge:
                best_choices.clear()
                best_choices.append((sector, False))
                best_charge = charge
            elif charge == best_charge:
                best_choices.append((sector, False))
        if len(best_choices) == 0:
            for sector in info.proposal[target]:
                if not valid_for_move(sector, provider, info):
                    continue
                charge, t_bal, p_bal = calc_combo_charge_for_move(sector, target, provider, info)
                if charge >= charge_to_beat and (p_bal.need_branches() or t_bal.branch_score() >= curr_branch_score):
                    continue
                if len(best_choices) == 0 or charge < best_charge:
                    best_choices.clear()
                    best_choices.append((sector, True))
                    best_charge = charge
                elif charge == best_charge:
                    best_choices.append((sector, True))
    best, swap = random.choice(best_choices)
    return provider, best, swap


def calc_combo_charge_for_move(sector, provider, target, info):
    bal = Balance(provider, info)
    bal.extend([x for x in info.proposal[provider] if x != sector])
    charge = bal.charge(False)
    bal2 = Balance(target, info)
    bal2.extend([x for x in info.proposal[target]])
    bal2.append(sector)
    total_charge = charge + bal2.charge(False)
    return total_charge, bal, bal2


def calc_charge_for_trade(sector_inc, sector_del, target, info):
    bal = Balance(target, info)
    bal.extend([x for x in info.proposal[target] if x != sector_del])
    bal.append(sector_inc)
    return bal.charge(False)


def valid_for_move(sector, dest, info):
    return (not sector.locked and (sector not in info.recent_moves)
            and (sector.restrict_list is None or dest in sector.restrict_list)
            and (sector.exclude_list is None or dest not in sector.exclude_list))


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

    def __init__(self, gen_log, all_sectors, flags, dungeon_map):
        self.proposal = defaultdict(list)
        self.gen_log = gen_log
        self.global_pole = GlobalPolarity(all_sectors)
        self.sector_pool = dict.fromkeys(all_sectors)
        self.flags = flags
        self.transitive_db = {}
        self.recent_moves = deque(maxlen=2)
        self.dungeon_map = dungeon_map
        self.random_moves = 0


class DoorFlags:
    def __init__(self):
        self.normal: str = 'none'
        self.spiral: bool = False
        self.straight: bool = False
        self.ladder: bool = False
        self.edges: str = 'none'
        self.lobbies: bool = False
        self.vanilla_traps: bool = False
        self.stair_loops: bool = False
        self.decoupled: bool = False
        self.warps_pits: bool = False  # NotYetImplemented
        self.cave_interiors: bool = False  # NotYetImplemented
        self.intratile: bool = False   # NotYetImplemented

        self.std_flag: bool = False
        self.rupee_bow_flag: bool = False
        self.bk_shuffle_flag: bool = False


    def from_world(self, world, player):
        self.vanilla_traps = world.trap_door_mode[player] == 'vanilla'
        self.stair_loops = world.door_self_loops[player]
        self.decoupled = world.decoupledoors[player]
        if world.doorShuffle[player] != 'door_type_only':
            if world.intensity[player] >= 1:
                self.normal = 'both'
                self.spiral = True
            if world.intensity[player] >= 2:
                self.straight = True
                self.ladder = True
                self.edges = 'both'
            if world.intensity[player] >= 3:
                self.lobbies = True
        self.std_flag = world.mode[player] == 'standard'
        self.rupee_bow_flag = world.bow_mode[player].startswith('retro')  # rupee bow
        self.bk_shuffle_flag = (world.bigkeyshuffle[player]  # big key can be anywhere
                                or world.pottery[player] not in ['none', 'cave'] # pottery item can have the big key
                                or world.door_type_mode in ['big', 'all', 'chaos'])  # big key doors can be shuffled
        return self

    def from_custom(self, intensity):
        if 'normal' in intensity:
            self.normal = intensity['normal']
        if 'spiral' in intensity:
            self.spiral = intensity['spiral']
        if 'straight' in intensity:
            self.straight = intensity['straight']
        if 'ladder' in intensity:
            self.ladder = intensity['ladder']
        if 'edges' in intensity:
            self.edges = intensity['edges']
        if 'lobbies' in intensity:
            self.lobbies = intensity['lobbies']


def score_door(item):
    door, sector = item
    longest = max(len(l) for d, l in sector.descriptor.reachability.items())
    score = len(sector.descriptor.reachability[door])
    if score == longest:
        score += 100
    return score

def cnt_non_bk_locations(sector):
    count = 0
    for region in sector.regions:
        for loc in region.locations:
            if '- Big Chest' not in loc.name and loc.parent_region.name not in ["Thieves Blind's Cell Interior", 'Hyrule Dungeon Cell', 'Thieves Boss']:
                count += 1
    return count


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
        self.connectables = 0

        self.dead_ends = 0
        self.branches = 0

        self.crystal_provided = 0
        self.crystal_needed = 0

        self.portal_needed = 0  # total needed
        self.destination_portals = 0  # not deadEnd or passage

        self.non_dead_end_portals = 0  # always at least one
        self.passable_portals = 0  # should be equal to destination portals + 1 (primary portal)
        self.both_pass_non_dead = 0  # unless not all passable portals are non-dead-end
        self.portal_options = 0  # total available

        self.bk_required = False
        self.non_bk_locations = 0

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
        if sector.portals:
            for portal in sector.portals:
                if not portal.assigned:
                    self.portal_needed += 1
                    if portal.destination:
                        self.destination_portals += 1

        adj = 0 if (sector.portals and any(not p.destination for p in sector.portals)) or 'Sewer Access Portal' == sector.sector_key() else 2
        best_access = max((len(access) for d, access in sector.descriptor.reachability.items() if d is not None), default=0)
        if sector.portals and any(not p.destination for p in sector.portals) and len(sector.outstanding_doors) > 0:
            best_access = max(best_access, 1)  # at least one branch for portal only sectors
        missing_doors = len(sector.outstanding_doors) - best_access
        branches = best_access - adj - missing_doors  # negative number represents dead ends
        if branches > 0:
            self.branches += branches
        elif branches < 0:
            self.dead_ends -= branches

        for region in sector.regions:
            for loc in region.locations:
                if '- Big Chest' in loc.name or loc.parent_region.name in ["Thieves Blind's Cell Interior", 'Hyrule Dungeon Cell', 'Thieves Boss']:
                    self.bk_required = True
                else:
                    self.non_bk_locations += 1

        if sector.blue_barrier and not sector.c_switch:
            self.crystal_needed += 1
        if sector.c_switch:
            self.crystal_provided += 1

        marked = []  # only one counted per super
        for d in sector.outstanding_doors:
            self.connectables += 1
            if d.portalAble and d.roomIndex not in marked:
                self.portal_options += 1
                marked.append(d.roomIndex)
                if d.passage:
                    self.passable_portals += 1
                if not d.deadEnd:
                    self.non_dead_end_portals += 1
                if d.passage and not d.deadEnd:
                    self.both_pass_non_dead += 0

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

    def complete(self):
        return self.connectables == 0 and self.balanced()

    def balanced(self):
        if not self.location_balanced():
            return False
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

    def non_transitive_balanced(self):
        if not self.polarity_balanced():
            return False
        if self.branches < self.dead_ends:
            return False
        if self.crystal_needed > 0 and self.crystal_provided == 0:
            return False
        if not self.portal_balanced():
            return False
        return True


    def pol_sum(self):
        return (self.north - self.south, self.east - self.west, 0 if self.stair_balanced() else 1)

    def location_balanced(self):
        if self.bk_required and self.non_bk_locations == 0:
            return False
        return True

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

    # <= 0 indicates enough branches
    def branch_score(self):
        return self.dead_ends - self.branches

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
        if self.portal_needed == 0:
            return True
        if self.portal_needed > 1 and self.non_dead_end_portals == 0:
            return False
        if self.destination_portals > 0:
            # only need a extra passable if all non-dead-end portals are passable (for primary portal)
            extra = 1 if self.passable_portals == self.both_pass_non_dead else 0
            if self.passable_portals < self.destination_portals + extra:  # we need 1 + destination passable portals
                return False
        return self.portal_needed <= self.portal_options

    def transitive(self):
        if not self.non_transitive_balanced():  # short-circuit expensive transitivity calls
            return False
        if self.transitive_init:
            return self.transitive_flag
        # neutral_sectors = [s for s in self.sectors if is_sector_neutral(s)]
        # non_neutral_sectors = [s for s in self.sectors if s not in neutral_sectors]
        db_key = frozenset([str(s) for s in self.sectors])
        if db_key in self.info.transitive_db:
            self.transitive_flag = self.info.transitive_db[db_key]
            self.transitive_init = True
            return self.transitive_flag
        # new transitivity calc
        transitivity = do_transitivity_check_new(self.info.dungeon_map[self.name], self.sectors, self.info.flags)
        self.info.transitive_db[db_key] = transitivity
        self.transitive_flag = transitivity
        self.transitive_init = True
        return transitivity

    def charge(self, include_t=True):
        charge = abs(self.north - self.south)
        charge += abs(self.east - self.west)
        charge += max(self.one_ways - self.landings, 0)
        charge += 0 if self.stair_balanced() else 1
        charge += 0 if self.crystal_needed == 0 or self.crystal_provided > 0 else self.crystal_needed
        charge += 0 if self.branches >= self.dead_ends else self.dead_ends
        charge += 0 if self.portal_balanced() else 1
        # charge += 0 if not self.need_parity() else .5  # penalty for disturbing parity
        # only run the transitivity check here if everything else is already good
        # otherwise it's likely not going to work
        charge += 0 if charge == 0 and include_t and self.transitive() else 1
        return charge


def seed_biased_builders(info, world, player):
    balance_map = proposal_balance(info)
    unbalanced = {dungeon: balance for dungeon, balance in balance_map.items() if not balance.balanced()}
    biased = [d for d in balance_map if world.dungeon_bias[player] in d]
    seedlings = [d for d in unbalanced if d not in biased]
    for seedling in seedlings:
        provider = random.choice(biased)
        candidates = [s for s in info.proposal[provider] if valid_for_move(s, seedling, info)]
        best, best_score = None, None
        for _ in range(400):
            amt = random.randint(1, 4)
            cluster = random.sample(candidates, k=amt)
            bal = Balance(seedling, info)
            bal.extend(info.proposal[seedling])
            bal.extend(cluster)
            charge = bal.charge()
            num_locations = sum(len(s.chest_location_set) for s in cluster)
            score = (charge, num_locations)
            if best is None or score < best_score:
                best = cluster
                best_score = score
            if best_score == (0, 0):
                break
        for sector in best:
            perform_move(info, sector, provider, seedling)
            info.gen_log.debug(f'Moved {sector.sector_key()} from {provider} to {seedling} for seeding')


def do_transitivity_check(sectors, starting_point_list):
    door_sector_map = {d: s for s in sectors for d in s.outstanding_doors}
    trans_calc = Transitivity()
    for s in sectors:
        if s.portals and any(not p.destination for p in s.portals):
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
        new_doors = {d for d, c, f in sector.descriptor.reachability[door] if d != door and d not in self.explored_doors}
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

dungeon_aliases = {
    'Hyrule Castle': ['Hyrule Castle', 'Hyrule Castle Dungeon', 'Hyrule Castle Sewers'],
    'Eastern Palace': ['Eastern Palace'],
    'Desert Palace': ['Desert Palace', 'Desert Palace Back', 'Desert Palace Front'],
    'Tower of Hera': ['Tower of Hera'],
    'Agahnims Tower': ['Agahnims Tower'],
    'Palace of Darkness': ['Palace of Darkness'],
    'Swamp Palace': ['Swamp Palace'],
    'Skull Woods': ['Skull Woods', 'Skull Woods Back', 'Skull Woods Front'],
    'Thieves Town': ['Thieves Town'],
    'Ice Palace': ['Ice Palace'],
    'Misery Mire': ['Misery Mire'],
    'Turtle Rock': ['Turtle Rock'],
    'Ganons Tower': ['Ganons Tower'],
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
    'Palace of Darkness': [['PoD Harmless Hellway SE', 'PoD Falling Bridge SW']],
    'Skull Woods': [['Skull Pot Prison SE', 'Skull 2 East Lobby SW'], ['Skull 1 Lobby S', 'Skull Map Room SE']],
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
    'Hyrule Castle Dungeon': half_dungeon_weight,
    'Hyrule Castle Sewers': half_dungeon_weight
}
