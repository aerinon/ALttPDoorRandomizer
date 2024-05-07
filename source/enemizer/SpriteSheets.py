import logging
from collections import defaultdict
import RaceRandom as random

from source.dungeon.EnemyList import EnemySprite, SpriteType, enemy_names, sprite_translation, overlord_names
from source.dungeon.RoomConstants import *


class SpriteRequirement:
    def __init__(self, sprite, overlord=0):
        self.sprite = sprite
        self.overlord = overlord

        self.boss = False
        self.static = False  # npcs and do not randomize
        self.killable = True
        self.can_drop = True
        self.water_only = False
        self.dont_use = False
        self.ow_valid = True
        self.uw_valid = True
        self.can_randomize = True
        self.water_phobic = False

        self.groups = []
        self.sub_groups = defaultdict(list)

        self.excluded_rooms = set()
        self.allowed_rooms = set()

    def can_spawn_in_room(self, room_id):
        return room_id not in self.excluded_rooms and (self.sprite != EnemySprite.Wallmaster or room_id < 0x100)

    def no_drop(self):
        self.can_drop = False
        return self

    def sub_group(self, key, subs):
        if isinstance(subs, list):
            self.sub_groups[key].extend(subs)
        else:
            self.sub_groups[key].append(subs)
        return self

    def group(self, group_id):
        self.groups.append(group_id)
        return self

    def exclude(self, exclusions):
        self.excluded_rooms.update(exclusions)
        return self

    def allow(self, allowed):
        self.allowed_rooms.update(allowed)
        return self

    def affix(self):
        self.static = True
        self.killable = False
        self.can_drop = False
        return self

    def stasis(self):
        self.can_randomize = False
        return self

    def exalt(self):
        self.boss = True
        self.static = True  # not randomized by sprite sheet
        return self

    def immune(self):
        self.killable = False
        self.can_drop = False
        return self

    def immerse(self):
        self.water_only = True
        return self

    def aquaphobia(self):
        self.water_phobic = True
        return self

    def skip(self):
        self.dont_use = True
        return self

    def ow_skip(self):
        self.ow_valid = False
        return self

    def uw_skip(self):
        self.uw_valid = False
        return self

    def good_for_uw_water(self):
        return self.water_only and not self.static and not self.dont_use and self.uw_valid

    def good_for_shutter(self, forbidden):
        if self.sprite in forbidden:
            return False
        return self.killable and not self.static and not self.dont_use and self.uw_valid

    def good_for_key_drop(self, forbidden):
        return self.good_for_shutter(forbidden) and self.can_drop

    def __str__(self):
        return f'Req for {enemy_names[self.sprite] if self.overlord != 0x7 else overlord_names[self.sprite]}'


NoFlyingRooms = {0xd2, 0x10c}  # Mire 2, Mimic Cave
NoBeamosOrTrapRooms = {0xb, 0x16, 0x19, 0x1e, 0x26, 0x27, 0x36, 0x3f, 0x40, 0x42, 0x46, 0x49, 0x4b, 0x4e, 0x55, 0x57,
                       0x5f, 0x65, 0x6a, 0x74, 0x76, 0x7d, 0x7f, 0x83, 0x84, 0x85, 0x8c, 0x8d, 0x92, 0x95, 0x98, 0x9b,
                       0x9c, 0x9d, 0x9e, 0xa0, 0xaa, 0xaf, 0xb3, 0xba, 0xbb, 0xbc, 0xc6, 0xcb, 0xce, 0xd0, 0xd2, 0xd5,
                       0xd8, 0xdc, 0xdf, 0xe4, 0xe7, 0xee, 0xf9, 0xfd, 0x10c}
LenientTrapsForTesting = {0x16, 0x26, 0x3f, 0x40, 0x42, 0x46, 0x49, 0x4e, 0x57,
                          0x65, 0x6a, 0x74, 0x76, 0x7d, 0x98,
                          0x9e, 0xaf, 0xba, 0xc6, 0xcb, 0xce, 0xd2, 0xd5,
                          0xd8, 0xdf, 0xe4, 0xe7, 0xee, 0xfd, 0x10c}
# this will have to be dynamic if cave rooms are allowed in dungeons
WallmasterValidRooms = {
    HC_NorthCorridor, HC_SwitchRoom, HoulihanRoom, TR_CrystalRollerRoom,
    PalaceofDarkness0x09, PoD_StalfosTrapRoom, PoD_TurtleRoom, GT_EntranceRoom, Ice_EntranceRoom,
    GanonEvacuationRoute, HC_BombableStockRoom, Sanctuary, TR_Hokku_BokkuKeyRoom2, TR_BigKeyRoom, TurtleRock0x15,
    Swamp_SwimmingTreadmill, Hera_MoldormFallRoom, PoD_DarkMaze, PoD_BigChestRoom, PoD_Mimics_MovingWallRoom,
    GT_IceArmos, GT_FinalHallway, Ice_BombFloor_BariRoom, Ice_Pengator_BigKeyRoom, Tower_Agahnim, HC_KeyRatRoom,
    HC_SewerTextTriggerRoom, TR_WestExittoBalcony, TR_DoubleHokku_Bokku_BigchestRoom, Swamp_StatueRoom, Hera_BigChest,
    Swamp_EntranceRoom, Skull_Mothula, PoD_BigHubRoom, PoD_MapChest_FairyRoom, Ice_CompassRoom, Hera_HardhatBeetlesRoom,
    HC_SewerKeyChestRoom, Desert_Lanmolas, Swamp_PushBlockPuzzle_Pre_BigKeyRoom, Swamp_BigKey_BSRoom,
    Swamp_BigChestRoom, Swamp_MapChest_WaterFillRoom, Swamp_KeyPotRoom, Skull_GibdoKey_MothulaHoleRoom,
    PoD_BombableFloorRoom, PoD_SpikeBlock_ConveyorRoom, GT_TorchRoom2, Ice_StalfosKnights_ConveyorHellway,
    Ice_MapChestRoom, Tower_FinalBridgeRoom, HC_FirstDarkRoom, HC_6RopesRoom, Desert_TorchPuzzle_MovingWallRoom,
    TT_BigChestRoom, TT_JailCellsRoom, Swamp_CompassChestRoom, Skull_GibdoTorchPuzzleRoom, PoD_EntranceRoom,
    PoD_Warps_SouthMimicsRoom, GT_Mini_HelmasaurConveyorRoom, GT_MoldormRoom, Ice_Bomb_JumpRoom,
    IcePalaceCloneRoom_FairyRoom, HC_WestCorridor, HC_ThroneRoom, HC_EastCorridor, Desert_Popos2_BeamosHellwayRoom,
    Swamp_UpstairsPitsRoom, CastleSecretEntrance_UncleDeathRoom, Skull_KeyPot_TrapRoom, Skull_BigKeyRoom,
    Skull_BigChestRoom, Skull_FinalSectionEntranceRoom, PoD_HelmasaurKing, GT_SpikePitRoom, GT_Ganon_BallZ,
    GT_Gauntlet1_2_3, Ice_LonelyFirebar, Ice_HiddenChest_SpikeFloorRoom, HC_WestEntranceRoom, HC_MainEntranceRoom,
    HC_EastEntranceRoom, Desert_FinalSectionEntranceRoom, TT_WestAtticRoom, TT_EastAtticRoom,
    Swamp_HiddenChest_HiddenDoorRoom, Skull_CompassChestRoom, Skull_KeyChest_TrapRoom, PoD_RupeeRoom, GT_MimicsRooms,
    GT_LanmolasRoom, GT_Gauntlet4_5, Ice_PengatorsRoom, HC_SmallCorridortoJailCells, HC_BoomerangChestRoom,
    HC_MapChestRoom, Desert_BigChestRoom, Desert_MapChestRoom, Desert_BigKeyChestRoom, Swamp_WaterDrainRoom,
    Hera_EntranceRoom, GanonsTower, GT_EastSideCollapsingBridge_ExplodingWallRoom, GT_Winder_WarpMazeRoom,
    Ice_HiddenChest_BombableFloorRoom, Ice_BigSpikeTrapsRoom, HC_JailCellRoom, HC_NextToChasmRoom, HC_BasementChasmRoom,
    Desert_WestEntranceRoom, Desert_MainEntranceRoom, Desert_EastEntranceRoom, Hera_TileRoom, Eastern_FairyRoom,
    GT_BlockPuzzle_SpikeSkip_MapChestRoom, GT_EastandWestDownstairs_BigChestRoom, GT_Tile_TorchPuzzleRoom,
    IcePalace0x8E, Mire_Vitreous, Mire_FinalSwitchRoom, Mire_DarkBombWall_SwitchesRoom,
    Mire_DarkCaneFloorSwitchPuzzleRoom, GT_FinalCollapsingBridgeRoom, GT_Torches1Room, Mire_TorchPuzzle_MovingWallRoom,
    Mire_EntranceRoom, Eastern_EyegoreKeyRoom, GT_ManySpikes_WarpMazeRoom, GT_InvisibleFloorMazeRoom,
    GT_CompassChest_InvisibleFloorRoom, Ice_BigChestRoom, IcePalace0x9F, Mire_Pre_VitreousRoom, Mire_FishRoom,
    Mire_BridgeKeyChestRoom, MiseryMire0xA3, TR_Trinexx, GT_WizzrobesRooms, GT_MoldormFallRoom, Hera_FairyRoom,
    Eastern_StalfosSpawnRoom, Eastern_BigChestRoom, Eastern_MapChestRoom, TT_MovingSpikes_KeyPotRoom, TT_BlindTheThief,
    IcePalace0xAE, Ice_IceBridgeRoom, Tower_CircleofPots, Mire_HourglassRoom, Mire_SlugRoom, Mire_SpikeKeyChestRoom,
    TR_Pre_TrinexxRoom, TR_DarkMaze, TR_ChainChompsRoom, TR_MapChest_KeyChest_RollerRoom, Eastern_BigKeyRoom,
    Eastern_LobbyCannonballsRoom, Eastern_DarkAntifairy_KeyPotRoom, TT_Hellway, TT_ConveyorToilet, Ice_BlockPuzzleRoom,
    IcePalaceCloneRoom_SwitchRoom, Tower_DarkBridgeRoom, Mire_CompassChest_TileRoom, Mire_BigHubRoom, Mire_BigChestRoom,
    TR_FinalCrystalSwitchPuzzleRoom, TR_LaserBridge, TurtleRock0xC6, TR_TorchPuzzle,
    Eastern_EntranceRoom, UnknownRoom, TT_NorthWestEntranceRoom, TT_NorthEastEntranceRoom, Ice_HoletoKholdstareRoom,
    Tower_DarkMaze, Mire_ConveyorSlug_BigKeyRoom, Mire_Mire02_WizzrobesRoom, TR_LaserKeyRoom, TR_EntranceRoom,
    Eastern_PreArmosKnightsRoom, Eastern_CanonballRoom, EasternPalace, TT_Main_SouthWestEntranceRoom,
    TT_SouthEastEntranceRoom, Tower_EntranceRoom
}


def init_sprite_requirements():
    reqs = [
        SpriteRequirement(EnemySprite.Raven).no_drop().sub_group(3, [0x11, 0x19]).exclude(NoFlyingRooms),
        SpriteRequirement(EnemySprite.Vulture).no_drop().sub_group(2, 0x12).exclude(NoFlyingRooms),
        SpriteRequirement(EnemySprite.CorrectPullSwitch).affix().sub_group(3, [0x52, 0x53]),
        SpriteRequirement(EnemySprite.WrongPullSwitch).affix().sub_group(3, [0x52, 0x53]),
        SpriteRequirement(EnemySprite.Octorok).sub_group(2, [0xc, 0x18]),
        SpriteRequirement(EnemySprite.Moldorm).exalt().sub_group(2, 0x30),
        SpriteRequirement(EnemySprite.Octorok4Way).sub_group(2, 0xc),
        SpriteRequirement(EnemySprite.Cucco).immune().sub_group(3, [0x15, 0x50]).exclude(NoFlyingRooms),
        SpriteRequirement(EnemySprite.Buzzblob).sub_group(3, 0x11),
        SpriteRequirement(EnemySprite.Snapdragon).sub_group(0, 0x16).sub_group(2, 0x17),
        SpriteRequirement(EnemySprite.Octoballoon).no_drop().sub_group(2, 0xc).exclude(NoFlyingRooms),
        SpriteRequirement(EnemySprite.Hinox).sub_group(0, 0x16),
        SpriteRequirement(EnemySprite.Moblin).sub_group(2, 0x17),
        SpriteRequirement(EnemySprite.MiniHelmasaur).sub_group(1, 0x1e),
        SpriteRequirement(EnemySprite.AntiFairy).no_drop().sub_group(3, [0x52, 0x53])
        .exclude(NoFlyingRooms).exclude({0x40}),  # no anti-fairies in aga tower bridge room
        SpriteRequirement(EnemySprite.Wiseman).affix().sub_group(2, 0x4c),
        SpriteRequirement(EnemySprite.Hoarder).sub_group(3, 0x11).exclude({0x10c}),
        SpriteRequirement(EnemySprite.MiniMoldorm).sub_group(1, 0x1e),
        SpriteRequirement(EnemySprite.Poe).no_drop().sub_group(3, 0x15).exclude(NoFlyingRooms),
        SpriteRequirement(EnemySprite.Smithy).affix().sub_group(1, 0x1d).sub_group(3, 0x15),
        SpriteRequirement(EnemySprite.Statue).stasis().immune().sub_group(3, [0x52, 0x53]),
        SpriteRequirement(EnemySprite.CrystalSwitch).affix().sub_group(3, [0x52, 0x53]),
        SpriteRequirement(EnemySprite.SickKid).affix().sub_group(0, 0x51),
        SpriteRequirement(EnemySprite.Sluggula).sub_group(2, 0x25),
        SpriteRequirement(EnemySprite.WaterSwitch).affix().sub_group(3, 0x53),
        SpriteRequirement(EnemySprite.Ropa).sub_group(0, 0x16),
        SpriteRequirement(EnemySprite.RedBari).sub_group(0, 0x1f),
        SpriteRequirement(EnemySprite.BlueBari).sub_group(0, 0x1f),
        SpriteRequirement(EnemySprite.TalkingTree).affix().sub_group(3, [0x15, 0x1B]),
        SpriteRequirement(EnemySprite.HardhatBeetle).sub_group(1, 0x1e),
        SpriteRequirement(EnemySprite.Deadrock).sub_group(3, 0x10).exclude({0x7f, 0x10c}),
        SpriteRequirement(EnemySprite.DarkWorldHintNpc).affix(),   # no groups?
        SpriteRequirement(EnemySprite.AdultNpc).affix().sub_group(0, [0xe, 0x4f]),
        SpriteRequirement(EnemySprite.SweepingLady).affix().group(6),  # no sub groups?
        SpriteRequirement(EnemySprite.Lumberjacks).affix().sub_group(2, 0x4a),
        SpriteRequirement(EnemySprite.RaceGameLady).affix().group(6),
        SpriteRequirement(EnemySprite.FortuneTeller).affix().sub_group(0, 0x4b),
        SpriteRequirement(EnemySprite.ArgueBros).affix().sub_group(0, 0x4f),
        SpriteRequirement(EnemySprite.RupeePull).affix(),
        SpriteRequirement(EnemySprite.YoungSnitch).affix().group(6),
        SpriteRequirement(EnemySprite.Innkeeper).affix(),   # no groups?
        SpriteRequirement(EnemySprite.Witch).affix().sub_group(2, 0x7c),
        SpriteRequirement(EnemySprite.Waterfall).affix(),
        SpriteRequirement(EnemySprite.EyeStatue).affix(),
        SpriteRequirement(EnemySprite.Locksmith).affix().sub_group(3, 0x11),
        SpriteRequirement(EnemySprite.MagicBat).affix().sub_group(3, 0x1d),
        SpriteRequirement(EnemySprite.KidInKak).affix().group(6),
        SpriteRequirement(EnemySprite.OldSnitch).affix().group(6),
        SpriteRequirement(EnemySprite.Hoarder2).sub_group(3, 0x11).exclude({0x10c}),
        SpriteRequirement(EnemySprite.TutorialGuard).affix(),
        SpriteRequirement(EnemySprite.LightningGate).affix().sub_group(3, 0x3f),
        SpriteRequirement(EnemySprite.BlueGuard).sub_group(1, [0xd, 0x49]),
        SpriteRequirement(EnemySprite.GreenGuard).sub_group(1, 0x49),
        SpriteRequirement(EnemySprite.RedSpearGuard).sub_group(1, [0xd, 0x49]),
        SpriteRequirement(EnemySprite.BluesainBolt).sub_group(0, 0x46).sub_group(1, [0xd, 0x49]),
        SpriteRequirement(EnemySprite.UsainBolt).sub_group(1, [0xd, 0x49]),
        SpriteRequirement(EnemySprite.BlueArcher).sub_group(0, 0x48).sub_group(1, 0x49),
        SpriteRequirement(EnemySprite.GreenBushGuard).sub_group(0, 0x48).sub_group(1, 0x49),
        SpriteRequirement(EnemySprite.RedJavelinGuard).sub_group(0, 0x46).sub_group(1, 0x49),
        SpriteRequirement(EnemySprite.RedBushGuard).sub_group(0, 0x46).sub_group(1, 0x49),
        SpriteRequirement(EnemySprite.BombGuard).sub_group(0, 0x46).sub_group(1, 0x49),
        SpriteRequirement(EnemySprite.GreenKnifeGuard).sub_group(1, 0x49).sub_group(2, 0x13),
        SpriteRequirement(EnemySprite.Geldman).sub_group(2, 0x12).exclude({0x10c}),
        SpriteRequirement(EnemySprite.Toppo).immune().sub_group(3, 0x11),
        SpriteRequirement(EnemySprite.Popo).sub_group(1, 0x2c),
        SpriteRequirement(EnemySprite.Popo2).sub_group(1, 0x2c),
        SpriteRequirement(EnemySprite.ArmosStatue).sub_group(3, 0x10).exclude({0x10c}),
        SpriteRequirement(EnemySprite.KingZora).affix().sub_group(3, 0x44),
        SpriteRequirement(EnemySprite.ArmosKnight).exalt().sub_group(3, 0x1d),
        SpriteRequirement(EnemySprite.Lanmolas).exalt().sub_group(3, 0x31),
        SpriteRequirement(EnemySprite.FireballZora).immerse().no_drop().sub_group(2, [0xc, 0x18]),  # .uw_skip() test
        SpriteRequirement(EnemySprite.Zora).sub_group(2, 0xc).sub_group(3, 0x44),  # .uw_skip() test
        SpriteRequirement(EnemySprite.DesertStatue).affix().sub_group(2, 0x12),
        SpriteRequirement(EnemySprite.Crab).sub_group(2, 0xc),
        SpriteRequirement(EnemySprite.LostWoodsBird).affix().sub_group(2, 0x37).sub_group(3, 0x36),
        SpriteRequirement(EnemySprite.LostWoodsSquirrel).affix().sub_group(2, 0x37).sub_group(3, 0x36),
        SpriteRequirement(EnemySprite.SparkCW).immune().sub_group(0, 0x1f),
        SpriteRequirement(EnemySprite.SparkCCW).immune().sub_group(0, 0x1f),
        SpriteRequirement(EnemySprite.RollerVerticalUp).immune().sub_group(2, 0x27).exclude(NoBeamosOrTrapRooms),
        SpriteRequirement(EnemySprite.RollerVerticalDown).immune().sub_group(2, 0x27).exclude(NoBeamosOrTrapRooms),
        SpriteRequirement(EnemySprite.RollerHorizontalLeft).immune().sub_group(2, 0x27).exclude(NoBeamosOrTrapRooms),
        SpriteRequirement(EnemySprite.RollerHorizontalRight).immune().sub_group(2, 0x27).exclude(NoBeamosOrTrapRooms),
        SpriteRequirement(EnemySprite.Beamos).no_drop().sub_group(1, 0x2c).exclude(NoBeamosOrTrapRooms),
        SpriteRequirement(EnemySprite.MasterSword).affix().sub_group(2, 0x37).sub_group(3, 0x36),

        SpriteRequirement(EnemySprite.DebirandoPit).sub_group(0, 0x2f),  # skip
        SpriteRequirement(EnemySprite.Debirando).sub_group(0, 0x2f),     # skip
        SpriteRequirement(EnemySprite.ArcheryNpc).affix().sub_group(0, 0x4b),
        SpriteRequirement(EnemySprite.WallCannonVertLeft).affix().sub_group(0, 0x2f),
        SpriteRequirement(EnemySprite.WallCannonVertRight).affix().sub_group(0, 0x2f),
        SpriteRequirement(EnemySprite.WallCannonHorzTop).affix().sub_group(0, 0x2f),
        SpriteRequirement(EnemySprite.WallCannonHorzBottom).affix().sub_group(0, 0x2f),
        SpriteRequirement(EnemySprite.BallNChain).sub_group(0, 0x46).sub_group(1, 0x49),
        SpriteRequirement(EnemySprite.CannonTrooper).sub_group(0, 0x46).sub_group(1, 0x49),
        SpriteRequirement(EnemySprite.CricketRat).sub_group(2, [0x1c, 0x24]),
        SpriteRequirement(EnemySprite.Snake).sub_group(2, [0x1c, 0x24]),
        SpriteRequirement(EnemySprite.Keese).no_drop().sub_group(2, [0x1c, 0x24]),
        SpriteRequirement(EnemySprite.Leever).sub_group(0, 0x2f),
        SpriteRequirement(EnemySprite.FairyPondTrigger).affix().sub_group(3, 0x36),
        SpriteRequirement(EnemySprite.UnclePriest).affix().sub_group(0, [0x47, 0x51]),
        SpriteRequirement(EnemySprite.RunningNpc).affix().group(6),
        SpriteRequirement(EnemySprite.BottleMerchant).affix().group(6),
        SpriteRequirement(EnemySprite.Zelda).affix(),
        SpriteRequirement(EnemySprite.Grandma).affix().sub_group(0, 0x4b).sub_group(1, 0x4d).sub_group(2, 0x4a),
        SpriteRequirement(EnemySprite.Agahnim).exalt().sub_group(0, 0x55).sub_group(1, [0x1a, 0x3d]).sub_group(2, 0x42)
        .sub_group(3, 0x43),
        SpriteRequirement(EnemySprite.FloatingSkull).sub_group(0, 0x1f).exclude(NoFlyingRooms),
        SpriteRequirement(EnemySprite.BigSpike).sub_group(3, [0x52, 0x53]).no_drop(),
        SpriteRequirement(EnemySprite.FirebarCW).immune().sub_group(0, 0x1f),
        SpriteRequirement(EnemySprite.FirebarCCW).immune().sub_group(0, 0x1f),
        SpriteRequirement(EnemySprite.Firesnake).no_drop().sub_group(0, 0x1f),
        SpriteRequirement(EnemySprite.Hover).sub_group(2, 0x22),  # .exclude(NoFlyingRooms), might be okay now
        SpriteRequirement(EnemySprite.AntiFairyCircle).no_drop().sub_group(3, [0x52, 0x53]),
        SpriteRequirement(EnemySprite.GreenEyegoreMimic).sub_group(2, 0x2e),
        SpriteRequirement(EnemySprite.RedEyegoreMimic).sub_group(2, 0x2e),

        SpriteRequirement(EnemySprite.Kodongo).sub_group(2, 0x2a),
        # SpriteRequirement(EnemySprite.YellowStalfos).sub_group(0, 0x1f),  # doesn't spawn
        SpriteRequirement(EnemySprite.Mothula).exalt().sub_group(2, 0x38).sub_group(3, 0x52),
        SpriteRequirement(EnemySprite.SpikeBlock).immune().sub_group(3, [0x52, 0x53]).exclude(NoBeamosOrTrapRooms)
        .exclude({0x28}),  # why exclude sp entrance?
        SpriteRequirement(EnemySprite.Gibdo).sub_group(2, 0x23),
        SpriteRequirement(EnemySprite.Arrghus).exalt().sub_group(2, 0x39),
        SpriteRequirement(EnemySprite.Arrghi).exalt().sub_group(2, 0x39),
        SpriteRequirement(EnemySprite.Terrorpin).sub_group(2, 0x2a).exclude({0x10c}),  # probably fine in mimic now
        SpriteRequirement(EnemySprite.Blob).sub_group(1, 0x20),
        SpriteRequirement(EnemySprite.Wallmaster).immune().ow_skip().sub_group(2, 0x23)
        .allow(WallmasterValidRooms),
        SpriteRequirement(EnemySprite.StalfosKnight).sub_group(1, 0x20).exclude({0x10c}),
        SpriteRequirement(EnemySprite.HelmasaurKing).exalt().sub_group(2, 0x3a).sub_group(3, 0x3e),
        SpriteRequirement(EnemySprite.Bumper).immune().aquaphobia().sub_group(3, [0x52, 0x53]),
        SpriteRequirement(EnemySprite.LaserEyeLeft).affix().sub_group(3, [0x52, 0x53]),
        SpriteRequirement(EnemySprite.LaserEyeRight).affix().sub_group(3, [0x52, 0x53]),
        SpriteRequirement(EnemySprite.LaserEyeTop).affix().sub_group(3, [0x52, 0x53]),
        SpriteRequirement(EnemySprite.LaserEyeBottom).affix().sub_group(3, [0x52, 0x53]),
        SpriteRequirement(EnemySprite.Pengator).sub_group(2, 0x26),
        SpriteRequirement(EnemySprite.Kyameron).no_drop().immerse().sub_group(2, 0x22),
        SpriteRequirement(EnemySprite.Wizzrobe).sub_group(2, [0x25, 0x29]),
        SpriteRequirement(EnemySprite.Zoro).sub_group(1, 0x20),
        SpriteRequirement(EnemySprite.Babasu).sub_group(1, 0x20),
        SpriteRequirement(EnemySprite.GroveOstritch).affix().sub_group(2, 0x4e),
        SpriteRequirement(EnemySprite.GroveRabbit).affix(),
        SpriteRequirement(EnemySprite.GroveBird).affix().sub_group(2, 0x4e),
        SpriteRequirement(EnemySprite.Freezor).stasis().skip().sub_group(2, 0x26),
        SpriteRequirement(EnemySprite.Kholdstare).exalt().sub_group(2, 0x3c),
        SpriteRequirement(EnemySprite.KholdstareShell).exalt(),
        SpriteRequirement(EnemySprite.FallingIce).exalt().sub_group(2, 0x3c),
        SpriteRequirement(EnemySprite.BlueZazak).sub_group(2, 0x28),
        SpriteRequirement(EnemySprite.RedZazak).sub_group(2, 0x28),
        SpriteRequirement(EnemySprite.Stalfos).sub_group(0, 0x1f),
        SpriteRequirement(EnemySprite.GreenZirro).no_drop().sub_group(3, 0x1b).exclude(NoFlyingRooms),
        SpriteRequirement(EnemySprite.BlueZirro).no_drop().sub_group(3, 0x1b).exclude(NoFlyingRooms),
        SpriteRequirement(EnemySprite.Pikit).sub_group(3, 0x1b),
        SpriteRequirement(EnemySprite.CrystalMaiden).affix(),
        SpriteRequirement(EnemySprite.OldMan).affix().sub_group(0, 0x46).sub_group(1, 0x49).sub_group(2, 0x1c),
        SpriteRequirement(EnemySprite.PipeDown).affix(),
        SpriteRequirement(EnemySprite.PipeUp).affix(),
        SpriteRequirement(EnemySprite.PipeRight).affix(),
        SpriteRequirement(EnemySprite.PipeLeft).affix(),
        SpriteRequirement(EnemySprite.GoodBee).affix().sub_group(0, 0x1f),
        SpriteRequirement(EnemySprite.PurpleChest).affix().sub_group(3, 0x15),
        SpriteRequirement(EnemySprite.BombShopGuy).affix().sub_group(1, 0x4d),
        SpriteRequirement(EnemySprite.Kiki).affix().sub_group(3, 0x19),
        SpriteRequirement(EnemySprite.BlindMaiden).affix(),
        #     dialog tester.sub_group(1, 0x2c)
        SpriteRequirement(EnemySprite.BullyPinkBall).affix().sub_group(3, 0x14),
        # shop keepers in complex thing below
        SpriteRequirement(EnemySprite.Drunkard).affix().sub_group(0, 0x4f).sub_group(1, 0x4d).sub_group(2, 0x4a).
        sub_group(3, 0x50),
        SpriteRequirement(EnemySprite.Vitreous).exalt().sub_group(3, 0x3d),
        SpriteRequirement(EnemySprite.Catfish).affix().sub_group(2, 0x18),
        SpriteRequirement(EnemySprite.CutsceneAgahnim).affix().sub_group(0, 0x55).sub_group(1, 0x3d)
        .sub_group(2, 0x42).sub_group(3, 0x43),
        SpriteRequirement(EnemySprite.Boulder).affix().sub_group(3, 0x10),
        SpriteRequirement(EnemySprite.Gibo).sub_group(2, 0x28),
        SpriteRequirement(EnemySprite.Thief).immune().uw_skip().sub_group(0, [0xe, 0x15]),
        SpriteRequirement(EnemySprite.Medusa).affix(),
        SpriteRequirement(EnemySprite.FourWayShooter).affix(),
        SpriteRequirement(EnemySprite.Pokey).sub_group(2, 0x27),
        SpriteRequirement(EnemySprite.BigFairy).affix().sub_group(2, 0x39).sub_group(3, 0x36),
        SpriteRequirement(EnemySprite.Tektite).sub_group(3, 0x10),
        SpriteRequirement(EnemySprite.Chainchomp).immune().sub_group(2, 0x27),
        SpriteRequirement(EnemySprite.TrinexxRockHead).exalt().sub_group(0, 0x40).sub_group(3, 0x3f),
        SpriteRequirement(EnemySprite.TrinexxFireHead).exalt().sub_group(0, 0x40).sub_group(3, 0x3f),
        SpriteRequirement(EnemySprite.TrinexxIceHead).exalt().sub_group(0, 0x40).sub_group(3, 0x3f),
        SpriteRequirement(EnemySprite.Blind).exalt().sub_group(1, 0x2c).sub_group(2, 0x3b),
        SpriteRequirement(EnemySprite.Swamola).no_drop().sub_group(3, 0x19),
        SpriteRequirement(EnemySprite.Lynel).sub_group(3, 0x14),
        SpriteRequirement(EnemySprite.BunnyBeam).no_drop().ow_skip(),
        SpriteRequirement(EnemySprite.FloppingFish).uw_skip().immune(),
        SpriteRequirement(EnemySprite.Stal),
        SpriteRequirement(EnemySprite.Landmine).skip(),
        SpriteRequirement(EnemySprite.DiggingGameNPC).affix().sub_group(1, 0x2a),
        SpriteRequirement(EnemySprite.Ganon).exalt().sub_group(0, 0x21).sub_group(1, 0x41)
        .sub_group(2, 0x45).sub_group(3, 0x33),
        SpriteRequirement(EnemySprite.Faerie).immune(),
        SpriteRequirement(EnemySprite.FakeMasterSword).immune().sub_group(3, 0x11),
        SpriteRequirement(EnemySprite.MagicShopAssistant).affix().sub_group(0, 0x4b).sub_group(3, 0x5a),
        SpriteRequirement(EnemySprite.SomariaPlatform).affix().sub_group(2, 0x27),
        SpriteRequirement(EnemySprite.CastleMantle).affix().sub_group(0, 0x5d),
        SpriteRequirement(EnemySprite.GreenMimic).sub_group(1, 0x2c),
        SpriteRequirement(EnemySprite.RedMimic).sub_group(1, 0x2c),
        SpriteRequirement(EnemySprite.MedallionTablet).affix().sub_group(2, 0x12),

        # overlord requirements - encapsulated mostly in the required sheets
        SpriteRequirement(2, 7).affix().sub_group(2, 46),
        SpriteRequirement(3, 7).affix().sub_group(2, 46),
        SpriteRequirement(5, 7).affix().sub_group(0, 31),
        SpriteRequirement(6, 7).affix().sub_group(2, [28, 36]),
        SpriteRequirement(7, 7).affix(),
        SpriteRequirement(8, 7).affix().sub_group(1, 32),
        SpriteRequirement(9, 7).affix().sub_group(2, 35),
        SpriteRequirement(0xa, 7).affix().sub_group(3, 82),
        SpriteRequirement(0xb, 7).affix().sub_group(3, 82),
        SpriteRequirement(0x10, 7).affix().sub_group(2, 34),
        SpriteRequirement(0x11, 7).affix().sub_group(2, 34),
        SpriteRequirement(0x12, 7).affix().sub_group(2, 34),
        SpriteRequirement(0x13, 7).affix().sub_group(2, 34),
        SpriteRequirement(0x14, 7).affix(),
        SpriteRequirement(0x15, 7).affix().sub_group(2, [37, 41]),
        SpriteRequirement(0x16, 7).affix().sub_group(1, 32),
        SpriteRequirement(0x17, 7).affix().sub_group(0, 31),
        SpriteRequirement(0x18, 7).affix().sub_group(0, 31),
        SpriteRequirement(0x19, 7).affix(),
        SpriteRequirement(0x1a, 7).affix(),
    ]
    simple = {(r.sprite, r.overlord): r for r in reqs}
    shopkeeper = [
        SpriteRequirement(EnemySprite.Shopkeeper).affix().sub_group(0, 75).sub_group(2, 74).sub_group(3, 90)
        .allow({0xff, 0x112, 0x11f}),
        SpriteRequirement(EnemySprite.Shopkeeper).affix().sub_group(0, 75).sub_group(1, 77).sub_group(2, 74)
        .sub_group(3, 90).allow({0x10f, 0x110, 0x11f}),
        SpriteRequirement(EnemySprite.Shopkeeper).affix().sub_group(0, 79).sub_group(2, 74).sub_group(3, 90)
        .allow({0x118}),
        SpriteRequirement(EnemySprite.Shopkeeper).affix().sub_group(0, 14).sub_group(2, 74).sub_group(3, 90)
        .allow({0x123, 0x124}),
        SpriteRequirement(EnemySprite.Shopkeeper).affix().sub_group(0, 14).sub_group(2, 74).sub_group(3, 80)
        .allow({0x125, 0x100}),
        SpriteRequirement(EnemySprite.Shopkeeper).affix().sub_group(0, 21).allow({0x11e}),
    ]
    complex_r = {}
    for req in shopkeeper:
        for r in req.allowed_rooms:
            complex_r[r] = req
    simple[(EnemySprite.Shopkeeper, 0)] = complex_r
    return simple


# sheet 1 and 1c have group 4 modified from vanilla for murahdahla
vanilla_sheets = [
    (0x00, 0x49, 0x00, 0x00), (0x46, 0x49, 0x0C, 0x3F), (0x48, 0x49, 0x13, 0x3F), (0x46, 0x49, 0x13, 0x0E),
    (0x48, 0x49, 0x0C, 0x11), (0x48, 0x49, 0x0C, 0x10), (0x4F, 0x49, 0x4A, 0x50), (0x0E, 0x49, 0x4A, 0x11),
    (0x46, 0x49, 0x12, 0x00), (0x00, 0x49, 0x00, 0x50), (0x00, 0x49, 0x00, 0x11), (0x48, 0x49, 0x0C, 0x00),
    (0x00, 0x00, 0x37, 0x36), (0x48, 0x49, 0x4C, 0x11), (0x5D, 0x2C, 0x0C, 0x44), (0x00, 0x00, 0x4E, 0x00),

    (0x0F, 0x00, 0x12, 0x10), (0x00, 0x00, 0x00, 0x4C), (0x00, 0x0D, 0x17, 0x00), (0x16, 0x0D, 0x17, 0x1B),
    (0x16, 0x0D, 0x17, 0x14), (0x15, 0x0D, 0x17, 0x15), (0x16, 0x0D, 0x18, 0x19), (0x16, 0x0D, 0x17, 0x19),
    (0x16, 0x0D, 0x00, 0x00), (0x16, 0x0D, 0x18, 0x1B), (0x0F, 0x49, 0x4A, 0x11), (0x4B, 0x2A, 0x5C, 0x15),
    (0x16, 0x49, 0x17, 0x3F), (0x00, 0x00, 0x00, 0x15), (0x16, 0x0D, 0x17, 0x10), (0x16, 0x49, 0x12, 0x00),

    (0x16, 0x49, 0x0C, 0x11), (0x00, 0x00, 0x12, 0x10), (0x16, 0x0D, 0x00, 0x11), (0x16, 0x49, 0x0C, 0x00),
    (0x16, 0x0D, 0x4C, 0x11), (0x0E, 0x0D, 0x4A, 0x11), (0x16, 0x1A, 0x17, 0x1B), (0x4F, 0x34, 0x4A, 0x50),
    (0x35, 0x4D, 0x65, 0x36), (0x4A, 0x34, 0x4E, 0x00), (0x0E, 0x34, 0x4A, 0x11), (0x51, 0x34, 0x5D, 0x59),
    (0x4B, 0x49, 0x4C, 0x11), (0x2D, 0x00, 0x00, 0x00), (0x5D, 0x00, 0x12, 0x59), (0x00, 0x00, 0x00, 0x00),

    (0x00, 0x00, 0x00, 0x00), (0x00, 0x00, 0x00, 0x00), (0x00, 0x00, 0x00, 0x00), (0x00, 0x00, 0x00, 0x00),
    (0x00, 0x00, 0x00, 0x00), (0x00, 0x00, 0x00, 0x00), (0x00, 0x00, 0x00, 0x00), (0x00, 0x00, 0x00, 0x00),
    (0x00, 0x00, 0x00, 0x00), (0x00, 0x00, 0x00, 0x00), (0x00, 0x00, 0x00, 0x00), (0x00, 0x00, 0x00, 0x00),
    (0x00, 0x00, 0x00, 0x00), (0x00, 0x00, 0x00, 0x00), (0x00, 0x00, 0x00, 0x00), (0x00, 0x00, 0x00, 0x00),

    (0x47, 0x49, 0x2B, 0x2D), (0x46, 0x49, 0x1C, 0x52), (0x00, 0x49, 0x1C, 0x52), (0x5D, 0x49, 0x00, 0x52),
    (0x46, 0x49, 0x13, 0x52), (0x4B, 0x4D, 0x4A, 0x5A), (0x47, 0x49, 0x1C, 0x52), (0x4B, 0x4D, 0x39, 0x36),
    (0x1F, 0x2C, 0x2E, 0x52), (0x1F, 0x2C, 0x2E, 0x1D), (0x2F, 0x2C, 0x2E, 0x52), (0x2F, 0x2C, 0x2E, 0x31),
    (0x1F, 0x1E, 0x30, 0x52), (0x51, 0x49, 0x13, 0x00), (0x4F, 0x49, 0x13, 0x50), (0x4F, 0x4D, 0x4A, 0x50),

    (0x4B, 0x49, 0x4C, 0x2B), (0x1F, 0x20, 0x22, 0x53), (0x55, 0x3D, 0x42, 0x43), (0x1F, 0x1E, 0x23, 0x52),
    (0x1F, 0x1E, 0x39, 0x3A), (0x1F, 0x1E, 0x3A, 0x3E), (0x1F, 0x1E, 0x3C, 0x3D), (0x40, 0x1E, 0x27, 0x3F),
    (0x55, 0x1A, 0x42, 0x43), (0x1F, 0x1E, 0x2A, 0x52), (0x1F, 0x1E, 0x38, 0x52), (0x1F, 0x20, 0x28, 0x52),
    (0x1F, 0x20, 0x26, 0x52), (0x1F, 0x2C, 0x25, 0x52), (0x1F, 0x20, 0x27, 0x52), (0x1F, 0x1E, 0x29, 0x52),

    (0x1F, 0x2C, 0x3B, 0x52), (0x46, 0x49, 0x24, 0x52), (0x21, 0x41, 0x45, 0x33), (0x1F, 0x2C, 0x28, 0x31),
    (0x1F, 0x0D, 0x29, 0x52), (0x1F, 0x1E, 0x27, 0x52), (0x1F, 0x20, 0x27, 0x53), (0x48, 0x49, 0x13, 0x52),
    (0x0E, 0x1E, 0x4A, 0x50), (0x1F, 0x20, 0x26, 0x53), (0x15, 0x00, 0x00, 0x00), (0x1F, 0x00, 0x2A, 0x52),
    (0x00, 0x00, 0x00, 0x00), (0x00, 0x00, 0x00, 0x00), (0x00, 0x00, 0x00, 0x00), (0x00, 0x00, 0x00, 0x00),
    (0x00, 0x00, 0x00, 0x00), (0x00, 0x00, 0x00, 0x00), (0x00, 0x00, 0x00, 0x00), (0x00, 0x00, 0x00, 0x00),
    (0x00, 0x00, 0x00, 0x00), (0x00, 0x00, 0x00, 0x00), (0x00, 0x00, 0x00, 0x00), (0x00, 0x00, 0x00, 0x00),
    (0x00, 0x00, 0x00, 0x00), (0x00, 0x00, 0x00, 0x00), (0x00, 0x00, 0x00, 0x00), (0x00, 0x00, 0x00, 0x00),
    (0x00, 0x00, 0x00, 0x00), (0x00, 0x00, 0x00, 0x08), (0x5D, 0x49, 0x00, 0x52), (0x55, 0x49, 0x42, 0x43),
    (0x61, 0x62, 0x63, 0x50), (0x61, 0x62, 0x63, 0x50), (0x61, 0x62, 0x63, 0x50), (0x61, 0x62, 0x63, 0x50),
    (0x61, 0x62, 0x63, 0x50), (0x61, 0x62, 0x63, 0x50), (0x61, 0x56, 0x57, 0x50), (0x61, 0x62, 0x63, 0x50),
    (0x61, 0x62, 0x63, 0x50), (0x61, 0x56, 0x57, 0x50), (0x61, 0x56, 0x63, 0x50), (0x61, 0x56, 0x57, 0x50),
    (0x61, 0x56, 0x33, 0x50), (0x61, 0x56, 0x57, 0x50), (0x61, 0x62, 0x63, 0x50), (0x61, 0x62, 0x63, 0x50)
]

required_boss_sheets = {EnemySprite.ArmosKnight: 9, EnemySprite.Lanmolas: 11, EnemySprite.Moldorm: 12,
                        EnemySprite.HelmasaurKing: 21, EnemySprite.Arrghus: 20, EnemySprite.Mothula: 26,
                        EnemySprite.Blind: 32, EnemySprite.Kholdstare: 22, EnemySprite.Vitreous: 22,
                        EnemySprite.TrinexxRockHead: 23}


class SpriteSheet:
    def __init__(self, id, default_sub_groups):
        self.id = id
        self.sub_groups = list(default_sub_groups)
        self.locked = [False] * 4
        self.room_set = set()

    def dungeon_id(self):
        return self.id + 0x40

    def valid_sprite(self, requirement):
        if requirement.groups and self.id not in requirement.groups:
            return False
        for idx, sub in enumerate(self.sub_groups):
            if requirement.sub_groups[idx] and sub not in requirement.sub_groups[idx]:
                return False
        return True

    def lock_sprite_in(self, sprite):
        for i, options in sprite.sub_groups.items():
            self.locked[i] = len(options) > 0

    def add_sprite_to_sheet(self, groups, rooms=None):
        for idx, g in enumerate(groups):
            if g is not None:
                self.sub_groups[idx] = g
                self.locked[idx] = True
        if rooms is not None:
            self.room_set.update(rooms)

    def write_to_rom(self, rom, base_address):
        rom.write_bytes(base_address + self.id * 4, self.sub_groups)

    def __str__(self):
        return f'{self.id} => [{", ".join([str(x) for x in self.sub_groups])}]'


# convert to dungeon id
def did(n):
    return n + 0x40


def init_sprite_sheets(requirements):
    sheets = {id: SpriteSheet(id, def_sheet) for id, def_sheet in enumerate(vanilla_sheets)}
    # wait until bosses are randomized to determine which are randomized
    for sprite, sheet_num in required_boss_sheets.items():
        sheet = sheets[did(sheet_num)]  # convert to dungeon sheet id
        boss_sprite = requirements[(sprite, 0)]
        sheet.lock_sprite_in(boss_sprite)
    return sheets


def setup_required_dungeon_groups(sheets, data_tables):

    sheets[did(1)].add_sprite_to_sheet([70, 73, 28, 82], {0xe4, 0xf0})  # old man
    # various npcs
    sheets[did(5)].add_sprite_to_sheet([75, 77, 74, 90], {0xf3, 0x109, 0x10e, 0x10f, 0x110, 0x111, 0x112,
                                                          0x11a, 0x11c, 0x11f, 0x122})
    sheets[did(7)].add_sprite_to_sheet([75, 77, 57, 54], {0x8, 0x2c, 0x114, 0x115, 0x116})  # big fairies
    sheets[did(13)].add_sprite_to_sheet([81, None, None, None], {0x55, 0x102, 0x104})  # uncle, sick kid
    sheets[did(14)].add_sprite_to_sheet([71, 73, 76, 80], {0x12, 0x105, 0x10a})  # wisemen
    sheets[did(15)].add_sprite_to_sheet([79, 77, 74, 80], {0xf4, 0xf5, 0x101, 0x103, 0x106, 0x118, 0x119})  # more npcs
    sheets[did(18)].add_sprite_to_sheet([85, 61, 66, 67], {0x20, 0x30})  # aga alter, aga1
    sheets[did(24)].add_sprite_to_sheet([85, 26, 66, 67], {0xd})  # aga2
    sheets[did(34)].add_sprite_to_sheet([33, 65, 69, 51], {0})  # ganon
    sheets[did(40)].add_sprite_to_sheet([14, None, 74, 80], {0x124, 0x125, 0x126})  # fairy + rupee npcs
    sheets[did(9)].add_sprite_to_sheet([None, None, None, 29], {0xe3})  # magic bat
    sheets[did(28)].add_sprite_to_sheet([None, None, 38, 82], {0xe, 0x7e, 0x8e, 0x9e})  # freezors
    sheets[did(3)].add_sprite_to_sheet([93, None, None, None], {0x51})  # mantle
    sheets[did(42)].add_sprite_to_sheet([21, None, None, None], {0x11e})  # hype cave
    sheets[did(10)].add_sprite_to_sheet([47, None, 46, None], {0x5c, 0x75, 0xb9, 0xd9})  # cannonballs
    sheets[did(37)].add_sprite_to_sheet([31, None, 39, 82], {0x24, 0xb4, 0xb5, 0xc6, 0xc7, 0xd6})  # somaria platforms
    # not sure 31 is needed above

    free_sheet_reqs = [
        ([75, None, None, None], [0xff, 0x11f]),  # shopkeepers
        ([None, 77, None, 21], [0x121]),  # smithy
        ([None, None, None, 80], [0x108]),  # chicken house
        ([14, 30, None, None], [0x123]),  # mini moldorm (shutter door)
        ([None, None, 34, None], [0x36, 0x46, 0x66, 0x76]),  # pirogusu spawners
        ([None, 32, None, None], [0x9f]),  # babasu spawners
        ([31, None, None, None], [0x7f]),  # force baris
        ([None, None, 35, None], [0x39, 0x49]),  # wallmasters
        # bumpers - why the split - because of other requirements -
        ([None, None, None, (82, 83)], [0x17, 0x2a, 0x4c, 0x59, 0x67, 0x7e, 0x8b, 0xeb, 0xfb]),
        # crystal switches - split for some reason
        ([None, None, None, (82, 83)], [0xb, 0x13, 0x1b, 0x1e, 0x2a, 0x2b, 0x31, 0x5b, 0x6b, 0x77, 0x8b,
                                        0x91, 0x92, 0x9b, 0x9d, 0xa1, 0xab, 0xbf, 0xc4, 0xef]),
        # laser eyes - split for some reason
        ([None, None, None, (82, 83)], [0x13, 0x23, 0x96, 0xa5, 0xc5, 0xd5]),
        # statues - split for some reason
        ([None, None, None, (82, 83)], [0x26, 0x2b, 0x40, 0x4a, 0x6b, 0x7b]),
        ([None, None, None, 83], [0x43, 0x63, 0x87]),  # tile rooms

        # non-optional
        ([None, None, None, 82], [0x58, 0x8c, 0x10b]),  # pull switches
        ([None, None, (28, 36), 82], [0x2, 0x64]),  # pull switches (snakes)
        ([None, None, None, 82], [0x1a, 0x3d, 0x44, 0x5e, 0x7c, 0x95, 0xc3]),  # collapsing bridges
        ([None, None, None, 83], [0x3f, 0xce]),  # pull tongue
        ([None, None, None, 83], [0x35, 0x37, 0x76]),  # swamp drains
        ([None, None, 34, None], [0x28]),  # tektike forced? - spawn chest
        ([None, None, 37, None], [0x97]),  # wizzrobe spawner - in middle of room...

        # combined
        ([None, 32, None, (82, 83)], [0x3e]),  # babasu spawners + crystal switch
        ([None, 32, None, 83], [0x4]),  # zoro spawners + crystal switch + pull switch
        ([None, None, 35, 82], [0x56]),  # wallmaster + collasping bridge
        ([None, None, 35, (82, 83)], [0x57, 0x68]),  # wallmaster + statue and wallmaster + bumpers
        ([None, None, 34, 83], [0x76]),  # swamp drain + pirogusu spawners
        ([None, None, 35, 83], [0x8d]),  # wallmaster + tile room
        ([None, None, None, 83], [0xb6, 0xc1]),  # tile room + crystal switch

        # allow some sprites / increase odds:
        ([72, 73, None, None], []),  # allow for blue archer + greenbush
        ([None, 73, 19, None], []),  # allow for green knife guard
        ([None, None, 12, 68], []),  # increase odds for zora
        ([22, None, 23, None], []),  # increase odds for snapdragon
    ]

    data_tables.room_requirements = {}
    # find home for the free_sheet_reqs
    for pair in free_sheet_reqs:
        groups, room_list = pair
        for room in room_list:
            data_tables.room_requirements[room] = groups
        find_matching_sheet(groups, sheets, range(65, 124), room_list)


# RandomizeRooms(optionFlags);
    # roomCollection.LoadRooms()
    # roomCollection.RandomizeRoomSpriteGroups(spriteGroupCollection, optionFlags);
    # more stuff
sub_group_choices = {
    0: [22, 31, 47, 14],
    1: [44, 30, 32],  # 73, 13
    2: [12, 18, 23, 24, 28, 46, 34, 35, 39, 40, 38, 41, 36, 37, 42],
    3: [17, 16, 27, 20, 82, 83, 25]  # 25 for Swamola
}
# 70, 72 for guards
# 0: 72 specifically for BlueArcher/GreenBush (but needs combination)
# 0: 70 for guards but needs combination
# 2: 19 for green knife guard, but needs combination
# 3: 68 for Zora, but needs combination


def combine_req(sub_groups, requirement):
    for i in range(0, 4):
        if requirement.sub_groups[i]:
            if len(sub_groups[i]) == 0:
                sub_groups[i].update(requirement.sub_groups[i])
            else:
                if len(sub_groups[i].intersection(requirement.sub_groups[i])) == 0:
                    raise IncompatibleEnemyException
                sub_groups[i].intersection_update(requirement.sub_groups[i])


def setup_custom_enemy_sheets(custom_enemies, sheets, data_tables, sheet_range, uw=True):
    requirements = data_tables.sprite_requirements
    for room_id, enemy_map in custom_enemies.items():
        if uw:
            original_list = data_tables.uw_enemy_table.room_map[room_id]
        else:
            original_list = data_tables.ow_enemy_table[room_id]
        sub_groups_choices = [set(), set(), set(), set()]
        for idx, sprite in enumerate(original_list):
            if idx in enemy_map:
                key = (sprite_translation[enemy_map[idx]], 0)
                if key not in requirements:
                    continue
                req = requirements[key]
                try:
                    combine_req(sub_groups_choices, req)
                except IncompatibleEnemyException:
                    logging.getLogger('').warning(f'Incompatible enemy: {hex(room_id)}:{idx} {enemy_map[idx]}')
            else:
                sprite_secondary = 0 if sprite.sub_type != SpriteType.Overlord else sprite.sub_type
                key = (sprite.kind, sprite_secondary)
                if key not in requirements:
                    continue
                req = requirements[key]
                if isinstance(req, dict):
                    req = req[room_id]
                if req.static or not req.can_randomize:
                    try:
                        combine_req(sub_groups_choices, req)
                    except IncompatibleEnemyException:
                        raise IncompatibleEnemyException(f'Incompatible enemy: {hex(room_id)}:{idx} {str(req)}')
        sheet_req = [None if not x else tuple(x) for x in sub_groups_choices]
        find_matching_sheet(sheet_req, sheets, sheet_range, [room_id], True)


def randomize_underworld_sprite_sheets(sheets, data_tables, custom_enemies):
    setup_required_dungeon_groups(sheets, data_tables)

    setup_custom_enemy_sheets(custom_enemies, sheets, data_tables, range(65, 124), True)

    for num in range(65, 124):  # sheets 0x41 to 0x7B inclusive
        sheet = sheets[num]
        # if not sheet.locked[1] and num in [65, 66, 67, 68]:  # guard stuff, kind of
        #     sheet.locked[1] = True
        #     sheet.sub_groups[1] = random.choice([13, 73])

        free_slots = [idx for idx in range(0, 4) if not sheet.locked[idx]]
        while free_slots:
            choices = [c for c in data_tables.sheet_choices if all(slot in free_slots for slot in c.slots)]
            weights = [c.weight for c in choices]
            choice = random.choices(choices, weights, k=1)[0]
            for idx, val in choice.assignments.items():
                v = random.choice(val) if isinstance(val, list) else val
                sheet.sub_groups[idx] = v
                sheet.locked[idx] = True
            free_slots = [idx for idx in range(0, 4) if not sheet.locked[idx]]


def setup_required_overworld_groups(sheets):
    sheets[7].add_sprite_to_sheet([None, None, 74, None], {0x2})  # lumberjacks
    sheets[16].add_sprite_to_sheet([None, None, 18, 16], {0x3, 0x93})  # WDM (pre/post-Aga)
    sheets[7].add_sprite_to_sheet([None, None, None, 17], {0xA, 0x9A})  # DM Foothills? (pre/post-Aga)
    sheets[4].add_sprite_to_sheet([None, None, None, None], {0xF, 0x9F})  # Waterfall of wishing (pre/post-Aga)
    sheets[3].add_sprite_to_sheet([None, None, None, 14], {0x14, 0xA4})  # Graveyard (pre/post-Aga)
    sheets[1].add_sprite_to_sheet([None, None, 76, 0x3F], {0x1B, 0xAB})  # Hyrule Castle (pre/post-Aga)
    ## group 0 set to 0x48 for tutortial guards
    ## group 1 & 2 set for green knife guards (and probably normal green guard)
    ## group 3 set for lightning gate
    sheets[2].add_sprite_to_sheet([0x48, 0x49, 0x13, 0x3F], {})  # Hyrule Castle - rain state

    # Smithy/Race/Kak (pre/post-Aga)
    sheets[6].add_sprite_to_sheet([0x4F, 0x49, 0x4A, 0x50], {0x18, 0x22, 0x28, 0xA8, 0xB2, 0xB8})
    sheets[8].add_sprite_to_sheet([None, None, 18, None], {0x30, 0xC0})  # Desert (pre/post-Aga)
    sheets[10].add_sprite_to_sheet([None, None, None, 17], {0x3A, 0xCA})  # M-rock (pre/post-Aga)
    sheets[22].add_sprite_to_sheet([None, None, 24, None], {0x4F, 0xDF})  # Catfish (pre/post-Aga)
    sheets[21].add_sprite_to_sheet([21, None, None, 21], {0x62, 0xF2})  # Smith DW (pre/post-Aga)
    sheets[27].add_sprite_to_sheet([None, 42, None, None], {0x68, 0xF8})  # Dig Game (pre/post-Aga)
    sheets[13].add_sprite_to_sheet([None, None, 76, None], {0x16, 0xA6})  # Witch hut (pre/post-Aga)
    sheets[29].add_sprite_to_sheet([None, 77, None, 21], {0x69, 0xF9})  # VoO South (pre/post-Aga)
    sheets[15].add_sprite_to_sheet([None, None, 78, None], {0x2A, 0xBA})  # Haunted Grove (pre/post-Aga)
    sheets[17].add_sprite_to_sheet([None, None, None, 76], {0x6A, 0xFA})  # Stumpy (pre/post-Aga)
    sheets[12].add_sprite_to_sheet([None, None, 55, 54], {0x80, 0x110})  # Specials (pre/post-Aga)
    sheets[14].add_sprite_to_sheet([None, None, 12, 68], {0x81, 0x111})  # Zora's Domain (pre/post-Aga)
    sheets[26].add_sprite_to_sheet([15, None, None, None], {0x92})  # Lumberjacks post-Aga
    sheets[23].add_sprite_to_sheet([None, None, None, 25], {0x5E, 0xEE})  # PoD pre/post-Aga

    free_sheet_reqs = [
        [None, None, None, 0x14],  # bully+pink ball needs this
        [72, 73, None, None],  # allow for blue archer + green bush
        [None, 73, 19, None],  # allow for green knife guard
        [22, None, 23, None],  # increase odds for snapdragon
        [70, 73, None, None],  # guards group (ballnchain, redbush, redjav, cannon, bomb, bluesain
        [None, None, None, 0x15],  # an option for talking trees
        [None, None, None, 0x1B],  # an option for talking trees
    ]

    for group in free_sheet_reqs:
        find_matching_sheet(group, sheets, range(1, 64))


class NoMatchingSheetException(Exception):
    pass


class IncompatibleEnemyException(Exception):
    pass


def find_matching_sheet(groups, sheets, search_sheets, room_list=None, lock_match=False):
    possible_sheets = []
    found_match = False
    for num in search_sheets:
        if num in {6, 65, 69, 71, 78, 79, 82, 88, 98}:  # these are not useful sheets for randomization
            continue
        sheet = sheets[num]
        valid = True
        match = True
        for idx, value in enumerate(groups):
            if value is not None and sheet.locked[idx]:
                valid = False
                if (sheet.sub_groups[idx] not in value if isinstance(value, tuple)
                   else value != sheet.sub_groups[idx]):
                    match = False
            elif value is not None:
                match = False
        if match:
            found_match = True
            if lock_match and room_list is not None:
                sheet.room_set.update(room_list)
            break
        if valid:
            possible_sheets.append(sheet)
    if not found_match:
        if len(possible_sheets) == 0:
            raise NoMatchingSheetException
        chosen_sheet = random.choice(possible_sheets)
        chosen_groups = [(random.choice(g) if isinstance(g, tuple) else g) for g in groups]
        chosen_sheet.add_sprite_to_sheet(chosen_groups, room_list)


def randomize_overworld_sprite_sheets(sheets, data_tables, custom_enemies):
    setup_required_overworld_groups(sheets)

    setup_custom_enemy_sheets(custom_enemies, sheets, data_tables, range(1, 64), False)

    for num in range(1, 64):  # sheets 0x1 to 0x3F inclusive
        sheet = sheets[num]
        if num == 6:  # skip this group - it is locked for kakariko
            continue

        free_slots = [idx for idx in range(0, 4) if not sheet.locked[idx]]
        while free_slots:
            choices = [c for c in data_tables.sheet_choices if all(slot in free_slots for slot in c.slots)]
            weights = [c.weight for c in choices]
            choice = random.choices(choices, weights, k=1)[0]
            for idx, val in choice.assignments.items():
                v = random.choice(val) if isinstance(val, list) else val
                sheet.sub_groups[idx] = v
                sheet.locked[idx] = True
            free_slots = [idx for idx in range(0, 4) if not sheet.locked[idx]]


class SheetChoice:

    def __init__(self, slots, assignments, weight):
        self.slots = slots
        self.assignments = assignments
        self.weight = weight
