import argparse
import RaceRandom as random
import os
from pathlib import Path

import urllib.request
import urllib.parse
import yaml


def get_weights(path):
    if os.path.exists(Path(path)):
        with open(path, "r", encoding="utf-8") as f:
            return yaml.load(f, Loader=yaml.SafeLoader)
    elif urllib.parse.urlparse(path).scheme in ['http', 'https']:
        return yaml.load(urllib.request.urlopen(path), Loader=yaml.FullLoader)


def roll_settings(weights):
    def get_choice(option, root=None):
        root = weights if root is None else root
        if option not in root:
            return None
        if type(root[option]) is not dict:
            return root[option]
        if not root[option]:
            return None
        return random.choices(list(root[option].keys()), weights=list(map(int, root[option].values())))[0]

    def get_choice_default(option, root=weights, default=None):
        choice = get_choice(option, root)
        if choice is None and default is not None:
            return default
        return choice

    def get_choice_bool(option, root=weights):
        choice = get_choice(option, root)
        if choice is True or choice == 'on':
            return True
        if choice is False or choice == 'off':
            return False
        if choice is None:
            return choice
        raise Exception("This fields needs to be true/false or off/on")

    def get_choice_non_bool(option, root=weights):
        choice = get_choice(option, root)
        if choice is True or choice == 'on':
            return 'on'
        if choice is False or choice == 'off':
            return 'off'
        return choice

    def get_choice_yn(option, root=weights):
        choice = get_choice(option, root)
        if choice is True or choice == 'yes':
            return 'yes'
        if choice is False or choice == 'no':
            return 'no'
        return choice


    def get_choice_bool_default(option, root=weights, default=None):
        choice = get_choice_bool(option, root)
        if choice is None and default is not None:
            return default
        return choice

    while True:
        subweights = weights.get('subweights', {})
        if len(subweights) == 0:
            break
        chances = ({k: int(v['chance']) for (k, v) in subweights.items()})
        subweight_name = random.choices(list(chances.keys()), weights=list(chances.values()))[0]
        subweights = weights.get('subweights', {}).get(subweight_name, {}).get('weights', {})
        subweights['subweights'] = subweights.get('subweights', {})
        weights = {**weights, **subweights}

    ret = argparse.Namespace()

    ret.algorithm = get_choice('algorithm')

    glitch_map = {'none': 'noglitches', 'no_logic': 'nologic', 'hybridglitches': 'hybridglitches',
                  'hmg': 'hybridglitches', 'owglitches': 'owglitches',
                  'owg': 'owglitches', 'minorglitches': 'minorglitches'}
    glitches_required = get_choice('glitches_required')
    if glitches_required is not None:
        if glitches_required not in glitch_map.keys():
            print(f'Logic did not match one of: {", ".join(glitch_map.keys())}')
            glitches_required = 'none'
        ret.logic = glitch_map[glitches_required]

    # item_placement = get_choice('item_placement')
    # not supported in ER

    dungeon_items = get_choice('dungeon_items')
    dungeon_items = '' if dungeon_items == 'standard' or dungeon_items is None else dungeon_items
    dungeon_items = 'mcsb' if dungeon_items == 'full' else dungeon_items
    ret.mapshuffle = get_choice_bool('map_shuffle') if 'map_shuffle' in weights else 'm' in dungeon_items
    ret.compassshuffle = get_choice_bool('compass_shuffle') if 'compass_shuffle' in weights else 'c' in dungeon_items
    if 'smallkey_shuffle' in weights:
        ret.keyshuffle = get_choice('smallkey_shuffle')
    else:
        if 's' in dungeon_items:
            ret.keyshuffle = 'wild'
        if 'u' in dungeon_items:
            ret.keyshuffle = 'universal'
    ret.bigkeyshuffle = get_choice_bool('bigkey_shuffle') if 'bigkey_shuffle' in weights else 'b' in dungeon_items

    ret.accessibility = get_choice('accessibility')
    ret.restrict_boss_items = get_choice('restrict_boss_items')

    entrance_shuffle = get_choice('entrance_shuffle')
    ret.shuffle = entrance_shuffle if entrance_shuffle != 'none' else 'vanilla'
    overworld_map = get_choice('overworld_map')
    ret.overworld_map = overworld_map if overworld_map != 'default' else 'default'
    door_shuffle = get_choice('door_shuffle')
    ret.door_shuffle = door_shuffle if door_shuffle != 'none' else 'vanilla'
    ret.intensity = get_choice('intensity')
    ret.door_type_mode = get_choice('door_type_mode')
    ret.trap_door_mode = get_choice('trap_door_mode')
    ret.key_logic_algorithm = get_choice('key_logic_algorithm')
    ret.decoupledoors = get_choice_bool('decoupledoors')
    ret.door_self_loops = get_choice_bool('door_self_loops')
    ret.experimental = get_choice_bool('experimental')
    ret.collection_rate = get_choice_bool('collection_rate')

    ret.dungeon_counters = get_choice_non_bool('dungeon_counters') if 'dungeon_counters' in weights else 'default'
    if ret.dungeon_counters == 'default':
        ret.dungeon_counters = 'pickup' if ret.door_shuffle != 'vanilla' or ret.compassshuffle == 'on' else 'off'

    ret.shufflelinks = get_choice_bool('shufflelinks')
    ret.shuffletavern = get_choice_bool('shuffletavern')
    ret.pseudoboots = get_choice_bool('pseudoboots')
    ret.shopsanity = get_choice_bool('shopsanity')
    keydropshuffle = get_choice_bool('keydropshuffle')
    ret.dropshuffle = get_choice('dropshuffle') if 'dropshuffle' in weights else 'none'
    ret.dropshuffle = 'keys' if ret.dropshuffle == 'none' and keydropshuffle else ret.dropshuffle
    ret.pottery = get_choice('pottery') if 'pottery' in weights else 'none'
    ret.pottery = 'keys' if ret.pottery == 'none' and keydropshuffle else ret.pottery
    ret.colorizepots = get_choice_bool_default('colorizepots', default=True)
    ret.shufflepots = get_choice_bool('pot_shuffle')
    ret.aga_randomness = get_choice_bool('aga_randomness')
    ret.mixed_travel = get_choice('mixed_travel') if 'mixed_travel' in weights else 'prevent'
    ret.standardize_palettes = (get_choice('standardize_palettes') if 'standardize_palettes' in weights
                                else 'standardize')

    goal = get_choice_default('goals', default='ganon')
    if goal is not None:
        ret.goal = {'ganon': 'ganon',
                    'fast_ganon': 'crystals',
                    'dungeons': 'dungeons',
                    'pedestal': 'pedestal',
                    'triforce-hunt': 'triforcehunt',
                    'trinity': 'trinity',
                    'ganonhunt': 'ganonhunt',
                    'completionist': 'completionist'
                    }[goal]
    ret.openpyramid = get_choice_yn('open_pyramid') if 'open_pyramid' in weights else 'auto'

    ret.crystals_gt = get_choice('tower_open')

    ret.crystals_ganon = get_choice('ganon_open')

    ret.triforce_pool = get_choice_default('triforce_pool', default=0)
    ret.triforce_goal = get_choice_default('triforce_goal', default=0)
    ret.triforce_pool_min = get_choice_default('triforce_pool_min', default=0)
    ret.triforce_pool_max = get_choice_default('triforce_pool_max', default=0)
    ret.triforce_goal_min = get_choice_default('triforce_goal_min', default=0)
    ret.triforce_goal_max = get_choice_default('triforce_goal_max', default=0)
    ret.triforce_min_difference = get_choice_default('triforce_min_difference', default=0)
    ret.triforce_max_difference = get_choice_default('triforce_max_difference', default=10000)

    ret.mode = get_choice('world_state')
    if ret.mode == 'retro':
        ret.mode = 'open'
        ret.retro = True
    ret.retro = get_choice_bool('retro')  # this overrides world_state if used
    ret.take_any = get_choice_default('take_any', default='none')

    ret.bombbag = get_choice_bool('bombbag')

    ret.hints = get_choice_bool('hints')

    swords = get_choice('weapons')
    if swords is not None:
        ret.swords = {'randomized': 'random',
                      'assured': 'assured',
                      'vanilla': 'vanilla',
                      'swordless': 'swordless'
                      }[swords]

    ret.difficulty = get_choice('item_pool')
    ret.flute_mode = get_choice_default('flute_mode', default='normal')
    ret.bow_mode = get_choice_default('bow_mode', default='progressive')

    ret.item_functionality = get_choice('item_functionality')

    old_style_bosses = {'basic': 'simple',
                        'normal': 'full',
                        'chaos': 'random'}
    boss_choice = get_choice('boss_shuffle')
    if boss_choice in old_style_bosses.keys():
        boss_choice = old_style_bosses[boss_choice]
    ret.shufflebosses = boss_choice

    enemy_choice = get_choice('enemy_shuffle')
    if enemy_choice == 'chaos':
        enemy_choice = 'random'
    ret.shuffleenemies = enemy_choice

    old_style_damage = {'none': 'default',
                        'chaos': 'random'}
    damage_choice = get_choice('enemy_damage')
    if damage_choice in old_style_damage:
        damage_choice = old_style_damage[damage_choice]
    ret.enemy_damage = damage_choice

    ret.enemy_health = get_choice('enemy_health')
    ret.any_enemy_logic = get_choice('any_enemy_logic')

    ret.beemizer = get_choice('beemizer') if 'beemizer' in weights else '0'

    inventoryweights = weights.get('startinventory', {})
    startitems = []
    for item in inventoryweights.keys():
        if get_choice(item, inventoryweights) == 'on':
            startitems.append(item)
    ret.startinventory = ','.join(startitems)
    if len(startitems) > 0:
        ret.usestartinventory = True

    if 'rom' in weights:
        romweights = weights['rom']
        ret.sprite = get_choice('sprite', romweights)
        ret.disablemusic = get_choice_bool('disablemusic', romweights)
        ret.quickswap = get_choice_bool('quickswap', romweights)
        ret.reduce_flashing = get_choice_bool('reduce_flashing', romweights)
        ret.fastmenu = get_choice('menuspeed', romweights)
        ret.heartcolor = get_choice('heartcolor', romweights)
        ret.heartbeep = get_choice_non_bool('heartbeep', romweights)
        ret.ow_palettes = get_choice('ow_palettes', romweights)
        ret.uw_palettes = get_choice('uw_palettes', romweights)
        ret.shuffle_sfx = get_choice_bool('shuffle_sfx', romweights)
        ret.msu_resume = get_choice_bool('msu_resume', romweights)

    return ret
