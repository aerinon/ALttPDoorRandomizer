!add = "clc : adc"
!sub = "sec : sbc"
!bge = "bcs"
!blt = "bcc"

; Free RAM notes
; Normal doors use $AB-AC for scrolling indicator
; Normal doors use $FE to store the trap door indicator
; Spiral doors use $045e to store stair type
; Gfx uses $b1 to for sub-sub-sub-module thing

; Hooks into various routines
incsrc drhooks.asm

;Main Code
org $278000 ;138000
incsrc normal.asm
incsrc spiral.asm
incsrc gfx.asm
incsrc keydoors.asm
incsrc overrides.asm
;incsrc edges.asm
;incsrc math.asm
warnpc $279000

; Data Section
org $279000
OffsetTable:
dw -8, 8
DRMode:
dw 0
DRFlags:
dw 0
DRScroll:
db 0

; Vert 0,6,0 Horz 2,0,8
org $279010
CoordIndex: ; Horizontal 1st
db 2, 0 ; Coordinate Index $20-$23
OppCoordIndex:
db 0, 2 ; Swapped coordinate Index $20-$23 (minor optimization)
CameraIndex: ; Horizontal 1st
db 0, 6 ; Camera Index $e2-$ea
CamQuadIndex: ; Horizontal 1st
db 8, 0 ; Camera quadrants $600-$60f
ShiftQuadIndex:
db 2, 1 ; see ShiftQuad func (relates to $a9,$aa)
CamBoundIndex: ; Horizontal 1st
db 0, 4 ; Camera Bounds $0618-$61f
OppCamBoundIndex: ; Horizontal 1st
db 4, 0 ; Camera Bounds $0618-$61f
CamBoundBaseLine: ; X camera stuff is 1st column todo Y camera needs more testing
dw $007f, $0077 ; Left/Top camera bounds when at edge or layout frozen
dw $0007, $000b ; Left/Top camera bounds when not frozen + appropriate low byte $22/$20 (preadj. by #$78/#$6c)
dw $00ff, $010b ; Right/Bot camera bounds when not frozen + appropriate low byte $20/$22
dw $017f, $0187 ; Right/Bot camera bound when at edge or layout frozen

incsrc doortables.asm
