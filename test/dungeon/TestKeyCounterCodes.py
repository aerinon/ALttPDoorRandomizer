import logging
import unittest

import Main
from CLI import parse_cli
from KeyDoorShuffle import create_key_counters, state_id
from source.classes.BabelFish import BabelFish


class TestKeyCounterCodes(unittest.TestCase):
    """create_key_counters keys each counter by the code its door opens, computed from the parent before expanding.
    That code must match the code of the expanded state, or counters would be lost or merged."""

    @classmethod
    def setUpClass(cls):
        argv = ['--door_shuffle', 'vanilla', '--keydropshuffle', '--pottery', 'keys', '--suppress_rom',
                '--spoiler', 'none', '--seed', '1']
        logging.disable(logging.WARNING)
        try:
            cls.world = Main.main(parse_cli(argv), seed=1, fish=BabelFish(lang='en'))
        finally:
            logging.disable(logging.NOTSET)

    def test_codes_match_expanded_states(self):
        checked = 0
        for name, layout in self.world.key_layout[1].items():
            counters = create_key_counters(layout, self.world, 1)
            with self.subTest(dungeon=name):
                for code, counter in counters.items():
                    self.assertEqual(code, state_id(counter.state_ref, layout.flat_prop))
                self.assertEqual(len(counters), len({id(c) for c in counters.values()}))
            checked += len(counters) > 1
        self.assertGreater(checked, 5)


if __name__ == '__main__':
    unittest.main()
