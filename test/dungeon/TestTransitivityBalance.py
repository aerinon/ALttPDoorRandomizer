import logging
import unittest

import Main
from CLI import parse_cli
from source.classes.BabelFish import BabelFish
import source.dungeon.DungeonGenTransitivity as Transitivity


class Stop(Exception):
    pass


class TestTransitivityBalance(unittest.TestCase):
    """A door that is already connected can't be forced to waste a branch, so the branch balance must not count it."""

    def setUp(self):
        self.original = Transitivity.do_transitivity_check_main

    def tearDown(self):
        Transitivity.do_transitivity_check_main = self.original

    def test_connected_door_not_counted_as_forced(self):
        # crossed i3, overworld glitches, standard, seed 802680006: the Hyrule Castle East entrance's candidates
        # Skull 3 Lobby SW and GT Bob's Room SE are both valid, but the balance counted the already-connected
        # Sewers Secret Room stairs as forced: the first was rejected and the second ran into the 20k cap.
        results = []
        check = self.original

        def east_candidates(builder, sector_list, flags, initial_connections=None, greedy=False):
            result = check(builder, sector_list, flags, initial_connections, greedy)
            if builder.name == 'Hyrule Castle Sewers' and not greedy \
                    and any('Enter HC (East)' in (a.name, b.name) for a, b in (initial_connections or [])):
                results.append(result)
                raise Stop()
            return result

        Transitivity.do_transitivity_check_main = east_candidates
        argv = ['--door_shuffle', 'crossed', '--intensity', '3', '--dungeon_shuffle_algorithm', 'experimental',
                '--key_logic_algorithm', 'experimental', '--logic', 'owglitches', '--mode', 'standard',
                '--suppress_rom', '--spoiler', 'none', '--seed', '802680006']
        logging.disable(logging.WARNING)
        try:
            with self.assertRaises(Stop):
                Main.main(parse_cli(argv), seed=802680006, fish=BabelFish(lang='en'))
        finally:
            logging.disable(logging.NOTSET)
        self.assertTrue(results[0])  # Skull 3 Lobby SW for the East entrance


if __name__ == '__main__':
    unittest.main()
