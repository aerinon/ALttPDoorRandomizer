import common                     # app common functions

import json                       # json manipulation
import os                         # for os data, filesystem manipulation
import subprocess                 # for running shell commands
import sys                        # for system commands
import traceback                  # for errors

env = common.prepare_env()  # get environment variables

WIDTH = 70  # width for labels

args = []

PIPEXE = ""

PYTHON_EXECUTABLE = os.path.splitext(sys.executable.split(os.path.sep).pop())[0]  # get command to run python
# get python version
PYTHON_VERSION = sys.version.split(" ")[0]
# get python major.minor version
PYTHON_MINOR_VERSION = '.'.join(PYTHON_VERSION.split(".")[:2])

PIP_VERSION = ""
PIP_FLOAT_VERSION = 0

SUCCESS = False
VERSIONS = {}


def process_module_output(lines):
    for line in lines:
        # if there's an error, print it and bail
        if "status 'error'" in line.strip():
            print(
                "🔴[%s] %s"
                %
                (
                    "_",
                    line.strip()
                )
            )
            return
            # sys.exit(1)
        # if it's already satisfied or building a wheel, print version data
        elif "already satisfied" in line or \
            "Building wheel" in line or \
                "Created wheel" in line:

            modulename = print_module_line(line)

            if "=" not in modulename and VERSIONS[modulename]["installed"] != VERSIONS[modulename]["latest"]:
                # install modules from list
                ret = subprocess.run(
                    [
                        *args,
                        "-m",
                        PIPEXE,
                        "install",
                        "--upgrade",
                        f"{modulename}"
                    ],
                    capture_output=True,
                    text=True
                )
                # if there's output
                if ret.stdout.strip():
                    process_module_output(ret.stdout.strip().split("\n"))

        # ignore lines about certain things
        elif "Attempting uninstall" in line or \
            "Collecting" in line or \
            "Downloading" in line or \
            "eta 0:00:00" in line or \
            "Found existing" in line or \
            "Installing collected" in line or \
            "Preparing metadata" in line or \
            "Successfully built" in line or \
            "Successfully installed" in line or \
            "Successfully uninstalled" in line or \
            "Stored in" in line or \
            "Uninstalling " in line or \
                "Using cached" in line:
            pass
        # else, I don't know what it is, print it
        else:
            print(line.strip())
    print("")


def print_module_line(line):
    global VERSIONS
    satisfied = line.strip().split(" in ")
    sver = ((len(satisfied) > 1) and satisfied[1].split("(").pop().replace(")", "")) or ""

    if "Created wheel" in line:
        line = line.strip().split(':')
        satisfied = [line[0]]
        sver = line[1].split('-')[1]

    modulename = satisfied[0].replace("Requirement already satisfied: ", "")
    VERSIONS[modulename] = {
        "installed": sver,
        "latest": (sver and get_module_version(satisfied[0].split(" ")[-1])).strip() or ""
    }

    print(
        (
            "[%s] %s\t%s\t%s"
            %
            (
                "Building wheel" in line and '.' or "X",
                satisfied[0].ljust(len("Requirement already satisfied: ") + len("python-bps-continued")),
                VERSIONS[modulename]["installed"],
                VERSIONS[modulename]["latest"]
            )
        )
    )
    return modulename


def get_module_version(module):
    # pip index versions [module]                             // >= 21.2
    # pip install [module]==                                  // >= 21.1
    # pip install --use-deprecated=legacy-resolver [module]== // >= 20.3
    # pip install [module]==                                  // >=  9.0
    # pip install [module]==blork                             // <   9.0
    global args
    global PIPEXE
    global PIP_FLOAT_VERSION
    ret = ""
    ver = ""

    if float(PIP_FLOAT_VERSION) >= 21.2:
        ret = subprocess.run(
            [
                *args,
                "-m",
                PIPEXE,
                "index",
                "versions",
                module
            ],
            capture_output=True,
            text=True
        )
        lines = ret.stdout.strip().split("\n")
        lines = lines[2::]
        vers = (list(map(lambda x: x.split(' ')[-1], lines)))
        if len(vers) > 1:
            ver = vers[1]
    elif float(PIP_FLOAT_VERSION) >= 21.1:
        ret = subprocess.run(
            [
                *args,
                "-m",
                PIPEXE,
                "install",
                f"{module}=="
            ],
            capture_output=True,
            text=True
        )
    elif float(PIP_FLOAT_VERSION) >= 20.3:
        ret = subprocess.run(
            [
                *args,
                "-m",
                PIPEXE,
                "install",
                "--use-deprecated=legacy-resolver",
                f"{module}=="
            ],
            capture_output=True,
            text=True
        )
    elif float(PIP_FLOAT_VERSION) >= 9.0:
        ret = subprocess.run(
            [
                *args,
                "-m",
                PIPEXE,
                "install",
                f"{module}=="
            ],
            capture_output=True,
            text=True
        )
    elif float(PIP_FLOAT_VERSION) < 9.0:
        ret = subprocess.run(
            [
                *args,
                "-m",
                PIPEXE,
                "install",
                f"{module}==blork"
            ],
            capture_output=True,
            ext=True
        )

    # if ver == "" and ret.stderr.strip():
    #     ver = (ret.stderr.strip().split("\n")[0].split(",")[-1].replace(')', '')).strip()

    return ver


def python_info():
    global args
    global PYTHON_VERSION

    # get python debug info
    ret = subprocess.run([*args, "--version"], capture_output=True, text=True)
    if ret.stdout.strip():
        PYTHON_VERSION = ret.stdout.strip().split(" ")[1]
        PY_STRING = (
            "%s\t%s\t%s"
            %
            (
                ((isinstance(args[0], list) and " ".join(
                    args[0])) or args[0]).strip(),
                PYTHON_VERSION,
                sys.platform
            )
        )
        print(PY_STRING)
        print('.' * WIDTH)


def pip_info():
    global args
    global PIPEXE
    global PIPEXE
    global VERSIONS

    # get pip debug info
    ret = subprocess.run(
        [
            *args,
            "-m",
            PIPEXE,
            "--version"
        ],
        capture_output=True,
        text=True
    )
    if ret.stdout.strip():
        if " from " in ret.stdout.strip():
            PIP_VERSION = ret.stdout.strip().split(" from ")[0].split(" ")[1]
            if PIP_VERSION:
                b, f, a = PIP_VERSION.partition('.')
                global PIP_FLOAT_VERSION
                PIP_FLOAT_VERSION = b+f+a.replace('.', '')
                PIP_LATEST = get_module_version("pip")

                VERSIONS["py"] = {
                    "version": PYTHON_VERSION,
                    "platform": sys.platform
                }
                VERSIONS["pip"] = {
                    "version": [
                        PIP_VERSION,
                        PIP_FLOAT_VERSION
                    ],
                    "latest": PIP_LATEST
                }

                PIP_STRING = (
                    "%s\t%s\t%s\t%s\t%s\t%s"
                    %
                    (
                        ((isinstance(args[0], list) and " ".join(
                            args[0])) or args[0]).strip(),
                        PYTHON_VERSION,
                        sys.platform,
                        PIPEXE,
                        PIP_VERSION,
                        PIP_LATEST
                    )
                )
                print(PIP_STRING)
                print('.' * WIDTH)


def pip_upgrade():
    global args
    global PIPEXE

    # upgrade pip
    ret = subprocess.run(
        [
            *args,
            "-m",
            PIPEXE,
            "install",
            "--upgrade", "pip"
        ],
        capture_output=True,
        text=True
    )
    # get output
    if ret.stdout.strip():
        # if it's not already satisfied, update it
        if "already satisfied" not in ret.stdout.strip():
            print(ret.stdout.strip())
            pip_info()


def install_modules():
    global args
    global PIPEXE
    global SUCCESS

    # install modules from list
    ret = subprocess.run(
        [
            *args,
            "-m",
            PIPEXE,
            "install",
            "-r",
            os.path.join(
                ".",
                "resources",
                "app",
                "meta",
                "manifests",
                "pip_requirements.txt"
            )
        ],
        capture_output=True,
        text=True
    )

    # if there's output
    if ret.stdout.strip():
        process_module_output(ret.stdout.strip().split("\n"))
        manifests_path = os.path.join(".", "resources", "user", "meta", "manifests")
        if not os.path.isdir(manifests_path):
            os.makedirs(manifests_path)

        with open(os.path.join(manifests_path, "settings.json"), "w+") as settings:
            settings.write(
                json.dumps(
                    {
                        "py": args,
                        "pip": PIPEXE,
                        "pipline": " ".join(args) + " -m " + PIPEXE,
                        "versions": VERSIONS
                    },
                    indent=2
                )
            )
        with open(os.path.join(manifests_path, "pipline.txt"), "w+") as settings:
            settings.write(" ".join(args) + " -m " + PIPEXE)
        SUCCESS = True


def main():
    global args
    global PIPEXE
    global SUCCESS
    # print python debug info
    heading = (
        "%s-%s-%s"
        %
        (
            PYTHON_EXECUTABLE,
            PYTHON_VERSION,
            sys.platform
        )
    )
    print(heading)
    print('=' * WIDTH)

    # figure out pip executable
    PIPEXE = "pip" if "windows" in env["OS_NAME"] else "pip3"
    PIPEXE = "pip" if "osx" in env["OS_NAME"] and "actions" in env["CI_SYSTEM"] else PIPEXE

    PIP_VERSION = ""  # holder for pip's version

    SUCCESS = False
    # foreach py executable
    for PYEXE in ["py", "python3", "python"]:
        if SUCCESS:
            continue

        args = []
        # if it's the py launcher, specify the version
        if PYEXE == "py":
            PYEXE = [PYEXE, "-" + PYTHON_MINOR_VERSION]
            # if it ain't windows, skip it
            if "windows" not in env["OS_NAME"]:
                continue

        # build executable command
        if isinstance(PYEXE, list):
            args = [*PYEXE]
        else:
            args = [PYEXE]

        try:
            python_info()

            # foreach py executable
            for PIPEXE in ["pip3", "pip"]:
                pip_info()
                pip_upgrade()
                install_modules()

        # if something else went fucky, print it
        except Exception as e:
            traceback.print_exc()


if __name__ == "__main__":
    main()
