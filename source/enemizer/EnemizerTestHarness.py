from types import SimpleNamespace
from collections import Counter, defaultdict

from source.dungeon.EnemyList import enemy_names, SpriteType
from source.enemizer.Enemizer import randomize_underworld_rooms, randomize_overworld_enemies
from source.enemizer.SpriteSheets import randomize_underworld_sprite_sheets, randomize_overworld_sprite_sheets
from source.rom.DataTables import init_data_tables
from source.enemizer.DamageTables import DamageTable
import RaceRandom as random


def calculate_odds():
    ctr_uw = Counter()
    ctr_ow = Counter()
    for trial in range(0, 100):
        world = SimpleNamespace(pottery={1: 'none'}, damage_table={1: DamageTable()})
        data_tables = init_data_tables(world, 1)

        randomize_underworld_sprite_sheets(data_tables.sprite_sheets, data_tables)
        randomize_overworld_sprite_sheets(data_tables.sprite_sheets)

        for num in range(65, 124):
            sheet = data_tables.sprite_sheets[num]
            ret = []
            for req in data_tables.sprite_requirements.values():
                if not isinstance(req, dict) and sheet.valid_sprite(req) and not req.overlord and not req.static:
                    ret.append(enemy_names[req.sprite])
            for x in ret:
                ctr_uw[x] += 1

        for num in range(1, 64):
            sheet = data_tables.sprite_sheets[num]
            ret = []
            for req in data_tables.sprite_requirements.values():
                if not isinstance(req, dict) and sheet.valid_sprite(req) and not req.overlord and not req.static:
                    ret.append(enemy_names[req.sprite])
            for x in ret:
                ctr_ow[x] += 1
    ttl = sum(ctr_uw.values())
    print(f'UW:  # Total {ttl}')
    for k, v in ctr_uw.items():
        weight = round(.01 * ttl * 100 / v)
        print(f'  {k}: {weight}   # {v*100/ttl:.5f}% raw:{v}')
    ttl = sum(ctr_ow.values())
    print(f'OW:  # Total {ttl}')
    for k, v in ctr_ow.items():
        weight = round(.01 * ttl * 100 / v)
        print(f'  {k}: {weight}  # {v*100/ttl:.5f}% raw:{v}')


if __name__ == '__main__':
    # calculate_odds()
    random.seed(42)
    #
    frequency = Counter()
    sheet_ctr = Counter()
    ctr_uw = Counter()
    ctr_ow = Counter()
    sheet_thing = Counter()
    sheet_sub_groups = defaultdict(set)

    for trial in range(0, 100):
        world = SimpleNamespace(pottery={1: 'none'}, damage_table={1: DamageTable()}, any_enemy_logic={1: 'allow_all'},
                                dropshuffle={1: 'off'})
        data_tables = init_data_tables(world, 1)
        stats = data_tables.enemy_stats

        def randomize_able_sprite(sprite, stats):
            if sprite.static:
                return False
            if sprite.sub_type == 0x7 and sprite.kind != 0x9:
                return False
            if sprite.sub_type == 0x7 and sprite.kind == 0x9:
                return True
            return sprite.kind not in stats or not stats[sprite.kind].static

        if trial == 0:
            print(f'    Underworld:')
            for room_id, enemy_list in data_tables.uw_enemy_table.room_map.items():
                print(f'      {hex(room_id)}:')
                for i, sprite in enumerate(enemy_list):
                    if randomize_able_sprite(sprite, stats):
                        print(f'        {i}: {str(sprite)}')
            print(f'    Overworld:')
            for area, enemy_list in data_tables.ow_enemy_table.items():
                print(f'      {hex(area)}:')
                for i, sprite in enumerate(enemy_list):
                    if randomize_able_sprite(sprite, stats):
                        print(f'        {i}: {str(sprite)}')

        randomize_underworld_sprite_sheets(data_tables.sprite_sheets, data_tables, {})
        randomize_underworld_rooms(data_tables, world, 1)
        randomize_overworld_sprite_sheets(data_tables.sprite_sheets, data_tables, {})
        randomize_overworld_enemies(data_tables)

        for room_id, enemy_list in data_tables.uw_enemy_table.room_map.items():
            # print(f'Room {hex(room_id)}:')
            for i, sprite in enumerate(enemy_list):
                if randomize_able_sprite(sprite, stats):
                    result = str(sprite)
                    frequency[result] += 1
        for area, enemy_list in data_tables.ow_enemy_table.items():
            for i, sprite in enumerate(enemy_list):
                if randomize_able_sprite(sprite, stats):
                    result = str(sprite)
                    frequency[result] += 1

        for num in range(65, 124):
            if num in {65, 69, 71, 78, 79, 82, 88, 98}:
                continue
            sheet = data_tables.sprite_sheets[num]
            ret = []
            for req in data_tables.sprite_requirements.values():
                if not isinstance(req, dict) and sheet.valid_sprite(req) and not req.overlord and not req.static:
                    ret.append(enemy_names[req.sprite])
            for x in ret:
                ctr_uw[x] += 1
                sheet_ctr[x] += 1
            key = tuple(sorted(ret))
            sheet_thing[key] += 1
            sheet_sub_groups[key].add(tuple(sheet.sub_groups))

        for num in range(1, 64):
            if num == 6:
                continue
            sheet = data_tables.sprite_sheets[num]
            ret = []
            for req in data_tables.sprite_requirements.values():
                if not isinstance(req, dict) and sheet.valid_sprite(req) and not req.overlord and not req.static:
                    ret.append(enemy_names[req.sprite])
            for x in ret:
                ctr_ow[x] += 1
                sheet_ctr[x] += 1
            key = tuple(sorted(ret))
            sheet_thing[key] += 1
            sheet_sub_groups[key].add(tuple(sheet.sub_groups))

    total_sheets = sum(sheet_thing.values())
    ttl = sum(ctr_uw.values())
    print(f'UW:  # Total {ttl}')
    for k in sorted(list(ctr_uw.keys())):
        v = ctr_uw[k]
        weight = round(.01 * ttl * 100 / v)
        print(f'  {k}: {weight}   # {v*100/ttl:.5f}% raw:{v} {v*100/total_sheets:.5f}%')
    ttl = sum(ctr_ow.values())
    print(f'OW:  # Total {ttl}')
    for k in sorted(list(ctr_ow.keys())):
        v = ctr_ow[k]
        weight = round(.01 * ttl * 100 / v)
        print(f'  {k}: {weight}  # {v*100/ttl:.5f}% raw:{v} {v*100/total_sheets:.5f}%')

    ttl = sum(sheet_ctr.values())
    print(f'Sheet:  # Total {ttl}')
    for k, v in sheet_ctr.items():
        print(f'  {k} {v*100/ttl:.5f}% raw:{v} {v*100/total_sheets:.5f}%')

    ttl = sum(frequency.values())
    print(f'Total: {ttl}')
    for enemy, freq in frequency.items():
        print(f'{enemy} {freq*100/ttl:.5f}% raw:{freq}')

    ttl = sum(sheet_thing.values())
    print(f'Total Sheets?: {ttl}')

    def rejoin(list_of_things):
        return f'[{",".join([str(i) for i in list_of_things])}]'

    for items, cnt in sheet_thing.items():
        print(f'{",".join(items)} {cnt} {cnt*100/ttl:.5f}% {",".join([rejoin(x) for x in sheet_sub_groups[items]])}')

    #             if result not in column_headers:
    #                 column_headers[result] = None
    #             stats[(room_id, i)][result] += 1
    # with open('result.csv', 'w') as result_file:
    #     result_file.write('room_id,slot,')
    #     result_file.write(','.join(column_headers.keys()))
    #     result_file.write('\n')
    #
    #     for key, counter in stats.items():
    #         rid, slot = key
    #         result_file.write(f'{rid},{slot}')
    #         for result_item in column_headers.keys():
    #             result_file.write(f',{counter[result_item]}')
    #         result_file.write('\n')

