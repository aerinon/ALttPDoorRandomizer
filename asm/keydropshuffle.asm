org $06926e ; <- 3126e - sprite_prep.asm : 2664 (LDA $0B9B : STA $0CBA, X)
jsl SpriteKeyPrep : nop #2

org $06d049 ; <- 35049 sprite_absorbable : 31-32 (JSL Sprite_DrawRippleIfInWater : JSR Sprite_DrawAbsorbable)
jsl SpriteKeyDrawGFX : bra + : nop : +

org $06d180
jsl BigKeyGet : bcs $07 : nop #5

org $06d18d ; <- 3518D - sprite_absorbable.asm : 274 (LDA $7EF36F : INC A : STA $7EF36F)
jsl KeyGet

org $06f9f3 ; bank06.asm : 6732 (JSL Sprite_LoadProperties)
jsl LoadProperties_PreserveItemMaybe




org $06d23a
Sprite_DrawAbsorbable:
org $1eff81
Sprite_DrawRippleIfInWater:
org $0db818
Sprite_LoadProperties:

org $288000 ;140000
ShuffleKeyDrops:
db 0
MultiClientFlags: ; 140001 -> stored in SRAM at 7ef33d
db 0

LootTable: ;PC: 140002
db $0e, $00, $24 ;; ice jelly key
db $13, $00, $24 ;; pokey 2
db $16, $00, $24 ;; swamp waterway pot
db $21, $00, $24 ;; key rat
db $35, $00, $24 ;; swamp trench 2 pot
db $36, $00, $24 ;; hookshot pot
db $37, $00, $24 ;; trench 1 pot
db $38, $00, $24 ;; pot row pot
db $39, $00, $24 ;; skull gibdo
db $3d, $00, $24 ;; gt minihelma
db $3e, $00, $24 ;; ice conveyor
db $3f, $00, $24 ;; ice hammer block ??? is this a dungeon secret?
db $43, $00, $24 ;; tiles 2 pot
db $53, $00, $24 ;; beamos hall pot
db $56, $00, $24 ;; skull west lobby pot
db $63, $00, $24 ;; desert tiles 1 pot
db $71, $00, $24 ;; boomerang guard
db $72, $00, $24 ;; hc map guard
db $7b, $00, $24 ;; gt star pits pot
db $80, $00, $32 ;; a big key (for the current dungeon)
db $8b, $00, $24 ;; gt conv cross block
db $9b, $00, $24 ;; gt dlb switch pot
db $9f, $00, $24 ;; ice many pots
db $99, $00, $24 ;; eastern eyegore
db $a1, $00, $24 ;; mire fishbone pot
db $ab, $00, $24 ;; tt spike switch pot
db $b0, $00, $24 ;; tower circle of pots usain
db $b3, $00, $24 ;; mire spikes pot
db $b6, $00, $24 ;; pokey 1
db $ba, $00, $24 ;; eastern dark pot
db $bc, $00, $24 ;; tt hallway pot
db $c0, $00, $24 ;; tower dark archer
db $c1, $00, $24 ;; mire glitchy jelly
db $ff, $00, $ff
;140068

KeyTable:
db $a0, $a0, $a2, $a3, $a4, $a5, $a6, $a7, $a8, $a9, $aa, $ab, $ac, $ad

SpriteKeyPrep:
{
    lda $0b9b : sta $0cba, x ; what we wrote over
    pha
        lda.l ShuffleKeyDrops : beq +
        phx
            ldx #$fd
            - inx #3 : lda.l LootTable, x : cmp #$ff : beq ++ : cmp $a0 : bne -
            inx : lda.l LootTable, x : sta !MULTIWORLD_SPRITEITEM_PLAYER_ID
            inx : lda.l LootTable, x
                plx : sta $0e80, x
                cmp #$24 : bne +++
                	lda $a0 : cmp #$80 : bne + : lda #$24
                +++ jsl PrepDynamicTile : bra +
        ++ plx : lda #$24 : sta $0e80, x
    + pla
    rtl
}

SpriteKeyDrawGFX:
{
    jsl Sprite_DrawRippleIfInWater
    pha
        lda.l ShuffleKeyDrops : bne +
            - pla
            phk : pea.w .jslrtsreturn-1
            pea.w $068014 ; an rtl address - 1 in Bank06
            jml Sprite_DrawAbsorbable
            .jslrtsreturn
            rtl
    + lda $0e80, x
    cmp #$24 : bne +
    	lda $a0 : cmp #$80 : bne - : lda #$24
    + jsl DrawDynamicTile ; see DrawHeartPieceGFX if problems
    cmp #$03 : bne +
        pha : lda $0e60, x : ora.b #$20 : sta $0E60, x : pla
    +
    jsl.l Sprite_DrawShadowLong

    pla : rtl
}

KeyGet:
{
    lda $7ef36f ; what we wrote over
    pha
        lda.l ShuffleKeyDrops : bne +
            - pla : rtl
        + ldy $0e80, x
        lda $a0 : cmp #$87 : bne +
        	jsr ShouldKeyBeCountedForDungeon : bcc -
        		jsl CountChestKeyLong : bra -
        + sty $00
		jsr KeyGetPlayer : sta !MULTIWORLD_ITEM_PLAYER_ID
		lda !MULTIWORLD_ITEM_PLAYER_ID : bne .receive
		phx
			lda $040c : lsr : tax
			lda $00 : CMP.l KeyTable, x : bne +
					- JSL.l FullInventoryExternal : jsl CountChestKeyLong : plx : pla : rtl
			+ cmp #$af : beq - ; universal key
			cmp #$24 : beq -   ; small key for this dungeon
		plx
		.receive
		jsl.l $0791b3 ; Player_HaltDashAttackLong
		jsl.l Link_ReceiveItem
    pla : dec : rtl
}

; Input Y - the item type
ShouldKeyBeCountedForDungeon:
{
	phx
		lda $040c : lsr : tax
		tya : cmp KeyTable, x : bne +
			- plx : sec : rts
		+ cmp #$24 : beq -
	plx : clc : rts
}

BigKeyGet:
{
    lda.l ShuffleKeyDrops : bne +
        - stz $02e9 : ldy.b #$32 ; what we wrote over
        phx : jsl Link_ReceiveItem : plx ; what we wrote over
        clc : rtl
    +
    ldy $0e80, x
    cpy #$32 : beq -
    + sec : rtl
}

KeyGetPlayer:
{
    phx
        ldx #$fd
        - inx #3 : lda.l LootTable, x : cmp #$ff : beq ++ : cmp $a0 : bne -
        ++ inx : lda.l LootTable, x
    plx
    rts
}

LoadProperties_PreserveItemMaybe:
{
    lda.l ShuffleKeyDrops : bne +
        jsl Sprite_LoadProperties : rtl
    + lda $0e80, x : pha
    jsl Sprite_LoadProperties
    pla : sta $0e80, x
    rtl
}
