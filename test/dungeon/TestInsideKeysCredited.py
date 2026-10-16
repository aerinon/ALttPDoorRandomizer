import logging
import unittest

import BaseClasses
import Main
from CLI import parse_cli
from source.classes.BabelFish import BabelFish

EXPERIMENTAL = ['--dungeon_shuffle_algorithm', 'experimental', '--key_logic_algorithm', 'experimental']


class Stop(Exception):
    pass


class TestInsideKeysCredited(unittest.TestCase):
    """A small key found inside its dungeon is credited where it lies, in every key-door order, never as held from the
    start: a careless player may waste the keys they have before reaching it."""

    def test_collected_inside_keys_stay_at_their_spots(self):
        # basic doors, full entrance shuffle: Turtle Rock's prize lobby alone reaches Eye Bridge, the Boss and the
        # Big Chest, outside the logic's main sphere graph
        seed, args = 75, ['--door_shuffle', 'basic', '--intensity', '3', '--shuffle', 'full']
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

        world.clear_exp_cache()
        state = BaseClasses.CollectionState(world)
        pending = [loc for loc in world.get_locations() if loc.item is not None]
        reached = [loc for loc in pending if loc.can_reach(state) and state.not_flooding_a_key(world, loc)]
        while reached:
            for loc in reached:
                pending.remove(loc)
                state.collect(loc.item, True, loc)
            reached = [loc for loc in pending if loc.can_reach(state) and state.not_flooding_a_key(world, loc)]

        logic = world.key_logic[1]['Turtle Rock']
        inside = [loc for loc in world.get_locations() if loc.parent_region.dungeon is not None
                  and loc.parent_region.dungeon.name == 'Turtle Rock' and loc.item is not None
                  and loc.item.name == logic.small_key_name]
        collected = [loc for loc in inside if loc in state.locations_checked]
        self.assertGreater(len(collected), 0)
        (in_hand, _, spots, _, _), _, _ = logic.new_logic.build_cache_key(state, logic, 1)
        self.assertEqual(state.prog_items[logic.small_key_name, 1] - len(collected), in_hand)
        self.assertEqual(sorted(loc.name for loc in inside), sorted(spots))


if __name__ == '__main__':
    unittest.main()
