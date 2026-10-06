import logging
import unittest

import BaseClasses
import Main
from CLI import parse_cli
from Items import ItemFactory
from source.classes.BabelFish import BabelFish


class Stop(Exception):
    pass


class TestSelfLockingAllowance(unittest.TestCase):
    """The experimental key logic may count a small key being placed as spent on a self-locking door only when the key
    is placed behind that door. Counting it while the key went elsewhere let fill lock two dungeons in each other."""

    @classmethod
    def setUpClass(cls):
        original = Main.fill_dungeons_restrictive

        def stop(world, locations):
            raise Stop(world)

        Main.fill_dungeons_restrictive = stop
        argv = ['--door_shuffle', 'vanilla', '--keysanity', '--key_logic_algorithm', 'experimental', '--suppress_rom',
                '--spoiler', 'none', '--seed', '1']
        logging.disable(logging.WARNING)
        try:
            Main.main(parse_cli(argv), seed=1, fish=BabelFish(lang='en'))
        except Stop as s:
            cls.world = s.args[0]
        finally:
            Main.fill_dungeons_restrictive = original
            logging.disable(logging.NOTSET)

    def reachable(self, spot_name, placed_at):
        """Hold every pooled item except Hera's small key, mark that key as being placed at placed_at (or nowhere)."""
        world = self.world
        state = BaseClasses.CollectionState(world)
        for item in world.itempool:
            if item.player == 1 and item.name != 'Small Key (Tower of Hera)':
                state.collect(item, True)
        key = ItemFactory('Small Key (Tower of Hera)', 1)
        state.placing_items = [key]
        state.placing_locations = [(key, world.get_location(placed_at, 1))] if placed_at else None
        state.stale[1] = True
        world.clear_exp_cache()
        return world.get_location(spot_name, 1).can_reach(state)

    def test_allowance_needs_the_key_behind_the_door(self):
        spot = 'Tower of Hera - Big Key Chest'
        self.assertFalse(self.reachable(spot, None))
        self.assertFalse(self.reachable(spot, "Link's Uncle"))  # placed outside the dungeon
        self.assertTrue(self.reachable(spot, spot))


if __name__ == '__main__':
    unittest.main()
