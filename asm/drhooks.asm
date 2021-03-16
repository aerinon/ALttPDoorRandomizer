org $02b5c4 ; -- moving right routine 135c4
jsl WarpRight
org $02b665 ; -- moving left routine
jsl WarpLeft
org $02b713 ; -- moving down routine
jsl WarpDown
org $02b7b4 ; -- moving up routine
jsl WarpUp
org $02bd80
jsl AdjustTransition
nop

;turn off linking doors -- see .notRoomLinkDoor label in Bank02.asm
org $02b5a8 ; <- 135a8 - Bank02.asm : 8368 (LDA $7EC004 : STA $A0)
jsl CheckLinkDoorR
bcc NotLinkDoor1
org $02b5b6
NotLinkDoor1:
org $02b649 ; <- 135a8 - Bank02.asm : 8482 (LDA $7EC004 : STA $A0)
jsl CheckLinkDoorL
bcc NotLinkDoor2
org $02b657
NotLinkDoor2:


; Staircase routine
org $01c3d4 ; <- c3d4 - Bank01.asm : 9762-4 (Dungeon_DetectStaircase-> STA $A0 : LDA $063D, X)
jsl RecordStairType : nop
org $02a1e7 ;(PC: 121e7)
jsl SpiralWarp

org $0291b3 ; <- Bank02.asm : 3303 (LDA $0462 : AND.b #$04)
jsl SpiralPriorityHack : nop
org $0290f9 ; <- Bank02.asm : 3188 (LDA $0462 : AND.b #$04)
jsl SpiralPriorityHack : nop

org $029369 ; <- 11369 - Bank02.asm : 3610 (STX $0464 :  STY $012E)
jsl StraightStairsAdj : nop #2
org $029383 ; <- 11384 - Bank02.asm : 3629 (.walkingDownStaircase-> ADD $20 : STA $20)
jsl StraightStairsFix : nop
org $0293aa ; <- 113aa - Bank02.asm : 3653 (ADD $20 : STA $20)
jsl StraightStairsFix : nop
org $0293d1 ; <- 113d1 - Bank02.asm : 3683 (ADD $20 : STA $20 BRANCH_IOTA)
jsl StraightStairsFix : nop
org $029396 ; <- 11396 - Bank02.asm : 3641 (LDA $01C322, X)
jsl StraightStairLayerFix
org $02c06d ; <- Bank02.asm : 9874 (LDX $0418, CMP.b #$02)
jsl DoorToStraight : nop
org $02c092 ; STA $0020, Y : LDX #$00
jsl DoorToInroom : nop
org $02c0f8 ; CMP $02C034, X
jsl DoorToInroomEnd
org $02941a ; <- Bank02.asm : 3748 module 7.12.11 (LDA $0464 : BNE BRANCH_$11513 : INC $B0 : RTS)
jsl StraightStairsTrapDoor : rts
org $028b54 ; <- Bank02.asm : 2200 (JSL UseImplicitRegIndexedLocalJumpTable)
jsl InroomStairsTrapDoor

org $0289a0 ; JSL $0091C4
jsl QuadrantLoadOrderBeforeScroll
org $02bd9c ; JSL $0091C4
jsl QuadrantLoadOrderAfterScroll


; Graphics fix
org $02895d ; Bank 02 line 1812 (JSL Dungeon_LoadRoom : JSL Dungeon_InitStarTileChr : JSL $00D6F9 : INC $B0)
Splicer:
jsl GfxFixer
lda $b1 : beq .done
rts
nop #5
.done

org $01b618 ; Bank01.asm : 7963 Dungeon_LoadHeader (REP #$20 : INY : LDA [$0D], Y)
nop : jsl OverridePaletteHeader

org $02817e ; Bank02.asm : 414 (LDA $02811E, X)
jsl FixAnimatedTiles

org $028a06 ; Bank02.asm : 1941 Dungeon_ResetTorchBackgroundAndPlayer
JSL FixWallmasterLamp

org $00d377 ;Bank 00 line 3185
DecompDungAnimatedTiles:
org $00fda4 ;Bank 00 line 8882
Dungeon_InitStarTileCh:
org $00d6ae ;(PC: 56ae)
LoadTransAuxGfx:
org $00d739 ;
LoadTransAuxGfx_Alt:
org $00df5a ;(PC: 5f5a)
PrepTransAuxGfx:
org $0ffd65 ;(PC: 07fd65)
Dungeon_LoadCustomTileAttr:
org $01feb0
Dungeon_ApproachFixedColor:
;org $01fec1
;Dungeon_ApproachFixedColor_variable:
;org $a0f972 ; Rando version
;LoadRoomHook:
org $1bee74 ;(PC: 0dee74)
Palette_DungBgMain:
org $1bec77
Palette_SpriteAux3:
org $1becc5
Palette_SpriteAux2:
org $1bece4
Palette_SpriteAux1:


org $0DFA53
jsl.l LampCheckOverride
org $028046 ; <- 10046 - Bank02.asm : 217 (JSL EnableForceBlank) (Start of Module_LoadFile)
jsl.l OnFileLoadOverride
org $07A93F  ; < 3A93F - Bank07.asm 6548 (LDA $8A : AND.b #$40 - Mirror checks)
jsl.l MirrorCheckOverride

org $05ef47
Sprite_HeartContainer_Override: ;sprite_heart_upgrades.asm : 96-100 (LDA $040C : CMP.b #$1A : BNE .not_in_ganons_tower)
jsl GtBossHeartCheckOverride : bcs .not_in_ganons_tower
nop : stz $0dd0, X : rts
.not_in_ganons_tower


org $07a955 ; <- Bank07.asm : around 6564 (JP is a bit different) (STZ $05FC : STZ $05FD)
jsl BlockEraseFix
nop #2

org $02b82a
jsl FixShopCode

org $1ddeea ; <- Bank1D.asm : 286 (JSL Sprite_LoadProperties)
jsl VitreousKeyReset

org $1ed024 ;  f5024 sprite_guruguru_bar.asm : 27 (LDA $040C : CMP.b #$12 : INY #2
jsl GuruguruFix : bra .next
nop #3
.next

org $028fc9
nop #2 : jsl BlindAtticFix

org $028409
jsl SuctionOverworldFix

org $0ded04 ; <- rando's hooks.asm line 2192 - 6ED04 - equipment.asm : 1963 (REP #$30)
jsl DrHudDungeonItemsAdditions
;org $098638 ; rando's hooks.asm line 2192
;jsl CountChestKeys
org $06D192 ; rando's hooks.asm line 457
jsl CountAbsorbedKeys
; rando's hooks.asm line 1020
;org $05FC7E ; <- 2FC7E - sprite_dash_item.asm : 118 (LDA $7EF36F : INC A : STA $7EF36F)
;jsl CountBonkItem

org $019dbd ; <- Bank01.asm : 4465 of Object_Draw8xN (LDA $9B52, Y : STA $7E2000, X)
jsl CutoffEntranceRug : bra .nextTile : nop
.nextTile

;maybe set 02e2 to 0

org $0799de ; <- Bank07.asm : 4088 (LDA.b #$15 : STA $5D)
JSL StoreTempBunnyState
;
org $08c450 ; <- ancilla_receive_item.asm : 146-148 (STY $5D : STZ $02D8)
JSL RetrieveBunnyState : NOP

org $02d9ce ; <- Bank02.asm : Dungeon_LoadEntrance 10829 (STA $A0 : STA $048E)
JSL CheckDarkWorldSanc : NOP

org $01891e ; <- Bank 01.asm : 991 Dungeon_LoadType2Object (LDA $00 : XBA : AND.w #$00FF)
JSL RainPrevention : NOP #2

org $1edabf ; <- sprite_energy_ball.asm : 86-7 Sprite_EnergyBall (LDA.b #$10 : LDX.b #$00)
JSL StandardAgaDmg

; These two, if enabled together, have implications for vanilla BK doors in IP/Hera/Mire
; IPBJ is common enough to consider not doing this. Mire is not a concern for vanilla - maybe glitched modes
; Hera BK door back can be seen with Pot clipping - likely useful for no logic seeds

;Kill big key (1e) check for south doors
;org $1aa90
;DontCheck:
;bra .done
;nop #3
;.done

;Enable south facing bk graphic
;org $4e24
;dw $2ac8

org $01b714 ; PC: b714
OpenableDoors:
jsl CheckIfDoorsOpen
bcs .normal
rts
.normal
