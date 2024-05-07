import copy
from itertools import zip_longest
import json
import logging
import os
import RaceRandom as random
import string
import time
import zlib
import base64

from BaseClasses import World, CollectionState, Item, Region, Location, Shop, Entrance, Settings
from Bosses import place_bosses
from Items import ItemFactory
from KeyDoorShuffle import validate_key_placement
from OverworldGlitchRules import create_owg_connections
from PotShuffle import shuffle_pots, shuffle_pot_switches
from Regions import create_regions, create_shops, mark_light_dark_world_regions, create_dungeon_regions, adjust_locations
from OverworldShuffle import link_overworld, create_dynamic_exits
from EntranceShuffle import link_entrances
from Rom import patch_rom, patch_race_rom, apply_rom_settings, LocalRom, JsonRom, get_hash_string
from Doors import create_doors
from DoorShuffle import link_doors, connect_portal, link_doors_prep
from RoomData import create_rooms
from Rules import set_rules
from Dungeons import create_dungeons
from Fill import distribute_items_restrictive, promote_dungeon_items, fill_dungeons_restrictive, ensure_good_items
from Fill import dungeon_tracking
from Fill import sell_potions, sell_keys, balance_multiworld_progression, balance_money_progression, lock_shop_locations
from ItemList import generate_itempool, difficulties, fill_prizes, customize_shops, fill_specific_items
from UnderworldGlitchRules import create_hybridmajor_connections, create_hybridmajor_connectors
from Utils import output_path, parse_player_names

from source.item.FillUtil import create_item_pool_config, massage_item_pool, district_item_pool_config
from source.overworld.EntranceShuffle2 import link_entrances_new
from source.tools.BPS import create_bps_from_data
from source.classes.CustomSettings import CustomSettings
from source.enemizer.DamageTables import DamageTable
from source.enemizer.Enemizer import randomize_enemies
from source.rom.DataTables import init_data_tables

version_number = '1.4.1.11'
version_branch = '-u'
__version__ = f'{version_number}{version_branch}'

from source.classes.BabelFish import BabelFish


class EnemizerError(RuntimeError):
    pass


def check_python_version():
    import sys
    version = sys.version_info
    if version.major < 3 or version.minor < 7:
        logging.warning(BabelFish().translate("cli","cli","old.python.version"), sys.version)


def main(args, seed=None, fish=None):
    check_python_version()
    if args.outputpath:
        os.makedirs(args.outputpath, exist_ok=True)
        output_path.cached_path = args.outputpath

    start = time.perf_counter()

    if args.securerandom:
        random.use_secure()
    seeded = False
    # initialize the world
    if args.code:
        for player, code in args.code.items():
            if code:
                Settings.adjust_args_from_code(code, player, args)
    customized = None
    if args.customizer:
        customized = CustomSettings()
        customized.load_yaml(args.customizer)
        seed = customized.determine_seed(seed)
        seeded = True
        customized.adjust_args(args)
    for i in zip(args.logic.values(), args.door_shuffle.values()):
        if i[0] == 'hybridglitches' and i[1] != 'vanilla':
            raise RuntimeError(BabelFish().translate("cli","cli","hybridglitches.door.shuffle"))
    world = World(args.multi, args.shuffle, args.door_shuffle, args.logic, args.mode, args.swords,
                  args.difficulty, args.item_functionality, args.timer, args.progressive, args.goal, args.algorithm,
                  args.accessibility, args.shuffleganon, args.custom, args.customitemarray, args.hints, args.spoiler)
    world.customizer = customized if customized else None
    logger = logging.getLogger('')
    if seed is None:
        random.seed(None)
        world.seed = random.randint(0, 999999999)
    else:
        world.seed = int(seed)
    if not seeded:
        random.seed(world.seed)

    if args.securerandom:
        world.seed = ''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(9))

    world.boots_hint = args.boots_hint.copy()
    world.remote_items = args.remote_items.copy()
    world.mapshuffle = args.mapshuffle.copy()
    world.compassshuffle = args.compassshuffle.copy()
    world.keyshuffle = args.keyshuffle.copy()
    world.bigkeyshuffle = args.bigkeyshuffle.copy()
    world.bombbag = args.bombbag.copy()
    world.flute_mode = args.flute_mode.copy()
    world.bow_mode = args.bow_mode.copy()
    world.crystals_needed_for_ganon = {player: random.randint(0, 7) if args.crystals_ganon[player] == 'random' else int(args.crystals_ganon[player]) for player in range(1, world.players + 1)}
    world.crystals_needed_for_gt = {player: random.randint(0, 7) if args.crystals_gt[player] == 'random' else int(args.crystals_gt[player]) for player in range(1, world.players + 1)}
    world.crystals_ganon_orig = args.crystals_ganon.copy()
    world.crystals_gt_orig = args.crystals_gt.copy()
    world.open_pyramid = args.openpyramid.copy()
    world.boss_shuffle = args.shufflebosses.copy()
    world.enemy_shuffle = args.shuffleenemies.copy()
    world.enemy_health = args.enemy_health.copy()
    world.enemy_damage = args.enemy_damage.copy()
    world.any_enemy_logic = args.any_enemy_logic.copy()
    world.beemizer = args.beemizer.copy()
    world.intensity = {player: random.randint(1, 3) if args.intensity[player] == 'random' else int(args.intensity[player]) for player in range(1, world.players + 1)}
    world.door_type_mode = args.door_type_mode.copy()
    world.trap_door_mode = args.trap_door_mode.copy()
    world.key_logic_algorithm = args.key_logic_algorithm.copy()
    world.decoupledoors = args.decoupledoors.copy()
    world.door_self_loops = args.door_self_loops.copy()
    world.experimental = args.experimental.copy()
    world.dungeon_counters = args.dungeon_counters.copy()
    world.fish = fish
    world.shopsanity = args.shopsanity.copy()
    world.dropshuffle = args.dropshuffle.copy()
    world.pottery = args.pottery.copy()
    world.potshuffle = args.shufflepots.copy()
    world.mixed_travel = args.mixed_travel.copy()
    world.standardize_palettes = args.standardize_palettes.copy()
    world.shufflelinks = args.shufflelinks.copy()
    world.shuffletavern = args.shuffletavern.copy()
    world.pseudoboots = args.pseudoboots.copy()
    world.overworld_map = args.overworld_map.copy()
    world.take_any = args.take_any.copy()
    world.restrict_boss_items = args.restrict_boss_items.copy()
    world.collection_rate = args.collection_rate.copy()
    world.colorizepots = args.colorizepots.copy()
    world.aga_randomness = args.aga_randomness.copy()

    world.treasure_hunt_count = {}
    world.treasure_hunt_total = {}
    for p in args.triforce_goal:
        if int(args.triforce_goal[p]) != 0 or int(args.triforce_pool[p]) != 0 or int(args.triforce_goal_min[p]) != 0 or int(args.triforce_goal_max[p]) != 0 or int(args.triforce_pool_min[p]) != 0 or int(args.triforce_pool_max[p]) != 0:
            if int(args.triforce_goal[p]) != 0:
                world.treasure_hunt_count[p] = int(args.triforce_goal[p])
            elif int(args.triforce_goal_min[p]) != 0 and int(args.triforce_goal_max[p]) != 0:
                world.treasure_hunt_count[p] = random.randint(int(args.triforce_goal_min[p]), int(args.triforce_goal_max[p]))
            else:
                world.treasure_hunt_count[p] = 8 if world.goal[p] == 'trinity' else 20
            if int(args.triforce_pool[p]) != 0:
                world.treasure_hunt_total[p] = int(args.triforce_pool[p])
            elif int(args.triforce_pool_min[p]) != 0 and int(args.triforce_pool_max[p]) != 0:
                world.treasure_hunt_total[p] = random.randint(max(int(args.triforce_pool_min[p]), world.treasure_hunt_count[p] + int(args.triforce_min_difference[p])), min(int(args.triforce_pool_max[p]), world.treasure_hunt_count[p] + int(args.triforce_max_difference[p])))
            else:
                world.treasure_hunt_total[p] = 10 if world.goal[p] == 'trinity' else 30
        else:
            # this will be handled in ItemList.py and custom item pool is used to determine the numbers
            world.treasure_hunt_count[p], world.treasure_hunt_total[p] = 0, 0

    world.rom_seeds = {player: random.randint(0, 999999999) for player in range(1, world.players + 1)}
    world.finish_init()

    logger.info(
      world.fish.translate("cli","cli","app.title") + "\n",
      __version__,
      world.seed,
      Settings.make_code(world, 1) if world.players == 1 else ''
    )

    parsed_names = parse_player_names(args.names, world.players, args.teams)
    world.teams = len(parsed_names)
    for i, team in enumerate(parsed_names, 1):
        if world.players > 1:
            logger.info('%s%s', 'Team%d: ' % i if world.teams > 1 else 'Players: ', ', '.join(team))
        for player, name in enumerate(team, 1):
            world.player_names[player].append(name)
    logger.info('')
    world.settings = CustomSettings()
    world.settings.create_from_world(world, args)

    outfilebase = f'DR_{args.outputname if args.outputname else world.seed}'

    for player in range(1, world.players + 1):
        world.difficulty_requirements[player] = difficulties[world.difficulty[player]]

        if world.mode[player] == 'standard' and world.enemy_shuffle[player] != 'none':
            if hasattr(world,"escape_assist") and player in world.escape_assist:
                world.escape_assist[player].append('bombs') # enemized escape assumes infinite bombs available and will likely be unbeatable without it

        if args.usestartinventory[player]:
            for tok in filter(None, args.startinventory[player].split(',')):
                name = tok.strip()
                name = name if name != 'Ocarina' or world.flute_mode[player] != 'active' else 'Ocarina (Activated)'
                item = ItemFactory(name, player)
                if item:
                    world.push_precollected(item)

    if world.spoiler_mode != 'none' and not args.jsonout:
        logger.info(world.fish.translate("cli", "cli", "create.meta"))
        world.spoiler.meta_to_file(output_path(f'{outfilebase}_Spoiler.txt'))
    if args.mystery and not args.suppress_meta:
        world.spoiler.mystery_meta_to_file(output_path(f'{outfilebase}_meta.txt'))

    for player in range(1, world.players + 1):
        create_regions(world, player)
        if world.logic[player] in ('owglitches', 'hybridglitches', 'nologic'):
            create_owg_connections(world, player)
        create_dungeon_regions(world, player)
        create_shops(world, player)
        create_doors(world, player)
        create_rooms(world, player)
        create_dungeons(world, player)
        world.damage_table[player] = DamageTable()
        world.data_tables[player] = init_data_tables(world, player)
        place_bosses(world, player)
        randomize_enemies(world, player)
        if world.logic[player] in ('nologic', 'hybridglitches'):
            create_hybridmajor_connections(world, player)
        adjust_locations(world, player)

    if world.customizer and world.customizer.get_start_inventory():
        for p, inv_list in world.customizer.get_start_inventory().items():
            if inv_list:
                for inv_item in inv_list:
                    item = ItemFactory(inv_item.strip(), p)
                    if item:
                        world.push_precollected(item)
    if args.print_custom_yaml:
        world.settings.record_info(world)

    if any(world.potshuffle.values()):
        logger.info(world.fish.translate("cli", "cli", "shuffling.pots"))
        for player in range(1, world.players + 1):
            if world.potshuffle[player]:
                if world.pottery[player] in ['none', 'cave', 'keys', 'cavekeys']:
                    shuffle_pots(world, player)
                else:
                    shuffle_pot_switches(world, player)

    logger.info(world.fish.translate("cli","cli","shuffling.world"))

    for player in range(1, world.players + 1):
        link_overworld(world, player)
        create_dynamic_exits(world, player)
        if world.experimental[player] or world.shuffle[player] in ['lite', 'lean', 'swapped'] or world.shuffletavern[player] or (world.customizer and world.customizer.get_entrances()):
            link_entrances_new(world, player)
        else:
            link_entrances(world, player)
        if world.logic[player] in ('nologic', 'hybridglitches'):
            create_hybridmajor_connectors(world, player)

    logger.info(world.fish.translate("cli", "cli", "shuffling.prep"))
    for player in range(1, world.players + 1):
        link_doors_prep(world, player)

    if args.print_custom_yaml:
        world.settings.record_entrances(world)
    create_item_pool_config(world)

    logger.info(world.fish.translate("cli", "cli", "shuffling.dungeons"))

    for player in range(1, world.players + 1):
        link_doors(world, player)
        mark_light_dark_world_regions(world, player)
    if args.print_custom_yaml:
        world.settings.record_doors(world)
    logger.info(world.fish.translate("cli", "cli", "generating.itempool"))

    for player in range(1, world.players + 1):
        generate_itempool(world, player)

    logger.info(world.fish.translate("cli","cli","calc.access.rules"))

    for player in range(1, world.players + 1):
        set_rules(world, player)

    district_item_pool_config(world)
    dungeon_tracking(world)
    fill_specific_items(world)
    for player in range(1, world.players + 1):
        if world.shopsanity[player]:
            sell_potions(world, player)
            if world.keyshuffle[player] == 'universal':
                sell_keys(world, player)
        else:
            lock_shop_locations(world, player)

    massage_item_pool(world)
    if args.print_custom_yaml:
        world.settings.record_item_pool(world)
    logger.info(world.fish.translate("cli", "cli", "placing.dungeon.prizes"))

    fill_prizes(world)

    logger.info(world.fish.translate("cli","cli","placing.dungeon.items"))

    if args.algorithm != 'equitable':
        shuffled_locations = world.get_unfilled_locations()
        random.shuffle(shuffled_locations)
        fill_dungeons_restrictive(world, shuffled_locations)
    else:
        promote_dungeon_items(world)

    for player in range(1, world.players+1):
        if world.logic[player] != 'nologic':
            for key_layout in world.key_layout[player].values():
                if not validate_key_placement(key_layout, world, player):
                    raise RuntimeError(
                      "%s: %s (%s %d)" %
                      (
                        world.fish.translate("cli", "cli", "keylock.detected"),
                        key_layout.sector.name,
                        world.fish.translate("cli", "cli", "player"),
                        player
                      )
                    )

    logger.info(world.fish.translate("cli","cli","fill.world"))

    distribute_items_restrictive(world, True)

    if world.players > 1:
        logger.info(world.fish.translate("cli", "cli", "balance.multiworld"))
        if args.algorithm in ['balanced', 'equitable']:
            balance_multiworld_progression(world)

    # if we only check for beatable, we can do this sanity check first before creating the rom
    world.clear_exp_cache()
    if not world.can_beat_game(log_error=True):
        raise RuntimeError(world.fish.translate("cli", "cli", "cannot.beat.game"))

    for player in range(1, world.players+1):
        if world.shopsanity[player]:
            customize_shops(world, player)
    if args.algorithm in ['balanced', 'equitable']:
        balance_money_progression(world)
    ensure_good_items(world, True)

    if args.print_custom_yaml:
        world.settings.record_item_placements(world)
        world.settings.write_to_file(output_path(f'{outfilebase}_custom.yaml'))

    rom_names = []
    jsonout = {}
    if not args.suppress_rom or args.bps:
        logger.info(world.fish.translate("cli","cli","patching.rom"))
        for team in range(world.teams):
            for player in range(1, world.players + 1):
                rom = JsonRom() if args.jsonout else LocalRom(args.rom)

                patch_rom(world, rom, player, team, bool(args.mystery))

                if args.race:
                    patch_race_rom(rom)

                rom_names.append((player, team, list(rom.name)))
                world.spoiler.hashes[(player, team)] = get_hash_string(rom.hash)

                apply_rom_settings(rom, args.heartbeep[player], args.heartcolor[player], args.quickswap[player],
                                   args.fastmenu[player], args.disablemusic[player], args.sprite[player],
                                   args.ow_palettes[player], args.uw_palettes[player], args.reduce_flashing[player],
                                   args.shuffle_sfx[player], args.msu_resume[player])

                if args.jsonout:
                    jsonout[f'patch_t{team}_p{player}'] = rom.patches
                    if args.bps:
                        localRom = LocalRom.fromJsonRom(rom, args.rom)
                        patch = create_bps_from_data(LocalRom(args.rom, patch=False).buffer, localRom.buffer)
                        jsonout[f'bps_t{team}_p{player}'] = base64.b64encode(patch.binary_ba).decode()
                else:
                    outfilepname = f'_T{team+1}' if world.teams > 1 else ''
                    if world.players > 1:
                        outfilepname += f'_P{player}'
                    if world.players > 1 or world.teams > 1:
                        outfilepname += f"_{world.player_names[player][team].replace(' ', '_')}" if world.player_names[player][team] != 'Player %d' % player else ''
                    outfilesuffix = f'_{Settings.make_code(world, player)}' if not args.outputname else ''
                    if args.bps:
                        patchfile = output_path(f'{outfilebase}{outfilepname}{outfilesuffix}.bps')
                        patch = create_bps_from_data(LocalRom(args.rom, patch=False).buffer, rom.buffer)
                        with open(patchfile, 'wb') as stream:
                            stream.write(patch.binary_ba)
                    if not args.suppress_rom:
                        sfc_file = output_path(f'{outfilebase}{outfilepname}{outfilesuffix}.sfc')
                        rom.write_to_file(sfc_file)

        if world.players > 1:
            multidata = zlib.compress(json.dumps({"names": parsed_names,
                                                  "roms": rom_names,
                                                  "remote_items": [player for player in range(1, world.players + 1) if world.remote_items[player]],
                                                  "locations": [((location.address, location.player), (location.item.code, location.item.player))
                                                                for location in world.get_filled_locations() if type(location.address) is int],
                                                  "tags" : ["DR"]
                                                  }).encode("utf-8"))
            if args.jsonout:
                jsonout["multidata"] = list(multidata)
            else:
                with open(output_path('%s_multidata' % outfilebase), 'wb') as f:
                    f.write(multidata)

    if args.mystery and not args.suppress_meta:
        world.spoiler.hashes_to_file(output_path(f'{outfilebase}_meta.txt'))
    elif world.spoiler_mode != 'none' and not args.jsonout:
        world.spoiler.hashes_to_file(output_path(f'{outfilebase}_Spoiler.txt'))
    if world.spoiler_mode != 'none' and not args.jsonout:
        logger.info(world.fish.translate("cli", "cli", "patching.spoiler"))
        world.spoiler.to_file(output_path(f'{outfilebase}_Spoiler.txt'))
        if 'debug' in world.spoiler.settings:
            world.spoiler.extras(output_path(f'{outfilebase}_Spoiler.txt'))

    if not args.skip_playthrough:
        logger.info(world.fish.translate("cli","cli","calc.playthrough"))
        create_playthrough(world)

    if args.jsonout:
        print(json.dumps({**jsonout, 'spoiler': world.spoiler.to_json()}))
    elif world.spoiler_mode != 'none':
        logger.info(world.fish.translate("cli","cli","patching.spoiler"))
        if args.jsonout:
            with open(output_path('%s_Spoiler.json' % outfilebase), 'w') as outfile:
              outfile.write(world.spoiler.to_json())
        else:
            world.spoiler.playthrough_to_file(output_path(f'{outfilebase}_Spoiler.txt'))

    YES = world.fish.translate("cli","cli","yes")
    NO = world.fish.translate("cli","cli","no")
    logger.info("")
    logger.info(world.fish.translate("cli","cli","done"))
    logger.info("")
    logger.info(world.fish.translate("cli","cli","made.rom") % (YES if (args.create_rom) else NO))
    logger.info(world.fish.translate("cli","cli","made.playthrough") % (YES if (args.calc_playthrough) else NO))
    logger.info(world.fish.translate("cli","cli","made.spoiler") % (YES if (not args.jsonout and world.spoiler_mode != 'none') else NO))
    logger.info(world.fish.translate("cli","cli","seed") + ": %s", world.seed)
    logger.info(world.fish.translate("cli","cli","total.time"), time.perf_counter() - start)

#    print_wiki_doors_by_room(dungeon_regions,world,1)
#    print_wiki_doors_by_region(dungeon_regions,world,1)

    return world


def copy_world(world):
    # ToDo: Not good yet
    ret = World(world.players, world.shuffle, world.doorShuffle, world.logic, world.mode, world.swords,
                world.difficulty, world.difficulty_adjustments, world.timer, world.progressive, world.goal, world.algorithm,
                world.accessibility, world.shuffle_ganon, world.custom, world.customitemarray, world.hints, world.spoiler_mode)
    ret.teams = world.teams
    ret.player_names = copy.deepcopy(world.player_names)
    ret.remote_items = world.remote_items.copy()
    ret.required_medallions = world.required_medallions.copy()
    ret.bottle_refills = world.bottle_refills.copy()
    ret.swamp_patch_required = world.swamp_patch_required.copy()
    ret.ganon_at_pyramid = world.ganon_at_pyramid.copy()
    ret.powder_patch_required = world.powder_patch_required.copy()
    ret.ganonstower_vanilla = world.ganonstower_vanilla.copy()
    ret.treasure_hunt_count = world.treasure_hunt_count.copy()
    ret.treasure_hunt_icon = world.treasure_hunt_icon.copy()
    ret.sewer_light_cone = world.sewer_light_cone.copy()
    ret.seed = world.seed
    ret.can_access_trock_eyebridge = world.can_access_trock_eyebridge.copy()
    ret.can_access_trock_front = world.can_access_trock_front.copy()
    ret.can_access_trock_big_chest = world.can_access_trock_big_chest.copy()
    ret.can_access_trock_middle = world.can_access_trock_middle.copy()
    ret.can_take_damage = world.can_take_damage
    ret.difficulty_requirements = world.difficulty_requirements.copy()
    ret.fix_fake_world = world.fix_fake_world.copy()
    ret.lamps_needed_for_dark_rooms = world.lamps_needed_for_dark_rooms
    ret.mapshuffle = world.mapshuffle.copy()
    ret.compassshuffle = world.compassshuffle.copy()
    ret.keyshuffle = world.keyshuffle.copy()
    ret.bigkeyshuffle = world.bigkeyshuffle.copy()
    ret.bombbag = world.bombbag.copy()
    ret.flute_mode = world.flute_mode.copy()
    ret.bow_mode = world.bow_mode.copy()
    ret.crystals_needed_for_ganon = world.crystals_needed_for_ganon.copy()
    ret.crystals_needed_for_gt = world.crystals_needed_for_gt.copy()
    ret.crystals_ganon_orig = world.crystals_ganon_orig.copy()
    ret.crystals_gt_orig = world.crystals_gt_orig.copy()
    ret.open_pyramid = world.open_pyramid.copy()
    ret.take_any = world.take_any.copy()
    ret.boss_shuffle = world.boss_shuffle.copy()
    ret.enemy_shuffle = world.enemy_shuffle.copy()
    ret.enemy_health = world.enemy_health.copy()
    ret.enemy_damage = world.enemy_damage.copy()
    ret.any_enemy_logic = world.any_enemy_logic.copy()
    ret.beemizer = world.beemizer.copy()
    ret.intensity = world.intensity.copy()
    ret.decoupledoors = world.decoupledoors.copy()
    ret.door_self_loops = world.door_self_loops.copy()
    ret.door_type_mode = world.door_type_mode.copy()
    ret.trap_door_mode = world.trap_door_mode.copy()
    ret.key_logic_algorithm = world.key_logic_algorithm.copy()
    ret.aga_randomness = world.aga_randomness.copy()
    ret.experimental = world.experimental.copy()
    ret.shopsanity = world.shopsanity.copy()
    ret.dropshuffle = world.dropshuffle.copy()
    ret.pottery = world.pottery.copy()
    ret.potshuffle = world.potshuffle.copy()
    ret.mixed_travel = world.mixed_travel.copy()
    ret.standardize_palettes = world.standardize_palettes.copy()
    ret.restrict_boss_items = world.restrict_boss_items.copy()
    ret.damage_table = world.damage_table
    ret.data_tables = world.data_tables  # can be changed...

    for player in range(1, world.players + 1):
        create_regions(ret, player)
        create_dynamic_exits(ret, player)
        create_dungeon_regions(ret, player)
        create_shops(ret, player)
        create_rooms(ret, player)
        create_dungeons(ret, player)
        if world.logic[player] in ('owglitches', 'hybridglitches', 'nologic'):
            create_owg_connections(ret, player)
        if world.logic[player] in ('nologic', 'hybridglitches'):
            create_hybridmajor_connections(ret, player)


    # there are region references here they must be migrated to preserve integrity
    # ret.exp_cache = world.exp_cache.copy()

    copy_dynamic_regions_and_locations(world, ret)
    for player in range(1, world.players + 1):
        if world.mode[player] == 'standard':
            parent = ret.get_region('Menu', player)
            target = ret.get_region('Hyrule Castle Secret Entrance', player)
            connection = Entrance(player, 'Uncle S&Q', parent)
            parent.exits.append(connection)
            connection.connect(target)

    # copy bosses
    for dungeon in world.dungeons:
        for level, boss in dungeon.bosses.items():
            ret.get_dungeon(dungeon.name, dungeon.player).bosses[level] = boss

    for player in range(1, world.players + 1):
        for shop in world.shops[player]:
            copied_shop = ret.get_region(shop.region.name, shop.region.player).shop
            copied_shop.inventory = copy.copy(shop.inventory)

    # connect copied world
    copied_locations = {(loc.name, loc.player): loc for loc in ret.get_locations()}  # caches all locations
    for region in world.regions:
        copied_region = ret.get_region(region.name, region.player)
        copied_region.is_light_world = region.is_light_world
        copied_region.is_dark_world = region.is_dark_world
        copied_region.dungeon = region.dungeon
        copied_region.locations = [copied_locations[(location.name, location.player)] for location in region.locations]
        for location in copied_region.locations:
            location.parent_region = copied_region
        for entrance in region.entrances:
            ret.get_entrance(entrance.name, entrance.player).connect(copied_region)

    # fill locations
    for location in world.get_locations():
        new_location = ret.get_location(location.name, location.player)
        if location.item is not None:
            item = Item(location.item.name, location.item.advancement, location.item.priority, location.item.type, player=location.item.player)
            new_location.item = item
            item.location = new_location
            item.world = ret
        new_location.event = location.event
        new_location.locked = location.locked
        # these need to be modified properly by set_rules
        new_location.access_rule = lambda state: True
        new_location.item_rule = lambda state: True
        new_location.forced_item = location.forced_item
        new_location.pot = location.pot

    # copy remaining itempool. No item in itempool should have an assigned location
    for item in world.itempool:
        ret.itempool.append(Item(item.name, item.advancement, item.priority, item.type, player = item.player))

    for item in world.precollected_items:
        ret.push_precollected(ItemFactory(item.name, item.player))

    # copy progress items in state
    ret.state.prog_items = world.state.prog_items.copy()
    ret.state.stale = {player: True for player in range(1, world.players + 1)}

    ret.doors = world.doors
    for door in ret.doors:
        entrance = ret.check_for_entrance(door.name, door.player)
        if entrance is not None:
            entrance.door = door
    ret.paired_doors = world.paired_doors
    ret.rooms = world.rooms
    ret.inaccessible_regions = world.inaccessible_regions
    ret.dungeon_layouts = world.dungeon_layouts
    ret.key_logic = world.key_logic
    ret.dungeon_portals = world.dungeon_portals
    for player, portals in world.dungeon_portals.items():
        for portal in portals:
            connect_portal(portal, ret, player)
    ret.sanc_portal = world.sanc_portal

    for player in range(1, world.players + 1):
        if world.logic[player] in ('nologic', 'hybridglitches'):
            create_hybridmajor_connectors(ret, player)
        set_rules(ret, player)

    return ret


def copy_dynamic_regions_and_locations(world, ret):
    for region in world.dynamic_regions:
        new_reg = Region(region.name, region.type, region.hint_text, region.player)
        ret.regions.append(new_reg)
        ret.initialize_regions([new_reg])
        ret.dynamic_regions.append(new_reg)

        # Note: ideally exits should be copied here, but the current use case (Take anys) do not require this

        if region.shop:
            new_reg.shop = Shop(new_reg, region.shop.room_id, region.shop.type, region.shop.shopkeeper_config,
                                region.shop.custom, region.shop.locked, region.shop.sram_address)
            ret.shops[region.player].append(new_reg.shop)

    for location in world.dynamic_locations:
        new_reg = ret.get_region(location.parent_region.name, location.parent_region.player)
        new_loc = Location(location.player, location.name, location.address, location.crystal, location.hint_text, new_reg)
        new_loc.type = location.type
        new_reg.locations.append(new_loc)

        ret.clear_location_cache()


def create_playthrough(world):
    # create a copy as we will modify it
    old_world = world
    world = copy_world(world)

    # get locations containing progress items
    prog_locations = [location for location in world.get_filled_locations() if location.item.advancement
                      or world.goal[location.player] == 'completionist']
    optional_locations = ['Trench 1 Switch', 'Trench 2 Switch', 'Ice Block Drop', 'Skull Star Tile']
    state_cache = [None]
    collection_spheres = []
    state = CollectionState(world)
    sphere_candidates = list(prog_locations)
    logging.getLogger('').debug(world.fish.translate("cli","cli","building.collection.spheres"))
    while sphere_candidates:
        state.sweep_for_events(key_only=True)

        sphere = set()
        # build up spheres of collection radius. Everything in each sphere is independent from each other in dependencies and only depends on lower spheres
        for location in sphere_candidates:
            if state.can_reach(location) and state.not_flooding_a_key(world, location):
                sphere.add(location)

        for location in sphere:
            sphere_candidates.remove(location)
            state.collect(location.item, True, location)

        collection_spheres.append(sphere)

        state_cache.append(state.copy())

        logging.getLogger('').debug(world.fish.translate("cli", "cli", "building.calculating.spheres"), len(collection_spheres), len(sphere), len(prog_locations))
        if not sphere:
            if world.accessibility[location.item.player] != 'none':
                logging.getLogger('').error(world.fish.translate("cli", "cli", "cannot.reach.items"),
                                            [world.fish.translate("cli","cli","cannot.reach.item") % (location.item.name, location.item.player, location.name, location.player) for location in sphere_candidates])
            if any([location.name not in optional_locations and world.accessibility[location.item.player] != 'none' for location in sphere_candidates]):
                raise RuntimeError(world.fish.translate("cli", "cli", "cannot.reach.progression"))
            else:
                old_world.spoiler.unreachables = sphere_candidates.copy()
                break

    # in the second phase, we cull each sphere such that the game is still beatable, reducing each range of influence to the bare minimum required inside it
    for num, sphere in reversed(list(enumerate(collection_spheres))):
        to_delete = set()
        for location in sphere:
            if world.goal[location.player] == 'completionist':
                continue  # every location for that player is required
            # we remove the item at location and check if game is still beatable
            logging.getLogger('').debug('Checking if %s (Player %d) is required to beat the game.', location.item.name, location.item.player)
            old_item = location.item
            location.item = None
            # todo: this is not very efficient, but I'm not sure how else to do it for this backwards logic
            world.clear_exp_cache()
            if world.can_beat_game(state_cache[max(num-1, 0)]):
                logging.getLogger('').debug(f'{old_item.name} (Player {old_item.player}) is not required')
                to_delete.add(location)
            else:
                # still required, got to keep it around
                logging.getLogger('').debug(f'{old_item.name} (Player {old_item.player}) is required')
                location.item = old_item

        # cull entries in spheres for spoiler walkthrough at end
        sphere -= to_delete

    # second phase, sphere 0
    for item in [i for i in world.precollected_items if i.advancement]:
        logging.getLogger('').debug('Checking if %s (Player %d) is required to beat the game.', item.name, item.player)
        world.precollected_items.remove(item)
        world.state.remove(item)
        if not world.can_beat_game():
            world.push_precollected(item)

    # we are now down to just the required progress items in collection_spheres. Unfortunately
    # the previous pruning stage could potentially have made certain items dependant on others
    # in the same or later sphere (because the location had 2 ways to access but the item originally
    # used to access it was deemed not required.) So we need to do one final sphere collection pass
    # to build up the correct spheres

    required_locations = {item for sphere in collection_spheres for item in sphere}
    state = CollectionState(world)
    collection_spheres = []
    while required_locations:
        state.sweep_for_events(key_only=True)

        sphere = list(filter(lambda loc: state.can_reach(loc) and state.not_flooding_a_key(world, loc), required_locations))

        for location in sphere:
            required_locations.remove(location)
            state.collect(location.item, True, location)

        collection_spheres.append(sphere)

        logging.getLogger('').debug(world.fish.translate("cli","cli","building.final.spheres"), len(collection_spheres), len(sphere), len(required_locations))
        if not sphere:
            if world.has_beaten_game(state):
                required_locations.clear()
            else:
                raise RuntimeError(world.fish.translate("cli","cli","cannot.reach.required"))

    # store the required locations for statistical analysis
    old_world.required_locations = [(location.name, location.player) for sphere in collection_spheres for location in sphere]

    def flist_to_iter(node):
        while node:
            value, node = node
            yield value

    def get_path(state, region):
        reversed_path_as_flist = state.path.get(region, (region, None))
        string_path_flat = reversed(list(map(str, flist_to_iter(reversed_path_as_flist))))
        # Now we combine the flat string list into (region, exit) pairs
        pathsiter = iter(string_path_flat)
        pathpairs = zip_longest(pathsiter, pathsiter)
        return list(pathpairs)

    old_world.spoiler.paths = dict()
    for player in range(1, world.players + 1):
        old_world.spoiler.paths.update({location.gen_name(): get_path(state, location.parent_region) for sphere in collection_spheres for location in sphere if location.player == player})
        for path in dict(old_world.spoiler.paths).values():
            if any(exit == 'Pyramid Fairy' for (_, exit) in path):
                old_world.spoiler.paths[str(world.get_region('Big Bomb Shop', player))] = get_path(state, world.get_region('Big Bomb Shop', player))

    # we can finally output our playthrough
    old_world.spoiler.playthrough = {"0": [str(item) for item in world.precollected_items if item.advancement]}
    for i, sphere in enumerate(collection_spheres):
        old_world.spoiler.playthrough[str(i + 1)] = {location.gen_name(): str(location.item) for location in sphere}
