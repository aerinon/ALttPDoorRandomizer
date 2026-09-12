from Items import ItemFactory
from test.TestBase import TestBase, build_vanilla_world


class TestInvertedOWG(TestBase):
    def setUp(self):
        self.world = build_vanilla_world(mode='inverted', logic='owglitches')
        self.world.precollected_items.clear()
        self.world.itempool.append(ItemFactory('Pegasus Boots', 1))
