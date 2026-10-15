import logging
import unittest

import Main
from CLI import parse_cli
from source.classes.BabelFish import BabelFish

EXPERIMENTAL = ['--dungeon_shuffle_algorithm', 'experimental', '--key_logic_algorithm', 'experimental']


class Stop(Exception):
    pass


class TestPrizeRelevantSpheres(unittest.TestCase):
    """A dungeon with a prize and a portal at Ganons Tower or the Pyramid Fairy keys its counters by whether the prize
    is in hand. The key logic's sphere graph (prize lobby closed; futures cover it open) must find those counters behind
    every small key door, or the rooms beyond them are missing from the logic and their keys go unseen."""

    def test_spheres_cover_every_counter(self):
        # basic doors, full entrance shuffle: Turtle Rock's Eye Bridge portal is at the Pyramid Fairy
        seed, args = 918699756, ['--door_shuffle', 'basic', '--intensity', '3', '--shuffle', 'full']
        original = Main.find_keylock

        def stop(key_layout, world, player):
            raise Stop(world)

        Main.find_keylock = stop
        logging.disable(logging.WARNING)
        try:
            Main.main(parse_cli(args + EXPERIMENTAL + ['--suppress_rom', '--spoiler', 'none', '--seed', str(seed)]),
                      seed=seed, fish=BabelFish(lang='en'))
            self.fail('generation finished without reaching the keylock check')
        except Stop as s:
            world = s.args[0]
        finally:
            Main.find_keylock = original
            logging.disable(logging.NOTSET)
        key_layout = world.key_layout[1]['Turtle Rock']
        self.assertTrue(key_layout.prize_relevant)
        counted = {loc for counter in key_layout.key_counters.values() if not counter.prize_doors_opened
                   for loc in set(counter.free_locations) | set(counter.key_only_locations) | set(counter.other_locations)}
        _, sphered = world.key_logic[1]['Turtle Rock'].new_logic.get_relevant_regions_and_locations()
        self.assertEqual([], sorted(loc.name for loc in counted - set(sphered)))


if __name__ == '__main__':
    unittest.main()
