import unittest

from source.classes.CustomSettings import CustomSettings
from source.dungeon.EnemyList import EnemySprite, SpriteType, Sprite, variant_sprites
from source.enemizer.Enemizer import randomize_enemies, split_custom_sub_types
from source.enemizer.EnemyLogic import enemy_vulnerability
from source.rom.DataTables import init_data_tables
from test.TestBase import build_vanilla_world

BEETLE_ROOM = 0x17  # Hera 5F: vanilla hardhat beetles in slots 3, 4, 6, 7 and 8


def uw_sprites(data_tables, kinds):
    return [s for sprites in data_tables.uw_enemy_table.room_map.values() for s in sprites if s.kind in kinds]


class TestEnemyVariants(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.world = build_vanilla_world()

    def test_vanilla_sub_type_keeps_the_x_parity_variant(self):
        sprites = uw_sprites(self.world.data_tables[1], variant_sprites)
        self.assertTrue(sprites)
        for s in sprites:
            self.assertEqual(s.sub_type, s.tile_x & 1, f'{s} room {hex(s.super_tile)}')
            self.assertEqual((s.sprite_data()[1] >> 5) & 7, s.tile_x & 1)
        beetles = uw_sprites(self.world.data_tables[1], {EnemySprite.HardhatBeetle})
        self.assertEqual((len(beetles), sum(b.sub_type for b in beetles)), (53, 47))

    def somaria_hits(self, kind, sub_type, tile_x, region):
        sprite = Sprite(BEETLE_ROOM, kind, sub_type, 0, tile_x, 0x10)
        return enemy_vulnerability(self.world, 1, sprite, region)['Somaria']

    def test_health_follows_sub_type_indoors_and_x_parity_outdoors(self):
        indoors = self.world.get_region('Hera 5F', 1)
        outdoors = self.world.get_region('Lumberjack Area', 1)
        self.assertTrue(outdoors.is_outdoors())
        # somaria does 2 damage: beetles take 16 hits at 32 hp and 3 at 6 hp, tektites 4 at 8 hp and 6 at 12 hp
        self.assertEqual(self.somaria_hits(EnemySprite.HardhatBeetle, 0, 0x11, indoors), 16)
        self.assertEqual(self.somaria_hits(EnemySprite.HardhatBeetle, 1, 0x10, indoors), 3)
        self.assertEqual(self.somaria_hits(EnemySprite.HardhatBeetle, 0, 0x11, outdoors), 3)
        self.assertEqual(self.somaria_hits(EnemySprite.HardhatBeetle, 1, 0x10, outdoors), 16)
        self.assertEqual(self.somaria_hits(EnemySprite.Tektite, 0, 0x11, indoors), 4)
        self.assertEqual(self.somaria_hits(EnemySprite.Tektite, 1, 0x10, indoors), 6)

    def test_variant_health_is_written_to_the_variant_tables(self):
        stats = self.world.data_tables[1].enemy_stats
        self.assertEqual(stats[EnemySprite.HardhatBeetle].health, (32, 6))
        self.assertEqual(stats[EnemySprite.Tektite].health, (8, 12))
        self.assertEqual(stats[EnemySprite.Stalfos].health, 4)

    def test_customizer_sub_type_only_on_variant_enemies(self):
        kinds, sub_types = split_custom_sub_types({0x37: {0: {'kind': 'HardhatBeetle', 'sub_type': 1},
                                                          1: 'Wizzrobe'}})
        self.assertEqual(kinds, {0x37: {0: 'HardhatBeetle', 1: 'Wizzrobe'}})
        self.assertEqual(sub_types, {0x37: {0: 1}})
        for bad in ({'kind': 'HardhatBeetle', 'sub_type': 7}, {'kind': 'Wizzrobe', 'sub_type': 1}):
            with self.assertRaises(ValueError):
                split_custom_sub_types({0x37: {0: bad}})


class TestEnemyVariantShuffle(unittest.TestCase):
    def enemize(self, enemy_map=None):
        world = build_vanilla_world()
        world.enemy_shuffle[1] = 'shuffled'
        if enemy_map is not None:
            world.customizer = CustomSettings()
            world.customizer.file_source = {'enemies': {1: enemy_map}}
        world.data_tables[1] = init_data_tables(world, 1)
        randomize_enemies(world, 1)
        return world

    def test_shuffled_slots_hold_valid_sub_types(self):
        data_tables = self.enemize().data_tables[1]
        shuffled = [s for sprites in data_tables.uw_enemy_table.room_map.values() for s in sprites if s.shuffled]
        self.assertTrue(shuffled)
        for s in shuffled:
            if s.kind in variant_sprites:
                self.assertIn(s.sub_type, (0, 1))
        # a vanilla beetle slot that became something else drops the beetle's variant bit
        vanilla = build_vanilla_world().data_tables[1].uw_enemy_table.room_map
        for room, sprites in data_tables.uw_enemy_table.room_map.items():
            for i, s in enumerate(sprites):
                was_variant = vanilla[room][i].kind in variant_sprites
                if s.shuffled and was_variant and s.kind not in variant_sprites \
                        and s.sub_type != SpriteType.Overlord:
                    self.assertEqual(s.sub_type, 0, f'{s} room {hex(room)} slot {i}')

    def test_pinned_sub_type_is_used(self):
        world = self.enemize({'Underworld': {BEETLE_ROOM: {3: {'kind': 'HardhatBeetle', 'sub_type': 0},
                                                           4: {'kind': 'HardhatBeetle', 'sub_type': 1},
                                                           6: {'kind': 'Stalfos', 'sub_type': 1}}}})
        sprites = world.data_tables[1].uw_enemy_table.room_map[BEETLE_ROOM]
        self.assertEqual(sprites[3].tile_x & 1, 1)  # vanilla variant was 1, the pin overrides it
        self.assertEqual((sprites[3].kind, sprites[3].sub_type), (EnemySprite.HardhatBeetle, 0))
        self.assertEqual((sprites[4].kind, sprites[4].sub_type), (EnemySprite.HardhatBeetle, 1))
        self.assertEqual((sprites[6].kind, sprites[6].sub_type), (EnemySprite.Stalfos, 1))

    def test_spoiler_names_the_sub_type(self):
        world = self.enemize({'Underworld': {BEETLE_ROOM: {3: {'kind': 'HardhatBeetle', 'sub_type': 1}}}})
        sprites = world.data_tables[1].uw_enemy_table.room_map[BEETLE_ROOM]
        self.assertEqual(sprites[3].describe_uw(), 'HardhatBeetle (sub_type 1)')
        self.assertEqual(Sprite(BEETLE_ROOM, EnemySprite.Wizzrobe, 1, 0, 0x10, 0x10).describe_uw(), 'Wizzrobe')

if __name__ == '__main__':
    unittest.main()
