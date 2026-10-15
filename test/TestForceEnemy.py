import unittest

import RaceRandom as random
from Rules import std_kill_rooms, kill_chests, get_challenge_rule
from source.dungeon.EnemyList import EnemySprite
from source.enemizer.Enemizer import randomize_enemies, shutter_sprites
from source.rom.DataTables import init_data_tables
from test.TestBase import build_vanilla_world


class TestForceEnemy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.world = build_vanilla_world()
        cls.world.enemy_shuffle[1] = 'shuffled'

    def enemize(self, forced, seed):
        self.world.force_enemy[1] = forced
        random.seed(seed)
        self.world.data_tables[1] = init_data_tables(self.world, 1)
        randomize_enemies(self.world, 1)
        return self.world.data_tables[1]

    def test_unkillable_force_skips_kill_rooms_and_drops(self):
        for seed in range(1, 4):
            data_tables = self.enemize('Chainchomp', seed)
            room_map = data_tables.uw_enemy_table.room_map
            stats = data_tables.enemy_stats
            for region, (_, _, room_id, enemy_list) in std_kill_rooms.items():
                get_challenge_rule(self.world, 1, room_map, stats, room_id, enemy_list, region)
            for region, (_, room_id, enemy_list) in kill_chests.items():
                get_challenge_rule(self.world, 1, room_map, stats, room_id, enemy_list, region)
            drops = [s for sprites in room_map.values() for s in sprites if s.drops_item]
            self.assertTrue(drops)
            self.assertFalse([s for s in drops if s.kind == EnemySprite.Chainchomp])
            # everywhere else the force still applies
            self.assertTrue(any(s.kind == EnemySprite.Chainchomp for sprites in room_map.values() for s in sprites))

    def test_enemizer_protects_every_logic_kill_slot(self):
        for region, (_, _, room_id, enemy_list) in std_kill_rooms.items():
            self.assertLessEqual(set(enemy_list), shutter_sprites.get(room_id, set()), region)
        for region, (_, room_id, enemy_list) in kill_chests.items():
            self.assertLessEqual(set(enemy_list), shutter_sprites.get(room_id, set()), region)

    def test_insufficient_kill_rules_name_room_and_slot(self):
        data_tables = self.enemize(None, 1)
        room_map = data_tables.uw_enemy_table.room_map
        room_map[0x71][0].kind = EnemySprite.Chainchomp
        _, _, room_id, enemy_list = std_kill_rooms['Hyrule Dungeon Armory Main']
        with self.assertRaisesRegex(Exception, r'Chainchomp \(room 0x71 slot 0, Hyrule Dungeon Armory Main\)'):
            get_challenge_rule(self.world, 1, room_map, data_tables.enemy_stats, room_id, enemy_list,
                               'Hyrule Dungeon Armory Main')

    def test_killable_force_still_fills_kill_rooms(self):
        data_tables = self.enemize('Lynel', 1)
        kinds = [data_tables.uw_enemy_table.room_map[room_id][i].kind
                 for _, (_, _, room_id, enemy_list) in std_kill_rooms.items() for i in enemy_list]
        self.assertIn(EnemySprite.Lynel, kinds)


if __name__ == '__main__':
    unittest.main()
