
from BaseClasses import OWEdge, Direction, Terrain, WorldType, PolSlot
from enum import Enum, unique
from Utils import bidict

@unique
class OpenStd(Enum):
    Open = 0
    Standard = 1

@unique
class IsParallel(Enum):
    No = 0
    Yes = 1

# constants
We = Direction.West
Ea = Direction.East
So = Direction.South
No = Direction.North

Ld = Terrain.Land
Wr = Terrain.Water

LW = WorldType.Light
DW = WorldType.Dark

Vt = PolSlot.NorthSouth
Hz = PolSlot.EastWest

Op = OpenStd.Open
St = OpenStd.Standard

PL = IsParallel.Yes
NP = IsParallel.No


def create_owedges(world, player):
    edges = [
                             # name,                        owID,dir,type,edge_id,(owSlot)        vram
        create_owedge(player, 'Lost Woods NW',               0x00, No, Ld, 0x00)      .coordInfo(0x00a0, 0x0284).special_entrance(0x80),
        create_owedge(player, 'Lost Woods SW',               0x00, So, Ld, 0x01, 0x08).coordInfo(0x0058, 0x2000),
        create_owedge(player, 'Lost Woods SC',               0x00, So, Ld, 0x02, 0x08).coordInfo(0x0178, 0x2020),
        create_owedge(player, 'Lost Woods SE',               0x00, So, Ld, 0x03, 0x09).coordInfo(0x0388, 0x2060),
        create_owedge(player, 'Lost Woods EN',               0x00, Ea, Ld, 0x00, 0x01).coordInfo(0x0088, 0x0180),
        create_owedge(player, 'Lumberjack SW',               0x02, So, Ld, 0x00)      .coordInfo(0x04cc, 0x100a),
        create_owedge(player, 'Lumberjack WN',               0x02, We, Ld, 0x00)      .coordInfo(0x0088, 0x00e0),
        create_owedge(player, 'West Death Mountain EN',      0x03, Ea, Ld, 0x01, 0x04).coordInfo(0x0070, 0x0180),
        create_owedge(player, 'West Death Mountain ES',      0x03, Ea, Ld, 0x03, 0x0c).coordInfo(0x0340, 0x1780),
        create_owedge(player, 'East Death Mountain WN',      0x05, We, Ld, 0x01, 0x05).coordInfo(0x0070, 0x0060),
        create_owedge(player, 'East Death Mountain WS',      0x05, We, Ld, 0x03, 0x0d).coordInfo(0x0340, 0x1660),
        create_owedge(player, 'East Death Mountain EN',      0x05, Ea, Ld, 0x02, 0x06).coordInfo(0x0078, 0x0180),
        create_owedge(player, 'Death Mountain TR Pegs WN',   0x07, We, Ld, 0x02)      .coordInfo(0x0078, 0x00e0),
        create_owedge(player, 'Mountain Pass NW',            0x0a, No, Ld, 0x01)      .coordInfo(0x04cc, 0x180a),
        create_owedge(player, 'Mountain Pass SE',            0x0a, So, Ld, 0x04)      .coordInfo(0x0518, 0x1012),
        create_owedge(player, 'Zora Waterfall NE',           0x0f, No, Ld, 0x02)      .coordInfo(0x0f80, 0x009a).special_entrance(0x82),
        create_owedge(player, 'Zora Waterfall SE',           0x0f, So, Ld, 0x05)      .coordInfo(0x0f80, 0x1020),
        create_owedge(player, 'Lost Woods Pass NW',          0x10, No, Ld, 0x03)      .coordInfo(0x0058, 0x1800),
        create_owedge(player, 'Lost Woods Pass NE',          0x10, No, Ld, 0x04)      .coordInfo(0x0178, 0x181e),
        create_owedge(player, 'Lost Woods Pass SW',          0x10, So, Ld, 0x06)      .coordInfo(0x0088, 0x1002),
        create_owedge(player, 'Lost Woods Pass SE',          0x10, So, Ld, 0x07)      .coordInfo(0x0148, 0x101a),
        create_owedge(player, 'Kakariko Fortune NE',         0x11, No, Ld, 0x05)      .coordInfo(0x0388, 0x1820),
        create_owedge(player, 'Kakariko Fortune SC',         0x11, So, Ld, 0x08)      .coordInfo(0x0318, 0x1014),
        create_owedge(player, 'Kakariko Fortune EN',         0x11, Ea, Ld, 0x04)      .coordInfo(0x046c, 0x00c0),
        create_owedge(player, 'Kakariko Fortune ES',         0x11, Ea, Ld, 0x05)      .coordInfo(0x0580, 0x08c0),
        create_owedge(player, 'Kakariko Pond NE',            0x12, No, Ld, 0x06)      .coordInfo(0x0518, 0x1812),
        create_owedge(player, 'Kakariko Pond SW',            0x12, So, Ld, 0x09)      .coordInfo(0x04a4, 0x1006),
        create_owedge(player, 'Kakariko Pond SE',            0x12, So, Ld, 0x0a)      .coordInfo(0x0524, 0x1016),
        create_owedge(player, 'Kakariko Pond WN',            0x12, We, Ld, 0x04)      .coordInfo(0x046c, 0x00e0),
        create_owedge(player, 'Kakariko Pond WS',            0x12, We, Ld, 0x05)      .coordInfo(0x0580, 0x08e0),
        create_owedge(player, 'Kakariko Pond EN',            0x12, Ea, Ld, 0x06)      .coordInfo(0x04c4, 0x0340),
        create_owedge(player, 'Kakariko Pond ES',            0x12, Ea, Ld, 0x07)      .coordInfo(0x0570, 0x08c0),
        create_owedge(player, 'Sanctuary WN',                0x13, We, Ld, 0x06)      .coordInfo(0x04c4, 0x0360),
        create_owedge(player, 'Sanctuary WS',                0x13, We, Ld, 0x07)      .coordInfo(0x0570, 0x08e0),
        create_owedge(player, 'Sanctuary EC',                0x13, Ea, Ld, 0x08)      .coordInfo(0x050c, 0x04c0),
        create_owedge(player, 'Graveyard WC',                0x14, We, Ld, 0x08)      .coordInfo(0x050c, 0x04e0),
        create_owedge(player, 'Graveyard EC',                0x14, Ea, Ld, 0x09)      .coordInfo(0x0504, 0x04c0),
        create_owedge(player, 'River Bend SW',               0x15, So, Ld, 0x0b)      .coordInfo(0x0a9c, 0x1004),
        create_owedge(player, 'River Bend SC',               0x15, So, Wr, 0x0c)      .coordInfo(0x0b30, 0x1018),
        create_owedge(player, 'River Bend SE',               0x15, So, Ld, 0x0d)      .coordInfo(0x0b88, 0x1020),
        create_owedge(player, 'River Bend WC',               0x15, We, Ld, 0x09)      .coordInfo(0x0504, 0x04e0),
        create_owedge(player, 'River Bend EN',               0x15, Ea, Wr, 0x0a)      .coordInfo(0x0484, 0x01c0),
        create_owedge(player, 'River Bend EC',               0x15, Ea, Ld, 0x0b)      .coordInfo(0x04e0, 0x04c0),
        create_owedge(player, 'River Bend ES',               0x15, Ea, Ld, 0x0c)      .coordInfo(0x0574, 0x08c0),
        create_owedge(player, 'Potion Shop WN',              0x16, We, Wr, 0x0a)      .coordInfo(0x0484, 0x01e0),
        create_owedge(player, 'Potion Shop WC',              0x16, We, Ld, 0x0b)      .coordInfo(0x04e0, 0x04e0),
        create_owedge(player, 'Potion Shop WS',              0x16, We, Ld, 0x0c)      .coordInfo(0x0574, 0x08e0),
        create_owedge(player, 'Potion Shop EN',              0x16, Ea, Wr, 0x0d)      .coordInfo(0x0454, 0x00c0),
        create_owedge(player, 'Potion Shop EC',              0x16, Ea, Ld, 0x0e)      .coordInfo(0x0494, 0x01c0),
        create_owedge(player, 'Zora Approach NE',            0x17, No, Ld, 0x07)      .coordInfo(0x0f80, 0x1820),
        create_owedge(player, 'Zora Approach WN',            0x17, We, Wr, 0x0d)      .coordInfo(0x0454, 0x00e0),
        create_owedge(player, 'Zora Approach WC',            0x17, We, Ld, 0x0e)      .coordInfo(0x0494, 0x01e0),
        create_owedge(player, 'Kakariko NW',                 0x18, No, Ld, 0x08)      .coordInfo(0x0088, 0x1802),
        create_owedge(player, 'Kakariko NC',                 0x18, No, Ld, 0x09)      .coordInfo(0x0148, 0x181a),
        create_owedge(player, 'Kakariko NE',                 0x18, No, Ld, 0x0a, 0x19).coordInfo(0x0318, 0x1854),
        create_owedge(player, 'Kakariko SE',                 0x18, So, Ld, 0x0f, 0x21).coordInfo(0x0370, 0x2060),
        create_owedge(player, 'Kakariko ES',                 0x18, Ea, Ld, 0x10, 0x21).coordInfo(0x0928, 0x1680),
        create_owedge(player, 'Forgotten Forest NW',         0x1a, No, Ld, 0x0b)      .coordInfo(0x04a4, 0x1806),
        create_owedge(player, 'Forgotten Forest NE',         0x1a, No, Ld, 0x0c)      .coordInfo(0x0524, 0x1816),
        create_owedge(player, 'Forgotten Forest ES',         0x1a, Ea, Ld, 0x0f)      .coordInfo(0x0728, 0x06c0),
        create_owedge(player, 'Hyrule Castle SW',            0x1b, So, Ld, 0x10, 0x23).coordInfo(0x068c, 0x2002),
        create_owedge(player, 'Hyrule Castle SE',            0x1b, So, Ld, 0x11, 0x24).coordInfo(0x0924, 0x2054),
        create_owedge(player, 'Hyrule Castle WN',            0x1b, We, Ld, 0x0f)      .coordInfo(0x0728, 0x0660),
        create_owedge(player, 'Hyrule Castle ES',            0x1b, Ea, Ld, 0x11, 0x24).coordInfo(0x0890, 0x1280),
        create_owedge(player, 'Wooden Bridge NW',            0x1d, No, Ld, 0x0d)      .coordInfo(0x0a9c, 0x1804),
        create_owedge(player, 'Wooden Bridge NC',            0x1d, No, Wr, 0x0e)      .coordInfo(0x0b30, 0x1818),
        create_owedge(player, 'Wooden Bridge NE',            0x1d, No, Ld, 0x0f)      .coordInfo(0x0b88, 0x1820),
        create_owedge(player, 'Wooden Bridge SW',            0x1d, So, Ld, 0x0e)      .coordInfo(0x0aa8, 0x1006),
        create_owedge(player, 'Eastern Palace SW',           0x1e, So, Ld, 0x13, 0x26).coordInfo(0x0c80, 0x2002),
        create_owedge(player, 'Eastern Palace SE',           0x1e, So, Ld, 0x14, 0x27).coordInfo(0x0f78, 0x2060),
        create_owedge(player, 'Blacksmith WS',               0x22, We, Ld, 0x10)      .coordInfo(0x0928, 0x05e0),
        create_owedge(player, 'Sand Dunes NW',               0x25, No, Ld, 0x10)      .coordInfo(0x0aa8, 0x1806),
        create_owedge(player, 'Sand Dunes SC',               0x25, So, Ld, 0x12)      .coordInfo(0x0af0, 0x100e),
        create_owedge(player, 'Sand Dunes WN',               0x25, We, Ld, 0x11)      .coordInfo(0x0890, 0x01e0),
        create_owedge(player, 'Maze Race ES',                0x28, Ea, Ld, 0x12)      .coordInfo(0x0bc0, 0x0940),
        create_owedge(player, 'Kakariko Suburb NE',          0x29, No, Ld, 0x11)      .coordInfo(0x0370, 0x1820),
        create_owedge(player, 'Kakariko Suburb WS',          0x29, We, Ld, 0x12)      .coordInfo(0x0bc0, 0x0960),
        create_owedge(player, 'Kakariko Suburb ES',          0x29, Ea, Ld, 0x13)      .coordInfo(0x0b80, 0x0940),
        create_owedge(player, 'Flute Boy SW',                0x2a, So, Ld, 0x15)      .coordInfo(0x044c, 0x1000),
        create_owedge(player, 'Flute Boy SC',                0x2a, So, Ld, 0x16)      .coordInfo(0x04e8, 0x100c),
        create_owedge(player, 'Flute Boy WS',                0x2a, We, Ld, 0x13)      .coordInfo(0x0b80, 0x0960),
        create_owedge(player, 'Central Bonk Rocks NW',       0x2b, No, Ld, 0x12)      .coordInfo(0x068c, 0x1802),
        create_owedge(player, 'Central Bonk Rocks SW',       0x2b, So, Ld, 0x17)      .coordInfo(0x069c, 0x1004),
        create_owedge(player, 'Central Bonk Rocks EN',       0x2b, Ea, Ld, 0x14)      .coordInfo(0x0ac0, 0x0340),
        create_owedge(player, 'Central Bonk Rocks EC',       0x2b, Ea, Ld, 0x15)      .coordInfo(0x0b18, 0x05c0),
        create_owedge(player, 'Central Bonk Rocks ES',       0x2b, Ea, Ld, 0x16)      .coordInfo(0x0b8c, 0x08c0),
        create_owedge(player, 'Links House NE',              0x2c, No, Ld, 0x13)      .coordInfo(0x0924, 0x1814),
        create_owedge(player, 'Links House SC',              0x2c, So, Ld, 0x18)      .coordInfo(0x08e0, 0x100e),
        create_owedge(player, 'Links House WN',              0x2c, We, Ld, 0x14)      .coordInfo(0x0ac0, 0x0360),
        create_owedge(player, 'Links House WC',              0x2c, We, Ld, 0x15)      .coordInfo(0x0b18, 0x05e0),
        create_owedge(player, 'Links House WS',              0x2c, We, Ld, 0x16)      .coordInfo(0x0b8c, 0x08a0),
        create_owedge(player, 'Links House ES',              0x2c, Ea, Ld, 0x17)      .coordInfo(0x0b80, 0x08c0),
        create_owedge(player, 'Stone Bridge NC',             0x2d, No, Ld, 0x14)      .coordInfo(0x0af0, 0x180e),
        create_owedge(player, 'Stone Bridge SC',             0x2d, So, Ld, 0x19)      .coordInfo(0x0ae0, 0x100c),
        create_owedge(player, 'Stone Bridge WC',             0x2d, We, Wr, 0x17)      .coordInfo(0x0b1c, 0x061c).special_entrance(0x81),
        create_owedge(player, 'Stone Bridge WS',             0x2d, We, Ld, 0x18)      .coordInfo(0x0b80, 0x08e0),
        create_owedge(player, 'Stone Bridge EN',             0x2d, Ea, Ld, 0x18)      .coordInfo(0x0a90, 0x01c0),
        create_owedge(player, 'Stone Bridge EC',             0x2d, Ea, Wr, 0x19)      .coordInfo(0x0b3c, 0x0640),
        create_owedge(player, 'Tree Line NW',                0x2e, No, Ld, 0x15)      .coordInfo(0x0c80, 0x1802),
        create_owedge(player, 'Tree Line SC',                0x2e, So, Wr, 0x1a)      .coordInfo(0x0d48, 0x101a),
        create_owedge(player, 'Tree Line SE',                0x2e, So, Ld, 0x1b)      .coordInfo(0x0d98, 0x1020),
        create_owedge(player, 'Tree Line WN',                0x2e, We, Ld, 0x19)      .coordInfo(0x0a90, 0x01e0),
        create_owedge(player, 'Tree Line WC',                0x2e, We, Wr, 0x1a)      .coordInfo(0x0b3c, 0x0660),
        create_owedge(player, 'Eastern Nook NE',             0x2f, No, Ld, 0x16)      .coordInfo(0x0f78, 0x1820),
        create_owedge(player, 'Desert EC',                   0x30, Ea, Ld, 0x1e, 0x39).coordInfo(0x0ee4, 0x1480),
        create_owedge(player, 'Desert ES',                   0x30, Ea, Ld, 0x1f, 0x39).coordInfo(0x0f90, 0x1980),
        create_owedge(player, 'Flute Boy Approach NW',       0x32, No, Ld, 0x17)      .coordInfo(0x044c, 0x1800),
        create_owedge(player, 'Flute Boy Approach NC',       0x32, No, Ld, 0x18)      .coordInfo(0x04e8, 0x180c),
        create_owedge(player, 'Flute Boy Approach EC',       0x32, Ea, Ld, 0x1a)      .coordInfo(0x0d04, 0x05c0),
        create_owedge(player, 'C Whirlpool NW',              0x33, No, Ld, 0x19)      .coordInfo(0x069c, 0x1804),
        create_owedge(player, 'C Whirlpool SC',              0x33, So, Ld, 0x1c)      .coordInfo(0x0728, 0x1016),
        create_owedge(player, 'C Whirlpool WC',              0x33, We, Ld, 0x1b)      .coordInfo(0x0d04, 0x05e0),
        create_owedge(player, 'C Whirlpool EN',              0x33, Ea, Ld, 0x1b)      .coordInfo(0x0cad, 0x02c0),
        create_owedge(player, 'C Whirlpool EC',              0x33, Ea, Wr, 0x1c)      .coordInfo(0x0d0b, 0x05c0),
        create_owedge(player, 'C Whirlpool ES',              0x33, Ea, Ld, 0x1d)      .coordInfo(0x0d76, 0x08c0),
        create_owedge(player, 'Statues NC',                  0x34, No, Ld, 0x1a)      .coordInfo(0x08e0, 0x180e),
        create_owedge(player, 'Statues SC',                  0x34, So, Ld, 0x1d)      .coordInfo(0x08f0, 0x1010),
        create_owedge(player, 'Statues WN',                  0x34, We, Ld, 0x1c)      .coordInfo(0x0cad, 0x02e0),
        create_owedge(player, 'Statues WC',                  0x34, We, Wr, 0x1d)      .coordInfo(0x0d0b, 0x05e0),
        create_owedge(player, 'Statues WS',                  0x34, We, Ld, 0x1e)      .coordInfo(0x0d76, 0x08e0),
        create_owedge(player, 'Lake Hylia NW',               0x35, No, Ld, 0x1b)      .coordInfo(0x0ae0, 0x180c),
        create_owedge(player, 'Lake Hylia NC',               0x35, No, Wr, 0x1c, 0x36).coordInfo(0x0d48, 0x185a),
        create_owedge(player, 'Lake Hylia NE',               0x35, No, Ld, 0x1d, 0x36).coordInfo(0x0d98, 0x1860),
        create_owedge(player, 'Lake Hylia WS',               0x35, We, Ld, 0x24, 0x3d).coordInfo(0x0f98, 0x1860),
        create_owedge(player, 'Lake Hylia EC',               0x35, Ea, Wr, 0x24, 0x3e).coordInfo(0x0f30, 0x1680),
        create_owedge(player, 'Lake Hylia ES',               0x35, Ea, Ld, 0x25, 0x3e).coordInfo(0x0f94, 0x1880),
        create_owedge(player, 'Ice Cave SW',                 0x37, So, Wr, 0x1e)      .coordInfo(0x0e80, 0x1002),
        create_owedge(player, 'Ice Cave SE',                 0x37, So, Ld, 0x1f)      .coordInfo(0x0f50, 0x101c),
        create_owedge(player, 'Desert Pass WC',              0x3a, We, Ld, 0x1f)      .coordInfo(0x0ee4, 0x03e0),
        create_owedge(player, 'Desert Pass WS',              0x3a, We, Ld, 0x20)      .coordInfo(0x0f90, 0x0860),
        create_owedge(player, 'Desert Pass EC',              0x3a, Ea, Ld, 0x20)      .coordInfo(0x0f18, 0x0640),
        create_owedge(player, 'Desert Pass ES',              0x3a, Ea, Ld, 0x21)      .coordInfo(0x0fcb, 0x08c0),
        create_owedge(player, 'Dam NC',                      0x3b, No, Ld, 0x1e)      .coordInfo(0x0728, 0x1816),
        create_owedge(player, 'Dam WC',                      0x3b, We, Ld, 0x21)      .coordInfo(0x0f18, 0x0660),
        create_owedge(player, 'Dam WS',                      0x3b, We, Ld, 0x22)      .coordInfo(0x0fc8, 0x08e0),
        create_owedge(player, 'Dam EC',                      0x3b, Ea, Ld, 0x22)      .coordInfo(0x0ef0, 0x04c0),
        create_owedge(player, 'South Pass NC',               0x3c, No, Ld, 0x1f)      .coordInfo(0x08f0, 0x1810),
        create_owedge(player, 'South Pass WC',               0x3c, We, Ld, 0x23)      .coordInfo(0x0ef0, 0x04e0),
        create_owedge(player, 'South Pass ES',               0x3c, Ea, Ld, 0x23)      .coordInfo(0x0f98, 0x08c0),
        create_owedge(player, 'Octoballoon NW',              0x3f, No, Wr, 0x20)      .coordInfo(0x0e80, 0x1802),
        create_owedge(player, 'Octoballoon NE',              0x3f, No, Ld, 0x21)      .coordInfo(0x0f50, 0x181c),
        create_owedge(player, 'Octoballoon WC',              0x3f, We, Wr, 0x25)      .coordInfo(0x0f30, 0x05e0),
        create_owedge(player, 'Octoballoon WS',              0x3f, We, Ld, 0x26)      .coordInfo(0x0f94, 0x0860),
        create_owedge(player, 'Skull Woods SW',              0x40, So, Ld, 0x21, 0x48).coordInfo(0x0058, 0x2000),
        create_owedge(player, 'Skull Woods SC',              0x40, So, Ld, 0x22, 0x48).coordInfo(0x0178, 0x2020),
        create_owedge(player, 'Skull Woods SE',              0x40, So, Ld, 0x23, 0x49).coordInfo(0x0388, 0x2060),
        create_owedge(player, 'Skull Woods EN',              0x40, Ea, Ld, 0x26, 0x41).coordInfo(0x0088, 0x0180),
        create_owedge(player, 'Dark Lumberjack SW',          0x42, So, Ld, 0x20)      .coordInfo(0x04cc, 0x100a),
        create_owedge(player, 'Dark Lumberjack WN',          0x42, We, Ld, 0x27)      .coordInfo(0x0088, 0x00e0),
        create_owedge(player, 'West Dark Death Mountain EN', 0x43, Ea, Ld, 0x27, 0x44).coordInfo(0x0070, 0x0180),
        create_owedge(player, 'West Dark Death Mountain ES', 0x43, Ea, Ld, 0x29, 0x4c).coordInfo(0x0340, 0x1780),
        create_owedge(player, 'East Dark Death Mountain WN', 0x45, We, Ld, 0x28)      .coordInfo(0x0070, 0x0060),
        create_owedge(player, 'East Dark Death Mountain WS', 0x45, We, Ld, 0x2a, 0x4d).coordInfo(0x0340, 0x1660),
        create_owedge(player, 'East Dark Death Mountain EN', 0x45, Ea, Ld, 0x28, 0x46).coordInfo(0x0078, 0x0180),
        create_owedge(player, 'Turtle Rock WN',              0x47, We, Ld, 0x29)      .coordInfo(0x0078, 0x00e0),
        create_owedge(player, 'Bumper Cave NW',              0x4a, No, Ld, 0x22)      .coordInfo(0x04cc, 0x180a),
        create_owedge(player, 'Bumper Cave SE',              0x4a, So, Ld, 0x24)      .coordInfo(0x0518, 0x1012),
        create_owedge(player, 'Catfish SE',                  0x4f, So, Ld, 0x25)      .coordInfo(0x0f80, 0x1020),
        create_owedge(player, 'Skull Woods Pass NW',         0x50, No, Ld, 0x23)      .coordInfo(0x0058, 0x181e),
        create_owedge(player, 'Skull Woods Pass NE',         0x50, No, Ld, 0x24)      .coordInfo(0x0178, 0x1800),
        create_owedge(player, 'Skull Woods Pass SW',         0x50, So, Ld, 0x26)      .coordInfo(0x0088, 0x1002),
        create_owedge(player, 'Skull Woods Pass SE',         0x50, So, Ld, 0x27)      .coordInfo(0x0148, 0x101a),
        create_owedge(player, 'Dark Fortune NE',             0x51, No, Ld, 0x25)      .coordInfo(0x0388, 0x1820),
        create_owedge(player, 'Dark Fortune SC',             0x51, So, Ld, 0x28)      .coordInfo(0x0318, 0x1014),
        create_owedge(player, 'Dark Fortune EN',             0x51, Ea, Ld, 0x2a)      .coordInfo(0x046c, 0x00c0),
        create_owedge(player, 'Dark Fortune ES',             0x51, Ea, Ld, 0x2b)      .coordInfo(0x0580, 0x08c0),
        create_owedge(player, 'Outcast Pond NE',             0x52, No, Ld, 0x26)      .coordInfo(0x0518, 0x1812),
        create_owedge(player, 'Outcast Pond SW',             0x52, So, Ld, 0x29)      .coordInfo(0x04a4, 0x1006),
        create_owedge(player, 'Outcast Pond SE',             0x52, So, Ld, 0x2a)      .coordInfo(0x0524, 0x1016),
        create_owedge(player, 'Outcast Pond WN',             0x52, We, Ld, 0x2b)      .coordInfo(0x046c, 0x00e0),
        create_owedge(player, 'Outcast Pond WS',             0x52, We, Ld, 0x2c)      .coordInfo(0x0580, 0x08e0),
        create_owedge(player, 'Outcast Pond EN',             0x52, Ea, Ld, 0x2c)      .coordInfo(0x04c4, 0x0340),
        create_owedge(player, 'Outcast Pond ES',             0x52, Ea, Ld, 0x2d)      .coordInfo(0x0570, 0x08c0),
        create_owedge(player, 'Dark Chapel WN',              0x53, We, Ld, 0x2d)      .coordInfo(0x04c4, 0x0360),
        create_owedge(player, 'Dark Chapel WS',              0x53, We, Ld, 0x2e)      .coordInfo(0x0570, 0x08e0),
        create_owedge(player, 'Dark Chapel EC',              0x53, Ea, Ld, 0x2e)      .coordInfo(0x050c, 0x04c0),
        create_owedge(player, 'Dark Graveyard WC',           0x54, We, Ld, 0x2f)      .coordInfo(0x050c, 0x04e0),
        create_owedge(player, 'Dark Graveyard EC',           0x54, Ea, Ld, 0x2f)      .coordInfo(0x0504, 0x04c0),
        create_owedge(player, 'Qirn Jump SW',                0x55, So, Ld, 0x2b)      .coordInfo(0x0a9c, 0x1004),
        create_owedge(player, 'Qirn Jump SC',                0x55, So, Wr, 0x2c)      .coordInfo(0x0b30, 0x1018),
        create_owedge(player, 'Qirn Jump SE',                0x55, So, Ld, 0x2d)      .coordInfo(0x0b88, 0x1020),
        create_owedge(player, 'Qirn Jump WC',                0x55, We, Ld, 0x30)      .coordInfo(0x0504, 0x04e0),
        create_owedge(player, 'Qirn Jump EN',                0x55, Ea, Wr, 0x30)      .coordInfo(0x0484, 0x01c0),
        create_owedge(player, 'Qirn Jump EC',                0x55, Ea, Ld, 0x31)      .coordInfo(0x04e0, 0x04c0),
        create_owedge(player, 'Qirn Jump ES',                0x55, Ea, Ld, 0x32)      .coordInfo(0x0574, 0x08c0),
        create_owedge(player, 'Dark Witch WN',               0x56, We, Wr, 0x31)      .coordInfo(0x0484, 0x01e0),
        create_owedge(player, 'Dark Witch WC',               0x56, We, Ld, 0x32)      .coordInfo(0x04e0, 0x04e0),
        create_owedge(player, 'Dark Witch WS',               0x56, We, Ld, 0x33)      .coordInfo(0x0574, 0x08e0),
        create_owedge(player, 'Dark Witch EN',               0x56, Ea, Wr, 0x33)      .coordInfo(0x0454, 0x00c0),
        create_owedge(player, 'Dark Witch EC',               0x56, Ea, Ld, 0x34)      .coordInfo(0x0494, 0x01c0),
        create_owedge(player, 'Catfish Approach NE',         0x57, No, Ld, 0x27)      .coordInfo(0x0f80, 0x1820),
        create_owedge(player, 'Catfish Approach WN',         0x57, We, Wr, 0x34)      .coordInfo(0x0454, 0x00e0),
        create_owedge(player, 'Catfish Approach WC',         0x57, We, Ld, 0x35)      .coordInfo(0x0494, 0x01e0),
        create_owedge(player, 'Village of Outcasts NW',      0x58, No, Ld, 0x28)      .coordInfo(0x0088, 0x1802),
        create_owedge(player, 'Village of Outcasts NC',      0x58, No, Ld, 0x29)      .coordInfo(0x0148, 0x181a),
        create_owedge(player, 'Village of Outcasts NE',      0x58, No, Ld, 0x2a, 0x59).coordInfo(0x0318, 0x1854),
        create_owedge(player, 'Village of Outcasts SE',      0x58, So, Ld, 0x2f, 0x61).coordInfo(0x0370, 0x2060),
        create_owedge(player, 'Village of Outcasts ES',      0x58, Ea, Ld, 0x35, 0x61).coordInfo(0x0928, 0x1680),
        create_owedge(player, 'Shield Shop NW',              0x5a, No, Ld, 0x2b)      .coordInfo(0x04a4, 0x1806),
        create_owedge(player, 'Shield Shop NE',              0x5a, No, Ld, 0x2c)      .coordInfo(0x0524, 0x1816),
        create_owedge(player, 'Pyramid SW',                  0x5b, So, Ld, 0x30, 0x63).coordInfo(0x068c, 0x2002),
        create_owedge(player, 'Pyramid SE',                  0x5b, So, Ld, 0x31, 0x64).coordInfo(0x0924, 0x2054),
        create_owedge(player, 'Pyramid ES',                  0x5b, Ea, Ld, 0x36, 0x64).coordInfo(0x0890, 0x1280),
        create_owedge(player, 'Broken Bridge NW',            0x5d, No, Ld, 0x2d)      .coordInfo(0x0a9c, 0x1804),
        create_owedge(player, 'Broken Bridge NC',            0x5d, No, Wr, 0x2e)      .coordInfo(0x0b30, 0x1818),
        create_owedge(player, 'Broken Bridge NE',            0x5d, No, Ld, 0x2f)      .coordInfo(0x0b88, 0x1820),
        create_owedge(player, 'Broken Bridge SW',            0x5d, So, Ld, 0x2e)      .coordInfo(0x0aa8, 0x1006),
        create_owedge(player, 'Palace of Darkness SW',       0x5e, So, Ld, 0x33, 0x66).coordInfo(0x0c80, 0x2002),
        create_owedge(player, 'Palace of Darkness SE',       0x5e, So, Ld, 0x34, 0x67).coordInfo(0x0f78, 0x2060),
        create_owedge(player, 'Hammer Pegs WS',              0x62, We, Ld, 0x36)      .coordInfo(0x0928, 0x05e0),
        create_owedge(player, 'Dark Dunes NW',               0x65, No, Ld, 0x30)      .coordInfo(0x0aa8, 0x1806),
        create_owedge(player, 'Dark Dunes SC',               0x65, So, Ld, 0x32)      .coordInfo(0x0af0, 0x100e),
        create_owedge(player, 'Dark Dunes WN',               0x65, We, Ld, 0x37)      .coordInfo(0x0890, 0x01e0),
        create_owedge(player, 'Dig Game EC',                 0x68, Ea, Ld, 0x37)      .coordInfo(0x0b64, 0x08c0),
        create_owedge(player, 'Dig Game ES',                 0x68, Ea, Ld, 0x38)      .coordInfo(0x0bc0, 0x0940),
        create_owedge(player, 'Frog NE',                     0x69, No, Ld, 0x31)      .coordInfo(0x0370, 0x1820),
        create_owedge(player, 'Frog WC',                     0x69, We, Ld, 0x38)      .coordInfo(0x0b64, 0x08e0),
        create_owedge(player, 'Frog WS',                     0x69, We, Ld, 0x39)      .coordInfo(0x0bc0, 0x0960),
        create_owedge(player, 'Frog ES',                     0x69, Ea, Ld, 0x39)      .coordInfo(0x0b80, 0x0940),
        create_owedge(player, 'Stumpy SW',                   0x6a, So, Ld, 0x35)      .coordInfo(0x044c, 0x1000),
        create_owedge(player, 'Stumpy SC',                   0x6a, So, Ld, 0x36)      .coordInfo(0x04e8, 0x100c),
        create_owedge(player, 'Stumpy WS',                   0x6a, We, Ld, 0x3a)      .coordInfo(0x0b80, 0x0960),
        create_owedge(player, 'Dark Bonk Rocks NW',          0x6b, No, Ld, 0x32)      .coordInfo(0x068c, 0x1802),
        create_owedge(player, 'Dark Bonk Rocks SW',          0x6b, So, Ld, 0x37)      .coordInfo(0x069c, 0x1004),
        create_owedge(player, 'Dark Bonk Rocks EN',          0x6b, Ea, Ld, 0x3a)      .coordInfo(0x0ac0, 0x0340),
        create_owedge(player, 'Dark Bonk Rocks EC',          0x6b, Ea, Ld, 0x3b)      .coordInfo(0x0b18, 0x05c0),
        create_owedge(player, 'Dark Bonk Rocks ES',          0x6b, Ea, Ld, 0x3c)      .coordInfo(0x0b8c, 0x08c0),
        create_owedge(player, 'Big Bomb Shop NE',            0x6c, No, Ld, 0x33)      .coordInfo(0x0924, 0x1814),
        create_owedge(player, 'Big Bomb Shop SC',            0x6c, So, Ld, 0x38)      .coordInfo(0x08e0, 0x100e),
        create_owedge(player, 'Big Bomb Shop WN',            0x6c, We, Ld, 0x3b)      .coordInfo(0x0ac0, 0x0360),
        create_owedge(player, 'Big Bomb Shop WC',            0x6c, We, Ld, 0x3c)      .coordInfo(0x0b18, 0x05e0),
        create_owedge(player, 'Big Bomb Shop WS',            0x6c, We, Ld, 0x3d)      .coordInfo(0x0b8c, 0x08a0),
        create_owedge(player, 'Big Bomb Shop ES',            0x6c, Ea, Ld, 0x3d)      .coordInfo(0x0b80, 0x08c0),
        create_owedge(player, 'Hammer Bridge NC',            0x6d, No, Ld, 0x34)      .coordInfo(0x0af0, 0x180e),
        create_owedge(player, 'Hammer Bridge SC',            0x6d, So, Ld, 0x39)      .coordInfo(0x0ae0, 0x100c),
        create_owedge(player, 'Hammer Bridge WS',            0x6d, We, Ld, 0x3e)      .coordInfo(0x0b80, 0x08e0),
        create_owedge(player, 'Hammer Bridge EN',            0x6d, Ea, Ld, 0x3e)      .coordInfo(0x0a90, 0x01c0),
        create_owedge(player, 'Hammer Bridge EC',            0x6d, Ea, Wr, 0x3f)      .coordInfo(0x0b3c, 0x0640),
        create_owedge(player, 'Dark Tree Line NW',           0x6e, No, Ld, 0x35)      .coordInfo(0x0c80, 0x1802),
        create_owedge(player, 'Dark Tree Line SC',           0x6e, So, Wr, 0x3a)      .coordInfo(0x0d48, 0x101a),
        create_owedge(player, 'Dark Tree Line SE',           0x6e, So, Ld, 0x3b)      .coordInfo(0x0d98, 0x1020),
        create_owedge(player, 'Dark Tree Line WN',           0x6e, We, Ld, 0x3f)      .coordInfo(0x0a90, 0x01e0),
        create_owedge(player, 'Dark Tree Line WC',           0x6e, We, Wr, 0x40)      .coordInfo(0x0b3c, 0x0660),
        create_owedge(player, 'Palace of Darkness Nook NE',  0x6f, No, Ld, 0x36)      .coordInfo(0x0f78, 0x1820),
        create_owedge(player, 'Stumpy Approach NW',          0x72, No, Ld, 0x37)      .coordInfo(0x044c, 0x1800),
        create_owedge(player, 'Stumpy Approach NC',          0x72, No, Ld, 0x38)      .coordInfo(0x04e8, 0x180c),
        create_owedge(player, 'Stumpy Approach EC',          0x72, Ea, Ld, 0x40)      .coordInfo(0x0d04, 0x05c0),
        create_owedge(player, 'Dark C Whirlpool NW',         0x73, No, Ld, 0x39)      .coordInfo(0x069c, 0x1804),
        create_owedge(player, 'Dark C Whirlpool SC',         0x73, So, Ld, 0x3c)      .coordInfo(0x0728, 0x1016),
        create_owedge(player, 'Dark C Whirlpool WC',         0x73, We, Ld, 0x41)      .coordInfo(0x0d04, 0x05e0),
        create_owedge(player, 'Dark C Whirlpool EN',         0x73, Ea, Ld, 0x41)      .coordInfo(0x0cad, 0x02c0),
        create_owedge(player, 'Dark C Whirlpool EC',         0x73, Ea, Wr, 0x42)      .coordInfo(0x0d0b, 0x05c0),
        create_owedge(player, 'Dark C Whirlpool ES',         0x73, Ea, Ld, 0x43)      .coordInfo(0x0d76, 0x08c0),
        create_owedge(player, 'Hype Cave NC',                0x74, No, Ld, 0x3a)      .coordInfo(0x08e0, 0x180e),
        create_owedge(player, 'Hype Cave SC',                0x74, So, Ld, 0x3d)      .coordInfo(0x08f0, 0x1010),
        create_owedge(player, 'Hype Cave WN',                0x74, We, Ld, 0x42)      .coordInfo(0x0cad, 0x02e0),
        create_owedge(player, 'Hype Cave WC',                0x74, We, Wr, 0x43)      .coordInfo(0x0d0b, 0x05e0),
        create_owedge(player, 'Hype Cave WS',                0x74, We, Ld, 0x44)      .coordInfo(0x0d76, 0x08e0),
        create_owedge(player, 'Ice Lake NW',                 0x75, No, Ld, 0x3b)      .coordInfo(0x0ae0, 0x180c),
        create_owedge(player, 'Ice Lake NC',                 0x75, No, Wr, 0x3c, 0x76).coordInfo(0x0d48, 0x185a),
        create_owedge(player, 'Ice Lake NE',                 0x75, No, Ld, 0x3d, 0x76).coordInfo(0x0d98, 0x1860),
        create_owedge(player, 'Ice Lake WS',                 0x75, We, Ld, 0x48, 0x7d).coordInfo(0x0f98, 0x1860),
        create_owedge(player, 'Ice Lake EC',                 0x75, Ea, Wr, 0x48, 0x7e).coordInfo(0x0f30, 0x1680),
        create_owedge(player, 'Ice Lake ES',                 0x75, Ea, Ld, 0x49, 0x7e).coordInfo(0x0f94, 0x1880),
        create_owedge(player, 'Shopping Mall SW',            0x77, So, Wr, 0x3e)      .coordInfo(0x0e80, 0x1002),
        create_owedge(player, 'Shopping Mall SE',            0x77, So, Ld, 0x3f)      .coordInfo(0x0f50, 0x101c),
        create_owedge(player, 'Swamp Nook EC',               0x7a, Ea, Ld, 0x44)      .coordInfo(0x0f18, 0x0640),
        create_owedge(player, 'Swamp Nook ES',               0x7a, Ea, Ld, 0x45)      .coordInfo(0x0fc8, 0x08c0),
        create_owedge(player, 'Swamp NC',                    0x7b, No, Ld, 0x3e)      .coordInfo(0x0728, 0x1816),
        create_owedge(player, 'Swamp WC',                    0x7b, We, Ld, 0x45)      .coordInfo(0x0f18, 0x0660),
        create_owedge(player, 'Swamp WS',                    0x7b, We, Ld, 0x46)      .coordInfo(0x0fc8, 0x08e0),
        create_owedge(player, 'Swamp EC',                    0x7b, Ea, Ld, 0x46)      .coordInfo(0x0ef0, 0x04c0),
        create_owedge(player, 'Dark South Pass NC',          0x7c, No, Ld, 0x3f)      .coordInfo(0x08f0, 0x1810),
        create_owedge(player, 'Dark South Pass WC',          0x7c, We, Ld, 0x47)      .coordInfo(0x0ef0, 0x04e0),
        create_owedge(player, 'Dark South Pass ES',          0x7c, Ea, Ld, 0x47)      .coordInfo(0x0f98, 0x08c0),
        create_owedge(player, 'Bomber Corner NW',            0x7f, No, Wr, 0x40)      .coordInfo(0x0e80, 0x1802),
        create_owedge(player, 'Bomber Corner NE',            0x7f, No, Ld, 0x41)      .coordInfo(0x0f50, 0x181c),
        create_owedge(player, 'Bomber Corner WC',            0x7f, We, Wr, 0x49)      .coordInfo(0x0f30, 0x05e0),
        create_owedge(player, 'Bomber Corner WS',            0x7f, We, Ld, 0x4a)      .coordInfo(0x0f94, 0x0860),
        create_owedge(player, 'Master Sword Meadow SC',      0x80, So, Ld, 0x40)      .coordInfo(0x0080, 0x0000).special_exit(0x80),
        create_owedge(player, 'Hobo EC',                     0x80, Ea, Wr, 0x4a)      .coordInfo(0x008c, 0x0020).special_exit(0x81),
        create_owedge(player, 'Zoras Domain SW',             0x81, So, Ld, 0x41, 0x89).coordInfo(0x02a4, 0x1782).special_exit(0x82)
    ]

    world.owedges += edges
    world.initialize_owedges(edges)
    set_parallel_owedge_links(world, player, edges)

def create_owedge(player, name, owIndex, direction, terrain, edge_id, owSlotIndex=0xff):
    if name not in OWExitTypes['OWEdge']:
        OWExitTypes['OWEdge'].append(name)
    return OWEdge(player, name, owIndex, direction, terrain, edge_id, owSlotIndex)

def set_parallel_owedge_links(world, player, edges):
    for edge in edges:
        if edge.name in parallel_links:
            dw_edge = world.get_owedge(parallel_links[edge.name], player)
            edge.parallel = dw_edge
            dw_edge.parallel = edge


OWEdgeGroups = {
    #(IsStandard, World, EdgeAxis, Terrain, HasParallel, NumberInGroup, CustomizerGroup)
    (St, LW, Vt, Ld, PL, 1, None): (
        [
            ['Hyrule Castle SW'],
            ['Hyrule Castle SE']
        ],
        [
            ['Central Bonk Rocks NW'],
            ['Links House NE']
        ]
    ),
    (St, LW, Hz, Ld, PL, 3, None): (
        [
            ['Central Bonk Rocks EN', 'Central Bonk Rocks EC', 'Central Bonk Rocks ES']
        ],
        [
            ['Links House WN', 'Links House WC', 'Links House WS']
        ]
    ),
    (Op, LW, Hz, Ld, PL, 1, None): (
        [
            ['Lost Woods EN'],
            ['East Death Mountain EN'],
            ['Sanctuary EC'],
            ['Graveyard EC'],
            ['Kakariko ES'],
            ['Hyrule Castle ES'],
            ['Maze Race ES'],
            ['Kakariko Suburb ES'],
            ['Links House ES'],
            ['Flute Boy Approach EC'],
            ['Dam EC'],
            ['South Pass ES'],
            ['Potion Shop EC'],
            ['Lake Hylia ES'],
            ['Stone Bridge EN'],
            ['West Death Mountain EN'],
            ['West Death Mountain ES']
        ],
        [
            ['Lumberjack WN'],
            ['Death Mountain TR Pegs WN'],
            ['Graveyard WC'],
            ['River Bend WC'],
            ['Blacksmith WS'],
            ['Sand Dunes WN'],
            ['Kakariko Suburb WS'],
            ['Flute Boy WS'],
            ['Stone Bridge WS'],
            ['C Whirlpool WC'],
            ['South Pass WC'],
            ['Lake Hylia WS'],
            ['Zora Approach WC'],
            ['Octoballoon WS'],
            ['Tree Line WN'],
            ['East Death Mountain WN'],
            ['East Death Mountain WS']
        ]
    ),
    (Op, LW, Hz, Ld, NP, 1, None): (
        [
            ['Forgotten Forest ES']
        ],
        [
            ['Hyrule Castle WN']
        ]
    ),
    (Op, LW, Vt, Ld, PL, 1, None): (
        [
            ['Lumberjack SW'],
            ['Mountain Pass SE'],
            ['Lost Woods SE'],
            ['Zora Waterfall SE'],
            ['Kakariko Fortune SC'],
            ['Wooden Bridge SW'],
            ['Kakariko SE'],
            ['Sand Dunes SC'],
            ['Eastern Palace SW'],
            ['Eastern Palace SE'],
            ['Central Bonk Rocks SW'],
            ['Links House SC'],
            ['Stone Bridge SC'],
            ['C Whirlpool SC'],
            ['Statues SC'],
            ['Tree Line SE'],
            ['Ice Cave SE']
        ],
        [
            ['Mountain Pass NW'],
            ['Kakariko Pond NE'],
            ['Kakariko Fortune NE'],
            ['Zora Approach NE'],
            ['Kakariko NE'],
            ['Sand Dunes NW'],
            ['Kakariko Suburb NE'],
            ['Stone Bridge NC'],
            ['Tree Line NW'],
            ['Eastern Nook NE'],
            ['C Whirlpool NW'],
            ['Statues NC'],
            ['Lake Hylia NW'],
            ['Dam NC'],
            ['South Pass NC'],
            ['Lake Hylia NE'],
            ['Octoballoon NE']
        ]
    ),
    (Op, LW, Vt, Ld, NP, 1, None): (
        [
            ['Master Sword Meadow SC'],
            ['Zoras Domain SW']
        ],
        [
            ['Lost Woods NW'],
            ['Zora Waterfall NE']
        ]
    ),
    (Op, LW, Hz, Ld, PL, 2, None): (
        [
            ['Kakariko Fortune EN', 'Kakariko Fortune ES'],
            ['Kakariko Pond EN', 'Kakariko Pond ES'],
            ['Desert Pass EC', 'Desert Pass ES'],
            ['River Bend EC', 'River Bend ES'],
            ['C Whirlpool EN', 'C Whirlpool ES']
        ],
        [
            ['Kakariko Pond WN', 'Kakariko Pond WS'],
            ['Sanctuary WN', 'Sanctuary WS'],
            ['Dam WC', 'Dam WS'],
            ['Potion Shop WC', 'Potion Shop WS'],
            ['Statues WN', 'Statues WS']
        ]
    ),
    (Op, LW, Hz, Ld, NP, 2, None): (
        [
            ['Desert EC', 'Desert ES']
        ],
        [
            ['Desert Pass WC', 'Desert Pass WS']
        ]
    ),
    (Op, LW, Vt, Ld, PL, 2, None): (
        [
            ['Lost Woods SW', 'Lost Woods SC'],
            ['Lost Woods Pass SW', 'Lost Woods Pass SE'],
            ['Kakariko Pond SW', 'Kakariko Pond SE'],
            ['Flute Boy SW', 'Flute Boy SC'],
            ['River Bend SW', 'River Bend SE']
        ],
        [
            ['Lost Woods Pass NW', 'Lost Woods Pass NE'],
            ['Kakariko NW', 'Kakariko NC'],
            ['Forgotten Forest NW', 'Forgotten Forest NE'],
            ['Flute Boy Approach NW', 'Flute Boy Approach NC'],
            ['Wooden Bridge NW', 'Wooden Bridge NE']
        ]
    ),
    (Op, LW, Hz, Wr, PL, 1, None): (
        [
            ['Potion Shop EN'],
            ['Lake Hylia EC'],
            ['Stone Bridge EC'],
            ['River Bend EN'],
            ['C Whirlpool EC']
        ],
        [
            ['Zora Approach WN'],
            ['Octoballoon WC'],
            ['Tree Line WC'],
            ['Potion Shop WN'],
            ['Statues WC']
        ]
    ),
    (Op, LW, Hz, Wr, NP, 1, None): (
        [
            ['Hobo EC']
        ],
        [
            ['Stone Bridge WC']
        ]
    ),
    (Op, LW, Vt, Wr, PL, 1, None): (
        [
            ['Tree Line SC'],
            ['Ice Cave SW'],
            ['River Bend SC']
        ],
        [
            ['Lake Hylia NC'],
            ['Octoballoon NW'],
            ['Wooden Bridge NC']
        ]
    ),
    (Op, DW, Hz, Ld, PL, 1, None): (
        [
            ['Skull Woods EN'],
            ['East Dark Death Mountain EN'],
            ['Dark Chapel EC'],
            ['Dark Graveyard EC'],
            ['Village of Outcasts ES'],
            ['Pyramid ES'],
            ['Frog ES'],
            ['Big Bomb Shop ES'],
            ['Stumpy Approach EC'],
            ['Swamp EC'],
            ['Dark South Pass ES'],
            ['Dark Witch EC'],
            ['Ice Lake ES'],
            ['Hammer Bridge EN'],
            ['West Dark Death Mountain EN'],
            ['West Dark Death Mountain ES']
        ],
        [
            ['Dark Lumberjack WN'],
            ['Turtle Rock WN'],
            ['Dark Graveyard WC'],
            ['Qirn Jump WC'],
            ['Hammer Pegs WS'],
            ['Dark Dunes WN'],
            ['Stumpy WS'],
            ['Hammer Bridge WS'],
            ['Dark C Whirlpool WC'],
            ['Dark South Pass WC'],
            ['Ice Lake WS'],
            ['Catfish Approach WC'],
            ['Bomber Corner WS'],
            ['Dark Tree Line WN'],
            ['East Dark Death Mountain WN'],
            ['East Dark Death Mountain WS']
        ]
    ),
    (Op, DW, Vt, Ld, PL, 1, None): (
        [
            ['Dark Lumberjack SW'],
            ['Bumper Cave SE'],
            ['Skull Woods SE'],
            ['Catfish SE'],
            ['Dark Fortune SC'],
            ['Broken Bridge SW'],
            ['Village of Outcasts SE'],
            ['Pyramid SW'],
            ['Pyramid SE'],
            ['Dark Dunes SC'],
            ['Palace of Darkness SW'],
            ['Palace of Darkness SE'],
            ['Dark Bonk Rocks SW'],
            ['Big Bomb Shop SC'],
            ['Hammer Bridge SC'],
            ['Dark C Whirlpool SC'],
            ['Hype Cave SC'],
            ['Dark Tree Line SE'],
            ['Shopping Mall SE']
        ],
        [
            ['Bumper Cave NW'],
            ['Outcast Pond NE'],
            ['Dark Fortune NE'],
            ['Catfish Approach NE'],
            ['Village of Outcasts NE'],
            ['Dark Dunes NW'],
            ['Frog NE'],
            ['Dark Bonk Rocks NW'],
            ['Big Bomb Shop NE'],
            ['Hammer Bridge NC'],
            ['Dark Tree Line NW'],
            ['Palace of Darkness Nook NE'],
            ['Dark C Whirlpool NW'],
            ['Hype Cave NC'],
            ['Ice Lake NW'],
            ['Swamp NC'],
            ['Dark South Pass NC'],
            ['Ice Lake NE'],
            ['Bomber Corner NE']
        ]
    ),
    (Op, DW, Hz, Ld, NP, 1, None): (
        [ ],
        [ ]
    ),
    (Op, DW, Hz, Ld, PL, 2, None): (
        [
            ['Dark Fortune EN', 'Dark Fortune ES'],
            ['Outcast Pond EN', 'Outcast Pond ES'],
            ['Swamp Nook EC', 'Swamp Nook ES'],
            ['Qirn Jump EC', 'Qirn Jump ES'],
            ['Dark C Whirlpool EN', 'Dark C Whirlpool ES']
        ],
        [
            ['Outcast Pond WN', 'Outcast Pond WS'],
            ['Dark Chapel WN', 'Dark Chapel WS'],
            ['Swamp WC', 'Swamp WS'],
            ['Dark Witch WC', 'Dark Witch WS'],
            ['Hype Cave WN', 'Hype Cave WS']
        ]
    ),
    (Op, DW, Vt, Ld, NP, 1, None): (
        [ ],
        [ ]
    ),
    (Op, DW, Hz, Ld, NP, 2, None): (
        [
            ['Dig Game EC', 'Dig Game ES']
        ],
        [
            ['Frog WC', 'Frog WS']
        ]
    ),
    (Op, DW, Vt, Ld, PL, 2, None): (
        [
            ['Skull Woods SW', 'Skull Woods SC'],
            ['Skull Woods Pass SW', 'Skull Woods Pass SE'],
            ['Outcast Pond SW', 'Outcast Pond SE'],
            ['Stumpy SW', 'Stumpy SC'],
            ['Qirn Jump SW', 'Qirn Jump SE']
        ],
        [
            ['Skull Woods Pass NW', 'Skull Woods Pass NE'],
            ['Village of Outcasts NW', 'Village of Outcasts NC'],
            ['Shield Shop NW', 'Shield Shop NE'],
            ['Stumpy Approach NW', 'Stumpy Approach NC'],
            ['Broken Bridge NW', 'Broken Bridge NE']
        ]
    ),
    (Op, DW, Hz, Ld, PL, 3, None): (
        [
            ['Dark Bonk Rocks EN', 'Dark Bonk Rocks EC', 'Dark Bonk Rocks ES']
        ],
        [
            ['Big Bomb Shop WN', 'Big Bomb Shop WC', 'Big Bomb Shop WS']
        ]
    ),
    (Op, DW, Hz, Wr, PL, 1, None): (
        [
            ['Dark Witch EN'],
            ['Ice Lake EC'],
            ['Hammer Bridge EC'],
            ['Qirn Jump EN'],
            ['Dark C Whirlpool EC']
        ],
        [
            ['Catfish Approach WN'],
            ['Bomber Corner WC'],
            ['Dark Tree Line WC'],
            ['Dark Witch WN'],
            ['Hype Cave WC']
        ]
    ),
    (Op, DW, Hz, Wr, NP, 1, None): (
        [ ],
        [ ]
    ),
    (Op, DW, Vt, Wr, PL, 1, None): (
        [
            ['Dark Tree Line SC'],
            ['Shopping Mall SW'],
            ['Qirn Jump SC']
        ],
        [
            ['Ice Lake NC'],
            ['Bomber Corner NW'],
            ['Broken Bridge NC']
        ]
    )
}

OWEdgeGroupsTerrain = {
    #(IsStandard, World, EdgeAxis, Terrain, HasParallel, NumberInGroup)
    (St, LW, Vt, None, PL, 1, None): (
        [
            ['Hyrule Castle SW'],
            ['Hyrule Castle SE']
        ],
        [
            ['Central Bonk Rocks NW'],
            ['Links House NE']
        ]
    ),
    (St, LW, Hz, None, PL, 3, None): (
        [
            ['Central Bonk Rocks EN', 'Central Bonk Rocks EC', 'Central Bonk Rocks ES']
        ],
        [
            ['Links House WN', 'Links House WC', 'Links House WS']
        ]
    ),
    (Op, LW, Hz, None, PL, 1, None): (
        [
            ['Lost Woods EN'],
            ['East Death Mountain EN'],
            ['Sanctuary EC'],
            ['Graveyard EC'],
            ['Kakariko ES'],
            ['Hyrule Castle ES'],
            ['Maze Race ES'],
            ['Kakariko Suburb ES'],
            ['Links House ES'],
            ['Flute Boy Approach EC'],
            ['Dam EC'],
            ['South Pass ES'],
            ['West Death Mountain EN'],
            ['West Death Mountain ES']
        ],
        [
            ['Lumberjack WN'],
            ['Death Mountain TR Pegs WN'],
            ['Graveyard WC'],
            ['River Bend WC'],
            ['Blacksmith WS'],
            ['Sand Dunes WN'],
            ['Kakariko Suburb WS'],
            ['Flute Boy WS'],
            ['Stone Bridge WS'],
            ['C Whirlpool WC'],
            ['South Pass WC'],
            ['Lake Hylia WS'],
            ['East Death Mountain WN'],
            ['East Death Mountain WS']
        ]
    ),
    (Op, LW, Hz, None, NP, 1, None): (
        [
            ['Forgotten Forest ES'],
            ['Hobo EC']
        ],
        [
            ['Hyrule Castle WN'],
            ['Stone Bridge WC']
        ]
    ),
    (Op, LW, Vt, None, PL, 1, None): (
        [
            ['Lumberjack SW'],
            ['Mountain Pass SE'],
            ['Lost Woods SE'],
            ['Zora Waterfall SE'],
            ['Kakariko Fortune SC'],
            ['Wooden Bridge SW'],
            ['Kakariko SE'],
            ['Sand Dunes SC'],
            ['Eastern Palace SW'],
            ['Eastern Palace SE'],
            ['Central Bonk Rocks SW'],
            ['Links House SC'],
            ['Stone Bridge SC'],
            ['C Whirlpool SC'],
            ['Statues SC']
        ],
        [
            ['Mountain Pass NW'],
            ['Kakariko Pond NE'],
            ['Kakariko Fortune NE'],
            ['Zora Approach NE'],
            ['Kakariko NE'],
            ['Sand Dunes NW'],
            ['Kakariko Suburb NE'],
            ['Stone Bridge NC'],
            ['Tree Line NW'],
            ['Eastern Nook NE'],
            ['C Whirlpool NW'],
            ['Statues NC'],
            ['Lake Hylia NW'],
            ['Dam NC'],
            ['South Pass NC']
        ]
    ),
    (Op, LW, Vt, None, NP, 1, None): (
        [
            ['Master Sword Meadow SC'],
            ['Zoras Domain SW']
        ],
        [
            ['Lost Woods NW'],
            ['Zora Waterfall NE']
        ]
    ),
    (Op, LW, Hz, None, PL, 2, None): (
        [
            ['Kakariko Fortune EN', 'Kakariko Fortune ES'],
            ['Kakariko Pond EN', 'Kakariko Pond ES'],
            ['Desert Pass EC', 'Desert Pass ES'],
            ['Potion Shop EN', 'Potion Shop EC'],
            ['Lake Hylia EC', 'Lake Hylia ES'],
            ['Stone Bridge EN', 'Stone Bridge EC']
        ],
        [
            ['Kakariko Pond WN', 'Kakariko Pond WS'],
            ['Sanctuary WN', 'Sanctuary WS'],
            ['Dam WC', 'Dam WS'],
            ['Zora Approach WN', 'Zora Approach WC'],
            ['Octoballoon WC', 'Octoballoon WS'],
            ['Tree Line WN', 'Tree Line WC']
        ]
    ),
    (Op, LW, Hz, None, NP, 2, None): (
        [
            ['Desert EC', 'Desert ES']
        ],
        [
            ['Desert Pass WC', 'Desert Pass WS']
        ]
    ),
    (Op, LW, Vt, None, PL, 2, None): (
        [
            ['Lost Woods SW', 'Lost Woods SC'],
            ['Lost Woods Pass SW', 'Lost Woods Pass SE'],
            ['Kakariko Pond SW', 'Kakariko Pond SE'],
            ['Flute Boy SW', 'Flute Boy SC'],
            ['Tree Line SC', 'Tree Line SE'],
            ['Ice Cave SW', 'Ice Cave SE']
        ],
        [
            ['Lost Woods Pass NW', 'Lost Woods Pass NE'],
            ['Kakariko NW', 'Kakariko NC'],
            ['Forgotten Forest NW', 'Forgotten Forest NE'],
            ['Flute Boy Approach NW', 'Flute Boy Approach NC'],
            ['Lake Hylia NC', 'Lake Hylia NE'],
            ['Octoballoon NW', 'Octoballoon NE']
        ]
    ),
    (Op, LW, Hz, None, PL, 3, None): (
        [
            ['River Bend EN', 'River Bend EC', 'River Bend ES'],
            ['C Whirlpool EN', 'C Whirlpool EC', 'C Whirlpool ES']
        ],
        [
            ['Potion Shop WN', 'Potion Shop WC', 'Potion Shop WS'],
            ['Statues WN', 'Statues WC', 'Statues WS']
        ]
    ),
    (Op, LW, Vt, None, PL, 3, None): (
        [
            ['River Bend SW', 'River Bend SC', 'River Bend SE']
        ],
        [
            ['Wooden Bridge NW', 'Wooden Bridge NC', 'Wooden Bridge NE']
        ]
    ),
    (Op, DW, Hz, None, PL, 1, None): (
        [
            ['Skull Woods EN'],
            ['East Dark Death Mountain EN'],
            ['Dark Chapel EC'],
            ['Dark Graveyard EC'],
            ['Village of Outcasts ES'],
            ['Pyramid ES'],
            ['Frog ES'],
            ['Big Bomb Shop ES'],
            ['Stumpy Approach EC'],
            ['Swamp EC'],
            ['Dark South Pass ES'],
            ['West Dark Death Mountain EN'],
            ['West Dark Death Mountain ES']
        ],
        [
            ['Dark Lumberjack WN'],
            ['Turtle Rock WN'],
            ['Dark Graveyard WC'],
            ['Qirn Jump WC'],
            ['Hammer Pegs WS'],
            ['Dark Dunes WN'],
            ['Stumpy WS'],
            ['Hammer Bridge WS'],
            ['Dark C Whirlpool WC'],
            ['Dark South Pass WC'],
            ['Ice Lake WS'],
            ['East Dark Death Mountain WN'],
            ['East Dark Death Mountain WS']
        ]
    ),
    (Op, DW, Vt, None, PL, 1, None): (
        [
            ['Dark Lumberjack SW'],
            ['Bumper Cave SE'],
            ['Skull Woods SE'],
            ['Catfish SE'],
            ['Dark Fortune SC'],
            ['Broken Bridge SW'],
            ['Village of Outcasts SE'],
            ['Pyramid SW'],
            ['Pyramid SE'],
            ['Dark Dunes SC'],
            ['Palace of Darkness SW'],
            ['Palace of Darkness SE'],
            ['Dark Bonk Rocks SW'],
            ['Big Bomb Shop SC'],
            ['Hammer Bridge SC'],
            ['Dark C Whirlpool SC'],
            ['Hype Cave SC']
        ],
        [
            ['Bumper Cave NW'],
            ['Outcast Pond NE'],
            ['Dark Fortune NE'],
            ['Catfish Approach NE'],
            ['Village of Outcasts NE'],
            ['Dark Dunes NW'],
            ['Frog NE'],
            ['Dark Bonk Rocks NW'],
            ['Big Bomb Shop NE'],
            ['Hammer Bridge NC'],
            ['Dark Tree Line NW'],
            ['Palace of Darkness Nook NE'],
            ['Dark C Whirlpool NW'],
            ['Hype Cave NC'],
            ['Ice Lake NW'],
            ['Swamp NC'],
            ['Dark South Pass NC']
        ]
    ),
    (Op, DW, Hz, None, NP, 1, None): (
        [ ],
        [ ]
    ),
    (Op, DW, Hz, None, PL, 2, None): (
        [
            ['Dark Fortune EN', 'Dark Fortune ES'],
            ['Outcast Pond EN', 'Outcast Pond ES'],
            ['Swamp Nook EC', 'Swamp Nook ES'],
            ['Dark Witch EN', 'Dark Witch EC'],
            ['Ice Lake EC', 'Ice Lake ES'],
            ['Hammer Bridge EN', 'Hammer Bridge EC']
        ],
        [
            ['Outcast Pond WN', 'Outcast Pond WS'],
            ['Dark Chapel WN', 'Dark Chapel WS'],
            ['Swamp WC', 'Swamp WS'],
            ['Catfish Approach WN', 'Catfish Approach WC'],
            ['Bomber Corner WC', 'Bomber Corner WS'],
            ['Dark Tree Line WN', 'Dark Tree Line WC']
        ]
    ),
    (Op, DW, Vt, None, NP, 1, None): (
        [ ],
        [ ]
    ),
    (Op, DW, Hz, None, NP, 2, None): (
        [
            ['Dig Game EC', 'Dig Game ES']
        ],
        [
            ['Frog WC', 'Frog WS']
        ]
    ),
    (Op, DW, Vt, None, PL, 2, None): (
        [
            ['Skull Woods SW', 'Skull Woods SC'],
            ['Skull Woods Pass SW', 'Skull Woods Pass SE'],
            ['Outcast Pond SW', 'Outcast Pond SE'],
            ['Stumpy SW', 'Stumpy SC'],
            ['Dark Tree Line SC', 'Dark Tree Line SE'],
            ['Shopping Mall SW', 'Shopping Mall SE']
        ],
        [
            ['Skull Woods Pass NW', 'Skull Woods Pass NE'],
            ['Village of Outcasts NW', 'Village of Outcasts NC'],
            ['Shield Shop NW', 'Shield Shop NE'],
            ['Stumpy Approach NW', 'Stumpy Approach NC'],
            ['Ice Lake NC', 'Ice Lake NE'],
            ['Bomber Corner NW', 'Bomber Corner NE']
        ]
    ),
    (Op, DW, Hz, None, PL, 3, None): (
        [
            ['Dark Bonk Rocks EN', 'Dark Bonk Rocks EC', 'Dark Bonk Rocks ES'],
            ['Qirn Jump EN', 'Qirn Jump EC', 'Qirn Jump ES'],
            ['Dark C Whirlpool EN', 'Dark C Whirlpool EC', 'Dark C Whirlpool ES']
        ],
        [
            ['Big Bomb Shop WN', 'Big Bomb Shop WC', 'Big Bomb Shop WS'],
            ['Dark Witch WN', 'Dark Witch WC', 'Dark Witch WS'],
            ['Hype Cave WN', 'Hype Cave WC', 'Hype Cave WS']
        ]
    ),
    (Op, DW, Vt, None, PL, 3, None): (
        [
            ['Qirn Jump SW', 'Qirn Jump SC', 'Qirn Jump SE']
        ],
        [
            ['Broken Bridge NW', 'Broken Bridge NC', 'Broken Bridge NE']
        ]
    )
}

OWTileRegions = bidict({
    'Lost Woods West Area': 0x00,
    'Lost Woods East Area': 0x00,

    'Lumberjack Area': 0x02,

    'West Death Mountain (Top)': 0x03,
    'Spectacle Rock Ledge': 0x03,
    'West Death Mountain (Bottom)': 0x03,
    'Old Man Drop Off': 0x03,

    'East Death Mountain (Top West)': 0x05,
    'East Death Mountain (Top East)': 0x05,
    'Spiral Cave Ledge': 0x05,
    'Mimic Cave Ledge': 0x05,
    'Spiral Mimic Ledge Extend': 0x05,
    'Fairy Ascension Ledge': 0x05,
    'Fairy Ascension Plateau': 0x05,
    'East Death Mountain (Bottom Left)': 0x05,
    'East Death Mountain (Bottom)': 0x05,
    'Death Mountain Floating Island': 0x05,

    'Death Mountain TR Pegs Area': 0x07,
    'Death Mountain TR Pegs Ledge': 0x07,

    'Mountain Pass Area': 0x0a,
    'Mountain Pass Entry': 0x0a,
    'Mountain Pass Ledge': 0x0a,

    'Zora Waterfall Area': 0x0f,
    'Zora Waterfall Water': 0x0f,
    'Zora Waterfall Entryway': 0x0f,

    'Lost Woods Pass West Area': 0x10,
    'Lost Woods Pass East Top Area': 0x10,
    'Lost Woods Pass Portal Area': 0x10,
    'Lost Woods Pass East Bottom Area': 0x10,

    'Kakariko Fortune Area': 0x11,

    'Kakariko Pond Area': 0x12,

    'Sanctuary Area': 0x13,
    'Bonk Rock Ledge': 0x13,

    'Graveyard Area': 0x14,
    'Graveyard Ledge': 0x14,
    'Kings Grave Area': 0x14,

    'River Bend Area': 0x15,
    'River Bend East Bank': 0x15,
    'River Bend Water': 0x15,

    'Potion Shop Area': 0x16,
    'Potion Shop Northeast': 0x16,
    'Potion Shop Water': 0x16,

    'Zora Approach Area': 0x17,
    'Zora Approach Ledge': 0x17,
    'Zora Approach Water': 0x17,

    'Kakariko Village': 0x18,
    'Kakariko Southwest': 0x18,
    'Kakariko Bush Yard': 0x18,

    'Forgotten Forest Area': 0x1a,

    'Hyrule Castle Area': 0x1b,
    'Hyrule Castle Southwest': 0x1b,
    'Hyrule Castle Courtyard': 0x1b,
    'Hyrule Castle Courtyard Northeast': 0x1b,
    'Hyrule Castle Ledge': 0x1b,
    'Hyrule Castle East Entry': 0x1b,
    'Hyrule Castle Water': 0x1b,

    'Wooden Bridge Area': 0x1d,
    'Wooden Bridge Northeast': 0x1d,
    'Wooden Bridge Water': 0x1d,

    'Eastern Palace Area': 0x1e,

    'Blacksmith Area': 0x22,
    'Blacksmith Ledge': 0x22,

    'Sand Dunes Area': 0x25,

    'Maze Race Area': 0x28,
    'Maze Race Ledge': 0x28,
    'Maze Race Prize': 0x28,

    'Kakariko Suburb Area': 0x29,

    'Flute Boy Area': 0x2a,
    'Flute Boy Pass': 0x2a,

    'Central Bonk Rocks Area': 0x2b,

    'Links House Area': 0x2c,

    'Stone Bridge North Area': 0x2d,
    'Stone Bridge South Area': 0x2d,
    'Stone Bridge Water': 0x2d,

    'Tree Line Area': 0x2e,
    'Tree Line Water': 0x2e,

    'Eastern Nook Area': 0x2f,

    'Desert Area': 0x30,
    'Desert Ledge': 0x30,
    'Desert Ledge Keep': 0x30,
    'Desert Checkerboard Ledge': 0x30,
    'Desert Stairs': 0x30,
    'Desert Mouth': 0x30,
    'Desert Teleporter Ledge': 0x30,
    'Bombos Tablet Ledge': 0x30,

    'Flute Boy Approach Area': 0x32,
    'Flute Boy Bush Entry': 0x32,
    'Cave 45 Ledge': 0x32,

    'C Whirlpool Area': 0x33,
    'C Whirlpool Portal Area': 0x33,
    'C Whirlpool Water': 0x33,
    'C Whirlpool Outer Area': 0x33,

    'Statues Area': 0x34,
    'Statues Water': 0x34,

    'Lake Hylia Northwest Bank': 0x35,
    'Lake Hylia Northeast Bank': 0x35,
    'Lake Hylia South Shore': 0x35,
    'Lake Hylia Central Island': 0x35,
    'Lake Hylia Island': 0x35,
    'Lake Hylia Water': 0x35,
    'Lake Hylia Water D': 0x35,

    'Ice Cave Area': 0x37,
    'Ice Cave Water': 0x37,

    'Desert Pass Area': 0x3a,
    'Middle Aged Man': 0x3a,
    'Desert Pass Southeast': 0x3a,
    'Desert Pass Ledge': 0x3a,

    'Dam Area': 0x3b,

    'South Pass Area': 0x3c,

    'Octoballoon Area': 0x3f,
    'Octoballoon Water': 0x3f,
    'Octoballoon Water Ledge': 0x3f,

    'Skull Woods Forest': 0x40,
    'Skull Woods Portal Entry': 0x40,
    'Skull Woods Forest (West)': 0x40,
    'Skull Woods Forgotten Path (Southwest)': 0x40,
    'Skull Woods Forgotten Path (Northeast)': 0x40,

    'Dark Lumberjack Area': 0x42,

    'West Dark Death Mountain (Top)': 0x43,
    'GT Stairs': 0x43,
    'West Dark Death Mountain (Bottom)': 0x43,

    'East Dark Death Mountain (Top)': 0x45,
    'East Dark Death Mountain (Bottom Left)': 0x45,
    'East Dark Death Mountain (Bottom)': 0x45,
    'East Dark Death Mountain (Bushes)': 0x45,
    'Dark Death Mountain Ledge': 0x45,
    'Dark Death Mountain Isolated Ledge': 0x45,
    'Dark Death Mountain Floating Island': 0x45,

    'Turtle Rock Area': 0x47,
    'Turtle Rock Ledge': 0x47,

    'Bumper Cave Area': 0x4a,
    'Bumper Cave Entry': 0x4a,
    'Bumper Cave Ledge': 0x4a,

    'Catfish Area': 0x4f,

    'Skull Woods Pass West Area': 0x50,
    'Skull Woods Pass East Top Area': 0x50,
    'Skull Woods Pass Portal Area': 0x50,
    'Skull Woods Pass East Bottom Area': 0x50,

    'Dark Fortune Area': 0x51,

    'Outcast Pond Area': 0x52,

    'Dark Chapel Area': 0x53,

    'Dark Graveyard Area': 0x54,
    'Dark Graveyard North': 0x54,

    'Qirn Jump Area': 0x55,
    'Qirn Jump East Bank': 0x55,
    'Qirn Jump Water': 0x55,

    'Dark Witch Area': 0x56,
    'Dark Witch Northeast': 0x56,
    'Dark Witch Water': 0x56,

    'Catfish Approach Area': 0x57,
    'Catfish Approach Ledge': 0x57,
    'Catfish Approach Water': 0x57,

    'Village of Outcasts': 0x58,
    'Village of Outcasts Bush Yard': 0x58,

    'Shield Shop Area': 0x5a,
    'Shield Shop Fence': 0x5a,

    'Pyramid Area': 0x5b,
    'Pyramid Crack': 0x5b,
    'Pyramid Exit Ledge': 0x5b,
    'Pyramid Pass': 0x5b,
    'Pyramid Water': 0x5b,

    'Broken Bridge Area': 0x5d,
    'Broken Bridge Northeast': 0x5d,
    'Broken Bridge West': 0x5d,
    'Broken Bridge Water': 0x5d,

    'Palace of Darkness Area': 0x5e,
    'Dark Palace Button': 0x5e,

    'Hammer Pegs Area': 0x62,
    'Hammer Pegs Entry': 0x62,

    'Dark Dunes Area': 0x65,

    'Dig Game Area': 0x68,
    'Dig Game Ledge': 0x68,

    'Frog Area': 0x69,
    'Frog Prison': 0x69,
    'Archery Game Area': 0x69,

    'Stumpy Area': 0x6a,
    'Stumpy Pass': 0x6a,

    'Dark Bonk Rocks Area': 0x6b,

    'Big Bomb Shop Area': 0x6c,

    'Hammer Bridge North Area': 0x6d,
    'Hammer Bridge South Area': 0x6d,
    'Hammer Bridge Water': 0x6d,

    'Dark Tree Line Area': 0x6e,
    'Dark Tree Line Water': 0x6e,

    'Darkness Nook Area': 0x6f,

    'Mire Area': 0x70,
    'Mire Teleporter Ledge': 0x70,

    'Stumpy Approach Area': 0x72,
    'Stumpy Approach Bush Entry': 0x72,

    'Dark C Whirlpool Area': 0x73,
    'Dark C Whirlpool Portal Area': 0x73,
    'Dark C Whirlpool Water': 0x73,
    'Dark C Whirlpool Outer Area': 0x73,

    'Hype Cave Area': 0x74,
    'Hype Cave Water': 0x74,

    'Ice Lake Northwest Bank': 0x75,
    'Ice Lake Northeast Bank': 0x75,
    'Ice Lake Southwest Ledge': 0x75,
    'Ice Lake Southeast Ledge': 0x75,
    'Ice Lake Water': 0x75,
    'Ice Lake Iceberg': 0x75,
    'Ice Palace Area': 0x75,

    'Shopping Mall Area': 0x77,
    'Shopping Mall Water': 0x77,

    'Swamp Nook Area': 0x7a,

    'Swamp Area': 0x7b,

    'Dark South Pass Area': 0x7c,

    'Bomber Corner Area': 0x7f,
    'Bomber Corner Water': 0x7f,
    'Bomber Corner Water Ledge': 0x7f,

    'Master Sword Meadow': 0x80,
    'Hobo Bridge': 0x80,

    'Zoras Domain': 0x81
})

parallel_links = bidict({'Lost Woods SW': 'Skull Woods SW',
                        'Lost Woods SC': 'Skull Woods SC',
                        'Lost Woods SE': 'Skull Woods SE',
                        'Lost Woods EN': 'Skull Woods EN',
                        'Lumberjack SW': 'Dark Lumberjack SW',
                        'Lumberjack WN': 'Dark Lumberjack WN',
                        'West Death Mountain EN': 'West Dark Death Mountain EN',
                        'West Death Mountain ES': 'West Dark Death Mountain ES',
                        'East Death Mountain WN': 'East Dark Death Mountain WN',
                        'East Death Mountain WS': 'East Dark Death Mountain WS',
                        'East Death Mountain EN': 'East Dark Death Mountain EN',
                        'Death Mountain TR Pegs WN': 'Turtle Rock WN',
                        'Mountain Pass NW': 'Bumper Cave NW',
                        'Mountain Pass SE': 'Bumper Cave SE',
                        'Zora Waterfall SE': 'Catfish SE',
                        'Lost Woods Pass NW': 'Skull Woods Pass NW',
                        'Lost Woods Pass NE': 'Skull Woods Pass NE',
                        'Lost Woods Pass SW': 'Skull Woods Pass SW',
                        'Lost Woods Pass SE': 'Skull Woods Pass SE',
                        'Kakariko Fortune NE': 'Dark Fortune NE',
                        'Kakariko Fortune SC': 'Dark Fortune SC',
                        'Kakariko Fortune EN': 'Dark Fortune EN',
                        'Kakariko Fortune ES': 'Dark Fortune ES',
                        'Kakariko Pond NE': 'Outcast Pond NE',
                        'Kakariko Pond SW': 'Outcast Pond SW',
                        'Kakariko Pond SE': 'Outcast Pond SE',
                        'Kakariko Pond WN': 'Outcast Pond WN',
                        'Kakariko Pond WS': 'Outcast Pond WS',
                        'Kakariko Pond EN': 'Outcast Pond EN',
                        'Kakariko Pond ES': 'Outcast Pond ES',
                        'Sanctuary WN': 'Dark Chapel WN',
                        'Sanctuary WS': 'Dark Chapel WS',
                        'Sanctuary EC': 'Dark Chapel EC',
                        'Graveyard WC': 'Dark Graveyard WC',
                        'Graveyard EC': 'Dark Graveyard EC',
                        'River Bend SW': 'Qirn Jump SW',
                        'River Bend SC': 'Qirn Jump SC',
                        'River Bend SE': 'Qirn Jump SE',
                        'River Bend WC': 'Qirn Jump WC',
                        'River Bend EN': 'Qirn Jump EN',
                        'River Bend EC': 'Qirn Jump EC',
                        'River Bend ES': 'Qirn Jump ES',
                        'Potion Shop WN': 'Dark Witch WN',
                        'Potion Shop WC': 'Dark Witch WC',
                        'Potion Shop WS': 'Dark Witch WS',
                        'Potion Shop EN': 'Dark Witch EN',
                        'Potion Shop EC': 'Dark Witch EC',
                        'Zora Approach NE': 'Catfish Approach NE',
                        'Zora Approach WN': 'Catfish Approach WN',
                        'Zora Approach WC': 'Catfish Approach WC',
                        'Kakariko NW': 'Village of Outcasts NW',
                        'Kakariko NC': 'Village of Outcasts NC',
                        'Kakariko NE': 'Village of Outcasts NE',
                        'Kakariko SE': 'Village of Outcasts SE',
                        'Kakariko ES': 'Village of Outcasts ES',
                        'Forgotten Forest NW': 'Shield Shop NW',
                        'Forgotten Forest NE': 'Shield Shop NE',
                        'Hyrule Castle SW': 'Pyramid SW',
                        'Hyrule Castle SE': 'Pyramid SE',
                        'Hyrule Castle ES': 'Pyramid ES',
                        'Wooden Bridge NW': 'Broken Bridge NW',
                        'Wooden Bridge NC': 'Broken Bridge NC',
                        'Wooden Bridge NE': 'Broken Bridge NE',
                        'Wooden Bridge SW': 'Broken Bridge SW',
                        'Eastern Palace SW': 'Palace of Darkness SW',
                        'Eastern Palace SE': 'Palace of Darkness SE',
                        'Blacksmith WS': 'Hammer Pegs WS',
                        'Sand Dunes NW': 'Dark Dunes NW',
                        'Sand Dunes SC': 'Dark Dunes SC',
                        'Sand Dunes WN': 'Dark Dunes WN',
                        'Maze Race ES': 'Dig Game ES',
                        'Kakariko Suburb NE': 'Frog NE',
                        'Kakariko Suburb WS': 'Frog WS',
                        'Kakariko Suburb ES': 'Frog ES',
                        'Flute Boy SW': 'Stumpy SW',
                        'Flute Boy SC': 'Stumpy SC',
                        'Flute Boy WS': 'Stumpy WS',
                        'Central Bonk Rocks NW': 'Dark Bonk Rocks NW',
                        'Central Bonk Rocks SW': 'Dark Bonk Rocks SW',
                        'Central Bonk Rocks EN': 'Dark Bonk Rocks EN',
                        'Central Bonk Rocks EC': 'Dark Bonk Rocks EC',
                        'Central Bonk Rocks ES': 'Dark Bonk Rocks ES',
                        'Links House NE': 'Big Bomb Shop NE',
                        'Links House SC': 'Big Bomb Shop SC',
                        'Links House WN': 'Big Bomb Shop WN',
                        'Links House WC': 'Big Bomb Shop WC',
                        'Links House WS': 'Big Bomb Shop WS',
                        'Links House ES': 'Big Bomb Shop ES',
                        'Stone Bridge NC': 'Hammer Bridge NC',
                        'Stone Bridge SC': 'Hammer Bridge SC',
                        'Stone Bridge WS': 'Hammer Bridge WS',
                        'Stone Bridge EN': 'Hammer Bridge EN',
                        'Stone Bridge EC': 'Hammer Bridge EC',
                        'Tree Line NW': 'Dark Tree Line NW',
                        'Tree Line SC': 'Dark Tree Line SC',
                        'Tree Line SE': 'Dark Tree Line SE',
                        'Tree Line WN': 'Dark Tree Line WN',
                        'Tree Line WC': 'Dark Tree Line WC',
                        'Eastern Nook NE': 'Palace of Darkness Nook NE',
                        'Flute Boy Approach NW': 'Stumpy Approach NW',
                        'Flute Boy Approach NC': 'Stumpy Approach NC',
                        'Flute Boy Approach EC': 'Stumpy Approach EC',
                        'C Whirlpool NW': 'Dark C Whirlpool NW',
                        'C Whirlpool SC': 'Dark C Whirlpool SC',
                        'C Whirlpool WC': 'Dark C Whirlpool WC',
                        'C Whirlpool EN': 'Dark C Whirlpool EN',
                        'C Whirlpool EC': 'Dark C Whirlpool EC',
                        'C Whirlpool ES': 'Dark C Whirlpool ES',
                        'Statues NC': 'Hype Cave NC',
                        'Statues SC': 'Hype Cave SC',
                        'Statues WN': 'Hype Cave WN',
                        'Statues WC': 'Hype Cave WC',
                        'Statues WS': 'Hype Cave WS',
                        'Lake Hylia NW': 'Ice Lake NW',
                        'Lake Hylia NC': 'Ice Lake NC',
                        'Lake Hylia NE': 'Ice Lake NE',
                        'Lake Hylia WS': 'Ice Lake WS',
                        'Lake Hylia EC': 'Ice Lake EC',
                        'Lake Hylia ES': 'Ice Lake ES',
                        'Ice Cave SW': 'Shopping Mall SW',
                        'Ice Cave SE': 'Shopping Mall SE',
                        'Desert Pass EC': 'Swamp Nook EC',
                        'Desert Pass ES': 'Swamp Nook ES',
                        'Dam NC': 'Swamp NC',
                        'Dam WC': 'Swamp WC',
                        'Dam WS': 'Swamp WS',
                        'Dam EC': 'Swamp EC',
                        'South Pass WC': 'Dark South Pass WC',
                        'South Pass NC': 'Dark South Pass NC',
                        'South Pass ES': 'Dark South Pass ES',
                        'Octoballoon NW': 'Bomber Corner NW',
                        'Octoballoon NE': 'Bomber Corner NE',
                        'Octoballoon WC': 'Bomber Corner WC',
                        'Octoballoon WS': 'Bomber Corner WS'
                        })

OWExitTypes = {
    'OWEdge': [],
    'Ledge': ['West Death Mountain Drop',
            'Spectacle Rock Ledge Drop',
            'EDM To Spiral Ledge Drop',
            'EDM To Fairy Ledge Drop',
            'EDM To Mimic Ledge Drop',
            'EDM Ledge Drop',
            'Spiral Ledge Drop',
            'Spiral Mimic Ledge Drop',
            'Fairy Ascension Ledge Drop',
            'Fairy Ascension Plateau Ledge Drop',
            'TR Pegs Ledge Drop',
            'Mountain Pass Entry Ledge Drop',
            'Mountain Pass Ledge Drop',
            'Zora Waterfall Water Drop',
            'Bonk Rock Ledge Drop',
            'Graveyard Ledge Drop',
            'Potion Shop Water Drop',
            'Potion Shop Northeast Water Drop',
            'Zora Approach Bottom Ledge Drop',
            'Zora Approach Water Drop',
            'Zora Approach Ledge Drop',
            'Hyrule Castle Ledge Drop',
            'Hyrule Castle Ledge Courtyard Drop',
            'Wooden Bridge Water Drop',
            'Wooden Bridge Northeast Water Drop',
            'Sand Dunes Cliff Ledge Drop',
            'Stone Bridge East Cliff Ledge Drop',
            'Tree Line Cliff Ledge Drop',
            'Eastern Palace Cliff Ledge Drop',
            'Maze Race Ledge Drop',
            'Central Bonk Rocks Cliff Ledge Drop',
            'Links House Cliff Ledge Drop',
            'Stone Bridge Cliff Ledge Drop',
            'Lake Hylia Northwest Cliff Ledge Drop',
            'Lake Hylia Island FAWT Ledge Drop',
            'Stone Bridge EC Cliff Water Drop',
            'Tree Line WC Cliff Water Drop',
            'C Whirlpool Outer Cliff Ledge Drop',
            'C Whirlpool Cliff Ledge Drop',
            'C Whirlpool Portal Cliff Ledge Drop',
            'Statues Cliff Ledge Drop',
            'Desert Ledge Drop',
            'Checkerboard Ledge Drop',
            'Desert Mouth Drop',
            'Desert Teleporter Drop',
            'Checkerboard Cliff Ledge Drop',
            'Suburb Cliff Ledge Drop',
            'Cave 45 Cliff Ledge Drop',
            'Desert C Whirlpool Cliff Ledge Drop',
            'Desert Pass Cliff Ledge Drop',
            'Dam Cliff Ledge Drop',
            'Bombos Tablet Drop',
            'Cave 45 Ledge Drop',
            'Lake Hylia South Water Drop',
            'Lake Hylia Island Water Drop',
            'Desert Pass Ledge Drop',
            'Octoballoon Waterfall Water Drop',
            'West Dark Death Mountain Drop',
            'East Dark Death Mountain Drop',
            'Floating Island Drop',
            'Turtle Rock Tail Ledge Drop',
            'Turtle Rock Ledge Drop',
            'Bumper Cave Ledge Drop',
            'Bumper Cave Entry Drop',
            'Qirn Jump Water Drop',
            'Dark Witch Water Drop',
            'Dark Witch Northeast Water Drop',
            'Catfish Approach Bottom Ledge Drop',
            'Catfish Approach Water Drop',
            'Catfish Approach Ledge Drop',
            'Shield Shop Fence Drop (Outer)',
            'Shield Shop Fence Drop (Inner)',
            'Pyramid Exit Ledge Drop',
            'Broken Bridge Water Drop',
            'Broken Bridge Northeast Water Drop',
            'Broken Bridge West Water Drop',
            'Dark Dunes Cliff Ledge Drop',
            'Hammer Bridge North Cliff Ledge Drop',
            'Dark Tree Line Cliff Ledge Drop',
            'Palace of Darkness Cliff Ledge Drop',
            'Dig Game To Ledge Drop',
            'Dig Game Ledge Drop',
            'Frog Ledge Drop',
            'Hammer Bridge Water Drop',
            'Dark Bonk Rocks Cliff Ledge Drop',
            'Bomb Shop Cliff Ledge Drop',
            'Hammer Bridge South Cliff Ledge Drop',
            'Ice Lake Iceberg Bomb Jump',
            'Ice Lake Northwest Cliff Ledge Drop',
            'Ice Palace Island FAWT Ledge Drop',
            'Hammer Bridge EC Cliff Water Drop',
            'Dark Tree Line WC Cliff Water Drop',
            'Dark C Whirlpool Outer Cliff Ledge Drop',
            'Dark C Whirlpool Cliff Ledge Drop',
            'Dark C Whirlpool Portal Cliff Ledge Drop',
            'Hype Cliff Ledge Drop',
            'Mire Teleporter Ledge Drop',
            'Mire Cliff Ledge Drop',
            'Dark Checkerboard Cliff Ledge Drop',
            'Archery Game Cliff Ledge Drop',
            'Stumpy Approach Cliff Ledge Drop',
            'Mire C Whirlpool Cliff Ledge Drop',
            'Swamp Nook Cliff Ledge Drop',
            'Swamp Cliff Ledge Drop',
            'Ice Lake Water Drop',
            'Ice Lake Southwest Water Drop',
            'Ice Lake Southeast Water Drop',
            'Bomber Corner Waterfall Water Drop'
        ],
    'OpenTerrain': ['Old Man Drop Off',
                'Spectacle Rock Approach',
                'Spectacle Rock Leave',
                'Floating Island Bridge (East)',
                'Spiral Mimic Bridge (West)',
                'Spiral Mimic Bridge (East)',
                'Spiral Ledge Approach',
                'Mimic Ledge Approach',
                'Floating Island Bridge (West)',
                'Graveyard Ladder (Bottom)',
                'Graveyard Ladder (Top)',
                'Hyrule Castle Main Gate (South)',
                'Hyrule Castle Main Gate (North)',
                'Stone Bridge (Northbound)',
                'Stone Bridge (Southbound)',
                'Checkerboard Ledge Approach',
                'Checkerboard Ledge Leave',
                'Cave 45 Approach',
                'Cave 45 Leave',
                'Middle Aged Man',
                'Desert Pass Ladder (South)',
                'Desert Pass Ladder (North)',
                'Kiki Assistance',
                'GT Approach',
                'GT Leave',
            ],
    'OWTerrain': ['Lost Woods Bush (West)',
                'Lost Woods Bush (East)',
                'DM Hammer Bridge (West)',
                'DM Hammer Bridge (East)',
                'Fairy Ascension Rocks (Inner)',
                'DM Broken Bridge (West)',
                'DM Broken Bridge (East)',
                'Fairy Ascension Rocks (Outer)',
                'TR Pegs Ledge Entry',
                'TR Pegs Ledge Leave',
                'Mountain Pass Rock (Outer)',
                'Mountain Pass Rock (Inner)',
                'Zora Waterfall Water Entry',
                'Zora Waterfall Approach',
                'Zora Waterfall Landing',
                'Lost Woods Pass Hammer (North)',
                'Lost Woods Pass Hammer (South)',
                'Lost Woods Pass Rock (North)',
                'Lost Woods Pass Rock (South)',
                'Kings Grave Rocks (Outer)',
                'Kings Grave Rocks (Inner)',
                'River Bend Water Drop',
                'River Bend West Pier',
                'River Bend East Water Drop',
                'River Bend East Pier',
                'Potion Shop Rock (South)',
                'Potion Shop Rock (North)',
                'Zora Approach Rocks (West)',
                'Zora Approach Rocks (East)',
                'Kakariko Southwest Bush (North)',
                'Kakariko Yard Bush (South)',
                'Kakariko Southwest Bush (South)',
                'Kakariko Yard Bush (North)',
                'Hyrule Castle East Rock (Inner)',
                'Hyrule Castle Southwest Bush (North)',
                'Hyrule Castle Southwest Bush (South)',
                'Hyrule Castle Courtyard Bush (South)',
                'Hyrule Castle Courtyard Bush (North)',
                'Hyrule Castle East Rock (Outer)',
                'Wooden Bridge Bush (South)',
                'Wooden Bridge Bush (North)',
                'Blacksmith Ledge Peg (West)',
                'Blacksmith Ledge Peg (East)',
                'Maze Race Game',
                'Desert Statue Move',
                'Desert Ledge Rocks (Outer)',
                'Desert Ledge Rocks (Inner)',
                'Flute Boy Bush (South)',
                'Flute Boy Bush (North)',
                'C Whirlpool Rock (Bottom)',
                'C Whirlpool Rock (Top)',
                'C Whirlpool Pegs (Outer)',
                'C Whirlpool Pegs (Inner)',
                'C Whirlpool Water Entry',
                'C Whirlpool Landing',
                'Statues Water Entry',
                'Statues Landing',
                'Lake Hylia Central Water Drop',
                'Lake Hylia Central Island Pier',
                'Lake Hylia Island Pier',
                'Lake Hylia Water Drop',
                'Lake Hylia West Pier',
                'Lake Hylia Northeast Water Drop',
                'Lake Hylia East Pier',
                'Lake Hylia Water D Approach',
                'Lake Hylia Water D Leave',
                'Ice Cave Pier',
                'Desert Pass Rocks (North)',
                'Desert Pass Rocks (South)',
                'Octoballoon Water Drop',
                'Octoballoon Pier',
                'Skull Woods Rock (East)',
                'Skull Woods Rock (West)',
                'Skull Woods Forgotten Bush (West)',
                'Skull Woods Forgotten Bush (East)',
                'East Dark Death Mountain Bushes',
                'Bumper Cave Rock (Outer)',
                'Bumper Cave Rock (Inner)',
                'Skull Woods Pass Bush Row (West)',
                'Skull Woods Pass Bush Row (East)',
                'Skull Woods Pass Bush (North)',
                'Skull Woods Pass Bush (South)',
                'Skull Woods Pass Rock (North)',
                'Skull Woods Pass Rock (South)',
                'Dark Graveyard Bush (South)',
                'Dark Graveyard Bush (North)',
                'Qirn Jump East Water Drop',
                'Qirn Jump Pier',
                'Dark Witch Rock (South)',
                'Dark Witch Rock (North)',
                'Catfish Approach Rocks (West)',
                'Catfish Approach Rocks (East)',
                'Bush Yard Pegs (Outer)',
                'Bush Yard Pegs (Inner)',
                'Pyramid Crack',
                'Broken Bridge Hammer Rock (South)',
                'Broken Bridge Hammer Rock (North)',
                'Broken Bridge Hookshot Gap',
                'Peg Area Rocks (West)',
                'Peg Area Rocks (East)',
                'Frog Rock (Outer)',
                'Archery Game Rock (North)',
                'Frog Rock (Inner)',
                'Archery Game Rock (South)',
                'Hammer Bridge Pegs (North)',
                'Hammer Bridge Pegs (South)',
                'Hammer Bridge Pier',
                'Stumpy Approach Bush (South)',
                'Stumpy Approach Bush (North)',
                'Dark C Whirlpool Rock (Bottom)',
                'Dark C Whirlpool Rock (Top)',
                'Dark C Whirlpool Pegs (Outer)',
                'Dark C Whirlpool Pegs (Inner)',
                'Dark C Whirlpool Water Entry',
                'Dark C Whirlpool Landing',
                'Hype Cave Water Entry',
                'Hype Cave Landing',
                'Ice Lake Northeast Water Drop',
                'Ice Lake Northeast Pier',
                'Ice Lake Northeast Pier Hop',
                'Ice Lake Iceberg Water Entry',
                'Shopping Mall Pier',
                'Bomber Corner Water Drop',
                'Bomber Corner Pier'
            ],
    'Portal': ['West Death Mountain Teleporter',
                'East Death Mountain Teleporter',
                'TR Pegs Teleporter',
                'Kakariko Teleporter',
                'Castle Gate Teleporter',
                'Castle Gate Teleporter (Inner)',
                'East Hyrule Teleporter',
                'Desert Teleporter',
                'South Hyrule Teleporter',
                'Lake Hylia Teleporter',
                'Dark Death Mountain Teleporter (West)',
                'East Dark Death Mountain Teleporter',
                'Turtle Rock Teleporter',
                'West Dark World Teleporter',
                'Post Aga Teleporter',
                'East Dark World Teleporter',
                'Mire Teleporter',
                'South Dark World Teleporter',
                'Ice Lake Teleporter'
            ],
    'Whirlpool': ['Zora Whirlpool',
                'Kakariko Pond Whirlpool',
                'River Bend Whirlpool',
                'C Whirlpool',
                'Lake Hylia Whirlpool',
                'Octoballoon Whirlpool',
                'Qirn Jump Whirlpool',
                'Bomber Corner Whirlpool'
            ],
    'Mirror': ['Mirror To Bombos Tablet Ledge'
            ]
}

OWTileDistricts = {
    0x00: (None, None, ('Northwest Hyrule', 'Northwest Dark World')),
    0x02: (None, None, ('Northwest Hyrule', 'Northwest Dark World')),
    0x03: (None, None, ('Death Mountain', 'Dark Death Mountain')),
    0x05: (None, None, ('Death Mountain', 'Dark Death Mountain')),
    0x07: (None, None, ('Death Mountain', 'Dark Death Mountain')),
    0x0a: (None, None, ('Northwest Hyrule', 'Northwest Dark World')),
    0x0f: (None, None, ('Eastern Hyrule', 'East Dark World')),
    0x10: (None, None, ('Northwest Hyrule', 'Northwest Dark World')),
    0x11: (None, None, ('Northwest Hyrule', 'Northwest Dark World')),
    0x12: (None, None, ('Northwest Hyrule', 'Northwest Dark World')),
    0x13: (None, None, ('Northwest Hyrule', 'Northwest Dark World')),
    0x14: (None, None, ('Northwest Hyrule', 'Northwest Dark World')),
    0x15: (['River Bend Area', 'Qirn Jump Area'], # if region in this list
                       ('Northwest Hyrule', 'Northwest Dark World'), # use this district
                       ('Eastern Hyrule', 'East Dark World')), # else this district
    0x16: (None, None, ('Eastern Hyrule', 'East Dark World')),
    0x17: (None, None, ('Eastern Hyrule', 'East Dark World')),
    0x18: (None, None, ('Kakariko', 'Northwest Dark World')),
    0x1a: (None, None, ('Northwest Hyrule', 'Northwest Dark World')),
    0x1b: (None, None, ('Central Hyrule', 'East Dark World')),
    0x1d: (None, None, ('Eastern Hyrule', 'East Dark World')),
    0x1e: (None, None, ('Eastern Hyrule', 'East Dark World')),
    0x22: (None, None, ('Kakariko', 'Northwest Dark World')),
    0x25: (None, None, ('Eastern Hyrule', 'East Dark World')),
    0x28: (None, None, ('Kakariko', 'South Dark World')),
    0x29: (None, None, ('Kakariko', 'South Dark World')),
    0x2a: (None, None, ('Central Hyrule', 'South Dark World')),
    0x2b: (None, None, ('Central Hyrule', 'South Dark World')),
    0x2c: (None, None, ('Central Hyrule', 'South Dark World')),
    0x2d: (['Stone Bridge North Area', 'Hammer Bridge North Area'],
                       ('Eastern Hyrule', 'East Dark World'),
                       ('Lake Hylia', 'South Dark World')),
    0x2e: (['Tree Line Area', 'Dark Tree Line Area'],
                       ('Eastern Hyrule', 'East Dark World'),
                       ('Lake Hylia', 'South Dark World')),
    0x2f: (None, None, ('Eastern Hyrule', 'East Dark World')),
    0x30: (None, None, ('The Desert Area', 'The Mire Area')),
    0x32: (None, None, ('Central Hyrule', 'South Dark World')),
    0x33: (None, None, ('Central Hyrule', 'South Dark World')),
    0x34: (None, None, ('Central Hyrule', 'South Dark World')),
    0x35: (None, None, ('Lake Hylia', 'South Dark World')),
    0x37: (None, None, ('Lake Hylia', 'South Dark World')),
    0x3a: (None, None, ('The Desert Area', 'South Dark World')),
    0x3b: (None, None, ('Central Hyrule', 'South Dark World')),
    0x3c: (None, None, ('Central Hyrule', 'South Dark World')),
    0x3f: (None, None, ('Lake Hylia', 'South Dark World')),
    0x80: (['Master Sword Meadow'],
                       ('Northwest Hyrule', 'Northwest Dark World'),
                       ('Lake Hylia', 'South Dark World')),
    0x81: (None, None, ('Eastern Hyrule', 'East Dark World'))
}