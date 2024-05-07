import math
from collections import defaultdict

import RaceRandom as random

from source.logic.Rule import RuleFactory
from source.dungeon.EnemyList import EnemySprite


# these are for drops only
def defeat_rule_single(world, player, enemy_sprite, region):
    if enemy_sprite.kind == EnemySprite.Terrorpin:
        # must be flipped
        return has('Hammer', player)
    elif enemy_sprite.kind == EnemySprite.RedBari:
        # must be burned to drop
        return or_rule(has('Fire Rod', player), and_rule(has_sword(player), has('Bombos', player)))
    vln = enemy_vulnerability(world, player, enemy_sprite, region)
    rules = []
    if vln['Blunt'] != 0:
        rules.append(has_blunt_weapon(player))
    if vln['Stun'] != 0:
        rules.append(buzzblob_rule(player))
    if vln['Somaria'] != 0:
        rules.append(somaria_rule(world, player, vln['Somaria']))
    if vln['Byrna'] != 0:
        rules.append(byrna_rule(world, player, vln['Byrna']))
    if vln['Master'] != 0:
        rules.append(has_class_2_weapon(player))
    if vln['Bow'] != 0:
        rules.append(bow_rule(world, player, vln['Bow']))
    if vln['Silvers'] != 0:
        rules.append(silvers_rule(world, player, vln['Silvers']))
    if vln['Bomb'] != 0:
        rules.append(bombs_rule(world, player, vln['Bomb']))
    if vln['Hookshot'] != 0:
        rules.append(has('Hookshot', player))
    if vln['IceRod'] != 0:
        rules.append(ice_rod_rule(world, player, vln['IceRod']))
    if vln['FireRod'] != 0:
        rules.append(fire_rod_rule(world, player, vln['FireRod']))
    if vln['Boomerang'] != 0:
        rules.append(has_boomerang(player))
    if vln['Powder'] not in [0, -3]:  # fairy doesn't make it drop
        rules.append(magic_powder_rule(world, player, vln['Powder']))
    # skip medallions if vln to Blunt?
    if vln['Bombos'] != 0 and vln['Blunt'] == 0:
        rules.append(medallion_rule(world, player, 'Bombos', vln['Bombos']))
    if vln['Ether'] != 0 and vln['Blunt'] == 0:
        rules.append(medallion_rule(world, player, 'Ether', vln['Ether']))
    if vln['Quake'] != 0 and vln['Blunt'] == 0:
        rules.append(medallion_rule(world, player, 'Quake', vln['Quake']))
    if enemy_sprite.kind == EnemySprite.StalfosKnight:
        # must be bombed once made vulnerable
        return and_rule(can_use_bombs(world, player), or_rule(*rules))
    return or_rule(*rules)


damage_cost = {
    'Bomb': 1,  'Bow': 1, 'Silvers': 1,
    'Powder': .5, 'Somaria': .5, 'Byrna': 1.125,
    'FireRod': 1, 'IceRod': 1,
    'Bombos': 2, 'Ether': 2, 'Quake': 2
}

# damage_set = ['Blunt', 'Stun', 'Master', 'Tempered', 'Boomerang', 'Hookshot', 'Bomb', 'Silvers', 'Bow',
#               'Somaria', 'Powder', 'FireRod', 'IceRod', 'Byrna', 'Bombos', 'Ether', 'Quake']


# these are for "challenge" rooms
def defeat_rule_multiple(world, player, enemy_sprite_region_pairs):
    vln_list = {}
    for sprite, region in enemy_sprite_region_pairs:
        vln_list[(sprite, region)] = enemy_vulnerability(world, player, sprite, region)

    # damage_accounting = {x: list(y) for x, y in damage_types.items()}
    used_resources = {'Bomb': 0, 'Arrow': 0, 'Magic': 0}
    required_rules = []
    picky_enemies = []
    hammer_required = False
    bombs_required = False

    for key, vln in vln_list.items():
        if key[0].kind == EnemySprite.Terrorpin:
            if not hammer_required:
                required_rules.append(has('Hammer', player))
                hammer_required = True
            picky_enemies.append(key)
            continue
        if key[0].kind == EnemySprite.StalfosKnight:
            if not bombs_required:
                required_rules.append(bombs_rule(world, player, 1))
                bombs_required = True
            used_resources['Bomb'] += 1
            picky_enemies.append(key)
            continue
        vln_types = [k for k in vln.keys() if vln[k] != 0]
        if len(vln_types) == 1:
            d_type = vln_types[0]
            required_rules.append(defeat_rule_single(world, player, key[0], key[1]))
            picky_enemies.append(key)
            if d_type in damage_cost:
                cost = damage_cost[d_type]
                if d_type == 'Bomb':
                    used_resources['Bomb'] += cost
                elif d_type in ['Bow', 'Silvers']:
                    used_resources['Arrow'] += cost
                else:
                    used_resources['Magic'] += cost
    vln_list = {k: v for k, v in vln_list.items() if k not in picky_enemies}

    while len(vln_list) > 0:

        optional_clears = find_possible_rules(vln_list, used_resources, world, player)
        if len(optional_clears) == 0:
            raise Exception('Kill rules seems to be insufficient for this enemy set, please report:'
                            + ', '.join([str(x) for x, y in enemy_sprite_region_pairs]))

        # find rules which kill the most
        # idea: this could be multiple criteria: most-constrained then which method kills the most
        best_rules = {}
        best_size = 0
        for vln_option in optional_clears.keys():
            if len(vln_option) > best_size:
                best_size = len(vln_option)
                best_rules.clear()
                best_rules[vln_option] = optional_clears[vln_option]
            elif len(vln_option) == best_size:  # assumes vln_option is different from prior options
                best_rules[vln_option] = optional_clears[vln_option]
        if len(best_rules) == 1:
            vln_option, rule_pair_list = next(iter(best_rules.items()))
        else:
            vln_option, rule_pair_list = random.choice(list(best_rules.items()))
        if best_size == 0:
            raise Exception('Invulnerable enemy? rules seems to be insufficient for this enemy set, please report:'
                            + ', '.join([str(x) for x, y in enemy_sprite_region_pairs]))

        new_vln_list = {vln_kv[0]: vln_kv[1] for idx, vln_kv in enumerate(vln_list.items()) if idx not in vln_option}
        rules_to_add = [rule for rule, resources in rule_pair_list]
        resources_to_use = [resources for rule, resources in rule_pair_list]
        required_rules.append(or_rule(*rules_to_add))
        for r in resources_to_use:
            for k, v in r.items():
                used_resources[k] += v
        vln_list = new_vln_list

    return and_rule(*required_rules)


def find_possible_rules(vln_list, used_resources, world, player):
    optional_clears = defaultdict(list)
    blunt_marker = defaultdict(bool)
    for damage_type in ['Blunt', 'Stun', 'Master', 'Boomerang', 'Hookshot']:
        # all_vln = all(vln[damage_type] != 0 for vln in vln_list.values())
        vln_sub_list = frozenset({idx for idx, vln in enumerate(vln_list.values()) if vln[damage_type] != 0})
        if vln_sub_list:
            if damage_type == 'Blunt':
                optional_clears[vln_sub_list].append((has_blunt_weapon(player), {}))
                blunt_marker[vln_sub_list] = True
            if damage_type == 'Stun':
                optional_clears[vln_sub_list].append((buzzblob_rule(player), {}))
            if damage_type == 'Master' and not blunt_marker[vln_sub_list]:
                optional_clears[vln_sub_list].append((has_class_2_weapon(player), {}))
            if damage_type == 'Boomerang':
                optional_clears[vln_sub_list].append((has('Hookshot', player), {}))
            elif damage_type == 'Hookshot':
                optional_clears[vln_sub_list].append((has_boomerang(player), {}))
    damage_type = 'Bomb'
    vln_sub_list = frozenset({idx for idx, vln in enumerate(vln_list.values()) if vln[damage_type] != 0})
    if vln_sub_list:
        hits = needed_resources(damage_type, vln_list)
        if hits + used_resources['Bomb'] <= 8:
            optional_clears[vln_sub_list].append(
                (bombs_rule(world, player, hits + used_resources['Bomb']), {'Bomb': hits}))
    for damage_type in ['Bow', 'Silvers']:
        vln_sub_list = frozenset({idx for idx, vln in enumerate(vln_list.values()) if vln[damage_type] != 0})
        if vln_sub_list:
            hits = needed_resources(damage_type, vln_list)
            resources = {'Arrow': hits}
            if damage_type == 'Bow' and hits + used_resources['Arrow'] <= 25:
                optional_clears[vln_sub_list].append(
                    (bow_rule(world, player, hits + used_resources['Arrow']), resources))
            if damage_type == 'Silvers' and hits + used_resources['Arrow'] <= 25:
                optional_clears[vln_sub_list].append(
                    (silvers_rule(world, player, hits + used_resources['Arrow']), resources))
    for damage_type in ['Powder', 'Somaria', 'Byrna', 'FireRod', 'IceRod', 'Bombos', 'Ether', 'Quake']:
        vln_sub_list = frozenset({idx for idx, vln in enumerate(vln_list.values()) if vln[damage_type] != 0})
        if vln_sub_list:
            hits = needed_resources(damage_type, vln_list)
            resources = {'Magic': damage_cost[damage_type] * hits}
            if damage_type == 'Powder' and math.ceil(hits / 16) * 8 + used_resources['Magic'] <= 160:
                flag = min(vln[damage_type] for vln in vln_list.values())
                flag = flag if flag < 0 else (hits + used_resources['Magic'] * 2)
                optional_clears[vln_sub_list].append((magic_powder_rule(world, player, flag), resources))
            elif damage_type == 'Somaria' and math.ceil(hits / 64) * 8 + used_resources['Magic'] <= 160:
                flag = min(vln[damage_type] for vln in vln_list.values())
                flag = flag if flag < 0 else (hits + used_resources['Magic'] * 8)
                optional_clears[vln_sub_list].append((somaria_rule(world, player, flag), resources))
            elif damage_type == 'Byrna' and math.ceil(hits / 7) * 8 + used_resources['Magic'] <= 160:
                flag = min(vln[damage_type] for vln in vln_list.values())
                flag = flag if flag < 0 else (hits + used_resources['Magic'] * 7 / 8)
                optional_clears[vln_sub_list].append((byrna_rule(world, player, flag), resources))
            elif damage_type == 'FireRod' and hits + used_resources['Magic'] <= 160:
                flag = min(vln[damage_type] for vln in vln_list.values())
                flag = flag if flag < 0 else (hits + used_resources['Magic'])
                optional_clears[vln_sub_list].append((fire_rod_rule(world, player, flag), resources))
            elif damage_type == 'IceRod' and hits + used_resources['Magic'] <= 160:
                flag = min(vln[damage_type] for vln in vln_list.values())
                flag = flag if flag < 0 else (hits + used_resources['Magic'])
                optional_clears[vln_sub_list].append((ice_rod_rule(world, player, flag), resources))
            elif hits * 2 + used_resources['Magic'] <= 160 and not blunt_marker[vln_sub_list]:
                flag = min(vln[damage_type] for vln in vln_list.values())
                flag = flag if flag < 0 else (hits + used_resources['Magic'] / 2)
                optional_clears[vln_sub_list].append((medallion_rule(world, player, damage_type, flag), resources))
    return optional_clears


def needed_resources(damage_type, vln_list):
    return sum(vln[damage_type] if vln[damage_type] >= 0 else 1 for vln in vln_list.values() if vln[damage_type] != 0)


special_rules_check = {
    'Swamp Waterway': None,
    'Hera Back': [5, 6],
    'GT Petting Zoo': [5, 8, 9, 11],
    'Mimic Cave': [4, 5, 6, 7],
    'Ice Hookshot Ledge': None,
    'TR Hub Ledges': [3, 4, 5, 6, 7],
    'TR Dark Ride': [1, 2, 3],
    'GT Speed Torch': [11, 13],
    'Old Man Cave (West)': None,
    'Old Man Cave (East)': None,
    'Old Man House': [1, 3],
    'Old Man House Back': [4, 5, 6],
    'Death Mountain Return Cave (left)': None,
    'Death Mountain Return Cave (right)': [1, 2, 3, 6, 7],  # 2, 5, 6 are considered embedded
    'Hookshot Fairy': [0, 1, 2, 3]
}


def special_rules_for_region(world, player, region_name, location, original_rule):
    if region_name == 'Swamp Waterway':
        return or_rule(medallion_rule(world, player, 'Quake', 1),
                       medallion_rule(world, player, 'Ether', 1),
                       medallion_rule(world, player, 'Bombos', 1))
    elif region_name in ['Hera Back', 'GT Petting Zoo', 'Mimic Cave']:
        enemy_number = int(location.name.split('#')[1])
        if region_name == 'Mimic Cave':
            if enemy_number in [4, 5]:  # these are behind hammer blocks potentially
                return and_rule(original_rule, has('Hammer', player))
            elif enemy_number in special_rules_check[region_name]:   # these are behind rails
                return and_rule(original_rule, has_boomerang(player))
        if enemy_number in special_rules_check[region_name]:
            return and_rule(original_rule, has_boomerang(player))
        else:
            return original_rule
    elif region_name in ['TR Hub Ledges', 'Ice Hookshot Ledge',  'TR Dark Ride']:
        enemy_number = int(location.name.split('#')[1])
        if special_rules_check[region_name] is None or enemy_number in special_rules_check[region_name]:
            return and_rule(original_rule, or_rule(has_boomerang(player), has('Hookshot', player)))
        else:
            return original_rule
    elif region_name in ['Old Man Cave (West)', 'Old Man Cave (East)', 'Old Man House Back', 'Old Man House',
                         'Death Mountain Return Cave (left)', 'Death Mountain Return Cave (right)',
                         'Hookshot Fairy']:
        enemy_number = int(location.name.split('#')[1])
        if region_name == 'Death Mountain Return Cave (left)':
            if enemy_number in [1, 5]:
                return and_rule(original_rule, or_rule(has_boomerang(player), has('Hookshot', player)))
            else:
                return and_rule(original_rule, has('Hookshot', player))
        if special_rules_check[region_name] is None or enemy_number in special_rules_check[region_name]:
            return and_rule(original_rule, has('Hookshot', player))
        else:
            return original_rule
    return original_rule


def has_blunt_weapon(player):
    return or_rule(has_sword(player), has('Hammer', player))


# Bombs, Arrows, Bombos, FireRod, Somaria, Byrna should be handled by the damage table logic
# Powder doesn't work (also handled by damage table)
def buzzblob_rule(player):
    return or_rule(has('Golden Sword', player),
                   and_rule(has_blunt_weapon(player),
                            or_rule(has_boomerang(player), has('Hookshot', player), has('Ice Rod', player))),
                   and_rule(has('Ether', player), has_sword(player)),
                   and_rule(has('Quake', player), has_sword(player)))


def has_class_2_weapon(player):
    return or_rule(has_beam_sword(player), has('Hammer', player))


def somaria_rule(world, player, somaria_hits):
    if somaria_hits == -1:
        return has('Cane of Somaria', player)  # insta-kill somaria? - not in vanilla
    else:
        magic_needed = math.ceil(somaria_hits / 64) * 8  # 64 hits per magic bar - 80 max?
        if magic_needed > 8:
            return and_rule(has('Cane of Somaria', player), can_extend_magic(world, player, magic_needed))
        else:
            return has('Cane of Somaria', player)


def byrna_rule(world, player, byrna_hits):
    if byrna_hits == -1:
        return has('Cane of Byrna', player)  # insta-kill byrna? - not in vanilla
    else:
        magic_needed = math.ceil(byrna_hits / 7) * 8  # 7 hits per magic bar - generous?
        if magic_needed > 8:
            return and_rule(has('Cane of Byrna', player), can_extend_magic(world, player, magic_needed))
        else:
            return has('Cane of Byrna', player)


def bow_rule(world, player, arrows):
    if arrows == -1 or 0 < arrows <= 25:
        return can_shoot_normal_arrows(world, player)
    return RuleFactory.static_rule(False)


def silvers_rule(world, player, arrows):
    if arrows == -1 or 0 < arrows <= 25:
        return can_shoot_silver_arrows(world, player)
    return RuleFactory.static_rule(False)


def bombs_rule(world, player, bombs):
    if bombs == -1 or 0 < bombs <= 8:
        return can_use_bombs(world, player)
    return RuleFactory.static_rule(False)


def ice_rod_rule(world, player, shots):
    if shots == -1:
        return has('Ice Rod', player)
    if shots > 8:
        return and_rule(has('Ice Rod', player), can_extend_magic(world, player, shots))
    else:
        return has('Ice Rod', player)


def fire_rod_rule(world, player, shots):
    if shots == -1:
        return has('Fire Rod', player)
    if shots > 8:
        return and_rule(has('Fire Rod', player), can_extend_magic(world, player, shots))
    else:
        return has('Fire Rod', player)


def magic_powder_rule(world, player, shots):
    if shots == -1:
        return has('Magic Powder', player)
    if shots == -2:
        # todo: other resources possible I guess - harder to keep track of though
        return and_rule(has('Magic Powder', player), or_rule(has_blunt_weapon(player), has('Hookshot', player)))
    magic_needed = math.ceil(shots / 16) * 8  # 16 tries per magic bar, that could be tight...
    if magic_needed > 8:
        return and_rule(has('Magic Powder', player), can_extend_magic(world, player, shots))
    else:
        return has('Magic Powder', player)


def medallion_rule(world, player, medallion, shots):
    if shots == -1:
        return and_rule(has(medallion, player), has_sword(player))
    if shots == -2:
        return and_rule(has(medallion, player), has_sword(player))
    magic_needed = shots * 2
    if magic_needed > 8:
        return and_rule(has(medallion, player), has_sword(player), can_extend_magic(world, player, shots))
    else:
        return and_rule(has(medallion, player), has_sword(player))


def or_rule(*rules):
    return RuleFactory.disj(rules)


def and_rule(*rules):
    return RuleFactory.conj(rules)


def has(item, player, count=1):
    return RuleFactory.item(item, player, count)


def has_sword(player):
    return or_rule(
        has('Fighter Sword', player), has('Master Sword', player),
        has('Tempered Sword', player), has('Golden Sword', player)
    )


def has_beam_sword(player):
    return or_rule(
        has('Master Sword', player), has('Tempered Sword', player), has('Golden Sword', player)
    )


def has_class_3_sword(player):
    return or_rule(
        has('Tempered Sword', player), has('Golden Sword', player)
    )


def can_extend_magic(world, player, magic, flag_t=False):
    potion_shops = (find_shops_that_sell('Blue Potion', world, player) |
                    find_shops_that_sell('Green Potion', world, player))
    return RuleFactory.extend_magic(player, magic, world.difficulty_adjustments[player], potion_shops, flag_t)


# class 0 damage (subtypes 1 and 2)
def has_boomerang(player):
    return or_rule(has('Blue Boomerang', player), has('Red_Boomerang', player))


def find_shops_that_sell(item, world, player):
    return {shop.region for shop in world.shops[player] if shop.has_unlimited(item) and shop.region.player == player}


def can_shoot_normal_arrows(world, player):
    if world.bow_mode[player].startswith('retro'):
        shops = find_shops_that_sell('Single Arrow', world, player)
        # retro+shopsanity, shops may not sell the Single Arrow at all
        if world.bow_mode[player] == 'retro_silvers':
            # non-progressive silvers grant wooden arrows, so shop may not be needed
            return and_rule(has('Bow', player), or_rule(RuleFactory.unlimited('Single Arrow', player, shops),
                                                        has('Single Arrow', player), has('Silver Arrows', player)))
        else:
            return and_rule(has('Bow', player), or_rule(RuleFactory.unlimited('Single Arrow', player, shops),
                                                        has('Single Arrow', player)))
    return has('Bow', player)


def can_shoot_silver_arrows(world, player):
    # retro_silver requires the silver arrows item which is sufficient for the quiver
    if world.bow_mode[player] == 'retro':
        shops = find_shops_that_sell('Single Arrow', world, player)
        # retro+shopsanity, shops may not sell the Single Arrow at all
        return and_rule(has('Silver Arrows', player), or_rule(RuleFactory.unlimited('Single Arrow', player, shops),
                                                              has('Single Arrow', player)))
    return and_rule(has('Bow', player), has('Silver Arrows', player))


def can_use_bombs(world, player):
    return or_rule(RuleFactory.static_rule(not world.bombbag[player]), has('Bomb Upgrade (+10)', player))


def enemy_vulnerability(world, player, enemy_sprite, region):
    damage_table = world.damage_table[player].damage_table
    stats = world.data_tables[player].enemy_stats
    damage_src = damage_table['DamageSource']
    sub_class_table = damage_table['SubClassTable']

    enemy_sub_class = sub_class_table[enemy_sprite.kind]

    vulnerability = defaultdict(int)

    c1 = number_of_hits('Sword1', damage_src, enemy_sub_class, stats, enemy_sprite, region)
    if c1 != 0:
        if enemy_sprite.kind == EnemySprite.Buzzblob:
            vulnerability['Stun'] = -1
        else:
            vulnerability['Blunt'] = -1
            vulnerability['Master'] = -1
        vulnerability['Somaria'] = c1
        vulnerability['Byrna'] = c1
    else:
        c2 = number_of_hits('Sword3', damage_src, enemy_sub_class, stats, enemy_sprite, region)
        if c2 != 0:
            vulnerability['Master'] = -1  # currently Lynels are only vulnerable to only master spins or above
    hits = number_of_hits('Arrow', damage_src, enemy_sub_class, stats, enemy_sprite, region)
    if hits != 0:
        vulnerability['Bow'] = hits
    hits = number_of_hits('SilverArrow', damage_src, enemy_sub_class, stats, enemy_sprite, region)
    if hits != 0:
        vulnerability['Silvers'] = hits
    for method in ['Bomb', 'Hookshot', 'FireRod', 'IceRod', 'Boomerang', 'Powder', 'Bombos', 'Ether', 'Quake']:
        hits = number_of_hits(method, damage_src, enemy_sub_class, stats, enemy_sprite, region)
        if hits == -3:
            if enemy_sprite.kind != EnemySprite.Buzzblob:  # buzzblobs are special and don't die
                vulnerability[method] = -1
        elif hits != 0:
            vulnerability[method] = hits
    return vulnerability


def number_of_hits(source_name, damage_src, enemy_sub_class, stats, enemy_sprite, region):
    damage_class = damage_src[source_name]['class']
    sub_class = enemy_sub_class[damage_class]
    damage_amount = damage_src[source_name]['subclass'][sub_class]
    if damage_amount == 0:
        return 0
    elif damage_amount <= 0x64:
        health = stats[enemy_sprite.kind].health
        if isinstance(health, tuple):
            if enemy_sprite.kind in [EnemySprite.Tektite, EnemySprite.HardhatBeetle]:
                idx = enemy_sprite.tile_x & 0x1
                health = health[idx]
            elif region.is_light_world and region.is_dark_world:
                health = min(health)
            elif region.is_light_world:
                health = health[0]
            elif region.is_dark_world:
                health = health[1]
            else:
                health = max(health)
        return math.ceil(health / damage_amount)
    elif damage_amount in [0xF9, 0xFA, 0xFD]:
        # -1 incinerated; -2 blobbed, -3 fairy-ed (depends on enemy if "killed" or not)
        # F9: fairy, defeated, but doesn't drop anything: -3
        # FA: blobbed - can you kill a blob?  = -2
        # FD: incinerated
        return special_classes[damage_amount]
    else:
        return 0


special_classes = {0xF9: -3, 0xFA: -2, 0xFD: -1}

