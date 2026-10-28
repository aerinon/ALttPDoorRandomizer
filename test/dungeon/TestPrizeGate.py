import logging
import unittest

import Main
from CLI import parse_cli
from KeyDoorShuffle import prize_gate
from source.classes.BabelFish import BabelFish


class Stop(Exception):
    pass


class TestPrizeGate(unittest.TestCase):
    """A dungeon entrance whose only overworld route passes the Ganons Tower entrance needs the GT crystals, which may
    include the dungeon's own prize: key logic must not treat it as open from the start."""

    @classmethod
    def setUpClass(cls):
        # entrances pinned by the customizer; the rest of the shuffle doesn't matter
        argv = ['--customizer', 'test/customizer/prize_gate_superbunny_gt.yaml', '--suppress_rom', '--spoiler', 'none',
                '--seed', '1']
        original = Main.fill_dungeons_restrictive

        def stop(world, *rest, **kwargs):
            raise Stop(world)

        Main.fill_dungeons_restrictive = stop
        logging.disable(logging.WARNING)
        try:
            Main.main(parse_cli(argv), seed=1, fish=BabelFish(lang='en'))
            raise AssertionError('generation finished without reaching the dungeon fill')
        except Stop as s:
            cls.world = s.args[0]
        finally:
            Main.fill_dungeons_restrictive = original
            logging.disable(logging.NOTSET)

    def test_entrance_behind_the_tower_entrance_is_gated(self):
        # Turtle Rock's Eye Bridge entrance; the ledge is reached only through Superbunny Cave, behind the tower entrance
        entrance = self.world.get_entrance('Dark Death Mountain Ledge (East)', 1)
        self.assertEqual('GT', prize_gate(entrance, 'Turtle Rock', False))

    def test_entrance_reached_through_another_dungeon_is_not_gated(self):
        # Swamp Palace's entrance is open overworld; Skull Woods Final Section is reached through Skull Woods
        for name in ['Swamp Palace', 'Skull Woods Final Section']:
            with self.subTest(entrance=name):
                self.assertIsNone(prize_gate(self.world.get_entrance(name, 1), 'Turtle Rock', False))

    def test_turtle_rock_layout_is_prize_relevant(self):
        self.assertEqual('GT', self.world.key_layout[1]['Turtle Rock'].prize_relevant)


if __name__ == '__main__':
    unittest.main()
