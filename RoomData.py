from enum import Enum, unique
from Tables import door_pair_offset_table


def create_rooms(world, player):
    world.rooms += [
        Room(player, 0x01, 0x51168).door(Position.WestN2, DoorKind.Warp).door(Position.EastN2, DoorKind.Warp),
        Room(player, 0x02, 0x50b97).door(Position.South2, DoorKind.TrapTriggerableLow).door(Position.InteriorV2, DoorKind.NormalLow2).door(Position.South2, DoorKind.ToggleFlag),
        # Room(player, 0x03, 0x509cf).door(Position.SouthW, DoorKind.CaveEntrance),
        Room(player, 0x04, 0xfe25c).door(Position.NorthW, DoorKind.StairKey2).door(Position.InteriorW, DoorKind.Dashable).door(Position.InteriorS, DoorKind.Dashable).door(Position.InteriorE, DoorKind.TrapTriggerable).door(Position.SouthW, DoorKind.Normal),
        Room(player, 0x06, 0xfa192).door(Position.SouthW, DoorKind.Trap),
        # Room(player, 0x08, 0x5064f).door(Position.InteriorS2, DoorKind.CaveEntranceLow08).door(Position.SouthE, DoorKind.CaveEntrance).door(Position.SouthW2, DoorKind.NormalLow2).door(Position.SouthW2, DoorKind.ToggleFlag),
        Room(player, 0x0a, 0xfa734).door(Position.North, DoorKind.StairKey),
        Room(player, 0x0b, 0xfabf0).door(Position.InteriorW, DoorKind.TrapTriggerable).door(Position.InteriorS, DoorKind.Trap2).door(Position.InteriorN, DoorKind.SmallKey),
        Room(player, 0x0c, 0xfef53).door(Position.South, DoorKind.DungeonEntrance),
        Room(player, 0x0d, 0xf918b).door(Position.SouthW, DoorKind.Trap),
        Room(player, 0x0e, 0xfc279).door(Position.InteriorW, DoorKind.StairKey2).door(Position.InteriorS, DoorKind.Trap).door(Position.SouthE, DoorKind.DungeonEntrance),

        # Room(player, 0x10, 0x50596).door(Position.SouthW, DoorKind.DungeonEntrance).door(Position.InteriorS, DoorKind.Normal),
        Room(player, 0x11, 0x50c52).door(Position.InteriorN, DoorKind.Dashable).door(Position.InteriorS, DoorKind.Dashable).door(Position.SouthE, DoorKind.SmallKey),
        Room(player, 0x12, 0x50a9b).door(Position.North2, DoorKind.NormalLow).door(Position.North2, DoorKind.ToggleFlag).door(Position.South2, DoorKind.NormalLow).door(Position.South2, DoorKind.IncognitoEntrance),
        Room(player, 0x13, 0xfe29d).door(Position.EastS, DoorKind.SmallKey).door(Position.EastN, DoorKind.Normal),
        Room(player, 0x14, 0xfe464).door(Position.SouthE, DoorKind.SmallKey).door(Position.WestS, DoorKind.SmallKey).door(Position.NorthW, DoorKind.Normal).door(Position.WestN, DoorKind.Normal).door(Position.SouthW, DoorKind.Normal).door(Position.EastN, DoorKind.Normal).door(Position.EastS, DoorKind.Normal),
        Room(player, 0x15, 0xfe63e).door(Position.WestS, DoorKind.Trap).door(Position.WestN, DoorKind.Normal),
        Room(player, 0x16, 0xfa150).door(Position.InteriorV, DoorKind.Bombable).door(Position.InteriorW, DoorKind.SmallKey).door(Position.InteriorE, DoorKind.Normal).door(Position.NorthW, DoorKind.Normal),
        # Room(player, 0x18, 0x506e5).door(Position.NorthW2, DoorKind.NormalLow).door(Position.NorthW2, DoorKind.ToggleFlag),
        Room(player, 0x19, 0xfacc6).door(Position.East, DoorKind.Bombable).door(Position.EastN, DoorKind.SmallKey),
        Room(player, 0x1a, 0xfa670).door(Position.InteriorE, DoorKind.SmallKey).door(Position.WestN, DoorKind.SmallKey).door(Position.West, DoorKind.Bombable).door(Position.SouthW, DoorKind.SmallKey).door(Position.InteriorN, DoorKind.Normal).door(Position.SouthE, DoorKind.Normal),
        Room(player, 0x1b, 0xfab31).door(Position.InteriorW, DoorKind.TrapTriggerable).door(Position.SouthW, DoorKind.Normal),
        Room(player, 0x1c, 0xff784).door(Position.InteriorE, DoorKind.TrapTriggerable).door(Position.InteriorS, DoorKind.Trap).door(Position.InteriorW, DoorKind.Dashable),
        Room(player, 0x1d, 0xfff19).door(Position.NorthW, DoorKind.BigKey),
        Room(player, 0x1e, 0xfc35e).door(Position.EastS, DoorKind.Trap).door(Position.InteriorS, DoorKind.Trap).door(Position.InteriorE, DoorKind.TrapTriggerable).door(Position.SouthE, DoorKind.Normal),
        Room(player, 0x1f, 0xfc3af).door(Position.WestS, DoorKind.Trap).door(Position.InteriorS, DoorKind.Trap2),

        Room(player, 0x20, 0xf918b).door(Position.SouthW, DoorKind.Trap),
        Room(player, 0x21, 0x50d2e).door(Position.NorthE, DoorKind.SmallKey).door(Position.InteriorV, DoorKind.Normal).door(Position.EastS, DoorKind.Normal),
        Room(player, 0x22, 0x50dd1).door(Position.South, DoorKind.SmallKey).door(Position.WestS, DoorKind.Normal),
        Room(player, 0x23, 0xfed30).door(Position.SouthE, DoorKind.BombableEntrance).door(Position.EastS, DoorKind.Normal),
        Room(player, 0x24, 0xfe6ee).door(Position.NorthE, DoorKind.BigKey).door(Position.InteriorN, DoorKind.Trap2).door(Position.InteriorW, DoorKind.Trap2).door(Position.InteriorE, DoorKind.Trap2).door(Position.SouthE, DoorKind.DungeonEntrance).door(Position.NorthW, DoorKind.Normal).door(Position.WestS, DoorKind.Normal).door(Position.InteriorS, DoorKind.Normal),
        Room(player, 0x26, 0xf9cbb).door(Position.South, DoorKind.SmallKey).door(Position.InteriorW, DoorKind.TrapTriggerable).door(Position.InteriorE, DoorKind.TrapTriggerable).door(Position.InteriorN, DoorKind.Normal),
        Room(player, 0x28, 0xf92a8).door(Position.NorthW, DoorKind.StairKey2).door(Position.South, DoorKind.DungeonEntrance),
        Room(player, 0x2a, 0xfa594).door(Position.NorthE, DoorKind.Trap).door(Position.NorthW, DoorKind.SmallKey).door(Position.EastS, DoorKind.Bombable).door(Position.East2, DoorKind.NormalLow).door(Position.SouthW, DoorKind.Normal).door(Position.SouthE, DoorKind.Normal),
        Room(player, 0x2b, 0xfaaa7).door(Position.InteriorS, DoorKind.Bombable).door(Position.WestS, DoorKind.Bombable).door(Position.NorthW, DoorKind.Trap).door(Position.West2, DoorKind.NormalLow),
        # Room(player, 0x2c, 0x508cf).door(Position.InteriorW, DoorKind.Bombable).door(Position.InteriorE, DoorKind.Bombable).door(Position.InteriorS, DoorKind.Bombable).door(Position.SouthE, DoorKind.Bombable).door(Position.SouthW, DoorKind.CaveEntrance),
        Room(player, 0x2e, 0xfc3d8).door(Position.NorthE, DoorKind.Normal),
        # Room(player, 0x2f, 0x507d1).door(Position.InteriorW, DoorKind.Bombable).door(Position.SouthE, DoorKind.CaveEntrance),

        Room(player, 0x30, 0xf8de3).door(Position.NorthW, DoorKind.Hidden).door(Position.InteriorW, DoorKind.Trap2),
        Room(player, 0x31, 0xfcf4f).door(Position.InteriorW, DoorKind.BigKey).door(Position.InteriorS, DoorKind.TrapTriggerable),
        Room(player, 0x32, 0x50e4b).door(Position.North, DoorKind.SmallKey),
        Room(player, 0x33, 0xf8792).door(Position.SouthW, DoorKind.Trap),
        Room(player, 0x34, 0xf993c).door(Position.EastN, DoorKind.Normal).door(Position.EastS, DoorKind.Normal),
        Room(player, 0x35, 0xf97f1).door(Position.EastN, DoorKind.SmallKey).door(Position.WestN, DoorKind.Normal).door(Position.WestS, DoorKind.Normal).door(Position.InteriorE, DoorKind.Normal)
         .door(Position.EastS, DoorKind.Normal).door(Position.InteriorV2, DoorKind.NormalLow),
        Room(player, 0x36, 0xf9685).door(Position.EastN, DoorKind.Bombable).door(Position.North, DoorKind.SmallKey).door(Position.WestN, DoorKind.SmallKey).door(Position.WestS, DoorKind.Normal)
         .door(Position.EastS, DoorKind.Normal).door(Position.South2, DoorKind.NormalLow),
        Room(player, 0x37, 0xf9492).door(Position.WestN, DoorKind.Bombable).door(Position.EastN, DoorKind.Bombable).door(Position.InteriorW, DoorKind.SmallKey).door(Position.EastS, DoorKind.SmallKey).door(Position.WestS, DoorKind.Normal).door(Position.InteriorV2, DoorKind.NormalLow),
        Room(player, 0x38, 0xf935b).door(Position.WestN, DoorKind.Bombable).door(Position.WestS, DoorKind.SmallKey),
        Room(player, 0x39, 0xfc180).door(Position.SouthW, DoorKind.Trap).door(Position.InteriorS, DoorKind.SmallKey),
        Room(player, 0x3a, 0xfa3f5).door(Position.South, DoorKind.SmallKey).door(Position.NorthW, DoorKind.Normal).door(Position.NorthE, DoorKind.Normal),
        Room(player, 0x3b, 0xfa9de).door(Position.SouthW, DoorKind.Normal),
        # Room(player, 0x3c, 0x509a3).door(Position.NorthE, DoorKind.Bombable).door(Position.SouthE, DoorKind.CaveEntrance),
        Room(player, 0x3d, 0xffd37).door(Position.InteriorE, DoorKind.TrapTriggerable).door(Position.InteriorN, DoorKind.SmallKey).door(Position.SouthW, DoorKind.SmallKey).door(Position.InteriorW, DoorKind.Bombable),
        Room(player, 0x3e, 0xfc486).door(Position.InteriorE, DoorKind.Trap).door(Position.SouthW, DoorKind.SmallKey),
        Room(player, 0x3f, 0xfc51b).door(Position.InteriorS, DoorKind.Trap),

        Room(player, 0x40, 0xf8eea).door(Position.InteriorS2, DoorKind.NormalLow2),
        Room(player, 0x41, 0x50f15).door(Position.South, DoorKind.Trap),
        Room(player, 0x43, 0xf87f8).door(Position.NorthW, DoorKind.BigKey).door(Position.InteriorE, DoorKind.SmallKey).door(Position.SouthE, DoorKind.SmallKey),
        Room(player, 0x44, 0xfdbcd).door(Position.InteriorN, DoorKind.Trap2).door(Position.InteriorS, DoorKind.SmallKey).door(Position.EastN, DoorKind.Normal).door(Position.EastS, DoorKind.Normal),
        Room(player, 0x45, 0xfdcae).door(Position.WestN, DoorKind.Trap).door(Position.InteriorW, DoorKind.Normal).door(Position.WestS, DoorKind.Normal).door(Position.InteriorS, DoorKind.Normal),
        Room(player, 0x46, 0xf9bbb).door(Position.North2, DoorKind.NormalLow).door(Position.InteriorW2, DoorKind.NormalLow).door(Position.InteriorE2, DoorKind.NormalLow),
        Room(player, 0x49, 0xfc12c).door(Position.NorthW, DoorKind.Hidden).door(Position.InteriorN, DoorKind.TrapTriggerable).door(Position.SouthW, DoorKind.SmallKey).door(Position.InteriorS, DoorKind.Normal),
        Room(player, 0x4a, 0xfa267).door(Position.InteriorW, DoorKind.Trap).door(Position.InteriorE, DoorKind.Trap).door(Position.North, DoorKind.SmallKey).door(Position.InteriorV, DoorKind.Normal).door(Position.South, DoorKind.DungeonEntrance),
        Room(player, 0x4b, 0xfa8c9).door(Position.NorthW, DoorKind.Trap).door(Position.InteriorW, DoorKind.Dashable).door(Position.InteriorE, DoorKind.Dashable),
        Room(player, 0x4c, 0xffece).door(Position.EastS, DoorKind.Trap),
        Room(player, 0x4d, 0xffe5a).door(Position.NorthW, DoorKind.SmallKey).door(Position.WestS, DoorKind.Normal),
        Room(player, 0x4e, 0xfc5ba).door(Position.InteriorN, DoorKind.Trap).door(Position.NorthW, DoorKind.SmallKey),
        Room(player, 0x4f, 0xfca89).door(Position.WestS, DoorKind.SmallKey),

        Room(player, 0x50, 0x510dc).door(Position.EastN2, DoorKind.Warp).door(Position.SouthE2, DoorKind.NormalLow2),
        Room(player, 0x51, 0x51029).door(Position.North, DoorKind.Normal).door(Position.North, DoorKind.DungeonChanger),
        Room(player, 0x52, 0x51230).door(Position.WestN2, DoorKind.Warp).door(Position.SouthW2, DoorKind.NormalLow2).door(Position.South, DoorKind.Normal),
        Room(player, 0x53, 0xf88ad).door(Position.InteriorW, DoorKind.TrapTriggerable).door(Position.InteriorS, DoorKind.Trap2).door(Position.NorthE, DoorKind.SmallKey),
        # Room(player, 0x55, 0x50166).door(Position.InteriorW2, DoorKind.NormalLow).door(Position.SouthW, DoorKind.Normal).door(Position.SouthW, DoorKind.IncognitoEntrance),
        Room(player, 0x56, 0xfbb4e).door(Position.InteriorW, DoorKind.SmallKey).door(Position.SouthW, DoorKind.DungeonEntrance).door(Position.InteriorS, DoorKind.Normal).door(Position.EastS, DoorKind.Normal),
        Room(player, 0x57, 0xfbbd2).door(Position.InteriorN, DoorKind.Bombable).door(Position.InteriorW, DoorKind.TrapTriggerable).door(Position.EastS, DoorKind.SmallKey).door(Position.SouthW, DoorKind.DungeonEntrance).door(Position.WestS, DoorKind.Normal).door(Position.SouthE, DoorKind.Normal),
        Room(player, 0x58, 0xfbcf6).door(Position.NorthW, DoorKind.BlastWall).door(Position.WestS, DoorKind.SmallKey).door(Position.SouthE, DoorKind.SmallKey).door(Position.InteriorN, DoorKind.Bombable).door(Position.SouthW, DoorKind.DungeonEntrance).door(Position.InteriorS, DoorKind.Normal),
        Room(player, 0x59, 0xfbff7).door(Position.NorthW, DoorKind.SmallKey).door(Position.SouthW, DoorKind.DungeonEntrance).door(Position.InteriorN2, DoorKind.NormalLow2).door(Position.InteriorS2, DoorKind.NormalLow2),
        Room(player, 0x5a, 0xfa7e5).door(Position.SouthE, DoorKind.Trap),
        Room(player, 0x5b, 0xff8cc).door(Position.SouthE, DoorKind.SmallKey).door(Position.EastN, DoorKind.Trap),
        Room(player, 0x5c, 0xff976).door(Position.InteriorE, DoorKind.Bombable).door(Position.WestN, DoorKind.Normal),
        Room(player, 0x5d, 0xff9e1).door(Position.InteriorW, DoorKind.Trap).door(Position.SouthW, DoorKind.Trap).door(Position.InteriorN, DoorKind.Trap),
        Room(player, 0x5e, 0xfc6b8).door(Position.EastS, DoorKind.SmallKey).door(Position.InteriorE, DoorKind.Trap2).door(Position.SouthE, DoorKind.Normal).door(Position.InteriorS, DoorKind.Normal),
        Room(player, 0x5f, 0xfc6fa).door(Position.WestS, DoorKind.SmallKey),

        Room(player, 0x60, 0x51309).door(Position.NorthE2, DoorKind.NormalLow2).door(Position.East2, DoorKind.NormalLow2).door(Position.East2, DoorKind.ToggleFlag).door(Position.EastN, DoorKind.Normal).door(Position.SouthE, DoorKind.Normal).door(Position.SouthE, DoorKind.IncognitoEntrance),
        Room(player, 0x61, 0x51454).door(Position.West2, DoorKind.NormalLow).door(Position.West2, DoorKind.ToggleFlag).door(Position.East2, DoorKind.NormalLow).door(Position.East2, DoorKind.ToggleFlag).door(Position.South2, DoorKind.NormalLow).door(Position.South2, DoorKind.IncognitoEntrance).door(Position.WestN, DoorKind.Normal),
        Room(player, 0x62, 0x51577).door(Position.West2, DoorKind.NormalLow2).door(Position.West2, DoorKind.ToggleFlag).door(Position.NorthW2, DoorKind.NormalLow2).door(Position.North, DoorKind.Normal).door(Position.SouthW, DoorKind.Normal).door(Position.SouthW, DoorKind.IncognitoEntrance),
        Room(player, 0x63, 0xf88ed).door(Position.NorthE, DoorKind.StairKey).door(Position.InteriorW, DoorKind.TrapTriggerable).door(Position.SouthW, DoorKind.DungeonEntrance),  # looked like a huge typo - I had to guess on StairKey
        Room(player, 0x64, 0xfda53).door(Position.InteriorS, DoorKind.Trap2),
        Room(player, 0x65, 0xfdac5).door(Position.InteriorS, DoorKind.Normal),
        Room(player, 0x66, 0xfa01b).door(Position.InteriorE2, DoorKind.Waterfall).door(Position.SouthW2, DoorKind.NormalLow2).door(Position.SouthW2, DoorKind.ToggleFlag).door(Position.InteriorW2, DoorKind.NormalLow2),
        Room(player, 0x67, 0xfbe17).door(Position.NorthE, DoorKind.Normal).door(Position.InteriorS, DoorKind.Normal).door(Position.EastS, DoorKind.Normal),
        Room(player, 0x68, 0xfbf02).door(Position.WestS, DoorKind.Trap).door(Position.NorthE, DoorKind.SmallKey),
        Room(player, 0x6a, 0xfa7c7).door(Position.NorthE, DoorKind.BigKey),
        Room(player, 0x6b, 0xff821).door(Position.NorthE, DoorKind.BigKey).door(Position.InteriorE, DoorKind.TrapTriggerable).door(Position.InteriorS, DoorKind.Trap).door(Position.InteriorW, DoorKind.Trap),
        Room(player, 0x6c, 0xffaa0).door(Position.InteriorS, DoorKind.Trap2).door(Position.InteriorW, DoorKind.Trap).door(Position.EastS, DoorKind.Normal),
        Room(player, 0x6d, 0xffa4e).door(Position.NorthW, DoorKind.Trap).door(Position.InteriorW, DoorKind.Trap).door(Position.WestS, DoorKind.Trap),
        Room(player, 0x6e, 0xfc74b).door(Position.NorthE, DoorKind.Trap),

        Room(player, 0x71, 0x52341).door(Position.InteriorW, DoorKind.SmallKey).door(Position.SouthW2, DoorKind.TrapTriggerableLow).door(Position.InteriorS2, DoorKind.TrapTriggerableLow),
        Room(player, 0x72, 0x51fda).door(Position.InteriorV, DoorKind.SmallKey),
        Room(player, 0x73, 0xf8972).door(Position.InteriorW, DoorKind.TrapTriggerable).door(Position.InteriorS, DoorKind.Trap2).door(Position.InteriorE, DoorKind.Normal),
        Room(player, 0x74, 0xf8a66).door(Position.InteriorE, DoorKind.Normal).door(Position.InteriorW, DoorKind.Normal),
        Room(player, 0x75, 0xf8ab9).door(Position.InteriorW, DoorKind.Trap2).door(Position.SouthE, DoorKind.Normal),
        Room(player, 0x76, 0xf9e35).door(Position.InteriorN2, DoorKind.NormalLow).door(Position.InteriorS2, DoorKind.NormalLow).door(Position.NorthW2, DoorKind.NormalLow).door(Position.NorthW2, DoorKind.ToggleFlag),
        Room(player, 0x77, 0xfd0e6).door(Position.NorthW2, DoorKind.StairKeyLow).door(Position.South2, DoorKind.DungeonEntranceLow),
        Room(player, 0x7b, 0xff02b).door(Position.SouthW, DoorKind.Trap).door(Position.EastN, DoorKind.SmallKey).door(Position.EastS, DoorKind.Normal),
        Room(player, 0x7c, 0xff0ef).door(Position.NorthE, DoorKind.BlastWall).door(Position.EastS, DoorKind.Bombable).door(Position.WestN, DoorKind.SmallKey).door(Position.WestS, DoorKind.Normal),
        Room(player, 0x7d, 0xff20c).door(Position.SouthE, DoorKind.Trap).door(Position.WestS, DoorKind.Bombable).door(Position.InteriorW, DoorKind.SmallKey),
        Room(player, 0x7e, 0xfc7c6).door(Position.SouthE, DoorKind.SmallKey).door(Position.InteriorS, DoorKind.TrapTriggerable).door(Position.EastN, DoorKind.Normal),
        Room(player, 0x7f, 0xfc827).door(Position.WestN, DoorKind.Trap).door(Position.InteriorW, DoorKind.Normal),

        Room(player, 0x81, 0x5224b).door(Position.NorthW2, DoorKind.NormalLow2),
        Room(player, 0x83, 0xf8bba).door(Position.InteriorW, DoorKind.TrapTriggerable).door(Position.SouthW, DoorKind.DungeonEntrance).door(Position.InteriorS, DoorKind.Normal),
        Room(player, 0x84, 0xf8cb7).door(Position.South, DoorKind.DungeonEntrance),
        Room(player, 0x85, 0xf8d7d).door(Position.NorthE, DoorKind.Trap).door(Position.InteriorN, DoorKind.SmallKey).door(Position.SouthE, DoorKind.DungeonEntrance).door(Position.InteriorS, DoorKind.Normal),
        Room(player, 0x87, 0xfd1b7).door(Position.InteriorN, DoorKind.Trap2).door(Position.InteriorE, DoorKind.Normal),
        Room(player, 0x8b, 0xff33f).door(Position.InteriorN, DoorKind.TrapTriggerable).door(Position.InteriorS, DoorKind.SmallKey).door(Position.EastN, DoorKind.Normal).door(Position.SouthW, DoorKind.Normal).door(Position.NorthW, DoorKind.Normal),
        Room(player, 0x8c, 0xff3ef).door(Position.EastN, DoorKind.Trap).door(Position.InteriorW, DoorKind.Trap2).door(Position.InteriorN, DoorKind.SmallKey).door(Position.WestN, DoorKind.Normal).door(Position.SouthW, DoorKind.Normal).door(Position.SouthE, DoorKind.Normal),
        Room(player, 0x8d, 0xff4e0).door(Position.SouthE, DoorKind.Trap).door(Position.InteriorN, DoorKind.SmallKey).door(Position.WestN, DoorKind.Normal).door(Position.NorthE, DoorKind.Normal).door(Position.InteriorS, DoorKind.Normal),
        Room(player, 0x8e, 0xfc84d).door(Position.NorthE, DoorKind.SmallKey),

        Room(player, 0x90, 0xfbab2).door(Position.SouthW, DoorKind.Trap),
        Room(player, 0x91, 0xfb9e6).door(Position.EastS, DoorKind.Normal),
        Room(player, 0x92, 0xfb97b).door(Position.InteriorN, DoorKind.Bombable).door(Position.InteriorW, DoorKind.Bombable).door(Position.WestS, DoorKind.Normal).door(Position.InteriorS, DoorKind.Normal).door(Position.EastS, DoorKind.Normal),
        Room(player, 0x93, 0xfb8e1).door(Position.InteriorW, DoorKind.Trap2).door(Position.InteriorE, DoorKind.SmallKey).door(Position.WestS, DoorKind.Normal),
        Room(player, 0x95, 0xffc04).door(Position.SouthE, DoorKind.Normal).door(Position.EastN, DoorKind.Normal),
        Room(player, 0x96, 0xffc78).door(Position.InteriorS, DoorKind.Trap2).door(Position.WestN, DoorKind.Normal),
        Room(player, 0x97, 0xfb30a).door(Position.InteriorS, DoorKind.Normal).door(Position.InteriorW, DoorKind.Normal),
        Room(player, 0x98, 0xfaf5b).door(Position.SouthW, DoorKind.DungeonEntrance),
        Room(player, 0x99, 0x5172a).door(Position.InteriorW, DoorKind.StairKey).door(Position.South, DoorKind.SmallKey).door(Position.InteriorE, DoorKind.Normal),
        Room(player, 0x9b, 0xff5a2).door(Position.InteriorN, DoorKind.SmallKey).door(Position.NorthW, DoorKind.Normal).door(Position.EastS, DoorKind.Normal),
        Room(player, 0x9c, 0xff6c9).door(Position.EastS, DoorKind.Trap).door(Position.NorthW, DoorKind.Normal).door(Position.NorthE, DoorKind.Normal).door(Position.WestS, DoorKind.Normal),
        Room(player, 0x9d, 0xff741).door(Position.NorthE, DoorKind.Normal).door(Position.WestS, DoorKind.Normal).door(Position.InteriorN, DoorKind.Normal),
        Room(player, 0x9e, 0xfc8c8).door(Position.NorthE, DoorKind.StairKey2).door(Position.InteriorE, DoorKind.BigKey).door(Position.InteriorS, DoorKind.Normal).door(Position.EastS, DoorKind.Normal),
        Room(player, 0x9f, 0xfc937).door(Position.WestS, DoorKind.Trap).door(Position.SouthW, DoorKind.Trap),

        Room(player, 0xa0, 0xfba9a).door(Position.NorthW, DoorKind.BigKey),
        Room(player, 0xa1, 0xfb83d).door(Position.SouthE, DoorKind.SmallKey).door(Position.East, DoorKind.Normal),
        Room(player, 0xa2, 0xfb759).door(Position.South, DoorKind.SmallKey).door(Position.West, DoorKind.Normal).door(Position.East, DoorKind.Normal).door(Position.SouthE, DoorKind.Normal),
        Room(player, 0xa3, 0xfb667).door(Position.West, DoorKind.Normal).door(Position.SouthW, DoorKind.Normal),
        Room(player, 0xa4, 0xfe741).door(Position.SouthW, DoorKind.Trap),
        Room(player, 0xa5, 0xffb7f).door(Position.NorthE, DoorKind.Trap).door(Position.InteriorE, DoorKind.Trap2).door(Position.InteriorW, DoorKind.Trap2),
        Room(player, 0xa8, 0x51887).door(Position.InteriorS, DoorKind.Trap2).door(Position.InteriorW, DoorKind.TrapTriggerable).door(Position.SouthE, DoorKind.SmallKey).door(Position.InteriorN2, DoorKind.NormalLow2).door(Position.EastN2, DoorKind.NormalLow2).door(Position.East, DoorKind.Normal),
        Room(player, 0xa9, 0x519c9).door(Position.West, DoorKind.Trap).door(Position.East, DoorKind.Trap).door(Position.North, DoorKind.BigKey).door(Position.WestN2, DoorKind.NormalLow2).door(Position.EastN2, DoorKind.NormalLow2).door(Position.South, DoorKind.Normal),
        Room(player, 0xaa, 0x51b29).door(Position.InteriorE, DoorKind.Trap2).door(Position.WestN2, DoorKind.NormalLow2).door(Position.InteriorN, DoorKind.Normal).door(Position.InteriorS, DoorKind.Normal).door(Position.West, DoorKind.Normal).door(Position.SouthW, DoorKind.Normal),
        Room(player, 0xab, 0xfd9a9).door(Position.InteriorW, DoorKind.StairKey).door(Position.SouthW, DoorKind.Normal),
        Room(player, 0xac, 0xfd9d8).door(Position.SouthE, DoorKind.Trap),
        Room(player, 0xae, 0xfc975).door(Position.EastN, DoorKind.Normal),
        Room(player, 0xaf, 0xfc9e1).door(Position.NorthW, DoorKind.Normal).door(Position.WestN, DoorKind.Normal),

        Room(player, 0xb0, 0xf8f6b).door(Position.InteriorW, DoorKind.Trap).door(Position.InteriorN, DoorKind.Trap).door(Position.InteriorS, DoorKind.SmallKey),
        Room(player, 0xb1, 0xfb3b7).door(Position.InteriorW, DoorKind.BigKey).door(Position.NorthE, DoorKind.SmallKey).door(Position.SouthE, DoorKind.Normal).door(Position.InteriorS, DoorKind.Normal),
        Room(player, 0xb2, 0xfb4ad).door(Position.North, DoorKind.BigKey).door(Position.InteriorS, DoorKind.Trap2).door(Position.InteriorE, DoorKind.TrapTriggerable).door(Position.EastN2, DoorKind.NormalLow2).door(Position.NorthE, DoorKind.Normal).door(Position.SouthW, DoorKind.Normal).door(Position.SouthE, DoorKind.Normal).door(Position.EastS, DoorKind.Normal),
        Room(player, 0xb3, 0xfb5e4).door(Position.InteriorW, DoorKind.SmallKey).door(Position.WestN2, DoorKind.NormalLow2).door(Position.NorthW, DoorKind.Normal).door(Position.WestS, DoorKind.Normal).door(Position.SouthW, DoorKind.Normal),
        Room(player, 0xb4, 0xfe807).door(Position.NorthW, DoorKind.BigKey),
        Room(player, 0xb5, 0xfeb07).door(Position.SouthW, DoorKind.Trap),
        Room(player, 0xb6, 0xfdd50).door(Position.NorthW, DoorKind.StairKey2).door(Position.InteriorE, DoorKind.TrapTriggerable).door(Position.SouthW, DoorKind.SmallKey).door(Position.InteriorW, DoorKind.SmallKey).door(Position.SouthE, DoorKind.Normal),
        Room(player, 0xb7, 0xfddcd).door(Position.SouthW, DoorKind.Normal),
        Room(player, 0xb8, 0x51b75).door(Position.NorthE, DoorKind.BigKey).door(Position.EastN, DoorKind.Normal),
        Room(player, 0xb9, 0x51d09).door(Position.EastN, DoorKind.SmallKey).door(Position.North, DoorKind.Normal).door(Position.South, DoorKind.Normal).door(Position.WestN, DoorKind.Normal),
        Room(player, 0xba, 0x51d57).door(Position.WestN, DoorKind.SmallKey).door(Position.NorthW, DoorKind.Trap).door(Position.InteriorN, DoorKind.Trap2),
        Room(player, 0xbb, 0xfd86b).door(Position.NorthW, DoorKind.Normal).door(Position.InteriorN, DoorKind.Normal).door(Position.InteriorS, DoorKind.Normal).door(Position.InteriorE, DoorKind.Normal).door(Position.EastN, DoorKind.Normal).door(Position.EastS, DoorKind.Normal),
        Room(player, 0xbc, 0xfd974).door(Position.InteriorS, DoorKind.SmallKey).door(Position.SouthE, DoorKind.SmallKey).door(Position.InteriorN, DoorKind.Trap).door(Position.SouthW, DoorKind.Bombable).door(Position.WestN, DoorKind.Normal).door(Position.WestS, DoorKind.Normal).door(Position.InteriorW, DoorKind.Normal).door(Position.NorthE, DoorKind.Normal),
        Room(player, 0xbe, 0xfca28).door(Position.SouthE, DoorKind.Trap).door(Position.EastS, DoorKind.SmallKey).door(Position.InteriorE, DoorKind.Normal),
        Room(player, 0xbf, 0xfca89).door(Position.WestS, DoorKind.SmallKey),

        Room(player, 0xc0, 0xf9026).door(Position.InteriorN, DoorKind.TrapTriggerable).door(Position.InteriorS, DoorKind.Trap2).door(Position.NorthE, DoorKind.StairKey),
        Room(player, 0xc1, 0xfb176).door(Position.InteriorS, DoorKind.SmallKey).door(Position.EastS, DoorKind.SmallKey).door(Position.InteriorN, DoorKind.TrapTriggerable).door(Position.InteriorW, DoorKind.TrapTriggerable).door(Position.SouthW, DoorKind.Normal).door(Position.EastN, DoorKind.Normal).door(Position.NorthE, DoorKind.Normal).door(Position.SouthE, DoorKind.Normal),
        Room(player, 0xc2, 0xfb0e7).door(Position.EastN, DoorKind.SmallKey).door(Position.WestS, DoorKind.SmallKey).door(Position.NorthW, DoorKind.Normal).door(Position.WestN, DoorKind.Normal).door(Position.East, DoorKind.Normal).door(Position.SouthE, DoorKind.Normal).door(Position.EastS, DoorKind.Normal).door(Position.NorthE, DoorKind.Normal),
        Room(player, 0xc3, 0xfb56c).door(Position.WestN, DoorKind.SmallKey).door(Position.InteriorN, DoorKind.Trap2).door(Position.InteriorH, DoorKind.Trap2).door(Position.InteriorS, DoorKind.TrapTriggerable).door(Position.NorthW, DoorKind.Normal).door(Position.West, DoorKind.Normal).door(Position.WestS, DoorKind.Normal),
        Room(player, 0xc4, 0xfec3f).door(Position.EastS, DoorKind.SmallKey),
        Room(player, 0xc5, 0xfece1).door(Position.WestS, DoorKind.SmallKey).door(Position.NorthW, DoorKind.Normal).door(Position.SouthW, DoorKind.Normal),
        Room(player, 0xc6, 0xfdf5c).door(Position.NorthW, DoorKind.SmallKey).door(Position.NorthE, DoorKind.Normal).door(Position.EastN, DoorKind.Normal).door(Position.EastS, DoorKind.Normal).door(Position.SouthW, DoorKind.Normal).door(Position.SouthE, DoorKind.Normal),
        Room(player, 0xc7, 0xfe0a1).door(Position.NorthW, DoorKind.Trap).door(Position.WestN, DoorKind.Normal).door(Position.WestS, DoorKind.Normal),
        Room(player, 0xc8, 0x51596).door(Position.SouthE, DoorKind.Trap),
        Room(player, 0xc9, 0x51e5a).door(Position.InteriorV, DoorKind.Trap).door(Position.North, DoorKind.Trap).door(Position.InteriorW, DoorKind.Normal).door(Position.InteriorE, DoorKind.Normal).door(Position.South, DoorKind.DungeonEntrance),
        Room(player, 0xcb, 0xfd630).door(Position.East, DoorKind.Dashable),
        Room(player, 0xcc, 0xfd783).door(Position.NorthE, DoorKind.BigKey).door(Position.NorthW, DoorKind.Bombable).door(Position.West, DoorKind.Dashable),
        Room(player, 0xce, 0xfcadd).door(Position.NorthE, DoorKind.Trap),

        Room(player, 0xd0, 0xf90de).door(Position.InteriorS, DoorKind.SmallKey).door(Position.InteriorN, DoorKind.Trap2),
        Room(player, 0xd1, 0xfb259).door(Position.InteriorS, DoorKind.Trap2).door(Position.NorthW, DoorKind.Normal).door(Position.NorthE, DoorKind.Normal).door(Position.InteriorE, DoorKind.Normal),
        Room(player, 0xd2, 0xfafd6).door(Position.NorthE, DoorKind.Trap),
        Room(player, 0xd5, 0xfee40).door(Position.SouthW, DoorKind.BombableEntrance).door(Position.NorthW, DoorKind.Normal),
        Room(player, 0xd6, 0xfe1cb).door(Position.NorthW, DoorKind.UnknownD6).door(Position.SouthE, DoorKind.DungeonEntrance).door(Position.NorthE, DoorKind.Normal),
        Room(player, 0xd8, 0x515ed).door(Position.NorthE, DoorKind.Trap).door(Position.InteriorE, DoorKind.TrapTriggerable).door(Position.EastS, DoorKind.Normal),
        Room(player, 0xd9, 0x5166f).door(Position.WestS, DoorKind.Trap).door(Position.InteriorS, DoorKind.Trap).door(Position.EastS, DoorKind.Trap),
        Room(player, 0xda, 0x5169d).door(Position.WestS, DoorKind.Trap),
        Room(player, 0xdb, 0xfd370).door(Position.East, DoorKind.Trap).door(Position.South, DoorKind.DungeonEntrance),
        Room(player, 0xdc, 0xfd4d1).door(Position.West, DoorKind.Normal),
        # Room(player, 0xdf, 0x52db4).door(Position.South, DoorKind.CaveEntrance),

        Room(player, 0xe0, 0xf9149).door(Position.InteriorN, DoorKind.Trap2).door(Position.InteriorW, DoorKind.Trap2).door(Position.NorthE, DoorKind.StairKey).door(Position.SouthW, DoorKind.DungeonEntrance),
        # Room(player, 0xe1, 0x5023c).door(Position.InteriorH2, DoorKind.NormalLow2).door(Position.SouthW, DoorKind.CaveEntrance),
        # Room(player, 0xe2, 0x50464).door(Position.InteriorH, DoorKind.Normal).door(Position.SouthE, DoorKind.CaveEntrance),
        # Room(player, 0xe3, 0x5032b).door(Position.InteriorS2, DoorKind.TrapLowE3).door(Position.InteriorE2, DoorKind.NormalLow2).door(Position.SouthW, DoorKind.CaveEntrance),
        # Room(player, 0xe4, 0x534b1).door(Position.SouthW2, DoorKind.CaveEntranceLow).door(Position.InteriorN, DoorKind.Normal).door(Position.East, DoorKind.Normal),
        # Room(player, 0xe5, 0x535ba).door(Position.West, DoorKind.Normal).door(Position.South, DoorKind.CaveEntrance),
        # Room(player, 0xe6, 0x532ee).door(Position.SouthW2, DoorKind.CaveEntranceLow).door(Position.EastN2, DoorKind.NormalLow),
        # Room(player, 0xe7, 0x533ce).door(Position.SouthE2, DoorKind.CaveEntranceLow).door(Position.WestN2, DoorKind.NormalLow),
        # Room(player, 0xe8, 0x529d3).door(Position.SouthE, DoorKind.CaveEntrance),
        # Room(player, 0xea, 0x531f5).door(Position.SouthW, DoorKind.CaveEntrance),
        # Room(player, 0xeb, 0x52e1a).door(Position.SouthE, DoorKind.CaveEntrance),
        # Room(player, 0xed, 0x52bec).door(Position.SouthE, DoorKind.CaveEntrance),
        # Room(player, 0xee, 0x52f76).door(Position.SouthE, DoorKind.CaveEntrance),
        # Room(player, 0xef, 0x52d37).door(Position.InteriorE, DoorKind.Trap2).door(Position.South, DoorKind.CaveEntrance),

        # Room(player, 0xf0, 0x5258a).door(Position.SouthW, DoorKind.CaveEntrance).door(Position.East2, DoorKind.NormalLow),
        # Room(player, 0xf1, 0x52703).door(Position.SouthE2, DoorKind.CaveEntranceLow).door(Position.West2, DoorKind.NormalLow),
        # Room(player, 0xf2, 0x5274a).door(Position.EastS, DoorKind.Normal).door(Position.SouthE, DoorKind.Normal).door(Position.SouthE, DoorKind.IncognitoEntrance),
        # Room(player, 0xf3, 0x52799).door(Position.WestS, DoorKind.Normal).door(Position.SouthW, DoorKind.Normal).door(Position.SouthW, DoorKind.IncognitoEntrance),
        # Room(player, 0xf4, 0x527d3).door(Position.EastS, DoorKind.Dashable).door(Position.SouthE, DoorKind.Normal).door(Position.SouthE, DoorKind.IncognitoEntrance),
        # Room(player, 0xf5, 0x52813).door(Position.WestS, DoorKind.Dashable).door(Position.SouthW, DoorKind.Normal).door(Position.SouthW, DoorKind.IncognitoEntrance),
        # Room(player, 0xf8, 0x528fe).door(Position.South, DoorKind.CaveEntrance),
        # Room(player, 0xf9, 0x5305a).door(Position.SouthW, DoorKind.CaveEntrance),
        # Room(player, 0xfa, 0x53165).door(Position.SouthW2, DoorKind.EntranceLow),
        # Room(player, 0xfb, 0x52ea4).door(Position.South, DoorKind.CaveEntrance),
        # Room(player, 0xfd, 0x52ab1).door(Position.South2, DoorKind.CaveEntranceLow),
        # Room(player, 0xfe, 0x52ff1).door(Position.SouthE2, DoorKind.CaveEntranceLow),
        # Room(player, 0xff, 0x52c9a).door(Position.InteriorW, DoorKind.Bombable).door(Position.InteriorE, DoorKind.Bombable).door(Position.SouthE, DoorKind.CaveEntrance),
    ]
    # fix some wonky things
    world.get_room(0x51, player).change(1, DoorKind.Normal)  # fix the dungeon changer
    world.get_room(0x60, player).swap(2, 4)  # puts the exit at pos 2 - enables pos 3
    world.get_room(0x61, player).swap(1, 6)  # puts the WN door at pos 1 - enables it
    world.get_room(0x61, player).swap(5, 6)  # puts the Incognito Entrance at the end, so it can be deleted
    world.get_room(0x62, player).swap(1, 4)  # puts the exit at pos 1 - enables pos 3
    world.get_room(0x77, player).swap(0, 1)  # fixes Hera Lobby Key Stairs - entrance now at pos 0
    if world.enemy_shuffle[player] != 'none':
        world.get_room(0xc0, player).change(0, DoorKind.Normal)  # fix this kill room if enemizer is on


class Room(object):
    def __init__(self, player, index, address):
        self.player = player
        self.index = index
        self.doorListAddress = address
        self.doorList = []
        self.modified = False

    def door(self, pos, kind):
        self.doorList.append((pos, kind))
        return self

    def change(self, list_idx, kind):
        prev = self.doorList[list_idx]
        self.doorList[list_idx] = (prev[0], kind)
        self.modified = True

    def mirror(self, list_idx):
        prev = self.doorList[list_idx]
        mirror_door = None
        for door in self.doorList:
            if door != prev:
                mirror_door = door
                break
        self.doorList[list_idx] = (mirror_door[0], mirror_door[1])
        self.modified = True

    def swap(self, idx1, idx2):
        item1 = self.doorList[idx1]
        item2 = self.doorList[idx2]
        self.doorList[idx1] = item2
        self.doorList[idx2] = item1
        self.modified = True

    def delete(self, list_idx):
        self.doorList[list_idx] = (Position.FF, DoorKind.FF)

    def address(self):
        return self.doorListAddress

    def rom_data(self):
        byte_array = []
        for pos, kind in self.doorList:
            byte_array.append(pos.value)
            byte_array.append(kind.value)
        return byte_array

    def __str__(self):
        return str(self.__unicode__())

    def __unicode__(self):
        return '%s' % self.index


class PairedDoor(object):
    def __init__(self, door_a, door_b):
        self.door_a = door_a
        self.door_b = door_b
        self.pair = True

    def address_a(self, world, player):
        d = world.check_for_door(self.door_a, player)
        return 0x13C000 + (door_pair_offset_table[d.roomIndex]+d.doorListPos)*2

    def address_b(self, world, player):
        d = world.check_for_door(self.door_b, player)
        return 0x13C000 + (door_pair_offset_table[d.roomIndex]+d.doorListPos)*2

    def rom_data_a(self, world, player):
        if not self.pair:
            return [0x00, 0x00]
        d = world.check_for_door(self.door_b, player)
        return [d.roomIndex, pos_map[d.doorListPos]]

    def rom_data_b(self, world, player):
        if not self.pair:
            return [0x00, 0x00]
        d = world.check_for_door(self.door_a, player)
        return [d.roomIndex, pos_map[d.doorListPos]]


pos_map = {
    0: 0x80, 1: 0x40, 2: 0x20, 3: 0x10
    # indices 4-7 not supported yet
}


@unique
class DoorKind(Enum):
    Normal = 0x00
    NormalLow = 0x02
    EntranceLow = 0x04
    Waterfall = 0x08
    DungeonEntrance = 0x0A
    DungeonEntranceLow = 0x0C
    CaveEntrance = 0x0E
    CaveEntranceLow = 0x10
    IncognitoEntrance = 0x12
    DungeonChanger = 0x14
    ToggleFlag = 0x16
    Trap = 0x18
    UnknownD6 = 0x1A
    SmallKey = 0x1C
    BigKey = 0x1E
    StairKey = 0x20
    StairKey2 = 0x22
    HauntedStairKey = 0x24  # not a real door, can see it in dark rooms when facing left
    StairKeyLow = 0x26
    Dashable = 0x28
    BombableEntrance = 0x2A
    Bombable = 0x2E
    BlastWall = 0x30
    Hidden = 0x32
    TrapTriggerable = 0x36
    Trap2 = 0x38
    NormalLow2 = 0x40
    TrapTriggerableLow = 0x44
    Warp = 0x46
    CaveEntranceLow08 = 0x48
    TrapLowE3 = 0x4A  # Maybe this is a toggle flag too?
    FF = 0xFF


@unique
class Position(Enum):
    NorthW = 0x00
    North = 0x10
    NorthE = 0x20
    NorthW2 = 0x30
    North2 = 0x40
    NorthE2 = 0x50
    InteriorW = 0x60
    InteriorV = 0x70
    InteriorE = 0x80
    InteriorW2 = 0x90
    InteriorV2 = 0xA0
    InteriorE2 = 0xB0
    SouthW = 0x61
    South = 0x71
    SouthE = 0x81
    SouthW2 = 0x91
    South2 = 0xA1
    SouthE2 = 0xB1
    WestN = 0x02
    West = 0x12
    WestS = 0x22
    WestN2 = 0x32
    West2 = 0x42
    # WestS2 = 0x52
    InteriorN = 0x62
    InteriorH = 0x72
    InteriorS = 0x82
    InteriorN2 = 0x92
    InteriorH2 = 0xA2
    InteriorS2 = 0xB2
    EastN = 0x63
    East = 0x73
    EastS = 0x83
    EastN2 = 0x93
    East2 = 0xA3
    # EastS2 = 0xB3
    FF = 0xFF


class TestWorld(object):
    def __init__(self):
        self.rooms = []


# python3 -c "from RoomData import offset_utility; offset_utility()"
# This utility was used to calculate the distance offsets
def offset_utility():
    world = TestWorld()
    create_rooms(world, 1)
    map = {}
    cntr = 1
    for room in world.rooms:
        map[room.index] = cntr
        cntr = cntr + len(room.doorList)
    string = ''
    for i in range(225):
        if i % 16 == 0:
            string = string + 'dw '
        if i not in map:
            string = string + '$0000,'
        else:
            string = string + hex(map[i]) + ','
    print(string)

# python3 -c "from RoomData import key_door_template_generator; key_door_template_generator()"
# This utility was used to help initialize the pairing data
def key_door_template_generator():
    world = TestWorld()
    create_rooms(world, 1)
    map = {}
    cntr = 1
    for room in world.rooms:
        string = 'dw '
        for door in room.doorList:
            if door[1] in [DoorKind.SmallKey, DoorKind.BigKey, DoorKind.SmallKey, DoorKind.Dashable, DoorKind.Bombable]:
                string = string + '$xxxx,'
            else:
                string = string + '$0000,'
        print(string[0:-1])


# python3 -c "from RoomData import door_address_list; door_address_list('/home/randall/kwyn/orig/z3.sfc')"
# python3 -c "from RoomData import door_address_list; door_address_list('path/to/rom.sfc')"
def door_address_list(rom):
    with open(rom, 'rb') as stream:
        rom_data = bytearray(stream.read())
    room_index = 0
    while room_index < 256:
        offset = room_index * 3
        address = rom_data[0x0F8000 + offset]
        address = address + 0x100 * rom_data[0x0F8000 + offset + 1]
        byte3 = rom_data[0x0F8000 + offset + 2]
        address = address + (byte3 << 16)
        if byte3 == 0x03:
            address = address - 0x020000
        elif byte3 == 0x0A:
            address = address - 0x058000
        elif byte3 == 0x1f:
            address = address - 0x100000
        else:
            print('Byte3 ' + hex(byte3))
            print('Address ' + hex(address))
            raise Exception('Bad address?')
        terminated = False
        while not terminated:
            marker = rom_data[address] + (rom_data[address+1] << 8)
            # if marker == 0xFFFF:
            #     print('Room '+ hex(room_index)+ ' terminated at '+ hex(address))
            #     terminated = True
            if marker == 0xFFF0:
                print(hex(room_index) + ': ' + hex(address+2))
                # print('Room ' + hex(room_index) + ' address: ' + hex(address+2))
                terminated = True
            else:
                address = address + 3
        room_index = room_index + 1
