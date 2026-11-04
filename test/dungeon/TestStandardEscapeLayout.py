import logging
import tempfile
import unittest

import Main
from CLI import parse_cli
from source.classes.BabelFish import BabelFish
from source.dungeon import DungeonStitcher, DungeonStitcherV2


class TestStandardEscapeLayout(unittest.TestCase):
    """Standard Hyrule Castle: the escape is checked from the courtyard, the rest once the later entrances open."""

    @classmethod
    def setUpClass(cls):
        logging.disable(logging.WARNING)
        try:
            with tempfile.TemporaryDirectory() as out:
                # crossed i3 standard: a trap leaves rooms reachable only through the Mire Tile Room portal and the sewers drop
                cls.world = Main.main(parse_cli(['--customizer', 'test/customizer/standard_post_escape_rooms.yaml',
                                                 '--suppress_rom', '--spoiler', 'none', '--outputpath', out]),
                                      fish=BabelFish(lang='en'))
        finally:
            logging.disable(logging.NOTSET)

    def test_pinned_traps_cutting_off_post_escape_rooms_load(self):
        self.assertTrue(self.world.required_locations)

    def test_both_stitchers_need_the_south_lobby_to_reach_cellblock(self):
        south = next(x for x in self.world.dungeon_portals[1] if x.name == 'Hyrule Castle South')
        path = (south.door.entrance.parent_region.name, 'Hyrule Dungeon Cellblock')
        for stitcher in (DungeonStitcher, DungeonStitcherV2):
            with self.subTest(stitcher=stitcher.__name__):
                self.assertIn(path, stitcher.determine_paths_for_dungeon(self.world, 1, [], 'Hyrule Castle Dungeon'))


if __name__ == '__main__':
    unittest.main()
