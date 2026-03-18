from Utils import snes_to_pc

# Subtype 3 object (0x2xx by jpdasm id - see bank 01)
# B
Normal_Pot = (0xFA, 3, 3)
Shuffled_Pot = (0xFB, 0, 0)  # formerly weird pot, or black diagonal thing


class RoomObject:

    def __init__(self, address, data, dummy=False):
        self.address = address
        self.data = data
        self.dummy = dummy  # some room objects are dummies, unreachable

    def change_type(self, new_type):
        type_id, datum_a, datum_b = new_type
        if 0xF8 <= type_id < 0xFC:  # sub type 3
            self.data = (self.data[0] & 0xFC) | datum_a, (self.data[1] & 0xFC) | datum_b, type_id
        else:
            pass  # not yet implemented

    def write_to_rom(self, rom):
        rom.write_bytes(snes_to_pc(self.address), self.data)

    # subtype 3 only?
    def matches_oid(self, oid):
        my_oid = (self.data[2] << 4) | ((self.data[1] & 3) << 2) | (self.data[0] & 3)
        return my_oid == oid

    @staticmethod
    def get_subtype(type_id):
        """Determine the subtype based on type_id."""
        if type_id >= 0x200:
            return 3
        if type_id >= 0x100:
            return 2
        else:
            return 1

    @staticmethod
    def subtype1_factory(type_id, x, y, size):
        """Create a subtype 1 object from x, y, size parameters.

        Args:
            x: X coordinate (0-31)
            y: Y coordinate (0-31)
            size: Size value containing width/height info (0-15)
            type_id: The object type/routine ID

        Returns:
            RoomObject with properly formatted data bytes
        """
        # Extract aa and cc bits from size (aacc in bottom 4 bits)
        cc = size & 0x3
        aa = (size >> 2) & 0x3

        # Format: Low byte = xxxxxxaa, High byte = yyyyccyy
        low_byte = ((x & 0x3F) << 2) | aa
        high_byte = ((y & 0x3F) << 2) | cc

        return RoomObject(None, [low_byte, high_byte, type_id])

    @staticmethod
    def subtype2_factory(type_id, x, y):
        """Create a subtype 2 object from x, y parameters.

        Subtype 2 format:
        Byte 1: aaaaaabb (marker bits all 1s, bb from x)
        Byte 2: eeeecccc (eeee from x, cccc from y)
        Byte 3: ffdddddd (ff from y, dddddd from type_id)

        Where:
        - x = bbeeee (6 bits total)
        - y = ccccff (6 bits total)
        - d = type_id - 0x100 (for type_id >= 0x100)

        Args:
            type_id: The object type/routine ID (>= 0xFC, typically 0x100+)
            x: X coordinate (0-63)
            y: Y coordinate (0-63)

        Returns:
            RoomObject with properly formatted data bytes
        """
        # Extract bits from coordinates
        bb = (x >> 4) & 0x3    # Upper 2 bits of x
        eeee = x  & 0xF        # Lower 4 bits of x
        cccc = (y >> 2) & 0xF  # Upper 4 bits of y
        ff = y & 0x3           # Lower 2 bits of y

        # Calculate d from type_id (offset from 0x100)
        dddddd = (type_id - 0x100) & 0x3F

        # Format bytes
        byte1 = 0xFC | bb  # Since 0xFC already has all marker bits set, just OR with bb
        byte2 = (eeee << 4) | cccc
        byte3 = (ff << 6) | dddddd

        return RoomObject(None, [byte1, byte2, byte3])

    @staticmethod
    def subtype3_factory(type_id, x, y):
        aa = type_id & 0x3
        cc = (type_id >> 2) & 0x3

        # Format: Low byte = xxxxxxaa, High byte = yyyyccyy
        byte1 = ((x & 0x3F) << 2) | aa
        byte2 = ((y & 0x3F) << 2) | cc
        byte3 = 0xF8 | ((type_id & 0x70) >> 4)


        return RoomObject(None, [byte1, byte2, byte3])

    @staticmethod
    def factory(obj_name, x, y, size=0):
        """Factory method that auto-detects subtype and calls appropriate factory.

        Args:
            x: X coordinate
            y: Y coordinate
            size: For subtype 1, this is size. For subtype 3, this is type_id
            type_id: Only used for subtype 1
        """
        type_id = ObjectType.from_string(obj_name)
        subtype = RoomObject.get_subtype(type_id)
        if subtype == 1:
            return RoomObject.subtype1_factory(type_id, x, y, size)
        elif subtype == 2:
            return RoomObject.subtype2_factory(type_id, x, y)
        elif subtype == 3:
            return RoomObject.subtype3_factory(type_id, x, y)
        else:
            raise ValueError(f"Invalid type_id {type_id} for this call pattern")


class DoorObject:

    def __init__(self, pos, kind):
        self.pos = pos
        self.kind = kind

    def get_bytes(self):
        return [self.pos.value, self.kind.value]


class ObjectType:
    """Maps object names to their type IDs."""

    # Subtype 1 Objects (0x00-0xF7)
    CeilingH = 0x00  # ↔
    WallTopNorth = 0x01  # ↔
    WallTopS = 0x02  # Wall (top, south) ↔
    WallBottomN = 0x03  # Wall (bottom, north) ↔
    WallBottomS = 0x04  # Wall (bottom, south) ↔
    WallColumnsN = 0x05  # Wall columns (north) ↔
    WallColumnsS = 0x06  # Wall columns (south) ↔
    DeepWallN = 0x07  # Deep wall (north) ↔
    DeepWallS = 0x08  # Deep wall (south) ↔
    DiagonalWallANwTop = 0x09  # Diagonal wall A ◤ (top)
    DiagonalWallASwTop = 0x0A  # Diagonal wall A ◣ (top)
    DiagonalWallANeTop = 0x0B  # Diagonal wall A ◥ (top)
    DiagonalWallASeTop = 0x0C  # Diagonal wall A ◢ (top)
    DiagonalWallBNwTop = 0x0D  # Diagonal wall B ◤ (top)
    DiagonalWallBSw = 0x0E  # ◣ (top)
    DiagonalWallBSe = 0x0F  # ◥ (top)
    DiagonalWallBNe = 0x10  # ◢ (top)
    DiagonalWallBNwBottom = 0x19  # Diagonal wall B ◤ (bottom)
    DiagonalWallBSwBottom = 0x1A  # Diagonal wall B ◣ (bottom)
    DiagonalWallBNeBottom = 0x1B  # Diagonal wall B ◥ (bottom)
    DiagonalWallBSeBottom = 0x1C  # Diagonal wall B ◢ (bottom)
    PlatformStairs = 0x21  # Platform stairs ↔
    RailH = 0x22  # ↔
    PitEdgeNorthFull = 0x27  # Pit edge ┏━┓ E (north) ↔
    PitEdgeSouthFull = 0x28  # Pit edge ┗━┛ (south) ↔
    PitEdgeSouthLine = 0x29  # Pit edge ━━━ (south) ↔
    PitEdgeNorthLine = 0x2A  # Pit edge ━━━ (north) ↔
    PitEdgeSouthE = 0x2B  # Pit edge ━━┛ (south) ↔
    PitEdgeSouthW = 0x2C  # Pit edge ┗━━ (south) ↔
    PitEdgeNorthE = 0x2D  # Pit edge ━━┓ (north) ↔
    PitEdgeNorthW = 0x2E  # Pit edge ┏━━ (north) ↔
    RailWallN = 0x2F  # Rail wall (north) ↔
    RailWallS = 0x30  # Rail wall (south) ↔
    Nothing1 = 0x31  # Nothing
    Nothing2 = 0x32  # Nothing
    CarpetH = 0x33  # ↔
    CarpetTrimH = 0x34  # ↔
    DrapesNorth = 0x36  # ↔
    Statues = 0x38  # Statues ↔
    WallDecorsN = 0x3A  # Wall decors (north) ↔
    WallDecorsS = 0x3B  # Wall decors (south) ↔
    ChairsInPairs = 0x3C  # Chairs in pairs ↔
    TallTorchesH = 0x3D  # Tall torches ↔
    SupportsN = 0x3E  # Supports (north) ↔
    WaterEdgeNorthConcave = 0x3F  # Water edge ┏━┓ (concave) ↔
    WaterEdgeSouthConcave = 0x40  # Water edge ┗━┛ (concave) ↔
    WaterEdgeNorthConvex = 0x41  # Water edge ┏━┓ (convex) ↔
    WaterEdgeSouthConvex = 0x42  # Water edge ┗━┛ (convex) ↔
    WaterEdgeNeConcave = 0x43  # Water edge ┏━┛ (concave) ↔
    WaterEdgeNwConcave = 0x44  # Water edge ┗━┓ (concave) ↔
    WaterEdgeNwConvex = 0x45  # Water edge ┗━┓ (convex) ↔
    WaterEdgeNeConvex = 0x46  # Water edge ┏━┛ (convex) ↔
    Support = 0x4B  # Support (south) ↔
    BarH = 0x4C  # Bar ↔
    Shelf = 0x4F  # Shelf ↔
    SomariaPathH = 0x50  # Somaria path ↔
    CannonHoleBottomN = 0x51  # Cannon hole (bottom, north) ↔
    CannonHoleBottomS = 0x52  # Cannon hole (bottom, south) ↔
    PipePathH = 0x53  # Pipe path ↔
    WallTorchesN = 0x55  # Wall torches (north) ↔
    WallTorchesS = 0x56  # Wall torches (south) ↔
    ThickRailH = 0x5D  # Thick rail ↔
    BlocksH = 0x5E  # Blocks ↔
    LongRailH = 0x5F  # Long rail ↔
    Ceiling = 0x60  # ↕
    WallTopWest = 0x61  # ↕
    WallTopEast = 0x62  # ↕
    WallBottomW = 0x63  # Wall (bottom, west) ↕
    WallBottomE = 0x64  # Wall (bottom, east) ↕
    WallColumnsW = 0x65  # Wall columns (west) ↕
    WallColumnsE = 0x66  # Wall columns (east) ↕
    DeepWallW = 0x67  # Deep wall (west) ↕
    DeepWallE = 0x68  # Deep wall (east) ↕
    RailV = 0x69  # ↕
    PitEdgeW = 0x6A  # Pit edge (west) ↕
    PitEdgeE = 0x6B  # Pit edge (east) ↕
    RailWallW = 0x6C  # Rail wall (west) ↕
    RailWallE = 0x6D  # Rail wall (east) ↕
    CarpetV = 0x70  # ↕
    CarpetTrimV = 0x71  # ↕
    DrapesWest = 0x73  # ↕
    Drapes = 0x74  # Drapes (east) ↕
    ColumnsV = 0x75  # Columns ↕
    WallDecorsW = 0x76  # Wall decors (west) ↕
    WallDecorsE = 0x77  # Wall decors (east) ↕
    SupportsW = 0x78  # Supports (west) ↕
    WaterEdgeW = 0x79  # Water edge (west) ↕
    WaterEdgeE = 0x7A  # Water edge (east) ↕
    SupportsE = 0x7B  # Supports (east) ↕
    SomariaPathV = 0x7C  # Somaria path ↕
    PipePathV = 0x7D  # Pipe path ↕
    WallTorchesW = 0x7F  # Wall torches (west) ↕
    WallTorchesE = 0x80  # Wall torches (east) ↕
    WallDecorsTightAW = 0x81  # Wall decors tight A (west) ↕
    WallDecorsTightAE = 0x82  # Wall decors tight A (east) ↕
    WallDecorsTightBW = 0x83  # Wall decors tight B (west) ↕
    WallDecorsTightBE = 0x84  # Wall decors tight B (east) ↕
    CannonHoleW = 0x85  # Cannon hole (west) ↕
    CannonHoleE = 0x86  # Cannon hole (east) ↕
    TallTorchesV = 0x87  # Tall torches ↕
    ThickRailV = 0x88  # ↕
    BlocksV = 0x89  # Blocks ↕
    LongRailV = 0x8A  # Long rail ↕
    JumpLedgeW = 0x8B  # Jump ledge (west) ↕
    JumpLedgeE = 0x8C  # Jump ledge (east) ↕
    RugTrimW = 0x8D  # Rug trim (west) ↕
    RugTrimE = 0x8E  # Rug trim (east) ↕
    BarV = 0x8F  # Bar ↕
    WallFlairW = 0x90  # Wall flair (west) ↕
    WallFlairE = 0x91  # Wall flair (east) ↕
    BluePegsV = 0x92  # Blue pegs ↕
    OrangePegsV = 0x93  # Orange pegs ↕
    InvisibleFloorV = 0x94  # Invisible floor ↕
    CeilingMediumH = 0x9C  # Ceiling (medium) ↔
    CeilingSmallV = 0x9D  # Ceiling (small) ↕
    CeilingTinyH = 0x9E  # Ceiling (tiny) ↔
    DiagonalCeiling = 0xA0  # Diagonal ceiling A ◤
    DiagonalCeilingASw = 0xA1  # ◣
    DiagonalCeilingANe = 0xA2  # ◥
    DiagonalCeilingASe = 0xA3  # ◢
    Pit = 0xA4  # ⇲
    DiagonalLayer2MaskANw = 0xA5  # Diagonal layer 2 mask A ◤
    DiagonalLayer2MaskANe = 0xA7  # Diagonal layer 2 mask A ◥
    DiagonalLayer2CeilingASw = 0xA8  # Diagonal layer 2 ceiling A ◣
    DiagonalLayer2CeilingASe = 0xAA  # Diagonal layer 2 ceiling A ◢
    DiagonalLayer2MaskBNw = 0xA9  # Diagonal layer 2 mask B ◤
    DiagonalLayer2MaskBSw = 0xAA  # Diagonal layer 2 mask B ◣
    DiagonalLayer2MaskBNe = 0xAB  # Diagonal layer 2 mask B ◥
    DiagonalLayer2MaskBSe = 0xAC  # Diagonal layer 2 mask B ◢
    JumpLedgeN = 0xB0  # Jump ledge (north) ↔
    JumpLedgeS = 0xB1  # Jump ledge (south) ↔
    Rug = 0xB2  # Rug ↔
    RugTrimN = 0xB3  # Rug trim (north) ↔
    RugTrimS = 0xB4  # Rug trim (south) ↔
    ArcheryGameCurtains = 0xB5  # Archery game curtains ↔
    WallFlairN = 0xB6  # Wall flair (north) ↔
    WallFlairS = 0xB7  # Wall flair (south) ↔
    BluePegsH = 0xB8  # Blue pegs ↔
    OrangePegsH = 0xB9  # Orange pegs ↔
    InvisibleFloorH = 0xBA  # Invisible floor ↔
    FakePressurePlates = 0xBB  # Fake pressure plates ↔
    CeilingLarge = 0xC0  # ⇲
    ChestPlatformTall = 0xC1  # Chest platform (tall) ⇲
    Layer2PitMaskLarge = 0xC2  # Layer 2 pit mask (large) ⇲
    Layer2PitMaskMedium = 0xC3  # Layer 2 pit mask (medium) ⇲
    Floor1 = 0xC4  # Floor 1 ⇲
    Floor3 = 0xC5  # Floor 3 ⇲
    Layer2MaskLarge = 0xC6  # Layer 2 mask (large) ⇲
    Floor4 = 0xC7  # Floor 4 ⇲
    WaterFloor = 0xC8  # Water floor ⇲
    FloodWaterMedium = 0xC9  # Flood water (medium) ⇲
    ConveyorFloor = 0xCA  # Conveyor floor ⇲
    MovingWallW = 0xCD  # Moving wall (west) ⇲
    MovingWallE = 0xCE  # Moving wall (east) ⇲
    IcyFloor = 0xD1  # Icy floor A ⇲
    IcyFloorB = 0xD2  # Icy floor B ⇲
    Layer2MaskMedium = 0xD7  # Layer 2 mask (medium) ⇲
    FloodWaterLarge = 0xD8  # Flood water (large) ⇲
    Layer2SwimMask = 0xD9  # Layer 2 swim mask ⇲
    FloodWaterB = 0xDA  # Flood water B (large) ⇲
    Floor2 = 0xDB  # Floor 2 ⇲
    ChestPlatformShort = 0xDC  # Chest platform (short) ⇲
    TableRock = 0xDD  # Table / Rock ⇲
    SpikeBlocks = 0xDE  # ⇲
    SpikedFloor = 0xDF  # ⇲
    Floor7 = 0xE0  # Floor 7 ⇲
    TiledFloor = 0xE1  # Tiled floor ⇲
    RupeeFloor = 0xE2  # ⇲
    ConveyorUpwards = 0xE3  # Conveyor upwards ⇲
    ConveyorDownwards = 0xE4  # Conveyor downwards ⇲
    ConveyorLeftwards = 0xE5  # Conveyor leftwards ⇲
    ConveyorRightwards = 0xE6  # Conveyor rightwards ⇲
    HeavyCurrentWater = 0xE7  # Heavy current water ⇲
    Floor10 = 0xE8  # Floor 10 ⇲

    # Subtype 2 Objects (0x100+)
    CornerTopConcaveNW = 0x100  # ▛
    CornerTopConcaveSE = 0x101  # ▙
    CornerTopConcaveNE = 0x102  # ▜
    CornerTopConcaveSW = 0x103  # ▟
    CornerTopConvexSW = 0x104  # ▟
    CornerTopConvexNE = 0x105  # Corner (top, convex) ▜
    CornerTopConvexSE = 0x106  # ▙
    CornerTopConvexNW = 0x107  # Corner (top, convex) ▛
    CornerBottomConcaveNW = 0x108  # Corner (bottom, concave) ▛
    CornerBottomConcaveSW = 0x109  # Corner (bottom, concave) ▙
    CornerBottomConcaveNE = 0x10A  # Corner (bottom, concave) ▜
    CornerBottomConcaveSE = 0x10B  # Corner (bottom, concave) ▟
    CornerBottomConvexSE = 0x10C  # Corner (bottom, convex) ▟
    CornerBottomConvexNE = 0x10D  # Corner (bottom, convex) ▜
    CornerBottomConvexSW = 0x10E  # Corner (bottom, convex) ▙
    CornerBottomConvexNW = 0x10F  # Corner (bottom, convex) ▛
    KinkedCornerNorthNE = 0x110  # Kinked corner north (bottom) ▜
    KinkedCornerNorthNW = 0x112  # Kinked corner north (bottom) ▛
    KinkedCornerSouth = 0x113  # Kinked corner south (bottom) ▙
    KinkedCornerWestSW = 0x114  # Kinked corner west (bottom) ▙
    KinkedCornerWestNW = 0x115  # Kinked corner west (bottom) ▛
    KinkedCornerEastSE = 0x116  # Kinked corner east (bottom) ▟
    KinkedCornerEastNE = 0x117  # Kinked corner east (bottom) ▜
    DeepCornerConcaveNW = 0x118  # Deep corner (concave) ▛
    DeepCornerConcaveSW = 0x119  # Deep corner (concave) ▙
    DeepCornerConcaveNE = 0x11A  # Deep corner (concave) ▜
    DeepCornerConcaveSE = 0x11B  # Deep corner (concave) ▟
    LargeBrazier = 0x11C  # Large brazier
    Statue = 0x11D  # Statue
    StarTileDisabled = 0x11E  # Star tile (disabled)
    StarTileEnabled = 0x11F  # Star tile (enabled)
    SmallTorch = 0x120  # Small torch (lit)
    Barrel = 0x121  # Barrel
    Table = 0x123  # Table
    FairyStatue = 0x124  # Fairy statue
    Chair = 0x127  # Chair
    Bed = 0x128  # Bed
    Fireplace = 0x129  # Fireplace
    MarioPortrait = 0x12A  # Mario portrait
    InterroomStairsUp = 0x12D  # Interroom stairs (up)
    InterroomStairsDown = 0x12E  # Interroom stairs (down)
    InterroomStairsB = 0x12F  # Interroom stairs B (down)
    IntraroomStairsNorthSeparate = 0x131  # Intraroom stairs north (separate layers)
    IntraroomStairsNorthMerged = 0x132  # Intraroom stairs north (merged layers)
    IntraroomStairsNorthSwim = 0x133  # Intraroom stairs north (swim layer)
    Block = 0x134  # Block
    WaterLadder = 0x135  # Water ladder (north)
    Torch = 0x136  # Torch
    DamFloodgate = 0x137  # Dam floodgate
    InterroomSpiralStairsUp = 0x138
    InterroomSpiralStairsDown = 0x139
    InterroomSpiralStairsDownBottom = 0x13B  # Interroom spiral stairs down (bottom)
    SanctuaryWall = 0x13C  # Sanctuary wall (north)
    Pew = 0x13E  # Pew
    MagicBatAltar = 0x13F  # Magic bat altar

    # Subtype 3 Objects (0x200+)
    WaterfallFaceEmpty = 0x200  # Waterfall face (empty)
    WaterfallFaceShort = 0x201  # Waterfall face (short)
    WaterfallFaceLong = 0x202  # Waterfall face (long)
    SomariaPathEndpoint = 0x203  # Somaria path endpoint
    SomariaPathIntersection4Way = 0x204  # Somaria path intersection ╋
    SomariaPathCornerNW = 0x205  # Somaria path corner ┏
    SomariaPathCornerSW = 0x206  # Somaria path corner ┗
    SomariaPathCornerNE = 0x207  # Somaria path corner ┓
    SomariaPathCornerSE = 0x208  # Somaria path corner ┛
    SomariaPathIntersectionN = 0x209  # Somaria path intersection ┳
    SomariaPathIntersectionS = 0x20A  # Somaria path intersection ┻
    SomariaPathIntersectionW = 0x20B  # Somaria path intersection ┣
    SomariaPathIntersectionE = 0x20C  # Somaria path intersection ┫
    SomariaPath2WayEndpoint = 0x20E  # Somaria path 2-way endpoint
    SomariaPathCrossover = 0x20F  # Somaria path crossover
    BabasuHoleN = 0x210  # Babasu hole (north)
    BabasuHoleS = 0x211  # Babasu hole (south)
    NineBlueRupees = 0x212
    TelepathyTile = 0x213  # Telepathy tile
    SpecialWaterfallDoor = 0x214  # Special waterfall door
    KholdstareShell = 0x215
    HammerPeg = 0x216  # Hammer peg
    PrisonCell = 0x217  # Prison cell
    BigKeyLock = 0x218  # Big key lock
    Chest = 0x219
    IntraroomStairsSouthSeparate = 0x21C  # Intraroom stairs south (separate layers)
    IntraroomStairsSouthMerged = 0x21D  # Intraroom stairs south (merged layers)
    InterroomStraightStairsUpNorthTop = 0x21E  # Interroom straight stairs up (north, top)
    InterroomStraightStairsDownNorthTop = 0x21F  # Interroom straight stairs down (north, top)
    InterroomStraightStairsUpSouthTop = 0x220  # Interroom straight stairs up (south, top)
    InterroomStraightStairsDownSouthTop = 0x221  # Interroom straight stairs down (south, top)
    DeepCornerConvexSE = 0x222  # Deep corner (convex) ▟
    DeepCornerConvexNE = 0x223  # Deep corner (convex) ▜
    DeepCornerConvexSW = 0x224  # Deep corner (convex) ▙
    DeepCornerConvexNW = 0x225  # Deep corner (convex) ▛
    InterroomStraightStairsDownSouthBottom = 0x229  # Interroom straight stairs down (south, bottom)
    LampCone = 0x22A
    BigGrayBlock = 0x22C  # Big gray block
    AgahnimsAltar = 0x22D  # Agahnim's altar
    AgahnimsRoom = 0x22E  # Agahnim's Room
    Pot = 0x22F
    ShuffledPot = 0x230
    BigChest = 0x231  # Big chest
    IntraroomStairsSouthSwim = 0x233  # Intraroom stairs south (swim layer)
    PipeEndS = 0x23A  # Pipe end (south)
    PipeEndN = 0x23B  # Pipe end (north)
    PipeEndE = 0x23C  # Pipe end (east)
    PipeEndW = 0x23D  # Pipe end (west)
    PipeCornerNW = 0x23E  # Pipe corner ▛
    PipeCornerSW = 0x23F  # Pipe corner ▙
    PipeCornerNE = 0x240  # Pipe corner ▜
    PipeCornerSE = 0x241  # Pipe corner ▟
    PipeRockIntersectionNeSw = 0x242  # Pipe-rock intersection ⯊
    PipeRockIntersectionNwSe = 0x243  # Pipe-rock intersection ⯋
    PipeRockIntersectionSeNw = 0x244  # Pipe-rock intersection ◖
    PipeRockIntersectionSwNe = 0x245  # Pipe-rock intersection ◗
    PipeCrossover = 0x246  # Pipe crossover
    BombableFloor = 0x247  # Bombable floor
    FakeBombableFloor = 0x248  # Fake bombable floor
    WarpTile = 0x24A  # Warp tile
    ToolRack = 0x24B  # Tool rack
    Furnace = 0x24C  # Furnace
    TubWide = 0x24D  # Tub (wide)
    Anvil = 0x24E  # Anvil
    WarpTileDisabled = 0x24F
    PressurePlate = 0x250  # Pressure plate
    FortuneTellerRoom = 0x254  # Fortune teller room
    BarCornerNE = 0x258  # Bar corner ▜
    BarCornerSE = 0x259  # Bar corner ▟
    DecorativeBowl = 0x25A  # Decorative bowl
    TubTall = 0x25B  # Tub (tall)
    Bookcase = 0x25C  # Bookcase
    Range = 0x25D  # Range
    Suitcase = 0x25E  # Suitcase
    BarBottles = 0x25F  # Bar bottles
    ArrowGameHoleW = 0x260  # Arrow game hole (west)
    ArrowGameHoleE = 0x261  # Arrow game hole (east)
    VitreousGooGraphics = 0x262  # Vitreous goo graphics
    FakePressurePlate = 0x263  # Fake pressure plate
    MedusaHead = 0x264  # Medusa head
    FourWayShooterBlock = 0x265  # 4-way shooter block
    PitSingle = 0x266  # Pit
    WallCrackN = 0x267  # Wall crack (north)
    WallCrackS = 0x268  # Wall crack (south)
    WallCrackW = 0x269  # Wall crack (west)
    WallCrackEast = 0x26A
    LargeDecor = 0x26B  # Large decor
    WaterGrateN = 0x26C  # Water grate (north)
    WaterGrateS = 0x26D  # Water grate (south)
    WaterGrateW = 0x26E  # Water grate (west)
    WaterGrateE = 0x26F  # Water grate (east)
    WindowSunlight = 0x270  # Window sunlight
    FloorSunlight = 0x271  # Floor sunlight
    TrinexxShell = 0x272
    Layer2MaskFull = 0x273  # Layer 2 mask (full)
    BossEntrance = 0x274
    MinigameChest = 0x275  # Minigame chest
    GanonDoor = 0x276  # Ganon door
    TriforceWallOrnament = 0x277  # Triforce wall ornament
    TriforceFloorTiles = 0x278  # Triforce floor tiles
    FreezorHole = 0x279  # Freezor hole
    PileOfBones = 0x27A  # Pile of bones
    VitreousGooDamage = 0x27B  # Vitreous goo damage
    ArrowTileUp = 0x27C  # Arrow tile ↑
    ArrowTileDown = 0x27D  # Arrow tile ↓
    ArrowTileRight = 0x27E  # Arrow tile →

    @staticmethod
    def from_string(name):
        if hasattr(ObjectType, name):
            return getattr(ObjectType, name)
        raise ValueError(f"Unknown object type: {name}")

    @staticmethod
    def to_string(type_id):
        for attr in dir(ObjectType):
            if not attr.startswith('_') and not callable(getattr(ObjectType, attr)):
                if getattr(ObjectType, attr) == type_id:
                    return attr
        return f"UNKNOWN_0x{type_id:02X}"

