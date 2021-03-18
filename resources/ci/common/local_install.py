import install
import get_get_pip

import argparse

parser = argparse.ArgumentParser(add_help=False)
parser.add_argument('--py', default=0)
parser.add_argument('--user', default=False, action="store_true")
command_line_args = parser.parse_args()
PY_VERSION = vars(command_line_args)["py"]
USER = vars(command_line_args)["user"]

# get & install pip
get_get_pip.get_get_pip(PY_VERSION)

# run installer
install.run_install(PY_VERSION,USER)
