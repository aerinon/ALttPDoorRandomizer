import logging
import unittest

import Main
from CLI import parse_cli
from source.classes.BabelFish import BabelFish


def generate_standard(seed, intensity):
    argv = ['--door_shuffle', 'crossed', '--intensity', str(intensity), '--dungeon_shuffle_algorithm', 'experimental',
            '--key_logic_algorithm', 'experimental', '--mode', 'standard', '--suppress_rom', '--spoiler', 'none',
            '--seed', str(seed)]
    logging.disable(logging.WARNING)
    try:
        return Main.main(parse_cli(argv), seed=seed, fish=BabelFish(lang='en'))
    finally:
        logging.disable(logging.NOTSET)


class TestStandardEscapeReservation(unittest.TestCase):
    """The escape locations kept free of dungeon items are chosen with the key doors, so the escape keys still fit."""

    def test_reservation_leaves_room_for_the_escape_keys(self):
        # formerly "No more spots to place Small Key (Escape)": the reservation took one of the few early locations
        world = generate_standard(1, 1)
        builder = world.dungeon_layouts[1]['Hyrule Castle']
        self.assertEqual(len(builder.key_door_proposal) // 5, len(builder.standard_reserved))
        for name in builder.standard_reserved:
            item = world.get_location(name, 1).item
            with self.subTest(location=name):
                self.assertFalse(item.smallkey or item.bigkey or item.map or item.compass, item.name)


if __name__ == '__main__':
    unittest.main()
