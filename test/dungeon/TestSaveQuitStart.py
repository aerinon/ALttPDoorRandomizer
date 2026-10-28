import logging
import unittest

import Main
from CLI import parse_cli
from source.classes.BabelFish import BabelFish


class Stop(Exception):
    pass


class TestSaveQuitStart(unittest.TestCase):
    """In open mode, save and quit puts the player in the Sanctuary room: the dungeon holding it starts there too, even
    when no portal leads into it."""

    def test_sanctuary_room_is_a_key_layout_start(self):
        argv = ['--customizer', 'test/customizer/sanctuary_room_not_lobby.yaml', '--suppress_rom', '--spoiler', 'none',
                '--seed', '1']
        original = Main.fill_dungeons_restrictive

        def stop(world, *rest, **kwargs):
            raise Stop(world)

        Main.fill_dungeons_restrictive = stop
        logging.disable(logging.WARNING)
        try:
            Main.main(parse_cli(argv), seed=1, fish=BabelFish(lang='en'))
            self.fail('generation finished without reaching the dungeon fill')
        except Stop as s:
            world = s.args[0]
        finally:
            Main.fill_dungeons_restrictive = original
            logging.disable(logging.NOTSET)
        sanctuary = world.get_region('Sanctuary', 1)
        self.assertFalse(any(p.door.entrance.parent_region == sanctuary for p in world.dungeon_portals[1]))
        layout = world.key_layout[1][sanctuary.dungeon.name]
        self.assertIn('Sanctuary', [r.name for r in layout.start_regions])


if __name__ == '__main__':
    unittest.main()
