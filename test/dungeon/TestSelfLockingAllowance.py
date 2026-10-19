import logging
import unittest

import BaseClasses
import Fill
import Main
from CLI import parse_cli
from Items import ItemFactory
from source.classes.BabelFish import BabelFish


class Stop(Exception):
    pass


class TestSelfLockingAllowance(unittest.TestCase):
    """A small key may be placed behind the self-locking door it opens: the key logic grants that spot while the key
    is named as placed there, and nothing else beyond the door. Granting it while the key went elsewhere let fill lock
    two dungeons in each other; granting the rooms beyond the door made what fill had placed there unreachable."""

    @classmethod
    def setUpClass(cls):
        original = Main.fill_dungeons_restrictive

        def stop(world, locations):
            raise Stop(world)

        Main.fill_dungeons_restrictive = stop
        argv = ['--door_shuffle', 'vanilla', '--keysanity', '--key_logic_algorithm', 'experimental', '--suppress_rom',
                '--spoiler', 'none', '--seed', '1']
        logging.disable(logging.WARNING)
        try:
            Main.main(parse_cli(argv), seed=1, fish=BabelFish(lang='en'))
        except Stop as s:
            cls.world = s.args[0]
        finally:
            Main.fill_dungeons_restrictive = original
            logging.disable(logging.NOTSET)

    def verdict(self, spot_name, placed_at):
        """Hold every pooled item except Hera's small key, mark that key as being placed at placed_at (or nowhere).
        Returns whether the spot is reachable, and whether fill may place the key there as a self-locking spot."""
        world = self.world
        state = BaseClasses.CollectionState(world)
        for item in world.itempool:
            if item.player == 1 and item.name != 'Small Key (Tower of Hera)':
                state.collect(item, True)
        key = ItemFactory('Small Key (Tower of Hera)', 1)
        state.placing_items = [key]
        state.placing_locations = [(key, world.get_location(placed_at, 1))] if placed_at else None
        state.stale[1] = True
        world.clear_exp_cache()
        spot = world.get_location(spot_name, 1)
        return spot.can_reach(state), Fill.self_locking_spot(spot, key, state, world)

    def test_allowance_needs_the_key_behind_the_door(self):
        spot = 'Tower of Hera - Big Key Chest'
        self.assertEqual((False, False), self.verdict(spot, None))
        self.assertEqual((False, False), self.verdict(spot, "Link's Uncle"))  # placed outside the dungeon
        self.assertEqual((False, True), self.verdict(spot, spot))  # the spot only, not its room


    def test_spot_rule_sees_its_room(self):
        # crossed i3: Eastern's key lies behind its own door at Tower of Hera - Basement Cage, whose rule needs the cage
        # reached in orange; the spot's room isn't granted, so its rule is judged with the room as the walk reaches it
        original = Main.find_keylock

        def stop(key_layout, world, player):
            raise Stop(world)

        Main.find_keylock = stop
        argv = ['--door_shuffle', 'crossed', '--intensity', '3', '--dungeon_shuffle_algorithm', 'experimental',
                '--key_logic_algorithm', 'experimental', '--suppress_rom', '--spoiler', 'none', '--seed', '44']
        logging.disable(logging.WARNING)
        try:
            Main.main(parse_cli(argv), seed=44, fish=BabelFish(lang='en'))
            self.fail('generation finished without reaching the keylock check')
        except Stop:
            pass
        finally:
            Main.find_keylock = original
            logging.disable(logging.NOTSET)


    def test_event_with_another_way_does_not_stop_a_self_lock(self):
        # basic i2, OWG, standard: Ice's last key fits only at Iced T Room, behind its own door; that door can also
        # reach Ice Block Drop, whose block has another way past (Cane of Somaria), so the spot still self-locks
        original = Main.find_keylock

        def stop(key_layout, world, player):
            raise Stop(world)

        Main.find_keylock = stop
        argv = ['--door_shuffle', 'basic', '--intensity', '2', '--logic', 'owglitches', '--mode', 'standard',
                '--dungeon_shuffle_algorithm', 'experimental', '--key_logic_algorithm', 'experimental',
                '--suppress_rom', '--spoiler', 'none', '--seed', '684160854']
        logging.disable(logging.WARNING)
        try:
            Main.main(parse_cli(argv), seed=684160854, fish=BabelFish(lang='en'))
            self.fail('generation finished without reaching the keylock check')
        except Stop:
            pass
        finally:
            Main.find_keylock = original
            logging.disable(logging.NOTSET)


if __name__ == '__main__':
    unittest.main()
