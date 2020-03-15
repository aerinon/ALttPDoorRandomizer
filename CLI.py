import argparse
import copy
import json
import os
import logging
import random
import textwrap
import shlex
import sys

from Main import main
from Utils import is_bundled, close_console
from Fill import FillError

import classes.constants as CONST


class ArgumentDefaultsHelpFormatter(argparse.RawTextHelpFormatter):

    def _get_help_string(self, action):
        return textwrap.dedent(action.help)

def parse_arguments(argv, no_defaults=False):
    def defval(value):
        return value if not no_defaults else None

    # get settings
    settings = get_settings()

    # we need to know how many players we have first
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--multi', default=defval(settings["multi"]), type=lambda value: min(max(int(value), 1), 255))
    multiargs, _ = parser.parse_known_args(argv)

    parser = argparse.ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter)
    parser.add_argument('--create_spoiler', default=defval(settings["create_spoiler"] != 0), help='Output a Spoiler File', action='store_true')
    parser.add_argument('--logic', default=defval(settings["logic"]), const='noglitches', nargs='?', choices=['noglitches', 'minorglitches', 'owglitches', 'nologic'],
                        help='''\
                             Select Enforcement of Item Requirements. (default: %(default)s)
                             No Glitches:
                             Minor Glitches: May require Fake Flippers, Bunny Revival
                                             and Dark Room Navigation.
                             Overworld Glitches: May require overworld glitches. Starts with
                                             boots.
                             No Logic: Distribute items without regard for
                                             item requirements. Starts with
                                             boots
                             ''')
    parser.add_argument('--mode', default=defval(settings["mode"]), const='open', nargs='?', choices=['standard', 'open', 'inverted'],
                        help='''\
                             Select game mode. (default: %(default)s)
                             Open:      World starts with Zelda rescued.
                             Standard:  Fixes Hyrule Castle Secret Entrance and Front Door
                                        but may lead to weird rain state issues if you exit
                                        through the Hyrule Castle side exits before rescuing
                                        Zelda in a full shuffle.
                             Inverted:  Starting locations are Dark Sanctuary in West Dark
                                        World or at Link's House, which is shuffled freely.
                                        Requires the moon pearl to be Link in the Light World
                                        instead of a bunny.
                             ''')
    parser.add_argument('--swords', default=defval(settings["swords"]), const='random', nargs='?', choices= ['random', 'assured', 'swordless', 'vanilla'],
                        help='''\
                             Select sword placement. (default: %(default)s)
                             Random:    All swords placed randomly.
                             Assured:   Start game with a sword already.
                             Swordless: No swords. Curtains in Skull Woods and Agahnim\'s
                                        Tower are removed, Agahnim\'s Tower barrier can be
                                        destroyed with hammer. Misery Mire and Turtle Rock
                                        can be opened without a sword. Hammer damages Ganon.
                                        Ether and Bombos Tablet can be activated with Hammer
                                        (and Book). Bombos pads have been added in Ice
                                        Palace, to allow for an alternative to firerod.
                             Vanilla:   Swords are in vanilla locations.
                             ''')
    parser.add_argument('--goal', default=defval(settings["goal"]), const='ganon', nargs='?', choices=['ganon', 'pedestal', 'dungeons', 'triforcehunt', 'crystals'],
                        help='''\
                             Select completion goal. (default: %(default)s)
                             Ganon:         Collect all crystals, beat Agahnim 2 then
                                            defeat Ganon.
                             Crystals:      Collect all crystals then defeat Ganon.
                             Pedestal:      Places the Triforce at the Master Sword Pedestal.
                             All Dungeons:  Collect all crystals, pendants, beat both
                                            Agahnim fights and then defeat Ganon.
                             Triforce Hunt: Places 30 Triforce Pieces in the world, collect
                                            20 of them to beat the game.
                             ''')
    parser.add_argument('--difficulty', default=defval(settings["difficulty"]), const='normal', nargs='?', choices=['normal', 'hard', 'expert'],
                        help='''\
                             Select game difficulty. Affects available itempool. (default: %(default)s)
                             Normal:          Normal difficulty.
                             Hard:            A harder setting with less equipment and reduced health.
                             Expert:          A harder yet setting with minimum equipment and health.
                             ''')
    parser.add_argument('--item_functionality', default=defval(settings["item_functionality"]), const='normal', nargs='?', choices=['normal', 'hard', 'expert'],
                             help='''\
                             Select limits on item functionality to increase difficulty. (default: %(default)s)
                             Normal:          Normal functionality.
                             Hard:            Reduced functionality.
                             Expert:          Greatly reduced functionality.
                                  ''')
    parser.add_argument('--timer', default=defval(settings["timer"]), const='normal', nargs='?', choices=['none', 'display', 'timed', 'timed-ohko', 'ohko', 'timed-countdown'],
                        help='''\
                             Select game timer setting. Affects available itempool. (default: %(default)s)
                             None:            No timer.
                             Display:         Displays a timer but does not affect
                                              the itempool.
                             Timed:           Starts with clock at zero. Green Clocks
                                              subtract 4 minutes (Total: 20), Blue Clocks
                                              subtract 2 minutes (Total: 10), Red Clocks add
                                              2 minutes (Total: 10). Winner is player with
                                              lowest time at the end.
                             Timed OHKO:      Starts clock at 10 minutes. Green Clocks add
                                              5 minutes (Total: 25). As long as clock is at 0,
                                              Link will die in one hit.
                             OHKO:            Like Timed OHKO, but no clock items are present
                                              and the clock is permenantly at zero.
                             Timed Countdown: Starts with clock at 40 minutes. Same clocks as
                                              Timed mode. If time runs out, you lose (but can
                                              still keep playing).
                             ''')
    parser.add_argument('--progressive', default=defval(settings["progressive"]), const='normal', nargs='?', choices=['on', 'off', 'random'],
                        help='''\
                             Select progressive equipment setting. Affects available itempool. (default: %(default)s)
                             On:              Swords, Shields, Armor, and Gloves will
                                              all be progressive equipment. Each subsequent
                                              item of the same type the player finds will
                                              upgrade that piece of equipment by one stage.
                             Off:             Swords, Shields, Armor, and Gloves will not
                                              be progressive equipment. Higher level items may
                                              be found at any time. Downgrades are not possible.
                             Random:          Swords, Shields, Armor, and Gloves will, per
                                              category, be randomly progressive or not.
                                              Link will die in one hit.
                             ''')
    parser.add_argument('--algorithm', default=defval(settings["algorithm"]), const='balanced', nargs='?', choices=['freshness', 'flood', 'vt21', 'vt22', 'vt25', 'vt26', 'balanced'],
                        help='''\
                             Select item filling algorithm. (default: %(default)s
                             balanced:    vt26 derivative that aims to strike a balance between
                                          the overworld heavy vt25 and the dungeon heavy vt26
                                          algorithm.
                             vt26:        Shuffle items and place them in a random location
                                          that it is not impossible to be in. This includes
                                          dungeon keys and items.
                             vt25:        Shuffle items and place them in a random location
                                          that it is not impossible to be in.
                             vt21:        Unbiased in its selection, but has tendency to put
                                          Ice Rod in Turtle Rock.
                             vt22:        Drops off stale locations after 1/3 of progress
                                          items were placed to try to circumvent vt21\'s
                                          shortcomings.
                             Freshness:   Keep track of stale locations (ones that cannot be
                                          reached yet) and decrease likeliness of selecting
                                          them the more often they were found unreachable.
                             Flood:       Push out items starting from Link\'s House and
                                          slightly biased to placing progression items with
                                          less restrictions.
                             ''')
    parser.add_argument('--shuffle', default=defval(settings["shuffle"]), const='full', nargs='?', choices=['vanilla', 'simple', 'restricted', 'full', 'crossed', 'insanity', 'restricted_legacy', 'full_legacy', 'madness_legacy', 'insanity_legacy', 'dungeonsfull', 'dungeonssimple'],
                        help='''\
                             Select Entrance Shuffling Algorithm. (default: %(default)s)
                             Full:       Mix cave and dungeon entrances freely while limiting
                                         multi-entrance caves to one world.
                             Simple:     Shuffle Dungeon Entrances/Exits between each other
                                         and keep all 4-entrance dungeons confined to one
                                         location. All caves outside of death mountain are
                                         shuffled in pairs and matched by original type.
                             Restricted: Use Dungeons shuffling from Simple but freely
                                         connect remaining entrances.
                             Crossed:    Mix cave and dungeon entrances freely while allowing
                                         caves to cross between worlds.
                             Insanity:   Decouple entrances and exits from each other and
                                         shuffle them freely. Caves that used to be single
                                         entrance will still exit to the same location from
                                         which they are entered.
                             Vanilla:    All entrances are in the same locations they were
                                         in the base game.
                             Legacy shuffles preserve behavior from older versions of the
                             entrance randomizer including significant technical limitations.
                             The dungeon variants only mix up dungeons and keep the rest of
                             the overworld vanilla.
                             ''')
    parser.add_argument('--door_shuffle', default=defval(settings["door_shuffle"]), const='vanilla', nargs='?', choices=['vanilla', 'basic', 'crossed'],
                        help='''\
                            Select Door Shuffling Algorithm. (default: %(default)s)
                            Basic:      Doors are mixed within a single dungeon.
                                        (Not yet implemented)
                            Crossed:    Doors are mixed between all dungeons.
                                        (Not yet implemented)
                            Vanilla:    All doors are connected the same way they were in the
                                        base game.                        
                        ''')
    parser.add_argument('--experimental', default=defval(settings["experimental"] != 0), help='Enable experimental features', action='store_true')
    parser.add_argument('--dungeon_counters', default=defval(settings["dungeon_counters"]), help='Enable dungeon chest counters', const='off', nargs='?', choices=['off', 'on', 'pickup', 'default'])
    parser.add_argument('--crystals_ganon', default=defval(settings["crystals_ganon"]), const='7', nargs='?', choices=['random', '0', '1', '2', '3', '4', '5', '6', '7'],
                        help='''\
                             How many crystals are needed to defeat ganon. Any other
                             requirements for ganon for the selected goal still apply.
                             This setting does not apply when the all dungeons goal is
                             selected. (default: %(default)s)
                             Random: Picks a random value between 0 and 7 (inclusive).
                             0-7:    Number of crystals needed
                             ''')
    parser.add_argument('--crystals_gt', default=defval(settings["crystals_gt"]), const='7', nargs='?', choices=['random', '0', '1', '2', '3', '4', '5', '6', '7'],
                        help='''\
                             How many crystals are needed to open GT. For inverted mode
                             this applies to the castle tower door instead. (default: %(default)s)
                             Random: Picks a random value between 0 and 7 (inclusive).
                             0-7:    Number of crystals needed
                             ''')
    parser.add_argument('--openpyramid', default=defval(settings["openpyramid"] != 0), help='''\
                            Pre-opens the pyramid hole, this removes the Agahnim 2 requirement for it
                             ''', action='store_true')
    parser.add_argument('--rom', default=defval(settings["rom"]), help='Path to an ALttP JAP(1.0) rom to use as a base.')
    parser.add_argument('--loglevel', default=defval('info'), const='info', nargs='?', choices=['error', 'info', 'warning', 'debug'], help='Select level of logging for output.')
    parser.add_argument('--seed', default=defval(int(settings["seed"]) if settings["seed"] != "" and settings["seed"] is not None else None), help='Define seed number to generate.', type=int)
    parser.add_argument('--count', default=defval(int(settings["count"]) if settings["count"] != "" and settings["count"] is not None else None), help='''\
                             Use to batch generate multiple seeds with same settings.
                             If --seed is provided, it will be used for the first seed, then
                             used to derive the next seed (i.e. generating 10 seeds with
                             --seed given will produce the same 10 (different) roms each
                             time).
                             ''', type=int)
    parser.add_argument('--fastmenu', default=defval(settings["fastmenu"]), const='normal', nargs='?', choices=['normal', 'instant', 'double', 'triple', 'quadruple', 'half'],
                        help='''\
                             Select the rate at which the menu opens and closes.
                             (default: %(default)s)
                             ''')
    parser.add_argument('--quickswap', default=defval(settings["quickswap"] != 0), help='Enable quick item swapping with L and R.', action='store_true')
    parser.add_argument('--disablemusic', default=defval(settings["disablemusic"] != 0), help='Disables game music.', action='store_true')
    parser.add_argument('--mapshuffle', default=defval(settings["mapshuffle"] != 0), help='Maps are no longer restricted to their dungeons, but can be anywhere', action='store_true')
    parser.add_argument('--compassshuffle', default=defval(settings["compassshuffle"] != 0), help='Compasses are no longer restricted to their dungeons, but can be anywhere', action='store_true')
    parser.add_argument('--keyshuffle', default=defval(settings["keyshuffle"] != 0), help='Small Keys are no longer restricted to their dungeons, but can be anywhere', action='store_true')
    parser.add_argument('--bigkeyshuffle', default=defval(settings["bigkeyshuffle"] != 0), help='Big Keys are no longer restricted to their dungeons, but can be anywhere', action='store_true')
    parser.add_argument('--keysanity', default=defval(settings["keysanity"] != 0), help=argparse.SUPPRESS, action='store_true')
    parser.add_argument('--retro', default=defval(settings["retro"] != 0), help='''\
                             Keys are universal, shooting arrows costs rupees,
                             and a few other little things make this more like Zelda-1.
                             ''', action='store_true')
    parser.add_argument('--startinventory', default=defval(settings["startinventory"]), help='Specifies a list of items that will be in your starting inventory (separated by commas)')
    parser.add_argument('--usestartinventory', default=defval(settings["usestartinventory"] != 0), help='Not supported.')
    parser.add_argument('--custom', default=defval(settings["custom"] != 0), help='Not supported.')
    parser.add_argument('--customitemarray', default={}, help='Not supported.')
    parser.add_argument('--accessibility', default=defval(settings["accessibility"]), const='items', nargs='?', choices=['items', 'locations', 'none'], help='''\
                             Select Item/Location Accessibility. (default: %(default)s)
                             Items:     You can reach all unique inventory items. No guarantees about
                                        reaching all locations or all keys.
                             Locations: You will be able to reach every location in the game.
                             None:      You will be able to reach enough locations to beat the game.
                             ''')
    parser.add_argument('--hints', default=defval(settings["hints"] != 0), help='''\
                             Make telepathic tiles and storytellers give helpful hints.
                             ''', action='store_true')
    # included for backwards compatibility
    parser.add_argument('--shuffleganon', help=argparse.SUPPRESS, action='store_true', default=defval(settings["shuffleganon"] != 0))
    parser.add_argument('--no-shuffleganon', help='''\
                             If set, the Pyramid Hole and Ganon's Tower are not
                             included entrance shuffle pool.
                             ''', action='store_false', dest='shuffleganon')
    parser.add_argument('--heartbeep', default=defval(settings["heartbeep"]), const='normal', nargs='?', choices=['double', 'normal', 'half', 'quarter', 'off'],
                        help='''\
                             Select the rate at which the heart beep sound is played at
                             low health. (default: %(default)s)
                             ''')
    parser.add_argument('--heartcolor', default=defval(settings["heartcolor"]), const='red', nargs='?', choices=['red', 'blue', 'green', 'yellow', 'random'],
                        help='Select the color of Link\'s heart meter. (default: %(default)s)')
    parser.add_argument('--ow_palettes', default=defval(settings["ow_palettes"]), choices=['default', 'random', 'blackout'])
    parser.add_argument('--uw_palettes', default=defval(settings["uw_palettes"]), choices=['default', 'random', 'blackout'])
    parser.add_argument('--sprite', default=defval(settings["sprite"]), help='''\
                             Path to a sprite sheet to use for Link. Needs to be in
                             binary format and have a length of 0x7000 (28672) bytes,
                             or 0x7078 (28792) bytes including palette data.
                             Alternatively, can be a ALttP Rom patched with a Link
                             sprite that will be extracted.
                             ''')
    parser.add_argument('--suppress_rom', default=defval(settings["suppress_rom"] != 0), help='Do not create an output rom file.', action='store_true')
    parser.add_argument('--gui', help='Launch the GUI', action='store_true')
    parser.add_argument('--jsonout', action='store_true', help='''\
                            Output .json patch to stdout instead of a patched rom. Used
                            for VT site integration, do not use otherwise.
                            ''')
    parser.add_argument('--skip_playthrough', action='store_true', default=defval(settings["skip_playthrough"] != 0))
    parser.add_argument('--enemizercli', default=defval(settings["enemizercli"]))
    parser.add_argument('--shufflebosses', default=defval(settings["shufflebosses"]), choices=['none', 'basic', 'normal', 'chaos'])
    parser.add_argument('--shuffleenemies', default=defval(settings["shuffleenemies"]), choices=['none', 'shuffled', 'chaos'])
    parser.add_argument('--enemy_health', default=defval(settings["enemy_health"]), choices=['default', 'easy', 'normal', 'hard', 'expert'])
    parser.add_argument('--enemy_damage', default=defval(settings["enemy_damage"]), choices=['default', 'shuffled', 'chaos'])
    parser.add_argument('--shufflepots', default=defval(settings["shufflepots"] != 0), action='store_true')
    parser.add_argument('--beemizer', default=defval(settings["beemizer"]), type=lambda value: min(max(int(value), 0), 4))
    parser.add_argument('--remote_items', default=defval(settings["remote_items"] != 0), action='store_true')
    parser.add_argument('--multi', default=defval(settings["multi"]), type=lambda value: min(max(int(value), 1), 255))
    parser.add_argument('--names', default=defval(settings["names"]))
    parser.add_argument('--teams', default=defval(1), type=lambda value: max(int(value), 1))
    parser.add_argument('--outputpath', default=defval(settings["outputpath"]))
    parser.add_argument('--race', default=defval(settings["race"] != 0), action='store_true')
    parser.add_argument('--saveonexit', default=defval(settings["saveonexit"]), choices=['never', 'ask', 'always'])
    parser.add_argument('--outputname')

    if multiargs.multi:
        for player in range(1, multiargs.multi + 1):
            parser.add_argument(f'--p{player}', default=defval(''), help=argparse.SUPPRESS)

    ret = parser.parse_args(argv)

    if ret.keysanity:
        ret.mapshuffle, ret.compassshuffle, ret.keyshuffle, ret.bigkeyshuffle = [True] * 4

    if multiargs.multi:
        defaults = copy.deepcopy(ret)
        for player in range(1, multiargs.multi + 1):
            playerargs = parse_arguments(shlex.split(getattr(ret,f"p{player}")), True)

            for name in ['logic', 'mode', 'swords', 'goal', 'difficulty', 'item_functionality',
                         'shuffle', 'door_shuffle', 'crystals_ganon', 'crystals_gt', 'openpyramid',
                         'mapshuffle', 'compassshuffle', 'keyshuffle', 'bigkeyshuffle', 'startinventory',
                         'retro', 'accessibility', 'hints', 'beemizer', 'experimental', 'dungeon_counters',
                         'shufflebosses', 'shuffleenemies', 'enemy_health', 'enemy_damage', 'shufflepots',
                         'ow_palettes', 'uw_palettes', 'sprite', 'disablemusic', 'quickswap', 'fastmenu', 'heartcolor', 'heartbeep',
                         'remote_items']:
                value = getattr(defaults, name) if getattr(playerargs, name) is None else getattr(playerargs, name)
                if player == 1:
                    setattr(ret, name, {1: value})
                else:
                    getattr(ret, name)[player] = value

    return ret


def get_settings():
    # set default settings
    settings = {
        "retro": False,
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

        "openpyramid": False,
        "shuffleganon": False,
        "shuffle": "vanilla",

        "shufflepots": False,
        "shuffleenemies": "none",
        "shufflebosses": "none",
        "enemy_damage": "default",
        "enemy_health": "default",
        "enemizercli": os.path.join(".", "EnemizerCLI", "EnemizerCLI.Core"),

        "mapshuffle": False,
        "compassshuffle": False,
        "keyshuffle": False,
        "bigkeyshuffle": False,
        "keysanity": False,
        "door_shuffle": "basic",
        "experimental": False,
        "dungeon_counters": "default",

        "multi": 1,
        "names": "",

        "hints": True,
        "disablemusic": False,
        "quickswap": False,
        "heartcolor": "red",
        "heartbeep": "normal",
        "sprite": None,
        "fastmenu": "normal",
        "ow_palettes": "default",
        "uw_palettes": "default",

        "create_spoiler": False,
        "skip_playthrough": False,
        "suppress_rom": False,
        "usestartinventory": False,
        "custom": False,
        "rom": os.path.join(".", "Zelda no Densetsu - Kamigami no Triforce (Japan).sfc"),

        "seed": None,
        "count": None,
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


def get_args_priority(settings_args, gui_args, cli_args):
    args = {}
    args["settings"] = get_settings() if settings_args is None else settings_args
    args["gui"] = {} if gui_args is None else gui_args
    args["cli"] = cli_args

    args["load"] = args["settings"]
    if args["gui"] is not None:
        for k in args["gui"]:
            if k not in args["load"] or args["load"][k] != args["gui"]:
                args["load"][k] = args["gui"][k]

    if args["cli"] is None:
        args["cli"] = {}
        cli = vars(parse_arguments(None))
        for k, v in cli.items():
            if isinstance(v, dict) and 1 in v:
                args["cli"][k] = v[1]
            else:
                args["cli"][k] = v
            load_doesnt_have_key = k not in args["load"]
            different_val = (k in args["load"] and k in args["cli"]) and (args["load"][k] != args["cli"][k])
            cli_has_empty_dict = k in args["cli"] and isinstance(args["cli"][k], dict) and len(args["cli"][k]) == 0
            if load_doesnt_have_key or different_val:
                if not cli_has_empty_dict:
                    args["load"][k] = args["cli"][k]

    return args
