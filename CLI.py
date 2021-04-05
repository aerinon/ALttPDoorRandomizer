import argparse
import copy
import json
import os
import textwrap
import shlex
import sys

import source.classes.constants as CONST
from source.classes.BabelFish import BabelFish

from Utils import update_deprecated_args


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
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--multi', default=defval(settings["multi"]), type=lambda value: min(max(int(value), 1), 255))
    multiargs, _ = parser.parse_known_args(argv)

    parser = argparse.ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter)

    # get args
    args = []
    with open(os.path.join("resources","app","cli","args.json")) as argsFile:
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
        arghelp = fish.translate("cli","help",arg)
        if "help" in argdata and argdata["help"] == "suppress":
          argatts["help"] = argparse.SUPPRESS
        elif not isinstance(arghelp,str):
          argatts["help"] = '\n'.join(arghelp).replace("\\'","'")
        else:
          argatts["help"] = arghelp + " " + argatts["help"]
        parser.add_argument(argname,**argatts)

    parser.add_argument('--seed', default=defval(int(settings["seed"]) if settings["seed"] != "" and settings["seed"] is not None else None), help="\n".join(fish.translate("cli","help","seed")), type=int)
    parser.add_argument('--count', default=defval(int(settings["count"]) if settings["count"] != "" and settings["count"] is not None else 1), help="\n".join(fish.translate("cli","help","count")), type=int)
    parser.add_argument('--customitemarray', default={}, help=argparse.SUPPRESS)

    # included for backwards compatibility
    parser.add_argument('--beemizer', default=defval(settings["beemizer"]), type=lambda value: min(max(int(value), 0), 4))
    parser.add_argument('--multi', default=defval(settings["multi"]), type=lambda value: min(max(int(value), 1), 255))
    parser.add_argument('--securerandom', default=defval(settings["securerandom"]), action='store_true')
    parser.add_argument('--teams', default=defval(1), type=lambda value: max(int(value), 1))

    if multiargs.multi:
        for player in range(1, multiargs.multi + 1):
            parser.add_argument(f'--p{player}', default=defval(''), help=argparse.SUPPRESS)

    ret = parser.parse_args(argv)

    if ret.keysanity:
        ret.mapshuffle, ret.compassshuffle, ret.keyshuffle, ret.bigkeyshuffle = [True] * 4

    if ret.futuro:
        ret.futurobombs, ret.futuromagic, ret.futurobows, ret.futuroportal = [True] * 4

    if multiargs.multi:
        defaults = copy.deepcopy(ret)
        for player in range(1, multiargs.multi + 1):
            playerargs = parse_cli(shlex.split(getattr(ret,f"p{player}")), True)

            for name in ['logic', 'mode', 'swords', 'goal', 'difficulty', 'item_functionality',
                         'shuffle', 'door_shuffle', 'intensity', 'crystals_ganon', 'crystals_gt', 'openpyramid',
                         'mapshuffle', 'compassshuffle', 'keyshuffle', 'bigkeyshuffle', 'startinventory',
                         'futurobombs', 'futuromagic', 'futurobows', 'futuroportal',
                         'retro', 'accessibility', 'hints', 'beemizer', 'experimental', 'dungeon_counters',
                         'triforce_pool_min', 'triforce_pool_max', 'triforce_goal_min', 'triforce_goal_max',
                         'triforce_min_difference', 'triforce_goal', 'triforce_pool',
                         'retro', 'accessibility', 'hints', 'beemizer', 'experimental', 'dungeon_counters',
                         'shufflebosses', 'shuffleenemies', 'enemy_health', 'enemy_damage', 'shufflepots',
                         'ow_palettes', 'uw_palettes', 'sprite', 'disablemusic', 'quickswap', 'fastmenu', 'heartcolor', 'heartbeep',
                         'remote_items', 'shopsanity', 'keydropshuffle', 'mixed_travel', 'standardize_palettes', 'code']:
                value = getattr(defaults, name) if getattr(playerargs, name) is None else getattr(playerargs, name)
                if player == 1:
                    setattr(ret, name, {1: value})
                else:
                    getattr(ret, name)[player] = value

    return ret


def parse_settings():
    # set default settings
    settings = {
        "lang": "en",
        "retro": False,
        "futuro": False,
        "futurobombs": False,
        "futuromagic": False,
        "futurobows": False,
        "futuroportal": False,
        "mode": "open",
        "logic": "noglitches",
        "goal": "ganon",
        "crystals_gt": "7",
        "crystals_ganon": "7",
        "swords": "random",
        "difficulty": "normal",
        "item_functionality": "normal",
        "timer": "none",
        "progressive": "on",
        "accessibility": "items",
        "algorithm": "balanced",

        # Shuffle Ganon defaults to TRUE
        "openpyramid": False,
        "shuffleganon": True,
        "shuffle": "vanilla",

        "shufflepots": False,
        "shuffleenemies": "none",
        "shufflebosses": "none",
        "enemy_damage": "default",
        "enemy_health": "default",
        "enemizercli": os.path.join(".", "EnemizerCLI", "EnemizerCLI.Core"),

        "shopsanity": False,
        "keydropshuffle": False,
        "mapshuffle": False,
        "compassshuffle": False,
        "keyshuffle": False,
        "bigkeyshuffle": False,
        "keysanity": False,
        "door_shuffle": "basic",
        "intensity": 2,
        "experimental": False,
        "dungeon_counters": "default",
        "mixed_travel": "prevent",
        "standardize_palettes": "standardize",
        
        "triforce_pool": 30,
        "triforce_goal": 20,
        "triforce_pool_min": 0,
        "triforce_pool_max": 0,
        "triforce_goal_min": 0,
        "triforce_goal_max": 0,
        "triforce_min_difference": 10,

        "code": "",
        "multi": 1,
        "names": "",
        "securerandom": False,

        # Hints default to TRUE
        "hints": True,
        "no_hints": False,
        "disablemusic": False,
        "quickswap": False,
        "heartcolor": "red",
        "heartbeep": "normal",
        "sprite": os.path.join(".","data","sprites","official","001.link.1.zspr"),
        "fastmenu": "normal",
        "ow_palettes": "default",
        "uw_palettes": "default",

        # Spoiler     defaults to TRUE
        # Playthrough defaults to TRUE
        # ROM         defaults to TRUE
        "create_spoiler": True,
        "calc_playthrough": True,
        "create_rom": True,
        "usestartinventory": False,
        "custom": False,
        "rom": os.path.join(".", "Zelda no Densetsu - Kamigami no Triforce (Japan).sfc"),

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
        "startinventoryarray": {}
    }

    if sys.platform.lower().find("windows"):
        settings["enemizercli"] += ".exe"

    # read saved settings file if it exists and set these
    settings_path = os.path.join(".", "resources", "user", "settings.json")
    if os.path.exists(settings_path):
        with(open(settings_path)) as json_file:
            data = json.load(json_file)
            for k, v in data.items():
                settings[k] = v
    return settings

# Priority fallback is:
#  1: CLI
#  2: Settings file
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
        if isinstance(cli_val,dict) and 1 in cli_val:
            cli_val = cli_val[1]
        different_val = (k in args["load"] and k in cli) and (str(args["load"][k]) != str(cli_val))
        cli_has_empty_dict = k in cli and isinstance(cli_val, dict) and len(cli_val) == 0
        if load_doesnt_have_key or different_val:
            if not cli_has_empty_dict:
                args["load"][k] = cli_val

    newArgs = {}
    for key in [ "settings", "gui", "cli", "load" ]:
        if args[key]:
            if isinstance(args[key],dict):
                newArgs[key] = argparse.Namespace(**args[key])
            else:
                newArgs[key] = args[key]

        else:
            newArgs[key] = args[key]
        newArgs[key] = update_deprecated_args(newArgs[key])

    args = newArgs

    return args
