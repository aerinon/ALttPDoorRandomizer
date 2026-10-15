import logging
import unittest

import BaseClasses
import Fill
import Main
from CLI import parse_cli
from source.classes.BabelFish import BabelFish

EXPERIMENTAL = ['--dungeon_shuffle_algorithm', 'experimental', '--key_logic_algorithm', 'experimental']


class Stop(Exception):
    pass


class TestSetReachability(unittest.TestCase):
    """Experimental key logic guarantees sets: a region reached by one key-door route or another, where neither
    route's first room is guaranteed on its own. Such a region must still be reachable, as long as items allow it."""

    def test_guaranteed_regions_are_reached(self):
        # vanilla doors, keysanity: GT's big key room is guaranteed by either of two key-door routes during the fill
        seed, args = 7, ['--door_shuffle', 'vanilla', '--keyshuffle', 'wild', '--bigkeyshuffle']
        gaps, injections = [], [0]
        original_verify, original_inject = Fill.verify_spot_to_fill_v2, BaseClasses.CollectionState.inject_guaranteed_regions
        original_balance = Main.balance_money_progression

        def verify(location, item, state, *rest):
            if state.stale[1]:
                state.update_reachable_regions(1)
            rrp = state.reachable_regions[1]
            for name, logic in state.world.key_logic[1].items():
                if logic.new_logic is None or logic.new_logic.fast_logic or not logic.new_logic.key_spheres.get(0):
                    continue
                regions, _ = logic.new_logic.query_reachability(state, logic, 1)
                missing = [r for r in regions if r not in rrp]
                if missing:
                    walked = state.reach_with_keys(logic, 1)
                    gaps.extend(f'{item.name} @ {location.name}: {r.name}' for r in missing if r in walked)
            return original_verify(location, item, state, *rest)

        def inject(state, player):
            result = original_inject(state, player)
            injections[0] += bool(result)
            return result

        def stop(world):
            raise Stop(world)

        Fill.verify_spot_to_fill_v2 = verify
        BaseClasses.CollectionState.inject_guaranteed_regions = inject
        Main.balance_money_progression = stop
        logging.disable(logging.WARNING)
        try:
            Main.main(parse_cli(args + EXPERIMENTAL + ['--suppress_rom', '--spoiler', 'none', '--seed', str(seed)]),
                      seed=seed, fish=BabelFish(lang='en'))
            self.fail('generation finished without reaching money balancing')
        except Stop:
            pass
        finally:
            Fill.verify_spot_to_fill_v2 = original_verify
            BaseClasses.CollectionState.inject_guaranteed_regions = original_inject
            Main.balance_money_progression = original_balance
            logging.disable(logging.NOTSET)
        self.assertEqual([], gaps)
        self.assertGreater(injections[0], 0)


if __name__ == '__main__':
    unittest.main()
