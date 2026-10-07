import itertools
import unittest

from test.dungeon.transitivity_harness import DUNGEONS, capture_sectors, make_builder, sectors_by_dungeon, timed_check


def vanilla_cases(intensity, pairs):
    sectors, flags = capture_sectors(intensity)
    grouped = sectors_by_dungeon(sectors)
    names = itertools.combinations(DUNGEONS, 2) if pairs else [(n,) for n in DUNGEONS]
    for case in names:
        yield '+'.join(case), make_builder(case[0]), [s for n in case for s in grouped[n]], flags


class TestTransitivityVanilla(unittest.TestCase):
    """Vanilla layouts are valid, so every vanilla dungeon, and every union of two, must be transitive."""

    def check(self, intensity, pairs):
        for label, builder, sector_list, flags in vanilla_cases(intensity, pairs):
            with self.subTest(case=label, intensity=intensity):
                verdict, elapsed = timed_check(builder, sector_list, flags, limit=120)
                self.assertTrue(verdict, f'vanilla {label} must be transitive')

    def test_singles_intensity_3(self):
        self.check(3, pairs=False)

    def test_pairs_intensity_3(self):
        self.check(3, pairs=True)


if __name__ == '__main__':
    unittest.main()
