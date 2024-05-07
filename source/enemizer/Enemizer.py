import RaceRandom as random
from Utils import snes_to_pc

from source.dungeon.EnemyList import SpriteType, EnemySprite, sprite_translation
from source.dungeon.RoomList import Room010C
from source.enemizer.SpriteSheets import sub_group_choices
from source.enemizer.SpriteSheets import randomize_underworld_sprite_sheets, randomize_overworld_sprite_sheets
from source.enemizer.TilePattern import tile_patterns

shutter_sprites = {
    0xb8: {0, 1, 2, 3, 4, 5}, 0xb: {4, 5, 6, 7, 8, 9}, 0x1b: {3, 4, 5}, 0x4b: {0, 3, 4}, 0x4: {9, 13, 14},
    0x24: {3, 4, 5, 6},  # not sure about 6 - bunny beam under pot
    0x28: {0, 1, 2, 3, 4}, 0xe: {0, 1, 2, 3}, 0x2e: {0, 1, 2, 3, 4, 5}, 0x3e: {1, 2}, 0x6e: {0, 1, 2, 3, 4},
    0x31: {7, 8, 10}, 0x44: {2, 3, 5}, 0x45: {1, 2, 3},  0x53: {5, 6, 8, 9, 10}, 0x75: {0, 2, 3, 4, 5},
    0x85: {2, 3, 4, 5}, 0x5d: {0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12}, 0x6b: {5, 6, 7, 8, 9, 10, 11, 12, 13},
    0x6d: {0, 1, 2, 3, 4, 5, 6, 7, 8}, 0x7b: {2, 3, 4, 5, 8, 9, 10}, 0x7d: {4, 5, 6, 7, 8, 10}, 0x8d: {0, 1, 2, 3, 4},
    0xa5: {0, 1, 2, 3, 4, 5, 6, 7}, 0x71: {0, 1}, 0xd8: {0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10},
    0xb0: {0, 1, 2, 3, 4, 5, 7, 8, 9, 10}, 0xc0: {0, 1, 2}, 0xe0: {0, 1, 2, 3}, 0xb2: {5, 6, 7, 10, 11},
    0xd2: {0, 1, 2, 3, 4, 5, 6, 7, 8, 9}, 0xef: {0, 1, 2}, 0x10c: {4, 5, 6, 7}, 0x123: {0, 1, 2, 3},
    0xee: {0, 1, 2, 3, 4}  # low health traversal
}


def setup_specific_requirements(data_tables):
    requirements = data_tables.sprite_requirements
    water_groups = set()
    water_sub_groups = {0: set(), 1: set(), 2: set(), 3: set()}
    killable_groups = set()
    killable_sub_groups = {0: set(), 1: set(), 2: set(), 3: set()}
    key_groups = set()
    key_sub_groups = {0: set(), 1: set(), 2: set(), 3: set()}

    for sid, requirement in requirements.items():
        if isinstance(requirement, dict):
            continue
        if requirement.good_for_uw_water():
            water_groups.update(requirement.groups)
            for i in range(0, 4):
                limited = [x for x in requirement.sub_groups[i] if x in sub_group_choices[i]]
                water_sub_groups[i].update(limited)
        if requirement.good_for_shutter([]):
            killable_groups.update(requirement.groups)
            for i in range(0, 4):
                killable_sub_groups[i].update(requirement.sub_groups[i])
            if requirement.can_drop:
                key_groups.update(requirement.groups)
                for i in range(0, 4):
                    key_sub_groups[i].update(requirement.sub_groups[i])
    return water_groups, water_sub_groups, killable_groups, killable_sub_groups, key_groups, key_sub_groups


def get_possible_sheets(room_id, data_tables, specific, all_sheets, uw_sheets):
    # forced sprites for room
    requirements = data_tables.sprite_requirements

    water_groups, water_sub_groups, killable_groups, killable_sub_groups, key_groups, key_sub_groups = specific

    # forced_req = set()
    key_needed = False
    killable_needed = room_id in shutter_sprites

    for sheet in all_sheets:
        if room_id in sheet.room_set:
            return [sheet]

    match_all_room_groups = set()
    match_all_sub_groups = {0: set(), 1: set(), 2: set(), 3: set()}
    # match_all_sub_groups = {0: set(uw_sub_group_choices[0] + [70, 72]), 1: set(uw_sub_group_choices[1] + [13, 73]),
    #                          2: set(uw_sub_group_choices[2] + [19]), 3: set(uw_sub_group_choices[3] + [25, 68])}
    
    for sprite in data_tables.uw_enemy_table.room_map[room_id]:
        sprite_secondary = 0 if sprite.sub_type != SpriteType.Overlord else sprite.sub_type
        key = (sprite.kind, sprite_secondary)
        if key not in requirements:
            continue
        req = requirements[key]
        if isinstance(req, dict):
            req = req[room_id]
        if req.static or not req.can_randomize or sprite.static:
            if req.groups:
                match_all_room_groups.intersection_update(req.groups)
                if not match_all_room_groups:
                    match_all_room_groups = set(req.groups)
            for i in range(0, 4):
                if req.sub_groups[i]:
                    match_all_sub_groups[i].intersection_update(req.sub_groups[i])
                    if not match_all_sub_groups[i]:
                        match_all_sub_groups[i] = set(req.sub_groups[i])
            # forced_req.add(req)
            if sprite.drops_item:
                key_needed = True

    match_any_room_groups = set()
    match_any_sub_groups = {0: set(), 1: set(), 2: set(), 3: set()}
    exclude_all_groups = set()
    exclude_all_sub_groups = {0: set(), 1: set(), 2: set(), 3: set()}

    if room_id in data_tables.room_requirements:
        required_groups = data_tables.room_requirements[room_id]
        for idx, grp in enumerate(required_groups):
            if grp is not None:
                if isinstance(grp, tuple):
                    match_any_sub_groups[idx].update(grp)
                else:
                    match_all_sub_groups[idx] = {grp}

    if key_needed:
        if key_groups:
            match_any_room_groups.update(key_groups)
            for i in range(0, 4):
                if key_sub_groups[i]:
                    match_any_sub_groups[i].update(key_sub_groups[i])
    elif killable_needed:
        if killable_groups:
            match_any_room_groups.update(killable_groups)
            for i in range(0, 4):
                if killable_sub_groups[i]:
                    match_any_sub_groups[i].update(killable_sub_groups[i])

    possible_sheets = []
    for sheet in uw_sheets:
        if match_all_room_groups and sheet.id not in match_all_room_groups:
            continue
        if any(match_all_sub_groups[i] and sheet.sub_groups[i] not in match_all_sub_groups[i] for i in range(0, 4)):
            continue
        if exclude_all_groups and sheet.id in exclude_all_groups:
            continue
        if any(exclude_all_sub_groups[i] and sheet.sub_groups[i] in exclude_all_sub_groups[i] for i in range(0, 4)):
            continue
        if match_any_room_groups and sheet.id not in match_any_sub_groups:
            continue
        test_subs = [i for i in range(0, 4) if match_any_sub_groups[i]]
        if test_subs and all(sheet.sub_groups[i] not in match_any_sub_groups[i] for i in test_subs):
            continue
        possible_sheets.append(sheet)
    return possible_sheets


def get_possible_ow_sheets(area_id, all_sheets, ow_sheets, data_tables):
    requirements = data_tables.sprite_requirements

    for sheet in all_sheets:
        if area_id in sheet.room_set:
            return [sheet]

    match_all_room_groups = set()
    match_all_sub_groups = {0: set(), 1: set(), 2: set(), 3: set()}

    for sprite in data_tables.ow_enemy_table[area_id]:
        sprite_secondary = 0 if sprite.sub_type != SpriteType.Overlord else sprite.sub_type
        key = (sprite.kind, sprite_secondary)
        if key not in requirements:
            continue
        req = requirements[key]
        if isinstance(req, dict):
            req = req[area_id]
        if req.static or not req.can_randomize:
            if req.groups:
                match_all_room_groups.intersection_update(req.groups)
                if not match_all_room_groups:
                    match_all_room_groups = set(req.groups)
            for i in range(0, 4):
                if req.sub_groups[i]:
                    match_all_sub_groups[i].intersection_update(req.sub_groups[i])
                    if not match_all_sub_groups[i]:
                        match_all_sub_groups[i] = set(req.sub_groups[i])

    possible_sheets = []
    for sheet in ow_sheets:
        if match_all_room_groups and sheet.id not in match_all_room_groups:
            continue
        if any(match_all_sub_groups[i] and sheet.sub_groups[i] not in match_all_sub_groups[i] for i in range(0, 4)):
            continue
        possible_sheets.append(sheet)
    return possible_sheets


ignore_sheets_uw = {65, 69, 71, 78, 79, 82, 88, 98}
ignore_sheets_ow = {6}


def find_candidate_sprites(data_tables, sheet_range, uw=True):
    requirements = data_tables.sprite_requirements
    sprite_candidates = []
    sheet_candidates = []
    all_sheets = []

    candidate_groups = set()
    candidate_sub_groups = {0: set(), 1: set(), 2: set(), 3: set()}

    for k, r in requirements.items():
        if isinstance(r, dict):
            continue
        valid_flag = (uw and r.uw_valid) or (not uw and r.ow_valid)
        if not r.static and valid_flag and not r.dont_use:
            candidate_groups.update(r.groups)
            for i in range(0, 4):
                candidate_sub_groups[i].update(r.sub_groups[i])
            sprite_candidates.append(k)

    for num in sheet_range:
        sheet = data_tables.sprite_sheets[num]
        all_sheets.append(sheet)
        if (uw and num in ignore_sheets_uw) or (not uw and num in ignore_sheets_ow):
            continue
        if candidate_groups and sheet not in candidate_groups:
            continue
        test_subs = [i for i in range(0, 4) if candidate_sub_groups[i]]
        if test_subs and all(sheet.sub_groups[i] not in candidate_sub_groups[i] for i in test_subs):
            continue
        sheet_candidates.append(sheet)

    return sprite_candidates, sheet_candidates, all_sheets


def get_possible_enemy_sprites(room_id, sheet, uw_sprites, data_tables):
    ret = []
    for sprite in uw_sprites:
        requirement = data_tables.sprite_requirements[sprite]
        if isinstance(requirement, dict):
            requirement = requirement[room_id]
        if sheet.valid_sprite(requirement) and requirement.can_spawn_in_room(room_id):
            ret.append(requirement)
    return ret


def get_possible_enemy_sprites_ow(sheet, sprites, data_tables):
    ret = []
    for sprite in sprites:
        requirement = data_tables.sprite_requirements[sprite]
        if isinstance(requirement, dict):
            continue
        if sheet.valid_sprite(requirement) and requirement.ow_valid:
            ret.append(requirement)
    return ret


def get_randomize_able_sprites(room_id, data_tables):
    sprite_table = {}
    for idx, sprite in enumerate(data_tables.uw_enemy_table.room_map[room_id]):
        sprite_secondary = 0 if sprite.sub_type != SpriteType.Overlord else sprite.sub_type
        key = (sprite.kind, sprite_secondary)
        if key not in data_tables.sprite_requirements:
            continue
        req = data_tables.sprite_requirements[key]
        if isinstance(req, dict):
            continue
        if not req.static and req.can_randomize and not sprite.static:
            sprite_table[idx] = sprite
    return sprite_table


def get_randomize_able_sprites_ow(area_id, data_tables):
    sprite_table = {}
    for idx, sprite in enumerate(data_tables.ow_enemy_table[area_id]):
        sprite_secondary = 0 if sprite.sub_type != SpriteType.Overlord else sprite.sub_type
        key = (sprite.kind, sprite_secondary)
        if key not in data_tables.sprite_requirements:
            continue
        req = data_tables.sprite_requirements[key]
        if isinstance(req, dict):
            continue
        if not req.static and req.can_randomize and not sprite.static:
            sprite_table[idx] = sprite
    return sprite_table


sprite_limiter = {
    EnemySprite.Debirando: 2,
    EnemySprite.DebirandoPit: 2,
    EnemySprite.Hinox: 2,
    EnemySprite.Sluggula: 2,
    EnemySprite.BombGuard: 2,
    EnemySprite.Beamos: 2,
    EnemySprite.Gibo: 2,
    # EnemySprite.CannonTrooper: 2, ??
    EnemySprite.WallCannonHorzTop: 2,
    EnemySprite.WallCannonHorzBottom: 2,
    EnemySprite.WallCannonVertLeft: 2,
    EnemySprite.WallCannonVertRight: 2,
    EnemySprite.BlueArcher: 2,
    EnemySprite.BlueGuard: 2,
    EnemySprite.GreenGuard: 2,
    EnemySprite.RedSpearGuard: 2,
    EnemySprite.RedJavelinGuard: 2,
    EnemySprite.AntiFairyCircle: 4
}


def exceeds_sprite_limit(limit, sprite):
    return sprite_limiter[sprite.sprite]-1+limit > 15 if sprite.sprite in sprite_limiter else False


def randomize_underworld_rooms(data_tables, world, player, custom_uw):
    any_enemy_logic = world.any_enemy_logic[player]
    enemy_drops_active = world.dropshuffle[player] in ['underworld']
    specific = setup_specific_requirements(data_tables)
    uw_candidates, uw_sheets, all_sheets = find_candidate_sprites(data_tables, range(65, 124))
    for room_id in range(0, 0x128):
        if room_id in {0, 1, 3, 6, 7, 0xd, 0x14, 0x20, 0x29, 0x30, 0x33,
                       0x4d, 0x5a, 0x90, 0xa4, 0xac, 0xc8, 0xde}:
            continue
        current_sprites = data_tables.uw_enemy_table.room_map[room_id]
        sprite_limit = sum(sprite_limiter[x.kind] if x.kind in sprite_limiter else 1 for x in current_sprites)
        if room_id in {0x3f, 0x44, 0x45, 0x93, 0xce, 0x117}:
            sprite_limit += 1  # for liftable blocks see PotFlags.Block in PotShuffle
        randomizeable_sprites = get_randomize_able_sprites(room_id, data_tables)
        if not randomizeable_sprites:
            candidate_sheets = get_possible_sheets(room_id, data_tables, specific, all_sheets, uw_sheets)
            chosen_sheet = random.choice(candidate_sheets)
            data_tables.room_headers[room_id].sprite_sheet = chosen_sheet.id - 0x40
        if randomizeable_sprites:
            candidate_sheets = get_possible_sheets(room_id, data_tables, specific, all_sheets, uw_sheets)
            done = False
            while not done:
                chosen_sheet = random.choice(candidate_sheets)
                data_tables.room_headers[room_id].sprite_sheet = chosen_sheet.id - 0x40
                candidate_sprites = get_possible_enemy_sprites(room_id, chosen_sheet, uw_candidates, data_tables)
                randomized = True
                # wallmaster in hera basement throws off hera basement key code
                wallmaster_chosen = room_id in {0x0039, 0x0049, 0x0056, 0x0057, 0x0068, 0x0087, 0x008d}
                for i, sprite in randomizeable_sprites.items():
                    if room_id in custom_uw and i in custom_uw[room_id]:
                        sprite.kind = sprite_translation[custom_uw[room_id][i]]
                    else:
                        # filter out water if necessary
                        candidate_sprites = [x for x in candidate_sprites if not x.water_only or sprite.water]
                        # filter out wallmaster if already on tile
                        if wallmaster_chosen:
                            candidate_sprites = [x for x in candidate_sprites if x.sprite != EnemySprite.Wallmaster]
                        candidate_sprites = [x for x in candidate_sprites if not exceeds_sprite_limit(sprite_limit, x)]
                        if sprite.drops_item:
                            forbidden = determine_forbidden(any_enemy_logic == 'none', room_id, True)
                            choice_list = [x for x in candidate_sprites if x.good_for_key_drop(forbidden)]
                        # terrorpin, deadrock, buzzblob, lynel, redmimic/eyegore
                        elif room_id in shutter_sprites and i in shutter_sprites[room_id]:
                            forbidden = determine_forbidden(any_enemy_logic != 'allow_all', room_id)
                            choice_list = [x for x in candidate_sprites if x.good_for_shutter(forbidden)]
                        else:
                            choice_list = [x for x in candidate_sprites if not x.water_only]
                        choice_list = filter_choices(choice_list, room_id, i, data_tables.uw_enemy_denials)
                        if enemy_drops_active:
                            choice_list = filter_choices(choice_list, room_id, i, data_tables.uw_enemy_drop_denials)
                        if len(choice_list) == 0:
                            randomized = False
                            break
                        weight = [data_tables.uw_weights[r.sprite] for r in choice_list]
                        chosen = random.choices(choice_list, weight, k=1)[0]
                        sprite.kind = chosen.sprite
                    if sprite.kind in sprite_limiter:
                        sprite_limit += sprite_limiter[sprite.kind]-1
                    if sprite.kind == EnemySprite.Wallmaster:
                        wallmaster_chosen = True
                        sprite.kind = 0x09
                        sprite.sub_type = SpriteType.Overlord
                done = randomized
        # done with sprites
    # done with rooms


def determine_forbidden(forbid, room_id, drop_flag=False):
    forbidden_set = set()
    if forbid:
        forbidden_set.update({EnemySprite.Terrorpin, EnemySprite.Deadrock, EnemySprite.Buzzblob,
                              EnemySprite.Lynel, EnemySprite.RedEyegoreMimic, EnemySprite.RedMimic})
        if drop_flag:
            forbidden_set.add(EnemySprite.RedBari)  # requires FireRod to Drop
        # else:  Not yet able to protect triggers, would change default GT tile room behavior
        #     forbidden_set.add(EnemySprite.AntiFairy)  # can't drop anyway
    return forbidden_set


def filter_choices(options, room_id, sprite_idx, denials):
    key = room_id, sprite_idx
    return [x for x in options if key not in denials or x.sprite not in denials[key]]


def filter_water_phobic(options, sprite):
    return [x for x in options if not x.water_phobic or not sprite.water]


def randomize_overworld_enemies(data_tables, custom_ow):
    ow_candidates, ow_sheets, all_sheets = find_candidate_sprites(data_tables, range(1, 64), False)
    areas_to_randomize = [0, 2, 3, 5, 7, 0xA, 0xF, 0x10, 0x11, 0x12, 0x13, 0x14, 0x15, 0x16, 0x17, 0x18,
                          0x1a, 0x1b, 0x1d, 0x1e, 0x22, 0x25, 0x28, 0x29, 0x2A, 0x2b, 0x2c, 0x2d, 0x2e, 0x2f,
                          0x30, 0x32, 0x33, 0x34, 0x35, 0x37, 0x3a, 0x3b, 0x3c, 0x3f]
    area_list = areas_to_randomize + [x + 0x40 for x in areas_to_randomize]  # light world + dark world
    area_list += [0x80, 0x81] + [x + 0x90 for x in areas_to_randomize]  # specials + post aga LW
    for area_id in area_list:
        randomizeable_sprites = get_randomize_able_sprites_ow(area_id, data_tables)
        if not randomizeable_sprites:
            candidate_sheets = get_possible_ow_sheets(area_id, all_sheets, ow_sheets, data_tables)
            chosen_sheet = random.choice(candidate_sheets)
            data_tables.overworld_sprite_sheets[area_id] = chosen_sheet
            candidate_sprites = get_possible_enemy_sprites_ow(chosen_sheet, ow_candidates, data_tables)
        else:
            candidate_sheets = get_possible_ow_sheets(area_id, all_sheets, ow_sheets, data_tables)
            chosen_sheet = random.choice(candidate_sheets)
            data_tables.overworld_sprite_sheets[area_id] = chosen_sheet
            candidate_sprites = get_possible_enemy_sprites_ow(chosen_sheet, ow_candidates, data_tables)
            for i, sprite in randomizeable_sprites.items():
                if area_id in custom_ow and i in custom_ow[area_id]:
                    sprite.kind = sprite_translation[custom_ow[area_id][i]]
                else:
                    candidate_sprites = filter_choices(candidate_sprites, area_id, i, data_tables.ow_enemy_denials)
                    candidate_sprites = filter_water_phobic(candidate_sprites, sprite)
                    weight = [data_tables.ow_weights[r.sprite] for r in candidate_sprites]
                    chosen = random.choices(candidate_sprites, weight, k=1)[0]
                    sprite.kind = chosen.sprite
        # randomize the bush sprite per area
        weight = [data_tables.ow_weights[r.sprite] for r in candidate_sprites]
        bush_sprite_choice = random.choices(candidate_sprites, weight, k=1)[0]
        data_tables.bush_sprite_table[area_id] = bush_sprite_choice


# damage and health tables only go to F2
skip_sprites = {
    EnemySprite.ArmosKnight, EnemySprite.Lanmolas, EnemySprite.Moldorm, EnemySprite.Mothula, EnemySprite.Arrghus,
    EnemySprite.HelmasaurKing, EnemySprite.Vitreous, EnemySprite.TrinexxRockHead, EnemySprite.TrinexxFireHead,
    EnemySprite.TrinexxIceHead, EnemySprite.Blind, EnemySprite.Kholdstare, EnemySprite.KholdstareShell,
    EnemySprite.FallingIce, EnemySprite.Arrghi, EnemySprite.Agahnim, EnemySprite.Ganon,
    EnemySprite.PositionTarget, EnemySprite.Boulders
}


def randomize_enemies(world, player):
    if world.enemy_shuffle[player] != 'none':
        data_tables = world.data_tables[player]
        custom_uw, custom_ow = {}, {}
        enemy_map = world.customizer.get_enemies() if world.customizer else None
        if enemy_map and player in enemy_map:
            if 'Underworld' in enemy_map[player]:
                custom_uw = enemy_map[player]['Underworld']
            if 'Overworld' in enemy_map[player]:
                custom_ow = enemy_map[player]['Overworld']
        randomize_underworld_sprite_sheets(data_tables.sprite_sheets, data_tables, custom_uw)
        randomize_underworld_rooms(data_tables, world, player, custom_uw)
        randomize_overworld_sprite_sheets(data_tables.sprite_sheets, data_tables, custom_ow)
        randomize_overworld_enemies(data_tables, custom_ow)
        # fix thief stats
        # subclass_table = world.damage_table[player].damage_table['SubClassTable']
        # subclass_table[EnemySprite.Thief] = subclass_table[EnemySprite.GreenEyegoreMimic]
        # data_tables.enemy_stats[EnemySprite.Thief].health = 4
        # could turn droppable on here if we wanted for killable theives
    # health shuffle
    if world.enemy_health[player] != 'default':
        stats = world.data_tables[player].enemy_stats
        min_health = {'easy': 1, 'normal': 2, 'hard': 2, 'expert': 4}
        max_health = {'easy': 4, 'normal': 15, 'hard': 25, 'expert': 50}
        min_h = min_health[world.enemy_health[player]]
        max_h = max_health[world.enemy_health[player]]
        for sprite, stat in stats.items():
            if sprite == EnemySprite.Octorok4Way:
                stat.health = stats[EnemySprite.Octorok].health   # these guys share data
            elif sprite == EnemySprite.GreenMimic:
                stat.health = stats[EnemySprite.GreenEyegoreMimic].health  # these share data
            elif sprite == EnemySprite.RedMimic:
                stat.health = stats[EnemySprite.RedEyegoreMimic].health  # these share data
            elif sprite not in skip_sprites:
                if isinstance(stat.health, tuple):
                    stat.health = random.randint(min_h, max_h), random.randint(min_h, max_h)
                else:
                    stat.health = random.randint(min_h, max_h)
    if world.enemy_damage[player] != 'default':
        stats = world.data_tables[player].enemy_stats
        # randomize damage groupings
        for sprite, stat in stats.items():
            if sprite == EnemySprite.Octorok4Way:
                stat.damage = stats[EnemySprite.Octorok].damage  # these guys share data
            elif sprite == EnemySprite.GreenMimic:
                stat.damage = stats[EnemySprite.GreenEyegoreMimic].damage  # these share data
            elif sprite == EnemySprite.RedMimic:
                stat.damage = stats[EnemySprite.RedEyegoreMimic].damage  # these share data
            elif sprite == EnemySprite.Thief:  # always group 0 for 0 damage
                stat.damage = 0
            elif sprite not in skip_sprites:
                if isinstance(stat.damage, tuple):
                    stat.damage = random.randint(0, 8), random.randint(0, 8)
                else:
                    stat.damage = random.randint(0, 8)
        # randomize bump table
        original_table = [
            (0x02, 0x01, 0x01),
            (0x04, 0x04, 0x04),
            (0x00, 0x00, 0x00),
            (0x08, 0x04, 0x02),
            (0x08, 0x08, 0x08),
            (0x10, 0x08, 0x04),
            (0x20, 0x10, 0x08),
            (0x20, 0x18, 0x10),
            (0x18, 0x10, 0x08),
            (0x40, 0x30, 0x18)]
        for i in range(0, 10):
            if i == 0:  # group 0 will always be 0 for thieves
                green_mail, blue_mail, red_mail = 0, 0, 0
                del original_table[2]
            else:
                if world.enemy_damage[player] == 'random':
                    green_mail = random.randint(0, 64)
                    if world.enemy_damage[player] == 'random':
                        blue_mail = random.randint(0, 64)
                        red_mail = random.randint(0, 64)
                else:
                    idx = random.randint(0, len(original_table)-1)
                    green_mail, blue_mail, red_mail = original_table[idx]
                    del original_table[idx]
            world.data_tables[player].enemy_damage[i] = [green_mail, blue_mail, red_mail]


def write_enemy_shuffle_settings(world, player, rom):
    if world.dropshuffle[player] in ['underworld']:
        rom.write_byte(snes_to_pc(0x368109), 0x01)
    if world.enemy_shuffle[player] != 'none':
        # enable new mimics
        rom.write_byte(snes_to_pc(0x368105), 0x01)

        # killable thief
        # rom.write_byte(snes_to_pc(0x368108), 0xc4)
        # rom.write_byte(snes_to_pc(0x0DB237), 4)  # health value - randomize it if killable, maybe

        # mimic room barriers
        data_tables = world.data_tables[player]
        mimic_room = data_tables.room_list[0x10c] = Room010C
        mimic_room.layer1[40].data[0] = 0x54  # rail adjust
        mimic_room.layer1[40].data[1] = 0x9C
        mimic_room.layer1[45].data[1] = 0xB0  # block adjust 1
        mimic_room.layer1[47].data[1] = 0xD0  # block adjust 2

        # random tile pattern
        pattern_name, tile_pattern = random.choice(tile_patterns)
        rom.write_byte(snes_to_pc(0x9BA1D), len(tile_pattern))
        for idx, pair in enumerate(tile_pattern):
            rom.write_byte(snes_to_pc(0x09BA2A + idx), (pair[0] + 3) * 16)
            rom.write_byte(snes_to_pc(0x09BA40 + idx), (pair[1] + 4) * 16)
    if world.enemy_shuffle[player] == 'random':
        rom.write_byte(snes_to_pc(0x368100), 1)  # randomize bushes
