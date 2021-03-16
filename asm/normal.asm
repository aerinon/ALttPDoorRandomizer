WarpLeft:
    lda.l DRMode : beq .end
	lda $040c : cmp.b #$ff : beq .end
	lda $20 : ldx $aa
	jsr CalcIndex
	!add #$06 : ldy #$01 ; offsets in A, Y
	jsr LoadRoomHorz
.end
	jsr Cleanup
	rtl

WarpRight:
    lda.l DRMode : beq .end
	lda $040c : cmp.b #$ff : beq .end
	lda $20 : ldx $aa
	jsr CalcIndex
	!add #$12 : ldy #$ff ; offsets in A, Y
	jsr LoadRoomHorz
.end
	jsr Cleanup
	rtl

WarpUp:
    lda.l DRMode : beq .end
	lda $040c : cmp.b #$ff : beq .end
	lda $22 : ldx $a9
	jsr CalcIndex
	ldy #$02 ; offsets in A, Y
	jsr LoadRoomVert
.end
	jsr Cleanup
	rtl

; Checks if $a0 is equal to <Room>. If it is, opens its stonewall if it's there
macro StonewallCheck(Room)
    lda $a0 : cmp.b #<Room> : bne ?end
        lda.l <Room>*2+$7ef000 : ora #$80 : sta.l <Room>*2+$7ef000
    ?end
endmacro

WarpDown:
    lda.l DRMode : beq .end
	lda $040c : cmp.b #$ff : beq .end
	lda $22 : ldx $a9
	jsr CalcIndex
	!add #$0c : ldy #$ff ; offsets in A, Y
	jsr LoadRoomVert
    %StonewallCheck($43)
.end
	jsr Cleanup
	rtl

; carry set = use link door like normal
; carry clear = we are in dr mode, never use linking doors
CheckLinkDoorR:
    lda.l DRMode : bne +
        lda $7ec004 : sta $a0 ; what we wrote over
        sec : rtl
    + clc : rtl

CheckLinkDoorL:
    lda.l DRMode : bne +
        lda $7ec003 : sta $a0 ; what we wrote over
        sec : rtl
    + clc : rtl

TrapDoorFixer:
    lda $fe : and #$0038 : beq .end
    xba : asl #2 : sta $00
    stz $0468 : lda $068c : ora $00 : sta $068c
    .end
    stz $fe ; clear our fe here because we don't need it anymore
    rts

Cleanup:
    stz $047a
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
	lda $07 : jsr LookupNewRoom ; New room is in A, Room Data is in $00-$01
	lda $00 : cmp #$03 : bne .gtg
	jsr HorzEdge : pla : bcs .end
	sta $a0 : bra .end ; Restore normal room, abort (straight staircases and open edges can get in this routine)

	.gtg ;Good to Go!
	pla ; Throw away normal room (don't fill up the stack)
	lda $a0 : and.b #$0F : asl a : !sub $23 : !add $06 : sta $02
	ldy #$00 : jsr ShiftVariablesMainDir

    lda $01 : and #$80 : beq .normal
    ldy $06 : cpy #$ff : beq +
        lda $01 : jsr LoadEastMidpoint : bra ++
    + lda $01 : jsr LoadWestMidpoint
    ++ jsr PrepScrollToEdge : bra .scroll

    .normal
    jsr PrepScrollToNormal
	.scroll
	lda $01 : and #$40 : pha
	jsr ScrollY
	pla : beq .end
	    ldy #$06 : jsr ApplyScroll
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
	lda $07 : jsr LookupNewRoom ; New room is in A, Room Data is in $00-$01
	lda $00 : cmp #$03 : bne .gtg
	jsr VertEdge : pla : bcs .end
	sta $a0 : bra .end ; Restore normal room, abort (straight staircases and open edges can get in this routine)
	.gtg ;Good to Go!
	pla ; Throw away normal room (don't fill up the stack)
	lda $a0 : and.b #$F0 : lsr #3 : !sub $21 : !add $06 : sta $02

	lda $01 : and #$80 : beq .notEdge
	    ldy #$01 : jsr ShiftVariablesMainDir
        ldy $06 : cpy #$ff : beq +
            lda $01 : jsr LoadSouthMidpoint : bra ++
        + lda $01 : jsr LoadNorthMidpoint
	++ jsr PrepScrollToEdge : bra .scroll

    .notEdge
    lda $01 : and #$03 : cmp #$03 : bne .normal
        jsr ScrollToInroomStairs
        bra .end
    .normal
	ldy #$01 : jsr ShiftVariablesMainDir
    jsr PrepScrollToNormal
    .scroll
    lda $01 : and #$40 : pha
    jsr ScrollX
    pla : beq .end
        ldy #$00 : jsr ApplyScroll
    .end
    plb ; restore db register
    rts
}

LookupNewRoom: ; expects data offset to be in A
{
    rep #$30 : and #$00FF ;sanitize A reg (who knows what is in the high byte)
	sta $00 ; offset in 00
	lda $a2 : tax ; probably okay loading $a3 in the high byte
	lda.w DoorOffset,x : and #$00FF ;we only want the low byte
	asl #3 : sta $02 : !add $02 : !add $02 ;multiply by 24 (data size)
	!add $00 ; should now have the offset of the address I want to load
	tax : lda.w DoorTable,x : sta $00
	and #$00FF : sta $a0 ; assign new room
	sep #$30
	rts
}

; INPUTS-- Y: Direction Index , $02:  Shift Value
; Sets high bytes of various registers
ShiftVariablesMainDir:
{
	lda.w CoordIndex,y : tax
	lda $21,x : !add $02 : sta $21,x ; coordinate update
	lda.w CameraIndex,y : tax
	lda $e3,x : !add $02 : sta $e3,x ; scroll register high byte
	lda.w CamQuadIndex,y : tax
	lda $0605,x : !add $02 : sta $0605,x ; high bytes of these guys
	lda $0607,x : !add $02 : sta $0607,x
	lda $0601,x : !add $02 : sta $0601,x
	lda $0603,x : !add $02 : sta $0603,x
	rts
}

; Normal Flags should be in $01
ScrollToInroomStairs:
{
    jsr PrepScrollToInroomStairs
    ldy #$01 : jsr ShiftVariablesMainDir
    jsr ScrollX
    ldy #$00 : jsr ApplyScroll
    lda $a0 : and #$0f : cmp #$0f : bne +
        stz $e0 : stz $e2 ; special case camera fix
        lda #$1f : sta $e1 : sta $e3
    +
    rts
}

; Direction should be in $06, Shift Value (see above) in $02 and other info in $01
; Sets $02, $04, $05, $ee, $045e, $045f and things related to Y coordinate
PrepScrollToInroomStairs:
{
    lda $01 : and #$30 : lsr #3 : tay
    lda.w InroomStairsX,y : sta $04
    lda.w InroomStairsX+1,y : sta $05
    lda $06 : cmp #$ff : beq .south
        lda.w InroomStairsY+1,y : bne +
            inc $045f ; flag indicating special screen transition
            dec $02 ; shift variables further
            stz $aa
            lda $a8 : and #%11111101 : sta $a8
            stz $0613 ; North scroll target
            inc $0603 : inc $0607
            dec $0619 : dec $061b
        +
        lda.w InroomStairsY,y : !add #$20 : sta $20
        !sub #$38 : sta $045e
        lda $01 : and #$40 : beq +
            lda $20 : !add #$20 : sta $20
            stz $045f
        +
        dec $21
        %StonewallCheck($1b)
        bra ++
    .south
        lda.w InroomStairsY+1,y : beq +
            inc $045f ; flag indicating special screen transition
            inc $02 ; shift variables further
            lda #$02 : sta $aa
            lda $a8 : ora #%00000010 : sta $a8
            inc $0611 ; South scroll target
            dec $0603 : dec $0607
            inc $0619 : inc $061b
        +
        lda.w InroomStairsY,y : !sub #$20 : sta $20
        !add #$38 : sta $045e
        lda $01 : and #$40 : beq +
            lda $20 : !sub #$20 : sta $20
            stz $045f
        +
        inc $21
    ++
    lda $01 : and #$04 : lsr #2 : sta $ee : bne +
    	stz $0476
    + rts
}

; Target pixel should be in A, other info in $01
; Sets $04 $05 and $ee
PrepScrollToEdge:
{
    sta $04 : lda $01 : and #$20 : beq +
        lda #01
    + sta $05
    lda $01 : and #$10 : beq +
        lda #01
    + sta $ee : bne +
    	stz $0476
    + rts
}

; Normal Flags should be in $01
; Sets $04 $05 and $ee, and $fe
PrepScrollToNormal:
{
    lda $01 : sta $fe : and #$04 : lsr #2 : sta $ee ; trap door and layer
    bne +
    	stz $0476
    + stz $05 : lda #$78 : sta $04
    lda $01 : and #$03 : beq .end
        cmp #$02 : !bge +
            lda #$f8 : sta $04 : bra .end
        + inc $05
    .end rts
}

StraightStairsAdj:
{
    stx $0464 : sty $012e ; what we wrote over
    lda.l DRMode : beq +
        lda $045e : bne .toInroom
        jsr GetTileAttribute : tax
        lda $11 : cmp #$12 : beq .goingNorth
            lda $a2 : cmp #$51 : bne ++
                rep #$20 : lda #$0018 : !add $20 : sta $20 : sep #$20 ; special fix for throne room
                jsr GetTileAttribute : tax
            ++ lda.l StepAdjustmentDown, X : bra .end
;            lda $ee : beq .end
;                rep #$20 : lda #$ffe0 : !add $20 : sta $20 : sep #$20
        .goingNorth
            cpx #$00 : bne ++
            lda $a0 : cmp #$51 : bne ++
                lda #$36 : bra .end ; special fix for throne room
            ++ ldy $ee : cpy #$00 : beq ++
                inx
            ++ lda.l StepAdjustmentUp, X
        .end
        pha : lda $0462 : and #$04 : bne ++
            pla : !add #$f6 : pha
        ++ pla : !add $0464 : sta $0464
    + rtl
    .toInroom
    lda #$32 : sta $0464 : stz $045e
    rtl
}

GetTileAttribute:
{
    phk : pea.w .jslrtsreturn-1
    pea.w $02802c
    jml $02c11d ; mucks with x/y sets a to Tile Attribute, I think
    .jslrtsreturn
    rts
}

; 0 open edge
; 1 nrm door high
; 2 straight str
; 3 nrm door low
; 4 trap door high
; 5 trap door low   (none of these exist on North direction)
StepAdjustmentUp: ; really North Stairs
db $00, $f6, $1a, $18, $16, $38
StepAdjustmentDown: ; really South Stairs
db $d0, $f6, $10, $1a, $f0, $00

StraightStairsFix:
{
    lda.l DRMode : bne +
        !add $20 : sta $20 ;what we wrote over
    + rtl
}

StraightStairLayerFix:
{
    lda.l DRMode : beq +
        lda $ee : rtl
    + lda $01c322, x : rtl ; what we wrote over
}

DoorToStraight:
{
    pha
    lda.l DRMode : beq .skip
        pla : bne .end
        pha
        lda $a0 : cmp #$51 : bne .skip
        lda #$04 : sta $4e
    .skip pla
    .end ldx $0418 : cmp #$02 ;what we wrote over
    rtl
}

DoorToInroom:
{
    ldx $045e : bne .end
        sta $0020, y ; what we wrote over
    .end
    ldx #$00 ; what we wrote over
    rtl
}

DoorToInroomEnd:
{
    ldy $045e : beq .vanilla
    cmp $045e : bne .return
        stz $045e ; clear
    .return
    rtl
    .vanilla
    cmp $02c034, x ; what we wrote over
    rtl
}

StraightStairsTrapDoor:
{
    lda $0464 : bne +
        ; reset function
        .reset phk : pea.w .jslrtsreturn-1
        pea.w $02802c
        jml $028c73 ; $10D71 .reset label of Bank02
        .jslrtsreturn
        lda $0468 : bne ++
        lda $a0 : cmp.b #$ac : bne .animateTraps
        lda $0403 : and.b #$20 : bne .animateTraps
        lda $0403 : and.b #$10 : beq ++
            .animateTraps
            lda #$05 : sta $11
            inc $0468 : stz $068e : stz $0690
        ++ rtl
    + jsl Dungeon_ApproachFixedColor ; what we wrote over
    rtl
}

InroomStairsTrapDoor:
{
    lda $0200 : cmp #$05 : beq .reset
    lda $b0 : jml $008781 ; what we wrote over (essentially)
    .reset
    pla : pla : pla
    jsl StraightStairsTrapDoor_reset
    jml $028b15 ; just some RTS in bank 02
}