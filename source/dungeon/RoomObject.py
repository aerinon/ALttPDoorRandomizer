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
    def subtype3_factory(x, y, type_id):
        return RoomObject(None, [((x << 2) & 0xFC) | (type_id & 0x3),
                                 ((y << 2) & 0xFC) | ((type_id >> 2) & 0x3),
                                 0xF0 | ((type_id >> 4) & 0xF)])


class DoorObject:

    def __init__(self, pos, kind):
        self.pos = pos
        self.kind = kind

    def get_bytes(self):
        return [self.pos.value, self.kind.value]

