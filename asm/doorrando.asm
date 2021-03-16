!add = "clc : adc"
!addl = "clc : adc.l"
!sub = "sec : sbc"
!bge = "bcs"
!blt = "bcc"

; Free RAM notes
; Normal doors use $AB-AC for scrolling indicator
; Normal doors use $FE to store the trap door indicator
; Normal doors use $045e to store Y coordinate when transitioning to in-room stairs
; Normal doors use $045f to determine the order in which supertile quadrants are drawn
; Spiral doors use $045e to store stair type
; Gfx uses $b1 to for sub-sub-sub-module thing

; Hooks into various routines
incsrc drhooks.asm

;Main Code
org $278000 ;138000
db $44, $52 ;DR
DRMode:
dw 0
DRFlags:
dw 0
DRScroll:
db 0
OffsetTable:
dw -8, 8

incsrc normal.asm
incsrc scroll.asm
incsrc spiral.asm
incsrc gfx.asm
incsrc keydoors.asm
incsrc overrides.asm
incsrc edges.asm
incsrc math.asm
incsrc hudadditions.asm
incsrc dr_lobby.asm
warnpc $279C00

incsrc doortables.asm
warnpc $288000

; deals with own hooks
incsrc keydropshuffle.asm
