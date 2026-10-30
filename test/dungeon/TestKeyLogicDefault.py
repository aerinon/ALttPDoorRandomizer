import unittest

from BaseClasses import World
from CLI import parse_cli
from Main import set_world_options
from source.classes.BabelFish import BabelFish


def key_logic(*argv):
    args = parse_cli(['--suppress_rom', '--spoiler', 'none', *argv])
    world = World(args.multi, args.shuffle, args.door_shuffle, args.logic, args.mode, args.swords,
                  args.difficulty, args.item_functionality, args.timer, args.progressive, args.goal, args.algorithm,
                  args.accessibility, args.shuffleganon, args.custom, args.customitemarray, args.hints, args.spoiler)
    set_world_options(world, args, BabelFish(lang='en'))
    return world.key_logic_algorithm[1]


class TestKeyLogicDefault(unittest.TestCase):
    """The new dungeon algorithms run experimental key logic unless strict or static is asked for."""

    def test_new_algorithms_replace_partial_and_dangerous(self):
        for algorithm in ('experimental', 'biased'):
            for requested in (None, 'partial', 'dangerous'):
                with self.subTest(algorithm=algorithm, requested=requested):
                    extra = ['--key_logic_algorithm', requested] if requested else []
                    self.assertEqual('experimental', key_logic('--dungeon_shuffle_algorithm', algorithm, *extra))

    def test_new_algorithms_keep_strict_and_static(self):
        for requested in ('strict', 'static'):
            with self.subTest(requested=requested):
                self.assertEqual(requested, key_logic('--dungeon_shuffle_algorithm', 'experimental',
                                                      '--key_logic_algorithm', requested))

    def test_classic_keeps_the_requested_key_logic(self):
        self.assertEqual('partial', key_logic())
        self.assertEqual('dangerous', key_logic('--key_logic_algorithm', 'dangerous'))


if __name__ == '__main__':
    unittest.main()
