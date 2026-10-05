import logging
import unittest

import Main
from CLI import parse_cli
from source.classes.BabelFish import BabelFish


class TestTakeAnyLogic(unittest.TestCase):
    """A take-any gives one item of the player's choice, so logic can't count on any of them; the Old Man's cave has
    no choice, so its sword still counts."""

    def test_take_any_heart_is_not_an_event(self):
        # retro, vanilla doors, seed 160817853: the playthrough cull let Cape, Cane of Byrna and a heart container go
        # because the take-any hearts counted toward Misery Mire's spike chest; its rebuild didn't count them, so the
        # Mire big key was stranded and generation raised "Not all required items reachable"
        argv = ['--door_shuffle', 'vanilla', '--retro', '--shuffle', 'vanilla', '--suppress_rom', '--spoiler', 'none',
                '--seed', '160817853']
        logging.disable(logging.WARNING)
        try:
            world = Main.main(parse_cli(argv), seed=160817853, fish=BabelFish(lang='en'))
        finally:
            logging.disable(logging.NOTSET)
        for n in range(1, 5):
            location = world.get_location(f'Take-Any #{n} Item 2', 1)
            with self.subTest(location=location.name):
                self.assertEqual('Boss Heart Container', location.item.name)
                self.assertFalse(location.event)
        self.assertTrue(world.get_location('Old Man Sword Cave Item 1', 1).event)


if __name__ == '__main__':
    unittest.main()
