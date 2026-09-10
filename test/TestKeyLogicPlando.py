import unittest

from BaseClasses import CollectionState, Entrance
from Items import ItemFactory
from KeyDoorShuffle import apply_custom_key_rules
from source.classes.CustomSettings import CustomSettings
from test.TestBase import build_vanilla_world


def customizer(doors, counting='all'):
    settings = CustomSettings()
    settings.file_source = {'doors': {1: {'key_logic': {'counting': counting, 'doors': doors}}}}
    return settings


def add_start(world, region_name):
    menu = world.get_region('Menu', 1)
    start = Entrance(1, f'Test Start: {region_name}', menu)
    start.connect(world.get_region(region_name, 1))
    menu.exits.append(start)


def can_reach(world, location, items):
    state = CollectionState(world)
    for item in ItemFactory(items, 1):
        item.advancement = True
        state.collect(item)
    return world.get_location(location, 1).can_reach(state)


# GT Hookshot ES: analyzed 8, two drops before it
MAP_CHEST = 'Ganons Tower - Map Chest'
MAP_CHEST_ITEMS = ['Hammer', 'Moon Pearl', 'Hookshot']
GT_KEY = 'Small Key (Ganons Tower)'
# chest counting needs every GT key door listed
GT_DOORS = {'GT Torch EN': 0, 'GT Tile Room EN': 4, 'GT Hookshot ES': 4, 'GT Double Switch EN': 2,
            'GT Firesnake Room SW': 4, 'GT Conveyor Star Pits EN': 4, 'GT Mini Helmasaur Room WN': 3,
            'GT Crystal Circles SW': 4}


def gt_doors(**overrides):
    doors = dict(GT_DOORS)
    doors.update(overrides)
    return doors


class TestKeyLogicPlando(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = build_vanilla_world()
        add_start(cls.base, 'Ganons Tower Portal')
        cls.plando = build_vanilla_world(customizer=customizer({'GT Hookshot ES': 4}))
        add_start(cls.plando, 'Ganons Tower Portal')
        cls.chests = build_vanilla_world(customizer=customizer(gt_doors(), 'chests'))
        add_start(cls.chests, 'Ganons Tower Portal')

    def test_lowered_door_number_is_used(self):
        rule = self.plando.key_logic[1]['Ganons Tower'].door_rules['GT Hookshot ES']
        self.assertEqual(rule.small_key_num, 4)
        self.assertEqual(rule.opposite.small_key_num, 4)
        self.assertFalse(can_reach(self.base, MAP_CHEST, MAP_CHEST_ITEMS + [GT_KEY] * 2))
        self.assertFalse(can_reach(self.plando, MAP_CHEST, MAP_CHEST_ITEMS + [GT_KEY] * 1))
        self.assertTrue(can_reach(self.plando, MAP_CHEST, MAP_CHEST_ITEMS + [GT_KEY] * 2))

    def test_chest_counting_ignores_drops(self):
        self.assertTrue(self.chests.key_logic[1]['Ganons Tower'].chest_counting)
        self.assertFalse(can_reach(self.chests, MAP_CHEST, MAP_CHEST_ITEMS + [GT_KEY] * 3))
        self.assertTrue(can_reach(self.chests, MAP_CHEST, MAP_CHEST_ITEMS + [GT_KEY] * 4))

    def test_lowering_keeps_alternatives_one_below(self):
        rule = self.chests.key_logic[1]['Ganons Tower'].door_rules['GT Hookshot ES']
        alternatives = {k: v for k, v in rule.new_rules.items() if k != 0}
        self.assertEqual(len(alternatives), 2)
        self.assertTrue(all(v == 3 for v in alternatives.values()))
        self.assertEqual(rule.alternate_small_key, 3)

    def test_explicit_conditionals(self):
        hookshot = {'keys': 4, 'big_key_in': [MAP_CHEST], 'with_big_key': 2,
                    'small_key_in': MAP_CHEST, 'with_small_key': 3}
        world = build_vanilla_world(customizer=customizer(gt_doors(**{'GT Hookshot ES': hookshot}), 'chests'))
        add_start(world, 'Ganons Tower Portal')
        spot = world.get_location(MAP_CHEST, 1)
        self.assertFalse(can_reach(world, MAP_CHEST, MAP_CHEST_ITEMS + [GT_KEY] * 3))
        spot.item = ItemFactory('Small Key (Ganons Tower)', 1)
        self.assertTrue(can_reach(world, MAP_CHEST, MAP_CHEST_ITEMS + [GT_KEY] * 3))
        self.assertFalse(can_reach(world, MAP_CHEST, MAP_CHEST_ITEMS + [GT_KEY] * 2))
        spot.item = ItemFactory('Big Key (Ganons Tower)', 1)
        self.assertTrue(can_reach(world, MAP_CHEST, MAP_CHEST_ITEMS + [GT_KEY] * 2))
        self.assertFalse(can_reach(world, MAP_CHEST, MAP_CHEST_ITEMS + [GT_KEY] * 1))

    def test_naming_the_paired_side_applies_to_both(self):
        world = build_vanilla_world(customizer=customizer({'GT Map Room WS': 4}))
        add_start(world, 'Ganons Tower Portal')
        self.assertEqual(world.key_logic[1]['Ganons Tower'].door_rules['GT Hookshot ES'].small_key_num, 4)
        self.assertTrue(can_reach(world, MAP_CHEST, MAP_CHEST_ITEMS + [GT_KEY] * 2))

    def test_each_side_can_differ_when_both_are_listed(self):
        world = self.base
        world.customizer = customizer({'PoD Middle Cage N': 2, 'PoD Pit Room S': 5})
        try:
            apply_custom_key_rules(world, 1)
            rules = world.key_logic[1]['Palace of Darkness'].door_rules
            self.assertEqual(rules['PoD Middle Cage N'].small_key_num, 2)
            self.assertEqual(rules['PoD Pit Room S'].small_key_num, 5)
        finally:
            world.customizer = None

    def test_unlisted_pair_side_keeps_its_own_minimum(self):
        world = self.base
        world.customizer = customizer({'Sewers Secret Room Key Door S': 1})
        try:
            apply_custom_key_rules(world, 1)
            rules = world.key_logic[1]['Hyrule Castle'].door_rules
            self.assertEqual(rules['Sewers Secret Room Key Door S'].small_key_num, 1)
            # floor is 2 (behind Dark Cross)
            self.assertEqual(rules['Sewers Key Rat NE'].small_key_num, 2)
        finally:
            world.customizer = None

    def test_invalid_numbers_and_doors_are_rejected(self):
        world = self.base
        for bad, counting, message in [({'GT Hookshot ES': 0}, 'all', 'fewer than 1'),
                                       ({'GT Hookshot ES': 9}, 'all', 'only has 8'),
                                       (gt_doors(**{'GT Hookshot ES': 5}), 'chests', 'only has 4'),
                                       ({'GT Hookshot ES': 4}, 'chests', 'every key door'),
                                       ({'GT Hope Room EN': 1}, 'all', 'not a small key door')]:
            world.customizer = customizer(bad, counting)
            try:
                with self.assertRaisesRegex(Exception, message):
                    apply_custom_key_rules(world, 1)
            finally:
                world.customizer = None
        for bad in [{'GT Hookshot ES': 'four'}, {'GT Hookshot ES': {'keys': 4, 'with_big_key': 5}},
                    {'GT Hookshot ES': {'big_key_in': [MAP_CHEST]}}]:
            with self.assertRaises(Exception):
                customizer(bad).get_key_logic(1)
        with self.assertRaisesRegex(Exception, 'counting'):
            customizer({'GT Hookshot ES': 4}, 'drops').get_key_logic(1)

    def test_export_records_every_door_side(self):
        settings = CustomSettings()
        settings.player_range = range(1, 2)
        settings.record_doors(self.chests)
        exported = settings.world_rep['doors'][1]['key_logic']
        self.assertEqual(exported['counting'], 'chests')
        self.assertEqual(exported['doors']['GT Hookshot ES'], 4)
        self.assertEqual(exported['doors']['GT Map Room WS'], 4)
        self.assertEqual(exported['doors']['PoD Middle Cage N'], 1)
        self.assertEqual(exported['doors']['PoD Pit Room S'], 6)
        self.assertNotIn('Mire Hub Upper Blue Barrier', exported['doors'])


if __name__ == '__main__':
    unittest.main()
