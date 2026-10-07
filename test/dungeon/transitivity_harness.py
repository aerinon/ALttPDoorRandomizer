import signal
import time
from collections import defaultdict
from contextlib import contextmanager
from functools import lru_cache

import Main
import source.dungeon.DungeonGenLocalSearch as local_search
from CLI import parse_cli
from source.classes.BabelFish import BabelFish
from source.dungeon.DungeonGenerationCommon import DungeonBuilder
from source.dungeon.DungeonGenTransitivity import do_transitivity_check

DUNGEONS = ['Agahnims Tower', 'Desert Palace', 'Eastern Palace', 'Ganons Tower', 'Hyrule Castle', 'Ice Palace',
            'Misery Mire', 'Palace of Darkness', 'Skull Woods', 'Swamp Palace', 'Thieves Town', 'Tower of Hera',
            'Turtle Rock']


class _Captured(Exception):
    pass


class CheckTimeout(Exception):
    pass


@lru_cache(maxsize=None)
def capture_sectors(intensity, seed=1):
    """Runs generation until DungeonGenInfo is built, returning the prepared sector pool and flags."""
    result = {}

    class CaptureInfo:
        def __init__(self, gen_log, all_sectors, flags, dungeon_map):
            result['sectors'] = all_sectors
            result['flags'] = flags
            raise _Captured()

    original = local_search.DungeonGenInfo
    local_search.DungeonGenInfo = CaptureInfo
    try:
        args = parse_cli(['--door_shuffle', 'crossed', '--intensity', str(intensity),
                          '--dungeon_shuffle_algorithm', 'experimental', '--suppress_rom', '--spoiler', 'none',
                          '--seed', str(seed)])
        Main.main(args, seed=seed, fish=BabelFish(lang='en'))
    except _Captured:
        pass
    finally:
        local_search.DungeonGenInfo = original
    if 'sectors' not in result:
        raise RuntimeError('generation finished without reaching DungeonGenInfo')
    return result['sectors'], result['flags']


def sectors_by_dungeon(sectors):
    grouped = defaultdict(list)
    for s in sectors:
        grouped[s.regions[0].dungeon.name].append(s)
    return grouped


def make_builder(name):
    builder = DungeonBuilder(name)
    builder.split_flag = False
    return builder


@contextmanager
def hard_timeout(seconds):
    """Aborts the block with CheckTimeout after `seconds` of wall time (POSIX only)."""
    def on_alarm(signum, frame):
        raise CheckTimeout(f'exceeded {seconds}s')
    previous = signal.signal(signal.SIGALRM, on_alarm)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous)


def timed_check(builder, sectors, flags, limit=30):
    start = time.process_time()
    with hard_timeout(limit):
        verdict = do_transitivity_check(builder, sectors, flags)
    return verdict, time.process_time() - start
