import fnmatch
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

def main(args=None):
    successes = []
    errors = []
    task_mapping = []
    tests = OrderedDict()

    successes.append(f"Testing DR (NewTestSuite)")
    print(successes[0])

    # max_attempts = args.count
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=cpu_threads)
    dead_or_alive = 0
    alive = 0

    def test(test_name: str, command: str, test_file: str):
        tests[test_name] = [command]

        base_command = f"{PYLINE} DungeonRandomizer.py --suppress_rom --spoiler none"

        def gen_seed():
            task_command = base_command + " " + command
            return subprocess.run(task_command, capture_output=True, shell=True, text=True)

        task = pool.submit(gen_seed)
        task.success = False
        task.name = test_name
        task.test_file = test_file
        task.cmd = base_command + " " + command
        task_mapping.append(task)

    for test_suite, test_files in args.test_suite.items():
        for test_file in test_files:
            test(test_suite, f'--customizer {os.path.join(test_suite, test_file)}', test_file)

    from tqdm import tqdm
    with tqdm(concurrent.futures.as_completed(task_mapping),
              total=len(task_mapping), unit="seed(s)",
              desc=f"Success rate: 0.00%") as progressbar:
        for task in progressbar:
            dead_or_alive += 1
            try:
                result = task.result()
                if result.returncode:
                    errors.append([task.name + ' ' + task.test_file, task.cmd, result.stderr])
                else:
                    alive += 1
                    task.success = True
            except Exception as e:
                raise e

            progressbar.set_description(f"Success rate: {(alive/dead_or_alive)*100:.2f}% - {task.name}")

    def get_results(testname: str):
        result = ""
        dead_or_alive = [task.success for task in task_mapping if task.name == testname]
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
    # parser.add_argument('--count', default=0, type=lambda value: max(int(value), 0))
    parser.add_argument('--cpu_threads', default=cpu_threads, type=lambda value: max(int(value), 1))
    parser.add_argument('--help', default=False, action='store_true')

    args = parser.parse_args()

    if args.help:
        parser.print_help()
        exit(0)

    cpu_threads = args.cpu_threads

    test_suites = {}
    # not sure if it supports subdirectories properly yet
    for root, dirnames, filenames in os.walk(os.path.join("test","suite")):
        test_suites[root] = fnmatch.filter(filenames, '*.yaml')

    args = argparse.Namespace()
    args.test_suite = test_suites
    s, errors = main(args=args)
    if successes:
        successes += [""] * 2
    successes += s
    print()

    if errors:
        with open(f"new-test-suite-errors.txt", 'w') as stream:
            for error in errors:
                stream.write(error[0] + "\n")
                stream.write(error[1] + "\n")
                stream.write(error[2] + "\n\n")

    with open("new-test-suite-success.txt", "w") as stream:
        stream.write(str.join("\n", successes))
