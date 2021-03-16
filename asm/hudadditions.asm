DrHudOverride:
{
	jsl.l NewDrawHud
	jsr HudAdditions
	rtl
}

HudAdditions:
{
    lda.l DRFlags : and #$0008 : beq ++
		LDA.w #$28A4 : STA !GOAL_DRAW_ADDRESS
		lda $7EF423
        jsr HudHexToDec4DigitCopy
		LDX.b $05 : TXA : ORA.w #$2400 : STA !GOAL_DRAW_ADDRESS+2 ; draw 100's digit
		LDX.b $06 : TXA : ORA.w #$2400 : STA !GOAL_DRAW_ADDRESS+4 ; draw 10's digit
		LDX.b $07 : TXA : ORA.w #$2400 : STA !GOAL_DRAW_ADDRESS+6 ; draw 1's digit
		LDA.w #$2830 : STA !GOAL_DRAW_ADDRESS+8 ; draw slash
		LDA.l DRFlags : AND #$0100 : BNE +
        	lda $7EF33E
			jsr HudHexToDec4DigitCopy
			LDX.b $05 : TXA : ORA.w #$2400 : STA !GOAL_DRAW_ADDRESS+10 ; draw 100's digit
			LDX.b $06 : TXA : ORA.w #$2400 : STA !GOAL_DRAW_ADDRESS+12 ; draw 10's digit
			LDX.b $07 : TXA : ORA.w #$2400 : STA !GOAL_DRAW_ADDRESS+14 ; draw 1's digit
			BRA ++
		+ LDA.w #$2405 : STA !GOAL_DRAW_ADDRESS+10 : STA !GOAL_DRAW_ADDRESS+12 : STA !GOAL_DRAW_ADDRESS+14
    ++

	LDX $1B : BNE + : RTS : + ; Skip if outdoors
	ldx $040c : cpx #$ff : bne + : rts : + ; Skip if not in dungeon
	lda.l DRMode : bne + : rts : + ; Skip if not door rando
        phb : phk : plb
        lda $7ef364 : and.l $0098c0, x : beq +
            lda.w CompassBossIndicator, x : and #$00ff : cmp $a0 : bne +
                lda $1a : and #$0010 : beq +
                    lda #$345e : sta $7ec790 : bra .next
        + lda #$207f : sta $7ec790
    .next lda.w DRMode : and #$0002 : bne + : plb : rts : +
            lda $7ef36d : and #$00ff : beq +
                lda.w DungeonReminderTable, x : bra .reminder
            + lda #$207f
            .reminder sta $7ec702
            + lda.w DRFlags : and #$0004 : beq .restore
            lda $7ef368 : and.l $0098c0, x : beq .restore
                txa : lsr : tax

				lda.l GenericKeys : and #$00ff : bne +
                	lda $7ef4e0, x : jsr ConvertToDisplay : sta $7ec7a2
                	lda #$2830 : sta $7ec7a4
                +
                lda.w ChestKeys, x : jsr ConvertToDisplay : sta $7ec7a6
                ; todo 4b0 no longer in use

    .restore
    plb : rts
}

;column distance for BK/Smalls
HudOffsets:
;   none  hc     east   desert aga    swamp  pod    mire   skull  ice    hera   tt     tr     gt
dw $fffe, $0000, $0006, $0008, $0002, $0010, $000e, $0018, $0012, $0016, $000a, $0014, $001a, $001e

; offset from 1644
RowOffsets:
dw $0000, $0000, $0040, $0080, $0000, $0080, $0040, $0080, $00c0, $0040, $00c0, $0000, $00c0, $0000

ColumnOffsets:
dw $0000, $0000, $0000, $0000, $000a, $000a, $000a, $0014, $000a, $0014, $0000, $0014, $0014, $001e


DrHudDungeonItemsAdditions:
{
    jsl DrawHUDDungeonItems
    lda.l HUDDungeonItems : and #$ff : bne + : rtl : +
    lda.l DRMode : cmp #$02 : beq + : rtl : +

    phx : phy : php
    rep #$30

    lda.w #$24f5 : sta $1606 : sta $1610 : sta $161a : sta $1624
    sta $1644 : sta $164a : sta $1652 : sta $1662 : sta $1684 : sta $16c4
    ldx #$0000
    - sta $1704, x : sta $170e, x : sta $1718, x
    inx #2 : cpx #$0008 : !blt -

    lda !HUD_FLAG : and.w #$0020 : beq + : brl ++ : +
    lda HUDDungeonItems : and.w #$0007 : bne + : brl ++ : +
    	; bk symbols
		lda.w #$2811 : sta $1606 : sta $1610 : sta $161a : sta $1624
		; sm symbols
		lda.w #$2810 : sta $160a : sta $1614 : sta $161e : sta $16e4
    	; blank out stuff
    	lda.w #$24f5 : sta $1724

        ldx #$0002
        	- lda #$0000 : !addl RowOffsets,x : !addl ColumnOffsets, x : tay
        	lda.l DungeonReminderTable, x : sta $1644, y : iny #2
        	lda.w #$24f5 : sta $1644, y
        	lda $7ef368 : and.l $0098c0, x : beq + ; must have map
        		jsr BkStatus : sta $1644, y : bra .smallKey ; big key status
        	+ lda $7ef366 : and.l $0098c0, x : beq .smallKey
        		lda.w #$2826 : sta $1644, y
        	.smallKey
        	+ iny #2
			cpx #$001a : bne +
				tya : !add #$003c : tay
        	+ stx $00
        		txa : lsr : tax
        		lda.w #$24f5 : sta $1644, y
        		lda.l GenericKeys : and #$00FF : bne +
        		lda.l $7ef37c, x : and #$00FF : beq +
        			jsr ConvertToDisplay2 : sta $1644, y
        		+ iny #2 : lda.w #$24f5 : sta $1644, y
        		phx : ldx $00
        			lda $7ef368 : and.l $0098c0, x : beq + ; must have map
        				plx : sep #$30 : lda.l ChestKeys, x : sta $02
        				lda.l GenericKeys : bne +++
        					lda $02 : !sub $7ef4e0, x : sta $02
        				+++ lda $02
        				rep #$30
        				jsr ConvertToDisplay2 : sta $1644, y ; small key totals
        				bra .skipStack
        		+ plx
        		.skipStack iny #2
        		cpx #$000d : beq +
        			lda.w #$24f5 : sta $1644, y
        		+
        	ldx $00
            + inx #2 : cpx #$001b : bcs ++ : brl -
    ++
    lda !HUD_FLAG : and.w #$0020 : bne + : brl ++ : +
    lda HUDDungeonItems : and.w #$000c : bne + : brl ++ : +
        ; map symbols (do I want these) ; note compass symbol is 2c20
        lda.w #$2821 : sta $1606 : sta $1610 : sta $161a : sta $1624
        ; blank out a couple thing from old hud
        lda.w #$24f5 : sta $16e4 : sta $1724
        sta $160a : sta $1614 : sta $161e ; blank out sm key indicators
        ldx #$0002
        	- lda #$0000 ; start of hud area
        	!addl RowOffsets, x : !addl ColumnOffsets, x : tay
        	lda.l DungeonReminderTable, x : sta $1644, y
        	iny #2
        	lda.w #$24f5 : sta $1644, y ; blank out map spot
        	lda $7ef368 : and.l $0098c0, x : beq + ; must have map
				lda #$2826 : sta $1644, y ; check mark
			+ iny #2
            cpx #$001a : bne +
				tya : !add #$003c : tay
			+ lda $7ef364 : and.l $0098c0, x : beq + ; must have compass
                phx ; total chest counts
                    txa : lsr : tax
                    sep #$30
                    lda.l TotalLocations, x : !sub $7EF4BF, x : JSR HudHexToDec2DigitCopy
                    rep #$30
                    lda $06 : jsr ConvertToDisplay2 : sta $1644, y : iny #2
                    lda $07 : jsr ConvertToDisplay2 : sta $1644, y
                plx
                bra .skipBlanks
			+ lda.w #$24f5 : sta $1644, y : iny #2 : sta $1644, y
            .skipBlanks iny #2
            cpx #$001a : beq +
				lda.w #$24f5 : sta $1644, y ; blank out spot
            + inx #2 : cpx #$001b : !bge ++ : brl -
    ++
    plp : ply : plx : rtl
}

BkStatus:
    lda $7ef366 : and.l $0098c0, x : bne +++ ; has the bk already
         lda.l BigKeyStatus, x : bne ++
            lda #$2827 : rts ; 0/O for no BK
         ++ cmp #$0002 : bne +
            lda #$2420 : rts ; symbol for BnC
    + lda #$24f5 : rts ; black otherwise
    +++ lda #$2826 : rts ; check mark

ConvertToDisplay:
    and.w #$00ff : cmp #$000a : !blt +
        !add #$2553 : rts
    + !add #$2490 : rts

ConvertToDisplay2:
    and.w #$00ff : beq ++
        cmp #$000a : !blt +
            !add #$2553 : rts
        + !add #$2816 : rts
    ++ lda #$2827 : rts ; 0/O for 0 or placeholder digit ;2483

CountAbsorbedKeys:
    jsl IncrementSmallKeysNoPrimary : phx
    lda $040c : cmp #$ff : beq +
        lsr : tax
        lda $7ef4b0, x : inc : sta $7ef4b0, x
    + plx : rtl

;================================================================================
; 16-bit A, 8-bit X
; in:	A(b) - Byte to Convert
; out:	$04 - $07 (high - low)
;================================================================================
HudHexToDec4DigitCopy:
    LDY.b #$90
    -
        CMP.w #1000 : !BLT +
        INY
        SBC.w #1000 : BRA -
    +
    STY $04 : LDY #$90 ; Store 1000s digit & reset Y
    -
        CMP.w #100 : !BLT +
        INY
        SBC.w #100 : BRA -
    +
    STY $05 : LDY #$90 ; Store 100s digit & reset Y
    -
        CMP.w #10 : !BLT +
        INY
        SBC.w #10 : BRA -
    +
    STY $06 : LDY #$90 ; Store 10s digit & reset Y
    CMP.w #1 : !BLT +
    -
        INY
        DEC : BNE -
    +
    STY $07 ; Store 1s digit
RTS

;================================================================================
; 8-bit registers
; in:	A(b) - Byte to Convert
; out:	$06 - $07 (high - low)
;================================================================================
HudHexToDec2DigitCopy: ; modified
	PHY
		LDY.b #$00
		-
			CMP.b #10 : !BLT +
			INY
			SBC.b #10 : BRA -
		+
		STY $06 : LDY #$00 ; Store 10s digit and reset Y
		CMP.b #1 : !BLT +
		-
			INY
			DEC : BNE -
		+
		STY $07	; Store 1s digit
	PLY
RTS