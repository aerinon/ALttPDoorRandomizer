import unittest

from source.dungeon.EnemyList import EnemySprite
from source.rom.DataTables import init_data_tables
from test.TestBase import build_vanilla_world


class TestEnemyDenials(unittest.TestCase):
    def test_no_terrorpin_under_ice_antechamber_block(self):
        # the right-hand Blue Bari slots by the liftable block: a Terrorpin there clips out of the room
        world = build_vanilla_world()
        denials = init_data_tables(world, 1).uw_enemy_denials
        for slot in (5, 7):
            self.assertIn(EnemySprite.Terrorpin, denials[0xce, slot])


if __name__ == '__main__':
    unittest.main()
