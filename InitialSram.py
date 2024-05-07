from dataclasses import dataclass, field
from typing import List

from BaseClasses import CollectionState
from Utils import count_set_bits

SRAM_SIZE = 0x500
ROOM_DATA = 0x000
OVERWORLD_DATA = 0x280

def _new_default_sram():
    sram_buf = [0x00] * 0x500
    sram_buf[ROOM_DATA+0x20D] = 0xF0
    sram_buf[ROOM_DATA+0x20F] = 0xF0
    sram_buf[0x379] = 0x68
    sram_buf[0x401] = 0xFF
    sram_buf[0x402] = 0xFF
    return sram_buf

@dataclass
class InitialSram:
    _initial_sram_bytes: List[int] = field(default_factory=_new_default_sram)

    def _set_value(self, idx: int, val:int):
        if idx > SRAM_SIZE:
            raise IndexError('SRAM index out of bounds: {idx}')
        if not (-1 < val < 256):
            raise ValueError('SRAM value must be between 0 and 255: {val}')
        self._initial_sram_bytes[idx] = val

    def _or_value(self, idx: int, val:int):
        if idx > SRAM_SIZE:
            raise IndexError('SRAM index out of bounds: {idx}')
        if not (-1 < val < 256):
            raise ValueError('SRAM value must be between 0 and 255: {val}')
        self._initial_sram_bytes[idx] |= val

    def pre_open_aga_curtains(self):
        self._or_value(ROOM_DATA+0x61, 0x80)

    def pre_open_skullwoods_curtains(self):
        self._or_value(ROOM_DATA+0x93, 0x80)

    def pre_open_lumberjack(self):
        self._or_value(OVERWORLD_DATA+0x02, 0x20)

    def pre_open_castle_gate(self):
        self._or_value(OVERWORLD_DATA+0x1B, 0x20)

    def pre_open_ganons_tower(self):
        self._or_value(OVERWORLD_DATA+0x43, 0x20)

    def pre_open_pyramid_hole(self):
        self._or_value(OVERWORLD_DATA+0x5B, 0x20)

    def pre_open_tr_bomb_doors(self):
        self._or_value(ROOM_DATA+0x47, 0x80)
        self._or_value(ROOM_DATA+0x01AB, 0x80)

    def set_starting_equipment(self, world: object, player: int):
        equip = [0] * (0x340 + 0x4F)
        equip[0x36C] = 0x18
        equip[0x36D] = 0x18
        equip[0x379] = 0x68
        starting_bomb_cap_upgrades = 10 if not world.bombbag[player] else 0
        starting_arrow_cap_upgrades = 30
        starting_bombs = 0
        starting_arrows = 0

        startingstate = CollectionState(world)

        if startingstate.has('Bow', player):
            equip[0x340] = 3 if startingstate.has('Silver Arrows', player) else 1
            equip[0x38E] |= 0x20  # progressive flag to get the correct hint in all cases
            if not world.bow_mode[player].startswith('retro'):
                equip[0x38E] |= 0x80
        if startingstate.has('Silver Arrows', player):
            equip[0x38E] |= 0x40

        if startingstate.has('Titans Mitts', player):
            equip[0x354] = 2
        elif startingstate.has('Power Glove', player):
            equip[0x354] = 1

        if startingstate.has('Golden Sword', player):
            equip[0x359] = 4
        elif startingstate.has('Tempered Sword', player):
            equip[0x359] = 3
        elif startingstate.has('Master Sword', player):
            equip[0x359] = 2
        elif startingstate.has('Fighter Sword', player):
            equip[0x359] = 1

        if startingstate.has('Mirror Shield', player):
            equip[0x35A] = 3
        elif startingstate.has('Red Shield', player):
            equip[0x35A] = 2
        elif startingstate.has('Blue Shield', player):
            equip[0x35A] = 1

        if startingstate.has('Red Mail', player):
            equip[0x35B] = 2
        elif startingstate.has('Blue Mail', player):
            equip[0x35B] = 1

        if startingstate.has('Magic Upgrade (1/4)', player):
            equip[0x37B] = 2
            equip[0x36E] = 0x80
        elif startingstate.has('Magic Upgrade (1/2)', player):
            equip[0x37B] = 1
            equip[0x36E] = 0x80

        for item in world.precollected_items:
            if item.player != player:
                continue

            if item.name in ['Bow', 'Silver Arrows', 'Progressive Bow', 'Progressive Bow (Alt)',
                             'Titans Mitts', 'Power Glove', 'Progressive Glove',
                             'Golden Sword', 'Tempered Sword', 'Master Sword', 'Fighter Sword', 'Progressive Sword',
                             'Mirror Shield', 'Red Shield', 'Blue Shield', 'Progressive Shield',
                             'Red Mail', 'Blue Mail', 'Progressive Armor',
                             'Magic Upgrade (1/4)', 'Magic Upgrade (1/2)']:
                continue

            set_table = {'Book of Mudora': (0x34E, 1), 'Hammer': (0x34B, 1), 'Bug Catching Net': (0x34D, 1), 'Hookshot': (0x342, 1), 'Magic Mirror': (0x353, 2),
                         'Cape': (0x352, 1), 'Lamp': (0x34A, 1), 'Moon Pearl': (0x357, 1), 'Cane of Somaria': (0x350, 1), 'Cane of Byrna': (0x351, 1),
                         'Fire Rod': (0x345, 1), 'Ice Rod': (0x346, 1), 'Bombos': (0x347, 1), 'Ether': (0x348, 1), 'Quake': (0x349, 1)}
            or_table = {'Green Pendant': (0x374, 0x04), 'Red Pendant': (0x374, 0x01), 'Blue Pendant': (0x374, 0x02),
                        'Crystal 1': (0x37A, 0x02), 'Crystal 2': (0x37A, 0x10), 'Crystal 3': (0x37A, 0x40), 'Crystal 4': (0x37A, 0x20),
                        'Crystal 5': (0x37A, 0x04), 'Crystal 6': (0x37A, 0x01), 'Crystal 7': (0x37A, 0x08),
                        'Big Key (Eastern Palace)': (0x367, 0x20), 'Compass (Eastern Palace)': (0x365, 0x20), 'Map (Eastern Palace)': (0x369, 0x20),
                        'Big Key (Desert Palace)': (0x367, 0x10), 'Compass (Desert Palace)': (0x365, 0x10), 'Map (Desert Palace)': (0x369, 0x10),
                        'Big Key (Tower of Hera)': (0x366, 0x20), 'Compass (Tower of Hera)': (0x364, 0x20), 'Map (Tower of Hera)': (0x368, 0x20),
                        'Big Key (Escape)': (0x367, 0xC0), 'Compass (Escape)': (0x365, 0xC0), 'Map (Escape)': (0x369, 0xC0),
                        'Big Key (Agahnims Tower)': (0x367, 0x08), 'Compass (Agahnims Tower)': (0x365, 0x08), 'Map (Agahnims Tower)': (0x369, 0x08),
                        'Big Key (Palace of Darkness)': (0x367, 0x02), 'Compass (Palace of Darkness)': (0x365, 0x02), 'Map (Palace of Darkness)': (0x369, 0x02),
                        'Big Key (Thieves Town)': (0x366, 0x10), 'Compass (Thieves Town)': (0x364, 0x10), 'Map (Thieves Town)': (0x368, 0x10),
                        'Big Key (Skull Woods)': (0x366, 0x80), 'Compass (Skull Woods)': (0x364, 0x80), 'Map (Skull Woods)': (0x368, 0x80),
                        'Big Key (Swamp Palace)': (0x367, 0x04), 'Compass (Swamp Palace)': (0x365, 0x04), 'Map (Swamp Palace)': (0x369, 0x04),
                        'Big Key (Ice Palace)': (0x366, 0x40), 'Compass (Ice Palace)': (0x364, 0x40), 'Map (Ice Palace)': (0x368, 0x40),
                        'Big Key (Misery Mire)': (0x367, 0x01), 'Compass (Misery Mire)': (0x365, 0x01), 'Map (Misery Mire)': (0x369, 0x01),
                        'Big Key (Turtle Rock)': (0x366, 0x08), 'Compass (Turtle Rock)': (0x364, 0x08), 'Map (Turtle Rock)': (0x368, 0x08),
                        'Big Key (Ganons Tower)': (0x366, 0x04), 'Compass (Ganons Tower)': (0x364, 0x04), 'Map (Ganons Tower)': (0x368, 0x04)}
            set_or_table = {'Flippers': (0x356, 1, 0x379, 0x02), 'Pegasus Boots': (0x355, 1, 0x379, 0x04),
                            'Shovel': (0x34C, 1, 0x38C, 0x04), 'Ocarina': (0x34C, 2, 0x38C, 0x02),
                            'Ocarina (Activated)': (0x34C, 3, 0x38C, 0x01),
                            'Mushroom': (0x344, 1, 0x38C, 0x20 | 0x08), 'Magic Powder': (0x344, 2, 0x38C, 0x10),
                            'Blue Boomerang': (0x341, 1, 0x38C, 0x80), 'Red Boomerang': (0x341, 2, 0x38C, 0x40)}
            keys = {'Small Key (Eastern Palace)': [0x37E], 'Small Key (Desert Palace)': [0x37F],
                    'Small Key (Tower of Hera)': [0x386],
                    'Small Key (Agahnims Tower)': [0x380], 'Small Key (Palace of Darkness)': [0x382],
                    'Small Key (Thieves Town)': [0x387],
                    'Small Key (Skull Woods)': [0x384], 'Small Key (Swamp Palace)': [0x381],
                    'Small Key (Ice Palace)': [0x385],
                    'Small Key (Misery Mire)': [0x383], 'Small Key (Turtle Rock)': [0x388],
                    'Small Key (Ganons Tower)': [0x389],
                    'Small Key (Universal)': [0x38B], 'Small Key (Escape)': [0x37C, 0x37D]}
            bottles = {'Bottle': 2, 'Bottle (Red Potion)': 3, 'Bottle (Green Potion)': 4, 'Bottle (Blue Potion)': 5,
                       'Bottle (Fairy)': 6, 'Bottle (Bee)': 7, 'Bottle (Good Bee)': 8}
            rupees = {'Rupee (1)': 1, 'Rupees (5)': 5, 'Rupees (20)': 20, 'Rupees (50)': 50, 'Rupees (100)': 100, 'Rupees (300)': 300}
            bomb_caps = {'Bomb Upgrade (+5)': 5, 'Bomb Upgrade (+10)': 10}
            arrow_caps = {'Arrow Upgrade (+5)': 5, 'Arrow Upgrade (+10)': 10}
            bombs = {'Single Bomb': 1, 'Bombs (3)': 3, 'Bombs (10)': 10}
            arrows = {'Single Arrow': 1, 'Arrows (10)': 10}

            if item.name in set_table:
                equip[set_table[item.name][0]] = set_table[item.name][1]
            elif item.name in or_table:
                equip[or_table[item.name][0]] |= or_table[item.name][1]
            elif item.name in set_or_table:
                equip[set_or_table[item.name][0]] = set_or_table[item.name][1]
                equip[set_or_table[item.name][2]] |= set_or_table[item.name][3]
            elif item.name in keys:
                for address in keys[item.name]:
                    equip[address] = min(equip[address] + 1, 99)
            elif item.name in bottles:
                if equip[0x34F] < world.difficulty_requirements[player].progressive_bottle_limit:
                    equip[0x35C + equip[0x34F]] = bottles[item.name]
                    equip[0x34F] += 1
            elif item.name in rupees:
                equip[0x360:0x362] = list(min(equip[0x360] + (equip[0x361] << 8) + rupees[item.name], 9999).to_bytes(2, byteorder='little', signed=False))
                equip[0x362:0x364] = list(min(equip[0x362] + (equip[0x363] << 8) + rupees[item.name], 9999).to_bytes(2, byteorder='little', signed=False))
            elif item.name in bomb_caps:
                starting_bomb_cap_upgrades += bomb_caps[item.name]
            elif item.name in arrow_caps:
                starting_arrow_cap_upgrades += arrow_caps[item.name]
            elif item.name in bombs:
                starting_bombs += bombs[item.name]
            elif item.name in arrows:
                if world.bow_mode[player].startswith('retro'):
                    equip[0x38E] |= 0x80
                    starting_arrows = 1
                else:
                    starting_arrows += arrows[item.name]
            elif item.name in ['Piece of Heart', 'Boss Heart Container', 'Sanctuary Heart Container']:
                if item.name == 'Piece of Heart':
                    equip[0x36B] = (equip[0x36B] + 1) % 4
                if item.name != 'Piece of Heart' or equip[0x36B] == 0:
                    equip[0x36C] = min(equip[0x36C] + 0x08, 0xA0)
                    equip[0x36D] = min(equip[0x36D] + 0x08, 0xA0)
            else:
                raise RuntimeError(f'Unsupported item in starting equipment: {item.name}')

        equip[0x370] = min(starting_bomb_cap_upgrades, 50)
        equip[0x371] = min(starting_arrow_cap_upgrades, 70)
        equip[0x343] = min(starting_bombs, equip[0x370])
        equip[0x377] = min(starting_arrows, equip[0x371])
        
        # Assertion and copy equip to initial_sram_bytes
        assert equip[:0x340] == [0] * 0x340
        self._initial_sram_bytes[0x340:0x38F] = equip[0x340:0x38F]

        # Set counters and highest equipment values
        self._initial_sram_bytes[0x471] = count_set_bits(self._initial_sram_bytes[0x37A])
        self._initial_sram_bytes[0x429] = count_set_bits(self._initial_sram_bytes[0x374])
        self._initial_sram_bytes[0x417] = self._initial_sram_bytes[0x359]
        self._initial_sram_bytes[0x422] = self._initial_sram_bytes[0x35A]
        self._initial_sram_bytes[0x46E] = self._initial_sram_bytes[0x35B]

        if world.swords[player] == "swordless":
            self._initial_sram_bytes[0x359] = 0xFF
            self._initial_sram_bytes[0x417] = 0x00

    def set_starting_rupees(self, rupees: int):
        if not (-1 < rupees < 10000):
            raise ValueError("Starting rupees must be between 0 and 9999")
        self._initial_sram_bytes[0x362] = self._initial_sram_bytes[0x360] = rupees & 0xFF
        self._initial_sram_bytes[0x363] = self._initial_sram_bytes[0x361] = rupees >> 8

    def set_progress_indicator(self, indicator: int):
        self._set_value(0x3C5, indicator)

    def set_progress_flags(self, flags: int):
        self._set_value(0x3C6, flags)

    def set_starting_entrance(self, entrance: int):
        self._set_value(0x3C8, entrance)

    def set_starting_timer(self, seconds: int):
        timer = (seconds * 60).to_bytes(4, "little")
        self._initial_sram_bytes[0x454] = timer[0]
        self._initial_sram_bytes[0x455] = timer[1]
        self._initial_sram_bytes[0x456] = timer[2]
        self._initial_sram_bytes[0x457] = timer[3]

    def set_swordless_curtains(self):
        self._or_value(ROOM_DATA+0x61, 0x80)
        self._or_value(ROOM_DATA+0x93, 0x80)

    def get_initial_sram(self):
        assert len(self._initial_sram_bytes) == SRAM_SIZE

        return self._initial_sram_bytes[:]
