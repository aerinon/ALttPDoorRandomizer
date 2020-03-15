WarpLeft:
    lda DRMode : beq .end
	lda $040c : cmp.b #$ff : beq .end
	lda $20 : ldx $aa
	jsr CalcIndex
	!add #$06 : ldy #$01 ; offsets in A, Y
	jsr LoadRoomHorz
.end
	jsr Cleanup
	rtl

WarpRight:
    lda DRMode : beq .end
	lda $040c : cmp.b #$ff : beq .end
	lda $20 : ldx $aa
	jsr CalcIndex
	!add #$12 : ldy #$ff ; offsets in A, Y
	jsr LoadRoomHorz
.end
	jsr Cleanup
	rtl

WarpUp:
    lda DRMode : beq .end
	lda $040c : cmp.b #$ff : beq .end
	lda $22 : ldx $a9
	jsr CalcIndex
	ldy #$02 ; offsets in A, Y
	jsr LoadRoomVert
.end
	jsr Cleanup
	rtl

WarpDown:
    lda DRMode : beq .end
	lda $040c : cmp.b #$ff : beq .end
	lda $22 : ldx $a9
	jsr CalcIndex
	!add #$0c : ldy #$ff ; offsets in A, Y
	jsr LoadRoomVert
.end
	jsr Cleanup
	rtl

TrapDoorFixer:
    lda $fe : and #$0038 : beq .end
    xba : asl #2 : sta $00
    stz $0468 : lda $068c : ora $00 : sta $068c
    .end
    stz $fe ; clear our ab here because we don't need it anymore
    rts

Cleanup:
	inc $11
	lda $ef
	rts

;A needs be to the low coordinate, x needs to be either 0 for left,upper or non-zero for right,down
; This sets A (00,02,04) and stores half that at $04 for later use, (src door)
CalcIndex: ; A->low byte of Link's Coord, X-> Link's quadrant, DoorOffset x 2 -> A, DoorOffset -> $04 (vert/horz agnostic)
	cpx.b #00 : bne .largeDoor
	cmp.b #$d0 : bcc .smallDoor
	lda #$01 : bra .done ; Middle Door
	.smallDoor lda #$00 : bra .done
	.largeDoor lda #$02
	.done
	sta $04
	asl
	rts

; Y is an adjustment for main direction of travel
; A is a door table row offset
LoadRoomHorz:
{
    phb : phk : plb
	sty $06 : sta $07 : lda $a0 : pha ; Store normal room on stack
	lda $07 : jsr LookupNewRoom ; New room is in A, Room Data is in $00
	lda $01 : and.b #$80 : cmp #$80 : bne .gtg
	; jsr HorzEdge : pla : bcs .end
	pla
	sta $a0 : bra .end ; Restore normal room, abort (straight staircases and open edges can get in this routine)

	.gtg ;Good to Go!
	pla ; Throw away normal room (don't fill up the stack)
	lda $a0 : and.b #$0F : asl a : !sub $23 : !add $06 : sta $02
	ldy #$00 : jsr ShiftVariablesMainDir
	lda $aa : lsr : sta $07
	lda $a0 : and.b #$F0 : lsr #3 : !add $07 : !sub $21 : sta $02 : sta $03
	jsr ShiftLowCoord
	jsr ShiftQuad
	jsr ShiftCameraBounds
	ldy #$01 : jsr ShiftVariablesSubDir ; flip direction
	jsr SetupScrollIndicator
	lda $01 : sta $fe : and #$04 : lsr #2
	sta $ee
	lda $01 : and #$10 : beq .end : stz $0468
	.end
	plb ; restore db register
	rts
}

; Y is an adjustment for main direction of travel (stored at $06)
; A is a door table row offset (stored a $07)
LoadRoomVert:
{
    phb : phk : plb
	sty $06 : sta $07 : lda $a0 : pha ; Store normal room on stack
	lda $07 : jsr LookupNewRoom ; New room is in A, Room Data is in $00
	lda $01 : and.b #$80 : cmp #$80 : bne .gtg
	; jsr VertEdge : pla : bcs .end
	pla
	sta $a0 : bra .end ; Restore normal room, abort (straight staircases and open edges can get in this routine)
	.gtg ;Good to Go!
	pla ; Throw away normal room (don't fill up the stack)
	lda $a0 : and.b #$F0 : lsr #3 : !sub $21 : !add $06 : sta $02
	ldy #$01 : jsr ShiftVariablesMainDir
	lda $a0 : and.b #$0F : asl a : !add $a9 : !sub $23 : sta $02 : sta $03
	jsr ShiftLowCoord
	jsr ShiftQuad
	jsr ShiftCameraBounds
	ldy #$00 : jsr ShiftVariablesSubDir ; flip direction
	jsr SetupScrollIndicator
	lda $01 : sta $fe : and #$04 : lsr #2
	sta $ee
	.end
	plb ; restore db register
	rts
}

SetupScrollIndicator:
    lda $ab : and #$01 : asl : sta $ac
    lda $ab : and #$40 : clc : rol #3 : ora $ac : sta $ac
    lda $ab : and #$20 : asl #2 : sta $ab
    rts

LookupNewRoom: ; expects data offset to be in A
{
    rep #$30 : and #$00FF ;sanitize A reg (who knows what is in the high byte)
	sta $00 ; offset in 00
	lda $a2 : tax ; probably okay loading $a3 in the high byte
	lda DoorOffset,x : and #$00FF ;we only want the low byte
	asl #3 : sta $02 : !add $02 : !add $02 ;multiply by 24 (data size)
	!add $00 ; should now have the offset of the address I want to load
	tax : lda DoorTable,x : sta $00
	and #$00FF : sta $a0 ; assign new room
	sep #$30
	rts
}

; INPUTS-- Y: Direction Index , $02:  Shift Value
; Sets high bytes of various registers
ShiftVariablesMainDir:
{
	lda CoordIndex,y : tax
	lda $21,x : !add $02 : sta $21,x ; coordinate update
	lda CameraIndex,y : tax
	lda $e3,x : !add $02 : sta $e3,x ; scroll register high byte
	lda CamQuadIndex,y : tax
	lda $0605,x : !add $02 : sta $0605,x ; high bytes of these guys
	lda $0607,x : !add $02 : sta $0607,x
	lda $0601,x : !add $02 : sta $0601,x
	lda $0603,x : !add $02 : sta $0603,x
	rts
}

ShiftLowCoord:
{
	lda $01 : and.b #$03 ; high byte index
	jsr CalcOpposingShift
	lda $ab : and.b #$f0 : cmp.b #$20 : bne .lowDone
	lda OppCoordIndex,y : tax
	lda #$80 : !add $20,x : sta $20,x
	.lowDone
	rts
}

; expects A to be (0,1,2) (dest number) and (0,1,2) (src door number) to be stored in $04
; $ab will be set to a bitmask aaaa qxxf
; a - amount of adjust
; f - flag, if set, then amount is pos, otherwise neg.
; q - quadrant, if set, then quadrant needs to be modified
CalcOpposingShift:
{
	stz $ab : stz $ac ; set up
	cmp.b $04 : beq .noOffset ; (equal, no shifts to do)
	phy : tay ; reserve these
	lda $04 : tax : tya : !sub $04 : sta $04 : cmp.b #$00 : bpl .shiftPos
	lda #$40
	cpx.b #$01 : beq .skipNegQuad
	ora #$08
	.skipNegQuad
	sta $ab : lda $04 : cmp.b #$FE : beq .done ;already set $ab
	lda $ab : eor #$60
	bra .setDone

	.shiftPos
	lda #$41
	cpy.b #$01 : beq .skipPosQuad
	ora #$08
	.skipPosQuad
	sta $ab : lda $04 : cmp.b #$02 : bcs .done ;already set $ab
	lda $ab : eor #$60

	.setDone  sta $ab
	.done     ply
	.noOffset rts
}


ShiftQuad:
{
	lda $ab : and #$08 : beq .quadDone
	lda ShiftQuadIndex,y : tax ; X should be set to either 1 (vertical) or 2 (horizontal) (for a9,aa quadrant)
	lda $ab : and #$01 : beq .decQuad
	inc $02
	txa : sta $a8, x ; alter a9/aa
	bra .quadDone
	.decQuad
	dec $02
	lda #$00 : sta $a8, x ; alter a9/aa
	.quadDone rts
}

ShiftVariablesSubDir:
{
	lda CoordIndex,y : tax
	lda $21,x : !add $02 : sta $21,x ; coordinate update
	lda CameraIndex,y : tax
	lda $e3,x : !add $03 : sta $e3,x ; scroll register high byte
	lda CamQuadIndex,y : tax
	lda $0601,x : !add $02 : sta $0601,x
	lda $0605,x : !add $02 : sta $0605,x ; high bytes of these guys
	lda $0603,x : !add $03 : sta $0603,x
	lda $0607,x : !add $03 : sta $0607,x
	rts
}

ShiftCameraBounds:
{
	lda CamBoundIndex,y : tax ; should be 0 for horz travel (vert bounds) or 4 for vert travel (horz bounds)
	rep #$30
	lda $ab : and #$00f0 : asl #2 : sta $06
	lda $ab : and #$0001 : cmp #$0000 : beq .subIt
	lda $0618, x : !add $06 : sta $0618, x
	lda $061A, x : !add $06 : sta $061A, x
	sep #$30
	rts
	.subIt
	lda $0618, x : !sub $06 : sta $0618, x
	lda $061A, x : !sub $06 : sta $061A, x
	sep #$30
	rts
}

AdjustTransition:
{
	lda $ab : and #$01ff : beq .reset
	phy : ldy #$06 ; operating on vertical registers during horizontal trans
	cpx.b #$02 : bcs .horizontalScrolling
	ldy #$00  ; operate on horizontal regs during vert trans
	.horizontalScrolling
	cmp #$0008 : bcs +
	    pha : lda $ab : and #$0200 : beq ++
	        pla : bra .add
	    ++ pla : eor #$ffff : inc ; convert to negative
	    .add jsr AdjustCamAdd : ply : bra .reset
	+ lda $ab : and #$0200 : xba : tax
	lda.l OffsetTable,x : jsr AdjustCamAdd
	lda $ab : !sub #$0008 : sta $ab
	ply : bra .done
	.reset ; clear the $ab variable so to not disturb intra-tile doors
	stz $ab
	.done
	lda $00 : and #$01fc
	rtl
}

AdjustCamAdd:
    !add $00E2,y : sta $00E2,y : sta $00E0,y : rts