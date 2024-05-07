import platform, sys, os, subprocess
try:
    import pkg_resources
except ModuleNotFoundError as e:
    pass
from datetime import datetime

from Main import __version__
DR_VERSION = __version__

PROJECT_NAME = "ALttP Door Randomizer"

def diagpad(str):
  return str.ljust(len(f"{PROJECT_NAME} Version") + 5,'.')

def output():
  lines = [
    f"{PROJECT_NAME} Diagnostics",
    "=================================",
    diagpad("UTC Time") + str(datetime.now(datetime.UTC))[:19],
    diagpad(f"{PROJECT_NAME} Version") + DR_VERSION,
    diagpad("Python Version") + platform.python_version()
  ]
  lines.append(diagpad("OS Version") + "%s %s" % (platform.system(), platform.release()))
  if hasattr(sys, "executable"):
    lines.append(diagpad("Executable") + sys.executable)
  lines.append(diagpad("Build Date") + platform.python_build()[1])
  lines.append(diagpad("Compiler") + platform.python_compiler())
  if hasattr(sys, "api_version"):
    lines.append(diagpad("Python API") + str(sys.api_version))
  if hasattr(os, "sep"):
    lines.append(diagpad("Filepath Separator") + os.sep)
  if hasattr(os, "pathsep"):
    lines.append(diagpad("Path Env Separator") + os.pathsep)
  lines.append("")
  lines.append("Packages")
  lines.append("--------")
  '''
  #this breaks when run from the .exe
  reqs = subprocess.check_output([sys.executable, '-m', 'pip', 'freeze'])
  installed_packages = [r.decode() for r in reqs.split()]
  for pkg in installed_packages:
   pkg = pkg.split("==")
   lines.append(diagpad(pkg[0]) + pkg[1])
  '''
  installed_packages = []
  installed_packages = [str(d) for d in pkg_resources.working_set]   #this doesn't work from the .exe either, but it doesn't crash the program
  installed_packages.sort()
  for pkg in installed_packages:
    pkg = pkg.split(' ')
    lines.append(diagpad(pkg[0]) + pkg[1])

  return lines

if __name__ == "__main__":
    raise AssertionError(f"Called main() on utility library {__file__}")
