from test.TestBase import TestBase, build_vanilla_world


class TestVanilla(TestBase):
    def setUp(self):
        self.world = build_vanilla_world(mode='open', logic='noglitches')
