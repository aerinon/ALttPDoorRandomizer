from BaseClasses import Entrance
import Rules
from OverworldGlitchRules import create_no_logic_connections

kikiskip_spots = [("Kiki Skip", "Spectacle Rock Cave (Bottom)", "Palace of Darkness Portal")]

mireheraswamp_spots = [
    ("Mire to Hera Clip", "Mire Torches Top", "Hera Portal"),
    ("Hera to Swamp Clip", "Mire Torches Top", "Swamp Portal"),
]

icepalace_spots = [("Ice Lobby Clip", "Ice Portal", "Ice Bomb Drop")]

thievesdesert_spots = [
    ("Thieves to Desert Clip", "Thieves Attic", "Desert West Portal"),
    ("Thieves to Desert Clip", "Thieves Attic", "Desert South Portal"),
    ("Thieves to Desert Clip", "Thieves Attic", "Desert East Portal"),
]

specrock_spots = [("Spec Rock Clip", "Spectacle Rock Cave (Peak)", "Spectacle Rock Cave (Top)")]

paradox_spots = [("Paradox Front Teleport", "Paradox Cave Front", "Paradox Cave Chest Area")]


# We need to make connectors at a separate time from the connections, because of how dungeons are linked to regions
kikiskip_connectors = [("Kiki Skip", "Spectacle Rock Cave (Bottom)", "Palace of Darkness Exit")]


mireheraswamp_connectors = [
    ("Mire to Hera Clip", "Mire Torches Top", "Tower of Hera Exit"),
    ("Mire to Hera Clip", "Mire Torches Top", "Swamp Palace Exit"),
]


thievesdesert_connectors = [
    ("Thieves to Desert Clip", "Thieves Attic", "Desert Palace Exit (West)"),
    ("Thieves to Desert Clip", "Thieves Attic", "Desert Palace Exit (South)"),
    ("Thieves to Desert Clip", "Thieves Attic", "Desert Palace Exit (East)"),
]

specrock_connectors = [
    ("Spec Rock Clip", "Spectacle Rock Cave (Peak)", "Spectacle Rock Cave Exit (Top)"),
    ("Spec Rock Clip", "Spectacle Rock Cave (Peak)", "Spectacle Rock Cave Exit"),
]


# Create connections between dungeons/locations
def create_hybridmajor_connections(world, player):
    for spots in [
        kikiskip_spots,
        mireheraswamp_spots,
        icepalace_spots,
        thievesdesert_spots,
        specrock_spots,
        paradox_spots,
    ]:
        create_no_logic_connections(player, world, spots)


# Turn dungeons into connectors
def create_hybridmajor_connectors(world, player):
    for connectors in [
        kikiskip_connectors,
        mireheraswamp_connectors,
        thievesdesert_connectors,
        specrock_connectors,
    ]:
        new_connectors = [(connector[0], connector[1], world.get_entrance(connector[2], player).connected_region) for connector in connectors]
        create_no_logic_connections(player, world, new_connectors)


# For some entrances, we need to fake having pearl, because we're in fake DW/LW.
# This creates a copy of the input state that has Moon Pearl.
def fake_pearl_state(state, player):
    if state.has("Moon Pearl", player):
        return state
    fake_state = state.copy()
    fake_state.prog_items["Moon Pearl", player] += 1
    return fake_state


# Sets the rules on where we can actually go using this clip.
# Behavior differs based on what type of ER shuffle we're playing.
def dungeon_reentry_rules(world, player, clip: Entrance, dungeon_region: str, dungeon_exit: str):
    fix_dungeon_exits = world.fix_palaceofdarkness_exit[player]
    fix_fake_worlds = world.fix_fake_world[player]

    dungeon_entrance = [r for r in world.get_region(dungeon_region, player).entrances if r.name != clip.name][0]
    if not fix_dungeon_exits:  # vanilla, simple, restricted, dungeonssimple; should never have fake worlds fix
        # Dungeons are only shuffled among themselves. We need to check SW, MM, and AT because they can't be reentered trivially.

        # entrance doesn't exist until you fire rod it from the other side
        if dungeon_entrance.name == "Skull Woods Final Section":
            Rules.set_rule(clip, lambda state: False)

        elif dungeon_entrance.name == "Misery Mire":
            if world.swords[player] == "swordless":
                Rules.add_rule(clip, lambda state: state.has_misery_mire_medallion(player))
            else:
                Rules.add_rule(clip, lambda state: state.has_sword(player) and state.has_misery_mire_medallion(player))

        elif dungeon_entrance.name == "Agahnims Tower":
            Rules.add_rule(
                clip,
                lambda state: state.has("Cape", player)
                or state.has_beam_sword(player)
                or state.has("Beat Agahnim 1", player),
            )

        # Then we set a restriction on exiting the dungeon, so you can't leave unless you got in normally.
        Rules.add_rule(world.get_entrance(dungeon_exit, player), lambda state: dungeon_entrance.can_reach(state))
    elif not fix_fake_worlds:  # full, dungeonsfull; fixed dungeon exits, but no fake worlds fix
        # Entry requires the entrance's requirements plus a fake pearl, but you don't gain logical access to the surrounding region.
        Rules.add_rule(clip, lambda state: dungeon_entrance.access_rule(fake_pearl_state(state, player)))
        # exiting restriction
        Rules.add_rule(world.get_entrance(dungeon_exit, player), lambda state: dungeon_entrance.can_reach(state))

    # Otherwise, the shuffle type is lean, lite, crossed, or insanity; all of these do not need additional rules on where we can go,
    # since the clip links directly to the exterior region.


def underworld_glitches_rules(world, player):
    # Ice Palace Entrance Clip, needs bombs or cane of somaria to exit bomb drop room
    Rules.add_rule(
        world.get_entrance("Ice Bomb Drop SE", player),
        lambda state: state.can_dash_clip(world.get_region("Ice Lobby", player), player)
        and (state.can_use_bombs(player) or state.has("Cane of Somaria", player)),
        combine="or",
    )

    # Kiki Skip
    kks = world.get_entrance("Kiki Skip", player)
    Rules.set_rule(kks, lambda state: state.can_bomb_clip(kks.parent_region, player))
    dungeon_reentry_rules(world, player, kks, "Palace of Darkness Portal", "Palace of Darkness Exit")

    # Mire -> Hera -> Swamp
    def mire_clip(state):
        return state.can_reach("Mire Torches Top", "Region", player) and state.can_dash_clip(
            world.get_region("Mire Torches Top", player), player
        )

    def hera_clip(state):
        return state.can_reach("Hera 4F", "Region", player) and state.can_dash_clip(
            world.get_region("Hera 4F", player), player
        )

    Rules.add_rule(
        world.get_entrance("Hera Startile Corner NW", player),
        lambda state: mire_clip(state) and state.has("Big Key (Misery Mire)", player),
        combine="or",
    )
    Rules.add_rule(
        world.get_location("Tower of Hera - Big Chest", player),
        lambda state: mire_clip(state) and state.has("Big Key (Misery Mire)", player),
        combine="or",
    )

    mire_to_hera = world.get_entrance("Mire to Hera Clip", player)
    mire_to_swamp = world.get_entrance("Hera to Swamp Clip", player)
    Rules.set_rule(mire_to_hera, mire_clip)
    Rules.set_rule(mire_to_swamp, lambda state: mire_clip(state) and state.has("Flippers", player))

    # Using the entrances for various ER types. Hera -> Swamp never matters because you can only logically traverse with the mire keys
    dungeon_reentry_rules(world, player, mire_to_hera, "Hera Lobby", "Tower of Hera Exit")
    dungeon_reentry_rules(world, player, mire_to_swamp, "Swamp Lobby", "Swamp Palace Exit")
    # We need to set _all_ swamp doors to be openable with mire keys, otherwise the small key can't be behind them - 6 keys because of Pots
    # Flippers required for all of these doors to prevent locks when flooding
    for door in [
        "Swamp Trench 1 Approach ES",
        "Swamp Hammer Switch SW",
        "Swamp Entrance Down Stairs",
        "Swamp Pot Row WS",
        "Swamp Trench 1 Key Ledge NW",
        "Swamp Hub WN",
        "Swamp Hub North Ledge N",
        "Swamp Crystal Switch EN",
        "Swamp Push Statue S",
        "Swamp Waterway NW",
        "Swamp T SW",
    ]:
        Rules.add_rule(
            world.get_entrance(door, player),
            lambda state: mire_clip(state)
            and state.has("Small Key (Misery Mire)", player, count=6)
            and state.has("Flippers", player),
            combine="or",
        )
        # Rules.add_rule(world.get_entrance(door, player), lambda state: mire_clip(state) and state.has('Flippers', player), combine="or")

    Rules.add_rule(
        world.get_location("Trench 1 Switch", player), lambda state: mire_clip(state) or hera_clip(state), combine="or"
    )

    # Build the rule for SP moat.
    # We need to be able to s+q to old man, then go to either Mire or Hera at either Hera or GT.
    # First we require a certain type of entrance shuffle, then build the rule from its pieces.
    if not world.swamp_patch_required[player]:
        if world.shuffle[player] in [
            "vanilla",
            "dungeonssimple",
            "dungeonsfull",
            "dungeonscrossed",
        ]:
            rule_map = {
                "Mire Portal": (lambda state: state.can_reach("Mire Torches Top", "Entrance", player)),
                "Hera Portal": (lambda state: state.can_reach("Hera Startile Corner NW", "Entrance", player)),
            }
            inverted = world.mode[player] == "inverted"

            def hera_rule(state):
                return (state.has("Moon Pearl", player) or not inverted) and rule_map.get(
                    world.get_entrance("Tower of Hera", player).connected_region.name, lambda state: False
                )(state)

            def gt_rule(state):
                return (state.has("Moon Pearl", player) or inverted) and rule_map.get(
                    world.get_entrance(("Ganons Tower"), player).connected_region.name, lambda state: False
                )(state)

            def mirrorless_moat_rule(state):
                return (
                    state.can_reach("Old Man S&Q", "Entrance", player)
                    and state.has("Flippers", player)
                    and mire_clip(state)
                    and (hera_rule(state) or gt_rule(state))
                )

            Rules.add_rule(
                world.get_entrance("Swamp Lobby Moat", player), lambda state: mirrorless_moat_rule(state), combine="or"
            )

    # Thieves -> Desert
    Rules.add_rule(
        world.get_entrance("Thieves to Desert Clip", player),
        lambda state: state.can_dash_clip(world.get_region("Thieves Attic", player), player),
    )
    dungeon_reentry_rules(
        world,
        player,
        world.get_entrance("Thieves to Desert Clip", player),
        "Desert West Portal",
        "Desert Palace Exit (West)",
    )
    dungeon_reentry_rules(
        world,
        player,
        world.get_entrance("Thieves to Desert Clip", player),
        "Desert South Portal",
        "Desert Palace Exit (South)",
    )
    dungeon_reentry_rules(
        world,
        player,
        world.get_entrance("Thieves to Desert Clip", player),
        "Desert East Portal",
        "Desert Palace Exit (East)",
    )

    # Collecting left chests in Paradox Cave using a dash clip -> dash citrus, 1f right, teleport up
    paradox_left_chests = ["Paradox Cave Lower - Far Left", "Paradox Cave Lower - Left", "Paradox Cave Lower - Middle"]
    for location in paradox_left_chests:
        Rules.add_rule(
            world.get_location(location, player),
            lambda state: state.can_dash_clip(world.get_location(location, player).parent_region, player),
            "or",
        )

    # Collecting right chests in Paradox Cave using a dash clip on left side -> dash citrus, 1f right, teleport up, then hitting the switch
    paradox_right_chests = ["Paradox Cave Lower - Right", "Paradox Cave Lower - Far Right"]
    for location in paradox_right_chests:
        Rules.add_rule(
            world.get_location(location, player),
            lambda state: (
                state.can_dash_clip(world.get_location(location, player).parent_region, player)
                and state.can_hit_crystal(player)
            ),
            "or",
        )
