import argparse
import copy
import json
import os
import textwrap
import shlex
import sys

from source.classes.BabelFish import BabelFish

from Utils import update_deprecated_args
from source.classes.CustomSettings import CustomSettings


class ArgumentDefaultsHelpFormatter(argparse.RawTextHelpFormatter):

    def _get_help_string(self, action):
        return textwrap.dedent(action.help)


def parse_cli(argv, no_defaults=False):
    def defval(value):
        return value if not no_defaults else None

    # get settings
    settings = parse_settings()

    lang = "en"
    fish = BabelFish(lang=lang)

    # we need to know how many players we have first
    # also if we're loading our own settings file, we should do that now
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--settingsfile', help="input json file of settings", type=str)
    parser.add_argument('--multi', default=defval(settings["multi"]), type=lambda value: min(max(int(value), 1), 255))
    parser.add_argument('--customizer', help='input yaml file for customizations', type=str)
    parser.add_argument('--print_custom_yaml', help='print example yaml for current settings',
                        default=False, action="store_true")
    parser.add_argument('--mystery', dest="mystery", default=False, action="store_true")

    multiargs, _ = parser.parse_known_args(argv)

    if multiargs.settingsfile:
        settings = apply_settings_file(settings, multiargs.settingsfile)

    player_num = multiargs.multi
    if multiargs.customizer:
        custom = CustomSettings()
        custom.load_yaml(multiargs.customizer)
        cp = custom.determine_players()
        if cp:
            player_num = cp


    parser = argparse.ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter)

    # get args
    args = []
    with open(os.path.join("resources", "app", "cli", "args.json")) as argsFile:
        args = json.load(argsFile)
        for arg in args:
            argdata = args[arg]
            argname = "--" + arg
            argatts = {}
            argatts["help"] = "(default: %(default)s)"
            if "action" in argdata:
                argatts["action"] = argdata["action"]
            if "choices" in argdata:
                argatts["choices"] = argdata["choices"]
                argatts["const"] = argdata["choices"][0]
                argatts["default"] = argdata["choices"][0]
                argatts["nargs"] = "?"
            if arg in settings:
                default = settings[arg]
                if "type" in argdata and argdata["type"] == "bool":
                    default = settings[arg] != 0
                argatts["default"] = defval(default)
            arghelp = fish.translate("cli", "help", arg)
            if "help" in argdata and argdata["help"] == "suppress":
                argatts["help"] = argparse.SUPPRESS
            elif not isinstance(arghelp, str):
                argatts["help"] = '\n'.join(arghelp).replace("\\'", "'")
            else:
                argatts["help"] = arghelp + " " + argatts["help"]
            parser.add_argument(argname, **argatts)

    parser.add_argument('--seed', default=defval(int(settings["seed"]) if settings["seed"] != "" and settings["seed"] is not None else None), help="\n".join(fish.translate("cli", "help", "seed")), type=int)
    parser.add_argument('--count', default=defval(int(settings["count"]) if settings["count"] != "" and settings["count"] is not None else 1), help="\n".join(fish.translate("cli", "help", "count")), type=int)
    parser.add_argument('--customitemarray', default={}, help=argparse.SUPPRESS)

    # included for backwards compatibility
    parser.add_argument('--multi', default=defval(settings["multi"]), type=lambda value: min(max(int(value), 1), 255))
    parser.add_argument('--securerandom', default=defval(settings["securerandom"]), action='store_true')
    parser.add_argument('--teams', default=defval(1), type=lambda value: max(int(value), 1))
    parser.add_argument('--settingsfile', dest="filename", help="input json file of settings", type=str)
    parser.add_argument('--customizer', dest="customizer", help='input yaml file for customizations', type=str)
    parser.add_argument('--print_custom_yaml', dest="print_custom_yaml", default=False, action="store_true")

    if player_num:
        for player in range(1, player_num + 1):
            parser.add_argument(f'--p{player}', default=defval(''), help=argparse.SUPPRESS)

    ret = parser.parse_args(argv)

    if ret.keysanity:
        ret.mapshuffle, ret.compassshuffle, ret.bigkeyshuffle = [True] * 3
        ret.keyshuffle = 'wild'

    if ret.keydropshuffle:
        ret.dropshuffle = True
        ret.pottery = 'keys' if ret.pottery == 'none' else ret.pottery

    if ret.retro or ret.mode == 'retro':
        if ret.bow_mode == 'progressive':
            ret.bow_mode = 'retro'
        elif ret.bow_mode == 'silvers':
            ret.bow_mode = 'retro_silvers'
        ret.take_any = 'random' if ret.take_any == 'none' else ret.take_any
        ret.keyshuffle = 'universal'

    if player_num:
        defaults = copy.deepcopy(ret)
        for player in range(1, player_num + 1):
            playerargs = parse_cli(shlex.split(getattr(ret, f"p{player}")), True)
            
            if playerargs.filename:
                playersettings = apply_settings_file({}, playerargs.filename)
                for k, v in playersettings.items():
                    setattr(playerargs, k, v)

            for name in ['logic', 'mode', 'swords', 'goal', 'difficulty', 'item_functionality',
                         'flute_mode', 'bow_mode', 'take_any', 'boots_hint',
                         'shuffle', 'door_shuffle', 'intensity', 'crystals_ganon', 'crystals_gt', 'openpyramid',
                         'mapshuffle', 'compassshuffle', 'keyshuffle', 'bigkeyshuffle', 'startinventory',
                         'usestartinventory', 'bombbag', 'overworld_map', 'restrict_boss_items',
                         'triforce_pool_min', 'triforce_pool_max', 'triforce_goal_min', 'triforce_goal_max',
                         'triforce_min_difference', 'triforce_goal', 'triforce_pool', 'shufflelinks', 'shuffletavern',
                         'pseudoboots', 'retro', 'accessibility', 'hints', 'beemizer', 'experimental', 'dungeon_counters',
                         'shufflebosses', 'shuffleenemies', 'enemy_health', 'enemy_damage', 'shufflepots',
                         'ow_palettes', 'uw_palettes', 'sprite', 'disablemusic', 'quickswap', 'fastmenu', 'heartcolor',
                         'heartbeep', 'remote_items', 'shopsanity', 'dropshuffle', 'pottery', 'keydropshuffle',
                         'mixed_travel', 'standardize_palettes', 'code', 'reduce_flashing', 'shuffle_sfx',
                         'msu_resume', 'collection_rate', 'colorizepots', 'decoupledoors', 'door_type_mode',
                         'trap_door_mode', 'key_logic_algorithm', 'seed_notes', 'seed_name']:
                value = getattr(defaults, name) if getattr(playerargs, name) is None else getattr(playerargs, name)
                if player == 1:
                    setattr(ret, name, {1: value})
                else:
                    getattr(ret, name)[player] = value

    return ret


def apply_settings_file(settings, settings_path):
    if os.path.exists(settings_path):
        with open(settings_path) as json_file:
            data = json.load(json_file)
            for k, v in data.items():
                settings[k] = v
    return settings


def parse_settings():
    # set default settings
    settings = {
        "lang": "en",
        "retro": False,
        "bombbag": False,
        "mode": "open",
        "boots_hint": False,
        "logic": "noglitches",
        "goal": "ganon",
        "crystals_gt": "7",
        "crystals_ganon": "7",
        "swords": "random",
        'flute_mode': 'normal',
        'bow_mode': 'progressive',
        "difficulty": "normal",
        "item_functionality": "normal",
        "timer": "none",
        "progressive": "on",
        "accessibility": "items",
        "algorithm": "balanced",
        'mystery': False,
        'suppress_meta': False,
        "restrict_boss_items": "none",

        # Shuffle Ganon defaults to TRUE
        "openpyramid": 'auto',
        "shuffleganon": True,
        "shuffle": "vanilla",
        "shufflelinks": False,
        "shuffletavern": False,
        "overworld_map": "default",
        'take_any': 'none',
        "pseudoboots": False,

        "shuffleenemies": "none",
        "shufflebosses": "none",
        "enemy_damage": "default",
        "enemy_health": "default",
        "enemizercli": os.path.join(".", "EnemizerCLI", "EnemizerCLI.Core"),

        "shopsanity": False,
        'keydropshuffle': False,
        'dropshuffle': False,
        'pottery': 'none',
        'colorizepots': True,
        'shufflepots': False,
        'mapshuffle': False,
        'compassshuffle': False,
        'keyshuffle': 'none',
        'bigkeyshuffle': False,
        'keysanity': False,
        'door_shuffle': 'vanilla',
        'intensity': 2,
        'door_type_mode': 'original',
        'trap_door_mode': 'optional',
        'key_logic_algorithm': 'default',
        'decoupledoors': False,
        'experimental': False,
        'dungeon_counters': 'default',
        'mixed_travel': 'prevent',
        'standardize_palettes': 'standardize',
        
        "triforce_pool": 0,
        "triforce_goal": 0,
        "triforce_pool_min": 0,
        "triforce_pool_max": 0,
        "triforce_goal_min": 0,
        "triforce_goal_max": 0,
        "triforce_min_difference": 10,

        "code": "",
        "multi": 1,
        "names": "",
        "securerandom": False,

        "hints": False,
        "disablemusic": False,
        "quickswap": False,
        "heartcolor": "red",
        "heartbeep": "normal",
        "sprite": None,
        "fastmenu": "normal",
        "ow_palettes": "default",
        "uw_palettes": "default",
        "reduce_flashing": False,
        "shuffle_sfx": False,
        'msu_resume': False,
        'collection_rate': False,

        # Spoiler     defaults to TRUE
        # Playthrough defaults to TRUE
        # ROM         defaults to TRUE
        "create_spoiler": True,
        "calc_playthrough": True,
        "create_rom": True,
        "bps": False,
        "usestartinventory": False,
        "custom": False,
        "rom": os.path.join(".", "Zelda no Densetsu - Kamigami no Triforce (Japan).sfc"),
        "patch": os.path.join(".", "Patch File.bps"),

        "seed": "",
        "count": 1,
        "startinventory": "",
        "beemizer": 0,
        "remote_items": False,
        "race": False,
        "customitemarray": {
            "bow": 0,
            "progressivebow": 2,
            "boomerang": 1,
            "redmerang": 1,
            "hookshot": 1,
            "mushroom": 1,
            "powder": 1,
            "firerod": 1,
            "icerod": 1,
            "bombos": 1,
            "ether": 1,
            "quake": 1,
            "lamp": 1,
            "hammer": 1,
            "shovel": 1,
            "flute": 1,
            "bugnet": 1,
            "book": 1,
            "bottle": 4,
            "somaria": 1,
            "byrna": 1,
            "cape": 1,
            "mirror": 1,
            "boots": 1,
            "powerglove": 0,
            "titansmitt": 0,
            "progressiveglove": 2,
            "flippers": 1,
            "pearl": 1,
            "heartpiece": 24,
            "heartcontainer": 10,
            "sancheart": 1,
            "sword1": 0,
            "sword2": 0,
            "sword3": 0,
            "sword4": 0,
            "progressivesword": 4,
            "shield1": 0,
            "shield2": 0,
            "shield3": 0,
            "progressiveshield": 3,
            "mail2": 0,
            "mail3": 0,
            "progressivemail": 2,
            "halfmagic": 1,
            "quartermagic": 0,
            "bombsplus5": 0,
            "bombsplus10": 0,
            "arrowsplus5": 0,
            "arrowsplus10": 0,
            "arrow1": 1,
            "arrow10": 12,
            "bomb1": 0,
            "bomb3": 16,
            "bomb10": 1,
            "rupee1": 2,
            "rupee5": 4,
            "rupee20": 28,
            "rupee50": 7,
            "rupee100": 1,
            "rupee300": 5,
            "blueclock": 0,
            "greenclock": 0,
            "redclock": 0,
            "silversupgrade": 0,
            "generickeys": 0,
            "triforcepieces": 0,
            "triforcepiecesgoal": 0,
            "triforce": 0,
            "rupoor": 0,
            "rupoorcost": 10
        },
        "randomSprite": False,
        "outputpath": os.path.join("."),
        "saveonexit": "ask",
        "outputname": "",
        "startinventoryarray": {},
        "seed_name": "",
        "seed_notes": ""
    }

    if sys.platform.lower().find("windows"):
        settings["enemizercli"] += ".exe"

    # read saved settings file if it exists and set these
    settings_path = os.path.join(".", "resources", "user", "settings.json")
    settings = apply_settings_file(settings, settings_path)
    return settings

# Priority fallback is:
#  1: CLI
#  2: Settings file(s)
#  3: Canned defaults


def get_args_priority(settings_args, gui_args, cli_args):
    args = {}
    args["settings"] = parse_settings() if settings_args is None else settings_args
    args["gui"] = gui_args
    args["cli"] = cli_args

    args["load"] = args["settings"]
    if args["gui"] is not None:
        for k in args["gui"]:
            if k not in args["load"] or args["load"][k] != args["gui"]:
                args["load"][k] = args["gui"][k]

    if args["cli"] is None:
        args["cli"] = {}
        cli = vars(parse_cli(None))
        for k, v in cli.items():
            if isinstance(v, dict) and 1 in v:
                args["cli"][k] = v[1]
            else:
                args["cli"][k] = v
        args["cli"] = argparse.Namespace(**args["cli"])

    cli = vars(args["cli"])
    for k in vars(args["cli"]):
        load_doesnt_have_key = k not in args["load"]
        cli_val = cli[k]
        if isinstance(cli_val, dict) and 1 in cli_val:
            cli_val = cli_val[1]
        different_val = (k in args["load"] and k in cli) and (str(args["load"][k]) != str(cli_val))
        cli_has_empty_dict = k in cli and isinstance(cli_val, dict) and len(cli_val) == 0
        if load_doesnt_have_key or different_val:
            if not cli_has_empty_dict:
                args["load"][k] = cli_val

    newArgs = {}
    for key in ["settings", "gui", "cli", "load"]:
        if args[key]:
            if isinstance(args[key], dict):
                newArgs[key] = argparse.Namespace(**args[key])
            else:
                newArgs[key] = args[key]

        else:
            newArgs[key] = args[key]
        newArgs[key] = update_deprecated_args(newArgs[key])

    args = newArgs

    return args
