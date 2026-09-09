import unittest

from BaseClasses import CollectionState, Entrance
from Items import ItemFactory
from test.TestBase import build_vanilla_world


# old test region names -> current portal/drop regions
STARTING_REGION_MAP = {
    'Eastern Palace': ['Eastern Portal'],
    'Agahnims Tower': ['Agahnims Tower Portal'],
    'Desert Palace North': ['Desert Back Portal'],
    'Desert Palace Main (Inner)': ['Desert South Portal'],
    'Desert Palace Main (Outer)': ['Desert West Portal', 'Desert East Portal'],
    'Ganons Tower (Entrance)': ['Ganons Tower Portal'],
    'Ice Palace (Entrance)': ['Ice Portal'],
    'Misery Mire (Entrance)': ['Mire Portal'],
    'Palace of Darkness (Entrance)': ['Palace of Darkness Portal'],
    'Skull Woods First Section': ['Skull 1 Portal', 'Skull Pinball'],
    'Skull Woods First Section (Left)': ['Skull Left Drop'],
    'Skull Woods First Section (Top)': ['Skull Pot Circle'],
    'Skull Woods Second Section': ['Skull 2 East Portal', 'Skull 2 West Portal', 'Skull Back Drop'],
    'Skull Woods Final Section (Entrance)': ['Skull 3 Portal'],
    'Swamp Palace (Entrance)': ['Swamp Portal'],
    'Thieves Town (Entrance)': ['Thieves Town Portal'],
    'Tower of Hera (Bottom)': ['Hera Portal'],
}


class TestDungeon(unittest.TestCase):
    def setUp(self):
        self.world = build_vanilla_world()
        self.starting_regions = []

    def run_tests(self, access_pool):
        # start regions hang off Menu
        menu = self.world.get_region('Menu', 1)
        for region in self.starting_regions:
            for region_name in STARTING_REGION_MAP.get(region, [region]):
                exit = Entrance(1, f'Test Start: {region_name}', menu)
                exit.connect(self.world.get_region(region_name, 1))
                menu.exits.append(exit)

        for location, access, *item_pool in access_pool:
            items = item_pool[0]
            all_except = item_pool[1] if len(item_pool) > 1 else None
            with self.subTest(location=location, access=access, items=items, all_except=all_except):
                if all_except and len(all_except) > 0:
                    items = self.world.itempool[:]
                    items = [item for item in items if item.name not in all_except and not ("Bottle" in item.name and "AnyBottle" in all_except)]
                    items.extend(ItemFactory(item_pool[0], 1))
                else:
                    items = ItemFactory(items, 1)
                state = CollectionState(self.world)
                for item in items:
                    item.advancement = True
                    state.collect(item)

                self.assertEqual(self.world.get_location(location, 1).can_reach(state), access)