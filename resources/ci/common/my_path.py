import os
import sys

def get_py_path():
  user_paths = os.environ["PATH"].split(os.pathsep)
  (python,py) = ("","")

  for path in user_paths:
    parts = path.split(os.sep)
    part = parts[len(parts) - 1].lower()
    if ("python" in part) and ('.' not in part):
      path.replace(os.sep,os.sep + os.sep)
      if path not in user_paths:
        py = path

  for path in sys.path:
    parts = path.split(os.sep)
    part = parts[len(parts) - 1].lower()
    if ("python" in part) and ('.' not in part):
      path.replace(os.sep,os.sep + os.sep)
      if path not in user_paths:
        python = path

  paths = (
    os.path.join(python,"") if python != "" else "",
    os.path.join(py,"") if py != "" else "",
    os.path.join(python,"Scripts","") if python != "" else ""
  )
  # print(paths)
  return paths

if __name__ == "__main__":
  get_py_path()
