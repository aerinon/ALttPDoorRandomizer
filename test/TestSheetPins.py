import unittest

from source.classes.CustomSettings import CustomSettings
from source.enemizer.Enemizer import randomize_enemies
from source.rom.DataTables import init_data_tables
from test.TestBase import build_vanilla_world

ROOM = 0x4  # TR Crysta-roller: zoro spawners and a crystal switch need sub-groups 1 = 32 and 3 = 83


def enemize(file_source):
    world = build_vanilla_world()
    world.enemy_shuffle[1] = 'shuffled'
    world.customizer = CustomSettings()
    world.customizer.file_source = file_source
    world.data_tables[1] = init_data_tables(world, 1)
    randomize_enemies(world, 1)
    return world.data_tables[1]


class TestSheetPins(unittest.TestCase):
    def test_partial_pin_is_used_and_the_rest_is_chosen(self):
        tables = enemize({'sprite_sheets': {1: {'Underworld': {'sheets': {70: [22, 32, 12, 83]},
                                                               'rooms': {ROOM: 70}},
                                                'Overworld': {'areas': {0x2: 7}}}}})
        self.assertEqual(tables.room_headers[ROOM].sprite_sheet + 0x40, 70)
        self.assertEqual(tables.sprite_sheets[70].sub_groups, [22, 32, 12, 83])
        self.assertEqual(tables.overworld_sprite_sheets[0x2].id, 7)
        self.assertTrue(all(all(s.locked) for n, s in tables.sprite_sheets.items() if 66 <= n < 124))

    def test_pinned_enemies_without_sheets_still_find_a_sheet(self):
        tables = enemize({'enemies': {1: {'Underworld': {ROOM: {0: 'Stalfos'}},
                                          'Bushes': {0x2: 'Hoarder'}}}})
        self.assertEqual(tables.bush_sprite_table[0x2].sprite, 0x17)

    def test_boss_sub_groups_stay(self):
        tables = enemize({'sprite_sheets': {1: {'Underworld': {'sheets': {87: [1, 2, 3, 4]}}}}})
        sheet = tables.sprite_sheets[87]  # Kholdstare's: sub-groups 0 and 3 are the boss's
        self.assertEqual(sheet.sub_groups[1:3], [2, 3])
        self.assertNotEqual(sheet.sub_groups[0], 1)
        self.assertNotEqual(sheet.sub_groups[3], 4)

    def test_bad_sheet_numbers_raise(self):
        for layout in ({'Underworld': {'sheets': {64: [0, 0, 0, 0]}}},
                       {'Underworld': {'sheets': {70: [1, 2, 3]}}},
                       {'Underworld': {'rooms': {ROOM: 12}}},
                       {'Overworld': {'areas': {0x2: 70}}},
                       {'Underworld': {'sheets': {70: [1, 2, 3, 256]}}},
                       {'Underworld': {'rooms': {0x7: 70}}},  # Hera boss room keeps its boss sheet
                       {'Overworld': {'areas': {0x1: 7}}}):
            with self.subTest(layout=layout), self.assertRaises(ValueError):
                enemize({'sprite_sheets': {1: layout}})

    def test_bush_must_fit_the_sheet(self):
        with self.assertRaises(ValueError):
            enemize({'enemies': {1: {'Bushes': {0x2: 'Hinox'}}}})


if __name__ == '__main__':
    unittest.main()
