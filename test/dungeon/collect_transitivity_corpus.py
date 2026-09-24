"""Usage: python test/dungeon/collect_transitivity_corpus.py OUT.jsonl INTENSITY SEED_START COUNT [SEED_TIMEOUT_S]

Runs generation through LocalSearch balancing only (stops before the stitcher), recording every Transitivity call
LocalSearch makes (including calls that hit the 20k-iteration cap, verdict "cap") and checking the plan behind every
True with the witness checker. Each seed runs under a hard timeout; records are flushed as written, so a stalled seed
still leaves its calls behind, followed by a summary line.
"""
import json
import sys
import time
from collections import Counter

import Main
import source.dungeon.DungeonGenLocalSearch as local_search
from CLI import parse_cli
from source.classes.BabelFish import BabelFish
from source.dungeon.DungeonGenerationCommon import GenerationException
from source.dungeon.DungeonGenTransitivity import find_transitivity_solution
from test.dungeon.transitivity_harness import CheckTimeout, hard_timeout
from test.dungeon.transitivity_witness import check_witness


class _BalanceDone(Exception):
    pass


def main(out_path, intensity, seed_start, count, seed_timeout=300):
    original_builders = local_search.main_dungeon_builders
    original_move = local_search.perform_move
    stats = {}

    def emit(record):
        out.write(json.dumps(record) + '\n')
        out.flush()

    def record(builder, sectors, verdict, problems, seconds, initial_connections):
        emit({'type': 'call', 'seed': stats['seed'], 'builder': builder.name, 'split': builder.split_flag,
              'sectors': [sorted(r.name for r in s.regions) for s in sectors],
              'initial': [[a.name, b.name] for a, b in (initial_connections or [])],
              'verdict': verdict, 'problems': problems, 'seconds': seconds})

    def checked_transitivity(builder, sectors, flags, initial_connections=None):
        start = time.process_time()
        try:
            solution = find_transitivity_solution(builder, sectors, flags, initial_connections)
        except GenerationException:
            record(builder, sectors, 'cap', None, round(time.process_time() - start, 4), initial_connections)
            raise
        seconds = round(time.process_time() - start, 4)
        problems = check_witness(solution) if solution is not None else None
        stats['calls'] += 1
        if solution is None:
            stats['false_by_builder'][builder.name] += 1
        elif problems:
            stats['wrong_true'] += 1
        record(builder, sectors, solution is not None, problems, seconds, initial_connections)
        return solution is not None

    def counting_move(*args, **kwargs):
        stats['moves'] += 1
        return original_move(*args, **kwargs)

    def stop_after_balance(*args, **kwargs):
        original_builders(*args, **kwargs)
        raise _BalanceDone()

    local_search.do_transitivity_check_new = checked_transitivity
    local_search.perform_move = counting_move
    local_search.main_dungeon_builders = stop_after_balance
    with open(out_path, 'a') as out:
        for seed in range(seed_start, seed_start + count):
            stats.update(seed=seed, calls=0, moves=0, wrong_true=0, false_by_builder=Counter())
            args = parse_cli(['--door_shuffle', 'crossed', '--intensity', str(intensity), '--dungeon_shuffle_algorithm',
                              'experimental', '--suppress_rom', '--spoiler', 'none', '--seed', str(seed)])
            start, outcome, detail = time.time(), 'finished', ''
            try:
                with hard_timeout(seed_timeout):
                    Main.main(args, seed=seed, fish=BabelFish(lang='en'))
            except _BalanceDone:
                outcome = 'balanced'
            except CheckTimeout:
                outcome = 'timeout'
            except Exception as e:
                outcome, detail = 'raised', f'{type(e).__name__}: {e}'[:300]
            emit({'type': 'seed', 'seed': seed, 'intensity': intensity, 'outcome': outcome, 'detail': detail,
                  'wall_seconds': round(time.time() - start, 1), 'calls': stats['calls'], 'moves': stats['moves'],
                  'wrong_true': stats['wrong_true'], 'false_by_builder': dict(stats['false_by_builder'])})
            print(f"seed {seed}: {outcome} moves={stats['moves']} calls={stats['calls']} "
                  f"wrong_true={stats['wrong_true']} {detail[:120]}", flush=True)


if __name__ == '__main__':
    main(sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), *(int(a) for a in sys.argv[5:6]))
