HorzEdge:
    cpy #$ff : beq +
        jsr DetectWestEdge : ldy #$02 : bra ++
    + jsr DetectEastEdge
    ++ cmp #$ff : beq +
        sta $00 : asl : !add $00 : tax
        cpy #$ff : beq ++
            jsr LoadWestData : bra .main
        ++ jsr LoadEastData
        .main
        jsr LoadEdgeRoomHorz
        sec : rts
    + clc : rts

VertEdge:
    cpy #$ff : beq +
        jsr DetectNorthEdge : bra ++
    + jsr DetectSouthEdge
    ++ cmp #$ff : beq +
        sta $00 : asl : !add $00 : tax
        cpy #$ff : beq ++
            jsr LoadNorthData : bra .main
        ++ jsr LoadSouthData
        .main
        jsr LoadEdgeRoomVert
        sec : rts
    + clc : rts

LoadEdgeRoomHorz:
    lda $03 : sta $a0
    sty $06
    and.b #$0f : asl a : !sub $23 : !add $06 : sta $02
    ldy #$00 : jsr ShiftVariablesMainDir

    lda $04 : and #$80 : bne .edge
    lda $04 : sta $01 ; load up flags in $01
    jsr PrepScrollToNormal
    bra .scroll

    .edge
    lda $04 : and #$10 : beq +
       lda #$01
    + sta $ee ; layer stuff

    jsr MathHorz

    .scroll
    jsr ScrollY
    rts

LoadEdgeRoomVert:
    lda $03 : sta $a0
    sty $06
    and.b #$f0 : lsr #3 : !sub $21 : !add $06 : sta $02

    lda $04 : and #$80 : bne .edge
    lda $04 : sta $01 ; load up flags in $01
    and #$03 : cmp #$03 : beq .inroom
    ldy #$01 : jsr ShiftVariablesMainDir
    jsr PrepScrollToNormal
    bra .scroll

    .inroom
    jsr ScrollToInroomStairs
    rts

    .edge
    ldy #$01 : jsr ShiftVariablesMainDir
    lda $04 : and #$10 : beq +
       lda #$01
    + sta $ee ; layer stuff

    jsr MathVert
    lda $03

    .scroll
    jsr ScrollX
    rts


MathHorz:
    jsr MathStart : lda $20
    jsr MathMid : and #$0040
    jsr MathEnd
    rts

MathVert:
    jsr MathStart : lda $22
    jsr MathMid : and #$0020
    jsr MathEnd
    rts

MathStart:
    rep #$30
    lda $08 : and #$00ff : sta $00
    rts

MathMid:
    and #$01ff : !sub $00 : and #$00ff : sta $00
    ; nothing should be bigger than $a0 at this point

    lda $05 : and #$00f0 : lsr #4 : tax
    lda MultDivInfo, x : and #$00ff : tay
    lda $00 : jsr MultiplyByY : sta $02

    lda $07 : and #$00ff : jsr MultiplyByY : tax

    lda $05 : and #$000f : tay
    lda MultDivInfo, y : and #$00ff : tay
    lda $02 : jsr DivideByY : sta $00
    lda $0c : and #$00ff : sta $02
    lda $04
    rts

MathEnd:
     beq +
        lda #$0100
    + !add $02 : !add $00
    sta $04
    sep #$30
    rts

; don't need midpoint of edge Link is leaving (formerly in $06 - used by dir indicator)
; don't need width of edge Link is going to (currently in $0b)
LoadNorthData:
    lda NorthOpenEdge, x : sta $03 : inx ; target room
    lda NorthEdgeInfo, x : sta $07 ; needed for maths - (divide by 2 anyway)
    lda NorthOpenEdge, x : sta $04 : inx ; bit field
    lda NorthEdgeInfo, x : sta $08 ; needed for maths
    lda NorthOpenEdge, x : sta $05 ; ratio
    lda $04 : jsr LoadSouthMidpoint : inx ; needed now, and for nrml transition
    lda SouthEdgeInfo, x : sta $0b : inx ; probably not needed todo: remove
    lda SouthEdgeInfo, x : sta $0c ; needed for maths
    rts

LoadSouthMidpoint:
    and #$0f : sta $00 : asl : !add $00 : tax
    lda SouthEdgeInfo, x : sta $0a ; needed now, and for nrml transition
    rts

LoadSouthData:
    lda SouthOpenEdge, x : sta $03 : inx
    lda SouthEdgeInfo, x : sta $07
    lda SouthOpenEdge, x : sta $04 : inx
    lda SouthEdgeInfo, x : sta $08
    lda SouthOpenEdge, x : sta $05
    lda $04 : jsr LoadNorthMidpoint : inx
    lda NorthEdgeInfo, x : sta $0b : inx
    lda NorthEdgeInfo, x : sta $0c
    rts

LoadNorthMidpoint:
    and #$0f : sta $00 : asl : !add $00 : tax
    lda NorthEdgeInfo, x : sta $0a ; needed now, and for nrml transition
    rts

LoadWestData:
    lda WestOpenEdge, x : sta $03 : inx
    lda WestEdgeInfo, x : sta $07
    lda WestOpenEdge, x : sta $04 : inx
    lda WestEdgeInfo, x : sta $08
    lda WestOpenEdge, x : sta $05
    lda $04 : jsr LoadEastMidpoint : inx
    lda EastEdgeInfo, x : sta $0b : inx
    lda EastEdgeInfo, x : sta $0c
    rts

LoadEastMidpoint:
    and #$0f : sta $00 : asl : !add $00 : tax
    lda EastEdgeInfo, x : sta $0a ; needed now, and for nrml transition
    rts

LoadEastData:
    lda EastOpenEdge, x : sta $03 : inx
    lda EastEdgeInfo, x : sta $07
    lda EastOpenEdge, x : sta $04 : inx
    lda EastEdgeInfo, x : sta $08
    lda EastOpenEdge, x : sta $05
    lda $04 : jsr LoadWestMidpoint : inx
    lda WestEdgeInfo, x : sta $0b : inx
    lda WestEdgeInfo, x : sta $0c


LoadWestMidpoint:
    and #$0f : sta $00 : asl : !add $00 : tax
    lda WestEdgeInfo, x : sta $0a ; needed now, and for nrml transition
    rts


DetectNorthEdge:
    ldx #$ff
    lda $a2
    cmp #$82 : bne +
        lda $22 : cmp #$50 : bcs ++
            ldx #$01 : bra .end
        ++ ldx #$00 : bra .end
    + cmp #$83 : bne +
        ldx #$02 : bra .end
    + cmp #$84 : bne +
        lda $a9 : beq ++
            lda $22 : cmp #$78 : bcs +++
                ldx #$04 : bra .end
            +++ ldx #$05 : bra .end
        ++ lda $22 : cmp #$78 : bcs ++
            ldx #$03 : bra .end
        ++ ldx #$04 : bra .end
    + cmp #$85 : bne +
        ldx #$06 : bra .end
    + cmp #$db : bne +
        lda $a9 : beq ++
            lda $22 : beq ++
                ldx #$08 : bra .end
        ++ ldx #$07 : bra .end
    + cmp #$dc : bne .end
        lda $a9 : bne ++
            lda $22 : cmp #$b0 : bcs ++
                ldx #$09 : bra .end
        ++ ldx #$0a
    .end txa : rts

DetectSouthEdge:
    ldx #$ff
    lda $a2
    cmp #$72 : bne +
        lda $22 : cmp #$50 : bcs ++
            ldx #$01 : bra .end
        ++ ldx #$00 : bra .end
    + cmp #$73 : bne +
        ldx #$02 : bra .end
    + cmp #$74 : bne +
        lda $a9 : beq ++
            lda $22 : cmp #$78 : bcs +++
                ldx #$04 : bra .end
            +++ ldx #$05 : bra .end
        ++ lda $22 : cmp #$78 : bcs ++
            ldx #$03 : bra .end
        ++ ldx #$04 : bra .end
    + cmp #$75 : bne +
        ldx #$06 : bra .end
    + cmp #$cb : bne +
        lda $a9 : beq ++
            lda $22 : beq ++
                ldx #$08 : bra .end
        ++ ldx #$07 : bra .end
    + cmp #$cc : bne .end
        lda $a9 : bne ++
            lda $22 : cmp #$b0 : bcs ++
                ldx #$09 : bra .end
        ++ ldx #$0a
    .end txa : rts

DetectWestEdge:
    ldx #$ff
    lda $a2
    cmp #$65 : bne +
        ldx #$00 : bra .end
    + cmp #$74 : bne +
        ldx #$01 : bra .end
    + cmp #$75 : bne +
        ldx #$02 : bra .end
    + cmp #$82 : bne +
        lda $aa : beq ++
           ldx #$03 : bra .end
        ++ ldx #$04 : bra .end
    + cmp #$85 : bne +
            ldx #$05 : bra .end
    + cmp #$cc : bne +
        lda $aa : beq ++
            ldx #$06 : bra .end
        ++ ldx #$07 : bra .end
    + cmp #$dc : bne .end
        ldx #$08
    .end txa : rts

DetectEastEdge:
    ldx #$ff
    lda $a2
    cmp #$64 : bne +
        ldx #$00 : bra .end
    + cmp #$73 : bne +
        ldx #$01 : bra .end
    + cmp #$74 : bne +
        ldx #$02 : bra .end
    + cmp #$81 : bne +
        lda $aa : beq ++
           ldx #$04 : bra .end
        ++ ldx #$03 : bra .end
    + cmp #$84 : bne +
        ldx #$05 : bra .end
    + cmp #$cb : bne +
        lda $aa : beq ++
            ldx #$06 : bra .end
        ++ ldx #$07 : bra .end
    + cmp #$db : bne .end
        ldx #$08
    .end txa : rts



