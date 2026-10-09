import logging
import unittest

import BaseClasses
import Main
from CLI import parse_cli
from source.classes.BabelFish import BabelFish

EXPERIMENTAL = ['--dungeon_shuffle_algorithm', 'experimental', '--key_logic_algorithm', 'experimental']


class Stop(Exception):
    pass


def generate(seed, args):
    """Generate through fill, stopping before money balancing."""
    original = Main.balance_money_progression

    def stop(world):
        raise Stop(world)

    Main.balance_money_progression = stop
    logging.disable(logging.WARNING)
    try:
        Main.main(parse_cli(args + EXPERIMENTAL + ['--suppress_rom', '--spoiler', 'none', '--seed', str(seed)]),
                  seed=seed, fish=BabelFish(lang='en'))
    except Stop as s:
        return s.args[0]
    finally:
        Main.balance_money_progression = original
        logging.disable(logging.NOTSET)
    raise AssertionError('generation finished without reaching money balancing')


def exhaustive_dungeons(world):
    return {name: logic for name, logic in world.key_logic[1].items()
            if logic.new_logic is not None and not logic.new_logic.fast_logic and logic.new_logic.key_spheres.get(0)}


class TestKeyLogicMonotone(unittest.TestCase):
    """What the experimental key logic guarantees must only grow as the player gains things, whatever order a sweep
    collects them in: a big key from outside the dungeon, or another lobby opening, gives a careless player more ways to
    waste keys, so the guarantee is the meet over every future the player can grow into."""

    def sweep_one_at_a_time(self, world, check):
        state = BaseClasses.CollectionState(world)
        pending = [loc for loc in world.get_locations() if loc.item is not None]
        steps = 0
        while True:
            state.update_reachable_regions(1)
            check(state)
            reachable = [loc for loc in pending if loc.can_reach(state)]
            # big keys first: holding one early gives a careless player the most ways to waste keys
            spot = next((loc for loc in reachable if loc.item.bigkey), reachable[0] if reachable else None)
            if spot is None:
                return steps
            pending.remove(spot)
            state.collect(spot.item, True, spot)
            steps += 1

    def assert_monotone(self, seed, args):
        world = generate(seed, args)
        dungeons = exhaustive_dungeons(world)
        seen = {name: set() for name in dungeons}
        shrinks = []

        def check(state):
            for name, logic in dungeons.items():
                _, locations = logic.new_logic.query_reachability(state, logic, 1)
                lost = {loc for loc in seen[name] - locations if loc not in state.locations_checked}
                if lost:
                    shrinks.append((name, sorted(loc.name for loc in lost)))
                seen[name] |= locations

        steps = self.sweep_one_at_a_time(world, check)
        self.assertGreater(steps, 50)
        self.assertEqual([], shrinks)

    def test_big_key_from_outside(self):
        # Palace of Darkness has one lobby, so only the big key can shrink it
        self.assert_monotone(415, ['--door_shuffle', 'basic', '--intensity', '1', '--keysanity', '--keydropshuffle',
                                   '--mode', 'standard'])

    def test_lobbies_opening(self):
        self.assert_monotone(406, ['--door_shuffle', 'vanilla', '--mode', 'inverted'])  # Turtle Rock big key chest

    def test_reachability_update_reaches_a_fixed_point(self):
        """After an update, no blocked connection from a reached region passes: an entrance key logic refused before
        another lobby was reached is tried again in the same update."""
        world = generate(401, ['--door_shuffle', 'basic', '--intensity', '2'])  # Desert Palace

        def check(state):
            rrp = state.reachable_regions[1]
            passable = [conn.name for conn in state.blocked_connections[1]
                        if conn.parent_region in rrp and conn.connected_region not in rrp and conn.can_reach(state)]
            self.assertEqual([], passable)

        self.sweep_one_at_a_time(world, check)


class TestBigKeysObtainable(unittest.TestCase):
    """An unplaced big key may come later, so it counts toward waste but never toward progress: counting it as held
    let fill put Ganons Tower's big key on a spot reachable only with that big key (seed 703, keysanity standard)."""

    def test_every_placed_big_key_is_collected(self):
        world = generate(703, ['--door_shuffle', 'basic', '--intensity', '1', '--keysanity', '--keydropshuffle',
                               '--mode', 'standard'])
        state = BaseClasses.CollectionState(world)
        pending = [loc for loc in world.get_locations() if loc.item is not None]
        sphere = [loc for loc in pending if loc.can_reach(state) and state.not_flooding_a_key(world, loc)]
        while sphere:
            for loc in sphere:
                pending.remove(loc)
                state.collect(loc.item, True, loc)
            sphere = [loc for loc in pending if loc.can_reach(state) and state.not_flooding_a_key(world, loc)]
        self.assertEqual([], [f'{loc.name}: {loc.item.name}' for loc in pending if loc.item.bigkey])


class TestLobbySubsetCredit(unittest.TestCase):
    """Keys in a section whose lobby isn't open yet aren't credited. Vanilla doors, seed 1: once the Map Guard key is
    collected but before the Sewers Rat Path drop can be entered, crediting the Rat Path section's keys would open
    Sewers Dark Cross Key Door N with a key the player could spend elsewhere."""

    def test_rat_path_keys_not_credited_early(self):
        world = generate(1, ['--door_shuffle', 'vanilla'])
        state = BaseClasses.CollectionState(world)
        map_guard = world.get_location('Hyrule Castle - Map Guard Key Drop', 1)
        while map_guard not in state.locations_checked:
            sphere = [loc for loc in world.get_locations()
                      if loc.item is not None and loc not in state.locations_checked and loc.can_reach(state)]
            self.assertTrue(sphere, 'Map Guard key drop never reached')
            for loc in sphere:
                state.collect(loc.item, True, loc)
        state.update_reachable_regions(1)
        self.assertNotIn(world.get_region('Sewers Rat Path', 1), state.reachable_regions[1])
        self.assertFalse(world.get_entrance('Sewers Dark Cross Key Door N', 1).can_reach(state))


if __name__ == '__main__':
    unittest.main()
