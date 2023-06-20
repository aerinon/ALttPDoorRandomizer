import os
import urllib.request
import urllib.parse
import yaml
from typing import Any
from yaml.representer import Representer
from collections import defaultdict
from pathlib import Path

import RaceRandom as random
from BaseClasses import LocationType, DoorType
from source.tools.MysteryUtils import roll_settings, get_weights


class CustomSettings(object):

    def __init__(self):
        self.file_source = None
        self.relative_dir = None
        self.world_rep = {}
        self.player_range = None

    def load_yaml(self, file):
        self.file_source = load_yaml(file)
        head, filename = os.path.split(file)
        self.relative_dir = head

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

    def adjust_args(self, args):
        def get_setting(value: Any, default):
            if value or value == 0:
                if isinstance(value, dict):
                    return random.choices(list(value.keys()), list(value.values()), k=1)[0]
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
            args.names = get_setting(meta['names'], args.names)
            args.race = get_setting(meta['race'], args.race)
            args.seed_notes = get_setting(meta['seed_notes'], args.seed_notes)
            args.seed_name = get_setting(meta['seed_name'], args.seed_name)
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
                    args.dropshuffle[p] = True
                    if args.pottery[p] == 'none':
                        args.pottery[p] = 'keys'

                if args.retro[p] or args.mode[p] == 'retro':
                    if args.bow_mode[p] == 'progressive':
                        args.bow_mode[p] = 'retro'
                    elif args.bow_mode[p] == 'silvers':
                        args.bow_mode[p] = 'retro_silvers'
                    args.take_any[p] = 'random' if args.take_any[p] == 'none' else args.take_any[p]
                    args.keyshuffle[p] = 'universal'

                args.mixed_travel[p] = get_setting(settings['mixed_travel'], args.mixed_travel[p])
                args.standardize_palettes[p] = get_setting(settings['standardize_palettes'],
                                                           args.standardize_palettes[p])
                args.intensity[p] = get_setting(settings['intensity'], args.intensity[p])
                args.door_type_mode[p] = get_setting(settings['door_type_mode'], args.door_type_mode[p])
                args.trap_door_mode[p] = get_setting(settings['trap_door_mode'], args.trap_door_mode[p])
                args.key_logic_algorithm[p] = get_setting(settings['key_logic_algorithm'], args.key_logic_algorithm[p])
                args.decoupledoors[p] = get_setting(settings['decoupledoors'], args.decoupledoors[p])
                args.dungeon_counters[p] = get_setting(settings['dungeon_counters'], args.dungeon_counters[p])
                args.crystals_gt[p] = get_setting(settings['crystals_gt'], args.crystals_gt[p])
                args.crystals_ganon[p] = get_setting(settings['crystals_ganon'], args.crystals_ganon[p])
                args.experimental[p] = get_setting(settings['experimental'], args.experimental[p])
                args.collection_rate[p] = get_setting(settings['collection_rate'], args.collection_rate[p])
                args.openpyramid[p] = get_setting(settings['openpyramid'], args.openpyramid[p])
                args.bigkeyshuffle[p] = get_setting(settings['bigkeyshuffle'], args.bigkeyshuffle[p])
                args.keyshuffle[p] = get_setting(settings['keyshuffle'], args.keyshuffle[p])
                args.mapshuffle[p] = get_setting(settings['mapshuffle'], args.mapshuffle[p])
                args.compassshuffle[p] = get_setting(settings['compassshuffle'], args.compassshuffle[p])

                if get_setting(settings['keysanity'], args.keysanity):
                    args.bigkeyshuffle[p] = True
                    if args.keyshuffle[p] == 'none':
                        args.keyshuffle[p] = 'wild'
                    args.mapshuffle[p] = True
                    args.compassshuffle[p] = True

                args.shufflebosses[p] = get_setting(settings['boss_shuffle'], args.shufflebosses[p])
                args.shuffleenemies[p] = get_setting(settings['enemy_shuffle'], args.shuffleenemies[p])
                args.enemy_health[p] = get_setting(settings['enemy_health'], args.enemy_health[p])
                args.enemy_damage[p] = get_setting(settings['enemy_damage'], args.enemy_damage[p])
                args.shufflepots[p] = get_setting(settings['shufflepots'], args.shufflepots[p])
                args.bombbag[p] = get_setting(settings['bombbag'], args.bombbag[p])
                args.shufflelinks[p] = get_setting(settings['shufflelinks'], args.shufflelinks[p])
                args.shuffletavern[p] = get_setting(settings['shuffletavern'], args.shuffletavern[p])
                args.restrict_boss_items[p] = get_setting(settings['restrict_boss_items'], args.restrict_boss_items[p])
                args.overworld_map[p] = get_setting(settings['overworld_map'], args.overworld_map[p])
                args.pseudoboots[p] = get_setting(settings['pseudoboots'], args.pseudoboots[p])
                args.triforce_goal[p] = get_setting(settings['triforce_goal'], args.triforce_goal[p])
                args.triforce_pool[p] = get_setting(settings['triforce_pool'], args.triforce_pool[p])
                args.beemizer[p] = get_setting(settings['beemizer'], args.beemizer[p])

                # mystery usage
                args.usestartinventory[p] = get_setting(settings['usestartinventory'], args.usestartinventory[p])
                args.startinventory[p] = get_setting(settings['startinventory'], args.startinventory[p])

                # rom adjust stuff
                args.sprite[p] = get_setting(settings['sprite'], args.sprite[p])
                args.disablemusic[p] = get_setting(settings['disablemusic'], args.disablemusic[p])
                args.quickswap[p] = get_setting(settings['quickswap'], args.quickswap[p])
                args.reduce_flashing[p] = get_setting(settings['reduce_flashing'], args.reduce_flashing[p])
                args.fastmenu[p] = get_setting(settings['fastmenu'], args.fastmenu[p])
                args.heartcolor[p] = get_setting(settings['heartcolor'], args.heartcolor[p])
                args.heartbeep[p] = get_setting(settings['heartbeep'], args.heartbeep[p])
                args.ow_palettes[p] = get_setting(settings['ow_palettes'], args.ow_palettes[p])
                args.uw_palettes[p] = get_setting(settings['uw_palettes'], args.uw_palettes[p])
                args.shuffle_sfx[p] = get_setting(settings['shuffle_sfx'], args.shuffle_sfx[p])
                args.msu_resume[p] = get_setting(settings['msu_resume'], args.msu_resume[p])

    def get_item_pool(self):
        if 'item_pool' in self.file_source:
            return self.file_source['item_pool']
        return None

    def get_placements(self):
        if 'placements' in self.file_source:
            return self.file_source['placements']
        return None

    def get_advanced_placements(self):
        if 'advanced_placements' in self.file_source:
            return self.file_source['advanced_placements']
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

    def create_from_world(self, world, race, seed_notes, seed_name):
        self.player_range = range(1, world.players + 1)
        settings_dict, meta_dict = {}, {}
        self.world_rep['meta'] = meta_dict
        meta_dict['players'] = world.players
        meta_dict['algorithm'] = world.algorithm
        meta_dict['seed'] = world.seed
        meta_dict['race'] = race
        meta_dict['seed_notes'] = world.seed_notes
        meta_dict['seed_name'] = world.seed_name
        self.world_rep['settings'] = settings_dict
        for p in self.player_range:
            settings_dict[p] = {}
            settings_dict[p]['shuffle'] = world.shuffle[p]
            settings_dict[p]['door_shuffle'] = world.doorShuffle[p]
            settings_dict[p]['intensity'] = world.intensity[p]
            settings_dict[p]['door_type_mode'] = world.door_type_mode[p]
            settings_dict[p]['trap_door_mode'] = world.trap_door_mode[p]
            settings_dict[p]['key_logic_algorithm'] = world.key_logic_algorithm[p]
            settings_dict[p]['decoupledoors'] = world.decoupledoors[p]
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
            settings_dict[p]['bigkeyshuffle'] = world.bigkeyshuffle[p]
            settings_dict[p]['keyshuffle'] = world.keyshuffle[p]
            settings_dict[p]['mapshuffle'] = world.mapshuffle[p]
            settings_dict[p]['compassshuffle'] = world.compassshuffle[p]
            settings_dict[p]['shufflebosses'] = world.boss_shuffle[p]
            settings_dict[p]['shuffleenemies'] = world.enemy_shuffle[p]
            settings_dict[p]['enemy_health'] = world.enemy_health[p]
            settings_dict[p]['enemy_damage'] = world.enemy_damage[p]
            settings_dict[p]['shufflepots'] = world.potshuffle[p]
            settings_dict[p]['bombbag'] = world.bombbag[p]
            settings_dict[p]['shufflelinks'] = world.shufflelinks[p]
            settings_dict[p]['shuffletavern'] = world.shuffletavern[p]
            settings_dict[p]['overworld_map'] = world.overworld_map[p]
            settings_dict[p]['pseudoboots'] = world.pseudoboots[p]
            settings_dict[p]['triforce_goal'] = world.treasure_hunt_count[p]
            settings_dict[p]['triforce_pool'] = world.treasure_hunt_total[p]
            settings_dict[p]['beemizer'] = world.beemizer[p]

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
            # more settings?

    def record_info(self, world):
        self.world_rep['bosses'] = bosses = {}
        self.world_rep['start_inventory'] = start_inv = {}
        for p in self.player_range:
            bosses[p] = {}
            start_inv[p] = []
        for dungeon in world.dungeons:
            for level, boss in dungeon.bosses.items():
                location = dungeon.name if level is None else f'{dungeon.name} ({level})'
                if boss and 'Agahnim' not in boss.name:
                    bosses[dungeon.player][location] = boss.name
        for item in world.precollected_items:
            start_inv[item.player].append(item.name)

    def record_item_pool(self, world):
        self.world_rep['item_pool'] = item_pool = {}
        self.world_rep['medallions'] = medallions = {}
        for p in self.player_range:
            item_pool[p] = defaultdict(int)
            medallions[p] = {}
        for item in world.itempool:
            item_pool[item.player][item.name] += 1
        for p, req_medals in world.required_medallions.items():
            medallions[p]['Misery Mire'] = req_medals[0]
            medallions[p]['Turtle Rock'] = req_medals[1]

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
        with open(destination, 'w') as file:
            yaml.dump(self.world_rep, file)


def load_yaml(path):
    if os.path.exists(Path(path)):
        with open(path, "r", encoding="utf-8") as f:
            return yaml.load(f, Loader=yaml.SafeLoader)
    elif urllib.parse.urlparse(path).scheme in ['http', 'https']:
        return yaml.load(urllib.request.urlopen(path), Loader=yaml.FullLoader)

