import logging
import unittest

import Fill
import Main
from CLI import parse_cli
from source.classes.BabelFish import BabelFish


class Stop(Exception):
    pass


class TestKeyRulesCoverLayout(unittest.TestCase):
    """Every region of a dungeon's key-door states carries the key access rule, including regions only a prize lobby
    reaches: the traversal never stands in such a region unless the dungeon's key logic guarantees it."""

    def test_reached_regions_are_guaranteed(self):
        # vanilla doors, full entrance shuffle, keysanity: Skull 3 is a prize lobby and alone reaches Skull's boss
        seed, args = 19, ['--door_shuffle', 'vanilla', '--shuffle', 'full', '--keyshuffle', 'wild',
                          '--key_logic_algorithm', 'experimental']
        unguaranteed = set()
        original_verify, original_check = Fill.verify_spot_to_fill_v2, Main.find_keylock

        def verify(location, item, state, *rest):
            if state.stale[1]:
                state.update_reachable_regions(1)
            rrp = state.reachable_regions[1]
            for name, logic in state.world.key_logic[1].items():
                new_logic = logic.new_logic
                if new_logic is None or new_logic.fast_logic or not new_logic.key_spheres.get(0):
                    continue
                regions, _ = new_logic.query_reachability(state, logic, 1)
                unguaranteed.update(f'{name}: {r.name}' for r in new_logic.layout_regions if r in rrp and r not in regions)
            return original_verify(location, item, state, *rest)

        def stop(key_layout, world, player):
            raise Stop()

        Fill.verify_spot_to_fill_v2 = verify
        Main.find_keylock = stop
        logging.disable(logging.WARNING)
        try:
            Main.main(parse_cli(args + ['--suppress_rom', '--spoiler', 'none', '--seed', str(seed)]),
                      seed=seed, fish=BabelFish(lang='en'))
            self.fail('generation finished without reaching the keylock check')
        except Stop:
            pass
        finally:
            Fill.verify_spot_to_fill_v2, Main.find_keylock = original_verify, original_check
            logging.disable(logging.NOTSET)
        self.assertEqual([], sorted(unguaranteed))


if __name__ == '__main__':
    unittest.main()
