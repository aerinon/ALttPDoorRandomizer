import logging
import tempfile
import unittest
from unittest import mock

import Main
from CLI import parse_cli
from source.classes.BabelFish import BabelFish
from source.overworld.EntranceData import indirect_connections


class Stop(Exception):
    pass


class TestIndirectConnections(unittest.TestCase):
    """An entrance whose rule reads another spot's reachability is retried when the region holding that spot is
    reached; keyed on any other region, shuffled entrances can reach it last and the traversal stops short."""

    def test_old_man_sq_retried_from_the_old_man(self):
        found = {}

        def stop(world, player):
            found['region'] = world.get_location('Old Man', player).parent_region.name
            raise Stop

        logging.disable(logging.WARNING)
        try:
            with tempfile.TemporaryDirectory() as out, mock.patch.object(Main, 'link_entrances_new', stop):
                try:
                    Main.main(parse_cli(['--shuffle', 'lean', '--suppress_rom', '--spoiler', 'none',
                                         '--outputpath', out, '--seed', '1']), seed=1, fish=BabelFish(lang='en'))
                except Stop:
                    pass
        finally:
            logging.disable(logging.NOTSET)
        self.assertEqual(indirect_connections.get(found['region']), 'Old Man S&Q')
        self.assertNotIn('Old Man S&Q', [e for r, e in indirect_connections.items() if r != found['region']])


if __name__ == '__main__':
    unittest.main()
