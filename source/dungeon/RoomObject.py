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
    DiagonalWallBSw = 0x0E  # ◣ (top)
    DiagonalWallBSe = 0x0F  # ◥ (top)
    DiagonalWallBNe = 0x10  # ◢ (top)
    RailH = 0x22  # ↔
    CarpetH = 0x33  # ↔
    CarpetTrimH = 0x34  # ↔
    DrapesNorth = 0x36  # ↔
    WallTopWest = 0x61  # ↕
    WallTopEast = 0x62  # ↕
    RailV = 0x69  # ↕
    CarpetV = 0x70  # ↕
    CarpetTrimV = 0x71  # ↕
    DrapesWest = 0x73  # ↕
    ThickRail = 0x88  # ↕
    DiagonalCeilingASw = 0xA1  # ◣
    DiagonalCeilingANe = 0xA2  # ◥
    DiagonalCeilingASe = 0xA3  # ◢
    Pit = 0xA4  # ⇲
    CeilingLarge = 0xC0  # ⇲
    SpikeBlocks = 0xDE  # ⇲
    RupeeFloor = 0xE2  # ⇲

    # Subtype 2 Objects (0x100+)
    CornerTopConcaveNw2 = 0x100  # ▛
    CornerTopConcaveSe = 0x101  # ▙
    CornerTopConcaveNe = 0x102  # ▜
    CornerTopConcaveNw = 0x103  # ▟
    InterroomSpiralStairsUp = 0x138

    # Subtype 3 Objects (0x100+)
    NineBlueRupees = 0x212
    KholdstareShell = 0x215
    Chest = 0x219
    LampCone = 0x22A
    WarpTileDisabled = 0x24F
    Pot = 0x22F
    ShuffledPot = 0x230
    TrinexxShell = 0x272
    BossEntrance = 0x274

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

