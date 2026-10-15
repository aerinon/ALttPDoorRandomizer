import unittest

import RaceRandom as random
from Bosses import place_boss
from source.enemizer.Bossmizer import boss_adjust
from source.enemizer.Enemizer import randomize_enemies
from source.enemizer.SpriteSheets import did, required_boss_sheets
from source.dungeon.EnemyList import EnemySprite
from source.rom.DataTables import init_data_tables
from test.TestBase import build_vanilla_world


class TestBossSheets(unittest.TestCase):
    def test_moved_boss_keeps_its_sheet(self):
        # Helmasaur in GT middle, with its sheet's free slots rolled to groups no shuffled enemy uses
        world = build_vanilla_world()
        world.enemy_shuffle[1] = 'shuffled'
        random.seed(1)
        data_tables = world.data_tables[1] = init_data_tables(world, 1)
        place_boss('Helmasaur King', 'middle', 'Ganons Tower', 'Ganons Tower (middle)', world, 1)
        boss_adjust(world, 1)
        sheet = data_tables.sprite_sheets[did(required_boss_sheets[EnemySprite.HelmasaurKing])]
        sheet.add_sprite_to_sheet([0x15, 0x23, None, None])
        randomize_enemies(world, 1)
        self.assertEqual(data_tables.room_headers[0x6c].sprite_sheet + 0x40, sheet.id)


if __name__ == '__main__':
    unittest.main()
