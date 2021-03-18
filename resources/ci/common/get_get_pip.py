import common
import argparse
import os
import urllib.request, ssl
import subprocess # do stuff at the shell level

env = common.prepare_env()

def get_get_pip(PY_VERSION):
  try:
    import pip
  except ImportError:
    print("Getting pip getter!")
    #make the request!
    url = "https://bootstrap.pypa.io/get-pip.py"
    context = ssl._create_unverified_context()
    req = urllib.request.urlopen(url, context=context)
    got_pip = req.read().decode("utf-8")

    with open("get-pip.py", "w") as g:
      req = urllib.request.Request(
        url,
        data=None,
        headers={
          "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.181 Safari/537.36"
        }
      )
      req = urllib.request.urlopen(req, context=context)
      data = req.read().decode("utf-8")
      g.write(data)

    # get executables
    #  python
    #   linux/windows: python
    #   macosx:        python3
    PYTHON_EXECUTABLE = "python3" if "osx" in env["OS_NAME"] else "python"
    if PY_VERSION == None:
      PY_VERSION = 0

    if float(PY_VERSION) > 0:
      PYTHON_EXECUTABLE = "py"

    print("Getting pip!")
    args = [
      env["PYTHON_EXE_PATH"] + PYTHON_EXECUTABLE,
      '-' + str(PY_VERSION),
      "get-pip.py"
    ]
    if PY_VERSION == 0:
      del args[1]
    subprocess.check_call(args)

if __name__ == "__main__":
  parser = argparse.ArgumentParser(add_help=False)
  parser.add_argument('--py', default=0)
  command_line_args = parser.parse_args()
  PY_VERSION = vars(command_line_args)["py"]

  try:
    import pip
    print("pip is installed")
  except ImportError:
    get_get_pip(PY_VERSION)
