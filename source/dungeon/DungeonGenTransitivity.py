from collections import defaultdict


# 'Ice Portal'

# Dead Ends
# 'Ice Antechamber', 'TR Refill', 'Mire Chest View', 'Ice Compass Room', 'Hera Tile Room', 'PoD Big Chest Balcony'

# Must Enters
# 'GT Big Key Room', 'GT Frozen Over', 'Thieves Lobby'

# Special
# 'Ice Bomb Drop'

# Neutral
# 'TR Lava Escape', 'Skull Star Pits', 'PoD Conveyor', 'Tower Dark Archers', 'Sewers Dark Cross'

# Other
# 'TR Torches', 'Sewers Pull Switch', 'Swamp Left Elbow', 'Ice Spike Room'

# pseuedo code

# Categorize into groups (Dead End, Must Enter, Portals, Neutral, Other, Special)
# Find valid starting points (dead ends aren't)
#   Bob's, Ice Cross S, Lava, Skull, PoD Cov, Pull Switch, Swamp Pull Statue
#   Portalable neutrals could be satisfied here without any loss of generality
    # Satisfy: Lava, Skull, Convey, Dark Cross
#   Prefer Must-Exit,Special over Other
#   Bob's -> Ice Cross -> Sewers Pull/Swamp Left Elbow
# Bob's Chosen
#   Satisfy: Tower Dark Archers
# How to Expand. Note Frozen, Lobby needs Torches, Spike connectors. No other options.
# Which do you connect to which? Best option is Spike Room > TT Lobby, but only because of lookahead
    # Recalc reachability?
# Must-enters now Either Ice Spike Stair or TR Torch south

# Choose Ice Spike Stair
# Avail hangers: ice spike stair + either frozen stair or lobby nx2/s
# Poor choice: 2 stairs avail
# Pull Switch or Swamp Left, either gets 1 S
#


def do_transitivity_check(sector_list, starting_point_list):
    door_sector_map = {d: s for s in sector_list for d in s.outstanding_doors}

    # satisfiable constraints
    must_enters = defaultdict(int)
    dead_ends = defaultdict(int)
    # todo: specials like ice cross

    for s in sector_list:
        pass
