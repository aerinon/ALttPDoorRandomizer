#!/usr/bin/env python3
import os
import json
import logging
import random
import sys

from CLI import parse_arguments
from Main import main
from Rom import get_sprite_from_name
from Utils import is_bundled, close_console
from Fill import FillError

def start():
    args = parse_arguments(None)

    if is_bundled() and len(sys.argv) == 1:
        # for the bundled builds, if we have no arguments, the user
        # probably wants the gui. Users of the bundled build who want the command line
        # interface shouuld specify at least one option, possibly setting a value to a
        # default if they like all the defaults
        from Gui import guiMain
        close_console()
        guiMain()
        sys.exit(0)

    # ToDo: Validate files further than mere existance

    # set up logger
    loglevel = {'error': logging.ERROR, 'info': logging.INFO, 'warning': logging.WARNING, 'debug': logging.DEBUG}[args.loglevel]
    logging.basicConfig(format='%(message)s', level=loglevel)

    if args.gui:
        from Gui import guiMain
        guiMain(args)
    elif args.count is not None:
        seed = args.seed or random.randint(0, 999999999)
        failures = []
        logger = logging.getLogger('')
        for _ in range(args.count):
            try:
                main(seed=seed, args=args)
                logger.info('Finished run %s', _+1)
            except (FillError, Exception, RuntimeError) as err:
                failures.append((err, seed))
                logger.warning('Generation failed: %s', err)
            seed = random.randint(0, 999999999)
        for fail in failures:
            logger.info('%s seed failed with: %s', fail[1], fail[0])
        logger.info('Generation fail rate: %f%%', 100*len(failures)/args.count)
    else:
        main(seed=args.seed, args=args)


if __name__ == '__main__':
    start()
