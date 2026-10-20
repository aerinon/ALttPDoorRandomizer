import logging
import unittest

import Main
from CLI import parse_cli
from source.classes.BabelFish import BabelFish


class Stop(Exception):
    pass


class TestKeyPlacementRecheck(unittest.TestCase):
    """Placing a small key turns a held key into one at a location; the worst case can spend held keys before the
    player reaches a placed one, so the key's dungeon may guarantee less, and so may everything reached through it,
    exits included. A placement must leave everything already placed reachable."""

    def test_placement_keeps_items_reached_through_the_dungeon(self):
        # crossed, keysanity, key drops, standard: Turtle Rock's key placed in its own big chest cut off TR Lazy Eyes'
        # exit, and with it the Ocarina already placed at Mimic Cave (then Misery Mire, Desert's key, Desert's prize)
        seed, args = 718287944, ['--door_shuffle', 'crossed', '--intensity', '1', '--shuffle', 'vanilla',
                                 '--keydropshuffle', '--keysanity', '--mode', 'standard',
                                 '--dungeon_shuffle_algorithm', 'experimental', '--key_logic_algorithm', 'experimental']
        original = Main.find_keylock

        def stop(key_layout, world, player):
            raise Stop()  # reached only once the beatable check has passed

        Main.find_keylock = stop
        logging.disable(logging.WARNING)
        try:
            Main.main(parse_cli(args + ['--suppress_rom', '--spoiler', 'none', '--seed', str(seed)]),
                      seed=seed, fish=BabelFish(lang='en'))
            self.fail('generation finished without reaching the keylock check')
        except Stop:
            pass
        finally:
            Main.find_keylock = original
            logging.disable(logging.NOTSET)

    def generates_without_keylock(self, seed, args):
        logging.disable(logging.WARNING)
        try:
            Main.main(parse_cli(args + ['--dungeon_shuffle_algorithm', 'experimental', '--key_logic_algorithm',
                                        'experimental', '--suppress_rom', '--spoiler', 'none', '--seed', str(seed)]),
                      seed=seed, fish=BabelFish(lang='en'))
        finally:
            logging.disable(logging.NOTSET)

    def test_big_key_sealed_in_its_big_chest_costs_only_the_chest(self):
        # basic, shopsanity, inverted: Misery Mire's big key went into its own big chest, and without it two key drops,
        # then the Compass and Map chests, were cut off
        self.generates_without_keylock(44524506, ['--door_shuffle', 'basic', '--intensity', '1', '--shuffle', 'vanilla',
                                                  '--shopsanity', '--mode', 'inverted'])

    def test_swapped_out_item_is_placed_without_itself(self):
        # crossed i3, chaos door types, key drops and pot keys: fill's swap fallback moved Desert Palace's big key with
        # it still held, behind its own big key door
        self.generates_without_keylock(237, ['--door_shuffle', 'crossed', '--intensity', '3', '--door_type_mode', 'all',
                                             '--door_type_distribution', 'chaos', '--keydropshuffle', '--pottery', 'keys'])


if __name__ == '__main__':
    unittest.main()
