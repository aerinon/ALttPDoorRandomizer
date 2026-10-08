from collections import namedtuple

from BaseClasses import RegionType

# An overworld hole always leads to its Drop Portal; the portal's fall (a one-way Hole) lands on a Terminal.
DropPortal = namedtuple('DropPortal', ['region', 'fall', 'landing', 'terminal', 'entrance_id', 'owner'])

drop_portals = [
    DropPortal('Skull Pot Circle Drop Portal', 'Skull Pot Circle Drop Portal Fall', 'Skull Pot Circle',
               'Skull Pot Circle Terminal', 0x76, 'Skull Woods'),
    DropPortal('Skull Left Drop Drop Portal', 'Skull Left Drop Drop Portal Fall', 'Skull Left Drop',
               'Skull Left Drop Terminal', 0x77, 'Skull Woods'),
    DropPortal('Skull Pinball Drop Portal', 'Skull Pinball Drop Portal Fall', 'Skull Pinball',
               'Skull Pinball Terminal', 0x78, 'Skull Woods'),
    DropPortal('Skull Back Drop Drop Portal', 'Skull Back Drop Drop Portal Fall', 'Skull Back Drop',
               'Skull Back Drop Terminal', 0x79, 'Skull Woods'),
    DropPortal('Sewers Drop Portal', 'Sewers Drop Portal Fall', 'Sewers Rat Path',
               'Sewers Rat Path Terminal', 0x81, 'Hyrule Castle'),
]
drop_portal_by_region = {p.region: p for p in drop_portals}


def is_drop_portal(region):
    return region is not None and region.name in drop_portal_by_region


def is_lobby_portal(region):
    return region is not None and region.name.endswith(' Portal') and not is_drop_portal(region)


def is_outside(region):
    return region is not None and region.type in [RegionType.LightWorld, RegionType.DarkWorld] and region.name != 'Menu'


def entered_from_outside(entrance):
    """Whether entrance comes into the dungeon from the overworld, directly or through a hole's Drop Portal."""
    return is_outside(entrance.parent_region) or is_drop_portal(entrance.parent_region)


def drop_parent_region(drop_portal_region):
    """The overworld region whose hole leads to this Drop Portal (None until entrance shuffle connects it)."""
    return next((e.parent_region for e in drop_portal_region.entrances if is_outside(e.parent_region)), None)


def outside_parent(entrance):
    """The non-dungeon region an entrance comes from: through a Drop Portal, the region of the hole leading to it."""
    parent = entrance.parent_region
    if is_drop_portal(parent):
        return drop_parent_region(parent)
    if parent.type != RegionType.Dungeon and parent.name != 'Menu':
        return parent
    return None


def sector_drop_portals(sector):
    return [r for r in sector.regions if is_drop_portal(r)]


def builder_drop_portals(builder):
    """Names of the Drop Portal regions in a dungeon builder's sectors: the dungeon's hole entrances. Once generated,
    the builder's sectors include its master sector, which holds them all again."""
    return list(dict.fromkeys(r.name for s in builder.sectors for r in sector_drop_portals(s)))


def region_overworld_side(portal_region):
    """The overworld region a lobby portal region leads out onto (None if it has no overworld exit)."""
    return next((e.connected_region for e in portal_region.exits
                 if e.connected_region is not None and e.connected_region.type != RegionType.Dungeon), None)


def portal_overworld_side(portal, world):
    return region_overworld_side(world.get_region(f'{portal.name} Portal', portal.player))


def is_escape_builder(builder_name, std_flag):
    """In standard the escape is walked from inside the castle, so no hole is a way into its builders."""
    return std_flag and builder_name in ['Hyrule Castle Sewers', 'Hyrule Castle Dungeon']
