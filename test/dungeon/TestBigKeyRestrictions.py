import logging
import unittest

import Fill
import Main
from CLI import parse_cli
from source.classes.BabelFish import BabelFish


class Stop(Exception):
    pass


class TestBigKeyRestrictions(unittest.TestCase):
    """The experimental key logic forbids the big key only where it can't go: behind its own doors, or where the key
    door layout has no solution with it there (`valid_bk_placement`). A per-sphere count of locations against key doors
    is no reason to forbid it."""

    def test_big_key_allowed_where_the_layout_is_satisfiable(self):
        # basic doors, inverted: every Ice Palace chest was forbidden to its big key, so its fill had no spot
        seed, args = 44230119, ['--door_shuffle', 'basic', '--intensity', '1', '--mode', 'inverted',
                                '--dungeon_shuffle_algorithm', 'experimental', '--key_logic_algorithm', 'experimental']
        original = Main.fill_dungeons_restrictive

        def stop(world, *rest, **kwargs):
            raise Stop(world)

        Main.fill_dungeons_restrictive = stop
        logging.disable(logging.WARNING)
        try:
            Main.main(parse_cli(args + ['--suppress_rom', '--spoiler', 'none', '--seed', str(seed)]),
                      seed=seed, fish=BabelFish(lang='en'))
            self.fail('generation finished without reaching the dungeon fill')
        except Stop as s:
            world = s.args[0]
        finally:
            Main.fill_dungeons_restrictive = original
            logging.disable(logging.NOTSET)
        logic = world.key_logic[1]['Ice Palace']
        big_key = next(item for dungeon in world.dungeons if dungeon.name == 'Ice Palace' and dungeon.player == 1
                       for item in [dungeon.big_key])
        for name in ['Ice Palace - Compass Chest', 'Ice Palace - Spike Room']:
            location = world.get_location(name, 1)
            self.assertTrue(Fill.valid_bk_placement(location, big_key, world), name)
            self.assertNotIn(location, logic.new_logic.bk_restricted, name)


if __name__ == '__main__':
    unittest.main()
