import logging
import unittest
from types import SimpleNamespace

from source.dungeon.SmallKeyDoorShuffle import is_key_door_layout_satisfiable


class Loc:
    def __init__(self, name):
        self.name, self.item, self.forced_item = name, None, None


def rule(needed, locations, bk_conditional_set=None):
    if bk_conditional_set:
        return SimpleNamespace(bk_conditional_set=bk_conditional_set, needed_keys_wo_bk=needed,
                               check_locations_wo_bk=set(locations))
    return SimpleNamespace(bk_conditional_set=None, needed_keys_w_bk=needed, check_locations_w_bk=set(locations))


def layout(locations, rules):
    return SimpleNamespace(big_key_special=False, item_locations=set(locations), max_chests=len(locations),
                           key_logic=SimpleNamespace(bk_name='Big Key (Test)', placement_rules=rules))


class TestBigKeyOutside(unittest.TestCase):
    """A shuffled big key may lie outside the dungeon, so a layout whose big key door precedes every location, or whose
    rules fail for the big key at each location inside, still has a solution."""

    @classmethod
    def setUpClass(cls):
        logging.disable(logging.WARNING)

    @classmethod
    def tearDownClass(cls):
        logging.disable(logging.NOTSET)

    def test_big_key_door_before_every_location(self):
        chest = Loc('Chest')
        key_layout = layout([chest], [rule(1, [chest])])
        self.assertFalse(is_key_door_layout_satisfiable(key_layout, {chest}, print_proposal=False))
        self.assertTrue(is_key_door_layout_satisfiable(key_layout, {chest}, print_proposal=False, bk_outside=True))

    def test_big_key_inside_starves_a_door(self):
        # the big key at the chest leaves no spot for the key the first door needs
        chest = Loc('Chest')
        key_layout = layout([chest], [rule(1, [], bk_conditional_set={chest}), rule(1, [chest])])
        self.assertFalse(is_key_door_layout_satisfiable(key_layout, set(), print_proposal=False))
        self.assertTrue(is_key_door_layout_satisfiable(key_layout, set(), print_proposal=False, bk_outside=True))

    def test_rules_without_the_big_key_still_apply(self):
        chest = Loc('Chest')
        key_layout = layout([chest], [rule(2, [chest])])
        self.assertFalse(is_key_door_layout_satisfiable(key_layout, set(), print_proposal=False, bk_outside=True))


if __name__ == '__main__':
    unittest.main()
