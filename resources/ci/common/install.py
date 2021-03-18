import common
import argparse
import os
import platform
import subprocess # do stuff at the shell level

env = common.prepare_env()

pip_requirements = os.path.join(".","resources","app","meta","manifests","pip_requirements.txt")

def run_install(PY_VERSION,USER):
  # get executables
  #  python
  #   linux/windows: python
  #   macosx:        python3
  #  pip
  #   linux/macosx: pip3
  #   windows:      pip
  PYTHON_PATH = env["PYTHON_EXE_PATH"]
  PYTHON_EXECUTABLE = "python3" if "osx" in env["OS_NAME"] else "python"
  PIP_PATH = env["PIP_EXE_PATH"]
  PIP_EXECUTABLE = "pip" if "windows" in env["OS_NAME"] else "pip3"
  PIP_EXECUTABLE = "pip" if "osx" in env["OS_NAME"] and "actions" in env["CI_SYSTEM"] else PIP_EXECUTABLE

  if PY_VERSION == None:
    PY_VERSION = 0
  if USER == None:
    USER = False

  if float(PY_VERSION) > 0:
    PYTHON_EXECUTABLE = "py"
    PYTHON_PATH = env["PY_EXE_PATH"]
    print("Installing to Python %.1f via Py Launcher" % float(PY_VERSION))
  else:
    print("Installing to Python %s" % platform.python_version())
  print("Installing packages at %s level" % ("User" if USER else "Global"))

  print()
  print("Upgrading pip-")
  # upgrade pip
  args = [
    PYTHON_PATH + PYTHON_EXECUTABLE,
    '-' + str(PY_VERSION),
    "-m",
    "pip",
    "install",
    "--upgrade",
    "--user",
    "pip"
  ]
  if not USER:
    args.remove("--user")
  if PY_VERSION == 0:
    del args[1]
  subprocess.check_call(args)

  # if pip3, install wheel
  if PIP_EXECUTABLE == "pip3":
    print("Installing Wheel!")
    args = [
      PIP_PATH + PIP_EXECUTABLE,
      "install",
      "--user",
      "-U",
      "wheel"
    ]
    if not USER:
      args.remove("--user")
    subprocess.check_call(args)

  print()
  # install listed dependencies
  print("Installing dependencies")
  print("-----------------------")
  args = [
    PIP_PATH + PIP_EXECUTABLE,
    "install",
    "--user",
    "-r",
    pip_requirements
  ]
  if not USER:
    args.remove("--user")
  subprocess.check_call(args)

if __name__ == "__main__":
  parser = argparse.ArgumentParser(add_help=False)
  parser.add_argument('--py', default=0)
  parser.add_argument('--user', default=False, action="store_true")
  command_line_args = parser.parse_args()
  PY_VERSION = vars(command_line_args)["py"]
  USER = vars(command_line_args)["user"]

  run_install(PY_VERSION,USER)
