#!/usr/bin/env python3
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

def int16_as_bytes(value):
    value = value & 0xFFFF
    return [value & 0xFF, (value >> 8) & 0xFF]

def int32_as_bytes(value):
    value = value & 0xFFFFFFFF
    return [value & 0xFF, (value >> 8) & 0xFF, (value >> 16) & 0xFF, (value >> 24) & 0xFF]

def pc_to_snes(value):
    return ((value<<1) & 0x7F0000)|(value & 0x7FFF)|0x8000

def snes_to_pc(value):
    return ((value & 0x7F0000)>>1)|(value & 0x7FFF)

def parse_player_names(names, players, teams):
    names = [n for n in re.split(r'[, ]', names) if n]
    ret = []
    while names or len(ret) < teams:
        team = [n[:16] for n in names[:players]]
        while len(team) != players:
            team.append(f"Player {len(team) + 1}")
        ret.append(team)

        names = names[players:]
    return ret

def is_bundled():
    return getattr(sys, 'frozen', False)

def local_path(path):
    return path

    if local_path.cached_path is not None:
        return os.path.join(local_path.cached_path, path)

    if is_bundled():
        # we are running in a bundle
        local_path.cached_path = sys._MEIPASS # pylint: disable=protected-access,no-member
    else:
        # we are running in a normal Python environment
        local_path.cached_path = os.path.dirname(os.path.abspath(__file__))

    return os.path.join(local_path.cached_path, path)

local_path.cached_path = None

def output_path(path):
    if output_path.cached_path is not None:
        return os.path.join(output_path.cached_path, path)

    if not is_bundled():
        output_path.cached_path = '.'
        return os.path.join(output_path.cached_path, path)
    else:
        # has been packaged, so cannot use CWD for output.
        if sys.platform == 'win32':
            #windows
            import ctypes.wintypes
            CSIDL_PERSONAL = 5       # My Documents
            SHGFP_TYPE_CURRENT = 0   # Get current, not default value

            buf = ctypes.create_unicode_buffer(ctypes.wintypes.MAX_PATH)
            ctypes.windll.shell32.SHGetFolderPathW(None, CSIDL_PERSONAL, None, SHGFP_TYPE_CURRENT, buf)

            documents = buf.value

        elif sys.platform == 'darwin':
            from AppKit import NSSearchPathForDirectoriesInDomains # pylint: disable=import-error
            # http://developer.apple.com/DOCUMENTATION/Cocoa/Reference/Foundation/Miscellaneous/Foundation_Functions/Reference/reference.html#//apple_ref/c/func/NSSearchPathForDirectoriesInDomains
            NSDocumentDirectory = 9
            NSUserDomainMask = 1
            # True for expanding the tilde into a fully qualified path
            documents = NSSearchPathForDirectoriesInDomains(NSDocumentDirectory, NSUserDomainMask, True)[0]
        else:
            raise NotImplementedError('Not supported yet')

        output_path.cached_path = os.path.join(documents, 'ALttPEntranceRandomizer')
        if not os.path.exists(output_path.cached_path):
            os.mkdir(output_path.cached_path)
        return os.path.join(output_path.cached_path, path)

output_path.cached_path = None

def open_file(filename):
    if sys.platform == 'win32':
        os.startfile(filename)
    else:
        open_command = 'open' if sys.platform == 'darwin' else 'xdg-open'
        subprocess.call([open_command, filename])

def close_console():
    if sys.platform == 'win32':
        #windows
        import ctypes.wintypes
        try:
            ctypes.windll.kernel32.FreeConsole()
        except Exception:
            pass

def make_new_base2current(old_rom='Zelda no Densetsu - Kamigami no Triforce (Japan).sfc', new_rom='working.sfc'):
    from collections import OrderedDict
    import json
    import hashlib
    with open(old_rom, 'rb') as stream:
        old_rom_data = bytearray(stream.read())
    with open(new_rom, 'rb') as stream:
        new_rom_data = bytearray(stream.read())
    # extend to 2 mb
    old_rom_data.extend(bytearray([0x00] * (2097152 - len(old_rom_data))))

    out_data = OrderedDict()
    for idx, old in enumerate(old_rom_data):
        new = new_rom_data[idx]
        if old != new:
            out_data[idx] = [int(new)]
    for offset in reversed(list(out_data.keys())):
        if offset - 1 in out_data:
            out_data[offset-1].extend(out_data.pop(offset))
    with open('data/base2current.json', 'wt') as outfile:
        json.dump([{key:value} for key, value in out_data.items()], outfile, separators=(",", ":"))

    basemd5 = hashlib.md5()
    basemd5.update(new_rom_data)
    return "New Rom Hash: " + basemd5.hexdigest()


entrance_offsets = {
    'Sanctuary': 0x2,
    'HC West': 0x3,
    'HC South': 0x4,
    'HC East': 0x5,
    'Eastern': 0x8,
    'Desert West': 0x9,
    'Desert South': 0xa,
    'Desert East': 0xb,
    'Desert Back': 0xc,
    'TR Lazy Eyes': 0x15,
    'TR Eye Bridge': 0x18,
    'TR Chest': 0x19,
    'Aga Tower': 0x24,
    'Swamp': 0x25,
    'Palace of Darkness': 0x26,
    'Mire': 0x27,
    'Skull 2 West': 0x28,
    'Skull 2 East': 0x29,
    'Skull 1': 0x2a,
    'Skull 3': 0x2b,
    'Ice': 0x2d,
    'Hera': 0x33,
    'Thieves': 0x34,
    'TR Main': 0x35,
    'GT': 0x37,
    'Skull Pots': 0x76,
    'Skull Left Drop': 0x77,
    'Skull Pinball': 0x78,
    'Skull Back Drop': 0x79,
    'Sewer Drop': 0x81
}

entrance_data = {
    'Room Ids': (0x14577, 2),
    'Relative coords': (0x14681, 8),
    'ScrollX': (0x14AA9, 2),
    'ScrollY': (0x14BB3, 2),
    'LinkX': (0x14CBD, 2),
    'LinkY': (0x14DC7, 2),
    'CameraX': (0x14ED1, 2),
    'CameraY': (0x14FDB, 2),
    'Blockset': (0x150e5, 1),
    'FloorValues': (0x1516A, 1),
    'Dungeon Value': (0x151EF, 1),
    'Frame on Exit': (0x15274, 1),
    'BG Setting': (0x152F9, 1),
    'HV Scroll': (0x1537E, 1),
    'Scroll Quad': (0x15403, 1),
    'Exit Door': (0x15488, 2),
    'Music': (0x15592, 1)
}


def read_entrance_data(old_rom='Zelda no Densetsu - Kamigami no Triforce (Japan).sfc'):
    with open(old_rom, 'rb') as stream:
        old_rom_data = bytearray(stream.read())

    for ent, offset in entrance_offsets.items():
        # print(ent)
        string = ent
        for dp, data in entrance_data.items():
            byte_array = []
            address, size = data
            for i in range(0, size):
                byte_array.append(old_rom_data[address+(offset*size)+i])
            some_bytes = ', '.join('0x{:02x}'.format(x) for x in byte_array)
            string += '\t'+some_bytes
            # print("%s: %s" % (dp, bytes))
        print(string)


def print_wiki_doors(d_regions, world, player):

    for d, region_list in d_regions.items():
        tile_map = {}
        for region in region_list:
            tile = None
            r = world.get_region(region, player)
            for ext in r.exits:
                door = world.check_for_door(ext.name, player)
                if door is not None and door.roomIndex != -1:
                    tile = door.roomIndex
                    break
            if tile is not None:
                if tile not in tile_map:
                    tile_map[tile] = []
                tile_map[tile].append(r)
        print(d)
        print('{| class="wikitable"')
        print('|-')
        print('! Room')
        print('! Supertile')
        print('! Doors')
        for tile, region_list in tile_map.items():
            tile_done = False
            for region in region_list:
                print('|-')
                print('| '+region.name)
                if not tile_done:
                    listlen = len(region_list)
                    link = '| {{UnderworldMapLink|'+str(tile)+'}}'
                    print(link if listlen < 2 else '| rowspan = '+str(listlen)+' '+link)
                    tile_done = True
                strs_to_print = []
                for ext in region.exits:
                    strs_to_print.append(ext.name)
                print('| '+' <br /> '.join(strs_to_print))
        print('|}')


def print_xml_doors(d_regions, world, player):
    root = ET.Element('root')
    for d, region_list in d_regions.items():
        tile_map = {}
        for region in region_list:
            tile = None
            r = world.get_region(region, player)
            for ext in r.exits:
                door = world.check_for_door(ext.name, player)
                if door is not None and door.roomIndex != -1:
                    tile = door.roomIndex
                    break
            if tile is not None:
                if tile not in tile_map:
                    tile_map[tile] = []
                tile_map[tile].append(r)
        dungeon = ET.SubElement(root, 'dungeon', {'name': d})
        for tile, r_list in tile_map.items():
            supertile = ET.SubElement(dungeon, 'supertile', {'id': str(tile)})
            for region in r_list:
                room = ET.SubElement(supertile, 'room', {'name': region.name})
                for ext in region.exits:
                    ET.SubElement(room, 'door', {'name': ext.name})
    ET.dump(root)


def print_graph(world):
    root = ET.Element('root')
    for region in world.regions:
        r = ET.SubElement(root, 'region', {'name': region.name})
        for ext in region.exits:
            attribs = {'name': ext.name}
            if ext.connected_region:
                attribs['connected_region'] = ext.connected_region.name
            if ext.door and ext.door.dest:
                attribs['dest'] = ext.door.dest.name
            ET.SubElement(r, 'exit', attribs)
    ET.dump(root)


if __name__ == '__main__':
    pass
    # make_new_base2current()
    read_entrance_data(old_rom='C:\\Users\\Randall\\Documents\\kwyn\\orig\\z3.sfc')
