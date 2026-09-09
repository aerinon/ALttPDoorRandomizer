from Items import ItemFactory
from test.TestBase import TestBase, build_vanilla_world


class TestVanillaOWG(TestBase):
    def setUp(self):
        self.world = build_vanilla_world(mode='open', logic='owglitches')
        self.world.precollected_items.clear()
        self.world.itempool.append(ItemFactory('Pegasus Boots', 1))
