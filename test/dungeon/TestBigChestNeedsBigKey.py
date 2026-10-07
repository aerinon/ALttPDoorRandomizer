import logging
import unittest

import BaseClasses
import Main
from CLI import parse_cli
from Items import ItemFactory
from KeyDoorShuffle import dungeon_bigs
from source.classes.BabelFish import BabelFish


class Stop(Exception):
    pass


class TestBigChestNeedsBigKey(unittest.TestCase):
    """A big chest opens only with its dungeon's big key, so under the experimental key logic every dungeon holding a
    big chest gets a big key, and the chest is unreachable without it. big_chest_allowed_big_key decides only whether
    the chest may hold the big key itself."""

    @classmethod
    def setUpClass(cls):
        original = Main.fill_dungeons_restrictive

        def stop(world, locations):
            raise Stop(world)

        Main.fill_dungeons_restrictive = stop
        argv = ['--door_shuffle', 'crossed', '--intensity', '2', '--dungeon_shuffle_algorithm', 'experimental',
                '--key_logic_algorithm', 'experimental', '--suppress_rom', '--spoiler', 'none', '--seed', '103']
        logging.disable(logging.WARNING)
        try:
            Main.main(parse_cli(argv), seed=103, fish=BabelFish(lang='en'))
        except Stop as s:
            cls.world = s.args[0]
        finally:
            Main.fill_dungeons_restrictive = original
            logging.disable(logging.NOTSET)

    def big_chests(self):
        for name, layout in self.world.key_layout[1].items():
            chests = [l for r in layout.sector.regions for l in r.locations if '- Big Chest' in l.name]
            if chests:
                yield name, layout, chests

    def test_every_dungeon_with_a_big_chest_has_a_big_key(self):
        lone = 0
        for name, layout, chests in self.big_chests():
            if not layout.key_logic.new_logic.bk_doors and len(chests) == 1:
                lone += 1
            with self.subTest(dungeon=name):
                provided = self.world.dungeon_layouts[1][name].bk_provided  # a forced big key already in the layout
                self.assertTrue(provided or self.world.get_dungeon(name, 1).big_key is not None)
        self.assertGreater(lone, 0, 'seed no longer has a lone big chest without big key doors')

    def test_big_chest_unreachable_without_its_big_key(self):
        world, checked = self.world, 0
        for name, layout, chests in self.big_chests():
            state = BaseClasses.CollectionState(world)
            for item in world.itempool + [i for d in world.dungeons for i in d.all_items]:
                if item.player == 1 and item.name != dungeon_bigs[name]:
                    state.collect(item, True)
            world.clear_exp_cache()
            for chest in chests:
                if state.can_reach(chest.parent_region, None, 1):
                    checked += 1
                    with self.subTest(chest=chest.name):
                        self.assertFalse(chest.can_reach(state))
        self.assertGreater(checked, 0)

    def test_flag_decides_whether_a_big_chest_may_hold_the_big_key(self):
        world, allowed = self.world, {True: 0, False: 0}
        for name, layout, chests in self.big_chests():
            flag = layout.key_logic.new_logic.big_chest_allowed_big_key
            big_key, state = ItemFactory(dungeon_bigs[name], 1), BaseClasses.CollectionState(world)
            for chest in chests:
                allowed[flag] += 1
                with self.subTest(chest=chest.name, allowed=flag):
                    allows = chest.always_allow is not None and chest.always_allow(state, big_key)
                    self.assertEqual(flag, allows)
        self.assertGreater(allowed[True], 0)
        self.assertGreater(allowed[False], 0)


if __name__ == '__main__':
    unittest.main()
