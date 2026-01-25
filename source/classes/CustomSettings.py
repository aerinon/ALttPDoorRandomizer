import os
import urllib.request
import urllib.parse
import yaml
from typing import Any
from yaml.representer import Representer
from Utils import HexInt, hex_representer
from collections import defaultdict
from pathlib import Path

import RaceRandom as random
from BaseClasses import LocationType, DoorType
from source.overworld.FluteShuffle import default_flute_connections, flute_data
from source.tools.MysteryUtils import roll_settings, get_weights


class CustomSettings(object):

    def __init__(self):
        self.file_source = None
        self.relative_dir = None
        self.world_rep = {}
        self.player_range = None
        self.player_map = {}  # player number to name

    def load_yaml(self, file):
        self.file_source = load_yaml(file)
        head, filename = os.path.split(file)
        self.relative_dir = head
        if 'version' in self.file_source and self.file_source['version'].startswith('2'):
            player_number = 1
            for key in self.file_source.keys():
                if key in ['meta', 'version']:
                    continue
                else:
                    self.player_map[player_number] = key
                    player_number += 1

    def determine_seed(self, default_seed):
        if 'meta' in self.file_source:
            meta = defaultdict(lambda: None, self.file_source['meta'])
            seed = meta['seed']
            if seed:
                random.seed(seed)
                return seed
        if default_seed is None:
            random.seed(None)
            seed = random.randint(0, 999999999)
        else:
            seed = default_seed
        random.seed(seed)
        return seed

    def determine_players(self):
        if 'meta' not in self.file_source:
            return None
        meta = defaultdict(lambda: None, self.file_source['meta'])
        return meta['players']

    def adjust_args(self, args, resolve_weighted=True):
        def get_setting(value: Any, default):
            if value or value == 0:
                if isinstance(value, dict):
                    if resolve_weighted:
                        return random.choices(list(value.keys()), list(value.values()), k=1)[0]
                    return None
                else:
                    return value
            return default
        if 'meta' in self.file_source:
            meta = defaultdict(lambda: None, self.file_source['meta'])
            args.multi = get_setting(meta['players'], args.multi)
            args.algorithm = get_setting(meta['algorithm'], args.algorithm)
            args.outputname = get_setting(meta['name'], args.outputname)
            args.bps = get_setting(meta['bps'], args.bps)
            args.suppress_rom = get_setting(meta['suppress_rom'], args.suppress_rom)
            args.skip_playthrough = get_setting(meta['skip_playthrough'], args.skip_playthrough)
            args.spoiler = get_setting(meta['spoiler'], args.spoiler)
            args.names = get_setting(meta['names'], args.names)
            args.race = get_setting(meta['race'], args.race)
            args.notes = get_setting(meta['user_notes'], args.notes)
        self.player_range = range(1, args.multi + 1)
        if 'settings' in self.file_source:
            for p in self.player_range:
                player_setting = self.file_source['settings'][p]
                if isinstance(player_setting, str):
                    weights = get_weights(os.path.join(self.relative_dir, player_setting))
                    settings = defaultdict(lambda: None, vars(roll_settings(weights)))
                    args.mystery = True
                else:
                    settings = defaultdict(lambda: None, player_setting)
                args.ow_layout[p] = get_setting(settings['ow_layout'], args.ow_layout[p])
                args.ow_parallel[p] = get_setting(settings['ow_parallel'], args.ow_parallel[p])
                args.ow_terrain[p] = get_setting(settings['ow_terrain'], args.ow_terrain[p])
                args.ow_crossed[p] = get_setting(settings['ow_crossed'], args.ow_crossed[p])
                if args.ow_crossed[p] == 'chaos':
                    import logging
                    logging.getLogger('').info("Crossed OWR option 'chaos' is deprecated. Use 'unrestricted' instead.")
                    args.ow_crossed[p] = 'unrestricted'
                args.ow_keepsimilar[p] = get_setting(settings['ow_keepsimilar'], args.ow_keepsimilar[p])
                args.ow_mixed[p] = get_setting(settings['ow_mixed'], args.ow_mixed[p])
                args.ow_whirlpool[p] = get_setting(settings['ow_whirlpool'], args.ow_whirlpool[p])
                args.ow_fluteshuffle[p] = get_setting(settings['ow_fluteshuffle'], args.ow_fluteshuffle[p])
                args.ow_fog[p] = get_setting(settings['ow_fog'], args.ow_fog[p])
                args.shuffle_followers[p] = get_setting(settings['shuffle_followers'], args.shuffle_followers[p])
                args.bonk_drops[p] = get_setting(settings['bonk_drops'], args.bonk_drops[p])
                args.shuffle[p] = get_setting(settings['shuffle'], args.shuffle[p])
                args.door_shuffle[p] = get_setting(settings['door_shuffle'], args.door_shuffle[p])
                args.logic[p] = get_setting(settings['logic'], args.logic[p])
                args.mode[p] = get_setting(settings['mode'], args.mode[p])
                args.boots_hint[p] = get_setting(settings['boots_hint'], args.boots_hint[p])
                args.swords[p] = get_setting(settings['swords'], args.swords[p])
                args.flute_mode[p] = get_setting(settings['flute_mode'], args.flute_mode[p])
                args.bow_mode[p] = get_setting(settings['bow_mode'], args.bow_mode[p])
                args.item_functionality[p] = get_setting(settings['item_functionality'], args.item_functionality[p])
                args.goal[p] = get_setting(settings['goal'], args.goal[p])
                args.difficulty[p] = get_setting(settings['difficulty'], args.difficulty[p])
                args.accessibility[p] = get_setting(settings['accessibility'], args.accessibility[p])
                args.retro[p] = get_setting(settings['retro'], args.retro[p])
                args.take_any[p] = get_setting(settings['take_any'], args.take_any[p])
                args.hints[p] = get_setting(settings['hints'], args.hints[p])
                args.shopsanity[p] = get_setting(settings['shopsanity'], args.shopsanity[p])
                args.dropshuffle[p] = get_setting(settings['dropshuffle'], args.dropshuffle[p])
                args.pottery[p] = get_setting(settings['pottery'], args.pottery[p])

                if get_setting(settings['keydropshuffle'], args.keydropshuffle[p]):
                    if args.dropshuffle[p] == 'none':
                        args.dropshuffle[p] = 'keys'
                    if args.pottery[p] == 'none':
                        args.pottery[p] = 'keys'

                if args.retro[p] or args.mode[p] == 'retro':
                    if args.bow_mode[p] == 'progressive':
                        args.bow_mode[p] = 'retro'
                    elif args.bow_mode[p] == 'silvers':
                        args.bow_mode[p] = 'retro_silvers'
                    args.take_any[p] = 'random' if args.take_any[p] == 'none' else args.take_any[p]
                    args.keyshuffle[p] = 'universal'

                ow_shuffle = get_setting(settings['ow_shuffle'], args.ow_shuffle[p])
                if ow_shuffle == 'parallel':
                    args.ow_layout = 'wild'
                    args.ow_parallel = True
                elif ow_shuffle == 'full':
                    args.ow_layout = 'wild'
                    args.ow_parallel = False

                args.mixed_travel[p] = get_setting(settings['mixed_travel'], args.mixed_travel[p])
                args.standardize_palettes[p] = get_setting(settings['standardize_palettes'],
                                                           args.standardize_palettes[p])
                args.intensity[p] = get_setting(settings['intensity'], args.intensity[p])
                args.door_type_mode[p] = get_setting(settings['door_type_mode'], args.door_type_mode[p])
                args.trap_door_mode[p] = get_setting(settings['trap_door_mode'], args.trap_door_mode[p])
                args.key_logic_algorithm[p] = get_setting(settings['key_logic_algorithm'], args.key_logic_algorithm[p])
                args.decoupledoors[p] = get_setting(settings['decoupledoors'], args.decoupledoors[p])
                args.door_self_loops[p] = get_setting(settings['door_self_loops'], args.door_self_loops[p])
                args.dungeon_counters[p] = get_setting(settings['dungeon_counters'], args.dungeon_counters[p])
                args.crystals_gt[p] = get_setting(settings['crystals_gt'], args.crystals_gt[p])
                args.crystals_ganon[p] = get_setting(settings['crystals_ganon'], args.crystals_ganon[p])
                args.experimental[p] = get_setting(settings['experimental'], args.experimental[p])
                args.collection_rate[p] = get_setting(settings['collection_rate'], args.collection_rate[p])
                args.openpyramid[p] = get_setting(settings['openpyramid'], args.openpyramid[p])
                args.prizeshuffle[p] = get_setting(settings['prizeshuffle'], args.prizeshuffle[p])
                args.bigkeyshuffle[p] = get_setting(settings['bigkeyshuffle'], args.bigkeyshuffle[p])
                args.keyshuffle[p] = get_setting(settings['keyshuffle'], args.keyshuffle[p])
                args.mapshuffle[p] = get_setting(settings['mapshuffle'], args.mapshuffle[p])
                args.compassshuffle[p] = get_setting(settings['compassshuffle'], args.compassshuffle[p])

                dungeon_item_map = { 0: 'none',
                                     1: 'wild' }
                if args.mapshuffle[p] in dungeon_item_map:
                    args.mapshuffle[p] = dungeon_item_map[args.mapshuffle[p]]
                if args.compassshuffle[p] in dungeon_item_map:
                    args.compassshuffle[p] = dungeon_item_map[args.compassshuffle[p]]
                if args.bigkeyshuffle[p] in dungeon_item_map:
                    args.bigkeyshuffle[p] = dungeon_item_map[args.bigkeyshuffle[p]]
                
                if get_setting(settings['keysanity'], args.keysanity):
                    if args.bigkeyshuffle[p] in ['none', 0]:
                        args.bigkeyshuffle[p] = 'wild'
                    if args.keyshuffle[p] == 'none':
                        args.keyshuffle[p] = 'wild'
                    if args.mapshuffle[p] in ['none', 0]:
                        args.mapshuffle[p] = 'wild'
                    if args.compassshuffle[p] in ['none', 0]:
                        args.compassshuffle[p] = 'wild'

                args.shufflebosses[p] = get_setting(settings['boss_shuffle'], get_setting(settings['shufflebosses'], args.shufflebosses[p]))
                args.shuffleenemies[p] = get_setting(settings['enemy_shuffle'], get_setting(settings['shuffleenemies'], args.shuffleenemies[p]))
                args.enemy_health[p] = get_setting(settings['enemy_health'], args.enemy_health[p])
                args.enemy_damage[p] = get_setting(settings['enemy_damage'], args.enemy_damage[p])
                args.any_enemy_logic[p] = get_setting(settings['any_enemy_logic'], args.any_enemy_logic[p])
                args.shufflepots[p] = get_setting(settings['shufflepots'], args.shufflepots[p])
                args.bombbag[p] = get_setting(settings['bombbag'], args.bombbag[p])
                args.shufflelinks[p] = get_setting(settings['shufflelinks'], args.shufflelinks[p])
                args.shuffletavern[p] = get_setting(settings['shuffletavern'], args.shuffletavern[p])
                args.skullwoods[p] = get_setting(settings['skullwoods'], args.skullwoods[p])
                args.linked_drops[p] = get_setting(settings['linked_drops'], args.linked_drops[p])
                args.restrict_boss_items[p] = get_setting(settings['restrict_boss_items'], args.restrict_boss_items[p])
                args.overworld_map[p] = get_setting(settings['overworld_map'], args.overworld_map[p])
                args.pseudoboots[p] = get_setting(settings['pseudoboots'], args.pseudoboots[p])
                args.mirrorscroll[p] = get_setting(settings['mirrorscroll'], args.mirrorscroll[p])
                args.triforce_goal[p] = get_setting(settings['triforce_goal'], args.triforce_goal[p])
                args.triforce_pool[p] = get_setting(settings['triforce_pool'], args.triforce_pool[p])
                args.triforce_goal_min[p] = get_setting(settings['triforce_goal_min'], args.triforce_goal_min[p])
                args.triforce_goal_max[p] = get_setting(settings['triforce_goal_max'], args.triforce_goal_max[p])
                args.triforce_pool_min[p] = get_setting(settings['triforce_pool_min'], args.triforce_pool_min[p])
                args.triforce_pool_max[p] = get_setting(settings['triforce_pool_max'], args.triforce_pool_max[p])
                args.triforce_min_difference[p] = get_setting(settings['triforce_min_difference'], args.triforce_min_difference[p])
                args.triforce_max_difference[p] = get_setting(settings['triforce_max_difference'], args.triforce_max_difference[p])
                args.beemizer[p] = get_setting(settings['beemizer'], args.beemizer[p])
                args.aga_randomness[p] = get_setting(settings['aga_randomness'], args.aga_randomness[p])
                args.money_balance[p] = get_setting(settings['money_balance'], args.money_balance[p])

                # mystery usage
                args.usestartinventory[p] = get_setting(settings['usestartinventory'], args.usestartinventory[p])
                args.startinventory[p] = get_setting(settings['startinventory'], args.startinventory[p])

                # rom adjust stuff
                args.sprite[p] = get_setting(settings['sprite'], args.sprite[p])
                args.triforce_gfx[p] = get_setting(settings['triforce_gfx'], args.triforce_gfx[p])
                args.disablemusic[p] = get_setting(settings['disablemusic'], args.disablemusic[p])
                args.quickswap[p] = get_setting(settings['quickswap'], args.quickswap[p])
                args.reduce_flashing[p] = get_setting(settings['reduce_flashing'], args.reduce_flashing[p])
                args.fastmenu[p] = get_setting(settings['fastmenu'], args.fastmenu[p])
                args.heartcolor[p] = get_setting(settings['heartcolor'], args.heartcolor[p])
                args.heartbeep[p] = get_setting(settings['heartbeep'], args.heartbeep[p])
                args.ow_palettes[p] = get_setting(settings['ow_palettes'], args.ow_palettes[p])
                args.uw_palettes[p] = get_setting(settings['uw_palettes'], args.uw_palettes[p])
                args.shuffle_sfx[p] = get_setting(settings['shuffle_sfx'], args.shuffle_sfx[p])
                args.shuffle_sfxinstruments[p] = get_setting(settings['shuffle_sfxinstruments'], args.shuffle_sfxinstruments[p])
                args.shuffle_songinstruments[p] = get_setting(settings['shuffle_songinstruments'], args.shuffle_songinstruments[p])
                args.msu_resume[p] = get_setting(settings['msu_resume'], args.msu_resume[p])

    def has_setting(self, player, setting):
        if 'settings' in self.file_source and player in self.file_source['settings']:
            return setting in self.file_source['settings'][player]
        return False

    def get_setting(self, player, setting):
        return self.file_source['settings'][player][setting]

    def get_item_pool(self):
        if 'item_pool' in self.file_source:
            return self.file_source['item_pool']
        return None

    def get_placements(self):
        if 'placements' in self.file_source:
            return self.file_source['placements']
        return None

    def get_prices(self, player):
        return self.get_attribute_by_player_composite('prices', player)

    def get_advanced_placements(self):
        if 'advanced_placements' in self.file_source:
            return self.file_source['advanced_placements']
        return None

    def get_owedges(self):
        if 'ow-edges' in self.file_source:
            return self.file_source['ow-edges']
        return None

    def get_owgrid(self):
        if 'ow-grid' in self.file_source:
            return self.file_source['ow-grid']
        return None

    def get_owcrossed(self):
        if 'ow-crossed' in self.file_source:
            return self.file_source['ow-crossed']
        return None

    def get_whirlpools(self):
        if 'ow-whirlpools' in self.file_source:
            return self.file_source['ow-whirlpools']
        return None

    def get_owtileflips(self):
        if 'ow-tileflips' in self.file_source:
            return self.file_source['ow-tileflips']
        return None

    def get_owflutespots(self):
        if 'ow-flutespots' in self.file_source:
            return self.file_source['ow-flutespots']
        return None

    def get_entrances(self):
        if 'entrances' in self.file_source:
            return self.file_source['entrances']
        return None

    def get_doors(self):
        if 'doors' in self.file_source:
            return self.file_source['doors']
        return None

    def get_bosses(self):
        if 'bosses' in self.file_source:
            return self.file_source['bosses']
        return None

    def get_start_inventory(self):
        if 'start_inventory' in self.file_source:
            return self.file_source['start_inventory']
        return None

    def get_medallions(self):
        if 'medallions' in self.file_source:
            return self.file_source['medallions']
        return None

    def get_drops(self):
        if 'drops' in self.file_source:
            return self.file_source['drops']
        return None

    def get_enemies(self):
        if 'enemies' in self.file_source:
            return self.file_source['enemies']
        return None
    
    def get_goals(self):
        if 'goals' in self.file_source:
            return self.file_source['goals']
        return None


    def get_attribute_by_player_composite(self, attribute, player):
        attempt = self.get_attribute_by_player_new(attribute, player)
        if attempt is not None:
            return attempt
        attempt = self.get_attribute_by_player(attribute, player)
        return attempt

    def get_attribute_by_player(self, attribute, player):
        if attribute in self.file_source:
            if player in self.file_source[attribute]:
                return self.file_source[attribute][player]
        return None

    def get_attribute_by_player_new(self, attribute, player):
        player_id = self.get_player_id(player)
        if player_id is not None:
            if attribute in self.file_source[player_id]:
                return self.file_source[player_id][attribute]
        return None

    def get_player_id(self, player):
        if player in self.file_source:
            return player
        if player in self.player_map and self.player_map[player] in self.file_source:
            return self.player_map[player]
        return None

    def create_from_world(self, world, settings):
        self.player_range = range(1, world.players + 1)
        settings_dict, meta_dict = {}, {}
        self.world_rep['meta'] = meta_dict
        if world.seed:
            meta_dict['seed'] = world.seed
        meta_dict['players'] = world.players
        meta_dict['algorithm'] = world.algorithm
        meta_dict['race'] = settings.race
        meta_dict['user_notes'] = settings.notes
        self.world_rep['settings'] = settings_dict
        if world.precollected_items:
            self.world_rep['start_inventory'] = start_inv = {}
        for p in self.player_range:
            settings_dict[p] = {}
            settings_dict[p]['ow_layout'] = world.owLayout[p]
            settings_dict[p]['ow_parallel'] = world.owParallel[p]
            settings_dict[p]['ow_terrain'] = world.owTerrain[p]
            settings_dict[p]['ow_crossed'] = world.owCrossed[p]
            settings_dict[p]['ow_keepsimilar'] = world.owKeepSimilar[p]
            settings_dict[p]['ow_mixed'] = world.owMixed[p]
            settings_dict[p]['ow_whirlpool'] = world.owWhirlpoolShuffle[p]
            settings_dict[p]['ow_fluteshuffle'] = world.owFluteShuffle[p]
            settings_dict[p]['ow_fog'] = world.owFog[p]
            settings_dict[p]['shuffle_followers'] = world.shuffle_followers[p]
            settings_dict[p]['bonk_drops'] = world.shuffle_bonk_drops[p]
            settings_dict[p]['shuffle'] = world.shuffle[p]
            settings_dict[p]['door_shuffle'] = world.doorShuffle[p]
            settings_dict[p]['intensity'] = world.intensity[p]
            settings_dict[p]['door_type_mode'] = world.door_type_mode[p]
            settings_dict[p]['trap_door_mode'] = world.trap_door_mode[p]
            settings_dict[p]['key_logic_algorithm'] = world.key_logic_algorithm[p]
            settings_dict[p]['decoupledoors'] = world.decoupledoors[p]
            settings_dict[p]['door_self_loops'] = world.door_self_loops[p]
            settings_dict[p]['logic'] = world.logic[p]
            settings_dict[p]['mode'] = world.mode[p]
            settings_dict[p]['swords'] = world.swords[p]
            settings_dict[p]['flute_mode'] = world.flute_mode[p]
            settings_dict[p]['bow_mode'] = world.bow_mode[p]
            settings_dict[p]['difficulty'] = world.difficulty[p]
            settings_dict[p]['goal'] = world.goal[p]
            settings_dict[p]['accessibility'] = world.accessibility[p]
            settings_dict[p]['item_functionality'] = world.difficulty_adjustments[p]
            settings_dict[p]['take_any'] = world.take_any[p]
            settings_dict[p]['hints'] = world.hints[p]
            settings_dict[p]['shopsanity'] = world.shopsanity[p]
            settings_dict[p]['dropshuffle'] = world.dropshuffle[p]
            settings_dict[p]['pottery'] = world.pottery[p]
            settings_dict[p]['mixed_travel'] = world.mixed_travel[p]
            settings_dict[p]['standardize_palettes'] = world.standardize_palettes[p]
            settings_dict[p]['dungeon_counters'] = world.dungeon_counters[p]
            settings_dict[p]['crystals_gt'] = world.crystals_gt_orig[p]
            settings_dict[p]['crystals_ganon'] = world.crystals_ganon_orig[p]
            settings_dict[p]['experimental'] = world.experimental[p]
            settings_dict[p]['collection_rate'] = world.collection_rate[p]
            settings_dict[p]['openpyramid'] = world.open_pyramid[p]
            settings_dict[p]['prizeshuffle'] = world.prizeshuffle[p]
            settings_dict[p]['bigkeyshuffle'] = world.bigkeyshuffle[p]
            settings_dict[p]['keyshuffle'] = world.keyshuffle[p]
            settings_dict[p]['mapshuffle'] = world.mapshuffle[p]
            settings_dict[p]['compassshuffle'] = world.compassshuffle[p]
            settings_dict[p]['boss_shuffle'] = world.boss_shuffle[p]
            settings_dict[p]['enemy_shuffle'] = world.enemy_shuffle[p]
            settings_dict[p]['enemy_health'] = world.enemy_health[p]
            settings_dict[p]['enemy_damage'] = world.enemy_damage[p]
            settings_dict[p]['any_enemy_logic'] = world.any_enemy_logic[p]
            settings_dict[p]['shufflepots'] = world.potshuffle[p]
            settings_dict[p]['bombbag'] = world.bombbag[p]
            settings_dict[p]['shufflelinks'] = world.shufflelinks[p]
            settings_dict[p]['shuffletavern'] = world.shuffletavern[p]
            settings_dict[p]['skullwoods'] = world.skullwoods[p]
            settings_dict[p]['linked_drops'] = world.linked_drops[p]
            settings_dict[p]['overworld_map'] = world.overworld_map[p]
            settings_dict[p]['pseudoboots'] = world.pseudoboots[p]
            settings_dict[p]['mirrorscroll'] = world.mirrorscroll[p]
            settings_dict[p]['triforce_goal'] = world.treasure_hunt_count[p]
            settings_dict[p]['triforce_pool'] = world.treasure_hunt_total[p]
            settings_dict[p]['beemizer'] = world.beemizer[p]
            settings_dict[p]['aga_randomness'] = world.aga_randomness[p]
            settings_dict[p]['money_balance'] = world.money_balance[p]
            if world.precollected_items:
                start_inv[p] = []
        for item in world.precollected_items:
            start_inv[item.player].append(item.name)

            # rom adjust stuff
            # settings_dict[p]['sprite'] = world.sprite[p]
            # settings_dict[p]['disablemusic'] = world.disablemusic[p]
            # settings_dict[p]['quickswap'] = world.quickswap[p]
            # settings_dict[p]['reduce_flashing'] = world.reduce_flashing[p]
            # settings_dict[p]['fastmenu'] = world.fastmenu[p]
            # settings_dict[p]['heartcolor'] = world.heartcolor[p]
            # settings_dict[p]['heartbeep'] = world.heartbeep[p]
            # settings_dict[p]['ow_palettes'] = world.ow_palettes[p]
            # settings_dict[p]['uw_palettes'] = world.uw_palettes[p]
            # settings_dict[p]['shuffle_sfx'] = world.shuffle_sfx[p]
            # settings_dict[p]['shuffle_songinstruments'] = world.shuffle_songinstruments[p]
            # more settings?

    def record_info(self, world):
        self.world_rep['meta']['seed'] = world.seed
        self.world_rep['bosses'] = bosses = {}
        self.world_rep['medallions'] = medallions = {}
        for p in self.player_range:
            bosses[p] = {}
            medallions[p] = {}
        for dungeon in world.dungeons:
            for level, boss in dungeon.bosses.items():
                location = dungeon.name if level is None else f'{dungeon.name} ({level})'
                if boss and 'Agahnim' not in boss.name:
                    bosses[dungeon.player][location] = boss.name
        for p, req_medals in world.required_medallions.items():
            medallions[p]['Misery Mire'] = req_medals[0]
            medallions[p]['Turtle Rock'] = req_medals[1]

    def record_item_pool(self, world, use_custom_pool=False):
        if not use_custom_pool or world.custom:
            self.world_rep['item_pool'] = item_pool = {}
            for p in self.player_range:
                if not use_custom_pool or p in world.customitemarray:
                    item_pool[p] = defaultdict(int)
        if use_custom_pool and world.custom:
            import source.classes.constants as CONST
            for p in world.customitemarray:
                for i, c in world.customitemarray[p].items():
                    if c > 0:
                        item = CONST.CUSTOMITEMLABELS[CONST.CUSTOMITEMS.index(i)]
                        item_pool[p][item] += c
        else:
            for item in world.itempool:
                item_pool[item.player][item.name] += 1

    def record_item_placements(self, world):
        self.world_rep['placements'] = placements = {}
        for p in self.player_range:
            placements[p] = {}
        for location in world.get_locations():
            if location.type != LocationType.Logical:
                if location.player != location.item.player:
                    placements[location.player][location.name] = f'{location.item.name}#{location.item.player}'
                else:
                    placements[location.player][location.name] = location.item.name

    def record_overworld(self, world):
        self.world_rep['ow-edges'] = edges = {}
        self.world_rep['ow-whirlpools'] = whirlpools = {}
        self.world_rep['ow-tileflips'] = flips = {}
        self.world_rep['ow-flutespots'] = flute = {}
        for p in self.player_range:
            connections = edges[p] = {}
            connections['two-way'] = {}
            connections['one-way'] = {}
            whirlconnects = whirlpools[p] = {}
            whirlconnects['two-way'] = {}
            whirlconnects['one-way'] = {}
            # tile flips
            if p in world.owswaps and len(world.owswaps[p][0]) > 0:
                flips[p] = {}
                flips[p]['force_flip'] = list(HexInt(f) for f in world.owswaps[p][0] if f & 0x40 == 0)
                flips[p]['force_flip'].sort()
                flips[p]['undefined_chance'] = 0
            # flute spots
            flute[p] = {}
            if p in world.owflutespots:
                flute[p]['force'] = list(HexInt(id) for id in sorted(world.owflutespots[p]))
            else:
                flute[p]['force'] = list(HexInt(id) for id in sorted(default_flute_connections))
            flute[p]['forbid'] = []
        for key, data in world.spoiler.overworlds.items():
            player = data['player'] if 'player' in data else 1
            connections = edges[player]
            sub = 'two-way' if data['direction'] == 'both' else 'one-way'
            connections[sub][data['entrance']] = data['exit']
        for key, data in world.spoiler.whirlpools.items():
            player = data['player'] if 'player' in data else 1
            whirlconnects = whirlconnects[player]
            sub = 'two-way' if data['direction'] == 'both' else 'one-way'
            whirlconnects[sub][data['entrance']] = data['exit']

    def record_entrances(self, world):
        self.world_rep['entrances'] = entrances = {}
        world.custom_entrances = {}
        for p in self.player_range:
            connections = entrances[p] = {}
            connections['entrances'] = {}
            connections['exits'] = {}
            connections['two-way'] = {}
        for key, data in world.spoiler.entrances.items():
            player = data['player'] if 'player' in data else 1
            connections = entrances[player]
            sub = 'two-way' if data['direction'] == 'both' else 'exits' if data['direction'] == 'exit' else 'entrances'
            connections[sub][data['entrance']] = data['exit']

    def record_doors(self, world):
        self.world_rep['doors'] = doors = {}
        for p in self.player_range:
            meta_doors = doors[p] = {}
            lobbies = meta_doors['lobbies'] = {}
            door_map = meta_doors['doors'] = {}
            for portal in world.dungeon_portals[p]:
                lobbies[portal.name] = portal.door.name
            door_types = {DoorType.Normal, DoorType.SpiralStairs, DoorType.Interior}
            if world.intensity[p] > 1:
                door_types.update([DoorType.Open, DoorType.StraightStairs, DoorType.Ladder])
            door_kinds, skip = {}, set()
            for key, info in world.spoiler.doorTypes.items():
                if key[1] == p:
                    if ' <-> ' in info['doorNames']:
                        dns = info['doorNames'].split(' <-> ')
                        for dn in dns:
                            door_kinds[dn] = info['type']  # Key Door, Bomb Door, Dash Door
                    else:
                        door_kinds[info['doorNames']] = info['type']
            for door in world.doors:
                if door.player == p and not door.entranceFlag and door.type in door_types and door not in skip:
                    if door.type == DoorType.Interior:
                        if door.name in door_kinds:
                            door_value = {'type':  door_kinds[door.name]}
                            door_map[door.name] = door_value  # intra-tile note
                            skip.add(door.dest)
                    elif door.dest:
                        if door.dest.dest == door:
                            door_value = door.dest.name
                            skip.add(door.dest)
                            if door.name in door_kinds:
                                door_value = {'dest': door_value, 'type': door_kinds[door.name]}
                            if door.name not in door_kinds and door.dest.name in door_kinds:
                                # tricky swap thing
                                door_value = {'dest': door.name, 'type': door_kinds[door.dest.name]}
                                door = door.dest  # this is weird
                        elif door.name in door_kinds:
                            door_value = {'dest': door.dest.name, 'one-way': True, 'type':  door_kinds[door.name]}
                        else:
                            door_value = {'dest': door.dest.name, 'one-way': True}
                        door_map[door.name] = door_value

    def record_medallions(self):
        pass

    def write_to_file(self, destination):
        yaml.add_representer(defaultdict, Representer.represent_dict)
        yaml.add_representer(HexInt, hex_representer)
        with open(destination, 'w') as file:
            yaml.dump(self.world_rep, file)


def load_yaml(path):
    try:
        if os.path.exists(Path(path)):
            with open(path, "r", encoding="utf-8") as f:
                return yaml.load(f, Loader=yaml.SafeLoader)
        elif urllib.parse.urlparse(path).scheme in ['http', 'https']:
            return yaml.load(urllib.request.urlopen(path), Loader=yaml.FullLoader)
    except yaml.YAMLError as e:
        error_msg = f"Error parsing YAML file '{path}':\n{str(e)}"
        raise ValueError(error_msg) from e

