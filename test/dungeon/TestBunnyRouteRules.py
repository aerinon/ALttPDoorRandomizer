import logging
import signal
import unittest

import Main
from CLI import parse_cli
from source.classes.BabelFish import BabelFish


class TestBunnyRouteRules(unittest.TestCase):
    """Bunny rules for mixed regions search routes when evaluated, so their cost follows the region graph rather than
    the number of distinct routes, which explodes with per-entrance key rules."""

    def test_route_heavy_world_generates_quickly(self):
        # crossed i2 experimental, OWG inverted; doors and entrances pinned by the customizer. Enumerating routes
        # stalled fill on this world for over four minutes
        argv = ['--customizer', 'test/customizer/bunny_routes.yaml', '--suppress_rom', '--spoiler', 'none']

        def too_slow(*_):
            raise TimeoutError('generation took over 120 s')

        previous = signal.signal(signal.SIGALRM, too_slow)
        signal.alarm(120)
        logging.disable(logging.WARNING)
        try:
            world = Main.main(parse_cli(argv), fish=BabelFish(lang='en'))
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, previous)
            logging.disable(logging.NOTSET)
        self.assertIsNotNone(world)


if __name__ == '__main__':
    unittest.main()
