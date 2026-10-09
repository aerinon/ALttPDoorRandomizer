import unittest
from types import SimpleNamespace

from Fill import keeps_dungeon_guaranteed


class Spot:
    def __init__(self, name, item=None):
        self.name, self.item, self.event = name, item, False


class StubState:
    """Holds the key or not; when the key sits at a spot named for placement, sweeping collects it only if fill has
    marked that spot as an event (as it does once an item is placed)."""

    def __init__(self, key_held=False):
        self.key_held, self.placing_items, self.placing_locations, self.stale = key_held, None, None, {1: False}

    def copy(self):
        return StubState(self.key_held)

    def collect(self, item, event=False, location=None):
        self.key_held = True

    def sweep_for_events(self):
        if self.placing_locations:
            item, spot = self.placing_locations[0]
            self.key_seen_at_event = spot.event


class StubLogic:
    """Guarantees `kept` while the key is held, and `when_placed` once it sits at the candidate spot."""

    def __init__(self, kept, when_placed):
        self.kept, self.when_placed, self.fast_logic = kept, when_placed, False

    def query_reachability(self, state, dungeon_logic, player):
        return set(), set(self.kept if state.key_held and not state.placing_locations else self.when_placed)


def world_with(logic):
    key_logic = SimpleNamespace(new_logic=logic)
    return SimpleNamespace(key_logic_algorithm={1: 'experimental'}, keyshuffle={1: 'wild'},
                           key_logic={1: {'Desert Palace': key_logic}})


class TestKeyPlacementRecheck(unittest.TestCase):
    """Placing a small key turns a held key into one at a location. The worst case can spend held keys before the player
    reaches a placed one, so a placement must not cut off anything already placed in the key's dungeon (seed 918608853
    at c9ffe99e: the Desert key placed at the self-locking Torch spot cut off Ether in the big key chest)."""

    def setUp(self):
        self.key = SimpleNamespace(name='Small Key (Desert Palace)', smallkey=True, player=1, dungeon='Desert Palace')
        self.ether = Spot('Desert Palace - Big Key Chest', item='Ether')
        self.torch = Spot('Desert Palace - Torch')

    def test_placement_that_cuts_off_a_placed_item_is_refused(self):
        logic = StubLogic(kept={self.ether, self.torch}, when_placed={self.torch})
        self.assertFalse(keeps_dungeon_guaranteed(self.torch, self.key, StubState(), world_with(logic)))

    def test_placement_that_keeps_placed_items_is_accepted(self):
        logic = StubLogic(kept={self.ether, self.torch}, when_placed={self.ether, self.torch})
        self.assertTrue(keeps_dungeon_guaranteed(self.torch, self.key, StubState(), world_with(logic)))

    def test_spot_restored_and_counted_as_placed_during_the_check(self):
        logic = StubLogic(kept={self.ether}, when_placed={self.ether})
        seen = []
        original = StubState.sweep_for_events

        def sweep(state):
            if state.placing_locations:
                seen.append((self.torch.item, self.torch.event))
            original(state)

        StubState.sweep_for_events = sweep
        try:
            keeps_dungeon_guaranteed(self.torch, self.key, StubState(), world_with(logic))
        finally:
            StubState.sweep_for_events = original
        self.assertEqual([(self.key, True)], seen)
        self.assertEqual((None, False), (self.torch.item, self.torch.event))


if __name__ == '__main__':
    unittest.main()
