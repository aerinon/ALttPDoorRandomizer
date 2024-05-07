import argparse
import logging
import RaceRandom as random

from DungeonRandomizer import parse_cli
from Main import main as DRMain
from source.classes.BabelFish import BabelFish
from yaml.constructor import SafeConstructor

from source.tools.MysteryUtils import roll_settings, get_weights


def add_bool(self, node):
    return self.construct_scalar(node)

SafeConstructor.add_constructor(u'tag:yaml.org,2002:bool', add_bool)


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--multi', default=1, type=lambda value: min(max(int(value), 1), 255))
    multiargs, _ = parser.parse_known_args()

    parser = argparse.ArgumentParser()
    parser.add_argument('--weights', help='Path to the weights file to use for rolling game settings, urls are also valid')
    parser.add_argument('--samesettings', help='Rolls settings per weights file rather than per player', action='store_true')
    parser.add_argument('--seed', help='Define seed number to generate.', type=int)
    parser.add_argument('--multi', default=1, type=lambda value: min(max(int(value), 1), 255))
    parser.add_argument('--names', default='')
    parser.add_argument('--teams', default=1, type=lambda value: max(int(value), 1))
    parser.add_argument('--spoiler', default='none', choices=['none', 'settings', 'semi', 'full', 'debug'])
    parser.add_argument('--suppress_rom', action='store_true')
    parser.add_argument('--suppress_meta', action='store_true')
    parser.add_argument('--bps', action='store_true')
    parser.add_argument('--rom')
    parser.add_argument('--outputpath')
    parser.add_argument('--loglevel', default='info', choices=['debug', 'info', 'warning', 'error', 'critical'])
    for player in range(1, multiargs.multi + 1):
        parser.add_argument(f'--p{player}', help=argparse.SUPPRESS)
    args = parser.parse_args()

    if args.seed is None:
        random.seed(None)
        seed = random.randint(0, 999999999)
    else:
        seed = args.seed
    random.seed(seed)

    seedname = f'M{random.randint(0, 999999999)}'
    print(f"Generating mystery for {args.multi} player{'s' if args.multi > 1 else ''}, {seedname} Seed {seed}")

    weights_cache = {}
    if args.weights:
        weights_cache[args.weights] = get_weights(args.weights)
        print(f"Weights: {args.weights} >> {weights_cache[args.weights]['description']}")
    for player in range(1, args.multi + 1):
        path = getattr(args, f'p{player}')
        if path:
            if path not in weights_cache:
                weights_cache[path] = get_weights(path)
            print(f"P{player} Weights: {path} >> {weights_cache[path]['description']}")

    erargs = parse_cli(['--multi', str(args.multi)])
    erargs.seed = seed
    erargs.names = args.names
    erargs.spoiler = args.spoiler
    erargs.suppress_rom = args.suppress_rom
    erargs.suppress_meta = args.suppress_meta
    erargs.bps = args.bps
    erargs.race = True
    erargs.outputname = seedname
    erargs.outputpath = args.outputpath
    erargs.loglevel = args.loglevel
    erargs.mystery = True

    if args.rom:
        erargs.rom = args.rom

    mw_settings = {'algorithm': False}

    settings_cache = {k: (roll_settings(v) if args.samesettings else None) for k, v in weights_cache.items()}

    for player in range(1, args.multi + 1):
        path = getattr(args, f'p{player}') if getattr(args, f'p{player}') else args.weights
        if path:
            settings = settings_cache[path] if settings_cache[path] else roll_settings(weights_cache[path])
            for k, v in vars(settings).items():
                if v is not None:
                    if k == 'algorithm':  # multiworld wide parameters
                        if not mw_settings[k]:  # only use the first roll
                            setattr(erargs, k, v)
                            mw_settings[k] = True
                    else:
                        getattr(erargs, k)[player] = v
        else:
            raise RuntimeError(f'No weights specified for player {player}')

    # set up logger
    loglevel = {'error': logging.ERROR, 'info': logging.INFO, 'warning': logging.WARNING, 'debug': logging.DEBUG}[erargs.loglevel]
    logging.basicConfig(format='%(message)s', level=loglevel)

    DRMain(erargs, seed, BabelFish())


if __name__ == '__main__':
    main()
