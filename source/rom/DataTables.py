from collections import defaultdict

from Utils import snes_to_pc, int24_as_bytes, int16_as_bytes, load_cached_yaml, pc_to_snes

from source.dungeon.EnemyList import EnemyTable, init_vanilla_sprites, vanilla_sprites, init_enemy_stats, EnemySprite
from source.dungeon.EnemyList import sprite_translation, overlord_translation
from RoomData import Position, DoorKind
from source.dungeon.RoomHeader import init_room_headers, RoomHeader
from source.dungeon.RoomList import Room0127, Room
from source.dungeon.RoomObject import RoomObject, DoorObject
from source.enemizer.OwEnemyList import init_vanilla_sprites_ow, vanilla_sprites_ow
from source.enemizer.SpriteSheets import init_sprite_sheets, init_sprite_requirements, SheetChoice
from source.classes.GFX import init_gfx_data


def convert_area_id_to_offset(area_id):
    if area_id < 0x40:
        return area_id
    if 0x40 <= area_id < 0x80:
        return area_id + 0x40
    if 0x90 <= area_id <= 0xCF:
        return area_id - 0x50
    raise Exception(f'{hex(area_id)} is not a valid area id for offset math')


class DataTables:
    def __init__(self):
        self.room_headers = None
        self.room_list = None
        self.sprite_sheets = None
        self.uw_enemy_table = None
        self.ow_enemy_table = None
        self.pot_secret_table = None
        self.overworld_sprite_sheets = None
        self.pointer_addresses = {
            # table: [data_start, data_size, pointer_table, references]
            'ow_sprites': [ 0x09CB41, None, (0x09C881, 0x09C901, 0x09CA21), None ],
            'uw_sprites': [ 0x09D92E, None, 0x09D62E, 0x09C298 ],
        }
        self.gfx_data = None

        # associated data
        self.sprite_requirements = None
        self.room_requirements = None
        self.enemy_stats = None
        self.enemy_damage = None
        self.bush_sprite_table = {}

        # enemizer conditions
        self.uw_enemy_denials = {}
        self.ow_enemy_denials = {}
        self.uw_enemy_drop_denials = {}
        self.sheet_choices = []
        denial_data = load_cached_yaml(['source', 'enemizer', 'enemy_deny.yaml'])
        for denial in denial_data['UwGeneralDeny']:
            self.uw_enemy_denials[denial[0], denial[1]] = {sprite_translation[x] for x in denial[2]}
        for denial in denial_data['OwGeneralDeny']:
            self.ow_enemy_denials[denial[0], denial[1]] = {sprite_translation[x] for x in denial[2]}
        for denial in denial_data['UwEnemyDrop']:
            self.uw_enemy_drop_denials[denial[0], denial[1]] = {sprite_translation[x] for x in denial[2]}
        weights = load_cached_yaml(['source', 'enemizer', 'enemy_weight.yaml'])
        self.uw_weights = {sprite_translation[k]: v for k, v in weights['UW'].items()}
        self.ow_weights = {sprite_translation[k]: v for k, v in weights['OW'].items()}
        sheet_weights = load_cached_yaml(['source', 'enemizer', 'sheet_weight.yaml'])
        for item in sheet_weights['SheetChoices']:
            choice = SheetChoice(tuple(item['slots']), item['assignments'], item['weight'])
            self.sheet_choices.append(choice)

    def write_to_rom(self, rom, colorize_pots=False, increase_bush_sprite_chance=False):
        if self.pot_secret_table.size() > 0x11c0:
            raise Exception('Pot table is too big for current area')
        self.pot_secret_table.write_pot_data_to_rom(rom, colorize_pots, self)
        for room_id, header in self.room_headers.items():
            data_location = (0x30DA00 + room_id * 14) & 0xFFFF
            rom.write_bytes(snes_to_pc(0x04F1E2) + room_id * 2, int16_as_bytes(data_location))
            header.write_to_rom(rom, snes_to_pc(0x30DA00))  # new header table, bank30, tables.asm
        room_start_address = 0x378000
        for room_id, room in self.room_list.items():
            rom.write_bytes(snes_to_pc(0x1F8000 + room_id * 3), int24_as_bytes(room_start_address))
            door_start, bytes_written = room.write_to_rom(snes_to_pc(room_start_address), rom)
            rom.write_bytes(snes_to_pc(0x1F83C0 + room_id * 3), int24_as_bytes(room_start_address + door_start))
            room_start_address += bytes_written
            if room_start_address > 0x380000:
                raise Exception('Room list exceeded bank size')
        #  size notes: bank 03 uses 140E bytes
        # bank 0A uses 372A bytes
        # bank 1F uses 77CE bytes: total is about a bank and a half
        # probably should reuse bank 1F if writing all the rooms out
        for area_id, sheet in self.overworld_sprite_sheets.items():
            if area_id in [0x80, 0x81]:
                offset = area_id - 0x80  # 02E575 for special areas?
                rom.write_byte(snes_to_pc(0x02E576+offset), sheet.id)
            else:
                offset = convert_area_id_to_offset(area_id)
                rom.write_byte(snes_to_pc(0x00FA81+offset), sheet.id)
            # _00FA81 is LW normal
            # _00FAC1 is LW post-aga
            # _00FB01 is DW
            # _00FA41 is rain state
        for sheet in self.sprite_sheets.values():
            sheet.write_to_rom(rom, snes_to_pc(0x00DB97))  # bank 00, SheetsTable_AA3
        self.write_ow_sprite_data_to_rom(rom)
        if self.uw_enemy_table.size() > 0x2800:
            raise Exception('Sprite table is too big for current area')
        self.uw_enemy_table.write_sprite_data_to_rom(rom, self.pointer_addresses)
        self.uw_enemy_table.check_special_bitmasks_size()
        self.uw_enemy_table.write_special_bitmask_table(rom)
        for sprite, stats in self.enemy_stats.items():
            # write health to rom
            if stats.health is not None:
                if isinstance(stats.health, tuple):
                    if sprite == EnemySprite.Octorok4Way:  # skip this one
                        continue
                    if sprite in special_health_table:
                        a1, a2 = special_health_table[sprite]
                        rom.write_byte(snes_to_pc(a1), stats.health[0])
                        rom.write_byte(snes_to_pc(a2), stats.health[1])
                else:
                    rom.write_byte(snes_to_pc(0x0DB173+int(sprite)), stats.health)
            # write damage class to rom
            if stats.damage is not None:
                if isinstance(stats.damage, tuple):
                    if sprite == EnemySprite.Octorok4Way:  # skip this one
                        continue
                    if sprite in special_damage_table:
                        a1, a2 = special_damage_table[sprite]
                        rom.write_byte(snes_to_pc(a1), stats.dmask | stats.damage[0])
                        rom.write_byte(snes_to_pc(a2), stats.dmask | stats.damage[1])
                else:
                    rom.write_byte(snes_to_pc(0x0DB266+int(sprite)), stats.dmask | stats.damage)
        # write damage table to rom
        for idx, damage_list in self.enemy_damage.items():
            rom.write_bytes(snes_to_pc(0x06F42D + idx * 3), damage_list)
        # write bush spawns to rom:
        for area_id, bush_sprite in self.bush_sprite_table.items():
            rom.write_byte(snes_to_pc(0x368120 + area_id), bush_sprite.sprite)
        if increase_bush_sprite_chance:
            rom.write_bytes(snes_to_pc(0x1AFBBB), [
                0x01, 0x0F, 0x0F, 0x0F, 0x0F, 0x0F, 0x0F, 0x12,
                0x0F, 0x01, 0x0F, 0x0F, 0x11, 0x0F, 0x0F, 0x03
            ])

    def write_ow_sprite_data_to_rom(self, rom):
        # calculate how big this table is going to be?
        bytes = sum(1+len(x)*3 for x in self.ow_enemy_table.values() if len(x) > 0)+1
        self.pointer_addresses['ow_sprites'][1] = bytes
        # ending_byte = 0x09CB3B + bytes
        max_per_state = {0: 0x40, 1: 0x90, 2: 0x82}  # dropped max on state 2 to steal space for extra sprites (Murahdahla, extra tutorial guard)

        pointer_address = snes_to_pc(self.pointer_addresses['ow_sprites'][2][0])
        self.pointer_addresses['ow_sprites'][0] = pointer_address + ((max_per_state[0] + max_per_state[1] + max_per_state[2]) * 2)
        data_pointer = self.pointer_addresses['ow_sprites'][0]
        empty_pointer = pc_to_snes(data_pointer) & 0xFFFF
        rom.write_byte(data_pointer, 0xff)
        cached_dark_world = {}
        data_pointer += 1
        for state in range(0, 3):
            if state > 0:  # move pointer to next section
                pointer_address += max_per_state[state-1] * 2
            for screen in range(0, max_per_state[state]):
                internal_screen_id = screen
                if state == 0:
                    internal_screen_id += 0x200
                if state == 2 and screen < 0x40:
                    internal_screen_id += 0x90
                # has no sprites
                if internal_screen_id not in self.ow_enemy_table or len(self.ow_enemy_table[internal_screen_id]) == 0:
                    rom.write_bytes(pointer_address + screen * 2, int16_as_bytes(empty_pointer))
                else:
                    if state == 2 and screen >= 0x40:  # state 2 uses state 1 pointer for screens >= 0x40
                        rom.write_bytes(pointer_address + screen * 2, cached_dark_world[screen])
                        # the sprites are already written out
                    elif len(self.ow_enemy_table[internal_screen_id]) > 0:
                        data_address = pc_to_snes(data_pointer) & 0xFFFF
                        ref = int16_as_bytes(data_address)
                        if screen >= 40:
                            cached_dark_world[screen] = ref
                        rom.write_bytes(pointer_address + screen * 2, ref)
                        for sprite in self.ow_enemy_table[internal_screen_id]:
                            data = sprite.sprite_data()
                            rom.write_bytes(data_pointer, data)
                            data_pointer += len(data)
                        rom.write_byte(data_pointer, 0xff)
                        data_pointer += 1
        # Check if OW sprite data has overwritten the UW sprite pointer table
        max_allowed_address = snes_to_pc(0x09D62E)
        if data_pointer > max_allowed_address:
            raise Exception(f'OW sprite data will cause the UW sprite pointer table to overwrite the pots pointer table. Data end: {hex(pc_to_snes(data_pointer))}, Max allowed: $09D62E')


special_health_table = {
    EnemySprite.Octorok: (0x068F76, 0x068F77),
    EnemySprite.HardhatBeetle: (0x06911F, 0x069120),
    EnemySprite.Tektite: (0x068D97, 0x068D98),
    EnemySprite.CricketRat: (0x068876, 0x068877),
    EnemySprite.Keese: (0x06888A, 0x06888B),
    EnemySprite.Snake: (0x0688A6, 0x0688A7),
    EnemySprite.Raven: (0x068965, 0x068966)
}

special_damage_table = {
    EnemySprite.Octorok: (0x068F74, 0x068F75),
    EnemySprite.Tektite: (0x068D99, 0x068D9A),
    EnemySprite.CricketRat: (0x068874, 0x068875),
    EnemySprite.Keese: (0x068888, 0x068889),
    EnemySprite.Snake: (0x0688A4, 0x0688A5),
    EnemySprite.Raven: (0x068963, 0x068964)
}


def init_data_tables(world, player):
    data_tables = DataTables()
    data_tables.room_headers = init_room_headers()
    data_tables.room_list = {}
    if world.pottery[player] not in ['none']:
        data_tables.room_list[0x0127] = Room0127
    data_tables.sprite_requirements = init_sprite_requirements()
    data_tables.sprite_sheets = init_sprite_sheets(data_tables.sprite_requirements)
    if world.customizer:
        sprite_sheet_overrides = world.customizer.get_sprite_sheets()
        if sprite_sheet_overrides:
            for sheet_id, slots in sprite_sheet_overrides.items():
                for slot, value in slots.items():
                    data_tables.sprite_sheets[sheet_id].sub_groups[slot] = value
    init_vanilla_sprites()
    data_tables.enemy_stats = init_enemy_stats()
    uw_table = data_tables.uw_enemy_table = EnemyTable()
    for room, sprite_list in vanilla_sprites.items():
        for sprite in sprite_list:
            uw_table.room_map[room].append(sprite.copy())
    data_tables.overworld_sprite_sheets = {}
    data_tables.ow_enemy_table = defaultdict(list)
    init_vanilla_sprites_ow()
    for area, sprite_list in vanilla_sprites_ow.items():
        for sprite in sprite_list:
            if sprite.bonk and world.shuffle_bonk_drops[player]:
                sprite.kind = EnemySprite.GreenRupee
            data_tables.ow_enemy_table[area].append(sprite.copy())
    data_tables.enemy_damage = {k: list(v) for k, v in world.damage_table[player].enemy_damage.items()}
    # todo: more denials based on enemy drops
    data_tables.gfx_data = init_gfx_data()
    return data_tables


def get_uw_enemy_table():
    init_vanilla_sprites()
    uw_table = EnemyTable()
    for room, sprite_list in vanilla_sprites.items():
        for sprite in sprite_list:
            uw_table.room_map[room].append(sprite.copy())
    return uw_table


def init_custom_rooms(world, player, custom_rooms):
    data_tables = world.data_tables[player]
    for room_id, room_data in custom_rooms.items():
        room_id = int(room_id, 16)
        if room_data['header']:
            data_bytes = [int(x, 16) for x in room_data['header']]
            data_tables.room_headers[room_id] = RoomHeader(room_id, data_bytes)

        if any(attr in room_data and room_data[attr] for attr in ['layout', 'layer1', 'layer2', 'layer3', 'doors']):
            room = data_tables.room_list[room_id] if room_id in data_tables.room_list else Room([], [], [], [])

            if room_data['layout']:
                room.layout = [int(x, 16) for x in room_data['layout']]
            if room_data['layer1']:
                room.layer1 = [RoomObject.factory(*[int(x, 16) if i != 0 else x for i, x in enumerate(obj)])
                               for obj in room_data['layer1']]
            if 'layer2' in room_data and room_data['layer2']:
                room.layer2 = [RoomObject.factory(*[int(x, 16) if i != 0 else x for i, x in enumerate(obj)])
                               for obj in room_data['layer2']]
            if 'layer3' in room_data and room_data['layer3']:
                room.layer3 = [RoomObject.factory(*[int(x, 16) if i != 0 else x for i, x in enumerate(obj)])
                               for obj in room_data['layer3']]
            if room_data['doors']:
                room.doors = [DoorObject(Position[pair[0]], DoorKind[pair[1]]) for pair in room_data['doors']]
            data_tables.room_list[room_id] = room


def init_custom_sprites(world, player, custom_sprites):
    """Initialize custom sprite placements for specified rooms.

    Args:
        world: World object
        player: Player number
        custom_sprites: Dict mapping room IDs to sprite lists

    Sprite format (5 or 4 params):
        [kind, tile_x, tile_y, layer, sub_type]  # Full format
        [kind, tile_x, tile_y, layer]             # sub_type defaults to 0x00

    kind can be either:
        - Hex string: "0x83"
        - English name: "Stalfos" (uses sprite_translation lookup)

    Example YAML:
        sprites:
          "0x02":
            - ["CricketRat", "0x12", "0x05", "0x01", "0x00"]  # CricketRat at x=0x12, y=0x05, layer=1
            - ["CricketRat", "0x15", "0x06", "0x01"]          # CricketRat at x=0x15, y=0x06, layer=1, sub_type=0x00
            - ["0x6D", "0x18", "0x09", "0x01"]                # Same as CricketRat (0x6D = CricketRat ID)
    """
    from source.dungeon.EnemyList import Sprite, sprite_translation

    data_tables = world.data_tables[player]
    for room_id, sprite_list in custom_sprites.items():
        room_id = int(room_id, 16)

        # Clear existing sprites for this room
        data_tables.uw_enemy_table.room_map[room_id] = []

        # Add custom sprites
        for sprite_data in sprite_list:
            # Parse sprite parameters: [kind, tile_x, tile_y, layer, sub_type (optional)]
            kind_param = sprite_data[0]

            # Handle both hex strings and English names
            if isinstance(kind_param, str) and kind_param.startswith('0x'):
                kind = int(kind_param, 16)
            elif kind_param in sprite_translation:
                kind = sprite_translation[kind_param]
            elif kind_param == 'Overlord' and sprite_data[4] in overlord_translation:
                kind = overlord_translation[sprite_data[4]]
            else:
                raise ValueError(f"Unknown sprite kind: {kind_param}")

            tile_x = int(sprite_data[1], 16)
            tile_y = int(sprite_data[2], 16)
            layer = int(sprite_data[3], 16)
            if kind_param == 'Overlord':
                sub_type = 0x07  # special sub type
            else:
                sub_type = int(sprite_data[4], 16) if len(sprite_data) > 4 else 0x00

            # Create sprite using factory
            sprite = Sprite.factory(room_id, kind, tile_x, tile_y, layer, sub_type)
            data_tables.uw_enemy_table.room_map[room_id].append(sprite)



