import logging
import unittest

import Main
from CLI import parse_cli
from source.classes.BabelFish import BabelFish


class TestDungeonFillReach(unittest.TestCase):
    """Dungeon items must sit where the finished world reaches them. The experimental key logic is not monotone in the
    big key (holding it opens more doors to waste small keys on), so reach swept before big keys were placed must not
    carry into the small key and map/compass fills: seed 120 put Turtle Rock's map behind a door a player can lock."""

    def test_dungeon_items_reachable_after_generation(self):
        argv = ['--door_shuffle', 'crossed', '--intensity', '2', '--dungeon_shuffle_algorithm', 'experimental',
                '--key_logic_algorithm', 'experimental', '--suppress_rom', '--spoiler', 'none', '--seed', '120']
        logging.disable(logging.WARNING)
        try:
            world = Main.main(parse_cli(argv), seed=120, fish=BabelFish(lang='en'))
        finally:
            logging.disable(logging.NOTSET)
        world.clear_exp_cache()
        state = world.get_all_state()
        state.sweep_for_events()
        unreached = [f'{l.name}: {l.item.name}' for l in world.get_locations()
                     if l.item is not None and (l.item.map or l.item.compass) and not l.can_reach(state)]
        self.assertEqual([], unreached)


if __name__ == '__main__':
    unittest.main()
