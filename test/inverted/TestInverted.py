from test.TestBase import TestBase, build_vanilla_world


class TestInverted(TestBase):
    def setUp(self):
        self.world = build_vanilla_world(mode='inverted', logic='noglitches')
