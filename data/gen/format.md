Intensity Settings:

For each setting, a letter will be present or the letter x

nptl_ebvw_ci

- n: Normal Doors
- p: Spiral Stairs
- t: Straight Stairs
- l: In-Room Ladders
- e: Open Edges
- b: Lobbies (requires Normal Doors)
- v: Vanilla Traps
- w: Warps/Pits (Not Yet Implemented)
- c: Cave Interiors (Not Yet Implemented)
- i: Intratile Doors (Not Yet Implemented, May Never Be)

Examples with Optional Traps:

Intensity 1: npxx_xxxx_xx
Intensity 2: nptl_exxx_xx
Intensity 3: nptl_ebxx_xx

Examples with Vanilla Traps:

Intensity 1: npxx_xxvx_xx
Intensity 2: nptl_exvx_xx
Intensity 3: nptl_ebvx_xx

Cave Interiors will likely requires spiral stairs, normals, lobbies and pits. Edges may be optional.

nb (00, 10, 11)
p
t
l
e
v
96 custom intensities

Not yet
w
npbwc (xxxx0, 11111)
i?
maxes out at 416


Transform proposal into correct format:

Rules:

1. Change door names into directions. Redundant directions can be removed.
2. If a tile can link on of it's required door itself, then it doesn't need a hook for it: for example Moldorm 2. YOu'd think you'd need a staricase for the right hand staircase, but there's a staircase in the pit. All that's required is a north connection. Stairs not an option here because the north connection cannot be satisfied. 
   1. Some places like GT Big Chest tile, don't really need anything because there are other reachable tiles.
3. Some tiles can incorrectly identify need for a crystal switch before entering. Change flag to false.