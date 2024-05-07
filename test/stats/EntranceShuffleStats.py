import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
import RaceRandom as random
import time

from collections import Counter, defaultdict

from source.overworld.EntranceShuffle2 import link_entrances_new
from EntranceShuffle import link_entrances
from BaseClasses import World
from Regions import create_regions, create_dungeon_regions


# tested: open + crossed (lh) Mar. 17 (made changes)
# tested: open + simple (lh) Mar. 22

def run_stats():
    # logging.basicConfig(format='%(message)s', level=logging.DEBUG)
    random.seed(None)
    tests = 10000

    for main_mode in ['open', 'standard', 'inverted']:
        for shuffle_mode in ['dungeonssimple', 'dungeonsfull',
                             'simple', 'restricted', 'full', 'crossed']:
            for ls in [True, False]:
                if ls and (main_mode == 'standard' or shuffle_mode in ['dungeonssimple', 'dungeonsfull']):
                    continue

                def runner_new(world):
                    link_entrances_new(world, 1)

                def runner_old(world):
                    link_entrances(world, 1)
                compare_tests(tests, shuffle_mode, main_mode, ls, runner_old, runner_new)


def run_test_stats():
    # logging.basicConfig(format='%(message)s', level=logging.DEBUG)
    random.seed(None)
    tests = 10000

    for main_mode in ['open']:
        for shuffle_mode in [#'dungeonssimple', 'dungeonsfull',
                             'simple']:#, 'restricted', 'full', 'crossed']:
            for ls in [True, False]:
                if ls and (main_mode == 'standard' or shuffle_mode in ['dungeonssimple', 'dungeonsfull']):
                    continue

                def runner_new(world):
                    link_entrances_new(world, 1)

                run_tests(tests, shuffle_mode, main_mode, ls, runner_new)


def run_old_stats():
    # logging.basicConfig(format='%(message)s', level=logging.DEBUG)
    random.seed(None)
    tests = 10000

    for main_mode in ['open']:
        for shuffle_mode in [#'dungeonssimple', 'dungeonsfull',
            'simple']:#, 'restricted', 'full', 'crossed']:
            for ls in [True, False]:
                if ls and (main_mode == 'standard' or shuffle_mode in ['dungeonssimple', 'dungeonsfull']):
                    continue

                def runner(world):
                    link_entrances(world, 1)
                run_tests(tests, shuffle_mode, main_mode, ls, runner)


def compare_tests(tests, shuffle_mode, main_mode, links=False, runner_old=None, runner_new=None):
    print(f'Testing {shuffle_mode} {main_mode}')
    entrance_set = set()
    exit_set = set()
    ctr = defaultdict(Counter)
    start = time.time()
    test_loop(tests, entrance_set, exit_set, ctr, shuffle_mode, main_mode, links, runner_old)
    print(f'Old test took {time.time() - start}s')
    start = time.time()
    test_loop(tests, entrance_set, exit_set, ctr, shuffle_mode, main_mode, links, runner_new, -1)
    # test_loop(tests, entrance_set, exit_set, ctr, shuffle_mode, main_mode, links, runner_new)
    print(f'New test took {time.time() - start}s')
    dump_file(tests, entrance_set, exit_set, ctr, shuffle_mode, main_mode, links)


def run_tests(tests, shuffle_mode, main_mode, links=False, runner=None):
    print(f'Testing {shuffle_mode} {main_mode}')
    entrance_set = set()
    exit_set = set()
    ctr = defaultdict(Counter)
    test_loop(tests, entrance_set, exit_set, ctr, shuffle_mode, main_mode, links, runner)


def test_loop(tests, entrance_set, exit_set, ctr, shuffle_mode, main_mode, links, runner, value=1):
    for i in range(0, tests):
        if i % 1000 == 0:
            print(f'Test {i}')
        seed = random.randint(0, 999999999)
        # seed = 635441530
        random.seed(seed)
        world = World(1, {1: shuffle_mode}, {1: 'vanilla'}, {1: 'noglitches'}, {1: main_mode}, {}, {}, {},
                      {}, {}, {}, {}, {}, True, {}, [], {})
        world.customizer = False
        world.shufflelinks = {1: links}
        world.shuffletavern = {1: False}
        create_regions(world, 1)
        create_dungeon_regions(world, 1)
        # print(f'Linking seed {seed}')
        # try:
        runner(world)
        # except Exception as e:
        #     print(f'Failure during seed {seed} with {e}')
        for data in world.spoiler.entrances.values():
            ent = data['entrance']
            ext = data['exit']
            # drc = data['direction']
            entrance_set.add(ent)
            exit_set.add(ext)
            ctr[ent][ext] += value


def dump_file(tests, entrance_set, exit_set, ctr, shuffle_mode, main_mode, links):
    columns = sorted(list(exit_set))
    rows = sorted(list(entrance_set))
    filename = f'er_stats_{shuffle_mode}_{main_mode}_{"ls" if links else "v"}.csv'
    with open(filename, 'w') as stat_file:
        stat_file.write(',')
        stat_file.write(','.join(columns))
        stat_file.write('\n')
        for r in rows:
            stat_file.write(f'{r},')
            formatted = []
            for c in columns:
                occurance = ctr[r][c] / tests
                formatted.append(f'{occurance:.5%}')
            stat_file.write(','.join(formatted))
            stat_file.write('\n')


if __name__ == "__main__":
    # logging.basicConfig(format='%(message)s', level=logging.DEBUG)
    # run_tests(1, 'restricted', 'inverted', True, lambda world: link_entrances_new(world, 1))
    # run_test_stats()
    # run_old_stats()
    run_stats()
