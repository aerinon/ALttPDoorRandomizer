import functools
from BaseClasses import Entrance, DoorType, Door
from DoorShuffle import connect_simple_door
import Rules

kikiskip_spots = [
    ("Kiki Skip", "Spectacle Rock Cave (Bottom)", "Palace of Darkness Portal")
]

mirehera_spots = [("Mire to Hera Clip", "Mire Torches Top", "Hera Portal")]

heraswamp_spots = [("Hera to Swamp Clip", "Mire Torches Top", "Swamp Portal")]

icepalace_spots = [("Ice Lobby Clip", "Ice Lobby", "Ice Bomb Drop - Top")]

thievesdesert_spots = [
    ("Thieves to Desert West Clip", "Thieves Attic", "Desert West Portal"),
    ("Thieves to Desert South Clip", "Thieves Attic", "Desert South Portal"),
    ("Thieves to Desert East Clip", "Thieves Attic", "Desert East Portal"),
]

specrock_spots = [
    ("Spec Rock Clip", "Spectacle Rock Cave (Peak)", "Spectacle Rock Cave (Top)")
]

paradox_spots = [
    ("Paradox Front Teleport", "Paradox Cave Front", "Paradox Cave Chest Area")
]

def create_hmg_entrances_regions(world, player):
    for spots in [
        kikiskip_spots,
        mirehera_spots,
        heraswamp_spots,
        icepalace_spots,
        thievesdesert_spots,
        specrock_spots,
        paradox_spots,
    ]:
        for entrance, parent_region, _, *_ in spots:
            parent = world.get_region(parent_region, player)
            connection = Entrance(player, entrance, parent)
            connection.spot_type = 'HMG'
            if connection not in parent.exits:
                parent.exits.append(connection)

    ip_bomb_top_reg = world.get_region("Ice Bomb Drop - Top", player)
    ip_clip_entrance = Entrance(player, "Ice Bomb Drop Clip", ip_bomb_top_reg)
    ip_bomb_top_reg.exits.append(ip_clip_entrance)

def connect_hmg_entrances_regions(world, player):
    for spots in [
        kikiskip_spots,
        mirehera_spots,
        heraswamp_spots,
        icepalace_spots,
        thievesdesert_spots,
        specrock_spots,
        paradox_spots,
    ]:
        for entrance, _, target_region, *_ in spots:
            connection = world.get_entrance(entrance, player)
            if world.fix_fake_world[player] and target_region.endswith(" Portal"):
                target = world.get_portal(target_region[:-7], player).find_portal_entrance().parent_region
            else:
                target = world.get_region(target_region, player)
            connection.connect(target)

    # Add the new Ice path (back of bomb drop to front) to the world and model it properly
    ip_clip_entrance = world.get_entrance('Ice Bomb Drop Clip', player)
    clip_door = Door(player, "Ice Bomb Drop Clip", DoorType.Logical, ip_clip_entrance)
    world.doors += [clip_door]
    world.initialize_doors([clip_door])

    connect_simple_door(world, "Ice Bomb Drop Clip", "Ice Bomb Drop", player)

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
def dungeon_reentry_rules(
    world,
    player,
    clip: Entrance,
    dungeon_region: str,
):
    fix_dungeon_exits = world.fix_palaceofdarkness_exit[player]
    fix_fake_worlds = world.fix_fake_world[player]

    all_clips = [
        x[0]
        for x in kikiskip_spots
        + mirehera_spots
        + heraswamp_spots
        + icepalace_spots
        + thievesdesert_spots
        + specrock_spots
        + paradox_spots
    ]

    dungeon_entrance = [
        r
        for r in world.get_region(dungeon_region, player).entrances
        if r.name not in all_clips
    ][0]

    dungeon_exit = [
        r
        for r in world.get_region(dungeon_region, player).exits
        if r.name not in all_clips
    ][0]


    if not fix_dungeon_exits:
        # vanilla, simple, restricted, dungeonssimple; should never have fake worlds fix
        # Dungeons are only shuffled among themselves. We need to check SW, MM, and AT because they can't be reentered trivially.

        # entrance doesn't exist until you fire rod it from the other side
        if dungeon_entrance.name == "Skull Woods Final Section":
            Rules.set_rule(clip, lambda state: False)

        elif dungeon_entrance.name == "Misery Mire":
            if world.swords[player] == "swordless":
                Rules.add_rule(
                    clip, lambda state: state.has_misery_mire_medallion(player)
                )
            else:
                Rules.add_rule(
                    clip,
                    lambda state: state.has_sword(player)
                    and state.has_misery_mire_medallion(player),
                )

        elif dungeon_entrance.name == "Agahnims Tower":
            Rules.add_rule(
                clip,
                lambda state: state.has("Cape", player)
                or state.has_beam_sword(player)
                or state.has("Beat Agahnim 1", player),
            )

        # Then we set a restriction on exiting the dungeon, so you can't leave unless you got in normally.
        Rules.add_rule(
            world.get_entrance(dungeon_exit, player),
            lambda state: dungeon_entrance.can_reach(state),
        )
    elif (
        not fix_fake_worlds
    ):  # full, dungeonsfull; fixed dungeon exits, but no fake worlds fix
        # Entry requires the entrance's requirements plus a fake pearl, but you don't gain logical access to the surrounding region.
        Rules.add_rule(
            clip,
            lambda state: dungeon_entrance.access_rule(fake_pearl_state(state, player)),
        )
        # exiting restriction
        Rules.add_rule(
            world.get_entrance(dungeon_exit, player),
            lambda state: dungeon_entrance.can_reach(state),
        )

    # Otherwise, the shuffle type is lean, lite, crossed, or insanity; all of these do not need additional rules on where we can go,
    # since the clip links directly to the exterior region.


def underworld_glitches_rules(world, player):
    def mire_clip(state):
        torches = world.get_region("Mire Torches Top", player)
        return (state.can_dash_clip(torches, player)
            or (state.can_bomb_clip(torches, player) and state.has_fire_source(player))
        ) and state.can_reach(torches, player)

    def hera_clip(state):
        hera = world.get_region("Hera 4F", player)
        return (state.can_bomb_clip(hera, player) or state.can_dash_clip(hera, player)) \
                and state.has("Flippers", player) and state.can_reach(hera) and mire_clip(state)

    # We use these plus functool.partial because lambdas don't work in loops properly.
    def bomb_clip(state, region, player):
        return state.can_bomb_clip(region, player) and state.can_reach(region, player)

    def dash_clip(state, region, player):
        return state.can_dash_clip(region, player) and state.can_reach(region, player)
    # Bomb clips
    for clip in (
        kikiskip_spots
        + icepalace_spots
        + thievesdesert_spots
        + specrock_spots
    ):
        region = world.get_region(clip[1], player)
        Rules.set_rule(
            world.get_entrance(clip[0], player),
            functools.partial(bomb_clip, region=region, player=player),
        )
    # Dash clips
    for clip in icepalace_spots:
        region = world.get_region(clip[1], player)
        Rules.add_rule(
            world.get_entrance(clip[0], player),
            functools.partial(dash_clip, region=region, player=player),
            combine="or",
        )

    for spot in kikiskip_spots + thievesdesert_spots:
        dungeon_reentry_rules(
            world,
            player,
            world.get_entrance(spot[0], player),
            spot[2],
        )

    for clip in mirehera_spots:
        Rules.set_rule(
            world.get_entrance(clip[0], player),
            lambda state: mire_clip(state),
        )

    # Need to be able to escape by hitting the switch from the back
    Rules.set_rule(
        world.get_entrance("Ice Bomb Drop Clip", player),
        lambda state: (
            state.can_use_bombs(player) or state.has("Cane of Somaria", player)
        ),
    )

    # Allow mire big key to be used in Hera
    Rules.add_rule(
        world.get_entrance("Hera Startile Corner NW", player),
        lambda state: state.has("Big Key (Misery Mire)", player) and mire_clip(state),
        combine="or",
    )
    Rules.add_rule(
        world.get_location("Tower of Hera - Big Chest", player),
        lambda state: state.has("Big Key (Misery Mire)", player) and mire_clip(state),
        combine="or",
    )
    # This uses the mire clip because it's always expected to come from mire
    Rules.set_rule(
        world.get_entrance("Hera to Swamp Clip", player),
        lambda state: state.has("Flippers", player) and mire_clip(state),
    )
    Rules.add_rule(
        world.get_location("Swamp Palace - Big Chest", player),
        lambda state: (state.has("Big Key (Misery Mire)", player) or state.has("Big Key (Tower of Hera)", player)) \
                and state.has("Flippers", player) and mire_clip(state),
        combine="or",
    )
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
            lambda state: state.has("Flippers", player)
            and state.has("Small Key (Misery Mire)", player, count=6)
            and mire_clip(state),
            combine="or",
        )

    Rules.add_rule(
        world.get_location("Trench 1 Switch", player),
        lambda state: mire_clip(state) or hera_clip(state),
        combine="or",
    )

    # Build the rule for SP moat.
    # We need to be able to s+q to old man, then go to either Mire or Hera at either Hera or GT.
    # First we require a certain type of entrance shuffle, then build the rule from its pieces.
    if not world.swamp_patch_required[player] and world.shuffle[player] in [
        "vanilla",
        "dungeonssimple",
        "dungeonsfull",
    ]:
        rule_map = {
            "Mire Portal": (
                lambda state: state.can_reach("Mire Torches Top", "Entrance", player)
            ),
            "Hera Portal": (
                lambda state: state.can_reach(
                    "Hera Startile Corner NW", "Entrance", player
                )
            ),
        }
        inverted_dm = world.mode[player] == "inverted"

        def hera_rule(state):
            return (state.has("Moon Pearl", player) or not inverted_dm) and rule_map.get(
                world.get_entrance("Tower of Hera", player).connected_region.name,
                lambda state: False,
            )(state)

        def gt_rule(state):
            return (state.has("Moon Pearl", player) or inverted_dm) and rule_map.get(
                world.get_entrance(("Ganons Tower"), player).connected_region.name,
                lambda state: False,
            )(state)

        def mirrorless_moat_rule(state):
            return (
                state.can_reach("Old Man S&Q", "Entrance", player)
                and state.has("Flippers", player)
                and (hera_rule(state) or gt_rule(state))
                and mire_clip(state)
            )

        Rules.add_rule(
            world.get_entrance("Swamp Lobby Moat", player),
            lambda state: mirrorless_moat_rule(state),
            combine="or",
        )
    desert_exits = ["West", "South", "East"]

    for desert_exit in desert_exits:
        Rules.add_rule(
            world.get_entrance(f"Thieves to Desert {desert_exit} Clip", player),
            lambda state: state.can_dash_clip(
                world.get_region("Thieves Attic", player), player
            ),
        )


    # Collecting left chests in Paradox Cave using a dash clip -> dash citrus, 1f right, teleport up
    paradox_left_chests = [
        "Paradox Cave Lower - Far Left",
        "Paradox Cave Lower - Left",
        "Paradox Cave Lower - Middle",
    ]
    for location in paradox_left_chests:
        Rules.add_rule(
            world.get_location(location, player),
            lambda state: state.can_dash_clip(
                world.get_location(location, player).parent_region, player
            ),
            "or",
        )

    # Collecting right chests in Paradox Cave using a dash clip on left side -> dash citrus, 1f right, teleport up, then hitting the switch
    paradox_right_chests = [
        "Paradox Cave Lower - Right",
        "Paradox Cave Lower - Far Right",
    ]
    for location in paradox_right_chests:
        Rules.add_rule(
            world.get_location(location, player),
            lambda state: (
                state.can_dash_clip(
                    world.get_location(location, player).parent_region, player
                )
                and state.can_hit_crystal(player)
            ),
            "or",
        )
