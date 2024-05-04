'''
Build Entrypoints
'''
import json
import platform
import os  # for checking for dirs
import re
from json.decoder import JSONDecodeError
from subprocess import Popen, PIPE, STDOUT, CalledProcessError

DEST_DIRECTORY = "."

# UPX greatly reduces the filesize.  You can get this utility from https://upx.github.io/
# just place it in a subdirectory named "upx" and this script will find it
UPX_DIR = "upx"
if os.path.isdir(os.path.join(".", UPX_DIR)):
    upx_string = f"--upx-dir={UPX_DIR}"
else:
    upx_string = ""
GO = True
DIFF_DLLS = False

# set a global var for Actions to try to read
def set_output(name, value):
    with open(os.environ['GITHUB_OUTPUT'], 'a') as fh:
        print(f'{name}={value}', file=fh)

# build the thing
def run_build(slug):
    global GO
    global DIFF_DLLS

    print(f"Building '{slug}' via Python {platform.python_version()}")

    PYINST_EXECUTABLE = "pyinstaller"
    args = [
        os.path.join("source", f"{slug}.spec").replace(os.sep, os.sep * 2),
        upx_string,
        "-y",
        f"--distpath={DEST_DIRECTORY}"
    ]
    errs = []
    strs = []
    print("PyInstaller args: %s" % " ".join(args))
    cmd = [
      PYINST_EXECUTABLE,
      *args
    ]

    ret = {
      "stdout": [],
      "stderr": []
    }

    with Popen(cmd, stdout=PIPE, stderr=STDOUT, bufsize=1, universal_newlines=True) as p:
      for line in p.stdout:
        ret["stdout"].append(line)
        print(line, end='')
      # if p.stderr:
      #   for line in p.stderr:
      #     ret["stderr"].append(line)
      #     print(line, end='')
      # if p.returncode != 0:
      #   raise CalledProcessError(p.returncode, p.args)

    # check stdout & stderr
    for key in ["stdout","stderr"]:
      if len(ret[key]) > 0:
        for line in ret[key]:
          # UPX can't compress this file
          if "NotCompressibleException" in line.strip():
            print(line)
            errs.append(line.strip())
          # print UPX messages
          if "UPX" in line:
            print(line)
          # try to get DLL filename
          elif "NotCompressibleException" in line.strip():
            matches = re.search(r'api-ms-win-(?:[^-]*)-([^-]*)', line.strip())
            if matches:
                strAdd = matches.group(1)
                strs.append(strAdd)
                errs.append(line.strip())
    # print collected errors
    if len(errs) > 0:
      print("=" * 10)
      print("| ERRORS |")
      print("=" * 10)
      print("\n".join(errs))
    else:
      GO = False

    # if we identified DLLs to ignore
    if len(strs) > 0:
      # read DLLs manifest that we've already got saved
      with open(os.path.join(".","resources","app","meta","manifests","excluded_dlls.json"), "w+", encoding="utf-8") as dllsManifest:
        oldDLLs = []
        try:
          oldDLLs = json.load(dllsManifest)
        except JSONDecodeError as e:
          oldDLLs = []
        #   raise ValueError("Windows DLLs manifest malformed!")

        # bucket for new list
        newDLLs = sorted(list(set(oldDLLs)))

        # items to add
        addDLLs = sorted(list(set(strs)))

        # add items
        newDLLs += addDLLs
        newDLLs = sorted(list(set(newDLLs)))

        # if the lists differ, we've gotta update the included list
        diffDLLs = newDLLs != oldDLLs

        # set a global var for Actions to try to read
        if diffDLLs:
            set_output("error_dlls","Failed to compress DLLs!")

        if diffDLLs:
            DIFF_DLLS = True
            dllsManifest.seek(0)
            dllsManifest.truncate()
            dllsManifest.write(json.dumps(sorted(newDLLs), indent=2))

        print(f"Old DLLs:  {json.dumps(sorted(oldDLLs))}")
        print(f"Add DLLs:  {json.dumps(sorted(addDLLs))}")
        print(f"New DLLs:  {json.dumps(sorted(newDLLs))}")
        print(f"Diff DLLs: {DIFF_DLLS}")
    print("")

def go_build(slug):
    slug = slug or ""
    if slug != "":
        GO = True
        while GO:
            run_build(slug)
            GO = False

if __name__ == "__main__":
    go_build("DungeonRandomizer")
    go_build("Gui")
    go_build("MultiClient")
    go_build("MultiServer")
    go_build("Mystery")
    if DIFF_DLLS:
        print("🔴Had to update Error DLLs list!")
        exit(1)
