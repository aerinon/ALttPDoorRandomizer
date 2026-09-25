import itertools
import unittest
from types import SimpleNamespace

from source.dungeon.DungeonGenTransitivity import valid_portal
from source.dungeon.DungeonStitcherV2 import find_portal_candidates
from test.dungeon.transitivity_harness import capture_sectors

ROLES = ['primary', 'dead_end_able', 'destination']


class Placeholder:
    """Stands in for the portal's own door, which valid_portal uses as a lookup key."""


def stitcher_accepts(door, role, split, bk, std, hc, vanilla_traps):
    """Whether the stitcher's candidate filter offers door for a portal of this role (determine_entrance_regions)."""
    bk_shuffle = bk or split
    hc_flag = std and hc
    rupee_bow = hc_flag  # a retro bow is modeled as always on here; it only narrows both sides the same way
    anything = SimpleNamespace(blocked=False, bk_shuffle_req=False, passage=True, deadEnd=False, standard_restricted=False,
                               rupee_bow_restricted=False)  # keeps the filter's lone-door fallback out of the way
    if role == 'primary':
        kept = find_portal_candidates([door, anything], vanilla_traps, standard=hc_flag, rupee_bow=rupee_bow, bk_shuffle=bk_shuffle)
    elif role == 'dead_end_able':
        kept = find_portal_candidates([door, anything], vanilla_traps, False, True, standard=hc_flag, rupee_bow=rupee_bow,
                                      bk_shuffle=bk_shuffle)
    else:
        kept = find_portal_candidates([door, anything], vanilla_traps, True, True, standard=std, rupee_bow=rupee_bow,
                                      bk_shuffle=True)
    return door in kept


def transitivity_accepts(door, role, split, bk, std, hc, vanilla_traps):
    """Whether valid_portal lets door serve a portal of this role at the start of the search."""
    placeholder = Placeholder()
    portal = SimpleNamespace(door=placeholder, destination=role == 'destination',
                             dependent=SimpleNamespace() if role == 'dead_end_able' else None)
    sector = SimpleNamespace(portals=[portal])
    other = SimpleNamespace(portals=[SimpleNamespace(door=None, destination=False, dependent=None)])
    c_info = SimpleNamespace(builder=SimpleNamespace(name='Hyrule Castle' if hc else 'Some Dungeon', split_flag=split),
                             flags=SimpleNamespace(vanilla_traps=vanilla_traps, bk_shuffle_flag=bk, std_flag=std,
                                                   rupee_bow_flag=std and hc),
                             door_sector_map={placeholder: sector}, sector_list=[sector, other])
    return valid_portal(door, placeholder, c_info, True)


class TestPortalConsistency(unittest.TestCase):
    """Transitivity must not accept a portal door that the stitcher would never assign (a wrong True).
    The reverse only narrows randomness and is allowed."""

    def test_transitivity_never_accepts_what_the_stitcher_refuses(self):
        sectors, flags = capture_sectors(4)
        world = sectors[0].regions[0].world
        doors = [d for d in world.doors if d.player == 1 and d.portalAble]
        self.assertTrue(doors)
        wrong = []
        for door, role, split, bk, std, hc, traps in itertools.product(doors, ROLES, *[(False, True)] * 5):
            if transitivity_accepts(door, role, split, bk, std, hc, traps) and \
                    not stitcher_accepts(door, role, split, bk, std, hc, traps):
                wrong.append((door.name, role, dict(split=split, bk=bk, std=std, hc=hc, vanilla_traps=traps)))
        self.assertEqual([], wrong[:20], f'{len(wrong)} mismatches')


if __name__ == '__main__':
    unittest.main()
