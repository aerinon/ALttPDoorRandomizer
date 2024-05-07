import logging
import RaceRandom as random

from BaseClasses import Boss, FillError
from source.enemizer.Bossmizer import boss_adjust


def BossFactory(boss, player, on_ice=False):
    if boss is None:
        return None
    if boss in boss_table:
        enemizer_name, normal_defeat_rule, ice_defeat_rule = boss_table[boss]
        defeat_rule = ice_defeat_rule if on_ice else normal_defeat_rule
        return Boss(boss, enemizer_name, defeat_rule, player)

    logging.getLogger('').error('Unknown Boss: %s', boss)
    return None

def ArmosKnightsDefeatRule(state, player):
    # Magic amounts are probably a bit overkill
    return (
        state.has_blunt_weapon(player) or
        state.can_shoot_arrows(player) or
        (state.has('Cane of Somaria', player) and state.can_extend_magic(player, 10)) or
        (state.has('Cane of Byrna', player) and state.can_extend_magic(player, 16)) or
        (state.has('Ice Rod', player) and state.can_extend_magic(player, 32)) or
        (state.has('Fire Rod', player) and state.can_extend_magic(player, 32)) or
        state.has('Blue Boomerang', player) or
        state.has('Red Boomerang', player))

def LanmolasDefeatRule(state, player):
    return (
        state.has_blunt_weapon(player) or
        state.has('Fire Rod', player) or
        state.has('Ice Rod', player) or
        state.has('Cane of Somaria', player) or
        (state.has('Cane of Byrna', player) and state.can_use_bombs(player)) or
        state.can_shoot_arrows(player))

def MoldormDefeatRule(state, player):
    return state.has_blunt_weapon(player)

def HelmasaurKingDefeatRule(state, player):
    return (state.has('Hammer', player) or state.can_use_bombs(player)) and (state.has_sword(player) or state.can_shoot_arrows(player))


def IceHelmasaurKingDefeatRule(state, player):
    return state.can_use_bombs(player) and (state.has_sword(player) or state.can_shoot_arrows(player))


def ArrghusDefeatRule(state, player):
    if not state.has('Hookshot', player):
        return False
    if state.has_blunt_weapon(player):
        return True

    if state.can_shoot_arrows(player) and state.has('Silver Arrows', player) and state.world.difficulty_adjustments[player] not in ['hard', 'expert']:
        return True

    return ((state.has('Fire Rod', player) and (state.can_shoot_arrows(player) or state.can_extend_magic(player, 12))) or  # assuming mostly getting two puffs with one shot
            (state.has('Ice Rod', player) and state.can_use_bombs(player) and (state.can_shoot_arrows(player) or state.can_extend_magic(player, 16))))


def MothulaDefeatRule(state, player):
    return (
        state.has_blunt_weapon(player) or
        (state.has('Fire Rod', player) and state.can_extend_magic(player, 10)) or
        # TODO: Not sure how much (if any) extend magic is needed for these two, since they only apply
        # to non-vanilla locations, so are harder to test, so sticking with what VT has for now:
        (state.has('Cane of Somaria', player) and state.can_extend_magic(player, 16)) or
        (state.has('Cane of Byrna', player) and state.can_extend_magic(player, 16))
    )


def BlindDefeatRule(state, player):
    return state.has_blunt_weapon(player) or state.has('Cane of Somaria', player) or state.has('Cane of Byrna', player)


def IceBlindDefeatRule(state, player):
    return (
            (
                # weapon
                state.has_beam_sword(player) or
                state.has('Cane of Somaria', player) or
                (state.has('Cane of Byrna', player) and state.can_extend_magic(player, 16))
            ) and
            (
                # protection
                state.has('Red Shield', player) or
                (state.has('Cane of Byrna', player) and state.world.difficulty_adjustments[player] not in ['hard', 'expert'])
            )
    )


def KholdstareDefeatRule(state, player):
    return (
        (
            state.has('Fire Rod', player) or
            (
                state.has('Bombos', player) and
                # FIXME: the following only actually works for the vanilla location for swordless
                (state.has_sword(player) or state.world.swords[player] == 'swordless')
            )
        ) and
        (
            state.has_blunt_weapon(player) or
            (state.has('Fire Rod', player) and state.can_extend_magic(player, 20)) or
            # FIXME: this actually only works for the vanilla location for swordless
            (
                state.has('Fire Rod', player) and
                state.has('Bombos', player) and
                state.world.swords[player] == 'swordless' and
                state.can_extend_magic(player, 16)
            )
        )
    )


def IceKholdstareDefeatRule(state, player):
    return (
        (
            state.has('Fire Rod', player) or
            (
                state.has('Bombos', player) and
                # FIXME: the following only actually works for the vanilla location for swordless
                (state.has_sword(player) or state.world.swords[player] == 'swordless')
            )
        ) and
        (
            state.has_beam_sword(player) or
            (state.has('Fire Rod', player) and state.can_extend_magic(player, 20)) or
            # FIXME: this actually only works for the vanilla location for swordless
            (
                state.has('Fire Rod', player) and
                state.has('Bombos', player) and
                (state.has_sword(player) or state.world.swords[player] == 'swordless') and
                state.can_extend_magic(player, 16)
            )
        )
    )


def VitreousDefeatRule(state, player):
    return (state.can_shoot_arrows(player) and state.can_use_bombs(player)) or state.has_blunt_weapon(player)


def IceVitreousDefeatRule(state, player):
    return (state.can_shoot_arrows(player) and state.can_use_bombs(player)) or state.has_beam_sword(player)


def TrinexxDefeatRule(state, player):
    if not (state.has('Fire Rod', player) and state.has('Ice Rod', player)):
        return False
    return (state.has('Hammer', player) or
            state.has('Golden Sword', player) or
            state.has('Tempered Sword', player) or
            (state.has('Master Sword', player) and state.can_extend_magic(player, 16)) or
            (state.has_sword(player) and state.can_extend_magic(player, 32)))


def IceTrinexxDefeatRule(state, player):
    if not (state.has('Fire Rod', player) and state.has('Ice Rod', player) and state.has_Boots(player)):
        return False
    return (state.has('Golden Sword', player) or
            (state.has('Tempered Sword', player) and state.can_extend_magic(player, 16)) or
            ((state.has('Hammer', player) or
              state.has('Master Sword', player)) and state.can_extend_magic(player, 32)))  # rod spam rule


def AgahnimDefeatRule(state, player):
    return state.has_sword(player) or state.has('Hammer', player) or state.has('Bug Catching Net', player)


boss_table = {
    'Armos Knights': ('Armos', ArmosKnightsDefeatRule, ArmosKnightsDefeatRule),
    'Lanmolas': ('Lanmola', LanmolasDefeatRule, LanmolasDefeatRule),
    'Moldorm': ('Moldorm', MoldormDefeatRule, MoldormDefeatRule),
    'Helmasaur King': ('Helmasaur', HelmasaurKingDefeatRule, IceHelmasaurKingDefeatRule),
    'Arrghus': ('Arrghus', ArrghusDefeatRule, ArrghusDefeatRule),
    'Mothula': ('Mothula', MothulaDefeatRule, MothulaDefeatRule),
    'Blind': ('Blind', BlindDefeatRule, IceBlindDefeatRule),
    'Kholdstare': ('Kholdstare', KholdstareDefeatRule, IceKholdstareDefeatRule),
    'Vitreous': ('Vitreous', VitreousDefeatRule, IceVitreousDefeatRule),
    'Trinexx': ('Trinexx', TrinexxDefeatRule, IceTrinexxDefeatRule),
    'Agahnim': ('Agahnim', AgahnimDefeatRule, AgahnimDefeatRule),
    'Agahnim2': ('Agahnim2', AgahnimDefeatRule, AgahnimDefeatRule)
}


def can_place_boss(world, player, boss, dungeon_name, level=None):
    if world.swords[player] in ['swordless'] and boss == 'Kholdstare' and dungeon_name != 'Ice Palace':
        return False

    if dungeon_name == 'Ganons Tower' and level == 'top':
        if boss in ["Armos Knights", "Arrghus",	"Blind", "Trinexx", "Lanmolas"]:
            return False

    if dungeon_name == 'Ganons Tower' and level == 'middle':
        if boss in ["Blind"]:
            return False

    # no Trinexx on Ice in doors without doing some health modelling
    if world.doorShuffle[player] != 'vanilla' and boss == 'Trinexx':
        if dungeon_name == 'Ganons Tower' and level == 'bottom':
            return False

    if dungeon_name == 'Tower of Hera' and boss in ["Armos Knights", "Arrghus",	"Blind", "Trinexx", "Lanmolas"]:
        return False

    if dungeon_name == 'Skull Woods' and boss in ["Trinexx"]:
        return False

    if boss in ["Agahnim",	"Agahnim2",	"Ganon"]:
        return False
    return True

def place_bosses(world, player):
    if world.boss_shuffle[player] == 'none':
        return
    # Most to least restrictive order
    boss_locations = [
        ['Ganons Tower', 'top'],
        ['Tower of Hera', None],
        ['Skull Woods', None],
        ['Ganons Tower', 'middle'],
        ['Ganons Tower', 'bottom'],
        ['Eastern Palace', None],
        ['Desert Palace', None],
        ['Palace of Darkness', None],
        ['Swamp Palace', None],
        ['Thieves Town', None],
        ['Ice Palace', None],
        ['Misery Mire', None],
        ['Turtle Rock', None],
    ]

    all_bosses = sorted(boss_table.keys()) #s orted to be deterministic on older pythons
    placeable_bosses = [boss for boss in all_bosses if boss not in ['Agahnim', 'Agahnim2', 'Ganon']]
    used_bosses = []

    if world.customizer and world.customizer.get_bosses():
        custom_bosses = world.customizer.get_bosses()
        if player in custom_bosses:
            for location, boss in custom_bosses[player].items():
                level = None
                if '(' in location:
                    i = location.find('(')
                    level = location[i+1:location.find(')')]
                    location = location[:i-1]
                if can_place_boss(world, player, boss, location, level):
                    loc_text = location + (' ('+level+')' if level else '')
                    place_boss(boss, level, location, loc_text, world, player)
                    boss_locations.remove([location, level])
                    used_bosses.append((boss, level))

    # temporary hack for swordless kholdstare:
    if world.boss_shuffle[player] in ["simple", "full", "unique"]:
        if world.swords[player] == 'swordless':
            world.get_dungeon('Ice Palace', player).boss = BossFactory('Kholdstare', player)
            logging.getLogger('').debug('Placing boss Kholdstare at Ice Palace')
            boss_locations.remove(['Ice Palace', None])
            placeable_bosses.remove('Kholdstare')

    if world.boss_shuffle[player] in ["simple", "full"]:
        if world.boss_shuffle[player] == "simple":  # vanilla bosses shuffled
            bosses = placeable_bosses + ['Armos Knights', 'Lanmolas', 'Moldorm']
        else:  # all bosses present, the three duplicates chosen at random
            bosses = placeable_bosses + random.sample(placeable_bosses, 3)
        for u, level in used_bosses:
            placeable_bosses.remove(u)

        logging.getLogger('').debug('Bosses chosen %s', bosses)

        for [loc, level] in boss_locations:
            loc_text = loc + (' ('+level+')' if level else '')
            try:
                boss = random.choice([b for b in bosses if can_place_boss(world, player, b, loc, level)])
            except IndexError:
                raise FillError('Could not place boss for location %s' % loc_text)
            bosses.remove(boss)

            place_boss(boss, level, loc, loc_text, world, player)
    elif world.boss_shuffle[player] == "random": #all bosses chosen at random
        for [loc, level] in boss_locations:
            loc_text = loc + (' ('+level+')' if level else '')
            try:
                boss = random.choice([b for b in placeable_bosses if can_place_boss(world, player, b, loc, level)])
            except IndexError:
                raise FillError('Could not place boss for location %s' % loc_text)

            place_boss(boss, level, loc, loc_text, world, player)
    elif world.boss_shuffle[player] == 'unique':
        bosses = list(placeable_bosses)
        for u, level in used_bosses:
            if not level:
                bosses.remove(u)
        gt_bosses = []

        for [loc, level] in boss_locations:
            loc_text = loc + (' ('+level+')' if level else '')
            try:
                if level:
                    boss = random.choice([b for b in placeable_bosses if can_place_boss(world, player, b, loc, level)
                                          and b not in gt_bosses])
                    gt_bosses.append(boss)
                else:
                    boss = random.choice([b for b in bosses if can_place_boss(world, player, b, loc, level)])
                    bosses.remove(boss)
            except IndexError:
                raise FillError('Could not place boss for location %s' % loc_text)

            place_boss(boss, level, loc, loc_text, world, player)
    boss_adjust(world, player)


def place_boss(boss, level, loc, loc_text, world, player):
    # GT Bosses can move dungeon - find the real dungeon to place them in
    if level:
        loc = [x.name for x in world.dungeons if x.player == player and level in x.bosses.keys()][0]
        loc_text = loc + ' (' + level + ')'
    logging.getLogger('').debug('Placing boss %s at %s', boss, loc_text)
    world.get_dungeon(loc, player).bosses[level] = BossFactory(boss, player, level == 'bottom')
