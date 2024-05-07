import os
import subprocess
import sys
import multiprocessing
import concurrent.futures
import argparse
from collections import OrderedDict

cpu_threads = multiprocessing.cpu_count()
py_version = f"{sys.version_info.major}.{sys.version_info.minor}"

PYLINE = "python"
PIPLINE_PATH = os.path.join(".","resources","user","meta","manifests","pipline.txt")
if os.path.isfile(PIPLINE_PATH):
    with open(PIPLINE_PATH) as pipline_file:
        PYLINE = pipline_file.read().replace("-m pip","").strip()

results = {
    "errors": [],
    "success": []
}

def main(args=None):
    successes = []
    errors = []
    task_mapping = []
    tests = OrderedDict()

    successes.append(f"Testing {args.dr} DR with {args.count} Tests" + (f" (intensity={args.tense})" if args.dr in ['basic', 'crossed'] else ""))
    print(successes[0])

    max_attempts = args.count
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=cpu_threads)
    dead_or_alive = 0
    alive = 0

    def test(testname: str, command: str):
        tests[testname] = [command]
        basecommand = f"{PYLINE} Mystery.py --suppress_rom --suppress_meta"

        def gen_seed():
            taskcommand = basecommand + " " + command
            return subprocess.run(taskcommand, capture_output=True, shell=True, text=True)

        for x in range(1, max_attempts + 1):
            task = pool.submit(gen_seed)
            task.success = False
            task.name = testname
            task.mode = "Mystery"
            task.cmd = basecommand + " " + command
            task_mapping.append(task)

    for i in range(0, 100):
        test("Mystery", "--weights mystery_testsuite.yml")

    from tqdm import tqdm
    with tqdm(concurrent.futures.as_completed(task_mapping),
              total=len(task_mapping), unit="seed(s)",
              desc=f"Success rate: 0.00%") as progressbar:
        for task in progressbar:
            dead_or_alive += 1
            try:
                result = task.result()
                if result.returncode:
                    errors.append([task.name, task.cmd, result.stderr])
                else:
                    alive += 1
                    task.success = True
            except Exception as e:
                raise e

            progressbar.set_description(f"Success rate: {(alive/dead_or_alive)*100:.2f}% - {task.name}")

    def get_results(testname: str):
        result = ""
        for mode in ['Mystery']:
            dead_or_alive = [task.success for task in task_mapping if task.name == testname and task.mode == mode]
            alive = [x for x in dead_or_alive if x]
            success = f"{testname} Rate: {(len(alive) / len(dead_or_alive)) * 100:.2f}%"
            successes.append(success)
            print(success)
            result += f"{(len(alive)/len(dead_or_alive))*100:.2f}%\t"
        return result.strip()

    results = []
    for t in tests.keys():
        results.append(get_results(t))

    for result in results:
        print(result)
        successes.append(result)

    return successes, errors


if __name__ == "__main__":
    successes = []

    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--count', default=0, type=lambda value: max(int(value), 0))
    parser.add_argument('--cpu_threads', default=cpu_threads, type=lambda value: max(int(value), 1))
    parser.add_argument('--help', default=False, action='store_true')

    args = parser.parse_args()

    if args.help:
        parser.print_help()
        exit(0)

    cpu_threads = args.cpu_threads

    for dr in [['mystery', args.count if args.count else 1, 1]]:

        for tense in range(1, dr[2] + 1):
            args = argparse.Namespace()
            args.dr = dr[0]
            args.tense = tense
            args.count = dr[1]
            s, errors = main(args=args)
            if successes:
                successes += [""] * 2
            successes += s
            print()

            if errors:
                with open(f"{dr[0]}{(f'-{tense}' if dr[0] in ['basic', 'crossed'] else '')}-errors.txt", 'w') as stream:
                    for error in errors:
                        stream.write(error[0] + "\n")
                        stream.write(error[1] + "\n")
                        stream.write(error[2] + "\n\n")
                        error[2] = error[2].split("\n")
                        results["errors"].append(error)

    with open("mystery-success.txt", "w") as stream:
        stream.write(str.join("\n", successes))
        results["success"] = successes

    print(results)
