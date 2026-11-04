import logging
import tempfile
import unittest
from unittest import mock

import Main
import source.overworld.EntranceShuffle2 as EntranceShuffle2
from CLI import parse_cli
from source.classes.BabelFish import BabelFish


class Stop(Exception):
    pass


SRC_UPPER = {'Spectacle Rock Cave Exit (Peak)', 'Spectacle Rock Cave Exit (Top)'}


class TestMustExitConnectors(unittest.TestCase):
    """A must-exit never lands in Spectacle Rock Cave's peak or top, which only drop into the cave."""

    def must_exit_connections(self, mode, shuffle, seed):
        connections = []
        must_exits = set()
        mandatory, two_way = EntranceShuffle2.do_mandatory_connections, EntranceShuffle2.connect_two_way

        def spy_mandatory(avail, entrances, cave_options, must_exit):
            # swapped can spend the cave's bottom exit on a swap partner, leaving peak and top as a pair
            for cave in cave_options:
                if 'Spectacle Rock Cave Exit (Peak)' in cave:
                    cave.remove('Spectacle Rock Cave Exit')
            must_exits.update(must_exit)
            mandatory(avail, entrances, cave_options, must_exit)
            raise Stop

        def spy_two_way(entrance, exit_name, avail):
            if entrance in must_exits:
                connections.append((entrance, exit_name))
            two_way(entrance, exit_name, avail)

        with tempfile.TemporaryDirectory() as out, \
                mock.patch.object(EntranceShuffle2, 'do_mandatory_connections', spy_mandatory), \
                mock.patch.object(EntranceShuffle2, 'connect_two_way', spy_two_way):
            try:
                Main.main(parse_cli(['--mode', mode, '--shuffle', shuffle, '--suppress_rom', '--spoiler', 'none',
                                     '--outputpath', out, '--seed', str(seed)]), seed=seed, fish=BabelFish(lang='en'))
            except Stop:
                pass
        return connections

    def test_must_exits_avoid_spectacle_rock_peak_and_top(self):
        logging.disable(logging.WARNING)
        try:
            for shuffle in ('full', 'crossed'):
                for seed in range(1, 31):
                    with self.subTest(shuffle=shuffle, seed=seed):
                        for entrance, exit_name in self.must_exit_connections('open', shuffle, seed):
                            self.assertNotIn(exit_name, SRC_UPPER, entrance)
        finally:
            logging.disable(logging.NOTSET)


if __name__ == '__main__':
    unittest.main()
