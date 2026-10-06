import unittest

from BaseClasses import Entrance, Region, RegionType
from Rules import zelda_delivery_rule


class StubWorld:
    def __init__(self, regions):
        self.regions = {r.name: r for r in regions}

    def get_region(self, name, player):
        return self.regions[name]


class StubState:
    def __init__(self, items):
        self.items = set(items)

    def has(self, item, player):
        return item in self.items


def connect(parent, child, rule=None):
    ext = Entrance(1, f'{parent.name} -> {child.name}', parent)
    if rule:
        ext.access_rule = rule
    parent.exits.append(ext)
    ext.connect(child)
    return ext


class TestZeldaDelivery(unittest.TestCase):
    """Zelda can be delivered by any route from the Cellblock to the Throne Room, not only the shortest one."""

    def setUp(self):
        names = ['Hyrule Dungeon Cellblock', 'Short', 'Long 1', 'Long 2', 'Hyrule Castle Throne Room']
        self.r = {n: Region(n, RegionType.Dungeon, None, 1) for n in names}
        r = self.r
        connect(r['Hyrule Dungeon Cellblock'], r['Short'])
        self.short_exit = connect(r['Short'], r['Hyrule Castle Throne Room'], lambda state: False)
        connect(r['Hyrule Dungeon Cellblock'], r['Long 1'])
        connect(r['Long 1'], r['Long 2'], lambda state: state.has('Lamp', 1))
        connect(r['Long 2'], r['Hyrule Castle Throne Room'])
        self.world = StubWorld(r.values())

    def test_longer_open_route_delivers(self):
        # the shortest route crosses a connection that never opens, as ranged-switch connections in crossed can
        rule = zelda_delivery_rule(self.world, 1)
        self.assertTrue(rule(StubState(['Zelda Herself', 'Lamp'])))

    def test_no_open_route(self):
        rule = zelda_delivery_rule(self.world, 1)
        self.assertFalse(rule(StubState(['Zelda Herself'])))

    def test_needs_zelda(self):
        rule = zelda_delivery_rule(self.world, 1)
        self.assertFalse(rule(StubState(['Lamp'])))

    def test_rules_read_when_evaluated(self):
        # rules added after setup, such as key door rules, still count
        rule = zelda_delivery_rule(self.world, 1)
        self.short_exit.access_rule = lambda state: True
        self.assertTrue(rule(StubState(['Zelda Herself'])))

    def test_no_route_at_all(self):
        self.r['Long 2'].exits.clear()
        self.r['Short'].exits.clear()
        with self.assertRaises(Exception):
            zelda_delivery_rule(self.world, 1)


if __name__ == '__main__':
    unittest.main()
