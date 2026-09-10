import unittest

from BaseClasses import CollectionState, Entrance
from Items import ItemFactory
from test.TestBase import build_vanilla_world

KEYS = {'Ganons Tower': 'Small Key (Ganons Tower)', 'Hyrule Castle': 'Small Key (Escape)',
        'Turtle Rock': 'Small Key (Turtle Rock)', 'Palace of Darkness': 'Small Key (Palace of Darkness)',
        'Ice Palace': 'Small Key (Ice Palace)', 'Misery Mire': 'Small Key (Misery Mire)'}


class TestStaticKeyLogic(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.world = build_vanilla_world(key_logic='static')
        menu = cls.world.get_region('Menu', 1)
        for name in ['Ganons Tower Portal', 'Hyrule Castle South Portal', 'Turtle Rock Main Portal',
                     'Palace of Darkness Portal', 'Ice Portal', 'Mire Portal']:
            start = Entrance(1, f'Test Start: {name}', menu)
            start.connect(cls.world.get_region(name, 1))
            menu.exits.append(start)
        cls.items = sorted({i.name for i in cls.world.itempool if (i.advancement or i.bigkey) and not i.smallkey})

    def state(self, dungeon, keys, without=()):
        state = CollectionState(self.world)
        names = [n for n in self.items if n not in without] + [KEYS[dungeon]] * keys
        for item in ItemFactory(names, 1):
            item.advancement = True
            state.collect(item)
        return state

    def min_keys(self, location, dungeon, without=()):
        for keys in range(0, 7):
            if self.world.get_location(location, 1).can_reach(self.state(dungeon, keys, without)):
                return keys
        return None

    def place(self, location, item):
        self.world.get_location(location, 1).item = ItemFactory(item, 1) if item else None

    def test_ganons_tower_chest_rules(self):
        gt = 'Ganons Tower'
        self.assertEqual(self.min_keys('Ganons Tower - Map Chest', gt), 4)
        self.assertEqual(self.min_keys('Ganons Tower - Randomizer Room - Top Left', gt), 4)
        self.assertEqual(self.min_keys('Ganons Tower - Compass Room - Top Left', gt), 4)
        self.assertEqual(self.min_keys('Ganons Tower - Firesnake Room', gt), 3)
        self.assertEqual(self.min_keys("Ganons Tower - Bob's Chest", gt), 3)
        self.assertEqual(self.min_keys('Ganons Tower - Big Key Chest', gt), 3)
        self.assertEqual(self.min_keys('Ganons Tower - Mini Helmasaur Room - Left', gt), 0)
        self.assertEqual(self.min_keys('Ganons Tower - Pre-Moldorm Chest', gt), 3)
        self.assertEqual(self.min_keys('Ganons Tower - Validation Chest', gt), 4)

    def test_ganons_tower_big_key_conditionals(self):
        gt = 'Ganons Tower'
        self.place('Ganons Tower - Randomizer Room - Bottom Right', 'Big Key (Ganons Tower)')
        try:
            self.assertEqual(self.min_keys('Ganons Tower - Randomizer Room - Top Left', gt), 3)
            self.assertEqual(self.min_keys('Ganons Tower - Firesnake Room', gt), 2)
            self.assertEqual(self.min_keys('Ganons Tower - Compass Room - Top Left', gt), 4)
        finally:
            self.place('Ganons Tower - Randomizer Room - Bottom Right', None)
        self.place('Ganons Tower - Map Chest', 'Big Key (Ganons Tower)')
        try:
            self.assertEqual(self.min_keys('Ganons Tower - Map Chest', gt), 3)
        finally:
            self.place('Ganons Tower - Map Chest', None)

    def test_ganons_tower_bottom_always_three_keys(self):
        gt = 'Ganons Tower'
        bottom = ["Ganons Tower - Bob's Chest", 'Ganons Tower - Big Key Chest', 'Ganons Tower - Big Chest',
                  'Ganons Tower - Big Key Room - Left', 'Ganons Tower - Big Key Room - Right']
        for where in bottom + ['Ganons Tower - Randomizer Room - Top Left', 'Ganons Tower - Compass Room - Top Left']:
            self.place(where, 'Big Key (Ganons Tower)')
            try:
                for name in bottom:
                    self.assertEqual(self.min_keys(name, gt), 3, f'{name} with big key at {where}')
            finally:
                self.place(where, None)

    def test_hyrule_castle_open_mode(self):
        self.assertEqual(self.min_keys('Hyrule Castle - Boomerang Chest', 'Hyrule Castle'), 1)
        self.assertEqual(self.min_keys("Hyrule Castle - Zelda's Chest", 'Hyrule Castle'), 1)
        self.assertEqual(self.min_keys('Hyrule Castle - Map Chest', 'Hyrule Castle'), 0)
        self.assertFalse(self.world.get_location('Hyrule Castle - Boomerang Chest', 1).item_rule(ItemFactory('Small Key (Escape)', 1)))

    def test_palace_of_darkness(self):
        pod = 'Palace of Darkness'
        self.assertEqual(self.min_keys('Palace of Darkness - Big Key Chest', pod), 6)
        self.assertEqual(self.min_keys('Palace of Darkness - Compass Chest', pod), 4)
        self.place('Palace of Darkness - Big Key Chest', 'Small Key (Palace of Darkness)')
        try:
            self.assertEqual(self.min_keys('Palace of Darkness - Big Key Chest', pod), 3)
        finally:
            self.place('Palace of Darkness - Big Key Chest', None)

    def test_turtle_rock_front_access(self):
        # vanilla entrances only reach Turtle Rock from the front: Pokey Room 1, North 2, Dark Room Staircase 3
        tr = 'Turtle Rock'
        self.assertEqual(self.min_keys('Turtle Rock - Chain Chomps', tr), 1)
        self.assertEqual(self.min_keys('Turtle Rock - Big Key Chest', tr), 4)
        self.assertEqual(self.min_keys('Turtle Rock - Big Chest', tr), 2)
        self.assertEqual(self.min_keys('Turtle Rock - Crystaroller Room', tr), 2)
        self.assertEqual(self.min_keys('Turtle Rock - Eye Bridge - Top Left', tr), 3)
        self.assertEqual(self.min_keys('Turtle Rock - Boss', tr), 4)
        self.place('Turtle Rock - Big Key Chest', 'Big Key (Turtle Rock)')
        try:
            self.assertEqual(self.min_keys('Turtle Rock - Big Key Chest', tr), 2)
        finally:
            self.place('Turtle Rock - Big Key Chest', None)
        self.assertFalse(self.world.get_location('Turtle Rock - Big Chest', 1).item_rule(ItemFactory('Big Key (Turtle Rock)', 1)))

    def test_kholdstare_somaria_alternative(self):
        ice = 'Ice Palace'
        self.assertEqual(self.min_keys('Ice Palace - Boss', ice), 1)
        self.assertEqual(self.min_keys('Ice Palace - Boss', ice, without=['Cane of Somaria']), 2)

    def test_mire_west_wing(self):
        mire = 'Misery Mire'
        self.assertEqual(self.min_keys('Misery Mire - Compass Chest', mire), 3)
        self.place('Misery Mire - Big Key Chest', 'Big Key (Misery Mire)')
        try:
            self.assertEqual(self.min_keys('Misery Mire - Compass Chest', mire), 2)
        finally:
            self.place('Misery Mire - Big Key Chest', None)

    def test_requires_vanilla_doors(self):
        from source.dungeon.StaticKeyLogic import static_logic_supported
        self.assertTrue(static_logic_supported(self.world, 1))
        self.world.dropshuffle[1] = 'keys'
        try:
            self.assertFalse(static_logic_supported(self.world, 1))
        finally:
            self.world.dropshuffle[1] = 'none'


if __name__ == '__main__':
    unittest.main()
