import subprocess
import sys
import multiprocessing
import concurrent.futures
import argparse
from collections import OrderedDict
import csv

cpu_threads = multiprocessing.cpu_count()
py_version = f"{sys.version_info.major}.{sys.version_info.minor}"


SETTINGS = {
    'mode': ['open', 'standard', 'inverted'],
    'goal': ['ganon', 'pedestal', 'triforcehunt'],
    'swords': ['random', 'swordless'],
    'shuffle': ['vanilla','simple','restricted','full','dungeonssimple','dungeonsfull', 'crossed','insanity'],
    'accessibility': [True, False],
    'difficulty': [True, False],
    'shufflepots': [True, False],
    'keydropshuffle': [True, False],
    'keysanity': [True, False],
    'retro': [True, False],
    'futuro': [True, False]
}

SETTINGS = {
    'mode': ['standard'],
    'goal': ['ganon', 'pedestal', 'triforcehunt'],
    'swords': ['random', 'vanilla'],
    'shuffle': ['dungeonsfull'],
    'accessibility': [True, False],
    'difficulty': [True, False],
    'shufflepots': [True, False],
    'keydropshuffle': [True, False],
    'keysanity': [True, False],
    'retro': [True, False],
    'futuro': [True, False]
}

optionsList = []
for sett,options in SETTINGS.items():
    for option in options:
        if isinstance(option, str):
            optionsList.append(f'{option}')
        else:
            optionsList.append('{}-{}'.format(sett,str(option)))

headerList = []
for sett,options in SETTINGS.items():
    for option in options:
        if isinstance(option, str):
            headerList.append(f'{option}')
        else:
            if option:
                headerList.append(f'{sett}')

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

    def test(testname: list, command: str):
        tests[' '.join(testname)] = [command]
        basecommand = f"py -3.8 DungeonRandomizer.py --door_shuffle {args.dr} --intensity {args.tense} --suppress_rom --suppress_spoiler"

        def gen_seed():
            taskcommand = basecommand + ' ' + command
            return subprocess.run(taskcommand, capture_output=True, shell=True, text=True)

        for _ in range(1, max_attempts + 1):
            task = pool.submit(gen_seed)
            task.success = False
            task.name = ' '.join(testname)
            task.settings = testname
            task.cmd = basecommand + ' ' + command
            task_mapping.append(task)

    for mode in SETTINGS['mode']:
        for goal in SETTINGS['goal']:
            for swords in SETTINGS['swords']:
                for shuffle in SETTINGS['shuffle']:
                    for difficulty in SETTINGS['difficulty']:
                        for shufflepots in SETTINGS['shufflepots']:
                            for accessibility in SETTINGS['accessibility']:
                                for keydropshuffle in SETTINGS['keydropshuffle']:
                                    for keysanity in SETTINGS['keysanity']:
                                        for retro in SETTINGS['retro']:
                                            for futuro in SETTINGS['futuro']:
                                                commands = ''
                                                name = []
                                                commands = commands + f' --mode {mode}'
                                                name.append(mode)
                                                commands = commands + f' --goal {goal}'
                                                name.append(goal)
                                                commands = commands + f' --swords {swords}'
                                                name.append(swords)
                                                commands = commands + f' --shuffle {shuffle}'
                                                name.append(shuffle)
                                                if difficulty:
                                                    commands = commands + f' --difficulty expert'
                                                    commands = commands + f' --item_functionality expert'
                                                    name.append('difficulty-True')
                                                else:
                                                    name.append('difficulty-False')
                                                if shufflepots:
                                                    commands = commands + f' --shufflepots'
                                                    name.append('shufflepots-True')
                                                else:
                                                    name.append('shufflepots-False')
                                                if not accessibility:
                                                    commands = commands + f' --accessibility none'
                                                    name.append('accessibility-False')
                                                else:
                                                    name.append('accessibility-True')
                                                if keydropshuffle:
                                                    commands = commands + f' --keydropshuffle'
                                                    name.append('keydropshuffle-True')
                                                else:
                                                    name.append('keydropshuffle-False')
                                                if keysanity:
                                                    commands = commands + f' --keysanity'
                                                    name.append('keysanity-True')
                                                else:
                                                    name.append('keysanity-False')
                                                if retro:
                                                    commands = commands + f' --retro'
                                                    name.append('retro-True')
                                                else:
                                                    name.append('retro-False')
                                                if futuro:
                                                    commands = commands + f' --futuro'
                                                    name.append('futuro-True')
                                                else:
                                                    name.append('futuro-False')
                                                test(name, commands)

#    test("Vanilla   ", "--futuro --shuffle vanilla")
#    test("Basic     ", "--futuro --retro --shuffle vanilla")
#    test("Keysanity ", "--futuro --shuffle vanilla --keydropshuffle --keysanity")
#    test("Simple    ", "--futuro --shuffle simple")
#    test("Crossed   ", "--futuro --shuffle crossed")
#    test("Insanity   ", "--futuro --shuffle insanity")
#    test("CrossKeys  ", "--futuro --shuffle crossed --keydropshuffle --keysanity")

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

    def get_results(option: str):
        result = ""
        dead_or_alive = [task.success for task in task_mapping if option in task.settings]
        alive = [x for x in dead_or_alive if x]
        success = f"{option} Rate: {(len(alive) / len(dead_or_alive)) * 100:.1f}%"
        successes.append(success)
        print(success)
        result += f"{(len(alive)/len(dead_or_alive))*100:.2f}%\t"
        return result.strip()
    
    results = []
    for option in optionsList:
        results.append(get_results(option))

    for result in results:
        successes.append(result)

    tabresultsfile = './output/' + args.dr + '.tsv'
    with open(tabresultsfile, 'w+', newline='') as f:
        writer = csv.writer(f, delimiter='\t')
        header = headerList.copy()
        header.append('Success')
        writer.writerow(header)
        for task in task_mapping:
            settings = []
            for option in headerList:
                if option in task.settings:
                    settings.append(1)
                elif str(option + '-True') in task.settings:
                    settings.append(1)
                else:
                    settings.append(0)
            if task.success:
                settings.append(1)
            else:
                settings.append(0)
            writer.writerow(settings)

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

#    for dr in [['vanilla', args.count if args.count else 2, 1],
#               ['basic', args.count if args.count else 5, 1],
#               ['crossed', args.count if args.count else 10, 1]]:
    for dr in [['vanilla', args.count if args.count else 2, 1]]:

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
                with open(f"./output/{dr[0]}{(f'-{tense}' if dr[0] in ['basic', 'crossed'] else '')}-errors.txt", 'w') as stream:
                    for error in errors:
                        stream.write(error[0] + "\n")
                        stream.write(error[1] + "\n")
                        stream.write(error[2] + "\n\n")

    with open("./output/success.txt", "w") as stream:
        stream.write(str.join("\n", successes))

    input("Press enter to continue")
