import RaceRandom as random
from Utils import snes_to_pc

from source.dungeon.EnemyList import EnemySprite, SpriteType, Sprite
from source.dungeon.RoomList import boss_rooms, gt_boss_room, Room0006
from source.dungeon.RoomObject import RoomObject
from source.enemizer.SpriteSheets import required_boss_sheets


def get_dungeon_boss_room(dungeon_name, level):
    if level is None:
        return boss_rooms[dungeon_name]
    return gt_boss_room[level]


def get_dungeon_boss_default(dungeon_name, level):
    if level is None:
        return boss_defaults[dungeon_name]
    return gt_boss_defaults[level]


def add_shell_to_boss_room(data_tables, dungeon_name, level, shell_id):
    room_id, room, shell_x, shell_y, clear_layer_2 = get_dungeon_boss_room(dungeon_name, level)
    if room_id in data_tables.room_list:
        room = data_tables.room_list[room_id]
    else:
        data_tables.room_list[room_id] = room
    room.layout[0] = 0xF0
    if clear_layer_2:
        room.layer2.clear()
    y_offset = 0 if shell_id == 0xF95 else -2
    room.layer2.append(RoomObject.subtype3_factory(shell_x, shell_y + y_offset, shell_id))


def remove_shell_from_boss_room(data_tables, dungeon_name, level, shell_id):
    room_id, room, shell_x, shell_y, clear_layer_2 = get_dungeon_boss_room(dungeon_name, level)
    if room_id in data_tables.room_list:
        room = data_tables.room_list[room_id]
    else:
        data_tables.room_list[room_id] = room
    room.layer2[:] = [obj for obj in room.layer2 if not obj.matches_oid(shell_id)]


def remove_water_tiles(data_tables):
    room = Room0006
    if 0x6 in data_tables.room_list:
        room = data_tables.room_list[0x6]
    else:
        data_tables.room_list[0x6] = room
    room.layer1.clear()


def create_sprite(super_tile, kind, sub_type, layer, tile_x, tile_y):
    return Sprite(super_tile, kind, sub_type, layer, tile_x, tile_y, None, False, None)


def add_armos_to_list(sprite_list, room_id):
    sprite_list.insert(0, create_sprite(room_id, EnemySprite.ArmosKnight, 0x00, 0, 0x04, 0x05))
    sprite_list.insert(1, create_sprite(room_id, EnemySprite.ArmosKnight, 0x00, 0, 0x07, 0x05))
    sprite_list.insert(2, create_sprite(room_id, EnemySprite.ArmosKnight, 0x00, 0, 0x0a, 0x05))
    sprite_list.insert(3, create_sprite(room_id, EnemySprite.ArmosKnight, 0x00, 0, 0x0a, 0x08))
    sprite_list.insert(4, create_sprite(room_id, EnemySprite.ArmosKnight, 0x00, 0, 0x07, 0x08))
    sprite_list.insert(5, create_sprite(room_id, EnemySprite.ArmosKnight, 0x00, 0, 0x04, 0x08))
    sprite_list.insert(6, create_sprite(room_id, 0x19, SpriteType.Overlord, 0, 0x07, 0x08))


def add_lanmolas_to_list(sprite_list, room_id):
    sprite_list.insert(0, create_sprite(room_id, EnemySprite.Lanmolas, 0x00, 0, 0x06, 0x07))
    sprite_list.insert(1, create_sprite(room_id, EnemySprite.Lanmolas, 0x00, 0, 0x09, 0x07))
    sprite_list.insert(2, create_sprite(room_id, EnemySprite.Lanmolas, 0x00, 0, 0x07, 0x09))


def add_moldorm_to_list(sprite_list, room_id):
    sprite_list.insert(0, create_sprite(room_id, EnemySprite.Moldorm, 0x00, 0, 0x09, 0x09))


def add_helmasaur_king_to_list(sprite_list, room_id):
    sprite_list.insert(0, create_sprite(room_id, EnemySprite.HelmasaurKing, 0x00, 0, 0x07, 0x06))


def add_arrghus_to_list(sprite_list, room_id):
    sprite_list.insert(0, create_sprite(room_id, EnemySprite.Arrghus, 0x00, 0, 0x07, 0x07))
    sprite_list.insert(1, create_sprite(room_id, EnemySprite.Arrghi, 0x00, 0, 0x07, 0x07))
    sprite_list.insert(2, create_sprite(room_id, EnemySprite.Arrghi, 0x00, 0, 0x07, 0x07))
    sprite_list.insert(3, create_sprite(room_id, EnemySprite.Arrghi, 0x00, 0, 0x07, 0x07))
    sprite_list.insert(4, create_sprite(room_id, EnemySprite.Arrghi, 0x00, 0, 0x07, 0x07))
    sprite_list.insert(5, create_sprite(room_id, EnemySprite.Arrghi, 0x00, 0, 0x07, 0x07))
    sprite_list.insert(6, create_sprite(room_id, EnemySprite.Arrghi, 0x00, 0, 0x07, 0x07))
    sprite_list.insert(7, create_sprite(room_id, EnemySprite.Arrghi, 0x00, 0, 0x07, 0x07))
    sprite_list.insert(8, create_sprite(room_id, EnemySprite.Arrghi, 0x00, 0, 0x07, 0x07))
    sprite_list.insert(9, create_sprite(room_id, EnemySprite.Arrghi, 0x00, 0, 0x07, 0x07))
    sprite_list.insert(10, create_sprite(room_id, EnemySprite.Arrghi, 0x00, 0, 0x07, 0x07))
    sprite_list.insert(11, create_sprite(room_id, EnemySprite.Arrghi, 0x00, 0, 0x07, 0x07))
    sprite_list.insert(12, create_sprite(room_id, EnemySprite.Arrghi, 0x00, 0, 0x07, 0x07))
    sprite_list.insert(13, create_sprite(room_id, EnemySprite.Arrghi, 0x00, 0, 0x07, 0x07))


def add_mothula_to_list(sprite_list, room_id):
    sprite_list.insert(0, create_sprite(room_id, EnemySprite.Mothula, 0x00, 0, 0x08, 0x06))


def add_blind_to_list(sprite_list, room_id):
    sprite_list.insert(0, create_sprite(room_id, EnemySprite.Blind, 0x00, 0, 0x09, 0x05))


def add_kholdstare_to_list(sprite_list, room_id):
    sprite_list.insert(0, create_sprite(room_id, EnemySprite.KholdstareShell, 0x00, 0, 0x07, 0x05))
    sprite_list.insert(1, create_sprite(room_id, EnemySprite.FallingIce, 0x00, 0, 0x07, 0x05))
    sprite_list.insert(2, create_sprite(room_id, EnemySprite.Kholdstare, 0x00, 0, 0x07, 0x05))


def add_vitreous_to_list(sprite_list, room_id):
    sprite_list.clear()  # vitreous does not play nice which other sprites on the tile, just kill them
    sprite_list.append(create_sprite(room_id, EnemySprite.Vitreous, 0x00, 0, 0x07, 0x05))


def add_trinexx_to_list(sprite_list, room_id):
    sprite_list.insert(0, create_sprite(room_id, EnemySprite.TrinexxRockHead, 0x00, 0, 0x07, 0x05))
    sprite_list.insert(1, create_sprite(room_id, EnemySprite.TrinexxFireHead, 0x00, 0, 0x07, 0x05))
    sprite_list.insert(2, create_sprite(room_id, EnemySprite.TrinexxIceHead, 0x00, 0, 0x07, 0x05))


def boss_adjust(world, player):
    data_tables = world.data_tables[player]
    for dungeon in world.get_dungeons(player):
        for level, boss in dungeon.bosses.items():
            if not boss or boss.name in ['Agahnim', 'Agahnim2']:
                continue
            default_boss = get_dungeon_boss_default(dungeon.name, level)
            room_data = get_dungeon_boss_room(dungeon.name, level)
            room_id = room_data[0]
            if default_boss != boss.name:
                sprite_list = data_tables.uw_enemy_table.room_map[room_id]
                data = boss_room_remove_data[room_id]
                del sprite_list[:data]
                add_func, sprite_type = boss_addition_table[boss.name]
                add_func(sprite_list, room_id)
                if len(sprite_list) > 15:
                    del sprite_list[15:]
                data_tables.room_headers[room_id].sprite_sheet = required_boss_sheets[sprite_type]


def boss_writes(world, player, rom):
    rom.write_byte(snes_to_pc(0x368107), 1)  # centralize drops
    eye_number = random.randint(0, 8)  # randomize moldorm eyes (var + 1)
    rom.write_byte(snes_to_pc(0x368102), eye_number)  # enemizer flag
    rom.write_byte(snes_to_pc(0x1DDBB3), eye_number)  # loop variable
    data_tables = world.data_tables[player]
    arrghus_can_swim = True
    water_tiles_on = True
    for dungeon in world.get_dungeons(player):
        for level, boss in dungeon.bosses.items():
            if not boss or boss.name in ['Agahnim', 'Agahnim2']:
                continue
            room_data = get_dungeon_boss_room(dungeon.name, level)
            room_id = room_data[0]
            # room changes
            if boss.name == 'Arrghus' and (dungeon.name != 'Swamp Palace' or level is not None):
                rom.write_byte(snes_to_pc(0x0DB6BE), 0)   # arrghus can stand on ground
                arrghus_can_swim = False
            if boss.name != 'Arrghus' and dungeon.name == 'Swamp Palace' and level is None:
                remove_water_tiles(data_tables)
                water_tiles_on = False
            if boss.name == 'Trinexx' and (dungeon.name != 'Turtle Rock' or level is not None):
                add_shell_to_boss_room(data_tables, dungeon.name, level, 0xFF2)
                data_tables.room_headers[room_id].byte_0 = 0x60
                data_tables.room_headers[room_id].effect = 4
                # $2E, $98, $FF (original shell)
                # disable trinexx ice breath with No-ops if there's a trinexx anywhere outside TR
                rom.write_bytes(snes_to_pc(0x09B37E), [0xEA, 0xEA, 0xEA, 0xEA])
            if boss.name == 'Kholdstare' and (dungeon.name != 'Ice Palace' or level is not None):
                add_shell_to_boss_room(data_tables, dungeon.name, level, 0xF95)
                data_tables.room_headers[room_id].byte_0 = 0xE0
                data_tables.room_headers[room_id].effect = 1
            if boss.name != 'Trinexx' and dungeon.name == 'Turtle Rock' and level is None:
                remove_shell_from_boss_room(data_tables, dungeon.name, level, 0xFF2)
            if boss.name != 'Kholdstare' and dungeon.name == 'Ice Palace' and level is None:
                remove_shell_from_boss_room(data_tables, dungeon.name, level, 0xF95)
            if boss.name != 'Blind' and dungeon.name == 'Thieves Town' and level is None:
                rom.write_byte(snes_to_pc(0x368101), 1)  # set blind boss door flag
                # maiden is deleted
                del data_tables.uw_enemy_table.room_map[0x45][0]
        if not arrghus_can_swim and water_tiles_on:
            remove_water_tiles(data_tables)


boss_defaults = {
    'Eastern Palace': 'Armos Knights',
    'Desert Palace': 'Lanmolas',
    'Tower of Hera': 'Moldorm',
    'Palace of Darkness': 'Helmasaur King',
    'Swamp Palace': 'Arrghus',
    'Skull Woods': 'Mothula',
    'Thieves Town': 'Blind',
    'Ice Palace': 'Kholdstare',
    'Misery Mire': 'Vitreous',
    'Turtle Rock': 'Trinexx',
}

gt_boss_defaults = {
    'bottom': 'Armos Knights',
    'middle': 'Lanmolas',
    'top': 'Moldorm',
}

boss_room_remove_data = {
    6: 14, 7: 1, 0x1c: 7, 0x29: 1, 0x33: 3, 0x4d: 1, 0x5a: 1,
    0x6c: 3, 0x90: 1, 0xa4: 2, 0xac: 1, 0xc8: 7, 0xde: 3
}

boss_addition_table = {
    'Armos Knights': (add_armos_to_list, EnemySprite.ArmosKnight),
    'Lanmolas': (add_lanmolas_to_list, EnemySprite.Lanmolas),
    'Moldorm': (add_moldorm_to_list, EnemySprite.Moldorm),
    'Helmasaur King': (add_helmasaur_king_to_list, EnemySprite.HelmasaurKing),
    'Arrghus': (add_arrghus_to_list, EnemySprite.Arrghus),
    'Mothula': (add_mothula_to_list, EnemySprite.Mothula),
    'Blind': (add_blind_to_list, EnemySprite.Blind),
    'Kholdstare': (add_kholdstare_to_list, EnemySprite.Kholdstare),
    'Vitreous': (add_vitreous_to_list, EnemySprite.Vitreous),
    'Trinexx': (add_trinexx_to_list,  EnemySprite.TrinexxRockHead)
}
