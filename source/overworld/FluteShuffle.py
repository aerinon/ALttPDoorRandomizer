import RaceRandom as random, logging, copy
from BaseClasses import Entrance, RegionType, Terrain
from source.overworld.EntranceShuffle2 import connect_simple
from OWEdges import OWTileRegions
from DungeonGenerator import GenerationException

def shuffle_flute_spots(world, player):
    def connect_flutes(flute_destinations):
        for o in range(0, len(flute_destinations)):
            owid = flute_destinations[o]
            regions = flute_data[owid][0]
            if not world.is_tile_swapped(owid, player):
                connect_simple(world, 'Flute Spot ' + str(o + 1), regions[0], player)
            else:
                connect_simple(world, 'Flute Spot ' + str(o + 1), regions[1], player)
    
    if world.owFluteShuffle[player] == 'vanilla':
        flute_spots = default_flute_connections.copy()
        sort_flute_spots(world, player, flute_spots)
        world.owflutespots[player] = flute_spots
        connect_flutes(flute_spots)
    else:
        from OverworldShuffle import one_way_ledges

        flute_spots = 8
        flute_pool = list(flute_data.keys())
        new_spots = list()
        ignored_regions = set()
        used_flute_regions = []
        forbidden_spots = []
        forbidden_regions = []

        def addSpot(owid, ignore_proximity, forced):
            if world.owFluteShuffle[player] == 'balanced':
                def getIgnored(regionname, base_owid, owid):
                    region = world.get_region(regionname, player)
                    for exit in region.exits:
                        if exit.connected_region is not None and exit.connected_region.type in [RegionType.LightWorld, RegionType.DarkWorld] and exit.connected_region.name not in new_ignored:
                            if exit.connected_region.name in OWTileRegions and (OWTileRegions[exit.connected_region.name] in [base_owid, owid] or OWTileRegions[regionname] == base_owid):
                                new_ignored.add(exit.connected_region.name)
                                getIgnored(exit.connected_region.name, base_owid, OWTileRegions[exit.connected_region.name])
                    if regionname in one_way_ledges:
                        for ledge_region in one_way_ledges[regionname]:
                            if ledge_region not in new_ignored:
                                new_ignored.add(ledge_region)
                                getIgnored(ledge_region, base_owid, OWTileRegions[ledge_region])

                if not world.is_tile_swapped(owid, player):
                    new_region = flute_data[owid][0][0]
                else:
                    new_region = flute_data[owid][0][1]

                if new_region in ignored_regions and not forced:
                    return False
                
                new_ignored = {new_region}
                getIgnored(new_region, OWTileRegions[new_region], OWTileRegions[new_region])
                if not ignore_proximity and not forced and random.randint(0, 31) != 0 and new_ignored.intersection(ignored_regions):
                    return False
                ignored_regions.update(new_ignored)
            if owid in flute_pool:
                flute_pool.remove(owid)
                if ignore_proximity and not forced:
                    logging.getLogger('').warning(f'Warning: Adding flute spot within proximity: {hex(owid)}')
                logging.getLogger('').debug(f'Placing flute at: {hex(owid)}')
                new_spots.append(owid)
            else:
                # TODO: Inspect later, seems to happen only with 'random' flute shuffle
                logging.getLogger('').warning(f'Warning: Attempted to place flute spot not in pool: {hex(owid)}')
            return True
        
        if world.customizer:
            custom_spots = world.customizer.get_owflutespots()
            if custom_spots and player in custom_spots:
                if 'force' in custom_spots[player]:
                    for id in custom_spots[player]['force']:
                        owid = id & 0xBF
                        addSpot(owid, True, True)
                        flute_spots -= 1
                        if not world.is_tile_swapped(owid, player):
                            used_flute_regions.append(flute_data[owid][0][0])
                        else:
                            used_flute_regions.append(flute_data[owid][0][1])
                if 'forbid' in custom_spots[player]:
                    for id in custom_spots[player]['forbid']:
                        owid = id & 0xBF
                        if owid not in new_spots:
                            forbidden_spots.append(owid)
                            if not world.is_tile_swapped(owid, player):
                                forbidden_regions.append(flute_data[owid][0][0])
                            else:
                                forbidden_regions.append(flute_data[owid][0][1])

        # determine sectors (isolated groups of regions) to place flute spots
        flute_regions = {(f[0][0] if (o not in world.owswaps[player][0]) != (world.mode[player] == 'inverted') else f[0][1]) : o for o, f in flute_data.items() if o not in new_spots and o not in forbidden_spots}
        flute_sectors = [(len([r for l in s for r in l]), [r for l in s for r in l if r in flute_regions]) for s in world.owsectors[player]]
        flute_sectors = [s for s in flute_sectors if len(s[1]) > 0]
        region_total = sum([c for c,_ in flute_sectors])
        sector_total = len(flute_sectors)
        empty_sector_total = 0
        sector_has_spot = []

        # determine which sectors still need a flute spot
        for sector in flute_sectors:
            already_has_spot = any(region in sector for region in used_flute_regions)
            sector_has_spot.append(already_has_spot)
            if not already_has_spot:
                empty_sector_total += 1
        if flute_spots < empty_sector_total:
            logging.getLogger('').warning(f'Warning: Not every sector can have a flute spot, generation might fail')
            # pretend like some of the empty sectors already have a flute spot, don't know if they will be reachable
            for i in range(len(flute_sectors)):
                if not sector_has_spot[i]:
                    sector_has_spot[i] = True
                    empty_sector_total -= 1
                    if flute_spots == empty_sector_total:
                        break

        # distribute flute spots for each sector
        for i in range(len(flute_sectors)):
            sector = flute_sectors[i]
            sector_total -= 1
            if not sector_has_spot[i]:
                empty_sector_total -= 1
            spots_to_place = min(flute_spots - empty_sector_total, max(0 if sector_has_spot[i] else 1, round((sector[0] * (flute_spots - sector_total) / region_total) + 0.5)))
            target_spots = len(new_spots) + spots_to_place
            logging.getLogger('').debug(f'Sector of {sector[0]} regions gets {spots_to_place} spot(s)')
            
            if 0x30 in flute_pool and 0x30 not in forbidden_spots and len(new_spots) < target_spots and ('Desert Teleporter Ledge' in sector[1] or 'Mire Teleporter Ledge' in sector[1]):
                addSpot(0x30, True, True) # guarantee desert/mire access

            random.shuffle(sector[1])
            f = 0
            t = 0
            while len(new_spots) < target_spots:
                if f >= len(sector[1]):
                    f = 0
                    t += 1
                    if t > 5:
                        raise GenerationException('Infinite loop detected in flute shuffle')
                owid = flute_regions[sector[1][f]]
                if owid not in new_spots and owid not in forbidden_spots:
                    addSpot(owid, t > 0, False)
                f += 1

            region_total -= sector[0]
            flute_spots -= spots_to_place

        # connect new flute spots
        sort_flute_spots(world, player, new_spots)
        world.owflutespots[player] = new_spots
        connect_flutes(new_spots)

        # update spoiler
        #new_spots = list(map(lambda o: flute_data[o][1], new_spots))
        s = list(map(lambda x: ' ' if x not in new_spots else 'F', [i for i in range(0x40)]))
        text_output = flute_spoiler_table.replace('s', '%s') % (                             s[0x02],                                s[0x07],
                                                                                 s[0x00],                s[0x03],        s[0x05],
            s[0x00],        s[0x02],s[0x03],        s[0x05],        s[0x07],                 s[0x0a],                                s[0x0f],
                            s[0x0a],                                s[0x0f],
            s[0x10],s[0x11],s[0x12],s[0x13],s[0x14],s[0x15],s[0x16],s[0x17], s[0x10],s[0x11],s[0x12],s[0x13],s[0x14],s[0x15],s[0x16],s[0x17],
            s[0x18],        s[0x1a],s[0x1b],        s[0x1d],s[0x1e],
                            s[0x22],                s[0x25],                                 s[0x1a],                s[0x1d],
            s[0x28],s[0x29],s[0x2a],s[0x2b],s[0x2c],s[0x2d],s[0x2e],s[0x2f],     s[0x18],                s[0x1b],                s[0x1e],
            s[0x30],        s[0x32],s[0x33],s[0x34],s[0x35],        s[0x37],                 s[0x22],                s[0x25],
                            s[0x3a],s[0x3b],s[0x3c],                s[0x3f],
                                                                             s[0x28],s[0x29],s[0x2a],s[0x2b],s[0x2c],s[0x2d],s[0x2e],s[0x2f],
                                                                                             s[0x32],s[0x33],s[0x34],                s[0x37],
                                                                                 s[0x30],                                s[0x35],
                                                                                             s[0x3a],s[0x3b],s[0x3c],                s[0x3f])
        world.spoiler.set_map('flute', text_output, new_spots, player)
    create_dynamic_flute_exits(world, player)


def sort_flute_spots(world, player, flute_spots):
    if world.owLayout[player] != 'grid':
        flute_spots.sort(key=lambda id: flute_data[id][1] if id != 0x03 or not world.is_tile_swapped(0x03, player) else 0x04)
    else:
        world_layout = world.owgrid[player][0] if world.mode[player] != 'inverted' else world.owgrid[player][1]
        layout_list = sum(world_layout, [])
        layout_map = {id & 0xBF: i for i, id in enumerate(layout_list)}
        flute_spots.sort(key=lambda id: layout_map[flute_data[id][1] if id != 0x03 or not world.is_tile_swapped(0x03, player) else 0x04])


def create_dynamic_flute_exits(world, player):
    flute_in_pool = True if player not in world.customitemarray else any(i for i, n in world.customitemarray[player].items() if i == 'flute' and n > 0)
    if not flute_in_pool:
        return
    for region in (r for r in world.regions if r.player == player and r.terrain == Terrain.Land and r.name not in ['Zoras Domain', 'Master Sword Meadow', 'Hobo Bridge']):
        if region.type == (RegionType.LightWorld if world.mode[player] != 'inverted' else RegionType.DarkWorld):
            exitname = 'Flute From ' + region.name
            exit = Entrance(region.player, exitname, region)
            exit.spot_type = 'Flute'
            exit.connect(world.get_region('Flute Sky', player))
            region.exits.append(exit)
    world.initialize_regions()


default_flute_connections = [
    0x03, 0x16, 0x18, 0x2c, 0x2f, 0x30, 0x3b, 0x3f
]

flute_data = {
    #OWID    LW Region                         DW Region                            Slot   VRAM    BG Y    BG X   Link Y  Link X   Cam Y   Cam X   Unk1    Unk2   IconY   IconX    AltY    AltX  AltVRAM  AltBGY  AltBGX  AltCamY AltCamX AltUnk1 AltUnk2 AltIconY AltIconX
    0x00: (['Lost Woods East Area',           'Skull Woods Forest'],                0x09, 0x1042, 0x022e, 0x0202, 0x0290, 0x0288, 0x029b, 0x028f, 0xfff2, 0x000e, 0x0290, 0x0288, 0x0290, 0x0290),
    0x02: (['Lumberjack Area',                'Dark Lumberjack Area'],              0x02, 0x059c, 0x00d6, 0x04e6, 0x0138, 0x0558, 0x0143, 0x0563, 0xfffa, 0xfffa, 0x01d8, 0x0518),
    0x03: (['West Death Mountain (Bottom)',   'West Dark Death Mountain (Top)'],    0x0b, 0x1600, 0x02ca, 0x060e, 0x0328, 0x0678, 0x0337, 0x0683, 0xfff6, 0xfff2, 0x03bb, 0x0680, 0x0118, 0x0860, 0x05c0, 0x00b8, 0x07ec, 0x0127, 0x086b, 0xfff8, 0x0004, 0x0148, 0x0850),
    0x05: (['East Death Mountain (Bottom)',   'East Dark Death Mountain (Bottom)'], 0x0e, 0x1860, 0x031e, 0x0d00, 0x0388, 0x0da8, 0x038d, 0x0d7d, 0x0000, 0x0000, 0x03c8, 0x0d98),
    0x07: (['Death Mountain TR Pegs Area',    'Turtle Rock Area'],                  0x07, 0x0804, 0x0102, 0x0e1a, 0x0160, 0x0e90, 0x016f, 0x0e97, 0xfffe, 0x0006, 0x0150, 0x0ea0),
    0x0a: (['Mountain Pass Area',             'Bumper Cave Area'],                  0x0a, 0x0180, 0x0220, 0x0406, 0x0280, 0x0488, 0x028f, 0x0493, 0x0000, 0xfffa, 0x0390, 0x04d8),
    0x0f: (['Zora Waterfall Area',            'Catfish Area'],                      0x0f, 0x0316, 0x025c, 0x0eb2, 0x02c0, 0x0f28, 0x02cb, 0x0f2f, 0x0002, 0xfffe, 0x0360, 0x0f58),
    0x10: (['Lost Woods Pass West Area',      'Skull Woods Pass West Area'],        0x10, 0x0080, 0x0400, 0x0000, 0x0448, 0x0058, 0x046f, 0x0085, 0x0000, 0x0000, 0x04f8, 0x0088),
    0x11: (['Kakariko Fortune Area',          'Dark Fortune Area'],                 0x11, 0x0912, 0x051e, 0x0292, 0x0588, 0x0318, 0x058d, 0x031f, 0x0000, 0xfffe, 0x05f8, 0x0318),
    0x12: (['Kakariko Pond Area',             'Outcast Pond Area'],                 0x12, 0x0890, 0x051a, 0x0476, 0x0578, 0x04f8, 0x0587, 0x0503, 0xfff6, 0x000a, 0x05b8, 0x04f8),
    0x13: (['Sanctuary Area',                 'Dark Chapel Area'],                  0x13, 0x051c, 0x04aa, 0x06de, 0x0508, 0x0758, 0x0517, 0x0763, 0xfff6, 0x0002, 0x05b8, 0x0738),
    0x14: (['Graveyard Area',                 'Dark Graveyard Area'],               0x14, 0x089c, 0x051e, 0x08e6, 0x0580, 0x0958, 0x058b, 0x0963, 0x0000, 0xfffa, 0x05f0, 0x0918, 0x0580, 0x0948),
    0x15: (['River Bend East Bank',           'Qirn Jump East Bank'],               0x15, 0x041a, 0x0486, 0x0ad2, 0x04e8, 0x0b48, 0x04f3, 0x0b4f, 0x0008, 0xfffe, 0x0548, 0x0b78),
    0x16: (['Potion Shop Area',               'Dark Witch Area'],                   0x16, 0x0888, 0x0516, 0x0c4e, 0x0578, 0x0cc8, 0x0583, 0x0cd3, 0xfffa, 0xfff2, 0x05e8, 0x0c9f),
    0x17: (['Zora Approach Ledge',            'Catfish Approach Ledge'],            0x17, 0x039e, 0x047e, 0x0ef2, 0x04e0, 0x0f68, 0x04eb, 0x0f6f, 0x0000, 0xfffe, 0x0580, 0x0f48),
    0x18: (['Kakariko Village',               'Village of Outcasts'],               0x18, 0x0b30, 0x0759, 0x017e, 0x07b7, 0x0200, 0x07c6, 0x020b, 0x0007, 0x0002, 0x0830, 0x0240, 0x07c8, 0x01f8),
    0x1a: (['Forgotten Forest Area',          'Shield Shop Fence'],                 0x1a, 0x081a, 0x070f, 0x04d2, 0x0770, 0x0548, 0x077c, 0x054f, 0xffff, 0xfffe, 0x0770, 0x0518),
    0x1b: (['Hyrule Castle Courtyard',        'Pyramid Area'],                      0x1b, 0x0c30, 0x077a, 0x0786, 0x07d8, 0x07f8, 0x07e7, 0x0803, 0x0006, 0xfffa, 0x07f8, 0x07f8),
    0x1d: (['Wooden Bridge Area',             'Broken Bridge Northeast'],           0x1d, 0x0602, 0x06c2, 0x0a0e, 0x0720, 0x0a80, 0x072f, 0x0a8b, 0xfffe, 0x0002, 0x0750, 0x0a70),
    0x1e: (['Eastern Palace Area',            'Palace of Darkness Area'],           0x26, 0x1802, 0x091e, 0x0c0e, 0x09c0, 0x0c80, 0x098b, 0x0c8b, 0x0000, 0x0002, 0x09a0, 0x0cb0),
    0x22: (['Blacksmith Area',                'Hammer Pegs Area'],                  0x22, 0x058c, 0x08aa, 0x0462, 0x0908, 0x04d8, 0x0917, 0x04df, 0x0006, 0xfffe, 0x0978, 0x04e8),
    0x25: (['Sand Dunes Area',                'Dark Dunes Area'],                   0x25, 0x030e, 0x085a, 0x0a76, 0x08b8, 0x0ae8, 0x08c7, 0x0af3, 0x0006, 0xfffa, 0x0918, 0x0b18),
    0x28: (['Maze Race Area',                 'Dig Game Area'],                     0x28, 0x0908, 0x0b1e, 0x003a, 0x0b88, 0x00b8, 0x0b8d, 0x00bf, 0x0000, 0x0006, 0x0ba8, 0x00b8),
    0x29: (['Kakariko Suburb Area',           'Frog Area'],                         0x29, 0x0408, 0x0a7c, 0x0242, 0x0ae0, 0x02c0, 0x0aeb, 0x02c7, 0x0002, 0xfffe, 0x0b30, 0x02e0),
    0x2a: (['Flute Boy Area',                 'Stumpy Area'],                       0x2a, 0x058e, 0x0aac, 0x046e, 0x0b10, 0x04e8, 0x0b1b, 0x04f3, 0x0002, 0x0002, 0x0b60, 0x04f8),
    0x2b: (['Central Bonk Rocks Area',        'Dark Bonk Rocks Area'],              0x2b, 0x0620, 0x0acc, 0x0700, 0x0b30, 0x0790, 0x0b3b, 0x0785, 0xfff2, 0x0000, 0x0b80, 0x0760),
    0x2c: (['Links House Area',               'Big Bomb Shop Area'],                0x2c, 0x0588, 0x0ab9, 0x0840, 0x0b17, 0x08b8, 0x0b26, 0x08bf, 0xfff7, 0x0000, 0x0bb0, 0x08a8),
    0x2d: (['Stone Bridge South Area',        'Hammer Bridge South Area'],          0x2d, 0x0886, 0x0b1e, 0x0a2a, 0x0ba0, 0x0aa8, 0x0b8b, 0x0aaf, 0x0000, 0x0006, 0x0bf0, 0x0ab8),
    0x2e: (['Tree Line Area',                 'Dark Tree Line Area'],               0x2e, 0x0100, 0x0a1a, 0x0c00, 0x0a78, 0x0c30, 0x0a87, 0x0c7d, 0x0006, 0x0000, 0x0ac8, 0x0c70),
    0x2f: (['Eastern Nook Area',              'Darkness Nook Area'],                0x2f, 0x0798, 0x0afa, 0x0eb2, 0x0b58, 0x0f30, 0x0b67, 0x0f37, 0xfff6, 0x000e, 0x0bc0, 0x0f00),
    0x30: (['Desert Teleporter Ledge',        'Mire Teleporter Ledge'],             0x38, 0x1880, 0x0f1e, 0x0000, 0x0fa8, 0x0078, 0x0f8d, 0x008d, 0x0000, 0x0000, 0x0ff0, 0x0070),
    0x32: (['Flute Boy Approach Area',        'Stumpy Approach Area'],              0x32, 0x03a0, 0x0c6c, 0x0500, 0x0cd0, 0x05a8, 0x0cdb, 0x0585, 0x0002, 0x0000, 0x0d00, 0x0528),
    0x33: (['C Whirlpool Outer Area',         'Dark C Whirlpool Outer Area'],       0x33, 0x0180, 0x0c20, 0x0600, 0x0c80, 0x0628, 0x0c8f, 0x067d, 0x0000, 0x0000, 0x0ce0, 0x0688),
    0x34: (['Statues Area',                   'Hype Cave Area'],                    0x34, 0x088e, 0x0d00, 0x0866, 0x0d60, 0x08d8, 0x0d6f, 0x08e3, 0x0000, 0x000a, 0x0dd0, 0x08e8),
    #0x35: (['Lake Hylia Northwest Bank',      'Ice Lake Northwest Bank'],           0x35, 0x0d00, 0x0da6, 0x0a06, 0x0e08, 0x0a80, 0x0e13, 0x0a8b, 0xfffa, 0xfffa, 0x0dc8, 0x0a90),
    0x35: (['Lake Hylia South Shore',         'Ice Lake Southeast Ledge'],          0x3e, 0x1860, 0x0f1e, 0x0d00, 0x0f98, 0x0da8, 0x0f8b, 0x0d85, 0x0000, 0x0000, 0x0fd8, 0x0da8),
    0x37: (['Ice Cave Area',                  'Shopping Mall Area'],                0x37, 0x0786, 0x0cf6, 0x0e2e, 0x0d58, 0x0ea0, 0x0d63, 0x0eab, 0x000a, 0x0002, 0x0d98, 0x0ed0),
    0x3a: (['Desert Pass Area',               'Swamp Nook Area'],                   0x3a, 0x001a, 0x0e08, 0x04c6, 0x0e70, 0x0540, 0x0e7d, 0x054b, 0x0006, 0x000a, 0x0ee0, 0x0570),
    0x3b: (['Dam Area',                       'Swamp Area'],                        0x3b, 0x069e, 0x0edf, 0x06f2, 0x0f3d, 0x0778, 0x0f4c, 0x077f, 0xfff1, 0xfffe, 0x0fd0, 0x0770),
    0x3c: (['South Pass Area',                'Dark South Pass Area'],              0x3c, 0x0584, 0x0ed0, 0x081e, 0x0f38, 0x0898, 0x0f45, 0x08a3, 0xfffe, 0x0002, 0x0fa8, 0x0898),
    0x3f: (['Octoballoon Area',               'Bomber Corner Area'],                0x3f, 0x0810, 0x0f05, 0x0e75, 0x0f67, 0x0ef3, 0x0f72, 0x0efa, 0xfffb, 0x000b, 0x0fd0, 0x0ef0)
}

flute_spoiler_table = \
"""                       0 1 2 3 4 5 6 7
                      +---+-+---+---+-+
      01234567   A(00)|   |s|   |   |s|
     +--------+       | s +-+ s | s +-+
A(00)|s ss s s|  B(08)|   |s|   |   |s|
B(08)|  s    s|       +-+-+-+-+-+-+-+-+
C(10)|ssssssss|  C(10)|s|s|s|s|s|s|s|s|
D(18)|s ss ss |       +-+-+-+-+-+-+-+-+
E(20)|  s  s  |  D(18)|   |s|   |s|   |
F(28)|ssssssss|       | s +-+ s +-+ s |
G(30)|s ssss s|  E(20)|   |s|   |s|   |
H(38)|  sss  s|       +-+-+-+-+-+-+-+-+
     +--------+  F(28)|s|s|s|s|s|s|s|s|
                      +-+-+-+-+-+-+-+-+
                 G(30)|   |s|s|s|   |s|
                      | s +-+-+-+ s +-+
                 H(38)|   |s|s|s|   |s|
                      +---+-+-+-+---+-+"""
