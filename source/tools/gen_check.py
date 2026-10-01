"""Fast checks for generation fixes, instead of a full TestSuite run.

  extract DIR [-o corpus.jsonl]     TestSuite *-errors.txt files -> one record per failure (command, seed, category)
  replay CORPUS [--match RE]        rerun recorded failures with their seeds; report which still fail
  sweep --seeds 1-100 -- ARGS...    run DungeonRandomizer ARGS over a seed range; report completion and failure categories

Common options: --workers N (default 5), --timeout S (default 600), --stop {entrances,doors} to stop once that stage
is done (door-stage bugs don't need item fill), --out results.jsonl to keep per-run results.

A replayed seed only reproduces when the code before the failure is unchanged: a fix that shifts random draws can make
an old seed pass or fail for unrelated reasons. Use replay to check the cases that broke, and sweep on fresh seeds for
the failure rate.
"""
import argparse
import concurrent.futures
import glob
import json
import os
import re
import shlex
import subprocess
import sys
from collections import Counter

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
STAGES = ('entrances', 'doors')


def normalize(message):
    """A stable failure category from an exception line: no module path, player tag, timings or seeds."""
    message = message.strip()
    message = re.sub(r'^(?:[\w.]+\.)?(\w+(?:Error|Exception|Exit|Iteration))\b', r'\1', message)
    message = re.sub(r'\s*\(Player \d+\)', '', message)
    message = re.sub(r'\b\d+\.\d+\b', '', message)
    message = re.sub(r'--seed \d+', '', message)
    return re.sub(r'\s+', ' ', message).strip()[:160]


# ---- extract ----

def extract(directory, out):
    records = []
    for path in sorted(glob.glob(os.path.join(directory, '*-errors.txt'))):
        lines = open(path).read().split('\n')
        starts = [i for i in range(len(lines) - 1) if lines[i + 1].startswith('python DungeonRandomizer.py')]
        for k, i in enumerate(starts):
            end = starts[k + 1] if k + 1 < len(starts) else len(lines)
            command, stderr = lines[i + 1], '\n'.join(lines[i + 2:end])
            seed = re.search(r'--seed (\d+)', stderr)
            tail = [line for line in stderr.strip().split('\n') if line.strip()]
            frames = re.findall(r'File "[^"]*/([^"/]+)", line \d+, in (\w+)', stderr)
            records.append({'block': os.path.basename(path)[:-len('-errors.txt')], 'name': lines[i].strip(),
                            'args': shlex.split(command)[2:], 'seed': int(seed.group(1)) if seed else None,
                            'category': normalize(tail[-1]) if tail else '?',
                            'where': ':'.join(frames[-1]) if frames else '?'})
    with open(out, 'w') as f:
        for r in records:
            f.write(json.dumps(r) + '\n')
    counts = Counter(r['category'] for r in records)
    print(f'{len(records)} failures, {sum(1 for r in records if r["seed"] is None)} without a seed -> {out}')
    for category, n in counts.most_common(15):
        print(f'{n:5}  {category}')


# ---- running one generation (in a child process) ----

def run_one(args, stop):
    """Child side: run one generation in-process and print one JSON line with the outcome."""
    sys.path[:0] = [ROOT, os.path.join(ROOT, 'source')]
    os.chdir(ROOT)
    import logging
    import traceback
    logging.disable(logging.WARNING)
    import Main
    from CLI import parse_cli
    from source.classes.BabelFish import BabelFish

    class Stopped(Exception):
        pass

    def stop_after(original):
        def wrapper(*a, **k):
            result = original(*a, **k)
            raise Stopped()
        return wrapper

    if stop == 'entrances':
        Main.link_entrances_new = stop_after(Main.link_entrances_new)
    elif stop == 'doors':
        Main.link_doors_prototype = stop_after(Main.link_doors_prototype)
        Main.link_doors = stop_after(Main.link_doors)
    parsed = parse_cli(args + ['--suppress_rom', '--spoiler', 'none'])
    outcome = {'status': 'completed', 'category': '', 'where': ''}
    try:
        Main.main(parsed, seed=parsed.seed, fish=BabelFish(lang='en'))
    except Stopped:
        outcome['status'] = f'passed {stop}'
    except BaseException as e:  # report everything, including StopIteration and SystemExit
        frames = traceback.extract_tb(e.__traceback__)
        outcome = {'status': 'failed', 'category': normalize(f'{type(e).__name__}: {e}'),
                   'where': f'{os.path.basename(frames[-1].filename)}:{frames[-1].name}' if frames else '?'}
    print('GEN_CHECK ' + json.dumps(outcome), flush=True)


def launch(args, stop, timeout):
    command = [sys.executable, os.path.abspath(__file__), '_run'] + (['--stop', stop] if stop else []) + ['--'] + args
    env = dict(os.environ, PYTHONPATH=os.pathsep.join([ROOT, os.path.join(ROOT, 'source')]))
    try:
        done = subprocess.run(command, capture_output=True, text=True, timeout=timeout, cwd=ROOT, env=env,
                              stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        return {'status': 'failed', 'category': f'TIMEOUT after {timeout}s', 'where': ''}
    line = next((l for l in reversed(done.stdout.split('\n')) if l.startswith('GEN_CHECK ')), None)
    if line is None:
        tail = [l for l in done.stderr.strip().split('\n') if l.strip()]
        return {'status': 'failed', 'category': normalize(tail[-1]) if tail else f'exit {done.returncode}', 'where': ''}
    return json.loads(line[len('GEN_CHECK '):])


def run_all(jobs, stop, timeout, workers, out):
    """jobs: list of (label dict, args). Returns the label dicts with the outcome merged in."""
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(launch, args, stop, timeout): label for label, args in jobs}
        for i, future in enumerate(concurrent.futures.as_completed(futures), 1):
            results.append(dict(futures[future], **future.result()))
            print(f'\r{i}/{len(jobs)}', end='', file=sys.stderr, flush=True)
    print(file=sys.stderr)
    if out:
        with open(out, 'w') as f:
            for r in results:
                f.write(json.dumps(r) + '\n')
    return results


def ok(result):
    return result['status'] != 'failed'


# ---- replay ----

def replay(corpus, match, stop, timeout, workers, out, limit):
    records = [json.loads(line) for line in open(corpus) if line.strip()]
    records = [r for r in records if r['seed'] is not None and (not match or re.search(match, r['category']))]
    if limit:
        records = records[:limit]
    jobs = [({'block': r['block'], 'name': r['name'], 'seed': r['seed'], 'was': r['category']},
             [a for a in r['args'] if a not in ('--suppress_rom',)] + ['--seed', str(r['seed'])]) for r in records]
    results = run_all(jobs, stop, timeout, workers, out)
    summary = Counter()
    for r in results:
        if ok(r):
            summary[('no longer fails', r['was'])] += 1
        elif r['category'] == r['was']:
            summary[('same failure', r['was'])] += 1
        else:
            summary[('different failure', r['category'])] += 1
    print(f'replayed {len(results)} recorded failures' + (f' (stopped after {stop})' if stop else ''))
    for (kind, category), n in sorted(summary.items(), key=lambda x: (x[0][0], -x[1])):
        print(f'{n:5}  {kind:17}  {category}')


# ---- sweep ----

def parse_seeds(text):
    seeds = []
    for part in text.split(','):
        lo, _, hi = part.partition('-')
        seeds.extend(range(int(lo), int(hi or lo) + 1))
    return seeds


def sweep(seeds, args, stop, timeout, workers, out):
    jobs = [({'seed': s}, args + ['--seed', str(s)]) for s in seeds]
    results = run_all(jobs, stop, timeout, workers, out)
    passed = sum(1 for r in results if ok(r))
    n = len(results)
    p = passed / n if n else 0
    margin = 1.96 * (p * (1 - p) / n) ** 0.5 if n else 0
    print(f'{passed}/{n} {"passed " + stop if stop else "completed"} ({100 * p:.1f}% ± {100 * margin:.1f})')
    for category, count in Counter(r['category'] for r in results if not ok(r)).most_common():
        print(f'{count:5}  {category}')


def main():
    if len(sys.argv) > 1 and sys.argv[1] == '_run':
        p = argparse.ArgumentParser()
        p.add_argument('--stop', choices=STAGES)
        own, rest = p.parse_known_args(sys.argv[2:])
        run_one([a for a in rest if a != '--'], own.stop)
        return
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='command', required=True)
    e = sub.add_parser('extract')
    e.add_argument('directory')
    e.add_argument('-o', '--out', default='failures.jsonl')
    for name in ('replay', 'sweep'):
        s = sub.add_parser(name)
        s.add_argument('--stop', choices=STAGES)
        s.add_argument('--timeout', type=int, default=600)
        s.add_argument('--workers', type=int, default=5)
        s.add_argument('--out')
        if name == 'replay':
            s.add_argument('corpus')
            s.add_argument('--match', help='regex on the failure category')
            s.add_argument('--limit', type=int)
        else:
            s.add_argument('--seeds', required=True, help='e.g. 1-100 or 1-50,200-220')
            s.add_argument('args', nargs=argparse.REMAINDER, help='DungeonRandomizer arguments, after --')
    a = p.parse_args()
    if a.command == 'extract':
        extract(a.directory, a.out)
    elif a.command == 'replay':
        replay(a.corpus, a.match, a.stop, a.timeout, a.workers, a.out, a.limit)
    else:
        sweep(parse_seeds(a.seeds), [x for x in a.args if x != '--'], a.stop, a.timeout, a.workers, a.out)


if __name__ == '__main__':
    main()
