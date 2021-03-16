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
    !add $00E2,y : pha
    and #$01ff : cmp #$0111 : !blt +
        cmp #$01f8 : !bge ++
            pla : and #$ff10 : pha : bra +
        ++ pla : and #$ff00 : !add #$0100 : pha
    + pla : sta $00E2,y : sta $00E0,y : rts

; expects target quad in $05 (either 0 or 1) and target pixel in $04, target room should be in $a0
; $06 is either $ff or $01/02
; uses $00-$03 and $0e for calculation
; also set up $ac
ScrollY: ;change the Y offset variables
    lda $a0 : and.b #$f0 : lsr #3 : sta $0603 : inc : sta $0607

    lda $05 : bne +
        lda $603 : sta $00 : stz $01 : bra ++
    +   lda $607 : sta $00 : lda #$02 : sta $01
    ++ ; $01 now contains 0 or 2 and $00 contains the correct lat

    stz $0e
    rep #$30
    lda $00 : pha

    lda $e8 : and #$01ff : sta $02
    lda $04 : jsr LimitYCamera : sta $00
    jsr CheckRoomLayoutY : bcc +
        lda $00 : cmp #$0080 : !bge ++
            cmp #$0010 : !blt .cmpSrll
                lda #$0010 : bra .cmpSrll
        ++ cmp #$0100 : !bge .cmpSrll
            lda #$0100
    .cmpSrll sta $00

    ; figures out scroll amt
    + lda $00 : cmp $02 : bne +
        lda #$0000 : bra .next
    + !blt +
        !sub $02 : inc $0e : bra .next
    + lda $02 : !sub $00

    .next
    sta $ab
    jsr AdjustCameraBoundsY

    pla : sta $00
    sep #$30
    lda $04 : sta $20
    lda $00 : sta $21 : sta $0601 : sta $0605
    lda $01 : sta $aa
    lda $0e : asl : ora $ac : sta $ac
    lda $e9 : and #$01 : asl #2 : tax : lda $0603, x : sta $e9
    rts

LimitYCamera:
    cmp #$006c : !bge +
        lda #$0000 : bra .end
    + cmp #$017d : !blt +
        lda #$0110 : bra .end
    + !sub #$006c
    .end rts

CheckRoomLayoutY:
    jsr LoadRoomLayout ;switches to 8-bit
    cmp #$00 : beq .lock
    cmp #$07 : beq .free
    cmp #$01 : beq .free
    cmp #$04 : !bge .lock
    cmp #$02 : bne +
        lda $06 : cmp #$ff : beq .lock
    + cmp #$03 : bne .free
        lda $06 : cmp #$ff : bne .lock
    .free rep #$30 : clc : rts
    .lock rep #$30 : sec : rts

AdjustCameraBoundsY:
    jsr CheckRoomLayoutY : bcc .free

    ; layouts that are camera locked (quads only)
    lda $04 : and #$00ff : cmp #$007d : !blt +
        lda #$0088 : bra ++
    + cmp #$006d : !bge +
        lda #$0078 : bra ++
    + !add #$000b

    ; I think we no longer need the $02 variable
    ++ sta $02 : lda $04 : and #$0100 : !add $02 : bra .setBounds

    ; layouts where the camera is free
    .free lda $04 : cmp #$006c : !bge +
        lda #$0077 : bra .setBounds
    + cmp #$017c : !blt +
        lda #$0187 : bra .setBounds
    + !add #$000b
    .setBounds sta $0618 : inc #2 : sta $061a
    rts

LoadRoomLayout:
    lda $a0 : asl : !add $a0 : tax
    lda $1f8001, x : sta $b8
    lda $1f8000, x : sta $b7
    sep #$30
    ldy #$01 : lda [$b7], y : and #$1c : lsr #2
    rts

; expects target quad in $05 (either 0 or 1) and target pixel in $04, target room should be in $a0
; uses $00-$03 and $0e for calculation
; also set up $ac
ScrollX: ;change the X offset variables
    lda $a0 : and.b #$0f : asl : sta $060b : inc : sta $060f

    lda $05 : bne +
        lda $60b : sta $00 : stz $01 : bra ++
    +   lda $60f : sta $00 : lda #$01 : sta $01
    ++ ; $01 now contains 0 or 1 and $00 contains the correct long

    stz $0e ; pos/neg indicator
    rep #$30
    lda $00 : pha

    lda $e2 : and #$01ff : sta $02
    lda $04 : jsr LimitXCamera : sta $00
    jsr CheckRoomLayoutX : bcc +
        lda $00 : cmp #$0080 : !bge ++
            lda #$0000 : bra .cmpSrll
        ++ lda #$0100
    .cmpSrll sta $00

    ;figures out scroll amt
    + lda $00 : cmp $02 : bne +
        lda #$0000 : bra .next
    + !blt +
        !sub $02 : inc $0e : bra .next
    + lda $02 : !sub $00

    .next
    sta $ab : lda $04

    cmp #$0078 : !bge +
        lda #$007f : bra ++
    + cmp #$0178 : !blt +
        lda #$017f : bra ++
    + !add #$0007
    ++ sta $061c : inc #2 : sta $061e

    pla : sta $00
    sep #$30
    lda $04 : sta $22
    lda $00 : sta $23 : sta $0609 : sta $060d
    lda $01 : sta $a9
    lda $0e : asl : ora $ac : sta $ac
    lda $e3 : and #$01 : asl #2 : tax : lda $060b, x : sta $e3

    rts

LimitXCamera:
    cmp #$0079 : !bge +
        lda #$0000 : bra .end
    + cmp #$0178 : !blt +
        lda #$0178
    + !sub #$0078
    .end rts

CheckRoomLayoutX:
    jsr LoadRoomLayout ;switches to 8-bit
    cmp #$04 : !blt .lock
    cmp #$05 : bne +
        lda $06 : cmp #$ff : beq .lock
    + cmp #$06 : bne .free
        lda $06 : cmp #$ff : bne .lock
    .free rep #$30 : clc : rts
    .lock rep #$30 : sec : rts

ApplyScroll:
    rep #$30
    lda $ab : and #$01ff : sta $00
    lda $ab : and #$0200 : beq +
        lda $00e2, y : !add $00 : bra .end
    + lda $00e2, y : !sub $00
    .end
    sta $00e2, y
    sta $00e0, y
    stz $ab : sep #$30 : rts

QuadrantLoadOrderBeforeScroll:
    lda $045f : beq .end
    lda #$08 : sta $045c ; start with opposite quadrant row
    .end
    jsl $0091c4 ; what we overwrote
    rtl

QuadrantLoadOrderAfterScroll:
    lda $045f : beq .end
    stz $045c : stz $045f ; draw other row and clear flag
    .end
    jsl $0091c4 ; what we overwrote
    rtl